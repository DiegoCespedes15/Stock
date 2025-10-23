# historial_alertas.py
import customtkinter as ctk
from bd import conectar_db
import threading
import tkinter as tk
from datetime import datetime

def _fmt_fecha(fecha):
    if not fecha:
        return "-"
    if isinstance(fecha, datetime):
        return fecha.strftime("%d/%m/%Y %H:%M")
    try:
        dt = datetime.fromisoformat(str(fecha).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(fecha)

def _estado_color_icono(nivel, estado):
    nivel_u = (str(nivel) if nivel is not None else "").upper()
    estado_u = (str(estado) if estado is not None else "").upper()
    if estado_u == "RESUELTA":
        return ("Resuelta", "#2ecc71", "✔️")
    if estado_u == "ACTIVA":
        if nivel_u == "AGOTADO":
            return ("Activa", "#e74c3c", "🛑")
        if nivel_u == "CRITICO":
            return ("Activa", "#f39c12", "⚠️")
        return ("Activa", "#f1c40f", "🔸")
    return (estado_u.capitalize() if estado_u else "Desconocida", "#7f8c8d", "❓")

def _badge(parent, text, bg, fg="white"):
    return ctk.CTkLabel(parent, text=text, fg_color=bg, text_color=fg, corner_radius=12, font=("Arial", 10, "bold"), padx=10, pady=4)

def mostrar_historial_alertas(contenido_frame):
    limpiar_contenido(contenido_frame)
    ctk.CTkLabel(contenido_frame, text="Historial de Alertas", font=("Arial", 20, "bold")).pack(pady=(20, 5))
    ctk.CTkLabel(contenido_frame, text="Aquí puedes ver todas las alertas, incluyendo las resueltas y las leídas.", font=("Arial", 12), text_color="#555").pack(pady=(0, 20))
    ctk.CTkButton(contenido_frame, text="⬅️ Volver a Alertas Vigentes", command=lambda: mostrar_alertas(contenido_frame) if 'mostrar_alertas' in globals() else None, font=("Arial", 12), fg_color="#8e44ad", hover_color="#7e329d", width=220).pack(pady=10)
    scroll = ctk.CTkScrollableFrame(contenido_frame, fg_color="transparent")
    scroll.pack(fill="both", expand=True, padx=20, pady=10)
    filtros_frame = ctk.CTkFrame(scroll, fg_color="#f2f2f2", corner_radius=10)
    filtros_frame.pack(fill="x", padx=5, pady=(0, 10))
    ctk.CTkLabel(filtros_frame, text="Filtros", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w", columnspan=6)
    entry_buscar = ctk.CTkEntry(filtros_frame, width=300, placeholder_text="Buscar por descripción…")
    entry_buscar.grid(row=1, column=0, padx=10, pady=10, sticky="w")
    estado_var = tk.StringVar(value="Todos")
    ctk.CTkLabel(filtros_frame, text="Estado:", font=("Arial", 11)).grid(row=1, column=1, padx=(10,4), pady=10, sticky="e")
    estado_menu = ctk.CTkOptionMenu(filtros_frame, variable=estado_var, values=["Todos", "Activa", "Resuelta", "Desconocida"], width=140)
    estado_menu.grid(row=1, column=2, padx=(0,10), pady=10, sticky="w")
    nivel_var = tk.StringVar(value="Todos")
    ctk.CTkLabel(filtros_frame, text="Nivel:", font=("Arial", 11)).grid(row=1, column=3, padx=(10,4), pady=10, sticky="e")
    nivel_menu = ctk.CTkOptionMenu(filtros_frame, variable=nivel_var, values=["Todos", "Agotado", "Crítico", "Bajo"], width=140)
    nivel_menu.grid(row=1, column=4, padx=(0,10), pady=10, sticky="w")
    btn_buscar = ctk.CTkButton(filtros_frame, text="🔎 Buscar", width=120, fg_color="#3498db", hover_color="#2d7fb8")
    btn_buscar.grid(row=1, column=5, padx=6, pady=10)
    btn_limpiar = ctk.CTkButton(filtros_frame, text="Limpiar", width=110, fg_color="#95a5a6", hover_color="#7f8c8d")
    btn_limpiar.grid(row=1, column=6, padx=(0,10), pady=10)
    info_label = ctk.CTkLabel(scroll, text="", font=("Arial", 11), text_color="#7f8c8d")
    info_label.pack(pady=(0,6))
    items_container = ctk.CTkFrame(scroll, fg_color="transparent")
    items_container.pack(fill="both", expand=True)
    loader = ctk.CTkLabel(scroll, text="", font=("Arial", 13, "italic"), text_color="#3498db")

    def pedir_filtros():
        return {"texto": entry_buscar.get().strip(), "estado": estado_var.get(), "nivel": nivel_var.get()}

    def limpiar_filtros():
        entry_buscar.delete(0, tk.END)
        estado_var.set("Todos")
        nivel_var.set("Todos")
        ejecutar_busqueda()

    def ejecutar_busqueda():
        info_label.configure(text="")
        for w in items_container.winfo_children(): w.destroy()
        loader.configure(text="⏳ Buscando…")
        loader.pack(pady=8)
        filtros = pedir_filtros()
        threading.Thread(target=lambda: _buscar_y_renderizar(items_container, info_label, loader, filtros), daemon=True).start()

    btn_buscar.configure(command=ejecutar_busqueda)
    btn_limpiar.configure(command=limpiar_filtros)
    ejecutar_busqueda()

def _buscar_y_renderizar(items_container, info_label, loader, filtros):
    filas = obtener_todas_las_alertas(filtros)
    items_container.after(0, lambda: _render_resultados(items_container, info_label, loader, filas))

def _render_resultados(items_container, info_label, loader, filas):
    try:
        loader.pack_forget()
    except Exception:
        pass
    for w in items_container.winfo_children():
        w.destroy()
    if not filas:
        info_label.configure(text="No se encontraron resultados con los filtros aplicados.")
        return
    info_label.configure(text=f"Resultados: {len(filas)}")
    for fila in filas:
        crear_linea_historial(items_container, fila)

def crear_linea_historial(parent, alerta):
    if not isinstance(alerta, (list, tuple)) or len(alerta) != 7:
        texto_crudo = " | ".join(str(v) for v in (alerta if isinstance(alerta, (list, tuple)) else [alerta]))
        frame = ctk.CTkFrame(parent, fg_color="#f8f9fa", border_width=1, border_color="#95a5a6", corner_radius=10)
        frame.pack(pady=6, fill="x", padx=5)
        ctk.CTkLabel(frame, text=texto_crudo, font=("Arial", 11), text_color="#2c3e50", justify="left", anchor="w").pack(pady=8, padx=10, fill="x")
        return
    id_alerta, descripcion, stock_actual, stock_minimo, nivel, estado, fecha_alerta = alerta
    estado_texto, color, icono = _estado_color_icono(nivel, estado)
    fecha_str = _fmt_fecha(fecha_alerta)
    card = ctk.CTkFrame(parent, fg_color="#ffffff", border_width=1, border_color=color, corner_radius=12)
    card.pack(pady=6, fill="x", padx=5)
    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=10, pady=(10, 4))
    ctk.CTkLabel(header, text=f"{icono}", font=("Arial", 16)).pack(side="left", padx=(0,6))
    ctk.CTkLabel(header, text=str(descripcion or "(Sin descripción)"), font=("Arial", 13, "bold"), text_color="#2c3e50").pack(side="left")
    badges = ctk.CTkFrame(card, fg_color="transparent")
    badges.pack(fill="x", padx=10, pady=(0, 6))
    _badge(badges, f"Estado: {estado_texto}", color).pack(side="left", padx=(0,6))
    _badge(badges, f"Nivel: {str(nivel or '-').capitalize()}", "#34495e").pack(side="left")
    pb_frame = ctk.CTkFrame(card, fg_color="transparent")
    pb_frame.pack(fill="x", padx=10, pady=(0, 6))
    try:
        s_act = float(stock_actual) if stock_actual is not None else 0.0
        s_min = float(stock_minimo) if stock_minimo is not None else 0.0
        progreso = 0.0 if s_min <= 0 else min(s_act / s_min, 1.0)
    except Exception:
        progreso = 0.0
    ctk.CTkLabel(pb_frame, text=f"Stock: {stock_actual if stock_actual is not None else '-'}  /  Mínimo: {stock_minimo if stock_minimo is not None else '-'}", font=("Arial", 11), text_color="#2c3e50").pack(anchor="w")
    bar = ctk.CTkProgressBar(pb_frame, height=10)
    bar.set(progreso)
    bar.pack(fill="x", pady=(4,0))
    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(footer, text=f"ID alerta: {id_alerta}", font=("Arial", 10), text_color="#7f8c8d").pack(side="left")
    ctk.CTkLabel(footer, text=f" · Fecha: {fecha_str}", font=("Arial", 10), text_color="#7f8c8d").pack(side="left")

def obtener_todas_las_alertas(filtros):
    texto = filtros.get("texto", "").strip()
    filtro_estado = filtros.get("estado", "Todos")
    filtro_nivel = filtros.get("nivel", "Todos")
    try:
        conn = conectar_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='desarrollo' AND table_name='alertas_stock'
        """)
        cols = {r[0] for r in cur.fetchall()}
        nivel_col = "nivel_alerta" if "nivel_alerta" in cols else ("nivel" if "nivel" in cols else None)
        estado_col = "estado" if "estado" in cols else None
        fecha_col  = "fecha_alerta" if "fecha_alerta" in cols else None
        nivel_expr = f"{nivel_col}" if nivel_col else "NULL::text"
        estado_expr = f"{estado_col}" if estado_col else "NULL::text"
        fecha_expr  = f"{fecha_col}" if fecha_col else "NULL::timestamp"
        select_sql = f"""
            SELECT
                id_alerta,
                descripcion_producto,
                stock_actual,
                stock_minimo,
                {nivel_expr} AS nivel,
                {estado_expr} AS estado,
                {fecha_expr} AS fecha_alerta
            FROM desarrollo.alertas_stock
        """
        where_parts = []
        params = []
        if texto and "descripcion_producto" in cols:
            where_parts.append("descripcion_producto ILIKE %s")
            params.append(f"%{texto}%")
        if filtro_estado in ("Activa", "Resuelta") and estado_col:
            where_parts.append(f"{estado_col} = %s")
            params.append(filtro_estado.upper())
        if filtro_nivel in ("Agotado", "Crítico", "Bajo") and nivel_col:
            target = {"Agotado": "AGOTADO", "Crítico": "CRITICO", "Bajo": "BAJO"}[filtro_nivel]
            where_parts.append(f"{nivel_col} = %s")
            params.append(target)
        if where_parts:
            select_sql += " WHERE " + " AND ".join(where_parts)
        if fecha_col:
            select_sql += " ORDER BY fecha_alerta DESC NULLS LAST, id_alerta DESC"
        else:
            select_sql += " ORDER BY id_alerta DESC"
        select_sql += " LIMIT 20"
        cur.execute(select_sql, params)
        filas = cur.fetchall()
        cur.close()
        conn.close()
        normalizadas = []
        for row in filas:
            if isinstance(row, (list, tuple)) and len(row) == 7:
                normalizadas.append(row)
            else:
                normalizadas.append(tuple(row))
        return normalizadas
    except Exception:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return []

def limpiar_contenido(contenido_frame):
    for widget in contenido_frame.winfo_children():
        widget.destroy()
