# Archivo: src/modulos/reportes_graficos.py

import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# Directorio donde se guardarán los gráficos generados
RUTA_GRAFICOS = os.path.join(os.path.expanduser('~'), 'ReportesGenerados', 'Graficos')
os.makedirs(RUTA_GRAFICOS, exist_ok=True)


def generar_reporte_historico(df_datos: pd.DataFrame, producto_id: str = None, categoria: str = None):
    """
    Genera un gráfico de línea del histórico de ventas (cantidad_total) a lo largo del tiempo.
    
    Args:
        df_datos (pd.DataFrame): DataFrame con columnas 'v_fecha' y 'cantidad_total'.
        producto_id (str): ID del producto para el título.
        categoria (str): Categoría para el título.
    """
    if df_datos.empty:
        return None

    # Asegurarse de que la columna de fecha sea el índice para el gráfico de series de tiempo
    df_datos = df_datos.set_index('v_fecha')
    
    plt.figure(figsize=(12, 6))
    plt.plot(df_datos.index, df_datos['cantidad_total'], marker='o', linestyle='-', color='skyblue')
    
    # Construir el título del gráfico
    titulo = "Histórico de Ventas"
    if producto_id:
        titulo += f" | Producto ID: {producto_id}"
    if categoria:
        titulo += f" | Categoría: {categoria}"

    plt.title(titulo, fontsize=16)
    plt.xlabel("Fecha", fontsize=12)
    plt.ylabel("Cantidad Total Vendida", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout() # Ajustar el diseño para que no se corten las etiquetas

    # Guardar el gráfico
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"Historico_Ventas_{producto_id or 'General'}_{timestamp}.png"
    ruta_completa = os.path.join(RUTA_GRAFICOS, nombre_archivo)
    plt.savefig(ruta_completa)
    plt.close() # Cerrar la figura para liberar memoria
    
    return ruta_completa


def generar_grafico_prediccion(df_predicciones: pd.DataFrame, producto_id: str):
    """
    Genera un gráfico de línea con la proyección de ventas futuras.
    
    Args:
        df_predicciones (pd.DataFrame): DataFrame con las columnas 'fecha' y 'cantidad_predicha'.
        producto_id (str): ID del producto que se predijo.
    """
    if df_predicciones.empty:
        return None

    plt.figure(figsize=(12, 6))
    
    # Gráfico de línea para las predicciones
    plt.plot(df_predicciones['fecha'], df_predicciones['cantidad_predicha'], 
             marker='.', linestyle='--', color='tomato', label='Venta Predicha')
    
    plt.title(f"Proyección de Ventas Futuras | Producto ID: {producto_id}", fontsize=16)
    plt.xlabel("Fecha", fontsize=12)
    plt.ylabel("Cantidad Predicha (Unidades)", fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Guardar el gráfico
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"Prediccion_Ventas_{producto_id}_{timestamp}.png"
    ruta_completa = os.path.join(RUTA_GRAFICOS, nombre_archivo)
    plt.savefig(ruta_completa)
    plt.close()

    return ruta_completa