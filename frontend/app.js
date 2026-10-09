// Estado global del simulador de RAM

const TOTAL_RAM_MB = 1024;

let simuladorRAM = {
    usada: 0,
    procesosEjecucion: [],
    colaEspera: [],
    siguienteId: 1
};

// Datos iniciales de ejemplo para las publicaciones
const publicacionesIniciales = [
    {
        id: 1,
        titulo: "Paginación y Segmentación",
        tipo: "Definición",
        categoria: "Sistemas Operativos",
        autor: "Cátedra de SO",
        fecha: "2026-10-08",
        contenido: "La paginación es un esquema de gestión de memoria que permite que el espacio de direcciones físicas de un proceso no sea contiguo. Divide la memoria en bloques de tamaño fijo llamados marcos."
    },
    {
        id: 2,
        titulo: "Estructura de Árboles B+",
        tipo: "Artículo",
        categoria: "Estructuras de Datos",
        autor: "Sistemas UMG",
        fecha: "2026-10-07",
        contenido: "Los árboles B+ son variantes de los árboles B optimizados para sistemas de archivos y bases de datos. Todos los datos se almacenan en las hojas, lo que facilita las búsquedas por rango."
    }
];

// Inicialización de la aplicación

document.addEventListener("DOMContentLoaded", () => {
    cargarPublicaciones();
    actualizarVistaSimulador();
});

// Navegación entre secciones

function mostrarSeccion(idSeccion) {
    document.querySelectorAll(".modulo").forEach(modulo => {
        modulo.classList.remove("active");
    });
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.classList.remove("active");
    });

    const seccionObj = document.getElementById(idSeccion);
    if (seccionObj) {
        seccionObj.classList.add("active");
    }

    // Resaltar botón de menú correspondiente
    const btnActivo = Array.from(document.querySelectorAll(".nav-btn"))
        .find(b => b.getAttribute("onclick") && b.getAttribute("onclick").includes(idSeccion));
    if (btnActivo) btnActivo.classList.add("active");
}

// Gestio de publicaciones
function obtenerPublicacionesGuardadas() {
    const data = localStorage.getItem("wiki_publicaciones");
    if (!data) {
        localStorage.setItem("wiki_publicaciones", JSON.stringify(publicacionesIniciales));
        return publicacionesIniciales;
    }
    return JSON.parse(data);
}

function cargarPublicaciones() {
    const lista = obtenerPublicacionesGuardadas();
    renderizarPublicaciones(lista);
    renderizarRecientes(lista);
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

function guardarPublicacion(event) {
    event.preventDefault();

    const titulo = document.getElementById("titulo").value;
    const tipo = document.getElementById("tipo").value;
    const categoria = document.getElementById("categoria").value;
    const autor = document.getElementById("autor").value;
    const contenido = document.getElementById("contenido").value;

    const nuevaPub = {
        id: Date.now(),
        titulo,
        tipo,
        categoria,
        autor,
        fecha: new Date().toISOString().split("T")[0],
        contenido
    };

    const listaActual = obtenerPublicacionesGuardadas();
    listaActual.unshift(nuevaPub);
    localStorage.setItem("wiki_publicaciones", JSON.stringify(listaActual));

    document.getElementById("form-publicacion").reset();
    cargarPublicaciones();
    alert("¡Publicación guardada con éxito!");
    mostrarSeccion("glosario");
}

function filtrarPublicaciones() {
    const busqueda = document.getElementById("input-buscar").value.toLowerCase();
    const categoria = document.getElementById("select-categoria").value;
    const lista = obtenerPublicacionesGuardadas();

    const filtrados = lista.filter(pub => {
        const coincideTexto = pub.titulo.toLowerCase().includes(busqueda) || 
                             pub.contenido.toLowerCase().includes(busqueda);
        const coincideCat = (categoria === "todas") || (pub.categoria === categoria);
        return coincideTexto && coincideCat;
    });

    renderizarPublicaciones(filtrados);
}

// Simulación de RAM

function agregarProcesoSimulador(event) {
    event.preventDefault();

    const nombreInput = document.getElementById("proc-nombre");
    const tamanoInput = document.getElementById("proc-tamano");

    const nombre = nombreInput.value.trim();
    const tamano = parseInt(tamanoInput.value);

    if (!nombre || isNaN(tamano) || tamano <= 0) return;

    const nuevoProceso = {
        id: simuladorRAM.siguienteId++,
        nombre: nombre,
        tamano: tamano
    };

    // Intentar asignar a la RAM
    const ramDisponible = TOTAL_RAM_MB - simuladorRAM.usada;
    if (tamano <= ramDisponible) {
        simuladorRAM.procesosEjecucion.push(nuevoProceso);
        simuladorRAM.usada += tamano;
    } else {
        simuladorRAM.colaEspera.push(nuevoProceso);
    }

    nombreInput.value = "";
    tamanoInput.value = "128";
    actualizarVistaSimulador();
}

function terminarProceso(idProceso) {
    // Buscar en ejecución
    const idx = simuladorRAM.procesosEjecucion.findIndex(p => p.id === idProceso);
    if (idx !== -1) {
        const procEliminado = simuladorRAM.procesosEjecucion.splice(idx, 1)[0];
        simuladorRAM.usada -= procEliminado.tamano;
        revisarColaEspera();
    } else {
        // Buscar en cola de espera
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
            // Pasa de la cola a Ejecución
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

    // Actualizar indicadores
    document.getElementById("ram-usada").innerText = `${simuladorRAM.usada} MB (${porcentaje}%)`;
    document.getElementById("ram-disponible").innerText = `${disponible} MB`;

    // Barra de progreso
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

    // Renderizar procesos en ejecución
    const listEjec = document.getElementById("lista-ejecucion");
    if (simuladorRAM.procesosEjecucion.length === 0) {
        listEjec.innerHTML = `<li style="color: var(--text-muted); padding: 0.5rem 0;">No hay procesos corriendo en la RAM.</li>`;
    } else {
        listEjec.innerHTML = simuladorRAM.procesosEjecucion.map(p => `
            <li class="process-item">
                <div>
                    <strong>${p.nombre}</strong> <small style="color:var(--text-muted);">(ID: ${p.id})</small>
                    <br><small style="color:var(--blue-primary); font-weight:600;">${p.tamano} MB</small>
                </div>
                <button class="btn btn-danger" style="padding:0.3rem 0.6rem; font-size:0.8rem;" onclick="terminarProceso(${p.id})">Terminar</button>
            </li>
        `).join("");
    }

    // Renderizar cola de espera
    const listEsp = document.getElementById("lista-espera");
    if (simuladorRAM.colaEspera.length === 0) {
        listEsp.innerHTML = `<li style="color: var(--text-muted); padding: 0.5rem 0;">No hay procesos en espera.</li>`;
    } else {
        listEsp.innerHTML = simuladorRAM.colaEspera.map(p => `
            <li class="process-item" style="border-left: 3px solid var(--warning-color);">
                <div>
                    <strong>${p.nombre}</strong> <small style="color:var(--text-muted);">(ID: ${p.id})</small>
                    <br><small style="color:var(--warning-color); font-weight:600;">${p.tamano} MB [Esperando RAM]</small>
                </div>
                <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.8rem;" onclick="terminarProceso(${p.id})">Cancelar</button>
            </li>
        `).join("");
    }
}