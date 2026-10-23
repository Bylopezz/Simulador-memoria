// ==========================================
// CONFIGURACIÓN GLOBAL Y MANEJO DE SESIÓN
// ==========================================
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : '/api';

// Identificador único por usuario en localStorage para aislar la RAM
function obtenerSessionId() {
    let sid = localStorage.getItem('wiki_os_session_id');
    if (!sid) {
        sid = 'user_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
        localStorage.setItem('wiki_os_session_id', sid);
    }
    return sid;
}

const SESSION_ID = obtenerSessionId();

// Variables globales de control de estado
let moduloActivo = 'inicio';
let idArticuloActivo = null;
let datosBanqueroActual = null;
let intervaloConcurrencia = null;
let intervaloRAM = null;

// ==========================================
// NAVEGACIÓN Y CAMBIO DE MÓDULOS
// ==========================================
function mostrarModulo(nombreModulo) {
    moduloActivo = nombreModulo;

    // Ocultar todos los módulos y quitar clase activa de botones
    document.querySelectorAll('.modulo').forEach(m => m.style.display = 'none');
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    // Mostrar el módulo seleccionado
    const target = document.getElementById(`modulo-${nombreModulo}`);
    if (target) target.style.display = 'block';

    // Marcar botón activo en la navegación
    const navBtn = Array.from(document.querySelectorAll('.nav-btn')).find(
        btn => btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(`'${nombreModulo}'`)
    );
    if (navBtn) navBtn.classList.add('active');

    // Detener temporizadores de módulos inactivos
    if (intervaloConcurrencia) clearInterval(intervaloConcurrencia);
    if (intervaloRAM) clearInterval(intervaloRAM);

    // Disparar lógica específica según el módulo seleccionado
    if (nombreModulo === 'inicio') {
        cargarInicio();
    } else if (nombreModulo === 'glosario') {
        cargarGlosario();
        cargarHistorialGeneralGlosario();
    } else if (nombreModulo === 'ram') {
        actualizarEstadoRAM();
        intervaloRAM = setInterval(actualizarEstadoRAM, 3000);
    } else if (nombreModulo === 'concurrencia') {
        actualizarConcurrencia();
        intervaloConcurrencia = setInterval(actualizarConcurrencia, 1500); // Polling 1.5s
    } else if (nombreModulo === 'banquero') {
        if (!datosBanqueroActual) cargarCasoEjemploBanquero('caso_1_seguro');
    } else if (nombreModulo === 'editor') {
        if (!document.getElementById('edit-pub-id').value) {
            limpiarFormularioEditor();
        }
    }
}

// ==========================================
// 1. MÓDULO INICIO (RESUMEN GENERAL)
// ==========================================
async function cargarInicio() {
    try {
        const res = await fetch(`${API_URL}/inicio/resumen`);
        if (!res.ok) throw new Error('Error al conectar con la API');
        const data = await res.json();

        // Renderizar últimas 3 publicaciones
        const contPubs = document.getElementById("contenedor-ultimas-publicaciones");
        if (!data.ultimas_publicaciones || data.ultimas_publicaciones.length === 0) {
            contPubs.innerHTML = "<p style='color: var(--text-muted);'>No hay publicaciones registradas aún.</p>";
        } else {
            contPubs.innerHTML = data.ultimas_publicaciones.map(p => `
                <div style="border-bottom: 1px solid var(--border-color); padding: 10px 0;">
                    <a href="#" onclick="verArticuloCompleto(${p.id}); return false;" style="text-decoration:none; color:var(--primary); font-weight:bold; font-size:1.05rem;">
                        ${p.titulo}
                    </a>
                    <br><small style="color:var(--text-muted);">Categoría: <strong>${p.categoria}</strong> | Por ${p.autor} (${p.fecha})</small>
                </div>
            `).join("");
        }

        // Renderizar últimos 3 cambios de auditoría
        const contCambios = document.getElementById("contenedor-ultimos-cambios");
        if (!data.ultimos_cambios || data.ultimos_cambios.length === 0) {
            contCambios.innerHTML = "<p style='color: var(--text-muted);'>No hay registros de auditoría aún.</p>";
        } else {
            contCambios.innerHTML = data.ultimos_cambios.map(c => `
                <div style="border-bottom: 1px solid var(--border-color); padding: 10px 0;">
                    <span class="badge" style="background:#3b82f6; color:white; font-size:0.7rem; margin-right:5px;">${c.tipo_accion}</span>
                    <strong>${c.titulo_anterior}</strong>
                    <br><small style="color:var(--text-muted);">Por ${c.autor_modificador} - ${c.fecha_modificacion}</small>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error("Error al cargar datos de Inicio:", err);
    }
}

// ==========================================
// 2. MÓDULO GLOSARIO Y AUDITORÍA GENERAL
// ==========================================
async function cargarGlosario() {
    try {
        const res = await fetch(`${API_URL}/publicaciones`);
        const publicaciones = await res.json();
        const contenedor = document.getElementById("lista-articulos-glosario");

        if (publicaciones.length === 0) {
            contenedor.innerHTML = "<p style='color: var(--text-muted); grid-column: span 2;'>No hay publicaciones en la wiki. ¡Crea la primera en el apartado Publicar!</p>";
            return;
        }

        contenedor.innerHTML = publicaciones.map(p => `
            <div class="card" style="display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <span class="badge" style="background:#e2e8f0; color:#334155; margin-bottom:8px;">${p.tipo}</span>
                    <h3 style="margin-bottom:8px;">${p.titulo}</h3>
                    <p style="color:var(--text-muted); font-size:0.85rem; margin-bottom:12px;">
                        Categoría: <strong>${p.categoria}</strong> | Autor: ${p.autor}
                    </p>
                </div>
                <div style="display:flex; gap:8px; margin-top:10px;">
                    <button class="btn btn-primary" style="padding:4px 10px; font-size:0.85rem;" onclick="verArticuloCompleto(${p.id})">📖 Leer Articulo</button>
                    <button class="btn btn-outline" style="padding:4px 10px; font-size:0.85rem;" onclick="abrirEditorParaEdicion(${p.id})">✏️ Editar</button>
                    <button class="btn btn-danger" style="padding:4px 10px; font-size:0.85rem;" onclick="eliminarPublicacion(${p.id})">🗑️</button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error al cargar glosario:", err);
    }
}

async function cargarHistorialGeneralGlosario() {
    try {
        const res = await fetch(`${API_URL}/historial-general`);
        const historial = await res.json();
        const tbody = document.getElementById("tabla-historial-general");
        
        if (!tbody) return;
        if (historial.length === 0) {
            tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;'>Sin registros de auditoría.</td></tr>";
            return;
        }

        tbody.innerHTML = historial.map(h => `
            <tr>
                <td><span class="badge" style="background:#334155; color:white;">${h.tipo_accion}</span></td>
                <td>${h.titulo_anterior}</td>
                <td>${h.autor_modificador}</td>
                <td><small>${h.fecha_modificacion}</small></td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Error al cargar historial general:", err);
    }
}

// ==========================================
// 3. VISTA DE DETALLE DE ARTÍCULO Y AUDITORÍA
// ==========================================
async function verArticuloCompleto(pubId) {
    idArticuloActivo = pubId;
    mostrarModulo("articulo-detalle");
    document.getElementById("panel-historial-articulo").style.display = "none";

    try {
        const res = await fetch(`${API_URL}/publicaciones`);
        const pubs = await res.json();
        const pub = pubs.find(p => p.id === pubId);

        if (pub) {
            document.getElementById("contenido-articulo-activo").innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span class="badge" style="background:var(--primary); color:white;">${pub.tipo}</span>
                    <small style="color:var(--text-muted);">ID: #${pub.id}</small>
                </div>
                <h1 style="margin-bottom:10px;">${pub.titulo}</h1>
                <p style="color: var(--text-muted); font-size:0.9rem; margin-bottom:20px;">
                    <strong>Categoría:</strong> ${pub.categoria} | <strong>Autor:</strong> ${pub.autor} | <strong>Fecha:</strong> ${pub.fecha}
                </p>
                <hr style="border:none; border-top:1px solid var(--border-color); margin-bottom:20px;">
                <div style="line-height:1.6; font-size:1.05rem;">${pub.contenido}</div>
            `;
        }
    } catch (err) {
        console.error("Error al cargar artículo:", err);
    }
}

function abrirEditorArticuloActual() {
    if (idArticuloActivo) abrirEditorParaEdicion(idArticuloActivo);
}

async function toggleHistorialArticulo() {
    const panel = document.getElementById("panel-historial-articulo");
    if (panel.style.display === "block") {
        panel.style.display = "none";
        return;
    }
    
    panel.style.display = "block";
    const cont = document.getElementById("lista-versiones-articulo");
    
    try {
        const res = await fetch(`${API_URL}/publicaciones/${idArticuloActivo}/historial`);
        const versiones = await res.json();

        if (versiones.length === 0) {
            cont.innerHTML = "<p style='color:var(--text-muted);'>No hay versiones previas en el historial para este artículo.</p>";
            return;
        }

        cont.innerHTML = versiones.map(v => `
            <div style="border: 1px solid var(--border-color); border-radius: 6px; padding: 12px; margin-top: 10px; background: white;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong>[${v.tipo_accion}] ${v.titulo_anterior}</strong>
                    <small style="color:var(--text-muted);">${v.fecha_modificacion}</small>
                </div>
                <p style="font-size:0.85rem; color:var(--text-muted); margin: 6px 0;">Modificado por: ${v.autor_modificador}</p>
                <button class="btn btn-primary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="restaurarVersionArticulo(${v.id})">
                    🔄 Restaurar esta versión
                </button>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error al cargar historial del artículo:", err);
    }
}

async function restaurarVersionArticulo(historialId) {
    if (confirm("¿Confirmas que deseas restaurar esta versión anterior?")) {
        try {
            const res = await fetch(`${API_URL}/publicaciones/${idArticuloActivo}/restaurar/${historialId}`, { method: 'POST' });
            if (res.ok) {
                alert("Artículo restaurado con éxito.");
                await verArticuloCompleto(idArticuloActivo);
                await cargarInicio();
            }
        } catch (err) {
            console.error("Error al restaurar versión:", err);
        }
    }
}

// ==========================================
// 4. EDITOR Y COMPRESIÓN DE IMÁGENES BASE64
// ==========================================
function limpiarFormularioEditor() {
    document.getElementById("edit-pub-id").value = "";
    document.getElementById("form-titulo").value = "";
    document.getElementById("form-tipo").value = "Concepto";
    document.getElementById("form-categoria").value = "";
    document.getElementById("form-autor").value = "";
    document.getElementById("form-contenido").value = "";
    document.getElementById("form-imagen-file").value = "";
    document.getElementById("titulo-form-editor").innerText = "✏️ Crear Nueva Publicación";
    actualizarVistaPreviaEditor();
}

async function abrirEditorParaEdicion(pubId) {
    try {
        const res = await fetch(`${API_URL}/publicaciones`);
        const pubs = await res.json();
        const pub = pubs.find(p => p.id === pubId);

        if (pub) {
            document.getElementById("edit-pub-id").value = pub.id;
            document.getElementById("form-titulo").value = pub.titulo;
            document.getElementById("form-tipo").value = pub.tipo;
            document.getElementById("form-categoria").value = pub.categoria;
            document.getElementById("form-autor").value = pub.autor;
            document.getElementById("form-contenido").value = pub.contenido;
            document.getElementById("titulo-form-editor").innerText = "✏️ Editar Publicación #" + pub.id;
            
            mostrarModulo("editor");
            actualizarVistaPreviaEditor();
        }
    } catch (err) {
        console.error("Error al abrir editor:", err);
    }
}

function insertarImagenBase64(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement("canvas");
            let width = img.width;
            let height = img.height;
            const MAX_WIDTH = 1080;

            if (width > MAX_WIDTH) {
                height = Math.round((height * MAX_WIDTH) / width);
                width = MAX_WIDTH;
            }

            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, width, height);

            const base64Data = canvas.toDataURL("image/jpeg", 0.8);
            const imgTag = `<br><img src="${base64Data}" alt="Imagen adjunta" style="max-width:100%; border-radius:6px; margin:10px 0;"><br>`;

            const textarea = document.getElementById("form-contenido");
            const startPos = textarea.selectionStart;
            const endPos = textarea.selectionEnd;

            textarea.value = textarea.value.substring(0, startPos) + imgTag + textarea.value.substring(endPos);
            actualizarVistaPreviaEditor();
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function actualizarVistaPreviaEditor() {
    const contenido = document.getElementById("form-contenido").value;
    document.getElementById("vista-previa-editor").innerHTML = contenido || "<p style='color:var(--text-muted);'>Vista previa en tiempo real...</p>";
}

async function guardarPublicacion(event) {
    event.preventDefault();

    const pubId = document.getElementById("edit-pub-id").value;
    const payload = {
        titulo: document.getElementById("form-titulo").value,
        tipo: document.getElementById("form-tipo").value,
        categoria: document.getElementById("form-categoria").value,
        autor: document.getElementById("form-autor").value,
        contenido: document.getElementById("form-contenido").value
    };

    try {
        let res;
        if (pubId) {
            res = await fetch(`${API_URL}/publicaciones/${pubId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            res = await fetch(`${API_URL}/publicaciones`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (res.ok) {
            alert(pubId ? "Publicación actualizada correctamente." : "Publicación creada con éxito.");
            limpiarFormularioEditor();
            mostrarModulo("glosario");
            await cargarInicio();
        }
    } catch (err) {
        console.error("Error al guardar publicación:", err);
    }
}

async function eliminarPublicacion(pubId) {
    if (confirm("¿Seguro que deseas eliminar esta publicación? Se guardará un respaldo en la auditoría.")) {
        try {
            const res = await fetch(`${API_URL}/publicaciones/${pubId}`, { method: 'DELETE' });
            if (res.ok) {
                await cargarGlosario();
                await cargarInicio();
            }
        } catch (err) {
            console.error("Error al eliminar publicación:", err);
        }
    }
}

// ==========================================
// 5. SIMULADOR DE MEMORIA RAM (AISLADO POR SESIÓN)
// ==========================================
async function actualizarEstadoRAM() {
    try {
        const res = await fetch(`${API_URL}/simulador-ram/estado?session_id=${SESSION_ID}`);
        const data = await res.json();

        // Barra de progreso y texto
        const pct = Math.round((data.usada / data.capacidad_total) * 100);
        document.getElementById("ram-texto-uso").innerText = `${data.usada} / ${data.capacidad_total} MB (${pct}%)`;
        const barra = document.getElementById("ram-barra-progreso");
        barra.style.width = `${pct}%`;
        barra.style.background = pct > 85 ? 'var(--danger)' : pct > 60 ? 'var(--warning)' : 'var(--primary)';

        // Procesos en ejecución
        const contEjec = document.getElementById("ram-lista-ejecucion");
        if (data.procesos_ejecucion.length === 0) {
            contEjec.innerHTML = "<p style='color:var(--text-muted); font-size:0.85rem;'>RAM vacía.</p>";
        } else {
            contEjec.innerHTML = data.procesos_ejecucion.map(p => `
                <div style="background:#f1f5f9; padding:8px; border-radius:4px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                    <div><strong>${p.nombre}</strong> (${p.tamano} MB)</div>
                    <small style="color:var(--text-muted);">${p.duracion}s duracion</small>
                </div>
            `).join("");
        }

        // Cola de espera
        const contEspera = document.getElementById("ram-lista-espera");
        if (data.cola_espera.length === 0) {
            contEspera.innerHTML = "<p style='color:var(--text-muted); font-size:0.85rem;'>Sin procesos retenidos en cola.</p>";
        } else {
            contEspera.innerHTML = data.cola_espera.map(p => `
                <div style="background:#fff7ed; border:1px solid #ffedd5; padding:8px; border-radius:4px; margin-bottom:6px; display:flex; justify-content:space-between;">
                    <div><strong>${p.nombre}</strong> (${p.tamano} MB)</div>
                    <span class="badge" style="background:var(--warning); color:white;">EN COLA</span>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error("Error al actualizar RAM:", err);
    }
}

async function agregarProcesoRAM(event) {
    event.preventDefault();
    const payload = {
        session_id: SESSION_ID,
        nombre: document.getElementById("ram-nombre").value,
        tamano: parseInt(document.getElementById("ram-tamano").value),
        duracion: parseInt(document.getElementById("ram-duracion").value)
    };

    try {
        await fetch(`${API_URL}/simulador-ram/agregar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        document.getElementById("ram-nombre").value = "";
        actualizarEstadoRAM();
    } catch (err) {
        console.error("Error al agregar proceso RAM:", err);
    }
}

async function generarLoteAleatorioRAM() {
    try {
        await fetch(`${API_URL}/simulador-ram/lote-aleatorio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: SESSION_ID })
        });
        actualizarEstadoRAM();
    } catch (err) {
        console.error("Error al generar lote RAM:", err);
    }
}

async function resetearRAM() {
    try {
        await fetch(`${API_URL}/simulador-ram/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: SESSION_ID })
        });
        actualizarEstadoRAM();
    } catch (err) {
        console.error("Error al reiniciar RAM:", err);
    }
}

// ==========================================
// 6. SIMULADOR DE CONCURRENCIA GLOBAL
// ==========================================
async function actualizarConcurrencia() {
    try {
        const res = await fetch(`${API_URL}/simulador-concurrencia/estado`);
        const data = await res.json();

        // Actualizar Badge de Mutex
        const badgeMutex = document.getElementById("concurrencia-estado-mutex");
        if (data.mutex_bloqueado) {
            badgeMutex.innerText = "MUTEX: BLOQUEADO (30s TTL)";
            badgeMutex.style.background = "var(--danger)";
            badgeMutex.style.color = "white";
        } else if (data.mutex_activado) {
            badgeMutex.innerText = "MUTEX: ACTIVADO (LISTO)";
            badgeMutex.style.background = "var(--success)";
            badgeMutex.style.color = "white";
        } else {
            badgeMutex.innerText = "MUTEX: INACTIVO";
            badgeMutex.style.background = "#e2e8f0";
            badgeMutex.style.color = "var(--text-main)";
        }

        // Renderizar mapa de asientos
        const mapa = document.getElementById("concurrencia-mapa-asientos");
        mapa.innerHTML = data.asientos.map(a => {
            let bgColor = "#f1f5f9";
            let borderColor = "#cbd5e1";
            let texto = a.id;

            if (a.overbooking) {
                bgColor = "#fef2f2";
                borderColor = "#ef4444";
                texto += " ⚠️ OVERBOOKING";
            } else if (a.pasajero_confirmado) {
                bgColor = "#f0fdf4";
                borderColor = "#22c55e";
                texto += `<br><small>${a.pasajero_confirmado}</small>`;
            }

            return `
                <div onclick="reservarAsientoConcurrencia('${a.id}')" style="background:${bgColor}; border:2px solid ${borderColor}; padding:10px; border-radius:6px; text-align:center; cursor:pointer; font-weight:bold; font-size:0.85rem;">
                    ${texto}
                </div>
            `;
        }).join("");

        // Terminal Logs
        const terminal = document.getElementById("concurrencia-terminal-logs");
        terminal.innerHTML = data.logs.map(log => `<div>${log}</div>`).join("");
        terminal.scrollTop = terminal.scrollHeight;
    } catch (err) {
        console.error("Error al actualizar concurrencia:", err);
    }
}

async function reservarAsientoConcurrencia(asientoId) {
    try {
        await fetch(`${API_URL}/simulador-concurrencia/reservar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asiento_id: asientoId, pasajero: "Usuario_" + SESSION_ID.substring(5, 9) })
        });
        actualizarConcurrencia();
    } catch (err) {
        console.error("Error al reservar asiento:", err);
    }
}

async function toggleMutexConcurrencia() {
    try {
        await fetch(`${API_URL}/simulador-concurrencia/toggle-mutex`, { method: 'POST' });
        actualizarConcurrencia();
    } catch (err) {
        console.error("Error al cambiar Mutex:", err);
    }
}

async function dispararRafagaConcurrencia() {
    try {
        await fetch(`${API_URL}/simulador-concurrencia/rafaga-hilos`, { method: 'POST' });
        actualizarConcurrencia();
    } catch (err) {
        console.error("Error al lanzar ráfaga de hilos:", err);
    }
}

async function resetearConcurrencia() {
    try {
        await fetch(`${API_URL}/simulador-concurrencia/reset`, { method: 'POST' });
        actualizarConcurrencia();
    } catch (err) {
        console.error("Error al reiniciar vuelo:", err);
    }
}

// ==========================================
// 7. SIMULADOR ALGORITMO DEL BANQUERO
// ==========================================
async function cargarCasoEjemploBanquero(claveCaso) {
    try {
        const res = await fetch(`${API_URL}/banquero/casos-ejemplo`);
        const casos = await res.json();
        const caso = casos[claveCaso];
        
        datosBanqueroActual = { disponibles: caso.recursos_disponibles, allocation: caso.allocation, max: caso.max };
        document.getElementById("banquero-titulo-caso").innerText = caso.titulo;
        
        const contenedor = document.getElementById("banquero-vistas-matrices");
        contenedor.innerHTML = `
            <div style="flex: 1; min-width: 150px;">
                <h4>Allocation (Asignados)</h4>
                <table border="1" style="width:100%; text-align:center; border-collapse:collapse;">
                    ${caso.allocation.map((f, i) => `<tr><td><strong>P${i}</strong></td>${f.map(v => `<td>${v}</td>`).join("")}</tr>`).join("")}
                </table>
            </div>
            <div style="flex: 1; min-width: 150px;">
                <h4>Max (Demandados)</h4>
                <table border="1" style="width:100%; text-align:center; border-collapse:collapse;">
                    ${caso.max.map((f, i) => `<tr><td><strong>P${i}</strong></td>${f.map(v => `<td>${v}</td>`).join("")}</tr>`).join("")}
                </table>
            </div>
            <div style="flex: 1; min-width: 150px;">
                <h4>Available (Disponibles)</h4>
                <table border="1" style="width:100%; text-align:center; border-collapse:collapse;">
                    <tr>${caso.recursos_disponibles.map(v => `<td><strong>${v}</strong></td>`).join("")}</tr>
                </table>
            </div>
        `;
        document.getElementById("banquero-resultado").style.display = "none";
    } catch (err) {
        console.error("Error al cargar caso del Banquero:", err);
    }
}

async function ejecutarEvaluacionBanquero() {
    if (!datosBanqueroActual) return;
    try {
        const res = await fetch(`${API_URL}/banquero/evaluar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datosBanqueroActual)
        });
        const resu = await res.json();
        const panelRes = document.getElementById("banquero-resultado");
        panelRes.style.display = "block";

        if (resu.es_seguro) {
            panelRes.innerHTML = `
                <div style="border-left: 5px solid var(--success); padding: 12px; background: #f0fdf4;">
                    <h3 style="color: #15803d; margin:0;">✅ Estado Seguro Confirmado</h3>
                    <p style="margin-top:8px;">
                        Secuencia Segura de Ejecución: 
                        <strong style="font-size:1.1rem; color:#166534;">${resu.secuencia_segura.join(" ➔ ")}</strong>
                    </p>
                </div>
            `;
        } else {
            panelRes.innerHTML = `
                <div style="border-left: 5px solid var(--danger); padding: 12px; background: #fef2f2;">
                    <h3 style="color: #b91c1c; margin:0;">⚠️ Estado Inseguro (Riesgo de Deadlock)</h3>
                    <p style="margin-top:8px;">
                        Procesos retenidos en interbloqueo: 
                        <strong style="color:#991b1b;">${resu.procesos_bloqueados.join(", ")}</strong>
                    </p>
                </div>
            `;
        }
    } catch (err) {
        console.error("Error en la evaluación del Banquero:", err);
    }
}

// ==========================================
// INICIALIZACIÓN DE LA APLICACIÓN
// ==========================================
window.addEventListener('DOMContentLoaded', () => {
    cargarInicio();
});