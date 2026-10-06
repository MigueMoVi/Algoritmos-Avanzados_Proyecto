"""Capa B del tráfico: simulación Monte Carlo de la ejecución de un plan.

NOTA: evaluación de robustez prevista para etapas posteriores del proyecto.
No forma parte de los algoritmos evaluados en la Entrega 1 (List Scheduling y
LPT); se conserva como prototipo para validar instancias pequeñas.

Cada bus ejecuta sus vueltas en el orden planificado:
  inicio_real = max(inicio_planificado, fin_real_anterior)
  (un bus no sale antes de su hora programada; si llega tarde, sale tarde)
  duración_real = tt(inicio_real) * eps,  eps ~ LogNormal(-sigma^2/2, sigma)
El almuerzo también se corre si el bus llega tarde (dura siempre 120 min).

Métricas por réplica: % de vueltas que salen después de su inicio máximo
(violación de ventana), retraso medio de salida, retraso máximo, % de buses
que terminan después de las 22:00 (horas extra) y carga máxima realizada.
"""

from __future__ import annotations

import math
import random
import statistics

from .model import Schedule
from .traffic import TrafficProfile


def simulate(sch: Schedule, profile: TrafficProfile, sigma: float, reps: int = 200,
             seed: int = 2026) -> dict:
    inst = sch.instance
    rng = random.Random(seed)
    mu = -sigma * sigma / 2
    plans = []
    b_dur = inst.buses[0].lunch_dur if inst.buses else 120.0
    for b in inst.buses:
        items = [(a.start, "J", inst.job(a.job_id)) for a in sch.by_bus()[b.id]]
        items.append((sch.lunches[b.id][0], "L", None))
        items.sort(key=lambda x: x[0])
        plans.append(items)

    n_jobs = max(1, len(sch.assignments))
    late_pct, mean_delay, max_delay, overtime_pct, lmax_real = [], [], [], [], []
    for _ in range(reps):
        late = 0
        delays = []
        overtime = 0
        loads = []
        for items in plans:
            t = inst.day_start
            load = 0.0
            for planned, kind, job in items:
                start = max(planned, t)
                if kind == "L":
                    t = start + b_dur
                    continue
                delay = start - planned
                delays.append(delay)
                if start > job.d + 1e-6:
                    late += 1
                eps = math.exp(rng.gauss(mu, sigma)) if sigma > 0 else 1.0
                dur = profile.travel_time(start, job.base) * eps
                load += dur
                t = start + dur
            if t > inst.day_end + 1e-6:
                overtime += 1
            loads.append(load)
        late_pct.append(100 * late / n_jobs)
        mean_delay.append(statistics.fmean(delays) if delays else 0.0)
        max_delay.append(max(delays) if delays else 0.0)
        overtime_pct.append(100 * overtime / inst.m)
        lmax_real.append(max(loads) / 60)

    def summary(xs):
        xs = sorted(xs)
        return statistics.fmean(xs), xs[int(0.95 * (len(xs) - 1))]

    out = {"ruta": inst.route, "algoritmo": sch.algorithm, "trafico": sch.traffic,
           "sigma": sigma, "replicas": reps}
    for name, xs in (("vueltas_fuera_ventana_pct", late_pct), ("retraso_medio_min", mean_delay),
                     ("retraso_max_min", max_delay), ("buses_horas_extra_pct", overtime_pct),
                     ("Lmax_real_h", lmax_real)):
        m, p95 = summary(xs)
        out[name] = m
        out[name + "_p95"] = p95
    return out
