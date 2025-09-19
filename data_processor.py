# Archivo: src/feature engineering/data_processor.py
import pandas as pd
# Corregimos la importación para que pueda ver el archivo bd.py en la carpeta superior
from bd import conectar_db

def obtener_datos_para_prediccion():
    """
    Conecta a la base de datos y obtiene los datos de ventas necesarios
    para la predicción.
    """
    try:
        conn = conectar_db()
        # Seleccionamos las columnas clave de la tabla de ventas
        query = "SELECT v_fecha, v_id_producto, v_cantidad FROM desarrollo.ventas"
        df_ventas = pd.read_sql(query, conn)
        conn.close()
        return df_ventas
    except Exception as e:
        print(f"Error al obtener datos de ventas: {e}")
        return pd.DataFrame()

def preparar_dataset_para_xgboost(df):
    """
    Realiza la ingeniería de características sobre el DataFrame de ventas.
    """
    if df.empty:
        return None, None

    # Agregamos las ventas por día y por producto para tener una serie de tiempo
    df_agregado = df.groupby(['v_fecha', 'v_id_producto']).agg(
        cantidad_vendida=('v_cantidad', 'sum')
    ).reset_index()

    # Convertir la columna de fecha a tipo datetime
    df_agregado['v_fecha'] = pd.to_datetime(df_agregado['v_fecha'])

    # Extraer características de la fecha.
    df_agregado['dia_del_mes'] = df_agregado['v_fecha'].dt.day
    df_agregado['dia_de_la_semana'] = df_agregado['v_fecha'].dt.dayofweek
    df_agregado['mes'] = df_agregado['v_fecha'].dt.month
    df_agregado['anio'] = df_agregado['v_fecha'].dt.year

    # Definimos las características (X) y la variable objetivo (y)
    features = ['v_id_producto', 'dia_del_mes', 'dia_de_la_semana', 'mes', 'anio']
    target = 'cantidad_vendida'

    X = df_agregado[features]
    y = df_agregado[target]

    return X, y

if __name__ == '__main__':
    df_ventas = obtener_datos_para_prediccion()
    if not df_ventas.empty:
        X, y = preparar_dataset_para_xgboost(df_ventas)
        if X is not None:
            print("Dataset de características (X) preparado:")
            print(X.head())
            print("\nVariable objetivo (y) preparada:")
            print(y.head())