# dashboard.py
import customtkinter as ctk
from modulos import stock
from modulos import ventas
from modulos import movimientos
from modulos import alertas
from modulos import reportes
import tkinter as tk
from tkinter import messagebox


def abrir_dashboard(nombre_usuario, volver_login_callback):
    app = ctk.CTk()
    app.title("Sistema de Inventario Inteligente")
    app.geometry("1280x720")
    app.resizable(True, True)  # Permitir maximizar

    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    # Frame principal para la barra superior y el contenido
    main_frame = ctk.CTkFrame(app, corner_radius=0)
    main_frame.pack(fill="both", expand=True)

    # Barra superior con el nombre de usuario y botón de menú
    top_bar = ctk.CTkFrame(main_frame, height=50, corner_radius=0)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    # Título del sistema en la barra superior
    ctk.CTkLabel(
        top_bar, 
        text="Sistema de Inventario Inteligente",
        font=("Arial", 16, "bold")
    ).pack(side="left", padx=20)

    # Frame para el menú de usuario (a la derecha)
    user_menu_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
    user_menu_frame.pack(side="right", padx=20)

    # Obtener iniciales del usuario
    partes_nombre = nombre_usuario.split()
    if len(partes_nombre) >= 2:
        iniciales = partes_nombre[0][0] + partes_nombre[1][0]
    else:
        iniciales = nombre_usuario[:2]
    iniciales = iniciales.upper()

    # Variable para controlar la visibilidad del menú
    menu_visible = False

    # Crear menú desplegable (inicialmente oculto)
    user_menu = ctk.CTkFrame(
        main_frame,  # Cambiado a main_frame para mejor posicionamiento
        width=150, 
        height=80, 
        corner_radius=10,
        border_width=1,
        border_color="#ccc"
    )
    
    # Etiqueta con nombre de usuario en el menú (versión abreviada)
    ctk.CTkLabel(
        user_menu,
        text=nombre_usuario,
        font=("Arial", 12),
        wraplength=140
    ).pack(pady=(10, 5), padx=10)

    # Separador
    separator = ctk.CTkFrame(user_menu, height=1, fg_color="#ccc")
    separator.pack(fill="x", padx=5)

    # Botón de cerrar sesión
    ctk.CTkButton(
        user_menu,
        text="Cerrar Sesión",
        font=("Arial", 12),
        width=130,
        height=30,
        fg_color="transparent",
        text_color="#FF5656",
        hover_color="#FFE5E5",
        command=lambda: confirmar_cierre_sesion(app, volver_login_callback)
    ).pack(pady=5)

    # Función para mostrar/ocultar el menú de usuario
    def toggle_user_menu():
        nonlocal menu_visible
        if menu_visible:
            # Ocultar menú
            user_menu.place_forget()
            menu_visible = False
        else:
            # Mostrar menú cerca del botón de usuario
            app.update_idletasks()  # Actualizar para obtener coordenadas correctas
            
            # Obtener posición del botón de usuario dentro del main_frame
            user_btn_x = user_btn.winfo_x()
            user_btn_y = user_btn.winfo_y()
            user_btn_width = user_btn.winfo_width()
            user_btn_height = user_btn.winfo_height()
            
            # Calcular posición del menú relativa al main_frame
            menu_x = user_btn_x + user_btn_width + 1030  # Ajustar para alinear a la izquierda
            menu_y = user_btn_y + user_btn_height + 5  # Colocar justo debajo del botón
            
            # Asegurarse de que el menú no se salga de los límites
            if menu_x < 0:
                menu_x = 10
            if menu_y < 0:
                menu_y = 10
                
            user_menu.place(x=menu_x, y=menu_y)
            user_menu.lift()  # Traer al frente
            menu_visible = True

    # Botón de usuario con sus iniciales
    user_btn = ctk.CTkButton(
        user_menu_frame,
        text=iniciales,
        width=35,
        height=35,
        font=("Arial", 14, "bold"),
        fg_color="#3B8ED0",
        hover_color="#3679B5",
        command=toggle_user_menu
    )
    user_btn.pack(side="right")

    

    # Función para confirmar cierre de sesión
    def confirmar_cierre_sesion(window, callback):
        nonlocal menu_visible
        user_menu.place_forget()
        menu_visible = False
        respuesta = messagebox.askyesno(
            "Cerrar Sesión", 
            "¿Estás seguro de que deseas cerrar sesión?"
        )
        if respuesta:
            window.destroy()
            callback()

    # Contenedor principal (menú lateral + contenido)
    content_container = ctk.CTkFrame(main_frame, corner_radius=0)
    content_container.pack(side="bottom", fill="both", expand=True)

    # Menú lateral
    menu_frame = ctk.CTkFrame(content_container, width=200, corner_radius=0)
    menu_frame.pack(side="left", fill="y")
    menu_frame.pack_propagate(False)

    # Frame de contenido
    contenido_frame = ctk.CTkFrame(content_container, corner_radius=0)
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
        
        
    # Iniciar servicio de alertas en segundo plano
    from services import alertas_service
    servicio_alertas = alertas_service.ServicioAlertas()
    servicio_alertas.iniciar_servicio(intervalo=30)
    
        
    def confirmar_salir(ventana):
        respuesta = messagebox.askyesno(
        "Salir del Sistema", 
        "¿Estás seguro de que deseas salir del sistema?"
    )
        if respuesta:
            ventana.destroy()
        
    botones = [
        ("Inicio", mostrar_inicio),
        ("Productos", lambda: stock.mostrar_productos(contenido_frame)),
        ("Ventas", lambda: ventas.mostrar_ventas(contenido_frame)),
        ("Movimientos", lambda: movimientos.mostrar_movimientos(contenido_frame)),
        ("Alertas", lambda: alertas.mostrar_alertas(contenido_frame)), 
        ("Reportes", lambda: reportes.mostrar_menu_reportes(contenido_frame)), 
        ("Salir", lambda: confirmar_salir(app))
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

    # Ocultar menú al hacer clic fuera de él
    def on_click(event):
        nonlocal menu_visible
        
        if menu_visible:
            # Verificar si el clic fue fuera del menú y fuera del botón de usuario
            x, y = event.x, event.y

            # Obtener posición y dimensiones del menú (relativas al main_frame)
            menu_x = user_menu.winfo_x()
            menu_y = user_menu.winfo_y()
            menu_width = user_menu.winfo_width()
            menu_height = user_menu.winfo_height()

            # Obtener posición y dimensiones del botón (relativas al user_menu_frame)
            btn_x = user_btn.winfo_x()
            btn_y = user_btn.winfo_y()
            btn_width = user_btn.winfo_width()
            btn_height = user_btn.winfo_height()

            # Convertir coordenadas del botón a coordenadas del main_frame
            btn_frame_x = user_menu_frame.winfo_x()
            btn_frame_y = user_menu_frame.winfo_y()
            btn_abs_x = btn_frame_x + btn_x
            btn_abs_y = btn_frame_y + btn_y

            # Verificar si el clic fue fuera del menú Y fuera del botón
            click_in_menu = (menu_x <= x <= menu_x + menu_width and 
                             menu_y <= y <= menu_y + menu_height)
            click_in_button = (btn_abs_x <= x <= btn_abs_x + btn_width and 
                               btn_abs_y <= y <= btn_abs_y + btn_height)

            if not click_in_menu and not click_in_button:
                user_menu.place_forget()
                menu_visible = False

    app.bind("<Button-1>", on_click)
    user_menu.bind("<Button-1>", lambda e: "break")
    user_btn.bind("<Button-1>", lambda e: "break") 

    
    
    
    mostrar_inicio()
    
    # Centrar la ventana
    app.eval('tk::PlaceWindow . center')
    
    app.mainloop()