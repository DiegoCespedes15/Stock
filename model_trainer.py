import pandas as pd
import numpy as np
import xgboost as xgb
import os
import sys
from datetime import datetime, timedelta
import psycopg2.extras 
import warnings
import argparse

# --- FIX DE CODIFICACIÓN ---
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
if sys.stderr.encoding != 'utf-8':
    try: sys.stderr.reconfigure(encoding='utf-8')
    except: pass

warnings.filterwarnings('ignore')

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from bd import conectar_db

# --- CONSTANTES ---
RUTA_MODELO = os.path.join(current_dir, "modelo_xgboost.json")
TABLA_TEMPORAL = "prediccion_dataset"
TABLA_PREDICCION = "prediccion_mensual"
SCHEMA = "desarrollo"

# ================================================
# 🔹 1. Cargar y Transformar
# ================================================
def cargar_y_agrupar_mensual():
    engine = conectar_db()
    if engine is None: return None
    try:
        print("📥 Cargando datos diarios...", flush=True)
        sql = f"SELECT * FROM {SCHEMA}.{TABLA_TEMPORAL} ORDER BY v_fecha"
        df = pd.read_sql(sql, engine)
        
        if df.empty: return None

        df["v_fecha"] = pd.to_datetime(df["v_fecha"])
        
        print("📅 Agrupando datos por MES...", flush=True)
        df["fecha_mes"] = df["v_fecha"].dt.to_period("M").dt.to_timestamp()
        
        df_mensual = df.groupby(["fecha_mes", "v_id_producto", "categoria"]).agg({
            "cantidad_vendida": "sum",
            "precio_promedio": "mean" 
        }).reset_index()
        
        df_mensual.rename(columns={"precio_promedio": "v_precio"}, inplace=True)
        if "v_precio" not in df_mensual.columns: df_mensual["v_precio"] = 1.0
        
        # --- CORRECCIÓN CRÍTICA: GARANTIZAR CONTINUIDAD TEMPORAL ---
        # Esto rellena los huecos de meses sin venta con 0 para que los LAGS funcionen.
        df_continuo = garantizar_continuidad_mensual(df_mensual)
        
        return df_continuo
        
    except Exception as e:
        print(f"❌ Error carga: {e}", flush=True)
        return None
    finally:
        try: engine.dispose() 
        except: pass

def garantizar_continuidad_mensual(df):
    """
    Crea filas para los meses faltantes con venta 0.
    Vital para que shift(1) sea realmente el mes anterior.
    """
    print("⏳ Rellenando huecos temporales (Meses sin venta)...", flush=True)
    
    # 1. Rango completo de fechas
    min_date = df["fecha_mes"].min()
    max_date = df["fecha_mes"].max()
    all_dates = pd.date_range(start=min_date, end=max_date, freq='MS')
    
    # 2. Obtener info estática de productos (Categoría, Precio último conocido)
    df_sorted = df.sort_values("fecha_mes")
    static_info = df_sorted.groupby("v_id_producto").agg({
        "categoria": "last",
        "v_precio": "last"
    }).reset_index()
    
    unique_products = static_info["v_id_producto"].unique()
    
    # 3. Crear Grid Cartesiano (Todos los productos x Todas las fechas)
    index_completo = pd.MultiIndex.from_product(
        [unique_products, all_dates], 
        names=["v_id_producto", "fecha_mes"]
    )
    
    # 4. Reindexar
    df_indexed = df.set_index(["v_id_producto", "fecha_mes"])
    df_full = df_indexed.reindex(index_completo).reset_index()
    
    # 5. Rellenar 0s y restaurar columnas
    df_full["cantidad_vendida"] = df_full["cantidad_vendida"].fillna(0)
    
    # Restaurar Categoria y Precio (que se pierden al reindexar)
    df_full = df_full.drop(columns=["categoria", "v_precio"], errors="ignore")
    df_full = df_full.merge(static_info, on="v_id_producto", how="left")
    
    # Rellenar precios nulos (si un producto es nuevo en el reindex) con algo razonable
    df_full["v_precio"] = df_full["v_precio"].fillna(0)
    
    print(f"✅ Dataset continuo: {len(df)} -> {len(df_full)} registros.", flush=True)
    return df_full

# ================================================
# 🔹 2. Feature Engineering
# ================================================
def generar_features_mensuales(df):
    df = df.copy()
    df = df.sort_values(["v_id_producto", "fecha_mes"])
    
    # Calendario
    df["mes"] = df["fecha_mes"].dt.month
    df["anio"] = df["fecha_mes"].dt.year
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)
    
    # Historia
    grouped = df.groupby("v_id_producto")["cantidad_vendida"]
    
    # AHORA SÍ: shift(1) es el mes anterior real, porque no hay huecos.
    df["lag_12"] = grouped.shift(12)
    df["lag_1"] = grouped.shift(1)
    df["lag_2"] = grouped.shift(2)
    df["lag_3"] = grouped.shift(3)
    
    # Tendencias
    df["rm_3"] = grouped.transform(lambda x: x.shift(1).rolling(window=3).mean())
    df["rm_6"] = grouped.transform(lambda x: x.shift(1).rolling(window=6).mean())
    df["rm_12"] = grouped.transform(lambda x: x.shift(1).rolling(window=12).mean())
    
    df["delta_precio"] = df.groupby("v_id_producto")["v_precio"].pct_change().fillna(0)
    
    cols_fillna = ["lag_12", "lag_1", "lag_2", "lag_3", "rm_3", "rm_6", "rm_12"]
    df[cols_fillna] = df[cols_fillna].fillna(0)
    
    df["promedio_historico"] = grouped.transform("mean")
    
    for col in ["v_id_producto", "categoria"]:
        df[col] = df[col].astype("category")
        
    return df

# ================================================
# 🔹 3. Entrenamiento
# ================================================
def entrenar_modelo(df_train):
    print(f"🚀 Entrenando modelo con {len(df_train)} registros...", flush=True)
    
    features = [
        "mes", "anio", "mes_sin", "mes_cos", 
        "v_precio", "delta_precio",
        "lag_12", "lag_1", "lag_2", "lag_3",
        "rm_3", "rm_6", "rm_12", "promedio_historico"
    ]
    
    features = [f for f in features if f in df_train.columns]
    X = df_train[features]
    y = np.log1p(df_train["cantidad_vendida"])
    
    modelo = xgb.XGBRegressor(
        objective="reg:squarederror",    
        n_estimators=500,           
        learning_rate=0.02,         
        max_depth=6,
        min_child_weight=1,
        subsample=0.8,
        colsample_bytree=0.8,
        enable_categorical=True,
        n_jobs=1,
        random_state=42
    )
    
    modelo.fit(X, y)
    print("✅ Modelo entrenado.", flush=True)
    return modelo, features

# ================================================
# 🔹 4. Predicción (HÍBRIDO ROBUSTO)
# ================================================
def predecir_futuro_recursivo(modelo, df_historia_con_features, features_cols, meses_a_predecir=12):
    print(f"🔮 Predicción sobre dataset continuo ({meses_a_predecir} meses)...", flush=True)
    
    df_actual = df_historia_con_features.copy()
    ultima_fecha = df_actual["fecha_mes"].max()
    predicciones_futuras = []
    
    cols_prod = ["v_id_producto", "categoria", "v_precio"]
    if "promedio_historico" in df_actual.columns: cols_prod.append("promedio_historico")
    
    # Tomamos la info del último mes conocido para cada producto
    productos = df_actual.sort_values("fecha_mes").groupby("v_id_producto").tail(1)[cols_prod]
    
    for i in range(1, meses_a_predecir + 1):
        siguiente_mes = ultima_fecha + pd.DateOffset(months=i)
        
        df_mes_futuro = productos.copy()
        df_mes_futuro["fecha_mes"] = siguiente_mes
        df_mes_futuro["cantidad_vendida"] = 0 
        
        # Concatenar
        df_temp = pd.concat([df_actual, df_mes_futuro], ignore_index=True)
        df_temp = df_temp.sort_values(["v_id_producto", "fecha_mes"])
        
        # Recalcular features (Ahora los lags son perfectos porque no hay huecos)
        df_temp = generar_features_mensuales(df_temp)
        
        df_target = df_temp[df_temp["fecha_mes"] == siguiente_mes].copy()
        X_target = df_target[features_cols]
        
        # A. IA
        preds_log = modelo.predict(X_target)
        preds_xgb = np.expm1(preds_log)
        
        # B. Red de Seguridad (Ahora rm_6 y lag_12 son datos reales, no basura)
        trend_recente = df_target["rm_6"].fillna(0).values
        seasonal_history = df_target["lag_12"].fillna(0).values
        
        # Base Sólida
        base_solida = (trend_recente * 0.7) + (seasonal_history * 0.3)
        
        # Ensamble
        preds_finales = np.maximum(preds_xgb, base_solida)
        preds_finales = np.round(preds_finales)
        preds_finales = np.clip(preds_finales, 0, None)
        
        df_target["cantidad_predicha"] = preds_finales
        df_target["cantidad_vendida"] = preds_finales
        
        predicciones_futuras.append(df_target)
        
        # Actualizar historia
        # Solo guardamos lo necesario para no explotar memoria, pero mantenemos continuidad
        cols_clave = ["fecha_mes", "v_id_producto", "categoria", "v_precio", "cantidad_vendida"]
        df_actual = pd.concat([df_actual, df_target[cols_clave]], ignore_index=True)
    
    return pd.concat(predicciones_futuras, ignore_index=True)

# ================================================
# 🔹 5. Guardar
# ================================================
def expandir_y_guardar(df_mensual_pred):
    print("⚡ Distribuyendo a diario...", flush=True)
    filas_diarias = []
    
    for _, row in df_mensual_pred.iterrows():
        total_mes = row["cantidad_predicha"]
        if total_mes < 1: continue 
        
        mes = row["fecha_mes"]
        dias_en_mes = pd.Period(mes, freq='M').days_in_month
        cantidad_diaria = total_mes / dias_en_mes
        
        for d in range(1, dias_en_mes + 1):
            fecha_dia = datetime(mes.year, mes.month, d)
            filas_diarias.append({
                "v_id_producto": row["v_id_producto"],
                "v_fecha": fecha_dia,
                "anio": mes.year,
                "mes": mes.month,
                "dia_del_mes": d,
                "dia_de_la_semana": fecha_dia.weekday(),
                "categoria": row["categoria"],
                "cantidad_predicha": cantidad_diaria,
                "cantidad_vendida_real": 0,
                "fecha_entrenamiento": datetime.now()
            })
            
    if not filas_diarias: return

    df_save = pd.DataFrame(filas_diarias)
    print(f"💾 Guardando {len(df_save)} registros...", flush=True)

    cols_db = ["v_id_producto", "v_fecha", "anio", "mes", "dia_del_mes", "dia_de_la_semana", 
               "categoria", "cantidad_predicha", "cantidad_vendida_real", "fecha_entrenamiento"]
    
    lista_valores = [tuple(x) for x in df_save[cols_db].to_numpy()]
    
    conn = conectar_db()
    if conn is None: return

    try:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {SCHEMA}.{TABLA_PREDICCION};") 
            query = f"INSERT INTO {SCHEMA}.{TABLA_PREDICCION} ({', '.join(cols_db)}) VALUES %s"
            psycopg2.extras.execute_values(cur, query, lista_valores, page_size=10000)
        conn.commit()
        print("✅ Guardado exitoso.", flush=True)
    except Exception as e:
        print(f"❌ Error DB: {e}", flush=True)
    finally:
        if conn: conn.close()

# ================================================
# 🔹 MAIN (REPORTE CATEGORÍA)
# ================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--horizonte', type=int, default=12)
    parser.add_argument('--modo', type=str, default='demo')
    args = parser.parse_args()
    
    meses_pred = args.horizonte
    es_modo_demo = (args.modo == 'demo')
    
    print(f"🏁 INICIANDO (H={meses_pred}m | M={args.modo})", flush=True)

    try:
        df_mensual_hist = cargar_y_agrupar_mensual()
        if df_mensual_hist is None: return
        
        df_full_features = generar_features_mensuales(df_mensual_hist)
        
        if es_modo_demo:
            print("🧪 MODO DEMO: Entrenando < 2024", flush=True)
            fecha_corte = pd.Timestamp("2024-01-01")
            
            df_train = df_full_features[df_full_features["fecha_mes"] < fecha_corte].copy()
            # Filtramos el primer año de historia de lags
            min_date = df_train["fecha_mes"].min() + pd.DateOffset(months=12)
            df_train = df_train[df_train["fecha_mes"] >= min_date]
            
            df_real_2024 = df_full_features[df_full_features["fecha_mes"] >= fecha_corte].copy()
            
            modelo, features_col = entrenar_modelo(df_train)
            
            df_base_prediccion = df_full_features[df_full_features["fecha_mes"] < fecha_corte].copy()
            df_futuro = predecir_futuro_recursivo(modelo, df_base_prediccion, features_col, meses_a_predecir=meses_pred)
            
        else:
            print("🏭 MODO PRODUCCIÓN", flush=True)
            df_train = df_full_features[df_full_features["fecha_mes"] >= df_full_features["fecha_mes"].min() + pd.DateOffset(months=12)]
            modelo, features_col = entrenar_modelo(df_train)
            df_futuro = predecir_futuro_recursivo(modelo, df_full_features, features_col, meses_a_predecir=meses_pred)
            df_real_2024 = None

        expandir_y_guardar(df_futuro)
        
        # VALIDACIÓN POR CATEGORÍA
        if es_modo_demo and df_real_2024 is not None:
            print("\n📊  REPORTE DE PRECISIÓN POR CATEGORÍA...", flush=True)
            merged = pd.merge(df_real_2024, df_futuro, on=["fecha_mes", "v_id_producto", "categoria"], how="outer", suffixes=('_real', '_pred'))
            
            col_real = "cantidad_vendida_real"
            col_pred = "cantidad_predicha"
            merged[col_real] = merged[col_real].fillna(0)
            merged[col_pred] = merged[col_pred].fillna(0)
            
            if not merged.empty:
                reporte = merged.groupby("categoria").agg(
                    Total_Real=(col_real, 'sum'),
                    Total_Pred=(col_pred, 'sum'),
                    Error_Abs_Total=(col_real, lambda x: (x - merged.loc[x.index, col_pred]).abs().sum())
                ).reset_index()
                
                reporte["WMAPE"] = (reporte["Error_Abs_Total"] / reporte["Total_Real"] * 100).fillna(0)
                reporte["Precision"] = (100 - reporte["WMAPE"]).clip(0, 100)
                
                reporte = reporte[reporte["Total_Real"] > 100].sort_values("Precision", ascending=False)
                
                print("-" * 80, flush=True)
                print(f"{'CATEGORÍA':<25} | {'REAL':<10} | {'PRED':<10} | {'PRECISIÓN':<10}", flush=True)
                print("-" * 80, flush=True)
                for _, row in reporte.iterrows():
                    print(f"{str(row['categoria'])[:25]:<25} | {int(row['Total_Real']):<10} | {int(row['Total_Pred']):<10} | {row['Precision']:.1f}%", flush=True)
                print("-" * 80, flush=True)
                
                # TOTAL GLOBAL
                print(f"📦 Total Real Global: {merged[col_real].sum():,.0f}")
                print(f"📦 Total Pred Global: {merged[col_pred].sum():,.0f} (¡Esto debe subir!)")

            else:
                print("⚠️ Sin datos.", flush=True)

        print("🏆 PROCESO TERMINADO.", flush=True)

    except Exception as e:
        print(f"💥 Error Fatal: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()