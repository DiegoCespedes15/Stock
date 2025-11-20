# bd.py
import psycopg2

DB_CONFIG = {
    'dbname': 'postgres',    
    'user': 'postgres',       
    'password': '123',        
    'host': 'localhost',
}

def conectar_db(usuario_app=None):
    """
    Conecta a la base de datos y establece el usuario de aplicación si se proporciona
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Si se proporciona un usuario de aplicación, establecerlo en la sesión
        if usuario_app:
            establecer_usuario_app(conn, usuario_app)
            
        return conn
    except Exception as e:
        print("Error al conectar a la base de datos:", e)
        return None

def establecer_usuario_app(conn, usuario_app):
    """
    Establece el usuario de la aplicación en la variable de sesión de PostgreSQL
    """
    try:
        cursor = conn.cursor()
        # Método más robusto - ejecutar en la misma transacción
        cursor.execute("SELECT set_config('app.usuario', %s, false)", (usuario_app,))
        conn.commit()
        cursor.close()
        print(f"✅ Usuario de aplicación establecido: {usuario_app}")
        return True
    except Exception as e:
        print("❌ Error estableciendo usuario en sesión:", e)
        return False

def verificar_variable_sesion(conn):
    """
    Verifica el valor actual de la variable app.usuario
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT current_setting('app.usuario', true)")
        resultado = cursor.fetchone()
        cursor.close()
        usuario = resultado[0] if resultado else 'NULL'
        print(f"🔍 Variable de sesión app.usuario = {usuario}")
        return usuario
    except Exception as e:
        print("❌ No se pudo verificar variable de sesión:", e)
        return None

def probar_conexion_usuario(usuario_app):
    """
    Función para probar que el usuario se establece correctamente
    """
    conn = conectar_db(usuario_app)
    if conn:
        verificar_variable_sesion(conn)
        conn.close()