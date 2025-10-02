# Archivo: src/feature_engineering/data_connector.py (VERSIÓN CORREGIDA)

import sqlalchemy
import os
import urllib.parse
from dotenv import load_dotenv

def conectar_data_db():
    """
    Función que crea y devuelve un motor (Engine) de SQLAlchemy.
    """
    # Cargar las variables de entorno desde el archivo .env
    load_dotenv()
    
    # Obtener los datos de conexión
    # ... (variables de entorno como antes) ...
    user = os.getenv("DB_USER") 
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    db = os.getenv("DB_NAME")
    
    password_encoded = urllib.parse.quote_plus(password)
    
    # Crear la cadena de conexión
    db_uri = f"postgresql+psycopg2://{user}:{password_encoded}@{host}:{port}/{db}"
    
    try:
        # Crea y devuelve el motor de SQLAlchemy
        # ESTA PARTE ES CRUCIAL: Debe devolver el objeto Engine.
        engine = sqlalchemy.create_engine(db_uri)
        return engine # ¡Asegúrate de devolver el ENGINE!
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        return None