"""Interfaz de línea de comandos.

    python -m sched build                       # Excel -> data/instances/*.json
    python -m sched demo --traffic T2           # ejemplo manual (LS, LPT, BnB, CP-SAT)
    python -m sched run --route RTI-01 --alg lpt --traffic T1 [--gantt]
    python -m sched run --instance mi.json --alg ls
    python -m sched simulate --route RTI-01 --alg ls --traffic T1 --sigma 0.1
    python -m sched profiles                    # muestra los perfiles T0/T1/T2
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .algorithms import ALGORITHMS, branch_and_bound
from .builder import from_excel, manual_instance
from .metrics import compute_metrics
from .model import Instance
from .simulation import simulate
from .timeutil import min_to_hhmm
from .traffic import PROFILES, get_profile
from .validator import validate

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def _load_instance(args) -> Instance:
    if getattr(args, "instance", None):
        return Instance.load(args.instance)
    if args.route.upper() == "DEMO":
        return manual_instance()
    p = DATA / "instances" / f"{args.route}.json"
    if not p.exists():
        sys.exit(f"No existe {p}. Ejecute primero: python -m sched build")
    return Instance.load(p)


def _solve(inst, alg, profile, policy="earliest", buffer=0.0):
    if alg == "bnb":
        return branch_and_bound(inst, profile)
    if alg == "cpsat":
        from .algorithms.cpsat import cpsat_solve
        return cpsat_solve(inst, profile)
    return ALGORITHMS[alg](inst, profile, policy=policy, buffer=buffer)


def _write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _print_metrics(m: dict) -> None:
    print(f"  L_max = {m['Lmax_h']:.3f} h | L_min = {m['Lmin_h']:.3f} h | "
          f"desbalance = {m['desbalance_h']:.3f} h | cota inf. = {m['cota_inferior_h']:.3f} h | "
          f"gap = {m['gap_vs_cota_pct']:.1f} %")
    print(f"  asignados = {m['asignados']}/{m['trabajos']} | utilización = "
          f"{m['utilizacion_media_pct']:.1f} % | sobrecosto tráfico = "
          f"{m['sobrecosto_trafico_pct']:.1f} % | tiempo = {m['tiempo_ejecucion_ms']:.1f} ms")


def cmd_build(args) -> None:
    out = DATA / "instances"
    out.mkdir(parents=True, exist_ok=True)
    insts = from_excel(args.excel)
    for inst in insts:
        inst.save(out / f"{inst.route}.json")
    manual_instance().save(out / "DEMO.json")
    tdir = DATA / "traffic"
    tdir.mkdir(parents=True, exist_ok=True)
    for name in PROFILES:
        get_profile(name).save(tdir / f"perfil_{name}.json")
    print(f"{len(insts)} instancias + DEMO escritas en {out}; perfiles en {tdir}")


def cmd_run(args) -> None:
    inst = _load_instance(args)
    profile = get_profile(args.traffic)
    sch = _solve(inst, args.alg, profile, args.policy, args.buffer)
    errors = validate(sch, profile)
    m = compute_metrics(sch, profile)
    print(f"{inst.route} ({inst.company}) · {inst.m} buses · {inst.n} vueltas · "
          f"algoritmo {sch.algorithm} · tráfico {profile.name}")
    _print_metrics(m)
    print("  VALIDACIÓN:", "OK (0 violaciones)" if not errors else f"{len(errors)} violaciones")
    for e in errors[:10]:
        print("   -", e)
    out = Path(args.out) if args.out else RESULTS / f"{inst.route}_{sch.algorithm}_{profile.name}.csv"
    _write_csv(sch.to_rows(), out)
    print("  asignaciones ->", out)
    if args.gantt:
        from .viz import gantt
        g = out.with_suffix(".png")
        gantt(sch, profile, g)
        print("  Gantt ->", g)
    if errors:
        sys.exit(1)


def cmd_demo(args) -> None:
    inst = manual_instance()
    profile = get_profile(args.traffic)
    print(f"Instancia manual: {inst.m} buses, {inst.n} vueltas, base 90 min, tráfico {profile.name}")
    print("Ventanas:", ", ".join(f"{j.id}[{min_to_hhmm(j.r)}–{min_to_hhmm(j.d)}]" for j in inst.jobs))
    algs = ["ls", "lpt", "bnb"] + (["cpsat"] if not args.no_cpsat else [])
    for alg in algs:
        sch = _solve(inst, alg, profile)
        m = compute_metrics(sch, profile)
        errs = validate(sch, profile)
        print(f"\n[{sch.algorithm}] L_max = {m['Lmax_h'] * 60:.1f} min  "
              f"(validación: {'OK' if not errs else errs})")
        for bus, items in sch.by_bus().items():
            load = sum(a.duration for a in items)
            seq = "  ".join(f"{a.job_id} {min_to_hhmm(a.start)}–{min_to_hhmm(a.end)} ({a.duration:.1f})"
                            for a in items)
            print(f"   {bus.split('-')[-1]}: {seq}  | carga {load:.1f} min")


def cmd_simulate(args) -> None:
    inst = _load_instance(args)
    profile = get_profile(args.traffic)
    sch = _solve(inst, args.alg, profile, args.policy, args.buffer)
    res = simulate(sch, profile, args.sigma, args.reps, args.seed)
    print(json.dumps(res, indent=2, ensure_ascii=False))


def cmd_profiles(args) -> None:
    for name in PROFILES:
        p = get_profile(name)
        print(f"{p.name}: {p.description}")
        for b in p.bands:
            print(f"   {min_to_hhmm(b.start)}–{min_to_hhmm(b.end)}  factor {b.factor:.3f}  {b.label}")
        print(f"   media ponderada en la jornada = {p.mean_factor():.3f}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="sched", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Excel -> instancias JSON")
    b.add_argument("--excel", default=str(DATA / "raw" / "tabla_37_empresas.xlsx"))
    b.set_defaults(func=cmd_build)

    def common(p):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--route", default="DEMO", help="código de ruta (p. ej. RTI-01) o DEMO")
        g.add_argument("--instance", help="ruta a un archivo JSON de instancia")
        p.add_argument("--alg", choices=["ls", "lpt", "bnb", "cpsat"], default="ls")
        p.add_argument("--traffic", default="T1", help="T0 | T1 | T2 | archivo.json")
        p.add_argument("--policy", choices=["earliest", "min_duration"], default="earliest")
        p.add_argument("--buffer", type=float, default=0.0, help="holgura relativa (0.10 = 10 %%)")

    r = sub.add_parser("run", help="resolver una instancia")
    common(r)
    r.add_argument("--out")
    r.add_argument("--gantt", action="store_true")
    r.set_defaults(func=cmd_run)

    d = sub.add_parser("demo", help="ejemplo manual")
    d.add_argument("--traffic", default="T2")
    d.add_argument("--no-cpsat", action="store_true")
    d.set_defaults(func=cmd_demo)

    s = sub.add_parser("simulate", help="Monte Carlo de la ejecución de un plan")
    common(s)
    s.add_argument("--sigma", type=float, default=0.10)
    s.add_argument("--reps", type=int, default=200)
    s.add_argument("--seed", type=int, default=2026)
    s.set_defaults(func=cmd_simulate)

    p = sub.add_parser("profiles", help="mostrar perfiles de tráfico")
    p.set_defaults(func=cmd_profiles)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
