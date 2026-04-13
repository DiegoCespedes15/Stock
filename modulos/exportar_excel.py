import pandas as pd
import os
from openpyxl.styles import Font, PatternFill, Alignment

def exportar_a_excel(df_reporte: pd.DataFrame, ruta_completa: str):
    """
    Exporta el DataFrame a Excel con formato profesional (Auto-ajuste de columnas y encabezados con estilo).
    """
    ruta_limpia = os.path.normpath(ruta_completa)
    print(f"Guardando Excel en: {ruta_limpia}...")
    
    try:
        # Usamos ExcelWriter para poder manipular el archivo antes de cerrarlo
        with pd.ExcelWriter(ruta_limpia, engine='openpyxl') as writer:
            df_reporte.to_excel(writer, index=False, sheet_name='Reporte de Inventario')
            
            # Obtenemos la hoja de cálculo que acabamos de crear
            worksheet = writer.sheets['Reporte de Inventario']
            
            # --- 1. ESTILO DE ENCABEZADOS ---
            # Fondo verde oscuro y letras blancas en negrita (Estilo corporativo)
            header_fill = PatternFill(start_color="006400", end_color="006400", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            
            for cell in worksheet[1]: # Iteramos sobre la primera fila (los títulos)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # --- 2. AUTO-AJUSTE DE ANCHO DE COLUMNAS ---
            # Recorremos todas las columnas para encontrar el texto más largo y ajustar el ancho
            for column in worksheet.columns:
                max_length = 0
                col_letter = column[0].column_letter # Obtiene la letra de la columna (A, B, C...)
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                # Le damos un pequeño margen extra al ancho (+2)
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[col_letter].width = adjusted_width

        print(f"✅ Reporte de Excel creado con formato profesional.")
        
    except Exception as e:
        error_detalle = f"Verifique si la ruta '{ruta_limpia}' existe, si tiene permisos, o si el archivo ya está abierto."
        raise Exception(f"Error al escribir el archivo Excel en disco: {e}. Detalle: {error_detalle}")