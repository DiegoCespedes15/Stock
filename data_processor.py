# Archivo: src/feature_engineering/data_processor.py

import pandas as pd
from datetime import datetime
import os
import sys
from sqlalchemy import text
import numpy as np

# --- Ajuste del path para asegurar la importación del módulo de conexión ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Asumo que este es el nombre correcto de tu archivo de conexión
try:
    from data_connector import conectar_data_db
except ImportError:
    # Fallback si data_connector está en otro lado o tiene otro nombre
    from bd import conectar_db as conectar_data_db

# --- Configuración general ---
TABLA_TEMPORAL = 'prediccion_dataset'
SCHEMA = 'desarrollo'

def obtener_datos_brutos(engine):
    """
    Extrae el historial de ventas diarias agregado por producto.
    Se optimiza haciendo la primera agregación en SQL.
    """
    try:
        # Usamos 2 años completos hacia atrás desde hoy
        fecha_limite = (datetime.now() - pd.DateOffset(years=2)).strftime('%Y-%m-%d')

        sql_query = f"""
            SELECT 
                DATE(v.v_fecha) as v_fecha,
                v.v_id_producto,
                SUM(v.v_cantidad) as cantidad_vendida
            FROM {SCHEMA}.ventas v
            WHERE v.v_fecha >= '{fecha_limite}'
            GROUP BY DATE(v.v_fecha), v.v_id_producto
            ORDER BY v_fecha ASC
        """
        print(f"🔄 Ejecutando query de ventas desde {fecha_limite}...")
        df_ventas = pd.read_sql(sql_query, engine)
        
        # Asegurar tipos correctos
        df_ventas['v_fecha'] = pd.to_datetime(df_ventas['v_fecha'])
        df_ventas['cantidad_vendida'] = pd.to_numeric(df_ventas['cantidad_vendida'], errors='coerce').fillna(0)
        
        print(f"📊 Datos brutos obtenidos: {len(df_ventas)} registros diarios por producto.")
        return df_ventas

    except Exception as e:
        print(f"❌ Error al obtener datos de ventas: {e}")
        return pd.DataFrame()

def obtener_maestro_productos(engine):
    """
    Recupera el catálogo único de productos con su categoría.
    Asegura un solo registro por producto para evitar duplicados.
    """
    try:
        # Usamos DISTINCT ON o GROUP BY para asegurar unicidad por producto.
        # Ajusta la lógica de selección de categoría si un producto puede tener varias.
        sql = f"""
            SELECT DISTINCT ON (s.id_articulo)
                s.id_articulo AS v_id_producto,
                COALESCE(g.gar_categoria, s.categoria, 'Sin Categoría') as categoria
            FROM {SCHEMA}.stock s
            LEFT JOIN {SCHEMA}.garantias g 
                ON s.categoria = g.gar_categoria
            ORDER BY s.id_articulo, g.gar_categoria -- Para que DISTINCT ON funcione bien
        """
        df_cat = pd.read_sql(sql, engine)
        print(f"🧩 Maestro de productos cargado: {len(df_cat)} productos únicos")
        return df_cat
    except Exception as e:
        print(f"⚠️ Error al obtener maestro de productos: {e}")
        return pd.DataFrame(columns=['v_id_producto', 'categoria'])

def rellenar_dias_sin_ventas(df_ventas, df_productos):
    """
    Genera un registro con venta 0 para los días que un producto no tuvo ventas.
    Fundamental para series temporales.
    """
    print("⏳ Rellenando días sin ventas (esto puede tardar)...")
    
    # Rango completo de fechas
    fecha_min = df_ventas['v_fecha'].min()
    fecha_max = df_ventas['v_fecha'].max()
    todas_fechas = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    
    # Crear un DataFrame con todas las combinaciones posibles (producto x fecha)
    # Usamos MultiIndex para hacer esto eficientemente
    idx = pd.MultiIndex.from_product(
        [todas_fechas, df_productos['v_id_producto'].unique()],
        names=['v_fecha', 'v_id_producto']
    )
    df_completo = pd.DataFrame(index=idx).reset_index()
    
    # Unir con las ventas reales
    df_final = pd.merge(
        df_completo, 
        df_ventas, 
        on=['v_fecha', 'v_id_producto'], 
        how='left'
    )
    
    # Rellenar con 0 las ventas faltantes
    df_final['cantidad_vendida'] = df_final['cantidad_vendida'].fillna(0)
    
    print(f"📈 Dataset expandido: {len(df_ventas)} -> {len(df_final)} registros")
    return df_final

def preparar_y_guardar_dataset():
    engine = conectar_data_db()
    if engine is None:
        print("❌ No se pudo conectar a la base de datos")
        return False

    try:
        print("🚀 Iniciando procesador de datos...")

        # 1️⃣ Obtener datos
        df_ventas = obtener_datos_brutos(engine)
        df_productos = obtener_maestro_productos(engine)

        if df_ventas.empty or df_productos.empty:
            print("❌ Error: Datos insuficientes para continuar.")
            return False

        # 2️⃣ Rellenar días sin ventas (CRÍTICO para time series)
        # Filtramos df_productos para usar solo los que tienen ventas alguna vez
        productos_activos = df_ventas['v_id_producto'].unique()
        df_productos_activos = df_productos[df_productos['v_id_producto'].isin(productos_activos)]
        
        df_completo = rellenar_dias_sin_ventas(df_ventas, df_productos_activos)

        # 3️⃣ Enriquecer con categorías
        df_final = pd.merge(df_completo, df_productos, on='v_id_producto', how='left')
        df_final['categoria'] = df_final['categoria'].fillna('Sin categoría')

        # 4️⃣ Crear columnas de fecha
        df_final['anio'] = df_final['v_fecha'].dt.year
        df_final['mes'] = df_final['v_fecha'].dt.month
        df_final['dia_del_mes'] = df_final['v_fecha'].dt.day
        df_final['dia_de_la_semana'] = df_final['v_fecha'].dt.dayofweek

        # 5️⃣ Filtrado de Outliers (Opcional pero recomendado hacerlo POR PRODUCTO)
        # Un enfoque simple es eliminar solo extremos absurdos globalmente para no distorsionar
        # O mejor, usar clipping en lugar de eliminar filas.
        print("✂️ Aplicando clipping de outliers extremos...")
        limite_superior = df_final['cantidad_vendida'].quantile(0.999) # Muy conservador
        df_final['cantidad_vendida'] = df_final['cantidad_vendida'].clip(upper=limite_superior)

        # 6️⃣ Guardar en BD
        print(f"💾 Guardando {len(df_final)} registros en {SCHEMA}.{TABLA_TEMPORAL}...")
        
        # Usamos 'replace' para que recree la tabla con las columnas nuevas (como v_fecha)
        # Ya no es necesario el TRUNCATE previo si usamos replace, pero el engine.begin() es bueno mantenerlo.
        with engine.begin() as conn:
            df_final.to_sql(
                TABLA_TEMPORAL,
                con=conn,
                schema=SCHEMA,
                if_exists='replace',  # <--- CAMBIO CLAVE: 'replace' en lugar de 'append'
                index=False,
                chunksize=10000
            )
        
        print("✅ Dataset preparado y guardado exitosamente.")
        return True

    except Exception as e:
        print(f"❌ Error crítico en data_processor: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            engine.dispose()
        except:
            pass

if __name__ == "__main__":
    preparar_y_guardar_dataset()