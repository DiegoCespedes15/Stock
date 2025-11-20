# modulos/alertas.py
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from bd import conectar_db
import tkinter as tk  # Para el Canvas
import threading
from modulos.historial_alertas import mostrar_historial_alertas

def mostrar_alertas(contenido_frame):
    """Muestra el módulo de alertas vigentes"""
    limpiar_contenido(contenido_frame)
    
    # Título
    ctk.CTkLabel(
        contenido_frame, 
        text="Alertas Vigentes de Stock",
        font=("Arial", 20, "bold")
    ).pack(pady=20)
    
    # Frame de controles
    controles_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    controles_frame.pack(pady=10, fill="x", padx=20)
    
    # Botón de actualizar
    btn_actualizar = ctk.CTkButton(
        controles_frame,
        text="🔄 Actualizar Alertas",
        command=lambda: actualizar_alertas(contenido_frame),
        font=("Arial", 12),
        fg_color="#3498db",
        hover_color="#2980b9",
        width=180
    )
    btn_actualizar.pack(side="left", padx=5)
    
    
    # Botón de historial
    btn_historial = ctk.CTkButton(
        controles_frame,
        text="📊 Ver Historial",
        # Ahora llama a la función importada desde el otro archivo
        command=lambda: mostrar_historial_alertas(contenido_frame),
        font=("Arial", 12),
        fg_color="#9b59b6",
        hover_color="#8e44ad",
        width=150
    )
    btn_historial.pack(side="left", padx=5)
    
    # Mostrar alertas con scroll
    mostrar_alertas_vigentes(contenido_frame)

def mostrar_alertas_vigentes(contenido_frame):
    """Muestra las alertas vigentes en líneas con scroll"""
    # Frame contenedor principal
    main_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    main_frame.pack(pady=10, fill="both", expand=True, padx=20)
    main_frame._es_frame_alertas = True
    
    # Obtener alertas activas
    alertas = obtener_alertas_activas()
    
    if not alertas:
        # No hay alertas
        ctk.CTkLabel(
            main_frame,
            text="✅ No hay alertas vigentes en este momento",
            font=("Arial", 14),
            text_color="#27ae60"
        ).pack(pady=50)
        return main_frame
    
    # Título de sección
    ctk.CTkLabel(
        main_frame,
        text="🚨 Alertas Vigentes",
        font=("Arial", 16, "bold"),
        text_color="#e74c3c"
    ).pack(pady=10, anchor="w")
    
    # Contador por tipo
    agotado = sum(1 for a in alertas if a[4] == 'AGOTADO')
    critico = sum(1 for a in alertas if a[4] == 'CRITICO')
    bajo = sum(1 for a in alertas if a[4] == 'BAJO')
    
    ctk.CTkLabel(
        main_frame,
        text=f"🛑 Agotado: {agotado} | ⚠️ Crítico: {critico} | 🔸 Bajo: {bajo}",
        font=("Arial", 12),
        text_color="#2c3e50"
    ).pack(pady=5, anchor="w")
    
    # Frame para el scroll
    scroll_container = ctk.CTkFrame(main_frame, fg_color="transparent")
    scroll_container.pack(pady=10, fill="both", expand=True)
    
    # Canvas y scrollbar
    canvas = tk.Canvas(scroll_container, highlightthickness=0, bg='white')
    scrollbar = ctk.CTkScrollbar(scroll_container, orientation="vertical", command=canvas.yview)
    scrollable_frame = ctk.CTkFrame(canvas, fg_color="transparent")
    
    # Configurar el scroll
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Función para scroll con rueda del mouse
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    canvas.bind("<MouseWheel>", on_mousewheel)
    scrollable_frame.bind("<MouseWheel>", on_mousewheel)
    
    # Empaquetar canvas y scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Mostrar cada alerta en el frame scrollable
    for alerta in alertas:
        crear_linea_alerta(scrollable_frame, alerta)
    
    # Ajustar scroll al inicio
    canvas.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    
    return main_frame

def crear_linea_alerta(parent, alerta):
    """Crea una línea de alerta individual"""
    id_alerta, descripcion, stock_actual, stock_minimo, nivel, fecha_alerta = alerta
    
    # Determinar color según nivel
    if nivel == "AGOTADO":
        color = "#e74c3c"
        icono = "🛑"
    elif nivel == "CRITICO":
        color = "#f39c12"
        icono = "⚠️"
    else:
        color = "#f1c40f"
        icono = "🔸"
    
    # Frame de la alerta
    alerta_frame = ctk.CTkFrame(
        parent, 
        fg_color="#f8f9fa",
        border_width=1,
        border_color=color,
        corner_radius=8
    )
    alerta_frame.pack(pady=5, fill="x", padx=5)
    
    # Contenido en línea
    contenido_frame = ctk.CTkFrame(alerta_frame, fg_color="transparent")
    contenido_frame.pack(pady=8, padx=10, fill="x")
    
    # Información de la alerta
    info_text = f"{icono} {descripcion} | "
    info_text += f"Stock: {stock_actual} | Mínimo: {stock_minimo} | "
    info_text += f"{nivel} | {fecha_alerta.strftime('%d/%m/%Y %H:%M')}"
    
    info_label = ctk.CTkLabel(
        contenido_frame,
        text=info_text,
        font=("Arial", 11),
        text_color=color,
        justify="left"
    )
    info_label.pack(side="left", anchor="w")
    
    # Botón de marcar como leída
    btn_marcar = ctk.CTkButton(
        contenido_frame,
        text="✅ Marcar",
        width=80,
        height=25,
        fg_color=color,
        hover_color=color,
        font=("Arial", 10),
        command=lambda: marcar_alerta_leida(id_alerta, alerta_frame)
    )
    btn_marcar.pack(side="right", padx=5)

def marcar_alerta_leida(id_alerta, alerta_frame):
    """Marca una alerta como leída"""
    try:
        from services.alertas_service import servicio_alertas
        
        if servicio_alertas.marcar_alerta_vista(id_alerta):
            # Animación de desvanecimiento
            alerta_frame.configure(fg_color="#ecf0f1")
            alerta_frame.after(300, alerta_frame.destroy)
            messagebox.showinfo("Éxito", "Alerta marcada como leída")
        else:
            messagebox.showerror("Error", "No se pudo marcar la alerta")
    except Exception as e:
        messagebox.showerror("Error", f"Error al marcar alerta: {str(e)}")

def obtener_alertas_activas():
    """Obtiene alertas activas desde la base de datos"""
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.id_alerta, a.descripcion_producto, a.stock_actual, 
                   a.stock_minimo, a.nivel_alerta, a.fecha_alerta
            FROM desarrollo.alertas_stock a
            WHERE a.estado = 'ACTIVA'
            ORDER BY a.nivel_alerta DESC, a.fecha_alerta DESC
        """)
        
        alertas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return alertas
        
    except Exception as e:
        print(f"Error al obtener alertas: {e}")
        return []

def actualizar_alertas(contenido_frame):
    """
    1. Ejecuta el servicio de verificación de stock.
    2. Actualiza la vista de alertas.
    """
    try:
        # Importar el servicio de alertas aquí para evitar importaciones circulares al inicio del archivo
        from services.alertas_service import servicio_alertas

        # Paso 1: Ejecutar el servicio de verificación de stock
        alertas_creadas = servicio_alertas.verificar_nuevas_alertas()
        
        # Paso 2: Limpiar y recrear la vista de alertas
        # Encontrar y destruir el frame de alertas existente
        for widget in contenido_frame.winfo_children():
            if hasattr(widget, '_es_frame_alertas'):
                widget.destroy()
                break
        
        mostrar_alertas_vigentes(contenido_frame)

        # Mostrar mensaje de éxito
        if alertas_creadas > 0:
            messagebox.showinfo("Actualización Completa", 
                                f"✅ Se encontraron y mostraron {alertas_creadas} nuevas alertas.")
        else:
            messagebox.showinfo("Actualización Completa", 
                                "✅ No se encontraron nuevas alertas. La vista ha sido actualizada.")
            
    except Exception as e:
        messagebox.showerror("Error", f"❌ Error al actualizar las alertas: {str(e)}")
 
    
    
def limpiar_contenido(contenido_frame):
    """Limpia el contenido del frame"""
    for widget in contenido_frame.winfo_children():
        widget.destroy()