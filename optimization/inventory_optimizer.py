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
    tasa_absorcion = df["demanda_predicha_mes"] / (df["stock_actual"] + 0.001)
    
    # Convertimos a porcentaje string "50%"
    df["probabilidad_venta_pct"] = (tasa_absorcion * 100).clip(upper=100).fillna(0).round(0).astype(int).astype(str) + "%"

    # 3. Lógica de Acción Sugerida (Actualizada con Riesgo de Quiebre)
    condiciones = [
        (df["inventario_proyectado"] < 0),                # Prioridad 1: Quiebre
        (df["stock_actual"] <= df["punto_reorden"]),      # Prioridad 2: Reorden
        (df["stock_actual"] > df["demanda_predicha_mes"] * 3) # Prioridad 3: Exceso
    ]
    elecciones = ["RIESGO DE QUIEBRE", "REPONER STOCK", "EXCESO DE STOCK"]
    
    df["accion_sugerida"] = np.select(condiciones, elecciones, default="STOCK SALUDABLE")

    # 4. Cantidad Económica de Pedido (EOQ)
    demanda_anual_estimada = df["demanda_predicha_mes"] * 12
    df["costo_holding_anual"] = df["costo_unitario"] * COSTO_ALMACENAMIENTO
    
    df["cantidad_a_comprar_eoq"] = np.sqrt(
        (2 * demanda_anual_estimada * COSTO_HACER_PEDIDO) / (df["costo_holding_anual"] + 0.0001)
    )
    df["cantidad_a_comprar_eoq"] = df["cantidad_a_comprar_eoq"].fillna(0).round(0).astype(int)

    # 5. Calcular Cantidad Final a Comprar
    df["falta_para_seguridad"] = df["punto_reorden"] - df["stock_actual"]
    
    # Si hay riesgo o toca reponer, usamos el mayor entre EOQ y lo que falta
    df["sugerencia_cantidad"] = np.where(
        (df["accion_sugerida"] == "RIESGO DE QUIEBRE") | (df["accion_sugerida"] == "REPONER STOCK"),
        np.maximum(df["cantidad_a_comprar_eoq"], df["falta_para_seguridad"]),
        0
    )
    
    # Limpieza final de negativos y tipos
    df["sugerencia_cantidad"] = np.clip(df["sugerencia_cantidad"], 0, None).round(0).astype(int)
    df["punto_reorden"] = df["punto_reorden"].round(0).astype(int)
    df["inventario_proyectado"] = df["inventario_proyectado"].round(0).astype(int)
    
    return df

def generar_dataset_reporte(categoria_filtro, simulated_date_str=None):
    """
    Función principal llamada por el UI.
    CORRECCIÓN: Renombra columnas para coincidir con los encabezados del PDF.
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
    # ⚠️ CAMBIO CRÍTICO: Nombres cortos IDÉNTICOS a los del PDF
    columnas_finales = {
        "id_articulo": "ID",
        "descripcion": "Descripción",
        "categoria": "Categoría",
        "stock_actual": "Stock Actual",
        
        # --- CORRECCIÓN AQUÍ ---
        "probabilidad_venta_pct": "Prob. %",    # <--- AHORA SÍ COINCIDE
        "inventario_proyectado": "Proyección",  
        "punto_reorden": "Reorden",             
        "sugerencia_cantidad": "Comprar",       
        # -----------------------
        
        "accion_sugerida": "Acción Sugerida"
    }
    
    # Filtramos solo las columnas que calculamos y existen
    # (Usamos un rename seguro)
    df_final = df_optin.rename(columns=columnas_finales)
    
    # Aseguramos que solo pasamos las columnas que definimos arriba
    cols_orden = list(columnas_finales.values())
    
    # Verificar que existan, si no, rellenar con 0 para evitar error
    for col in cols_orden:
        if col not in df_final.columns:
            df_final[col] = 0
            
    df_final = df_final[cols_orden]
    
    return df_final.sort_values("Acción Sugerida")

# Prueba rápida
if __name__ == "__main__":
    df = generar_dataset_reporte("Todas las Categorías")
    if not df.empty:
        print(df.head(10).to_string())
    else:
        print("Dataset vacío")