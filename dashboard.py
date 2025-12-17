# dashboard.py
import customtkinter as ctk
from modulos import stock
from modulos import ventas
from modulos import movimientos
from modulos import alertas
from modulos import reportes
from modulos import reportes_predictivos
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime # Para manejar fechas en las consultas

def abrir_dashboard(nombre_usuario, volver_callback, conexion, usuario_db):
    
    def ejecutar_consulta(query, params=None):
        """Función helper para ejecutar consultas manteniendo la sesión"""
        try:
            cursor = conexion.cursor()

            # ✅ ESTABLECER USUARIO ANTES DE CADA CONSULTA
            cursor.execute("SET app.usuario = %s", (usuario_db,))
            conexion.commit()

            # Ejecutar la consulta real
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Para SELECT retornar resultados, para otros hacer commit
            if query.strip().upper().startswith('SELECT'):
                resultado = cursor.fetchall()
            else:
                conexion.commit()
                resultado = None

            cursor.close()
            return resultado

        except Exception as e:
            print("Error en consulta:", e)
            conexion.rollback()
            return None
    
    
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
            # Si ya está visible, lo ocultamos
            user_menu.place_forget()
            menu_visible = False
        else:
            # --- CÁLCULO DE POSICIÓN EXACTA ---
            app.update_idletasks() # Asegura que las medidas sean actuales
            
            # 1. Obtener coordenadas globales (en la pantalla) del botón y la ventana
            btn_x_root = user_btn.winfo_rootx()
            btn_y_root = user_btn.winfo_rooty()
            win_x_root = app.winfo_rootx()
            win_y_root = app.winfo_rooty()
            
            # 2. Calcular la posición relativa dentro de la ventana (Resta simple)
            # Esto nos dice dónde está el botón "dentro" de tu aplicación
            rel_x = btn_x_root - win_x_root
            rel_y = btn_y_root - win_y_root
            
            # 3. Ajuste de Alineación (Para que quede pegado a la derecha)
            # El menú mide 150px de ancho, el botón unos 35px.
            # Si ponemos solo 'rel_x', el menú sale alineado a la izquierda del botón.
            # Queremos alinearlo a la derecha, así que restamos la diferencia.
            menu_width = 150 
            btn_width = user_btn.winfo_width()
            btn_height = user_btn.winfo_height()
            
            # Coordenada final X: Posición botón - (Diferencia de anchos)
            final_x = rel_x - (menu_width - btn_width)
            
            # Coordenada final Y: Posición botón + Altura botón + un margen pequeño (5px)
            final_y = rel_y + btn_height + 5
            
            # --- COLOCAR EL MENÚ ---
            user_menu.place(x=final_x, y=final_y)
            user_menu.lift() # Traer al frente por si acaso
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
            try:
                conexion.close()
            except:
                pass
            window.destroy()
            callback()


    def volver_login_callback():
        """Callback para volver al login"""
        try:
            conexion.close()
        except:
            pass
        app.destroy()
        volver_callback()
    
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
        
        # --- 1. OBTENCIÓN DE DATOS (Queries Reales) ---
        try:
            # A. KPI: Total Productos
            res_prod = ejecutar_consulta("SELECT COUNT(*) FROM desarrollo.stock")
            total_productos = res_prod[0][0] if res_prod else 0
            
            # B. KPI: Valor del Inventario (Dinero)
            res_valor = ejecutar_consulta("SELECT SUM(cant_inventario * precio_unit) FROM desarrollo.stock")
            valor_inventario = res_valor[0][0] if res_valor and res_valor[0][0] else 0
            
            # C. KPI: Alertas (Stock Bajo < 10 unidades por ejemplo)
            res_alertas = ejecutar_consulta("SELECT COUNT(*) FROM desarrollo.stock WHERE cant_inventario <= 10") # Ajusta el límite si quieres
            total_alertas = res_alertas[0][0] if res_alertas else 0
            
            # D. KPI: Ventas del Mes Actual (Predicción vs Realidad)
            # Nota: Esto es un ejemplo, ajusta si tu tabla de predicciones tiene otra estructura
            mes_actual = datetime.datetime.now().month
            anio_simulado = 2024
            # Intentamos traer la suma de predicciones para este mes
            res_pred = ejecutar_consulta("""
                SELECT SUM(cantidad_predicha) FROM desarrollo.prediccion_mensual 
                WHERE mes = %s AND anio = %s
            """, (mes_actual, anio_simulado))
            venta_predicha = res_pred[0][0] if res_pred and res_pred[0][0] else 0
            
        except Exception as e:
            print(f"Error cargando datos dashboard: {e}")
            total_productos, valor_inventario, total_alertas, venta_predicha = 0, 0, 0, 0

        # --- 2. CONSTRUCCIÓN DE LA INTERFAZ ---
        
        # Frame con Scroll para que se adapte a cualquier pantalla
        main_scroll = ctk.CTkScrollableFrame(contenido_frame, fg_color="transparent")
        main_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Título de Bienvenida mejorado
        header_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 20), padx=10)
        ctk.CTkLabel(header_frame, text=f"Hola, {nombre_usuario}", font=("Arial", 24, "bold"), text_color="#2c3e50").pack(anchor="w")
        ctk.CTkLabel(header_frame, text="Aquí tienes el resumen de hoy.", font=("Arial", 14), text_color="gray").pack(anchor="w")

        # --- SECCIÓN KPI (TARJETAS SUPERIORES) ---
        kpi_container = ctk.CTkFrame(main_scroll, fg_color="transparent")
        kpi_container.pack(fill="x", pady=10)

        def crear_card(parent, titulo, valor, color_borde, icono):
            card = ctk.CTkFrame(parent, fg_color="white", corner_radius=15, border_color=color_borde, border_width=2)
            card.pack(side="left", fill="both", expand=True, padx=10)
            ctk.CTkLabel(card, text=icono, font=("Arial", 32)).pack(pady=(15, 5))
            ctk.CTkLabel(card, text=valor, font=("Arial", 22, "bold"), text_color="#333").pack()
            ctk.CTkLabel(card, text=titulo, font=("Arial", 11, "bold"), text_color="gray").pack(pady=(0, 15))

        crear_card(kpi_container, "Total Productos", f"{total_productos}", "#3498db", "📦")
        crear_card(kpi_container, "Valor Inventario", f"${valor_inventario:,.0f}", "#2ecc71", "💰")
        crear_card(kpi_container, "Alertas Stock", f"{total_alertas}", "#e74c3c", "⚠️")
        crear_card(kpi_container, "Predicción Mes", f"{int(venta_predicha)} un.", "#f39c12", "🔮")

        # --- SECCIÓN CENTRAL (GRÁFICO + LISTA) ---
        mid_container = ctk.CTkFrame(main_scroll, fg_color="transparent")
        mid_container.pack(fill="both", expand=True, pady=20)

        # 1. Gráfico (Izquierda)
        chart_frame = ctk.CTkFrame(mid_container, fg_color="white", corner_radius=10)
        chart_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(chart_frame, text="Resumen de Ventas (Últimos 6 Meses)", font=("Arial", 12, "bold"), text_color="#555").pack(pady=10)
        
        # Datos Dummy para el gráfico (puedes conectarlo a SQL igual que los KPIs)
        # query_grafico = "SELECT to_char(v_fecha, 'Mon'), SUM(v_cantidad) FROM desarrollo.ventas ... GROUP BY 1"
        meses = ['Ago', 'Sep', 'Oct', 'Nov', 'Dic', 'Ene']
        valores = [120, 145, 110, 170, 210, 180] # Ejemplo estático para diseño
        
        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        ax.bar(meses, valores, color="#FF9100", alpha=0.7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(colors='gray', labelsize=8)
        fig.patch.set_facecolor('white')
        
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0,10))

        # 2. Accesos Rápidos (Derecha)
        actions_frame = ctk.CTkFrame(mid_container, fg_color="transparent") # Transparente para botones flotantes
        actions_frame.pack(side="right", fill="y", padx=10, anchor="n")
        
        ctk.CTkLabel(actions_frame, text="Acciones Rápidas", font=("Arial", 12, "bold"), text_color="gray").pack(pady=(0,10), anchor="w")

        ctk.CTkButton(actions_frame, text="Ver Ventas", fg_color="#2ecc71", width=200, height=40, font=("Arial", 12, "bold"),
                      command=lambda: ventas.mostrar_ventas(contenido_frame)).pack(pady=5)
                      
        ctk.CTkButton(actions_frame, text="Ver Predicciones", fg_color="#3498db", width=200, height=40, font=("Arial", 12, "bold"),
                      command=lambda: reportes.mostrar_reportes_predictivos(contenido_frame)).pack(pady=5)
                      
        ctk.CTkButton(actions_frame, text="Gestionar Productos", fg_color="#95a5a6", width=200, height=40, font=("Arial", 12, "bold"),
                      command=lambda: stock.mostrar_productos(contenido_frame)).pack(pady=5)
        
    
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
        ("Movimientos", lambda: movimientos.mostrar_movimientos(contenido_frame, usuario_db)),
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
    

