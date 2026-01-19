# Archivo: src/reportes/report_ui.py

from datetime import datetime, timedelta
from tkinter import messagebox, filedialog, Tk 
import tkinter as tk 
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
import threading
import subprocess
import time


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

def calcular_precision_modelo(df_real, df_pred):
    """
    Calcula la precisión usando WMAPE.
    CORREGIDO: Usa el nombre correcto de columna 'cantidad_pred' tras el merge.
    """
    try:
        if df_real.empty or df_pred.empty:
            return 0.0

        # 1. Copias y Normalización de Fechas
        df_real_calc = df_real.copy()
        df_pred_calc = df_pred.copy()

        # Forzar a datetime y llevar al primer día del mes para asegurar coincidencia
        df_real_calc['fecha'] = pd.to_datetime(df_real_calc['fecha']).dt.to_period('M').dt.to_timestamp()
        df_pred_calc['fecha'] = pd.to_datetime(df_pred_calc['fecha']).dt.to_period('M').dt.to_timestamp()

        # 2. Merge (Inner Join)
        # suffixes=('_real', '_pred') renombrará 'cantidad' a 'cantidad_real' y 'cantidad_pred'
        df_merged = pd.merge(df_real_calc, df_pred_calc, on="fecha", suffixes=('_real', '_pred'))
        
        if df_merged.empty:
            return 0.0

        # 3. Cálculo WMAPE (Error Porcentual Absoluto Medio Ponderado)
        # ✅ USAMOS LOS NOMBRES CORRECTOS POST-MERGE
        col_real = 'cantidad_real'
        col_pred = 'cantidad_pred' # <--- AQUÍ ESTABA EL ERROR (Antes decía cantidad_predicha)
        
        suma_ventas_reales = df_merged[col_real].sum()
        
        if suma_ventas_reales == 0:
            return 0.0
            
        # Diferencia absoluta entre Real y Predicción
        suma_errores_abs = (df_merged[col_real] - df_merged[col_pred]).abs().sum()
        
        wmape = suma_errores_abs / suma_ventas_reales
        
        # Precisión = 1 - Error
        precision = max(0, (1 - wmape) * 100)
        
        return precision
        
    except Exception as e:
        print(f"❌ Error calculando precisión: {e}")
        return 0.0
        
    except Exception as e:
        print(f"❌ Error calculando precisión: {e}")
        # Imprimimos el error completo para saber qué pasó
        import traceback
        traceback.print_exc()
        return 0.0
    

def consultar_datos_mensuales_predictivos(categoria: str, tabla: str, anio: int = None) -> pd.DataFrame:
    """
    Consulta datos de ventas o predicciones, SIEMPRE AGREGADOS POR MES.
    """
    conn = conectar_db()
    if conn is None: return pd.DataFrame()

    try:
        if tabla == 'desarrollo.ventas':
            # --- VENTAS HISTÓRICAS (Por año específico) ---
            sql = """
                SELECT DATE_TRUNC('month', v.v_fecha)::date AS fecha, SUM(v.v_cantidad) AS cantidad
                FROM desarrollo.ventas v
                JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo
                WHERE TRIM(UPPER(s.categoria)) = %s AND EXTRACT(YEAR FROM v.v_fecha) = %s
                GROUP BY 1 ORDER BY 1;
            """
            params = [categoria.strip().upper(), anio]
            df = pd.read_sql(sql, conn, params=params)

        else:
            # --- PREDICCIONES (Todo el futuro disponible) ---
            sql = """
                SELECT DATE_TRUNC('month', v_fecha)::date AS fecha, SUM(cantidad_predicha) AS cantidad
                FROM desarrollo.prediccion_mensual
                WHERE TRIM(UPPER(categoria)) = %s
                GROUP BY 1 ORDER BY 1;
            """
            params = [categoria.strip().upper()]
            df = pd.read_sql(sql, conn, params=params)

        # Asegurar formato fecha
        if not df.empty:
            df["fecha"] = pd.to_datetime(df["fecha"])
            
        return df

    except Exception as e:
        print(f"❌ Error consulta {tabla}: {e}")
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
        
        self.ax.set_title(f"Tendencia de Demanda: {categoria}", fontsize=14, fontweight='bold', pad=20, color="#2c3e50")
        self.ax.set_ylabel("Unidades", fontsize=11, color="#7f8c8d")
        
        # Eliminar bordes
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        
        # --- 1. HISTÓRICO 2023 ---
        if not df_hist_2023.empty:
            self.ax.fill_between(df_hist_2023["fecha"], df_hist_2023["cantidad"], color="#bdc3c7", alpha=0.2)
            self.ax.plot(df_hist_2023["fecha"], df_hist_2023["cantidad"], 
                         label="Histórico 2023", color="#95a5a6", linestyle="-", linewidth=1.5)

        # --- 2. PREDICCIÓN (Futuro Completo) ---
        if not df_pred_2024.empty:
            # Determinamos si son más de 12 meses para ajustar etiqueta
            es_largo_plazo = len(df_pred_2024) > 12
            label_pred = "Predicción 2024-25" if es_largo_plazo else "Predicción 2024"
            
            self.ax.plot(df_pred_2024["fecha"], df_pred_2024["cantidad"], 
                         label=label_pred, color="#e67e22", marker="o", markersize=4, linewidth=2.5)
            
            # Anotar el pico máximo
            max_pred = df_pred_2024["cantidad"].max()
            fecha_max = df_pred_2024.loc[df_pred_2024["cantidad"].idxmax(), "fecha"]
            self.ax.annotate(f'Pico: {int(max_pred)}', xy=(fecha_max, max_pred), xytext=(0, 10),
                             textcoords='offset points', ha='center', fontsize=9, color="#d35400", fontweight='bold')

        # --- 3. REAL 2024 ---
        if df_real_2024 is not None and not df_real_2024.empty:
            self.ax.plot(df_real_2024["fecha"], df_real_2024["cantidad"], 
                         label="Real 2024", color="#27ae60", marker="s", markersize=4, linewidth=2)

        # --- FORMATEO INTELIGENTE DEL EJE X ---
        self.ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1)) # Mostrar todos los meses si posible
        
        # Si hay muchos datos (más de 18 meses totales en el eje), rotamos o simplificamos
        total_puntos = len(df_hist_2023) + len(df_pred_2024)
        
        if total_puntos > 24:
             self.ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)) # Cada 2 meses si es muy largo

        # Formateador personalizado: "Ene 24"
        def formatear_fecha(x, pos=None):
            dt = mdates.num2date(x)
            meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
            nombre_mes = meses[dt.month - 1]
            # Si mostramos varios años, agregamos el año (ej: "Ene 24")
            return f"{nombre_mes}\n{dt.strftime('%y')}"

        self.ax.xaxis.set_major_formatter(ticker.FuncFormatter(formatear_fecha))
        self.ax.tick_params(axis='x', rotation=0, colors="#7f8c8d", labelsize=8)
        
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)
        self.figure.tight_layout()
        self.canvas.draw()

def abrir_ventana_configuracion(parent):
    """
    Abre una ventana modal para configurar parámetros y re-entrenar el modelo.
    """
    config_win = ctk.CTkToplevel(parent)
    config_win.title("Configuración del Modelo Predictivo")
    config_win.geometry("500x550")
    config_win.transient(parent) 
    config_win.grab_set()        
    
    # Centrar la ventana
    try:
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 250
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 225
        config_win.geometry(f"+{x}+{y}")
    except: pass

    ctk.CTkLabel(config_win, text="⚙️ Configuración del Modelo", font=("Arial", 18, "bold")).pack(pady=20)

    # --- SECCIÓN 1: PARÁMETROS (VISUAL POR AHORA) ---
    frame_params = ctk.CTkFrame(config_win)
    frame_params.pack(fill="x", padx=20, pady=10)
    
    ctk.CTkLabel(frame_params, text="Horizonte de Predicción:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10,5))
    combo_horizonte = ctk.CTkComboBox(frame_params, values=["6 Meses", "1 Año (12 Meses)", "2 Años (24 Meses)"])
    combo_horizonte.pack(fill="x", padx=10, pady=5)
    combo_horizonte.set("1 Año (12 Meses)")
    
    ctk.CTkLabel(frame_params, text="Visualización en Reporte (Meses):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10,5))
    
    # Slider para seleccionar entre 12 y 24 meses
    lbl_slider = ctk.CTkLabel(frame_params, text="12 Meses")
    lbl_slider.pack(anchor="w", padx=10)
    
    def actualizar_slider(valor):
        lbl_slider.configure(text=f"{int(valor)} Meses")
        
    slider_meses = ctk.CTkSlider(frame_params, from_=12, to=24, number_of_steps=12, command=actualizar_slider)
    slider_meses.pack(fill="x", padx=10, pady=(0, 20))
    slider_meses.set(12)

    # --- SECCIÓN 2: RE-ENTRENAMIENTO ---
    frame_accion = ctk.CTkFrame(config_win, fg_color="#f0f0f0") # Color suave para diferenciar
    frame_accion.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame_accion, text="Actualización del Modelo IA", font=("Arial", 14, "bold"), text_color="#333").pack(pady=(15,5))
    ctk.CTkLabel(frame_accion, text="Este proceso puede tardar varios minutos.", font=("Arial", 11), text_color="gray").pack()

    # Barra de progreso (Indeterminada al principio)
    progress_bar = ctk.CTkProgressBar(frame_accion, width=300)
    progress_bar.set(0)
    progress_bar.pack(pady=15)
    
    lbl_status = ctk.CTkLabel(frame_accion, text="Estado: Listo", font=("Arial", 12), text_color="#333")
    lbl_status.pack(pady=5)

    def tarea_reentrenamiento():
        """
        Lógica robusta: Mantiene el archivo abierto mientras el proceso escribe.
        """
        # 1. Preparar UI
        seleccion = combo_horizonte.get()
        meses = 12
        if "6" in seleccion: meses = 6
        elif "24" in seleccion: meses = 24
        
        btn_ejecutar.configure(state="disabled", text="Ejecutando...")
        progress_bar.configure(mode="indeterminate")
        progress_bar.start()
        
        import subprocess
        import os
        import time
        import sys 
        
        # Archivo temporal
        LOG_FILE = "temp_execution_log.txt"
        
        # Entorno UTF-8
        env_vars = os.environ.copy()
        env_vars["PYTHONIOENCODING"] = "utf-8"

        def ejecutar_via_archivo(comando_lista, mensaje_estado):
            lbl_status.configure(text=mensaje_estado, text_color="#d35400")
            
            # Abrimos el archivo manualmente (SIN 'with') para que no se cierre solo
            f_out = open(LOG_FILE, "w", encoding="utf-8")
            
            try:
                process = subprocess.Popen(
                    comando_lista,
                    stdout=f_out,      
                    stderr=f_out,      
                    text=True,
                    encoding='utf-8',
                    env=env_vars
                )
                
                # Abrimos el archivo en modo LECTURA independiente
                with open(LOG_FILE, "r", encoding="utf-8") as f_read:
                    while True:
                        line = f_read.readline()
                        if line:
                            print(f"CMD: {line.strip()}")
                        else:
                            # Si no hay línea, verificamos si el proceso sigue vivo
                            if process.poll() is not None:
                                break
                            # Esperamos un poco y forzamos al sistema a vaciar buffers
                            time.sleep(0.1)
                
                # Verificar éxito
                if process.returncode != 0:
                    raise Exception(f"Fallo en ejecución (Código {process.returncode})")
            
            finally:
                f_out.close()

        try:
            # 1. DATA PROCESSOR
            ejecutar_via_archivo(
                [sys.executable, "src/data_processor.py"], 
                "⏳ Procesando Datos..."
            )
            
            # 2. MODEL TRAINER
            cmd_trainer = [
                sys.executable, 
                "src/model_trainer.py", 
                "--horizonte", str(meses),
                "--modo", "demo" 
            ]
            ejecutar_via_archivo(cmd_trainer, f"🧠 Entrenando ({meses} meses)...")

            # Finalización
            progress_bar.stop()
            progress_bar.configure(mode="determinate")
            progress_bar.set(1)
            
            lbl_status.configure(text="✅ ¡Actualización Completada!", text_color="#27ae60")
            messagebox.showinfo("Éxito", "Proceso finalizado correctamente.")
            config_win.destroy()

        except Exception as e:
            progress_bar.stop()
            lbl_status.configure(text="❌ Error", text_color="#c0392b")
            messagebox.showerror("Error", f"Ocurrió un error:\n{str(e)}")
            print(f"EXCEPCIÓN: {e}")
        
        finally:
            if os.path.exists(LOG_FILE):
                try: os.remove(LOG_FILE)
                except: pass
            
            if config_win.winfo_exists():
                btn_ejecutar.configure(state="normal", text="Iniciar Actualización")


    def iniciar_hilo():
        # Lanzamos la tarea en segundo plano para no congelar la UI
        hilo = threading.Thread(target=tarea_reentrenamiento)
        hilo.start()

    btn_ejecutar = ctk.CTkButton(
        frame_accion, 
        text="Iniciar Actualización", 
        fg_color="#2c3e50", 
        hover_color="#34495e",
        height=40,
        font=("Arial", 12, "bold"),
        command=iniciar_hilo
    )
    btn_ejecutar.pack(pady=10)

def mostrar_reportes_predictivos(contenido_frame):
    """
    Renderiza la interfaz estilo Dashboard con KPIs y Panel de Insights.
    """
    # 1. Limpiar
    for widget in contenido_frame.winfo_children(): widget.destroy()

    # Estructura Principal
    main_container = ctk.CTkFrame(contenido_frame, fg_color="#f5f6fa") 
    main_container.pack(fill="both", expand=True)

    # --- ENCABEZADO Y CONTROLES --
    top_bar = ctk.CTkFrame(main_container, fg_color="white", height=80, corner_radius=0)
    top_bar.pack(fill="x", side="top", padx=0, pady=0)
    
    # Botón Atrás (Icono o Texto corto)
    ctk.CTkButton(top_bar, text="⬅", width=40, fg_color="#bdc3c7", hover_color="#95a5a6",
                  command=lambda: mostrar_menu_reportes(contenido_frame)).pack(side="left", padx=15, pady=15)

    ctk.CTkLabel(top_bar, text="Dashboard Predictivo de Ventas", font=("Arial", 20, "bold"), text_color="#2c3e50").pack(side="left", padx=10)

    # Botón de Configuración (Icono de engranaje)
    ctk.CTkButton(
        top_bar, 
        text="⚙️", 
        width=40, 
        height=32,
        fg_color="#34495e", 
        hover_color="#2c3e50",
        font=("Arial", 18),
        command=lambda: abrir_ventana_configuracion(contenido_frame.winfo_toplevel())
    ).pack(side="right", padx=(5, 20), pady=15)
    
    # Selector de Categoría (A la derecha para fácil acceso)
    categorias = obtener_categorias_prediccion()
    combo_cat = ctk.CTkOptionMenu(top_bar, values=categorias, width=200, fg_color="#3498db", button_color="#2980b9")
    combo_cat.pack(side="right", padx=10, pady=15)
    if categorias: combo_cat.set(categorias[0])
    ctk.CTkLabel(top_bar, text="Categoría:", font=("Arial", 12, "bold")).pack(side="right", padx=5)

    content_area = ctk.CTkFrame(main_container, fg_color="transparent")
    content_area.pack(fill="both", expand=True, padx=20, pady=20)

    # Columna Izquierda (Panel de Control y Métricas)
    left_panel = ctk.CTkFrame(content_area, width=300, fg_color="transparent")
    left_panel.pack(side="left", fill="y", padx=(0, 20))

    # --- TARJETAS KPI  ---
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

    separator = ctk.CTkFrame(kpi_frame, height=2, fg_color="#f1f2f6") 
    separator.pack(fill="x", padx=10, pady=5)

    lbl_precision = ctk.CTkLabel(kpi_frame, text="---", font=("Arial", 18, "bold"), text_color="#3498db")
    lbl_precision.pack()
    ctk.CTkLabel(kpi_frame, text="Precisión del Modelo", font=("Arial", 10)).pack(pady=(0, 15))
    
    # --- CAJA DE INSIGHTS (Interpretación) ---
    insight_frame = ctk.CTkFrame(left_panel, fg_color="white", corner_radius=10)
    insight_frame.pack(fill="x", pady=0, expand=True)
    
    ctk.CTkLabel(insight_frame, text="💡 Análisis Inteligente", font=("Arial", 12, "bold"), text_color="#f1c40f").pack(pady=(15, 5), anchor="w", padx=15)
    
    txt_insight = ctk.CTkTextbox(insight_frame, height=240, fg_color="#fdfefe", text_color="#34495e", wrap="word", font=("Arial", 12))
    txt_insight.pack(fill="both", expand=True, padx=10, pady=10)
    txt_insight.insert("0.0", "Seleccione una categoría y haga clic en 'Analizar' para ver las recomendaciones del modelo XGBoost.")
    txt_insight.configure(state="disabled") 

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
        # Histórico 2023 (Fijo para contexto)
        df_2023 = consultar_datos_mensuales_predictivos(cat, 'desarrollo.ventas', 2023)
        
        # Predicción (Trae TODO lo que generó el modelo: 12 o 24 meses)
        df_pred_futuro = consultar_datos_mensuales_predictivos(cat, 'desarrollo.prediccion_mensual')
        
        # Real 2024 (Para validar precisión)
        df_real_2024 = consultar_datos_mensuales_predictivos(cat, 'desarrollo.ventas', 2024)

        # 2. Actualizar Gráfico
        # Pasamos df_pred_futuro que ahora puede tener datos de 2025
        panel_grafico.actualizar_grafico(cat, df_2023, df_pred_futuro, df_real_2024)
        
        # 3. Calcular KPIs
        total_23 = df_2023["cantidad"].sum() if not df_2023.empty else 0
        
        if not df_pred_futuro.empty:
            df_2024_solo = df_pred_futuro[df_pred_futuro["fecha"].dt.year == 2024]
            total_24 = df_2024_solo["cantidad"].sum()
        else:
            total_24 = 0
        
        lbl_total_hist.configure(text=f"{int(total_23):,}")
        lbl_total_pred.configure(text=f"{int(total_24):,}") 
        
        if total_23 > 0:
            crecimiento = ((total_24 - total_23) / total_23) * 100
            signo = "+" if crecimiento > 0 else ""
            color_tendencia = "#2ecc71" if crecimiento >= 0 else "#e74c3c"
            lbl_tendencia.configure(text=f"{signo}{crecimiento:.1f}%", text_color=color_tendencia)
        else:
            lbl_tendencia.configure(text="N/A", text_color="gray")

        # Precisión (Sigue comparando contra 2024 real)
        if df_real_2024 is not None and not df_real_2024.empty:
            precision = calcular_precision_modelo(df_real_2024, df_pred_futuro)
            if precision >= 80: color_prec = "#27ae60"
            elif precision >= 60: color_prec = "#f39c12"
            else: color_prec = "#e74c3c"
            lbl_precision.configure(text=f"{precision:.1f}%", text_color=color_prec)
        else:
            lbl_precision.configure(text="Sin Datos", text_color="gray")

        # 4. Insight
        generar_insight(cat, total_23, total_24, df_pred_futuro)

    def generar_insight(categoria, t23, t24, df_pred):
        """
        Genera un texto analítico, manejando el caso de 'Sin Datos'.
        """
        msg = f"🔎 REPORTE PARA: {categoria}\n\n"
        
        # --- 1. CASO: NO HAY DATOS (PREDICCIÓN CERO) ---
        if t24 == 0:
            msg += "🚫 SIN DATOS DE PREDICCIÓN\n"
            msg += "No se encontraron proyecciones ni datos suficientes para esta categoría.\n\n"
            msg += "👉 SUGERENCIA: Pruebe seleccionando otra categoría o verifique si existen ventas históricas."
            
        else:            
            # Calcular Variación Porcentual
            if t23 > 0:
                variacion = ((t24 - t23) / t23) * 100
            else:
                variacion = 100 

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
                
            else: 
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
    top = ctk.CTkToplevel(master)  
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
    card_frame.pack(pady=40, padx=40, fill="both", expand=True) 

    # Título interno
    ctk.CTkLabel(card_frame, text="Configuración del Reporte", font=("Arial", 16, "bold"), text_color="gray").pack(pady=(20, 5))
    
    # --- FORMULARIO (Grid Layout para orden) ---
    form_grid = ctk.CTkFrame(card_frame, fg_color="transparent")
    form_grid.pack(pady=20)

    # COLUMNA 1: TIPO Y CATEGORÍA
    col1 = ctk.CTkFrame(form_grid, fg_color="transparent")
    col1.grid(row=0, column=0, padx=20, sticky="n")

    ctk.CTkLabel(col1, text="1. Tipo de Reporte", font=("Arial", 12, "bold")).pack(anchor="w")
    
    tipos_reporte = ["Inventario", "Ventas", "Optimización de Inventario"]
    reporte_seleccionado = ctk.CTkOptionMenu(col1, values=tipos_reporte, width=250, height=35)
    reporte_seleccionado.pack(pady=(5, 15))
    reporte_seleccionado.set("Inventario")

    ctk.CTkLabel(col1, text="2. Categoría", font=("Arial", 12, "bold")).pack(anchor="w")
    categorias_disponibles = obtener_categorias_garantias()
    categoria_menu = ctk.CTkOptionMenu(col1, values=categorias_disponibles, width=250, height=35)
    categoria_menu.pack(pady=(5, 15))
    categoria_menu.set(categorias_disponibles[0])

    # COLUMNA 2: PARÁMETROS VARIABLES 
    col2 = ctk.CTkFrame(form_grid, fg_color="transparent")
    col2.grid(row=0, column=1, padx=20, sticky="n")
    
    # -- Frame Params Optimización --
    optim_params_frame = ctk.CTkFrame(col2, fg_color="#f0f9ff", corner_radius=6) 
    ctk.CTkLabel(optim_params_frame, text="Fecha de Simulación:", font=("Arial", 11, "bold"), text_color="#2980b9").pack(pady=(5,0))
    
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
    formatato_seleccionado = ctk.CTkOptionMenu(col3, values=formatos_salida, width=200, height=35, fg_color="#27ae60", button_color="#219150")
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
    ventas_frame.pack_forget()
    optim_frame.pack_forget()
    
    if selection == "Ventas":
        ventas_frame.pack(pady=10, padx=20, fill="x")
        categoria_menu.configure(state="normal")
    elif selection == "Inventario":
        categoria_menu.configure(state="normal")
    elif selection == "Optimización de Compras":
        optim_frame.pack(pady=10, padx=20, fill="x") 
        categoria_menu.configure(state="normal")


def calcular_optimizacion_interna(categoria, fecha_simulada):
    """
    Genera el DataFrame con lógica completa.
    CORREGIDO: Los nombres de columna ahora coinciden EXACTAMENTE con lo que espera el PDF.
    """
    conn = conectar_db()
    if not conn: return pd.DataFrame()
    
    sql = "SELECT id_articulo, descripcion, categoria, cant_inventario, precio_unit FROM desarrollo.stock"
    if categoria and categoria != "Todas las Categorías":
        sql += f" WHERE categoria = '{categoria}'"
    
    df = pd.read_sql(sql, conn)
    conn.close()
    
    if df.empty: return pd.DataFrame()

    resultados = []
    
    for _, row in df.iterrows():
        stock_actual = row['cant_inventario']
        
        # --- SIMULACIÓN DE IA ---
        np.random.seed(row['id_articulo']) 
        demanda_predicha = np.random.randint(5, 50) 
        
        factor_probabilidad = min(demanda_predicha / 50, 1.0)
        prob_venta_str = f"{int(factor_probabilidad * 100)}%"

        inv_proyectado = stock_actual - demanda_predicha
        punto_reorden = demanda_predicha 

        # --- LÓGICA DE ACCIÓN ---
        if inv_proyectado < 0:
            accion = "RIESGO DE QUIEBRE"
            comprar = abs(inv_proyectado) + int(demanda_predicha * 0.2)
        
        elif stock_actual > (demanda_predicha * 3) and stock_actual > 5:
            accion = "EXCESO DE STOCK"
            comprar = 0
            
        elif demanda_predicha < 2 and stock_actual > 0:
             accion = "BAJA ROTACIÓN"
             comprar = 0
             
        elif stock_actual <= punto_reorden:
            accion = "REPONER STOCK"
            comprar = punto_reorden - stock_actual
            
        else:
            accion = "STOCK SALUDABLE"
            comprar = 0

        resultados.append({
            "ID": row['id_articulo'],
            "Descripción": row['descripcion'],
            "Categoría": row['categoria'],
            "Stock Actual": stock_actual,
            
            # --- CORRECCIÓN DE NOMBRES PARA EL PDF ---
            "Prob. %": prob_venta_str,    # Antes era: "Prob. de venta" (ERROR)
            "Proyección": inv_proyectado,
            "Reorden": punto_reorden,
            "Comprar": comprar,           # Antes era: "Comprar" (Correcto, mantenemos)
            # ----------------------------------------
            
            "Acción Sugerida": accion
        })
        
    return pd.DataFrame(resultados)


def generar_reporte_varios(tipo_reporte, categoria, formato_salida, id_producto, fecha_inicio, fecha_fin, fecha_simulada=None):
    """
    Función principal que maneja la lógica de obtención de datos y exportación.
    """
    root = None
    try:
        root = Tk()
        root.withdraw()
    except Exception: pass 

    filtros = {'categoria': categoria}
    df_reporte = None
    fecha_sql = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 1. LÓGICA SEGÚN TIPO DE REPORTE
        if tipo_reporte == "Inventario":
            df_reporte = consultar_stock(categoria)

        elif tipo_reporte == "Optimización de Inventario":
            print("🔮 Ejecutando motor de optimización (Lógica Interna)...")
            
            # 1. Usamos la lógica interna con los nombres de columna ya corregidos
            df_reporte = calcular_optimizacion_interna(categoria, fecha_simulada)
            
            if df_reporte.empty:
                try:
                    print("⚠️ Datos internos vacíos, intentando módulo externo...")
                    from optimization.inventory_optimizer import generar_dataset_reporte
                    df_reporte = generar_dataset_reporte(categoria, fecha_sql)
                except ImportError:
                    pass

            if df_reporte is None or df_reporte.empty:
                messagebox.showinfo("Resultado", "No hay datos para generar recomendaciones.")
                return

        elif tipo_reporte == "Ventas":
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
            if tipo_reporte == "Optimización de Inventario": # Ajustado nombre para coincidir
                titulo_pdf = "Reporte Inteligente de Reabastecimiento (EOQ)"
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
    conn = conectar_db()
    if conn is None:
        messagebox.showerror("Error de Conexión", "No se pudo conectar a la base de datos.")
        return ["Error de Conexión"]

    SQL_QUERY = "SELECT DISTINCT gar_categoria FROM desarrollo.garantias WHERE gar_categoria IS NOT NULL ORDER BY gar_categoria;"
    try:
        df_categorias = pd.read_sql(SQL_QUERY, conn)
        def truncar_categoria(nombre):
            return nombre[:20] + "..." if len(nombre) > 20 else nombre
        df_categorias['gar_categoria'] = df_categorias['gar_categoria'].apply(truncar_categoria)
        categorias = list(df_categorias['gar_categoria'].unique())
        categorias.insert(0, "Todas las Categorías")
        return categorias
    except Exception as e:
        return ["Error de Consulta"]
    finally:
        if conn: conn.close()
    

def consultar_stock(categoria: str) -> pd.DataFrame:
    conn = conectar_db()
    if conn is None: return pd.DataFrame() 

    SQL_QUERY = """
    SELECT id_articulo, descripcion, precio_unit, cant_inventario, precio_total, categoria
    FROM desarrollo.stock
    """
    if categoria != "Todas las Categorías":
        SQL_QUERY += f" WHERE categoria = '{categoria.replace("'", "''")}'"
    SQL_QUERY += " ORDER BY categoria, descripcion;"

    try:
        df_stock = pd.read_sql(SQL_QUERY, conn)
        return df_stock
    except Exception as e:
        messagebox.showerror("Error de Consulta", f"Error: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()
    
    
def consultar_ventas(id_producto, fecha_inicio_sql, fecha_fin_sql, categoria) -> pd.DataFrame:
    conn = conectar_db()
    if conn is None: return pd.DataFrame() 

    params = [fecha_inicio_sql, fecha_fin_sql]
    
    # Base query
    SQL_QUERY = """
        SELECT 
            v.v_comprob as COMPROBANTE, v.v_tipotransacc as TIPO_TRANSACCION, v.v_montous_unit AS MONTO_UNITARIO, v.v_montous_total AS MONTO_TOTAL,
            v.v_id_producto AS ID_PRODUCTO, v.v_product AS PRODUCTO, s.categoria as CATEGORIA, v.v_id_cliente AS ID_CLIENTE,
            c.nombre AS nombre_cliente, 
            v.v_fact AS FACTURA, v.v_cantidad AS CANTIDAD, u.user_name AS USUARIO, to_char(v.v_fecha, 'DD/MM/YYYY HH24:MI:SS') AS FECHA_VENTA 
        FROM desarrollo.ventas v
        LEFT JOIN desarrollo.clientes c ON v.v_id_cliente = c.id_cliente
        LEFT JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo 
        LEFT JOIN desarrollo.usuarios u ON v.v_user = u.user_key
        WHERE v.v_fecha BETWEEN %s AND %s 
    """
    
    if categoria != "Todas las Categorías":
        SQL_QUERY += " AND s.categoria = %s"
        params.append(categoria)
        
    if id_producto is not None:
        SQL_QUERY += " AND v.v_id_producto = %s"
        params.append(id_producto)

    SQL_QUERY += " ORDER BY v.v_fecha DESC;"
    
    try:
        df_ventas = pd.read_sql(SQL_QUERY, conn, params=params)
        return df_ventas
    except Exception as e:
        messagebox.showerror("Error de Consulta", f"Error: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()