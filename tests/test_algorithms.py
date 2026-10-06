import pytest

from sched.algorithms import branch_and_bound, list_scheduling, lpt
from sched.builder import manual_instance, random_instance
from sched.metrics import compute_metrics, lower_bound
from sched.model import Bus, Instance, Job, make_buses
from sched.traffic import get_profile
from sched.validator import validate

T0, T1, T2 = (get_profile(x) for x in ("T0", "T1", "T2"))


def lmax(s):
    return max(s.bus_loads().values())


# ---------------------------------------------------------------- básicos
@pytest.mark.parametrize("alg", [list_scheduling, lpt, branch_and_bound])
@pytest.mark.parametrize("prof", [T0, T1, T2])
def test_instancia_manual_valida_y_completa(alg, prof):
    s = alg(manual_instance(), prof)
    assert validate(s, prof) == []
    assert s.unassigned == []


def test_resultados_conocidos_ejemplo_manual():
    inst = manual_instance()
    # Sin tráfico: 8 vueltas de 90 min en 3 buses -> 3+3+2 -> L_max = 270
    for alg in (list_scheduling, lpt, branch_and_bound):
        assert lmax(alg(inst, T0)) == pytest.approx(270.0)
    # Con T2 (valores verificados a mano en la monografía)
    assert lmax(list_scheduling(inst, T2)) == pytest.approx(329.0, abs=0.05)
    assert lmax(lpt(inst, T2)) == pytest.approx(333.2, abs=0.05)
    assert lmax(branch_and_bound(inst, T2)) == pytest.approx(316.6, abs=0.05)


def test_bnb_nunca_peor_que_heuristicas():
    for seed in range(8):
        inst = random_instance(9, 3, seed=seed, spread=0.25)
        for prof in (T0, T2):
            b = branch_and_bound(inst, prof)
            for h in (list_scheduling(inst, prof), lpt(inst, prof)):
                assert (len(b.unassigned), lmax(b)) <= (len(h.unassigned), lmax(h) + 1e-9)
            assert validate(b, prof) == []


def test_cota_inferior_es_valida():
    for seed in range(5):
        inst = random_instance(10, 3, seed=seed, spread=0.2)
        b = branch_and_bound(inst, T1)
        if not b.unassigned:
            assert lmax(b) >= lower_bound(inst, T1) - 1e-6


# ------------------------------------------------------------------ límite
def test_ventana_de_ancho_cero():
    j = Job("J", "R", 60, 600, 600, 600)
    inst = Instance("R", "x", [j], make_buses("R", 1))
    s = list_scheduling(inst, T0)
    assert s.assignments["J"].start == 600 and validate(s, T0) == []


def test_vuelta_que_termina_exactamente_a_las_22():
    j = Job("J", "R", 120, 1200, 1200, 1200)          # 20:00 + 120 = 22:00
    inst = Instance("R", "x", [j], make_buses("R", 1))
    s = list_scheduling(inst, T0)
    assert s.unassigned == [] and s.assignments["J"].end == pytest.approx(1320)


def test_un_solo_bus():
    inst = random_instance(6, 1, seed=3)
    for alg in (list_scheduling, lpt):
        s = alg(inst, T1)
        assert validate(s, T1) == []


def test_duraciones_iguales_lpt_equivale_a_ls_sin_trafico():
    inst = random_instance(30, 6, seed=11, spread=0.0)
    a, b = list_scheduling(inst, T0), lpt(inst, T0)
    assert lmax(a) == pytest.approx(lmax(b))


# ----------------------------------------------------------------- adversos
def test_instancia_infactible_reporta_no_asignados():
    # 3 vueltas simultáneas de 2 h con ventana rígida y un solo bus
    jobs = [Job(f"J{k}", "R", 120, 480, 480, 480) for k in range(3)]
    inst = Instance("R", "x", jobs, make_buses("R", 1))
    for alg in (list_scheduling, lpt, branch_and_bound):
        s = alg(inst, T0)
        assert len(s.unassigned) == 2
        assert validate(s, T0) == []


def test_vuelta_que_choca_con_el_almuerzo_fijo():
    # almuerzo fijo 12:00–14:00; vuelta que debe salir 11:30 y dura 60 min
    bus = Bus("R-B1", "R", 720, 720)
    inst = Instance("R", "x", [Job("J", "R", 60, 690, 690, 690)], [bus])
    s = list_scheduling(inst, T0)
    assert s.unassigned == ["J"]


def test_almuerzo_flexible_se_mueve_para_dejar_pasar_la_vuelta():
    bus = Bus("R-B1", "R", 690, 780)                 # almuerzo puede iniciar 11:30–13:00
    inst = Instance("R", "x", [Job("J", "R", 60, 690, 690, 690)], [bus])
    s = list_scheduling(inst, T0)
    assert s.unassigned == [] and validate(s, T0) == []
    assert s.lunches["R-B1"][0] >= 750                # almuerzo después de la vuelta


def test_lpt_peor_caso_clasico_sin_ventanas():
    # Instancia de Graham (m=2): {3,3,2,2,2}; LPT = 7, óptimo = 6
    jobs = [Job(f"J{k}", "R", p * 60, 360, 1320 - p * 60, 360)
            for k, p in enumerate([3, 3, 2, 2, 2])]
    inst = Instance("R", "x", jobs, [Bus(f"R-B{i}", "R", 1200, 1200) for i in (1, 2)])
    assert lmax(lpt(inst, T0)) == pytest.approx(7 * 60)
    assert lmax(branch_and_bound(inst, T0)) == pytest.approx(6 * 60)


def test_validador_detecta_errores():
    inst = manual_instance()
    s = list_scheduling(inst, T0)
    a = next(iter(s.assignments.values()))
    a.start -= 100                                    # rompe ventana y duración
    errs = validate(s, T0)
    assert any("fuera de ventana" in e for e in errs)
    assert any("duración" in e for e in errs)


# ------------------------------------------------------------------ escala
def test_escala_ruta_grande_es_valida():
    inst = random_instance(400, 60, seed=5, base=150, spread=0.1)
    for alg in (list_scheduling, lpt):
        s = alg(inst, T1)
        assert validate(s, T1) == []
        m = compute_metrics(s, T1)
        assert m["asignados"] + m["no_asignados"] == 400
