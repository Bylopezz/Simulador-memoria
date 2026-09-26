from flask import Flask, jsonify
from main import SimuladorMemoria
import threading

app = Flask(__name__)

# Un único simulador compartido
simulador = SimuladorMemoria(ram_total_mb=1024)


@app.route("/")
def inicio():
    return """
    <h1>Servidor del Simulador de Memoria</h1>
    <p>El servidor está funcionando correctamente.</p>
    <p><a href="/estado">Ver estado del simulador</a></p>
    """


@app.route("/estado")
def estado():
    with simulador.lock:
        usado = simulador.ram_total - simulador.ram_disponible
        porcentaje = (usado / simulador.ram_total) * 100

        procesos = []

        for p in simulador.procesos_ejecucion:
            procesos.append({
                "pid": p.pid,
                "nombre": p.nombre,
                "memoria_mb": p.memoria_mb,
                "tiempo_restante": p.tiempo_restante
            })

        cola = []

        for p in list(simulador.cola_espera.queue):
            cola.append({
                "pid": p.pid,
                "nombre": p.nombre,
                "memoria_mb": p.memoria_mb,
                "duracion_seg": p.duracion_seg
            })

        return jsonify({
            "ram_total_mb": simulador.ram_total,
            "ram_usada_mb": usado,
            "ram_disponible_mb": simulador.ram_disponible,
            "porcentaje_ram_usada": round(porcentaje, 2),
            "procesos_ejecucion": procesos,
            "cola_espera": cola
        })


def iniciar_servidor():
    app.run(debug=True, port=5001, use_reloader=False)

if __name__ == "__main__":
    servidor = threading.Thread(
        target=iniciar_servidor,
        daemon=True
    )
    servidor.start()

    print("Servidor iniciado en http://127.0.0.1:5001")

    from main import menu

    menu(simulador)