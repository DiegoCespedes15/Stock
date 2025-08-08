# login.py
import customtkinter as ctk
from bd import conectar_db
from dashboard import abrir_dashboard
from tkinter import messagebox

def abrir_login():
    app = ctk.CTk()
    app.title("Inicio de Sesión")
    app.geometry("400x300")
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    ctk.CTkLabel(app, text="Inicio de Sesión", font=("Arial", 20)).pack(pady=20)

    username_entry = ctk.CTkEntry(app, placeholder_text="Usuario")
    username_entry.pack(pady=10)

    password_entry = ctk.CTkEntry(app, placeholder_text="Contraseña", show="*")
    password_entry.pack(pady=10)

    def verificar():
        username = username_entry.get()
        password = password_entry.get()

        if not username or not password:
            messagebox.showwarning("Campos vacíos", "Por favor completa todos los campos")
            return

        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desarrollo.usuarios WHERE user_key = %s AND pass = %s", (username, password))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()

            if resultado:
                app.destroy()  # Cierra la ventana 
                abrir_dashboard()
            else:
                messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar a la base de datos:\n{e}")

    ctk.CTkButton(app, text="Iniciar Sesión", command=verificar,fg_color="#FF9100", hover_color="#E07B00", cursor="hand2").pack(pady=20)
    app.mainloop()
