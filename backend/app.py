import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Rutas base
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
frontend_folder = os.path.join(base_dir, 'frontend')
db_path = os.path.join(os.path.dirname(__file__), 'wiki.db')

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURACIÓN Y BASE DE DATOS SQLITE
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Crear tabla de publicaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS publicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            autor TEXT NOT NULL,
            fecha TEXT NOT NULL,
            contenido TEXT NOT NULL
        )
    ''')
    
    # Insertar publicaciones iniciales de prueba si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM publicaciones')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            "Paginación y Segmentación",
            "Definición",
            "Sistemas Operativos",
            "Cátedra de SO",
            "2026-10-08",
            "La paginación es un esquema de gestión de memoria que permite que el espacio de direcciones físicas de un proceso no sea contiguo."
        ))
        cursor.execute('''
            INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            "Estructura de Árboles B+",
            "Artículo",
            "Estructuras de Datos",
            "Sistemas UMG",
            "2026-10-07",
            "Los árboles B+ son variantes de los árboles B optimizados para sistemas de archivos y bases de datos relacionales."
        ))
    conn.commit()
    conn.close()

# Inicializar BD al arrancar
init_db()

# ==========================================
# SIMULADOR RAM (EN MEMORIA)
# ==========================================
RAM_TOTAL_MB = 1024

estado_simulador = {
    "ram_total_mb": RAM_TOTAL_MB,
    "ram_usada_mb": 0,
    "ram_disponible_mb": RAM_TOTAL_MB,
    "porcentaje_ram_usada": 0.0,
    "procesos_ejecucion": [],
    "cola_espera": [],
    "siguiente_id": 1
}

# ==========================================
# RUTAS PARA SERVIR EL FRONTEND
# ==========================================
@app.route('/')
def main_index():
    return send_from_directory(frontend_folder, 'index.html')

@app.route('/<path:filename>')
def serve_frontend_files(filename):
    return send_from_directory(frontend_folder, filename)

# ==========================================
# RUTAS DE LA API (PUBLICACIONES CON SQLITE)
# ==========================================
@app.route('/api/publicaciones', methods=['GET'])
def obtener_publicaciones():
    conn = get_db_connection()
    publicaciones = conn.execute('SELECT * FROM publicaciones ORDER BY id DESC').fetchall()
    conn.close()
    
    # Convertir filas de la BD a lista de diccionarios
    resultado = [dict(p) for p in publicaciones]
    return jsonify(resultado), 200

@app.route('/api/publicaciones', methods=['POST'])
def crear_publicacion():
    data = request.get_json()
    if not data or not data.get('titulo') or not data.get('contenido'):
        return jsonify({"error": "El título y contenido son obligatorios."}), 400

    titulo = data.get('titulo')
    tipo = data.get('tipo', 'Definición')
    categoria = data.get('categoria', 'General')
    autor = data.get('autor', 'Anónimo')
    fecha = data.get('fecha', '2026-10-08')
    contenido = data.get('contenido')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (titulo, tipo, categoria, autor, fecha, contenido))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()

    nueva_pub = {
        "id": nuevo_id,
        "titulo": titulo,
        "tipo": tipo,
        "categoria": categoria,
        "autor": autor,
        "fecha": fecha,
        "contenido": contenido
    }
    return jsonify(nueva_pub), 201

# ==========================================
# RUTAS DEL SIMULADOR RAM
# ==========================================
def actualizar_metricas_ram():
    usada = sum(p["tamano_mb"] for p in estado_simulador["procesos_ejecucion"])
    estado_simulador["ram_usada_mb"] = usada
    estado_simulador["ram_disponible_mb"] = RAM_TOTAL_MB - usada
    estado_simulador["porcentaje_ram_usada"] = round((usada / RAM_TOTAL_MB) * 100, 1)

def procesar_cola_espera():
    i = 0
    while i < len(estado_simulador["cola_espera"]):
        proc = estado_simulador["cola_espera"][i]
        if proc["tamano_mb"] <= estado_simulador["ram_disponible_mb"]:
            estado_simulador["procesos_ejecucion"].append(proc)
            estado_simulador["cola_espera"].pop(i)
            actualizar_metricas_ram()
        else:
            i += 1

@app.route('/api/simulador/estado', methods=['GET'])
def obtener_estado_simulador():
    return jsonify(estado_simulador), 200

@app.route('/api/simulador/crear', methods=['POST'])
def crear_proceso():
    data = request.get_json()
    nombre = data.get('nombre')
    tamano = int(data.get('tamano', 128))

    if not nombre or tamano <= 0:
        return jsonify({"error": "Nombre y tamaño válidos son requeridos."}), 400

    nuevo_proceso = {
        "id": estado_simulador["siguiente_id"],
        "nombre": nombre,
        "tamano_mb": tamano
    }
    estado_simulador["siguiente_id"] += 1

    if tamano <= estado_simulador["ram_disponible_mb"]:
        estado_simulador["procesos_ejecucion"].append(nuevo_proceso)
        actualizar_metricas_ram()
    else:
        estado_simulador["cola_espera"].append(nuevo_proceso)

    return jsonify(estado_simulador), 200

@app.route('/api/simulador/eliminar/<int:proceso_id>', methods=['DELETE', 'POST'])
def eliminar_proceso(proceso_id):
    estado_simulador["procesos_ejecucion"] = [
        p for p in estado_simulador["procesos_ejecucion"] if p["id"] != proceso_id
    ]
    estado_simulador["cola_espera"] = [
        p for p in estado_simulador["cola_espera"] if p["id"] != proceso_id
    ]
    actualizar_metricas_ram()
    procesar_cola_espera()
    return jsonify(estado_simulador), 200

@app.route('/api/simulador/reiniciar', methods=['POST'])
def reiniciar_simulador():
    global estado_simulador
    estado_simulador = {
        "ram_total_mb": RAM_TOTAL_MB,
        "ram_usada_mb": 0,
        "ram_disponible_mb": RAM_TOTAL_MB,
        "porcentaje_ram_usada": 0.0,
        "procesos_ejecucion": [],
        "cola_espera": [],
        "siguiente_id": 1
    }
    return jsonify(estado_simulador), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)