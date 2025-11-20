# Archivo: src/reportes/report_ui.py

from datetime import datetime, timedelta
from tkinter import messagebox, filedialog, Tk 
import customtkinter as ctk
import numpy as np
import pandas as pd
from modulos.exportar_excel import exportar_a_excel
from bd import conectar_db
from modulos.exportar_pdf import exportar_a_pdf 
from tkcalendar import Calendar, DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.append(src_dir)

try:
    from optimization.inventory_optimizer import generar_dataset_reporte
except ImportError:
    print("⚠️ Advertencia: No se encontró el módulo optimization.inventory_optimizer")


def mostrar_menu_reportes(contenido_frame):
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
        # command=lambda: mostrar_reportes_predictivos(contenido_frame) # Asumo que tienes esta func
        command=lambda: messagebox.showinfo("Info", "Función de gráficos en desarrollo")
    )
    btn_salida.pack(side="left", padx=20)
    
    # Botón de Reportes Varios
    btn_garantias = ctk.CTkButton(
        opciones_frame,
        text="Reportes Varios / Compras",
        width=180,
        height=60,
        font=("Arial", 16),
        fg_color="#FF9100",
        hover_color="#E07B00",
        command=lambda: mostrar_reporte(contenido_frame)
    )
    btn_garantias.pack(side="left", padx=20)
    
    
#-------------------------------------------------------------------------------------------------------------------
#aqui ira el codigo de prediccion


#-------------------------------------------------------------------------------------------------------------------


def open_calendar(master, entry_widget):
    """Abre una ventana de calendario y establece la fecha seleccionada en el widget de entrada."""
    
    x_pos = entry_widget.winfo_rootx()
    y_pos = entry_widget.winfo_rooty()
    
    # Crea una ventana Toplevel para el calendario
    top = ctk.CTkToplevel(master)  # Usa el 'master' (la ventana principal) para el Toplevel
    top.title("Seleccionar Fecha")

    # Obtiene la fecha actual por defecto
    now = datetime.now()

    # Crea el widget Calendar
    cal = Calendar(top, 
                   selectmode='day', 
                   year=now.year, 
                   month=now.month, 
                   day=now.day,
                   date_pattern='dd-mm-yyyy') 
    cal.pack(padx=10, pady=10)

    def grab_date():
        """Función que se llama al seleccionar la fecha."""
        selected_date = cal.get_date()
        entry_widget.delete(0, 'end')
        entry_widget.insert(0, selected_date)
        top.destroy() 

    # Botón para confirmar la fecha (usando tkinter base, ya que es una ventana Toplevel)
    ctk.CTkButton(top, text="Aceptar", command=grab_date).pack(pady=5)
    
    top.geometry(f"+{x_pos}+{y_pos + 25}") 
    
    # Bloquea la interacción con la ventana principal hasta que se cierre el calendario
    top.deiconify() 
    top.grab_set() 
    master.wait_window(top)

       
def mostrar_reporte(contenido_frame):
    """
    Muestra la interfaz de Reportes Varios con Scrollbar, filtros condicionales
    y datos de Categoría cargados desde la BD.
    """
    # 1. Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()
    canvas = ctk.CTkCanvas(contenido_frame)
    canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
    scrollbar = ctk.CTkScrollbar(contenido_frame, orientation="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollable_frame = ctk.CTkFrame(canvas)
    canvas_window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas_window_id, width=event.width)
    scrollable_frame.bind("<Configure>", on_frame_configure)
    canvas.bind('<Configure>', on_frame_configure)
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # --- CONTENIDO DE LA VISTA ---
    ctk.CTkLabel(scrollable_frame, text="Generador de Reportes", font=("Arial", 22, "bold")).pack(pady=30)
    control_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent") 
    control_frame.pack(pady=20, padx=40)

    # 1. Tipo de Reporte
    ctk.CTkLabel(control_frame, text="1. Seleccione el Tipo de Reporte", font=("Arial", 14, "bold")).pack(pady=(15, 5), padx=20, anchor='w')
    tipos_reporte = ["Inventario", "Ventas", "Optimización de Compras (IA)"]
    reporte_seleccionado = ctk.CTkOptionMenu(control_frame, values=tipos_reporte, width=250, height=35,
        command=lambda sel: actualizar_opciones(sel, ventas_params_frame, optim_params_frame, categoria_menu)) # ✅ Actualizado
    reporte_seleccionado.pack(pady=10, padx=20)
    reporte_seleccionado.set("Inventario")

    # 2. Categoría
    ctk.CTkLabel(control_frame, text="2. Seleccione la Categoría", font=("Arial", 14, "bold")).pack(pady=(15, 5), padx=20, anchor='w')
    categorias_disponibles = obtener_categorias_garantias()
    categoria_menu = ctk.CTkOptionMenu(control_frame, values=categorias_disponibles, width=250, height=35)
    categoria_menu.pack(pady=10, padx=20)
    categoria_menu.set(categorias_disponibles[0]) 

    # --- 3. PARÁMETROS CONDICIONALES ---
    
    # ✅ NUEVO: Frame para Optimización (Fecha Simulada)
    optim_params_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
    ctk.CTkLabel(optim_params_frame, text="*Simular Reporte para la Fecha:*", font=("Arial", 12, "italic")).pack(pady=5, anchor='w')
    frame_fecha_simulada = ctk.CTkFrame(optim_params_frame, fg_color="transparent")
    frame_fecha_simulada.pack(pady=5, fill="x", padx=10)
    
    # Para tu demo, restamos un año a la fecha actual
    fecha_demo_default = (datetime.now() - timedelta(days=365)).strftime('%d-%m-%Y')
    
    fecha_simulada_entry = ctk.CTkEntry(frame_fecha_simulada, placeholder_text="Ej: 16-11-2024", width=210)
    fecha_simulada_entry.pack(side="left", fill="x", expand=True)
    fecha_simulada_entry.insert(0, fecha_demo_default) # Insertamos la fecha de hace un año
    
    ctk.CTkButton(frame_fecha_simulada, text="📅", width=30, 
        command=lambda: open_calendar(scrollable_frame.winfo_toplevel(), fecha_simulada_entry)).pack(side="left", padx=(5, 0))

    # Frame para Ventas (ID Producto y Rango)
    ventas_params_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
    ctk.CTkLabel(ventas_params_frame, text="ID de Producto:").pack(pady=5)
    id_producto_entry = ctk.CTkEntry(ventas_params_frame, placeholder_text="Ej: 11109", width=250)
    id_producto_entry.pack(pady=5)
    # ... (El resto del frame 'ventas_params_frame' con fecha_inicio y fecha_fin se mantiene igual) ...
    ctk.CTkLabel(ventas_params_frame, text="Fecha de Inicio (DD-MM-YYYY):").pack(pady=5, anchor='w')
    frame_fecha_inicio = ctk.CTkFrame(ventas_params_frame, fg_color="transparent")
    frame_fecha_inicio.pack(pady=5, fill="x", padx=10)
    fecha_inicio_entry = ctk.CTkEntry(frame_fecha_inicio, placeholder_text="Ej: 01-01-2024", width=210)
    fecha_inicio_entry.pack(side="left", fill="x", expand=True)
    ctk.CTkButton(frame_fecha_inicio, text="📅", width=30, command=lambda: open_calendar(scrollable_frame.winfo_toplevel(), fecha_inicio_entry)).pack(side="left", padx=(5, 0))
    ctk.CTkLabel(ventas_params_frame, text="Fecha Fin (DD-MM-YYYY):").pack(pady=5, anchor='w')
    frame_fecha_fin = ctk.CTkFrame(ventas_params_frame, fg_color="transparent")
    frame_fecha_fin.pack(pady=5, fill="x", padx=10)
    fecha_fin_entry = ctk.CTkEntry(frame_fecha_fin, placeholder_text="Ej: 31-12-2024", width=210)
    fecha_fin_entry.pack(side="left", fill="x", expand=True)
    ctk.CTkButton(frame_fecha_fin, text="📅", width=30, command=lambda: open_calendar(scrollable_frame.winfo_toplevel(), fecha_fin_entry)).pack(side="left", padx=(5, 0))


    # 4. Formato de Salida
    ctk.CTkLabel(control_frame, text="3. Seleccione el Formato de Salida", font=("Arial", 14, "bold")).pack(pady=(15, 5), padx=20, anchor='w')
    formatos_salida = ["Excel", "PDF"]
    formato_seleccionado = ctk.CTkOptionMenu(control_frame, values=formatos_salida, width=250, height=35)
    formato_seleccionado.pack(pady=10, padx=20)
    formato_seleccionado.set("Excel")

    # 5. Botones
    button_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    button_frame.pack(pady=40)
    
    ctk.CTkButton(button_frame, text="Generar Reporte", width=150, height=40, fg_color="#006400", hover_color="#004d00",
        command=lambda: generar_reporte_varios(
            reporte_seleccionado.get(),
            categoria_menu.get(),
            formato_seleccionado.get(),
            id_producto_entry.get(),
            fecha_inicio_entry.get(),
            fecha_fin_entry.get(),
            fecha_simulada_entry.get() # ✅ NUEVO: Pasamos la fecha simulada
        )
    ).pack(side="left", padx=15)
    ctk.CTkButton(button_frame, text="← Atrás", width=150, height=40, fg_color="#E07B00", hover_color="#C06C00",
        command=lambda: mostrar_menu_reportes(contenido_frame)).pack(side="left", padx=15)
    
    # Iniciar estado de la UI
    actualizar_opciones(reporte_seleccionado.get(), ventas_params_frame, optim_params_frame, categoria_menu)


def actualizar_opciones(selection, ventas_frame, optim_frame, categoria_menu):
    """
    Muestra u oculta frames según el tipo de reporte.
    """
    # Ocultar todos los frames condicionales
    ventas_frame.pack_forget()
    optim_frame.pack_forget()
    
    if selection == "Ventas":
        ventas_frame.pack(pady=10, padx=20, fill="x")
        categoria_menu.configure(state="normal")
    elif selection == "Inventario":
        categoria_menu.configure(state="normal")
    elif selection == "Optimización de Compras (IA)":
        optim_frame.pack(pady=10, padx=20, fill="x") # Mostrar frame de simulación
        categoria_menu.configure(state="normal")


def generar_reporte_varios(tipo_reporte, categoria, formato_salida, id_producto, fecha_inicio, fecha_fin, fecha_simulada=None):
    """
    Función principal que maneja la lógica de obtención de datos y exportación.
    """
    # ... (Inicialización de root para dialogo de archivos) ...
    root = None
    try:
        root = Tk()
        root.withdraw()
    except Exception: pass 

    filtros = {'categoria': categoria}
    df_reporte = None
    
    try:
        # 1. LÓGICA SEGÚN TIPO DE REPORTE
        if tipo_reporte == "Inventario":
            # ... (Tu lógica de Inventario se mantiene igual) ...
            df_reporte = consultar_stock(categoria)

        elif tipo_reporte == "Optimización de Compras (IA)":
            print("🔮 Ejecutando motor de optimización (XGBoost + EOQ)...")
            
            # Validar y formatear la fecha simulada
            try:
                fecha_obj = datetime.strptime(fecha_simulada.strip(), '%d-%m-%Y')
                fecha_sql = fecha_obj.strftime('%Y-%m-%d')
                filtros['fecha_simulada'] = fecha_sql
            except ValueError:
                messagebox.showerror("Error", "Fecha de simulación inválida. Use formato DD-MM-YYYY.")
                return

            df_reporte = generar_dataset_reporte(categoria, fecha_sql) # ✅ Le pasamos la fecha
            
            if df_reporte.empty:
                messagebox.showinfo("Resultado", "No hay recomendaciones (Stock saludable o sin datos).")
                return

        elif tipo_reporte == "Ventas":
            # ... (Tu lógica de Ventas se mantiene igual) ...
            try:
                id_prod_filter = int(id_producto.strip()) if id_producto.strip() else None
                fecha_inicio_sql = datetime.strptime(fecha_inicio.strip(), '%d-%m-%Y').strftime('%Y-%m-%d') if fecha_inicio.strip() else '2000-01-01'
                fecha_fin_sql = datetime.strptime(fecha_fin.strip(), '%d-%m-%Y').strftime('%Y-%m-%d') if fecha_fin.strip() else datetime.now().strftime('%Y-%m-%d')
                
                filtros['id_producto'] = id_prod_filter if id_prod_filter else 'Todos'
                filtros['fecha_inicio'] = fecha_inicio if fecha_inicio else 'Inicio'
                filtros['fecha_fin'] = fecha_fin if fecha_fin else 'Hoy'
                
                df_reporte = consultar_ventas(id_prod_filter, fecha_inicio_sql, fecha_fin_sql, categoria)
            except ValueError:
                messagebox.showerror("Error", "Revise formatos (Fecha DD-MM-YYYY, ID numérico).")
                return
        
        # ... (Resto de tu lógica de guardado de Excel/PDF se mantiene igual) ...
        if df_reporte is None or df_reporte.empty:
            messagebox.showinfo("Resultado", "No se generaron datos para el reporte.")
            return

        nombre_base = f"{tipo_reporte.replace(' ', '_')}_{categoria.replace(' ', '_')}"[:30]
        extension = ".xlsx" if formato_salida == "Excel" else ".pdf"
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=extension,
            initialfile=f"{nombre_base}_{pd.Timestamp.now().strftime('%Y%m%d')}",
            title=f"Guardar {tipo_reporte}",
            filetypes=[(f"{formato_salida}", f"*{extension}")]
        )
        if not file_path: return
        if not file_path.lower().endswith(extension): file_path += extension
            
        if formato_salida == "Excel":
            exportar_a_excel(df_reporte, file_path)
            messagebox.showinfo("Éxito", f"Reporte guardado en:\n{file_path}")
        
        elif formato_salida == "PDF":
            titulo_pdf = tipo_reporte
            if tipo_reporte == "Optimización de Compras (IA)":
                titulo_pdf = "Reporte Inteligente de Reabastecimiento (EOQ)"
                # ✅ Le pasamos los filtros correctos al PDF
                filtros['categoria'] = categoria
                filtros['simulado_en'] = fecha_sql
                
            exportar_a_pdf(df_reporte, file_path, titulo_pdf, filtros) 
            messagebox.showinfo("Éxito", f"Reporte guardado en:\n{file_path}")

    except Exception as e:
        messagebox.showerror("Error Crítico", f"Error al generar reporte: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if root: root.destroy()
        
        
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
  
#-------------------------------------------------------------------------------------------------------------------
    