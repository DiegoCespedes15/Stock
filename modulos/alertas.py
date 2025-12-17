import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from bd import conectar_db
import tkinter as tk
from modulos.historial_alertas import mostrar_historial_alertas

# --- SEMÁFORO DE COLORES (NUEVO) ---
COLOR_AGOTADO = "#c0392b"   # Rojo Oscuro
COLOR_CRITICO = "#e67e22"   # Naranja Fuerte
COLOR_BAJO    = "#f1c40f"   # Amarillo/Dorado (Preventivo)
COLOR_TEXTO_BAJO = "#b7950b" # Un amarillo más oscuro para que se lea bien el texto

def mostrar_alertas(contenido_frame):
    """Muestra el Dashboard de Alertas Vigentes"""
    limpiar_contenido(contenido_frame)
    
    # --- HEADER ---
    header_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(header_frame, text="⚡ Centro de Control de Stock", font=("Arial", 24, "bold"), text_color="#2c3e50").pack(side="left")
    
    btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    btn_frame.pack(side="right")

    ctk.CTkButton(btn_frame, text="🔄 Actualizar Análisis", command=lambda: actualizar_alertas(contenido_frame), 
                  font=("Arial", 12, "bold"), fg_color="#3498db", width=160, height=35).pack(side="left", padx=5)
    
    ctk.CTkButton(btn_frame, text="📜 Historial Completo", command=lambda: mostrar_historial_alertas(contenido_frame), 
                  font=("Arial", 12, "bold"), fg_color="#9b59b6", width=160, height=35).pack(side="left", padx=5)

    alertas = obtener_alertas_activas()

    # --- SECCIÓN DE KPIs ---
    crear_kpis_superiores(contenido_frame, alertas)

    # --- LISTADO DE TARJETAS ---
    mostrar_listado_tarjetas(contenido_frame, alertas)


def crear_kpis_superiores(parent, alertas):
    kpi_frame = ctk.CTkFrame(parent, fg_color="transparent")
    kpi_frame.pack(fill="x", padx=15, pady=10)

    # Contadores separados por categoría
    n_agotados = sum(1 for a in alertas if a[4] == 'AGOTADO')
    n_criticos = sum(1 for a in alertas if a[4] == 'CRITICO')
    n_preventivos = sum(1 for a in alertas if a[4] == 'BAJO') # Ahora contamos preventivos

    def draw_card(container, titulo, numero, color, icon):
        card = ctk.CTkFrame(container, fg_color="white", corner_radius=15, border_width=2, border_color=color)
        card.pack(side="left", fill="both", expand=True, padx=5)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, pady=15)
        ctk.CTkLabel(inner, text=icon, font=("Segoe UI Emoji", 30)).pack(side="left", padx=10)
        v_frame = ctk.CTkFrame(inner, fg_color="transparent")
        v_frame.pack(side="left")
        ctk.CTkLabel(v_frame, text=str(numero), font=("Arial", 28, "bold"), text_color=color).pack(anchor="w")
        ctk.CTkLabel(v_frame, text=titulo, font=("Arial", 11, "bold"), text_color="gray").pack(anchor="w")

    draw_card(kpi_frame, "AGOTADOS", n_agotados, COLOR_AGOTADO, "🛑")
    draw_card(kpi_frame, "CRÍTICOS (Bajo Mínimo)", n_criticos, COLOR_CRITICO, "⚠️")
    draw_card(kpi_frame, "PREVENTIVOS (Cerca)", n_preventivos, COLOR_BAJO, "🔸")


def mostrar_listado_tarjetas(parent, alertas):
    ctk.CTkLabel(parent, text="Detalle de Productos", font=("Arial", 14, "bold"), text_color="gray", anchor="w").pack(fill="x", padx=25, pady=(10,5))
    scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    if not alertas:
        ctk.CTkLabel(scroll_frame, text="✅ Todo en orden. El inventario está saludable.", font=("Arial", 16), text_color="#2ecc71").pack(pady=50)
        return

    for alerta in alertas:
        crear_tarjeta_inteligente(scroll_frame, alerta, parent)


def crear_tarjeta_inteligente(parent, alerta, main_window_ref):
    """
    Crea una tarjeta con lógica visual de SEMÁFORO (3 Colores)
    """
    id_alerta, desc, stock, minimo, nivel, fecha = alerta[0], alerta[1], alerta[2], alerta[3], alerta[4], alerta[5]
    id_producto = alerta[6] if len(alerta) > 6 else None 

    # --- LÓGICA DE SEMÁFORO ---
    if nivel == "AGOTADO":
        color_borde = COLOR_AGOTADO
        icono_solo = "🛑"
        texto_estado = "AGOTADO"
        texto_extra = "Stock en Cero"
        progreso_valor = 0
    elif nivel == "CRITICO":
        color_borde = COLOR_CRITICO
        icono_solo = "⚠️"
        texto_estado = "CRÍTICO"
        texto_extra = "Por debajo del mínimo"
        # Progreso relativo al mínimo (ej: 4 de 5 = 0.8)
        progreso_valor = stock / minimo if minimo > 0 else 0
    else: # NIVEL 'BAJO' (PREVENTIVO)
        color_borde = COLOR_BAJO
        icono_solo = "🔸"
        texto_estado = "PREVENTIVO"
        texto_extra = "Cerca del límite (+25%)"
        # Progreso visual: Lo ponemos casi lleno para indicar que aun hay, pero es amarillo
        progreso_valor = 0.85 

    # --- CARD ---
    card = ctk.CTkFrame(parent, fg_color="white", corner_radius=10, border_width=2, border_color=color_borde)
    card.pack(fill="x", pady=8, padx=5)
    card.grid_columnconfigure(1, weight=1) 

    # 1. PANEL IZQUIERDO (Estado)
    left_panel = ctk.CTkFrame(card, fg_color=color_borde, corner_radius=8, width=100)
    left_panel.grid(row=0, column=0, sticky="ns", padx=(2,10))
    
    center_icon_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
    center_icon_frame.pack(expand=True, fill="both", pady=5)
    
    # Ajuste de color de texto para el amarillo (el blanco no se lee bien sobre amarillo)
    color_texto_icono = "white"
    if nivel == "BAJO": color_texto_icono = "#5c4804" # Marrón oscuro para contraste

    ctk.CTkLabel(center_icon_frame, text=icono_solo, font=("Segoe UI Emoji", 26), text_color=color_texto_icono).pack(anchor="center")
    ctk.CTkLabel(center_icon_frame, text=texto_estado, font=("Arial", 9, "bold"), text_color=color_texto_icono).pack(anchor="center")

    # 2. INFO CENTRAL
    info_frame = ctk.CTkFrame(card, fg_color="transparent")
    info_frame.grid(row=0, column=1, sticky="nsew", pady=10)
    
    ctk.CTkLabel(info_frame, text=desc, font=("Arial", 14, "bold"), text_color="#2c3e50", anchor="w").pack(fill="x")
    
    progress_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
    progress_frame.pack(fill="x", pady=5)
    
    pb = ctk.CTkProgressBar(progress_frame, width=300, height=10, progress_color=color_borde)
    pb.set(progreso_valor)
    pb.pack(side="left", padx=(0, 10))
    
    # Texto explicativo dinámico
    texto_stock = f"{stock} u. (Mín: {minimo})"
    ctk.CTkLabel(progress_frame, text=f"{texto_stock} | {texto_extra}", font=("Arial", 11), text_color="gray").pack(side="left")

    # 3. ACCIONES
    action_frame = ctk.CTkFrame(card, fg_color="transparent")
    action_frame.grid(row=0, column=2, padx=10, pady=10)

    btn_ajuste = ctk.CTkButton(action_frame, text="⚙️ Ajustar Mínimo", width=120, height=30,
                               fg_color="#ecf0f1", text_color="#2c3e50", hover_color="#bdc3c7",
                               command=lambda: abrir_modal_ajuste(main_window_ref, id_producto, desc, minimo))
    btn_ajuste.pack(pady=2)

    # Botón diferente para preventivo
    texto_btn = "✅ Entendido" if nivel == "BAJO" else "✅ Resolver"
    
    btn_ok = ctk.CTkButton(action_frame, text=texto_btn, width=120, height=30,
                           fg_color=color_borde, hover_color=color_borde,
                           text_color=color_texto_icono, # Ajuste de contraste
                           command=lambda: marcar_alerta_leida(id_alerta, card))
    btn_ok.pack(pady=2)


# --- FUNCIONES DE LÓGICA ---

def abrir_modal_ajuste(parent, id_producto, nombre_prod, minimo_actual):
    """Abre una ventana para cambiar la parametrización del stock mínimo"""
    if not id_producto:
        messagebox.showerror("Error", "No se puede identificar el producto.")
        return

    modal = ctk.CTkToplevel(parent)
    modal.title("Ajuste Inteligente de Stock")
    modal.geometry("400x250")
    modal.transient(parent.winfo_toplevel()) # Mantener encima
    modal.grab_set()
    
    # Centrar
    modal.geometry("+%d+%d" % (modal.winfo_screenwidth()/2 - 200, modal.winfo_screenheight()/2 - 125))

    ctk.CTkLabel(modal, text="⚙️ Re-parametrización de Stock", font=("Arial", 14, "bold")).pack(pady=15)
    ctk.CTkLabel(modal, text=f"Producto:\n{nombre_prod}", font=("Arial", 12), text_color="gray").pack(pady=5)

    frame_input = ctk.CTkFrame(modal, fg_color="transparent")
    frame_input.pack(pady=10)
    
    ctk.CTkLabel(frame_input, text="Nuevo Mínimo:").pack(side="left", padx=5)
    entry_nuevo = ctk.CTkEntry(frame_input, width=80)
    entry_nuevo.insert(0, str(minimo_actual))
    entry_nuevo.pack(side="left", padx=5)

    def guardar_cambio():
        nuevo_val = entry_nuevo.get()
        if not nuevo_val.isdigit():
            messagebox.showerror("Error", "Ingrese un número entero válido.")
            return
        
        try:
            conn = conectar_db()
            cur = conn.cursor()
            # Actualizamos el parámetro en la tabla maestra de stock
            cur.execute("UPDATE desarrollo.stock SET stock_minimo = %s WHERE id_articulo = %s", (nuevo_val, id_producto))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Éxito", f"Parámetro actualizado a {nuevo_val} unidades.\nEl sistema recalculará las alertas.")
            modal.destroy()
            actualizar_alertas(parent) # Refrescar dashboard
            
        except Exception as e:
            messagebox.showerror("Error DB", str(e))

    ctk.CTkButton(modal, text="💾 Guardar Cambios", fg_color="#27ae60", command=guardar_cambio).pack(pady=15)


def obtener_alertas_activas():
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # --- QUERY MEJORADA: Ahora traemos id_producto para poder editarlo ---
        # Asegúrate de que tu tabla desarrollo.alertas_stock tenga la columna id_producto
        # Si no la tiene, intenta hacer JOIN con movimientos o stock si es necesario.
        # Asumiendo estructura estándar:
        cursor.execute("""
            SELECT a.id_alerta, a.descripcion_producto, a.stock_actual, 
                   a.stock_minimo, a.nivel_alerta, a.fecha_alerta, a.id_producto
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

def marcar_alerta_leida(id_alerta, frame_widget):
    try:
        from services.alertas_service import servicio_alertas
        if servicio_alertas.marcar_alerta_vista(id_alerta):
            frame_widget.destroy()
            # No mostramos popup para hacerlo más fluido, solo desaparece
        else:
            messagebox.showerror("Error", "No se pudo actualizar.")
    except Exception as e:
        messagebox.showerror("Error", f"Excepción: {e}")

def actualizar_alertas(contenido_frame):
    """
    Fuerza la ejecución inmediata de la verificación de stock
    y refresca la pantalla.
    """
    try:
        from services.alertas_service import servicio_alertas
        
        # 1. Primero LIMPIAMOS: Forzamos la resolución de alertas que ya tienen stock
        resueltas = servicio_alertas.verificar_alertas_resueltas()
        
        # 2. Luego BUSCAMOS: Forzamos la búsqueda de nuevos problemas
        nuevas = servicio_alertas.verificar_nuevas_alertas()
        
        # 3. Finalmente repintamos la pantalla con la data fresca de la DB
        mostrar_alertas(contenido_frame) 

    except Exception as e:
        messagebox.showerror("Error", f"Error al actualizar: {str(e)}")

def limpiar_contenido(frame):
    for widget in frame.winfo_children():
        widget.destroy()