# Plan de aprendizaje autónomo — Grupo 4 (Entrega 1)

Evidencia para el indicador **AG-C06.01** (necesidades de aprendizaje y actividades independientes).
Cada integrante registra el avance real en su bitácora (`docs/bitacora/`), con fecha, fuente
consultada, lo que aprendió, cómo lo aplicó y el commit o archivo que lo demuestra.

## Responsable principal por componente (propuesta)

| Componente | Responsable | Apoyo |
|---|---|---|
| Arquitectura, modelo de tráfico, integración, CP-SAT | Aguilar Quispe, Yon | todos |
| List Scheduling, LPT, línea de tiempo por bus | Choque Mamani, Brayan Isau | Aguilar |
| Ramificación y poda, cotas inferiores, pruebas | Huacani de la Cruz, Dany | Choque |
| Datos/Excel, instancias, experimentos, simulación y gráficos | Moreano Villena, Miguel Angel | Huacani |

## Necesidades de aprendizaje y actividades

| # | Necesidad (brecha) | Integrante | Actividades independientes | Fuentes | Evidencia esperada | Semana |
|---|---|---|---|---|---|---|
| N1 | Modelos de tiempo de viaje dependientes del tiempo y propiedad FIFO | Aguilar | Leer Ichoua et al. (2003); reproducir a mano 3 casos; implementar `travel_time` y prueba FIFO | Ichoua, Gendreau y Potvin (2003); Gawiejnowicz (2008) | `traffic.py`, `test_traffic.py`, hoja *Calculadora vuelta* | S1 |
| N2 | Programación con restricciones (CP-SAT): intervalos opcionales, `NoOverlap`, `AddElement` | Aguilar | Tutorial oficial de OR-Tools; modelo de juguete de 3 trabajos; modelo completo | Documentación de OR-Tools | `cpsat.py`, comparación B&B vs CP-SAT (E2) | S1–S2 |
| N3 | Scheduling en máquinas paralelas idénticas, cotas de Graham | Choque | Leer Graham (1966, 1969) y Pinedo (cap. 5); demostrar la cota 2 − 1/m en una instancia | Graham; Pinedo (2016) | `greedy.py`, prueba `test_lpt_peor_caso_clasico_sin_ventanas` | S1 |
| N4 | Estructuras para huecos de tiempo (listas ordenadas, `bisect`, colas de prioridad) | Choque | Comparar lista+bisect vs árbol de intervalos; medir costo de inserción | Cormen et al. (2022), documentación de `bisect`/`heapq` | `BusTimeline`, experimento E3 | S2 |
| N5 | Ramificación y poda: diseño de cotas y ruptura de simetrías | Huacani | Leer Land y Doig (1960) y apuntes del curso; implementar cota Σpmin/m y poda por buses equivalentes | Land y Doig (1960); material del curso | `bnb.py`, conteo de nodos/podas | S1–S2 |
| N6 | Diseño de pruebas (pytest): casos límite y adversos | Huacani | Guía de pytest; catálogo de casos límite del problema | Documentación de pytest | `tests/` (35 pruebas) | S1 |
| N7 | Manejo de datos y control de calidad con pandas/openpyxl | Moreano | Verificar la consistencia entre hojas y validar ventanas y duraciones | Documentación de pandas y openpyxl | `builder.py` (`check_instance`), Excel actualizado | S1 |
| N8 | Simulación Monte Carlo y medidas de robustez | Moreano | Leer Law (2015, caps. 4 y 9); replicaciones con semilla; percentil 95 | Law (2015) | `simulation.py`, experimento E4 | S2 |
| N9 | Visualización reproducible (matplotlib) y paleta accesible | Moreano | Diseñar Gantt y gráficos de escenarios; validar paleta | Documentación de matplotlib | `viz.py`, figuras en `results/` | S2 |

S1 = 6–12 oct 2026 · S2 = 13–26 oct 2026.
