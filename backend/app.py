import os
import sqlite3
import threading
import time
import random
import ctypes
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
# RUTAS DE LA API (CRUD PUBLICACIONES WIKI)
# ==========================================
@app.route('/api/publicaciones', methods=['GET'])
def obtener_publicaciones():
    conn = get_db_connection()
    publicaciones = conn.execute('SELECT * FROM publicaciones ORDER BY id DESC').fetchall()
    conn.close()
    resultado = [dict(p) for p in publicaciones]
    return jsonify(resultado), 200

@app.route('/api/publicaciones/<int:pub_id>', methods=['GET'])
def obtener_publicacion_por_id(pub_id):
    conn = get_db_connection()
    pub = conn.execute('SELECT * FROM publicaciones WHERE id = ?', (pub_id,)).fetchone()
    conn.close()
    if pub is None:
        return jsonify({"error": "Publicación no encontrada"}), 404
    return jsonify(dict(pub)), 200

@app.route('/api/publicaciones', methods=['POST'])
def crear_publicacion():
    data = request.get_json() or {}
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

@app.route('/api/publicaciones/<int:pub_id>', methods=['PUT'])
def actualizar_publicacion(pub_id):
    data = request.get_json() or {}
    titulo = data.get('titulo')
    tipo = data.get('tipo', 'Definición')
    categoria = data.get('categoria', 'General')
    autor = data.get('autor', 'Anónimo')
    fecha = data.get('fecha', '2026-10-08')
    contenido = data.get('contenido')

    if not titulo or not contenido:
        return jsonify({"error": "El título y el contenido son obligatorios."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE publicaciones 
        SET titulo = ?, tipo = ?, categoria = ?, autor = ?, fecha = ?, contenido = ?
        WHERE id = ?
    ''', (titulo, tipo, categoria, autor, fecha, contenido, pub_id))
    conn.commit()
    afectados = cursor.rowcount
    conn.close()

    if afectados == 0:
        return jsonify({"error": "Publicación no encontrada"}), 404

    return jsonify({"mensaje": "Publicación actualizada correctamente", "id": pub_id}), 200

@app.route('/api/publicaciones/<int:pub_id>', methods=['DELETE'])
def eliminar_publicacion(pub_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM publicaciones WHERE id = ?', (pub_id,))
    conn.commit()
    afectados = cursor.rowcount
    conn.close()

    if afectados == 0:
        return jsonify({"error": "Publicación no encontrada"}), 404

    return jsonify({"mensaje": "Publicación eliminada correctamente"}), 200

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
    data = request.get_json() or {}
    nombre = data.get('nombre')
    tamano = int(data.get('tamano', 128))
    ttl = int(data.get('ttl', 20))

    if not nombre or tamano <= 0:
        return jsonify({"error": "Nombre y tamaño válidos son requeridos."}), 400

    nuevo_proceso = {
        "id": estado_simulador["siguiente_id"],
        "nombre": nombre,
        "tamano_mb": tamano,
        "ttl": ttl,
        "ttl_inicial": ttl
    }
    estado_simulador["siguiente_id"] += 1

    if tamano <= estado_simulador["ram_disponible_mb"]:
        estado_simulador["procesos_ejecucion"].append(nuevo_proceso)
        actualizar_metricas_ram()
    else:
        estado_simulador["cola_espera"].append(nuevo_proceso)

    return jsonify(estado_simulador), 200

@app.route('/api/simulador/lote-aleatorio', methods=['POST'])
def crear_lote_aleatorio_ram():
    """Genera 1 de 3 configuraciones aleatorias de procesos con TTL > 15s para saturar y probar el planificador"""
    escenarios = [
        # Escenario 1: Carga Servidor Web y Base de Datos
        [
            {"nombre": "BaseDatos_PostgreSQL", "tamano_mb": 480, "ttl": random.randint(20, 30)},
            {"nombre": "Servidor_Nginx", "tamano_mb": 320, "ttl": random.randint(16, 22)},
            {"nombre": "Worker_Celery", "tamano_mb": 350, "ttl": random.randint(25, 35)},
            {"nombre": "Cache_Redis", "tamano_mb": 220, "ttl": random.randint(18, 25)}
        ],
        # Escenario 2: Modelo IA + Tareas en Segundo Plano
        [
            {"nombre": "Modelo_IA_PyTorch", "tamano_mb": 750, "ttl": random.randint(22, 35)},
            {"nombre": "Servicio_Autenticacion", "tamano_mb": 180, "ttl": random.randint(16, 20)},
            {"nombre": "Respaldo_Sistema", "tamano_mb": 380, "ttl": random.randint(20, 28)},
            {"nombre": "Monitor_Grafana", "tamano_mb": 150, "ttl": random.randint(18, 24)}
        ],
        # Escenario 3: Ráfaga de Microservicios
        [
            {"nombre": "Microservicio_Pagos", "tamano_mb": 280, "ttl": random.randint(16, 22)},
            {"nombre": "Microservicio_Usuarios", "tamano_mb": 310, "ttl": random.randint(18, 26)},
            {"nombre": "Contenedor_Docker", "tamano_mb": 360, "ttl": random.randint(20, 30)},
            {"nombre": "Proxy_Inverso", "tamano_mb": 290, "ttl": random.randint(17, 24)}
        ]
    ]

    escenario_elegido = random.choice(escenarios)

    for proc in escenario_elegido:
        p_id = estado_simulador["siguiente_id"]
        estado_simulador["siguiente_id"] += 1
        
        nuevo_p = {
            "id": p_id,
            "nombre": proc["nombre"],
            "tamano_mb": proc["tamano_mb"],
            "ttl": proc["ttl"],
            "ttl_inicial": proc["ttl"]
        }

        if proc["tamano_mb"] <= estado_simulador["ram_disponible_mb"]:
            estado_simulador["procesos_ejecucion"].append(nuevo_p)
            actualizar_metricas_ram()
        else:
            estado_simulador["cola_espera"].append(nuevo_p)

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

# ==========================================
# SIMULADOR DE CONCURRENCIA (SISTEMA DE VUELO)
# ==========================================
def get_kernel_tid():
    try:
        libc = ctypes.CDLL('libc.so.6')
        return libc.gettid()
    except Exception:
        return threading.get_ident()

class Asiento:
    def __init__(self, id_asiento):
        self.id_asiento = id_asiento
        self.reservado_por = None
        self.historial_reservas = []
        self.lock = threading.Lock()

class SistemaReservasAerolinea:
    def __init__(self, lista_asientos):
        self.lista_ids = lista_asientos
        self.asientos = {id_a: Asiento(id_a) for id_a in lista_asientos}
        self.conteo_exito = 0
        self.conteo_fallo = 0
        self.lock_global_stats = threading.Lock()
        self.logs = []
        self.lock_logs = threading.Lock()

    def add_log(self, mensaje):
        with self.lock_logs:
            self.logs.append(mensaje)

    def reservar_sin_sincronizar(self, id_asiento, pasajero, id_agente):
        asiento = self.asientos[id_asiento]
        if asiento.reservado_por is None:
            time.sleep(0.001)
            asiento.reservado_por = pasajero
            asiento.historial_reservas.append(pasajero)
            with self.lock_global_stats:
                self.conteo_exito += 1
            self.add_log(f"⚠️ [Sin Sync] Agente {id_agente:02d} reservó {id_asiento} -> {pasajero}")
            return True
        else:
            asiento.historial_reservas.append(pasajero) # Para detectar overbooking
            with self.lock_global_stats:
                self.conteo_fallo += 1
            return False

    def reservar_sincronizado(self, id_asiento, pasajero, id_agente):
        asiento = self.asientos[id_asiento]
        with asiento.lock:
            if asiento.reservado_por is None:
                time.sleep(0.001)
                asiento.reservado_por = pasajero
                asiento.historial_reservas.append(pasajero)
                with self.lock_global_stats:
                    self.conteo_exito += 1
                self.add_log(f"🔒 [Lock Mutex] Agente {id_agente:02d} reservó {id_asiento} -> {pasajero}")
                return True
            else:
                with self.lock_global_stats:
                    self.conteo_fallo += 1
                return False

    def reiniciar(self):
        for asiento in self.asientos.values():
            asiento.reservado_por = None
            asiento.historial_reservas.clear()
        self.conteo_exito = 0
        self.conteo_fallo = 0
        self.logs.clear()
        self.add_log("🔄 Vuelo reajustado. Todos los asientos liberados.")

# Vuelo con 12 asientos (Filas 1 a 3, Columnas A, B | Pasillo | C, D)
ASIENTOS_CABINA = ["1A", "1B", "1C", "1D", "2A", "2B", "2C", "2D", "3A", "3B", "3C", "3D"]
sistema_vuelo = SistemaReservasAerolinea(ASIENTOS_CABINA)

@app.route('/api/simulador-concurrencia/estado', methods=['GET'])
def obtener_estado_vuelo():
    asientos_res = []
    asientos_con_overbooking = 0

    for id_a in ASIENTOS_CABINA:
        asiento = sistema_vuelo.asientos[id_a]
        historial = list(asiento.historial_reservas)
        total_asignaciones = len(historial)
        es_overbooking = total_asignaciones > 1
        if es_overbooking:
            asientos_con_overbooking += 1

        asientos_res.append({
            "id": id_a,
            "pasajero_confirmado": asiento.reservado_por,
            "historial": historial,
            "total_asignaciones": total_asignaciones,
            "overbooking": es_overbooking
        })

    return jsonify({
        "asientos": asientos_res,
        "asientos_con_overbooking": asientos_con_overbooking,
        "conteo_exito": sistema_vuelo.conteo_exito,
        "conteo_fallo": sistema_vuelo.conteo_fallo,
        "integridad_ok": asientos_con_overbooking == 0,
        "logs": sistema_vuelo.logs,
        "pid": os.getpid()
    })

@app.route('/api/simulador-concurrencia/reservar-manual', methods=['POST'])
def reservar_manual():
    data = request.get_json() or {}
    id_asiento = data.get('id_asiento')
    pasajero = data.get('pasajero', 'Pasajero Manual')

    if id_asiento not in sistema_vuelo.asientos:
        return jsonify({"error": "Asiento no válido"}), 400

    exito = sistema_vuelo.reservar_sincronizado(id_asiento, pasajero, id_agente=0)
    if not exito:
        return jsonify({"error": f"El asiento {id_asiento} ya está ocupado"}), 400

    return obtener_estado_vuelo()

@app.route('/api/simulador-concurrencia/reiniciar', methods=['POST'])
def reiniciar_vuelo():
    sistema_vuelo.reiniciar()
    return obtener_estado_vuelo()

@app.route('/api/simulador-concurrencia/ejecutar', methods=['POST'])
def ejecutar_simulacion_concurrencia():
    data = request.get_json() or {}
    modo_protegido = data.get('modo_protegido', False)
    
    # Permitir variación aleatoria dinámica de agentes (entre 15 y 25 agentes) si no se especifica un número estático
    num_agentes = int(data.get('num_agentes', random.randint(15, 25)))
    
    # Reiniciar asientos para la prueba
    sistema_vuelo.reiniciar()
    hilos = []

    # Variación aleatoria de asientos en disputa en cada ejecución
    grupos_asientos_disputa = [
        ["1A", "1B", "1C", "1D", "2A"],
        ["2A", "2B", "2C", "3A", "3B"],
        ["1A", "2A", "3A", "1C", "2C"]
    ]
    asientos_objetivo = random.choice(grupos_asientos_disputa)

    def tarea_agente(id_agente):
        tid = get_kernel_tid()
        sistema_vuelo.add_log(f"🧵 Hilo Agente-{id_agente:02d} (TID Kernel: {tid}) compitiendo...")
        for id_asiento in asientos_objetivo:
            pasajero_nombre = f"Pasajero_{id_agente}_{random.randint(100, 999)}"
            if modo_protegido:
                sistema_vuelo.reservar_sincronizado(id_asiento, pasajero_nombre, id_agente)
            else:
                sistema_vuelo.reservar_sin_sincronizar(id_asiento, pasajero_nombre, id_agente)

    for i in range(1, num_agentes + 1):
        t = threading.Thread(target=tarea_agente, args=(i,), name=f"HiloAgente-{i}")
        hilos.append(t)
        t.start()

    for t in hilos:
        t.join()

    return obtener_estado_vuelo()


if __name__ == '__main__':
    app.run(debug=True, port=5000)