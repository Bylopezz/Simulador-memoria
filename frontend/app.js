const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : '/api';

let moduloActivo = 'inicio';
let idArticuloActivo = null;
let intervaloConcurrencia = null;
let intervaloRAM = null;

function mostrarModulo(nombreModulo) {
    moduloActivo = nombreModulo;

    document.querySelectorAll('.modulo').forEach(m => m.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    const target = document.getElementById(`modulo-${nombreModulo}`);
    if (target) target.classList.add('active');

    const navBtn = Array.from(document.querySelectorAll('.nav-btn')).find(
        btn => btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(`'${nombreModulo}'`)
    );
    if (navBtn) navBtn.classList.add('active');

    if (intervaloConcurrencia) clearInterval(intervaloConcurrencia);
    if (intervaloRAM) clearInterval(intervaloRAM);

    if (nombreModulo === 'inicio') {
        cargarInicio();
    } else if (nombreModulo === 'glosario') {
        cargarGlosario();
        cargarHistorialGeneralGlosario();
    } else if (nombreModulo === 'ram') {
        actualizarEstadoRAM();
        intervaloRAM = setInterval(actualizarEstadoRAM, 1000);
    } else if (nombreModulo === 'concurrencia') {
        actualizarConcurrencia();
        intervaloConcurrencia = setInterval(actualizarConcurrencia, 1500);
    } else if (nombreModulo === 'editor') {
        if (!document.getElementById('edit-pub-id').value) {
            limpiarFormularioEditor();
        }
    }
}

// INICIO
async function cargarInicio() {
    try {
        const res = await fetch(`${API_URL}/inicio/resumen`);
        if (!res.ok) throw new Error('Error de conexión');
        const data = await res.json();

        const contPubs = document.getElementById("contenedor-ultimas-publicaciones");
        if (!data.ultimas_publicaciones || data.ultimas_publicaciones.length === 0) {
            contPubs.innerHTML = "<p class='text-muted'>No hay publicaciones registradas aún.</p>";
        } else {
            contPubs.innerHTML = data.ultimas_publicaciones.map(p => `
                <div style="border-bottom: 1px solid var(--border-color); padding: 10px 0;">
                    <a href="#" onclick="verArticuloCompleto(${p.id}); return false;" style="text-decoration:none; color:var(--blue-primary); font-weight:bold;">
                        ${p.titulo}
                    </a>
                    <br><small style="color:var(--text-muted);">Categoría: <strong>${p.categoria}</strong> | Por ${p.autor} (${p.fecha})</small>
                </div>
            `).join("");
        }

        const contCambios = document.getElementById("contenedor-ultimos-cambios");
        if (!data.ultimos_cambios || data.ultimos_cambios.length === 0) {
            contCambios.innerHTML = "<p class='text-muted'>No hay registros de auditoría aún.</p>";
        } else {
            contCambios.innerHTML = data.ultimos_cambios.map(c => `
                <div style="border-bottom: 1px solid var(--border-color); padding: 10px 0;">
                    <span style="background:#2563eb; color:white; padding:2px 6px; border-radius:4px; font-size:0.7rem;">${c.tipo_accion}</span>
                    <strong>${c.titulo_anterior}</strong>
                    <br><small style="color:var(--text-muted);">Por ${c.autor_modificador} - ${c.fecha_modificacion}</small>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error("Error al cargar inicio:", err);
    }
}

// GLOSARIO
async function cargarGlosario() {
    try {
        const res = await fetch(`${API_URL}/publicaciones`);
        const publicaciones = await res.json();
        const contenedor = document.getElementById("lista-articulos-glosario");

        if (publicaciones.length === 0) {
            contenedor.innerHTML = "<p class='text-muted'>No hay publicaciones en la wiki. ¡Crea la primera en la opción Publicar!</p>";
            return;
        }

        contenedor.innerHTML = publicaciones.map(p => `
            <div class="article-card">
                <div>
                    <span class="article-badge">${p.tipo}</span>
                    <h3 class="article-title">${p.titulo}</h3>
                    <p class="article-meta">Categoría: <strong>${p.categoria}</strong> | Autor: ${p.autor}</p>
                </div>
                <div style="display:flex; gap:8px; margin-top:10px;">
                    <button class="btn btn-primary" style="padding:4px 10px; font-size:0.85rem;" onclick="verArticuloCompleto(${p.id})">Leer Articulo</button>
                    <button class="btn btn-outline" style="padding:4px 10px; font-size:0.85rem;" onclick="abrirEditorParaEdicion(${p.id})">Editar</button>
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
            tbody.innerHTML = "<tr><td colspan='4' style='text-align:center; padding:15px;'>Sin registros de auditoría.</td></tr>";
            return;
        }

        tbody.innerHTML = historial.map(h => `
            <tr>
                <td style="padding:10px; border-bottom:1px solid var(--border-color);"><span style="background:#334155; color:white; padding:2px 6px; border-radius:4px; font-size:0.75rem;">${h.tipo_accion}</span></td>
                <td style="padding:10px; border-bottom:1px solid var(--border-color);">${h.titulo_anterior}</td>
                <td style="padding:10px; border-bottom:1px solid var(--border-color);">${h.autor_modificador}</td>
                <td style="padding:10px; border-bottom:1px solid var(--border-color);"><small>${h.fecha_modificacion}</small></td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Error al cargar historial general:", err);
    }
}

// ARTÍCULO DETALLE
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
                    <span class="article-badge">${pub.tipo}</span>
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
            cont.innerHTML = "<p class='text-muted'>No hay versiones previas registradas para este artículo.</p>";
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
                    Restaurar esta versión
                </button>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error al cargar historial:", err);
    }
}

async function restaurarVersionArticulo(historialId) {
    if (confirm("¿Confirmas que deseas restaurar esta versión anterior del artículo?")) {
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

// EDITOR
function limpiarFormularioEditor() {
    document.getElementById("edit-pub-id").value = "";
    document.getElementById("form-titulo").value = "";
    document.getElementById("form-tipo").value = "Concepto";
    document.getElementById("form-categoria").value = "";
    document.getElementById("form-autor").value = "";
    document.getElementById("form-contenido").value = "";
    document.getElementById("form-imagen-file").value = "";
    document.getElementById("titulo-form-editor").innerText = "Crear Nueva Publicación";
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
            document.getElementById("titulo-form-editor").innerText = "Editar Publicación #" + pub.id;
            
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
    document.getElementById("vista-previa-editor").innerHTML = contenido || "<p class='text-muted'>Vista previa en tiempo real...</p>";
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

// SIMULADOR RAM
async function actualizarEstadoRAM() {
    try {
        const res = await fetch(`${API_URL}/simulador-ram/estado`);
        const data = await res.json();

        const pct = Math.round((data.usada / data.capacidad_total) * 100);
        document.getElementById("ram-texto-uso").innerText = `${data.usada} / ${data.capacidad_total} MB (${pct}%)`;
        const barra = document.getElementById("ram-barra-progreso");
        if (barra) barra.style.width = `${pct}%`;

        const contEjec = document.getElementById("ram-lista-ejecucion");
        if (data.procesos_ejecucion.length === 0) {
            contEjec.innerHTML = "<p class='text-muted'>RAM libre.</p>";
        } else {
            contEjec.innerHTML = data.procesos_ejecucion.map(p => `
                <div class="process-item" style="background:#ffffff; border:1px solid var(--border-color); padding:10px; border-radius:6px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                    <div><strong>${p.nombre}</strong> (${p.tamano} MB)</div>
                    <span style="color:#2563eb; font-weight:bold; font-size:0.85rem;">${p.tiempo_restante}s restantes</span>
                </div>
            `).join("");
        }

        const contEspera = document.getElementById("ram-lista-espera");
        if (data.cola_espera.length === 0) {
            contEspera.innerHTML = "<p class='text-muted'>Sin procesos retenidos.</p>";
        } else {
            contEspera.innerHTML = data.cola_espera.map(p => `
                <div class="process-item" style="background:#fff7ed; border:1px solid #ffedd5; padding:10px; border-radius:6px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                    <div><strong>${p.nombre}</strong> (${p.tamano} MB)</div>
                    <span style="background:#f59e0b; color:white; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold;">EN COLA</span>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error("Error al actualizar RAM:", err);
    }
}

async function agregarProcesoRAM(event) {
    if (event) event.preventDefault();
    const nombreInput = document.getElementById("ram-nombre");
    const tamanoInput = document.getElementById("ram-tamano");
    const duracionInput = document.getElementById("ram-duracion");

    const payload = {
        nombre: nombreInput.value || "Proceso_Manual",
        tamano: parseInt(tamanoInput.value) || 128,
        duracion: parseInt(duracionInput.value) || 15
    };

    try {
        await fetch(`${API_URL}/simulador-ram/agregar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        nombreInput.value = "";
        actualizarEstadoRAM();
    } catch (err) {
        console.error("Error al agregar proceso RAM:", err);
    }
}

async function generarLoteAleatorioRAM() {
    try {
        await fetch(`${API_URL}/simulador-ram/lote-aleatorio`, { method: 'POST' });
        actualizarEstadoRAM();
    } catch (err) {
        console.error("Error al generar lote RAM:", err);
    }
}

async function resetearRAM() {
    try {
        await fetch(`${API_URL}/simulador-ram/reset`, { method: 'POST' });
        actualizarEstadoRAM();
    } catch (err) {
        console.error("Error al reiniciar RAM:", err);
    }
}

// SIMULADOR CONCURRENCIA
async function cambiarMutexCheck(activar) {
    try {
        await fetch(`${API_URL}/simulador-concurrencia/toggle-mutex`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activar: activar })
        });
        actualizarConcurrencia();
    } catch (err) {
        console.error("Error al cambiar Mutex:", err);
    }
}

async function actualizarConcurrencia() {
    try {
        const res = await fetch(`${API_URL}/simulador-concurrencia/estado`);
        const data = await res.json();

        const chkMutex = document.getElementById("chk-mutex-activado");
        if (chkMutex && document.activeElement !== chkMutex) {
            chkMutex.checked = data.mutex_activado;
        }

        const badgeMutex = document.getElementById("concurrencia-estado-mutex");
        if (badgeMutex) {
            if (data.mutex_bloqueado) {
                badgeMutex.innerText = "MUTEX: BLOQUEADO (SECCIÓN CRÍTICA)";
                badgeMutex.style.background = "#ef4444";
                badgeMutex.style.color = "white";
            } else if (data.mutex_activado) {
                badgeMutex.innerText = "MUTEX: ACTIVADO (PROTEGIDO)";
                badgeMutex.style.background = "#10b981";
                badgeMutex.style.color = "white";
            } else {
                badgeMutex.innerText = "MUTEX: INACTIVO (RACE CONDITION RISK)";
                badgeMutex.style.background = "#e2e8f0";
                badgeMutex.style.color = "#0f172a";
            }
        }

        const mapa = document.getElementById("concurrencia-mapa-asientos");
        if (mapa) {
            mapa.innerHTML = data.asientos.map(a => {
                let bgColor = "#f1f5f9";
                let borderColor = "#cbd5e1";
                let texto = a.id;

                if (a.overbooking) {
                    bgColor = "#fef2f2";
                    borderColor = "#ef4444";
                    texto += " [OVERBOOKING]";
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
        }

        const terminal = document.getElementById("concurrencia-terminal-logs");
        if (terminal) {
            terminal.innerHTML = data.logs.map(log => `<div>${log}</div>`).join("");
            terminal.scrollTop = terminal.scrollHeight;
        }
    } catch (err) {
        console.error("Error al actualizar concurrencia:", err);
    }
}

async function reservarAsientoConcurrencia(asientoId) {
    try {
        await fetch(`${API_URL}/simulador-concurrencia/reservar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asiento_id: asientoId, pasajero: "Usuario_Web" })
        });
        actualizarConcurrencia();
    } catch (err) {
        console.error("Error al reservar asiento:", err);
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

window.addEventListener('DOMContentLoaded', () => {
    cargarInicio();
});