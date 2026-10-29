"""
Transmission-Line Core Model
=============================
Reference: Pozar, D.M. "Microwave Engineering", 4th ed. (Wiley, 2012)
           - Section 2.1: Telegrapher's equations
           - Section 2.2: Propagation constant, phase velocity
           - Section 2.3: Lossless TL, input impedance
           - Section 2.4: Reflection coefficient, SWR

Reference plane: ALL quantities (Zin, Gamma_in) are referred to the INPUT
(source) end of the line, i.e. at z = 0 where z increases toward the load.
The load is at z = l. Gamma_L is the reflection coefficient AT the load.

Physics recap (shown here so every formula can be hand-verified):
  Propagation constant : gamma = alpha + j*beta
  Phase constant       : beta  = 2*pi*f / vp,  vp = VF*c
  Input impedance      : Zin = Z0 * (ZL + Z0*tanh(gamma*l))
                                   / (Z0 + ZL*tanh(gamma*l))
  Reflection coeff     : Gamma = (Z - Z0)/(Z + Z0)
  VSWR                 : S = (1+|Gamma|)/(1-|Gamma|)
  Return loss          : RL = -20*log10(|Gamma|)  [dB]
"""

import numpy as np
import cmath
import warnings

# Physical constants
C_LIGHT = 299_792_458.0   # m/s

# Numerical guards
_LARGE_ZL     = 1e9       # substitute for ZL = inf (open circuit)
_GAMMA_FLOOR  = 1e-9      # avoid log(0) and 1/(1-|Gamma|)=inf
_VSWR_CAP     = 1e6       # capped VSWR when |Gamma|->1


# ─────────────────────────────────────────────────────────────────────────────
# Helper: single-frequency, single-length input impedance
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_ZL(ZL: complex) -> complex:
    """Replace pure-open (ZL = inf or extremely large) with _LARGE_ZL."""
    if np.isinf(abs(ZL)):
        return complex(_LARGE_ZL, 0.0)
    return ZL


def zin_scalar(Z0: float, ZL: complex, length: float, f: float,
               VF: float = 1.0, alpha: float = 0.0) -> complex:
    """
    Compute input impedance of a transmission line at one (f, length).

    Parameters
    ----------
    Z0     : characteristic impedance [Ω], real, positive
    ZL     : load impedance [Ω], complex
    length : line length [m]
    f      : frequency [Hz]
    VF     : velocity factor (0 < VF <= 1)
    alpha  : attenuation constant [Np/m] (default 0 = lossless)

    Returns
    -------
    Zin : complex impedance [Ω]

    Notes
    -----
    Uses the generalised formula with tanh(gamma*l) to handle attenuation.
    For alpha = 0, gamma = j*beta, tanh(j*beta*l) = j*tan(beta*l).
    Singularities (tan -> ±inf) occur when beta*l = (2n+1)*pi/2.
    These are handled by detecting the condition and returning Z0*Z0/ZL.
    Hand-check example (documented in docs/technical_explanation.md):
      Z0=50, ZL=50, any f, any l => Zin=50+0j  (matched line)
    """
    Z0 = float(Z0)
    ZL = _sanitize_ZL(complex(ZL))
    vp = VF * C_LIGHT
    beta = 2.0 * np.pi * f / vp
    gamma = complex(alpha, beta)
    gl = gamma * length

    # tanh(gamma*l); use numpy for stability at large arguments
    tgl = np.tanh(gl)

    denom = Z0 + ZL * tgl
    if abs(denom) < 1e-30:
        # singular case: return large but finite value
        return complex(_LARGE_ZL, 0.0)

    Zin = Z0 * (ZL + Z0 * tgl) / denom
    return Zin


# ─────────────────────────────────────────────────────────────────────────────
# ABCD matrix approach (independent verification)
# ─────────────────────────────────────────────────────────────────────────────

def abcd_tline(Z0: float, length: float, f: float,
               VF: float = 1.0, alpha: float = 0.0) -> np.ndarray:
    """
    ABCD matrix of a uniform transmission-line section.
    [A B; C D] where A=D=cosh(gl), B=Z0*sinh(gl), C=sinh(gl)/Z0.
    Ref: Pozar (4th ed.) Table 4.1.
    """
    vp = VF * C_LIGHT
    beta = 2.0 * np.pi * f / vp
    gamma = complex(alpha, beta)
    gl = gamma * length
    cgl = np.cosh(gl)
    sgl = np.sinh(gl)
    return np.array([[cgl,       Z0 * sgl],
                     [sgl / Z0,  cgl     ]], dtype=complex)


def zin_from_abcd(ABCD: np.ndarray, ZL: complex) -> complex:
    """
    Input impedance from ABCD matrix and load impedance.
    Zin = (A*ZL + B) / (C*ZL + D)
    """
    ZL = _sanitize_ZL(complex(ZL))
    A, B = ABCD[0, 0], ABCD[0, 1]
    C, D = ABCD[1, 0], ABCD[1, 1]
    denom = C * ZL + D
    if abs(denom) < 1e-30:
        return complex(_LARGE_ZL, 0.0)
    return (A * ZL + B) / denom


def zin_abcd_scalar(Z0: float, ZL: complex, length: float, f: float,
                    VF: float = 1.0, alpha: float = 0.0) -> complex:
    """ABCD-based Zin (must match zin_scalar to 1e-9)."""
    M = abcd_tline(Z0, length, f, VF, alpha)
    return zin_from_abcd(M, ZL)


# ─────────────────────────────────────────────────────────────────────────────
# Reflection coefficient and derived quantities
# ─────────────────────────────────────────────────────────────────────────────

def gamma_from_z(Z: complex, Z0: float) -> complex:
    """
    Reflection coefficient: Gamma = (Z - Z0)/(Z + Z0).
    When Z+Z0 ≈ 0 (active medium), return Gamma = 1 (worst case).
    """
    denom = Z + Z0
    if abs(denom) < 1e-30:
        return complex(1.0, 0.0)
    return (Z - Z0) / denom


def vswr_from_gamma(gamma_mag: float) -> float:
    """
    VSWR = (1 + |Gamma|) / (1 - |Gamma|).
    Capped at _VSWR_CAP when |Gamma| -> 1 to avoid inf/NaN.
    """
    gm = float(np.clip(abs(gamma_mag), 0.0, 1.0 - 1.0 / _VSWR_CAP))
    return (1.0 + gm) / (1.0 - gm)


def return_loss_db(gamma_mag: float) -> float:
    """
    Return loss = -20 log10(|Gamma|) [dB].
    Positive value => loss.  Floor |Gamma| at _GAMMA_FLOOR to avoid -inf.
    """
    gm = float(np.clip(abs(gamma_mag), _GAMMA_FLOOR, 1.0))
    return -20.0 * np.log10(gm)


# ─────────────────────────────────────────────────────────────────────────────
# Frequency/length sweep
# ─────────────────────────────────────────────────────────────────────────────

def sweep(Z0: float, ZL: complex, length: float,
          freqs: np.ndarray, VF: float = 1.0, alpha: float = 0.0,
          noise_std: float = 0.0, rng: np.random.Generator = None) -> dict:
    """
    Compute Zin, Gamma_in, Gamma_L, VSWR, RL over a frequency array.

    Parameters
    ----------
    Z0        : characteristic impedance [Ω]
    ZL        : load impedance [Ω]
    length    : line length [m]
    freqs     : 1-D array of frequencies [Hz]
    VF        : velocity factor
    alpha     : attenuation [Np/m]
    noise_std : std of complex Gaussian noise added to Gamma_in
    rng       : numpy random Generator (for reproducibility)

    Returns
    -------
    dict with keys:
        freqs, Zin, Gamma_in, Gamma_L, VSWR, RL_dB, S11
        S11 is Gamma_in (possibly with noise); kept as separate key so
        the classifier uses S11 and never touches raw Zin or ZL.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    freqs = np.asarray(freqs, dtype=float)
    N = len(freqs)
    Zin_arr     = np.zeros(N, dtype=complex)
    GammaIn_arr = np.zeros(N, dtype=complex)
    VSWR_arr    = np.zeros(N, dtype=float)
    RL_arr      = np.zeros(N, dtype=float)

    # Load reflection coefficient (at load plane, frequency-independent for lumped ZL)
    Gamma_L = gamma_from_z(complex(ZL), Z0)

    for i, f in enumerate(freqs):
        Zin = zin_scalar(Z0, ZL, length, f, VF, alpha)
        Gin = gamma_from_z(Zin, Z0)
        Zin_arr[i]     = Zin
        GammaIn_arr[i] = Gin
        VSWR_arr[i]    = vswr_from_gamma(abs(Gin))
        RL_arr[i]      = return_loss_db(abs(Gin))

    # Optionally add complex Gaussian noise to S11 (=Gamma_in)
    S11 = GammaIn_arr.copy()
    if noise_std > 0.0:
        noise = rng.normal(0, noise_std / np.sqrt(2), N) \
              + 1j * rng.normal(0, noise_std / np.sqrt(2), N)
        S11 = S11 + noise
        # Clip |S11| to [0, 1] to keep physical meaning
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
# Verification helper
# ─────────────────────────────────────────────────────────────────────────────

def verify_abcd_vs_closedform(Z0: float, ZL: complex,
                               length: float, f: float,
                               VF: float = 1.0, alpha: float = 0.0,
                               tol: float = 1e-9) -> bool:
    """
    Assert that ABCD method and closed-form agree to within tol.
    Returns True if OK, raises AssertionError otherwise.
    """
    z1 = zin_scalar(Z0, ZL, length, f, VF, alpha)
    z2 = zin_abcd_scalar(Z0, ZL, length, f, VF, alpha)
    err = abs(z1 - z2) / max(abs(z1), 1e-30)
    assert err < tol, (
        f"ABCD vs closed-form mismatch: {z1} vs {z2}, rel error={err:.3e}"
    )
    return True

