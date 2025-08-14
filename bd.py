import psycopg2

DB_CONFIG = {
    'dbname': 'postgres',    
    'user': 'postgres',       
    'password': '123',        
    'host': 'localhost',
}

def conectar_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print("Error al conectar a la base de datos:", e)
        return None
