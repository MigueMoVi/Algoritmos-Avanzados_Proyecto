"""Diagrama de Gantt por bus, con franjas de tráfico de fondo."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .model import Schedule  # noqa: E402
from .traffic import TrafficProfile  # noqa: E402

GUINDA = "#6E0F1D"
DORADO = "#C9A227"
GRIS = "#8C8C8C"


def gantt(sch: Schedule, profile: TrafficProfile, path: str | Path, title: str | None = None,
          max_buses: int = 40) -> None:
    inst = sch.instance
    buses = inst.buses[:max_buses]
    by_bus = sch.by_bus()
    h = max(2.2, (0.32 if len(buses) <= 6 else 0.17) * len(buses) + 1.2)
    fig, ax = plt.subplots(figsize=(11, h))
    # franjas de tráfico (más oscuro = más congestión)
    for b in profile.bands:
        if b.factor > 1.0 + 1e-9:
            ax.axvspan(b.start / 60, b.end / 60, color=DORADO,
                       alpha=min(0.35, 0.8 * (b.factor - 1.0)), lw=0)
    for y, bus in enumerate(buses):
        if bus.id in sch.lunches:
            ls, le = sch.lunches[bus.id]
            ax.barh(y, (le - ls) / 60, left=ls / 60, color="white", edgecolor=GRIS,
                    hatch="///", height=0.6)
        for a in by_bus[bus.id]:
            ax.barh(y, a.duration / 60, left=a.start / 60, color=GUINDA, edgecolor="white",
                    height=0.6)
            if len(buses) <= 6:
                ax.text((a.start + a.end) / 120, y, a.job_id.split("-")[-1], ha="center",
                        va="center", color="white", fontsize=8)
    ax.set_yticks(range(len(buses)))
    ax.set_yticklabels([b.id.split("-")[-1] for b in buses], fontsize=7 if len(buses) > 15 else 9)
    ax.invert_yaxis()
    ax.set_xlim(inst.day_start / 60, inst.day_end / 60)
    ax.set_xticks(range(int(inst.day_start // 60), int(inst.day_end // 60) + 1))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(int(inst.day_start // 60),
                                                     int(inst.day_end // 60) + 1)],
                       fontsize=8, rotation=0)
    ax.set_xlabel("Hora del día")
    ax.grid(axis="x", color="#dddddd", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    loads = sch.bus_loads()
    lmax = max(loads.values()) / 60
    ax.set_title(title or f"{inst.route} · {sch.algorithm} · tráfico {sch.traffic} · "
                 f"L_max = {lmax:.2f} h · no asignados = {len(sch.unassigned)}",
                 fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
