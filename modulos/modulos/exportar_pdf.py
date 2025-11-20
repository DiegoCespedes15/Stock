from fpdf import FPDF, XPos, YPos
import pandas as pd
from datetime import datetime

class PDF(FPDF):
    """Clase personalizada para el PDF con encabezados y pies de página."""
    def __init__(self, tipo_reporte, filtros):
        # ✅ AJUSTE: Orientación 'L' (Apaisado) para Reporte IA si tiene muchas columnas
        if tipo_reporte == 'Ventas' or tipo_reporte == 'Reporte Inteligente de Reabastecimiento (EOQ)':
            super().__init__('L', 'mm', 'A4')
        else:
            super().__init__('P', 'mm', 'A4') # Inventario en Portrait
            
        self.tipo_reporte = tipo_reporte
        self.filtros = filtros

    def header(self):
        self.set_font('Arial', 'B', 14)
        ancho_pagina = self.w - 2 * self.l_margin
        
        # 1. Título Centrado
        titulo = f"REPORTE DE {self.tipo_reporte.upper()}"
        self.set_x(self.l_margin)
        self.cell(ancho_pagina, 8, titulo, border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # 2. Resumen de Filtros
        self.set_font('Arial', '', 9)
        y_inicial = self.get_y()
        self.set_fill_color(220, 220, 220)
        self.set_draw_color(150, 150, 150)
        
        # Parámetros del reporte
        info_filtro = [f"Generado el: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"]
        info_filtro.append(f"Categoría: {self.filtros.get('categoria', 'N/A')}")
        
        if self.tipo_reporte == 'Ventas':
            info_filtro.append(f"Rango: {self.filtros.get('fecha_inicio', 'N/A')} al {self.filtros.get('fecha_fin', 'N/A')}")
            info_filtro.append(f"ID Producto: {self.filtros.get('id_producto', 'Todos')}")
        
        # ✅ AJUSTE: El reporte IA no necesita filtros de fecha (siempre es futuro)
        elif self.tipo_reporte == 'Reporte Inteligente de Reabastecimiento (EOQ)':
            info_filtro.append("Datos: Predicción 30 días (XGBoost + EOQ)")

        # Imprimir filtros en una línea
        self.set_x(self.l_margin)
        ancho_celda_filtro = ancho_pagina / len(info_filtro)
        for i, info in enumerate(info_filtro):
            self.cell(ancho_celda_filtro, 6, info, border=1, align='C', fill=True, new_x=XPos.RIGHT)
        
        self.set_y(y_inicial + 6 + 5) # Salto de línea después del resumen

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')


def exportar_a_pdf(df_reporte: pd.DataFrame, file_path: str, tipo_reporte: str, filtros: dict):
    """
    Exporta un DataFrame a un archivo PDF maquetado.
    """
    
    def sanitizar_texto(texto):
        """Codifica y decodifica el texto a latin-1 para soportar tildes y ñ."""
        if texto is None:
            return ''
        texto = str(texto).replace('•', '') 
        return texto.encode('latin-1', 'replace').decode('latin-1')

    try:
        # ✅ MEJORA: Trabajar sobre una copia para evitar el SettingWithCopyWarning
        df_reporte = df_reporte.copy()

        pdf = PDF(tipo_reporte, filtros)
        pdf.alias_nb_pages()
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 10)
        
        # Truncar descripción si existe
        if 'descripcion' in df_reporte.columns:
            df_reporte['descripcion'] = df_reporte['descripcion'].astype(str).str.slice(0, 50) + \
                                        df_reporte['descripcion'].astype(str).apply(lambda x: '...' if len(x) > 50 else '')

        # 1. Preprocesar y definir columnas visibles y anchos
        if tipo_reporte == "Inventario":
            # Orientación 'P' (190mm usable)
            columnas_visibles = ['id_articulo', 'descripcion', 'categoria', 'cant_inventario', 'precio_unit']
            nombres_columnas = ['ID', 'Descripción', 'Categoría', 'Stock Actual', 'P. Unitario (USD)']
            ancho_columna = [20, 89, 35, 20, 25] # Total: 189
            
        elif tipo_reporte == "Ventas":
            # Orientación 'L' (277mm usable)
            columnas_visibles = ['fecha_venta', 'producto', 'nombre_cliente', 'cantidad', 'monto_unitario', 'monto_total']
            nombres_columnas = ['Fecha', 'Producto', 'Cliente', 'Cantidad', 'P. Unit. (USD)', 'Total Venta (USD)']
            ancho_columna = [30, 95, 70, 20, 30, 30] # Total: 275
        
        # ✅ NUEVO: Definición para el Reporte de Optimización IA
        elif tipo_reporte == "Reporte Inteligente de Reabastecimiento (EOQ)":
            # Orientación 'L' (277mm usable)
            columnas_visibles = [
                "id_articulo", 
                "descripcion", 
                "categoria", 
                "stock_actual", 
                "demanda_predicha_mes", 
                "punto_reorden", 
                "accion_sugerida", 
                "sugerencia_cantidad"
            ]
            nombres_columnas = [
                "ID", "Descripción", "Categoría", "Stock Actual", 
                "Demanda 30d (IA)", "Punto Reorden", "Acción Sugerida", "Cant. a Comprar"
            ]
            ancho_columna = [15, 70, 40, 20, 30, 25, 35, 30] # Total: 265
        
        else:
            # Si no se define, usamos todas las columnas por defecto (puede verse mal)
            print(f"Advertencia: Tipo de reporte '{tipo_reporte}' no tiene formato PDF definido. Usando formato por defecto.")
            columnas_visibles = df_reporte.columns.tolist()
            nombres_columnas = df_reporte.columns.tolist()
            ancho_columna = [ (pdf.w - 2 * pdf.l_margin) / len(columnas_visibles) ] * len(columnas_visibles)


        df_imprimir = df_reporte[columnas_visibles].fillna('') 
        
        # 2. Imprimir Encabezado de la Tabla
        pdf.set_fill_color(0, 128, 0) 
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 8)
        
        for i, header in enumerate(nombres_columnas):
            pdf.cell(ancho_columna[i], 7, sanitizar_texto(header), 1, 0, 'C', 1) 
        pdf.ln()

        # 3. Imprimir Filas de la Tabla
        pdf.set_fill_color(240, 240, 240) 
        pdf.set_text_color(0)
        pdf.set_font('Arial', '', 8)
        relleno = False 
        
        for index, row in df_imprimir.iterrows():
            # Añadir página si no cabe la fila
            if pdf.get_y() > (pdf.h - 30):
                pdf.add_page()
                # Reimprimir encabezado
                pdf.set_fill_color(0, 128, 0) 
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Arial', 'B', 8)
                for i, header in enumerate(nombres_columnas):
                    pdf.cell(ancho_columna[i], 7, sanitizar_texto(header), 1, 0, 'C', 1)
                pdf.ln()
                # Restablecer colores de fila
                pdf.set_fill_color(240, 240, 240) 
                pdf.set_text_color(0)
                pdf.set_font('Arial', '', 8)
                relleno = False

            # Imprimir celdas de la fila
            for i, col in enumerate(columnas_visibles):
                valor = str(row[col])
                align = 'L' # Alineación por defecto
                
                # ✅ LÓGICA DE ALINEACIÓN MEJORADA
                # Columnas de texto
                if col in ['descripcion', 'producto', 'nombre_cliente', 'categoria', 'accion_sugerida']:
                    align = 'L'
                # Columnas de IDs
                elif col in ['id_articulo']:
                    align = 'C'
                # Columnas numéricas (enteros)
                elif col in ['cant_inventario', 'cantidad', 'stock_actual', 'demanda_predicha_mes', 'punto_reorden', 'sugerencia_cantidad']:
                    align = 'C'
                # Columnas de moneda
                elif col.startswith('precio_') or col.endswith('total') or col.endswith('unitario'):
                    try:
                        valor_num = float(valor.replace(',', '').replace('$', '')) if valor else 0.0
                        valor = f"USD {valor_num:,.2f}"
                    except ValueError:
                        valor = valor # Dejar como texto si no es número
                    align = 'R'
                
                valor_sanitizado = sanitizar_texto(valor)
                pdf.cell(ancho_columna[i], 6, valor_sanitizado, 1, 0, align, relleno)
            
            pdf.ln()
            relleno = not relleno
        
        # 4. Guardar
        pdf.output(file_path)
        
    except Exception as e:
        # Imprimir el traceback completo en la consola para depuración
        import traceback
        traceback.print_exc()
        raise Exception(f"Error al generar el PDF: {e}")