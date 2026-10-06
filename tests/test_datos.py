"""Pruebas de datos: Excel del proyecto (35 rutas), regla general de vueltas, JSON."""
from pathlib import Path

import pytest

from bus_sched.algorithms import list_scheduling
from bus_sched.builder import from_excel, random_instance, window_policy_jobs
from bus_sched.model import Instance
from bus_sched.traffic import get_profile

ROOT = Path(__file__).resolve().parents[1]
EXCEL = ROOT / "data" / "raw" / "tabla_proyecto_35_rutas.xlsx"


@pytest.mark.skipif(not EXCEL.exists(), reason="falta el Excel del proyecto")
def test_excel_35_rutas_y_vueltas_planificadas():
    insts = from_excel(EXCEL)
    assert len(insts) == 35
    assert len({i.route for i in insts}) == 35            # rutas distintas, sin duplicados
    assert all(i.n == i.meta["viajes_planificados"] for i in insts)
    assert sum(i.n for i in insts) == 4733
    rti01 = next(i for i in insts if i.route == "RTI-01")
    assert rti01.m == 35 and rti01.n == 103


def test_regla_general_de_vueltas():
    jobs = window_policy_jobs("X", 103, 148.8)          # RTI-01
    assert (jobs[0].r, jobs[0].d) == (360, 375)         # 06:00–06:15
    assert jobs[-1].nominal == 1171 and jobs[-1].d == 1171   # última salida 19:31
    assert all(j.r <= j.d for j in jobs)


def test_json_ida_y_vuelta(tmp_path):
    inst = random_instance(12, 3, seed=1)
    f = tmp_path / "i.json"
    inst.save(f)
    back = Instance.load(f)
    assert back.n == 12 and back.m == 3
    a = list_scheduling(inst, get_profile("T1"))
    b = list_scheduling(back, get_profile("T1"))
    assert max(a.bus_loads().values()) == pytest.approx(max(b.bus_loads().values()), abs=1.0)
