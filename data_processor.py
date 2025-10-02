# Archivo: src/feature_engineering/data_processor.py

import pandas as pd
from datetime import datetime
import os
import sys
import sqlalchemy
from sqlalchemy import text # Necesaria para el TRUNCATE

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
    """
    try:
        sql_query = f"SELECT v_fecha, v_id_producto, v_cantidad FROM {SCHEMA}.ventas ORDER BY v_fecha ASC"
        df_ventas = pd.read_sql(sql_query, engine)
        return df_ventas
    
    except Exception as e:
        print(f"Error al obtener datos de ventas: {e}")
        return pd.DataFrame()


def preparar_y_guardar_dataset():
    """
    Función principal: Conecta, extrae, aplica Feature Engineering y guarda.
    """
    engine = conectar_data_db() 
    if engine is None:
        return False

    try:
        print("Obteniendo y preparando datos...")
        df_ventas = obtener_datos_brutos(engine)
        
        if df_ventas.empty:
            print("Error: No se encontraron datos para la predicción.")
            return False

        print(f"Datos brutos obtenidos: {len(df_ventas)} registros.")
        
        # 2. Ingeniería de Características (Preparación de df_final)
        df_ventas['v_fecha'] = pd.to_datetime(df_ventas['v_fecha'])
        
        df_agregado = df_ventas.groupby(['v_fecha', 'v_id_producto']).agg(
            cantidad_vendida=('v_cantidad', 'sum')
        ).reset_index()

        df_agregado['dia_del_mes'] = df_agregado['v_fecha'].dt.day
        df_agregado['dia_de_la_semana'] = df_agregado['v_fecha'].dt.dayofweek
        df_agregado['mes'] = df_agregado['v_fecha'].dt.month
        df_agregado['anio'] = df_agregado['v_fecha'].dt.year
        
        df_agregado['v_id_producto'] = df_agregado['v_id_producto'].astype('category').cat.codes
        
        df_final = df_agregado[[
            'v_id_producto', 
            'dia_del_mes', 
            'dia_de_la_semana', 
            'mes', 
            'anio',
            'cantidad_vendida'
        ]]

        # 3. Conexión, Limpieza y Guardado
        with engine.connect() as conn: 
            
            # 3.1. Intentar limpiar la tabla con TRUNCATE
            print(f"Limpiando tabla: {SCHEMA}.{TABLA_TEMPORAL}...")
            try:
                conn.execute(text(f"TRUNCATE TABLE {SCHEMA}.{TABLA_TEMPORAL} RESTART IDENTITY;"))
                conn.commit()
            except Exception as e:
                print(f"Aviso: TRUNCATE falló. La tabla será creada por Pandas. {e}")
                
            # 3.2. Guardar el nuevo dataset preparado
            print(f"Insertando nuevo dataset de {len(df_final)} registros...")
            
            df_final.to_sql(
                TABLA_TEMPORAL, 
                conn,             
                schema=SCHEMA, 
                if_exists='append', 
                index=False
            )
            conn.commit()
            
        print(f"Dataset guardado exitosamente.")
        return True
        
    except Exception as e:
        print(f"❌ Error al guardar el dataset en la base de datos: {e}")
        return False
        
    finally:
        if engine:
            engine.dispose() # Asegurar que el Engine se libere


if __name__ == "__main__":
    preparar_y_guardar_dataset()