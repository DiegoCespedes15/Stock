# Archivo: src/feature_engineering/predictor.py

import pandas as pd
import numpy as np
import pickle
from datetime import datetime
import os

# Directorio del modelo (asume que está al lado del data_processor)
# Ambos están en src/feature_engineering/
RUTA_MODELO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modelo_xgboost.pkl')

def cargar_modelo():
    """
    Carga el modelo XGBoost previamente entrenado desde el archivo .pkl.
    """
    try:
        # Nota: La ruta correcta es clave. El modelo fue guardado en el directorio src/
        # Si tienes problemas, verifica dónde se guardó realmente 'modelo_xgboost.pkl'
        # y ajusta RUTA_MODELO.
        ruta_modelo_ajustada = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modelo_xgboost.pkl')
        
        with open(ruta_modelo_ajustada, 'rb') as f:
            modelo = pickle.load(f)
        return modelo
    except FileNotFoundError:
        print(f"❌ Error: Archivo de modelo no encontrado. Asegúrese de que 'modelo_xgboost.pkl' esté en el directorio 'src/'.")
        return None
    except Exception as e:
        print(f"❌ Error al cargar el modelo: {e}")
        return None

def crear_df_futuro(producto_id, anio_prediccion):
    """
    Crea un DataFrame con todas las fechas del año a predecir 
    y sus características temporales.
    """
    try:
        # Generar un rango de fechas para todo el año
        fecha_inicio = f'{anio_prediccion}-01-01'
        fecha_fin = f'{anio_prediccion}-12-31'
        
        df_futuro = pd.DataFrame({
            'v_fecha': pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
        })
        
        # El ID del producto DEBE estar codificado de la misma forma que se entrenó.
        # Ya que en 'data_processor.py' usamos .cat.codes, si solo entrenaste un producto, 
        # el ID codificado será 0. Si entrenaste múltiples, la lógica aquí debe ser más compleja.
        df_futuro['v_id_producto'] = 0 

        # Extraer las mismas características temporales que en el entrenamiento
        df_futuro['dia_del_mes'] = df_futuro['v_fecha'].dt.day
        df_futuro['dia_de_la_semana'] = df_futuro['v_fecha'].dt.dayofweek
        df_futuro['mes'] = df_futuro['v_fecha'].dt.month
        df_futuro['anio'] = df_futuro['v_fecha'].dt.year

        # Seleccionar solo las columnas de características para la predicción
        X_futuro = df_futuro[[
            'v_id_producto', 
            'dia_del_mes', 
            'dia_de_la_semana', 
            'mes', 
            'anio'
        ]]
        
        return X_futuro, df_futuro[['v_fecha']]

    except Exception as e:
        print(f"Error al crear el DataFrame futuro: {e}")
        return pd.DataFrame(), pd.DataFrame()


def predecir_ventas_anuales(modelo, producto_id, anio_prediccion):
    """
    Genera las predicciones de ventas diarias para el producto y año dados.
    """
    if modelo is None:
        return pd.DataFrame()
        
    X_futuro, df_fechas = crear_df_futuro(producto_id, anio_prediccion)
    
    if X_futuro.empty:
        return pd.DataFrame()

    try:
        # Generar las predicciones
        predicciones = modelo.predict(X_futuro)
        
        # Asegurar que las predicciones no sean negativas y redondear
        predicciones = np.maximum(0, predicciones).round().astype(int)
        
        # Combinar las fechas con las predicciones
        df_resultado = df_fechas.copy()
        df_resultado['cantidad_predicha'] = predicciones
        
        # Agrupar por mes para un reporte más conciso (opcional)
        df_resultado['mes'] = df_resultado['v_fecha'].dt.to_period('M')
        df_reporte = df_resultado.groupby('mes').agg(
            ventas_predichas=('cantidad_predicha', 'sum')
        ).reset_index()
        
        return df_resultado # Devolvemos el DataFrame diario para el gráfico

    except Exception as e:
        print(f"Error durante la predicción: {e}")
        return pd.DataFrame()