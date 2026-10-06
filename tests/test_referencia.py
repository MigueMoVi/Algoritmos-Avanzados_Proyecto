"""Pruebas de los mecanismos de referencia previstos para etapas posteriores
(Ramificación y Poda, CP-SAT y simulación). No forman parte de la evaluación
de la Entrega 1; se mantienen para que el prototipo siga siendo correcto."""
import pytest

from sched.algorithms import branch_and_bound, list_scheduling, lpt
from sched.builder import manual_instance, random_instance
from sched.simulation import simulate
from sched.traffic import get_profile
from sched.validator import validate

T0, T1, T2 = (get_profile(x) for x in ("T0", "T1", "T2"))


def lmax(s):
    return max(s.bus_loads().values())


def test_bnb_nunca_peor_que_ls_ni_lpt():
    for seed in range(4):
        inst = random_instance(9, 3, seed=seed, spread=0.25)
        b = branch_and_bound(inst, T2)
        assert validate(b, T2) == []
        for h in (list_scheduling(inst, T2), lpt(inst, T2)):
            assert (len(b.unassigned), lmax(b)) <= (len(h.unassigned), lmax(h) + 1e-9)


def test_cpsat_valido_y_no_peor_que_bnb():
    pytest.importorskip("ortools")
    from sched.algorithms.cpsat import cpsat_solve
    inst = manual_instance()
    c = cpsat_solve(inst, T2, time_limit_s=20)
    assert validate(c, T2) == [] and c.extra["status"] == "OPTIMAL"
    assert lmax(c) <= lmax(branch_and_bound(inst, T2)) + 1.0


def test_simulacion_sin_ruido_reproduce_el_plan():
    s = list_scheduling(manual_instance(), T1)
    r = simulate(s, T1, sigma=0.0, reps=3)
    assert r["vueltas_fuera_ventana_pct"] == 0 and r["retraso_medio_min"] == pytest.approx(0.0)
