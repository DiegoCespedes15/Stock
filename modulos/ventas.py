import customtkinter as ctk
import tkinter.ttk as ttk
from bd import conectar_db

def mostrar_ventas(frame_destino):
    for widget in frame_destino.winfo_children():
        widget.destroy()

    ctk.CTkLabel(frame_destino, text="Listado de Ventas", font=("Arial", 18)).pack(pady=10)

    # --- Filtros ---
    filtros_frame = ctk.CTkFrame(frame_destino)
    filtros_frame.pack(pady=5, padx=10, fill="x")

    cliente_var = ctk.StringVar()
    fecha_var = ctk.StringVar()  # formato: YYYY-MM-DD

    ctk.CTkLabel(filtros_frame, text="Cliente:").grid(row=0, column=0, padx=5, pady=5)
    cliente_entry = ctk.CTkEntry(filtros_frame, textvariable=cliente_var, width=150)
    cliente_entry.grid(row=0, column=1, padx=5, pady=5)

    ctk.CTkLabel(filtros_frame, text="Fecha (YYYY-MM-DD):").grid(row=0, column=2, padx=5, pady=5)
    fecha_entry = ctk.CTkEntry(filtros_frame, textvariable=fecha_var, width=150)
    fecha_entry.grid(row=0, column=3, padx=5, pady=5)

    # --- Tabla de ventas ---
    tabla_frame = ctk.CTkFrame(frame_destino)
    tabla_frame.pack(padx=10, pady=10, fill="both", expand=True)

    columnas = ("Comprobante", "Tipo de Transaccion", "Monto unitario", "Monto total", "Id Producto", "Producto", "Cliente", "Factura", "Cantidad", "Usuario", "Fecha")
    tree = ttk.Treeview(tabla_frame, columns=columnas, show="headings")

    # Configurar encabezados y columnas
    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=100)

    # --- Scroll vertical ---
    scrollbar_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.pack(side="right", fill="y")

    # --- Scroll horizontal ---
    scrollbar_x = ttk.Scrollbar(tabla_frame, orient="horizontal", command=tree.xview)
    tree.configure(xscrollcommand=scrollbar_x.set)
    scrollbar_x.pack(side="bottom", fill="x")

    tree.pack(fill="both", expand=True)

    # --- Función para cargar ventas ---
    def cargar_ventas():
        tree.delete(*tree.get_children())
        cliente_filtro = cliente_var.get().strip()
        fecha_filtro = fecha_var.get().strip()

        query = """
            SELECT v_comprob, v_tipotransacc, v_montous_unit, v_montous_total, v_id_producto, v_product, v_id_cliente, v_fact, v_cantidad, v_user, 
            TO_CHAR(v_fecha, 'DD/MM/YYYY HH24:MI:SS')
            FROM desarrollo.ventas
            WHERE 1=1
        """
        params = []

        if cliente_filtro:
            query += " AND v_id_cliente::text LIKE %s"
            params.append(f"%{cliente_filtro}%")
        if fecha_filtro:
            query += " AND TO_CHAR(v_fecha, 'DD/MM/YYYY HH24:MI:SS')::text LIKE %s"
            params.append(f"%{fecha_filtro}%")

        query += " ORDER BY v_fecha DESC"

        try:
            conn = conectar_db()
            cur = conn.cursor()
            cur.execute(query, params)
            for row in cur.fetchall():
                tree.insert("", "end", values=row)
            cur.close()
            conn.close()
        except Exception as e:
            ctk.CTkLabel(frame_destino, text=f"Error: {e}", text_color="red").pack()

    # Botón de búsqueda
    buscar_btn = ctk.CTkButton(filtros_frame, text="Buscar", command=cargar_ventas, fg_color="#FF9100", hover_color="#E07B00")
    buscar_btn.grid(row=0, column=4, padx=10)

    # Carga inicial
    cargar_ventas()

    # --- Botón para ver detalles ---
    def ver_detalle_venta():
        seleccionado = tree.selection()
        if not seleccionado:
            ctk.CTkLabel(frame_destino, text="Selecciona una venta para ver el detalle.", text_color="red").pack()
            return

        item = tree.item(seleccionado)
        id_venta = item["values"][0]

        detalle_win = ctk.CTkToplevel()
        detalle_win.title(f"Detalle de Venta #{id_venta}")
        detalle_win.geometry("500x400")
        detalle_win.lift()
        detalle_win.grab_set()

        detalle_tree = ttk.Treeview(detalle_win, columns=("Producto", "Cantidad", "Precio Unit", "Subtotal"), show="headings")
        for col in ("Producto", "Cantidad", "Precio Unit", "Subtotal"):
            detalle_tree.heading(col, text=col)
            detalle_tree.column(col, anchor="center")
        detalle_tree.pack(padx=10, pady=10, fill="both", expand=True)

        try:
            conn = conectar_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT p.descripcion, dv.cantidad, dv.precio_unit, (dv.cantidad * dv.precio_unit) as subtotal
                FROM desarrollo.detalle_ventas dv
                JOIN desarrollo.stock p ON dv.id_articulo = p.id_articulo
                WHERE dv.id_venta = %s
            """, (id_venta,))
            for row in cur.fetchall():
                detalle_tree.insert("", "end", values=row)
            cur.close()
            conn.close()
        except Exception as e:
            ctk.CTkLabel(detalle_win, text=f"Error: {e}", text_color="red").pack()

    acciones_frame = ctk.CTkFrame(frame_destino)
    acciones_frame.pack(pady=5)

    ctk.CTkButton(acciones_frame, text="Ver Detalle", command=ver_detalle_venta, fg_color="#4CAF50").pack(side="left", padx=10)
