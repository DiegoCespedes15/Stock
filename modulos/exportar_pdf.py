# Archivo: src/reportes/export_pdf.py
from fpdf import FPDF, XPos, YPos
import pandas as pd
from datetime import datetime

class PDF(FPDF):
    """Clase personalizada para el PDF con encabezados y pies de página."""
    def __init__(self, tipo_reporte, filtros):
        super().__init__('L' if tipo_reporte == 'Ventas' else 'P', 'mm', 'A4')
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
        
        # Imprimir filtros en una línea
        self.set_x(self.l_margin)
        for i, info in enumerate(info_filtro):
            self.cell(ancho_pagina / len(info_filtro), 6, info, border=1, align='C', fill=True, new_x=XPos.RIGHT)
        
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
        """
        Codifica y decodifica el texto a latin-1 para soportar tildes y ñ con Arial,
        y elimina caracteres que causan el error de encoding (como el •).
        """
        if texto is None:
            return ''
        texto = str(texto).replace('•', '') 
        return texto.encode('latin-1', 'replace').decode('latin-1')

    try:
        pdf = PDF(tipo_reporte, filtros)
        pdf.alias_nb_pages()
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 10)
        
        if 'descripcion' in df_reporte.columns:
            df_reporte['descripcion'] = df_reporte['descripcion'].astype(str).str.slice(0, 50) + \
                                        df_reporte['descripcion'].astype(str).apply(lambda x: '...' if len(x) > 50 else '')

        # 1. Preprocesar y definir columnas visibles y anchos
        if tipo_reporte == "Inventario":
            columnas_visibles = ['id_articulo', 'descripcion', 'categoria', 'cant_inventario', 'precio_unit']
            
            # Encabezados para el PDF
            nombres_columnas = ['ID', 'Descripción', 'Categoría', 'Stock Actual', 'P. Unitario (USD)']
            ancho_columna = [20, 89, 35, 20, 25] 
            
        elif tipo_reporte == "Ventas":
            columnas_visibles = ['fecha_venta', 'producto', 'nombre_cliente', 'cantidad', 'monto_unitario', 'monto_total']
            nombres_columnas = ['Fecha', 'Producto', 'Cliente', 'Cantidad', 'P. Unit. (USD)', 'Total Venta (USD)'] # Cambiado de $ a USD
            ancho_columna = [30, 95, 70, 20, 30, 30] 
            
            
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

                # 1. Reimprimir encabezado de tabla
                pdf.set_fill_color(0, 128, 0) 
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Arial', 'B', 8)
                for i, header in enumerate(nombres_columnas):
                    pdf.cell(ancho_columna[i], 7, sanitizar_texto(header), 1, 0, 'C', 1)
                pdf.ln()

                # 2. RESTABLECER LA CONFIGURACIÓN DE FILAS
                pdf.set_fill_color(240, 240, 240) 
                pdf.set_text_color(0)
                pdf.set_font('Arial', '', 8)
                relleno = False

            for i, col in enumerate(columnas_visibles):
                valor = str(row[col])
                
                # Formato especial para moneda o números
                if col.startswith('precio_') or col.endswith('total') or col.endswith('unitario'):
                    valor_num = float(valor.replace(',', '').replace('$', '')) if valor else 0.0
                    valor = f"USD {valor_num:,.2f}"
                    align = 'R'
                elif col.startswith('cant_') or col.startswith('v_id'):
                    align = 'C'
                else:
                    align = 'L'
                    
                valor_sanitizado = sanitizar_texto(valor)
                    
                pdf.cell(ancho_columna[i], 6, valor_sanitizado, 1, 0, align, relleno)
            pdf.ln()
            relleno = not relleno
        
        # 4. Guardar
        pdf.output(file_path)
        
    except Exception as e:
        raise Exception(f"Error al generar el PDF: {e}")