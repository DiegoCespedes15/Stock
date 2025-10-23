# Archivo: src/model_trainer.py - VERSIÓN COMPLETA MEJORADA

import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import os
import sys
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error 
import sqlalchemy
from sqlalchemy import text 
from datetime import datetime, timedelta

# Al principio del archivo, después de los imports
print("🔊 SCRIPT INICIADO - IMPORTS CARGADOS")

# --- CONFIGURACIÓN DE RUTAS Y CONEXIÓN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from data_connector import conectar_data_db 

RUTA_MODELO = os.path.join(current_dir, 'modelo_xgboost.pkl')
TABLA_TEMPORAL = 'prediccion_dataset' 
TABLA_PREDICCION = 'prediccion_mensual' 
SCHEMA = 'desarrollo'

def cargar_dataset_temporal():
    """
    Carga el dataset preparado directamente desde la tabla temporal de la BD.
    """
    engine = conectar_data_db()
    
    if engine is None:
        print("ERROR: La conexión a la base de datos falló.")
        return None
        
    try:
        sql_query = f"SELECT * FROM {SCHEMA}.{TABLA_TEMPORAL} ORDER BY anio, mes, dia_del_mes"
        
        print(f"📥 Cargando datos desde la tabla temporal '{TABLA_TEMPORAL}'...")
        df_dataset = pd.read_sql(sql_query, engine)
        
        if df_dataset.empty:
            print(f"❌ ERROR: El DataFrame está vacío.")
            return None
        
        print(f"✅ Dataset cargado: {len(df_dataset)} registros")
        return df_dataset
    
    except Exception as e:
        print(f"❌ ERROR al leer la tabla: {e}")
        return None
    finally:
        if engine:
            engine.dispose()

def crear_features_en_memoria(df_dataset):
    """
    Crea características avanzadas EN MEMORIA para el entrenamiento.
    """
    print("🔄 Creando características avanzadas en memoria...")
    df = df_dataset.copy()
    
    # Reconstruir fecha para features temporales
    df['v_fecha'] = pd.to_datetime(
        df['anio'].astype(str) + '-' + 
        df['mes'].astype(str) + '-' + 
        df['dia_del_mes'].astype(str)
    )
    
    # Features adicionales que NO van a la BD
    df['semana_del_anio'] = df['v_fecha'].dt.isocalendar().week
    df['es_fin_de_semana'] = (df['dia_de_la_semana'] >= 5).astype(int)
    df['es_inicio_mes'] = (df['dia_del_mes'] <= 7).astype(int)
    df['es_fin_mes'] = (df['dia_del_mes'] >= 25).astype(int)
    
    # Variables cíclicas
    df['mes_sin'] = np.sin(2 * np.pi * df['mes'] / 12)
    df['mes_cos'] = np.cos(2 * np.pi * df['mes'] / 12)
    df['dia_semana_sin'] = np.sin(2 * np.pi * df['dia_de_la_semana'] / 7)
    df['dia_semana_cos'] = np.cos(2 * np.pi * df['dia_de_la_semana'] / 7)
    
    # Features históricas (necesitan ordenamiento)
    df = df.sort_values(['v_id_producto', 'v_fecha'])
    
    # Medias móviles
    df['media_movil_7d'] = df.groupby('v_id_producto')['cantidad_vendida'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )
    df['media_movil_30d'] = df.groupby('v_id_producto')['cantidad_vendida'].transform(
        lambda x: x.rolling(window=30, min_periods=1).mean()
    )
    
    # Lag features
    for lag in [1, 7, 30]:
        df[f'lag_{lag}d'] = df.groupby('v_id_producto')['cantidad_vendida'].shift(lag)
    
    # Rellenar NaN
    df = df.fillna(0)
    
    print(f"✅ Características avanzadas creadas: {len(df.columns)} columnas totales")
    return df

def crear_features_futuras_mejorado(ultima_fecha, producto_id, df_historico, meses_prediccion=12):
    """
    Versión MEJORADA: Crea características futuras propagando el estado histórico.
    """
    # Obtener los últimos datos históricos del producto específico
    hist_producto = df_historico[df_historico['v_id_producto'] == producto_id].sort_values('v_fecha')
    
    # Calcular fecha de inicio (día siguiente al último dato)
    fecha_inicio = ultima_fecha + timedelta(days=1)
    
    # Generar rango de fechas futuras
    fechas_futuras = pd.date_range(
        start=fecha_inicio, 
        periods=meses_prediccion * 30,  # Aprox 30 días por mes
        freq='D'
    )
    
    # Crear DataFrame base
    df_futuro = pd.DataFrame({'v_fecha': fechas_futuras})
    
    # Características básicas (igual que antes)
    df_futuro['v_id_producto'] = producto_id
    df_futuro['dia_del_mes'] = df_futuro['v_fecha'].dt.day
    df_futuro['dia_de_la_semana'] = df_futuro['v_fecha'].dt.dayofweek
    df_futuro['mes'] = df_futuro['v_fecha'].dt.month
    df_futuro['anio'] = df_futuro['v_fecha'].dt.year
    df_futuro['semana_del_anio'] = df_futuro['v_fecha'].dt.isocalendar().week
    
    # Características avanzadas
    df_futuro['es_fin_de_semana'] = (df_futuro['dia_de_la_semana'] >= 5).astype(int)
    df_futuro['es_inicio_mes'] = (df_futuro['dia_del_mes'] <= 7).astype(int)
    df_futuro['es_fin_mes'] = (df_futuro['dia_del_mes'] >= 25).astype(int)
    
    # Variables cíclicas
    df_futuro['mes_sin'] = np.sin(2 * np.pi * df_futuro['mes'] / 12)
    df_futuro['mes_cos'] = np.cos(2 * np.pi * df_futuro['mes'] / 12)
    df_futuro['dia_semana_sin'] = np.sin(2 * np.pi * df_futuro['dia_de_la_semana'] / 7)
    df_futuro['dia_semana_cos'] = np.cos(2 * np.pi * df_futuro['dia_de_la_semana'] / 7)
    
    # 🔥 MEJORA CRÍTICA: Usar los últimos valores históricos conocidos
    if not hist_producto.empty:
        ultimos_valores = hist_producto.tail(30)  # Últimos 30 días
        
        # Usar el último valor conocido para lags y medias móviles
        ultima_media_7d = hist_producto['media_movil_7d'].iloc[-1] if 'media_movil_7d' in hist_producto.columns else 0
        ultima_media_30d = hist_producto['media_movil_30d'].iloc[-1] if 'media_movil_30d' in hist_producto.columns else 0
        ultimo_lag_1d = hist_producto['cantidad_vendida'].iloc[-1] if 'cantidad_vendida' in hist_producto.columns else 0
        ultimo_lag_7d = hist_producto['cantidad_vendida'].iloc[-7] if len(hist_producto) >= 7 else ultimo_lag_1d
        ultimo_lag_30d = hist_producto['cantidad_vendida'].iloc[-30] if len(hist_producto) >= 30 else ultimo_lag_1d
    else:
        ultima_media_7d = 0
        ultima_media_30d = 0
        ultimo_lag_1d = 0
        ultimo_lag_7d = 0
        ultimo_lag_30d = 0
    
    # Asignar valores iniciales basados en historia
    df_futuro['media_movil_7d'] = ultima_media_7d
    df_futuro['media_movil_30d'] = ultima_media_30d
    df_futuro['lag_1d'] = ultimo_lag_1d
    df_futuro['lag_7d'] = ultimo_lag_7d
    df_futuro['lag_30d'] = ultimo_lag_30d
    
    return df_futuro

def entrenar_y_predecir_mejorado():
    """
    Versión MEJORADA con características futuras más realistas.
    """
    print("🚀 INICIANDO ENTRENAMIENTO Y PREDICCIÓN MEJORADA...")
    
    # 1. Cargar datos históricos
    df_dataset = cargar_dataset_temporal()
    if df_dataset is None or df_dataset.empty:
        print("❌ ERROR: No se pudo cargar el dataset.")
        return 

    # 2. Crear features avanzadas EN MEMORIA
    df_dataset_completo = crear_features_en_memoria(df_dataset)
    
    # 3. Preparar características para entrenamiento
    feature_columns = [col for col in df_dataset_completo.columns 
                      if col not in ['cantidad_vendida', 'v_fecha']]
    
    X = df_dataset_completo[feature_columns]
    y = df_dataset_completo['cantidad_vendida']

    print(f"📊 Características para entrenamiento: {len(feature_columns)} columnas")
    
    # 4. Dividir datos cronológicamente
    split_point = int(len(X) * 0.8)
    X_train, X_test = X[:split_point], X[split_point:]
    y_train, y_test = y[:split_point], y[split_point:]
    
    # 5. Entrenar modelo con semilla fija y parámetros más determinísticos
    print("🤖 Entrenando modelo XGBoost MEJORADO...")
    modelo = xgb.XGBRegressor(
        objective='reg:squarederror', 
        n_estimators=300,
        learning_rate=0.1,
        max_depth=6,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,  # Semilla fija
        n_jobs=-1
    )

    modelo.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # 6. Evaluación
    predicciones_test = modelo.predict(X_test)
    rmse = root_mean_squared_error(y_test, predicciones_test)
    print(f"✅ Entrenamiento completado. RMSE: {rmse:.2f} unidades")
    
    # 7. PREDICCIÓN FUTURA MEJORADA
    print("🔮 Generando predicciones futuras MEJORADAS...")
    
    ultima_fecha = df_dataset_completo['v_fecha'].max()
    productos_unicos = df_dataset_completo['v_id_producto'].unique()
    todas_predicciones = []
    
    for i, producto_id in enumerate(productos_unicos):
        if i % 10 == 0:
            print(f"   Procesando producto {i+1}/{len(productos_unicos)} (ID: {producto_id})...")
            
        # 🔥 USAR VERSIÓN MEJORADA
        df_futuro_completo = crear_features_futuras_mejorado(
            ultima_fecha, producto_id, df_dataset_completo, meses_prediccion=12
        )
        
        fechas_futuras = df_futuro_completo['v_fecha'].copy()
        df_futuro_features = df_futuro_completo[feature_columns]
        
        # Predecir
        predicciones_futuras = modelo.predict(df_futuro_features)
        
        # Crear DataFrame de resultados
        for fecha, pred in zip(fechas_futuras, predicciones_futuras):
            todas_predicciones.append({
                'v_id_producto': producto_id,
                'dia_del_mes': fecha.day,
                'dia_de_la_semana': fecha.weekday(),
                'mes': fecha.month,
                'anio': fecha.year,
                'cantidad_vendida_real': 0,
                'cantidad_predicha': max(0, float(pred)),
                'fecha_entrenamiento': datetime.now()
            })
    
    # 8. Guardar en BD (igual que antes)
    df_predicciones_futuras = pd.DataFrame(todas_predicciones)
    
    engine = conectar_data_db()
    if engine is None: 
        print("❌ No se pudo conectar a la BD")
        return
    
    try:
        with engine.connect() as conn:
            print(f"🗃️ Limpiando tabla: {SCHEMA}.{TABLA_PREDICCION}...")
            conn.execute(text(f"TRUNCATE TABLE {SCHEMA}.{TABLA_PREDICCION} RESTART IDENTITY;"))
            conn.commit()
            
            print("💿 Insertando nuevas predicciones...")
            df_predicciones_futuras.to_sql(
                TABLA_PREDICCION, 
                conn, 
                schema=SCHEMA, 
                if_exists='append', 
                index=False
            )
            conn.commit()
            print("✅ Predicciones futuras MEJORADAS guardadas exitosamente")
            
    except Exception as e:
        print(f"❌ Error al guardar predicciones: {e}")
        import traceback
        traceback.print_exc()
        return
    finally:
        if engine: 
            engine.dispose()
    
    # 9. Guardar modelo
    try:
        with open(RUTA_MODELO, 'wb') as f:
            pickle.dump(modelo, f)
        print("✅ Modelo guardado exitosamente")
    except Exception as e:
        print(f"❌ Error al guardar modelo: {e}")
    
    print("🎯 Proceso MEJORADO completado exitosamente!")
    
def test_ejecucion():
    print("🧪 TEST: Script se está ejecutando correctamente")
    return True

# 🔥 ESTO DEBE SER LO ÚLTIMO EN EL ARCHIVO 🔥
if __name__ == "__main__":
    print("🔊 INICIANDO SCRIPT DESDE __main__")
    
    try:
        test_ejecucion()
        print("🔊 TEST COMPLETADO - LLAMANDO entrenar_y_predecir()")
        entrenar_y_predecir_mejorado()
        print("🔊 PROCESO COMPLETADO EXITOSAMENTE")
    except Exception as e:
        print(f"❌ ERROR NO MANEJADO: {e}")
        import traceback
        traceback.print_exc()   