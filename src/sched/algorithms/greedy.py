"""Heurísticas de lista: List Scheduling (LS) y Longest Processing Time (LPT)
adaptadas a ventanas de inicio, almuerzo y tráfico dependiente del tiempo.

Esquema común (greedy_schedule):
    para cada trabajo j en el ORDEN de la estrategia:
        para cada bus i de la ruta:
            buscar el hueco factible más temprano en la línea de tiempo de i
        elegir el bus factible de menor carga acumulada
            (empate: inicio más temprano, luego índice de bus)
        insertar j; si ningún bus es factible -> j queda NO ASIGNADO

LS  : orden por inicio mínimo de ventana r_j (orden de llegada del servicio).
LPT : orden por duración esperada decreciente, evaluada en el inicio nominal
      (con tráfico, las vueltas de hora punta son las "más largas").
"""

from __future__ import annotations

import time
from typing import Callable

from ..model import Assignment, BusTimeline, Instance, Job, Schedule
from ..traffic import TrafficProfile


def duration_fn(profile: TrafficProfile, base: float, buffer: float = 0.0) -> Callable[[float], float]:
    """Duración planificada = tiempo de viaje con tráfico * (1 + holgura)."""
    k = 1.0 + buffer
    return lambda s: profile.travel_time(s, base) * k


def _idle_before(tl: BusTimeline, start: float) -> float:
    """Tiempo muerto que queda en el bus justo antes de `start`."""
    prev = tl.day_start
    for e in tl.ends:
        if e <= start + 1e-9:
            prev = max(prev, e)
    if tl.lunch is None:
        b = tl.bus
        if b.lunch_d + b.lunch_dur <= start:      # el almuerzo cabe antes
            prev = max(prev, min(start, b.lunch_d + b.lunch_dur))
    return start - prev


def greedy_schedule(inst: Instance, order: list[Job], profile: TrafficProfile,
                    name: str, policy: str = "earliest", buffer: float = 0.0,
                    rule: str = "min_load") -> Schedule:
    """rule = "min_load": bus factible de menor carga (equilibrio, P||Cmax).
    rule = "best_fit": bus factible que deja menos tiempo muerto antes de la
                       vuelta (compacta las líneas de tiempo; favorece la
                       factibilidad). Empates -> menor carga."""
    t0 = time.perf_counter()
    timelines = [BusTimeline(b, inst.day_start, inst.day_end) for b in inst.buses]
    sch = Schedule(inst, name, profile.name, policy, buffer)
    for job in order:
        dur = duration_fn(profile, job.base, buffer)
        best = None
        for idx, tl in enumerate(timelines):
            slot = tl.find_slot(job, dur, policy)
            if slot is None:
                continue
            if rule == "best_fit":
                key = (round(_idle_before(tl, slot[0]), 9), round(tl.load, 9), slot[0], idx)
            else:
                key = (round(tl.load, 9), slot[0], idx)
            if best is None or key < best[0]:
                best = (key, tl, slot)
        if best is None:
            sch.unassigned.append(job.id)
            continue
        _, tl, (s, e) = best
        tl.insert(s, e, job.id)
        sch.assignments[job.id] = Assignment(job.id, tl.bus.id, s, e)
    for tl in timelines:
        sch.lunches[tl.bus.id] = tl.finalize_lunch()
    sch.runtime_s = time.perf_counter() - t0
    return sch


def list_scheduling(inst: Instance, profile: TrafficProfile, policy: str = "earliest",
                    buffer: float = 0.0, rule: str = "min_load") -> Schedule:
    order = sorted(inst.jobs, key=lambda j: (j.r, j.nominal, j.id))
    return greedy_schedule(inst, order, profile, "LS" if rule == "min_load" else "LS-BF",
                           policy, buffer, rule)


def lpt(inst: Instance, profile: TrafficProfile, policy: str = "earliest",
        buffer: float = 0.0) -> Schedule:
    t0 = time.perf_counter()
    key = {j.id: profile.travel_time(j.nominal, j.base) for j in inst.jobs}
    order = sorted(inst.jobs, key=lambda j: (-round(key[j.id], 9), j.r, j.id))
    sch = greedy_schedule(inst, order, profile, "LPT", policy, buffer)
    sch.runtime_s = time.perf_counter() - t0          # incluye el ordenamiento
    return sch
