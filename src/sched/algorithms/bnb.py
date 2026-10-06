"""Ramificación y poda (Branch and Bound) para instancias pequeñas.

NOTA: mecanismo de referencia previsto para etapas posteriores del proyecto.
No forma parte de los algoritmos evaluados en la Entrega 1 (List Scheduling y
LPT); se conserva como prototipo para validar instancias pequeñas.

Espacio de búsqueda: asignaciones trabajo -> bus. Los trabajos se ramifican
en orden cronológico de ventana (r_j) y en cada bus se programan con el
inicio factible más temprano. Por tanto, el B&B es EXACTO dentro del espacio
de programas "cronológicos de inicio más temprano" (el mismo espacio que
explora LS). El modelo CP-SAT (cpsat.py) es exacto sobre el modelo completo
(cualquier inicio entero dentro de la ventana) y sirve de verificación
cruzada.

Poda:
  * cota inferior  LB = max(L_max actual,
                            (carga total actual + sum_{j pendiente} pmin_j) / m)
    con pmin_j = menor duración posible de j dentro de su ventana;
  * cota superior inicial = mejor entre LS y LPT;
  * prioridad a minimizar trabajos NO asignados (objetivo lexicográfico:
    primero factibilidad, luego L_max);
  * simetría: buses vacíos con el mismo turno de almuerzo son
    intercambiables -> sólo se prueba el primero.
"""

from __future__ import annotations

import time

from ..model import Assignment, BusTimeline, Instance, Schedule
from ..traffic import TrafficProfile
from .greedy import duration_fn, list_scheduling, lpt


def _value(sch: Schedule) -> tuple[int, float]:
    loads = sch.bus_loads().values()
    return len(sch.unassigned), max(loads) if loads else 0.0


def branch_and_bound(inst: Instance, profile: TrafficProfile, max_jobs: int = 14,
                     time_limit_s: float = 60.0) -> Schedule:
    if inst.n > max_jobs:
        raise ValueError(f"B&B limitado a {max_jobs} trabajos (instancia: {inst.n})")
    t0 = time.perf_counter()
    jobs = sorted(inst.jobs, key=lambda j: (j.r, j.nominal, j.id))
    durs = [duration_fn(profile, j.base) for j in jobs]
    pmin = [profile.min_travel_time(j.base, j.r, j.d) for j in jobs]
    suffix = [0.0] * (len(jobs) + 1)
    for k in range(len(jobs) - 1, -1, -1):
        suffix[k] = suffix[k + 1] + pmin[k]

    # cota superior inicial
    incumbent = min((list_scheduling(inst, profile), lpt(inst, profile)), key=_value)
    best_val = _value(incumbent)
    best_plan: list[tuple[int, float, float] | None] | None = None

    m = inst.m
    tls = [BusTimeline(b, inst.day_start, inst.day_end) for b in inst.buses]
    plan: list[tuple[int, float, float] | None] = []
    stats = {"nodos": 0, "podas": 0, "timeout": False}

    def rec(k: int, unassigned: int, total: float) -> None:
        nonlocal best_val, best_plan
        stats["nodos"] += 1
        if time.perf_counter() - t0 > time_limit_s:
            stats["timeout"] = True
            return
        lmax = max(tl.load for tl in tls)
        lb = max(lmax, (total + suffix[k]) / m)
        if (unassigned, lb) >= (best_val[0], best_val[1] - 1e-9):
            stats["podas"] += 1
            return
        if k == len(jobs):
            best_val = (unassigned, lmax)
            best_plan = list(plan)
            return
        job = jobs[k]
        seen_empty_turns = set()
        options = []
        for i, tl in enumerate(tls):
            if not tl.starts:                                 # bus vacío
                key = (tl.bus.lunch_r, tl.bus.lunch_d)
                if key in seen_empty_turns:
                    continue
                seen_empty_turns.add(key)
            slot = tl.find_slot(job, durs[k])
            if slot is not None:
                options.append((tl.load, i, slot))
        options.sort()                                       # menor carga primero
        for _, i, (s, e) in options:
            tl = tls[i]
            tl.insert(s, e, job.id)
            plan.append((i, s, e))
            rec(k + 1, unassigned, total + (e - s))
            plan.pop()
            tl.remove(job.id)
        # rama "no asignar" (sólo si puede mejorar en factibilidad)
        if unassigned + 1 <= best_val[0]:
            plan.append(None)
            rec(k + 1, unassigned + 1, total)
            plan.pop()

    rec(0, 0, 0.0)

    sch = Schedule(inst, "BnB", profile.name)
    if best_plan is None:            # el incumbente ya era óptimo
        sch.assignments = dict(incumbent.assignments)
        sch.unassigned = list(incumbent.unassigned)
        sch.lunches = dict(incumbent.lunches)
        stats["optimo_es_heuristica"] = incumbent.algorithm
    else:
        for job, p in zip(jobs, best_plan):
            if p is None:
                sch.unassigned.append(job.id)
            else:
                i, s, e = p
                sch.assignments[job.id] = Assignment(job.id, inst.buses[i].id, s, e)
        final = [BusTimeline(bus, inst.day_start, inst.day_end) for bus in inst.buses]
        for a in sch.assignments.values():
            final[[x.id for x in inst.buses].index(a.bus_id)].insert(a.start, a.end, a.job_id)
        for tl in final:
            sch.lunches[tl.bus.id] = tl.finalize_lunch()
    sch.runtime_s = time.perf_counter() - t0
    sch.extra = stats
    return sch
