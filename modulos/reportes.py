# Archivo: src/reportes/report_ui.py


from tkinter import ttk, messagebox
import customtkinter as ctk


def mostrar_menu_reportes(contenido_frame):
    # Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()
    
    # Título del módulo
    ctk.CTkLabel(
        contenido_frame, 
        text="Módulo de Reportes",
        font=("Arial", 20, "bold")
    ).pack(pady=20)
    
    # Frame para los botones de opciones
    opciones_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    opciones_frame.pack(pady=30)
    
    # Botón de Reportes de Predicción de Ventas
    btn_salida = ctk.CTkButton(
        opciones_frame,
        text="Reportes de Predicción de Ventas",
        width=180,
        height=60,
        font=("Arial", 16),
        fg_color="#FF9100",
        hover_color="#E07B00",
        command=lambda: mostrar_reporte_prediccion(contenido_frame)
    )
    btn_salida.pack(side="left", padx=20)
    
    # Botón de Salida de Artículos
    btn_garantias = ctk.CTkButton(
        opciones_frame,
        text="Reportes varios",
        width=180,
        height=60,
        font=("Arial", 16),
        fg_color="#FF9100",
        hover_color="#E07B00",
        command=lambda: mostrar_reporte(contenido_frame)
    )
    btn_garantias.pack(side="left", padx=20)
    
    
    
def mostrar_reporte_prediccion(contenido_frame):
    # Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()
    
    # Título del módulo
    ctk.CTkLabel(
        contenido_frame, 
        text="Reportes de Predicción de Ventas",
        font=("Arial", 20, "bold")
    ).pack(pady=20)
    
    # Frame para los botones de opciones
    opciones_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    opciones_frame.pack(pady=30)
    
    
    
    
    
def mostrar_reporte(contenido_frame):
    # Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()
    
    # Título del módulo
    ctk.CTkLabel(
        contenido_frame, 
        text="Reportes varios",
        font=("Arial", 20, "bold")
    ).pack(pady=20)
    
    # Frame para los botones de opciones
    opciones_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    opciones_frame.pack(pady=30)
    
    