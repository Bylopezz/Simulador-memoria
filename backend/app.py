import os
import sqlite3
import threading
import time
import random

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Carga condicional de libSQL (Turso)
try:
    import libsql_experimental as libsql
except ImportError:
    libsql = None

# Configuración de rutas base
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
frontend_folder = os.path.join(base_dir, 'frontend')
db_path = os.path.join(os.path.dirname(__file__), 'wiki.db')

app = Flask(__name__, static_folder=frontend_folder)
CORS(app)

# Variables de entorno para Turso
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

# ==========================================
# CONEXIÓN A BASE DE DATOS (TURSO / SQLITE FALLBACK)
# ==========================================
def get_db_connection():
    """Intenta conectar a Turso en la nube; si falla o no hay credenciales, usa SQLite local."""
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN and libsql:
        try:
            conn = libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
            return conn, "turso"
        except Exception as e:
            print(f"⚠️ Fallo conexión Turso ({e}). Usando SQLite local...")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"

def execute_query(query, params=(), fetchall=False, fetchone=False, commit=False):
    """Helper para ejecutar queries independientemente del motor de BD (Turso o SQLite)."""
    conn, db_type = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = None
        
        if fetchall:
            rows = cursor.fetchall()
            if db_type == "sqlite":
                result = [dict(r) for r in rows]
            else:
                # Para Turso/libsql se mapean las filas a diccionarios
                cols = [description[0] for description in cursor.description] if cursor.description else []
                result = [dict(zip(cols, row)) for row in rows]
        elif fetchone:
            row = cursor.fetchone()
            if row:
                if db_type == "sqlite":
                    result = dict(row)
                else:
                    cols = [description[0] for description in cursor.description] if cursor.description else []
                    result = dict(zip(cols, row))
        
        if commit:
            conn.commit()
            
        last_id = getattr(cursor, 'lastrowid', None)
        return result, last_id
    finally:
        conn.close()

def init_db():
    """Inicializa la tabla principal, la tabla de auditoría y los Triggers SQL."""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()

    # Tabla principal de publicaciones
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

    # Tabla de auditoría e historial
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_publicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publicacion_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            autor TEXT NOT NULL,
            fecha TEXT NOT NULL,
            contenido TEXT NOT NULL,
            accion TEXT NOT NULL,
            fecha_cambio DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Triggers SQL para auditoría automática
    cursor.execute('DROP TRIGGER IF EXISTS trigger_auditoria_update')
    cursor.execute('''
        CREATE TRIGGER trigger_auditoria_update
        BEFORE UPDATE ON publicaciones
        BEGIN
            INSERT INTO historial_publicaciones (publicacion_id, titulo, tipo, categoria, autor, fecha, contenido, accion)
            VALUES (OLD.id, OLD.titulo, OLD.tipo, OLD.categoria, OLD.autor, OLD.fecha, OLD.contenido, 'UPDATE');
        END;
    ''')

    cursor.execute('DROP TRIGGER IF EXISTS trigger_auditoria_delete')
    cursor.execute('''
        CREATE TRIGGER trigger_auditoria_delete
        BEFORE DELETE ON publicaciones
        BEGIN
            INSERT INTO historial_publicaciones (publicacion_id, titulo, tipo, categoria, autor, fecha, contenido, accion)
            VALUES (OLD.id, OLD.titulo, OLD.tipo, OLD.categoria, OLD.autor, OLD.fecha, OLD.contenido, 'DELETE');
        END;
    ''')

    # Insertar datos iniciales si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM publicaciones')
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute('''
            INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            "Paginación y Segmentación",
            "Definición",
            "Sistemas Operativos",
            "Cátedra de SO",
            "2026-10-08",
            "<p>La <strong>paginación</strong> es un esquema de gestión de memoria que divide el espacio físico sin requerir bloques contiguos.</p>"
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
            "<p>Los árboles B+ optimizan el acceso a discos y bases de datos relacionales.</p>"
        ))

    conn.commit()
    conn.close()

# Inicialización al arrancar
init_db()

# ==========================================
# RUTAS DE SERVICIO DE FRONTEND (SPA)
# ==========================================
@app.route('/')
def serve_index():
    try:
        return app.send_static_file('index.html')
    except Exception:
        return send_from_directory(frontend_folder, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(frontend_folder, filename)

# ==========================================
# INICIO Y RESUMEN GENERAL
# ==========================================
@app.route('/api/inicio/resumen', methods=['GET'])
def obtener_resumen_inicio():
    try:
        ultimas_pubs, _ = execute_query('SELECT * FROM publicaciones ORDER BY id DESC LIMIT 3', fetchall=True)
        ultimos_logs, _ = execute_query('SELECT * FROM historial_publicaciones ORDER BY id DESC LIMIT 3', fetchall=True)
        return jsonify({
            "ultimas_publicaciones": ultimas_pubs or [],
            "ultimos_auditorias": ultimos_logs or []
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener resumen: {str(e)}"}), 500

# ==========================================
# RUTAS DE WIKI, GLOSARIO Y AUDITORÍA
# ==========================================
@app.route('/api/publicaciones', methods=['GET'])
def obtener_publicaciones():
    try:
        pubs, _ = execute_query('SELECT * FROM publicaciones ORDER BY id DESC', fetchall=True)
        return jsonify(pubs or []), 200
    except Exception as e:
        return jsonify({"error": f"Error al listar publicaciones: {str(e)}"}), 500

@app.route('/api/publicaciones/<int:pub_id>', methods=['GET'])
def obtener_publicacion_por_id(pub_id):
    try:
        pub, _ = execute_query('SELECT * FROM publicaciones WHERE id = ?', (pub_id,), fetchone=True)
        if not pub:
            return jsonify({"error": "Publicación no encontrada"}), 404
        return jsonify(pub), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener publicación: {str(e)}"}), 500

@app.route('/api/publicaciones', methods=['POST'])
def crear_publicacion():
    try:
        data = request.get_json() or {}
        titulo = data.get('titulo')
        contenido = data.get('contenido')
        
        if not titulo or not contenido:
            return jsonify({"error": "Título y contenido son requeridos."}), 400

        tipo = data.get('tipo', 'Definición')
        categoria = data.get('categoria', 'General')
        autor = data.get('autor', 'Anónimo')
        fecha = data.get('fecha', time.strftime('%Y-%m-%d'))

        query = '''
            INSERT INTO publicaciones (titulo, tipo, categoria, autor, fecha, contenido)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        _, nuevo_id = execute_query(query, (titulo, tipo, categoria, autor, fecha, contenido), commit=True)
        
        return jsonify({"id": nuevo_id, "titulo": titulo, "mensaje": "Publicación creada con éxito"}), 201
    except Exception as e:
        return jsonify({"error": f"Error al crear publicación: {str(e)}"}), 500

@app.route('/api/publicaciones/<int:pub_id>', methods=['PUT'])
def actualizar_publicacion(pub_id):
    try:
        data = request.get_json() or {}
        titulo = data.get('titulo')
        contenido = data.get('contenido')

        if not titulo or not contenido:
            return jsonify({"error": "Título y contenido son requeridos."}), 400

        tipo = data.get('tipo', 'Definición')
        categoria = data.get('categoria', 'General')
        autor = data.get('autor', 'Anónimo')
        fecha = data.get('fecha', time.strftime('%Y-%m-%d'))

        query = '''
            UPDATE publicaciones 
            SET titulo = ?, tipo = ?, categoria = ?, autor = ?, fecha = ?, contenido = ?
            WHERE id = ?
        '''
        execute_query(query, (titulo, tipo, categoria, autor, fecha, contenido, pub_id), commit=True)
        return jsonify({"mensaje": "Publicación actualizada y respaldada en auditoría", "id": pub_id}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar publicación: {str(e)}"}), 500

@app.route('/api/publicaciones/<int:pub_id>', methods=['DELETE'])
def eliminar_publicacion(pub_id):
    try:
        execute_query('DELETE FROM publicaciones WHERE id = ?', (pub_id,), commit=True)
        return jsonify({"mensaje": "Publicación eliminada y archivada en auditoría"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar publicación: {str(e)}"}), 500

@app.route('/api/historial-general', methods=['GET'])
def obtener_historial_general():
    try:
        logs, _ = execute_query('SELECT * FROM historial_publicaciones ORDER BY id DESC', fetchall=True)
        return jsonify(logs or []), 200
    except Exception as e:
        return jsonify({"error": f"Error al consultar auditoría: {str(e)}"}), 500

@app.route('/api/publicaciones/<int:pub_id>/historial', methods=['GET'])
def obtener_historial_publicacion(pub_id):
    try:
        logs, _ = execute_query('SELECT * FROM historial_publicaciones WHERE publicacion_id = ? ORDER BY id DESC', (pub_id,), fetchall=True)
        return jsonify(logs or []), 200
    except Exception as e:
        return jsonify({"error": f"Error al consultar historial del artículo: {str(e)}"}), 500

@app.route('/api/publicaciones/<int:pub_id>/restaurar/<int:historial_id>', methods=['POST'])
def restaurar_version(pub_id, historial_id):
    try:
        version, _ = execute_query('SELECT * FROM historial_publicaciones WHERE id = ?', (historial_id,), fetchone=True)
        if not version:
            return jsonify({"error": "Versión histórica no encontrada"}), 404

        query = '''
            UPDATE publicaciones 
            SET titulo = ?, tipo = ?, categoria = ?, autor = ?, fecha = ?, contenido = ?
            WHERE id = ?
        '''
        execute_query(query, (
            version['titulo'], version['tipo'], version['categoria'],
            version['autor'], version['fecha'], version['contenido'], pub_id
        ), commit=True)

        return jsonify({"mensaje": f"Publicación #{pub_id} restaurada con éxito a la versión de auditoría #{historial_id}"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al restaurar versión: {str(e)}"}), 500

# ==========================================
# SIMULADOR RAM (GLOBAL - 1024 MB)
# ==========================================
RAM_TOTAL_MB = 1024

estado_ram_global = {
    "ram_total_mb": RAM_TOTAL_MB,
    "ram_usada_mb": 0,
    "ram_disponible_mb": RAM_TOTAL_MB,
    "porcentaje_ram_usada": 0.0,
    "procesos_ejecucion": [],
    "cola_espera": [],
    "siguiente_id": 1
}

def actualizar_metricas_ram():
    usada = sum(p["tamano_mb"] for p in estado_ram_global["procesos_ejecucion"])
    estado_ram_global["ram_usada_mb"] = usada
    estado_ram_global["ram_disponible_mb"] = RAM_TOTAL_MB - usada
    estado_ram_global["porcentaje_ram_usada"] = round((usada / RAM_TOTAL_MB) * 100, 1)

def procesar_cola_espera_ram():
    i = 0
    while i < len(estado_ram_global["cola_espera"]):
        proc = estado_ram_global["cola_espera"][i]
        if proc["tamano_mb"] <= estado_ram_global["ram_disponible_mb"]:
            estado_ram_global["procesos_ejecucion"].append(proc)
            estado_ram_global["cola_espera"].pop(i)
            actualizar_metricas_ram()
        else:
            i += 1

@app.route('/api/simulador/estado', methods=['GET'])
def estado_ram():
    return jsonify(estado_ram_global), 200

@app.route('/api/simulador/crear', methods=['POST'])
def crear_proceso_ram():
    try:
        data = request.get_json() or {}
        nombre = data.get('nombre')
        tamano = int(data.get('tamano', 128))
        ttl = int(data.get('ttl', 20))

        if not nombre or tamano <= 0:
            return jsonify({"error": "Nombre y tamaño válidos son requeridos."}), 400

        nuevo_p = {
            "id": estado_ram_global["siguiente_id"],
            "nombre": nombre,
            "tamano_mb": tamano,
            "ttl": ttl,
            "ttl_inicial": ttl
        }
        estado_ram_global["siguiente_id"] += 1

        if tamano <= estado_ram_global["ram_disponible_mb"]:
            estado_ram_global["procesos_ejecucion"].append(nuevo_p)
            actualizar_metricas_ram()
        else:
            estado_ram_global["cola_espera"].append(nuevo_p)

        return jsonify(estado_ram_global), 200
    except Exception as e:
        return jsonify({"error": f"Error al agregar proceso: {str(e)}"}), 500

@app.route('/api/simulador/escenario/<int:escenario_num>', methods=['POST'])
def cargar_escenario_ram(escenario_num):
    """Carga uno de los 3 escenarios preconfigurados de memoria RAM."""
    try:
        # Limpiar estado previo
        estado_ram_global["procesos_ejecucion"] = []
        estado_ram_global["cola_espera"] = []
        actualizar_metricas_ram()

        escenarios = {
            1: [ # Carga Ligera (Entran todos)
                {"nombre": "Nginx_Web", "tamano_mb": 128, "ttl": 25},
                {"nombre": "Flask_API", "tamano_mb": 256, "ttl": 30},
                {"nombre": "Redis_Cache", "tamano_mb": 128, "ttl": 20}
            ],
            2: [ # Sobrecarga y Cola de Espera (Satura 1024 MB)
                {"nombre": "PostgreSQL_DB", "tamano_mb": 512, "ttl": 35},
                {"nombre": "PyTorch_AI_Model", "tamano_mb": 600, "ttl": 40}, # Excede RAM, pasa a cola
                {"nombre": "Celery_Worker", "tamano_mb": 256, "ttl": 25}
            ],
            3: [ # Carga Mixta Rápida
                {"nombre": "Auth_Service", "tamano_mb": 200, "ttl": 15},
                {"nombre": "Docker_Engine", "tamano_mb": 400, "ttl": 25},
                {"nombre": "Grafana_Monitor", "tamano_mb": 300, "ttl": 20},
                {"nombre": "Backup_Job", "tamano_mb": 350, "ttl": 30} # Pasa a cola
            ]
        }

        procs = escenarios.get(escenario_num, escenarios[1])

        for p in procs:
            p_id = estado_ram_global["siguiente_id"]
            estado_ram_global["siguiente_id"] += 1
            nuevo_p = {
                "id": p_id,
                "nombre": p["nombre"],
                "tamano_mb": p["tamano_mb"],
                "ttl": p["ttl"],
                "ttl_inicial": p["ttl"]
            }
            if p["tamano_mb"] <= estado_ram_global["ram_disponible_mb"]:
                estado_ram_global["procesos_ejecucion"].append(nuevo_p)
                actualizar_metricas_ram()
            else:
                estado_ram_global["cola_espera"].append(nuevo_p)

        return jsonify(estado_ram_global), 200
    except Exception as e:
        return jsonify({"error": f"Error al cargar escenario RAM: {str(e)}"}), 500

@app.route('/api/simulador/eliminar/<int:proceso_id>', methods=['DELETE', 'POST'])
def eliminar_proceso_ram(proceso_id):
    try:
        estado_ram_global["procesos_ejecucion"] = [
            p for p in estado_ram_global["procesos_ejecucion"] if p["id"] != proceso_id
        ]
        estado_ram_global["cola_espera"] = [
            p for p in estado_ram_global["cola_espera"] if p["id"] != proceso_id
        ]
        actualizar_metricas_ram()
        procesar_cola_espera_ram()
        return jsonify(estado_ram_global), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar proceso: {str(e)}"}), 500

@app.route('/api/simulador/reiniciar', methods=['POST'])
def reiniciar_ram():
    global estado_ram_global
    estado_ram_global["procesos_ejecucion"] = []
    estado_ram_global["cola_espera"] = []
    estado_ram_global["siguiente_id"] = 1
    actualizar_metricas_ram()
    return jsonify(estado_ram_global), 200

# ==========================================
# SIMULADOR DE CONCURRENCIA (ASIENTOS DE VUELO)
# ==========================================
ASIENTOS_CABINA = ["1A", "1B", "1C", "1D", "2A", "2B", "2C", "2D", "3A", "3B", "3C", "3D"]

class AsientoConcurrencia:
    def __init__(self, id_asiento):
        self.id_asiento = id_asiento
        self.reservado_por = None
        self.historial_reservas = []
        self.lock = threading.Lock()
        self.lock_timestamp = 0

class SistemaConcurrenciaVuelo:
    def __init__(self):
        self.asientos = {id_a: AsientoConcurrencia(id_a) for id_a in ASIENTOS_CABINA}
        self.conteo_exito = 0
        self.conteo_fallo = 0
        self.lock_stats = threading.Lock()
        self.logs = []
        self.lock_logs = threading.Lock()

    def log(self, mensaje):
        with self.lock_logs:
            self.logs.append(mensaje)

    def reservar_sin_mutex(self, id_asiento, pasajero, id_agente):
        asiento = self.asientos[id_asiento]
        if asiento.reservado_por is None:
            time.sleep(0.002)  # Simula latencia para inducir Race Condition
            asiento.reservado_por = pasajero
            asiento.historial_reservas.append(pasajero)
            with self.lock_stats:
                self.conteo_exito += 1
            self.log(f"💥 [SIN MUTEX] Agente-{id_agente:02d} reservó {id_asiento} -> {pasajero}")
            return True
        else:
            asiento.historial_reservas.append(f"COLISIÓN({pasajero})")
            with self.lock_stats:
                self.conteo_fallo += 1
            return False

    def reservar_con_mutex(self, id_asiento, pasajero, id_agente, ttl_seconds=30):
        asiento = self.asientos[id_asiento]
        
        # Auto-Release TTL: Si un lock lleva más de ttl_seconds tomado, se notifica
        now = time.time()
        if asiento.lock_timestamp > 0 and (now - asiento.lock_timestamp) > ttl_seconds:
            self.log(f"⏰ [TTL Auto-Release] Expiró bloqueo previo en asiento {id_asiento}")

        acquired = asiento.lock.acquire(timeout=2.0)
        if not acquired:
            with self.lock_stats:
                self.conteo_fallo += 1
            self.log(f"🔒 [MUTEX TIMEOUT] Agente-{id_agente:02d} no pudo adquirir candado en {id_asiento}")
            return False

        try:
            asiento.lock_timestamp = time.time()
            if asiento.reservado_por is None:
                time.sleep(0.002)
                asiento.reservado_por = pasajero
                asiento.historial_reservas.append(pasajero)
                with self.lock_stats:
                    self.conteo_exito += 1
                self.log(f"🔒 [MUTEX LOCK] Agente-{id_agente:02d} reservó exitosamente {id_asiento} -> {pasajero}")
                return True
            else:
                with self.lock_stats:
                    self.conteo_fallo += 1
                return False
        finally:
            asiento.lock_timestamp = 0
            asiento.lock.release()

    def reiniciar(self):
        for asiento in self.asientos.values():
            asiento.reservado_por = None
            asiento.historial_reservas.clear()
            asiento.lock_timestamp = 0
        self.conteo_exito = 0
        self.conteo_fallo = 0
        self.logs.clear()
        self.log("🔄 Mapa de asientos reiniciado y liberado.")

sistema_vuelo = SistemaConcurrenciaVuelo()

@app.route('/api/simulador-concurrencia/estado', methods=['GET'])
def estado_vuelo():
    try:
        asientos_res = []
        asientos_con_overbooking = 0

        for id_a in ASIENTOS_CABINA:
            asiento = sistema_vuelo.asientos[id_a]
            historial = list(asiento.historial_reservas)
            total = len(historial)
            es_overbooking = total > 1

            if es_overbooking:
                asientos_con_overbooking += 1

            asientos_res.append({
                "id": id_a,
                "pasajero_confirmado": asiento.reservado_por,
                "historial": historial,
                "total_asignaciones": total,
                "overbooking": es_overbooking
            })

        return jsonify({
            "asientos": asientos_res,
            "asientos_con_overbooking": asientos_con_overbooking,
            "conteo_exito": sistema_vuelo.conteo_exito,
            "conteo_fallo": sistema_vuelo.conteo_fallo,
            "integridad_ok": asientos_con_overbooking == 0,
            "logs": sistema_vuelo.logs
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al consultar estado de concurrencia: {str(e)}"}), 500

@app.route('/api/simulador-concurrencia/escenario/<int:escenario_num>', methods=['POST'])
def ejecutar_escenario_concurrencia(escenario_num):
    """Ejecuta uno de los 3 escenarios de concurrencia preconfigurados."""
    try:
        sistema_vuelo.reiniciar()
        hilos = []

        if escenario_num == 1:
            # Escenario 1: Condición de Carrera (Sin Mutex / Colisión directa en asiento 1A)
            sistema_vuelo.log("▶️ Ejecutando Escenario 1: Condición de Carrera (Sin Mutex / Colisión en 1A)")
            def tarea_escenario1(id_agente):
                sistema_vuelo.reservar_sin_mutex("1A", f"Pasajero_E1_{id_agente}", id_agente)

            for i in range(1, 10):
                t = threading.Thread(target=tarea_escenario1, args=(i,))
                hilos.append(t)
                t.start()

        elif escenario_num == 2:
            # Escenario 2: Exclusión Mutua (Con Mutex / Reservas seguras en 1A)
            sistema_vuelo.log("▶️ Ejecutando Escenario 2: Exclusión Mutua (Con Mutex / Asiento 1A Protegido)")
            def tarea_escenario2(id_agente):
                sistema_vuelo.reservar_con_mutex("1A", f"Pasajero_E2_{id_agente}", id_agente)

            for i in range(1, 10):
                t = threading.Thread(target=tarea_escenario2, args=(i,))
                hilos.append(t)
                t.start()

        elif escenario_num == 3:
            # Escenario 3: Ráfaga Distribuida (12 hilos masivos en paralelo)
            sistema_vuelo.log("▶️ Ejecutando Escenario 3: Ráfaga Distribuida (12 hilos compitiendo por toda la cabina)")
            def tarea_escenario3(id_agente):
                for id_asiento in random.sample(ASIENTOS_CABINA, 4):
                    sistema_vuelo.reservar_con_mutex(id_asiento, f"Pasajero_E3_{id_agente}", id_agente)

            for i in range(1, 13):
                t = threading.Thread(target=tarea_escenario3, args=(i,))
                hilos.append(t)
                t.start()

        for t in hilos:
            t.join()

        return estado_vuelo()
    except Exception as e:
        return jsonify({"error": f"Error al ejecutar escenario de concurrencia: {str(e)}"}), 500

@app.route('/api/simulador-concurrencia/reservar-manual', methods=['POST'])
def reservar_manual_vuelo():
    try:
        data = request.get_json() or {}
        id_asiento = data.get('id_asiento')
        pasajero = data.get('pasajero', 'Pasajero Manual')

        if id_asiento not in sistema_vuelo.asientos:
            return jsonify({"error": "Asiento no válido"}), 400

        exito = sistema_vuelo.reservar_con_mutex(id_asiento, pasajero, id_agente=0)
        if not exito:
            return jsonify({"error": f"El asiento {id_asiento} ya está ocupado"}), 400

        return estado_vuelo()
    except Exception as e:
        return jsonify({"error": f"Error al realizar reserva manual: {str(e)}"}), 500

@app.route('/api/simulador-concurrencia/reiniciar', methods=['POST'])
def reiniciar_vuelo():
    try:
        sistema_vuelo.reiniciar()
        return estado_vuelo()
    except Exception as e:
        return jsonify({"error": f"Error al reiniciar vuelo: {str(e)}"}), 500

# ==========================================
# ARRANCADOR DE APLICACIÓN
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)