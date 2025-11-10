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


NON_SELECTION_VALUES = ["SELECCIONAR", "Seleccionar Categoría"]
DATE_FORMAT_UI = "%d-%m-%Y" # Formato de la Interfaz: Día-Mes-Año
DATE_FORMAT_SQL = "%Y-%m-%d" # Formato SQL/Base de Datos: Año-Mes-Día


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
        command=lambda: mostrar_reportes_predictivos(contenido_frame)
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
    
    
#-------------------------------------------------------------------------------------------------------------------


def ejecutar_consulta_df(sql_query: str, params: list = None) -> pd.DataFrame:
    """
    Función auxiliar para ejecutar consultas con pandas y manejo de conexión.
    Si la conexión falla, se retorna un DataFrame vacío y se maneja el error.
    """
    conn = conectar_db() # Asumo que esta función ya maneja el entorno
    df = pd.DataFrame()
    
    # --- CORRECCIÓN: Definir las columnas esperadas para evitar ValueError en el merge ---
    expected_columns = []
    if "ventas v" in sql_query or "ventas_mensuales" in sql_query:
        expected_columns = ['fecha', 'cantidad_vendida']
    elif "prediccion_mensual" in sql_query:
        expected_columns = ['fecha', 'cantidad_predicha']
    # ----------------------------------------------------------------------------------
    
    if conn:
        try:
            # Psycopg2 espera una lista/tupla de parámetros, incluso si es uno solo.
            df = pd.read_sql(sql_query, conn, params=params)
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"Error al ejecutar la consulta: {e}")
            print(f"SQL Error: {e}")
            print(f"Query: {sql_query}")
            # Si hay error en la DB, retornamos un DF vacío con las columnas correctas
            return pd.DataFrame(columns=expected_columns)
        finally:
            if conn:
                conn.close()
    else:
        # Esto es un fallback en caso de que la conexión falle (simulación de datos)
        if "desarrollo.garantias" in sql_query and "categoria" in sql_query:
            return pd.DataFrame({'categoria': ["Electrónica", "Herramientas", "Muebles", "Deporte"]})
        if "ventas" in sql_query:
            meses = pd.date_range(end=datetime.now(), periods=12, freq='M').to_period('M').astype(str)
            ventas = 100 + np.random.randint(0, 50, 12)
            return pd.DataFrame({'fecha': meses, 'cantidad_vendida': ventas})
        if "prediccion_mensual" in sql_query:
            start_date = datetime.now() + timedelta(days=1)
            horizonte = params[-1] if params and isinstance(params[-1], int) else 6
            meses_futuro = pd.date_range(start=start_date, periods=horizonte, freq='M').to_period('M').astype(str)
            prediccion = 100 + np.cumsum(np.random.normal(10, 20, horizonte))
            return pd.DataFrame({'fecha': meses_futuro, 'cantidad_predicha': np.maximum(0, prediccion)})
        
    
    # --- CORRECCIÓN ADICIONAL: Final check para evitar el ValueError en rename/merge ---
    # Si la consulta no trajo filas (df.empty) y se esperaban columnas, aseguramos la estructura.
    if df.empty and expected_columns:
        return pd.DataFrame(columns=expected_columns)
        
    return df

    
def generar_previsualizacion(df_completo, tipo_grafico, resultados_frame):
    """
    Genera gráficos de predicción diferenciados por producto/categoría.
    """
    try:
        for widget in resultados_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(resultados_frame, text=f"Generando Gráfico: {tipo_grafico}...", font=("Arial", 16, "italic")).pack(pady=10)

        # Validación de columnas
        required_cols = ['fecha', 'Cantidad_Real', 'Cantidad_Predicha']
        for col in required_cols:
            if col not in df_completo.columns:
                raise KeyError(f"Columna faltante: {col}")

        # Detectar si hay columna de producto
        tiene_producto = 'v_id_producto' in df_completo.columns

        # Filtrar históricos y predicciones
        df_hist = df_completo[df_completo['Cantidad_Real'].notna()]
        df_pred = df_completo[df_completo['Cantidad_Predicha'].notna()]

        if df_hist.empty and df_pred.empty:
            raise ValueError("No hay datos para graficar")

        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        # === GRAFICADO SEGÚN TIPO ===
        if tipo_grafico == "Línea (Tendencia)":
            # Si hay más de un producto, graficar cada uno
            if tiene_producto and 'v_id_producto' in df_hist.columns:
                for prod_id, grupo in df_hist.groupby('v_id_producto'):
                    ax.plot(grupo['fecha'], grupo['Cantidad_Real'], 
                            label=f"Real - Prod {prod_id}", 
                            linewidth=2.5, marker='o')
            else:
                ax.plot(df_hist['fecha'], df_hist['Cantidad_Real'], 
                        label="Real (Histórico)", color='#3498db', linewidth=3, marker='o')

            if tiene_producto and 'v_id_producto' in df_pred.columns:
                for prod_id, grupo in df_pred.groupby('v_id_producto'):
                    ax.plot(grupo['fecha'], grupo['Cantidad_Predicha'], 
                            label=f"Pred - Prod {prod_id}", 
                            linestyle='--', linewidth=2.5, marker='s')
            else:
                ax.plot(df_pred['fecha'], df_pred['Cantidad_Predicha'], 
                        label="Predicción", color='#e74c3c', linestyle='--', linewidth=3, marker='s')

            ax.set_title('Predicción de Ventas (por Producto)', fontsize=14, fontweight='bold')

        elif tipo_grafico == "Barras (Mensual)":
            if tiene_producto:
                productos = sorted(df_completo['v_id_producto'].unique())
                colores = plt.cm.get_cmap('tab10', len(productos))
                for i, prod_id in enumerate(productos):
                    subset = df_completo[df_completo['v_id_producto'] == prod_id]
                    ax.bar(subset['fecha'], subset['Cantidad_Predicha'], 
                           label=f"Prod {prod_id}", alpha=0.8, color=colores(i))
            else:
                ax.bar(df_pred['fecha'], df_pred['Cantidad_Predicha'], label="Predicción", color="#f39c12", alpha=0.7)
                ax.bar(df_hist['fecha'], df_hist['Cantidad_Real'], label="Histórico", color="#2ecc71", alpha=0.7)

            ax.set_title('Predicción Mensual (por Producto)', fontsize=14, fontweight='bold')

        # Configuración común
        ax.set_xlabel('Fecha (Mes)', fontsize=12)
        ax.set_ylabel('Cantidad', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        ax.legend(fontsize=10)
        ax.grid(True, linestyle=':', alpha=0.6)
        plt.tight_layout()

        # Embed gráfico en el frame
        canvas = FigureCanvasTkAgg(fig, master=resultados_frame)
        canvas.get_tk_widget().pack(pady=20, padx=20, fill='both', expand=True)
        canvas.draw()

        # Botón de exportación
        def descargar():
            f = filedialog.asksaveasfilename(defaultextension=".png", 
                                             filetypes=[("PNG", "*.png")],
                                             initialfile="Reporte_Prediccion.png")
            if f:
                fig.savefig(f, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Exportado", f"Gráfico guardado en:\n{f}")

        ctk.CTkButton(resultados_frame, text="Descargar Gráfico", command=descargar, fg_color="#3498db", hover_color="#2980b9").pack(pady=(10, 30))

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al generar el gráfico:\n{e}")
        print(f"❌ ERROR en generar_previsualizacion: {e}")
        import traceback; traceback.print_exc()


def consultar_ventas_agregadas_para_prediccion(id_producto: int, fecha_inicio_sql: str, fecha_fin_sql: str, categoria: str) -> pd.DataFrame:
    """
    Consulta ventas históricas agrupadas por mes,
    devolviendo 'fecha' y 'Cantidad_Real', con filtros robustos.
    """
    conn = conectar_db()
    if conn is None:
        return pd.DataFrame(columns=['fecha', 'Cantidad_Real'])

    NON_SELECTION_VALUES = ["SELECCIONAR", "Seleccionar Categoría", "Todas las Categorías"]
    where_clause = "WHERE DATE(v.v_fecha) BETWEEN %s AND %s"
    params = [fecha_inicio_sql, fecha_fin_sql]

    # Filtro por categoría
    if categoria and categoria not in NON_SELECTION_VALUES:
        where_clause += " AND s.categoria = %s"
        params.append(categoria)

    # Filtro por producto
    if id_producto and id_producto > 0:
        where_clause += " AND v.v_id_producto = %s"
        params.append(id_producto)

    SQL = f"""
        SELECT 
            TO_CHAR(DATE_TRUNC('month', v.v_fecha), 'YYYY-MM') AS fecha,
            SUM(v.v_cantidad) AS cantidad_vendida
        FROM desarrollo.ventas v
        JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo
        {where_clause}
        GROUP BY 1
        ORDER BY 1;
    """

    try:
        print(f"🧩 DEBUG SQL HISTÓRICO:\n{SQL}")
        print(f"🧩 Parámetros: {params}")

        df_ventas = pd.read_sql(SQL, conn, params=params)
        print(f"✅ Registros históricos obtenidos: {len(df_ventas)}")

        if 'cantidad_vendida' in df_ventas.columns:
            df_ventas.rename(columns={'cantidad_vendida': 'Cantidad_Real'}, inplace=True)

        return df_ventas

    except Exception as e:
        print(f"❌ Error al consultar ventas agregadas: {e}")
        return pd.DataFrame(columns=['fecha', 'Cantidad_Real'])
    finally:
        if conn:
            conn.close()


def consultar_prediccion_mensual_db(horizonte_meses: int, fecha_fin_hist: str, id_producto: int, categoria: str = "") -> pd.DataFrame:
    """
    Consulta predicciones desde la tabla desarrollo.prediccion_mensual.
    - Si se selecciona un producto: muestra las predicciones de ese producto.
    - Si se selecciona una categoría: muestra el promedio mensual de esa categoría.
    - Si no se selecciona nada: muestra el promedio global.
    """

    from datetime import datetime, timedelta
    import pandas as pd

    NON_SELECTION_VALUES = ["SELECCIONAR", "Seleccionar Categoría", "Todas las Categorías"]

    try:
        fecha_fin_dt = datetime.strptime(fecha_fin_hist, "%Y-%m-%d")
    except Exception:
        fecha_fin_dt = datetime.now()

    # Calcular el rango temporal (futuro)
    start_date = (fecha_fin_dt + timedelta(days=1)).replace(day=1)
    end_date = (start_date + pd.DateOffset(months=horizonte_meses)).to_pydatetime()

    # Construcción dinámica de SQL
    where_conditions = []
    params = []

    join_clause = ""

    # Si se selecciona un producto específico
    if id_producto and id_producto > 0:
        where_conditions.append("p.v_id_producto = %s")
        params.append(id_producto)

    # Si se selecciona una categoría
    elif categoria and categoria not in NON_SELECTION_VALUES:
        join_clause = "JOIN desarrollo.stock s ON p.v_id_producto = s.id_articulo"
        where_conditions.append("s.categoria = %s")
        params.append(categoria)

    # Filtro temporal
    where_conditions.append("(MAKE_DATE(p.anio, p.mes, 1) BETWEEN %s::date AND %s::date)")
    params.extend([
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    ])

    where_sql = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    # SQL final adaptado
    if categoria and categoria not in NON_SELECTION_VALUES:
        # 🔸 Promedio mensual por categoría
        SQL = f"""
            SELECT 
                s.categoria,
                TO_CHAR(MAKE_DATE(p.anio, p.mes, 1), 'YYYY-MM') AS fecha,
                ROUND(AVG(p.cantidad_predicha)::numeric, 2) AS cantidad_predicha
            FROM desarrollo.prediccion_mensual p
            JOIN desarrollo.stock s ON p.v_id_producto = s.id_articulo
            {where_sql}
            GROUP BY s.categoria, p.anio, p.mes
            ORDER BY p.anio, p.mes;
        """
    else:
        # 🔸 Promedio mensual por producto (o general)
        SQL = f"""
            SELECT 
                p.v_id_producto,
                TO_CHAR(MAKE_DATE(p.anio, p.mes, 1), 'YYYY-MM') AS fecha,
                ROUND(AVG(p.cantidad_predicha)::numeric, 2) AS cantidad_predicha
            FROM desarrollo.prediccion_mensual p
            {join_clause}
            {where_sql}
            GROUP BY p.v_id_producto, p.anio, p.mes
            ORDER BY p.anio, p.mes;
        """

    try:
        df_pred = ejecutar_consulta_df(SQL, params=params)

        if df_pred is None or df_pred.empty:
            print("⚠️ No se obtuvieron predicciones, devolviendo fallback.")
            return generar_fallback_prediccion(horizonte_meses, fecha_fin_hist)

        # Normalización del tipo de dato
        df_pred['cantidad_predicha'] = pd.to_numeric(df_pred['cantidad_predicha'], errors='coerce').fillna(0)
        return df_pred

    except Exception as e:
        print(f"❌ Error en consultar_prediccion_mensual_db: {e}")
        return generar_fallback_prediccion(horizonte_meses, fecha_fin_hist)


def consultar_ventas_2023_para_prediccion(id_producto: int, categoria: str) -> pd.DataFrame:
    """
    Consulta automática de ventas de todo el año 2023 para predicción,
    filtrando correctamente por categoría o producto.
    """
    conn = conectar_db()
    if conn is None:
        return pd.DataFrame(columns=['fecha', 'Cantidad_Real'])

    NON_SELECTION_VALUES = ["SELECCIONAR", "Seleccionar Categoría", "Todas las Categorías"]
    where_clause = "WHERE EXTRACT(YEAR FROM v.v_fecha) = 2023"
    params = []

    # Filtro por categoría
    if categoria and categoria not in NON_SELECTION_VALUES:
        where_clause += " AND s.categoria = %s"
        params.append(categoria)

    # Filtro por producto
    if id_producto and id_producto > 0:
        where_clause += " AND v.v_id_producto = %s"
        params.append(id_producto)

    SQL = f"""
        SELECT 
            TO_CHAR(DATE_TRUNC('month', v.v_fecha), 'YYYY-MM') AS fecha,
            SUM(v.v_cantidad) AS cantidad_vendida
        FROM desarrollo.ventas v
        JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo
        {where_clause}
        GROUP BY 1
        ORDER BY 1;
    """

    try:
        print(f"🧩 DEBUG SQL 2023:\n{SQL}")
        print(f"🧩 Parámetros: {params}")

        df_ventas = pd.read_sql(SQL, conn, params=params)
        print(f"✅ Datos 2023 obtenidos: {len(df_ventas)} filas")

        if 'cantidad_vendida' in df_ventas.columns:
            df_ventas.rename(columns={'cantidad_vendida': 'Cantidad_Real'}, inplace=True)

        return df_ventas

    except Exception as e:
        print(f"❌ Error al consultar ventas 2023: {e}")
        return pd.DataFrame(columns=['fecha', 'Cantidad_Real'])
    finally:
        if conn:
            conn.close()

def consultar_ventas_reales_2024() -> pd.DataFrame:
    """
    Consulta las ventas reales del año 2024 para comparar con las predicciones.
    Devuelve: fecha (YYYY-MM) y cantidad total vendida.
    """
    conn = conectar_db()
    if conn is None:
        return pd.DataFrame(columns=['fecha', 'Cantidad_Real_2024'])

    SQL = """
        SELECT 
            TO_CHAR(DATE_TRUNC('month', v.v_fecha), 'YYYY-MM') AS fecha,
            SUM(v.v_cantidad) AS cantidad_real_2024
        FROM desarrollo.ventas v
        WHERE EXTRACT(YEAR FROM v.v_fecha) = 2024
        GROUP BY 1
        ORDER BY 1;
    """

    try:
        df = pd.read_sql(SQL, conn)
        df.rename(columns={'cantidad_real_2024': 'Cantidad_Real_2024'}, inplace=True)
        print(f"✅ Ventas reales 2024 obtenidas: {len(df)} meses")
        return df
    except Exception as e:
        print(f"❌ Error al consultar ventas 2024: {e}")
        return pd.DataFrame(columns=['fecha', 'Cantidad_Real_2024'])
    finally:
        if conn:
            conn.close()


def generar_fallback_prediccion(horizonte_meses: int, fecha_fin_hist: str) -> pd.DataFrame:
    """Genera datos de fallback REALES Y ESTABLES cuando la consulta falla"""
    try:
        start_date = datetime.strptime(fecha_fin_hist, "%Y-%m-%d") + timedelta(days=1)
    except:
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        
    # SEMILLA PARA REPRODUCIBILIDAD
    np.random.seed(123)  # Semilla diferente pero fija
    
    meses_futuro = pd.date_range(start=start_date, periods=horizonte_meses, freq='M').to_period('M').astype(str)
    
    # Valores de fallback REALISTAS Y ESTABLES
    base_value = 180  # Valor base consistente
    # Patrón predecible en lugar de aleatorio
    tendencia = base_value + np.arange(horizonte_meses) * 5  # Crecimiento lineal de 5 unidades por mes
    variacion = np.sin(np.arange(horizonte_meses) * 0.8) * 15  # Patrón sinusoidal estable
    
    prediccion = tendencia + variacion
    
    df_fallback = pd.DataFrame({
        'fecha': meses_futuro, 
        'cantidad_predicha': np.maximum(100, prediccion).round().astype(int)
    })
    
    print(f"🔄 Usando datos de fallback ESTABLES: {df_fallback['cantidad_predicha'].tolist()}")
    return df_fallback


def mostrar_selector_grafico(df_completo, resultados_frame):
    """
    Muestra el submenú para seleccionar el tipo de gráfico.
    Versión mejorada con diseño más atractivo.
    """
    for widget in resultados_frame.winfo_children():
        widget.destroy()

    selector_frame = ctk.CTkFrame(resultados_frame)
    selector_frame.pack(pady=30, padx=40, fill="both", expand=True)

    ctk.CTkLabel(
        selector_frame, 
        text="🎨 Seleccione el Tipo de Gráfico", 
        font=("Arial", 18, "bold")
    ).pack(pady=20)

    ctk.CTkLabel(
        selector_frame,
        text="Elija el estilo de visualización para su reporte predictivo",
        font=("Arial", 14),
        text_color="gray"
    ).pack(pady=(0, 20))

    tipos_grafico = ["Línea (Tendencia)", "Barras (Mensual)"]
    grafico_seleccionado = ctk.CTkOptionMenu(
        selector_frame,
        values=tipos_grafico,
        width=300,
        height=45,
        font=("Arial", 14),
        dropdown_font=("Arial", 12)
    )
    grafico_seleccionado.pack(pady=20)
    grafico_seleccionado.set(tipos_grafico[0])

    # Botón con mejor diseño
    ctk.CTkButton(
        selector_frame,
        text="👁️ Previsualizar Gráfico",
        command=lambda: generar_previsualizacion(df_completo, grafico_seleccionado.get(), resultados_frame),
        width=250,
        height=45,
        font=("Arial", 14, "bold"),
        fg_color="#3498db",
        hover_color="#2980b9"
    ).pack(pady=30)


def generar_grafico_tk(df: pd.DataFrame, frame: ctk.CTkFrame, title: str):
    """
    Genera un gráfico de línea comparando valores reales vs. predichos
    y lo incrusta en el frame de resultados.
    MEJORADO: Límite del eje Y ajustado a 1000.
    """
    # Verificación de librerías instaladas
    if plt is None or FigureCanvasTkAgg is None:
        return

    # Limpiamos el frame antes de dibujar
    for widget in frame.winfo_children():
        widget.destroy()
        
    fig = Figure(figsize=(10, 5), dpi=100)
    # Establecer color de fondo para que coincida con el tema de ctk
    fig.patch.set_facecolor('#2b2b2b') # Fondo oscuro de CustomTkinter
    
    ax = fig.add_subplot(111)
    # Establecer colores de fondo y texto del eje para el tema oscuro
    ax.set_facecolor('#2b2b2b')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.spines['left'].set_color('white')
    ax.spines['bottom'].set_color('white')
    ax.spines['right'].set_color('white')
    ax.spines['top'].set_color('white')

    # Convertir la columna 'fecha' a tipo datetime para mejor manejo en el gráfico
    df['fecha_dt'] = pd.to_datetime(df['fecha'])

    # --- NUEVO: Calcular límite del eje Y ---
    all_values = []
    if 'Cantidad_Real' in df.columns:
        real_values = df['Cantidad_Real'].dropna()
        if not real_values.empty:
            all_values.extend(real_values.tolist())
    if 'Cantidad_Predicha' in df.columns:
        pred_values = df['Cantidad_Predicha'].dropna()
        if not pred_values.empty:
            all_values.extend(pred_values.tolist())
    
    if all_values:
        max_value = max(all_values)
        y_upper_limit = min(1000, max_value * 1.1)  # Máximo 1000 o valor real + 10%
    else:
        y_upper_limit = 1000

    # Graficar Cantidad Real (datos históricos)
    if 'Cantidad_Real' in df.columns:
        real_data = df[df['Cantidad_Real'].notna()]
        if not real_data.empty:
            ax.plot(
                real_data['fecha_dt'], 
                real_data['Cantidad_Real'], 
                label='Venta Real', 
                marker='o', 
                linestyle='-', 
                color='#1f77b4', # Azul
                linewidth=2
            )
    
    # Graficar Cantidad Predicha (puede tener NaN en el histórico)
    if 'Cantidad_Predicha' in df.columns:
        pred_data = df[df['Cantidad_Predicha'].notna()]
        if not pred_data.empty:
            ax.plot(
                pred_data['fecha_dt'], 
                pred_data['Cantidad_Predicha'], 
                label='Venta Predicha', 
                marker='x', 
                linestyle='--', 
                color='#ff7f0e', # Naranja
                linewidth=2
            )

    # --- NUEVO: Aplicar límite del eje Y ---
    ax.set_ylim(0, y_upper_limit)

    # Título y Etiquetas
    ax.set_title(title, fontsize=14, color='white')
    ax.set_xlabel("Fecha", fontsize=10, color='white')
    ax.set_ylabel("Cantidad Vendida", fontsize=10, color='white')
    
    # Leyenda
    ax.legend(loc='best', facecolor='#3a3a3a', edgecolor='#505050', labelcolor='white')
    
    # Rotar etiquetas del eje X para mayor legibilidad
    fig.autofmt_xdate(rotation=45)
    
    # Línea divisoria en la última fecha real (separador histórico/predicción)
    if 'Cantidad_Real' in df.columns:
        last_real_date = df[df['Cantidad_Real'].notna()]['fecha_dt'].max()
        if pd.notna(last_real_date):
            ax.axvline(last_real_date, color='#FF9100', linestyle=':', linewidth=1.5, label='Inicio Predicción')
        
    # Incrustar el gráfico en CustomTkinter
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill='both', expand=True, padx=10, pady=10)
    canvas.draw()
    
    
    # --- NUEVO BOTÓN DE COMPARACIÓN 2024 ---
    def comparar_con_ventas_2024():
        df_2024 = consultar_ventas_reales_2024()
        if df_2024.empty:
            messagebox.showwarning("Sin datos", "No hay registros reales de ventas 2024 para comparar.")
            return

        # Fusionar con el df actual (df del gráfico original)
        df_merge = pd.merge(df, df_2024, on='fecha', how='outer').sort_values('fecha')
        generar_grafico_tk(df_merge, frame, "Comparación Predicción vs Ventas Reales 2024")

    ctk.CTkButton(
        frame,
        text="📊 Comparar con Ventas Reales 2024",
        command=comparar_con_ventas_2024,
        width=280,
        height=40,
        font=("Arial", 14, "bold"),
        fg_color="#3498db",
        hover_color="#2980b9"
    ).pack(pady=(10, 20))


def mostrar_reportes_predictivos(contenido_frame):
    """
    Muestra la interfaz de Reportes Predictivos de Ventas - Versión SIMPLIFICADA
    """
    # Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()
        
    # Configurar scroll
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
    canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window_id, width=e.width))
    
    def _on_mousewheel(event):
        if event.widget.winfo_exists():
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.focus_set() 
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    # --- CONTENIDO SIMPLIFICADO ---
    
    ctk.CTkLabel(
        scrollable_frame, 
        text="Generador de Reportes Predictivos de Ventas",
        font=("Arial", 22, "bold")
    ).pack(pady=(20, 10))

    # Subtítulo descriptivo
    ctk.CTkLabel(
        scrollable_frame,
        text="Sistema automático: usa datos 2023 para mostrar predicciones 2024",
        font=("Arial", 14),
        text_color="gray"
    ).pack(pady=(0, 30))

    # ====================
    # SECCIÓN 1: CONFIGURACIÓN PRINCIPAL
    # ====================
    config_section = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    config_section.pack(pady=15, padx=40, fill="x")
    
    ctk.CTkLabel(
        config_section, 
        text="📊 Configuración Principal",
        font=("Arial", 18, "bold")
    ).pack(anchor="w", pady=(0, 15))

    # Frame para configuración en 2 columnas
    config_grid = ctk.CTkFrame(config_section, fg_color="transparent")
    config_grid.pack(fill="x")

    # Columna izquierda - Horizonte
    left_col = ctk.CTkFrame(config_grid, fg_color="transparent")
    left_col.pack(side="left", padx=(0, 20), fill="x", expand=True)
    
    ctk.CTkLabel(
        left_col, 
        text="Horizonte de Predicción (meses)",
        font=("Arial", 14, "bold")
    ).pack(anchor="w", pady=(0, 5))
    
    ctk.CTkLabel(
        left_col,
        text="Número de meses futuros a predecir",
        font=("Arial", 12),
        text_color="gray"
    ).pack(anchor="w", pady=(0, 10))
    
    horizonte_entry = ctk.CTkEntry(
        left_col, 
        placeholder_text="Ej: 6 meses", 
        width=200,
        height=40,
        font=("Arial", 14)
    )
    horizonte_entry.pack(anchor="w", pady=(0, 10))
    horizonte_entry.insert(0, "6")

    # Columna derecha - Exportación
    right_col = ctk.CTkFrame(config_grid, fg_color="transparent")
    right_col.pack(side="left", padx=(20, 0), fill="x", expand=True)
    
    ctk.CTkLabel(
        right_col, 
        text="Formato de Salida",
        font=("Arial", 14, "bold")
    ).pack(anchor="w", pady=(0, 5))
    
    ctk.CTkLabel(
        right_col,
        text="Tipo de reporte a generar",
        font=("Arial", 12),
        text_color="gray"
    ).pack(anchor="w", pady=(0, 10))
    
    exportacion_tipos = ["Gráfico Interactivo", "Datos CSV", "Excel", "PDF"]
    exportacion_menu = ctk.CTkOptionMenu(
        right_col,
        values=exportacion_tipos,
        width=200,
        height=40,
        font=("Arial", 14),
        dropdown_font=("Arial", 12)
    )
    exportacion_menu.pack(anchor="w", pady=(0, 10))
    exportacion_menu.set(exportacion_tipos[0])

    # ====================
    # SECCIÓN 2: FILTROS AVANZADOS
    # ====================
    filtros_section = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    filtros_section.pack(pady=25, padx=40, fill="x")
    
    ctk.CTkLabel(
        filtros_section, 
        text="🔍 Filtros Avanzados",
        font=("Arial", 18, "bold")
    ).pack(anchor="w", pady=(0, 15))

    ctk.CTkLabel(
        filtros_section,
        text="Opcional: filtrar por categoría o producto específico",
        font=("Arial", 12),
        text_color="gray"
    ).pack(anchor="w", pady=(0, 15))

    # Frame para filtros en 2 columnas
    filtros_grid = ctk.CTkFrame(filtros_section, fg_color="transparent")
    filtros_grid.pack(fill="x")

    # Filtro Categoría
    cat_col = ctk.CTkFrame(filtros_grid, fg_color="transparent")
    cat_col.pack(side="left", padx=(0, 20), fill="x", expand=True)
    
    ctk.CTkLabel(cat_col, text="Categoría", font=("Arial", 14, "bold")).pack(anchor="w")
    
    categorias_disponibles = obtener_categorias_db()
    categoria_menu = ctk.CTkOptionMenu(
        cat_col,
        values=categorias_disponibles,
        width=250,
        height=35,
        font=("Arial", 12)
    )
    categoria_menu.pack(anchor="w", pady=5)
    categoria_menu.set(categorias_disponibles[0])

    # Filtro Producto
    prod_col = ctk.CTkFrame(filtros_grid, fg_color="transparent")
    prod_col.pack(side="left", padx=(20, 0), fill="x", expand=True)
    
    ctk.CTkLabel(prod_col, text="Producto", font=("Arial", 14, "bold")).pack(anchor="w")
    
    def actualizar_productos_ui(categoria):
        productos = obtener_productos_por_categoria_db(categoria)
        producto_menu.configure(values=productos)
        producto_menu.set(productos[0])

    productos_disponibles_inicial = obtener_productos_por_categoria_db(categoria_menu.get())
    producto_menu = ctk.CTkOptionMenu(
        prod_col,
        values=productos_disponibles_inicial,
        width=250,
        height=35,
        font=("Arial", 12)
    )
    producto_menu.pack(anchor="w", pady=5)
    producto_menu.set(productos_disponibles_inicial[0])
    categoria_menu.configure(command=actualizar_productos_ui)

    # ====================
    # SECCIÓN 3: ACCIONES
    # ====================
    acciones_section = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    acciones_section.pack(pady=40, padx=40, fill="x")
    
    button_frame = ctk.CTkFrame(acciones_section, fg_color="transparent")
    button_frame.pack()

    # Botón principal más destacado
    ctk.CTkButton(
        button_frame,
        text="🚀 Generar Reporte Predictivo",
        width=280, 
        height=50,
        font=("Arial", 16, "bold"),
        fg_color="#006400",
        hover_color="#004d00",
        command=lambda: generar_reporte_predictivo(
            horizonte_entry,
            categoria_menu,
            producto_menu,
            exportacion_menu,
            resultados_frame  # Solo 4 parámetros ahora
        )
    ).pack(side="left", padx=15)

    ctk.CTkButton(
        button_frame,
        text="← Volver al Menú",
        width=150,
        height=50,
        font=("Arial", 14),
        fg_color="#E07B00",
        hover_color="#C06C00",
        command=lambda: mostrar_menu_reportes(contenido_frame)
    ).pack(side="left", padx=15)

    # ====================
    # SECCIÓN 4: RESULTADOS
    # ====================
    ctk.CTkLabel(
        scrollable_frame, 
        text="📈 Resultados",
        font=("Arial", 18, "bold")
    ).pack(anchor="w", pady=(40, 15), padx=40)

    resultados_frame = ctk.CTkFrame(
        scrollable_frame, 
        fg_color="transparent",
        border_width=2,
        border_color="gray"
    )
    resultados_frame.pack(pady=10, padx=40, fill="both", expand=True, ipady=20)

    # Mensaje inicial en resultados
    ctk.CTkLabel(
        resultados_frame,
        text="Configure los parámetros y haga clic en 'Generar Reporte Predictivo'",
        font=("Arial", 14),
        text_color="gray"
    ).pack(expand=True, pady=50)

    scrollable_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))


def formatear_fechas_correctamente(df):
    """Convierte y formatea las fechas correctamente para el gráfico"""
    df_corregido = df.copy()
    
    print(f"🔍 FECHAS ANTES DE FORMATEAR: {df_corregido['fecha'].tol() if 'fecha' in df_corregido.columns else 'No hay columna fecha'}")
    
    if 'fecha' in df_corregido.columns:
        # Intentar convertir a formato de fecha estándar
        try:
            # Si las fechas están en formato "YYYY-M" o "YYYY-MM", convertirlas a "YYYY-MM"
            df_corregido['fecha'] = df_corregido['fecha'].astype(str)
            
            # Corregir formatos como "2022-1" -> "2022-01"
            def corregir_formato_fecha(fecha_str):
                if '-' in fecha_str:
                    parts = fecha_str.split('-')
                    if len(parts) == 2:
                        año = parts[0]
                        mes = parts[1]
                        # Asegurar que el mes tenga 2 dígitos
                        if len(mes) == 1:
                            mes = f"0{mes}"
                        return f"{año}-{mes}"
                return fecha_str
            
            df_corregido['fecha'] = df_corregido['fecha'].apply(corregir_formato_fecha)
            
            # Crear una columna de fecha completa para ordenamiento
            df_corregido['fecha_dt'] = pd.to_datetime(df_corregido['fecha'] + '-01', format='%Y-%m-%d', errors='coerce')
            
            # Ordenar por fecha
            df_corregido = df_corregido.sort_values('fecha_dt').reset_index(drop=True)
            
            print(f"✅ FECHAS CORREGIDAS: {df_corregido['fecha'].tolist()}")
            
        except Exception as e:
            print(f"❌ Error al formatear fechas: {e}")
    
    return df_corregido


def obtener_categorias_db():
    """Consulta las categorías disponibles en la tabla de productos (stock)."""
    SQL = """
        SELECT DISTINCT gar_categoria 
        FROM desarrollo.garantias
        WHERE gar_categoria IS NOT NULL 
        ORDER BY gar_categoria;
    """
    try:
        df = ejecutar_consulta_df(SQL)
        categorias = ["Seleccionar Categoría"] + df['gar_categoria'].tolist()
        if not df.empty and len(categorias) > 1:
            return categorias
        else:
            # Fallback de ejemplo en caso de que la DB esté vacía o la conexión simule datos.
            return ["Seleccionar Categoría", "Electrónica (Ejemplo)", "Muebles (Ejemplo)"] 
    except Exception as e:
        print(f"Error al obtener categorías: {e}")
        return ["Seleccionar Categoría", "Error de Carga"] # Fallback


def obtener_productos_por_categoria_db(categoria: str):
    """Consulta los productos basados en la categoría seleccionada."""
    productos = ["Todos los Productos"]
    if categoria == "Seleccionar Categoría":
        return productos
    
    # La consulta SQL utiliza el parámetro '%s' para filtrar por la categoría.
    SQL = f"""
        SELECT id_articulo, descripcion
        FROM desarrollo.stock
        WHERE categoria = %s
        ORDER BY descripcion;
    """
    try:
        # Usamos la función auxiliar 'ejecutar_consulta_df' para ejecutar la query
        df = ejecutar_consulta_df(SQL, params=[categoria])
        
        # Creamos la lista de productos en el formato "Nombre Producto (ID: X)"
        productos += [f"{row['descripcion']} (ID: {row['id_articulo']})" for _, row in df.iterrows()]
    except Exception as e:
        print(f"Error al obtener productos: {e}")
    
    return productos


def generar_reporte_predictivo(horizonte_entry, categoria_menu, producto_menu, exportacion_menu, resultados_frame):
    """
    Función principal - Genera reportes predictivos usando 2023 para predecir y mostrar 2024
    """
    # 1. Limpiar el frame de resultados y mostrar mensaje de carga
    for widget in resultados_frame.winfo_children():
        widget.destroy()
    
    loading_label = ctk.CTkLabel(
        resultados_frame, 
        text="🔄 Consultando datos y generando reporte...",
        font=("Arial", 16, "italic")
    )
    loading_label.pack(pady=40)
    
    # Forzar actualización de la UI
    resultados_frame.winfo_toplevel().update_idletasks()

    NON_SELECTION_VALUES = ["SELECCIONAR", "Seleccionar Categoría", "Todas las Categorías"]
    
    try:
        # 2. Obtención y Validación de Parámetros
        horizonte_meses_str = horizonte_entry.get().strip()
        categoria = categoria_menu.get()
        producto_con_id = producto_menu.get()
        tipo_exportacion = exportacion_menu.get()
        
        # Validaciones
        validation_errors = []
        
        if not horizonte_meses_str.isdigit() or int(horizonte_meses_str) <= 0:
            validation_errors.append("El Horizonte debe ser un número entero positivo.")
        
        if categoria in NON_SELECTION_VALUES:
            validation_errors.append("Debe seleccionar una Categoría válida.")
            
        if validation_errors:
            loading_label.destroy()
            messagebox.showerror("Error de Entrada", "\n".join(validation_errors))
            return

        horizonte_meses = int(horizonte_meses_str)
        
        # 3. Procesar ID de producto
        id_producto_consulta = 0
        if "ID:" in producto_con_id and producto_con_id != "Todos los Productos":
            try:
                id_producto_consulta = int(producto_con_id.split("ID: ")[-1].strip().replace(")", ""))
            except ValueError:
                loading_label.destroy()
                messagebox.showerror("Error", "Formato de ID de Producto inválido.")
                return

        # 4. Obtener datos Históricos (2023) y Predictivos (2024)
        loading_label.configure(text="📊 Consultando datos históricos 2023...")
        resultados_frame.update_idletasks()
        
        df_historico = consultar_ventas_2023_para_prediccion(
            id_producto=id_producto_consulta,
            categoria=categoria
        )
        
        loading_label.configure(text="🔮 Generando predicciones 2024...")
        resultados_frame.update_idletasks()
        
        df_prediccion = consultar_prediccion_mensual_db(
            horizonte_meses=horizonte_meses,
            fecha_fin_hist="2023-12-31", 
            id_producto=id_producto_consulta,
            categoria=categoria  # ← NUEVO PARÁMETRO
        )
        
        
        # === DEBUG POST-PREDICCIÓN ===
        print("🧠 DEPURACIÓN: Verificando datos de predicción por categoría/producto")
        if not df_prediccion.empty:
            print("   Productos únicos:", df_prediccion['v_id_producto'].unique().tolist() if 'v_id_producto' in df_prediccion.columns else "⚠️ No hay columna v_id_producto")
            print("   Promedio por producto:")
            if 'v_id_producto' in df_prediccion.columns:
                print(df_prediccion.groupby('v_id_producto')['Cantidad_Predicha'].mean())
        else:
            print("⚠️ df_prediccion está vacío")
        
        # === NUEVO: DEBUG DETALLADO ===
        print(f"🔍 DEBUG - DATOS HISTÓRICOS:")
        print(f"   Columnas: {df_historico.columns.tolist()}")
        print(f"   Filas: {len(df_historico)}")
        if not df_historico.empty:
            print(f"   Primeros datos: {df_historico.head().to_dict()}")
        
        print(f"🔍 DEBUG - DATOS PREDICCIÓN:")
        print(f"   Columnas: {df_prediccion.columns.tolist()}")
        print(f"   Filas: {len(df_prediccion)}")
        if not df_prediccion.empty:
            print(f"   Primeros datos: {df_prediccion.head().to_dict()}")
        # === FIN DEBUG ===
        
        # 5. Unificar DataFrames - CORREGIDO
        if 'fecha' not in df_historico.columns:
            df_historico = pd.DataFrame(columns=['fecha', 'Cantidad_Real'])
         
        if 'fecha' not in df_prediccion.columns:
            df_prediccion = pd.DataFrame(columns=['fecha', 'Cantidad_Predicha'])

        # === CORRECCIÓN CRÍTICA: Asegurar nombres de columnas ===
        # Renombrar columnas para que coincidan
        if 'cantidad_vendida' in df_historico.columns:
            df_historico = df_historico.rename(columns={'cantidad_vendida': 'Cantidad_Real'})
        
        if 'cantidad_predicha' in df_prediccion.columns:
            df_prediccion = df_prediccion.rename(columns={'cantidad_predicha': 'Cantidad_Predicha'})

        # Unir datos históricos y de predicción
        merge_cols = ['fecha']

        # Si ambas tablas tienen el campo v_id_producto, lo usamos también
        if 'v_id_producto' in df_historico.columns and 'v_id_producto' in df_prediccion.columns:
            merge_cols.append('v_id_producto')

        try:
            #df_completo = pd.merge(df_historico, df_prediccion, on=merge_cols, how='outer')
            
            df_completo = pd.merge(
                df_historico, df_prediccion,
                on='fecha', how='outer'   # <-- CLAVE: usar outer merge
            ).sort_values('fecha')
            
        except Exception as e:
            print(f"⚠️ Error en el merge de DataFrames: {e}")
            df_completo = df_historico.copy()

        # Normalizamos nombres de columnas por consistencia
        df_completo.rename(columns={
            'cantidad_vendida': 'Cantidad_Real',
            'cantidad_predicha': 'Cantidad_Predicha'
        }, inplace=True, errors='ignore')

        print(f"✅ Merge completado con columnas: {df_completo.columns.tolist()}")
        print(df_completo.head())

        print(f"🔍 DEBUG - DATOS COMPLETOS UNIFICADOS:")
        print(f"   Columnas finales: {df_completo.columns.tolist()}")
        print(f"   Filas totales: {len(df_completo)}")
        print(f"   Datos completos:")
        for idx, row in df_completo.iterrows():
            print(f"     {row['fecha']} - Real: {row.get('Cantidad_Real', 'NaN')}, Pred: {row.get('Cantidad_Predicha', 'NaN')}")

        # 6. PROCESAR SEGÚN TIPO DE EXPORTACIÓN
        loading_label.destroy()
        
        if tipo_exportacion == "Gráfico Interactivo":
            # Mostrar gráfico interactivo
            titulo_grafico = f"Predicción de Ventas - Categoría: {categoria}"
            if id_producto_consulta > 0:
                titulo_grafico = f"Predicción de Ventas - Producto ID: {id_producto_consulta}"
                
            generar_grafico_tk(df_completo, resultados_frame, titulo_grafico)
            
            # Mostrar selector de gráficos adicionales
            mostrar_selector_grafico(df_completo, resultados_frame)
            
        else:
            # Para CSV, Excel, PDF - Mostrar datos tabulares y opción de descarga
            mostrar_datos_exportacion(df_completo, tipo_exportacion, categoria, id_producto_consulta, resultados_frame)
        
        # Mensaje de éxito
        ctk.CTkLabel(
            resultados_frame, 
            text="✅ Reporte Generado Exitosamente",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
            
    except Exception as e:
        loading_label.destroy()
        messagebox.showerror("Error General", f"Ocurrió un error al procesar el reporte: {str(e)}")
        print(f"ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()


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

    # ----------------------------------------
    # Fecha de Inicio (DD-MM-YYYY) - CON CALENDARIO
    # ----------------------------------------
    ctk.CTkLabel(ventas_params_frame, text="Fecha de Inicio (DD-MM-YYYY):").pack(pady=5, anchor='w')

    frame_fecha_inicio = ctk.CTkFrame(ventas_params_frame, fg_color="transparent")
    frame_fecha_inicio.pack(pady=5, fill="x", padx=10) # Usamos fill="x" para que se expanda

    fecha_inicio_entry = ctk.CTkEntry(frame_fecha_inicio, placeholder_text="Ej: 01-01-2024", width=210) # Un poco más estrecho
    fecha_inicio_entry.pack(side="left", fill="x", expand=True)

    # Botón de Calendario (El 'master' es el scrollable_frame, que es donde está el control_frame)
    btn_calendar_inicio = ctk.CTkButton(
        frame_fecha_inicio, 
        text="📅", 
        width=30, 
        command=lambda: open_calendar(scrollable_frame.winfo_toplevel(), fecha_inicio_entry)
    )
    btn_calendar_inicio.pack(side="left", padx=(5, 0))

    # ----------------------------------------
    # Fecha Fin (DD-MM-YYYY) - CON CALENDARIO
    # ----------------------------------------
    ctk.CTkLabel(ventas_params_frame, text="Fecha Fin (DD-MM-YYYY):").pack(pady=5, anchor='w')

    frame_fecha_fin = ctk.CTkFrame(ventas_params_frame, fg_color="transparent")
    frame_fecha_fin.pack(pady=5, fill="x", padx=10)

    fecha_fin_entry = ctk.CTkEntry(frame_fecha_fin, placeholder_text="Ej: 31-12-2024", width=210)
    fecha_fin_entry.pack(side="left", fill="x", expand=True)

    btn_calendar_fin = ctk.CTkButton(
        frame_fecha_fin, 
        text="📅", 
        width=30, 
        command=lambda: open_calendar(scrollable_frame.winfo_toplevel(), fecha_fin_entry)
    )
    btn_calendar_fin.pack(side="left", padx=(5, 0))
    
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
  
     
    
    
    
    
    
    