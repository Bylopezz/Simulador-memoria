import threading
import time
import random
import os
import ctypes

# Función auxiliar para obtener el TID (Thread ID) real del Kernel de Linux
def get_kernel_tid():
    try:
        # Llama a la llamada al sistema gettid() de libc en Linux
        libc = ctypes.CDLL('libc.so.6')
        return libc.gettid()
    except Exception:
        return threading.get_ident()

class Asiento:
    def __init__(self, id_asiento):
        self.id_asiento = id_asiento
        self.reservado_por = None
        self.historial_reservas = []  # Para registrar sobreventas (condición de carrera)
        self.lock = threading.Lock()   # Lock nativo para sincronización

class SistemaReservasAerolinea:
    def __init__(self, lista_asientos):
        self.asientos = {id_a: Asiento(id_a) for id_a in lista_asientos}
        self.conteo_exito = 0
        self.conteo_fallo = 0
        self.lock_global_stats = threading.Lock()

    def reservar_sin_sincronizar(self, id_asiento, pasajero):
        """
        MODO CON CONDICIÓN DE CARRERA:
        Simula una verificación y reserva sin lock.
        Provoca OVERBOOKING (sobreventa) bajo concurrencia real.
        """
        asiento = self.asientos[id_asiento]
        
        # Simula una lectura del estado
        if asiento.reservado_por is None:
            # Simula una pequeña latencia de red/procesamiento para forzar el solapamiento de hilos
            time.sleep(0.001)
            
            # ESCRITURA INSEGURA (Sección crítica no protegida)
            asiento.reservado_por = pasajero
            asiento.historial_reservas.append(pasajero)
            
            with self.lock_global_stats:
                self.conteo_exito += 1
            return True
        else:
            with self.lock_global_stats:
                self.conteo_fallo += 1
            return False

    def reservar_sincronizado(self, id_asiento, pasajero):
        """
        MODO PROTEGIDO POR LOCK (SECCIÓN CRÍTICA ATÓMICA):
        Usa el Lock nativo del asiento para evitar condiciones de carrera.
        """
        asiento = self.asientos[id_asiento]
        
        # Adquiere el Lock exclusivo del asiento
        with asiento.lock:
            if asiento.reservado_por is None:
                time.sleep(0.001)  # Latencia simulada
                asiento.reservado_por = pasajero
                asiento.historial_reservas.append(pasajero)
                
                with self.lock_global_stats:
                    self.conteo_exito += 1
                return True
            else:
                with self.lock_global_stats:
                    self.conteo_fallo += 1
                return False

    def reiniciar_asientos(self):
        for asiento in self.asientos.values():
            asiento.reservado_por = None
            asiento.historial_reservas.clear()
        self.conteo_exito = 0
        self.conteo_fallo = 0


def tarea_agente_venta(id_agente, sistema, asientos_objetivo, modo_protegido):
    pid = os.getpid()
    tid = get_kernel_tid()
    print(f"  [Agente-{id_agente:02d}] Iniciado -> PID OS: {pid} | Kernel TID: {tid}")

    # Pausa intencional prolongada para dar tiempo a inspeccionar en Linux (ps -eLf / htop)
    time.sleep(1.5)

    for id_asiento in asientos_objetivo:
        pasajero_nombre = f"Pasajero_{id_agente}_{random.randint(100, 999)}"
        if modo_protegido:
            sistema.reservar_sincronizado(id_asiento, pasajero_nombre)
        else:
            sistema.reservar_sin_sincronizar(id_asiento, pasajero_nombre)


def ejecutar_demostracion(modo_protegido=False):
    # Definimos 5 asientos con alta demanda
    asientos_vuelo = ["1A", "1B", "2A", "2B", "3A"]
    sistema = SistemaReservasAerolinea(asientos_vuelo)

    # Creamos 20 agentes/hilos compitiendo simultáneamente por los mismos 5 asientos
    num_agentes = 20
    hilos = []

    modo_str = "SINCRONIZADO (PROTEGIDO CON LOCKS)" if modo_protegido else "SIN SINCRONIZAR (CONDICIÓN DE CARRERA)"
    print("\n" + "=" * 70)
    print(f" MODO DE EJECUCIÓN: {modo_str}")
    print(f" PID del Proceso Principal: {os.getpid()}")
    print(" Instrucción para verificación en WSL2/Linux durante la pausa:")
    print(f"   Terminal 2>  ps -eLf | grep {os.getpid()}")
    print("=" * 70)

    for i in range(1, num_agentes + 1):
        # Todos los agentes intentan reservar los mismos asientos
        t = threading.Thread(
            target=tarea_agente_venta,
            args=(i, sistema, asientos_vuelo, modo_protegido),
            name=f"HiloAgente-{i}"
        )
        hilos.append(t)

    # Iniciar todos los hilos
    for t in hilos:
        t.start()

    # Esperar a que todos los hilos terminen
    for t in hilos:
        t.join()

    # Evaluación de Resultados e Integridad de Datos
    print("\n" + "-" * 70)
    print(" RESULTADOS DEL SISTEMA DE RESERVAS DE ASIENTOS")
    print("-" * 70)

    asientos_con_overbooking = 0
    for id_a, asiento in sistema.asientos.items():
        total_asignaciones = len(asiento.historial_reservas)
        print(f" Asiento [{id_a}]: Confirmado {total_asignaciones} vez/veces -> Pasajeros: {asiento.historial_reservas}")
        if total_asignaciones > 1:
            asientos_con_overbooking += 1

    print("\n RESUMEN DE INTEGRIDAD DE DATOS:")
    if asientos_con_overbooking > 0:
        print(f" ❌ CONDICIÓN DE CARRERA DETECTADA: Se detectó OVERBOOKING en {asientos_con_overbooking} asientos!")
        print("    Varios pasajeros creen tener asignado el mismo asiento.")
    else:
        print(" ✅ INTEGRIDAD GARANTIZADA: Cada asiento fue asignado a exactamente UN solo pasajero.")
        print("    No ocurrió overbooking.")


if __name__ == "__main__":
    print("=== PROYECTO 2: MOTOR DE TRANSACCIONES CONCURRENTES (ENTREGABLE 1) ===")
    
    # 1. Pruebas sin sincronización (Demostración de Condición de Carrera)
    ejecutar_demostracion(modo_protegido=False)
    
    time.sleep(2)
    
    # 2. Pruebas con sincronización (Protección de Sección Crítica)
    ejecutar_demostracion(modo_protegido=True)
