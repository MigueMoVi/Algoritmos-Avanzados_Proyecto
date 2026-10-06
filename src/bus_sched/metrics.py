"""Métricas de un programa."""

from __future__ import annotations

from .model import Schedule
from .traffic import TrafficProfile


def lower_bound(sch_or_inst, profile: TrafficProfile, job_ids=None) -> float:
    """Cota inferior de L_max: max( max_j pmin_j , sum_j pmin_j / m ),
    con pmin_j = menor duración de j dentro de su ventana. Si se da job_ids,
    la cota se calcula sólo para ese subconjunto (vueltas atendidas)."""
    inst = getattr(sch_or_inst, "instance", sch_or_inst)
    jobs = inst.jobs if job_ids is None else [inst.job(x) for x in job_ids]
    pmins = [profile.min_travel_time(j.base, j.r, j.d) for j in jobs]
    if not pmins:
        return 0.0
    return max(max(pmins), sum(pmins) / inst.m)


def compute_metrics(sch: Schedule, profile: TrafficProfile, lb: float | None = None) -> dict:
    inst = sch.instance
    loads = list(sch.bus_loads().values())
    lmax, lmin = max(loads), min(loads)
    total = sum(loads)
    lunch = inst.buses[0].lunch_dur if inst.buses else 120.0
    available = (inst.day_end - inst.day_start) - lunch          # 14 h netas
    # La cota se evalúa sobre las vueltas ATENDIDAS: si quedan vueltas sin
    # asignar, compararse contra la cota de todas daría brechas negativas.
    if sch.unassigned:
        lb = lower_bound(inst, profile, list(sch.assignments))
    elif lb is None:
        lb = lower_bound(inst, profile)
    base_total = sum(inst.job(a.job_id).base for a in sch.assignments.values())
    out = {
        "ruta": inst.route,
        "algoritmo": sch.algorithm,
        "trafico": sch.traffic,
        "buses": inst.m,
        "trabajos": inst.n,
        "asignados": len(sch.assignments),
        "no_asignados": len(sch.unassigned),
        "Lmax_h": lmax / 60,
        "Lmin_h": lmin / 60,
        "desbalance_h": (lmax - lmin) / 60,
        "carga_media_h": total / len(loads) / 60,
        "conduccion_total_h": total / 60,
        "sobrecosto_trafico_pct": 100 * (total - base_total) / base_total if base_total else 0.0,
        "utilizacion_media_pct": 100 * total / (len(loads) * available),
        "buses_sin_vueltas": sum(1 for x in loads if x == 0),
        "rho_saturacion": sum(j.base for j in inst.jobs) / (inst.m * available),
        "cota_inferior_h": lb / 60,
        "gap_vs_cota_pct": 100 * (lmax - lb) / lb if lb else 0.0,
        "tiempo_ejecucion_ms": sch.runtime_s * 1000,
    }
    return out
