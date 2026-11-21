"""PSV sizing engine (API 520 Part I, SI form).

Internal units: pressure kPa, mass flow kg/h, liquid flow L/min, temperature K, area mm2.
Engineering aid only: verify against the study basis and the manufacturer's certified data.
"""
import math

ATM_KPA = 101.325

# API 526 standard orifice effective areas, mm2
ORIFICES = [
    ("D", 71.0), ("E", 126.5), ("F", 198.1), ("G", 324.5), ("H", 506.5),
    ("J", 830.3), ("K", 1185.8), ("L", 1840.6), ("M", 2322.6), ("N", 2800.0),
    ("P", 4116.1), ("Q", 7129.0), ("R", 10322.6), ("T", 16774.2),
]

# ---------- unit sets: (pressure, mass flow, liquid flow, temperature) ----------
UNIT_SETS = {
    "bar":  {"p": "bar(g)",  "w": "kg/h", "q": "m3/h", "t": "C"},
    "kpa":  {"p": "kPa(g)",  "w": "kg/h", "q": "L/min", "t": "C"},
    "kgcm": {"p": "kg/cm2(g)", "w": "kg/h", "q": "m3/h", "t": "C"},
    "us":   {"p": "psig",    "w": "lb/h", "q": "gpm",  "t": "F"},
}
P_TO_KPA = {"bar(g)": 100.0, "kPa(g)": 1.0, "kg/cm2(g)": 98.0665, "psig": 6.894757}
W_TO_KGH = {"kg/h": 1.0, "lb/h": 0.45359237}
Q_TO_LMIN = {"m3/h": 1000 / 60, "L/min": 1.0, "gpm": 3.785412}


def p_gauge_kpa(v, unit_set):
    return v * P_TO_KPA[UNIT_SETS[unit_set]["p"]]


def w_kgh(v, unit_set):
    return v * W_TO_KGH[UNIT_SETS[unit_set]["w"]]


def q_lmin(v, unit_set):
    return v * Q_TO_LMIN[UNIT_SETS[unit_set]["q"]]


def t_kelvin(v, unit_set):
    return (v - 32) * 5 / 9 + 273.15 if UNIT_SETS[unit_set]["t"] == "F" else v + 273.15


def select_orifice(area_mm2):
    for letter, a in ORIFICES:
        if a >= area_mm2:
            return {"letter": letter, "area_mm2": a, "utilization_pct": 100 * area_mm2 / a}
    return {"letter": None, "area_mm2": None, "utilization_pct": None}


def relieving_pressure_kpa_g(set_g, overpressure_pct):
    return set_g * (1 + overpressure_pct / 100)


# ---------------------------- GAS / VAPOUR ----------------------------
def c_coeff(k):
    # Dimensionless API 520 coefficient (356 for k = 1.4); the SI constant 13160 sits in the area equation
    return 520 * math.sqrt(k * (2 / (k + 1)) ** ((k + 1) / (k - 1)))


def f2_coeff(k, r):
    return math.sqrt(k / (k - 1) * r ** (2 / k) * (1 - r ** ((k - 1) / k)) / (1 - r))


def size_gas(W, set_g, overpressure_pct, back_g, T, Z, M, k, Kd=0.975, Kb=1.0, Kc=1.0):
    P1 = relieving_pressure_kpa_g(set_g, overpressure_pct) + ATM_KPA
    P2 = back_g + ATM_KPA
    notes = []
    r = P2 / P1
    r_crit = (2 / (k + 1)) ** (k / (k - 1))
    if r <= r_crit:
        regime = "critical"
        C = c_coeff(k)
        A = 13160 * W / (C * Kd * P1 * Kb * Kc) * math.sqrt(T * Z / M)
        extra = {"C": C}
    else:
        regime = "subcritical"
        F2 = f2_coeff(k, r)
        A = 17.9 * W / (F2 * Kd * Kc) * math.sqrt(Z * T / (M * P1 * (P1 - P2)))
        extra = {"F2": F2}
        notes.append("Subcritical flow: Kb is not applied, F2 method used.")
    if back_g > 0.1 * set_g and Kb == 1.0:
        notes.append("Backpressure above 10% of set pressure: confirm Kb for a balanced-bellows valve.")
    return {"area_mm2": A, "regime": regime, "P1_kpa_abs": P1, "pressure_ratio": r,
            "critical_ratio": r_crit, **extra, "notes": notes}


# ------------------------------ LIQUID ------------------------------
def kv_from_re(Re):
    return 1.0 / (0.9935 + 2.878 / Re ** 0.5 + 342.75 / Re ** 1.5)


def size_liquid(Q, set_g, overpressure_pct, back_g, G, mu_cp, Kd=0.65, Kw=1.0, Kc=1.0):
    P1 = relieving_pressure_kpa_g(set_g, overpressure_pct)
    dP = P1 - back_g
    if dP <= 0:
        raise ValueError("Relieving pressure must exceed backpressure.")
    base = 11.78 * Q / (Kd * Kw * Kc) * math.sqrt(G / dP)
    A, Kv, Re, notes = base, 1.0, None, []
    for _ in range(50):
        Re = Q * 18800 * G / (mu_cp * math.sqrt(A))
        Kv_new = min(kv_from_re(Re), 1.0)
        A_new = base / Kv_new
        if abs(A_new - A) < 1e-6 * A:
            A, Kv = A_new, Kv_new
            break
        A, Kv = A_new, Kv_new
    if Kv < 0.999:
        notes.append("Viscosity correction Kv applied (Re = %.0f)." % Re)
    return {"area_mm2": A, "P1_kpa_g": P1, "dP_kpa": dP, "Kv": Kv, "Re": Re, "notes": notes}


# ------------------------------ STEAM ------------------------------
def kn_steam(P1_kpa_abs):
    if P1_kpa_abs <= 10339:
        return 1.0
    return (0.02764 * P1_kpa_abs - 1000) / (0.03324 * P1_kpa_abs - 1061)


def size_steam(W, set_g, overpressure_pct, back_g, Kd=0.975, Kb=1.0, Kc=1.0, Ksh=1.0):
    P1 = relieving_pressure_kpa_g(set_g, overpressure_pct) + ATM_KPA
    Kn = kn_steam(P1)
    A = 190.5 * W / (P1 * Kd * Kb * Kc * Kn * Ksh)
    notes = []
    if Ksh == 1.0:
        notes.append("Ksh = 1.0 assumes saturated steam. Enter the superheat correction factor if superheated.")
    if P1 > 22060:
        notes.append("Pressure above 22 MPa: the steam formula is outside its range.")
    return {"area_mm2": A, "P1_kpa_abs": P1, "Kn": Kn, "notes": notes}


# ------------------------------ DISPATCH ------------------------------
def size(data):
    """data: dict from the UI (values in the selected unit set)."""
    us = data.get("unit_set", "bar")
    fluid = data["fluid"]
    set_g = p_gauge_kpa(float(data["set_pressure"]), us)
    op = float(data.get("overpressure", 10))
    back = p_gauge_kpa(float(data.get("backpressure", 0)), us)
    Kd = data.get("Kd"); Kb = float(data.get("Kb") or 1.0); Kc = float(data.get("Kc") or 1.0)

    if set_g <= 0:
        raise ValueError("Set pressure must be greater than zero.")
    if not 0 <= op <= 50:
        raise ValueError("Overpressure should be between 0 and 50 %.")

    if fluid == "gas":
        res = size_gas(w_kgh(float(data["flow"]), us), set_g, op, back,
                       t_kelvin(float(data["temperature"]), us), float(data.get("Z", 1)),
                       float(data["mol_weight"]), float(data["k"]),
                       Kd=float(Kd) if Kd else 0.975, Kb=Kb, Kc=Kc)
    elif fluid == "liquid":
        res = size_liquid(q_lmin(float(data["flow"]), us), set_g, op, back,
                          float(data["sg"]), float(data["viscosity_cp"]),
                          Kd=float(Kd) if Kd else 0.65, Kw=float(data.get("Kw") or 1.0), Kc=Kc)
    elif fluid == "steam":
        res = size_steam(w_kgh(float(data["flow"]), us), set_g, op, back,
                         Kd=float(Kd) if Kd else 0.975, Kb=Kb, Kc=Kc, Ksh=float(data.get("Ksh") or 1.0))
    else:
        raise ValueError("Fluid must be gas, liquid or steam.")

    res["orifice"] = select_orifice(res["area_mm2"])
    if res["orifice"]["letter"] is None:
        res["notes"].append("Required area exceeds a T orifice: use multiple valves.")
    res["area_in2"] = res["area_mm2"] / 645.16
    res["set_kpa_g"] = set_g
    return res
