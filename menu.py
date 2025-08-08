import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import pandas as pd

# ⚙️ Configuración de base de datos
DB_HOST = 'localhost'
#DB_PORT = '5432'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = '123'

class AppVentas(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Ventas")
        self.geometry("800x400")
        
        # Botón para cargar datos
        btn_cargar = ttk.Button(self, text="Cargar Ventas", command=self.cargar_datos)
        btn_cargar.pack(pady=10)

        # Tabla para mostrar datos
        self.tabla = ttk.Treeview(self, columns=("Id del Producto", "Nombre del Producto", "Precio", "Cantidad"), show="headings")
        self.tabla.heading("Id del Producto", text="ID")
        self.tabla.heading("Nombre del Producto", text="Nombre del Producto")
        self.tabla.heading("Precio", text="Precio")
        self.tabla.heading("Cantidad", text="Cantidad")
        self.tabla.pack(expand=True, fill="both")

    def cargar_datos(self):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                #port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            query = "SELECT id_articulo, descripcion, precio_unit, cant_inventario FROM desarrollo.stock ORDER BY id_articulo DESC LIMIT 50;"
            df = pd.read_sql(query, conn)
            conn.close()

            # Limpiar tabla antes de insertar nuevos datos
            for fila in self.tabla.get_children():
                self.tabla.delete(fila)

            # Insertar datos en la tabla
            for _, row in df.iterrows():
                self.tabla.insert("", "end", values=(row['id_articulo'], row['descripcion'], row['precio_unit'], row['cant_inventario']))

        except Exception as e:
            messagebox.showerror("Error de conexión", f"No se pudo conectar a la base de datos:\n{e}")

# Ejecutar aplicación
if __name__ == "__main__":
    app = AppVentas()
    app.mainloop()
