# services/alertas_service.py
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
        self.activo = True
        self.callback_actualizacion = callback
        
        def verificar_periodicamente():
            while self.activo:
                try:
                    print(f"\n🔍 Iniciando verificación... {datetime.now().strftime('%H:%M:%S')}")
                    
                    # DEBUG: Estado actual
                    self.debug_alertas_existentes()
                    self.debug_estado_stock()
                    
                    # 1. Primero resolver alertas que ya se solucionaron
                    alertas_resueltas = self.verificar_alertas_resueltas()
                    
                    # 2. Luego crear nuevas alertas SOLO si hay stock bajo real
                    alertas_creadas = self.verificar_nuevas_alertas()
                    
                    # 3. Notificar si hay cambios
                    print(f"📊 Resultado: {alertas_creadas} nuevas, {alertas_resueltas} resueltas")
                    
                    if (alertas_resueltas > 0 or alertas_creadas > 0) and self.callback_actualizacion:
                        print("🚀 Ejecutando callback...")
                        self.callback_actualizacion(alertas_creadas, alertas_resueltas)
                    else:
                        print("⏭️  No se ejecuta callback (sin cambios o no hay callback)")
                    
                    time.sleep(intervalo)
                except Exception as e:
                    print(f"❌ Error en servicio alertas: {e}")
                    time.sleep(60)
        
        self.hilo = threading.Thread(target=verificar_periodicamente, daemon=True)
        self.hilo.start()
        print("✅ Servicio de alertas iniciado")
    
    def debug_estado_stock(self):
        """Debug: Verificar el estado actual del stock"""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.id_articulo, s.descripcion, s.cant_inventario, 
                       COALESCE(s.stock_minimo, 5) as stock_minimo,
                       CASE 
                           WHEN s.cant_inventario = 0 THEN 'AGOTADO'
                           WHEN s.cant_inventario <= COALESCE(s.stock_minimo, 5) THEN 'CRITICO'
                           WHEN s.cant_inventario <= COALESCE(s.stock_minimo, 5) * 1.25 THEN 'BAJO'
                           ELSE 'NORMAL'
                       END as estado
                FROM desarrollo.stock s
                WHERE s.cant_inventario <= COALESCE(s.stock_minimo, 5) * 1.25
                ORDER BY s.cant_inventario ASC
            """)
            
            productos = cursor.fetchall()
            cursor.close()
            conn.close()
            
            print("=== DEBUG: Productos con stock bajo ===")
            for producto in productos:
                id_art, desc, stock, minimo, estado = producto
                print(f"{desc}: {stock} (mín: {minimo}) -> {estado}")
            print(f"Total: {len(productos)} productos con stock bajo")
            print("======================================")
            
            return productos
            
        except Exception as e:
            print(f"❌ Error en debug stock: {e}")
            return []
    
    def debug_alertas_existentes(self):
        """Debug: Verificar alertas activas existentes"""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT a.id_alerta, a.descripcion_producto, a.stock_actual, 
                       a.stock_minimo, a.nivel_alerta, a.fecha_alerta
                FROM desarrollo.alertas_stock a
                WHERE a.estado = 'ACTIVA'
                ORDER BY a.fecha_alerta DESC
            """)
            
            alertas = cursor.fetchall()
            cursor.close()
            conn.close()
            
            print("=== DEBUG: Alertas activas existentes ===")
            for alerta in alertas:
                id_alerta, descripcion, stock_actual, stock_minimo, nivel, fecha = alerta
                print(f"{descripcion} - {nivel} - {fecha.strftime('%Y-%m-%d %H:%M')}")
            print(f"Total: {len(alertas)} alertas activas")
            print("========================================")
            
            return alertas
            
        except Exception as e:
            print(f"❌ Error en debug alertas: {e}")
            return []
    
    def verificar_alertas_resueltas(self):
        """Verifica y resuelve alertas existentes"""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            # SOLO resolver alertas cuando el stock sea MAYOR que el mínimo requerido
            cursor.execute("""
                UPDATE desarrollo.alertas_stock 
                SET estado = 'RESUELTA', 
                    fecha_resolucion = CURRENT_TIMESTAMP
                WHERE estado = 'ACTIVA'
                AND id_producto IN (
                    SELECT s.id_articulo 
                    FROM desarrollo.stock s 
                    WHERE s.cant_inventario > s.stock_minimo
                    OR (s.stock_minimo IS NULL AND s.cant_inventario > 5)
                )
            """)
            
            alertas_resueltas = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            if alertas_resueltas > 0:
                print(f"✅ {alertas_resueltas} alertas resueltas automáticamente")
            
            return alertas_resueltas
            
        except Exception as e:
            print(f"❌ Error al resolver alertas: {e}")
            return 0
    
    def verificar_nuevas_alertas(self):
        """Verifica, crea o actualiza alertas para reflejar el estado actual del stock."""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            # --- CAMBIO 1: Simplificamos la consulta ---
            # Seleccionamos TODOS los productos con stock bajo, sin importar si ya tienen alerta.
            # La lógica para evitar duplicados la haremos en Python.
            cursor.execute("""
                SELECT 
                    s.id_articulo, 
                    s.descripcion, 
                    s.cant_inventario, 
                    COALESCE(s.stock_minimo, 5) as stock_minimo
                FROM desarrollo.stock s
                WHERE s.cant_inventario <= COALESCE(s.stock_minimo, 5) * 1.25
            """)
            
            productos_con_stock_bajo = cursor.fetchall()
            alertas_modificadas = 0
            
            print(f"🔎 Encontrados {len(productos_con_stock_bajo)} productos con stock bajo o agotado para revisar.")
            
            for producto in productos_con_stock_bajo:
                id_producto, descripcion, stock_actual, stock_minimo = producto
                
                # Determinar el nivel de alerta que DEBERÍA tener este producto
                nivel_alerta_actual = ""
                if stock_actual == 0:
                    nivel_alerta_actual = "AGOTADO"
                elif stock_actual <= stock_minimo:
                    nivel_alerta_actual = "CRITICO"
                else: # Ya sabemos que es <= stock_minimo * 1.25 por la consulta
                    nivel_alerta_actual = "BAJO"

                # --- CAMBIO 2: Lógica de Actualizar o Insertar ---
                # Buscamos si ya existe una alerta ACTIVA para este producto
                cursor.execute("""
                    SELECT id_alerta, nivel_alerta, stock_actual 
                    FROM desarrollo.alertas_stock
                    WHERE id_producto = %s AND estado = 'ACTIVA'
                """, (id_producto,))
                
                alerta_existente = cursor.fetchone()

                if alerta_existente:
                    # Si ya existe una alerta, la actualizamos si el nivel o el stock ha cambiado
                    id_alerta_existente, nivel_viejo, stock_viejo = alerta_existente
                    
                    if nivel_viejo != nivel_alerta_actual or stock_viejo != stock_actual:
                        cursor.execute("""
                            UPDATE desarrollo.alertas_stock
                            SET nivel_alerta = %s,
                                stock_actual = %s,
                                fecha_alerta = CURRENT_TIMESTAMP
                            WHERE id_alerta = %s
                        """, (nivel_alerta_actual, stock_actual, id_alerta_existente))
                        alertas_modificadas += 1
                        print(f"🔄 Alerta actualizada: {descripcion} de '{nivel_viejo}' a '{nivel_alerta_actual}'")
                
                else:
                    # Si no existe ninguna alerta activa, creamos una nueva
                    cursor.execute("""
                        INSERT INTO desarrollo.alertas_stock 
                        (id_producto, descripcion_producto, stock_actual, stock_minimo, nivel_alerta, estado)
                        VALUES (%s, %s, %s, %s, %s, 'ACTIVA')
                    """, (id_producto, descripcion, stock_actual, stock_minimo, nivel_alerta_actual))
                    alertas_modificadas += 1
                    print(f"📝 Nueva alerta creada: {descripcion} - {nivel_alerta_actual}")

            conn.commit()
            cursor.close()
            conn.close()
            
            if alertas_modificadas > 0:
                print(f"📢 {datetime.now().strftime('%H:%M:%S')} - {alertas_modificadas} alertas creadas/actualizadas.")
            
            return alertas_modificadas
            
        except Exception as e:
            print(f"❌ Error al verificar/crear alertas: {e}")
            return 0
    
    def obtener_alertas_activas(self):
        """Obtiene todas las alertas activas"""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT a.id_alerta, a.descripcion_producto, a.stock_actual, 
                       a.stock_minimo, a.nivel_alerta, a.fecha_alerta
                FROM desarrollo.alertas_stock a
                WHERE a.estado = 'ACTIVA'
                ORDER BY a.nivel_alerta DESC, a.fecha_alerta DESC
            """)
            
            alertas = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return alertas
            
        except Exception as e:
            print(f"❌ Error al obtener alertas activas: {e}")
            return []
    
    def marcar_alerta_vista(self, id_alerta):
        """Marca una alerta como vista"""
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE desarrollo.alertas_stock 
                SET vista = TRUE 
                WHERE id_alerta = %s
            """, (id_alerta,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Alerta {id_alerta} marcada como vista")
            return True
            
        except Exception as e:
            print(f"❌ Error al marcar alerta como vista: {e}")
            return False
    
    def detener_servicio(self):
        """Detiene el servicio de alertas"""
        self.activo = False
        if self.hilo:
            self.hilo.join(timeout=2)
        print("⏹️ Servicio de alertas detenido")

# Instancia global del servicio
servicio_alertas = ServicioAlertas()