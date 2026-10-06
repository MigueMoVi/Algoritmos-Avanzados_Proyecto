"""Pruebas de List Scheduling y LPT (algoritmos de la Entrega 1)."""
import pytest

from bus_sched.algorithms import list_scheduling, lpt
from bus_sched.builder import manual_instance, random_instance
from bus_sched.metrics import compute_metrics, lower_bound
from bus_sched.model import Bus, Instance, Job, make_buses
from bus_sched.traffic import get_profile
from bus_sched.validator import validate

T0, T1, T2 = (get_profile(x) for x in ("T0", "T1", "T2"))
ALGS = (list_scheduling, lpt)


def lmax(s):
    return max(s.bus_loads().values())


# ------------------------------------------------------------------ básicos
@pytest.mark.parametrize("alg", ALGS)
@pytest.mark.parametrize("prof", [T0, T1, T2])
def test_basico_instancia_manual_valida_y_completa(alg, prof):
    s = alg(manual_instance(), prof)
    assert validate(s, prof) == []
    assert s.unassigned == []


def test_basico_resultados_del_ejemplo_manual():
    inst = manual_instance()
    # Sin tráfico: 8 vueltas de 90 min en 3 buses -> 3 + 3 + 2 -> L_max = 270
    assert lmax(list_scheduling(inst, T0)) == pytest.approx(270.0)
    assert lmax(lpt(inst, T0)) == pytest.approx(270.0)
    # Con T2 (valores calculados a mano en el informe, sección 7)
    assert lmax(list_scheduling(inst, T2)) == pytest.approx(329.0, abs=0.05)
    assert lmax(lpt(inst, T2)) == pytest.approx(333.2, abs=0.05)


def test_basico_asignacion_ls_del_ejemplo_manual():
    s = list_scheduling(manual_instance(), T2)
    bus = {a.job_id: a.bus_id.split("-")[-1] for a in s.assignments.values()}
    assert bus == {"J1": "B1", "J2": "B2", "J3": "B3", "J4": "B1",
                   "J5": "B2", "J6": "B3", "J7": "B2", "J8": "B1"}


def test_basico_orden_lpt_por_duracion_en_salida_nominal():
    s = lpt(manual_instance(), T2)
    bus = {a.job_id: a.bus_id.split("-")[-1] for a in s.assignments.values()}
    assert bus == {"J8": "B1", "J2": "B2", "J7": "B3", "J3": "B3",
                   "J1": "B1", "J6": "B1", "J4": "B2", "J5": "B2"}


# ------------------------------------------------------------------- límite
def test_limite_ventana_de_ancho_cero():
    inst = Instance("R", "x", [Job("J", "R", 60, 600, 600, 600)], make_buses("R", 1))
    for alg in ALGS:
        s = alg(inst, T0)
        assert s.assignments["J"].start == 600 and validate(s, T0) == []


def test_limite_vuelta_que_termina_exactamente_a_las_22():
    inst = Instance("R", "x", [Job("J", "R", 120, 1200, 1200, 1200)], make_buses("R", 1))
    s = list_scheduling(inst, T0)
    assert s.unassigned == [] and s.assignments["J"].end == pytest.approx(1320)


def test_limite_un_solo_bus():
    inst = random_instance(6, 1, seed=3)
    for alg in ALGS:
        assert validate(alg(inst, T1), T1) == []


def test_limite_duraciones_iguales_sin_trafico_lpt_equivale_a_ls():
    inst = random_instance(30, 6, seed=11, spread=0.0)
    assert lmax(list_scheduling(inst, T0)) == pytest.approx(lmax(lpt(inst, T0)))


# ------------------------------------------------------------------ adversos
def test_adverso_mas_vueltas_simultaneas_que_buses():
    jobs = [Job(f"J{k}", "R", 120, 480, 480, 480) for k in range(3)]
    inst = Instance("R", "x", jobs, make_buses("R", 1))
    for alg in ALGS:
        s = alg(inst, T0)
        assert len(s.unassigned) == 2 and validate(s, T0) == []


def test_adverso_peor_caso_clasico_de_lpt():
    # Graham (m = 2, duraciones 3,3,2,2,2 h): LPT = 7 h, mientras que el óptimo es 6 h
    jobs = [Job(f"J{k}", "R", p * 60, 360, 1320 - p * 60, 360)
            for k, p in enumerate([3, 3, 2, 2, 2])]
    inst = Instance("R", "x", jobs, [Bus(f"R-B{i}", "R", 1200, 1200) for i in (1, 2)])
    assert lmax(lpt(inst, T0)) == pytest.approx(7 * 60)


# ------------------------------------------------------------------ ventanas
def test_ventanas_toda_salida_dentro_de_su_ventana():
    inst = random_instance(80, 12, seed=7, base=130, spread=0.2)
    for alg in ALGS:
        s = alg(inst, T2)
        for a in s.assignments.values():
            j = inst.job(a.job_id)
            assert j.r - 1e-9 <= a.start <= j.d + 1e-9


# ------------------------------------------------------------------- tráfico
def test_trafico_duracion_asignada_coincide_con_p_j_s():
    inst = manual_instance()
    s = list_scheduling(inst, T2)
    for a in s.assignments.values():
        assert a.duration == pytest.approx(T2.travel_time(a.start, 90))


def test_trafico_aumenta_la_carga_total_en_t2():
    inst = random_instance(40, 8, seed=2, base=120)
    c0 = compute_metrics(list_scheduling(inst, T0), T0)["conduccion_total_h"]
    c2 = compute_metrics(list_scheduling(inst, T2), T2)["conduccion_total_h"]
    assert c2 > c0


# ------------------------------------------------------------------ almuerzo
def test_almuerzo_fijo_bloquea_la_vuelta():
    bus = Bus("R-B1", "R", 720, 720)           # almuerzo fijo 12:00–14:00
    inst = Instance("R", "x", [Job("J", "R", 60, 690, 690, 690)], [bus])
    assert list_scheduling(inst, T0).unassigned == ["J"]


def test_almuerzo_flexible_se_desplaza_para_dejar_pasar_la_vuelta():
    bus = Bus("R-B1", "R", 690, 780)           # almuerzo puede iniciar 11:30–13:00
    inst = Instance("R", "x", [Job("J", "R", 60, 690, 690, 690)], [bus])
    s = list_scheduling(inst, T0)
    assert s.unassigned == [] and validate(s, T0) == []
    assert s.lunches["R-B1"][0] >= 750


def test_almuerzo_cada_bus_tiene_su_almuerzo_en_ventana():
    inst = random_instance(60, 9, seed=5, base=110)
    for alg in ALGS:
        s = alg(inst, T1)
        for b in inst.buses:
            ls, le = s.lunches[b.id]
            assert b.lunch_r <= ls <= b.lunch_d and le - ls == pytest.approx(120)


# --------------------------------------------------- validación de restricciones
def test_validacion_detecta_solucion_corrompida():
    s = list_scheduling(manual_instance(), T0)
    a = next(iter(s.assignments.values()))
    a.start -= 100
    errs = validate(s, T0)
    assert any("fuera de ventana" in e for e in errs)
    assert any("duración" in e for e in errs)


def test_validacion_cota_inferior_no_supera_a_lmax():
    for seed in range(5):
        inst = random_instance(12, 3, seed=seed, spread=0.2)
        for alg in ALGS:
            s = alg(inst, T1)
            assert compute_metrics(s, T1)["cota_inferior_h"] * 60 <= lmax(s) + 1e-6


def test_validacion_ruta_grande_valida_y_conservacion():
    inst = random_instance(400, 60, seed=5, base=150, spread=0.1)
    for alg in ALGS:
        s = alg(inst, T1)
        assert validate(s, T1) == []
        assert len(s.assignments) + len(s.unassigned) == 400
