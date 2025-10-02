# Archivo: src/monthly_service.py

import schedule
import time
import subprocess
import sys
import os

# --- Configuración ---
# La ruta del ejecutable de Python de tu entorno virtual.
# Asegúrate de que esta ruta sea absoluta para evitar fallos.
PYTHON_EXE = sys.executable 
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # src/

def ejecutar_proceso_mensual():
    """Ejecuta secuencialmente el procesador de datos y el entrenador de modelos."""
    
    # 1. Ejecutar Data Processor
    data_processor_path = os.path.join(BASE_DIR, 'feature_engineering', 'data_processor.py')
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando Data Processor...")
    
    # Usamos subprocess.run para ejecutar el script
    try:
        resultado_data = subprocess.run([PYTHON_EXE, data_processor_path], capture_output=True, text=True, check=True)
        print("Data Processor Salida:\n", resultado_data.stdout)
        print("✅ Data Processor completado.")
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Data Processor falló con código {e.returncode}. {e.stderr}")
        return
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el ejecutable de Python en {PYTHON_EXE}")
        return

    # 2. Ejecutar Model Trainer (solo si el paso anterior fue exitoso)
    model_trainer_path = os.path.join(BASE_DIR, 'model_trainer.py')
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando Model Trainer...")
    
    try:
        resultado_model = subprocess.run([PYTHON_EXE, model_trainer_path], capture_output=True, text=True, check=True)
        print("Model Trainer Salida:\n", resultado_model.stdout)
        print("🎉 Proceso de ML Mensual completado.")
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Model Trainer falló con código {e.returncode}. {e.stderr}")
        return

# --- Programación de la Tarea ---

# TAREA CLAVE: Ejecutar el día 1 de cada mes a las 03:00 AM
# Nota: La librería 'schedule' no tiene una función directa 'run_on_the_first_day_of_the_month',
# por lo que programamos la ejecución diaria y la función comprueba la fecha.

def job_checker():
    """Comprueba si es el día 1 del mes antes de ejecutar el trabajo."""
    if time.localtime().tm_mday == 1:
        ejecutar_proceso_mensual()
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Esperando el día 1...")

# Programar la verificación todos los días a las 3:00 AM
schedule.every().day.at("03:00").do(job_checker)

print("Servicio de ML iniciado. Esperando la próxima ejecución programada.")

while True:
    schedule.run_pending()
    time.sleep(60 * 60) # Dormir 1 hora para reducir la carga de CPU