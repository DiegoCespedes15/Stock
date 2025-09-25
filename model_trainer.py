# Archivo: src/feature engineering/model_trainer.py
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import pickle
from math import sqrt
from data_processor import obtener_datos_para_prediccion, preparar_dataset_para_xgboost

def entrenar_modelo():
    """
    Obtiene los datos, entrena el modelo de XGBoost y lo guarda.
    """
    # 1. Obtener y preparar los datos
    df_ventas = obtener_datos_para_prediccion()
    X, y = preparar_dataset_para_xgboost(df_ventas)

    if X is None:
        print("No se pudo preparar el dataset. Saliendo del entrenamiento.")
        return

    # 2. Dividir los datos en conjuntos de entrenamiento y prueba
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Inicializar y entrenar el modelo XGBoost
    modelo = xgb.XGBRegressor(
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    modelo.fit(X_train, y_train, eval_set=[(X_test, y_test)]) 

    # 4. Inicializar y entrenar el modelo XGBoost
    print("3. Entrenando el modelo XGBoost (Regresión)...")
    
    # El constructor mantiene 'eval_metric="rmse"'
    modelo = xgb.XGBRegressor(
        objective='reg:squarederror', 
        n_estimators=1000, 
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        n_jobs=-1,
        eval_metric="rmse" 
    )
    # Entrenar el modelo
    # ¡ESTA ES LA CORRECCIÓN CLAVE!
    # Eliminamos 'early_stopping_rounds' porque tu versión de XGBoost no lo acepta.
    modelo.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        # Línea ELIMINADA: early_stopping_rounds=50,
        verbose=False 
    )
    
    # El modelo ahora entrenará las 1000 estimaciones completas.
    
    print("4. Evaluación del modelo:")

    # 5. Guardar el modelo entrenado
    with open('modelo_xgboost.pkl', 'wb') as f:
        pickle.dump(modelo, f)
    print("Modelo entrenado y guardado como 'modelo_xgboost.pkl'.")

if __name__ == '__main__':
    entrenar_modelo()