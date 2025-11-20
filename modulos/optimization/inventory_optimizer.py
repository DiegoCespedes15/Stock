import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# Ajuste de rutas para importar bd
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir)) # Subir dos niveles
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from src.bd import conectar_db

# --- CONSTANTES DE NEGOCIO (Configurables) ---
COSTO_HACER_PEDIDO = 50.0   # Costo fijo por emitir una orden de compra (ej. $50)
COSTO_ALMACENAMIENTO = 0.20 # Porcentaje del valor del producto (20% anual)
LEAD_TIME_DIAS = 7          # Tiempo promedio que tarda el proveedor en entregar
STOCK_SEGURIDAD_FACTOR = 1.65 # Z-score para 95% de nivel de servicio

def obtener_datos_combinados(simulated_date_str=None):
    """
    Une predicciones, stock y costos, usando una fecha simulada.
    """
    conn = conectar_db()
    if conn is None: return pd.DataFrame()

    # ✅ LÓGICA DE FECHA SIMULADA
    # Si no nos dan fecha, usamos la real. Si nos la dan, la usamos.
    if simulated_date_str:
        fecha_base = simulated_date_str # ej: "2024-11-16"
        print(f"Simulando reporte para la fecha: {fecha_base}")
    else:
        fecha_base = datetime.now().strftime('%Y-%m-%d')
        
    # Usamos placeholders (%s) para la fecha base
    sql = """
        WITH PrediccionMes AS (
            SELECT 
                v_id_producto,
                ROUND(SUM(cantidad_predicha)::numeric, 2) as demanda_proximos_30_dias
            FROM desarrollo.prediccion_mensual
            WHERE v_fecha BETWEEN %(fecha)s::date AND (%(fecha)s::date + INTERVAL '30 days')
            GROUP BY v_id_producto
        )
        SELECT 
            s.id_articulo,
            s.descripcion,
            s.categoria,
            COALESCE(s.cant_inventario, 0) as stock_actual,
            COALESCE(s.precio_unit, 10) as costo_unitario, -- Usamos precio_unit como costo
            COALESCE(p.demanda_proximos_30_dias, 0) as demanda_predicha_mes
        FROM desarrollo.stock s
        LEFT JOIN PrediccionMes p ON s.id_articulo = p.v_id_producto
    """
    
    try:
        # Pasamos la fecha como parámetro
        df = pd.read_sql(sql, conn, params={"fecha": fecha_base})
        return df
    except Exception as e:
        print(f"❌ Error obteniendo datos para optimización: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def calcular_recomendacion_compra(df):
    """
    Aplica fórmulas de EOQ y ROP usando la demanda predicha por XGBoost.
    """
    if df.empty: return df

    print("🧮 Calculando métricas de optimización de inventario...")

    # 1. Demanda Diaria Estimada
    df["demanda_diaria_avg"] = df["demanda_predicha_mes"] / 30

    # 2. Punto de Reorden (ROP) Dinámico
    stock_seguridad = df["demanda_diaria_avg"] * np.sqrt(LEAD_TIME_DIAS) * STOCK_SEGURIDAD_FACTOR
    df["punto_reorden"] = (df["demanda_diaria_avg"] * LEAD_TIME_DIAS) + stock_seguridad

    # 3. Estado del Inventario
    df["accion_sugerida"] = np.where(df["stock_actual"] <= df["punto_reorden"], "COMPRAR URGENTE", "Stock Saludable")

    # 4. Cantidad Económica de Pedido (EOQ)
    demanda_anual_estimada = df["demanda_predicha_mes"] * 12
    df["costo_holding_anual"] = df["costo_unitario"] * COSTO_ALMACENAMIENTO
    
    df["cantidad_a_comprar_eoq"] = np.sqrt(
        (2 * demanda_anual_estimada * COSTO_HACER_PEDIDO) / (df["costo_holding_anual"] + 0.0001) # Se añade +0.0001 para evitar división por cero
    )
    
    df["cantidad_a_comprar_eoq"] = df["cantidad_a_comprar_eoq"].fillna(0).round(0).astype(int)

    # 5. Lógica Final de Cantidad
    df["sugerencia_cantidad"] = np.where(
        df["accion_sugerida"] == "COMPRAR URGENTE", 
        df["cantidad_a_comprar_eoq"], 
        0
    )
    
    # ✅ CORRECCIÓN AQUÍ:
    # Primero asignamos 'minimo_pedido' como una columna en el DataFrame
    df["minimo_pedido"] = df["punto_reorden"] - df["stock_actual"]
    
    # Ahora esta línea funcionará porque ambas columnas existen
    df["sugerencia_cantidad"] = df[["sugerencia_cantidad", "minimo_pedido"]].max(axis=1)
    
    # Aseguramos que la cantidad sugerida no sea negativa
    df["sugerencia_cantidad"] = np.clip(df["sugerencia_cantidad"], 0, None).round(0).astype(int)

    # Formateo final para reporte
    df["punto_reorden"] = df["punto_reorden"].round(0).astype(int)
    
    return df

def generar_dataset_reporte(categoria_filtro, simulated_date_str=None):
    """
    Función principal para llamar desde tu módulo de reportes PDF/Excel.
    Ahora acepta una fecha simulada.
    """
    # 1. Obtener datos usando la fecha simulada
    df_raw = obtener_datos_combinados(simulated_date_str)
    if df_raw.empty:
        return pd.DataFrame()
    
    # 2. Filtrar por categoría (después de obtener todos los datos)
    if categoria_filtro != "Todas las Categorías":
        df_filtrado = df_raw[df_raw["categoria"] == categoria_filtro].copy()
    else:
        df_filtrado = df_raw.copy()

    # 3. Calcular optimización
    df_optin = calcular_recomendacion_compra(df_filtrado)
    
    cols_reporte = [
        "id_articulo", "descripcion", "categoria", 
        "stock_actual", "demanda_predicha_mes", 
        "punto_reorden", "accion_sugerida", "sugerencia_cantidad"
    ]
    
    # Asegurarse de que las columnas existan
    cols_presentes = [col for col in cols_reporte if col in df_optin.columns]
    
    return df_optin[cols_presentes].sort_values("accion_sugerida")

# Prueba rápida
if __name__ == "__main__":
    df = generar_dataset_reporte()
    print(df.head(10).to_string())