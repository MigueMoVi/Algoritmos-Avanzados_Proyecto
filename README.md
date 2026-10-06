# Asignación de vueltas a buses con ventanas y tráfico — Transporte urbano de Cusco

Proyecto semestral de **Algoritmos Avanzados** (UNSAAC, 2026-II) — **Grupo 4**.
Tema: *optimización de asignación de trabajos en máquinas idénticas*.
Docente: Héctor Eduardo Ugarte Rojas.

| Integrante | Código |
|---|---|
| Aguilar Quispe, Yon | 111276 |
| Choque Mamani, Brayan Isau | 215719 |
| Huacani de la Cruz, Dany | 081561 |
| Moreano Villena, Miguel Angel | 211859 |

## Objetivo

Para cada empresa/ruta (35 rutas experimentales), asignar cada **vuelta** (origen → destino →
origen) a un **bus** de su propia flota (máquinas idénticas) y fijar su hora de salida dentro de
su **ventana**, respetando la jornada 06:00–22:00, el **almuerzo** de 2 h de cada bus y un
**tiempo de viaje p_j(s_j) que depende de la hora de salida** por efecto del tráfico.

Objetivo lexicográfico: 1) maximizar las vueltas atendidas; 2) minimizar la carga máxima de
conducción por bus `L_max`.

**Entrega 1:** se implementan y comparan **List Scheduling (LS)** y **LPT**. El repositorio incluye
además prototipos de Ramificación y Poda, CP-SAT y simulación de robustez, previstos como
mecanismos de referencia para etapas posteriores; no forman parte de la evaluación de esta entrega.

## Estructura

```
src/bus_sched/
  traffic.py      perfiles de tráfico T0/T1/T2 y tiempo de viaje p_j(s)
  model.py        Job, Bus, Instance, BusTimeline (huecos y almuerzo), Schedule
  builder.py      Excel -> instancias (regla general de vueltas y ventanas), validación de datos
  algorithms/
    greedy.py     List Scheduling y LPT                       <- Entrega 1
    bnb.py        Ramificación y Poda                          (referencia, etapa posterior)
    cpsat.py      modelo CP-SAT                                (referencia, etapa posterior)
  simulation.py   robustez por Monte Carlo                     (etapa posterior)
  validator.py    verificación independiente de restricciones
  metrics.py      vueltas atendidas, L_max, cota inferior, desbalance, saturación
  viz.py, cli.py  diagramas de Gantt e interfaz de línea de comandos
tests/            pytest (LS/LPT, tráfico, datos, referencia)
experiments/      run_experiments.py (E1), build_excel.py, export_latex.py, fig_arquitectura.py, demo_prototipo.ipynb
data/raw/         Excel del proyecto (35 empresas/rutas)
data/instances/   instancias JSON (35 rutas + DEMO), generadas por `build`
data/traffic/     perfiles de tráfico en JSON
results/          CSV, figuras y Excel de la Entrega 1
docs/             informe LaTeX (docs/informe), plan de aprendizaje, bitácoras y contribuciones
```

## Instalación

Requiere Python ≥ 3.10.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
# opcional, solo para el prototipo CP-SAT: pip install ortools
```

Sin `pip install -e .` los comandos funcionan anteponiendo `PYTHONPATH=src`.

## Ejecución

```bash
python -m bus_sched build                                     # genera data/instances/*.json (35 rutas + DEMO)
python -m bus_sched profiles                                  # muestra T0, T1, T2
python -m bus_sched run --route RTI-01 --alg ls  --traffic T1 --gantt     # List Scheduling
python -m bus_sched run --route RTI-01 --alg lpt --traffic T1             # LPT
python -m bus_sched demo --traffic T2                         # ejemplo manual (LS y LPT)
python experiments/run_experiments.py                     # E1: 35 rutas × {LS, LPT} × {T0, T1, T2}
python experiments/build_excel.py                         # Excel de la Entrega 1
python experiments/export_latex.py                        # tablas y figuras del informe LaTeX
python -m pytest -q                                       # pruebas
```

Cada `run` imprime las métricas, **valida** la solución y escribe
`results/<ruta>_<alg>_<tráfico>.csv` (y un Gantt con `--gantt`).

### Ejemplo mínimo

```json
{"route": "MINI", "company": "Ejemplo", "day_start": "06:00", "day_end": "22:00",
 "buses": [{"id": "MINI-B1", "lunch_r": "10:30", "lunch_d": "11:30", "lunch_min": 120},
           {"id": "MINI-B2", "lunch_r": "12:00", "lunch_d": "13:00", "lunch_min": 120}],
 "jobs":  [{"id": "J1", "base_min": 90, "r": "06:00", "d": "06:30", "nominal": "06:15"},
           {"id": "J2", "base_min": 90, "r": "06:30", "d": "07:00", "nominal": "06:45"},
           {"id": "J3", "base_min": 90, "r": "08:00", "d": "08:30", "nominal": "08:15"}]}
```

```bash
python -m bus_sched run --instance mini.json --alg ls --traffic T2
```

## Formato de datos

* **Instancia (JSON):** ruta, empresa, jornada, buses (ventana de almuerzo) y vueltas
  (duración base en minutos, ventana `r`–`d` y salida nominal, en HH:MM).
* **Perfil de tráfico (JSON):** franjas `start`, `end`, `factor` y `outside_factor`.
  Se puede usar un perfil propio con `--traffic archivo.json`.
* **Salida (CSV):** una fila por vuelta: ruta, vuelta, bus, ventana, salida, llegada, duración con
  tráfico y duración base; las no atendidas llevan `bus = NO_ASIGNADO`.

## Datos

| Tipo | Contenido |
|---|---|
| Fuente de referencia | Flota operativa, tiempo de vuelta, demanda y viajes por unidad vehicular (*Tabla de datos — Unidades de transporte — Flota operativa 2020*). Se seleccionaron 35 empresas/rutas con parámetros consistentes para la generación reproducible de instancias. |
| Construidos por el grupo | Excel del proyecto, vueltas planificadas = round(flota × viajes por unidad), inicios nominales e instancias JSON. |
| Supuestos experimentales | Ventanas (±15 min en 06–09 y 16–19; ±30 min en el resto), jornada 06:00–22:00, almuerzo de 2 h en tres turnos con ventana de ±30 min, perfiles de tráfico T0/T1/T2. Los factores de tráfico no son mediciones oficiales. |

`build` genera las vueltas de **todas** las rutas con la misma regla general y verifica que
coincidan con la hoja *Trabajos y ventanas*; también valida ventanas y jornada. Ninguna ruta
recibe tratamiento especial.

## Informe (LaTeX)

El informe de la Entrega 1 está en `docs/informe/` (`main.tex` + `secciones/`).

```bash
cd docs/informe
latexmk -pdf main.tex          # o pdflatex main.tex dos veces
```

Las tablas de resultados (`tablas/`) y las figuras (`figuras/`) se regeneran con
`python experiments/export_latex.py`. Las capturas de pantalla se guardan en
`docs/informe/capturas/` con los nombres listados en `capturas/LEEME.txt`; si un archivo no
existe, el PDF muestra un recuadro reservado con el nombre esperado.
