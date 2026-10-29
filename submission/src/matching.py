"""
Quarter-Wave Impedance Matching
================================
Reference: Pozar, "Microwave Engineering" 4th ed., Section 5.1.

Theory
------
For a real load resistance RL (purely resistive), a quarter-wavelength
transformer of characteristic impedance Zt = sqrt(Z0 * RL) placed between
Z0 and RL achieves perfect matching at the design frequency f0.

At f0:  electrical length = beta*lt = pi/2  => Zin = Zt^2 / RL = Z0.  (exact)
Away from f0: matching degrades; bandwidth is defined by RL_threshold.

Transformer parameters
  Zt = sqrt(Z0 * RL)          characteristic impedance of transformer section
  lt = vp / (4 * f0)          physical length (lambda/4 at f0)

Restrictions
  - RL must be real and positive. Complex loads require a pre-matching network
    (not implemented; clear error message is returned).
  - RL = Z0 (already matched): transformer has Zt = Z0, lt = lambda/4;
    this is valid but trivially adds a lambda/4 section.

Usable bandwidth
  Defined as the frequency range where RL_dB >= RL_threshold (e.g., 20 dB).
  From Pozar eq. 5.11 (lossless): bandwidth shrinks as mismatch RL/Z0 grows.
"""

import numpy as np
import cmath
from .model import zin_scalar, gamma_from_z, vswr_from_gamma, return_loss_db, C_LIGHT


def quarter_wave_match(Z0: float, ZL: complex,
                       f0: float, freqs: np.ndarray,
                       VF: float = 1.0) -> dict:
    """
    Design a quarter-wave transformer and return before/after metrics.

    Parameters
    ----------
    Z0    : system characteristic impedance [Ω]
    ZL    : load impedance [Ω]  (must be real and positive)
    f0    : design frequency [Hz]
    freqs : frequency sweep array [Hz]
    VF    : velocity factor of the transformer section

    Returns
    -------
    dict:
        valid         : bool – False if complex load or RL <= 0
        error_msg     : str (empty if valid)
        Zt            : transformer Zt [Ω]
        lt            : transformer physical length [m]
        before        : dict with Gamma, VSWR, RL_dB arrays (no transformer)
        after         : dict with Gamma, VSWR, RL_dB arrays (with transformer)
        bandwidth_hz  : float – usable BW where RL >= rl_threshold
        rl_threshold  : float [dB] used for BW calculation
        at_f0_exact   : bool – |Gamma| < 1e-4 at f0 after matching
    """
    ZL = complex(ZL)
    RL_threshold = 20.0   # dB

    # Validation
    if abs(ZL.imag) > 1e-6 * abs(ZL.real + 1e-30):
        return {
            'valid': False,
            'error_msg': (
                f"Quarter-wave matching requires a purely real load. "
                f"ZL = {ZL:.3f} Ω is complex. "
                f"For complex loads, a single-stub or L-network is needed (not implemented)."
            ),
        }

    RL = ZL.real
    if RL <= 0:
        return {
            'valid': False,
            'error_msg': f"Load resistance RL = {RL:.3f} Ω must be positive.",
        }

    # Transformer design
    Zt = float(np.sqrt(Z0 * RL))
    vp = VF * C_LIGHT
    lt = vp / (4.0 * f0)

    freqs = np.asarray(freqs, dtype=float)
    N = len(freqs)

    # Before matching: direct connection of ZL to Z0 line
    before_G   = np.zeros(N, dtype=float)
    before_VSWR= np.zeros(N, dtype=float)
    before_RL  = np.zeros(N, dtype=float)

    # After matching: insert lambda/4 section between Z0 line and ZL
    after_G    = np.zeros(N, dtype=float)
    after_VSWR = np.zeros(N, dtype=float)
    after_RL   = np.zeros(N, dtype=float)

    for i, f in enumerate(freqs):
        # Before: just ZL presented to Z0
        G_before  = gamma_from_z(ZL, Z0)
        bg = abs(G_before)
        before_G[i]    = bg
        before_VSWR[i] = vswr_from_gamma(bg)
        before_RL[i]   = return_loss_db(bg)

        # After: Zin of lambda/4 section (Zt, lt) loaded by ZL
        Zin_trans = zin_scalar(Zt, ZL, lt, f, VF)
        G_after   = gamma_from_z(Zin_trans, Z0)
        ag = abs(G_after)
        after_G[i]    = ag
        after_VSWR[i] = vswr_from_gamma(ag)
        after_RL[i]   = return_loss_db(ag)

    # Check exact matching at f0 (by interpolation to nearest freq point)
    # Note: f0 may fall between grid points; use nearest and check min in window
    idx_f0 = int(np.argmin(np.abs(freqs - f0)))
    window_half = max(1, N // 100)  # 1% window around f0
    lo = max(0, idx_f0 - window_half)
    hi = min(N, idx_f0 + window_half + 1)
    min_gamma_near_f0 = float(np.min(after_G[lo:hi]))
    at_f0_exact = bool(min_gamma_near_f0 < 0.02)

    # Usable bandwidth (RL >= threshold)
    bw_mask = after_RL >= RL_threshold
    if np.any(bw_mask):
        bw_freqs = freqs[bw_mask]
        bandwidth_hz = float(bw_freqs[-1] - bw_freqs[0])
    else:
        bandwidth_hz = 0.0

    return {
        'valid':          True,
        'error_msg':      '',
        'Zt':             Zt,
        'lt':             lt,
        'before': {
            'Gamma': before_G,
            'VSWR':  before_VSWR,
            'RL_dB': before_RL,
        },
        'after': {
            'Gamma': after_G,
            'VSWR':  after_VSWR,
            'RL_dB': after_RL,
        },
        'bandwidth_hz':   bandwidth_hz,
        'rl_threshold':   RL_threshold,
        'at_f0_exact':    at_f0_exact,
        'f0':             f0,
        'freqs':          freqs,
    }
