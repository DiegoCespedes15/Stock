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
COSTO_HACER_PEDIDO = 50.0   # Costo fijo por emitir una orden de compra
COSTO_ALMACENAMIENTO = 0.20 # 20% anual
LEAD_TIME_DIAS = 7          # Tiempo de proveedor
STOCK_SEGURIDAD_FACTOR = 1.65 # Z-score 95%

def obtener_datos_combinados(simulated_date_str=None):
    """
    Une predicciones, stock y costos, usando una fecha simulada.
    """
    conn = conectar_db()
    if conn is None: return pd.DataFrame()

    if simulated_date_str:
        fecha_base = simulated_date_str
        print(f"Simulando reporte para la fecha: {fecha_base}")
    else:
        fecha_base = datetime.now().strftime('%Y-%m-%d')
        
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
            COALESCE(s.precio_unit, 10) as costo_unitario,
            COALESCE(p.demanda_proximos_30_dias, 0) as demanda_predicha_mes
        FROM desarrollo.stock s
        LEFT JOIN PrediccionMes p ON s.id_articulo = p.v_id_producto
    """
    
    try:
        df = pd.read_sql(sql, conn, params={"fecha": fecha_base})
        return df
    except Exception as e:
        print(f"❌ Error obteniendo datos para optimización: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def calcular_recomendacion_compra(df):
    """
    Aplica fórmulas de EOQ, ROP y Proyecciones.
    """
    if df.empty: return df

    print("🧮 Calculando métricas de optimización de inventario...")

    # 1. Demanda Diaria Estimada
    df["demanda_diaria_avg"] = df["demanda_predicha_mes"] / 30

    # 2. Punto de Reorden (ROP)
    stock_seguridad = df["demanda_diaria_avg"] * np.sqrt(LEAD_TIME_DIAS) * STOCK_SEGURIDAD_FACTOR
    df["punto_reorden"] = (df["demanda_diaria_avg"] * LEAD_TIME_DIAS) + stock_seguridad

    # --- NUEVOS CÁLCULOS SOLICITADOS ---

    # A. Inventario Proyectado (Stock actual - Demanda prevista)
    df["inventario_proyectado"] = df["stock_actual"] - df["demanda_predicha_mes"]

    # B. Probabilidad de Venta (Representado como Tasa de Absorción)
    # Cálculo: (Demanda / Stock Actual). Si demanda > Stock, es 100%.
    # Evitamos división por cero sumando un epsilon pequeño
    tasa_absorcion = df["demanda_predicha_mes"] / (df["stock_actual"] + 0.001)
    
    # Convertimos a porcentaje (0-100), limitamos a 100% máximo, y hacemos string "50%"
    df["probabilidad_venta_pct"] = (tasa_absorcion * 100).clip(upper=100).fillna(0).round(0).astype(int).astype(str) + "%"


    # 3. Lógica de Acción Sugerida (Actualizada con Riesgo de Quiebre)
    # Condiciones en orden de prioridad
    condiciones = [
        (df["inventario_proyectado"] < 0),                # Prioridad 1: Nos vamos a quedar sin stock
        (df["stock_actual"] <= df["punto_reorden"]),      # Prioridad 2: Llegamos al punto de reorden
        (df["stock_actual"] > df["demanda_predicha_mes"] * 3) # Prioridad 3: Tenemos demasiado
    ]
    elecciones = ["Riesgo de Quiebre", "REABASTECER URGENTE", "Exceso de Inventario"]
    
    df["accion_sugerida"] = np.select(condiciones, elecciones, default="Stock Saludable")

    # 4. Cantidad Económica de Pedido (EOQ)
    demanda_anual_estimada = df["demanda_predicha_mes"] * 12
    df["costo_holding_anual"] = df["costo_unitario"] * COSTO_ALMACENAMIENTO
    
    df["cantidad_a_comprar_eoq"] = np.sqrt(
        (2 * demanda_anual_estimada * COSTO_HACER_PEDIDO) / (df["costo_holding_anual"] + 0.0001)
    )
    df["cantidad_a_comprar_eoq"] = df["cantidad_a_comprar_eoq"].fillna(0).round(0).astype(int)

    # 5. Calcular Cantidad Final a Comprar
    # Si hay riesgo de quiebre, pedimos lo que falta + el EOQ
    # Si es reabastecer urgente, pedimos lo necesario para llegar al ROP o el EOQ (el mayor)
    
    df["falta_para_seguridad"] = df["punto_reorden"] - df["stock_actual"]
    
    # Lógica vectorizada para definir cantidad
    df["sugerencia_cantidad"] = np.where(
        (df["accion_sugerida"] == "Riesgo de Quiebre") | (df["accion_sugerida"] == "REABASTECER URGENTE"),
        np.maximum(df["cantidad_a_comprar_eoq"], df["falta_para_seguridad"]),
        0
    )
    
    # Limpieza final
    df["sugerencia_cantidad"] = np.clip(df["sugerencia_cantidad"], 0, None).round(0).astype(int)
    df["punto_reorden"] = df["punto_reorden"].round(0).astype(int)
    df["inventario_proyectado"] = df["inventario_proyectado"].round(0).astype(int)
    
    return df

def generar_dataset_reporte(categoria_filtro, simulated_date_str=None):
    """
    Función principal llamada por el UI.
    Devuelve un DF con las columnas RENOMBRADAS para el PDF.
    """
    # 1. Obtener datos
    df_raw = obtener_datos_combinados(simulated_date_str)
    if df_raw.empty:
        return pd.DataFrame()
    
    # 2. Filtrar
    if categoria_filtro != "Todas las Categorías":
        df_filtrado = df_raw[df_raw["categoria"] == categoria_filtro].copy()
    else:
        df_filtrado = df_raw.copy()

    # 3. Calcular métricas
    df_optin = calcular_recomendacion_compra(df_filtrado)
    
    # 4. Seleccionar y Renombrar columnas para el Reporte
    # Mapeo: Nombre interno -> Nombre que sale en el PDF/Excel
    columnas_finales = {
        "id_articulo": "ID",
        "descripcion": "Descripción",
        "categoria": "Categoría",
        "stock_actual": "Stock Actual",
        "probabilidad_venta_pct": "Prob. Venta (30d)", # La nueva columna de %
        "inventario_proyectado": "Inv. Proyectado",    # La nueva columna de proyección
        "punto_reorden": "Punto Reorden",
        "accion_sugerida": "Acción Sugerida",
        "sugerencia_cantidad": "Cant. a Comprar"
    }
    
    # Filtramos solo las columnas que calculamos y existen
    df_final = df_optin.rename(columns=columnas_finales)
    
    # Asegurar orden
    cols_orden = list(columnas_finales.values())
    df_final = df_final[cols_orden]
    
    return df_final.sort_values("Acción Sugerida")

# Prueba rápida
if __name__ == "__main__":
    df = generar_dataset_reporte("Todas las Categorías")
    print(df.head(10).to_string())