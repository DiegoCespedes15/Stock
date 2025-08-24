# modulos/stock.py
from tkinter import messagebox
import customtkinter as ctk
from sqlalchemy import null
from bd import conectar_db
import tkinter.ttk as ttk
from decimal import Decimal, InvalidOperation


def mostrar_productos(frame_destino):
    for widget in frame_destino.winfo_children():
        widget.destroy()

    # Frame principal para organizar mejor los elementos
    main_frame = ctk.CTkFrame(frame_destino)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(main_frame, text="Listado de Artículos", font=("Arial", 18)).pack(pady=10)

    # --- Filtros ---
    filtros_frame = ctk.CTkFrame(main_frame)
    filtros_frame.pack(pady=5, fill="x")

    descripcion_var = ctk.StringVar()
    categoria_var = ctk.StringVar()

    # Fila 1 de filtros
    ctk.CTkLabel(filtros_frame, text="Descripción:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    descripcion_entry = ctk.CTkEntry(filtros_frame, textvariable=descripcion_var, width=150)
    descripcion_entry.grid(row=0, column=1, padx=5, pady=5)

    ctk.CTkLabel(filtros_frame, text="Categoría:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
    categoria_entry = ctk.CTkEntry(filtros_frame, textvariable=categoria_var, width=150)
    categoria_entry.grid(row=0, column=3, padx=5, pady=5)

    # Botón de búsqueda
    buscar_btn = ctk.CTkButton(filtros_frame, text="Buscar", command=lambda: cargar_articulos(), 
                              fg_color="#FF9100", hover_color="#E07B00", width=100)
    buscar_btn.grid(row=0, column=4, padx=10, pady=5)

    # Botón para agregar nueva categoría 
    btn_agregar_categoria = ctk.CTkButton(
        filtros_frame,
        text="Agregar Categoría",
        width=150,
        height=30,
        font=("Arial", 12),
        fg_color="#FF9100",
        hover_color="#E07B00",
        command=lambda: agregar_categoria()
    )
    btn_agregar_categoria.grid(row=0, column=5, padx=10, pady=5)

    # --- Tabla de artículos ---
    tabla_frame = ctk.CTkFrame(main_frame)
    tabla_frame.pack(pady=10, fill="both", expand=True)

    columnas = ("ID", "Descripción", "Precio Unit", "Inventario", "Categoría", "Precio Total")
    tree = ttk.Treeview(tabla_frame, columns=columnas, show="headings")

    # Configurar encabezados y columnas
    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=100)

    # Ajustar anchos de columnas específicas
    tree.column("Descripción", width=250)
    tree.column("Precio Unit", width=100)
    tree.column("Precio Total", width=100)

    # Scroll vertical
    scrollbar_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)
    
    # Scroll horizontal
    scrollbar_x = ttk.Scrollbar(tabla_frame, orient="horizontal", command=tree.xview)
    tree.configure(xscrollcommand=scrollbar_x.set)

    # Usar grid para una mejor disposición
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar_y.grid(row=0, column=1, sticky="ns")
    scrollbar_x.grid(row=1, column=0, sticky="ew")
    
    # Configurar el peso de las filas y columnas para que se expandan
    tabla_frame.grid_rowconfigure(0, weight=1)
    tabla_frame.grid_columnconfigure(0, weight=1)

    # --- Función para cargar artículos con filtros ---
    def cargar_articulos():
        tree.delete(*tree.get_children())
        descripcion_filtro = descripcion_var.get().strip()
        categoria_filtro = categoria_var.get().strip()

        query = """
            SELECT id_articulo, descripcion, precio_unit, cant_inventario, categoria, precio_total
            FROM desarrollo.stock
            WHERE 1=1
        """
        params = []

        if descripcion_filtro:
            query += " AND descripcion ILIKE %s"
            params.append(f"%{descripcion_filtro}%")
        if categoria_filtro:
            query += " AND categoria ILIKE %s"
            params.append(f"%{categoria_filtro}%")

        query += " ORDER BY id_articulo"

        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor.fetchall():
                tree.insert("", "end", values=row)
            cursor.close()
            conn.close()
        except Exception as e:
            error_label = ctk.CTkLabel(main_frame, text=f"Error: {e}", text_color="red")
            error_label.pack(pady=5)

    # --- Botones de acción (Agregar / Eliminar) ---
    acciones_frame = ctk.CTkFrame(main_frame)
    acciones_frame.pack(pady=5, fill="x")

    botones_center_frame = ctk.CTkFrame(acciones_frame, fg_color="transparent")
    botones_center_frame.pack(expand=True) 

    def obtener_categorias_existentes():
        """Obtiene las categorías existentes de la tabla de garantías"""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT gar_categoria FROM desarrollo.garantias ORDER BY gar_categoria")
            categorias = [row[0] for row in cursor.fetchall() if row[0]]
            cursor.close()
            conn.close()
            return categorias
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las categorías:\n{e}")
            return []


    def abrir_formulario_agregar():
        form = ctk.CTkToplevel()
        form.title("Agregar Producto")
        form.geometry("400x450")
        form.transient(frame_destino.winfo_toplevel())
        form.grab_set()

        # Variables para los campos del formulario
        desc_var = ctk.StringVar()
        precio_var = ctk.StringVar()
        stock_var = ctk.StringVar()
        categoria_var = ctk.StringVar()

        ctk.CTkLabel(form, text="Descripción:").pack(pady=5)
        desc_entry = ctk.CTkEntry(form, textvariable=desc_var)
        desc_entry.pack()

        ctk.CTkLabel(form, text="Precio Unitario:").pack(pady=5)
        precio_entry = ctk.CTkEntry(form, textvariable=precio_var)
        precio_entry.pack()

        ctk.CTkLabel(form, text="Cantidad Inventario:").pack(pady=5)
        stock_entry = ctk.CTkEntry(form, textvariable=stock_var)
        stock_entry.pack()

        ctk.CTkLabel(form, text="Categoría:").pack(pady=5)

        # Obtener categorías existentes
        categorias = obtener_categorias_existentes()

        # Crear combobox simple sin frames adicionales (para debugging)
        categoria_combobox = ttk.Combobox(
            form, 
            textvariable=categoria_var, 
            values=categorias,
            width=38,
            state="normal"
        )
        categoria_combobox.pack(pady=5)

        # Configurar autocompletado
        def autocompletar_categoria(event):
            texto = categoria_var.get().lower()
            if texto:
                coincidencias = [cat for cat in categorias if texto in cat.lower()]
                categoria_combobox['values'] = coincidencias
            else:
                categoria_combobox['values'] = categorias
            return "break"

        categoria_combobox.bind('<KeyRelease>', autocompletar_categoria)

        error_label = ctk.CTkLabel(form, text="", text_color="red")
        error_label.pack(pady=5)

        def guardar():
            # DEBUG: Mostrar el valor actual de la categoría
            print(f"Valor de categoría: '{categoria_var.get()}'")

            if not messagebox.askyesno("Confirmar", "¿Seguro que deseas agregar este producto?"):
                return

            try:
                descripcion = desc_var.get().strip()
                if not descripcion:
                    raise ValueError("La descripción no puede estar vacía.")

                categoria = categoria_var.get().strip()
                print(f"Categoría después de strip: '{categoria}'")  # DEBUG
                if not categoria:
                    raise ValueError("La categoría no puede estar vacía.")

                if not precio_var.get().strip():
                    raise ValueError("El precio no puede estar vacío.")
                try:
                    precio = float(precio_var.get())
                    if precio < 0:
                        raise ValueError("El precio debe ser un número positivo.")
                except ValueError:  
                    raise ValueError("El precio debe ser un número válido.")

                if not stock_var.get().strip():
                    raise ValueError("La cantidad no puede estar vacía.")
                try:
                    stock = int(stock_var.get())
                    if stock < 0:
                        raise ValueError("El inventario debe ser un número entero positivo.")
                except ValueError:
                    raise ValueError("El inventario debe ser un número entero válido.")

                precio_total = precio * stock

                conn = conectar_db()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO desarrollo.stock (descripcion, precio_unit, cant_inventario, categoria, precio_total)
                    VALUES (%s, %s, %s, %s, %s)
                """, (descripcion, precio, stock, categoria, precio_total))
                conn.commit()
                cur.close()
                conn.close()

                messagebox.showinfo("Éxito", "Producto agregado correctamente.")
                form.destroy()
                cargar_articulos()
                
            except ValueError as ve:
                error_label.configure(text=str(ve))
                print(f"Error de validación: {ve}")  # DEBUG
            except Exception as e:
                error_label.configure(text=f"Error: {e}")
                print(f"Error general: {e}")  # DEBUG

        ctk.CTkButton(form, text="Guardar", command=guardar, fg_color="#FF9100", hover_color="#E07B00").pack(pady=10)
    
        # Poner foco en el primer campo
        desc_entry.focus()

    def eliminar_producto():
        seleccionado = tree.selection()
        if seleccionado:
            item = tree.item(seleccionado)
            id_articulo = item["values"][0]
            
            if not messagebox.askyesno("Confirmar", "¿Seguro que deseas eliminar este producto?"):
                return
            try:
                conn = conectar_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM desarrollo.stock WHERE id_articulo = %s", (id_articulo,))
                conn.commit()
                cur.close()
                conn.close()
                
                messagebox.showinfo("Éxito", "Producto eliminado correctamente.")
                cargar_articulos()
            except Exception as e:
                error_label = ctk.CTkLabel(main_frame, text=f"Error: {e}", text_color="red")
                error_label.pack(pady=5)
        else:
            error_label = ctk.CTkLabel(main_frame, text="Selecciona un producto para eliminar.", text_color="red")
            error_label.pack(pady=5)

    ctk.CTkButton(botones_center_frame, text="Agregar Producto", command=abrir_formulario_agregar, fg_color="#4CAF50").pack(side="left", padx=10)
    ctk.CTkButton(botones_center_frame, text="Eliminar Seleccionado", command=eliminar_producto, fg_color="#FF4444").pack(side="left", padx=10)
    
    # --- Editar producto al hacer doble clic ---
    def editar_producto(event):
        seleccionado = tree.selection()
        if not seleccionado:
            return

        item = tree.item(seleccionado)
        datos = item["values"]

        id_articulo = datos[0]
        descripcion_ini = datos[1]
        precio_unit_ini = datos[2]
        inventario_ini = datos[3]
        categoria_ini = datos[4]

        form = ctk.CTkToplevel()
        form.title("Editar Producto")
        form.geometry("400x450")  # Un poco más alto para el combobox
        form.transient(frame_destino.winfo_toplevel())  
        form.grab_set()  

        desc_var = ctk.StringVar(value=descripcion_ini)
        precio_var = ctk.StringVar(value=str(precio_unit_ini))
        stock_var = ctk.StringVar(value=str(inventario_ini))
        categoria_var = ctk.StringVar(value=categoria_ini)

        ctk.CTkLabel(form, text="Descripción:").pack(pady=5)
        ctk.CTkEntry(form, textvariable=desc_var).pack()

        ctk.CTkLabel(form, text="Precio Unitario:").pack(pady=5)
        ctk.CTkEntry(form, textvariable=precio_var).pack()

        ctk.CTkLabel(form, text="Inventario:").pack(pady=5)
        ctk.CTkEntry(form, textvariable=stock_var).pack()

        ctk.CTkLabel(form, text="Categoría:").pack(pady=5)

        # Combobox con autocompletado para categorías
        categorias = obtener_categorias_existentes()
        categoria_combobox = ttk.Combobox(
            form, 
            textvariable=categoria_var, 
            values=categorias,
            width=38,
            state="normal"
        )
        categoria_combobox.pack(pady=5)

        # Configurar autocompletado
        def autocompletar_categoria(event):
            texto = categoria_var.get().lower()
            if texto:
                coincidencias = [cat for cat in categorias if texto in cat.lower()]
                categoria_combobox['values'] = coincidencias
                categoria_combobox.event_generate('<Down>')
            else:
                categoria_combobox['values'] = categorias

            return "break"

        categoria_combobox.bind('<KeyRelease>', autocompletar_categoria)

        error_label = ctk.CTkLabel(form, text="", text_color="red")
        error_label.pack(pady=5)

        def guardar_cambios():
            error_label.configure(text="")
            
            if not messagebox.askyesno("Confirmar", "¿Seguro que deseas modificar este producto?"):
                return
            try:
                nueva_desc = (desc_var.get() or "").strip()
                if not nueva_desc:
                    raise ValueError("La descripción no puede estar vacía.")

                nueva_categoria = (categoria_var.get() or "").strip()
                print(f"Categoría después de strip: '{nueva_categoria}'")
                if not nueva_categoria:
                    raise ValueError("La categoría no puede estar vacía.")

                nuevo_precio = (precio_var.get() or "").strip()
                if not nuevo_precio:
                    raise ValueError("El precio no puede estar vacío.")
                try:
                    precio = float(nuevo_precio)
                    if precio < 0:
                        raise ValueError("El precio debe ser un número positivo.")
                except ValueError:  
                    raise ValueError("El precio debe ser un número válido.")
                
                nuevo_stock = (stock_var.get() or "").strip()
                if not nuevo_stock:
                    raise ValueError("La cantidad no puede estar vacía.")
                try:
                    stock = int(nuevo_stock)
                    if stock < 0:
                        raise ValueError("El inventario debe ser un número entero positivo.")
                except ValueError:
                    raise ValueError("El inventario debe ser un número entero válido.")
                
                nuevo_precio_total = precio * stock

                conn = conectar_db()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE desarrollo.stock
                    SET descripcion = %s,
                        precio_unit = %s,
                        cant_inventario = %s,
                        categoria = %s,
                        precio_total = %s
                    WHERE id_articulo = %s
                """, (
                    nueva_desc,
                    precio,
                    stock,
                    nueva_categoria,
                    nuevo_precio_total,
                    id_articulo
                ))
                conn.commit()
                cur.close()
                conn.close()

                messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
                form.destroy()
                cargar_articulos()
                
            except ValueError as ve:
                error_label.configure(text=str(ve))
                print(f"Error de validación: {ve}")
            except Exception as e:
                error_label.configure(text=f"Error: {e}")
                print(f"Error general: {e}")

        ctk.CTkButton(form, text="Guardar Cambios", command=guardar_cambios, fg_color="#FF9100", hover_color="#E07B00").pack(pady=10)
        
    tree.bind("<Double-1>", editar_producto)
    
    
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
