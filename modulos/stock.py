# modulos/stock.py
from tkinter import messagebox
import customtkinter as ctk
from sqlalchemy import null
from bd import conectar_db
import tkinter.ttk as ttk
from decimal import Decimal, InvalidOperation

def mostrar_productos(frame_destino):
    # Limpiar el frame anterior
    for widget in frame_destino.winfo_children():
        widget.destroy()

    # ============================================================
    # 1. ESTILOS VISUALES PARA LA TABLA (MODERNO)
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
    # 2. ESTRUCTURA PRINCIPAL (LAYOUT)
    # ============================================================
    main_frame = ctk.CTkFrame(frame_destino, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 5)) 

    # --- Header (Título) ---
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", pady=(0, 10)) 
    
    lbl_titulo = ctk.CTkLabel(header_frame, text="📦 Gestión de Inventario", font=("Arial", 24, "bold"), text_color="#2c3e50")
    lbl_titulo.pack(side="left")

    # --- Barra de Herramientas ---
    toolbar_frame = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    toolbar_frame.pack(fill="x", pady=(0, 10), ipady=5)

    # [SECCIÓN IZQUIERDA] Filtros
    ctk.CTkLabel(toolbar_frame, text="🔍", font=("Arial", 16)).pack(side="left", padx=(20, 5))
    
    entry_desc = ctk.CTkEntry(toolbar_frame, placeholder_text="Buscar por descripción o código...", width=220)
    entry_desc.pack(side="left", padx=5)
    
    entry_cat = ctk.CTkEntry(toolbar_frame, placeholder_text="Categoría...", width=150)
    entry_cat.pack(side="left", padx=5)

    ctk.CTkButton(toolbar_frame, text="Buscar", width=80, fg_color="#34495e", hover_color="#2c3e50", 
                  command=lambda: cargar_articulos()).pack(side="left", padx=10)

    # [SECCIÓN DERECHA] Botones
    ctk.CTkButton(toolbar_frame, text="🗑 Eliminar", width=100, fg_color="#e74c3c", hover_color="#c0392b",
                  command=lambda: eliminar_producto()).pack(side="right", padx=(5, 20))

    ctk.CTkButton(toolbar_frame, text="+ Nuevo Producto", width=140, fg_color="#2ecc71", hover_color="#27ae60",
                  command=lambda: abrir_formulario_agregar()).pack(side="right", padx=5)

    ctk.CTkButton(toolbar_frame, text="🗑 Eliminar Categoria", width=120, fg_color="#e74c3c", hover_color="#c0392b",
                  command=lambda: eliminar_categoria()).pack(side="right", padx=5)

    ctk.CTkButton(toolbar_frame, text="+ Agregar Categorías", width=120, fg_color="#2ecc71", hover_color="#27ae60",
                  command=lambda: agregar_categoria()).pack(side="right", padx=5)
    
    # ============================================================
    # 3. TABLA DE DATOS (TREEVIEW MODIFICADO)
    # ============================================================
    table_container = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    table_container.pack(fill="both", expand=True, pady=(0, 10))

    scrollbar_y = ttk.Scrollbar(table_container, orient="vertical")
    scrollbar_x = ttk.Scrollbar(table_container, orient="horizontal")

    # NUEVAS COLUMNAS
    columnas = ("ID", "Cód. Barras", "Descripción", "Moneda", "Precio Unit", "Inventario", "Categoría", "Precio Total")
    tree = ttk.Treeview(table_container, columns=columnas, show="headings", 
                        yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    scrollbar_y.config(command=tree.yview)
    scrollbar_x.config(command=tree.xview)

    scrollbar_y.pack(side="right", fill="y", padx=(0, 2), pady=2)
    scrollbar_x.pack(side="bottom", fill="x", padx=2, pady=(0, 2))
    tree.pack(side="left", fill="both", expand=True, padx=5, pady=5) 
    
    # Configuración de Cabeceras
    col_widths = {
        "ID": 50, "Cód. Barras": 120, "Descripción": 280, 
        "Moneda": 70, "Precio Unit": 100, "Inventario": 80, 
        "Categoría": 130, "Precio Total": 100
    }
    for col in columnas:
        tree.heading(col, text=col)
        anchor_type = "w" if col == "Descripción" else "center"
        tree.column(col, anchor=anchor_type, width=col_widths.get(col, 100))

    # --- Función para cargar artículos ---
    def cargar_articulos():
        tree.delete(*tree.get_children())
        
        desc_filtro = entry_desc.get().strip()
        cat_filtro = entry_cat.get().strip()

        # QUERY ACTUALIZADA
        query = """
            SELECT id_articulo, descripcion, precio_unit, cant_inventario, categoria, precio_total, moneda, codigo_barras
            FROM desarrollo.stock
            WHERE 1=1
        """
        params = []
        
        if desc_filtro:
            # Busca tanto en descripción como en el código de barras
            query += " AND (descripcion ILIKE %s OR codigo_barras ILIKE %s)"
            params.extend([f"%{desc_filtro}%", f"%{desc_filtro}%"])
        if cat_filtro:
            query += " AND categoria ILIKE %s"
            params.append(f"%{cat_filtro}%")
        
        query += " ORDER BY id_articulo DESC"

        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute(query, params)
            filas = cursor.fetchall()
            
            for row in filas:
                id_art, descripcion, precio, stock, categoria, total, moneda, cod_barras = row
                
                moneda_str = moneda if moneda else "USD"
                cb_str = cod_barras if cod_barras else "Sin código"
                simbolo = "$" if moneda_str == "USD" else "Gs."
                
                precio_fmt = f"{simbolo}{precio:,.2f}" if precio is not None else f"{simbolo}0.00"
                total_fmt = f"{simbolo}{total:,.2f}" if total is not None else f"{simbolo}0.00"
                
                tree.insert("", "end", values=(id_art, cb_str, descripcion, moneda_str, precio_fmt, stock, categoria, total_fmt))
            
            cursor.close()
            conn.close()
            
            try: lbl_titulo.configure(text=f"📦 Gestión de Inventario ({len(filas)} productos)")
            except: pass
            
        except Exception as e:
            print(f"Error al filtrar: {e}")

    entry_desc.bind("<Return>", lambda event: cargar_articulos())
    entry_cat.bind("<Return>", lambda event: cargar_articulos())
    
    # --- Formulario de Edición ---
    def abrir_formulario_editar(event):
        seleccion = tree.selection()
        if not seleccion: return
            
        item = tree.item(seleccion[0])
        datos = item["values"]
        
        id_art = datos[0]
        cod_barras_actual = str(datos[1]) if datos[1] != "Sin código" else ""
        desc_actual = datos[2]
        moneda_actual = datos[3]
        
        try:
            precio_limpio = str(datos[4]).replace("$", "").replace("Gs.", "").replace(",", "").strip()
            stock_actual = str(datos[5])
        except:
            precio_limpio = "0"
            stock_actual = "0"

        cat_actual = datos[6]

        edit_win = ctk.CTkToplevel()
        edit_win.title(f"Editar Producto #{id_art}")
        edit_win.geometry("500x500") # Ventana más alta
        edit_win.transient(frame_destino.winfo_toplevel())
        edit_win.grab_set()
        edit_win.geometry("+%d+%d" % (edit_win.winfo_screenwidth()/2 - 250, edit_win.winfo_screenheight()/2 - 250))

        ctk.CTkLabel(edit_win, text="Editar Producto", font=("Arial", 20, "bold"), text_color="#2c3e50").pack(pady=20)

        content = ctk.CTkFrame(edit_win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=40)

        var_desc = ctk.StringVar(value=desc_actual)
        var_precio = ctk.StringVar(value=precio_limpio)
        var_stock = ctk.StringVar(value=stock_actual)
        var_cat = ctk.StringVar(value=cat_actual)
        var_moneda = ctk.StringVar(value=moneda_actual)
        var_cod_barras = ctk.StringVar(value=cod_barras_actual)

        # CAMPOS
        ctk.CTkLabel(content, text="Cód. Barras:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=10)
        entry_cod_ed = ctk.CTkEntry(content, textvariable=var_cod_barras, width=280)
        entry_cod_ed.grid(row=0, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Descripción:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=10)
        entry_desc_ed = ctk.CTkEntry(content, textvariable=var_desc, width=280)
        entry_desc_ed.grid(row=1, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Moneda:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=10)
        combo_moneda_ed = ctk.CTkOptionMenu(content, variable=var_moneda, values=["USD", "GS"], width=150)
        combo_moneda_ed.grid(row=2, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Precio Unit:", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="w", pady=10)
        entry_precio_ed = ctk.CTkEntry(content, textvariable=var_precio, width=150)
        entry_precio_ed.grid(row=3, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Stock:", font=("Arial", 12, "bold")).grid(row=4, column=0, sticky="w", pady=10)
        entry_stock_ed = ctk.CTkEntry(content, textvariable=var_stock, width=150)
        entry_stock_ed.grid(row=4, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Categoría:", font=("Arial", 12, "bold")).grid(row=5, column=0, sticky="w", pady=10)
        cats = obtener_categorias_existentes()
        combo_cat_ed = ttk.Combobox(content, textvariable=var_cat, values=cats, width=32)
        combo_cat_ed.grid(row=5, column=1, sticky="w", pady=10, padx=10)

        def guardar_cambios():
            try:
                n_cod = var_cod_barras.get().strip() or None
                n_desc = var_desc.get().strip()
                n_precio = float(var_precio.get())
                n_stock = int(var_stock.get())
                n_cat = var_cat.get().strip()
                n_mon = var_moneda.get()
                n_total = n_precio * n_stock

                if not messagebox.askyesno("Confirmar", "¿Guardar cambios?"):
                    return

                conn = conectar_db()
                cur = conn.cursor()
                
                sql = """
                    UPDATE desarrollo.stock 
                    SET descripcion=%s, precio_unit=%s, cant_inventario=%s, categoria=%s, precio_total=%s, moneda=%s, codigo_barras=%s
                    WHERE id_articulo=%s
                """
                cur.execute(sql, (n_desc, n_precio, n_stock, n_cat, n_total, n_mon, n_cod, id_art))
                conn.commit()
                cur.close()
                conn.close()
                
                edit_win.destroy()
                cargar_articulos() 
                messagebox.showinfo("Éxito", "Producto actualizado.")
                
            except Exception as e:
                error_str = str(e).lower()
                # Traducimos el error de código duplicado
                if "duplicate key" in error_str or "unique constraint" in error_str:
                    messagebox.showerror("Código Duplicado", "No se pudo actualizar el producto.\n\nEl Código de Barras ingresado ya está siendo usado por otro producto.")
                else:
                    messagebox.showerror("Error", f"Error al actualizar:\n{e}")
                
        ctk.CTkButton(edit_win, text="Guardar Cambios", command=guardar_cambios, fg_color="#2ecc71", width=200).pack(pady=30)

    tree.bind("<Double-1>", abrir_formulario_editar)
    acciones_frame = ctk.CTkFrame(main_frame)
    acciones_frame.pack(pady=5, fill="x")

    def obtener_categorias_existentes():
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT gar_categoria FROM desarrollo.garantias ORDER BY gar_categoria")
            categorias = [row[0] for row in cursor.fetchall() if row[0]]
            cursor.close()
            conn.close()
            return categorias
        except Exception as e:
            return []

    def abrir_formulario_agregar():
        form = ctk.CTkToplevel()
        form.title("Nuevo Producto")
        form.geometry("500x500") 
        form.transient(frame_destino.winfo_toplevel()) 
        form.grab_set() 
        form.geometry("+%d+%d" % (form.winfo_screenwidth()/2 - 250, form.winfo_screenheight()/2 - 250))

        ctk.CTkLabel(form, text="Registrar Nuevo Producto", font=("Arial", 20, "bold"), text_color="#2c3e50").pack(pady=(20, 15))

        content_frame = ctk.CTkFrame(form, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=40)

        cod_barras_var = ctk.StringVar()
        desc_var = ctk.StringVar()
        moneda_var = ctk.StringVar(value="USD")
        precio_var = ctk.StringVar()
        stock_var = ctk.StringVar()
        categoria_var = ctk.StringVar()

        # CAMPOS
        ctk.CTkLabel(content_frame, text="Cód. Barras:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=10)
        entry_cod = ctk.CTkEntry(content_frame, textvariable=cod_barras_var, width=280, placeholder_text="Opcional / Escanear aquí")
        entry_cod.grid(row=0, column=1, sticky="w", pady=10, padx=(10, 0))

        ctk.CTkLabel(content_frame, text="Descripción:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=10)
        entry_desc = ctk.CTkEntry(content_frame, textvariable=desc_var, width=280, placeholder_text="Ej: Monitor LED 24 pulg")
        entry_desc.grid(row=1, column=1, sticky="w", pady=10, padx=(10, 0))

        ctk.CTkLabel(content_frame, text="Moneda:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=10)
        combo_moneda = ctk.CTkOptionMenu(content_frame, variable=moneda_var, values=["USD", "GS"], width=150)
        combo_moneda.grid(row=2, column=1, sticky="w", pady=10, padx=(10, 0))

        ctk.CTkLabel(content_frame, text="Precio Unitario:", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="w", pady=10)
        entry_precio = ctk.CTkEntry(content_frame, textvariable=precio_var, width=150, placeholder_text="0.00")
        entry_precio.grid(row=3, column=1, sticky="w", pady=10, padx=(10, 0))

        ctk.CTkLabel(content_frame, text="Stock Inicial:", font=("Arial", 12, "bold")).grid(row=4, column=0, sticky="w", pady=10)
        entry_stock = ctk.CTkEntry(content_frame, textvariable=stock_var, width=150, placeholder_text="0")
        entry_stock.grid(row=4, column=1, sticky="w", pady=10, padx=(10, 0))

        ctk.CTkLabel(content_frame, text="Categoría:", font=("Arial", 12, "bold")).grid(row=5, column=0, sticky="w", pady=10)
        categorias_disponibles = obtener_categorias_existentes()
        combo_cat = ttk.Combobox(content_frame, textvariable=categoria_var, values=categorias_disponibles, width=32, font=("Arial", 11))
        combo_cat.grid(row=5, column=1, sticky="w", pady=10, padx=(10, 0))

        def autocompletar_categoria(event):
            texto = categoria_var.get().lower()
            if texto:
                coincidencias = [cat for cat in categorias_disponibles if texto in cat.lower()]
                combo_cat['values'] = coincidencias
            else:
                combo_cat['values'] = categorias_disponibles

        combo_cat.bind('<KeyRelease>', autocompletar_categoria)

        lbl_error = ctk.CTkLabel(form, text="", text_color="#e74c3c", font=("Arial", 11))
        lbl_error.pack(pady=5)

        def guardar_datos():
            lbl_error.configure(text="") 
            
            cod = cod_barras_var.get().strip() or None
            desc = desc_var.get().strip()
            cat = categoria_var.get().strip()
            mon = moneda_var.get()
            
            if not desc:
                lbl_error.configure(text="⚠ La descripción es obligatoria")
                entry_desc.focus()
                return
            if not cat:
                lbl_error.configure(text="⚠ Debes seleccionar o escribir una categoría")
                combo_cat.focus()
                return

            try:
                precio = float(precio_var.get())
                if precio < 0: raise ValueError
            except:
                lbl_error.configure(text="⚠ El precio debe ser un número válido positivo")
                entry_precio.focus()
                return

            try:
                stock = int(stock_var.get())
                if stock < 0: raise ValueError
            except:
                lbl_error.configure(text="⚠ El stock debe ser un número entero positivo")
                entry_stock.focus()
                return

            if not messagebox.askyesno("Confirmar", f"¿Registrar '{desc}' en el sistema?"):
                return

            try:
                total = precio * stock
                conn = conectar_db()
                cur = conn.cursor()
                sql = """
                    INSERT INTO desarrollo.stock (descripcion, precio_unit, cant_inventario, categoria, precio_total, moneda, codigo_barras)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(sql, (desc, precio, stock, cat, total, mon, cod))
                conn.commit()
                cur.close()
                conn.close()

                messagebox.showinfo("Éxito", "Producto registrado correctamente")
                form.destroy()
                cargar_articulos() 
                
            except Exception as e:
                error_str = str(e).lower()
                # Traducimos el error de código duplicado a algo amigable
                if "duplicate key" in error_str or "unique constraint" in error_str:
                    messagebox.showerror("Código Duplicado", "No se pudo guardar el producto.\n\nEl Código de Barras ingresado ya pertenece a otro producto en el sistema.")
                else:
                    messagebox.showerror("Error Base de Datos", f"Error inesperado:\n{e}")

        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#95a5a6", hover_color="#7f8c8d", width=120,
                      command=form.destroy).pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="Guardar Producto", fg_color="#2ecc71", hover_color="#27ae60", width=160, font=("Arial", 12, "bold"),
                      command=guardar_datos).pack(side="left", padx=10)

        form.bind('<Return>', lambda e: guardar_datos())
        entry_cod.focus() # Foco inicial en el código por si usan pistola láser

    def eliminar_producto():
        seleccionado = tree.selection()
        if seleccionado:
            item = tree.item(seleccionado[0])
            datos = item["values"]
            id_articulo = datos[0]
            descripcion = datos[2] # El índice cambió por las nuevas columnas
            mostrar_ventana_confirmacion_eliminar(id_articulo, descripcion)
        else:
            mostrar_ventana_seleccion_eliminar()

    def mostrar_ventana_seleccion_eliminar():
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id_articulo, descripcion, categoria, cant_inventario FROM desarrollo.stock ORDER BY descripcion")
            productos = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Error de conexión: {e}")
            return

        if not productos:
            messagebox.showinfo("Vacío", "No hay productos registrados para eliminar.")
            return

        dialog = ctk.CTkToplevel()
        dialog.title("Seleccionar para Eliminar")
        dialog.geometry("600x500")
        dialog.transient(frame_destino.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("+%d+%d" % (dialog.winfo_screenwidth()/2 - 300, dialog.winfo_screenheight()/2 - 250))

        ctk.CTkLabel(dialog, text="Seleccione el producto a eliminar", font=("Arial", 16, "bold"), text_color="#34495e").pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text="Doble clic para confirmar", font=("Arial", 11), text_color="gray").pack(pady=(0, 10))

        frame_tabla = ctk.CTkFrame(dialog, fg_color="white", corner_radius=10)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)

        scroll_y = ttk.Scrollbar(frame_tabla, orient="vertical")
        cols = ("ID", "Descripción", "Categoría", "Stock")
        tree_del = ttk.Treeview(frame_tabla, columns=cols, show="headings", yscrollcommand=scroll_y.set, height=10)
        scroll_y.config(command=tree_del.yview)

        scroll_y.pack(side="right", fill="y", padx=(0, 5), pady=5)
        tree_del.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        tree_del.heading("ID", text="ID"); tree_del.column("ID", width=50, anchor="center")
        tree_del.heading("Descripción", text="Descripción"); tree_del.column("Descripción", width=250, anchor="w")
        tree_del.heading("Categoría", text="Categoría"); tree_del.column("Categoría", width=100, anchor="center")
        tree_del.heading("Stock", text="Stock"); tree_del.column("Stock", width=60, anchor="center")

        for p in productos:
            tree_del.insert("", "end", values=p)

        def on_select(event=None):
            sel = tree_del.selection()
            if not sel: return
            item = tree_del.item(sel[0])
            dialog.destroy()
            mostrar_ventana_confirmacion_eliminar(item["values"][0], item["values"][1])

        tree_del.bind("<Double-1>", on_select)
        ctk.CTkButton(dialog, text="Cancelar", fg_color="#95a5a6", command=dialog.destroy).pack(pady=20)

    def mostrar_ventana_confirmacion_eliminar(id_articulo, descripcion):
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            # Traemos la moneda también
            cursor.execute("SELECT descripcion, precio_unit, cant_inventario, categoria, precio_total, moneda FROM desarrollo.stock WHERE id_articulo = %s", (id_articulo,))
            data = cursor.fetchone()
            cursor.close()
            conn.close()
        except: return

        if not data: return

        confirm = ctk.CTkToplevel()
        confirm.title("⚠ Confirmar Eliminación")
        confirm.geometry("450x450")
        confirm.transient(frame_destino.winfo_toplevel())
        confirm.grab_set()
        confirm.geometry("+%d+%d" % (confirm.winfo_screenwidth()/2 - 225, confirm.winfo_screenheight()/2 - 225))

        ctk.CTkLabel(confirm, text="⚠", font=("Arial", 40), text_color="#e74c3c").pack(pady=(20, 0))
        ctk.CTkLabel(confirm, text="¿Eliminar definitivamente?", font=("Arial", 18, "bold"), text_color="#c0392b").pack(pady=(5, 15))

        card = ctk.CTkFrame(confirm, fg_color="white", corner_radius=10, border_color="#e74c3c", border_width=2)
        card.pack(fill="x", padx=40, pady=10)

        moneda_str = data[5] if data[5] else "USD"
        simbolo = "$" if moneda_str == "USD" else "Gs."

        info_text = (
            f"Producto:  {data[0]}\n"
            f"Categoría: {data[3]}\n"
            f"Valor:     {simbolo}{data[1]:,.2f}\n"
            f"Stock:     {data[2]} unidades"
        )
        
        ctk.CTkLabel(card, text=info_text, font=("Consolas", 12), justify="left", text_color="#2c3e50").pack(padx=20, pady=20, anchor="w")
        ctk.CTkLabel(confirm, text="Esta acción no se puede deshacer.", font=("Arial", 11), text_color="gray").pack(pady=5)

        def ejecutar_borrado():
            try:
                conn = conectar_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM desarrollo.stock WHERE id_articulo = %s", (id_articulo,))
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Eliminado", f"El producto ha sido eliminado.")
                confirm.destroy()
                cargar_articulos() 
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {e}")

        btn_frame = ctk.CTkFrame(confirm, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#95a5a6", width=100, command=confirm.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="SÍ, ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b", width=140, command=ejecutar_borrado).pack(side="left", padx=10)  
  
    def eliminar_categoria():
        dialog = ctk.CTkToplevel()
        dialog.title("Eliminar Categoría")
        dialog.geometry("400x320")
        dialog.transient(frame_destino.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("+%d+%d" % (dialog.winfo_screenwidth()/2 - 200, dialog.winfo_screenheight()/2 - 160))

        ctk.CTkLabel(dialog, text="Eliminar Categoría", font=("Arial", 18, "bold"), text_color="#c0392b").pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text="Seleccione la categoría a borrar:", font=("Arial", 12)).pack(pady=(0, 10))

        cats = obtener_categorias_existentes()
        
        if not cats:
            ctk.CTkLabel(dialog, text="No hay categorías disponibles.", text_color="gray").pack(pady=20)
            return

        combo_var = ctk.StringVar()
        combo = ttk.Combobox(dialog, textvariable=combo_var, values=cats, state="readonly", width=35, font=("Arial", 11))
        combo.pack(pady=10)
        combo.current(0)

        info_frame = ctk.CTkFrame(dialog, fg_color="#fff3cd", corner_radius=5)
        info_frame.pack(pady=15, padx=30, fill="x")
        ctk.CTkLabel(info_frame, text="⚠ Si la categoría tiene productos asociados,\nno se podrá eliminar.", 
                     text_color="#856404", font=("Arial", 10)).pack(pady=5)

        def ejecutar_borrado():
            seleccion = combo_var.get()
            if not seleccion: return

            try:
                conn = conectar_db()
                cur = conn.cursor()

                cur.execute("SELECT COUNT(*) FROM desarrollo.stock WHERE categoria = %s", (seleccion,))
                uso = cur.fetchone()[0]
                
                if uso > 0:
                    messagebox.showwarning("Bloqueado", f"No se puede eliminar '{seleccion}'.\n\nHay {uso} productos usándola.")
                    cur.close(); conn.close()
                    return

                if messagebox.askyesno("Confirmar", f"¿Borrar '{seleccion}' permanentemente?"):
                    cur.execute("DELETE FROM desarrollo.garantias WHERE gar_categoria = %s", (seleccion,))
                    conn.commit()
                    messagebox.showinfo("Éxito", "Categoría eliminada.")
                    dialog.destroy()
                
                cur.close(); conn.close()
                
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(dialog, text="Eliminar Definitivamente", fg_color="#e74c3c", hover_color="#c0392b", 
                      width=180, command=ejecutar_borrado).pack(pady=10)

    def agregar_categoria():
        dialog = ctk.CTkToplevel()
        dialog.title("Agregar Nueva Categoría")
        dialog.geometry("500x300")  
        dialog.resizable(False, False)
        dialog.transient(frame_destino.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("+%d+%d" % (dialog.winfo_screenwidth()/2 - 250, dialog.winfo_screenheight()/2 - 150))
        
        ctk.CTkLabel(dialog, text="Agregar Nueva Categoría", font=("Arial", 16, "bold")).pack(pady=15)
        
        campos_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        campos_frame.pack(pady=10)
        
        ctk.CTkLabel(campos_frame, text="Nombre de Categoría:", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        nombre_entry = ctk.CTkEntry(campos_frame, width=250, height=35, font=("Arial", 12), placeholder_text="Ej: Disco Duro, Memoria, etc.")
        nombre_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(campos_frame, text="Duración de Garantía:", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        duracion_entry = ctk.CTkEntry(campos_frame, width=150, height=35, font=("Arial", 12), placeholder_text="Ej: 12 meses, 24 meses")
        duracion_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        nombre_entry.focus()
        
        def guardar_categoria():
            nombre = nombre_entry.get().strip()
            duracion = duracion_entry.get().strip()
            
            if not nombre:
                messagebox.showwarning("Advertencia", "Por favor ingrese un nombre para la categoría")
                return
            if not duracion:
                messagebox.showwarning("Advertencia", "Por favor ingrese la duración de la garantía")
                return
            
            try:
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM desarrollo.garantias WHERE gar_categoria = %s", (nombre,))
                existe = cursor.fetchone()[0] > 0
                
                if existe:
                    messagebox.showinfo("Información", f"La categoría '{nombre}' ya existe en el sistema de garantías")
                else:
                    cursor.execute("""
                        INSERT INTO desarrollo.garantias (gar_categoria, gar_duracion)
                        VALUES (%s, %s)
                    """, (nombre, duracion))
                    conn.commit()
                    messagebox.showinfo("Éxito", f"Categoría '{nombre}' con garantía de {duracion} creada correctamente")
                
                cursor.close()
                conn.close()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo agregar la categoría:\n{e}")
        
        botones_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        botones_frame.pack(pady=20)
        
        btn_guardar = ctk.CTkButton(botones_frame, text="Guardar Categoría", width=150, height=40,
                                    command=guardar_categoria, fg_color="#FF9100", hover_color="#E07B00", font=("Arial", 12))
        btn_guardar.pack(side="left", padx=15)
        
        btn_cancelar = ctk.CTkButton(botones_frame, text="Cancelar", width=120, height=40,
                                     fg_color="#6c757d", hover_color="#5a6268", command=dialog.destroy, font=("Arial", 12))
        btn_cancelar.pack(side="left", padx=15)
        
        nombre_entry.bind("<Return>", lambda e: guardar_categoria())
        duracion_entry.bind("<Return>", lambda e: guardar_categoria())
        
        dialog.wait_window()

    # Carga inicial
    cargar_articulos()