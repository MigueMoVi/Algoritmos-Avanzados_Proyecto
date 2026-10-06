"""Experimento preliminar de la Entrega 1 (reproducible).

    python -m sched build
    python experiments/run_experiments.py

E1  35 rutas × {LS, LPT} × tráfico {T0, T1, T2}
Salidas: results/E1_35_rutas.csv, results/E1_resumen.csv y figuras fig_*.png
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from sched.algorithms import list_scheduling, lpt  # noqa: E402
from sched.builder import manual_instance  # noqa: E402
from sched.metrics import compute_metrics, lower_bound  # noqa: E402
from sched.model import Instance  # noqa: E402
from sched.traffic import get_profile  # noqa: E402
from sched.validator import validate  # noqa: E402
from sched.viz import gantt  # noqa: E402

RES = ROOT / "results"
RES.mkdir(exist_ok=True)
C_LS, C_LPT = "#9B1B30", "#B8860B"     # paleta validada (dataviz)
INK, MUTED, GRID = "#222222", "#666666", "#E3E3E3"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 160})

ALGS = {"LS": list_scheduling, "LPT": lpt}


def routes() -> list[Instance]:
    files = sorted((ROOT / "data" / "instances").glob("RT*.json"))
    if not files:
        sys.exit("Ejecute primero: python -m sched build")
    return [Instance.load(f) for f in files]


# ====================================================================== E1
def e1(insts):
    rows = []
    lbs = {}
    for tname in ("T0", "T1", "T2"):
        prof = get_profile(tname)
        for inst in insts:
            lbs[inst.route, tname] = lower_bound(inst, prof)
            for name, alg in ALGS.items():
                s = alg(inst, prof)
                errs = validate(s, prof)
                m = compute_metrics(s, prof, lbs[inst.route, tname])
                m["violaciones"] = len(errs)
                rows.append(m)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "E1_35_rutas.csv", index=False, float_format="%.4f")

    agg = (df.groupby(["trafico", "algoritmo"])
             .agg(rutas=("ruta", "count"), vueltas=("trabajos", "sum"),
                  no_asignadas=("no_asignados", "sum"),
                  rutas_completas=("no_asignados", lambda x: int((x == 0).sum())),
                  Lmax_medio_h=("Lmax_h", "mean"), gap_medio_pct=("gap_vs_cota_pct", "mean"),
                  desbalance_medio_h=("desbalance_h", "mean"),
                  sobrecosto_trafico_pct=("sobrecosto_trafico_pct", "mean"),
                  tiempo_total_ms=("tiempo_ejecucion_ms", "sum"),
                  violaciones=("violaciones", "sum"))
             .reset_index())
    agg.to_csv(RES / "E1_resumen.csv", index=False, float_format="%.3f")
    return df, agg


def fig_e1(df):
    d = df
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    scen = ["T0", "T1", "T2"]
    x = range(len(scen))
    w = 0.36
    for k, (alg, col) in enumerate((("LS", C_LS), ("LPT", C_LPT))):
        sub = d[d.algoritmo == alg].groupby("trafico")
        na = [sub.get_group(t).no_asignados.sum() for t in scen]
        gp = [sub.get_group(t).gap_vs_cota_pct.mean() for t in scen]
        xs = [i + (k - 0.5) * w for i in x]
        axes[0].bar(xs, na, w - 0.03, color=col, label=alg)
        axes[1].bar(xs, gp, w - 0.03, color=col, label=alg)
        for xi, v in zip(xs, na):
            axes[0].text(xi, v, f"{v}", ha="center", va="bottom", fontsize=8, color=INK)
        for xi, v in zip(xs, gp):
            axes[1].text(xi, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8, color=INK)
    for ax, t in zip(axes, ("Vueltas no atendidas (suma de 35 rutas)",
                            "Brecha media de L_max vs cota inferior (%)")):
        ax.set_xticks(list(x))
        ax.set_xticklabels(["T0 sin tráfico", "T1 normalizado", "T2 pesimista"])
        ax.set_title(t, loc="left", fontsize=10, color=INK)
        ax.grid(axis="y", color=GRID)
        ax.set_axisbelow(True)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(RES / "fig_E1_escenarios.png")
    plt.close(fig)


# ================================================================ figuras base
def fig_profiles():
    fig, ax = plt.subplots(figsize=(8, 2.8))
    for name, col, ls in (("T2", C_LPT, "-"), ("T1", C_LS, "-"), ("T0", MUTED, "--")):
        p = get_profile(name)
        xs, ys = [], []
        if p.bands:
            for b in p.bands:
                xs += [b.start / 60, b.end / 60]
                ys += [b.factor, b.factor]
        else:
            xs, ys = [6, 22], [1, 1]
        ax.plot(xs, ys, color=col, lw=2, ls=ls, label=f"{name}")
    ax.set_xlim(6, 22)
    ax.set_xticks(range(6, 23, 2))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(6, 23, 2)])
    ax.set_ylabel("Factor sobre el tiempo base")
    ax.set_title("Perfiles de congestión por franja horaria", loc="left", fontsize=10)
    ax.grid(color=GRID)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    fig.tight_layout()
    fig.savefig(RES / "fig_perfiles_trafico.png")
    plt.close(fig)


def fig_gantts():
    t2 = get_profile("T2")
    inst = manual_instance()
    gantt(list_scheduling(inst, t2), t2, RES / "fig_gantt_manual_LS_T2.png")
    gantt(lpt(inst, t2), t2, RES / "fig_gantt_manual_LPT_T2.png")
    t1 = get_profile("T1")
    r = Instance.load(ROOT / "data" / "instances" / "RTI-01.json")
    gantt(list_scheduling(r, t1), t1, RES / "fig_gantt_RTI-01_LS_T1.png")


def main():
    t0 = time.time()
    insts = routes()
    assert len(insts) == 35, f"se esperaban 35 rutas, hay {len(insts)}"
    fig_profiles()
    fig_gantts()
    df1, agg1 = e1(insts)
    fig_e1(df1)
    print("E1\n", agg1.to_string(index=False))
    print(f"Listo en {time.time() - t0:.0f} s. Resultados en {RES}")


if __name__ == "__main__":
    main()
