import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np

# Importamos tu conector (simulado si no existe)
try:
    from bd import conectar_db
except ImportError:
    def conectar_db(): return None 

# ===============================
# 🔹 1. FUNCIONES DE CONSULTA SQL
# ===============================

def obtener_categorias():
    conn = conectar_db()
    if conn is None: return ["CAT_EJEMPLO_A", "CAT_EJEMPLO_B"] 
    try:
        sql = "SELECT DISTINCT TRIM(UPPER(categoria)) as categoria FROM desarrollo.stock ORDER BY 1;"
        df = pd.read_sql(sql, conn)
        return df["categoria"].tolist()
    except Exception as e:
        print(f"❌ Error categorías: {e}")
        return []
    finally:
        if conn: conn.close()

def consultar_datos_mensuales(categoria: str, tabla: str, anio: int) -> pd.DataFrame:
    """
    Consulta datos para un año específico.
    """
    conn = conectar_db()
    
    # --- MOCK DATA (Para que pruebes el gráfico si no hay BD) ---
    if conn is None: 
        # Generamos datos aleatorios pero consistentes con el año solicitado
        np.random.seed(anio) # Semilla fija por año para que no cambie al refrescar
        fechas = pd.date_range(start=f"{anio}-01-01", periods=12, freq='MS')
        base = 100 if anio == 2023 else 110 # Tendencia ligera al alza en 2024
        ruido = np.random.randint(-20, 20, size=12)
        cantidades = base + ruido
        return pd.DataFrame({"fecha": fechas, "cantidad": cantidades})
    # -----------------------------------------------------------

    if tabla == 'desarrollo.ventas':
        # Ventas reales (históricas o del 2024 actual)
        sql = """
            SELECT DATE_TRUNC('month', v.v_fecha)::date AS fecha, SUM(v.v_cantidad) AS cantidad
            FROM desarrollo.ventas v
            JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo
            WHERE TRIM(UPPER(s.categoria)) = %s AND EXTRACT(YEAR FROM v.v_fecha) = %s
            GROUP BY 1 ORDER BY 1;
        """
    else:
        # Predicciones (Específicamente para comparar el año 2024)
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

# ===============================
# 🔹 2. VISUALIZACIÓN (PANEL GRÁFICO)
# ===============================

class PanelGraficoPredictivo:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.figure = None
        self.ax = None
        self.canvas = None

        # Frame contenedor
        self.plot_frame = tk.Frame(parent_frame, bg="white", bd=1, relief="sunken")
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.inicializar_grafico()

    def inicializar_grafico(self):
        plt.style.use('ggplot')
        self.figure, self.ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor('#FFFFFF')
        
        self.ax.set_title("Seleccione una categoría para analizar", color="#7f8c8d")
        self.ax.axis('off') # Ocultar ejes hasta que haya datos
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def actualizar_grafico(self, categoria, df_hist_2023, df_pred_2024, df_real_2024=None):
        self.ax.clear()
        self.ax.axis('on') # Reactivar ejes
        
        # Títulos y Etiquetas
        titulo = f"Análisis de Precisión: {categoria}"
        self.ax.set_title(titulo, fontsize=12, fontweight='bold', pad=15)
        self.ax.set_ylabel("Cantidad (Unidades)", fontsize=10)
        self.ax.grid(True, linestyle=':', alpha=0.6)
        
        # --- 1. HISTÓRICO (2023) ---
        # Se muestra para ver de dónde venimos
        if not df_hist_2023.empty:
            self.ax.plot(df_hist_2023["fecha"], df_hist_2023["cantidad"], 
                         label="Histórico 2023", color="#7f8c8d", linestyle="-", alpha=0.5)

        # --- 2. PREDICCIÓN (2024) ---
        # Esta es la línea que generó tu modelo XGBoost
        if not df_pred_2024.empty:
            self.ax.plot(df_pred_2024["fecha"], df_pred_2024["cantidad"], 
                         label="Predicción IA (2024)", color="#e67e22", marker="o", markersize=4, linewidth=2, linestyle="--")
            
            # Sombra de margen de error visual (Estético)
            y_vals = df_pred_2024["cantidad"]
            self.ax.fill_between(df_pred_2024["fecha"], y_vals*0.9, y_vals*1.1, color="#e67e22", alpha=0.1)

        # --- 3. REALIDAD (2024) ---
        # Lo que realmente ocurrió/está ocurriendo este año
        if df_real_2024 is not None and not df_real_2024.empty:
            self.ax.plot(df_real_2024["fecha"], df_real_2024["cantidad"], 
                         label="Venta Real (2024)", color="#2ecc71", marker="s", markersize=5, linewidth=2)

            # Calcular error simple para mostrar en el gráfico
            comun = pd.merge(df_real_2024, df_pred_2024, on="fecha", how="inner", suffixes=("_real", "_pred"))
            if not comun.empty:
                error_total = (comun["cantidad_real"] - comun["cantidad_pred"]).abs().sum()
                venta_total = comun["cantidad_real"].sum()
                prec = 100 - ((error_total / venta_total) * 100) if venta_total > 0 else 0
                
                # Texto de precisión dentro del gráfico
                self.ax.text(0.02, 0.95, f"Precisión Modelo: {prec:.1f}%", transform=self.ax.transAxes,
                             bbox=dict(facecolor='white', alpha=0.8, edgecolor='#2ecc71', boxstyle='round'))

        # Formato eje X (Fechas)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
        self.ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)) # Cada 2 meses para no saturar
        self.figure.autofmt_xdate(rotation=30)
        
        self.ax.legend(loc='upper right', fontsize=9)
        self.canvas.draw()

# ===============================
# 🔹 3. INTERFAZ PRINCIPAL
# ===============================

def crear_interfaz_reportes_predictivos(parent_frame):
    # Limpieza
    for widget in parent_frame.winfo_children(): widget.destroy()

    main_container = tk.Frame(parent_frame, bg="#f5f6fa")
    main_container.pack(fill="both", expand=True)
    
    # --- PANEL IZQUIERDO (CONTROLES) ---
    control_frame = tk.Frame(main_container, bg="#ecf0f1", width=250)
    control_frame.pack(side="left", fill="y")
    
    tk.Label(control_frame, text="Validación de Modelo", font=("Segoe UI", 14, "bold"), bg="#ecf0f1", fg="#2c3e50").pack(pady=20, padx=15)
    
    # Selector
    tk.Label(control_frame, text="Categoría de Producto:", bg="#ecf0f1").pack(padx=15, anchor="w")
    categorias = obtener_categorias()
    combo_cat = ttk.Combobox(control_frame, values=categorias, state="readonly")
    combo_cat.pack(fill="x", padx=15, pady=(5, 20))
    if categorias: combo_cat.current(0)

    # Variables Fijas de Años
    ANIO_HISTORICO = 2023
    ANIO_OBJETIVO = 2024

    # Instancia del Gráfico
    graph_area = tk.Frame(main_container, bg="white")
    graph_area.pack(side="right", fill="both", expand=True, padx=10, pady=10)
    panel = PanelGraficoPredictivo(graph_area)

    # --- LÓGICA DE BOTONES ---
    def cargar_escenario_completo():
        cat = combo_cat.get()
        if not cat: return
        
        # 1. Traer datos 2023 (Contexto)
        df_2023 = consultar_datos_mensuales(cat, 'desarrollo.ventas', ANIO_HISTORICO)
        
        # 2. Traer predicción 2024 (Modelo)
        df_pred_2024 = consultar_datos_mensuales(cat, 'desarrollo.prediccion_mensual', ANIO_OBJETIVO)
        
        # 3. Traer realidad 2024 (Validación)
        df_real_2024 = consultar_datos_mensuales(cat, 'desarrollo.ventas', ANIO_OBJETIVO)
        
        if df_2023.empty and df_pred_2024.empty:
            messagebox.showwarning("Sin datos", "No se encontraron datos para graficar.")
            return

        # Actualizar gráfico con las 3 series
        panel.actualizar_grafico(cat, df_2023, df_pred_2024, df_real_2024)

    def ver_solo_pronostico():
        # Opción para ver solo la predicción sin "hacer trampa" viendo la realidad
        cat = combo_cat.get()
        if not cat: return
        
        df_2023 = consultar_datos_mensuales(cat, 'desarrollo.ventas', ANIO_HISTORICO)
        df_pred_2024 = consultar_datos_mensuales(cat, 'desarrollo.prediccion_mensual', ANIO_OBJETIVO)
        
        panel.actualizar_grafico(cat, df_2023, df_pred_2024, df_real_2024=None)

    # Botones
    btn_style = {"relief":"flat", "font":("Segoe UI", 10), "cursor":"hand2", "pady": 8}

    tk.Button(control_frame, text=f"👁 Ver Solo Pronóstico {ANIO_OBJETIVO}", 
              command=ver_solo_pronostico, bg="#3498db", fg="white", **btn_style).pack(fill="x", padx=15, pady=5)

    tk.Button(control_frame, text=f"✅ Validar vs Real {ANIO_OBJETIVO}", 
              command=cargar_escenario_completo, bg="#27ae60", fg="white", **btn_style).pack(fill="x", padx=15, pady=5)

    # Resumen Informativo
    tk.Label(control_frame, text=f"Comparando:\n• Base: {ANIO_HISTORICO}\n• Objetivo: {ANIO_OBJETIVO}", 
             bg="#ecf0f1", fg="#7f8c8d", justify="left", font=("Arial", 9)).pack(side="bottom", anchor="w", padx=15, pady=20)

# ===============================
# EJECUCIÓN
# ===============================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Validación de Stock Inteligente")
    root.geometry("1100x600")
    crear_interfaz_reportes_predictivos(root)
    root.mainloop()