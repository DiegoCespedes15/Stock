# Archivo: src/reportes/export_excel.py

import pandas as pd
import os
import time

def exportar_a_excel(df_reporte: pd.DataFrame, ruta_completa: str):
    """
    Exporta el DataFrame de reporte al path completo especificado por el usuario,
    asegurando la compatibilidad de la ruta.
    """
    
    # ⚠️ Mejora de Robustez: Normalizar la ruta a un formato estándar de sistema operativo
    # Esto puede ayudar con problemas de codificación o barras inversas.
    ruta_limpia = os.path.normpath(ruta_completa)
    
    print(f"Guardando Excel en: {ruta_limpia}...")
    
    try:
        df_reporte.to_excel(
            ruta_limpia, # Usar la ruta normalizada
            index=False, 
            sheet_name='Datos del Reporte',
            engine='openpyxl' 
        )
        print(f"✅ Reporte de Excel creado con éxito.")
    except Exception as e:
        # Lanzamos una excepción más informativa
        error_detalle = f"Verifique si la ruta '{ruta_limpia}' existe o si tiene permisos de escritura."
        raise Exception(f"Error al escribir el archivo Excel en disco: {e}. Detalle: {error_detalle}")