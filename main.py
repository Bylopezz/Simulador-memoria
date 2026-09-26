import time
import threading
from queue import Queue
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print

console = Console()

class Proceso:
    def __init__(self, pid, nombre, memoria_mb, duracion_seg):
        self.pid = pid
        self.nombre = nombre if nombre.strip() else f"Proceso_{pid}"
        self.memoria_mb = memoria_mb
        self.duracion_seg = duracion_seg
        self.tiempo_restante = duracion_seg

class SimuladorMemoria:
    def __init__(self, ram_total_mb=1024):
        self.ram_total = ram_total_mb
        self.ram_disponible = ram_total_mb
        self.cola_espera = Queue()
        self.procesos_ejecucion = []
        self.lock = threading.Lock()
        self.contador_pid = 1

    def agregar_proceso(self, nombre, memoria_mb, duracion_seg):
        with self.lock:
            proceso = Proceso(self.contador_pid, nombre, memoria_mb, duracion_seg)
            self.contador_pid += 1
            self.cola_espera.put(proceso)
        self._procesar_cola()

    def _procesar_cola(self):
        with self.lock:
            while not self.cola_espera.empty():
                siguiente = self.cola_espera.queue[0]
                if siguiente.memoria_mb <= self.ram_disponible:
                    proceso = self.cola_espera.get()
                    self.ram_disponible -= proceso.memoria_mb
                    self.procesos_ejecucion.append(proceso)
                    
                    hilo = threading.Thread(target=self._ejecutar_proceso, args=(proceso,), daemon=True)
                    hilo.start()
                else:
                    break

    def _ejecutar_proceso(self, proceso):
        while proceso.tiempo_restante > 0:
            time.sleep(1)
            proceso.tiempo_restante -= 1

        with self.lock:
            if proceso in self.procesos_ejecucion:
                self.procesos_ejecucion.remove(proceso)
                self.ram_disponible += proceso.memoria_mb
        
        self._procesar_cola()

    def renderizar_dashboard(self):
        with self.lock:
            usado = self.ram_total - self.ram_disponible
            porcentaje = (usado / self.ram_total) * 100
            
            # Panel RAM
            resumen_ram = f"RAM Usada: {usado} MB / {self.ram_total} MB ({porcentaje:.1f}%)\nRAM Disponible: {self.ram_disponible} MB"
            panel_ram = Panel(resumen_ram, title="[bold blue]Estado de Memoria RAM[/bold blue]", border_style="blue")

            # Tabla Ejecución
            tabla_ejec = Table(title="[bold green]Procesos en Ejecución[/bold green]", expand=True)
            tabla_ejec.add_column("PID", justify="center", style="cyan")
            tabla_ejec.add_column("Nombre", style="bold white")
            tabla_ejec.add_column("RAM", justify="right", style="yellow")
            tabla_ejec.add_column("Tiempo Restante", justify="right", style="magenta")

            for p in self.procesos_ejecucion:
                tabla_ejec.add_row(str(p.pid), p.nombre, f"{p.memoria_mb} MB", f"{p.tiempo_restante}s")

            # Tabla Cola
            tabla_cola = Table(title="[bold yellow]Cola de Espera[/bold yellow]", expand=True)
            tabla_cola.add_column("PID", justify="center", style="cyan")
            tabla_cola.add_column("Nombre", style="bold white")
            tabla_cola.add_column("RAM Requerida", justify="right", style="yellow")
            tabla_cola.add_column("Duración", justify="right", style="magenta")

            for p in list(self.cola_espera.queue):
                tabla_cola.add_row(str(p.pid), p.nombre, f"{p.memoria_mb} MB", f"{p.duracion_seg}s")

            console.clear()
            console.print(Panel("[bold white]SIMULADOR DE GESTIÓN DE PROCESOS EN MEMORIA[/bold white]", style="bold cyan"))
            console.print(panel_ram)
            console.print(tabla_ejec)
            console.print(tabla_cola)
            console.print("\n[dim]Presiona Ctrl+C para regresar al menú principal...[/dim]")


def menu(simulador):
    
    while True:
        console.clear()
        console.print(Panel.fit(
            "[1] Agregar un nuevo proceso\n"
            "[2] Cargar lote de procesos de prueba\n"
            "[3] Ver Monitor en Tiempo Real\n"
            "[4] Salir",
            title="[bold cyan]Menú Principal[/bold cyan]",
            border_style="cyan"
        ))
        
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == "1":
            nombre = input("Nombre del proceso (dejar vacío para dinámico): ")
            try:
                ram = int(input("Memoria RAM requerida en MB (ej. 256): "))
                duracion = int(input("Duración en segundos (ej. 10): "))
                simulador.agregar_proceso(nombre, ram, duracion)
                print("[green]✓ Proceso agregado exitosamente.[/green]")
                time.sleep(1)
            except ValueError:
                print("[red]Error: Ingrese valores numéricos válidos.[/red]")
                time.sleep(1.5)

        elif opcion == "2":
            simulador.agregar_proceso("Navegador Web", 400, 12)
            simulador.agregar_proceso("VS Code", 350, 15)
            simulador.agregar_proceso("Base de Datos", 400, 10)
            simulador.agregar_proceso("Reproductor", 150, 8)
            print("[green]✓ Lote de prueba cargado correctamente.[/green]")
            time.sleep(1.5)

        elif opcion == "3":
            try:
                while True:
                    simulador.renderizar_dashboard()
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass

        elif opcion == "4":
            print("[bold blue]¡Hasta luego![/bold blue]")
            break

if __name__ == "__main__":
    simulador = SimuladorMemoria(ram_total_mb=1024)
    menu(simulador)
