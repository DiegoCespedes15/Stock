# Archivo: src/model_trainer.py
import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import os
import sys
from datetime import datetime, timedelta
from sklearn.metrics import root_mean_squared_error
from sqlalchemy import text
import psycopg2.extras

print("🔊 SCRIPT INICIADO - IMPORTS CARGADOS")

# --- CONFIGURACIÓN DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Importamos las funciones que ya tenías
from bd import conectar_db
def cargar_dataset_temporal():
    engine = conectar_db()
    if engine is None:
        print("❌ ERROR: conexión fallida.")
        return None

    try:
        sql = f"SELECT * FROM desarrollo.prediccion_dataset ORDER BY anio, mes, dia_del_mes"
        df = pd.read_sql(sql, engine)
        print(f"✅ Dataset cargado ({len(df)} registros)")
        return df
    except Exception as e:
        print(f"❌ Error al leer dataset: {e}")
        return None
    finally:
        try:
            engine.close()
        except:
            pass


# ================================================
# 🔹 Crear features avanzadas en memoria
# ================================================
def crear_features_en_memoria(df):
    print("🔄 Generando features ESTÁTICAS ESTACIONALES...")
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["v_fecha"]):
         df["v_fecha"] = pd.to_datetime(df["v_fecha"])
    df = df.sort_values(["v_id_producto", "v_fecha"])

    # --- Calendario básico ---
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

    # --- ANCLAS ESTÁTICAS (MEMORIA SEGURA) ---
    # 1. Promedio General (ya lo teníamos)
    df["promedio_total"] = df.groupby("v_id_producto")["cantidad_vendida"].transform("mean")
    
    # 2. NUEVO: Promedio por MES (Captura estacionalidad sin riesgo recursivo)
    # Ej: Cuánto vende el producto X en Enero históricamente
    df["promedio_mensual"] = df.groupby(["v_id_producto", "mes"])["cantidad_vendida"].transform("mean")

    # --- LIMPIEZA ---
    # Eliminamos lags dinámicos para evitar colapso
    # Rellenamos nulos en las nuevas features estáticas
    for col in ["promedio_total", "promedio_mensual"]:
        df[col] = df[col].fillna(0)

    print("✅ Features estacionales generadas.")
    return df

# --- CONSTANTES ---
# Cambiamos a .json, es más seguro y universal para XGBoost
RUTA_MODELO = os.path.join(current_dir, "modelo_xgboost.json")
TABLA_PREDICCION = "prediccion_mensual"
SCHEMA = "desarrollo"


# ================================================
# 🔹 1. Entrenar Modelo Global
# ================================================
def entrenar_modelo_global(df_hist):
    """
    Entrena un único modelo global con todos los productos.
    """
    print(f"🚀 Iniciando entrenamiento GLOBAL con {len(df_hist)} registros...")

    # --- Preparar Features Categóricas ---
    # Convertimos 'v_id_producto' y 'categoria' en features
    # que XGBoost entenderá.
    try:
        df_hist["categoria"] = df_hist["categoria"].astype("category")
        df_hist["v_id_producto"] = df_hist["v_id_producto"].astype("category")
    except Exception as e:
        print(f"❌ Error convirtiendo tipos a 'category': {e}")
        print("Asegúrate de que las columnas 'categoria' y 'v_id_producto' existen.")
        return None

    # --- Definir X (features) e y (objetivo) ---
    # Excluimos la variable objetivo y la fecha original
    features_a_excluir = ["cantidad_vendida", "v_fecha"]
    
    # Nos aseguramos de excluir solo las que existan
    columnas_x = [col for col in df_hist.columns if col not in features_a_excluir]
    
    X_train = df_hist[columnas_x]
    y_train = df_hist["cantidad_vendida"]

    # --- Inicializar Modelo XGBoost ---
    modelo = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=150,        # Reducido de 250 para evitar overfit
        learning_rate=0.05,      # Más lento pero más seguro
        max_depth=4,             # Árboles menos profundos (antes 6)
        subsample=0.7,
        colsample_bytree=0.7,
        # min_child_weight=5,    # Opcional: obliga al modelo a no crear hojas con pocos datos
        random_state=42,
        enable_categorical=True,
        n_jobs=-1
    )

    # --- Entrenar ---
    print("📦 Entrenando modelo... esto puede tardar.")
    modelo.fit(X_train, y_train)
    print("✅ Modelo GLOBAL entrenado exitosamente.")

    # --- Guardar Modelo ---
    # Usamos .save_model() en formato JSON en lugar de pickle.
    # Es más robusto contra cambios de versión de librerías.
    modelo.save_model(RUTA_MODELO)
    print(f"💾 Modelo guardado en {RUTA_MODELO}")

    return modelo

# ================================================
# 🔹 2. Predecir Futuro Recursivo
# ================================================
# Reemplaza COMPLETAMENTE tu función predecir_futuro_recursivo con esta:

def predecir_futuro_directo(modelo, df_hist, dias_a_predecir=365):
    print(f"🚀 Iniciando predicción DIRECTA ESTACIONAL para {dias_a_predecir} días...")

    # 1. Extraer Anclas (General y Mensual)
    # Necesitamos dos tablas de anclas: una por producto y otra por producto-mes
    anclas_total = df_hist[["v_id_producto", "categoria", "promedio_total"]].drop_duplicates()
    anclas_mensual = df_hist[["v_id_producto", "mes", "promedio_mensual"]].groupby(["v_id_producto", "mes"]).mean().reset_index()

    # 2. Generar esqueleto de fechas futuras
    ultima_fecha = df_hist["v_fecha"].max()
    fechas_futuras = pd.date_range(start=ultima_fecha + timedelta(days=1), periods=dias_a_predecir, freq="D")
    
    # DataFrame base con todas las fechas
    df_futuro = pd.DataFrame({"v_fecha": fechas_futuras})
    df_futuro["mes"] = df_futuro["v_fecha"].dt.month # Necesario para el merge mensual

    # 3. Cruzar Productos x Fechas (Cross Join)
    # Primero obtenemos lista única de productos
    df_prods = anclas_total[["v_id_producto", "categoria", "promedio_total"]].copy()
    df_futuro = df_prods.merge(df_futuro, how="cross")

    # 4. Pegar el Ancla Mensual correcta
    df_futuro = pd.merge(df_futuro, anclas_mensual, on=["v_id_producto", "mes"], how="left")
    # Si no hay historia para un mes específico, usamos el promedio total como fallback
    df_futuro["promedio_mensual"] = df_futuro["promedio_mensual"].fillna(df_futuro["promedio_total"])

    # 5. Generar resto de features de calendario
    df_futuro["anio"] = df_futuro["v_fecha"].dt.year
    df_futuro["dia_del_mes"] = df_futuro["v_fecha"].dt.day
    df_futuro["dia_de_la_semana"] = df_futuro["v_fecha"].dt.dayofweek
    df_futuro["semana_del_anio"] = df_futuro["v_fecha"].dt.isocalendar().week.astype(int)
    df_futuro["es_fin_de_semana"] = (df_futuro["dia_de_la_semana"] >= 5).astype(int)
    df_futuro["es_fin_mes"] = (df_futuro["dia_del_mes"] >= 25).astype(int)
    df_futuro["anio_mes"] = df_futuro["v_fecha"].dt.strftime("%Y%m").astype(int)
    df_futuro["mes_sin"] = np.sin(2 * np.pi * df_futuro["mes"] / 12)
    df_futuro["mes_cos"] = np.cos(2 * np.pi * df_futuro["mes"] / 12)

    # 6. Predecir
    cols_modelo = modelo.get_booster().feature_names
    X_futuro = df_futuro[cols_modelo].copy()
    for col in ["v_id_producto", "categoria"]:
        X_futuro[col] = X_futuro[col].astype("category")

    print(f"🔮 Prediciendo {len(X_futuro)} filas de una sola vez...")
    df_futuro["cantidad_vendida"] = np.clip(modelo.predict(X_futuro), 0, None)
    print("✅ Predicción directa completada.")
    return df_futuro

# ================================================
# 🔹 3. Guardar predicciones en la BD
# ================================================
def guardar_predicciones_db(df_preds):
    if df_preds is None or df_preds.empty:
        print("⚠️ No hay predicciones para guardar.")
        return

    print(f"💾 Preparando {len(df_preds)} registros para inserción directa...")

    # 1. Preparar DataFrame (Igual que antes)
    df_final = df_preds.copy()
    if "v_fecha" not in df_final.columns:
        df_final["v_fecha"] = pd.to_datetime(df_final[["anio", "mes", "dia_del_mes"]].rename(columns={"anio": "year", "mes": "month", "dia_del_mes": "day"}))
    df_final["cantidad_vendida_real"] = 0
    df_final["fecha_entrenamiento"] = datetime.now()
    if "cantidad_vendida" in df_final.columns and "cantidad_predicha" not in df_final.columns:
         df_final.rename(columns={"cantidad_vendida": "cantidad_predicha"}, inplace=True)

    # Columnas exactas para la BD
    cols_db = ["v_id_producto", "v_fecha", "anio", "mes", "dia_del_mes", "dia_de_la_semana", "categoria", "cantidad_predicha", "cantidad_vendida_real", "fecha_entrenamiento"]
    df_final_db = df_final[cols_db]

    # Convertir DataFrame a lista de tuplas para psycopg2
    lista_valores = [tuple(x) for x in df_final_db.to_numpy()]

    # 2. Conexión e Inserción con Cursor
    conn = conectar_db()
    if conn is None: return

    try:
        with conn.cursor() as cur:
            print(f"🧹 Limpiando tabla {SCHEMA}.{TABLA_PREDICCION}...")
            cur.execute(f"TRUNCATE TABLE {SCHEMA}.{TABLA_PREDICCION} RESTART IDENTITY;")
            
            print("📥 Insertando masivamente...")
            query_insert = f"""
                INSERT INTO {SCHEMA}.{TABLA_PREDICCION}
                ({', '.join(cols_db)})
                VALUES %s
            """
            # execute_values es MUY eficiente para grandes volúmenes
            psycopg2.extras.execute_values(cur, query_insert, lista_valores, page_size=10000)
            
        conn.commit() # ¡IMPORTANTE! Confirmar la transacción
        print("✅ ¡Predicciones guardadas exitosamente!")

    except Exception as e:
        print(f"❌ Error guardando con cursor: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
        
# ================================================
# 🔹 Ejecución principal (Workflow)
# ================================================
if __name__ == "__main__":
    print("🧪 INICIANDO MODO VALIDACIÓN 2024 (CON GUARDADO EN BD)")
    try:
        # 1. Cargar TODO el historial
        df_completo = cargar_dataset_temporal()
        if df_completo is None: raise Exception("Fallo carga de datos")

        # 2. Crear features (Estacionalidad estable)
        df_features = crear_features_en_memoria(df_completo)

        # --- CORTE TEMPORAL ---
        fecha_corte = pd.Timestamp("2024-01-01")
        df_train_2023 = df_features[df_features["v_fecha"] < fecha_corte].copy()
        df_test_real_2024 = df_features[df_features["v_fecha"] >= fecha_corte].copy()
        
        print(f"📊 Entrenando con datos hasta: {df_train_2023['v_fecha'].max().date()}")

        # 3. Entrenar modelo SOLO con 2023
        modelo = entrenar_modelo_global(df_train_2023)

        # 4. Predecir el 2024
        dias_2024 = (df_test_real_2024["v_fecha"].max() - fecha_corte).days + 1
        # Si no hay datos de 2024, predecimos 366 por defecto (año bisiesto 2024)
        if np.isnan(dias_2024) or dias_2024 <= 0: dias_2024 = 366
            
        df_prediccion_2024 = predecir_futuro_directo(modelo, df_train_2023, dias_a_predecir=int(dias_2024))

        # =========================================
        # 🛑 AQUÍ ESTÁ EL INSERT QUE PEDISTE
        # =========================================
        # Guardamos las predicciones de 2024 en la BD para que tu módulo de gráficos las vea.
        # OJO: Esto borrará lo que haya en la tabla 'prediccion_mensual'
        guardar_predicciones_db(df_prediccion_2024)
        # =========================================

        # 5. VALIDACIÓN (Comparar con realidad en pantalla)
        print("\n--- 📉 RESULTADOS DE VALIDACIÓN 2024 ---")
        df_comparativa = pd.merge(
            df_test_real_2024[["v_fecha", "v_id_producto", "cantidad_vendida"]],
            # USA 'cantidad_vendida' SI ASÍ LA LLAMASTE EN LA FUNCIÓN DE PREDICCIÓN
            df_prediccion_2024[["v_fecha", "v_id_producto", "cantidad_vendida"]], 
            on=["v_fecha", "v_id_producto"], how="inner",
            suffixes=("_real", "_pred") # Esto renombrará automáticamente a cantidad_vendida_real y _pred
        )
        
        # Ajuste de nombres para consistencia
        df_comparativa.rename(columns={"cantidad_predicha": "cantidad_vendida_pred", "cantidad_vendida": "cantidad_vendida_real"}, inplace=True)

        mae = (df_comparativa["cantidad_vendida_real"] - df_comparativa["cantidad_vendida_pred"]).abs().mean()
        print(f"📉 MAE Diario: {mae:.2f}")

        # Validación Mensual Rápida
        df_comparativa["mes"] = df_comparativa["v_fecha"].dt.month
        df_mensual = df_comparativa.groupby(["mes", "v_id_producto"])[["cantidad_vendida_real", "cantidad_vendida_pred"]].sum()
        wmape = (df_mensual["cantidad_vendida_real"] - df_mensual["cantidad_vendida_pred"]).abs().sum() / df_mensual["cantidad_vendida_real"].sum() * 100
        print(f"📊 WMAPE Mensual Global: {wmape:.2f}%")

        print("✅ Proceso finalizado: Predicciones 2024 guardadas y validadas.")

    except Exception as e:
        print(f"💥 ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()

    # --- Métricas Diarias (YA LO TIENES) ---
    df_comparativa["error_absoluto"] = abs(df_comparativa["cantidad_vendida_real"] - df_comparativa["cantidad_vendida_pred"])
    mae = df_comparativa["error_absoluto"].mean()
    print(f"📉 MAE Diario: {mae:.2f}")

    # --- 📅 INSERTAR AQUÍ LA VALIDACIÓN MENSUAL ---
    print("\n--- 📅 VALIDACIÓN MENSUAL ---")
    # 1. Agrupar por año, mes y producto
    df_mensual = df_comparativa.copy()
    df_mensual['anio'] = df_mensual['v_fecha'].dt.year
    df_mensual['mes'] = df_mensual['v_fecha'].dt.month
    
    df_mensual_agg = df_mensual.groupby(['anio', 'mes', 'v_id_producto'])[[
        "cantidad_vendida_real", "cantidad_vendida_pred"
    ]].sum().reset_index()

    # 2. Calcular métricas mensuales
    df_mensual_agg["error_absoluto"] = abs(df_mensual_agg["cantidad_vendida_real"] - df_mensual_agg["cantidad_vendida_pred"])
    
    mae_mensual = df_mensual_agg["error_absoluto"].mean()
    print(f"📉 MAE Mensual: {mae_mensual:.2f} unidades por mes")

    total_ventas_mes = df_mensual_agg["cantidad_vendida_real"].sum()
    if total_ventas_mes > 0:
        wmape_mensual = (df_mensual_agg["error_absoluto"].sum() / total_ventas_mes) * 100
        print(f"📊 WMAPE Mensual: {wmape_mensual:.2f}%")
    else:
        print("⚠️ No hay ventas reales para calcular WMAPE mensual.")

    print("\n--- 📊 ANÁLISIS POR VOLUMEN DE VENTAS ---")
    # 1. Calcular venta total histórica por producto para clasificarlos
    ventas_por_producto = df_mensual_agg.groupby("v_id_producto")["cantidad_vendida_real"].sum()
    
    # Clasificamos: Top 20% de productos (Pareto) vs el resto
    top_productos = ventas_por_producto.nlargest(int(len(ventas_por_producto) * 0.2)).index
    
    df_top = df_mensual_agg[df_mensual_agg["v_id_producto"].isin(top_productos)]
    df_bajo = df_mensual_agg[~df_mensual_agg["v_id_producto"].isin(top_productos)]

    # 2. Calcular WMAPE para cada grupo
    def calcular_wmape(df, nombre):
        total_ventas = df["cantidad_vendida_real"].sum()
        total_error = df["error_absoluto"].sum()
        if total_ventas > 0:
            wmape = (total_error / total_ventas) * 100
            print(f"👉 {nombre}: WMAPE = {wmape:.2f}% (en {len(df)} registros mensuales)")
        else:
            print(f"👉 {nombre}: No hay ventas suficientes para calcular WMAPE.")

    calcular_wmape(df_top, "Top 20% Productos (Alta Rotación)")
    calcular_wmape(df_bajo, "Resto de Productos (Baja Rotación)")

    print("\n--- 🧐 INSPECCIÓN VISUAL (Top Producto) ---")
    # Tomamos el ID del producto más vendido
    top_product_id = df_mensual_agg.groupby("v_id_producto")["cantidad_vendida_real"].sum().idxmax()
    
    print(f"Producto más vendido (ID: {top_product_id}):")
    muestra = df_mensual_agg[df_mensual_agg["v_id_producto"] == top_product_id].sort_values(["anio", "mes"])
    
    for _, row in muestra.iterrows():
        print(f"  📅 {int(row['anio'])}-{int(row['mes']):02d} | Real: {int(row['cantidad_vendida_real']):<5} | Pred: {int(row['cantidad_vendida_pred']):<5} | Diff: {int(row['cantidad_vendida_pred'] - row['cantidad_vendida_real'])}")
    
    print("✅ Validación completada.")