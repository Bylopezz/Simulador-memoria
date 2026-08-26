# Simulador de Gestión de Procesos en Memoria RAM

Este proyecto es un simulador interactivo de gestión de procesos y memoria RAM limitada (1 GB / 1024 MB) desarrollado en Python para entornos Linux (WSL).

Características
- **Límite de RAM:** Simulación dinámica con 1024 MB de memoria.
- **Concurrencia:** Manejo de procesos simultáneos mediante *multithreading* (`threading`).
- **Cola de Espera:** Gestión de procesos diferidos por falta de memoria RAM usando FIFO (`queue.Queue`).
- **Interfaz Interactiva:** Monitor en tiempo real desarrollado con la librería `rich`.
- **Liberación Automática:** Recuperación instantánea de memoria al finalizar la ejecución de cada proceso.

Tecnologías Utilizadas
- **Lenguaje:** Python 3
- **Librerías:** 
  - `threading` y `queue` (Módulos nativos para concurrencia y control de cola)
  - `rich` (Librería externa para la interfaz CLI)

Requisitos e Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/Bylopezz/Simulador-memoria.git](https://github.com/Bylopezz/Simulador-memoria.git)
   cd Simulador-memoria
