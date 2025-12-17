import threading
import time
from datetime import datetime
from bd import conectar_db

class ServicioAlertas:
    def __init__(self):
        self.activo = False
        self.hilo = None
        self.callback_actualizacion = None
    
    def iniciar_servicio(self, callback=None, intervalo=30):
        """Inicia el servicio de alertas en segundo plano"""
        if self.activo: return # Evitar doble inicio
        
        self.activo = True
        self.callback_actualizacion = callback
        
        def verificar_periodicamente():
            print(f"✅ Servicio de alertas iniciado (Intervalo: {intervalo}s)")
            while self.activo:
                try:
                    # 1. Resolver alertas viejas (Productos que ya tienen stock)
                    n_resueltas = self.verificar_alertas_resueltas()
                    
                    # 2. Crear/Actualizar alertas nuevas
                    n_nuevas = self.verificar_nuevas_alertas()
                    
                    # 3. Feedback en consola (solo si hubo cambios para no ensuciar el log)
                    if n_resueltas > 0 or n_nuevas > 0:
                        print(f"⚡ [Monitor Stock] Cambios detectados: {n_nuevas} actualizaciones, {n_resueltas} resoluciones.")
                        if self.callback_actualizacion:
                            self.callback_actualizacion(n_nuevas)
                    
                    time.sleep(intervalo)
                    
                except Exception as e:
                    print(f"❌ Error crítico en servicio de alertas: {e}")
                    time.sleep(60) # Esperar un minuto si hay error grave antes de reintentar
        
        self.hilo = threading.Thread(target=verificar_periodicamente, daemon=True)
        self.hilo.start()
    
    def detener_servicio(self):
        self.activo = False
        if self.hilo: self.hilo.join(timeout=1)
        print("⏹️ Servicio detenido.")

    def verificar_alertas_resueltas(self):
        """Marca como RESUELTA las alertas donde el stock ya supera el mínimo"""
        conn = None
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            # Query optimizada: Solo toca alertas ACTIVAS cuyo stock ya esté bien
            cursor.execute("""
                UPDATE desarrollo.alertas_stock a
                SET estado = 'RESUELTA', fecha_resolucion = NOW()
                FROM desarrollo.stock s
                WHERE a.id_producto = s.id_articulo
                  AND a.estado = 'ACTIVA'
                  AND s.cant_inventario > COALESCE(s.stock_minimo, 5)
            """)
            
            count = cursor.rowcount
            conn.commit()
            return count
        except Exception as e:
            print(f"Error resolviendo alertas: {e}")
            return 0
        finally:
            if conn: conn.close()

    def verificar_nuevas_alertas(self):
        """Analiza el stock y gestiona las alertas (CORREGIDO)"""
        conn = None
        cambios = 0
        try:
            conn = conectar_db()
            cursor = conn.cursor()

            # 1. Obtener alertas activas (AHORA INCLUIMOS stock_minimo EN LA LECTURA)
            cursor.execute("""
                SELECT id_producto, id_alerta, nivel_alerta, stock_actual, stock_minimo 
                FROM desarrollo.alertas_stock WHERE estado = 'ACTIVA'
            """)
            # Guardamos también el mínimo registrado en el diccionario
            alertas_activas = {
                row[0]: {'id': row[1], 'nivel': row[2], 'stock': row[3], 'minimo': row[4]} 
                for row in cursor.fetchall()
            }

            # 2. Obtener productos con problemas
            cursor.execute("""
                SELECT id_articulo, descripcion, cant_inventario, COALESCE(stock_minimo, 5)
                FROM desarrollo.stock
                WHERE cant_inventario <= COALESCE(stock_minimo, 5) * 1.25
            """)
            productos_problematicos = cursor.fetchall()

            # 3. Comparar
            for prod in productos_problematicos:
                pid, desc, stock, minimo = prod
                
                # Calcular nivel actual
                nuevo_nivel = self._calcular_nivel(stock, minimo)

                if pid in alertas_activas:
                    # YA EXISTE ALERTA
                    datos_alerta = alertas_activas[pid]
                    
                    # --- CORRECCIÓN AQUÍ ---
                    # Ahora verificamos también si el MÍNIMO ha cambiado
                    if (datos_alerta['nivel'] != nuevo_nivel or 
                        datos_alerta['stock'] != stock or 
                        datos_alerta['minimo'] != minimo): # <--- ESTO FALTABA
                        
                        cursor.execute("""
                            UPDATE desarrollo.alertas_stock 
                            SET nivel_alerta = %s, stock_actual = %s, fecha_alerta = NOW(), stock_minimo = %s
                            WHERE id_alerta = %s
                        """, (nuevo_nivel, stock, minimo, datos_alerta['id']))
                        cambios += 1
                        # print(f"🔄 Alerta actualizada: {desc}")
                else:
                    # NO EXISTE ALERTA
                    cursor.execute("""
                        INSERT INTO desarrollo.alertas_stock 
                        (id_producto, descripcion_producto, stock_actual, stock_minimo, nivel_alerta, estado, fecha_alerta)
                        VALUES (%s, %s, %s, %s, %s, 'ACTIVA', NOW())
                    """, (pid, desc, stock, minimo, nuevo_nivel))
                    cambios += 1

            conn.commit()
            return cambios

        except Exception as e:
            print(f"Error verificando nuevas alertas: {e}")
            return 0
        finally:
            if conn: conn.close()

    def marcar_alerta_vista(self, id_alerta):
        """Versión compatible con restricción de estado"""
        conn = None
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            # En lugar de cambiar estado='VISTA', usamos la columna booleana 'vista'
            # (Asegúrate de que tu tabla tenga la columna 'vista')
            cursor.execute("UPDATE desarrollo.alertas_stock SET vista = TRUE WHERE id_alerta = %s", (id_alerta,))
            conn.commit()
            return True
        except Exception as e:
            print(e); return False
        finally:
            if conn: conn.close()

    def _calcular_nivel(self, stock, minimo):
        """Helper puro para determinar string de nivel"""
        if stock == 0: return 'AGOTADO'
        if stock <= minimo: return 'CRITICO'
        return 'BAJO'

# Instancia Singleton
servicio_alertas = ServicioAlertas()