import customtkinter as ctk
from tkinter import ttk
from tkinter import messagebox
from bd import conectar_db
import datetime

# Variables globales para mantener estado en la pestaña de salida
current_user_id = None
current_product_id = None
current_barcode_real = None
current_stock_actual = 0       
current_prod_desc = ""
current_prod_price = 0
current_movimiento_id = None

def mostrar_movimientos(frame_destino, usuario_id_actual):
    # Limpiar frame anterior
    for widget in frame_destino.winfo_children():
        widget.destroy()

    # --- ESTILOS VISUALES ---
    style = ttk.Style()
    style.theme_use("clam")
    
    style.configure("Treeview",
                    background="white",
                    foreground="#2c3e50",
                    rowheight=30,
                    fieldbackground="white",
                    bordercolor="#dcdcdc",
                    borderwidth=0,
                    font=("Arial", 11))
    
    style.configure("Treeview.Heading",
                    background="#f1f2f6",
                    foreground="#34495e",
                    relief="flat",
                    font=("Arial", 11, "bold"))
    
    style.map("Treeview",
              background=[('selected', '#3498db')],
              foreground=[('selected', 'white')])

    # --- ESTRUCTURA PRINCIPAL ---
    ctk.CTkLabel(frame_destino, text="📦 Control de Movimientos", font=("Arial", 24, "bold"), text_color="#2c3e50").pack(pady=(20, 10))

    # TabView
    tabview = ctk.CTkTabview(frame_destino, width=900, height=600)
    tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # Crear pestañas
    tab_salida = tabview.add("📤 Registrar Salida")
    tab_garantia = tabview.add("🛡️ Verificar Garantía")

    # Configurar Grids
    tab_salida.grid_columnconfigure(0, weight=1)
    tab_salida.grid_rowconfigure(1, weight=1)
    
    tab_garantia.grid_columnconfigure(0, weight=1)
    tab_garantia.grid_rowconfigure(1, weight=1)

    # Inicializar pestañas pasando el usuario
    setup_pestana_salida(tab_salida, usuario_id_actual)
    setup_pestana_garantia(tab_garantia)


# ============================================================
# FUNCIONES AUXILIARES GLOBALES
# ============================================================
def obtener_resumen_global_stock():
    """Consulta el total de items y el valor total del inventario para mostrar al inicio"""
    try:
        conn = conectar_db()
        cur = conn.cursor()
        cur.execute("SELECT SUM(cant_inventario), SUM(cant_inventario * precio_unit) FROM desarrollo.stock")
        res = cur.fetchone()
        conn.close()
        
        total_cant = res[0] if res[0] else 0
        total_valor = res[1] if res[1] else 0
        
        return f"📊 Estado del Inventario: {total_cant:,.0f} unidades en total | Valorizado en: ${total_valor:,.0f}"
    except Exception as e:
        print(f"Error resumen stock: {e}")
        return "Esperando búsqueda..."

# ============================================================
# LÓGICA PESTAÑA 1: SALIDA DE ARTÍCULOS
# ============================================================
def setup_pestana_salida(parent, usuario_recibido):
    global current_user_id
    current_user_id = usuario_recibido

    # --- FUNCIÓN DE VALIDACIÓN PARA EL CAMPO CANTIDAD ---
    def validar_cantidad(new_value):
        """Impide escribir un número mayor al stock disponible"""
        if not new_value: return True # Permitir borrar todo
        try:
            cant_ingresada = int(new_value)
            # Si hay un producto cargado y la cantidad supera el stock, bloqueamos la entrada
            if current_stock_actual > 0 and cant_ingresada > current_stock_actual:
                # Opcional: Feedback visual rápido (parpadeo rojo)
                entry_cant.configure(text_color="red")
                parent.after(200, lambda: entry_cant.configure(text_color="black"))
                return False 
            
            entry_cant.configure(text_color="black")
            return True
        except ValueError:
            return False # No es un número, bloquear

    # Registramos la función de validación en Tkinter
    vcmd = (parent.register(validar_cantidad), '%P')


    # --- SECCIÓN SUPERIOR: BUSCADOR PRODUCTO ---
    search_frame = ctk.CTkFrame(parent, fg_color="transparent")
    search_frame.grid(row=0, column=0, sticky="ew", pady=10)

    ctk.CTkLabel(search_frame, text="Escriba el Nombre del producto:", font=("Arial", 12, "bold")).pack(side="left", padx=10)
    
    entry_buscar = ctk.CTkEntry(search_frame, placeholder_text="Buscar producto...", width=300)
    entry_buscar.pack(side="left", padx=5)
    
    # FRAMES FLOTANTES DE SUGERENCIAS
    suggestion_frame = ctk.CTkScrollableFrame(parent, width=400, height=200, fg_color="white", corner_radius=10, border_width=1, border_color="gray")
    suggestion_frame_cliente = ctk.CTkScrollableFrame(parent, width=300, height=150, fg_color="white", corner_radius=10, border_width=1, border_color="gray")

    # --- FORMULARIO ---
    form_frame = ctk.CTkFrame(parent, fg_color="white", corner_radius=10)
    form_frame.grid(row=1, column=0, sticky="new", padx=10, pady=10) 

    # Variables
    # Usamos la nueva función para el texto inicial
    var_prod_info = ctk.StringVar(value="Esperando búsqueda...")
    var_cantidad = ctk.StringVar(value="1")
    var_motivo = ctk.StringVar()
    var_cliente = ctk.StringVar()
    var_cod_manual = ctk.StringVar()

    # Layout
    lbl_info = ctk.CTkLabel(form_frame, textvariable=var_prod_info, font=("Arial", 16, "bold"), text_color="gray", height=40)
    lbl_info.grid(row=0, column=0, columnspan=4, sticky="ew", padx=20, pady=10)
    
    ttk.Separator(form_frame, orient="horizontal").grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(form_frame, text="Cantidad:", font=("Arial", 12)).grid(row=2, column=0, padx=20, pady=10, sticky="e")
    
    # APLICAMOS LA VALIDACIÓN AL ENTRY DE CANTIDAD
    entry_cant = ctk.CTkEntry(form_frame, textvariable=var_cantidad, width=100, state="disabled",
                              validate="key", validatecommand=vcmd) # <--- AQUÍ ESTÁ LA MAGIA
    entry_cant.grid(row=2, column=1, padx=10, pady=10, sticky="w")

    ctk.CTkLabel(form_frame, text="Motivo:", font=("Arial", 12)).grid(row=2, column=2, padx=20, pady=10, sticky="e")
    motivos = ["VENTA", "USO INTERNO", "OTRO"]
    combo_motivo = ttk.Combobox(form_frame, textvariable=var_motivo, values=motivos, state="disabled", width=25)
    combo_motivo.grid(row=2, column=3, padx=10, pady=10, sticky="w")

    ctk.CTkLabel(form_frame, text="Cliente:", font=("Arial", 12)).grid(row=3, column=0, padx=20, pady=10, sticky="e")
    entry_cliente = ctk.CTkEntry(form_frame, textvariable=var_cliente, width=200, state="disabled", placeholder_text="Buscar cliente...")
    entry_cliente.grid(row=3, column=1, padx=10, pady=10, sticky="w")

    # --- CAMBIO: Etiqueta naranja y placeholder de Serial ---
    ctk.CTkLabel(form_frame, text="Nro. Serial / S.N.:", font=("Arial", 12, "bold"), text_color="#d35400").grid(row=3, column=2, padx=20, pady=10, sticky="e")
    entry_cod_manual = ctk.CTkEntry(form_frame, textvariable=var_cod_manual, width=200, state="disabled", placeholder_text="🔍 Escanee Serial Único")
    entry_cod_manual.grid(row=3, column=3, padx=10, pady=10, sticky="w")

    btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
    btn_frame.grid(row=4, column=0, columnspan=4, pady=20)

    # --- FUNCIONES AUXILIARES INTERNAS ---
    
    def limpiar_form_salida(borrar_busqueda=True):
        global current_product_id, current_stock_actual
        current_product_id = None
        current_stock_actual = 0
        
        # --- CAMBIO AQUÍ: Volvemos al texto simple ---
        var_prod_info.set("Esperando búsqueda...")
        # ---------------------------------------------
        
        var_cantidad.set("1")
        var_motivo.set("")
        var_cliente.set("")
        var_cod_manual.set("")
        
        lbl_info.configure(text_color="gray")
        entry_cant.configure(state="disabled", text_color="black")
        combo_motivo.configure(state="disabled")
        entry_cliente.configure(state="disabled")
        entry_cod_manual.configure(state="disabled")
        btn_registrar.configure(state="disabled")
        
        suggestion_frame.place_forget()
        suggestion_frame_cliente.place_forget()
        
        if borrar_busqueda:
            entry_buscar.delete(0, "end")
        entry_buscar.focus()

    def cargar_datos_producto(datos):
        global current_product_id, current_barcode_real, current_stock_actual, current_prod_desc, current_prod_price
        
        current_product_id = datos[0]
        desc = datos[1]
        stock = datos[2]
        precio = datos[3]
        current_barcode_real = datos[4] if datos[4] else "" # Lo guardamos pero no lo mostramos en el campo manual
        
        current_stock_actual = stock
        current_prod_desc = desc
        current_prod_price = precio

        # Actualizamos variables visuales
        var_prod_info.set(f"{desc} | Stock: {stock} | ${precio:,.0f}")
        lbl_info.configure(text_color="#2c3e50")
        entry_buscar.delete(0, "end"); entry_buscar.insert(0, str(desc))
        suggestion_frame.place_forget()

        # Habilitar campos
        entry_cant.configure(state="normal"); var_cantidad.set("1")
        combo_motivo.configure(state="readonly"); var_motivo.set("VENTA")
        entry_cliente.configure(state="normal")
        
        # --- CAMBIO CLAVE: Dejar campo Serial vacío y poner foco ---
        entry_cod_manual.configure(state="normal")
        var_cod_manual.set("") # Vacío para obligar el escaneo
        entry_cod_manual.focus() # El cursor salta directo aquí
        # ---------------------------------------------------------
        
        btn_registrar.configure(state="normal", command=ejecutar_salida)

    def seleccionar_producto_modal(resultados):
        modal = ctk.CTkToplevel()
        modal.title("Seleccione Producto")
        modal.geometry("650x400")
        modal.transient(parent.winfo_toplevel()) 
        modal.grab_set()
        modal.geometry("+%d+%d" % (modal.winfo_screenwidth()/2 - 325, modal.winfo_screenheight()/2 - 200))

        ctk.CTkLabel(modal, text="⚠️ Se encontraron varios productos. Haga doble clic en uno:", font=("Arial", 14, "bold")).pack(pady=10)

        frame_tabla = ctk.CTkFrame(modal)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)

        cols = ("ID", "Producto", "Stock", "Precio")
        tree_sel = ttk.Treeview(frame_tabla, columns=cols, show="headings")
        tree_sel.heading("ID", text="ID"); tree_sel.column("ID", width=60, anchor="center")
        tree_sel.heading("Producto", text="Producto"); tree_sel.column("Producto", width=300, anchor="w")
        tree_sel.heading("Stock", text="Stock"); tree_sel.column("Stock", width=60, anchor="center")
        tree_sel.heading("Precio", text="Precio"); tree_sel.column("Precio", width=100, anchor="center")
        
        scroll = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree_sel.yview)
        tree_sel.configure(yscrollcommand=scroll.set)
        tree_sel.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for res in resultados:
            tree_sel.insert("", "end", values=(res[0], res[1], res[2], f"${res[3]:,.0f}"), tags=(res[0],)) 

        def on_double_click(event):
            item = tree_sel.selection()
            if not item: return
            val = tree_sel.item(item[0], "values")
            id_selec = int(val[0])
            dato_completo = next((r for r in resultados if r[0] == id_selec), None)
            if dato_completo:
                modal.destroy()
                cargar_datos_producto(dato_completo)

        tree_sel.bind("<Double-1>", on_double_click)
        ctk.CTkButton(modal, text="Cancelar", fg_color="gray", command=modal.destroy).pack(pady=10)

    # --- LÓGICA DE BÚSQUEDA Y SUGERENCIAS ---
    def seleccionar_sugerencia(id_prod):
        suggestion_frame.place_forget()
        try:
            conn = conectar_db()
            cur = conn.cursor()
            query = """
                SELECT DISTINCT ON (s.id_articulo) 
                    s.id_articulo, s.descripcion, s.cant_inventario, s.precio_unit, m.serial
                FROM desarrollo.stock s
                LEFT JOIN desarrollo.movimientos m ON s.id_articulo = m.id_producto
                WHERE s.id_articulo = %s
                ORDER BY s.id_articulo, m.fecha_entrega DESC
            """
            cur.execute(query, (id_prod,))
            res = cur.fetchone()
            conn.close()
            if res: cargar_datos_producto(res)
        except Exception as e: print(e)

    def actualizar_sugerencias(event):
        texto = entry_buscar.get().strip()
        if len(texto) < 2:
            suggestion_frame.place_forget()
            return

        for widget in suggestion_frame.winfo_children(): widget.destroy()

        try:
            conn = conectar_db()
            cur = conn.cursor()
            # 🚀 MEJORA: Ahora también busca mientras escribes/escaneas el código de barras
            cur.execute("""
                SELECT id_articulo, descripcion 
                FROM desarrollo.stock 
                WHERE descripcion ILIKE %s OR id_articulo::text ILIKE %s OR codigo_barras ILIKE %s 
                LIMIT 8
            """, (f"%{texto}%", f"{texto}%", f"{texto}%"))
            resultados = cur.fetchall()
            conn.close()

            if resultados:
                suggestion_frame.place(x=280, y=55)
                suggestion_frame.lift()
                for id_art, desc in resultados:
                    btn = ctk.CTkButton(suggestion_frame, text=f"{desc}", anchor="w", fg_color="transparent", text_color="black", hover_color="#e0e0e0", height=25, command=lambda i=id_art: seleccionar_sugerencia(i))
                    btn.pack(fill="x", pady=1)
            else:
                suggestion_frame.place_forget()
        except: pass

    def seleccionar_cliente_sugerido(nombre_cliente):
        entry_cliente.delete(0, "end")
        entry_cliente.insert(0, nombre_cliente)
        suggestion_frame_cliente.place_forget()

    def actualizar_sugerencias_cliente(event):
        texto = entry_cliente.get().strip()
        if entry_cliente.cget("state") == "disabled" or len(texto) < 2:
            suggestion_frame_cliente.place_forget()
            return

        for widget in suggestion_frame_cliente.winfo_children(): widget.destroy()

        try:
            conn = conectar_db()
            cur = conn.cursor()
            # Ajustado a tu columna 'nombre'
            query = "SELECT nombre FROM desarrollo.clientes WHERE nombre ILIKE %s OR id_cliente::text ILIKE %s LIMIT 5"
            cur.execute(query, (f"%{texto}%", f"{texto}%"))
            resultados = cur.fetchall()
            conn.close()

            if resultados:
                suggestion_frame_cliente.place(x=150, y=240) 
                suggestion_frame_cliente.lift()
                for row in resultados:
                    nombre_encontrado = row[0]
                    btn = ctk.CTkButton(suggestion_frame_cliente, text=nombre_encontrado, anchor="w", 
                                        fg_color="transparent", text_color="black", hover_color="#e0e0e0", height=25,
                                        command=lambda n=nombre_encontrado: seleccionar_cliente_sugerido(n))
                    btn.pack(fill="x", pady=1)
            else:
                suggestion_frame_cliente.place_forget()
        except: suggestion_frame_cliente.place_forget()

    def buscar_prod(event=None):
        criterio = entry_buscar.get().strip()
        if not criterio: return
        suggestion_frame.place_forget()

        try:
            conn = conectar_db()
            cur = conn.cursor()
            # 🚀 MEJORA: Agregamos "OR s.codigo_barras = %s" para encontrar el producto exacto al escanear
            query = """
                SELECT DISTINCT ON (s.id_articulo) 
                    s.id_articulo, s.descripcion, s.cant_inventario, s.precio_unit, m.serial
                FROM desarrollo.stock s
                LEFT JOIN desarrollo.movimientos m ON s.id_articulo = m.id_producto
                WHERE s.id_articulo::text = %s OR m.serial::text = %s OR s.descripcion ILIKE %s OR s.codigo_barras = %s
                ORDER BY s.id_articulo, m.fecha_entrega DESC LIMIT 50
            """
            cur.execute(query, (criterio, criterio, f"%{criterio}%", criterio))
            resultados = cur.fetchall()
            conn.close()

            if not resultados:
                lbl_info.configure(text=f"❌ Sin resultados", text_color="red")
                limpiar_form_salida(borrar_busqueda=False)
            elif len(resultados) == 1:
                cargar_datos_producto(resultados[0])
            else:
                seleccionar_producto_modal(resultados)
        except Exception as e: messagebox.showerror("Error", str(e))

    # --- EJECUCIÓN FINAL ---
    def ejecutar_salida():
        # 🛡️ FIX 1: Bloqueamos el botón para evitar doble-clic rápido
        btn_registrar.configure(state="disabled")
        
        global current_user_id, current_product_id, current_stock_actual
        if not current_user_id: 
            messagebox.showerror("Error", "Usuario no identificado")
            btn_registrar.configure(state="normal"); return
        
        cant_str = var_cantidad.get()
        motivo = var_motivo.get()
        cliente = var_cliente.get().strip()
        serial_manual = var_cod_manual.get().strip()
        termino_busqueda = entry_buscar.get().strip() 

        if not motivo: 
            messagebox.showwarning("Falta dato", "Seleccione un motivo")
            btn_registrar.configure(state="normal"); return
            
        if not cliente: 
            messagebox.showwarning("Falta dato", "El campo 'Cliente' es obligatorio.")
            entry_cliente.focus()
            btn_registrar.configure(state="normal"); return

        try:
            cant = int(cant_str)
            if cant <= 0: raise ValueError
        except: 
            messagebox.showwarning("Error", "Cantidad inválida")
            btn_registrar.configure(state="normal"); return

        # =======================================================
        # 1. FUNCIONES AUXILIARES INTERNAS (Para guardar y validar)
        # =======================================================
        def procesar_guardado_db(conn, cur, cant_total, lista_seriales, stock_db):
            try:
                for serial in lista_seriales:
                    cur.execute("""
                        INSERT INTO desarrollo.movimientos (id_producto, tipo_movimiento, cantidad, motivo, id_usuario, serial, cliente, fecha_entrega)
                        VALUES (%s, 'SALIDA', 1, %s, %s, %s, %s, NOW())
                    """, (current_product_id, motivo, current_user_id, serial, cliente))

                cur.execute("""
                    UPDATE desarrollo.stock SET cant_inventario = cant_inventario - %s, precio_total = precio_unit * (cant_inventario - %s)
                    WHERE id_articulo = %s
                """, (cant_total, cant_total, current_product_id))
                
                conn.commit()
                conn.close()
                
                # 🛡️ FIX 2: Usamos tu función para resetear TODO el formulario
                limpiar_form_salida(borrar_busqueda=True)
                cargar_tabla_historial()
                messagebox.showinfo("Éxito", f"Se registraron {cant_total} salidas correctamente.")
                
            except Exception as e:
                messagebox.showerror("Error DB", str(e))
                btn_registrar.configure(state="normal") # Reactivar si falla la BD

        def recolectar_multiples_seriales(cantidad_total, primer_serial, stock_db):
            seriales = []
            if primer_serial:
                seriales.append(primer_serial)

            modal = ctk.CTkToplevel()
            modal.title("Escaneo Múltiple de Productos")
            modal.geometry("500x450")
            modal.transient(parent.winfo_toplevel())
            modal.grab_set()
            modal.geometry("+%d+%d" % (modal.winfo_screenwidth()/2 - 250, modal.winfo_screenheight()/2 - 225))

            # 🛡️ FIX 3: Si el usuario cierra la ventana manual con la 'X', reactivamos el botón
            def cancelar_modal():
                modal.destroy()
                btn_registrar.configure(state="normal")
            modal.protocol("WM_DELETE_WINDOW", cancelar_modal)

            ctk.CTkLabel(modal, text=f"Se requieren {cantidad_total} códigos", font=("Arial", 18, "bold")).pack(pady=(20, 5))
            
            lbl_contador = ctk.CTkLabel(modal, text=f"📦 Escaneados: {len(seriales)} de {cantidad_total}", font=("Arial", 14), text_color="#3498db")
            lbl_contador.pack(pady=5)

            entry_scan = ctk.CTkEntry(modal, width=300, placeholder_text="Escanee el siguiente producto aquí...", font=("Arial", 14))
            entry_scan.pack(pady=10)
            entry_scan.focus()

            lista_scans = ctk.CTkTextbox(modal, width=350, height=200, font=("Consolas", 12))
            lista_scans.pack(pady=10)
            if primer_serial:
                lista_scans.insert("end", f"1. {primer_serial}\n")

            def registrar_scan(event):
                codigo = entry_scan.get().strip()
                if not codigo: return

                conn_val = conectar_db()
                cur_val = conn_val.cursor()
                cur_val.execute("""
                    SELECT s.descripcion, m.fecha_entrega 
                    FROM desarrollo.movimientos m
                    JOIN desarrollo.stock s ON m.id_producto = s.id_articulo
                    WHERE m.serial = %s AND m.tipo_movimiento = 'SALIDA'
                """, (codigo,))
                ya_vendido = cur_val.fetchone()
                conn_val.close()

                if ya_vendido:
                    fecha_str = ya_vendido[1].strftime("%d/%m/%Y %H:%M")
                    messagebox.showerror("❌ ERROR DE INVENTARIO", 
                                         f"Este producto YA FUE VENDIDO.\n\nProducto: {ya_vendido[0]}\nFecha: {fecha_str}")
                    entry_scan.delete(0, "end")
                    return

                if codigo in seriales:
                    messagebox.showwarning("Duplicado", "Ya escaneó esta unidad en este lote. Escanee otra distinta.")
                    entry_scan.delete(0, "end")
                    return

                seriales.append(codigo)
                lista_scans.insert("end", f"{len(seriales)}. {codigo}\n")
                entry_scan.delete(0, "end")
                lbl_contador.configure(text=f"📦 Escaneados: {len(seriales)} de {cantidad_total}")

                if len(seriales) == cantidad_total:
                    entry_scan.configure(state="disabled") # Bloquea el campo para evitar que el usuario siga escaneando
                    modal.destroy()
                    conn_fin = conectar_db()
                    cur_fin = conn_fin.cursor()
                    procesar_guardado_db(conn_fin, cur_fin, cantidad_total, seriales, stock_db)

            entry_scan.bind("<Return>", registrar_scan)

        # =======================================================
        # 2. LÓGICA PRINCIPAL DE LA FUNCIÓN
        # =======================================================
        try:
            conn = conectar_db()
            cur = conn.cursor()
            
            cur.execute("SELECT cant_inventario, codigo_barras FROM desarrollo.stock WHERE id_articulo = %s", (current_product_id,))
            res_stock = cur.fetchone()
            stock_db = res_stock[0]
            codigo_barras_db = res_stock[1]

            if cant > stock_db:
                messagebox.showerror("Error", f"Stock insuficiente. Stock actual: {stock_db}")
                conn.close()
                btn_registrar.configure(state="normal"); return

            # Magia UX
            if not serial_manual and termino_busqueda == codigo_barras_db:
                serial_manual = termino_busqueda
                var_cod_manual.set(serial_manual)

            # Validación del primer serial
            if serial_manual:
                cur.execute("""
                    SELECT s.descripcion, m.fecha_entrega 
                    FROM desarrollo.movimientos m
                    JOIN desarrollo.stock s ON m.id_producto = s.id_articulo
                    WHERE m.serial = %s AND m.tipo_movimiento = 'SALIDA'
                """, (serial_manual,))
                ya_vendido = cur.fetchone()
                
                if ya_vendido:
                    fecha_str = ya_vendido[1].strftime("%d/%m/%Y %H:%M")
                    messagebox.showerror("❌ ERROR DE INVENTARIO", 
                                         f"El Serial escaneado YA FUE VENDIDO.\n\nProducto: {ya_vendido[0]}\nFecha: {fecha_str}")
                    var_cod_manual.set("")
                    entry_cod_manual.focus()
                    conn.close()
                    btn_registrar.configure(state="normal"); return

            conn.close()

            if cant == 1:
                if not serial_manual:
                    messagebox.showwarning("Falta Serial", "⚠️ Escanee el código de la caja en el campo 'Nro. Serial'.")
                    entry_cod_manual.focus()
                    btn_registrar.configure(state="normal"); return
                    
                conn_directo = conectar_db()
                cur_directo = conn_directo.cursor()
                procesar_guardado_db(conn_directo, cur_directo, cant, [serial_manual], stock_db)
            else:
                recolectar_multiples_seriales(cant, serial_manual, stock_db)

        except Exception as e:
            messagebox.showerror("Error general", str(e))
            btn_registrar.configure(state="normal")

    # --- BOTONES ---
    btn_registrar = ctk.CTkButton(btn_frame, text="CONFIRMAR SALIDA", fg_color="#2ecc71", hover_color="#27ae60", 
                                  font=("Arial", 14, "bold"), width=200, height=40, state="disabled")
    btn_registrar.pack(side="left", padx=10)

    btn_limpiar = ctk.CTkButton(btn_frame, text="Cancelar / Limpiar", fg_color="#95a5a6", width=120, height=40,
                                command=lambda: limpiar_form_salida())
    btn_limpiar.pack(side="left", padx=10)

    # --- HISTORIAL (TABLA) ---
    hist_frame = ctk.CTkFrame(parent, fg_color="white", corner_radius=10)
    hist_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(10, 0))
    hist_frame.grid_rowconfigure(0, weight=1); hist_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(hist_frame, text="Últimos Movimientos", font=("Arial", 12, "bold")).place(x=15, y=5)

    ctk.CTkLabel(hist_frame, text="Últimos Movimientos", font=("Arial", 12, "bold")).place(x=15, y=5)
    cols = ("ID", "Fecha", "Producto", "Motivo", "Cliente", "Serial (S/N)")
    tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=5)
    
    tree.heading("ID", text="ID"); tree.column("ID", width=40, anchor="center")
    tree.heading("Fecha", text="Fecha"); tree.column("Fecha", width=110, anchor="center")
    tree.heading("Producto", text="Producto"); tree.column("Producto", width=200)
    tree.heading("Motivo", text="Motivo"); tree.column("Motivo", width=70, anchor="center")
    tree.heading("Cliente", text="Cliente"); tree.column("Cliente", width=100)
    tree.heading("Serial (S/N)", text="Serial (S/N)"); tree.column("Serial (S/N)", width=100, anchor="center")
    
    tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=(30, 5))

    def cargar_tabla_historial():
        for i in tree.get_children(): tree.delete(i)
        try:
            conn = conectar_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT m.id_movimiento, TO_CHAR(m.fecha_entrega, 'DD/MM/YYYY HH24:MI'), 
                       s.descripcion, m.motivo, m.cliente, m.serial
                FROM desarrollo.movimientos m
                JOIN desarrollo.stock s ON m.id_producto = s.id_articulo
                WHERE m.tipo_movimiento = 'SALIDA'
                ORDER BY m.fecha_entrega DESC LIMIT 10
            """)
            for row in cur.fetchall(): tree.insert("", "end", values=row)
            conn.close()
        except: pass

    # --- BINDINGS ---
    entry_buscar.bind("<KeyRelease>", actualizar_sugerencias)
    entry_buscar.bind("<Return>", buscar_prod)
    entry_cliente.bind("<KeyRelease>", actualizar_sugerencias_cliente)
    ctk.CTkButton(search_frame, text="Buscar", width=80, command=buscar_prod).pack(side="left", padx=5)
    
    cargar_tabla_historial()
        
        
# ============================================================
# LÓGICA PESTAÑA 2: GARANTÍAS (CON GESTIÓN DE CAMBIOS)
# ============================================================
def setup_pestana_garantia(parent):
    
    # Variables locales para manejar el movimiento seleccionado
    current_movimiento_id = None 
    
    # --- HEADER BÚSQUEDA ---
    head_frame = ctk.CTkFrame(parent, fg_color="transparent")
    head_frame.grid(row=0, column=0, sticky="ew", pady=20)

    ctk.CTkLabel(head_frame, text="🔍 Escanear Serial / Código del Producto:", font=("Arial", 14)).pack()
    entry_scan = ctk.CTkEntry(head_frame, placeholder_text="Escanee aquí...", width=300, height=40, font=("Arial", 16))
    entry_scan.pack(pady=10)
    
    # --- ÁREA DE RESULTADO ---
    result_frame = ctk.CTkFrame(parent, fg_color="white", corner_radius=15)
    result_frame.grid(row=1, column=0, sticky="nsew", padx=40, pady=10)
    result_frame.grid_columnconfigure(0, weight=1)

    # Etiquetas de Estado
    lbl_status = ctk.CTkLabel(result_frame, text="ESPERANDO ESCANEO...", font=("Arial", 24, "bold"), text_color="gray")
    lbl_status.pack(pady=(30, 5))

    lbl_detalles = ctk.CTkLabel(result_frame, text="", font=("Arial", 14), text_color="#2c3e50")
    lbl_detalles.pack(pady=5)
    
    # --- BOTÓN DE ACCIÓN (CAMBIO) ---
    # Lo creamos oculto y solo lo mostramos si es necesario
    btn_cambiar = ctk.CTkButton(result_frame, text="🔄 PROCESAR CAMBIO POR GARANTÍA", 
                                fg_color="#d35400", hover_color="#e67e22",
                                font=("Arial", 14, "bold"), height=40, state="disabled")
    
    # --- TABLA DE DETALLES ---
    cols = ("Fecha Movimiento", "Cliente", "Vendedor", "Vence", "¿Cambiado?")
    tree_hist = ttk.Treeview(result_frame, columns=cols, show="headings", height=3)
    
    tree_hist.heading("Fecha Movimiento", text="Fecha Movimiento"); tree_hist.column("Fecha Movimiento", width=120, anchor="center")
    tree_hist.heading("Cliente", text="Cliente"); tree_hist.column("Cliente", width=150, anchor="center")
    tree_hist.heading("Vendedor", text="Vendedor"); tree_hist.column("Vendedor", width=100, anchor="center")
    tree_hist.heading("Vence", text="Vencimiento"); tree_hist.column("Vence", width=100, anchor="center")
    tree_hist.heading("¿Cambiado?", text="¿Cambiado?"); tree_hist.column("¿Cambiado?", width=80, anchor="center")

    # --- LÓGICA DE PROCESAR CAMBIO ---
    def procesar_cambio():
        nonlocal current_movimiento_id
        if not current_movimiento_id: return
        
        confirm = messagebox.askyesno("Confirmar Garantía", 
                                      "¿Está seguro de marcar este producto como CAMBIADO?\n\n"
                                      "Esto actualizará el movimiento original indicando que se entregó otro producto.")
        if not confirm: return

        try:
            conn = conectar_db()
            cur = conn.cursor()
            # Actualizamos el campo de cambio y la fecha
            cur.execute("""
                UPDATE desarrollo.movimientos 
                SET cambiado_por_garantia = 'SI', 
                    fecha_cambio = NOW()
                WHERE id_movimiento = %s
            """, (current_movimiento_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Éxito", "Cambio registrado correctamente.")
            consultar_garantia() # Recargar para ver los cambios

        except Exception as e:
            messagebox.showerror("Error DB", str(e))

    btn_cambiar.configure(command=procesar_cambio)

    # --- LÓGICA DE CONSULTA ---
    def consultar_garantia(event=None):
        nonlocal current_movimiento_id
        codigo = entry_scan.get().strip()
        
        if not codigo: return

        # Reset visual
        lbl_status.configure(text="BUSCANDO...", text_color="blue")
        lbl_detalles.configure(text="")
        for i in tree_hist.get_children(): tree_hist.delete(i)
        tree_hist.pack_forget()
        btn_cambiar.pack_forget()
        current_movimiento_id = None

        try:
            conn = conectar_db()
            cur = conn.cursor()
            
            # --- QUERY MEJORADA: Formateamos las 3 fechas directamente con TO_CHAR ---
            query = """
                SELECT 
                    m.id_movimiento,
                    p.descripcion,
                    TO_CHAR(m.fecha_entrega, 'DD/MM/YYYY HH24:MI:SS'), -- Fecha Venta
                    g.gar_duracion, 
                    TO_CHAR((m.fecha_entrega + (g.gar_duracion || ' months')::interval), 'DD/MM/YYYY HH24:MI:SS') AS fecha_vencimiento,
                    CASE 
                        WHEN (m.fecha_entrega + (g.gar_duracion || ' months')::interval) >= CURRENT_DATE THEN 'VIGENTE'
                        ELSE 'VENCIDA'
                    END as estado_tiempo,
                    m.cliente,
                    u.user_name,           -- Vendedor
                    m.cambiado_por_garantia, -- Estado (SI/NO)
                    m.serial,           -- Serial
                    TO_CHAR(m.fecha_cambio, 'DD/MM/YYYY HH24:MI:SS') -- Fecha del cambio
                FROM desarrollo.movimientos m
                JOIN desarrollo.stock p ON m.id_producto = p.id_articulo
                LEFT JOIN desarrollo.garantias g ON p.categoria = g.gar_categoria
                LEFT JOIN desarrollo.usuarios u ON m.id_usuario = u.user_key
                WHERE m.serial = %s AND m.tipo_movimiento = 'SALIDA'
                ORDER BY m.fecha_entrega DESC
                LIMIT 1
            """
            cur.execute(query, (codigo,))
            res = cur.fetchone()
            conn.close()

            if res:
                current_movimiento_id = res[0]
                prod_nombre = res[1]
                fecha_venta = res[2] # Ya viene formateada
                duracion = res[3] if res[3] else 0
                fecha_vence = res[4] # Ya viene formateada
                estado_tiempo = res[5]
                cliente = res[6] if res[6] else "C. Final"
                vendedor = res[7] if res[7] else "Desconocido"
                ya_cambiado = res[8] if res[8] else "NO"
                serial = res[9]
                fecha_cambio_str = res[10] # Ya viene formateada

                # --- LÓGICA DE FORMATO PARA LA TABLA ---
                texto_cambiado = ya_cambiado
                info_extra = ""
                
                if ya_cambiado == 'SI' and fecha_cambio_str:
                    # Usamos directamente la fecha que nos dio SQL
                    texto_cambiado = f"SI ({fecha_cambio_str})"

                # --- LÓGICA DE ESTADOS Y BOTÓN ---
                if ya_cambiado == 'SI':
                    lbl_status.configure(text="⚠️ GARANTÍA YA UTILIZADA", text_color="#e67e22")
                    info_extra = f"\nCambio realizado el: {fecha_cambio_str}"
                    btn_cambiar.pack_forget() 
                elif estado_tiempo == 'VIGENTE':
                    lbl_status.configure(text="✅ GARANTÍA VIGENTE", text_color="#27ae60")
                    info_extra = ""
                    btn_cambiar.configure(state="normal")
                    btn_cambiar.pack(pady=10)
                else:
                    lbl_status.configure(text="❌ GARANTÍA VENCIDA", text_color="#c0392b")
                    info_extra = ""
                    btn_cambiar.pack_forget()

                detalle_txt = (f"Producto: {prod_nombre}\n"
                               f"Serial: {serial}\n"
                               f"Duración: {duracion} meses\n"
                               f"Vencimiento: {fecha_vence}"
                               f"{info_extra}")
                
                lbl_detalles.configure(text=detalle_txt)

                # Mostrar tabla con el texto compuesto
                tree_hist.pack(fill="x", padx=20, pady=10)
                tree_hist.insert("", "end", values=(fecha_venta, cliente, vendedor, fecha_vence, texto_cambiado))

            else:
                lbl_status.configure(text="⚠️ NO ENCONTRADO", text_color="#f39c12")
                lbl_detalles.configure(text=f"No existe venta registrada para el serial:\n{codigo}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    entry_scan.bind("<Return>", consultar_garantia)
    ctk.CTkButton(head_frame, text="Consultar", command=consultar_garantia).pack(pady=5)