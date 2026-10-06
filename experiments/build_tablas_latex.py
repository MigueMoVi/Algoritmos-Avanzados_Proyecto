"""Genera las tablas de resultados del informe LaTeX a partir de los CSV de
results/ y copia las figuras a docs/informe/figuras/.

    python experiments/build_tablas_latex.py

Así las cifras del informe salen siempre de los mismos archivos que produce
run_experiments.py (no se escriben a mano).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
INF = ROOT / "docs" / "informe"
TAB = INF / "tablas"
FIG = INF / "figuras"

FIGURAS = ["fig_perfiles_trafico.png", "fig_arquitectura.png", "fig_gantt_manual_LS_T2.png",
           "fig_gantt_manual_LPT_T2.png", "fig_gantt_RTI-01_LS_T1.png", "fig_E1_escenarios.png"]


def pct(x: float) -> str:
    return f"{x:.1f}".replace("-0.0", "0.0")


def e1_resumen() -> str:
    agg = pd.read_csv(RES / "E1_resumen.csv").set_index(["trafico", "algoritmo"])
    total = int(agg.iloc[0].vueltas)
    rows = []
    for tr in ("T0", "T1", "T2"):
        algs = (("LS = LPT", "LS"),) if tr == "T0" else (("LS", "LS"), ("LPT", "LPT"))
        for label, key in algs:
            r = agg.loc[(tr, key)]
            na = int(r.no_asignadas)
            bold = (tr != "T0" and key == "LS")
            b = (lambda s: f"\\textbf{{{s}}}") if bold else (lambda s: s)
            rows.append(" & ".join([
                tr, b(label), b(f"{na} ({100 * na / total:.1f}\\,\\%)"), str(int(r.rutas_completas)),
                b(f"{r.Lmax_medio_h:.2f}"), b(f"{r.gap_medio_pct:.1f}\\,\\%"), b(f"{r.desbalance_medio_h:.2f}"),
                f"{'+' if r.sobrecosto_trafico_pct > 0.05 else ''}{pct(r.sobrecosto_trafico_pct)}\\,\\%",
            ]) + r" \\")
        if tr != "T2":
            rows.append(r"\midrule")
    return "\n".join([
        r"\begin{table}[H]",
        r"\centering\small",
        r"\caption{Resultados agregados de E1 sobre las 35 rutas (" + f"{total:,}".replace(",", "\\,")
        + r" vueltas; brecha y desbalance promediados por ruta; 0 violaciones en todas las soluciones).}",
        r"\label{tab:e1}",
        r"\begin{tabular}{llrrrrrr}",
        r"\toprule",
        r"Tráfico & Algoritmo & No atendidas & \makecell{Rutas\\completas} & \makecell{$L_{\max}$\\medio (h)} & "
        r"\makecell{Brecha\\vs $LB$} & \makecell{Desbalance\\(h)} & \makecell{Sobrecosto\\por tráfico} \\",
        r"\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])


def anexo_rutas() -> str:
    d = pd.read_csv(RES / "E1_35_rutas.csv")
    lines = []
    tot = {"b": 0, "n": 0, "t0": 0, "ls1": 0, "lpt1": 0, "ls2": 0, "lpt2": 0}
    for route in sorted(d.ruta.unique()):
        x = d[d.ruta == route]

        def g(t, a, c):
            return x[(x.trafico == t) & (x.algoritmo == a)][c].iloc[0]

        rho = g("T0", "LS", "rho_saturacion")
        vals = [route, int(g("T0", "LS", "buses")), int(g("T0", "LS", "trabajos")), f"{rho:.2f}",
                int(g("T0", "LS", "no_asignados")), int(g("T1", "LS", "no_asignados")),
                f"{g('T1', 'LS', 'Lmax_h'):.2f}", int(g("T1", "LPT", "no_asignados")),
                f"{g('T1', 'LPT', 'Lmax_h'):.2f}", int(g("T2", "LS", "no_asignados")),
                int(g("T2", "LPT", "no_asignados"))]
        tot["b"] += vals[1]; tot["n"] += vals[2]; tot["t0"] += vals[4]; tot["ls1"] += vals[5]
        tot["lpt1"] += vals[7]; tot["ls2"] += vals[9]; tot["lpt2"] += vals[10]
        row = " & ".join(str(v) for v in vals) + r" \\"
        if rho >= 0.85:
            row = r"\rowcolor{dorado!20}" + row
        lines.append(row)
    lines.append(r"\midrule")
    lines.append(f"\\textbf{{Total}} & {tot['b']} & {tot['n']} & & {tot['t0']} & {tot['ls1']} & & "
                 f"{tot['lpt1']} & & {tot['ls2']} & {tot['lpt2']} \\\\")
    return "\n".join([
        r"{\footnotesize",
        r"\begin{longtable}{lrrrrrrrrrr}",
        r"\caption{Resultados por ruta (resaltadas: rutas con $\rho \geq 0.85$).}\label{tab:rutas}\\",
        r"\toprule",
        r"Ruta & Buses & Vueltas & $\rho$ & NA T0 & \makecell{LS\\NA T1} & \makecell{LS\\$L_{\max}$ T1} & "
        r"\makecell{LPT\\NA T1} & \makecell{LPT\\$L_{\max}$ T1} & \makecell{LS\\NA T2} & \makecell{LPT\\NA T2} \\",
        r"\midrule\endfirsthead",
        r"\toprule",
        r"Ruta & Buses & Vueltas & $\rho$ & NA T0 & \makecell{LS\\NA T1} & \makecell{LS\\$L_{\max}$ T1} & "
        r"\makecell{LPT\\NA T1} & \makecell{LPT\\$L_{\max}$ T1} & \makecell{LS\\NA T2} & \makecell{LPT\\NA T2} \\",
        r"\midrule\endhead",
        r"\bottomrule\endfoot",
        *lines,
        r"\end{longtable}}",
    ])


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    (TAB / "e1_resumen.tex").write_text(e1_resumen() + "\n", encoding="utf-8")
    (TAB / "anexo_rutas.tex").write_text(anexo_rutas() + "\n", encoding="utf-8")
    for f in FIGURAS:
        shutil.copy(RES / f, FIG / f)
    print("tablas ->", TAB, "| figuras ->", FIG)


if __name__ == "__main__":
    main()
