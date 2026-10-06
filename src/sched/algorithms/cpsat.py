"""Modelo exacto de referencia con OR-Tools CP-SAT (tiempo discretizado a 1 min).

Variables
  s_j  in [r_j, d_j]          inicio entero (minutos)
  p_j  = tabla_j[s_j - r_j]   duración con tráfico (AddElement, redondeada
                              hacia arriba al minuto)
  x_ij in {0,1}               trabajo j en bus i (intervalo opcional)
  L_i  = sum_j x_ij * p_j     carga del bus i
Restricciones
  sum_i x_ij + u_j = 1        (u_j = 1 si j no se asigna)
  NoOverlap por bus (incluye el almuerzo fijo)
  s_j + p_j <= fin de jornada
Objetivo (lexicográfico vía pesos)
  min  BIG * sum_j u_j + L_max
"""

from __future__ import annotations

import math
import time

from ..model import Assignment, Instance, Schedule
from ..traffic import TrafficProfile


def cpsat_solve(inst: Instance, profile: TrafficProfile, time_limit_s: float = 30.0,
                workers: int = 1) -> Schedule:
    from ortools.sat.python import cp_model

    t0 = time.perf_counter()
    mdl = cp_model.CpModel()
    horizon = int(math.ceil(inst.day_end))
    big = horizon * len(inst.buses) + 1
    S, P, E, U = {}, {}, {}, {}
    X: dict[tuple[int, str], object] = {}
    Y: dict[tuple[int, str], object] = {}
    per_bus = {i: [] for i in range(inst.m)}

    LS = {}
    for i, b in enumerate(inst.buses):
        lr, ld, ldur = int(math.ceil(b.lunch_r)), int(math.floor(b.lunch_d)), int(round(b.lunch_dur))
        ls = mdl.NewIntVar(lr, ld, f"ls_{i}")
        LS[i] = ls
        per_bus[i].append(mdl.NewFixedSizeIntervalVar(ls, ldur, f"lunch_{i}"))

    for j in inst.jobs:
        r, d = int(math.ceil(j.r - 1e-9)), int(math.floor(j.d + 1e-9))
        table = [int(math.ceil(profile.travel_time(t, j.base) - 1e-9)) for t in range(r, d + 1)]
        s = mdl.NewIntVar(r, d, f"s_{j.id}")
        idx = mdl.NewIntVar(0, d - r, f"i_{j.id}")
        mdl.Add(idx == s - r)
        p = mdl.NewIntVar(min(table), max(table), f"p_{j.id}")
        mdl.AddElement(idx, table, p)
        e = mdl.NewIntVar(r, horizon, f"e_{j.id}")
        mdl.Add(e == s + p)
        u = mdl.NewBoolVar(f"u_{j.id}")
        S[j.id], P[j.id], E[j.id], U[j.id] = s, p, e, u
        lits = []
        for i in range(inst.m):
            x = mdl.NewBoolVar(f"x_{i}_{j.id}")
            X[i, j.id] = x
            lits.append(x)
            per_bus[i].append(mdl.NewOptionalIntervalVar(s, p, e, x, f"iv_{i}_{j.id}"))
            y = mdl.NewIntVar(0, max(table), f"y_{i}_{j.id}")
            mdl.Add(y == p).OnlyEnforceIf(x)
            mdl.Add(y == 0).OnlyEnforceIf(x.Not())
            Y[i, j.id] = y
        mdl.AddExactlyOne(lits + [u])

    for i in range(inst.m):
        mdl.AddNoOverlap(per_bus[i])
    # simetría: buses con el mismo turno de almuerzo -> cargas no crecientes
    loads = []
    for i in range(inst.m):
        L = mdl.NewIntVar(0, horizon, f"L_{i}")
        mdl.Add(L == sum(Y[i, j.id] for j in inst.jobs))
        loads.append(L)
    for i in range(inst.m):
        for k in range(i + 1, inst.m):
            if (inst.buses[i].lunch_r, inst.buses[i].lunch_d) == \
                    (inst.buses[k].lunch_r, inst.buses[k].lunch_d):
                mdl.Add(loads[i] >= loads[k])
                break
    lmax = mdl.NewIntVar(0, horizon, "Lmax")
    mdl.AddMaxEquality(lmax, loads)
    mdl.Minimize(big * sum(U.values()) + lmax)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = 2026          # reproducible con workers=1
    status = solver.Solve(mdl)

    sch = Schedule(inst, "CP-SAT", profile.name)
    sch.extra = {"status": solver.StatusName(status),
                 "objetivo_Lmax_min": None, "cota_inferior": solver.BestObjectiveBound()}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        sch.extra["objetivo_Lmax_min"] = solver.Value(lmax)
        for i, b in enumerate(inst.buses):
            ls = float(solver.Value(LS[i]))
            sch.lunches[b.id] = (ls, ls + b.lunch_dur)
        for j in inst.jobs:
            if solver.Value(U[j.id]):
                sch.unassigned.append(j.id)
                continue
            for i, b in enumerate(inst.buses):
                if solver.Value(X[i, j.id]):
                    s = float(solver.Value(S[j.id]))
                    # duración exacta (no redondeada) para validar igual que el resto
                    sch.assignments[j.id] = Assignment(j.id, b.id, s,
                                                       s + profile.travel_time(s, j.base))
    sch.runtime_s = time.perf_counter() - t0
    return sch
