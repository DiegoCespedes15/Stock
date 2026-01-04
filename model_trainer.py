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
        
        # Agrupamos sumando cantidades y promediando precios
        df_mensual = df.groupby(["fecha_mes", "v_id_producto", "categoria"]).agg({
            "cantidad_vendida": "sum",
            "precio_promedio": "mean" 
        }).reset_index()
        
        df_mensual.rename(columns={"precio_promedio": "v_precio"}, inplace=True)
        if "v_precio" not in df_mensual.columns: df_mensual["v_precio"] = 1.0
        
        print(f"✅ Datos reducidos a {len(df_mensual)} registros mensuales.", flush=True)
        return df_mensual
        
    except Exception as e:
        print(f"❌ Error carga: {e}", flush=True)
        return None
    finally:
        try: engine.dispose() 
        except: pass

# ================================================
# 🔹 2. Feature Engineering (NIVEL EXPERTO)
# ================================================
def generar_features_mensuales(df):
    """
    Genera features avanzadas de Momentum, Precio y Volatilidad.
    """
    print("🔄 Generando features avanzadas...", flush=True)
    df = df.copy()
    df = df.sort_values(["v_id_producto", "fecha_mes"])
    
    # --- A. Calendario ---
    df["mes"] = df["fecha_mes"].dt.month
    df["anio"] = df["fecha_mes"].dt.year
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12) # Ciclo anual suave
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)
    
    # --- B. Lags y Medias Móviles (Historia) ---
    grouped = df.groupby("v_id_producto")["cantidad_vendida"]
    
    # Lag 12 (Año pasado mismo mes) - Muy importante para estacionalidad
    df["lag_12"] = grouped.shift(12)
    # Lag 1 (Mes pasado) - Base de la tendencia
    df["lag_1"] = grouped.shift(1)
    
    # Medias móviles (Tendencias)
    df["rm_3"] = grouped.transform(lambda x: x.shift(1).rolling(window=3).mean())
    df["rm_6"] = grouped.transform(lambda x: x.shift(1).rolling(window=6).mean())
    df["rm_12"] = grouped.transform(lambda x: x.shift(1).rolling(window=12).mean()) # Tendencia anual
    
    # --- C. MOMENTUM (NUEVO 🔥) ---
    # ¿El producto vende más ahora (3 meses) que en el último año?
    # Si rm_3 > rm_12 -> Momentum > 1 (Crecimiento)
    # Agregamos 0.1 para evitar división por cero
    df["momentum"] = (df["rm_3"] + 0.1) / (df["rm_12"] + 0.1)
    
    # --- D. VOLATILIDAD (NUEVO 🔥) ---
    # Desviación estándar de los últimos 6 meses.
    # Si es alta, el producto es inestable, el modelo debe ser conservador.
    df["volatilidad"] = grouped.transform(lambda x: x.shift(1).rolling(window=6).std())
    
    # --- E. DINÁMICA DE PRECIOS (NUEVO 🔥) ---
    # Cambio porcentual del precio respecto al mes anterior.
    # Si bajó de precio (-0.1), esperamos más ventas.
    df["delta_precio"] = df.groupby("v_id_producto")["v_precio"].pct_change().fillna(0)
    
    # --- F. Limpieza ---
    # Rellenar nulos generados por lags (los primeros meses de cada producto)
    cols_fillna = ["lag_12", "lag_1", "rm_3", "rm_6", "rm_12", "momentum", "volatilidad"]
    df[cols_fillna] = df[cols_fillna].fillna(0)
    
    # "Promedio Histórico" estático (Respaldo final)
    df["promedio_historico"] = grouped.transform("mean")
    
    for col in ["v_id_producto", "categoria"]:
        df[col] = df[col].astype("category")
        
    return df

# ================================================
# 🔹 3. Entrenamiento (Tweedie Optimizado)
# ================================================
def entrenar_modelo(df_train):
    print(f"🚀 Entrenando modelo con {len(df_train)} registros...", flush=True)
    
    features = [
        "mes", "anio", "mes_sin", "mes_cos", 
        "v_precio", "delta_precio",             # Economía
        "lag_12", "lag_1",                      # Historia Pura
        "rm_3", "rm_6", "momentum",             # Tendencia
        "volatilidad", "promedio_historico"     # Estabilidad
    ]
    
    # Verificar existencia
    features = [f for f in features if f in df_train.columns]

    X = df_train[features]
    y = df_train["cantidad_vendida"]
    
    # CONFIGURACIÓN XGBOOST
    modelo = xgb.XGBRegressor(
        objective="reg:tweedie",    
        tweedie_variance_power=1.3, # 1.3 es más cercano a Poisson (conteos puros) que 1.5
        n_estimators=600,           
        learning_rate=0.015,         # Un poco más rápido que 0.01
        max_depth=5,                # Profundidad media para capturar relaciones complejas (Precio vs Venta)
        min_child_weight=3,         # Evita aprender de productos con 1 sola venta aislada
        subsample=0.7,
        colsample_bytree=0.7,
        enable_categorical=True,
        n_jobs=1,
        random_state=42
    )
    
    modelo.fit(X, y)
    print("✅ Modelo entrenado.", flush=True)
    
    # Mostrar importancia de variables (Debug en consola)
    try:
        importances = modelo.feature_importances_
        feature_imp = pd.DataFrame({'Feature': features, 'Importance': importances})
        print("🔍 Top Features:", flush=True)
        print(feature_imp.sort_values("Importance", ascending=False).head(5).to_string(index=False), flush=True)
    except: pass
    
    modelo.save_model(RUTA_MODELO)
    return modelo, features

# ================================================
# 🔹 4. Predicción Recursiva
# ================================================
def predecir_futuro_recursivo(modelo, df_historia_con_features, features_cols, meses_a_predecir=12):
    print(f"🔮 Predicción recursiva ({meses_a_predecir} meses)...", flush=True)
    
    df_actual = df_historia_con_features.copy()
    ultima_fecha = df_actual["fecha_mes"].max()
    predicciones_futuras = []
    
    # Productos activos (último estado conocido)
    cols_prod = ["v_id_producto", "categoria", "v_precio"]
    if "promedio_historico" in df_actual.columns: cols_prod.append("promedio_historico")
    
    productos = df_actual[cols_prod].drop_duplicates("v_id_producto", keep="last")
    
    for i in range(1, meses_a_predecir + 1):
        siguiente_mes = ultima_fecha + pd.DateOffset(months=i)
        
        # Esqueleto
        df_mes_futuro = productos.copy()
        df_mes_futuro["fecha_mes"] = siguiente_mes
        df_mes_futuro["cantidad_vendida"] = 0 
        
        # Unir y recalcular features
        df_temp = pd.concat([df_actual, df_mes_futuro], ignore_index=True)
        df_temp = df_temp.sort_values(["v_id_producto", "fecha_mes"])
        
        df_temp = generar_features_mensuales(df_temp)
        
        # Predecir target
        df_target = df_temp[df_temp["fecha_mes"] == siguiente_mes].copy()
        X_target = df_target[features_cols]
        
        preds = modelo.predict(X_target)
        preds = np.clip(preds, 0, None) 
        
        df_target["cantidad_predicha"] = preds
        df_target["cantidad_vendida"] = preds # Feedback
        
        predicciones_futuras.append(df_target)
        
        # Actualizar historia
        cols_clave = ["fecha_mes", "v_id_producto", "categoria", "v_precio", "cantidad_vendida"]
        df_actual = pd.concat([df_actual, df_target[cols_clave]], ignore_index=True)
    
    return pd.concat(predicciones_futuras, ignore_index=True)

# ================================================
# 🔹 5. Expandir y Guardar
# ================================================
def expandir_y_guardar(df_mensual_pred):
    print("⚡ Distribuyendo a diario...", flush=True)
    filas_diarias = []
    
    for _, row in df_mensual_pred.iterrows():
        total_mes = row["cantidad_predicha"]
        if total_mes <= 0.05: continue # Filtrar ruido mínimo
        
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
# 🔹 MAIN
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
        # 1. Cargar y Agrupar
        df_mensual_hist = cargar_y_agrupar_mensual()
        if df_mensual_hist is None: return
        
        # 2. Generar Features Globales
        df_full_features = generar_features_mensuales(df_mensual_hist)
        
        # 3. Lógica
        if es_modo_demo:
            print("🧪 MODO DEMO: Entrenando < 2024", flush=True)
            fecha_corte = pd.Timestamp("2024-01-01")
            
            # Train: Todo < 2024. Filtramos el primer año porque los lags y rm_12 son nulos
            df_train = df_full_features[df_full_features["fecha_mes"] < fecha_corte].copy()
            # Necesitamos al menos 12 meses de historia para que rm_12 funcione bien
            fecha_min_train = df_train["fecha_mes"].min() + pd.DateOffset(months=12)
            df_train = df_train[df_train["fecha_mes"] >= fecha_min_train]
            
            # Validation
            df_real_2024 = df_full_features[df_full_features["fecha_mes"] >= fecha_corte].copy()
            
            # Entrenar
            modelo, features_col = entrenar_modelo(df_train)
            
            # Predecir (base < 2024)
            df_base_prediccion = df_full_features[df_full_features["fecha_mes"] < fecha_corte].copy()
            df_futuro = predecir_futuro_recursivo(modelo, df_base_prediccion, features_col, meses_a_predecir=meses_pred)
            
        else:
            print("🏭 MODO PRODUCCIÓN", flush=True)
            # Train: Todo el historial > 12 meses
            df_train = df_full_features[df_full_features["fecha_mes"] >= df_full_features["fecha_mes"].min() + pd.DateOffset(months=12)]
            
            modelo, features_col = entrenar_modelo(df_train)
            df_futuro = predecir_futuro_recursivo(modelo, df_full_features, features_col, meses_a_predecir=meses_pred)
            df_real_2024 = None

        # 4. Guardar
        expandir_y_guardar(df_futuro)
        
        # 5. Validación
        if es_modo_demo and df_real_2024 is not None:
            merged = pd.merge(df_real_2024, df_futuro, on=["fecha_mes", "v_id_producto"], suffixes=('_real', '_pred'))
            
            if not merged.empty:
                col_real = "cantidad_vendida_real"
                col_pred = "cantidad_predicha"
                
                # --- MÉTRICAS ---
                # 1. WMAPE General
                sum_err = (merged[col_real] - merged[col_pred]).abs().sum()
                sum_real = merged[col_real].sum()
                wmape = (sum_err / sum_real * 100) if sum_real > 0 else 0
                
                # 2. Precisión (Limitada visualmente)
                precision = max(0, 100 - wmape)
                
                print(f"📉 Error WMAPE Final: {wmape:.1f}%", flush=True)
                print(f"📊 Precisión Estimada: {precision:.1f}%", flush=True)
                
                # 3. FILTRO DE CALIDAD: ¿Cómo nos fue en productos 'Importantes'?
                # Filtramos productos que vendieron al menos 10 unidades en el año (evitar ruido de basura)
                prod_importantes = merged.groupby("v_id_producto")[col_real].transform("sum") > 10
                merged_imp = merged[prod_importantes]
                
                if not merged_imp.empty:
                    err_imp = (merged_imp[col_real] - merged_imp[col_pred]).abs().sum()
                    tot_imp = merged_imp[col_real].sum()
                    wmape_imp = (err_imp / tot_imp * 100)
                    print(f"💎 Precisión en Productos Top (>10 ventas): {max(0, 100-wmape_imp):.1f}%", flush=True)

            else:
                print("⚠️ Sin datos coincidentes para validar.", flush=True)

        print("🏆 PROCESO TERMINADO.", flush=True)

    except Exception as e:
        print(f"💥 Error Fatal: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()