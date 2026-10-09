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

// Datos iniciales de fallback
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
});

// ==========================================
// NAVEGACIÓN DINÁMICA ENTRE SECCIONES
// ==========================================
function mostrarSeccion(idSeccion) {
    // 1. Ocultar todos los módulos
    document.querySelectorAll(".modulo").forEach(modulo => {
        modulo.classList.remove("active");
    });

    // 2. Desactivar todos los botones del menú
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.classList.remove("active");
    });

    // 3. Activar el módulo seleccionado
    const seccionObj = document.getElementById(idSeccion);
    if (seccionObj) {
        seccionObj.classList.add("active");
    }

    // 4. Activar el botón correspondiente en el menú superior
    const btnActivo = Array.from(document.querySelectorAll(".nav-btn"))
        .find(b => b.getAttribute("onclick") && b.getAttribute("onclick").includes(`'${idSeccion}'`));
    if (btnActivo) {
        btnActivo.classList.add("active");
    }
}

// ==========================================
// GESTIÓN DE PUBLICACIONES (WIKI)
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

    contenedor.innerHTML = lista.map(pub => `
        <article class="article-card">
            <div>
                <span class="article-badge">${pub.tipo} • ${pub.categoria}</span>
                <h3 class="article-title">${pub.titulo}</h3>
                <p class="article-meta">Por <strong>${pub.autor}</strong> — ${pub.fecha}</p>
                <p style="font-size: 0.95rem; color: #334155;">${pub.contenido}</p>
            </div>
        </article>
    `).join("");
}

function renderizarRecientes(lista) {
    const contenedor = document.getElementById("lista-recientes");
    if (!contenedor) return;

    const ultimos = [...lista].reverse().slice(0, 3);
    contenedor.innerHTML = ultimos.map(pub => `
        <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border-color);">
            <strong style="color: var(--navy-dark);">${pub.titulo}</strong>
            <br>
            <small style="color: var(--text-muted);">${pub.tipo} | ${pub.categoria}</small>
        </div>
    `).join("");
}

async function guardarPublicacion(event) {
    event.preventDefault();

    const nuevaPub = {
        titulo: document.getElementById("titulo").value,
        tipo: document.getElementById("tipo").value,
        categoria: document.getElementById("categoria").value,
        autor: document.getElementById("autor").value,
        contenido: document.getElementById("contenido").value
    };

    try {
        await fetch(`${API_URL}/publicaciones`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(nuevaPub)
        });
    } catch (err) {
        console.error("Error al guardar publicación:", err);
    }

    document.getElementById("form-publicacion").reset();
    await cargarPublicaciones();
    mostrarSeccion("glosario");
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

    // Descontar 1 segundo a cada proceso en ejecución
    for (let i = simuladorRAM.procesosEjecucion.length - 1; i >= 0; i--) {
        let proc = simuladorRAM.procesosEjecucion[i];
        proc.tiempoRestante -= 1;

        // Si completó su tiempo de ejecución, liberarlo
        if (proc.tiempoRestante <= 0) {
            simuladorRAM.usada -= proc.tamano;
            simuladorRAM.procesosEjecucion.splice(i, 1);
            seLiberaronProcesos = true;
        }
    }

    // Si se liberó espacio, promover procesos en cola de espera
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
    const tiempo = parseInt(tiempoInput.value) || 5;

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
    if (tiempoInput) tiempoInput.value = "5";

    iniciarRelojRAM();
    actualizarVistaSimulador();
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

    // Renderizar procesos en ejecución con temporizador
    const listEjec = document.getElementById("lista-ejecucion");
    if (listEjec) {
        if (simuladorRAM.procesosEjecucion.length === 0) {
            listEjec.innerHTML = `<li style="color: var(--text-muted); padding: 0.5rem 0;">No hay procesos corriendo en la RAM.</li>`;
        } else {
            listEjec.innerHTML = simuladorRAM.procesosEjecucion.map(p => {
                const pctTiempo = Math.max(0, Math.min(100, (p.tiempoRestante / p.tiempoTotal) * 100));
                return `
                    <li class="process-item" style="flex-direction: column; align-items: stretch; gap: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${p.nombre}</strong> <small style="color:var(--text-muted);">(ID: ${p.id})</small>
                                <br><small style="color:var(--blue-primary); font-weight:600;">${p.tamano} MB</small>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="badge" style="background:#e0f2fe; color:#0369a1; font-size:0.8rem;">⏱️ ${p.tiempoRestante}s</span>
                                <button class="btn btn-danger" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick="terminarProceso(${p.id})">Terminar</button>
                            </div>
                        </div>
                        <div style="background:#e2e8f0; height: 4px; border-radius:2px; overflow:hidden;">
                            <div style="background:var(--blue-primary); height:100%; width:${pctTiempo}%; transition: width 0.3s linear;"></div>
                        </div>
                    </li>
                `;
            }).join("");
        }
    }

    // Renderizar cola de espera
    const listEsp = document.getElementById("lista-espera");
    if (listEsp) {
        if (simuladorRAM.colaEspera.length === 0) {
            listEsp.innerHTML = `<li style="color: var(--text-muted); padding: 0.5rem 0;">No hay procesos en espera.</li>`;
        } else {
            listEsp.innerHTML = simuladorRAM.colaEspera.map(p => `
                <li class="process-item" style="border-left: 3px solid var(--warning-color);">
                    <div>
                        <strong>${p.nombre}</strong> <small style="color:var(--text-muted);">(ID: ${p.id})</small>
                        <br><small style="color:var(--warning-color); font-weight:600;">${p.tamano} MB [Esperando RAM] (${p.tiempoTotal}s)</small>
                    </div>
                    <button class="btn btn-secondary" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick="terminarProceso(${p.id})">Cancelar</button>
                </li>
            `).join("");
        }
    }
}

// ==========================================
// SIMULADOR DE CONCURRENCIA (API FLASK)
// ==========================================
async function ejecutarSimulacionConcurrencia() {
    const modoProtegido = document.getElementById('chk-modo-protegido').checked;
    const gridAsientos = document.getElementById('grid-asientos');
    const terminalLogs = document.getElementById('terminal-logs');

    gridAsientos.innerHTML = "<p class='placeholder-text'>Ejecutando 20 hilos concurrentes...</p>";
    terminalLogs.textContent = "Procesando reservas de asientos en el backend...";

    try {
        const res = await fetch(`${API_URL}/simulador-concurrencia/ejecutar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modo_protegido: modoProtegido, num_agentes: 20 })
        });

        if (!res.ok) {
            throw new Error(`Respuesta HTTP con error: ${res.status}`);
        }

        const data = await res.json();

        // 1. Actualizar Estados de Integridad
        const elIntegridad = document.getElementById('stat-integridad');
        const elOverbooking = document.getElementById('stat-overbooking');

        if (data.integridad_ok) {
            elIntegridad.textContent = "✅ INTEGRIDAD GARANTIZADA";
            elIntegridad.style.color = "#10b981";
        } else {
            elIntegridad.textContent = "❌ CONDICIÓN DE CARRERA (OVERBOOKING)";
            elIntegridad.style.color = "#ef4444";
        }

        elOverbooking.textContent = `${data.asientos_con_overbooking} de 5 asientos`;

        // 2. Renderizar Tarjetas de Asientos
        gridAsientos.innerHTML = "";
        data.asientos.forEach(asiento => {
            const card = document.createElement('div');
            card.className = `seat-card ${asiento.overbooking ? 'seat-danger' : (asiento.total_asignaciones > 0 ? 'seat-success' : '')}`;

            card.innerHTML = `
                <div class="seat-header">
                    <span>Asiento ${asiento.id}</span>
                    <span class="seat-badge">${asiento.overbooking ? '⚠️ OVERBOOKING' : 'OK'}</span>
                </div>
                <div>
                    <p style="font-size:0.85rem;"><strong>Confirmado:</strong> ${asiento.pasajero_confirmado || 'N/A'}</p>
                    <p style="font-size:0.8rem; color:#6c757d;">Intentos: ${asiento.total_asignaciones}</p>
                </div>
            `;
            gridAsientos.appendChild(card);
        });

        // 3. Imprimir Logs del Kernel en la Consola Negra
        terminalLogs.textContent = `[PID OS: ${data.pid}]\n` + data.logs.join('\n');

    } catch (err) {
        console.error("Error al ejecutar simulación:", err);
        gridAsientos.innerHTML = "<p style='color:red;'>Error al conectar con el servidor backend.</p>";
        terminalLogs.textContent = "Error: Asegúrate de que el servidor Flask esté corriendo (python backend/app.py).";
    }
}