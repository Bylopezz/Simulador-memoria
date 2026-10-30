import os
import time
import random
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    import libsql_experimental as libsql
    HAS_LIBSQL = True
except Exception as e:
    HAS_LIBSQL = False
    print(f"[WARN] libsql_experimental no disponible: {e}")

FRONTEND_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_FOLDER, static_url_path='')
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'wiki.db')
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# ==========================================
# CONEXIÓN A BASE DE DATOS (TURSO / SQLITE)
# ==========================================
def get_db_connection():
    if HAS_LIBSQL and TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try:
            url = TURSO_DATABASE_URL.strip()
            token = TURSO_AUTH_TOKEN.strip()
            return libsql.connect(url, auth_token=token)
        except Exception as e:
            print(f"[ERROR TURSO] Falló conexión a Turso Cloud: {e}. Usando SQLite local.")
    else:
        print("[WARN DB] Variables TURSO_DATABASE_URL o TURSO_AUTH_TOKEN no detectadas.")

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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

        conn.commit()
        conn.close()
        print("[DB OK] Estructura inicializada.")
    except Exception as e:
        print(f"[ERROR DB INIT]: {e}")

init_db()

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

# ==========================================
# 1. API DE WIKI, GLOSARIO Y AUDITORÍA
# ==========================================
@app.route('/api/inicio/resumen', methods=['GET'])
def resumen_inicio():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM publicaciones ORDER BY id DESC LIMIT 3")
        pubs = [dict(f) if isinstance(f, dict) else {
            "id": f[0], "titulo": f[1], "tipo": f[2], "categoria": f[3], "autor": f[4], "fecha": f[5], "contenido": f[6]
        } for f in cursor.fetchall()]
        
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
    except Exception as e:
        print(f"[ERROR RESUMEN]: {e}")
        return jsonify({"ultimas_publicaciones": [], "ultimos_cambios": []})

@app.route('/api/publicaciones', methods=['GET'])
def listar_publicaciones():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM publicaciones ORDER BY id DESC")
        resultado = [dict(f) if isinstance(f, dict) else {
            "id": f[0], "titulo": f[1], "tipo": f[2], "categoria": f[3], "autor": f[4], "fecha": f[5], "contenido": f[6]
        } for f in cursor.fetchall()]
        conn.close()
        return jsonify(resultado)
    except Exception as e:
        print(f"[ERROR LISTAR PUBLICACIONES]: {e}")
        return jsonify([])

@app.route('/api/publicaciones', methods=['POST'])
def crear_publicacion():
    try:
        data = request.json or {}
        conn = get_db_connection()
        cursor = conn.cursor()
        fecha_actual = time.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data.get('titulo', ''), data.get('tipo', 'Concepto'), data.get('categoria', ''), data.get('autor', 'Anonimo'), fecha_actual, data.get('contenido', '')))
        new_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO historial_publicaciones (publicacion_id, tipo_accion, titulo_anterior, contenido_anterior, autor_modificador)
            VALUES (?, 'CREACION', ?, ?, ?)
        ''', (new_id, data.get('titulo', ''), data.get('contenido', ''), data.get('autor', 'Anonimo')))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "id": new_id}), 201
    except Exception as e:
        print(f"[ERROR CREAR]: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/publicaciones/<int:pub_id>', methods=['PUT'])
def editar_publicacion(pub_id):
    try:
        data = request.json or {}
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE publicaciones SET titulo = ?, tipo = ?, categoria = ?, autor = ?, contenido = ? WHERE id = ?
        ''', (data.get('titulo', ''), data.get('tipo', ''), data.get('categoria', ''), data.get('autor', ''), data.get('contenido', ''), pub_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/historial-general', methods=['GET'])
def historial_general():
    try:
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
    except Exception as e:
        return jsonify([])

@app.route('/api/publicaciones/<int:pub_id>/historial', methods=['GET'])
def historial_articulo(pub_id):
    try:
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
    except Exception as e:
        return jsonify([])

@app.route('/api/publicaciones/<int:pub_id>/restaurar/<int:historial_id>', methods=['POST'])
def restaurar_version(pub_id, historial_id):
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 2. SIMULADOR DE MEMORIA RAM (TIEMPO REAL)
# ==========================================
simulador_ram = {
    "usada": 0,
    "procesos_ejecucion": [],
    "cola_espera": [],
    "siguiente_id": 1
}
CAPACIDAD_MAXIMA_RAM = 1024

def actualizar_cronograma_ram():
    ahora = time.time()
    en_ejecucion_activos = []
    for p in simulador_ram["procesos_ejecucion"]:
        transcurrido = ahora - p["tiempo_inicio"]
        if transcurrido >= p["duracion"]:
            simulador_ram["usada"] -= p["tamano"]
        else:
            p_info = dict(p)
            p_info["tiempo_restante"] = max(1, int(p["duracion"] - transcurrido))
            en_ejecucion_activos.append(p_info)
    simulador_ram["procesos_ejecucion"] = en_ejecucion_activos

    cola_restante = []
    for p in simulador_ram["cola_espera"]:
        if simulador_ram["usada"] + p["tamano"] <= CAPACIDAD_MAXIMA_RAM:
            p["tiempo_inicio"] = ahora
            simulador_ram["usada"] += p["tamano"]
            p_info = dict(p)
            p_info["tiempo_restante"] = p["duracion"]
            simulador_ram["procesos_ejecucion"].append(p_info)
        else:
            cola_restante.append(p)
    simulador_ram["cola_espera"] = cola_restante

@app.route('/api/simulador-ram/estado', methods=['GET'])
def estado_ram():
    actualizar_cronograma_ram()
    return jsonify({
        "capacidad_total": CAPACIDAD_MAXIMA_RAM,
        "usada": simulador_ram["usada"],
        "libre": CAPACIDAD_MAXIMA_RAM - simulador_ram["usada"],
        "procesos_ejecucion": simulador_ram["procesos_ejecucion"],
        "cola_espera": simulador_ram["cola_espera"]
    })

@app.route('/api/simulador-ram/agregar', methods=['POST'])
def agregar_proceso_ram():
    data = request.json or {}
    nombre = data.get('nombre') or f'Proceso_{simulador_ram["siguiente_id"]}'
    tamano = int(data.get('tamano', 128))
    duracion = int(data.get('duracion', 15))
    
    proceso = {
        "id": simulador_ram["siguiente_id"],
        "nombre": nombre,
        "tamano": tamano,
        "duracion": duracion,
        "tiempo_inicio": time.time()
    }
    simulador_ram["siguiente_id"] += 1

    if simulador_ram["usada"] + tamano <= CAPACIDAD_MAXIMA_RAM:
        simulador_ram["usada"] += tamano
        simulador_ram["procesos_ejecucion"].append(proceso)
        estado_msg = "ejecucion"
    else:
        simulador_ram["cola_espera"].append(proceso)
        estado_msg = "espera"

    return jsonify({"status": "ok", "ubicacion": estado_msg, "proceso": proceso})

@app.route('/api/simulador-ram/lote-aleatorio', methods=['POST'])
def generar_lote_ram():
    nombres = ["Servidor_DB", "Modelo_ML", "Contenedor_App", "Script_Worker", "Cache_Redis"]
    creados = 0
    for _ in range(4):
        tamano = random.choice([64, 128, 256, 512])
        duracion = random.randint(15, 30)
        nombre = f"{random.choice(nombres)}_{simulador_ram['siguiente_id']}"
        
        proceso = {
            "id": simulador_ram["siguiente_id"],
            "nombre": nombre,
            "tamano": tamano,
            "duracion": duracion,
            "tiempo_inicio": time.time()
        }
        simulador_ram["siguiente_id"] += 1

        if simulador_ram["usada"] + tamano <= CAPACIDAD_MAXIMA_RAM:
            simulador_ram["usada"] += tamano
            simulador_ram["procesos_ejecucion"].append(proceso)
        else:
            simulador_ram["cola_espera"].append(proceso)
        creados += 1

    return jsonify({"status": "ok", "creados": creados})

@app.route('/api/simulador-ram/reset', methods=['POST'])
def reset_ram():
    global simulador_ram
    simulador_ram = {
        "usada": 0,
        "procesos_ejecucion": [],
        "cola_espera": [],
        "siguiente_id": 1
    }
    return jsonify({"status": "reset"})

# ==========================================
# 3. SIMULADOR CONCURRENCIA GLOBAL (20 HILOS + PID/THREAD ID + AUTO-LIMPIEZA 5S)
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
        self.hilos_activos = 0
        self.ultimo_cambio = time.time()

    def verificar_expiracion_y_limpieza(self):
        ahora = time.time()
        pid = os.getpid()
        
        if self.mutex_bloqueado and (ahora - self.mutex_timestamp > self.ttl_segundos):
            self.mutex_bloqueado = False
            self.logs.append(f"[PID: {pid}] [KERNEL {time.strftime('%H:%M:%S')}] Mutex Auto-Released tras 30s TTL.")

        asientos_ocupados = any(info['pasajero'] is not None or info['total_asignaciones'] > 0 for info in self.asientos.values())
        if self.hilos_activos == 0 and asientos_ocupados and (ahora - self.ultimo_cambio >= 5.0):
            self.asientos = {f"{f}{c}": {"pasajero": None, "overbooking": False, "total_asignaciones": 0} 
                            for f in [1, 2, 3] for c in ['A', 'B', 'C', 'D']}
            self.mutex_bloqueado = False
            self.logs.append(f"[PID: {pid}] [KERNEL {time.strftime('%H:%M:%S')}] Auto-limpieza: Mapa de asientos reiniciado tras finalizar la simulación.")

vuelo_global = VueloGlobal()

def _ejecutar_asignacion(asiento_id, pasajero, con_mutex):
    asiento = vuelo_global.asientos[asiento_id]
    pid = os.getpid()
    tid = threading.get_ident()
    prefix = f"[PID: {pid} | Thread: {tid}]"
    
    if con_mutex:
        if asiento['pasajero'] is None:
            asiento['pasajero'] = pasajero
            asiento['total_asignaciones'] = 1
            vuelo_global.logs.append(f"{prefix} [MUTEX PROTECTED] Asiento {asiento_id} reservado exitosamente para {pasajero}.")
        else:
            vuelo_global.logs.append(f"{prefix} [MUTEX PREVENTED] Asiento {asiento_id} ocupado por {asiento['pasajero']}. Reserva de {pasajero} rechazada.")
    else:
        asiento['total_asignaciones'] += 1
        if asiento['pasajero'] is None:
            asiento['pasajero'] = pasajero
            vuelo_global.logs.append(f"{prefix} [SIN MUTEX] Asiento {asiento_id} reservado por {pasajero}.")
        else:
            asiento['overbooking'] = True
            vuelo_global.logs.append(f"{prefix} [RACE CONDITION] ¡COLISIÓN en {asiento_id}! {pasajero} compite contra {asiento['pasajero']}.")
    
    vuelo_global.ultimo_cambio = time.time()

@app.route('/api/simulador-concurrencia/estado', methods=['GET'])
def estado_concurrencia():
    vuelo_global.verificar_expiracion_y_limpieza()
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
            "overbooking": info['overbooking'],
            "total_asignaciones": info['total_asignaciones']
        })

    return jsonify({
        "pid": os.getpid(),
        "asientos": asientos_list,
        "asientos_con_overbooking": overbooking_count,
        "conteo_exito": conteo_exito,
        "mutex_activado": vuelo_global.mutex_activado,
        "mutex_bloqueado": vuelo_global.mutex_bloqueado,
        "hilos_activos": vuelo_global.hilos_activos,
        "logs": vuelo_global.logs[-15:]
    })

@app.route('/api/simulador-concurrencia/toggle-mutex', methods=['POST'])
def toggle_mutex():
    data = request.json or {}
    pid = os.getpid()
    if 'activar' in data:
        vuelo_global.mutex_activado = bool(data['activar'])
    else:
        vuelo_global.mutex_activado = not vuelo_global.mutex_activado
    
    estado = "ACTIVADO" if vuelo_global.mutex_activado else "DESACTIVADO"
    vuelo_global.logs.append(f"[PID: {pid}] [KERNEL] Mutex {estado} por el usuario.")
    return jsonify({"mutex_activado": vuelo_global.mutex_activado})

@app.route('/api/simulador-concurrencia/reservar', methods=['POST'])
def reservar_asiento():
    data = request.json or {}
    asiento_id = data.get('asiento_id')
    pasajero = data.get('pasajero', 'Usuario_Web')
    
    if asiento_id not in vuelo_global.asientos:
        return jsonify({"error": "Asiento no valido"}), 400

    def procesar_reserva():
        vuelo_global.hilos_activos += 1
        try:
            if vuelo_global.mutex_activado:
                vuelo_global.mutex_bloqueado = True
                vuelo_global.mutex_timestamp = time.time()
                with vuelo_global.lock:
                    time.sleep(0.8)
                    _ejecutar_asignacion(asiento_id, pasajero, con_mutex=True)
                vuelo_global.mutex_bloqueado = False
            else:
                time.sleep(0.1)
                _ejecutar_asignacion(asiento_id, pasajero, con_mutex=False)
        finally:
            vuelo_global.hilos_activos = max(0, vuelo_global.hilos_activos - 1)
            vuelo_global.ultimo_cambio = time.time()

    t = threading.Thread(target=procesar_reserva)
    t.start()
    return jsonify({"status": "ok"})

@app.route('/api/simulador-concurrencia/rafaga-hilos', methods=['POST'])
def rafaga_hilos():
    asientos_llaves = list(vuelo_global.asientos.keys())
    
    def lanzar_hilo(i):
        vuelo_global.hilos_activos += 1
        try:
            time.sleep(random.uniform(0.1, 1.2))
            asiento_tarjeta = random.choice(asientos_llaves)
            pasajero_nombre = f"Hilo_{i}"
            
            if vuelo_global.mutex_activado:
                vuelo_global.mutex_bloqueado = True
                vuelo_global.mutex_timestamp = time.time()
                with vuelo_global.lock:
                    time.sleep(0.5)
                    _ejecutar_asignacion(asiento_tarjeta, pasajero_nombre, con_mutex=True)
                vuelo_global.mutex_bloqueado = False
            else:
                time.sleep(0.2)
                _ejecutar_asignacion(asiento_tarjeta, pasajero_nombre, con_mutex=False)
        finally:
            vuelo_global.hilos_activos = max(0, vuelo_global.hilos_activos - 1)
            vuelo_global.ultimo_cambio = time.time()

    for i in range(1, 21):
        t = threading.Thread(target=lanzar_hilo, args=(i,))
        t.start()

    return jsonify({"status": "rafaga_iniciada", "hilos": 20})

@app.route('/api/simulador-concurrencia/reset', methods=['POST'])
def reset_concurrencia():
    pid = os.getpid()
    vuelo_global.asientos = {f"{f}{c}": {"pasajero": None, "overbooking": False, "total_asignaciones": 0} 
                            for f in [1, 2, 3] for c in ['A', 'B', 'C', 'D']}
    vuelo_global.logs = [f"[PID: {pid}] [KERNEL] Estado de vuelo reiniciado."]
    vuelo_global.mutex_bloqueado = False
    vuelo_global.hilos_activos = 0
    return jsonify({"status": "reset"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)