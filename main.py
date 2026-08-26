import time
import threading
from queue import Queue

class Proceso:
    def __init__(self, pid, nombre, memoria_mb, duracion_seg):
        self.pid = pid
        self.nombre = nombre or f"Proceso_{pid}"
        self.memoria_mb = memoria_mb
        self.duracion_seg = duracion_seg

class SimuladorMemoria:
    def __init__(self, ram_total_mb=1024):
        self.ram_total = ram_total_mb
        self.ram_disponible = ram_total_mb
        self.cola_espera = Queue()
        self.procesos_ejecucion = []
        self.lock = threading.Lock()

    def agregar_proceso(self, proceso):
        print(f"[+] Proceso {proceso.pid} ({proceso.nombre}) creado. Requiere {proceso.memoria_mb} MB.")
        self.cola_espera.put(proceso)
        self.procesar_cola()

    def procesar_cola(self):
        with self.lock:
            while not self.cola_espera.empty():
                siguiente = self.cola_espera.queue[0]
                if siguiente.memoria_mb <= self.ram_disponible:
                    proceso = self.cola_espera.get()
                    self.ram_disponible -= proceso.memoria_mb
                    self.procesos_ejecucion.append(proceso)
                    
                    # Ejecutar proceso en un hilo secundario
                    hilo = threading.Thread(target=self._ejecutar_proceso, args=(proceso,))
                    hilo.start()
                else:
                    break  # No hay suficiente memoria, se queda en la cola

    def _ejecutar_proceso(self, proceso):
        print(f"[EJECUCIÓN] {proceso.nombre} (PID: {proceso.pid}) inició.")
        time.sleep(proceso.duracion_seg)  # Simula el tiempo de CPU
        
        with self.lock:
            self.procesos_ejecucion.remove(proceso)
            self.ram_disponible += proceso.memoria_mb
            print(f"[FINALIZADO] {proceso.nombre} (PID: {proceso.pid}). Memoria liberada: {proceso.memoria_mb} MB.")
        
        # Intentar meter procesos en cola tras liberar RAM
        self.procesar_cola()

    def mostrar_estado(self):
        with self.lock:
            print("\n--- ESTADO DEL SISTEMA ---")
            print(f"RAM Disponible: {self.ram_disponible}/{self.ram_total} MB")
            print(f"En Ejecución: {[p.nombre for p in self.procesos_ejecucion]}")
            print(f"En Cola: {[p.nombre for p in list(self.cola_espera.queue)]}")
            print("---------------------------\n")

# Prueba rápida
if __name__ == "__main__":
    sim = SimuladorMemoria(ram_total_mb=1024)
    sim.agregar_proceso(Proceso(1, "Navegador", 500, 5))
    sim.agregar_proceso(Proceso(2, "IDE Code", 400, 3))
    sim.agregar_proceso(Proceso(3, "Juego", 300, 4)) # Debe ir a cola
    
    time.sleep(1)
    sim.mostrar_estado()
