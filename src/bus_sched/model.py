"""Entidades del problema: trabajos (vueltas), buses (máquinas), instancia,
línea de tiempo por bus y programa (schedule)."""

from __future__ import annotations

import bisect
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .timeutil import hhmm_to_min, min_to_hhmm
from .traffic import DAY_END, DAY_START

LUNCH_MINUTES = 120.0
# Almuerzo escalonado en 3 turnos; cada turno es una VENTANA de inicio de
# ±30 min alrededor de 11:00, 12:30 y 14:00 (el bus k usa el turno k mod 3).
LUNCH_TURNS = (("10:30", "11:30"), ("12:00", "13:00"), ("13:30", "14:30"))
EPS = 1e-6


@dataclass(frozen=True)
class Job:
    """Una vuelta completa origen -> destino -> origen."""
    id: str
    route: str
    base: float        # duración base en minutos (tabla 2020)
    r: float           # inicio mínimo (min desde 00:00)
    d: float           # inicio máximo
    nominal: float     # inicio nominal (centro de la ventana antes de recortes)


@dataclass(frozen=True)
class Bus:
    """Máquina. El almuerzo es un bloque de `lunch_dur` minutos que debe
    iniciar dentro de [lunch_r, lunch_d] (si lunch_r == lunch_d es fijo)."""
    id: str
    route: str
    lunch_r: float
    lunch_d: float
    lunch_dur: float = LUNCH_MINUTES


@dataclass
class Instance:
    route: str
    company: str
    jobs: list[Job]
    buses: list[Bus]
    day_start: float = DAY_START
    day_end: float = DAY_END
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.jobs)

    @property
    def m(self) -> int:
        return len(self.buses)

    def job(self, job_id: str) -> Job:
        return self._index()[job_id]

    def _index(self) -> dict[str, Job]:
        if not hasattr(self, "_idx"):
            self._idx = {j.id: j for j in self.jobs}  # type: ignore[attr-defined]
        return self._idx  # type: ignore[attr-defined]

    # ---------------------------------------------------------------- JSON
    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "company": self.company,
            "day_start": min_to_hhmm(self.day_start),
            "day_end": min_to_hhmm(self.day_end),
            "meta": self.meta,
            "buses": [
                {"id": b.id, "lunch_r": min_to_hhmm(b.lunch_r),
                 "lunch_d": min_to_hhmm(b.lunch_d), "lunch_min": b.lunch_dur}
                for b in self.buses
            ],
            "jobs": [
                {"id": j.id, "base_min": round(j.base, 4), "r": min_to_hhmm(j.r),
                 "d": min_to_hhmm(j.d), "nominal": min_to_hhmm(j.nominal)}
                for j in self.jobs
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Instance":
        route = d["route"]
        return cls(
            route=route,
            company=d.get("company", ""),
            day_start=hhmm_to_min(d.get("day_start", "06:00")),
            day_end=hhmm_to_min(d.get("day_end", "22:00")),
            meta=d.get("meta", {}),
            buses=[Bus(b["id"], route, hhmm_to_min(b["lunch_r"]), hhmm_to_min(b["lunch_d"]),
                       float(b.get("lunch_min", LUNCH_MINUTES))) for b in d["buses"]],
            jobs=[Job(j["id"], route, float(j["base_min"]), hhmm_to_min(j["r"]),
                      hhmm_to_min(j["d"]), hhmm_to_min(j.get("nominal", j["r"])))
                  for j in d["jobs"]],
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1, ensure_ascii=False),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Instance":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def make_buses(route: str, m: int, turns=LUNCH_TURNS, lunch=LUNCH_MINUTES) -> list[Bus]:
    """Crea m buses; el bus k almuerza en el turno k mod len(turns).
    Cada turno es (inicio_min, inicio_max) o una sola hora (almuerzo fijo)."""
    out = []
    for k in range(m):
        t = turns[k % len(turns)]
        lr, ld = (t, t) if isinstance(t, str) else t
        out.append(Bus(f"{route}-B{k + 1}", route, hhmm_to_min(lr), hhmm_to_min(ld), lunch))
    return out


# ====================================================================== #
@dataclass
class Assignment:
    job_id: str
    bus_id: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


class BusTimeline:
    """Intervalos ocupados de un bus, ordenados por inicio (listas + bisect).

    El almuerzo NO se fija al inicio: es un bloque de duración fija con
    ventana de inicio [lunch_r, lunch_d]. Toda inserción debe dejar al menos
    un hueco donde el almuerzo todavía quepa (invariante de factibilidad).
    finalize_lunch() lo ubica al final en el inicio factible más temprano.

    find_slot recorre los huecos en orden; por la propiedad FIFO del modelo
    de tráfico, dentro de un hueco el inicio más temprano también es el que
    termina antes.
    """

    __slots__ = ("bus", "starts", "ends", "tags", "load", "day_start", "day_end", "lunch")

    def __init__(self, bus: Bus, day_start: float, day_end: float):
        self.bus = bus
        self.day_start = day_start
        self.day_end = day_end
        self.starts: list[float] = []
        self.ends: list[float] = []
        self.tags: list[str] = []
        self.load = 0.0          # minutos de conducción asignados
        self.lunch: tuple[float, float] | None = None

    @staticmethod
    def _gaps(starts, ends, lo, hi):
        prev = lo
        for s, e in zip(starts, ends):
            if s > prev:
                yield prev, s
            prev = max(prev, e)
        if hi > prev:
            yield prev, hi

    def gaps(self):
        return self._gaps(self.starts, self.ends, self.day_start, self.day_end)

    def _lunch_fits(self, extra: tuple[float, float] | None = None):
        """Inicio más temprano del almuerzo si cabe (con el intervalo extra
        hipotético), o None."""
        b = self.bus
        if extra is None:
            starts, ends = self.starts, self.ends
        else:
            i = bisect.bisect_left(self.starts, extra[0])
            starts = self.starts[:i] + [extra[0]] + self.starts[i:]
            ends = self.ends[:i] + [extra[1]] + self.ends[i:]
        for g0, g1 in self._gaps(starts, ends, self.day_start, self.day_end):
            ls = max(g0, b.lunch_r)
            if ls > b.lunch_d + EPS:
                return None
            if ls + b.lunch_dur <= g1 + EPS:
                return ls
        return None

    def find_slot(self, job: Job, duration: Callable[[float], float]):
        """Devuelve (inicio, fin) con el inicio factible más temprano, o None.

        En cada hueco se prueban dos candidatos: salir lo antes posible, o
        salir justo después de ubicar el almuerzo en ese mismo hueco. Un
        candidato se acepta sólo si respeta ventana y jornada y si el almuerzo
        todavía cabe (invariante de factibilidad).
        """
        b = self.bus
        for g0, g1 in self.gaps():
            s0 = max(job.r, g0)
            if s0 > job.d + EPS:
                return None                 # los huecos siguientes son más tardíos
            cands = [s0]
            ls = max(g0, b.lunch_r)
            if ls <= b.lunch_d + EPS:
                cands.append(max(s0, ls + b.lunch_dur))
            for s in cands:
                if s > job.d + EPS:
                    break
                e = s + duration(s)
                if e > g1 + EPS:
                    break                   # FIFO: más tarde tampoco cabe
                if self._lunch_fits((s, e)) is not None:
                    return s, e
        return None

    def insert(self, start: float, end: float, tag: str) -> None:
        i = bisect.bisect_left(self.starts, start)
        self.starts.insert(i, start)
        self.ends.insert(i, end)
        self.tags.insert(i, tag)
        self.load += end - start

    def remove(self, tag: str) -> None:
        i = self.tags.index(tag)
        self.load -= self.ends[i] - self.starts[i]
        del self.starts[i], self.ends[i], self.tags[i]

    def finalize_lunch(self) -> tuple[float, float]:
        ls = self._lunch_fits()
        if ls is None:                      # no debería ocurrir (invariante)
            raise RuntimeError(f"Almuerzo infactible en {self.bus.id}")
        self.lunch = (ls, ls + self.bus.lunch_dur)
        return self.lunch


@dataclass
class Schedule:
    instance: Instance
    algorithm: str
    traffic: str
    assignments: dict[str, Assignment] = field(default_factory=dict)
    unassigned: list[str] = field(default_factory=list)
    runtime_s: float = 0.0
    extra: dict = field(default_factory=dict)
    lunches: dict[str, tuple[float, float]] = field(default_factory=dict)

    def bus_loads(self) -> dict[str, float]:
        loads = {b.id: 0.0 for b in self.instance.buses}
        for a in self.assignments.values():
            loads[a.bus_id] += a.duration
        return loads

    def by_bus(self) -> dict[str, list[Assignment]]:
        out: dict[str, list[Assignment]] = {b.id: [] for b in self.instance.buses}
        for a in self.assignments.values():
            out[a.bus_id].append(a)
        for v in out.values():
            v.sort(key=lambda a: a.start)
        return out

    def to_rows(self) -> list[dict]:
        rows = []
        for a in sorted(self.assignments.values(), key=lambda a: (a.bus_id, a.start)):
            j = self.instance.job(a.job_id)
            rows.append({
                "ruta": self.instance.route, "trabajo": a.job_id, "bus": a.bus_id,
                "ventana_min": min_to_hhmm(j.r), "ventana_max": min_to_hhmm(j.d),
                "inicio": min_to_hhmm(a.start), "fin": min_to_hhmm(a.end),
                "inicio_min": round(a.start, 3), "fin_min": round(a.end, 3),
                "duracion_min": round(a.duration, 3), "duracion_base_min": round(j.base, 3),
            })
        for jid in self.unassigned:
            j = self.instance.job(jid)
            rows.append({"ruta": self.instance.route, "trabajo": jid, "bus": "NO_ASIGNADO",
                         "ventana_min": min_to_hhmm(j.r), "ventana_max": min_to_hhmm(j.d),
                         "inicio": "", "fin": "", "inicio_min": None, "fin_min": None,
                         "duracion_min": None, "duracion_base_min": round(j.base, 3)})
        return rows
