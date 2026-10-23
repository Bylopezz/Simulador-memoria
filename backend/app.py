import os
import time
import uuid
import random
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# Intentar la conexión con la librería de Turso (libSQL)
try:
    import libsql_experimental as libsql
    HAS_LIBSQL = True
except ImportError:
    HAS_LIBSQL = False

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'wiki.db')
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# ==========================================
# CONEXIÓN A BASE DE DATOS (TURSO / SQLITE)
# ==========================================
def get_db_connection():
    if HAS_LIBSQL and TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        return libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabla principal de la Wiki
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS publicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            autor TEXT NOT NULL,
            fecha TEXT NOT NULL,
            contenido TEXT NOT NULL
        );
    ''')
    
    # 2. Tabla de Historial (Auditoría)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_publicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publicacion_id INTEGER NOT NULL,
            titulo_anterior TEXT NOT NULL,
            contenido_anterior TEXT NOT NULL,
            autor_modificador TEXT NOT NULL,
            fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # 3. TRIGGER: Respaldo automático antes de actualizar
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS respaldar_antes_de_editar
        BEFORE UPDATE ON publicaciones
        FOR EACH ROW
        BEGIN
            INSERT INTO historial_publicaciones (
                publicacion_id, 
                titulo_anterior, 
                contenido_anterior, 
                autor_modificador
            )
            VALUES (
                OLD.id, 
                OLD.titulo, 
                OLD.contenido, 
                OLD.autor
            );
        END;
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# SIMULADOR RAM (AISLADO POR SESSION-ID)
# ==========================================
simuladores_ram = {}
CAPACIDAD_MAXIMA_RAM = 1024  # MB

def obtener_ram_sesion(session_id):
    if not session_id:
        session_id = "default_session"
    if session_id not in simuladores_ram:
        simuladores_ram[session_id] = {
            "usada": 0,
            "procesos_ejecucion": [],
            "cola_espera": [],
            "siguiente_id": 1
        }
    return simuladores_ram[session_id]

@app.route('/api/simulador-ram/estado', methods=['GET'])
def estado_ram():
    session_id = request.args.get('session_id', 'default_session')
    ram = obtener_ram_sesion(session_id)
    return jsonify({
        "capacidad_total": CAPACIDAD_MAXIMA_RAM,
        "usada": ram["usada"],
        "libre": CAPACIDAD_MAXIMA_RAM - ram["usada"],
        "procesos_ejecucion": ram["procesos_ejecucion"],
        "cola_espera": ram["cola_espera"]
    })

@app.route('/api/simulador-ram/agregar', methods=['POST'])
def agregar_proceso_ram():
    data = request.json
    session_id = data.get('session_id', 'default_session')
    ram = obtener_ram_sesion(session_id)
    
    nombre = data.get('nombre', f'Proceso_{ram["siguiente_id"]}')
    tamano = int(data.get('tamano', 128))
    duracion = int(data.get('duracion', 10))
    
    proceso = {
        "id": ram["siguiente_id"],
        "nombre": nombre,
        "tamano": tamano,
        "duracion": duracion,
        "tiempo_inicio": time.time()
    }
    ram["siguiente_id"] += 1

    if ram["usada"] + tamano <= CAPACIDAD_MAXIMA_RAM:
        ram["usada"] += tamano
        ram["procesos_ejecucion"].append(proceso)
        estado_msg = "ejecucion"
    else:
        ram["cola_espera"].append(proceso)
        estado_msg = "espera"

    return jsonify({"status": "ok", "ubicacion": estado_msg, "proceso": proceso})

@app.route('/api/simulador-ram/lote-aleatorio', methods=['POST'])
def generar_lote_ram():
    data = request.json or {}
    session_id = data.get('session_id', 'default_session')
    ram = obtener_ram_sesion(session_id)

    nombres = ["Servidor_MySQL", "Modelo_PyTorch", "Contenedor_Docker", "Script_Python", "Cache_Redis"]
    creados = 0
    for _ in range(4):
        tamano = random.choice([64, 128, 256, 512])
        duracion = random.randint(15, 30)
        nombre = f"{random.choice(nombres)}_{ram['siguiente_id']}"
        
        proceso = {
            "id": ram["siguiente_id"],
            "nombre": nombre,
            "tamano": tamano,
            "duracion": duracion,
            "tiempo_inicio": time.time()
        }
        ram["siguiente_id"] += 1

        if ram["usada"] + tamano <= CAPACIDAD_MAXIMA_RAM:
            ram["usada"] += tamano
            ram["procesos_ejecucion"].append(proceso)
        else:
            ram["cola_espera"].append(proceso)
        creados += 1

    return jsonify({"status": "ok", "creados": creados})

@app.route('/api/simulador-ram/reset', methods=['POST'])
def reset_ram():
    data = request.json or {}
    session_id = data.get('session_id', 'default_session')
    simuladores_ram[session_id] = {
        "usada": 0,
        "procesos_ejecucion": [],
        "cola_espera": [],
        "siguiente_id": 1
    }
    return jsonify({"status": "reset"})

# ==========================================
# CONCURRENCIA GLOBAL CON MUTEX (TTL 30s)
# ==========================================
class VueloGlobal:
    def __init__(self):
        self.lock = threading.Lock()
        self.asientos = {f"{f}{c}": {"pasajero": None, "overbooking": False, "total_asignaciones": 0} 
                        for f in [1, 2, 3] for c in ['A', 'B', 'C', 'D']}
        self.logs = []
        self.mutex_activado = False
        self.mutex_bloqueado = False
        self.mutex_timestamp = 0
        self.ttl_segundos = 30

    def verificar_expiracion_mutex(self):
        if self.mutex_bloqueado and (time.time() - self.mutex_timestamp > self.ttl_segundos):
            self.mutex_bloqueado = False
            self.logs.append(f"⏰ [KERNEL {time.strftime('%H:%M:%S')}] Mutex Auto-Released tras 30s TTL.")

vuelo_global = VueloGlobal()

@app.route('/api/simulador-concurrencia/estado', methods=['GET'])
def estado_concurrencia():
    vuelo_global.verificar_expiracion_mutex()
    
    asientos_list = []
    overbooking_count = 0
    conteo_exito = 0
    
    for id_a, info in vuelo_global.asientos.items():
        if info['total_asignaciones'] > 1:
            overbooking_count += 1
        if info['pasajero']:
            conteo_exito += 1
            
        asientos_list.append({
            "id": id_a,
            "pasajero_confirmado": info['pasajero'],
            "overbooking": info['total_asignaciones'] > 1,
            "total_asignaciones": info['total_asignaciones']
        })

    return jsonify({
        "pid": os.getpid(),
        "asientos": asientos_list,
        "asientos_con_overbooking": overbooking_count,
        "conteo_exito": conteo_exito,
        "mutex_activado": vuelo_global.mutex_activado,
        "mutex_bloqueado": vuelo_global.mutex_bloqueado,
        "logs": vuelo_global.logs[-15:]
    })

@app.route('/api/simulador-concurrencia/toggle-mutex', methods=['POST'])
def toggle_mutex():
    data = request.json or {}
    vuelo_global.mutex_activado = data.get('activar', not vuelo_global.mutex_activado)
    estado = "ACTIVADO" if vuelo_global.mutex_activado else "DESACTIVADO"
    vuelo_global.logs.append(f"🔒 [KERNEL] Mutex {estado} por el usuario.")
    return jsonify({"mutex_activado": vuelo_global.mutex_activado})

@app.route('/api/simulador-concurrencia/reservar', methods=['POST'])
def reservar_asiento():
    data = request.json
    asiento_id = data.get('asiento_id')
    pasajero = data.get('pasajero', 'Usuario_Web')
    
    if asiento_id not in vuelo_global.asientos:
        return jsonify({"error": "Asiento no valido"}), 400

    def procesar_reserva():
        if vuelo_global.mutex_activado:
            vuelo_global.mutex_bloqueado = True
            vuelo_global.mutex_timestamp = time.time()
            with vuelo_global.lock:
                _ejecutar_asignacion(asiento_id, pasajero)
            vuelo_global.mutex_bloqueado = False
        else:
            _ejecutar_asignacion(asiento_id, pasajero)

    t = threading.Thread(target=procesar_reserva)
    t.start()
    t.join()

    return jsonify({"status": "ok"})

def _ejecutar_asignacion(asiento_id, pasajero):
    asiento = vuelo_global.asientos[asiento_id]
    asiento['total_asignaciones'] += 1
    
    if asiento['pasajero'] is None:
        asiento['pasajero'] = pasajero
        vuelo_global.logs.append(f"✅ [HILO {threading.get_ident()}] Asiento {asiento_id} reservado para {pasajero}.")
    else:
        asiento['overbooking'] = True
        vuelo_global.logs.append(f"⚠️ [RACE CONDITION] ¡Colisión en {asiento_id}! Intento de {pasajero} sobre {asiento['pasajero']}.")

@app.route('/api/simulador-concurrencia/rafaga-hilos', methods=['POST'])
def rafaga_hilos():
    asientos_llaves = list(vuelo_global.asientos.keys())
    
    def lanzar_hilo(i):
        asiento_tarjeta = random.choice(asientos_llaves)
        pasajero_nombre = f"Hilo_Simulado_{i}"
        
        if vuelo_global.mutex_activado:
            vuelo_global.mutex_bloqueado = True
            vuelo_global.mutex_timestamp = time.time()
            with vuelo_global.lock:
                _ejecutar_asignacion(asiento_tarjeta, pasajero_nombre)
            vuelo_global.mutex_bloqueado = False
        else:
            _ejecutar_asignacion(asiento_tarjeta, pasajero_nombre)

    hilos = []
    for i in range(1, 11):
        t = threading.Thread(target=lanzar_hilo, args=(i,))
        hilos.append(t)
        t.start()

    return jsonify({"status": "rafaga_iniciada", "hilos": 10})

@app.route('/api/simulador-concurrencia/reset', methods=['POST'])
def reset_concurrencia():
    vuelo_global.asientos = {f"{f}{c}": {"pasajero": None, "overbooking": False, "total_asignaciones": 0} 
                            for f in [1, 2, 3] for c in ['A', 'B', 'C', 'D']}
    vuelo_global.logs = ["🔄 [KERNEL] Estado de vuelo reiniciado."]
    vuelo_global.mutex_bloqueado = False
    return jsonify({"status": "reset"})

# ==========================================
# RUTAS CRUD WIKI Y HISTORIAL
# ==========================================
@app.route('/api/publicaciones', methods=['GET'])
def listar_publicaciones():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM publicaciones ORDER BY id DESC")
    filas = cursor.fetchall()
    conn.close()
    
    resultado = []
    for f in filas:
        if isinstance(f, dict):
            resultado.append(f)
        else:
            resultado.append({
                "id": f[0], "titulo": f[1], "tipo": f[2], 
                "categoria": f[3], "autor": f[4], "fecha": f[5], "contenido": f[6]
            })
    return jsonify(resultado)

@app.route('/api/publicaciones', methods=['POST'])
def crear_publicacion():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    fecha_actual = time.strftime('%Y-%m-%d')
    
    cursor.execute('''
        INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['titulo'], data['tipo'], data['categoria'], data['autor'], fecha_actual, data['contenido']))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 201

@app.route('/api/publicaciones/<int:pub_id>', methods=['PUT'])
def editar_publicacion(pub_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE publicaciones 
        SET titulo = ?, tipo = ?, categoria = ?, autor = ?, contenido = ?
        WHERE id = ?
    ''', (data['titulo'], data['tipo'], data['categoria'], data['autor'], data['contenido'], pub_id))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})

@app.route('/api/publicaciones/<int:pub_id>', methods=['DELETE'])
def eliminar_publicacion(pub_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM publicaciones WHERE id = ?", (pub_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route('/api/publicaciones/<int:pub_id>/historial', methods=['GET'])
def obtener_historial(pub_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, publicacion_id, titulo_anterior, contenido_anterior, autor_modificador, fecha_modificacion 
        FROM historial_publicaciones 
        WHERE publicacion_id = ? 
        ORDER BY id DESC
    ''', (pub_id,))
    versiones = cursor.fetchall()
    conn.close()
    
    resultado = []
    for v in versiones:
        if isinstance(v, dict):
            resultado.append(v)
        else:
            resultado.append({
                "id": v[0], "publicacion_id": v[1], "titulo_anterior": v[2],
                "contenido_anterior": v[3], "autor_modificador": v[4], "fecha_modificacion": v[5]
            })
    return jsonify(resultado)

@app.route('/api/publicaciones/<int:pub_id>/restaurar/<int:historial_id>', methods=['POST'])
def restaurar_historial(pub_id, historial_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT titulo_anterior, contenido_anterior FROM historial_publicaciones WHERE id = ?', (historial_id,))
    version = cursor.fetchone()
    if not version:
        conn.close()
        return jsonify({"error": "No encontrado"}), 404
        
    tit = version['titulo_anterior'] if isinstance(version, dict) else version[0]
    cont = version['contenido_anterior'] if isinstance(version, dict) else version[1]
    
    cursor.execute('UPDATE publicaciones SET titulo = ?, contenido = ? WHERE id = ?', (tit, cont, pub_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "restored"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)