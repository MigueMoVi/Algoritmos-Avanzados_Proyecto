# Asignación de vueltas a buses con ventanas y tráfico — Transporte urbano de Cusco

Proyecto semestral de **Algoritmos Avanzados** (UNSAAC, 2026-II) — **Grupo 4**.

**Tema:** Optimización de asignación de trabajos en máquinas idénticas.

**Docente:** Héctor Eduardo Ugarte Rojas.

| Integrante | Código |
|---|---|
| Aguilar Quispe, Yon | 111276 |
| Choque Mamani, Brayan Isau | 215719 |
| Huacani de la Cruz, Dany | 081561 |
| Moreano Villena, Miguel Angel | 211859 |

---

## Objetivo

Para cada empresa/ruta, se busca asignar cada **vuelta** (origen → destino → origen) a un **bus** de su propia flota, considerando los buses como máquinas idénticas.

Cada vuelta debe iniciar dentro de una **ventana temporal**, respetando:

- jornada de operación de 06:00 a 22:00;
- período de almuerzo de cada bus;
- ausencia de solapamientos entre vueltas;
- pertenencia del bus a la misma ruta;
- tiempo de viaje dependiente de la hora de salida debido al perfil de tráfico.

El objetivo se formula de manera lexicográfica:

1. **Maximizar el número de vueltas atendidas.**
2. **Minimizar la carga máxima de conducción por bus**, representada por \(L_{max}\).

### Entrega 1

En esta entrega se implementan y comparan:

- **List Scheduling (LS)**
- **LPT (Longest Processing Time)**

El repositorio incluye además prototipos de:

- Ramificación y Poda;
- CP-SAT;
- simulación de robustez.

Estos mecanismos se mantienen como referencia para etapas posteriores y **no forman parte de la evaluación principal de la Entrega 1**.

---

## Estructura del proyecto

```text
transporte-cusco-scheduling/
│
├── src/
│   └── bus_sched/
│       ├── traffic.py
│       │   Perfiles de tráfico T0/T1/T2 y cálculo del tiempo de viaje.
│       │
│       ├── model.py
│       │   Job, Bus, Instance, BusTimeline y Schedule.
│       │
│       ├── builder.py
│       │   Construcción de instancias a partir del Excel y validación
│       │   de los datos.
│       │
│       ├── algorithms/
│       │   ├── greedy.py
│       │   │   List Scheduling y LPT.
│       │   │
│       │   ├── bnb.py
│       │   │   Ramificación y Poda (referencia, etapa posterior).
│       │   │
│       │   └── cpsat.py
│       │       Modelo CP-SAT (referencia, etapa posterior).
│       │
│       ├── simulation.py
│       │   Simulación de robustez por Monte Carlo (etapa posterior).
│       │
│       ├── validator.py
│       │   Verificación independiente de las restricciones.
│       │
│       ├── metrics.py
│       │   Métricas de evaluación.
│       │
│       ├── viz.py
│       │   Generación de diagramas de Gantt y visualizaciones.
│       │
│       └── cli.py
│           Interfaz de línea de comandos.
│
├── tests/
│   Pruebas automatizadas con pytest.
│
├── experiments/
│   ├── run_experiments.py
│   │   Ejecución del experimento E1.
│   │
│   ├── build_excel.py
│   │   Generación del Excel de resultados.
│   │
│   ├── export_latex.py
│   │   Generación de tablas y figuras para el informe.
│   │
│   └── fig_arquitectura.py
│       Generación de la figura de arquitectura.
│
├── data/
│   ├── raw/
│   │   Excel base del proyecto.
│   │
│   ├── instances/
│   │   Instancias JSON generadas por el sistema.
│   │
│   └── traffic/
│       Perfiles de tráfico T0, T1 y T2.
│
├── results/
│   Resultados experimentales, CSV, figuras y Excel.
│
├── docs/
│   Informe, documentación, bitácoras y contribuciones.
│
├── pyproject.toml
├── requirements.txt
├── README.md
└── .gitignore

## 1. Objetivo

El proyecto modela la asignación de vueltas de buses a los buses de su propia ruta como un problema de asignación de trabajos en máquinas idénticas.

- **Máquina:** un bus de la flota de una ruta.
- **Trabajo:** una vuelta completa (origen → destino → origen).
- **Tiempo de procesamiento:** duración de la vuelta, dependiente de la hora de salida mediante un perfil de tráfico.
- **Ventana:** intervalo permitido para iniciar una vuelta.
- **Jornada:** 06:00–22:00.
- **Almuerzo:** período de 2 horas asociado a cada bus.
- **Objetivo lexicográfico:** primero maximizar las vueltas atendidas y después minimizar la carga máxima por bus, `L_max`.

La **Entrega 1** implementa y compara **List Scheduling (LS)** y **LPT (Longest Processing Time)**. Ramificación y Poda, CP-SAT y simulación de robustez se mantienen para etapas posteriores.

## 2. Requisitos

- Windows 10/11.
- PowerShell.
- Python 3.10 o superior.
- Git, si el proyecto se obtiene desde un repositorio.

Versión utilizada para validar esta entrega:

```text
Python 3.11.9
```

## 3. Instalación completa en Windows PowerShell

### 3.1 Entrar a la carpeta del proyecto

```powershell
cd "C:\ruta\al\proyecto\transporte-cusco-scheduling"
```

Comprobar:

```powershell
Get-Location
Get-ChildItem
```

La carpeta raíz debe contener, entre otros:

```text
data
docs
experiments
results
src
tests
pyproject.toml
requirements.txt
README.md
```

### 3.2 Comprobar Python

```powershell
python --version
```

### 3.3 Crear el entorno virtual

```powershell
python -m venv .venv
```

### 3.4 Activar el entorno virtual

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

La consola debe mostrar:

```text
(.venv) PS C:\...\transporte-cusco-scheduling>
```

### 3.5 Instalar dependencias

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## 4. Verificar la instalación

```powershell
python -c "import bus_sched; print(bus_sched.__file__)"
```

Debe mostrar una ruta similar a:

```text
...\transporte-cusco-scheduling\src\bus_sched\__init__.py
```

Comprobar la ayuda:

```powershell
python -m bus_sched -h
```

## 5. Generar las instancias

Ejecutar:

```powershell
python -m bus_sched build
```

Esto genera las instancias de las **35 rutas** y la instancia **DEMO**.

Las instancias quedan en:

```text
data\instances\
```

Los perfiles de tráfico quedan en:

```text
data\traffic\
```

Comprobar la cantidad:

```powershell
(Get-ChildItem data\instances -Filter *.json).Count
```

Resultado esperado:

```text
36
```

Es decir:

```text
35 rutas + DEMO
```

Para listar las instancias:

```powershell
Get-ChildItem data\instances -Filter *.json | Select-Object -ExpandProperty BaseName
```

## 6. Consultar los perfiles de tráfico

```powershell
python -m bus_sched profiles
```

Se utilizan:

- **T0:** escenario base.
- **T1:** escenario de tráfico normal.
- **T2:** escenario de tráfico elevado.

Los factores son supuestos experimentales del proyecto y no mediciones oficiales de tráfico.

## 7. Ejecutar la instancia manual

```powershell
python -m bus_sched demo
```

La DEMO permite comprobar LS y LPT sobre un caso pequeño de:

```text
3 buses
8 vueltas
```

**Importante:** la versión actual de `demo` no acepta `--traffic`. Por tanto, el comando correcto es:

```powershell
python -m bus_sched demo
```

No utilizar:

```powershell
python -m bus_sched demo --traffic T2
```

Los perfiles T0/T1/T2 se seleccionan mediante `run`.

## 8. Ejecutar List Scheduling (LS)

### T0

```powershell
python -m bus_sched run --route RTI-01 --alg ls --traffic T0
```

### T1

```powershell
python -m bus_sched run --route RTI-01 --alg ls --traffic T1
```

### T2

```powershell
python -m bus_sched run --route RTI-01 --alg ls --traffic T2
```

Para generar un Gantt:

```powershell
python -m bus_sched run --route RTI-01 --alg ls --traffic T1 --gantt
```

## 9. Ejecutar LPT

### T0

```powershell
python -m bus_sched run --route RTI-01 --alg lpt --traffic T0
```

### T1

```powershell
python -m bus_sched run --route RTI-01 --alg lpt --traffic T1
```

### T2

```powershell
python -m bus_sched run --route RTI-01 --alg lpt --traffic T2
```

Para generar un Gantt:

```powershell
python -m bus_sched run --route RTI-01 --alg lpt --traffic T1 --gantt
```

## 10. Ejecutar las seis combinaciones sobre RTI-01

```powershell
python -m bus_sched run --route RTI-01 --alg ls --traffic T0
python -m bus_sched run --route RTI-01 --alg ls --traffic T1
python -m bus_sched run --route RTI-01 --alg ls --traffic T2

python -m bus_sched run --route RTI-01 --alg lpt --traffic T0
python -m bus_sched run --route RTI-01 --alg lpt --traffic T1
python -m bus_sched run --route RTI-01 --alg lpt --traffic T2
```

Los resultados individuales se guardan en:

```text
results\
```

Por ejemplo:

```text
results\RTI-01_LS_T1.csv
results\RTI-01_LPT_T1.csv
```

Con `--gantt` también se genera el PNG correspondiente.

Cada ejecución muestra métricas y valida las restricciones. Una solución válida muestra:

```text
VALIDACIÓN: OK (0 violaciones)
```

## 11. Ejecutar el experimento completo de la Entrega 1

Ejecutar:

```powershell
python experiments\run_experiments.py
```

El experimento procesa:

```text
35 rutas × 2 algoritmos × 3 perfiles de tráfico = 210 ejecuciones
```

Los algoritmos son:

```text
LS
LPT
```

Los perfiles son:

```text
T0
T1
T2
```

Los resultados principales son:

```text
results\E1_35_rutas.csv
results\E1_resumen.csv
```

## 12. Consultar el resumen

```powershell
Import-Csv results\E1_resumen.csv | Format-Table -AutoSize
```

El resumen contiene:

- tráfico;
- algoritmo;
- rutas;
- vueltas;
- vueltas no asignadas;
- rutas completas;
- carga máxima media;
- gap medio;
- desbalance medio;
- sobrecosto por tráfico.

Comprobar los archivos:

```powershell
Get-ChildItem results -Filter "E1*"
```

## 13. Generar el Excel

Después del experimento:

```powershell
python experiments\build_excel.py
```

Se genera:

```text
results\Tabla_35_Rutas_Entrega1.xlsx
```

Comprobar:

```powershell
Get-ChildItem results -Filter "*.xlsx"
```

## 14. Ejecutar las pruebas

```powershell
python -m pytest -q
```

Resultado validado para la Entrega 1:

```text
35 passed, 1 skipped
```

Esto significa:

```text
35 pruebas aprobadas
1 prueba omitida
0 pruebas fallidas
```

## 15. Generar el informe

El informe se encuentra en:

```text
docs\informe\
```

Entrar:

```powershell
cd docs\informe
```

Con `latexmk`:

```powershell
latexmk -pdf main.tex
```

Alternativamente:

```powershell
pdflatex main.tex
pdflatex main.tex
```

## 16. Secuencia completa desde cero

Después de abrir PowerShell en la carpeta raíz, ejecutar en este orden:

### Instalación

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### Verificación

```powershell
python -c "import bus_sched; print(bus_sched.__file__)"
python -m bus_sched -h
```

### Generar instancias

```powershell
python -m bus_sched build
```

### Comprobar instancias

```powershell
(Get-ChildItem data\instances -Filter *.json).Count
```

Resultado esperado:

```text
36
```

### Consultar tráfico

```powershell
python -m bus_sched profiles
```

### Ejecutar DEMO

```powershell
python -m bus_sched demo
```

### Probar LS

```powershell
python -m bus_sched run --route RTI-01 --alg ls --traffic T1 --gantt
```

### Probar LPT

```powershell
python -m bus_sched run --route RTI-01 --alg lpt --traffic T1 --gantt
```

### Ejecutar las 35 rutas

```powershell
python experiments\run_experiments.py
```

### Consultar resultados

```powershell
Import-Csv results\E1_resumen.csv | Format-Table -AutoSize
```

### Generar Excel

```powershell
python experiments\build_excel.py
```

### Ejecutar pruebas

```powershell
python -m pytest -q
```

Resultado esperado:

```text
35 passed, 1 skipped
```

## 17. Archivos principales generados

Después de completar la ejecución, los archivos principales son:

```text
results\
├── E1_35_rutas.csv
├── E1_resumen.csv
└── Tabla_35_Rutas_Entrega1.xlsx
```

Además, las ejecuciones individuales generan sus respectivos CSV y los diagramas de Gantt cuando se utiliza `--gantt`.

## 18. Datos de la Entrega 1

La experimentación utiliza:

```text
35 rutas
4733 vueltas
2 algoritmos
3 perfiles de tráfico
210 ejecuciones
```

Los algoritmos comparados son:

```text
List Scheduling (LS)
LPT
```

Los escenarios son:

```text
T0
T1
T2
```

## 19. Alcance de la Entrega 1

Esta entrega comprende:

- formulación del problema;
- buses como máquinas idénticas;
- vueltas como trabajos;
- ventanas temporales;
- jornada 06:00–22:00;
- almuerzo de los buses;
- tiempos de viaje dependientes del tráfico;
- List Scheduling;
- LPT;
- instancia manual;
- validación de restricciones;
- experimento de 35 rutas;
- comparación T0/T1/T2;
- resultados CSV;
- Excel de resultados;
- pruebas automatizadas.

Ramificación y Poda, CP-SAT y simulación de robustez se mantienen para etapas posteriores.

## 20. Comprobación final

Antes de presentar la Entrega 1, ejecutar:

```powershell
python -m bus_sched -h
python -m bus_sched profiles
python -m bus_sched build
python -m bus_sched demo
python experiments\run_experiments.py
python experiments\build_excel.py
python -m pytest -q
```

Debe verificarse que:

```text
36 instancias = 35 rutas + DEMO
35 rutas
4733 vueltas
210 ejecuciones experimentales
35 passed, 1 skipped
```

Los archivos finales principales deben estar en:

```text
results\E1_35_rutas.csv
results\E1_resumen.csv
results\Tabla_35_Rutas_Entrega1.xlsx
```

Con estos pasos se puede instalar, ejecutar, probar y reproducir la **Entrega 1 del proyecto del Grupo 4**.
"""
