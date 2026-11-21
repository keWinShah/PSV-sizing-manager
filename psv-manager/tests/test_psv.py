import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import psv_calc as p


def test_c_coeff_k14():
    assert abs(p.c_coeff(1.4) - 356) < 1.0


def test_gas_continuity_at_critical_ratio():
    k = 1.4
    r = (2 / (k + 1)) ** (k / (k - 1))
    P1 = 1201.325
    crit = p.size_gas(5000, 1000, 10, r * P1 - p.ATM_KPA + 0.001, 373.15, 1, 28, k)
    sub = p.size_gas(5000, 1000, 10, r * P1 - p.ATM_KPA + 0.05, 373.15, 1, 28, k)
    assert abs(crit["area_mm2"] - sub["area_mm2"]) / crit["area_mm2"] < 0.01


def test_gas_critical_scales_with_flow():
    a = p.size_gas(10000, 1000, 10, 0, 350, 1, 28, 1.4)["area_mm2"]
    b = p.size_gas(20000, 1000, 10, 0, 350, 1, 28, 1.4)["area_mm2"]
    assert abs(b / a - 2) < 1e-9


def test_liquid_viscosity_increases_area():
    water = p.size_liquid(500, 1000, 10, 0, 1.0, 1.0)["area_mm2"]
    oil = p.size_liquid(500, 1000, 10, 0, 1.0, 500)["area_mm2"]
    assert oil > water


def test_orifice_pick():
    assert p.select_orifice(300)["letter"] == "G"
    assert p.select_orifice(99999)["letter"] is None


def test_dispatch_us_units():
    r = p.size({"fluid": "steam", "unit_set": "us", "set_pressure": 150,
                "flow": 20000, "overpressure": 10})
    assert r["area_mm2"] > 0 and r["orifice"]["letter"]
