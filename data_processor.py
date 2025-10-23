# Archivo: src/feature_engineering/data_processor.py

import pandas as pd
from datetime import datetime
import os
import sys
import sqlalchemy
from sqlalchemy import text 
import numpy as np

# Ajuste del path para asegurar la importación del nuevo módulo
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from data_connector import conectar_data_db

# Nombre de la tabla temporal donde guardaremos el dataset final
TABLA_TEMPORAL = 'prediccion_dataset' 
SCHEMA = 'desarrollo'

def obtener_datos_brutos(engine):
    """
    Extrae el historial de ventas usando el Engine proporcionado.
    MEJORADO: Incluye filtro por fecha para datos más recientes.
    """
    try:
        # Obtener solo datos de los últimos 2 años para mejor rendimiento
        fecha_limite = (datetime.now() - pd.DateOffset(years=2)).strftime('%Y-%m-%d')
        
        sql_query = f"""
            SELECT v_fecha, v_id_producto, v_cantidad 
            FROM {SCHEMA}.ventas 
            WHERE v_fecha >= '{fecha_limite}'
            ORDER BY v_fecha ASC
        """
        df_ventas = pd.read_sql(sql_query, engine)
        print(f"📊 Datos brutos obtenidos: {len(df_ventas)} registros desde {fecha_limite}")
        return df_ventas
    
    except Exception as e:
        print(f"❌ Error al obtener datos de ventas: {e}")
        return pd.DataFrame()

def crear_features_temporales(df):
    """
    Crea características temporales mejoradas para el modelo.
    """
    df_temp = df.copy()
    
    # Características básicas
    df_temp['dia_del_mes'] = df_temp['v_fecha'].dt.day
    df_temp['dia_de_la_semana'] = df_temp['v_fecha'].dt.dayofweek
    df_temp['mes'] = df_temp['v_fecha'].dt.month
    df_temp['anio'] = df_temp['v_fecha'].dt.year
    df_temp['semana_del_anio'] = df_temp['v_fecha'].dt.isocalendar().week
    
    # Características avanzadas
    df_temp['es_fin_de_semana'] = (df_temp['dia_de_la_semana'] >= 5).astype(int)
    df_temp['es_inicio_mes'] = (df_temp['dia_del_mes'] <= 7).astype(int)
    df_temp['es_fin_mes'] = (df_temp['dia_del_mes'] >= 25).astype(int)
    
    # Variables cíclicas para mes y día de la semana
    df_temp['mes_sin'] = np.sin(2 * np.pi * df_temp['mes'] / 12)
    df_temp['mes_cos'] = np.cos(2 * np.pi * df_temp['mes'] / 12)
    df_temp['dia_semana_sin'] = np.sin(2 * np.pi * df_temp['dia_de_la_semana'] / 7)
    df_temp['dia_semana_cos'] = np.cos(2 * np.pi * df_temp['dia_de_la_semana'] / 7)
    
    return df_temp

def agregar_features_historicas(df):
    """
    Agrega características históricas (medias móviles, etc.)
    """
    df_hist = df.copy()
    df_hist = df_hist.sort_values(['v_id_producto', 'v_fecha'])
    
    # Media móvil de 7 y 30 días
    df_hist['media_movil_7d'] = df_hist.groupby('v_id_producto')['cantidad_vendida'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )
    df_hist['media_movil_30d'] = df_hist.groupby('v_id_producto')['cantidad_vendida'].transform(
        lambda x: x.rolling(window=30, min_periods=1).mean()
    )
    
    # Lag features (ventas de días anteriores)
    for lag in [1, 7, 30]:
        df_hist[f'lag_{lag}d'] = df_hist.groupby('v_id_producto')['cantidad_vendida'].shift(lag)
    
    # Rellenar NaN con 0 o valores apropiados
    df_hist = df_hist.fillna(0)
    
    return df_hist

def preparar_y_guardar_dataset():
    """
    Función principal SIMPLIFICADA: Solo guarda las 5 columnas básicas en la BD.
    Las características avanzadas se crearán en memoria durante el entrenamiento.
    """
    engine = conectar_data_db() 
    if engine is None:
        print("❌ No se pudo conectar a la base de datos")
        return False

    try:
        print("🔄 Obteniendo y preparando datos...")
        df_ventas = obtener_datos_brutos(engine)
        
        if df_ventas.empty:
            print("❌ Error: No se encontraron datos para la predicción.")
            return False

        # Convertir fecha
        df_ventas['v_fecha'] = pd.to_datetime(df_ventas['v_fecha'])
        
        print("📈 Aplicando agregación básica...")
        
        # 1. Agregación inicial por fecha y producto
        df_agregado = df_ventas.groupby(['v_fecha', 'v_id_producto']).agg(
            cantidad_vendida=('v_cantidad', 'sum')
        ).reset_index()

        # 2. Crear características BÁSICAS (solo las que caben en la tabla existente)
        df_agregado['dia_del_mes'] = df_agregado['v_fecha'].dt.day
        df_agregado['dia_de_la_semana'] = df_agregado['v_fecha'].dt.dayofweek
        df_agregado['mes'] = df_agregado['v_fecha'].dt.month
        df_agregado['anio'] = df_agregado['v_fecha'].dt.year
        
        print(f"📊 Datos después de agregación: {len(df_agregado)} registros")

        # 3. Filtrar datos válidos (eliminar outliers extremos)
        Q1 = df_agregado['cantidad_vendida'].quantile(0.01)
        Q3 = df_agregado['cantidad_vendida'].quantile(0.99)
        df_filtrado = df_agregado[
            (df_agregado['cantidad_vendida'] >= Q1) & 
            (df_agregado['cantidad_vendida'] <= Q3)
        ]
        
        print(f"📊 Datos después de filtrar outliers: {len(df_filtrado)} registros")
        print(f"📈 Rango de ventas: {df_filtrado['cantidad_vendida'].min()} - {df_filtrado['cantidad_vendida'].max()}")
        
        # 4. Seleccionar SOLO las columnas que existen en la tabla
        columnas_compatibles = [
            'v_id_producto', 
            'dia_del_mes', 
            'dia_de_la_semana', 
            'mes', 
            'anio',
            'cantidad_vendida'
        ]
        
        df_final = df_filtrado[columnas_compatibles]

        # 5. Guardar en base de datos
        with engine.connect() as conn: 
            
            print(f"🗃️ Limpiando tabla: {SCHEMA}.{TABLA_TEMPORAL}...")
            try:
                conn.execute(text(f"TRUNCATE TABLE {SCHEMA}.{TABLA_TEMPORAL} RESTART IDENTITY;"))
                conn.commit()
                print("✅ Tabla limpiada exitosamente")
            except Exception as e:
                print(f"ℹ️ TRUNCATE falló. La tabla será creada/sobrescrita por Pandas. Error: {e}")
                
            print(f"💾 Insertando dataset de {len(df_final)} registros...")
            
            df_final.to_sql(
                TABLA_TEMPORAL, 
                conn,             
                schema=SCHEMA, 
                if_exists='append', 
                index=False
            )
            conn.commit()
            
        print(f"✅ Dataset guardado exitosamente con {len(df_final)} registros")
        print("📝 Columnas guardadas: v_id_producto, dia_del_mes, dia_de_la_semana, mes, anio, cantidad_vendida")
        print("💡 Las características avanzadas se crearán en memoria durante el entrenamiento")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al guardar el dataset en la base de datos: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    success = preparar_y_guardar_dataset()
    if success:
        print("🎉 Proceso de preparación de datos completado exitosamente")
    else:
        print("💥 Proceso de preparación de datos falló")