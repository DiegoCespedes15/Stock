# Archivo: src/reportes/report_ui.py

from datetime import datetime, timedelta
from tkinter import messagebox, filedialog, Tk 
import tkinter as tk # Necesario para los elementos internos de Matplotlib
import customtkinter as ctk
from matplotlib import ticker
import numpy as np
import pandas as pd
from modulos.exportar_excel import exportar_a_excel
from bd import conectar_db
from modulos.exportar_pdf import exportar_a_pdf 
from tkcalendar import Calendar, DateEntry
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
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
        # ✅ CAMBIO: Ahora llama a la función real
        command=lambda: mostrar_reportes_predictivos(contenido_frame)
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
# AQUI COMIENZA EL CODIGO DE PREDICCION INTEGRADO
#-------------------------------------------------------------------------------------------------------------------

def obtener_categorias_prediccion():
    """Obtiene categorías únicas desde la tabla stock para el combo."""
    conn = conectar_db()
    if conn is None: return []
    try:
        sql = "SELECT DISTINCT TRIM(UPPER(categoria)) as categoria FROM desarrollo.stock ORDER BY 1;"
        df = pd.read_sql(sql, conn)
        return df["categoria"].tolist()
    except Exception as e:
        print(f"❌ Error categorías: {e}")
        return []
    finally:
        if conn: conn.close()

def consultar_datos_mensuales_predictivos(categoria: str, tabla: str, anio: int) -> pd.DataFrame:
    """
    Consulta datos para un año específico (Ventas reales o Predicción).
    """
    conn = conectar_db()
    
    # --- MOCK DATA (Fallback si no hay conexión) ---
    if conn is None: 
        np.random.seed(anio) 
        fechas = pd.date_range(start=f"{anio}-01-01", periods=12, freq='MS')
        base = 100 if anio == 2023 else 110 
        ruido = np.random.randint(-20, 20, size=12)
        cantidades = base + ruido
        return pd.DataFrame({"fecha": fechas, "cantidad": cantidades})
    # -----------------------------------------------

    if tabla == 'desarrollo.ventas':
        # Ventas reales (históricas o del 2024 actual)
        sql = """
            SELECT DATE_TRUNC('month', v.v_fecha)::date AS fecha, SUM(v.v_cantidad) AS cantidad
            FROM desarrollo.ventas v
            JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo
            WHERE TRIM(UPPER(s.categoria)) = %s AND EXTRACT(YEAR FROM v.v_fecha) = %s
            GROUP BY 1 ORDER BY 1;
        """
        params = [categoria.strip().upper(), anio]
    else:
        # Predicciones (Tabla prediccion_mensual)
        sql = """
            SELECT MAKE_DATE(anio, mes, 1) AS fecha, SUM(cantidad_predicha) AS cantidad
            FROM desarrollo.prediccion_mensual
            WHERE TRIM(UPPER(categoria)) = %s
            AND anio = %s
            GROUP BY 1 ORDER BY 1;
        """
        params = [categoria.strip().upper(), anio]

    try:
        df = pd.read_sql(sql, conn, params=params)
        df["fecha"] = pd.to_datetime(df["fecha"])
        return df
    except Exception as e:
        print(f"❌ Error consulta {tabla} ({anio}): {e}")
        return pd.DataFrame(columns=["fecha", "cantidad"])
    finally:
        if conn: conn.close()

class PanelGraficoPredictivo:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.figure = None
        self.ax = None
        self.canvas = None

        # Frame contenedor
        self.plot_frame = ctk.CTkFrame(parent_frame, fg_color="white", corner_radius=10)
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.inicializar_grafico()

    def inicializar_grafico(self):
        plt.style.use('ggplot')
        self.figure, self.ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor('#FFFFFF')
        
        self.ax.set_title("Seleccione una categoría para analizar", color="#7f8c8d")
        self.ax.axis('off') 
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def actualizar_grafico(self, categoria, df_hist_2023, df_pred_2024, df_real_2024=None):
        self.ax.clear()
        self.ax.axis('on') 
        
        # Títulos limpios
        self.ax.set_title(f"Tendencia de Demanda: {categoria}", fontsize=14, fontweight='bold', pad=20, color="#2c3e50")
        self.ax.set_ylabel("Unidades", fontsize=11, color="#7f8c8d")
        self.ax.tick_params(axis='x', rotation=0, colors="#7f8c8d")
        self.ax.tick_params(axis='y', colors="#7f8c8d")
        
        # Eliminar bordes feos (spines)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        
        # --- 1. HISTÓRICO (Contexto Suave) ---
        if not df_hist_2023.empty:
            self.ax.fill_between(df_hist_2023["fecha"], df_hist_2023["cantidad"], color="#bdc3c7", alpha=0.2)
            self.ax.plot(df_hist_2023["fecha"], df_hist_2023["cantidad"], 
                         label="Histórico 2023", color="#95a5a6", linestyle="-", linewidth=1.5)

        # --- 2. PREDICCIÓN (Protagonista) ---
        if not df_pred_2024.empty:
            self.ax.plot(df_pred_2024["fecha"], df_pred_2024["cantidad"], 
                         label="Predicción 2024", color="#e67e22", marker="o", markersize=6, linewidth=2.5)
            
            # Etiqueta de valor máximo en la predicción
            max_pred = df_pred_2024["cantidad"].max()
            fecha_max = df_pred_2024.loc[df_pred_2024["cantidad"].idxmax(), "fecha"]
            self.ax.annotate(f'Pico: {int(max_pred)}', xy=(fecha_max, max_pred), xytext=(0, 10),
                             textcoords='offset points', ha='center', fontsize=9, color="#d35400", fontweight='bold')

        # --- 3. REALIDAD (Validación) ---
        if df_real_2024 is not None and not df_real_2024.empty:
            self.ax.plot(df_real_2024["fecha"], df_real_2024["cantidad"], 
                         label="Real 2024", color="#27ae60", marker="s", markersize=5, linewidth=2)

        meses_esp = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        
        def formatear_fecha_es(x, pos=None):
            # Convertimos el numero de fecha de matplotlib a objeto fecha real
            dt = mdates.num2date(x)
            return meses_esp[dt.month]

        # Aplicamos el formateador personalizado
        self.ax.xaxis.set_major_locator(mdates.MonthLocator())
        self.ax.xaxis.set_major_formatter(ticker.FuncFormatter(formatear_fecha_es))
        # ==========================================
        
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)
        self.figure.tight_layout()
        self.canvas.draw()

def mostrar_reportes_predictivos(contenido_frame):
    """
    Renderiza la interfaz estilo Dashboard con KPIs y Panel de Insights.
    """
    # 1. Limpiar
    for widget in contenido_frame.winfo_children(): widget.destroy()

    # Estructura Principal
    main_container = ctk.CTkFrame(contenido_frame, fg_color="#f5f6fa") # Fondo gris muy suave
    main_container.pack(fill="both", expand=True)

    # --- ENCABEZADO Y CONTROLES (Barra Superior) ---
    top_bar = ctk.CTkFrame(main_container, fg_color="white", height=80, corner_radius=0)
    top_bar.pack(fill="x", side="top", padx=0, pady=0)
    
    # Botón Atrás (Icono o Texto corto)
    ctk.CTkButton(top_bar, text="⬅", width=40, fg_color="#bdc3c7", hover_color="#95a5a6",
                  command=lambda: mostrar_menu_reportes(contenido_frame)).pack(side="left", padx=15, pady=15)

    ctk.CTkLabel(top_bar, text="Dashboard Predictivo de Ventas", font=("Arial", 20, "bold"), text_color="#2c3e50").pack(side="left", padx=10)

    # Selector de Categoría (A la derecha para fácil acceso)
    categorias = obtener_categorias_prediccion()
    combo_cat = ctk.CTkOptionMenu(top_bar, values=categorias, width=200, fg_color="#3498db", button_color="#2980b9")
    combo_cat.pack(side="right", padx=20, pady=15)
    if categorias: combo_cat.set(categorias[0])
    ctk.CTkLabel(top_bar, text="Categoría:", font=("Arial", 12, "bold")).pack(side="right", padx=5)

    # --- ÁREA DE CONTENIDO (Dividida en 2 columnas: Izq=KPIs/Insights, Der=Gráfico) ---
    content_area = ctk.CTkFrame(main_container, fg_color="transparent")
    content_area.pack(fill="both", expand=True, padx=20, pady=20)

    # Columna Izquierda (Panel de Control y Métricas)
    left_panel = ctk.CTkFrame(content_area, width=300, fg_color="transparent")
    left_panel.pack(side="left", fill="y", padx=(0, 20))

    # --- TARJETAS KPI (Visualización Rápida) ---
    kpi_frame = ctk.CTkFrame(left_panel, fg_color="white", corner_radius=10)
    kpi_frame.pack(fill="x", pady=(0, 20))
    
    ctk.CTkLabel(kpi_frame, text="Resumen Anual", font=("Arial", 14, "bold"), text_color="#7f8c8d").pack(pady=(15, 5))
    
    # Etiquetas que actualizaremos dinámicamente
    lbl_total_hist = ctk.CTkLabel(kpi_frame, text="---", font=("Arial", 24, "bold"), text_color="#95a5a6")
    lbl_total_hist.pack()
    ctk.CTkLabel(kpi_frame, text="Total 2023", font=("Arial", 10)).pack(pady=(0, 10))
    
    lbl_total_pred = ctk.CTkLabel(kpi_frame, text="---", font=("Arial", 24, "bold"), text_color="#e67e22")
    lbl_total_pred.pack()
    ctk.CTkLabel(kpi_frame, text="Proyección 2024", font=("Arial", 10)).pack(pady=(0, 10))

    lbl_tendencia = ctk.CTkLabel(kpi_frame, text="---", font=("Arial", 18, "bold"), text_color="#2ecc71")
    lbl_tendencia.pack()
    ctk.CTkLabel(kpi_frame, text="Crecimiento Esperado", font=("Arial", 10)).pack(pady=(0, 15))

    # --- CAJA DE INSIGHTS (Interpretación) ---
    insight_frame = ctk.CTkFrame(left_panel, fg_color="white", corner_radius=10)
    insight_frame.pack(fill="x", pady=0, expand=True)
    
    ctk.CTkLabel(insight_frame, text="💡 Análisis Inteligente", font=("Arial", 12, "bold"), text_color="#f1c40f").pack(pady=(15, 5), anchor="w", padx=15)
    
    txt_insight = ctk.CTkTextbox(insight_frame, height=240, fg_color="#fdfefe", text_color="#34495e", wrap="word", font=("Arial", 12))
    txt_insight.pack(fill="both", expand=True, padx=10, pady=10)
    txt_insight.insert("0.0", "Seleccione una categoría y haga clic en 'Analizar' para ver las recomendaciones del modelo XGBoost.")
    txt_insight.configure(state="disabled") # Solo lectura

    # Botón de Acción Principal
    btn_analizar = ctk.CTkButton(left_panel, text="⚡ Analizar Ahora", height=50, font=("Arial", 14, "bold"),
                                 fg_color="#27ae60", hover_color="#2ecc71",
                                 command=lambda: ejecutar_analisis())
    btn_analizar.pack(fill="x", pady=20)


    # Columna Derecha (Gráfico)
    right_panel = ctk.CTkFrame(content_area, fg_color="transparent")
    right_panel.pack(side="right", fill="both", expand=True)
    
    panel_grafico = PanelGraficoPredictivo(right_panel)


    # --- LÓGICA DE NEGOCIO ---
    def ejecutar_analisis():
        cat = combo_cat.get()
        if not cat: return
        
        # 1. Obtener datos
        df_2023 = consultar_datos_mensuales_predictivos(cat, 'desarrollo.ventas', 2023)
        df_pred_2024 = consultar_datos_mensuales_predictivos(cat, 'desarrollo.prediccion_mensual', 2024)
        df_real_2024 = consultar_datos_mensuales_predictivos(cat, 'desarrollo.ventas', 2024) # Opcional si ya hay datos reales

        # 2. Actualizar Gráfico
        panel_grafico.actualizar_grafico(cat, df_2023, df_pred_2024, df_real_2024)
        
        # 3. Calcular KPIs y Actualizar Etiquetas
        total_23 = df_2023["cantidad"].sum() if not df_2023.empty else 0
        total_24 = df_pred_2024["cantidad"].sum() if not df_pred_2024.empty else 0
        
        lbl_total_hist.configure(text=f"{int(total_23):,}")
        lbl_total_pred.configure(text=f"{int(total_24):,}")
        
        if total_23 > 0:
            crecimiento = ((total_24 - total_23) / total_23) * 100
            signo = "+" if crecimiento > 0 else ""
            color_tendencia = "#2ecc71" if crecimiento >= 0 else "#e74c3c" # Verde si sube, Rojo si baja
            lbl_tendencia.configure(text=f"{signo}{crecimiento:.1f}%", text_color=color_tendencia)
        else:
            lbl_tendencia.configure(text="N/A", text_color="gray")

        # 4. Generar Texto de Insight (Interpretación)
        generar_insight(cat, total_23, total_24, df_pred_2024)

    def generar_insight(categoria, t23, t24, df_pred):
        """
        Genera un texto analítico, manejando el caso de 'Sin Datos'.
        """
        msg = f"🔎 REPORTE PARA: {categoria}\n\n"
        
        # --- 1. CASO: NO HAY DATOS (PREDICCIÓN CERO) ---
        # Si la predicción es 0 (o ambos son 0), mostramos aviso y paramos aquí.
        if t24 == 0:
            msg += "🚫 SIN DATOS DE PREDICCIÓN\n"
            msg += "No se encontraron proyecciones ni datos suficientes para esta categoría.\n\n"
            msg += "👉 SUGERENCIA: Pruebe seleccionando otra categoría o verifique si existen ventas históricas."
            
        else:            
            # Calcular Variación Porcentual
            if t23 > 0:
                variacion = ((t24 - t23) / t23) * 100
            else:
                variacion = 100 # Si no había historial y ahora sí (crecimiento infinito)

            # Clasificación del Insight
            if variacion > 20:
                msg += f"🚀 CRECIMIENTO EXPLOSIVO (+{variacion:.1f}%)\n"
                msg += "El modelo detecta un aumento drástico en la demanda.\n"
                msg += "👉 ACCIÓN: Asegurar stock agresivamente y revisar capacidad.\n\n"
                
            elif 5 < variacion <= 20:
                msg += f"📈 TENDENCIA AL ALZA (+{variacion:.1f}%)\n"
                msg += "Se prevé un crecimiento saludable respecto al año anterior.\n"
                msg += "👉 ACCIÓN: Aumentar pedidos gradualmente (aprox. 10%).\n\n"
                
            elif -5 <= variacion <= 5:
                msg += f"⚖️ ESTABILIDAD ({variacion:.1f}%)\n"
                msg += "La demanda se mantiene muy similar al 2023.\n"
                msg += "👉 ACCIÓN: Mantener niveles de stock actuales.\n\n"
                
            elif -20 <= variacion < -5:
                msg += f"📉 CONTRACCIÓN LEVE ({variacion:.1f}%)\n"
                msg += "Se espera una ligera caída en las ventas.\n"
                msg += "👉 ACCIÓN: Reducir compras para evitar capital inmovilizado.\n\n"
                
            else: # Menor a -20%
                msg += f"⚠️ ALERTA DE CAÍDA ({variacion:.1f}%)\n"
                msg += "El modelo predice una reducción significativa.\n"
                msg += "👉 ACCIÓN: ¡Pausar pedidos grandes! Liquidar stock antiguo.\n\n"
            
            # Análisis de Picos (Solo si hay datos en el dataframe)
            if not df_pred.empty and df_pred["cantidad"].sum() > 0:
                try:
                    mes_pico_idx = df_pred["cantidad"].idxmax()
                    mes_pico_fecha = df_pred.loc[mes_pico_idx, "fecha"]
                    
                    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    nombre_mes = meses_nombres[mes_pico_fecha.month - 1]
                    
                    msg += f"📅 MOMENTO CLAVE: Prepare su inventario máximo para {nombre_mes}."
                except: pass

        # --- 3. Actualizar la UI ---
        txt_insight.configure(state="normal")
        txt_insight.delete("0.0", "end")
        txt_insight.insert("0.0", msg)
        txt_insight.configure(state="disabled")

#-------------------------------------------------------------------------------------------------------------------
# FIN DEL CODIGO DE PREDICCION INTEGRADO
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
    Muestra la interfaz de Reportes Varios CON DISEÑO LIMPIO (Sin Scroll innecesario).
    """
    # 1. Limpiar el contenido anterior
    for widget in contenido_frame.winfo_children():
        widget.destroy()

    # --- ESTRUCTURA PRINCIPAL (Fija y Limpia) ---
    # Usamos un Frame transparente que ocupe todo, sin Canvas ni Scrollbars manuales
    main_view = ctk.CTkFrame(contenido_frame, fg_color="transparent")
    main_view.pack(fill="both", expand=True)

    # --- ENCABEZADO ---
    header_frame = ctk.CTkFrame(main_view, fg_color="white", height=60, corner_radius=0)
    header_frame.pack(fill="x", side="top")
    
    # Botón Volver
    ctk.CTkButton(header_frame, text="⬅ Volver", width=80, fg_color="#95a5a6", hover_color="#7f8c8d",
                  command=lambda: mostrar_menu_reportes(contenido_frame)).pack(side="left", padx=20, pady=10)
    
    ctk.CTkLabel(header_frame, text="Generador de Reportes", font=("Arial", 20, "bold"), text_color="#2c3e50").pack(side="left", padx=10)

    # --- CONTENEDOR CENTRAL (Tarjeta Flotante) ---
    # Esto centra el formulario y le da un fondo blanco bonito, eliminando el "cuadro blanco" aleatorio
    card_frame = ctk.CTkFrame(main_view, fg_color="white", corner_radius=15)
    card_frame.pack(pady=40, padx=40, fill="both", expand=True) # expand=True llena el espacio pero con márgenes

    # Título interno
    ctk.CTkLabel(card_frame, text="Configuración del Reporte", font=("Arial", 16, "bold"), text_color="gray").pack(pady=(20, 5))
    
    # --- FORMULARIO (Grid Layout para orden) ---
    form_grid = ctk.CTkFrame(card_frame, fg_color="transparent")
    form_grid.pack(pady=20)

    # COLUMNA 1: TIPO Y CATEGORÍA
    col1 = ctk.CTkFrame(form_grid, fg_color="transparent")
    col1.grid(row=0, column=0, padx=20, sticky="n")

    ctk.CTkLabel(col1, text="1. Tipo de Reporte", font=("Arial", 12, "bold")).pack(anchor="w")
    # Referencias para pasar a la función de actualización
    # (Las definimos antes para poder referenciarlas en el command)
    # Nota: Python permite esto porque las lambdas se ejecutan después.
    
    tipos_reporte = ["Inventario", "Ventas", "Optimización de Compras (IA)"]
    reporte_seleccionado = ctk.CTkOptionMenu(col1, values=tipos_reporte, width=250, height=35)
    reporte_seleccionado.pack(pady=(5, 15))
    reporte_seleccionado.set("Inventario")

    ctk.CTkLabel(col1, text="2. Categoría", font=("Arial", 12, "bold")).pack(anchor="w")
    categorias_disponibles = obtener_categorias_garantias()
    categoria_menu = ctk.CTkOptionMenu(col1, values=categorias_disponibles, width=250, height=35)
    categoria_menu.pack(pady=(5, 15))
    categoria_menu.set(categorias_disponibles[0])

    # COLUMNA 2: PARÁMETROS VARIABLES (Aquí ocurre la magia de ocultar/mostrar)
    col2 = ctk.CTkFrame(form_grid, fg_color="transparent")
    col2.grid(row=0, column=1, padx=20, sticky="n")
    
    # -- Frame Params Optimización --
    optim_params_frame = ctk.CTkFrame(col2, fg_color="#f0f9ff", corner_radius=6) # Un azul muy suave para diferenciar
    ctk.CTkLabel(optim_params_frame, text="Fecha de Simulación (IA):", font=("Arial", 11, "bold"), text_color="#2980b9").pack(pady=(5,0))
    
    frame_f_sim = ctk.CTkFrame(optim_params_frame, fg_color="transparent")
    frame_f_sim.pack(pady=5, padx=5)
    
    fecha_demo_default = (datetime.now() - timedelta(days=365)).strftime('%d-%m-%Y')
    fecha_simulada_entry = ctk.CTkEntry(frame_f_sim, width=140)
    fecha_simulada_entry.insert(0, fecha_demo_default)
    fecha_simulada_entry.pack(side="left")
    ctk.CTkButton(frame_f_sim, text="📅", width=30, fg_color="#2980b9", 
                  command=lambda: open_calendar(contenido_frame.winfo_toplevel(), fecha_simulada_entry)).pack(side="left", padx=5)

    # -- Frame Params Ventas --
    ventas_params_frame = ctk.CTkFrame(col2, fg_color="transparent")
    
    ctk.CTkLabel(ventas_params_frame, text="ID Producto (Opcional):", font=("Arial", 11)).pack(anchor="w")
    id_producto_entry = ctk.CTkEntry(ventas_params_frame, width=200, placeholder_text="Todos")
    id_producto_entry.pack(pady=(0, 10))

    ctk.CTkLabel(ventas_params_frame, text="Rango de Fechas:", font=("Arial", 11)).pack(anchor="w")
    # Fecha Inicio
    f_start_frame = ctk.CTkFrame(ventas_params_frame, fg_color="transparent")
    f_start_frame.pack(fill="x", pady=2)
    fecha_inicio_entry = ctk.CTkEntry(f_start_frame, width=140, placeholder_text="Inicio: 01-01-2024")
    fecha_inicio_entry.pack(side="left")
    ctk.CTkButton(f_start_frame, text="📅", width=30, fg_color="#7f8c8d",
                  command=lambda: open_calendar(contenido_frame.winfo_toplevel(), fecha_inicio_entry)).pack(side="left", padx=5)

    # Fecha Fin
    f_end_frame = ctk.CTkFrame(ventas_params_frame, fg_color="transparent")
    f_end_frame.pack(fill="x", pady=2)
    fecha_fin_entry = ctk.CTkEntry(f_end_frame, width=140, placeholder_text="Fin: Hoy")
    fecha_fin_entry.pack(side="left")
    ctk.CTkButton(f_end_frame, text="📅", width=30, fg_color="#7f8c8d",
                  command=lambda: open_calendar(contenido_frame.winfo_toplevel(), fecha_fin_entry)).pack(side="left", padx=5)

    # Configurar el comando del dropdown principal AHORA que los frames existen
    reporte_seleccionado.configure(command=lambda sel: actualizar_opciones(sel, ventas_params_frame, optim_params_frame, categoria_menu))

    # COLUMNA 3: FORMATO Y ACCIÓN
    col3 = ctk.CTkFrame(form_grid, fg_color="transparent")
    col3.grid(row=0, column=2, padx=20, sticky="n")

    ctk.CTkLabel(col3, text="3. Formato de Salida", font=("Arial", 12, "bold")).pack(anchor="w")
    formatos_salida = ["Excel", "PDF"]
    formato_seleccionado = ctk.CTkOptionMenu(col3, values=formatos_salida, width=200, height=35, fg_color="#27ae60", button_color="#219150")
    formato_seleccionado.pack(pady=(5, 25))
    formato_seleccionado.set("Excel")

    ctk.CTkButton(col3, text="🚀 GENERAR REPORTE", width=200, height=50, fg_color="#2ecc71", hover_color="#27ae60", font=("Arial", 14, "bold"),
        command=lambda: generar_reporte_varios(
            reporte_seleccionado.get(),
            categoria_menu.get(),
            formato_seleccionado.get(),
            id_producto_entry.get(),
            fecha_inicio_entry.get(),
            fecha_fin_entry.get(),
            fecha_simulada_entry.get()
        )
    ).pack(side="bottom")

    # Inicializar estado visual
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
    elif selection == "Optimización de Compras":
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