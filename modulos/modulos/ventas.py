import customtkinter as ctk
import tkinter.ttk as ttk
from bd import conectar_db
from tkinter import messagebox

def mostrar_ventas(frame_destino):
    # Limpiar frame anterior
    for widget in frame_destino.winfo_children():
        widget.destroy()

    # ============================================================
    # 1. ESTILOS VISUALES (IGUAL QUE EN STOCK)
    # ============================================================
    style = ttk.Style()
    style.theme_use("clam")
    
    style.configure("Treeview",
                    background="white",
                    foreground="#2c3e50",
                    rowheight=35,
                    fieldbackground="white",
                    bordercolor="#dcdcdc",
                    borderwidth=0,
                    font=("Arial", 11))
    
    style.configure("Treeview.Heading",
                    background="#f1f2f6",
                    foreground="#34495e",
                    relief="flat",
                    font=("Arial", 11, "bold"))
    
    style.map("Treeview",
              background=[('selected', '#3498db')],
              foreground=[('selected', 'white')])

    # ============================================================
    # 2. ESTRUCTURA PRINCIPAL (GRID LAYOUT)
    # ============================================================
    main_frame = ctk.CTkFrame(frame_destino, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 0))

    # Configuración de Grid para expansión total
    main_frame.grid_rowconfigure(2, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    # --- Header (Fila 0) ---
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    
    # Título con contador (se actualiza al cargar)
    lbl_titulo = ctk.CTkLabel(header_frame, text="💰 Historial de Ventas", font=("Arial", 24, "bold"), text_color="#2c3e50")
    lbl_titulo.pack(side="left")

    # --- Barra de Herramientas (Fila 1) ---
    toolbar_frame = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    toolbar_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10), ipady=5)

    # Filtros (Izquierda)
    ctk.CTkLabel(toolbar_frame, text="🔍", font=("Arial", 16)).pack(side="left", padx=(20, 5))

    # Usamos Entry directos (sin StringVar) para que funcionen los placeholders
    entry_cliente = ctk.CTkEntry(toolbar_frame, placeholder_text="Filtrar por Cliente...", width=200)
    entry_cliente.pack(side="left", padx=5)

    entry_fecha = ctk.CTkEntry(toolbar_frame, placeholder_text="Fecha (DD/MM/YYYY)...", width=180)
    entry_fecha.pack(side="left", padx=5)

    ctk.CTkButton(toolbar_frame, text="Buscar", width=80, fg_color="#34495e", hover_color="#2c3e50", 
                  command=lambda: cargar_ventas()).pack(side="left", padx=10)

    # Botón de Acción Principal (Derecha)
    # "Ver Detalle" ahora está arriba, más accesible
    btn_detalle = ctk.CTkButton(toolbar_frame, text="📄 Ver Detalle de la Venta", width=160, 
                                fg_color="#f39c12", hover_color="#d35400",
                                command=lambda: ver_detalle_venta())
    btn_detalle.pack(side="right", padx=(5, 20))

    # ============================================================
    # 3. TABLA DE VENTAS (Fila 2)
    # ============================================================
    table_container = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    table_container.grid(row=2, column=0, sticky="nsew", pady=(0, 20))

    table_container.grid_rowconfigure(0, weight=1)
    table_container.grid_columnconfigure(0, weight=1)

    scrollbar_y = ttk.Scrollbar(table_container, orient="vertical")
    scrollbar_x = ttk.Scrollbar(table_container, orient="horizontal")

    # Columnas (He ocultado ID de producto o usuario si no son relevantes visualmente, pero siguen en datos)
    # Mantengo tus columnas originales
    columnas = ("Comprobante", "Tipo", "Monto Unit", "Total", "ID Prod", "Producto", "Cliente", "Factura", "Cant", "Usuario", "Fecha")
    
    tree = ttk.Treeview(table_container, columns=columnas, show="headings", 
                        yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    scrollbar_y.config(command=tree.yview)
    scrollbar_x.config(command=tree.xview)

    tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    scrollbar_y.grid(row=0, column=1, sticky="ns", pady=5, padx=(0, 5))
    scrollbar_x.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))

    # Configuración de columnas
    col_widths = {
        "Comprobante": 100, "Tipo": 100, "Monto Unit": 100, "Total": 100, 
        "ID Prod": 60, "Producto": 200, "Cliente": 150, "Factura": 80, 
        "Cant": 60, "Usuario": 100, "Fecha": 140
    }
    
    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, anchor="center" if col != "Producto" else "w", width=col_widths.get(col, 100))

    # ============================================================
    # 4. LÓGICA DE DATOS
    # ============================================================
    def cargar_ventas():
        tree.delete(*tree.get_children())
        
        # Obtener filtros directos
        cliente_filtro = entry_cliente.get().strip()
        fecha_filtro = entry_fecha.get().strip()

        query = """
            SELECT v_comprob, v_tipotransacc, v_montous_unit, v_montous_total, 
                   v_id_producto, v_product, v_id_cliente, v_fact, v_cantidad, v_user, 
                   TO_CHAR(v_fecha, 'DD/MM/YYYY HH24:MI:SS')
            FROM desarrollo.ventas
            WHERE 1=1
        """
        params = []

        if cliente_filtro:
            # Verificamos si el usuario escribió solo números (es un ID)
            if cliente_filtro.isdigit():
                # Búsqueda EXACTA por ID (soluciona tu problema)
                query += " AND v_id_cliente = %s"
                params.append(cliente_filtro)
            else:
                # Si escribió letras, buscamos por el NOMBRE del cliente
                # (Asumiendo que 'v_cliente' es la columna del nombre en tu tabla)
                query += " AND v_cliente ILIKE %s"
                params.append(f"%{cliente_filtro}%")
        
        if fecha_filtro:
            query += " AND TO_CHAR(v_fecha, 'DD/MM/YYYY')::text LIKE %s"
            params.append(f"%{fecha_filtro}%")

        query += " ORDER BY v_fecha DESC"

        try:
            conn = conectar_db()
            cur = conn.cursor()
            cur.execute(query, params)
            filas = cur.fetchall()
            
            for row in filas:
                # Desempaquetar para formatear dinero
                (v_comp, v_tipo, v_m_unit, v_m_total, v_id_p, v_prod, v_cli, v_fact, v_cant, v_user, v_fecha) = row
                
                # Formato bonito de dinero
                unit_fmt = f"${v_m_unit:,.0f}" if v_m_unit else "$0"
                total_fmt = f"${v_m_total:,.0f}" if v_m_total else "$0"

                tree.insert("", "end", values=(v_comp, v_tipo, unit_fmt, total_fmt, v_id_p, v_prod, v_cli, v_fact, v_cant, v_user, v_fecha))
            
            cur.close()
            conn.close()
            
            # Actualizar título
            lbl_titulo.configure(text=f"💰 Historial de Ventas ({len(filas)} registros)")

        except Exception as e:
            print(f"Error cargando ventas: {e}")
            messagebox.showerror("Error", f"Error al cargar datos: {e}")

    # ============================================================
    # 5. DETALLE DE VENTA (POPUP)
    # ============================================================
    def ver_detalle_venta(event=None):
        seleccionado = tree.selection()
        if not seleccionado:
            messagebox.showinfo("Información", "Por favor selecciona una venta de la tabla.")
            return

        item = tree.item(seleccionado[0])
        valores = item["values"]
        
        # Obtenemos MÁS datos para filtrar con precisión
        nro_comprobante = valores[0] # Columna 0: Comprobante
        tipo_transacc = valores[1]   # Columna 1: Tipo de Transacción

        # --- Configuración Ventana ---
        detalle_win = ctk.CTkToplevel()
        detalle_win.title(f"Detalle {tipo_transacc} #{nro_comprobante}")
        detalle_win.geometry("900x600")
        detalle_win.transient(frame_destino.winfo_toplevel())
        detalle_win.grab_set()
        
        detalle_win.geometry("+%d+%d" % (detalle_win.winfo_screenwidth()/2 - 325, detalle_win.winfo_screenheight()/2 - 225))

        ctk.CTkLabel(detalle_win, text=f"Detalle de Venta #{nro_comprobante}", font=("Arial", 18, "bold"), text_color="#2c3e50").pack(pady=15)

        # --- Tabla ---
        frame_det = ctk.CTkFrame(detalle_win, fg_color="white", corner_radius=10)
        frame_det.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        cols_det = ("Producto", "Cant.", "Precio Unit.", "Subtotal")
        tree_det = ttk.Treeview(frame_det, columns=cols_det, show="headings")
        
        tree_det.heading("Producto", text="Producto"); tree_det.column("Producto", width=250, anchor="w")
        tree_det.heading("Cant.", text="Cant."); tree_det.column("Cant.", width=50, anchor="center")
        tree_det.heading("Precio Unit.", text="Precio Unit."); tree_det.column("Precio Unit.", width=100, anchor="center")
        tree_det.heading("Subtotal", text="Subtotal"); tree_det.column("Subtotal", width=100, anchor="center")

        scroll_y = ttk.Scrollbar(frame_det, orient="vertical", command=tree_det.yview)
        tree_det.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        tree_det.pack(side="left", fill="both", expand=True)

        try:
            conn = conectar_db()
            cur = conn.cursor()
            
            # === CORRECCIÓN CLAVE AQUÍ ===
            # 1. Usamos DISTINCT para evitar duplicados exactos.
            # 2. Agregamos AND v_tipotransacc = %s para no mezclar comprobantes de distintos tipos.
            query = """
                SELECT DISTINCT v_product, v_cantidad, v_montous_unit, v_montous_total
                FROM desarrollo.ventas_detalle
                WHERE v_comprob = %s 
                  AND v_tipotransacc = %s
            """
            # Pasamos ambos parámetros
            cur.execute(query, (nro_comprobante, tipo_transacc))
            
            filas = cur.fetchall()
            total_calculado = 0
            
            for row in filas:
                prod, cant, unit, total = row
                
                # Validación para evitar errores si vienen nulos
                val_total = float(total) if total is not None else 0
                val_unit = float(unit) if unit is not None else 0
                
                total_calculado += val_total
                
                tree_det.insert("", "end", values=(prod, cant, f"${val_unit:,.0f}", f"${val_total:,.0f}"))
            
            cur.close()
            conn.close()

            # Footer
            footer_frame = ctk.CTkFrame(detalle_win, fg_color="transparent")
            footer_frame.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(footer_frame, text=f"Items: {len(filas)}", text_color="gray").pack(side="left")
            ctk.CTkLabel(footer_frame, text=f"TOTAL: ${total_calculado:,.0f}", font=("Arial", 18, "bold"), text_color="#2ecc71").pack(side="right")

        except Exception as e:
            messagebox.showerror("Error", f"Error SQL: {e}")
            
        ctk.CTkButton(detalle_win, text="Cerrar", fg_color="#95a5a6", command=detalle_win.destroy).pack(pady=(0, 15))

    # Eventos y Carga Inicial
    entry_cliente.bind("<Return>", lambda e: cargar_ventas())
    entry_fecha.bind("<Return>", lambda e: cargar_ventas())
    
    # Doble clic en la tabla abre el detalle
    tree.bind("<Double-1>", ver_detalle_venta)

    cargar_ventas()
