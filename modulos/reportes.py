# Archivo: src/modulos/reportes.py

import customtkinter as ctk
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from datetime import datetime
from bd import conectar_db 
from predictor import cargar_modelo, predecir_ventas_anuales 
from .reportes_graficos import generar_grafico_prediccion, generar_reporte_historico 


def mostrar_modulo_reportes(contenido_frame):
    """Muestra la interfaz de usuario con tres secciones de filtros."""
    
    # Limpiar el frame anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()

    ctk.CTkLabel(contenido_frame, text="Módulo de Reportes", font=("Arial", 20, "bold")).pack(pady=20)

    # --- Sección de Reportes Históricos (STOCK) ---
    historial_frame = ctk.CTkFrame(contenido_frame)
    historial_frame.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(historial_frame, text="Reporte Histórico de Stock", font=("Arial", 16, "bold")).pack(pady=10)

    historial_filtros_frame = ctk.CTkFrame(historial_frame)
    historial_filtros_frame.pack(pady=5, padx=5)

    ctk.CTkLabel(historial_filtros_frame, text="ID Producto:", font=("Arial", 12)).pack(side="left", padx=5)
    hist_id_producto_entry = ctk.CTkEntry(historial_filtros_frame)
    hist_id_producto_entry.pack(side="left", padx=5)

    ctk.CTkLabel(historial_filtros_frame, text="Categoría:", font=("Arial", 12)).pack(side="left", padx=5)
    hist_categoria_entry = ctk.CTkEntry(historial_filtros_frame)
    hist_categoria_entry.pack(side="left", padx=5)

    ctk.CTkLabel(historial_filtros_frame, text="Fecha Inicio (YYYY-MM-DD):", font=("Arial", 12)).pack(side="left", padx=5)
    hist_fecha_inicio_entry = ctk.CTkEntry(historial_filtros_frame)
    hist_fecha_inicio_entry.pack(side="left", padx=5)

    ctk.CTkLabel(historial_filtros_frame, text="Fecha Fin (YYYY-MM-DD):", font=("Arial", 12)).pack(side="left", padx=5)
    hist_fecha_fin_entry = ctk.CTkEntry(historial_filtros_frame)
    hist_fecha_fin_entry.pack(side="left", padx=5)

    historial_botones_frame = ctk.CTkFrame(historial_frame)
    historial_botones_frame.pack(pady=10)

    btn_historial = ctk.CTkButton(
        historial_botones_frame,
        text="Generar Reporte Histórico",
        command=lambda: generar_reporte_historico_ui(
            hist_id_producto_entry.get(),
            hist_categoria_entry.get(),
            hist_fecha_inicio_entry.get(),
            hist_fecha_fin_entry.get()
        )
    )
    btn_historial.pack(side="left", padx=5)
    
    # --- Sección de Reportes de VENTAS ---
    ventas_frame = ctk.CTkFrame(contenido_frame)
    ventas_frame.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(ventas_frame, text="Reporte de Ventas", font=("Arial", 16, "bold")).pack(pady=10)

    ventas_filtros_frame = ctk.CTkFrame(ventas_frame)
    ventas_filtros_frame.pack(pady=5, padx=5)
    
    ctk.CTkLabel(ventas_filtros_frame, text="ID Producto:", font=("Arial", 12)).pack(side="left", padx=5)
    ventas_id_producto_entry = ctk.CTkEntry(ventas_filtros_frame)
    ventas_id_producto_entry.pack(side="left", padx=5)
    
    ctk.CTkLabel(ventas_filtros_frame, text="Categoría:", font=("Arial", 12)).pack(side="left", padx=5)
    ventas_categoria_entry = ctk.CTkEntry(ventas_filtros_frame)
    ventas_categoria_entry.pack(side="left", padx=5)

    ctk.CTkLabel(ventas_filtros_frame, text="Fecha Inicio (YYYY-MM-DD):", font=("Arial", 12)).pack(side="left", padx=5)
    ventas_fecha_inicio_entry = ctk.CTkEntry(ventas_filtros_frame)
    ventas_fecha_inicio_entry.pack(side="left", padx=5)

    ctk.CTkLabel(ventas_filtros_frame, text="Fecha Fin (YYYY-MM-DD):", font=("Arial", 12)).pack(side="left", padx=5)
    ventas_fecha_fin_entry = ctk.CTkEntry(ventas_filtros_frame)
    ventas_fecha_fin_entry.pack(side="left", padx=5)
    
    ventas_botones_frame = ctk.CTkFrame(ventas_frame)
    ventas_botones_frame.pack(pady=10)

    btn_ventas = ctk.CTkButton(
        ventas_botones_frame,
        text="Generar Reporte de Ventas",
        command=lambda: generar_reporte_ventas_ui(
            ventas_id_producto_entry.get(),
            ventas_categoria_entry.get(),
            ventas_fecha_inicio_entry.get(),
            ventas_fecha_fin_entry.get()
        )
    )
    btn_ventas.pack(side="left", padx=5)

    # Botones de exportación (se mantienen, asociados a los filtros de ventas)
    btn_exportar_excel = ctk.CTkButton(
        ventas_botones_frame,
        text="Exportar a Excel",
        command=lambda: exportar_a_excel(
            ventas_id_producto_entry.get(),
            ventas_categoria_entry.get(),
            ventas_fecha_inicio_entry.get(),
            ventas_fecha_fin_entry.get()
        )
    )
    btn_exportar_excel.pack(side="left", padx=5)

    btn_exportar_pdf = ctk.CTkButton(
        ventas_botones_frame,
        text="Exportar a PDF",
        command=lambda: exportar_a_pdf(
            ventas_id_producto_entry.get(),
            ventas_categoria_entry.get(),
            ventas_fecha_inicio_entry.get(),
            ventas_fecha_fin_entry.get()
        )
    )
    btn_exportar_pdf.pack(side="left", padx=5)

    # --- Sección de Reporte de Predicción ---
    prediccion_frame = ctk.CTkFrame(contenido_frame)
    prediccion_frame.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(prediccion_frame, text="Reporte de Predicción (Ventas Futuras)", font=("Arial", 16, "bold")).pack(pady=10)

    prediccion_filtros_frame = ctk.CTkFrame(prediccion_frame)
    prediccion_filtros_frame.pack(pady=5, padx=5)

    # Widgets de entrada
    ctk.CTkLabel(prediccion_filtros_frame, text="ID Producto:", font=("Arial", 12)).pack(side="left", padx=5)
    pred_id_producto_entry = ctk.CTkEntry(prediccion_filtros_frame)
    pred_id_producto_entry.pack(side="left", padx=5)

    ctk.CTkLabel(prediccion_filtros_frame, text="Año a Predecir:", font=("Arial", 12)).pack(side="left", padx=5)
    pred_anio_entry = ctk.CTkEntry(prediccion_filtros_frame) 
    pred_anio_entry.insert(0, str(datetime.now().year + 1))
    pred_anio_entry.pack(side="left", padx=5)

    # Botones de Predicción
    prediccion_botones_frame = ctk.CTkFrame(prediccion_frame)
    prediccion_botones_frame.pack(pady=10)

    btn_predecir = ctk.CTkButton(
        prediccion_botones_frame,
        text="Generar Gráfico de Predicción",
        command=lambda: generar_reporte_prediccion_ui(
            pred_id_producto_entry.get(),
            pred_anio_entry.get()
        )
    )
    btn_predecir.pack(side="left", padx=5)



    # --- Sección de Reporte de Predicción ---
    prediccion_frame = ctk.CTkFrame(contenido_frame) # << AHORA SÍ CONOCE 'contenido_frame'
    prediccion_frame.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(prediccion_frame, text="Reporte de Predicción (Ventas Futuras)", font=("Arial", 16, "bold")).pack(pady=10)

    prediccion_filtros_frame = ctk.CTkFrame(prediccion_frame)
    prediccion_filtros_frame.pack(pady=5, padx=5)

    # Widgets de entrada
    ctk.CTkLabel(prediccion_filtros_frame, text="ID Producto:", font=("Arial", 12)).pack(side="left", padx=5)
    pred_id_producto_entry = ctk.CTkEntry(prediccion_filtros_frame)
    pred_id_producto_entry.pack(side="left", padx=5)

    ctk.CTkLabel(prediccion_filtros_frame, text="Año a Predecir:", font=("Arial", 12)).pack(side="left", padx=5)
    pred_anio_entry = ctk.CTkEntry(prediccion_filtros_frame) 
    pred_anio_entry.insert(0, str(datetime.now().year + 1))
    pred_anio_entry.pack(side="left", padx=5)

    # Botones de Predicción
    prediccion_botones_frame = ctk.CTkFrame(prediccion_frame)
    prediccion_botones_frame.pack(pady=10)

    btn_predecir = ctk.CTkButton(
        prediccion_botones_frame,
        text="Generar Gráfico de Predicción",
        # El command llama a la función de lógica con los valores de los Entry
        command=lambda: generar_reporte_prediccion_ui(
            pred_id_producto_entry.get(),
            pred_anio_entry.get()
        )
    )
    btn_predecir.pack(side="left", padx=5)

    # Contenedor para los botones
    prediccion_botones_frame = ctk.CTkFrame(prediccion_frame)
    prediccion_botones_frame.pack(pady=10)

    # El botón que inicia todo el proceso de ML
    btn_predecir = ctk.CTkButton(
        prediccion_botones_frame,
        text="Generar Gráfico de Predicción",
        command=lambda: generar_reporte_prediccion_ui(
            pred_id_producto_entry.get(),
            pred_anio_entry.get()
        )
    )
    btn_predecir.pack(side="left", padx=5)

# --- Lógica de la funcionalidad ---

def mostrar_reporte_stock_ui(contenido_frame):
    """
    Muestra la interfaz para generar un reporte de stock con filtros.
    """
    # Limpiar el frame anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()

    ctk.CTkLabel(contenido_frame, text="Reporte Histórico de Stock", font=("Arial", 20, "bold")).pack(pady=20)

    # Contenedor para los filtros
    filtros_frame = ctk.CTkFrame(contenido_frame)
    filtros_frame.pack(pady=10, padx=10, fill="x")

    # Campos de filtrado
    ctk.CTkLabel(filtros_frame, text="ID Producto:", font=("Arial", 12)).pack(side="left", padx=5)
    id_producto_entry = ctk.CTkEntry(filtros_frame)
    id_producto_entry.pack(side="left", padx=5)

    ctk.CTkLabel(filtros_frame, text="Categoría:", font=("Arial", 12)).pack(side="left", padx=5)
    categoria_entry = ctk.CTkEntry(filtros_frame)
    categoria_entry.pack(side="left", padx=5)

    ctk.CTkLabel(filtros_frame, text="Fecha Inicio (YYYY-MM-DD):", font=("Arial", 12)).pack(side="left", padx=5)
    fecha_inicio_entry = ctk.CTkEntry(filtros_frame)
    fecha_inicio_entry.pack(side="left", padx=5)

    ctk.CTkLabel(filtros_frame, text="Fecha Fin (YYYY-MM-DD):", font=("Arial", 12)).pack(side="left", padx=5)
    fecha_fin_entry = ctk.CTkEntry(filtros_frame)
    fecha_fin_entry.pack(side="left", padx=5)

    # Botón para generar el reporte
    btn_generar = ctk.CTkButton(
        contenido_frame,
        text="Generar Gráfico de Historial de Stock",
        command=lambda: generar_reporte_stock(
            id_producto_entry.get(),
            categoria_entry.get(),
            fecha_inicio_entry.get(),
            fecha_fin_entry.get()
        )
    )
    btn_generar.pack(pady=10)

def generar_reporte_stock(producto_id, categoria, fecha_inicio, fecha_fin):
    """
    Obtiene los datos de stock y llama a la función de graficación.
    """
    try:
        engine = conectar_db()
        if not engine:
            return

        # Construir la consulta SQL con un JOIN y filtros
        sql_query = f"""
            SELECT m.fecha, m.id_articulo, m.tipo_movimiento, s.categoria
            FROM desarrollo.movimientos m
            JOIN desarrollo.stock s ON m.id_articulo = s.id_articulo
        """
        where_conditions = []
        if producto_id:
            where_conditions.append(f"m.id_articulo = '{producto_id}'")
        if categoria:
            where_conditions.append(f"s.categoria LIKE '%{categoria}%'")
        if fecha_inicio:
            where_conditions.append(f"m.fecha >= '{fecha_inicio}'")
        if fecha_fin:
            where_conditions.append(f"m.fecha <= '{fecha_fin}'")

        if where_conditions:
            sql_query += " WHERE " + " AND ".join(where_conditions)
            
        df_movimientos = pd.read_sql(sql_query, engine)
        
        if df_movimientos.empty:
            messagebox.showinfo("Reporte", "No se encontraron datos para los filtros seleccionados.")
            return

        # Convertir la columna de fecha a tipo datetime y agrupar
        df_movimientos['fecha'] = pd.to_datetime(df_movimientos['fecha'])
        df_agregado = df_movimientos.groupby(['fecha', 'id_articulo', 'tipo_movimiento']).size().reset_index(name='conteo')

        # Pasar el DataFrame al módulo de gráficos
        generar_reporte_historico(df_agregado, producto_id, categoria)
        messagebox.showinfo("Reporte Generado", "El reporte histórico de stock se ha generado y guardado en un archivo.")

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al generar el reporte: {e}")

def obtener_datos_reporte(producto_id, categoria, fecha_inicio, fecha_fin, tabla='ventas'):
    """
    Función que conecta a la BD y obtiene datos de la tabla de ventas o stock
    según los filtros, usando el operador LIKE para la categoría.
    """
    try:
        conn = conectar_db()
        
        # Construir la consulta SQL dinámicamente
        sql_query = f"""
            SELECT v.v_fecha, v.v_id_producto, v.v_product, v.v_cantidad, s.categoria
            FROM desarrollo.ventas v
            LEFT JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo
        """
        where_conditions = []
        if producto_id:
            where_conditions.append(f"v.v_id_producto = '{producto_id}'")
        if categoria:
            # CAMBIO CLAVE: Usamos LIKE para la búsqueda flexible
            where_conditions.append(f"s.categoria LIKE '%{categoria}%'")
        if fecha_inicio:
            where_conditions.append(f"v.v_fecha >= '{fecha_inicio}'")
        if fecha_fin:
            where_conditions.append(f"v.v_fecha <= '{fecha_fin}'")

        if where_conditions:
            sql_query += " WHERE " + " AND ".join(where_conditions)
            
        df = pd.read_sql(sql_query, conn)
        conn.close()
        return df
    except Exception as e:
        messagebox.showerror("Error de base de datos", f"Error al obtener datos: {e}")
        return pd.DataFrame()

def generar_reporte_historico_ui(producto_id, categoria, fecha_inicio, fecha_fin):
    """
    Genera el reporte histórico y llama a la función de graficación.
    """
    df_datos = obtener_datos_reporte(producto_id, categoria, fecha_inicio, fecha_fin)
    if not df_datos.empty:
        # Sumar la cantidad de ventas por fecha para el gráfico
        df_agregado = df_datos.groupby('v_fecha').agg(
            cantidad_total=('v_cantidad', 'sum')
        ).reset_index()
        generar_reporte_historico(producto_id=producto_id, categoria=categoria, df_datos=df_agregado)
        messagebox.showinfo("Reporte Generado", "El reporte histórico se ha generado y guardado en un archivo.")
    else:
        messagebox.showinfo("Reporte", "No se encontraron datos para los filtros seleccionados.")

# NUEVA FUNCIÓN PARA EL REPORTE DE VENTAS
def generar_reporte_ventas_ui(producto_id, fecha_inicio, fecha_fin):
    """
    Genera un reporte de ventas detallado.
    """
    df_datos = obtener_datos_reporte(producto_id, None, fecha_inicio, fecha_fin)
    if not df_datos.empty:
        print("Datos del reporte de ventas generados:")
        print(df_datos)
        messagebox.showinfo("Reporte de Ventas", f"Se encontraron {len(df_datos)} registros de ventas.")
    else:
        messagebox.showinfo("Reporte de Ventas", "No se encontraron datos para los filtros seleccionados.")


def exportar_a_excel(producto_id, categoria, fecha_inicio, fecha_fin):
    """Exporta los datos filtrados a un archivo de Excel."""
    df_datos = obtener_datos_reporte(producto_id, categoria, fecha_inicio, fecha_fin)
    if not df_datos.empty:
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            try:
                df_datos.to_excel(file_path, index=False)
                messagebox.showinfo("Exportar a Excel", "Datos exportados correctamente.")
            except Exception as e:
                messagebox.showerror("Error de Exportación", f"No se pudo exportar a Excel: {e}")
    else:
        messagebox.showinfo("Exportar a Excel", "No hay datos para exportar.")


def exportar_a_pdf(producto_id, categoria, fecha_inicio, fecha_fin):
    """Exporta los datos filtrados a un archivo PDF."""
    try:
        from fpdf import FPDF
    except ImportError:
        messagebox.showerror("Librería FPDF no encontrada", "Por favor, instala 'fpdf2' usando: pip install fpdf2")
        return

    df_datos = obtener_datos_reporte(producto_id, categoria, fecha_inicio, fecha_fin)
    if not df_datos.empty:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Reporte de Ventas", ln=True, align="C")
        pdf.ln(10)

        # Lógica para añadir la tabla de datos al PDF
        for index, row in df_datos.iterrows():
            pdf.cell(0, 10, f"Fecha: {row['v_fecha']} | Producto: {row['v_product']} | Cantidad: {row['v_cantidad']}", ln=True)

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if file_path:
            pdf.output(file_path)
            messagebox.showinfo("Exportar a PDF", "Datos exportados correctamente.")
    else:
        messagebox.showinfo("Exportar a PDF", "No hay datos para exportar.")
        
        
        
def generar_reporte_prediccion_ui(producto_id, anio_prediccion):
    """
    Función de interfaz que orquesta la carga del modelo, la predicción de ventas
    futuras y la generación del gráfico.
    """
    if not producto_id or not anio_prediccion:
        messagebox.showwarning("Faltan datos", "Por favor, ingrese el ID del Producto y el Año a predecir.")
        return

    try:
        # 1. Cargar el modelo
        modelo = cargar_modelo()
        if modelo is None:
            messagebox.showerror("Error", "No se pudo cargar el modelo de predicción. Asegúrate de que exista 'modelo_xgboost.pkl'.")
            return

        # 2. Generar la proyección de datos (llamada a predictor.py)
        predicciones_df = predecir_ventas_anuales(modelo, int(producto_id), int(anio_prediccion))

        if predicciones_df.empty:
            messagebox.showinfo("Reporte", "No se pudieron generar predicciones (Modelo o datos no válidos).")
            return

        # 3. Generar el gráfico y guardarlo como imagen
        # La función generar_grafico_prediccion guarda el archivo y devuelve el nombre
        nombre_archivo = generar_grafico_prediccion(predicciones_df, producto_id)

        # 4. Mostrar confirmación
        messagebox.showinfo("Éxito", f"Gráfico de predicción generado y guardado como: {nombre_archivo}")
        
        # Opcional: Aquí puedes añadir la lógica para cargar y mostrar el PNG
        # en tu contenido_frame.

    except ValueError:
        messagebox.showerror("Error de entrada", "El ID de Producto y el Año deben ser números enteros válidos.")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al predecir: {e}")

