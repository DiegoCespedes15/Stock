# historial_alertas.py
import customtkinter as ctk
from bd import conectar_db
import threading
import tkinter as tk
from datetime import datetime
#from modulos.alertas import mostrar_alertas

def mostrar_historial_alertas(contenido_frame):
    """Muestra el historial de alertas en un hilo separado."""
    
    limpiar_contenido(contenido_frame)
    
    # Título y subtítulo
    ctk.CTkLabel(
        contenido_frame, 
        text="Historial de Alertas",
        font=("Arial", 20, "bold")
    ).pack(pady=(20, 5))
    
    ctk.CTkLabel(
        contenido_frame,
        text="Aquí puedes ver todas las alertas, incluyendo las resueltas y las leídas.",
        font=("Arial", 12),
        text_color="#555"
    ).pack(pady=(0, 20))
    
    # Botón de volver
    btn_volver = ctk.CTkButton(
        contenido_frame,
        text="⬅️ Volver a Alertas Vigentes",
        command=lambda: mostrar_alertas(contenido_frame),
        font=("Arial", 12),
        fg_color="#8e44ad",
        hover_color="#7e329d",
        width=220
    )
    btn_volver.pack(pady=10)
    
    # Mostrar mensaje de carga mientras se obtienen los datos
    loading_label = ctk.CTkLabel(
        contenido_frame,
        text="⏳ Cargando historial...",
        font=("Arial", 14, "italic"),
        text_color="#3498db"
    )
    loading_label.pack(pady=50)

    # Iniciar la tarea de carga en un hilo de ejecución
    hilo_historial = threading.Thread(
        target=lambda: _obtener_y_mostrar_historial(contenido_frame, loading_label),
        daemon=True
    )
    hilo_historial.start()

def _obtener_y_mostrar_historial(contenido_frame, loading_label):
    """
    Función que se ejecuta en el hilo secundario para obtener los datos.
    """
    alertas_historial = obtener_todas_las_alertas()
    
    # Después de obtener los datos, programar la actualización de la UI
    # en el hilo principal usando el método .after().
    contenido_frame.after(
        0, 
        lambda: _mostrar_datos_en_ui(contenido_frame, loading_label, alertas_historial)
    )

def _mostrar_datos_en_ui(contenido_frame, loading_label, alertas_historial):
    """
    Función que se ejecuta en el hilo principal para construir la UI con los datos.
    """
    # Eliminar el mensaje de carga
    loading_label.destroy()
    
    # Crear un contenedor con scroll
    historial_scroll_frame = ctk.CTkScrollableFrame(contenido_frame, fg_color="transparent")
    historial_scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

    if not alertas_historial:
        ctk.CTkLabel(
            historial_scroll_frame,
            text="🔍 No hay historial de alertas para mostrar.",
            font=("Arial", 14),
            text_color="#7f8c8d"
        ).pack(pady=50)
        return

    # Mostrar cada alerta en la lista
    for alerta in alertas_historial:
        crear_linea_historial(historial_scroll_frame, alerta)

def crear_linea_historial(parent, alerta):
    """Crea una línea de alerta para la vista de historial."""
    id_alerta, descripcion, stock_actual, stock_minimo, nivel, estado, fecha_alerta = alerta
    
    if estado == 'RESUELTA':
        color = "#2ecc71"
        icono = "✔️"
        estado_texto = "Resuelta"
    elif estado == 'ACTIVA':
        if nivel == "AGOTADO":
            color = "#e74c3c"
            icono = "🛑"
        elif nivel == "CRITICO":
            color = "#f39c12"
            icono = "⚠️"
        else: # BAJO
            color = "#f1c40f"
            icono = "🔸"
        estado_texto = "Activa"
    else:
        color = "#7f8c8d"
        icono = "❓"
        estado_texto = "Desconocida"
    
    alerta_frame = ctk.CTkFrame(
        parent, 
        fg_color="#f8f9fa",
        border_width=1,
        border_color=color,
        corner_radius=8
    )
    alerta_frame.pack(pady=5, fill="x", padx=5)
    
    info_text = f"{icono} {descripcion} | Stock: {stock_actual} | Mínimo: {stock_minimo} | Estado: {estado_texto} | Fecha: {fecha_alerta.strftime('%d/%m/%Y %H:%M')}"
    
    ctk.CTkLabel(
        alerta_frame,
        text=info_text,
        font=("Arial", 11),
        text_color=color,
        justify="left"
    ).pack(pady=8, padx=10, fill="x")

def obtener_todas_las_alertas():
    """Obtiene todas las alertas desde la base de datos."""
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.id_alerta, a.descripcion_producto, a.stock_actual, 
                   a.stock_minimo, a.nivel_alerta, a.estado, a.fecha_alerta
            FROM desarrollo.alertas_stock a
            ORDER BY a.fecha_alerta DESC
        """)
        
        alertas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return alertas
        
    except Exception as e:
        print(f"Error al obtener historial de alertas: {e}")
        return []

def limpiar_contenido(contenido_frame):
    """Limpia el contenido del frame."""
    for widget in contenido_frame.winfo_children():
        widget.destroy()

