import customtkinter as ctk
from bd import conectar_db
import threading
import tkinter as tk
from datetime import datetime

# --- CONFIGURACIÓN VISUAL (COHERENCIA CON ALERTAS) ---
COLOR_AGOTADO = "#c0392b"   # Rojo
COLOR_CRITICO = "#e67e22"   # Naranja
COLOR_BAJO    = "#f1c40f"   # Amarillo
COLOR_RESUELTA = "#27ae60"  # Verde
COLOR_NEUTRO  = "#95a5a6"   # Gris

def _fmt_fecha(fecha):
    if not fecha: return "-"
    if isinstance(fecha, datetime): return fecha.strftime("%d/%m/%Y %H:%M")
    return str(fecha)

def mostrar_historial_alertas(contenido_frame):
    """Muestra el historial completo con filtros funcionales"""
    limpiar_contenido(contenido_frame)
    
    # --- HEADER ---
    header_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(header_frame, text="📜 Historial de Incidentes", font=("Arial", 24, "bold"), text_color="#2c3e50").pack(side="left")
    
    # --- SOLUCIÓN AL BOTÓN VOLVER (Importación Local) ---
    def volver_atras():
        # Importamos AQUÍ dentro para evitar el error de importación circular
        from modulos.alertas import mostrar_alertas
        mostrar_alertas(contenido_frame)

    ctk.CTkButton(header_frame, text="⬅️ Volver ", command=volver_atras,
                  font=("Arial", 12, "bold"), fg_color="#34495e", width=180).pack(side="right")

    # --- BARRA DE FILTROS ---
    filtros_frame = ctk.CTkFrame(contenido_frame, fg_color="white", corner_radius=10)
    filtros_frame.pack(fill="x", padx=20, pady=10)
    
    ctk.CTkLabel(filtros_frame, text="Filtros de Búsqueda:", font=("Arial", 12, "bold"), text_color="gray").grid(row=0, column=0, padx=15, pady=10, sticky="w")
    
    # 1. Buscador Texto
    entry_buscar = ctk.CTkEntry(filtros_frame, width=250, placeholder_text="Nombre del producto...")
    entry_buscar.grid(row=0, column=1, padx=5, pady=10)
    
    # 2. Filtro Estado
    combo_estado = ctk.CTkComboBox(filtros_frame, values=["Todos", "ACTIVA", "RESUELTA", "VISTA"], width=120)
    combo_estado.set("Todos")
    combo_estado.grid(row=0, column=2, padx=5, pady=10)
    
    # 3. Filtro Nivel
    combo_nivel = ctk.CTkComboBox(filtros_frame, values=["Todos", "AGOTADO", "CRITICO", "BAJO"], width=120)
    combo_nivel.set("Todos")
    combo_nivel.grid(row=0, column=3, padx=5, pady=10)
    
    # Botones
    def ejecutar():
        filtros = {
            "texto": entry_buscar.get(),
            "estado": combo_estado.get(),
            "nivel": combo_nivel.get()
        }
        buscar_alertas(scroll_container, lbl_status, filtros)

    def limpiar():
        entry_buscar.delete(0, "end")
        combo_estado.set("Todos")
        combo_nivel.set("Todos")
        ejecutar()

    ctk.CTkButton(filtros_frame, text="🔎 Buscar", width=100, command=ejecutar).grid(row=0, column=4, padx=10)
    ctk.CTkButton(filtros_frame, text="Limpiar", width=80, fg_color="gray", command=limpiar).grid(row=0, column=5, padx=5)

    # --- ÁREA DE RESULTADOS ---
    lbl_status = ctk.CTkLabel(contenido_frame, text="", font=("Arial", 12, "italic"), text_color="gray")
    lbl_status.pack(pady=(5,0))

    scroll_container = ctk.CTkScrollableFrame(contenido_frame, fg_color="transparent")
    scroll_container.pack(fill="both", expand=True, padx=20, pady=10)

    # Carga inicial
    ejecutar()

def buscar_alertas(parent, status_label, filtros):
    # Limpiar
    for w in parent.winfo_children(): w.destroy()
    status_label.configure(text="⏳ Cargando historial...")
    
    # Hilo para no congelar interfaz
    threading.Thread(target=lambda: _consultar_bd(parent, status_label, filtros), daemon=True).start()

def _consultar_bd(parent, status_label, filtros):
    try:
        conn = conectar_db()
        cur = conn.cursor()
        
        # Construcción de Query Dinámica
        sql = """
            SELECT id_alerta, descripcion_producto, stock_actual, stock_minimo, nivel_alerta, estado, fecha_alerta 
            FROM desarrollo.alertas_stock
            WHERE 1=1
        """
        params = []
        
        if filtros["texto"]:
            sql += " AND descripcion_producto ILIKE %s"
            params.append(f"%{filtros['texto']}%")
            
        if filtros["estado"] != "Todos":
            sql += " AND estado = %s"
            params.append(filtros["estado"])
            
        if filtros["nivel"] != "Todos":
            sql += " AND nivel_alerta = %s"
            params.append(filtros["nivel"])
            
        sql += " ORDER BY fecha_alerta DESC LIMIT 50" # Limitamos a 50 para no saturar
        
        cur.execute(sql, tuple(params))
        resultados = cur.fetchall()
        conn.close()
        
        # Renderizar en hilo principal (necesario para Tkinter)
        parent.after(0, lambda: _renderizar_tarjetas(parent, status_label, resultados))
        
    except Exception as e:
        print(e)
        parent.after(0, lambda: status_label.configure(text="❌ Error de conexión"))

def _renderizar_tarjetas(parent, status_label, resultados):
    if not resultados:
        status_label.configure(text="No se encontraron registros.")
        return
    
    status_label.configure(text=f"Mostrando los últimos {len(resultados)} eventos encontrados.")
    
    for row in resultados:
        crear_tarjeta_historial(parent, row)

def crear_tarjeta_historial(parent, datos):
    id_alerta, desc, stock, minimo, nivel, estado, fecha = datos
    
    # Determinar Colores e Iconos
    if estado == "RESUELTA":
        color = COLOR_RESUELTA
        icono = "✔️"
        texto_estado = "RESUELTA"
    elif estado == "VISTA":
        color = "#3498db" # Azul para visto
        icono = "👀"
        texto_estado = "VISTA / ARCHIVADA"
    else: # ACTIVA
        if nivel == "AGOTADO": color = COLOR_AGOTADO; icono = "🛑"
        elif nivel == "CRITICO": color = COLOR_CRITICO; icono = "⚠️"
        else: color = COLOR_BAJO; icono = "🔸"
        texto_estado = "ACTIVA"

    # Frame Tarjeta
    card = ctk.CTkFrame(parent, fg_color="white", corner_radius=10, border_width=2, border_color=color)
    card.pack(fill="x", pady=5, padx=5)
    
    # Grid interno
    card.grid_columnconfigure(1, weight=1)
    
    # 1. Icono Izquierda
    left = ctk.CTkFrame(card, fg_color=color, width=60, corner_radius=8)
    left.grid(row=0, column=0, sticky="ns", padx=5, pady=5)
    ctk.CTkLabel(left, text=icono, font=("Segoe UI Emoji", 20), text_color="white").place(relx=0.5, rely=0.5, anchor="center")
    
    # 2. Datos Centro
    center = ctk.CTkFrame(card, fg_color="transparent")
    center.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
    
    ctk.CTkLabel(center, text=desc, font=("Arial", 12, "bold"), text_color="#2c3e50").pack(anchor="w")
    
    info_text = f"Estado: {texto_estado} | Nivel: {nivel} | Stock en ese momento: {stock} (Mín: {minimo})"
    ctk.CTkLabel(center, text=info_text, font=("Arial", 11), text_color="gray").pack(anchor="w")
    
    # 3. Fecha Derecha
    right = ctk.CTkFrame(card, fg_color="transparent")
    right.grid(row=0, column=2, padx=10)
    ctk.CTkLabel(right, text=_fmt_fecha(fecha), font=("Arial", 11, "bold"), text_color="gray").pack()

def limpiar_contenido(frame):
    for w in frame.winfo_children(): w.destroy()