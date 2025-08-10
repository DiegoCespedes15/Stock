# dashboard.py

import customtkinter as ctk
from modulos import stock
from modulos import ventas


def abrir_dashboard(nombre_usuario):
    app = ctk.CTk()
    app.title("Sistema de Inventario Inteligente")
    app.geometry("1280x720")

    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    menu_frame = ctk.CTkFrame(app, width=200, corner_radius=0)
    menu_frame.pack(side="left", fill="y")

    contenido_frame = ctk.CTkFrame(app, corner_radius=0)
    contenido_frame.pack(side="right", expand=True, fill="both")

    def limpiar_contenido():
        for widget in contenido_frame.winfo_children():
            widget.destroy()

    def mostrar_inicio():
        limpiar_contenido()
        ctk.CTkLabel(
            contenido_frame, 
            text=f"Bienvenido, {nombre_usuario}",
            font=("Arial", 20, "bold")
        ).pack(pady=30)

    def mostrar_modulo(nombre):
        limpiar_contenido()
        ctk.CTkLabel(
            contenido_frame, 
            text=f"Módulo: {nombre}", 
            font=("Arial", 20)
        ).pack(pady=30)

    botones = [
        ("Inicio", mostrar_inicio),
        ("Productos", lambda: stock.mostrar_productos(contenido_frame)),
        ("Ventas", lambda: ventas.mostrar_ventas(contenido_frame)),
        ("Reportes", lambda: mostrar_modulo("Reportes")),
        ("Salir", app.destroy)
    ]

    for texto, comando in botones:
        ctk.CTkButton(
            menu_frame,
            text=texto,
            command=comando,
            font=("Arial", 14),
            width=180,
            height=40,
            corner_radius=10,
            fg_color="#FF9100",
            hover_color="#E07B00",
            cursor="hand2"
        ).pack(pady=10, padx=10)

    mostrar_inicio()
    app.mainloop()
