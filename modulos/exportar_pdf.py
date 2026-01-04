from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import pandas as pd

def exportar_a_pdf(df_reporte: pd.DataFrame, file_path: str, tipo_reporte: str, filtros: dict):
    """
    Genera un PDF profesional con ajuste de texto automático usando ReportLab.
    """
    try:
        # 1. Configuración de página (A4 Horizontal para reportes anchos)
        doc = SimpleDocTemplate(
            file_path, 
            pagesize=landscape(A4), 
            rightMargin=10*mm, leftMargin=10*mm, 
            topMargin=15*mm, bottomMargin=15*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # --- ESTILOS DE TEXTO ---
        estilo_titulo = ParagraphStyle(
            'TituloReporte',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=10
        )
        
        estilo_celda_texto = ParagraphStyle(
            'CeldaTexto',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_LEFT
        )
        
        estilo_celda_centro = ParagraphStyle(
            'CeldaCentro',
            parent=estilo_celda_texto,
            alignment=TA_CENTER
        )

        # 2. ENCABEZADO
        elements.append(Paragraph(f"REPORTE DE {tipo_reporte.upper()}", estilo_titulo))

        # 3. METADATOS
        fecha_gen = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        info_texto = f"<b>Generado:</b> {fecha_gen} | <b>Categoría:</b> {filtros.get('categoria', 'Todas')}"
        
        # Agregamos info extra si es EOQ
        if "EOQ" in tipo_reporte or "Optimización" in tipo_reporte:
            sim_date = filtros.get('simulado_en', filtros.get('fecha_simulada', 'Hoy'))
            info_texto += f" | <b>Simulado al:</b> {sim_date}"

        meta_table = Table([[Paragraph(info_texto, styles['Normal'])]], colWidths=[270*mm])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('BOX', (0, 0), (-1, -1), 1, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # 4. DEFINICIÓN DE COLUMNAS (MAPPING)
        # Aquí definimos qué columnas del DF queremos ver y con qué título
        
        anchos = []
        columnas_mapping = {} # Clave: Columna en DF, Valor: Título en PDF
        aligns = []

        # CASO A: INVENTARIO SIMPLE
        if tipo_reporte == "Inventario":
            columnas_mapping = {
                'id_articulo': 'ID', 'descripcion': 'Descripción', 'categoria': 'Categoría',
                'cant_inventario': 'Stock', 'precio_unit': 'P. Unit'
            }
            anchos = [20*mm, 100*mm, 40*mm, 25*mm, 30*mm]
            aligns = ['C', 'L', 'C', 'C', 'R']

        # CASO B: VENTAS
        elif tipo_reporte == "Ventas":
            columnas_mapping = {
                'fecha_venta': 'Fecha', 'producto': 'Producto', 'nombre_cliente': 'Cliente',
                'cantidad': 'Cant', 'monto_unitario': 'P. Unit', 'monto_total': 'Total'
            }
            anchos = [30*mm, 80*mm, 60*mm, 20*mm, 30*mm, 30*mm]
            aligns = ['C', 'L', 'L', 'C', 'R', 'R']
            
        # CASO C: OPTIMIZACIÓN (EOQ) - ✅ AQUÍ ESTABA EL ERROR
        # Usamos 'in' por si el título varía ligeramente
        elif "EOQ" in tipo_reporte or "Optimización" in tipo_reporte:
            # Las claves (izquierda) deben coincidir con las columnas que genera inventory_optimizer.py
            columnas_mapping = {
                "ID": "ID",
                "Descripción": "Descripción",
                "Categoría": "Categoría",
                "Stock Actual": "Stock",
                "Prob. Venta (30d)": "Prob. %",       # Nueva columna
                "Inv. Proyectado": "Proyección",      # Nueva columna
                "Punto Reorden": "Reorden",
                "Acción Sugerida": "Acción Sugerida",
                "Cant. a Comprar": "Comprar"
            }
            # Ajustamos anchos para que quepa todo (Total ~275mm)
            anchos = [15*mm, 65*mm, 35*mm, 20*mm, 20*mm, 25*mm, 20*mm, 50*mm, 20*mm]
            aligns = ['C', 'L', 'C', 'C', 'C', 'C', 'C', 'L', 'C']

        # CASO D: FALLBACK (Por si el nombre no coincide, calculamos automático)
        else:
            print(f"⚠️ Aviso: Tipo de reporte '{tipo_reporte}' no reconocido. Usando formato genérico.")
            # Usamos todas las columnas del DF
            cols = list(df_reporte.columns)
            columnas_mapping = {c: c for c in cols}
            # Dividimos el ancho disponible entre el número de columnas
            ancho_total = 270 * mm
            anchos = [ancho_total / len(cols)] * len(cols)
            aligns = ['L'] * len(cols)

        # 5. CONSTRUCCIÓN DE DATA
        data = []
        
        # A. Cabeceras
        headers = [Paragraph(f"<b>{title}</b>", estilo_celda_centro) for title in columnas_mapping.values()]
        data.append(headers)

        # B. Filas
        claves_df = list(columnas_mapping.keys())
        
        for _, row in df_reporte.iterrows():
            fila_procesada = []
            for idx, col_key in enumerate(claves_df):
                # Usamos .get() para evitar errores si falta una columna
                valor = row.get(col_key, '')
                
                # Formateo visual
                if 'precio' in col_key.lower() or 'monto' in col_key.lower():
                    try: valor = f"${float(valor):,.2f}"
                    except: pass
                
                # Estilo según alineación
                estilo = estilo_celda_texto if aligns[idx] == 'L' else estilo_celda_centro
                
                # Crear Paragraph
                fila_procesada.append(Paragraph(str(valor), estilo))
            
            data.append(fila_procesada)

        # 6. TABLA FINAL
        # Verificación final de seguridad
        if not anchos or len(anchos) != len(data[0]):
             # Si falló la lógica, regeneramos anchos automáticos
             anchos = [(270*mm) / len(data[0])] * len(data[0])

        tabla_datos = Table(data, colWidths=anchos, repeatRows=1)
        
        estilo_tabla = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006400")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ])

        # Coloreado Semáforo para EOQ
        if "EOQ" in tipo_reporte or "Optimización" in tipo_reporte:
            # Buscamos en qué índice quedó la columna "Acción Sugerida"
            idx_accion = -1
            claves_lista = list(columnas_mapping.keys())
            if "Acción Sugerida" in claves_lista:
                idx_accion = claves_lista.index("Acción Sugerida")

            if idx_accion != -1:
                for i, row_data in enumerate(data[1:], start=1):
                    # row_data[idx_accion] es un Paragraph, obtenemos su texto
                    texto_accion = row_data[idx_accion].text
                    
                    bg = colors.white
                    if "URGENTE" in texto_accion or "Quiebre" in texto_accion:
                        bg = colors.HexColor("#ffcccc") # Rojo Alerta
                    elif "Exceso" in texto_accion:
                        bg = colors.HexColor("#fff3cd") # Amarillo
                    elif "Saludable" in texto_accion:
                        bg = colors.HexColor("#d4edda") # Verde
                    
                    estilo_tabla.add('BACKGROUND', (0, i), (-1, i), bg)

        tabla_datos.setStyle(estilo_tabla)
        elements.append(tabla_datos)

        doc.build(elements)
        print(f"✅ PDF Generado: {file_path}")

    except Exception as e:
        print(f"❌ Error en PDF: {e}")
        import traceback
        traceback.print_exc()
        raise e