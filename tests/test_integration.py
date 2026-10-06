from pathlib import Path

import pytest

from sched.algorithms import branch_and_bound, list_scheduling, lpt
from sched.builder import from_excel, manual_instance, random_instance
from sched.model import Instance
from sched.simulation import simulate
from sched.traffic import get_profile
from sched.validator import validate

ROOT = Path(__file__).resolve().parents[1]
EXCEL = ROOT / "data" / "raw" / "tabla_37_empresas.xlsx"


@pytest.mark.skipif(not EXCEL.exists(), reason="falta el Excel fuente")
def test_excel_genera_37_rutas_consistentes():
    insts = from_excel(EXCEL)
    assert len(insts) == 37
    by = {i.route: i for i in insts}
    assert by["RTU-28"].n == 145 and by["RTU-29"].n == 139
    # cada ruta tiene exactamente las vueltas planificadas en 'Parametros del modelo'
    assert all(i.n == int(i.meta["viajes_planificados"]) for i in insts)
    assert sum(i.n for i in insts) == 5017
    rti01 = next(i for i in insts if i.route == "RTI-01")
    assert rti01.m == 35 and rti01.n == 103
    assert all(j.r <= j.d for i in insts for j in i.jobs)


def test_politica_de_ventanas_reproduce_la_hoja_de_trabajos():
    from sched.builder import window_policy_jobs
    orig = {i.route: i for i in from_excel(EXCEL)}["RTI-01"]
    regen = window_policy_jobs("RTI-01", orig.n, orig.jobs[0].base)
    diff = [abs(a.r - b.r) + abs(a.d - b.d) for a, b in zip(orig.jobs, regen)]
    assert max(diff) <= 2          # coincide salvo redondeos de 1 min


def test_json_ida_y_vuelta(tmp_path):
    inst = random_instance(12, 3, seed=1)
    f = tmp_path / "i.json"
    inst.save(f)
    back = Instance.load(f)
    assert back.n == 12 and back.m == 3
    a = list_scheduling(inst, get_profile("T1"))
    b = list_scheduling(back, get_profile("T1"))
    assert max(a.bus_loads().values()) == pytest.approx(max(b.bus_loads().values()), abs=1.0)


def test_cpsat_coincide_o_mejora_bnb():
    pytest.importorskip("ortools")
    from sched.algorithms.cpsat import cpsat_solve
    for prof in (get_profile("T0"), get_profile("T2")):
        inst = manual_instance()
        c = cpsat_solve(inst, prof, time_limit_s=20)
        b = branch_and_bound(inst, prof)
        assert validate(c, prof) == []
        assert c.extra["status"] == "OPTIMAL"
        # CP-SAT explora además desplazar inicios dentro de la ventana
        assert max(c.bus_loads().values()) <= max(b.bus_loads().values()) + 1.0


def test_simulacion_sin_ruido_reproduce_el_plan():
    prof = get_profile("T1")
    s = list_scheduling(manual_instance(), prof)
    r = simulate(s, prof, sigma=0.0, reps=3)
    assert r["vueltas_fuera_ventana_pct"] == 0
    assert r["retraso_medio_min"] == pytest.approx(0.0)
    assert r["Lmax_real_h"] == pytest.approx(max(s.bus_loads().values()) / 60)


def test_simulacion_reproducible_con_semilla():
    prof = get_profile("T1")
    s = lpt(manual_instance(), prof)
    assert simulate(s, prof, 0.2, 50, seed=7) == simulate(s, prof, 0.2, 50, seed=7)


def test_mayor_variabilidad_produce_mas_retraso():
    prof = get_profile("T1")
    inst = random_instance(60, 12, seed=4, base=120)
    s = list_scheduling(inst, prof)
    r1 = simulate(s, prof, 0.05, 100)
    r2 = simulate(s, prof, 0.30, 100)
    assert r2["retraso_medio_min"] >= r1["retraso_medio_min"]
