"""
utils/physics.py — Core power system stability models
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple


# ── System parameters ─────────────────────────────────────────────────────────

@dataclass
class GridParams:
    gen_mw:     float = 850.0
    load_mw:    float = 780.0
    base_kv:    float = 345.0
    frequency:  float = 60.0
    fault_type: str   = "3-Phase (Severe)"
    fault_dur:  float = 100.0    # ms
    fault_bus:  str   = "Bus 1 (Generator)"
    sim_dur:    float = 10.0     # s
    damping:    float = 0.05


# ── Thermal stability ──────────────────────────────────────────────────────────

LINES = [
    ("L1-2", 1, 2, 95.0),
    ("L1-3", 1, 3, 80.0),
    ("L2-4", 2, 4, 75.0),
    ("L3-4", 3, 4, 70.0),
    ("L4-5", 4, 5, 85.0),
    ("L3-5", 3, 5, 90.0),
    ("L5-6", 5, 6, 65.0),
    ("L2-6", 2, 6, 78.0),
]

THERMAL_LIMIT_C = 90.0   # °C — rated conductor temperature
AMBIENT_C       = 25.0   # °C

def compute_thermal(p: GridParams):
    """Returns per-line thermal loading and temperature time series."""
    rng = np.random.default_rng(seed=int(p.gen_mw + p.load_mw))
    ratio = p.load_mw / p.gen_mw

    loadings = {}
    for name, *_ , cap in LINES:
        base = ratio * 100 * (0.65 + rng.uniform(0, 0.7))
        loadings[name] = min(base, 108.0)

    # Temperature rise vs time for most-loaded line
    t = np.linspace(0, p.sim_dur, 200)
    max_load = max(loadings.values()) / 100.0
    tau = 3.5                 # thermal time constant (minutes) → seconds
    delta_T = (THERMAL_LIMIT_C - AMBIENT_C) * max_load
    temp = AMBIENT_C + delta_T * (1 - np.exp(-t / tau))
    temp += rng.normal(0, 0.4, len(t))   # measurement noise

    return loadings, t, temp


def line_status(loading_pct: float) -> str:
    if loading_pct > 95: return "overloaded"
    if loading_pct > 80: return "warning"
    return "normal"


# ── Voltage stability ──────────────────────────────────────────────────────────

BUSES = ["Bus 1", "Bus 2", "Bus 3", "Bus 4", "Bus 5", "Bus 6"]

def compute_voltage(p: GridParams):
    """P-V nose curve, per-bus voltage profile, Q reserves."""
    rng = np.random.default_rng(seed=int(p.load_mw * 2))
    v_nom = p.base_kv / 345.0            # normalise to 1 pu at 345 kV

    # P-V curve
    lam = np.linspace(0, 1.5, 300)
    V_upper = v_nom * (1.0 - 0.35 * lam - 0.18 * lam**2)
    V_lower = v_nom * (0.6 - 0.25 * lam)
    collapse_idx = np.argmax(V_upper < V_lower)
    if collapse_idx == 0:
        collapse_idx = 250

    V_upper[:collapse_idx] = np.clip(V_upper[:collapse_idx], 0.5, 1.15)
    V_lower[:collapse_idx] = np.clip(V_lower[:collapse_idx], 0.45, 1.05)

    # Load margin (MW) to nose point
    load_margin = (lam[collapse_idx] - p.load_mw / p.gen_mw) * p.gen_mw

    # Bus voltage profile
    bus_voltages = {}
    for bus in BUSES:
        v = v_nom * (0.93 + rng.uniform(-0.06, 0.06))
        bus_voltages[bus] = float(np.clip(v, 0.80, 1.08))

    # Q reserve per generator
    q_max  = [250, 200, 180]
    q_used = [max(0, q * (p.load_mw / p.gen_mw) * (0.7 + rng.uniform(0, 0.3)))
              for q in q_max]
    q_res  = [q_max[i] - q_used[i] for i in range(3)]

    return lam, V_upper, V_lower, collapse_idx, load_margin, bus_voltages, q_res


def bus_v_status(v_pu: float) -> str:
    if v_pu < 0.90: return "danger"
    if v_pu < 0.95: return "warning"
    if v_pu > 1.05: return "warning"
    return "ok"


# ── Transient stability ────────────────────────────────────────────────────────

GENERATORS = [
    {"name": "Gen 1", "H": 6.5, "D": 4.0, "Pm_frac": 0.38, "delta0": 20.0},
    {"name": "Gen 2", "H": 4.2, "D": 3.0, "Pm_frac": 0.33, "delta0": 18.0},
    {"name": "Gen 3", "H": 3.8, "D": 2.5, "Pm_frac": 0.29, "delta0": 22.0},
]
CRITICAL_ANGLE = 120.0   # degrees

def _fault_severity(fault_type: str) -> float:
    return {
        "3-Phase (Severe)":       0.10,
        "Line-to-Line":           0.35,
        "Double Line-to-Ground":  0.25,
        "Single Line-to-Ground":  0.55,
    }.get(fault_type, 0.10)

def swing_equation(p: GridParams) -> Tuple[np.ndarray, List[np.ndarray], np.ndarray]:
    """Numerically integrate swing equation for each generator."""
    dt        = 0.002                        # 2 ms time step
    n_steps   = int(p.sim_dur / dt)
    t         = np.arange(n_steps) * dt

    fault_start = 0.5                        # s — fault occurs at 0.5 s
    fault_end   = fault_start + p.fault_dur / 1000.0
    ke          = _fault_severity(p.fault_type)
    omega_s     = 2 * np.pi * p.frequency

    deltas, omegas = [], []
    for g in GENERATORS:
        Pm     = g["Pm_frac"] * p.gen_mw
        H      = g["H"]
        D      = g["D"] * p.damping / 0.05  # scale by user damping
        delta  = np.zeros(n_steps)
        omega  = np.zeros(n_steps)
        delta[0] = g["delta0"]
        omega[0] = 0.0

        for i in range(1, n_steps):
            in_fault = fault_start <= t[i] <= fault_end
            Pe_coeff = ke if in_fault else 0.95
            Pe       = Pe_coeff * Pm * np.sin(np.radians(delta[i-1]))
            Pa       = Pm - Pe
            # 2H/ωs · d²δ/dt² = Pa − D·dω/dt
            domega   = (omega_s / (2 * H)) * (Pa - D * omega[i-1]) * dt
            omega[i] = omega[i-1] + domega
            ddelta   = np.degrees(omega[i]) * dt
            delta[i] = delta[i-1] + ddelta
            # Limit: generator loses synchronism beyond 180°
            if delta[i] > 179.0:
                delta[i:] = 180.0 + np.random.normal(0, 2, n_steps - i)
                break

        deltas.append(delta)
        omegas.append(omega)

    # Frequency deviation (aggregate)
    freq_dev = np.zeros(n_steps)
    for i in range(1, n_steps):
        dPe = sum(
            (_fault_severity(p.fault_type) if fault_start <= t[i] <= fault_end else 0.95)
            * GENERATORS[j]["Pm_frac"] * p.gen_mw
            * np.sin(np.radians(deltas[j][i]))
            for j in range(3)
        )
        dP = p.gen_mw - dPe - p.load_mw
        freq_dev[i] = freq_dev[i-1] + dP / (2 * sum(g["H"] for g in GENERATORS) * 1000) * dt

    return t, deltas, freq_dev


def compute_cct(p: GridParams) -> float:
    """Estimate critical clearing time via equal area criterion."""
    ke  = _fault_severity(p.fault_type)
    Pm  = p.gen_mw * 0.38
    d0  = np.radians(20.0)
    dmax = np.radians(160.0)
    # Accelerating area = Pa * (dcl - d0)
    # Decelerating area must equal accelerating area
    Pa_avg = Pm * (1 - ke * np.sin(np.radians(20)))
    H      = 6.5
    omega_s = 2 * np.pi * p.frequency
    # TCR = sqrt(4*H*(dcr - d0) / (ω_s * Pa_avg))
    dcr = np.radians(90.0)
    try:
        cct = np.sqrt(4 * H * (dcr - d0) / (omega_s * Pa_avg)) * 1000  # ms
    except Exception:
        cct = 150.0
    return float(np.clip(cct, 40, 600))


def gen_stability_status(delta_arr: np.ndarray) -> str:
    max_d = float(np.max(np.abs(delta_arr)))
    if max_d > 130: return "unstable"
    if max_d > 100: return "marginal"
    return "stable"


# ── Network topology (6-bus, 8-branch) ────────────────────────────────────────

BUS_DATA = [
    {"id": 1, "name": "Gen Bus 1",  "type": "PV", "V": 1.02, "angle": 0.0,   "Pg": 320, "Qg":  80},
    {"id": 2, "name": "Gen Bus 2",  "type": "PV", "V": 1.01, "angle": -2.1,  "Pg": 280, "Qg":  60},
    {"id": 3, "name": "Swing Bus",  "type": "SW", "V": 1.05, "angle": 0.0,   "Pg": 250, "Qg": 100},
    {"id": 4, "name": "Load Bus 4", "type": "PQ", "V": 0.98, "angle": -5.4,  "Pd": 260, "Qd":  80},
    {"id": 5, "name": "Load Bus 5", "type": "PQ", "V": 0.97, "angle": -7.1,  "Pd": 300, "Qd":  90},
    {"id": 6, "name": "Load Bus 6", "type": "PQ", "V": 0.96, "angle": -8.3,  "Pd": 220, "Qd":  70},
]

BRANCH_DATA = [
    {"from": 1, "to": 2, "R": 0.010, "X": 0.085, "B": 0.176, "rating": 250},
    {"from": 1, "to": 4, "R": 0.017, "X": 0.092, "B": 0.158, "rating": 200},
    {"from": 2, "to": 3, "R": 0.012, "X": 0.100, "B": 0.209, "rating": 230},
    {"from": 2, "to": 5, "R": 0.008, "X": 0.072, "B": 0.149, "rating": 280},
    {"from": 3, "to": 5, "R": 0.006, "X": 0.062, "B": 0.132, "rating": 300},
    {"from": 3, "to": 6, "R": 0.014, "X": 0.110, "B": 0.221, "rating": 220},
    {"from": 4, "to": 5, "R": 0.021, "X": 0.115, "B": 0.195, "rating": 180},
    {"from": 5, "to": 6, "R": 0.018, "X": 0.096, "B": 0.180, "rating": 210},
]
