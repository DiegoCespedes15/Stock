# modulos/productos.py
from tkinter import messagebox
import customtkinter as ctk
from sqlalchemy import null
from bd import conectar_db
import tkinter.ttk as ttk
from decimal import Decimal, InvalidOperation


def mostrar_productos(frame_destino):
    for widget in frame_destino.winfo_children():
        widget.destroy()

    ctk.CTkLabel(frame_destino, text="Listado de Artículos", font=("Arial", 18)).pack(pady=10)

    # --- Filtros ---
    filtros_frame = ctk.CTkFrame(frame_destino)
    filtros_frame.pack(pady=5, padx=10, fill="x")

    descripcion_var = ctk.StringVar()
    categoria_var = ctk.StringVar()


    ctk.CTkLabel(filtros_frame, text="Descripción:").grid(row=0, column=0, padx=5, pady=5)
    descripcion_entry = ctk.CTkEntry(filtros_frame, textvariable=descripcion_var, width=150)
    descripcion_entry.grid(row=0, column=1, padx=5, pady=5)

    ctk.CTkLabel(filtros_frame, text="Categoría:").grid(row=0, column=2, padx=5, pady=5)
    categoria_entry = ctk.CTkEntry(filtros_frame, textvariable=categoria_var, width=150)
    categoria_entry.grid(row=0, column=3, padx=5, pady=5)

    # --- Tabla de artículos ---
    tabla_frame = ctk.CTkFrame(frame_destino)
    tabla_frame.pack(padx=10, pady=10, fill="both", expand=True)

    columnas = ("ID", "Descripción", "Precio Unit", "Inventario", "Categoría", "Precio Total")
    tree = ttk.Treeview(tabla_frame, columns=columnas, show="headings")

    # Configurar encabezados y columnas
    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=100)

    # Scroll vertical
    scrollbar_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.pack(side="right", fill="y")

    # Scroll horizontal
    scrollbar_x = ttk.Scrollbar(tabla_frame, orient="horizontal", command=tree.xview)
    tree.configure(xscrollcommand=scrollbar_x.set)
    scrollbar_x.pack(side="bottom", fill="x")

    tree.pack(fill="both", expand=True)

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
            ctk.CTkLabel(frame_destino, text=f"Error: {e}", text_color="red").pack()

    # --- Botón de búsqueda ---
    buscar_btn = ctk.CTkButton(filtros_frame, text="Buscar", command=cargar_articulos, fg_color="#FF9100", hover_color="#E07B00")
    buscar_btn.grid(row=0, column=4, padx=10)

    # Carga inicial
    cargar_articulos()
    
    # --- Botones de acción (Agregar / Eliminar) ---
    acciones_frame = ctk.CTkFrame(frame_destino)
    acciones_frame.pack(pady=5)


    #--------------------------------------------------------------------------------------------------------------------------------------------


    def abrir_formulario_agregar():
        form = ctk.CTkToplevel()
        form.title("Agregar Producto")
        form.geometry("400x400")
        form.transient(frame_destino.winfo_toplevel())
        form.grab_set()

        # Variables para los campos del formulario
        desc_var = ctk.StringVar()
        precio_var = ctk.StringVar()
        stock_var = ctk.StringVar()
        categoria_var = ctk.StringVar()

        ctk.CTkLabel(form, text="Descripción:").pack(pady=5)
        ctk.CTkEntry(form, textvariable=desc_var).pack()

        ctk.CTkLabel(form, text="Precio Unitario:").pack(pady=5)
        ctk.CTkEntry(form, textvariable=precio_var).pack()

        ctk.CTkLabel(form, text="Cantidad Inventario:").pack(pady=5)
        ctk.CTkEntry(form, textvariable=stock_var).pack()

        ctk.CTkLabel(form, text="Categoría:").pack(pady=5)
        ctk.CTkEntry(form, textvariable=categoria_var).pack()
        
        error_label = ctk.CTkLabel(form, text="", text_color="red")
        error_label.pack(pady=5)

        def guardar():
            if not messagebox.askyesno("Confirmar", "¿Seguro que deseas agregar este producto?"):
                return
            
            try:
                descripcion = desc_var.get().strip()
                if not descripcion:
                    raise ValueError("La descripción no puede estar vacía.")

                categoria = categoria_var.get().strip()
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
                form.destroy()
                cargar_articulos()
                
            except ValueError as ve:
                error_label.configure(text=str(ve))
            except Exception as e:
                error_label.configure(text=f"Error: {e}")
        ctk.CTkButton(form, text="Guardar", command=guardar, fg_color="#FF9100", hover_color="#E07B00").pack(pady=10)


    #--------------------------------------------------------------------------------------------------------------------------------------------

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
                ctk.CTkLabel(frame_destino, text=f"Error: {e}", text_color="red").pack()
        else:
            ctk.CTkLabel(frame_destino, text="Selecciona un producto para eliminar.", text_color="red").pack()

    ctk.CTkButton(acciones_frame, text="Agregar Producto", command=abrir_formulario_agregar, fg_color="#4CAF50").pack(side="left", padx=10)
    ctk.CTkButton(acciones_frame, text="Eliminar Seleccionado", command=eliminar_producto, fg_color="#FF4444").pack(side="left", padx=10)
    
    
    #--------------------------------------------------------------------------------------------------------------------------------------------
    
    
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
        form.geometry("400x420")
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
        ctk.CTkEntry(form, textvariable=categoria_var).pack()

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
                
                nuevo_precio_total = nuevo_precio * nuevo_stock


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
                    float(nuevo_precio),   # si tu columna es numeric/float
                    int(nuevo_stock),
                    nueva_categoria,
                    float(nuevo_precio_total),
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
            except Exception as e:
                error_label.configure(text=f"Error: {e}")

        ctk.CTkButton(form, text="Guardar Cambios", command=guardar_cambios, fg_color="#FF9100", hover_color="#E07B00").pack(pady=10)
    tree.bind("<Double-1>", editar_producto)
