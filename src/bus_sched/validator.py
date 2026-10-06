"""Validador independiente de los algoritmos.

Recalcula todo a partir de la instancia y del perfil de tráfico; no usa las
líneas de tiempo internas de las heurísticas. Devuelve la lista de
violaciones (vacía = programa válido).
"""

from __future__ import annotations

from .model import Schedule
from .traffic import TrafficProfile

TOL = 1e-6


def validate(sch: Schedule, profile: TrafficProfile) -> list[str]:
    inst = sch.instance
    errors: list[str] = []
    bus_ids = {b.id: b for b in inst.buses}
    job_ids = {j.id for j in inst.jobs}

    # 1. cobertura: cada trabajo exactamente una vez (asignado o no asignado)
    seen = list(sch.assignments) + list(sch.unassigned)
    if sorted(seen) != sorted(job_ids):
        missing = job_ids - set(seen)
        dup = {x for x in seen if seen.count(x) > 1}
        extra = set(seen) - job_ids
        if missing:
            errors.append(f"Trabajos sin tratar: {sorted(missing)[:5]}")
        if dup:
            errors.append(f"Trabajos duplicados: {sorted(dup)[:5]}")
        if extra:
            errors.append(f"Trabajos desconocidos: {sorted(extra)[:5]}")

    for a in sch.assignments.values():
        if a.job_id not in job_ids:
            continue
        j = inst.job(a.job_id)
        # 2. ruta: el bus pertenece a la misma ruta del trabajo
        b = bus_ids.get(a.bus_id)
        if b is None or b.route != j.route:
            errors.append(f"{a.job_id}: bus {a.bus_id} no pertenece a la ruta {j.route}")
        # 3. ventana de inicio
        if a.start < j.r - TOL or a.start > j.d + TOL:
            errors.append(f"{a.job_id}: inicio {a.start:.1f} fuera de ventana [{j.r}, {j.d}]")
        # 4. jornada
        if a.start < inst.day_start - TOL or a.end > inst.day_end + TOL:
            errors.append(f"{a.job_id}: fuera de jornada ({a.start:.1f}–{a.end:.1f})")
        # 5. duración coherente con el modelo de tráfico
        expected = profile.travel_time(a.start, j.base)
        if abs(a.duration - expected) > 1e-3:
            errors.append(f"{a.job_id}: duración {a.duration:.3f} ≠ esperada {expected:.3f}")

    # 6. almuerzo: uno por bus, duración fija, inicio dentro de su ventana
    for b in inst.buses:
        if b.id not in sch.lunches:
            errors.append(f"{b.id}: sin almuerzo programado")
            continue
        ls, le = sch.lunches[b.id]
        if ls < b.lunch_r - TOL or ls > b.lunch_d + TOL:
            errors.append(f"{b.id}: almuerzo {ls:.1f} fuera de ventana [{b.lunch_r}, {b.lunch_d}]")
        if abs((le - ls) - b.lunch_dur) > TOL:
            errors.append(f"{b.id}: almuerzo de {le - ls:.1f} min (debe ser {b.lunch_dur})")

    # 7. no solapamiento por bus (incluido el almuerzo)
    for bus_id, items in sch.by_bus().items():
        lunch = sch.lunches.get(bus_id)
        ivs = [(a.start, a.end, a.job_id) for a in items]
        if lunch:
            ivs.append((lunch[0], lunch[1], "ALMUERZO"))
        ivs.sort()
        for (s1, e1, n1), (s2, e2, n2) in zip(ivs, ivs[1:]):
            if s2 < e1 - TOL:
                errors.append(f"{bus_id}: solapamiento {n1} ({s1:.1f}–{e1:.1f}) con {n2} ({s2:.1f}–{e2:.1f})")
    return errors
