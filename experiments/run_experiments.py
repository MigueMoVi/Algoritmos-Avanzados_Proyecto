"""Experimentos preliminares de la Entrega 1 (reproducibles).

    python experiments/run_experiments.py            # todo (≈ 2–4 min)
    python experiments/run_experiments.py --quick    # versión corta

E1  37 rutas × {LS, LPT} × {T0, T1, T2}
E2  heurísticas vs exactos (B&B propio y CP-SAT) en instancias pequeñas
E3  escalabilidad: tiempo de ejecución vs número de vueltas
E4  robustez Monte Carlo: σ ∈ {0.10, 0.20}, perfil T1
Salidas: results/*.csv y results/fig_*.png
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from sched.algorithms import branch_and_bound, list_scheduling, lpt  # noqa: E402
from sched.builder import manual_instance, random_instance  # noqa: E402
from sched.metrics import compute_metrics, lower_bound  # noqa: E402
from sched.model import Instance  # noqa: E402
from sched.simulation import simulate  # noqa: E402
from sched.traffic import get_profile  # noqa: E402
from sched.validator import validate  # noqa: E402
from sched.viz import gantt  # noqa: E402

RES = ROOT / "results"
RES.mkdir(exist_ok=True)
C_LS, C_LPT, C_EX = "#9B1B30", "#B8860B", "#2C7FB8"     # paleta validada (dataviz)
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
    df.to_csv(RES / "E1_37_rutas.csv", index=False, float_format="%.4f")

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
    for ax, t in zip(axes, ("Vueltas no asignadas (suma 37 rutas)",
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


# ====================================================================== E2
def e2(quick):
    from sched.algorithms.cpsat import cpsat_solve
    rows = []
    seeds = range(6 if quick else 15)
    for n in (8, 10, 12):
        for seed in seeds:
            inst = random_instance(n, 3, seed=1000 * n + seed, base=110, spread=0.25)
            for tname in ("T0", "T2"):
                prof = get_profile(tname)
                res = {"LS": list_scheduling(inst, prof), "LPT": lpt(inst, prof),
                       "BnB": branch_and_bound(inst, prof, time_limit_s=30),
                       "CP-SAT": cpsat_solve(inst, prof, time_limit_s=20, workers=4)}
                for name, s in res.items():
                    assert validate(s, prof) == [], (name, validate(s, prof)[:3])
                    rows.append({"n": n, "seed": seed, "trafico": tname, "algoritmo": name,
                                 "no_asignados": len(s.unassigned),
                                 "Lmax_min": max(s.bus_loads().values()),
                                 "tiempo_ms": s.runtime_s * 1000,
                                 "estado": s.extra.get("status", "")})
    df = pd.DataFrame(rows)
    ref = df[df.algoritmo == "CP-SAT"].set_index(["n", "seed", "trafico"])
    def gap(r):
        o = ref.loc[(r.n, r.seed, r.trafico)]
        if r.no_asignados != o.no_asignados:
            return float("nan")
        return 100 * (r.Lmax_min - o.Lmax_min) / o.Lmax_min
    df["gap_vs_cpsat_pct"] = df.apply(gap, axis=1)
    df["mas_no_asignados_que_cpsat"] = df.apply(
        lambda r: r.no_asignados - ref.loc[(r.n, r.seed, r.trafico)].no_asignados, axis=1)
    df.to_csv(RES / "E2_exactos.csv", index=False, float_format="%.3f")
    agg = (df.groupby(["trafico", "algoritmo"])
             .agg(instancias=("seed", "count"), gap_medio_pct=("gap_vs_cpsat_pct", "mean"),
                  gap_max_pct=("gap_vs_cpsat_pct", "max"),
                  optimo_alcanzado=("gap_vs_cpsat_pct", lambda x: int((x.abs() < 0.5).sum())),
                  peor_factibilidad=("mas_no_asignados_que_cpsat", lambda x: int((x > 0).sum())),
                  tiempo_medio_ms=("tiempo_ms", "mean"))
             .reset_index())
    agg.to_csv(RES / "E2_resumen.csv", index=False, float_format="%.3f")
    return df, agg


# ====================================================================== E3
def e3(quick):
    rows = []
    sizes = (100, 250, 500, 1000) if quick else (100, 250, 500, 1000, 2000, 4000)
    prof = get_profile("T1")
    for n in sizes:
        m = max(3, n // 3)
        inst = random_instance(n, m, seed=n, base=140, spread=0.1)
        for name, alg in ALGS.items():
            best = min(alg(inst, prof).runtime_s for _ in range(3))
            rows.append({"n": n, "m": m, "algoritmo": name, "tiempo_ms": best * 1000})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "E3_escalabilidad.csv", index=False, float_format="%.3f")
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for name, col in (("LS", C_LS), ("LPT", C_LPT)):
        s = df[df.algoritmo == name]
        ax.plot(s.n, s.tiempo_ms, color=col, lw=2, marker="o", ms=5, label=name)
        ax.annotate(name, (s.n.iloc[-1], s.tiempo_ms.iloc[-1]), xytext=(5, 0),
                    textcoords="offset points", color=INK, fontsize=8, va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Vueltas n (buses m = n/3)")
    ax.set_ylabel("Tiempo (ms, escala log)")
    ax.set_title("Escalabilidad de las heurísticas (perfil T1)", loc="left", fontsize=10)
    ax.grid(color=GRID, which="both")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(RES / "fig_E3_escalabilidad.png")
    plt.close(fig)
    return df


# ====================================================================== E4
def e4(insts, quick):
    prof = get_profile("T1")
    reps = 30 if quick else 100
    rows = []
    for inst in insts:
        for name, alg in ALGS.items():
            s = alg(inst, prof)
            for sigma in (0.10, 0.20):
                r = simulate(s, prof, sigma, reps, seed=2026)
                r["no_asignados_plan"] = len(s.unassigned)
                rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "E4_montecarlo.csv", index=False, float_format="%.4f")
    agg = (df.groupby(["algoritmo", "sigma"])
             .agg(fuera_ventana_pct=("vueltas_fuera_ventana_pct", "mean"),
                  fuera_ventana_p95=("vueltas_fuera_ventana_pct_p95", "mean"),
                  retraso_medio_min=("retraso_medio_min", "mean"),
                  buses_horas_extra_pct=("buses_horas_extra_pct", "mean"),
                  no_asignados_plan=("no_asignados_plan", "sum"))
             .reset_index())
    agg.to_csv(RES / "E4_resumen.csv", index=False, float_format="%.3f")

    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    w = 0.36
    for k, (alg, col) in enumerate((("LS", C_LS), ("LPT", C_LPT))):
        vals = [float(agg[(agg.algoritmo == alg) & (agg.sigma == sg)].fuera_ventana_pct.iloc[0])
                for sg in (0.10, 0.20)]
        xs = [i + (k - 0.5) * w for i in range(2)]
        ax.bar(xs, vals, w - 0.03, color=col, label=alg)
        for xi, v in zip(xs, vals):
            ax.text(xi, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["σ = 0.10", "σ = 0.20"])
    ax.legend(frameon=False)
    ax.set_ylabel("% vueltas que salen fuera de ventana")
    ax.set_title("Robustez ante variabilidad del tráfico (T1, 37 rutas)", loc="left", fontsize=10)
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(RES / "fig_E4_robustez.png")
    plt.close(fig)
    return df, agg


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
    gantt(branch_and_bound(inst, t2), t2, RES / "fig_gantt_manual_BnB_T2.png")
    t1 = get_profile("T1")
    r = Instance.load(ROOT / "data" / "instances" / "RTI-01.json")
    gantt(list_scheduling(r, t1), t1, RES / "fig_gantt_RTI-01_LS_T1.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    insts = routes()
    fig_profiles()
    fig_gantts()
    df1, agg1 = e1(insts)
    fig_e1(df1)
    print("E1\n", agg1.to_string(index=False))
    _, agg2 = e2(a.quick)
    print("E2\n", agg2.to_string(index=False))
    print("E3\n", e3(a.quick).to_string(index=False))
    _, agg4 = e4(insts, a.quick)
    print("E4\n", agg4.to_string(index=False))
    print(f"Listo en {time.time() - t0:.0f} s. Resultados en {RES}")


if __name__ == "__main__":
    main()
