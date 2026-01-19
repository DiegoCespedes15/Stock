import pandas as pd
import numpy as np
import sys
import os

# Ajuste de path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path: sys.path.append(parent_dir)

from bd import conectar_db

def analizar_errores():
    print("🔍 INICIANDO DIAGNÓSTICO PROFUNDO DE ERRORES...")
    conn = conectar_db()
    if not conn: return

    # 1. Traer Realidad (2024) vs Predicción (Tabla guardada)
    # Asumimos que la tabla prediccion_mensual ya tiene los datos del último run
    sql = """
        SELECT 
            p.v_id_producto,
            p.categoria,
            SUM(p.cantidad_predicha) as total_predicho,
            SUM(p.cantidad_vendida_real) as total_real
        FROM desarrollo.prediccion_mensual p
        GROUP BY p.v_id_producto, p.categoria
    """
    df = pd.read_sql(sql, conn)
    conn.close()

    if df.empty:
        print("❌ No hay datos en prediccion_mensual. Ejecuta model_trainer primero.")
        return

    # 2. Calcular Errores
    df["error_abs"] = (df["total_real"] - df["total_predicho"]).abs()
    df["wmape_prod"] = np.where(df["total_real"] > 0, (df["error_abs"] / df["total_real"]), 0)

    # 3. SEGMENTACIÓN POR VOLUMEN DE VENTA (Clave del diagnóstico)
    # Clasificamos los productos según cuánto vendieron realmente
    conditions = [
        (df["total_real"] == 0),
        (df["total_real"] <= 12),  # Vende 1 o menos al mes (Baja Rotación)
        (df["total_real"] > 12)    # Vende > 1 al mes (Alta Rotación)
    ]
    choices = ["Sin Ventas (0)", "Baja Rotación (1-12)", "Alta Rotación (>12)"]
    df["segmento"] = np.select(conditions, choices, default="Otro")

    # 4. Resultados por Segmento
    print("\n📊 --- RESULTADOS POR TIPO DE PRODUCTO ---")
    resumen = df.groupby("segmento").agg(
        productos=('v_id_producto', 'count'),
        venta_real_total=('total_real', 'sum'),
        venta_pred_total=('total_predicho', 'sum'),
        error_total=('error_abs', 'sum')
    ).reset_index()

    # Calcular WMAPE del grupo
    resumen["WMAPE_Grupo"] = (resumen["error_total"] / resumen["venta_real_total"] * 100).round(1)
    resumen["Precision_Grupo"] = (100 - resumen["WMAPE_Grupo"]).clip(0, 100)

    print(resumen.to_string())

    # 5. Top 5 Peores Productos (Alta Rotación)
    print("\n💀 --- TOP 5 PEORES ERRORES (Productos que SÍ venden) ---")
    top_err = df[df["segmento"] == "Alta Rotación (>12)"].sort_values("error_abs", ascending=False).head(5)
    print(top_err[["v_id_producto", "categoria", "total_real", "total_predicho", "error_abs"]].to_string(index=False))

    # 6. Sesgo Global
    total_real = df["total_real"].sum()
    total_pred = df["total_predicho"].sum()
    sesgo = total_pred - total_real
    tipo_sesgo = "SOBRE-PREDICCIÓN (Predices de más)" if sesgo > 0 else "SUB-PREDICCIÓN (Predices de menos)"
    
    print(f"\n⚖️ SESGO GLOBAL: {tipo_sesgo}")
    print(f"   Real Total: {total_real:,.0f}")
    print(f"   Pred Total: {total_pred:,.0f}")
    print(f"   Diferencia: {sesgo:,.0f}")

if __name__ == "__main__":
    analizar_errores()