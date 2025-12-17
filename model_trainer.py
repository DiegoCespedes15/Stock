import pandas as pd
import numpy as np
import xgboost as xgb
import os
import sys
from datetime import datetime, timedelta
import psycopg2.extras 
from sqlalchemy import text

# Ajuste de rutas
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
# 🔹 1. Cargar Datos
# ================================================
def cargar_dataset_temporal():
    engine = conectar_db()
    if engine is None:
        print("❌ ERROR: conexión fallida.")
        return None
    try:
        # Cargamos explícitamente el precio_promedio
        sql = f"SELECT * FROM {SCHEMA}.{TABLA_TEMPORAL} ORDER BY v_fecha"
        df = pd.read_sql(sql, engine)
        print(f"✅ Dataset cargado ({len(df)} registros)")
        
        # --- MAPEO CRÍTICO DE PRECIOS ---
        # El procesador guardó 'precio_promedio', pero el modelo usa 'v_precio' internamente
        if "precio_promedio" in df.columns:
            df.rename(columns={"precio_promedio": "v_precio"}, inplace=True)
            print("💰 Columna de precios detectada y mapeada correctamente.")
            
        return df
    except Exception as e:
        print(f"❌ Error al leer dataset: {e}")
        return None
    finally:
        try: engine.dispose()
        except: pass

# ================================================
# 🔹 2. Feature Engineering (Con Sensibilidad de Precio)
# ================================================
def crear_features_en_memoria(df):
    print("🔄 Generando features: ESTACIONALIDAD + TENDENCIA + PRECIOS...")
    df = df.copy()
    
    if not pd.api.types.is_datetime64_any_dtype(df["v_fecha"]):
         df["v_fecha"] = pd.to_datetime(df["v_fecha"])
    
    df = df.sort_values(["v_id_producto", "v_fecha"])

    # --- 1. Calendario básico ---
    df["anio"] = df["v_fecha"].dt.year
    df["mes"] = df["v_fecha"].dt.month
    df["dia_del_mes"] = df["v_fecha"].dt.day
    df["dia_de_la_semana"] = df["v_fecha"].dt.dayofweek
    df["semana_del_anio"] = df["v_fecha"].dt.isocalendar().week.astype(int)
    df["es_fin_de_semana"] = (df["dia_de_la_semana"] >= 5).astype(int)
    df["es_fin_mes"] = (df["dia_del_mes"] >= 25).astype(int)
    df["anio_mes"] = df["v_fecha"].dt.strftime("%Y%m").astype(int)
    
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)

    # --- 2. ANCLAS ESTÁTICAS ---
    df["promedio_total"] = df.groupby("v_id_producto")["cantidad_vendida"].transform("mean")
    df["promedio_mensual"] = df.groupby(["v_id_producto", "mes"])["cantidad_vendida"].transform("mean")

    # --- 3. POTENCIA DEL PRODUCTO ---
    df["venta_total_prod"] = df.groupby("v_id_producto")["cantidad_vendida"].transform("sum")
    df["venta_total_cat"] = df.groupby("categoria")["cantidad_vendida"].transform("sum")
    df["ratio_potencia_producto"] = df["venta_total_prod"] / (df["venta_total_cat"] + 1)

    # --- 4. INGENIERÍA DE PRECIOS ---
    if "v_precio" not in df.columns:
        df["v_precio"] = 1.0 # Fallback si no hay precios

    # Precio Base: ¿Cuánto cuesta normalmente este producto?
    df["precio_base"] = df.groupby("v_id_producto")["v_precio"].transform("mean")

    # Ratio Precio: ¿Está barato (<1) o caro (>1)?
    df["ratio_precio"] = df["v_precio"] / (df["precio_base"] + 0.01)

    # --- 5. LIMPIEZA ---
    cols_a_rellenar = [
        "promedio_total", "promedio_mensual", 
        "ratio_potencia_producto", "venta_total_prod", "venta_total_cat",
        "precio_base", "ratio_precio", "v_precio"
    ]
    
    for col in cols_a_rellenar:
        if col in df.columns:
            val = 1.0 if col in ["ratio_precio", "v_precio", "precio_base"] else 0
            df[col] = df[col].fillna(val)

    print("✅ Features generadas.")
    return df

# ================================================
# 🔹 3. Entrenar Modelo Global
# ================================================
def entrenar_modelo_global(df_hist):
    print(f"🚀 Entrenando modelo GLOBAL con {len(df_hist)} registros...")
    
    for col in ["v_id_producto", "categoria"]:
        df_hist[col] = df_hist[col].astype("category")

    features = [c for c in df_hist.columns if c not in ["cantidad_vendida", "v_fecha"]]
    X_train = df_hist[features]
    y_train = df_hist["cantidad_vendida"]

    # Hiperparámetros optimizados
    modelo = xgb.XGBRegressor(
        objective="reg:squarederror", 
        n_estimators=300,
        learning_rate=0.03,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        enable_categorical=True,
        n_jobs=-1,
        random_state=42
    )

    modelo.fit(X_train, y_train)
    print("✅ Modelo entrenado y listo.")
    modelo.save_model(RUTA_MODELO)
    return modelo

# ================================================
# 🔹 4. Predicción Directa (Futuro)
# ================================================
def predecir_futuro_directo(modelo, df_hist, dias_a_predecir=365):
    print(f"🔮 Iniciando predicción DIRECTA CON PRECIOS para {dias_a_predecir} días...")

    # 1. Anclas Estáticas
    cols_estaticas = [
        "v_id_producto", "categoria", 
        "promedio_total", "ratio_potencia_producto", 
        "venta_total_prod", "venta_total_cat", "precio_base"
    ]
    cols_existentes = [c for c in cols_estaticas if c in df_hist.columns]
    anclas_total = df_hist[cols_existentes].drop_duplicates()

    # 2. Último Precio Conocido (Asumimos que se mantiene)
    df_precios_actuales = df_hist.sort_values("v_fecha").groupby("v_id_producto").tail(1)[["v_id_producto", "v_precio"]]
    df_precios_actuales.rename(columns={"v_precio": "precio_futuro_estimado"}, inplace=True)

    # 3. Anclas Mensuales
    anclas_mensual = df_hist[["v_id_producto", "mes", "promedio_mensual"]].groupby(["v_id_producto", "mes"]).mean().reset_index()

    # 4. Fechas Futuras
    ultima_fecha = df_hist["v_fecha"].max()
    fechas_futuras = pd.date_range(start=ultima_fecha + timedelta(days=1), periods=dias_a_predecir, freq="D")
    df_futuro = pd.DataFrame({"v_fecha": fechas_futuras})
    df_futuro["mes"] = df_futuro["v_fecha"].dt.month

    # 5. Cruzar Datos
    df_futuro = anclas_total.merge(df_futuro, how="cross")
    df_futuro = pd.merge(df_futuro, anclas_mensual, on=["v_id_producto", "mes"], how="left")
    
    if "promedio_total" in df_futuro.columns:
        df_futuro["promedio_mensual"] = df_futuro["promedio_mensual"].fillna(df_futuro["promedio_total"])
    else:
        df_futuro["promedio_mensual"] = df_futuro["promedio_mensual"].fillna(0)

    # 6. Pegar Precios
    df_futuro = pd.merge(df_futuro, df_precios_actuales, on="v_id_producto", how="left")
    df_futuro["precio_futuro_estimado"] = df_futuro["precio_futuro_estimado"].fillna(df_futuro["precio_base"])
    
    # Calcular Ratio Futuro
    df_futuro["v_precio"] = df_futuro["precio_futuro_estimado"]
    df_futuro["ratio_precio"] = df_futuro["v_precio"] / (df_futuro["precio_base"] + 0.01)
    df_futuro["ratio_precio"] = df_futuro["ratio_precio"].fillna(1.0)

    # 7. Calendario
    df_futuro["anio"] = df_futuro["v_fecha"].dt.year
    df_futuro["dia_del_mes"] = df_futuro["v_fecha"].dt.day
    df_futuro["dia_de_la_semana"] = df_futuro["v_fecha"].dt.dayofweek
    df_futuro["semana_del_anio"] = df_futuro["v_fecha"].dt.isocalendar().week.astype(int)
    df_futuro["es_fin_de_semana"] = (df_futuro["dia_de_la_semana"] >= 5).astype(int)
    df_futuro["es_fin_mes"] = (df_futuro["dia_del_mes"] >= 25).astype(int)
    df_futuro["anio_mes"] = df_futuro["v_fecha"].dt.strftime("%Y%m").astype(int)
    df_futuro["mes_sin"] = np.sin(2 * np.pi * df_futuro["mes"] / 12)
    df_futuro["mes_cos"] = np.cos(2 * np.pi * df_futuro["mes"] / 12)
    
    # 8. Predecir
    cols_modelo = modelo.get_booster().feature_names
    for col in cols_modelo:
        if col not in df_futuro.columns:
            df_futuro[col] = 0

    X_futuro = df_futuro[cols_modelo].copy()
    for col in ["v_id_producto", "categoria"]:
        if col in X_futuro.columns:
            X_futuro[col] = X_futuro[col].astype("category")

    print(f"⚡ Generando predicciones ({len(X_futuro)} registros)...")
    predicciones = modelo.predict(X_futuro)
    df_futuro["cantidad_predicha"] = np.clip(predicciones, 0, None)

    return df_futuro

# ================================================
# 🔹 5. Guardar en Base de Datos
# ================================================
def guardar_predicciones_db(df_preds):
    if df_preds is None or df_preds.empty:
        print("⚠️ No hay predicciones para guardar.")
        return

    print(f"💾 Guardando {len(df_preds)} registros en BD...")

    df_final = df_preds.copy()
    if "v_fecha" not in df_final.columns:
        df_final["v_fecha"] = pd.to_datetime(df_final[["anio", "mes", "dia_del_mes"]].rename(columns={"anio": "year", "mes": "month", "dia_del_mes": "day"}))
    
    df_final["cantidad_vendida_real"] = 0
    df_final["fecha_entrenamiento"] = datetime.now()
    
    if "cantidad_vendida" in df_final.columns and "cantidad_predicha" not in df_final.columns:
         df_final.rename(columns={"cantidad_vendida": "cantidad_predicha"}, inplace=True)

    cols_db = ["v_id_producto", "v_fecha", "anio", "mes", "dia_del_mes", "dia_de_la_semana", "categoria", "cantidad_predicha", "cantidad_vendida_real", "fecha_entrenamiento"]
    
    # Asegurar que todas las columnas existen
    for col in cols_db:
        if col not in df_final.columns: df_final[col] = None

    df_final_db = df_final[cols_db]
    lista_valores = [tuple(x) for x in df_final_db.to_numpy()]

    conn = conectar_db()
    if conn is None: return

    try:
        with conn.cursor() as cur:
            print(f"🧹 Truncando tabla {SCHEMA}.{TABLA_PREDICCION}...")
            cur.execute(f"TRUNCATE TABLE {SCHEMA}.{TABLA_PREDICCION} RESTART IDENTITY;")
            
            print("📥 Insertando datos...")
            query_insert = f"INSERT INTO {SCHEMA}.{TABLA_PREDICCION} ({', '.join(cols_db)}) VALUES %s"
            psycopg2.extras.execute_values(cur, query_insert, lista_valores, page_size=10000)
            
        conn.commit()
        print("✅ Predicciones guardadas exitosamente.")

    except Exception as e:
        print(f"❌ Error guardando en BD: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

# ================================================
# 🔹 CONFIGURACIÓN DE EJECUCIÓN
# ================================================

# True = Entrena con 2023, Predice 2024 (Para Demo/Backtesting)
# False = Entrena con TODO, Predice 2025+ (Para Uso Real)
MODO_DEMO = True

if __name__ == "__main__":
    print(f"🏁 INICIANDO MODEL TRAINER (Modo Demo: {MODO_DEMO})")
    
    try:
        df_completo = cargar_dataset_temporal()
        if df_completo is None: raise Exception("Error de carga")

        df_features = crear_features_en_memoria(df_completo)

        if MODO_DEMO:
            print("🧪 MODO DEMO: Entrenando hasta 2023, prediciendo 2024...")
            fecha_corte = pd.Timestamp("2024-01-01")
            df_train = df_features[df_features["v_fecha"] < fecha_corte].copy()
            # Guardamos los datos reales para validar después
            df_test_real = df_features[df_features["v_fecha"] >= fecha_corte].copy()
            dias_pred = 366 # 2024 bisiesto
        else:
            print("🏭 MODO PRODUCCIÓN: Entrenando con todo el historial...")
            df_train = df_features
            df_test_real = None
            dias_pred = 365

        # Entrenar
        modelo = entrenar_modelo_global(df_train)

        # Predecir
        df_futuro = predecir_futuro_directo(modelo, df_train, dias_a_predecir=dias_pred)

        # Guardar
        guardar_predicciones_db(df_futuro)
        
        # --- VALIDACIÓN WMAPE (Solo en MODO DEMO) ---
        if MODO_DEMO and df_test_real is not None and not df_test_real.empty:
            print("\n--- 📉 RESULTADOS DE VALIDACIÓN (WMAPE) ---")
            
            df_comparativa = pd.merge(
                df_test_real[["v_fecha", "v_id_producto", "cantidad_vendida"]],
                df_futuro[["v_fecha", "v_id_producto", "cantidad_predicha"]],
                on=["v_fecha", "v_id_producto"],
                how="inner"
            )
            
            df_comparativa.rename(columns={
                "cantidad_vendida": "cantidad_vendida_real",
                "cantidad_predicha": "cantidad_vendida_pred"
            }, inplace=True)
            
            mae = (df_comparativa["cantidad_vendida_real"] - df_comparativa["cantidad_vendida_pred"]).abs().mean()
            print(f"📉 MAE Diario: {mae:.2f}")

            # WMAPE Mensual
            df_comparativa["mes"] = df_comparativa["v_fecha"].dt.month
            df_mensual = df_comparativa.groupby(["mes", "v_id_producto"])[["cantidad_vendida_real", "cantidad_vendida_pred"]].sum()
            
            total_ventas_reales = df_mensual["cantidad_vendida_real"].sum()
            if total_ventas_reales > 0:
                error_total = (df_mensual["cantidad_vendida_real"] - df_mensual["cantidad_vendida_pred"]).abs().sum()
                wmape = (error_total / total_ventas_reales) * 100
                print(f"📊 WMAPE Mensual Global: {wmape:.2f}%")
            else:
                print("⚠️ No hay ventas reales para calcular WMAPE.")
                
        print("\n🏆 EJECUCIÓN EXITOSA.")

    except Exception as e:
        print(f"💥 Error Fatal: {e}")
        import traceback
        traceback.print_exc()