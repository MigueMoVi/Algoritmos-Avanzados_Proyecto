"""Diagrama de módulos y flujo de información (figura de la monografía)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "results" / "fig_arquitectura.png"
G, D, INK, LIGHT = "#6E0F1D", "#B8860B", "#222222", "#F6EFE3"

boxes = {
    "xlsx": (0.2, 3.3, "Excel 35 rutas\n(data/raw)", LIGHT),
    "builder": (2.6, 3.3, "builder.py\ngeneración y validación", "white"),
    "json": (5.0, 3.3, "Instancias JSON\n(data/instances)", LIGHT),
    "traffic": (5.0, 1.6, "traffic.py\nperfil T0/T1/T2", "white"),
    "alg": (7.6, 3.3, "algorithms/greedy.py\nLS · LPT", "white"),
    "valid": (10.2, 3.3, "validator.py\n7 restricciones", "white"),
    "metrics": (10.2, 1.6, "metrics.py · viz.py\nCSV · Gantt", LIGHT),
    "sim": (7.6, 1.6, "Referencia posterior\nB&B · CP-SAT · robustez", "#F2F2F2"),
    "model": (2.6, 1.6, "model.py\nJob · Bus · BusTimeline", "white"),
}
W, H = 2.1, 1.0
fig, ax = plt.subplots(figsize=(11, 3.4))
for k, (x, y, t, c) in boxes.items():
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=c, ec="#999999" if k == "sim" else G, lw=1.4,
                                ls="--" if k == "sim" else "-"))
    ax.text(x + W / 2, y + H / 2, t, ha="center", va="center", fontsize=8.5, color=INK)

def arrow(a, b, side_a="r", side_b="l", color=G):
    xa, ya = boxes[a][:2]; xb, yb = boxes[b][:2]
    pa = {"r": (xa + W, ya + H / 2), "b": (xa + W / 2, ya), "t": (xa + W / 2, ya + H), "l": (xa, ya + H / 2)}[side_a]
    pb = {"l": (xb, yb + H / 2), "t": (xb + W / 2, yb + H), "b": (xb + W / 2, yb), "r": (xb + W, yb + H / 2)}[side_b]
    ax.add_patch(FancyArrowPatch(pa, pb, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.3))

arrow("xlsx", "builder"); arrow("builder", "json"); arrow("json", "alg")
ax.add_patch(FancyArrowPatch((7.1, 2.4), (7.95, 3.3), arrowstyle="-|>", mutation_scale=12, color=D, lw=1.3))
arrow("alg", "valid"); arrow("valid", "metrics", "b", "t")
 
arrow("model", "builder", "t", "b", "#888888"); arrow("model", "traffic", "r", "l", "#888888")
ax.text(0.2, 0.9, "Flechas guinda: datos de la instancia · doradas: modelo de tráfico · grises: estructuras compartidas · caja gris: etapa posterior",
        fontsize=8, color="#555555")
ax.set_xlim(0, 12.5); ax.set_ylim(0.7, 4.5); ax.axis("off")
fig.tight_layout(); fig.savefig(OUT, dpi=170); print(OUT)
