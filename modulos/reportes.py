# Archivo: src/reportes/report_ui.py


from datetime import datetime
from tkinter import messagebox, filedialog, Tk 
import customtkinter as ctk
import pandas as pd
from modulos.exportar_excel import exportar_a_excel
from bd import conectar_db
from modulos.exportar_pdf import exportar_a_pdf 

def mostrar_menu_reportes(contenido_frame):
    # Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()
    
    # Título del módulo
    ctk.CTkLabel(
        contenido_frame, 
        text="Módulo de Reportes",
        font=("Arial", 20, "bold")
    ).pack(pady=20)
    
    # Frame para los botones de opciones
    opciones_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    opciones_frame.pack(pady=30)
    
    # Botón de Reportes de Predicción de Ventas
    btn_salida = ctk.CTkButton(
        opciones_frame,
        text="Reportes de Predicción de Ventas",
        width=180,
        height=60,
        font=("Arial", 16),
        fg_color="#FF9100",
        hover_color="#E07B00",
        command=lambda: mostrar_reporte_prediccion(contenido_frame)
    )
    btn_salida.pack(side="left", padx=20)
    
    # Botón de Salida de Artículos
    btn_garantias = ctk.CTkButton(
        opciones_frame,
        text="Reportes varios",
        width=180,
        height=60,
        font=("Arial", 16),
        fg_color="#FF9100",
        hover_color="#E07B00",
        command=lambda: mostrar_reporte(contenido_frame)
    )
    btn_garantias.pack(side="left", padx=20)
    
    
def mostrar_reporte_prediccion(contenido_frame):
    # Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()
    
    # Título del módulo
    ctk.CTkLabel(
        contenido_frame, 
        text="Reportes de Predicción de Ventas",
        font=("Arial", 20, "bold")
    ).pack(pady=20)
    
    # Frame para los botones de opciones
    opciones_frame = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    opciones_frame.pack(pady=30)
    
       
def mostrar_reporte(contenido_frame):
    """
    Muestra la interfaz de Reportes Varios con Scrollbar, filtros condicionales
    y datos de Categoría cargados desde la BD.
    """
    # 1. Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()

    # --- Configuración del Scrollbar ---
    
    canvas = ctk.CTkCanvas(contenido_frame)
    canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)

    scrollbar = ctk.CTkScrollbar(contenido_frame, orientation="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    
    scrollable_frame = ctk.CTkFrame(canvas)

    canvas_window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())

    def on_frame_configure(event):
        """Ajusta el scrollregion del canvas y el ancho del frame interno."""
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas_window_id, width=event.width)

    scrollable_frame.bind("<Configure>", on_frame_configure)
    canvas.bind('<Configure>', on_frame_configure)
    
    # Binding para el scroll del mouse
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # CONTENIDO DE LA VISTA DENTRO DE scrollable_frame 
    ctk.CTkLabel(
        scrollable_frame, 
        text="Generador de Reportes Varios",
        font=("Arial", 22, "bold")
    ).pack(pady=30)

    # El control_frame es transparente para eliminar el marco blanco
    control_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent") 
    control_frame.pack(pady=20, padx=40)

    # 1. SELECCIÓN DEL TIPO DE REPORTE
    ctk.CTkLabel(control_frame, text="1. Seleccione el Tipo de Reporte", font=("Arial", 14, "bold")).pack(pady=(15, 5), padx=20, anchor='w')
    
    tipos_reporte = ["Inventario", "Ventas"]
    reporte_seleccionado = ctk.CTkOptionMenu(
        control_frame,
        values=tipos_reporte,
        width=250,
        height=35,
        command=lambda selection: actualizar_opciones(selection, ventas_params_frame)
    )
    reporte_seleccionado.pack(pady=10, padx=20)
    reporte_seleccionado.set("Inventario")

    # 2. SELECCIÓN DE CATEGORÍA
    categorias_disponibles = obtener_categorias_garantias()
    
    ctk.CTkLabel(control_frame, text="2. Seleccione la Categoría", font=("Arial", 14, "bold")).pack(pady=(15, 5), padx=20, anchor='w') 

    categoria_menu = ctk.CTkOptionMenu(
        control_frame,
        values=categorias_disponibles,
        width=250,
        height=35
    )
    categoria_menu.pack(pady=10, padx=20)
    categoria_menu.set(categorias_disponibles[0]) 

    # 3. PARÁMETROS CONDICIONALES DE VENTA
    ventas_params_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
    
    # Controles para ID de Producto y Rango de Fechas
    ctk.CTkLabel(ventas_params_frame, text="ID de Producto:").pack(pady=5)
    id_producto_entry = ctk.CTkEntry(ventas_params_frame, placeholder_text="Ej: 11109", width=250)
    id_producto_entry.pack(pady=5)

    ctk.CTkLabel(ventas_params_frame, text="Fecha de Inicio (DD-MM-YYYY):").pack(pady=5)
    fecha_inicio_entry = ctk.CTkEntry(ventas_params_frame, placeholder_text="Ej: 01-01-2024", width=250)
    fecha_inicio_entry.pack(pady=5)

    ctk.CTkLabel(ventas_params_frame, text="Fecha Fin (DD-MM-YYYY):").pack(pady=5)
    fecha_fin_entry = ctk.CTkEntry(ventas_params_frame, placeholder_text="Ej: 31-12-2024", width=250)
    fecha_fin_entry.pack(pady=5)
    
    # 4. SELECCIÓN DEL FORMATO DE SALIDA
    ctk.CTkLabel(control_frame, text="3. Seleccione el Formato de Salida", font=("Arial", 14, "bold")).pack(pady=(15, 5), padx=20, anchor='w')
    
    formatos_salida = ["Excel", "PDF"]
    formato_seleccionado = ctk.CTkOptionMenu(
        control_frame,
        values=formatos_salida,
        width=250,
        height=35
    )
    formato_seleccionado.pack(pady=10, padx=20)
    formato_seleccionado.set("Excel")

    button_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    button_frame.pack(pady=40)
    
    # Botón de GENERAR
    ctk.CTkButton(
        button_frame,
        text="Generar Reporte",
        width=150,
        height=40,
        fg_color="#006400",
        hover_color="#004d00",
        command=lambda: generar_reporte_varios(
            reporte_seleccionado.get(),
            categoria_menu.get(),
            formato_seleccionado.get(),
            id_producto_entry.get(),
            fecha_inicio_entry.get(),
            fecha_fin_entry.get()
        )
    ).pack(side="left", padx=15)

    # Botón de ATRÁS
    ctk.CTkButton(
        button_frame,
        text="← Atrás",
        width=150,
        height=40,
        fg_color="#E07B00",
        hover_color="#C06C00",
        command=lambda: mostrar_menu_reportes(contenido_frame)
    ).pack(side="left", padx=15)
    
    actualizar_opciones(reporte_seleccionado.get(), ventas_params_frame)


def actualizar_opciones(selection, ventas_frame):
    """
    Muestra u oculta solo el frame de parámetros avanzados (ID de Producto y Fechas).
    La Categoría siempre permanece visible.
    """
    if selection == "Ventas":
        ventas_frame.pack(pady=10, padx=20, fill="x")
    else:
        ventas_frame.pack_forget()


def generar_reporte_varios(tipo_reporte, categoria, formato_salida, id_producto, fecha_inicio, fecha_fin):
    """
    Función principal que maneja la lógica de obtención, validación, 
    y solicita la ruta de guardado al usuario, asegurando la extensión.
    """
    
    # Inicialización de root para asegurar que esté disponible en caso de error
    root = None
    try:
        root = Tk()
        root.withdraw()
    except Exception:
        pass 

    filtros = {
        'categoria': categoria,
        'id_producto': None,
        'fecha_inicio': None,
        'fecha_fin': None,
    }

    try:
        df_reporte = None
        
        # 1. VALIDACIÓN Y OBTENCIÓN DE DATOS (Simulación de consulta) ---
        
        if tipo_reporte == "Inventario":
            df_reporte = consultar_stock(categoria)
            
            if df_reporte.empty:
                messagebox.showinfo("Resultado", f"No se encontraron artículos en stock para la categoría: {categoria}")
                return
            
            print(f"Generando Reporte de Inventario para categoría: {categoria}")

        elif tipo_reporte == "Ventas":
            # Inicialización de filtros con valores por defecto y nulos
            id_prod_filter = None
            fecha_inicio_sql = None
            
            # Si no se da fecha fin, el reporte va hasta hoy
            fecha_fin_sql = datetime.now().strftime('%Y-%m-%d') 
            
            try:
                # 1. Validación y seteo de ID de Producto (opcional)
                if id_producto.strip():
                    id_prod_filter = int(id_producto.strip())
                
                # 2. Validación y seteo de Fecha de Inicio (opcional)
                if fecha_inicio.strip():
                    start_date_obj = datetime.strptime(fecha_inicio.strip(), '%d-%m-%Y')
                    fecha_inicio_sql = start_date_obj.strftime('%Y-%m-%d')
                
                # 3. Validación y seteo de Fecha Fin (opcional)
                if fecha_fin.strip():
                    end_date_obj = datetime.strptime(fecha_fin.strip(), '%d-%m-%Y')
                    fecha_fin_sql = end_date_obj.strftime('%Y-%m-%d')
                    
                if not fecha_inicio_sql:
                    fecha_inicio_sql = '2000-01-01' 

                filtros['id_producto'] = id_prod_filter if id_prod_filter is not None else 'Todos'
                filtros['fecha_inicio'] = fecha_inicio if fecha_inicio.strip() else 'Desde Inicio'
                filtros['fecha_fin'] = fecha_fin if fecha_fin.strip() else datetime.now().strftime('%d-%m-%Y') # Usamos la fecha actual en formato local
                
                # Resumen de filtros
                filtro_id_str = f"ID: {id_prod_filter}" if id_prod_filter is not None else "Todos los IDs"
                filtro_fechas_str = f"desde {fecha_inicio_sql} hasta {fecha_fin_sql}"
                print(f"Obteniendo Ventas (Categoría: {categoria}, {filtro_id_str}) {filtro_fechas_str}")

                df_reporte = consultar_ventas(id_prod_filter, fecha_inicio_sql, fecha_fin_sql, categoria)
                
                # Resumen de filtros aplicados
                filtro_id_str = f"ID: {id_prod_filter}" if id_prod_filter is not None else "Todos los IDs"
                filtro_fechas_str = f"desde {fecha_inicio_sql} hasta {fecha_fin_sql}"
                
                print(f"Obteniendo Ventas (Categoría: {categoria}, {filtro_id_str}) {filtro_fechas_str}")
                print(f"Obteniendo Ventas para ID {id_producto} entre {fecha_inicio_sql} y {fecha_fin_sql}")
                
                data = {"Fecha_Venta": [fecha_inicio_sql, fecha_fin_sql], 
                        "ID_Producto": [id_prod_filter or 100, id_prod_filter or 100], 
                        "Cantidad": [10, 5],
                        "Categoria": [categoria, categoria]}
                df_reporte = pd.DataFrame(data)

            except ValueError:
                messagebox.showerror("Error de Validación", "Revise: ID de Producto debe ser numérico. Las fechas, si se ingresan, deben estar en formato DD-MM-YYYY.")
                return

        # 2. Verificación de datos
        if df_reporte is None or df_reporte.empty:
            messagebox.showinfo("Resultado", f"No se encontraron datos para el reporte de {tipo_reporte} con los parámetros ingresados.")
            return

        elif tipo_reporte == "Ventas":
            id_prod_filter = None
            fecha_inicio_sql = None
            fecha_fin_sql = datetime.now().strftime('%Y-%m-%d')
            
            try:
                # 1. Validación y seteo de ID de Producto (opcional)
                if id_producto.strip():
                    id_prod_filter = int(id_producto.strip())
                
                # 2. Validación de Fechas
                if fecha_inicio.strip():
                    start_date_obj = datetime.strptime(fecha_inicio.strip(), '%d-%m-%Y')
                    fecha_inicio_sql = start_date_obj.strftime('%Y-%m-%d')
                
                if fecha_fin.strip():
                    end_date_obj = datetime.strptime(fecha_fin.strip(), '%d-%m-%Y')
                    fecha_fin_sql = end_date_obj.strftime('%Y-%m-%d')

                if not fecha_inicio_sql:
                    fecha_inicio_sql = '2000-01-01' 

                # Resumen de filtros
                filtro_id_str = f"ID: {id_prod_filter}" if id_prod_filter is not None else "Todos los IDs"
                filtro_fechas_str = f"desde {fecha_inicio_sql} hasta {fecha_fin_sql}"
                
                print(f"Obteniendo Ventas (Categoría: {categoria}, {filtro_id_str}) {filtro_fechas_str}")

                df_reporte = consultar_ventas(id_prod_filter, fecha_inicio_sql, fecha_fin_sql, categoria)

            except ValueError:
                messagebox.showerror("Error de Validación", "Revise: ID de Producto debe ser numérico. Las fechas, si se ingresan, deben estar en formato DD-MM-YYYY.")
                return

        # 2. Verificación de datos
        if df_reporte is None or df_reporte.empty:
            msg = f"No se encontraron datos para el reporte de {tipo_reporte}"
            if categoria != "Todas las Categorías":
                 msg += f" (Categoría: {categoria})"
            messagebox.showinfo("Resultado", msg)
            return
        
        # --- 3. SOLICITAR RUTA DE GUARDADO AL USUARIO ---
            
        nombre_base = f"{tipo_reporte}_{categoria.replace(' ', '_')}"
        if tipo_reporte == 'Ventas' and id_producto:
             nombre_base = f"Ventas_ID{id_producto}"
             
        extension = ".xlsx" if formato_salida == "Excel" else f".{formato_salida.lower()}"
        
        # Muestra el diálogo de guardado del sistema
        file_path = filedialog.asksaveasfilename(
            defaultextension=extension,
            initialfile=f"{nombre_base}_{pd.Timestamp.now().strftime('%Y%m%d')}",
            title=f"Guardar Reporte de {tipo_reporte} como {formato_salida}",
            filetypes=[(f"{formato_salida} files", f"*{extension}")]
        )
        
        # 4. VERIFICACIÓN Y CORRECCIÓN DE LA EXTENSIÓN (Soluciona el ValueError) ---
        if file_path:
            if not file_path.lower().endswith(extension):
                file_path += extension

        if not file_path:
            messagebox.showinfo("Cancelado", "Guardado del reporte cancelado por el usuario.")
            return
            
        # 5. LÓGICA DE EXPORTACIÓN ---
        if formato_salida == "Excel":
            exportar_a_excel(df_reporte, file_path)
            messagebox.showinfo("Éxito", f"Reporte de {tipo_reporte} exportado a Excel correctamente en:\n{file_path}")
        
        elif formato_salida == "PDF":
            exportar_a_pdf(df_reporte, file_path, tipo_reporte, filtros) 
            messagebox.showinfo("Éxito", f"Reporte de {tipo_reporte} exportado a PDF correctamente en:\n{file_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al generar el reporte: {e}")
        
    finally:
        if root:
             root.destroy()
        
        
def obtener_categorias_garantias():
    """
    Se conecta a la BD usando conectar_db() y obtiene una lista única de categorías.
    Maneja la conexión de psycopg2 (conn) directamente con pd.read_sql.
    """
    conn = conectar_db()
    if conn is None:
        messagebox.showerror("Error de Conexión", "No se pudo conectar a la base de datos para obtener categorías.")
        return ["Error de Conexión"]

    SQL_QUERY = """
    SELECT DISTINCT gar_categoria
    FROM desarrollo.garantias
    WHERE gar_categoria IS NOT NULL AND gar_categoria != ''
    ORDER BY gar_categoria;
    """
    
    try:
        # ⚠️ USAMOS LA CONEXIÓN DIRECTA DE PSYCOPG2 (conn) ⚠️
        # Aunque esto genera la advertencia (UserWarning), es la manera de mantener 
        # la compatibilidad con el resto de tus módulos.
        df_categorias = pd.read_sql(SQL_QUERY, conn)
        
        # Lógica de truncamiento y limpieza
        def truncar_categoria(nombre):
            if len(nombre) > 20:
                # Truncamos a 20 caracteres
                return nombre[:20] + "..." 
            return nombre
            
        df_categorias['gar_categoria'] = df_categorias['gar_categoria'].apply(truncar_categoria)

        categorias = list(df_categorias['gar_categoria'].unique())
        categorias.insert(0, "Todas las Categorías")
        
        return categorias
        
    except Exception as e:
        error_msg = f"Error al consultar las categorías de garantías: {e}"
        print(f"❌ {error_msg}")
        messagebox.showerror("Error de Consulta", error_msg)
        return ["Error de Consulta"]
        
    finally:
        # ⚠️ CERRAMOS LA CONEXIÓN ASEGURANDO LA LIBERACIÓN DE RECURSOS
        if conn:
            conn.close()
    

def consultar_stock(categoria: str) -> pd.DataFrame:
    """
    Consulta la tabla desarrollo.stock, filtrando por categoría si es necesario.
    
    :param categoria: La categoría seleccionada por el usuario (o "Todas las Categorías").
    :return: Un DataFrame con los datos de stock.
    """
    conn = conectar_db()
    if conn is None:
        return pd.DataFrame() 

    # 1. Construir la consulta SQL
    SQL_QUERY = """
    SELECT 
        id_articulo,
        descripcion,
        precio_unit,
        cant_inventario,
        precio_total,
        categoria
    FROM 
        desarrollo.stock
    """
    
    # 2. Aplicar el filtro condicional
    params = {}
    if categoria != "Todas las Categorías":
        SQL_QUERY += " WHERE categoria = %(cat)s"
        params = {'cat': categoria}

    SQL_QUERY += " ORDER BY categoria, descripcion;"

    df_stock = pd.DataFrame()
    try:
        if categoria != "Todas las Categorías":
            SQL_QUERY = f"SELECT id_articulo, descripcion, precio_unit, cant_inventario, precio_total, categoria FROM desarrollo.stock WHERE categoria = '{categoria.replace("'", "''")}' ORDER BY categoria, descripcion;"
        df_stock = pd.read_sql(SQL_QUERY, conn)
        
        print(f"✅ Registros de Stock obtenidos: {len(df_stock)}")
        
    except Exception as e:
        error_msg = f"Error al consultar la tabla desarrollo.stock: {e}"
        print(f"❌ {error_msg}")
        messagebox.showerror("Error de Consulta", error_msg)
        
    finally:
        if conn:
            conn.close()
            
    return df_stock
    
    
def consultar_ventas(id_producto: int, fecha_inicio_sql: str, fecha_fin_sql: str, categoria: str) -> pd.DataFrame:
    """
    Consulta la tabla desarrollo.ventas, haciendo JOIN con clientes y stock para incluir 
    el nombre del cliente y permitir el filtro por categoría.
    
    :param id_producto: ID del producto (None si se buscan todos).
    :param fecha_inicio_sql: Fecha de inicio en formato 'YYYY-MM-DD'.
    :param fecha_fin_sql: Fecha de fin en formato 'YYYY-MM-DD'.
    :param categoria: La categoría seleccionada (o "Todas las Categorías").
    :return: Un DataFrame con los datos de ventas.
    """
    conn = conectar_db()
    if conn is None:
        return pd.DataFrame() 

    
    params = [fecha_inicio_sql, fecha_fin_sql]
    
    # 1. Definición de la consulta base (con lógica de JOIN condicional)
    
    if categoria != "Todas las Categorías":
        SQL_QUERY = """
        SELECT 
            v.v_comprob as COMPROBANTE, v.v_tipotransacc as TIPO_TRANSACCION, v.v_montous_unit AS MONTO_UNITARIO, v.v_montous_total AS MONTO_TOTAL,
            v.v_id_producto AS ID_PRODUCTO, v.v_product AS PRODUCTO, s.categoria as CATEGORIA, v.v_id_cliente AS ID_CLIENTE,
            c.nombre AS nombre_cliente, 
            v.v_fact AS FACTURA, v.v_cantidad AS CANTIDAD, u.user_name AS USUARIO, to_char(v.v_fecha, 'DD/MM/YYYY HH24:MI:SS') AS FECHA_VENTA 
        FROM 
            desarrollo.ventas v
        LEFT JOIN 
            desarrollo.clientes c ON v.v_id_cliente = c.id_cliente
        LEFT JOIN 
            desarrollo.stock s ON v.v_id_producto = s.id_articulo 
        LEFT JOIN
            desarrollo.usuarios u ON v.v_user = u.user_key
        WHERE 
            v.v_fecha BETWEEN %s AND %s 
            AND s.categoria = %s 
        """
        params.append(categoria)
        
    else:
        SQL_QUERY = """
        SELECT 
            v.v_comprob as COMPROBANTE, v.v_tipotransacc as TIPO_TRANSACCION, v.v_montous_unit AS MONTO_UNITARIO, v.v_montous_total AS MONTO_TOTAL,
            v.v_id_producto AS ID_PRODUCTO, v.v_product AS PRODUCTO, s.categoria as CATEGORIA, v.v_id_cliente AS ID_CLIENTE,
            c.nombre AS nombre_cliente, 
            v.v_fact AS FACTURA, v.v_cantidad AS CANTIDAD, u.user_name AS USUARIO, to_char(v.v_fecha, 'DD/MM/YYYY HH24:MI:SS') AS FECHA_VENTA 
        FROM 
            desarrollo.ventas v
        LEFT JOIN 
            desarrollo.clientes c ON v.v_id_cliente = c.id_cliente
        LEFT JOIN 
            desarrollo.stock s ON v.v_id_producto = s.id_articulo 
        LEFT JOIN
            desarrollo.usuarios u ON v.v_user = u.user_key
        WHERE 
            v.v_fecha BETWEEN %s AND %s 
        """
        
    # 2. Aplicar el filtro de ID de Producto (condicional)
    if id_producto is not None:
        SQL_QUERY += " AND v.v_id_producto = %s"
        params.append(id_producto)

    
    SQL_QUERY += " ORDER BY v.v_fecha DESC;"
    
    df_ventas = pd.DataFrame()
    try:
        # Ejecución de la consulta con pd.read_sql
        df_ventas = pd.read_sql(SQL_QUERY, conn, params=params)
        
        print(f"✅ Registros de Ventas obtenidos: {len(df_ventas)}")
        
    except Exception as e:
        error_msg = f"Error al consultar las ventas con filtros: {e}"
        print(f"❌ {error_msg}")
        messagebox.showerror("Error de Consulta", error_msg)
        
    finally:
        if conn:
            conn.close()
            
    return df_ventas
    
    
    
    
    
    
    
    
    
    