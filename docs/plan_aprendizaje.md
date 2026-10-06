# Plan de aprendizaje autónomo — Grupo 4 (Entrega 1)

Evidencia para el indicador **AG-C06.01**. Cada integrante registra sus actividades reales en su
bitácora (`docs/bitacora/`): fecha, fuente consultada, lo aprendido, dónde se aplicó (archivo o
commit) y la dificultad resuelta.

| # | Conocimiento requerido | Responsable | Para qué se usa | Cómo se adquiere y verifica | Evidencia |
|---|---|---|---|---|---|
| N1 | Tiempo de viaje por franjas y propiedad FIFO | Aguilar | Modelo de tráfico p_j(s) | Ichoua, Gendreau y Potvin (2003); cálculo manual; prueba automática FIFO; hoja *Calculadora vuelta* | `traffic.py`, `tests/test_traffic.py` |
| N2 | Scheduling en máquinas paralelas idénticas; garantías de LS y LPT | Choque | Diseño de LS y LPT | Graham (1966, 1969); Pinedo (2016); peor caso de LPT reproducido en una prueba | `algorithms/greedy.py`, `tests/test_ls_lpt.py` |
| N3 | Listas ordenadas con búsqueda binaria (`bisect`) | Choque | Línea de tiempo de cada bus | Documentación de Python; Cormen et al. (2022) | `model.py` (`BusTimeline`) |
| N4 | Diseño de pruebas con pytest (básicas, límite, adversas) | Huacani | Plan de pruebas | Documentación de pytest | `tests/` |
| N5 | Validación de restricciones | Huacani | Verificador independiente | Formulación del modelo; pruebas de soluciones corrompidas | `validator.py` |
| N6 | Lectura y validación de datos con openpyxl/pandas | Moreano | Instancias y Excel | Documentación oficial; regla general de vueltas verificada contra la hoja | `builder.py`, `experiments/build_excel.py` |
| N7 | Visualización reproducible con matplotlib | Moreano | Gantt y gráficos de resultados | Documentación de matplotlib | `viz.py`, `results/fig_*.png` |
| N8 | Métodos exactos de referencia (Ramificación y Poda, CP-SAT) | Aguilar, Huacani | Referencia para instancias pequeñas en etapas posteriores | Land y Doig (1960); documentación de OR-Tools; prototipos iniciales | `algorithms/bnb.py`, `algorithms/cpsat.py` |
