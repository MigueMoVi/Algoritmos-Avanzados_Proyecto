import random

import pytest

from bus_sched.traffic import Band, TrafficProfile, get_profile


def test_t0_duracion_constante():
    p = get_profile("T0")
    for s in (360, 500, 1000, 1200):
        assert p.travel_time(s, 148.8) == pytest.approx(148.8)


def test_calculo_manual_t2():
    # J1 del ejemplo manual: sale 06:00, base 90 min.
    # 06:00–06:30 (f=0.9) recorre 30/0.9 = 33.33 min base; quedan 56.67 a f=1.3
    p = get_profile("T2")
    assert p.travel_time(360, 90) == pytest.approx(30 + 56.6667 * 1.3, abs=1e-3)
    # dentro de una sola franja de valle (f = 1.0)
    assert p.travel_time(570, 90) == pytest.approx(90.0)


def test_fifo_salir_mas_tarde_nunca_llega_antes():
    rng = random.Random(1)
    for name in ("T1", "T2"):
        p = get_profile(name)
        for _ in range(2000):
            base = rng.uniform(30, 200)
            s1 = rng.uniform(360, 1300)
            s2 = s1 + rng.uniform(0, 60)
            assert s1 + p.travel_time(s1, base) <= s2 + p.travel_time(s2, base) + 1e-9


def test_t1_normalizado_media_uno():
    assert get_profile("T1").mean_factor() == pytest.approx(1.0)
    assert get_profile("T2").mean_factor() > 1.0


def test_perfil_rechaza_solapes_y_factores_invalidos():
    with pytest.raises(ValueError):
        TrafficProfile("x", [Band(0, 100, 1.0), Band(50, 200, 1.2)])
    with pytest.raises(ValueError):
        TrafficProfile("x", [Band(0, 100, 0.0)])


def test_serializacion_ida_y_vuelta(tmp_path):
    p = get_profile("T1")
    f = tmp_path / "p.json"
    p.save(f)
    q = TrafficProfile.load(f)
    for s in (400, 700, 1100):
        assert q.travel_time(s, 120) == pytest.approx(p.travel_time(s, 120), abs=1e-3)
