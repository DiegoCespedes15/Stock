# Archivo: src/model_trainer.py

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

# --- CONFIGURACIÓN DE RUTAS Y CONEXIÓN ---

# Ajuste del path para asegurar la importación del módulo 'data_connector'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Importamos el conector que devuelve el Engine de SQLAlchemy
from data_connector import conectar_data_db 

# Ubicación del modelo guardado
RUTA_MODELO = os.path.join(current_dir, 'modelo_xgboost.pkl')

# Tablas en la base de datos
TABLA_TEMPORAL = 'prediccion_dataset' 
TABLA_PREDICCION = 'prediccion_mensual' 
SCHEMA = 'desarrollo'


def cargar_dataset_temporal():
    """
    Carga el dataset preparado directamente desde la tabla temporal de la BD.
    """
    engine = conectar_data_db()
    
    # 🚨 DEBUG: Verifica si el motor se creó correctamente
    if engine is None:
        print("ERROR: La conexión a la base de datos falló (Engine is None). Revisar variables de entorno o credenciales.")
        return None
        
    try:
        sql_query = f"SELECT * FROM {SCHEMA}.{TABLA_TEMPORAL} ORDER BY anio, mes, dia_del_mes"
        
        print(f"Cargando datos desde la tabla temporal '{TABLA_TEMPORAL}'...")
        df_dataset = pd.read_sql(sql_query, engine)
        
        if df_dataset.empty:
            print(f"ERROR CRÍTICO al leer la tabla '{TABLA_TEMPORAL}': El DataFrame está vacío.")
            return None
        
        return df_dataset
    
    except Exception as e:
        # 🚨 DEBUG: Imprime el error si la lectura SQL falla
        print(f"ERROR CRÍTICO al leer la tabla '{TABLA_TEMPORAL}': {e}")
        return None
    finally:
        if engine:
            engine.dispose()


def entrenar_modelo():
    # ... (Se omite la primera parte de la función que permanece igual) ...
    
    df_dataset = cargar_dataset_temporal()
    
    if df_dataset is None or df_dataset.empty:
        print("ERROR CRÍTICO: No se pudo cargar el dataset o el DataFrame está vacío. El script terminará.")
        return 

    print("Preparando X (features) e y (target)...")
    
    # ----------------------------------------------------
    # 1. PREPARACIÓN DE DATOS PARA ML
    # ----------------------------------------------------
    # X (features): Las columnas que el modelo necesita para la predicción
    X = df_dataset[[
        'v_id_producto', 
        'dia_del_mes', 
        'dia_de_la_semana', 
        'mes', 
        'anio'
    ]]
    
    # y (target): La columna objetivo
    y = df_dataset['cantidad_vendida']

    # Dividir datos para evaluación (80/20 cronológica)
    split_point = int(len(X) * 0.8)
    X_train, X_test = X[:split_point], X[split_point:]
    y_train, y_test = y[:split_point], y[split_point:]
    
    # ----------------------------------------------------
    # 2. ENTRENAMIENTO y EVALUACIÓN
    # ----------------------------------------------------
    print("Entrenando el modelo XGBoost (Regresión)...")
    modelo = xgb.XGBRegressor(
        objective='reg:squarederror', 
        n_estimators=1000, 
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        n_jobs=-1
    )

    # Entrenar el modelo (Se eliminó 'early_stopping_rounds' para evitar TypeError)
    modelo.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False 
    )

    # Evaluación
    predicciones_test = modelo.predict(X_test)
    rmse = root_mean_squared_error(y_test, predicciones_test)
    print(f"Entrenamiento completado. El RMSE en prueba es: {rmse:.2f} unidades.")

    # ----------------------------------------------------
    # 3. GENERAR PREDICCIONES Y PREPARAR RESULTADOS PARA GUARDAR
    # ----------------------------------------------------
    print("Generando predicciones históricas para todos los datos...")
    
    # Generar predicciones sobre el dataset COMPLETO (X)
    predicciones_completas = modelo.predict(X)
    
    # Crear el DataFrame de resultados para guardar en BD
    df_resultados = df_dataset.copy()
    
    # Renombrar la columna real
    df_resultados = df_resultados.rename(columns={'cantidad_vendida': 'cantidad_vendida_real'})
    
    # Añadir la predicción
    df_resultados['cantidad_predicha'] = predicciones_completas.round().astype(int)
    
    # Seleccionar solo las columnas que coinciden con el DDL de la tabla histórica
    # Esto garantiza que no haya valores nulos o columnas faltantes.
    df_resultados = df_resultados[[
        'v_id_producto', 
        'dia_del_mes', 
        'dia_de_la_semana', 
        'mes', 
        'anio', 
        'cantidad_vendida_real',
        'cantidad_predicha'
    ]]
    
    # Agregar la columna de auditoría (si existe en el DDL de la BD)
    df_resultados['fecha_entrenamiento'] = pd.Timestamp.now()
    
    # ----------------------------------------------------
    
    print(f"Guardando {len(df_resultados)} predicciones en la tabla histórica...")
    engine = conectar_data_db()
    if engine is None: return
    
    try:
        with engine.connect() as conn:
            # Limpiar la tabla histórica antes de insertar nuevos resultados
            conn.execute(text(f"TRUNCATE TABLE {SCHEMA}.{TABLA_PREDICCION} RESTART IDENTITY;"))
            
            df_resultados.to_sql(
                TABLA_PREDICCION, 
                conn, 
                schema=SCHEMA, 
                if_exists='append', 
                index=False
            )
            conn.commit()
            print("Predicciones históricas guardadas exitosamente en la BD.")
            
    except Exception as e:
        print(f"ERROR al guardar predicciones históricas en la base de datos: {e}")
        return
    finally:
        if engine: engine.dispose()
    
    # ----------------------------------------------------
    # 5. GUARDAR MODELO .PKL (BLOQUE FALTANTE RESTAURADO)
    # ----------------------------------------------------
    print(f"Guardando el modelo .pkl en: {RUTA_MODELO}")
    with open(RUTA_MODELO, 'wb') as f:
        pickle.dump(modelo, f)
    
    print("Modelo y Predicciones actualizados con éxito")


if __name__ == "__main__":
    try:
        entrenar_modelo()
    except Exception as e:
        print(f"ERROR NO MANEJADO DURANTE EL ENTRENAMIENTO: {e}")