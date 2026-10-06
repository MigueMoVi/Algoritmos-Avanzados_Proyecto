"""Heurísticas de lista: List Scheduling (LS) y Longest Processing Time (LPT)
adaptadas a ventanas de inicio, almuerzo y tráfico dependiente de la hora.

Esquema común (greedy_schedule):
    para cada vuelta j en el ORDEN de la estrategia:
        para cada bus i de la ruta:
            buscar el inicio factible más temprano en la línea de tiempo de i
        elegir el bus factible de menor carga acumulada
            (empate: inicio más temprano, luego índice de bus)
        insertar j; si ningún bus es factible -> j queda NO ASIGNADA

LS  : orden por inicio mínimo de ventana r_j.
LPT : orden por duración con tráfico, evaluada en la salida nominal, de mayor
      a menor.
"""

from __future__ import annotations

import time
from typing import Callable

from ..model import Assignment, BusTimeline, Instance, Job, Schedule
from ..traffic import TrafficProfile


def duration_fn(profile: TrafficProfile, base: float) -> Callable[[float], float]:
    """p_j(s): duración de la vuelta según su hora de salida s."""
    return lambda s: profile.travel_time(s, base)


def greedy_schedule(inst: Instance, order: list[Job], profile: TrafficProfile,
                    name: str) -> Schedule:
    t0 = time.perf_counter()
    timelines = [BusTimeline(b, inst.day_start, inst.day_end) for b in inst.buses]
    sch = Schedule(inst, name, profile.name)
    for job in order:
        dur = duration_fn(profile, job.base)
        best = None
        for idx, tl in enumerate(timelines):
            slot = tl.find_slot(job, dur)
            if slot is None:
                continue
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


def list_scheduling(inst: Instance, profile: TrafficProfile) -> Schedule:
    order = sorted(inst.jobs, key=lambda j: (j.r, j.nominal, j.id))
    return greedy_schedule(inst, order, profile, "LS")


def lpt(inst: Instance, profile: TrafficProfile) -> Schedule:
    t0 = time.perf_counter()
    key = {j.id: profile.travel_time(j.nominal, j.base) for j in inst.jobs}
    order = sorted(inst.jobs, key=lambda j: (-round(key[j.id], 9), j.r, j.id))
    sch = greedy_schedule(inst, order, profile, "LPT")
    sch.runtime_s = time.perf_counter() - t0          # incluye el ordenamiento
    return sch
