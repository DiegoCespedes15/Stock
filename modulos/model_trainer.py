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
    print("🔄 Generando features ESTÁTICAS ESTACIONALES + TENDENCIA...")
    df = df.copy()
    
    # Asegurar tipo de dato fecha
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
    
    # Features cíclicas (ayudan con la estacionalidad anual)
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)

    # --- 2. ANCLAS ESTÁTICAS (MEMORIA SEGURA) ---
    # Promedio histórico general del producto
    df["promedio_total"] = df.groupby("v_id_producto")["cantidad_vendida"].transform("mean")
    
    # Promedio histórico por MES (Captura estacionalidad específica, ej: picos en diciembre)
    df["promedio_mensual"] = df.groupby(["v_id_producto", "mes"])["cantidad_vendida"].transform("mean")

    # --- 3. NUEVO: POTENCIA DEL PRODUCTO ---
    # Calculamos cuánto ha vendido históricamente este producto en total
    df["venta_total_prod"] = df.groupby("v_id_producto")["cantidad_vendida"].transform("sum")
    
    # Calculamos cuánto ha vendido toda su categoría en total
    df["venta_total_cat"] = df.groupby("categoria")["cantidad_vendida"].transform("sum")
    
    # RATIO DE POTENCIA: ¿Qué porcentaje de la categoría representa este producto?
    # (Sumamos +1 al denominador para evitar división por cero si la categoría es nueva)
    df["ratio_potencia_producto"] = df["venta_total_prod"] / (df["venta_total_cat"] + 1)

    # --- 4. LIMPIEZA ---
    # Rellenamos nulos en las features nuevas
    cols_a_rellenar = [
        "promedio_total", 
        "promedio_mensual", 
        "ratio_potencia_producto",
        "venta_total_prod",
        "venta_total_cat"
    ]
    
    for col in cols_a_rellenar:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    print("✅ Features estacionales y de tendencia generadas correctamente.")
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
        n_estimators=300,        # Reducido de 250 para evitar overfit
        learning_rate=0.03,      # Más lento pero más seguro
        max_depth=7,             # Árboles menos profundos (antes 6)
        subsample=0.8,
        colsample_bytree=0.8,
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
    print(f"🔮 Iniciando predicción DIRECTA para los próximos {dias_a_predecir} días...")

    # 1. Extraer Anclas ESTÁTICAS (General y Nuevas variables de Tendencia)
    # Estas son características que NO cambian con el tiempo (son propias del producto)
    cols_estaticas = [
        "v_id_producto", 
        "categoria", 
        "promedio_total", 
        "ratio_potencia_producto", # <--- Nueva variable importante
        "venta_total_prod",        # <--- Nueva
        "venta_total_cat"          # <--- Nueva
    ]
    # Filtramos para usar solo las columnas que realmente existen en el histórico
    cols_existentes = [c for c in cols_estaticas if c in df_hist.columns]
    
    # Creamos un dataframe único de productos con sus características fijas
    anclas_total = df_hist[cols_existentes].drop_duplicates()

    # 2. Extraer Anclas MENSUALES (Estacionalidad)
    # Promedio histórico por mes y producto
    anclas_mensual = df_hist[["v_id_producto", "mes", "promedio_mensual"]].groupby(["v_id_producto", "mes"]).mean().reset_index()

    # 3. Generar fechas futuras (desde el día siguiente al último dato)
    ultima_fecha = df_hist["v_fecha"].max()
    fechas_futuras = pd.date_range(start=ultima_fecha + timedelta(days=1), periods=dias_a_predecir, freq="D")
    
    df_futuro = pd.DataFrame({"v_fecha": fechas_futuras})
    df_futuro["mes"] = df_futuro["v_fecha"].dt.month

    # 4. Cruzar Productos x Fechas (Cross Join)
    # Esto crea una fila para cada producto en cada fecha futura
    df_futuro = anclas_total.merge(df_futuro, how="cross")

    # 5. Pegar el Ancla Mensual correcta
    df_futuro = pd.merge(df_futuro, anclas_mensual, on=["v_id_producto", "mes"], how="left")
    
    # Si un producto es nuevo y no tiene historia en un mes específico, usamos su promedio total como relleno
    if "promedio_total" in df_futuro.columns:
        df_futuro["promedio_mensual"] = df_futuro["promedio_mensual"].fillna(df_futuro["promedio_total"])
    else:
        df_futuro["promedio_mensual"] = df_futuro["promedio_mensual"].fillna(0)

    # 6. Generar resto de features de calendario
    # (Debe ser idéntico a lo que hiciste en crear_features_en_memoria)
    df_futuro["anio"] = df_futuro["v_fecha"].dt.year
    df_futuro["dia_del_mes"] = df_futuro["v_fecha"].dt.day
    df_futuro["dia_de_la_semana"] = df_futuro["v_fecha"].dt.dayofweek
    df_futuro["semana_del_anio"] = df_futuro["v_fecha"].dt.isocalendar().week.astype(int)
    df_futuro["es_fin_de_semana"] = (df_futuro["dia_de_la_semana"] >= 5).astype(int)
    df_futuro["es_fin_mes"] = (df_futuro["dia_del_mes"] >= 25).astype(int)
    df_futuro["anio_mes"] = df_futuro["v_fecha"].dt.strftime("%Y%m").astype(int)
    df_futuro["mes_sin"] = np.sin(2 * np.pi * df_futuro["mes"] / 12)
    df_futuro["mes_cos"] = np.cos(2 * np.pi * df_futuro["mes"] / 12)
    
    # Feature de tendencia (días desde inicio)
    min_fecha_hist = df_hist["v_fecha"].min()
    df_futuro["dias_desde_inicio"] = (df_futuro["v_fecha"] - min_fecha_hist).dt.days

    # 7. Preparar para el modelo
    cols_modelo = modelo.get_booster().feature_names
    
    # Asegurar que todas las columnas necesarias están presentes (rellenar con 0 si falta alguna rara)
    for col in cols_modelo:
        if col not in df_futuro.columns:
            df_futuro[col] = 0

    X_futuro = df_futuro[cols_modelo].copy()
    
    # Asegurar tipos categóricos
    for col in ["v_id_producto", "categoria"]:
        if col in X_futuro.columns:
            X_futuro[col] = X_futuro[col].astype("category")

    # 8. Predecir
    print(f"⚡ Generando predicciones para {len(X_futuro)} registros...")
    predicciones = modelo.predict(X_futuro)
    
    # Guardar predicción asegurando que no sea negativa
    df_futuro["cantidad_predicha"] = np.clip(predicciones, 0, None)

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
    print("🧪 PREPARANDO ENTORNO DE DEMO (MODO VALIDACIÓN 2024)")
    try:
        # 1. Cargar TODO el historial (2023 + 2024)
        df_completo = cargar_dataset_temporal()
        if df_completo is None: raise Exception("Fallo carga de datos")

        # 2. Crear features (Estacionalidad estable)
        df_features = crear_features_en_memoria(df_completo)

        # --- CORTE TEMPORAL ---
        fecha_corte = pd.Timestamp("2024-01-01")
        df_train_2023 = df_features[df_features["v_fecha"] < fecha_corte].copy()
        
        # ✅ CORRECCIÓN: Aquí definimos la variable que faltaba
        df_test_real_2024 = df_features[df_features["v_fecha"] >= fecha_corte].copy()
        
        if df_train_2023.empty:
            raise Exception("No hay datos de 2023 para entrenar. Verifique la BD.")
            
        print(f"📊 Entrenando con datos hasta: {df_train_2023['v_fecha'].max().date()}")

        # 3. Entrenar modelo SOLO con 2023
        modelo = entrenar_modelo_global(df_train_2023)

        # 4. Predecir el 2024
        # (Usamos 366 días para 2024, que fue bisiesto)
        df_prediccion_2024 = predecir_futuro_directo(modelo, df_train_2023, dias_a_predecir=366)

        # 5. GUARDAR DATOS DE 2024 EN LA BD
        print("💾 Guardando pronóstico de 2024 en la base de datos para la simulación...")
        guardar_predicciones_db(df_prediccion_2024)
        
        print("\n✅ Entorno de DEMO listo. La tabla 'prediccion_mensual' contiene datos de 2024.")
        print("Ahora puede ejecutar el reporte de optimización desde la UI.")

        print("\n--- 📉 RESULTADOS DE VALIDACIÓN 2024 ---")
        
        # CORRECCIÓN AQUÍ: Usamos 'cantidad_predicha' en el dataframe de predicción
        df_comparativa = pd.merge(
            df_test_real_2024[["v_fecha", "v_id_producto", "cantidad_vendida"]],   # Dato Real
            df_prediccion_2024[["v_fecha", "v_id_producto", "cantidad_predicha"]], # Dato Predicho (Nombre corregido)
            on=["v_fecha", "v_id_producto"], 
            how="inner"
        )
        
        # Renombrar columnas para que el cálculo de error funcione
        df_comparativa.rename(columns={
            "cantidad_vendida": "cantidad_vendida_real",
            "cantidad_predicha": "cantidad_vendida_pred"
        }, inplace=True)

        # Calcular métricas
        mae = (df_comparativa["cantidad_vendida_real"] - df_comparativa["cantidad_vendida_pred"]).abs().mean()
        print(f"📉 MAE Diario: {mae:.2f}")

        # Validación Mensual Rápida
        df_comparativa["mes"] = df_comparativa["v_fecha"].dt.month
        
        # Agrupar por mes y producto
        df_mensual = df_comparativa.groupby(["mes", "v_id_producto"])[["cantidad_vendida_real", "cantidad_vendida_pred"]].sum()
        
        # Calcular WMAPE
        total_ventas_reales = df_mensual["cantidad_vendida_real"].sum()
        if total_ventas_reales > 0:
            error_total = (df_mensual["cantidad_vendida_real"] - df_mensual["cantidad_vendida_pred"]).abs().sum()
            wmape = (error_total / total_ventas_reales) * 100
            print(f"📊 WMAPE Mensual Global: {wmape:.2f}%")
        else:
            print("⚠️ No hay ventas reales para calcular WMAPE.")

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