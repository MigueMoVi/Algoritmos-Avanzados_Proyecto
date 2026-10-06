"""Modelo de tráfico.

Capa A (determinística): la ruta se recorre con una velocidad constante por
franja horaria (modelo de Ichoua, Gendreau y Potvin, 2003). Cada franja tiene
un *factor de congestión* f >= 0 que multiplica el tiempo de viaje: dentro de
la franja, un minuto real avanza 1/f minutos de "recorrido base".

    travel_time(s, p) = tiempo real para completar p minutos de recorrido base
                        saliendo en el instante s.

Como la velocidad es constante por tramos y positiva, el modelo cumple la
propiedad FIFO: si s1 <= s2 entonces s1 + tt(s1) <= s2 + tt(s2).

Capa B (estocástica): la duración realizada es tt(s, p) * eps, con
eps ~ LogNormal(-sigma^2/2, sigma) (media 1). Se usa sólo en simulation.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .timeutil import hhmm_to_min, min_to_hhmm

DAY_START = 360.0   # 06:00
DAY_END = 1320.0    # 22:00

# Perfil de congestión propuesto (factores "pesimistas" = escenario T2).
# Supuesto experimental documentado: no proviene de mediciones de Cusco.
RAW_BANDS: list[tuple[str, str, float, str]] = [
    ("06:00", "06:30", 0.90, "Valle temprano"),
    ("06:30", "09:00", 1.30, "Punta mañana"),
    ("09:00", "12:00", 1.00, "Valle"),
    ("12:00", "14:30", 1.20, "Punta mediodía (salida escolar)"),
    ("14:30", "17:00", 1.00, "Valle"),
    ("17:00", "20:00", 1.35, "Punta tarde"),
    ("20:00", "22:00", 0.90, "Valle nocturno"),
]


@dataclass
class Band:
    start: float
    end: float
    factor: float
    label: str = ""


@dataclass
class TrafficProfile:
    name: str
    bands: list[Band]
    outside_factor: float = 1.0          # factor fuera de las franjas definidas
    description: str = ""
    _starts: list[float] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.bands = sorted(self.bands, key=lambda b: b.start)
        for a, b in zip(self.bands, self.bands[1:]):
            if a.end > b.start + 1e-9:
                raise ValueError("Las franjas de tráfico se solapan")
        for b in self.bands:
            if b.factor <= 0:
                raise ValueError("El factor de congestión debe ser positivo")
        self._starts = [b.start for b in self.bands]

    # ------------------------------------------------------------------ #
    def factor_at(self, t: float) -> float:
        for b in self.bands:
            if b.start <= t < b.end:
                return b.factor
        return self.outside_factor

    def _segments_from(self, t: float):
        """Genera (fin_del_segmento, factor) a partir del instante t."""
        for b in self.bands:
            if b.end <= t:
                continue
            if t < b.start:               # hueco sin franja definida
                yield b.start, self.outside_factor
                t = b.start
            yield b.end, b.factor
            t = b.end
        yield float("inf"), self.outside_factor

    def travel_time(self, start: float, base: float) -> float:
        """Duración real de una vuelta con duración base `base` (min) que
        parte en `start` (min). Integra la velocidad franja por franja."""
        remaining = base
        t = start
        for seg_end, f in self._segments_from(start):
            capacity = (seg_end - t) / f          # minutos base que caben
            if capacity >= remaining:
                return t + remaining * f - start
            remaining -= capacity
            t = seg_end
        raise RuntimeError("inalcanzable")

    def min_travel_time(self, base: float, r: float, d: float, step: float = 1.0) -> float:
        """Menor duración posible saliendo en algún instante de [r, d]
        (búsqueda en rejilla de `step` minutos + extremos y bordes de franja)."""
        cands = {r, d}
        t = r
        while t <= d:
            cands.add(t)
            t += step
        for b in self.bands:
            for x in (b.start, b.end):
                if r <= x <= d:
                    cands.add(x)
        return min(self.travel_time(s, base) for s in cands)

    # ------------------------------------------------------------------ #
    def mean_factor(self, a: float = DAY_START, b: float = DAY_END) -> float:
        """Media ponderada por tiempo del factor en [a, b]."""
        total = 0.0
        for band in self.bands:
            lo, hi = max(a, band.start), min(b, band.end)
            if hi > lo:
                total += (hi - lo) * band.factor
        covered = sum(max(0.0, min(b, x.end) - max(a, x.start)) for x in self.bands)
        total += (b - a - covered) * self.outside_factor
        return total / (b - a)

    def normalized(self, name: str | None = None) -> "TrafficProfile":
        """Escala los factores para que su media en la jornada sea 1. Así la
        duración media coincide con el tiempo de vuelta de la tabla 2020."""
        m = self.mean_factor()
        return TrafficProfile(
            name=name or f"{self.name}-norm",
            bands=[Band(b.start, b.end, b.factor / m, b.label) for b in self.bands],
            outside_factor=self.outside_factor / m,
            description=f"{self.description} (normalizado, media=1; divisor={m:.4f})",
        )

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "outside_factor": self.outside_factor,
            "bands": [
                {"start": min_to_hhmm(b.start), "end": min_to_hhmm(b.end),
                 "factor": round(b.factor, 6), "label": b.label}
                for b in self.bands
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TrafficProfile":
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            outside_factor=d.get("outside_factor", 1.0),
            bands=[Band(hhmm_to_min(b["start"]), hhmm_to_min(b["end"]),
                        float(b["factor"]), b.get("label", "")) for b in d["bands"]],
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TrafficProfile":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _raw() -> TrafficProfile:
    return TrafficProfile(
        name="T2",
        bands=[Band(hhmm_to_min(a), hhmm_to_min(b), f, lab) for a, b, f, lab in RAW_BANDS],
        outside_factor=0.90,
        description="Perfil pesimista: factores de congestión sin normalizar",
    )


def get_profile(name: str) -> TrafficProfile:
    """T0 = sin tráfico, T1 = perfil normalizado (media 1), T2 = pesimista."""
    name = name.upper()
    if name == "T0":
        return TrafficProfile(name="T0", bands=[], outside_factor=1.0,
                              description="Sin tráfico: duración constante igual al tiempo base")
    if name == "T2":
        return _raw()
    if name == "T1":
        p = _raw().normalized(name="T1")
        p.description = "Perfil normalizado: media ponderada del factor = 1 en 06:00–22:00"
        return p
    path = Path(name)
    if path.exists():
        return TrafficProfile.load(path)
    raise ValueError(f"Perfil de tráfico desconocido: {name}")


PROFILES = ("T0", "T1", "T2")
