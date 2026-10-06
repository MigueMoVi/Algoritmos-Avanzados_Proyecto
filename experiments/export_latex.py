"""Exporta tablas y figuras de los resultados al informe LaTeX.

    python experiments/export_latex.py

Lee results/E1_resumen.csv y results/E1_35_rutas.csv, escribe
docs/informe/tablas/{e1_resumen,anexo_rutas}.tex y copia results/fig_*.png a
docs/informe/figuras/. Así el informe usa siempre los resultados del programa.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
INF = ROOT / "docs" / "informe"


def pct(x: float) -> str:
    return f"{x:.1f}\\,\\%"


def e1_resumen() -> str:
    df = pd.read_csv(RES / "E1_resumen.csv").set_index(["trafico", "algoritmo"])
    total = int(df["vueltas"].iloc[0])

    def row(t, alg, label, bold):
        r = df.loc[(t, alg)]
        na = int(r.no_asignadas)
        cells = [f"{na} ({pct(100 * na / total)})", f"{int(r.rutas_completas)}",
                 f"{r.Lmax_medio_h:.2f}", pct(r.gap_medio_pct), f"{r.desbalance_medio_h:.2f}"]
        sob = r.sobrecosto_trafico_pct
        sob_s = "0.0\\,\\%" if abs(sob) < 0.05 else ("+" if sob > 0 else "") + pct(sob)
        if bold:
            cells = [cells[0], cells[1], cells[2], cells[3], cells[4]]
            cells = [f"\\textbf{{{c}}}" if i != 1 else c for i, c in enumerate(cells)]
            label = f"\\textbf{{{label}}}"
        return f"{t} & {label} & " + " & ".join(cells) + f" & {sob_s} \\\\"

    viol = int(df["violaciones"].sum())
    lines = [
        "\\begin{table}[H]",
        "\\centering\\small",
        f"\\caption{{Resultados agregados de E1 sobre las 35 rutas ({total:,} vueltas; brecha y desbalance "
        f"promediados por ruta; {viol} violaciones en todas las soluciones).}}".replace(",", "\\,"),
        "\\label{tab:e1}",
        "\\begin{tabular}{llrrrrrr}",
        "\\toprule",
        "Tráfico & Algoritmo & No atendidas & \\makecell{Rutas\\\\completas} & \\makecell{$L_{\\max}$\\\\medio (h)} "
        "& \\makecell{Brecha\\\\vs $LB$} & \\makecell{Desbalance\\\\(h)} & \\makecell{Sobrecosto\\\\por tráfico} \\\\",
        "\\midrule",
        row("T0", "LS", "LS = LPT", False),
        "\\midrule",
        row("T1", "LS", "LS", True), row("T1", "LPT", "LPT", False),
        "\\midrule",
        row("T2", "LS", "LS", True), row("T2", "LPT", "LPT", False),
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]
    return "\n".join(lines) + "\n"


def anexo_rutas() -> str:
    d = pd.read_csv(RES / "E1_35_rutas.csv")
    head = ("Ruta & Buses & Vueltas & $\\rho$ & NA T0 & \\makecell{LS\\\\NA T1} & \\makecell{LS\\\\$L_{\\max}$ T1} "
            "& \\makecell{LPT\\\\NA T1} & \\makecell{LPT\\\\$L_{\\max}$ T1} & \\makecell{LS\\\\NA T2} "
            "& \\makecell{LPT\\\\NA T2} \\\\")
    lines = ["{\\footnotesize", "\\begin{longtable}{lrrrrrrrrrr}",
             "\\caption{Resultados por ruta (resaltadas: rutas con $\\rho \\geq 0.85$).}\\label{tab:rutas}\\\\",
             "\\toprule", head, "\\midrule\\endfirsthead", "\\toprule", head, "\\midrule\\endhead",
             "\\bottomrule\\endfoot"]
    tot = dict(buses=0, vueltas=0, na0=0, na1=0, na1p=0, na2=0, na2p=0)
    for ruta in sorted(d.ruta.unique()):
        x = d[d.ruta == ruta]

        def g(t, a, c):
            return x[(x.trafico == t) & (x.algoritmo == a)][c].iloc[0]

        rho = g("T0", "LS", "rho_saturacion")
        vals = [int(g("T0", "LS", "buses")), int(g("T0", "LS", "trabajos")), f"{rho:.2f}",
                int(g("T0", "LS", "no_asignados")), int(g("T1", "LS", "no_asignados")),
                f"{g('T1', 'LS', 'Lmax_h'):.2f}", int(g("T1", "LPT", "no_asignados")),
                f"{g('T1', 'LPT', 'Lmax_h'):.2f}", int(g("T2", "LS", "no_asignados")),
                int(g("T2", "LPT", "no_asignados"))]
        for k, v in zip(("buses", "vueltas", None, "na0", "na1", None, "na1p", None, "na2", "na2p"), vals):
            if k:
                tot[k] += v
        pre = "\\rowcolor{dorado!20}" if round(rho, 2) >= 0.85 else ""
        lines.append(pre + f"{ruta} & " + " & ".join(str(v) for v in vals) + " \\\\")
    lines += ["\\midrule",
              f"\\textbf{{Total}} & {tot['buses']} & {tot['vueltas']} & & {tot['na0']} & {tot['na1']} & & "
              f"{tot['na1p']} & & {tot['na2']} & {tot['na2p']} \\\\",
              "\\end{longtable}}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    (INF / "tablas").mkdir(parents=True, exist_ok=True)
    (INF / "figuras").mkdir(parents=True, exist_ok=True)
    (INF / "tablas" / "e1_resumen.tex").write_text(e1_resumen(), encoding="utf-8")
    (INF / "tablas" / "anexo_rutas.tex").write_text(anexo_rutas(), encoding="utf-8")
    for f in sorted(RES.glob("fig_*.png")):
        shutil.copy2(f, INF / "figuras" / f.name)
    print("Tablas y figuras exportadas a", INF)


if __name__ == "__main__":
    main()
