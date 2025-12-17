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
    style.theme_use("clam")  # Base limpia para personalizar
    
    # Configuración de colores (Modo Light compatible con tu Dashboard)
    style.configure("Treeview",
                    background="white",
                    foreground="#2c3e50",
                    rowheight=35,           # Filas más altas para mejor lectura
                    fieldbackground="white",
                    bordercolor="#dcdcdc",
                    borderwidth=0,
                    font=("Arial", 11))
    
    style.configure("Treeview.Heading",
                    background="#f1f2f6",   # Gris muy suave para encabezados
                    foreground="#34495e",
                    relief="flat",
                    font=("Arial", 11, "bold"))
    
    style.map("Treeview",
              background=[('selected', '#3498db')], # Azul al seleccionar
              foreground=[('selected', 'white')])

    # ============================================================
    # 2. ESTRUCTURA PRINCIPAL (LAYOUT)
    # ============================================================
    main_frame = ctk.CTkFrame(frame_destino, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 5)) 

    # --- Header (Título) ---
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", pady=(0, 10)) # Reduje el espacio vertical
    
    lbl_titulo = ctk.CTkLabel(header_frame, text="📦 Gestión de Inventario", font=("Arial", 24, "bold"), text_color="#2c3e50")
    lbl_titulo.pack(side="left")

    # --- Barra de Herramientas ---
    toolbar_frame = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    toolbar_frame.pack(fill="x", pady=(0, 10), ipady=5) # Reduje pady para dar más espacio a la tabla

    # [SECCIÓN IZQUIERDA] Filtros
    ctk.CTkLabel(toolbar_frame, text="🔍", font=("Arial", 16)).pack(side="left", padx=(20, 5))
    
    entry_desc = ctk.CTkEntry(toolbar_frame, placeholder_text="Buscar por descripción...", width=220)
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
    # 3. TABLA DE DATOS (TREEVIEW)
    # ============================================================
    table_container = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=10)
    table_container.pack(fill="both", expand=True, pady=(0, 10)) # Pequeño margen abajo para que no toque el borde literal

    # Scrollbars
    scrollbar_y = ttk.Scrollbar(table_container, orient="vertical")
    scrollbar_x = ttk.Scrollbar(table_container, orient="horizontal")

    # Tabla
    columnas = ("ID", "Descripción", "Precio Unit", "Inventario", "Categoría", "Precio Total")
    tree = ttk.Treeview(table_container, columns=columnas, show="headings", 
                        yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    scrollbar_y.config(command=tree.yview)
    scrollbar_x.config(command=tree.xview)

    # Layout Tabla - Optimizada para llenar el contenedor blanco
    scrollbar_y.pack(side="right", fill="y", padx=(0, 2), pady=2)
    scrollbar_x.pack(side="bottom", fill="x", padx=2, pady=(0, 2))
    tree.pack(side="left", fill="both", expand=True, padx=5, pady=5) 
    
    
    # Configuración de Cabeceras... (resto igual)
    col_widths = {"ID": 60, "Descripción": 350, "Precio Unit": 120, "Inventario": 100, "Categoría": 150, "Precio Total": 120}
    for col in columnas:
        tree.heading(col, text=col)
        anchor_type = "w" if col == "Descripción" else "center"
        tree.column(col, anchor=anchor_type, width=col_widths.get(col, 100))

    # --- Función para cargar artículos con filtros ---
    def cargar_articulos():
        tree.delete(*tree.get_children())
        
        # --- AQUÍ ESTÁ EL TRUCO ---
        # Obtenemos el texto directamente de los widgets creados arriba
        # Si usas variables con otros nombres, aquí fallará.
        desc_filtro = entry_desc.get().strip()
        cat_filtro = entry_cat.get().strip()

        # --- EL RESTO DEL SQL SIGUE IGUAL ---
        query = """
            SELECT id_articulo, descripcion, precio_unit, cant_inventario, categoria, precio_total
            FROM desarrollo.stock
            WHERE 1=1
        """
        params = []
        
        if desc_filtro:
            query += " AND descripcion ILIKE %s"
            params.append(f"%{desc_filtro}%")
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
                id_art, descripcion, precio, stock, categoria, total = row
                precio_fmt = f"${precio:,.2f}" if precio is not None else "$0.00"
                total_fmt = f"${total:,.2f}" if total is not None else "$0.00"
                tree.insert("", "end", values=(id_art, descripcion, precio_fmt, stock, categoria, total_fmt))
            
            cursor.close()
            conn.close()
            # Actualizamos el título si existe la etiqueta lbl_titulo
            try: lbl_titulo.configure(text=f"📦 Gestión de Inventario ({len(filas)} productos)")
            except: pass
            
        except Exception as e:
            print(f"Error al filtrar: {e}")

    entry_desc.bind("<Return>", lambda event: cargar_articulos())
    entry_cat.bind("<Return>", lambda event: cargar_articulos())
    
    
    def abrir_formulario_editar(event):
        seleccion = tree.selection()
        if not seleccion:
            return
            
        item = tree.item(seleccion[0])
        datos = item["values"]
        # datos = [id, descripcion, precio_fmt, stock, categoria, total]
        
        id_art = datos[0]
        
        # Limpieza de datos (Quitar el signo $ y las comas para editar)
        try:
            precio_limpio = str(datos[2]).replace("$", "").replace(",", "")
            stock_actual = str(datos[3])
        except:
            precio_limpio = "0"
            stock_actual = "0"

        # --- Crear Ventana de Edición ---
        edit_win = ctk.CTkToplevel()
        edit_win.title(f"Editar Producto #{id_art}")
        edit_win.geometry("500x550")
        edit_win.transient(frame_destino.winfo_toplevel())
        edit_win.grab_set()
        
        # Centrar ventana
        edit_win.geometry("+%d+%d" % (edit_win.winfo_screenwidth()/2 - 250, edit_win.winfo_screenheight()/2 - 275))

        ctk.CTkLabel(edit_win, text="Editar Producto", font=("Arial", 20, "bold"), text_color="#2c3e50").pack(pady=20)

        content = ctk.CTkFrame(edit_win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=40)

        # Variables
        var_desc = ctk.StringVar(value=datos[1])
        var_precio = ctk.StringVar(value=precio_limpio)
        var_stock = ctk.StringVar(value=stock_actual)
        var_cat = ctk.StringVar(value=datos[4])

        # Inputs
        ctk.CTkLabel(content, text="Descripción:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=10)
        entry_desc_ed = ctk.CTkEntry(content, textvariable=var_desc, width=280)
        entry_desc_ed.grid(row=0, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Precio Unit:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=10)
        entry_precio_ed = ctk.CTkEntry(content, textvariable=var_precio, width=150)
        entry_precio_ed.grid(row=1, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Stock:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=10)
        entry_stock_ed = ctk.CTkEntry(content, textvariable=var_stock, width=150)
        entry_stock_ed.grid(row=2, column=1, sticky="w", pady=10, padx=10)

        ctk.CTkLabel(content, text="Categoría:", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="w", pady=10)
        cats = obtener_categorias_existentes() # Usamos la función helper
        combo_cat_ed = ttk.Combobox(content, textvariable=var_cat, values=cats, width=32)
        combo_cat_ed.grid(row=3, column=1, sticky="w", pady=10, padx=10)

        def guardar_cambios():
            try:
                n_desc = var_desc.get()
                n_precio = float(var_precio.get())
                n_stock = int(var_stock.get())
                n_cat = var_cat.get()
                n_total = n_precio * n_stock

                if not messagebox.askyesno("Confirmar", "¿Guardar cambios?"):
                    return

                conn = conectar_db()
                cur = conn.cursor()
                

                sql = """
                    UPDATE desarrollo.stock 
                    SET descripcion=%s, precio_unit=%s, cant_inventario=%s, categoria=%s, precio_total=%s
                    WHERE id_articulo=%s
                """
                cur.execute(sql, (n_desc, n_precio, n_stock, n_cat, n_total, id_art))
                conn.commit()
                cur.close()
                conn.close()
                
                edit_win.destroy()
                cargar_articulos() # Refrescar tabla
                messagebox.showinfo("Éxito", "Producto actualizado.")
            
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al actualizar: {e}")
        ctk.CTkButton(edit_win, text="Guardar Cambios", command=guardar_cambios, fg_color="#2ecc71", width=200).pack(pady=30)

    tree.bind("<Double-1>", abrir_formulario_editar)
    # --- Botones de acción (Agregar / Eliminar) ---
    acciones_frame = ctk.CTkFrame(main_frame)
    acciones_frame.pack(pady=5, fill="x")

    botones_center_frame = ctk.CTkFrame(acciones_frame, fg_color="transparent")
    botones_center_frame.pack(expand=True) 

    def obtener_categorias_existentes():
        """Obtiene las categorías de la tabla de garantías para el combobox."""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT gar_categoria FROM desarrollo.garantias ORDER BY gar_categoria")
            # Extraemos el primer elemento de cada tupla
            categorias = [row[0] for row in cursor.fetchall() if row[0]]
            cursor.close()
            conn.close()
            return categorias
        except Exception as e:
            print(f"Error obteniendo categorías: {e}")
            return []

    def abrir_formulario_agregar():
        # Configuración de la Ventana Modal
        form = ctk.CTkToplevel()
        form.title("Nuevo Producto")
        form.geometry("500x550")
        form.transient(frame_destino.winfo_toplevel()) # Mantener encima de la principal
        form.grab_set() # Bloquear la ventana principal hasta cerrar esta
        
        # Centrar en pantalla
        form.geometry("+%d+%d" % (form.winfo_screenwidth()/2 - 250, form.winfo_screenheight()/2 - 275))

        # Título del Formulario
        ctk.CTkLabel(form, text="Registrar Nuevo Producto", font=("Arial", 20, "bold"), text_color="#2c3e50").pack(pady=(20, 15))

        # Contenedor central (Usamos Grid para alinear bonito)
        content_frame = ctk.CTkFrame(form, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=40)

        # Variables de control
        desc_var = ctk.StringVar()
        precio_var = ctk.StringVar()
        stock_var = ctk.StringVar()
        categoria_var = ctk.StringVar()

        # --- FILA 1: Descripción ---
        ctk.CTkLabel(content_frame, text="Descripción:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=10)
        entry_desc = ctk.CTkEntry(content_frame, textvariable=desc_var, width=280, placeholder_text="Ej: Monitor LED 24 pulg")
        entry_desc.grid(row=0, column=1, sticky="w", pady=10, padx=(10, 0))

        # --- FILA 2: Precio ---
        ctk.CTkLabel(content_frame, text="Precio Unitario:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=10)
        entry_precio = ctk.CTkEntry(content_frame, textvariable=precio_var, width=150, placeholder_text="0.00")
        entry_precio.grid(row=1, column=1, sticky="w", pady=10, padx=(10, 0))

        # --- FILA 3: Stock ---
        ctk.CTkLabel(content_frame, text="Stock Inicial:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=10)
        entry_stock = ctk.CTkEntry(content_frame, textvariable=stock_var, width=150, placeholder_text="0")
        entry_stock.grid(row=2, column=1, sticky="w", pady=10, padx=(10, 0))

        # --- FILA 4: Categoría (Combobox) ---
        ctk.CTkLabel(content_frame, text="Categoría:", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="w", pady=10)
        
        categorias_disponibles = obtener_categorias_existentes()
        
        # Usamos ttk.Combobox porque maneja mejor el autocompletado nativo
        combo_cat = ttk.Combobox(content_frame, textvariable=categoria_var, values=categorias_disponibles, width=32, font=("Arial", 11))
        combo_cat.grid(row=3, column=1, sticky="w", pady=10, padx=(10, 0))

        # Lógica de Autocompletado (Tu código original)
        def autocompletar_categoria(event):
            texto = categoria_var.get().lower()
            if texto:
                coincidencias = [cat for cat in categorias_disponibles if texto in cat.lower()]
                combo_cat['values'] = coincidencias
            else:
                combo_cat['values'] = categorias_disponibles

        combo_cat.bind('<KeyRelease>', autocompletar_categoria)

        # Label para Errores (Feedback visual sin popups molestos)
        lbl_error = ctk.CTkLabel(form, text="", text_color="#e74c3c", font=("Arial", 11))
        lbl_error.pack(pady=5)

        def guardar_datos():
            lbl_error.configure(text="") # Limpiar errores previos

            # 1. Validaciones
            desc = desc_var.get().strip()
            cat = categoria_var.get().strip()
            
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

            # 2. Confirmación rápida
            if not messagebox.askyesno("Confirmar", f"¿Registrar '{desc}' en el sistema?"):
                return

            # 3. Insertar en BD
            try:
                total = precio * stock
                
                conn = conectar_db()
                cur = conn.cursor()
                sql = """
                    INSERT INTO desarrollo.stock (descripcion, precio_unit, cant_inventario, categoria, precio_total)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cur.execute(sql, (desc, precio, stock, cat, total))
                conn.commit()
                cur.close()
                conn.close()

                messagebox.showinfo("Éxito", "Producto registrado correctamente")
                form.destroy()
                cargar_articulos() # Recargar la tabla principal
                
            except Exception as e:
                messagebox.showerror("Error Base de Datos", f"No se pudo guardar:\n{e}")

        # --- BOTONES DE ACCIÓN ---
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(pady=20)

        # Botón Cancelar (Gris)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#95a5a6", hover_color="#7f8c8d", width=120,
                      command=form.destroy).pack(side="left", padx=10)

        # Botón Guardar (Verde)
        ctk.CTkButton(btn_frame, text="Guardar Producto", fg_color="#2ecc71", hover_color="#27ae60", width=160, font=("Arial", 12, "bold"),
                      command=guardar_datos).pack(side="left", padx=10)

        # Bind de la tecla ENTER para guardar rápido
        form.bind('<Return>', lambda e: guardar_datos())
        
        # Foco inicial
        entry_desc.focus()

    def eliminar_producto():
        """Punto de entrada: Verifica si hay selección en la tabla principal o abre buscador."""
        seleccionado = tree.selection()
        
        if seleccionado:
            # Caso A: Usuario seleccionó en la tabla principal -> Confirmación directa
            item = tree.item(seleccionado[0])
            datos = item["values"]
            id_articulo = datos[0]
            descripcion = datos[1]
            mostrar_ventana_confirmacion_eliminar(id_articulo, descripcion)
        else:
            # Caso B: No seleccionó nada -> Abrir ventana de búsqueda para eliminar
            mostrar_ventana_seleccion_eliminar()

    def mostrar_ventana_seleccion_eliminar():
        """Muestra una ventana auxiliar con tabla para buscar el producto a eliminar."""
        
        # Consultar todos los productos
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

        # Configuración Ventana
        dialog = ctk.CTkToplevel()
        dialog.title("Seleccionar para Eliminar")
        dialog.geometry("600x500")
        dialog.transient(frame_destino.winfo_toplevel())
        dialog.grab_set()
        
        # Centrar
        dialog.geometry("+%d+%d" % (dialog.winfo_screenwidth()/2 - 300, dialog.winfo_screenheight()/2 - 250))

        # Header
        ctk.CTkLabel(dialog, text="Seleccione el producto a eliminar", font=("Arial", 16, "bold"), text_color="#34495e").pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text="Doble clic para confirmar", font=("Arial", 11), text_color="gray").pack(pady=(0, 10))

        # Tabla Auxiliar
        frame_tabla = ctk.CTkFrame(dialog, fg_color="white", corner_radius=10)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)

        # Scrollbars
        scroll_y = ttk.Scrollbar(frame_tabla, orient="vertical")
        
        # Treeview (Reutiliza el estilo moderno que definimos al inicio)
        cols = ("ID", "Descripción", "Categoría", "Stock")
        tree_del = ttk.Treeview(frame_tabla, columns=cols, show="headings", yscrollcommand=scroll_y.set, height=10)
        scroll_y.config(command=tree_del.yview)

        # Layout Tabla
        scroll_y.pack(side="right", fill="y", padx=(0, 5), pady=5)
        tree_del.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Configuración Columnas
        tree_del.heading("ID", text="ID"); tree_del.column("ID", width=50, anchor="center")
        tree_del.heading("Descripción", text="Descripción"); tree_del.column("Descripción", width=250, anchor="w")
        tree_del.heading("Categoría", text="Categoría"); tree_del.column("Categoría", width=100, anchor="center")
        tree_del.heading("Stock", text="Stock"); tree_del.column("Stock", width=60, anchor="center")

        # Llenar datos
        for p in productos:
            tree_del.insert("", "end", values=p)

        # Acción al seleccionar
        def on_select(event=None):
            sel = tree_del.selection()
            if not sel: return
            item = tree_del.item(sel[0])
            # Cerrar esta ventana y abrir confirmación
            dialog.destroy()
            mostrar_ventana_confirmacion_eliminar(item["values"][0], item["values"][1])

        tree_del.bind("<Double-1>", on_select)

        # Botón Cancelar
        ctk.CTkButton(dialog, text="Cancelar", fg_color="#95a5a6", command=dialog.destroy).pack(pady=20)

    def mostrar_ventana_confirmacion_eliminar(id_articulo, descripcion):
        """Muestra la tarjeta de confirmación final con advertencia roja."""
        
        # Obtener detalles completos para mostrar en la tarjeta
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT descripcion, precio_unit, cant_inventario, categoria, precio_total FROM desarrollo.stock WHERE id_articulo = %s", (id_articulo,))
            data = cursor.fetchone()
            cursor.close()
            conn.close()
        except: return

        if not data: return

        # Ventana de Alerta
        confirm = ctk.CTkToplevel()
        confirm.title("⚠ Confirmar Eliminación")
        confirm.geometry("450x450")
        confirm.transient(frame_destino.winfo_toplevel())
        confirm.grab_set()
        
        # Centrar
        confirm.geometry("+%d+%d" % (confirm.winfo_screenwidth()/2 - 225, confirm.winfo_screenheight()/2 - 225))

        # Ícono y Título de Advertencia
        ctk.CTkLabel(confirm, text="⚠", font=("Arial", 40), text_color="#e74c3c").pack(pady=(20, 0))
        ctk.CTkLabel(confirm, text="¿Eliminar definitivamente?", font=("Arial", 18, "bold"), text_color="#c0392b").pack(pady=(5, 15))

        # Tarjeta de Detalles (Visualización limpia)
        card = ctk.CTkFrame(confirm, fg_color="white", corner_radius=10, border_color="#e74c3c", border_width=2)
        card.pack(fill="x", padx=40, pady=10)

        info_text = (
            f"Producto:  {data[0]}\n"
            f"Categoría:  {data[3]}\n"
            f"Valor:      ${data[1]:,.2f}\n"
            f"Stock:      {data[2]} unidades"
        )
        
        ctk.CTkLabel(card, text=info_text, font=("Consolas", 12), justify="left", text_color="#2c3e50").pack(padx=20, pady=20, anchor="w")

        ctk.CTkLabel(confirm, text="Esta acción no se puede deshacer.", font=("Arial", 11), text_color="gray").pack(pady=5)

        # Lógica de borrado real
        def ejecutar_borrado():
            try:
                conn = conectar_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM desarrollo.stock WHERE id_articulo = %s", (id_articulo,))
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Eliminado", f"El producto ha sido eliminado.")
                confirm.destroy()
                cargar_articulos() # Recargar tabla principal
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {e}")

        # Botones
        btn_frame = ctk.CTkFrame(confirm, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#95a5a6", width=100, command=confirm.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="SÍ, ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b", width=140, command=ejecutar_borrado).pack(side="left", padx=10)  
  
    # --- Editar producto al hacer doble clic ---
    def obtener_categorias_existentes():
        """Helper para llenar comboboxes."""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT gar_categoria FROM desarrollo.garantias ORDER BY gar_categoria")
            # Lista plana de strings
            cats = [row[0] for row in cursor.fetchall() if row[0]]
            cursor.close()
            conn.close()
            return cats
        except Exception as e:
            print(f"Error cargando categorías: {e}")
            return []

    def agregar_categoria():
        """Formulario para crear nuevas categorías de garantía."""
        dialog = ctk.CTkToplevel()
        dialog.title("Nueva Categoría")
        dialog.geometry("400x350")
        dialog.transient(frame_destino.winfo_toplevel())
        dialog.grab_set()
        
        # Centrar
        dialog.geometry("+%d+%d" % (dialog.winfo_screenwidth()/2 - 200, dialog.winfo_screenheight()/2 - 175))

        ctk.CTkLabel(dialog, text="Crear Categoría", font=("Arial", 18, "bold"), text_color="#2c3e50").pack(pady=(20, 15))

        # Contenedor
        frame_inputs = ctk.CTkFrame(dialog, fg_color="transparent")
        frame_inputs.pack(fill="x", padx=30)

        # Nombre
        ctk.CTkLabel(frame_inputs, text="Nombre:", font=("Arial", 12, "bold")).pack(anchor="w")
        entry_nombre = ctk.CTkEntry(frame_inputs, placeholder_text="Ej: Tarjetas de Video")
        entry_nombre.pack(fill="x", pady=(5, 10))

        # Duración Garantía
        ctk.CTkLabel(frame_inputs, text="Garantía (Meses/Años):", font=("Arial", 12, "bold")).pack(anchor="w")
        entry_duracion = ctk.CTkEntry(frame_inputs, placeholder_text="Ej: 12 Meses")
        entry_duracion.pack(fill="x", pady=(5, 10))

        # Label Error
        lbl_error = ctk.CTkLabel(dialog, text="", text_color="#e74c3c", font=("Arial", 11))
        lbl_error.pack(pady=5)

        def guardar():
            lbl_error.configure(text="")
            nombre = entry_nombre.get().strip()
            duracion = entry_duracion.get().strip()

            if not nombre:
                lbl_error.configure(text="⚠ Falta el nombre")
                entry_nombre.focus()
                return
            if not duracion:
                lbl_error.configure(text="⚠ Falta la duración")
                entry_duracion.focus()
                return

            try:
                conn = conectar_db()
                cursor = conn.cursor()
                
                # Validar duplicados
                cursor.execute("SELECT COUNT(*) FROM desarrollo.garantias WHERE gar_categoria = %s", (nombre,))
                if cursor.fetchone()[0] > 0:
                    lbl_error.configure(text=f"⚠ La categoría '{nombre}' ya existe")
                    cursor.close(); conn.close()
                    return

                # Insertar
                cursor.execute("INSERT INTO desarrollo.garantias (gar_categoria, gar_duracion) VALUES (%s, %s)", (nombre, duracion))
                conn.commit()
                cursor.close(); conn.close()

                messagebox.showinfo("Éxito", f"Categoría '{nombre}' creada.")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Botones
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#95a5a6", width=100, command=dialog.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Guardar", fg_color="#2ecc71", hover_color="#27ae60", width=120, command=guardar).pack(side="left", padx=10)
        
        entry_nombre.focus()


    def eliminar_categoria():
        """Formulario para borrar categorías (con validación de uso)."""
        dialog = ctk.CTkToplevel()
        dialog.title("Eliminar Categoría")
        dialog.geometry("400x320")
        dialog.transient(frame_destino.winfo_toplevel())
        dialog.grab_set()
        
        # Centrar
        dialog.geometry("+%d+%d" % (dialog.winfo_screenwidth()/2 - 200, dialog.winfo_screenheight()/2 - 160))

        ctk.CTkLabel(dialog, text="Eliminar Categoría", font=("Arial", 18, "bold"), text_color="#c0392b").pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text="Seleccione la categoría a borrar:", font=("Arial", 12)).pack(pady=(0, 10))

        cats = obtener_categorias_existentes()
        
        if not cats:
            ctk.CTkLabel(dialog, text="No hay categorías disponibles.", text_color="gray").pack(pady=20)
            return

        # Combobox
        combo_var = ctk.StringVar()
        combo = ttk.Combobox(dialog, textvariable=combo_var, values=cats, state="readonly", width=35, font=("Arial", 11))
        combo.pack(pady=10)
        combo.current(0)

        # Advertencia visual
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

                # 1. Verificar si está en uso en STOCK
                cur.execute("SELECT COUNT(*) FROM desarrollo.stock WHERE categoria = %s", (seleccion,))
                uso = cur.fetchone()[0]
                
                if uso > 0:
                    messagebox.showwarning("Bloqueado", f"No se puede eliminar '{seleccion}'.\n\nHay {uso} productos usándola.")
                    cur.close(); conn.close()
                    return

                # 2. Confirmación final
                if messagebox.askyesno("Confirmar", f"¿Borrar '{seleccion}' permanentemente?"):
                    cur.execute("DELETE FROM desarrollo.garantias WHERE gar_categoria = %s", (seleccion,))
                    conn.commit()
                    messagebox.showinfo("Éxito", "Categoría eliminada.")
                    dialog.destroy()
                
                cur.close(); conn.close()
                
            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Botón Rojo
        ctk.CTkButton(dialog, text="Eliminar Definitivamente", fg_color="#e74c3c", hover_color="#c0392b", 
                      width=180, command=ejecutar_borrado).pack(pady=10)
    # --- Función para agregar categoría ---
    def agregar_categoria():
        # Ventana para agregar nueva categoría
        dialog = ctk.CTkToplevel()
        dialog.title("Agregar Nueva Categoría")
        dialog.geometry("500x300")  # Un poco más grande para incluir duración
        dialog.resizable(False, False)
        dialog.transient(frame_destino.winfo_toplevel())
        dialog.grab_set()
        
        # Centrar la ventana
        dialog.geometry("+%d+%d" % (dialog.winfo_screenwidth()/2 - 250, dialog.winfo_screenheight()/2 - 150))
        
        ctk.CTkLabel(
            dialog,
            text="Agregar Nueva Categoría",
            font=("Arial", 16, "bold")
        ).pack(pady=15)
        
        # Frame para los campos
        campos_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        campos_frame.pack(pady=10)
        
        # Campo para nombre de categoría
        ctk.CTkLabel(campos_frame, text="Nombre de Categoría:", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        nombre_entry = ctk.CTkEntry(
            campos_frame,
            width=250,
            height=35,
            font=("Arial", 12),
            placeholder_text="Ej: Disco Duro, Memoria, etc."
        )
        nombre_entry.grid(row=0, column=1, padx=10, pady=10)
        
        # Campo para duración de garantía
        ctk.CTkLabel(campos_frame, text="Duración de Garantía:", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        duracion_entry = ctk.CTkEntry(
            campos_frame,
            width=150,
            height=35,
            font=("Arial", 12),
            placeholder_text="Ej: 12 meses, 24 meses"
        )
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
                # Verificar si la categoría ya existe en la tabla de garantías
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM desarrollo.garantias WHERE gar_categoria = %s", (nombre,))
                existe = cursor.fetchone()[0] > 0
                
                if existe:
                    messagebox.showinfo("Información", f"La categoría '{nombre}' ya existe en el sistema de garantías")
                else:
                    # Insertar en la tabla desarrollo.garantias
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
        
        # Frame para botones
        botones_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        botones_frame.pack(pady=20)
        
        btn_guardar = ctk.CTkButton(
            botones_frame,
            text="Guardar Categoría",
            width=150,
            height=40,
            command=guardar_categoria,
            fg_color="#FF9100",
            hover_color="#E07B00",
            font=("Arial", 12)
        )
        btn_guardar.pack(side="left", padx=15)
        
        btn_cancelar = ctk.CTkButton(
            botones_frame,
            text="Cancelar",
            width=120,
            height=40,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=dialog.destroy,
            font=("Arial", 12)
        )
        btn_cancelar.pack(side="left", padx=15)
        
        # Permitir guardar con la tecla Enter
        nombre_entry.bind("<Return>", lambda e: guardar_categoria())
        duracion_entry.bind("<Return>", lambda e: guardar_categoria())
        
        dialog.wait_window()

    # Carga inicial
    cargar_articulos()