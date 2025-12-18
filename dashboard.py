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
            cursor.execute("SET app.usuario = %s", (usuario_db,))
            conexion.commit()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
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
    
    # OBTENER NIVEL DE USUARIO
    nivel_usuario = 0 
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT user_nivel FROM desarrollo.usuarios WHERE user_key = %s", (usuario_db,))
        resultado = cursor.fetchone()
        if resultado:
            nivel_usuario = resultado[0]
        cursor.close()
    except Exception as e:
        print(f"Error de seguridad: {e}")
        nivel_usuario = 0 

    if nivel_usuario == 0:
        ventana_temp = tk.Tk()
        ventana_temp.withdraw()  
        
        messagebox.showerror(
            "Acceso Denegado", 
            "EL USUARIO INGRESADO ESTÁ INHABILITADO.\n\n"
            "No tiene permisos para acceder al sistema.\n"
            "Por favor, contacte al administrador.",
            parent=ventana_temp 
        )
        
        ventana_temp.destroy() 
        volver_callback()      # Volvemos al login
        return
    
   
    NIVEL_INHABILITADO = 0
    NIVEL_DEPOSITO = 1
    NIVEL_VENTAS = 2
    NIVEL_ENCARGADO = 3
    
    
    app = ctk.CTk()
    app.title("Sistema de Inventario Inteligente")
    app.geometry("1280x720")
    app.resizable(True, True)  # Permite maximizar

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
        main_frame,  
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
            
            rel_x = btn_x_root - win_x_root
            rel_y = btn_y_root - win_y_root
            
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
    def confirmar_cierre_sesion(window, callback_final):
        nonlocal menu_visible
        user_menu.place_forget()
        menu_visible = False
        
        respuesta = messagebox.askyesno(
            "Cerrar Sesión", 
            "¿Estás seguro de que deseas cerrar sesión?"
        )
        
        if respuesta:
            #Primero destruimos la ventana actual (Dashboard)
            window.destroy() 
            
            #Luego llamamos al callback que cierra la DB y abre el Login
            callback_final()


    def volver_login_callback():
        """Callback intermedio para cerrar DB antes de ir al login"""
        try:
            conexion.close()
        except:
            pass
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
        
        total_productos = 0
        valor_inventario = 0
        total_alertas = 0
        venta_predicha = 0
        ventas_reales_mes = 0
        
        try:
            # DATOS COMUNES (Todos ven la cantidad de productos)
            res_prod = ejecutar_consulta("SELECT COUNT(*) FROM desarrollo.stock")
            total_productos = res_prod[0][0] if res_prod else 0
            
            # DATOS PARA ENCARGADO (Nivel 3)
            if nivel_usuario == NIVEL_ENCARGADO:
                # Valor Inventario
                res_valor = ejecutar_consulta("SELECT SUM(cant_inventario * precio_unit) FROM desarrollo.stock")
                valor_inventario = res_valor[0][0] if res_valor and res_valor[0][0] else 0
                
                # Alertas
                res_alertas = ejecutar_consulta("SELECT COUNT(*) FROM desarrollo.stock WHERE cant_inventario <= 10")
                total_alertas = res_alertas[0][0] if res_alertas else 0
                
                # Predicciones
                mes_actual = datetime.datetime.now().month
                anio_actual = datetime.datetime.now().year
                res_pred = ejecutar_consulta("SELECT SUM(cantidad_predicha) FROM desarrollo.prediccion_mensual WHERE mes = %s AND anio = %s", (mes_actual, 2024))
                venta_predicha = res_pred[0][0] if res_pred and res_pred[0][0] else 0

            # DATOS PARA VENTAS (Nivel 2)
            elif nivel_usuario == NIVEL_VENTAS:
                res_ventas = ejecutar_consulta("""
                    SELECT SUM(v_montous_total) 
                    FROM desarrollo.ventas 
                    WHERE EXTRACT(MONTH FROM v_fecha) = EXTRACT(MONTH FROM CURRENT_DATE)
                    AND EXTRACT(YEAR FROM v_fecha) = 2024 
                """)
                ventas_reales_mes = res_ventas[0][0] if res_ventas and res_ventas[0][0] else 0

            # D. DATOS PARA DEPÓSITO (Nivel 1)
            elif nivel_usuario == NIVEL_DEPOSITO:
                res_alertas = ejecutar_consulta("SELECT COUNT(*) FROM desarrollo.stock WHERE cant_inventario <= 10")
                total_alertas = res_alertas[0][0] if res_alertas else 0

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

        # 1. NIVEL VENTAS: Solo Productos y Ventas Reales (Limpio y directo)
        if nivel_usuario == NIVEL_VENTAS:
            crear_card(kpi_container, "Total Productos", f"{total_productos}", "#3498db", "📦")
            crear_card(kpi_container, "Ventas este Mes", f"${ventas_reales_mes:,.0f}", "#2ecc71", "💲")

        # 2. NIVEL DEPÓSITO: Productos y Alertas (Urgente)
        elif nivel_usuario == NIVEL_DEPOSITO:
            crear_card(kpi_container, "Total Productos", f"{total_productos}", "#3498db", "📦")
            crear_card(kpi_container, "Alertas Stock", f"{total_alertas}", "#e74c3c", "⚠️")

        # 3. NIVEL ENCARGADO: Ve el panorama completo (Dashboard Original)
        else:
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
        
        meses = ['Ago', 'Sep', 'Oct', 'Nov', 'Dic', 'Ene']
        valores = [120, 145, 110, 170, 210, 180] 
        
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
        actions_frame = ctk.CTkFrame(mid_container, fg_color="transparent")
        actions_frame.pack(side="right", fill="y", padx=10, anchor="n")
        
        ctk.CTkLabel(actions_frame, text="Acciones Rápidas", font=("Arial", 12, "bold"), text_color="gray").pack(pady=(0,10), anchor="w")

        # SOLO MOSTRAR SI TIENE PERMISO (Ventas o Encargado)
        if nivel_usuario in [NIVEL_VENTAS, NIVEL_ENCARGADO]:
            ctk.CTkButton(actions_frame, text="Ver Ventas", fg_color="#2ecc71", width=200, height=40, font=("Arial", 12, "bold"),
                          command=lambda: ventas.mostrar_ventas(contenido_frame)).pack(pady=5)
            
            ctk.CTkButton(actions_frame, text="Ver Predicciones", fg_color="#3498db", width=200, height=40, font=("Arial", 12, "bold"),
                          command=lambda: reportes.mostrar_reportes_predictivos(contenido_frame)).pack(pady=5)

        # SOLO MOSTRAR SI TIENE PERMISO (Depósito o Encargado)
        if nivel_usuario in [NIVEL_DEPOSITO, NIVEL_ENCARGADO]:                  
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
        
    # --- CONSTRUCCIÓN DINÁMICA DEL MENÚ LATERAL ---
    botones = []


    if nivel_usuario > 0:
        botones.append(("Inicio", mostrar_inicio))

    # Lógica según niveles
    
    # -- NIVEL 1: DEPÓSITO --
    if nivel_usuario == NIVEL_DEPOSITO:
        botones.append(("Productos", lambda: stock.mostrar_productos(contenido_frame)))
        botones.append(("Movimientos", lambda: movimientos.mostrar_movimientos(contenido_frame, usuario_db)))
        botones.append(("Alertas", lambda: alertas.mostrar_alertas(contenido_frame)))

    # -- NIVEL 2: VENTAS --
    elif nivel_usuario == NIVEL_VENTAS:
        botones.append(("Ventas", lambda: ventas.mostrar_ventas(contenido_frame)))
        botones.append(("Productos", lambda: stock.mostrar_productos(contenido_frame)))
        
    # -- NIVEL 3: ENCARGADO --
    elif nivel_usuario == NIVEL_ENCARGADO:
        botones.append(("Productos", lambda: stock.mostrar_productos(contenido_frame)))
        botones.append(("Ventas", lambda: ventas.mostrar_ventas(contenido_frame)))
        botones.append(("Movimientos", lambda: movimientos.mostrar_movimientos(contenido_frame, usuario_db)))
        botones.append(("Alertas", lambda: alertas.mostrar_alertas(contenido_frame)))
        botones.append(("Reportes", lambda: reportes.mostrar_menu_reportes(contenido_frame)))
        

    # 3. El botón de Salir siempre va al final
    botones.append(("Salir", lambda: confirmar_salir(app)))

    # --- GENERAR BOTONES VISUALMENTE ---
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


    def on_click(event):
        try:
            if not app.winfo_exists(): return
        except:
            return

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
    
