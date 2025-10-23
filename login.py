# login.py
import customtkinter as ctk
from bd import conectar_db, establecer_usuario_app
from dashboard import abrir_dashboard
from tkinter import messagebox

def abrir_login():
    app = ctk.CTk()
    app.title("Inicio de Sesión")
    app.geometry("400x300")
    app.resizable(False, False)
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    
    # Centrar la ventana
    app.eval('tk::PlaceWindow . center')

    ctk.CTkLabel(app, text="Inicio de Sesión", font=("Arial", 20, "bold")).pack(pady=20)

    username_entry = ctk.CTkEntry(app, placeholder_text="Usuario", width=250, height=40)
    username_entry.pack(pady=10)

    password_entry = ctk.CTkEntry(app, placeholder_text="Contraseña", show="*", width=250, height=40)
    password_entry.pack(pady=10)

    def verificar():
        username = username_entry.get().strip()
        password = password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Campos vacíos", "Por favor completa todos los campos")
            return

        try:
            # Conexión siempre como postgres (como antes)
            conn = conectar_db()
            
            if conn:
                cursor = conn.cursor()

                # Verificar credenciales en tu tabla de usuarios
                cursor.execute("""
                    SELECT user_name
                    FROM desarrollo.usuarios
                    WHERE user_key = %s AND pass = %s AND user_active = 1
                """, (username, password))

                resultado = cursor.fetchone()
                cursor.close()

                if resultado:
                    nombre_usuario = resultado[0]
                    
                    # ✅ ESTABLECER VARIABLE DE SESIÓN PARA AUDITORÍA
                    if establecer_usuario_app(conn, username):
                        app.destroy()
                        # Pasar la conexión y el usuario al dashboard
                        abrir_dashboard(nombre_usuario, volver_al_login, conn, username)
                    else:
                        messagebox.showerror("Error", "No se pudo establecer sesión de auditoría")
                        conn.close()
                else:
                    conn.close()
                    messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar a la base de datos:\n{e}")

    def volver_al_login():
        abrir_login()

    ctk.CTkButton(
        app, 
        text="Iniciar Sesión", 
        command=verificar,
        fg_color="#FF9100", 
        hover_color="#E07B00", 
        cursor="hand2",
        width=250,
        height=40
    ).pack(pady=20)
    
    # Manejar la tecla Enter
    username_entry.bind("<Return>", lambda e: verificar())
    password_entry.bind("<Return>", lambda e: verificar())

    app.mainloop()

if __name__ == "__main__":
    abrir_login()