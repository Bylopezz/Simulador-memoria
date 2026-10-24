// ==========================================
// ESTADO GLOBAL Y CONFIGURACIÓN
// ==========================================
const API_URL = '/api';
const TOTAL_RAM_MB = 1024;

let simuladorRAM = {
    usada: 0,
    procesosEjecucion: [],
    colaEspera: [],
    siguienteId: 1
};

let publicacionesLocales = [];
let editandoId = null; // Guarda el ID de la publicación cuando se está editando

// Datos iniciales de fallback por si la API no responde
const publicacionesIniciales = [
    {
        id: 1,
        titulo: "Paginación y Segmentación",
        tipo: "Definición",
        categoria: "Sistemas Operativos",
        autor: "Cátedra de SO",
        fecha: "2026-10-08",
        contenido: "La paginación es un esquema de gestión de memoria que permite que el espacio de direcciones físicas de un proceso no sea contiguo."
    },
    {
        id: 2,
        titulo: "Estructura de Árboles B+",
        tipo: "Artículo",
        categoria: "Estructuras de Datos",
        autor: "Sistemas UMG",
        fecha: "2026-10-07",
        contenido: "Los árboles B+ son variantes de los árboles B optimizados para sistemas de archivos y bases de datos relacionales."
    }
];

// ==========================================
// INICIALIZACIÓN
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    cargarPublicaciones();
    actualizarVistaSimulador();
    cargarEstadoVuelo();

    const textareaContenido = document.getElementById("contenido");
    if (textareaContenido) {
        textareaContenido.addEventListener("input", actualizarVistaPreviaEditor);
    }
});

// ==========================================
// NAVEGACIÓN DINÁMICA ENTRE SECCIONES
// ==========================================
function mostrarSeccion(idSeccion) {
    // 1. Ocultar todos los módulos
    document.querySelectorAll(".modulo").forEach(modulo => {
        modulo.classList.remove("active");
        modulo.style.display = "none";
    });

    // 2. Desactivar todos los botones del menú
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.classList.remove("active");
    });

    // 3. Activar el módulo seleccionado
    const seccionObj = document.getElementById(idSeccion);
    if (seccionObj) {
        seccionObj.classList.add("active");
        seccionObj.style.display = "block";
    }

    // 4. Activar el botón correspondiente en el menú superior
    const btnActivo = Array.from(document.querySelectorAll(".nav-btn"))
        .find(b => b.getAttribute("onclick") && b.getAttribute("onclick").includes(`'${idSeccion}'`));
    if (btnActivo) {
        btnActivo.classList.add("active");
    }
}

// ==========================================
// HERRAMIENTAS DE IMÁGENES & VISTA PREVIA
// ==========================================
function actualizarVistaPreviaEditor() {
    const textarea = document.getElementById("contenido");
    const contenedorPreview = document.getElementById("vista-previa-editor");
    if (!textarea || !contenedorPreview) return;

    const texto = textarea.value;

    if (texto.trim() === "") {
        contenedorPreview.innerHTML = `<span style="color: #94a3b8; font-style: italic;">La vista previa de tu texto e imágenes aparecerá aquí conforme escribas...</span>`;
    } else {
        contenedorPreview.innerHTML = texto;
    }
}

function insertarEnCursor(textareaId, textoAInsertar) {
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;

    const startPos = textarea.selectionStart || 0;
    const endPos = textarea.selectionEnd || 0;

    textarea.value = textarea.value.substring(0, startPos) + textoAInsertar + textarea.value.substring(endPos);
    textarea.selectionStart = startPos + textoAInsertar.length;
    textarea.selectionEnd = startPos + textoAInsertar.length;
    textarea.focus();

    actualizarVistaPreviaEditor();
}

function insertarImagenURL() {
    const url = prompt("Ingresa la URL pública de la imagen:");
    if (url && url.trim() !== "") {
        const imgTag = `\n<img src="${url.trim()}" class="wiki-img" style="max-width:100%; border-radius:8px; margin:15px 0; display:block;" alt="Imagen URL">\n`;
        insertarEnCursor("contenido", imgTag);
    }
}

function insertarImagenBase64(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.src = e.target.result;
        img.onload = function() {
            const canvas = document.createElement("canvas");
            const maxAncho = 1080;
            let escala = 1;

            if (img.width > maxAncho) {
                escala = maxAncho / img.width;
            }

            canvas.width = img.width * escala;
            canvas.height = img.height * escala;

            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            const base64Comprimido = canvas.toDataURL("image/jpeg", 0.8);
            const imgTag = `\n<img src="${base64Comprimido}" class="wiki-img" style="max-width:100%; border-radius:8px; margin:15px 0; display:block;" alt="Imagen Base64">\n`;

            insertarEnCursor("contenido", imgTag);
            event.target.value = "";
        };
    };
    reader.readAsDataURL(file);
}

// ==========================================
// GESTIÓN DE PUBLICACIONES (WIKI & CRUD)
// ==========================================
async function cargarPublicaciones() {
    try {
        const res = await fetch(`${API_URL}/publicaciones`);
        if (res.ok) {
            publicacionesLocales = await res.json();
        } else {
            publicacionesLocales = publicacionesIniciales;
        }
    } catch (err) {
        publicacionesLocales = publicacionesIniciales;
    }
    renderizarPublicaciones(publicacionesLocales);
    renderizarRecientes(publicacionesLocales);
}

function renderizarPublicaciones(lista) {
    const contenedor = document.getElementById("contenedor-articulos");
    if (!contenedor) return;

    if (lista.length === 0) {
        contenedor.innerHTML = `<p style="color: var(--text-muted);">No hay publicaciones disponibles.</p>`;
        return;
    }

    contenedor.innerHTML = lista.map(pub => {
        const textoPlano = pub.contenido.replace(/<[^>]*>?/gm, '');
        const extracto = textoPlano.length > 120 ? textoPlano.substring(0, 120) + "..." : textoPlano;

        return `
            <article class="article-card" style="display:flex; flex-direction:column; justify-content:space-between; padding:1.2rem; border:1px solid #e2e8f0; border-radius:8px; background:white;">
                <div>
                    <span class="article-badge" style="background:#e2e8f0; color:#334155; padding:3px 8px; border-radius:4px; font-size:0.8rem; font-weight:600;">${pub.tipo} • ${pub.categoria}</span>
                    <h3 class="article-title" style="margin:0.5rem 0 0.2rem 0; font-size:1.2rem;">${pub.titulo}</h3>
                    <p class="article-meta" style="font-size:0.85rem; color:#64748b; margin-bottom:0.8rem;">Por <strong>${pub.autor}</strong> — ${pub.fecha}</p>
                    <p style="font-size: 0.95rem; color: #334155; line-height:1.5;">${extracto}</p>
                </div>
                <div style="margin-top: 1rem; display: flex; gap: 8px; border-top: 1px solid #f1f5f9; padding-top: 0.8rem;">
                    <button class="btn btn-outline" style="padding:4px 10px; font-size:0.85rem;" onclick="verArticuloCompleto(${pub.id})">Leer</button>
                    <button class="btn btn-outline" style="padding:4px 10px; font-size:0.85rem;" onclick="cargarParaEditar(${pub.id})">Editar</button>
                    <button class="btn btn-danger" style="padding:4px 10px; font-size:0.85rem;" onclick="eliminarPublicacion(${pub.id})">Eliminar</button>
                </div>
            </article>
        `;
    }).join("");
}

function renderizarRecientes(lista) {
    const contenedor = document.getElementById("lista-recientes");
    if (!contenedor) return;

    const ultimos = [...lista].reverse().slice(0, 3);
    contenedor.innerHTML = ultimos.map(pub => `
        <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border-color, #e2e8f0);">
            <strong style="color: var(--navy-dark, #0f172a);">${pub.titulo}</strong>
            <br>
            <small style="color: var(--text-muted, #64748b);">${pub.tipo} | ${pub.categoria}</small>
        </div>
    `).join("");
}

async function verArticuloCompleto(id) {
    try {
        const res = await fetch(`${API_URL}/publicaciones/${id}`);
        let pub;
        if (res.ok) {
            pub = await res.json();
        } else {
            pub = publicacionesLocales.find(p => p.id === id);
        }

        if (!pub) return;

        document.getElementById("lectura-categoria").innerText = `${pub.tipo} • ${pub.categoria}`;
        document.getElementById("lectura-titulo").innerText = pub.titulo;
        document.getElementById("lectura-autor").innerText = pub.autor;
        document.getElementById("lectura-fecha").innerText = pub.fecha;
        document.getElementById("lectura-contenido").innerHTML = pub.contenido;

        mostrarSeccion("modulo-lectura");
    } catch (err) {
        console.error("Error al cargar artículo completo:", err);
    }
}

async function cargarParaEditar(id) {
    try {
        const res = await fetch(`${API_URL}/publicaciones/${id}`);
        let pub;
        if (res.ok) {
            pub = await res.json();
        } else {
            pub = publicacionesLocales.find(p => p.id === id);
        }

        if (!pub) return;

        editandoId = id;
        document.getElementById("edit-id").value = id;
        document.getElementById("titulo").value = pub.titulo;
        document.getElementById("tipo").value = pub.tipo;
        document.getElementById("categoria").value = pub.categoria;
        document.getElementById("autor").value = pub.autor;
        document.getElementById("contenido").value = pub.contenido;

        document.getElementById("form-titulo-header").innerText = "Editar Publicación";
        document.getElementById("btn-guardar-pub").innerText = "Guardar Cambios";
        document.getElementById("btn-cancelar-edicion").style.display = "inline-block";

        actualizarVistaPreviaEditor();
        mostrarSeccion("publicar");
    } catch (err) {
        console.error("Error al preparar edición:", err);
    }
}

function cancelarEdicion() {
    editandoId = null;
    const editIdInput = document.getElementById("edit-id");
    if (editIdInput) editIdInput.value = "";
    
    document.getElementById("form-publicacion").reset();
    document.getElementById("form-titulo-header").innerText = "Publicar Definición o Artículo";
    document.getElementById("btn-guardar-pub").innerText = "Guardar y Publicar";
    document.getElementById("btn-cancelar-edicion").style.display = "none";
    
    actualizarVistaPreviaEditor();
}

async function guardarPublicacion(event) {
    event.preventDefault();

    const payload = {
        titulo: document.getElementById("titulo").value,
        tipo: document.getElementById("tipo").value,
        categoria: document.getElementById("categoria").value,
        autor: document.getElementById("autor").value,
        fecha: new Date().toISOString().split('T')[0],
        contenido: document.getElementById("contenido").value
    };

    const url = editandoId ? `${API_URL}/publicaciones/${editandoId}` : `${API_URL}/publicaciones`;
    const method = editandoId ? 'PUT' : 'POST';

    try {
        await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } catch (err) {
        console.error("Error al guardar publicación:", err);
    }

    cancelarEdicion();
    await cargarPublicaciones();
    mostrarSeccion("glosario");
}

async function eliminarPublicacion(id) {
    if (confirm("¿Estás seguro de que deseas eliminar esta publicación de la Wiki?")) {
        try {
            await fetch(`${API_URL}/publicaciones/${id}`, { method: 'DELETE' });
        } catch (err) {
            console.error("Error al eliminar publicación:", err);
        }
        await cargarPublicaciones();
    }
}

function filtrarPublicaciones() {
    const busqueda = document.getElementById("input-buscar").value.toLowerCase();
    const categoria = document.getElementById("select-categoria").value;

    const filtrados = publicacionesLocales.filter(pub => {
        const coincideTexto = pub.titulo.toLowerCase().includes(busqueda) || 
                             pub.contenido.toLowerCase().includes(busqueda);
        const coincideCat = (categoria === "todas") || (pub.categoria === categoria);
        return coincideTexto && coincideCat;
    });

    renderizarPublicaciones(filtrados);
}

// ==========================================
// SIMULADOR DE MEMORIA RAM (CON PLANIFICADOR TEMPORIZADO)
// ==========================================
let intervalSimuladorRAM = null;

function iniciarRelojRAM() {
    if (!intervalSimuladorRAM) {
        intervalSimuladorRAM = setInterval(tickSimuladorRAM, 1000);
    }
}

function tickSimuladorRAM() {
    if (simuladorRAM.procesosEjecucion.length === 0) return;

    let seLiberaronProcesos = false;

    for (let i = simuladorRAM.procesosEjecucion.length - 1; i >= 0; i--) {
        let proc = simuladorRAM.procesosEjecucion[i];
        proc.tiempoRestante -= 1;

        if (proc.tiempoRestante <= 0) {
            simuladorRAM.usada -= proc.tamano;
            simuladorRAM.procesosEjecucion.splice(i, 1);
            seLiberaronProcesos = true;
        }
    }

    if (seLiberaronProcesos) {
        revisarColaEspera();
    }

    actualizarVistaSimulador();
}

function agregarProcesoSimulador(event) {
    event.preventDefault();

    const nombreInput = document.getElementById("proc-nombre");
    const tamanoInput = document.getElementById("proc-tamano");
    const tiempoInput = document.getElementById("proc-tiempo");

    const nombre = nombreInput.value.trim();
    const tamano = parseInt(tamanoInput.value);
    const tiempo = parseInt(tiempoInput.value) || 18;

    if (!nombre || isNaN(tamano) || tamano <= 0) return;

    const nuevoProceso = {
        id: simuladorRAM.siguienteId++,
        nombre: nombre,
        tamano: tamano,
        tiempoTotal: tiempo,
        tiempoRestante: tiempo
    };

    const ramDisponible = TOTAL_RAM_MB - simuladorRAM.usada;
    if (tamano <= ramDisponible) {
        simuladorRAM.procesosEjecucion.push(nuevoProceso);
        simuladorRAM.usada += tamano;
    } else {
        simuladorRAM.colaEspera.push(nuevoProceso);
    }

    nombreInput.value = "";
    tamanoInput.value = "128";
    if (tiempoInput) tiempoInput.value = "18";

    iniciarRelojRAM();
    actualizarVistaSimulador();
}

async function ejecutarEscenarioAleatorioRAM() {
    try {
        const res = await fetch(`${API_URL}/simulador/lote-aleatorio`, { method: 'POST' });
        if (res.ok) {
            const estadoBackend = await res.json();
            
            simuladorRAM.procesosEjecucion = estadoBackend.procesos_ejecucion.map(p => ({
                id: p.id,
                nombre: p.nombre,
                tamano: p.tamano_mb,
                tiempoTotal: p.ttl_inicial || p.ttl,
                tiempoRestante: p.ttl
            }));

            simuladorRAM.colaEspera = estadoBackend.cola_espera.map(p => ({
                id: p.id,
                nombre: p.nombre,
                tamano: p.tamano_mb,
                tiempoTotal: p.ttl_inicial || p.ttl,
                tiempoRestante: p.ttl
            }));

            simuladorRAM.usada = estadoBackend.ram_usada_mb;
            simuladorRAM.siguienteId = estadoBackend.siguiente_id;

            iniciarRelojRAM();
            actualizarVistaSimulador();
        }
    } catch (err) {
        console.error("Error al generar escenario aleatorio:", err);
    }
}

function terminarProceso(idProceso) {
    const idx = simuladorRAM.procesosEjecucion.findIndex(p => p.id === idProceso);
    if (idx !== -1) {
        const procEliminado = simuladorRAM.procesosEjecucion.splice(idx, 1)[0];
        simuladorRAM.usada -= procEliminado.tamano;
        revisarColaEspera();
    } else {
        const idxEspera = simuladorRAM.colaEspera.findIndex(p => p.id === idProceso);
        if (idxEspera !== -1) {
            simuladorRAM.colaEspera.splice(idxEspera, 1);
        }
    }
    actualizarVistaSimulador();
}

function revisarColaEspera() {
    let i = 0;
    while (i < simuladorRAM.colaEspera.length) {
        const proc = simuladorRAM.colaEspera[i];
        const ramDisponible = TOTAL_RAM_MB - simuladorRAM.usada;

        if (proc.tamano <= ramDisponible) {
            simuladorRAM.procesosEjecucion.push(proc);
            simuladorRAM.usada += proc.tamano;
            simuladorRAM.colaEspera.splice(i, 1);
        } else {
            i++;
        }
    }
}

function reiniciarSimulador() {
    simuladorRAM = {
        usada: 0,
        procesosEjecucion: [],
        colaEspera: [],
        siguienteId: 1
    };
    fetch(`${API_URL}/simulador/reiniciar`, { method: 'POST' }).catch(() => {});
    actualizarVistaSimulador();
}

function actualizarVistaSimulador() {
    const disponible = TOTAL_RAM_MB - simuladorRAM.usada;
    const porcentaje = ((simuladorRAM.usada / TOTAL_RAM_MB) * 100).toFixed(1);

    const elRamUsada = document.getElementById("ram-usada");
    const elRamDisp = document.getElementById("ram-disponible");
    if (elRamUsada) elRamUsada.innerText = `${simuladorRAM.usada} MB (${porcentaje}%)`;
    if (elRamDisp) elRamDisp.innerText = `${disponible} MB`;

    const bar = document.getElementById("ram-bar");
    if (bar) {
        bar.style.width = `${porcentaje}%`;
        if (porcentaje > 85) {
            bar.style.background = "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)";
        } else if (porcentaje > 60) {
            bar.style.background = "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)";
        } else {
            bar.style.background = "linear-gradient(90deg, #10b981 0%, #059669 100%)";
        }
    }

    const listEjec = document.getElementById("lista-ejecucion");
    if (listEjec) {
        if (simuladorRAM.procesosEjecucion.length === 0) {
            listEjec.innerHTML = `<li style="color: var(--text-muted); padding: 0.5rem 0;">No hay procesos corriendo en la RAM.</li>`;
        } else {
            listEjec.innerHTML = simuladorRAM.procesosEjecucion.map(p => {
                const pctTiempo = Math.max(0, Math.min(100, (p.tiempoRestante / p.tiempoTotal) * 100));
                return `
                    <li class="process-item" style="flex-direction: column; align-items: stretch; gap: 6px; padding:8px; border:1px solid #e2e8f0; border-radius:6px; margin-bottom:6px; background:white;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${p.nombre}</strong> <small style="color:#64748b;">(ID: ${p.id})</small>
                                <br><small style="color:#2563eb; font-weight:600;">${p.tamano} MB</small>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="badge" style="background:#e0f2fe; color:#0369a1; font-size:0.8rem; padding:2px 6px; border-radius:4px;">${p.tiempoRestante}s</span>
                                <button class="btn btn-danger" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick="terminarProceso(${p.id})">Terminar</button>
                            </div>
                        </div>
                        <div style="background:#e2e8f0; height: 4px; border-radius:2px; overflow:hidden;">
                            <div style="background:#2563eb; height:100%; width:${pctTiempo}%; transition: width 0.3s linear;"></div>
                        </div>
                    </li>
                `;
            }).join("");
        }
    }

    const listEsp = document.getElementById("lista-espera");
    if (listEsp) {
        if (simuladorRAM.colaEspera.length === 0) {
            listEsp.innerHTML = `<li style="color: var(--text-muted); padding: 0.5rem 0;">No hay procesos en espera.</li>`;
        } else {
            listEsp.innerHTML = simuladorRAM.colaEspera.map(p => `
                <li class="process-item" style="border-left: 3px solid #f59e0b; padding:8px; border-radius:6px; margin-bottom:6px; background:white; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>${p.nombre}</strong> <small style="color:#64748b;">(ID: ${p.id})</small>
                        <br><small style="color:#d97706; font-weight:600;">${p.tamano} MB [Esperando RAM] (${p.tiempoTotal}s)</small>
                    </div>
                    <button class="btn btn-secondary" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick="terminarProceso(${p.id})">Cancelar</button>
                </li>
            `).join("");
        }
    }
}

// ==========================================
// SIMULADOR DE CONCURRENCIA (CABINA DE VUELO)
// ==========================================
async function cargarEstadoVuelo() {
    try {
        const res = await fetch(`${API_URL}/simulador-concurrencia/estado`);
        if (res.ok) {
            const data = await res.json();
            actualizarVistaCabina(data);
        }
    } catch (err) {
        console.error("Error al obtener estado del vuelo:", err);
    }
}

function actualizarVistaCabina(data) {
    const elIntegridad = document.getElementById('stat-integridad');
    const elOverbooking = document.getElementById('stat-overbooking');

    if (elIntegridad) {
        if (data.asientos_con_overbooking > 0) {
            elIntegridad.textContent = "OVERBOOKING DETECTADO";
            elIntegridad.style.color = "#ef4444";
        } else if (data.conteo_exito > 0) {
            elIntegridad.textContent = "INTEGRIDAD GARANTIZADA";
            elIntegridad.style.color = "#10b981";
        } else {
            elIntegridad.textContent = "Esperando acción";
            elIntegridad.style.color = "#64748b";
        }
    }

    if (elOverbooking) {
        elOverbooking.textContent = `${data.asientos_con_overbooking} de 12 asientos`;
    }

    const gridCabina = document.getElementById('grid-cabina');
    const selectManual = document.getElementById('select-asiento-manual');

    if (gridCabina) gridCabina.innerHTML = "";
    if (selectManual) selectManual.innerHTML = "";

    const filas = { "1": [], "2": [], "3": [] };

    data.asientos.forEach(asiento => {
        const numFila = asiento.id[0];
        if (filas[numFila]) filas[numFila].push(asiento);

        if (selectManual && !asiento.pasajero_confirmado) {
            const opt = document.createElement('option');
            opt.value = asiento.id;
            opt.textContent = `Asiento ${asiento.id} (Disponible)`;
            selectManual.appendChild(opt);
        }
    });

    if (selectManual && selectManual.options.length === 0) {
        selectManual.innerHTML = "<option value=''>Vuelo Lleno</option>";
    }

    if (gridCabina) {
        Object.keys(filas).forEach(f => {
            const rowDiv = document.createElement('div');
            rowDiv.className = 'cabin-row';

            const asientosFila = filas[f];
            const leftSeats = asientosFila.filter(a => a.id.includes('A') || a.id.includes('B'));
            const rightSeats = asientosFila.filter(a => a.id.includes('C') || a.id.includes('D'));

            let html = "";
            leftSeats.forEach(a => html += crearBotonAsientoHTML(a));
            html += `<div class="aisle">Fila ${f}</div>`;
            rightSeats.forEach(a => html += crearBotonAsientoHTML(a));

            rowDiv.innerHTML = html;
            gridCabina.appendChild(rowDiv);
        });
    }

    const terminalLogs = document.getElementById('terminal-logs');
    if (terminalLogs) {
        terminalLogs.textContent = `[PID OS Kernel: ${data.pid || 'N/A'}]\n` + (data.logs && data.logs.length > 0 ? data.logs.join('\n') : "Esperando acciones...");
        terminalLogs.scrollTop = terminalLogs.scrollHeight;
    }
}

function crearBotonAsientoHTML(asiento) {
    let clase = "seat-btn";
    let subtext = "Libre";

    if (asiento.overbooking) {
        clase += " seat-overbooking";
        subtext = `OVERBOOK (${asiento.total_asignaciones})`;
    } else if (asiento.pasajero_confirmado) {
        clase += " seat-occupied";
        subtext = asiento.pasajero_confirmado;
    }

    return `
        <button class="${clase}" onclick="seleccionarAsientoDirecto('${asiento.id}')" title="Asiento ${asiento.id} - ${subtext}">
            <span class="seat-id">${asiento.id}</span>
            <span class="seat-passenger">${subtext}</span>
        </button>
    `;
}

function seleccionarAsientoDirecto(idAsiento) {
    const select = document.getElementById('select-asiento-manual');
    if (select) {
        select.value = idAsiento;
        const inputNombre = document.getElementById('input-pasajero-nombre');
        if (inputNombre) inputNombre.focus();
    }
}

async function reservarAsientoManual() {
    const select = document.getElementById('select-asiento-manual');
    const inputNombre = document.getElementById('input-pasajero-nombre');

    if (!select) return;

    const idAsiento = select.value;
    const pasajero = (inputNombre ? inputNombre.value.trim() : "") || "Pasajero Web";

    if (!idAsiento) {
        alert("Selecciona un asiento disponible.");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/simulador-concurrencia/reservar-manual`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_asiento: idAsiento, pasajero: pasajero })
        });

        const data = await res.json();
        if (res.ok) {
            actualizarVistaCabina(data);
        } else {
            alert(data.error || "No se pudo reservar el asiento.");
        }
    } catch (err) {
        console.error("Error al reservar manual:", err);
    }
}

async function reiniciarVuelo() {
    try {
        const res = await fetch(`${API_URL}/simulador-concurrencia/reiniciar`, { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            actualizarVistaCabina(data);
        }
    } catch (err) {
        console.error("Error al reiniciar vuelo:", err);
    }
}

async function ejecutarSimulacionConcurrencia() {
    const chkModo = document.getElementById('chk-modo-protegido');
    const modoProtegido = chkModo ? chkModo.checked : false;
    const terminalLogs = document.getElementById('terminal-logs');

    if (terminalLogs) terminalLogs.textContent = "Lanzando ráfaga de hilos en paralelo...";

    try {
        const res = await fetch(`${API_URL}/simulador-concurrencia/ejecutar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modo_protegido: modoProtegido })
        });

        if (res.ok) {
            const data = await res.json();
            actualizarVistaCabina(data);
        }
    } catch (err) {
        console.error("Error en prueba de concurrencia:", err);
    }
}