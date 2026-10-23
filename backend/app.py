import os
import time
import random
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# Intentar importar libSQL para conexión remota a Turso DB
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
# CONEXIÓN Y CONFIGURACIÓN DE BASE DE DATOS
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
    
    # 2. Tabla de Auditoría e Historial de Cambios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_publicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publicacion_id INTEGER,
            tipo_accion TEXT NOT NULL,
            titulo_anterior TEXT NOT NULL,
            contenido_anterior TEXT NOT NULL,
            autor_modificador TEXT NOT NULL,
            fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # 3. Triggers automáticos para capturar ediciones y eliminaciones
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS respaldar_antes_de_editar
        BEFORE UPDATE ON publicaciones
        FOR EACH ROW
        BEGIN
            INSERT INTO historial_publicaciones (
                publicacion_id, tipo_accion, titulo_anterior, contenido_anterior, autor_modificador
            )
            VALUES (OLD.id, 'EDICION', OLD.titulo, OLD.contenido, OLD.autor);
        END;
    ''')

    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS respaldar_antes_de_eliminar
        BEFORE DELETE ON publicaciones
        FOR EACH ROW
        BEGIN
            INSERT INTO historial_publicaciones (
                publicacion_id, tipo_accion, titulo_anterior, contenido_anterior, autor_modificador
            )
            VALUES (OLD.id, 'ELIMINACION', OLD.titulo, OLD.contenido, OLD.autor);
        END;
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 1. RUTAS DE LA WIKI, AUDITORÍA E HISTORIAL
# ==========================================

@app.route('/api/inicio/resumen', methods=['GET'])
def resumen_inicio():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Últimas 3 publicaciones
    cursor.execute("SELECT * FROM publicaciones ORDER BY id DESC LIMIT 3")
    pubs = [dict(f) if isinstance(f, dict) else {
        "id": f[0], "titulo": f[1], "tipo": f[2], "categoria": f[3], "autor": f[4], "fecha": f[5], "contenido": f[6]
    } for f in cursor.fetchall()]
    
    # Últimos 3 cambios registrados en la auditoría
    cursor.execute("""
        SELECT id, publicacion_id, tipo_accion, titulo_anterior, autor_modificador, fecha_modificacion 
        FROM historial_publicaciones 
        ORDER BY id DESC LIMIT 3
    """)
    cambios = [dict(c) if isinstance(c, dict) else {
        "id": c[0], "publicacion_id": c[1], "tipo_accion": c[2], 
        "titulo_anterior": c[3], "autor_modificador": c[4], "fecha_modificacion": c[5]
    } for c in cursor.fetchall()]
    
    conn.close()
    return jsonify({"ultimas_publicaciones": pubs, "ultimos_cambios": cambios})

@app.route('/api/publicaciones', methods=['GET'])
def listar_publicaciones():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM publicaciones ORDER BY id DESC")
    resultado = [dict(f) if isinstance(f, dict) else {
        "id": f[0], "titulo": f[1], "tipo": f[2], "categoria": f[3], "autor": f[4], "fecha": f[5], "contenido": f[6]
    } for f in cursor.fetchall()]
    conn.close()
    return jsonify(resultado)

@app.route('/api/publicaciones', methods=['POST'])
def crear_publicacion():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    fecha_actual = time.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['titulo'], data['tipo'], data['categoria'], data['autor'], fecha_actual, data['contenido']))
    new_id = cursor.lastrowid
    
    # Registrar auditoría de creación
    cursor.execute('''
        INSERT INTO historial_publicaciones (publicacion_id, tipo_accion, titulo_anterior, contenido_anterior, autor_modificador)
        VALUES (?, 'CREACION', ?, ?, ?)
    ''', (new_id, data['titulo'], data['contenido'], data['autor']))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201

@app.route('/api/publicaciones/<int:pub_id>', methods=['PUT'])
def editar_publicacion(pub_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE publicaciones SET titulo = ?, tipo = ?, categoria = ?, autor = ?, contenido = ? WHERE id = ?
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

@app.route('/api/historial-general', methods=['GET'])
def historial_general():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, publicacion_id, tipo_accion, titulo_anterior, autor_modificador, fecha_modificacion 
        FROM historial_publicaciones 
        ORDER BY id DESC
    """)
    filas = cursor.fetchall()
    conn.close()
    resultado = [dict(h) if isinstance(h, dict) else {
        "id": h[0], "publicacion_id": h[1], "tipo_accion": h[2],
        "titulo_anterior": h[3], "autor_modificador": h[4], "fecha_modificacion": h[5]
    } for h in filas]
    return jsonify(resultado)

@app.route('/api/publicaciones/<int:pub_id>/historial', methods=['GET'])
def historial_articulo(pub_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, publicacion_id, tipo_accion, titulo_anterior, contenido_anterior, autor_modificador, fecha_modificacion 
        FROM historial_publicaciones 
        WHERE publicacion_id = ? 
        ORDER BY id DESC
    """, (pub_id,))
    filas = cursor.fetchall()
    conn.close()
    resultado = [dict(h) if isinstance(h, dict) else {
        "id": h[0], "publicacion_id": h[1], "tipo_accion": h[2], "titulo_anterior": h[3],
        "contenido_anterior": h[4], "autor_modificador": h[5], "fecha_modificacion": h[6]
    } for h in filas]
    return jsonify(resultado)

@app.route('/api/publicaciones/<int:pub_id>/restaurar/<int:historial_id>', methods=['POST'])
def restaurar_version(pub_id, historial_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo_anterior, contenido_anterior FROM historial_publicaciones WHERE id = ?", (historial_id,))
    version = cursor.fetchone()
    if not version:
        conn.close()
        return jsonify({"error": "No encontrado"}), 404
        
    tit = version['titulo_anterior'] if isinstance(version, dict) else version[0]
    cont = version['contenido_anterior'] if isinstance(version, dict) else version[1]
    
    cursor.execute("UPDATE publicaciones SET titulo = ?, contenido = ? WHERE id = ?", (tit, cont, pub_id))
    
    cursor.execute('''
        INSERT INTO historial_publicaciones (publicacion_id, tipo_accion, titulo_anterior, contenido_anterior, autor_modificador)
        VALUES (?, 'RESTAURACION', ?, ?, 'Sistema')
    ''', (pub_id, tit, cont))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "restored"})

# ==========================================
# 2. SIMULADOR DE MEMORIA RAM (POR SESIÓN)
# ==========================================
simuladores_ram = {}
CAPACIDAD_MAXIMA_RAM = 1024

def obtener_ram_sesion(session_id):
    if not session_id:
        session_id = "default_session"
    if session_id not in simuladores_ram:
        simuladores_ram[session_id] = {
            "usada": 0, "procesos_ejecucion": [], "cola_espera": [], "siguiente_id": 1
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
    data = request.json or {}
    session_id = data.get('session_id', 'default_session')
    ram = obtener_ram_sesion(session_id)
    
    nombre = data.get('nombre', f'Proceso_{ram["siguiente_id"]}')
    tamano = int(data.get('tamano', 128))
    duracion = int(data.get('duracion', 10))
    
    proceso = {
        "id": ram["siguiente_id"], "nombre": nombre,
        "tamano": tamano, "duracion": duracion, "tiempo_inicio": time.time()
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
            "id": ram["siguiente_id"], "nombre": nombre,
            "tamano": tamano, "duracion": duracion, "tiempo_inicio": time.time()
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
        "usada": 0, "procesos_ejecucion": [], "cola_espera": [], "siguiente_id": 1
    }
    return jsonify({"status": "reset"})

# ==========================================
# 3. SIMULADOR CONCURRENCIA GLOBAL (MUTEX 30s)
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
    data = request.json or {}
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
        vuelo_global.logs.append(f"⚠️ [RACE CONDITION] Colision en {asiento_id}: {pasajero} compite con {asiento['pasajero']}.")

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
# 4. SIMULADOR ALGORITMO DEL BANQUERO
# ==========================================
CASOS_BANQUERO = {
    "caso_1_seguro": {
        "titulo": "Caso 1: Estado Seguro Standard (5 Procesos, 3 Recursos)",
        "recursos_disponibles": [3, 3, 2],
        "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
        "max": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
    },
    "caso_2_inseguro": {
        "titulo": "Caso 2: Estado Inseguro / Riesgo de Deadlock",
        "recursos_disponibles": [1, 0, 0],
        "allocation": [[2, 1, 1], [1, 1, 0], [0, 0, 1]],
        "max": [[4, 2, 2], [2, 2, 1], [1, 1, 1]]
    }
}

@app.route('/api/banquero/casos-ejemplo', methods=['GET'])
def obtener_casos_banquero():
    return jsonify(CASOS_BANQUERO)

@app.route('/api/banquero/evaluar', methods=['POST'])
def evaluar_banquero():
    data = request.json or {}
    disponibles = data.get('disponibles', [])
    allocation = data.get('allocation', [])
    max_matrix = data.get('max', [])
    
    num_p = len(allocation)
    num_r = len(disponibles)
    need = [[max_matrix[i][j] - allocation[i][j] for j in range(num_r)] for i in range(num_p)]
    
    work = list(disponibles)
    finish = [False] * num_p
    secuencia = []
    pasos = []
    
    for _ in range(num_p):
        encontrado = False
        for i in range(num_p):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(num_r)):
                work_prev = list(work)
                for j in range(num_r):
                    work[j] += allocation[i][j]
                finish[i] = True
                secuencia.append(f"P{i}")
                encontrado = True
                pasos.append({
                    "proceso": f"P{i}", "need": need[i],
                    "work_prev": work_prev, "liberado": allocation[i], "work_nuevo": list(work)
                })
                break
        if not encontrado:
            break
            
    es_seguro = all(finish)
    return jsonify({
        "es_seguro": es_seguro,
        "secuencia_segura": secuencia if es_seguro else [],
        "need": need, "pasos": pasos,
        "procesos_bloqueados": [f"P{i}" for i in range(num_p) if not finish[i]]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)