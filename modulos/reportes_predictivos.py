import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from bd import conectar_db

# ===============================
# 🔹 1. FUNCIONES DE CONSULTA SQL
# ===============================

def obtener_categorias():
    """Obtiene todas las categorías disponibles."""
    conn = conectar_db()
    if conn is None: return []
    try:
        # Usamos UPPER/TRIM para evitar duplicados sucios
        sql = "SELECT DISTINCT TRIM(UPPER(categoria)) as categoria FROM desarrollo.stock ORDER BY 1;"
        df = pd.read_sql(sql, conn)
        return df["categoria"].tolist()
    except Exception as e:
        print(f"❌ Error categorías: {e}")
        return []
    finally:
        if conn: conn.close()

def consultar_datos_mensuales(categoria: str, tabla: str, anio: int = None) -> pd.DataFrame:
    """
    Función genérica para consultar ventas o predicciones mensuales.
    tabla: 'desarrollo.ventas' (requiere join con stock) o 'desarrollo.prediccion_mensual'
    """
    conn = conectar_db()
    if conn is None: return pd.DataFrame(columns=["fecha", "cantidad"])

    if tabla == 'desarrollo.ventas':
        # Consulta para histórico real (join necesario)
        sql = """
            SELECT DATE_TRUNC('month', v.v_fecha)::date AS fecha, SUM(v.v_cantidad) AS cantidad
            FROM desarrollo.ventas v
            JOIN desarrollo.stock s ON v.v_id_producto = s.id_articulo
            WHERE TRIM(UPPER(s.categoria)) = %s AND EXTRACT(YEAR FROM v.v_fecha) = %s
            GROUP BY 1 ORDER BY 1;
        """
        params = [categoria.strip().upper(), anio]
    else:
        # Consulta para predicciones (directa a la tabla nueva)
        # Ajusta si tu tabla prediccion_mensual ya tiene columna fecha real
        sql = """
            SELECT MAKE_DATE(anio, mes, 1) AS fecha, SUM(cantidad_predicha) AS cantidad
            FROM desarrollo.prediccion_mensual
            WHERE TRIM(UPPER(categoria)) = %s
            GROUP BY 1 ORDER BY 1;
        """
        params = [categoria.strip().upper()]

    try:
        df = pd.read_sql(sql, conn, params=params)
        df["fecha"] = pd.to_datetime(df["fecha"]) # Asegurar tipo datetime
        return df
    except Exception as e:
        print(f"❌ Error consulta {tabla}: {e}")
        return pd.DataFrame(columns=["fecha", "cantidad"])
    finally:
        if conn: conn.close()

# ===============================
# 🔹 2. LÓGICA DE GRÁFICOS Y MÉTRICAS
# ===============================

def calcular_precision_segura(df_real, df_pred):
    """Calcula WMAPE (Weighted Mean Absolute Percentage Error) para evitar divisiones por cero."""
    # Unir datos por fecha
    df_merged = pd.merge(df_real, df_pred, on="fecha", how="inner", suffixes=("_real", "_pred"))
    
    if df_merged.empty: return None, 0

    total_ventas = df_merged["cantidad_real"].sum()
    total_error = (df_merged["cantidad_real"] - df_merged["cantidad_pred"]).abs().sum()

    if total_ventas == 0: return None, 0 # Evitar división por cero si no hubo ventas

    wmape = (total_error / total_ventas) * 100
    precision = max(0, 100 - wmape) # Precisión no puede ser negativa
    
    return df_merged, precision

def generar_grafico_unificado(categoria: str, mostrar_real_2024=False):
    """Genera el gráfico solicitado."""
    print(f"📊 Generando gráfico para: {categoria} (Comparativa 2024: {mostrar_real_2024})")
    
    # 1. Cargar datos
    df_hist_2023 = consultar_datos_mensuales(categoria, 'desarrollo.ventas', 2023)
    df_pred_2024 = consultar_datos_mensuales(categoria, 'desarrollo.prediccion_mensual')
    
    if df_hist_2023.empty and df_pred_2024.empty:
        messagebox.showwarning("Sin datos", f"No hay información para la categoría '{categoria}'.")
        return

    # 2. Configurar gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title(f"Análisis de Ventas: {categoria}", fontsize=14, fontweight='bold')
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Cantidad Unidades")
    ax.grid(True, linestyle='--', alpha=0.6)

    # 3. Graficar Histórico 2023 (Siempre se muestra como contexto)
    if not df_hist_2023.empty:
        ax.plot(df_hist_2023["fecha"], df_hist_2023["cantidad"], 
                label="Histórico 2023", color="#3498db", marker="o", linestyle="-", alpha=0.7)

    # 4. Graficar Predicción 2024
    if not df_pred_2024.empty:
        # Filtramos solo 2024 para la predicción si hay datos futuros
        df_pred_2024_plot = df_pred_2024[df_pred_2024["fecha"].dt.year == 2024]
        ax.plot(df_pred_2024_plot["fecha"], df_pred_2024_plot["cantidad"], 
                label="Predicción Modelo", color="#e67e22", marker="D", linestyle="--", linewidth=2)

    # 5. (Opcional) Graficar Real 2024 y calcular precisión
    precision_texto = ""
    if mostrar_real_2024:
        df_real_2024 = consultar_datos_mensuales(categoria, 'desarrollo.ventas', 2024)
        if not df_real_2024.empty:
            ax.plot(df_real_2024["fecha"], df_real_2024["cantidad"], 
                    label="Venta Real 2024", color="#2ecc71", marker="s", linewidth=2.5)
            
            # Calcular precisión
            _, precision = calcular_precision_segura(df_real_2024, df_pred_2024)
            if precision is not None:
                precision_texto = f"\nPrecisión Global (2024): {precision:.1f}%"
                # Añadir texto al gráfico
                plt.figtext(0.15, 0.85, precision_texto, fontsize=11, 
                            bbox={"facecolor":"white", "alpha":0.8, "pad":5})
        else:
             messagebox.showinfo("Info", "No hay ventas reales registradas aún en 2024 para comparar.")

    # Formato de fechas en eje X
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()

# ===============================
# 🔹 3. INTERFAZ GRÁFICA
# ===============================

def crear_interfaz_reportes_predictivos(parent_frame):
    """
    Integra este módulo en tu ventana principal. 
    'parent_frame' debe ser el frame contenedor donde quieres que aparezca.
    """
    # Limpiar frame previo si existe
    for widget in parent_frame.winfo_children():
        widget.destroy()

    frame = tk.Frame(parent_frame, bg="#f5f6fa")
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    tk.Label(frame, text="🔮 Módulo de Predicción de Ventas", 
             font=("Helvetica", 18, "bold"), bg="#f5f6fa", fg="#2c3e50").pack(pady=(0, 20))

    # Selector de Categoría
    tk.Label(frame, text="Seleccione Categoría:", font=("Arial", 11), bg="#f5f6fa").pack(anchor="w")
    
    categorias = obtener_categorias()
    combo_cat = ttk.Combobox(frame, values=categorias, state="readonly", font=("Arial", 11))
    combo_cat.pack(fill="x", pady=(5, 20))
    if categorias: combo_cat.current(0)

    # Botones de Acción
    btn_frame = tk.Frame(frame, bg="#f5f6fa")
    btn_frame.pack(fill="x", pady=10)

    def on_ver_prediccion():
        cat = combo_cat.get()
        if cat: generar_grafico_unificado(cat, mostrar_real_2024=False)

    def on_comparar_realidad():
        cat = combo_cat.get()
        if cat: generar_grafico_unificado(cat, mostrar_real_2024=True)

    tk.Button(btn_frame, text="📈 Ver Pronóstico Futuro", command=on_ver_prediccion,
              bg="#3498db", fg="white", font=("Arial", 12, "bold"), relief="flat", padx=20, pady=10).pack(side="left", expand=True, fill="x", padx=(0, 10))

    tk.Button(btn_frame, text="🆚 Comparar con Realidad", command=on_comparar_realidad,
              bg="#2ecc71", fg="white", font=("Arial", 12, "bold"), relief="flat", padx=20, pady=10).pack(side="right", expand=True, fill="x", padx=(10, 0))

    # Nota informativa
    tk.Label(frame, text="Nota: La comparación requiere que existan ventas registradas en 2024.",
             font=("Arial", 9, "italic"), bg="#f5f6fa", fg="#7f8c8d").pack(pady=20)

# ===============================
# 🔹 EJECUCIÓN INDEPENDIENTE
# ===============================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Sistema de Predicción")
    root.geometry("600x400")
    root.configure(bg="#f5f6fa")
    crear_interfaz_reportes_predictivos(root)
    root.mainloop()
    
    
    