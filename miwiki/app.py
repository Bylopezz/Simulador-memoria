from flask import Flask, render_template
import requests

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/articulo/<nombre>")
def articulo(nombre):

    articulos = {
        "programacion": {
            "titulo": "Programación",
            "icono": "💻",
            "descripcion": "La programación es el proceso de crear instrucciones que permiten a una computadora realizar determinadas tareas."
        },

        "redes": {
            "titulo": "Redes",
            "icono": "🌐",
            "descripcion": "Las redes informáticas permiten conectar dispositivos para compartir información y recursos."
        },

        "bases-datos": {
            "titulo": "Bases de Datos",
            "icono": "🗄️",
            "descripcion": "Una base de datos permite almacenar, organizar y consultar información de manera estructurada."
        },

        "sistemas-operativos": {
            "titulo": "Sistemas Operativos",
            "icono": "⚙️",
            "descripcion": "Un sistema operativo administra los recursos de una computadora y permite la interacción entre el usuario y el hardware."
        }
    }

    articulo = articulos.get(nombre)

    if articulo is None:
        return "Artículo no encontrado", 404

    return render_template(
        "articulo.html",
        articulo=articulo
    )


@app.route("/simulador")
def simulador():

    try:
        respuesta = requests.get(
            "http://127.0.0.1:5001/estado",
            timeout=2
        )

        estado = respuesta.json()

    except requests.exceptions.RequestException:
        estado = {
            "ram_total_mb": 1024,
            "ram_usada_mb": 0,
            "ram_disponible_mb": 1024,
            "porcentaje_ram_usada": 0,
            "procesos_ejecucion": [],
            "cola_espera": []
        }

    return render_template(
        "simulador.html",
        estado=estado
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)