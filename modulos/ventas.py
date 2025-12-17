import customtkinter as ctk
import tkinter.ttk as ttk
from bd import conectar_db
from tkinter import messagebox

def mostrar_ventas(frame_destino):
    # Limpiar frame anterior
    for widget in frame_destino.winfo_children():
        widget.destroy()

    # ============================================================
    # 1. ESTILOS VISUALES
    # ============================================================
    style = ttk.Style()
    style.theme_use("clam")
    
    style.configure("Treeview",
                    background="white", foreground="#2c3e50", rowheight=35, fieldbackground="white",
                    bordercolor="#dcdcdc", borderwidth=0, font=("Arial", 11))
    
    style.configure("Treeview.Heading",
                    background="#f1f2f6", foreground="#34495e", relief="flat", font=("Arial", 11, "bold"))
    
    style.map("Treeview", background=[('selected', '#3498db')], foreground=[('selected', 'white')])

    # ============================================================
    # 2. ESTRUCTURA PRINCIPAL
    # ============================================================
    main_frame = ctk.CTkFrame(frame_destino, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 0))

    main_frame.grid_rowconfigure(2, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    # --- Header ---
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    lbl_titulo = ctk.CTkLabel(header_frame, text="💰 Historial de Ventas", font=("Arial", 24, "bold"), text_color="#2c3e50")
    lbl_titulo.pack(side="left")

    # --- Barra de Herramientas (FILTROS) ---
    toolbar_frame = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    toolbar_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10), ipady=5)

    ctk.CTkLabel(toolbar_frame, text="🔍", font=("Arial", 16)).pack(side="left", padx=(20, 5))

    # 1. Filtro Comprobante (NUEVO)
    entry_comp = ctk.CTkEntry(toolbar_frame, placeholder_text="Nro Comprobante...", width=150)
    entry_comp.pack(side="left", padx=5)

    # 2. Filtro Cliente
    entry_cliente = ctk.CTkEntry(toolbar_frame, placeholder_text="Cliente...", width=200)
    entry_cliente.pack(side="left", padx=5)

    # 3. Filtro Fecha
    entry_fecha = ctk.CTkEntry(toolbar_frame, placeholder_text="Fecha (DD/MM/YYYY)...", width=150)
    entry_fecha.pack(side="left", padx=5)

    ctk.CTkButton(toolbar_frame, text="Buscar", width=80, fg_color="#34495e", hover_color="#2c3e50", 
                  command=lambda: cargar_ventas()).pack(side="left", padx=10)

    btn_detalle = ctk.CTkButton(toolbar_frame, text="📄 Ver Detalle Completo", width=160, 
                                fg_color="#f39c12", hover_color="#d35400",
                                command=lambda: ver_detalle_venta())
    btn_detalle.pack(side="right", padx=(5, 20))

    # ============================================================
    # 3. TABLA PRINCIPAL
    # ============================================================
    table_container = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    table_container.grid(row=2, column=0, sticky="nsew", pady=(0, 20))

    table_container.grid_rowconfigure(0, weight=1)
    table_container.grid_columnconfigure(0, weight=1)

    scrollbar_y = ttk.Scrollbar(table_container, orient="vertical")
    scrollbar_x = ttk.Scrollbar(table_container, orient="horizontal")

    columnas = ("Comprobante", "Tipo", "Total Factura", "Cliente", "Fact. Ref", "Cant. Items", "Usuario", "Fecha")
    
    tree = ttk.Treeview(table_container, columns=columnas, show="headings", 
                        yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    scrollbar_y.config(command=tree.yview)
    scrollbar_x.config(command=tree.xview)
    
    tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    scrollbar_y.grid(row=0, column=1, sticky="ns", pady=5, padx=(0, 5))
    scrollbar_x.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))

    for col in columnas:
        tree.heading(col, text=col)
        w = 100
        if col == "Cliente": w = 200
        if col == "Fecha": w = 140
        tree.column(col, anchor="center", width=w)

    # ============================================================
    # 4. LÓGICA DE CARGA (Con nuevo filtro)
    # ============================================================
    def cargar_ventas():
        tree.delete(*tree.get_children())
        
        # Obtenemos valores de los inputs
        filtro_comp = entry_comp.get().strip() ### NUEVO
        filtro_cli = entry_cliente.get().strip()
        filtro_fec = entry_fecha.get().strip()

        # Query Base
        query = """
            SELECT 
                v_comprob, 
                v_tipotransacc, 
                SUM(v_montous_total) as total_factura, 
                MAX(v_cliente) as nombre_cliente,
                v_fact, 
                COUNT(*) as items_fisicos, 
                MAX(v_user), 
                TO_CHAR(MAX(v_fecha), 'DD/MM/YYYY HH24:MI:SS')
            FROM desarrollo.ventas
            WHERE 1=1
        """
        params = []

        # --- APLICACIÓN DE FILTROS ---
        if filtro_comp: ### NUEVO LÓGICA
            query += " AND CAST(v_comprob AS TEXT) ILIKE %s"
            params.append(f"%{filtro_comp}%")

        if filtro_cli:
            if filtro_cli.isdigit():
                query += " AND v_id_cliente = %s"
                params.append(filtro_cli)
            else:
                query += " AND v_cliente ILIKE %s"
                params.append(f"%{filtro_cli}%")
        
        if filtro_fec:
            query += " AND TO_CHAR(v_fecha, 'DD/MM/YYYY')::text LIKE %s"
            params.append(f"%{filtro_fec}%")

        # Group By
        query += """
            GROUP BY v_comprob, v_tipotransacc, v_fact, v_id_cliente
            ORDER BY MAX(v_fecha) DESC
        """

        try:
            conn = conectar_db()
            cur = conn.cursor()
            cur.execute(query, params)
            filas = cur.fetchall()
            
            for row in filas:
                (v_comp, v_tipo, v_total, v_nom, v_fact_ref, v_cant, v_usr, v_date) = row
                
                total_fmt = f"${v_total:,.0f}" if v_total else "$0"
                v_comp_str = str(v_comp) # Asegurar string

                tree.insert("", "end", values=(
                    v_comp_str, v_tipo, total_fmt, v_nom, v_fact_ref, v_cant, v_usr, v_date
                ))
            
            cur.close()
            conn.close()
            lbl_titulo.configure(text=f"💰 Historial de Ventas ({len(filas)} registros)")

        except Exception as e:
            messagebox.showerror("Error", f"Error SQL: {e}")
            print(e)

    # ============================================================
    # 5. DETALLE "FULL" (Mostrar todo)
    # ============================================================
    def ver_detalle_venta(event=None):
        seleccionado = tree.selection()
        if not seleccionado:
            return

        item = tree.item(seleccionado[0])
        valores = item["values"]
        
        nro_comprobante = str(valores[0]) 
        tipo_transacc = valores[1]   

        # Ventana más ancha para ver todo
        detalle_win = ctk.CTkToplevel()
        detalle_win.title(f"Detalle Completo #{nro_comprobante}")
        detalle_win.geometry("1200x600") # Aumenté el ancho
        detalle_win.transient(frame_destino.winfo_toplevel())
        detalle_win.grab_set()
        detalle_win.geometry("+%d+%d" % (detalle_win.winfo_screenwidth()/2 - 550, detalle_win.winfo_screenheight()/2 - 300))

        ctk.CTkLabel(detalle_win, text=f"Detalle Extendido: {tipo_transacc} #{nro_comprobante}", 
                     font=("Arial", 18, "bold"), text_color="#2c3e50").pack(pady=15)

        # Frame Tabla
        frame_det = ctk.CTkFrame(detalle_win, fg_color="white", corner_radius=10)
        frame_det.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- COLUMNAS EXTENDIDAS ---
        # Agregamos ID Producto, Guaraníes, Cotización, Usuario, Estado y Comentario
        cols_det = ("ID Prod", "Producto", "Cant", "P. Unit ($)", "Total ($)", "Total (Gs)", "Cotiz", "Usuario", "Estado", "Comentario")
        
        tree_det = ttk.Treeview(frame_det, columns=cols_det, show="headings")
        
        # Configuración de anchos
        tree_det.heading("ID Prod", text="ID");        tree_det.column("ID Prod", width=60, anchor="center")
        tree_det.heading("Producto", text="Producto");  tree_det.column("Producto", width=250, anchor="w")
        tree_det.heading("Cant", text="Cant");          tree_det.column("Cant", width=50, anchor="center")
        tree_det.heading("P. Unit ($)", text="Unit ($)"); tree_det.column("P. Unit ($)", width=80, anchor="e")
        tree_det.heading("Total ($)", text="Total ($)");  tree_det.column("Total ($)", width=80, anchor="e")
        tree_det.heading("Total (Gs)", text="Total (Gs)");tree_det.column("Total (Gs)", width=100, anchor="e")
        tree_det.heading("Cotiz", text="Cotiz");        tree_det.column("Cotiz", width=60, anchor="center")
        tree_det.heading("Usuario", text="User");       tree_det.column("Usuario", width=60, anchor="center")
        tree_det.heading("Estado", text="Estado");      tree_det.column("Estado", width=80, anchor="center")
        tree_det.heading("Comentario", text="Comentario");tree_det.column("Comentario", width=150, anchor="w")

        # Scrollbars (Importante el horizontal por tantas columnas)
        scroll_y = ttk.Scrollbar(frame_det, orient="vertical", command=tree_det.yview)
        scroll_x = ttk.Scrollbar(frame_det, orient="horizontal", command=tree_det.xview)
        tree_det.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        tree_det.pack(side="left", fill="both", expand=True)

        try:
            conn = conectar_db()
            cur = conn.cursor()
            
            # Consultamos TODOS los campos relevantes
            query = """
                SELECT 
                    v_id_product,
                    v_product, 
                    v_cantidad,
                    v_montous_unit,
                    v_montous_total,
                    v_montogs,
                    v_cotiz,
                    v_user,
                    v_estado,
                    v_comentario
                FROM desarrollo.ventas_detalle
                WHERE CAST(v_comprob AS TEXT) = %s 
                  AND v_tipotransacc = %s
                ORDER BY v_product
            """
            cur.execute(query, (nro_comprobante, tipo_transacc))
            filas = cur.fetchall()
            
            total_us = 0
            total_gs = 0

            for row in filas:
                (id_p, prod, cant, unit_us, tot_us, tot_gs, cot, usr, est, com) = row
                
                # Convertir a float seguro
                f_cant = float(cant) if cant else 0
                f_unit = float(unit_us) if unit_us else 0
                f_tot_us = float(tot_us) if tot_us else 0
                f_tot_gs = float(tot_gs) if tot_gs else 0
                f_cot = float(cot) if cot else 0

                total_us += f_tot_us
                total_gs += f_tot_gs

                # Formateo
                tree_det.insert("", "end", values=(
                    id_p,
                    prod,
                    f"{f_cant:g}",
                    f"${f_unit:,.2f}",
                    f"${f_tot_us:,.2f}",
                    f"₲{f_tot_gs:,.0f}",
                    f"{f_cot:,.0f}",
                    usr,
                    est,
                    com
                ))
            
            cur.close()
            conn.close()

            # Footer
            footer_frame = ctk.CTkFrame(detalle_win, fg_color="transparent")
            footer_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(footer_frame, text=f"Registros: {len(filas)}", text_color="gray").pack(side="left")
            
            # Totales a la derecha
            resumen = f"TOTAL US$: {total_us:,.2f}  |  TOTAL GS: {total_gs:,.0f}"
            ctk.CTkLabel(footer_frame, text=resumen, font=("Arial", 16, "bold"), text_color="#2ecc71").pack(side="right")

        except Exception as e:
            messagebox.showerror("Error", f"Error SQL: {e}")
            
        ctk.CTkButton(detalle_win, text="Cerrar", fg_color="#95a5a6", command=detalle_win.destroy).pack(pady=(0, 15))

    # Binds
    entry_comp.bind("<Return>", lambda e: cargar_ventas())
    entry_cliente.bind("<Return>", lambda e: cargar_ventas())
    entry_fecha.bind("<Return>", lambda e: cargar_ventas())
    tree.bind("<Double-1>", ver_detalle_venta)

    cargar_ventas()