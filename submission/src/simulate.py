"""
Scenario Generator
==================
Creates six named fault scenarios for the transmission-line simulator.

Scenarios
---------
1. healthy_matched   : ZL = Z0  (no fault, reference)
2. wrong_load        : ZL = 2*Z0 (resistive mismatch)
3. open_circuit      : ZL = inf (large finite)
4. short_circuit     : ZL = 0+epsilon
5. series_L          : discontinuity Z = j*w*L inserted at position p
6. shunt_C           : discontinuity Y = j*w*C inserted at position p

For scenarios 5 and 6 the line is split:
  [input] -- segment A (0..p) -- [discontinuity] -- segment B (p..l) -- [ZL=Z0]
The ABCD matrices are cascaded: M_total = M_A * M_disc * M_B.

Ground-truth labels are stored in a separate dict; the classifier
(diagnose.py) receives ONLY S11 arrays, freqs, and Z0.
"""

import numpy as np
from .model import (abcd_tline, zin_from_abcd, gamma_from_z,
                    vswr_from_gamma, return_loss_db, sweep,
                    C_LIGHT, _LARGE_ZL, _GAMMA_FLOOR)

# ─────────────────────────────────────────────────────────────────────────────
# ABCD matrices for discontinuities
# ─────────────────────────────────────────────────────────────────────────────

def abcd_series_impedance(Z: complex) -> np.ndarray:
    """Series impedance: [1, Z; 0, 1]"""
    return np.array([[1.0, Z], [0.0, 1.0]], dtype=complex)


def abcd_shunt_admittance(Y: complex) -> np.ndarray:
    """Shunt admittance: [1, 0; Y, 1]"""
    return np.array([[1.0, 0.0], [Y, 1.0]], dtype=complex)


# ─────────────────────────────────────────────────────────────────────────────
# Cascaded sweep for discontinuity scenarios
# ─────────────────────────────────────────────────────────────────────────────

def sweep_with_discontinuity(Z0: float, ZL: complex,
                              total_length: float, fault_pos: float,
                              freqs: np.ndarray,
                              disc_abcd_fn,   # callable(f) -> 2x2 ndarray
                              VF: float = 1.0, alpha: float = 0.0,
                              noise_std: float = 0.0,
                              rng: np.random.Generator = None) -> dict:
    """
    Compute S11 for a line with a lumped discontinuity at fault_pos from input.

    ABCD cascade: M_A(0..p) * M_disc * M_B(p..l)
    Zin computed from total ABCD + ZL at load.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    freqs = np.asarray(freqs, dtype=float)
    N = len(freqs)
    Zin_arr = np.zeros(N, dtype=complex)
    GammaIn_arr = np.zeros(N, dtype=complex)
    VSWR_arr = np.zeros(N, dtype=float)
    RL_arr   = np.zeros(N, dtype=float)

    len_A = float(np.clip(fault_pos, 0.0, total_length))
    len_B = total_length - len_A

    Gamma_L = gamma_from_z(complex(ZL), Z0)

    for i, f in enumerate(freqs):
        M_A = abcd_tline(Z0, len_A, f, VF, alpha)
        M_d = disc_abcd_fn(f)
        M_B = abcd_tline(Z0, len_B, f, VF, alpha)
        M_total = M_A @ M_d @ M_B
        Zin = zin_from_abcd(M_total, ZL)
        Gin = gamma_from_z(Zin, Z0)
        Zin_arr[i]     = Zin
        GammaIn_arr[i] = Gin
        VSWR_arr[i]    = vswr_from_gamma(abs(Gin))
        RL_arr[i]      = return_loss_db(abs(Gin))

    S11 = GammaIn_arr.copy()
    if noise_std > 0.0:
        noise = rng.normal(0, noise_std / np.sqrt(2), N) \
              + 1j * rng.normal(0, noise_std / np.sqrt(2), N)
        S11 = S11 + noise
        mag = np.abs(S11)
        mask = mag > 1.0
        S11[mask] = S11[mask] / mag[mask]

    return {
        'freqs':    freqs,
        'Zin':      Zin_arr,
        'Gamma_in': GammaIn_arr,
        'Gamma_L':  Gamma_L,
        'VSWR':     VSWR_arr,
        'RL_dB':    RL_arr,
        'S11':      S11,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Named scenario builders
# ─────────────────────────────────────────────────────────────────────────────

SCENARIO_NAMES = [
    'healthy_matched',
    'wrong_load',
    'open_circuit',
    'short_circuit',
    'series_L',
    'shunt_C',
]


def build_scenario(name: str, Z0: float, length: float, freqs: np.ndarray,
                   VF: float = 1.0, alpha: float = 0.0,
                   fault_pos: float = None,
                   L_val: float = 10e-9,      # 10 nH
                   C_val: float = 10e-12,     # 10 pF
                   ZL_wrong: complex = None,
                   noise_std: float = 0.0,
                   rng: np.random.Generator = None) -> dict:
    """
    Build one named scenario and return sweep results + ground-truth label.

    Ground-truth label dict contains: name, ZL, fault_pos (if applicable).
    The caller MUST NOT pass ground-truth to the classifier.

    Parameters
    ----------
    name      : one of SCENARIO_NAMES
    Z0        : characteristic impedance [Ω]
    length    : total line length [m]
    freqs     : frequency array [Hz]
    VF        : velocity factor
    alpha     : attenuation [Np/m]
    fault_pos : position of fault from input [m] (None => length/2)
    L_val     : inductance for series_L scenario [H]
    C_val     : capacitance for shunt_C scenario [F]
    ZL_wrong  : load for wrong_load scenario (None => 2*Z0)
    noise_std : noise std on S11
    rng       : random generator

    Returns
    -------
    dict: {'results': sweep_dict, 'truth': ground_truth_dict}
    """
    if rng is None:
        rng = np.random.default_rng(42)
    if fault_pos is None:
        fault_pos = length / 2.0

    truth = {'scenario': name, 'Z0': Z0, 'length': length,
             'fault_pos': fault_pos, 'L_val': L_val, 'C_val': C_val}

    if name == 'healthy_matched':
        ZL = complex(Z0)
        truth['ZL'] = ZL
        res = sweep(Z0, ZL, length, freqs, VF, alpha, noise_std, rng)

    elif name == 'wrong_load':
        ZL = complex(ZL_wrong) if ZL_wrong is not None else complex(2.0 * Z0)
        truth['ZL'] = ZL
        res = sweep(Z0, ZL, length, freqs, VF, alpha, noise_std, rng)

    elif name == 'open_circuit':
        ZL = complex(_LARGE_ZL, 0.0)
        truth['ZL'] = ZL
        res = sweep(Z0, ZL, length, freqs, VF, alpha, noise_std, rng)

    elif name == 'short_circuit':
        ZL = complex(1e-6, 0.0)   # near-zero resistance
        truth['ZL'] = ZL
        res = sweep(Z0, ZL, length, freqs, VF, alpha, noise_std, rng)

    elif name == 'series_L':
        ZL = complex(Z0)          # matched load; fault is the discontinuity
        truth['ZL'] = ZL
        def disc_fn(f):
            Z_disc = 1j * 2.0 * np.pi * f * L_val
            return abcd_series_impedance(Z_disc)
        res = sweep_with_discontinuity(
            Z0, ZL, length, fault_pos, freqs, disc_fn, VF, alpha, noise_std, rng)

    elif name == 'shunt_C':
        ZL = complex(Z0)
        truth['ZL'] = ZL
        def disc_fn(f):
            Y_disc = 1j * 2.0 * np.pi * f * C_val
            return abcd_shunt_admittance(Y_disc)
        res = sweep_with_discontinuity(
            Z0, ZL, length, fault_pos, freqs, disc_fn, VF, alpha, noise_std, rng)

    else:
        raise ValueError(f"Unknown scenario: {name!r}. "
                         f"Choose from {SCENARIO_NAMES}")

    return {'results': res, 'truth': truth}


# ─────────────────────────────────────────────────────────────────────────────
# Batch builder for validation datasets
# ─────────────────────────────────────────────────────────────────────────────

def generate_dataset(Z0: float, length: float, freqs: np.ndarray,
                     VF: float = 1.0, alpha: float = 0.0,
                     n_per_class: int = 50,
                     noise_std: float = 0.0,
                     seed: int = 42) -> list:
    """
    Generate a randomised dataset with n_per_class examples per scenario.
    Parameters (ZL_wrong, fault_pos, L_val, C_val) are randomised within
    physically meaningful ranges.

    Returns list of dicts: [{'results':..., 'truth':...}, ...]
    """
    rng = np.random.default_rng(seed)
    dataset = []

    for name in SCENARIO_NAMES:
        for _ in range(n_per_class):
            # Randomise secondary parameters
            fp = rng.uniform(0.05 * length, 0.95 * length)
            L_v = rng.uniform(1e-9, 50e-9)
            C_v = rng.uniform(1e-12, 50e-12)
            ZL_w = complex(rng.uniform(1.5 * Z0, 4.0 * Z0))

            rec = build_scenario(
                name, Z0, length, freqs, VF, alpha,
                fault_pos=fp, L_val=L_v, C_val=C_v,
                ZL_wrong=ZL_w,
                noise_std=noise_std,
                rng=rng,
            )
            dataset.append(rec)

    return dataset

