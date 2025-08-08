import psycopg2

DB_CONFIG = {
    'dbname': 'postgres',    # nombre de tu base de datos
    'user': 'postgres',        # tu usuario de PostgreSQL
    'password': '123',        # tu contraseña
    'host': 'localhost',
}

def conectar_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print("Error al conectar a la base de datos:", e)
        return None
