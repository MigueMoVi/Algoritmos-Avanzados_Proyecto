# Asignación de vueltas a buses con ventanas y tráfico — Transporte urbano de Cusco

Proyecto semestral de **Algoritmos Avanzados** (UNSAAC, 2026-II) — **Grupo 4**
Tema: *optimización de asignación de trabajos en máquinas idénticas*.

| Integrante | Código |
|---|---|
| Aguilar Quispe, Yon | 111276 |
| Choque Mamani, Brayan Isau | 215719 |
| Huacani de la Cruz, Dany | 081561 |
| Moreano Villena, Miguel Angel | 211859 |

Docente: Héctor Eduardo Ugarte Rojas.

## Problema en una línea

Para cada empresa/ruta (37 en total), asignar cada **vuelta** (origen → destino → origen) a un
**bus** de su propia flota (máquinas idénticas), eligiendo su hora de salida dentro de una
**ventana**, respetando la jornada 06:00–22:00, el **almuerzo** de 2 h y un **tiempo de viaje que
depende del tráfico** según la hora de salida. Objetivo lexicográfico: 1) maximizar vueltas
atendidas, 2) minimizar la carga máxima por bus `L_max`.

## Instalación

Requiere Python ≥ 3.10.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .                                       # instala el paquete `sched`
```

Sin `pip install -e .` también funciona anteponiendo `PYTHONPATH=src` (Linux/macOS) o
`set PYTHONPATH=src` (Windows) a los comandos.

## Uso rápido

```bash
python -m sched build                                   # Excel -> data/instances/*.json (37 rutas + DEMO)
python -m sched profiles                                # perfiles de tráfico T0 / T1 / T2
python -m sched demo --traffic T2                       # ejemplo manual: LS, LPT, B&B y CP-SAT
python -m sched run --route RTI-01 --alg ls --traffic T1 --gantt
python -m sched run --route RTI-01 --alg lpt --traffic T2
python -m sched run --instance mi_instancia.json --alg bnb --traffic T0
python -m sched simulate --route RTI-01 --alg ls --traffic T1 --sigma 0.2
python -m pytest -q                                     # 35 pruebas
python experiments/run_experiments.py                   # E1–E4 (≈ 3–4 min) -> results/
python experiments/build_excel.py                       # Excel actualizado -> results/
```

Cada `run` imprime métricas, **valida** el programa con un verificador independiente y escribe
`results/<ruta>_<alg>_<tráfico>.csv` (y un diagrama de Gantt con `--gantt`).

## Estructura del repositorio

```
src/sched/
  traffic.py      modelo de tráfico (velocidad por franja, FIFO) y perfiles T0/T1/T2
  model.py        Job, Bus, Instance, BusTimeline (huecos + almuerzo flexible), Schedule
  builder.py      Excel -> instancias; instancia manual; generador aleatorio con semilla
  algorithms/
    greedy.py     List Scheduling (LS) y LPT adaptados
    bnb.py        Ramificación y poda (exacto en instancias pequeñas)
    cpsat.py      Modelo exacto de referencia con OR-Tools CP-SAT
  validator.py    verificación independiente de todas las restricciones
  metrics.py      L_max, desbalance, utilización, cota inferior, saturación ρ
  simulation.py   Monte Carlo de ejecución con tráfico estocástico
  viz.py          diagramas de Gantt
  cli.py          interfaz de línea de comandos (python -m sched ...)
tests/            pytest: casos básicos, límite, adversos y de escala
experiments/      run_experiments.py (E1–E4) y build_excel.py
data/raw/         Excel del proyecto (37 empresas/rutas)
data/instances/   instancias JSON generadas (una por ruta + DEMO)
data/traffic/     perfiles de tráfico en JSON (editables)
results/          CSV, figuras y Excel actualizado
docs/             plan de aprendizaje, bitácoras y matriz de contribuciones
```

## Formatos de archivo

**Instancia (`data/instances/RTI-01.json`)**

```json
{"route": "RTI-01", "company": "E.T. SAYLLA S.A.", "day_start": "06:00", "day_end": "22:00",
 "buses": [{"id": "RTI-01-B1", "lunch_r": "10:30", "lunch_d": "11:30", "lunch_min": 120}, ...],
 "jobs":  [{"id": "RTI-01-J001", "base_min": 148.8, "r": "06:00", "d": "06:15", "nominal": "06:00"}, ...]}
```

**Perfil de tráfico (`data/traffic/perfil_T2.json`)** — franjas `start`, `end`, `factor`.
Se puede pasar un perfil propio con `--traffic ruta/al/perfil.json`.

**Salida (`results/*.csv`)** — una fila por vuelta: ruta, trabajo, bus, ventana, inicio, fin,
duración con tráfico y duración base; las vueltas no asignadas aparecen con `bus = NO_ASIGNADO`.

## Reproducibilidad

* Todas las instancias aleatorias y la simulación usan semillas fijas (`seed`, por defecto 2026).
* CP-SAT corre con 1 hilo y semilla fija en el ejemplo manual.
* Los factores de tráfico y las ventanas son **supuestos experimentales** documentados; la
  fuente 2020 no contiene horarios individuales ni mediciones de congestión.

## Notas sobre los datos

| Tipo | Contenido |
|---|---|
| Datos de la fuente de referencia | Flota operativa, tiempo de vuelta, demanda y viajes por unidad vehicular de las 37 empresas/rutas (*Tabla de datos — Unidades de transporte — Flota operativa 2020*). |
| Parámetros construidos por el grupo | Excel del proyecto, número de vueltas planificadas (flota × viajes por unidad), inicios nominales e instancias JSON. |
| Supuestos experimentales | Ventanas de inicio (±15 min en 06–09 y 16–19; ±30 min en el resto), jornada 06:00–22:00, almuerzo de 2 h en tres turnos con ventana de ±30 min, perfiles de tráfico T0/T1/T2 y variabilidad σ. |

El constructor verifica que el número de vueltas de cada ruta coincida con las vueltas
planificadas, que toda ventana sea válida (r ≤ d) y que toda vuelta pueda terminar antes de las 22:00.
