"""
Fault Location Module
=====================
Estimates the distance to a fault using two methods:

Method 1 (Primary): Windowed IFFT of S11(f) -> time domain -> peak detection
  - Apply a Hann window to reduce spectral leakage.
  - Compute IFFT to get impulse response in pseudo-time.
  - Locate the dominant peak (ignoring DC = direct coupling at t=0).
  - Convert: distance d = vp * t_peak / 2  (round-trip factor of 2).
  - Range resolution : dr = vp / (2*B),  B = f_max - f_min
  - Unambiguous range: d_max = vp / (2*df), df = f[1]-f[0]

Method 2 (Cross-check): Unwrapped phase slope of S11
  - phi(f) = -4*pi*f*d/vp + const  (for a simple reflector)
  - Slope  = d(phi)/d(f) = -4*pi*d/vp
  - => d = -(vp/(4*pi)) * (d_phi/d_f)
  - BIAS: This formula assumes a pure reflection; for L/C faults the
    phase slope also includes the discontinuity's own phase contribution.
    It is therefore less reliable for series_L and shunt_C.

Reliability checks
  - Bandwidth < 10*dr  => estimate flagged as 'uncertain'
  - Peak ambiguous (two peaks within 3 dB of each other) => 'uncertain'
  - Noise standard deviation > 0.1 => add 'low_snr' to warnings

Reference: Pozar, §2.1, §2.4; TDR method described in HP Application Note 1304-2.
"""

import numpy as np

C_LIGHT = 299_792_458.0


def locate_fault(S11: np.ndarray, freqs: np.ndarray,
                 VF: float = 1.0,
                 noise_std: float = 0.0) -> dict:
    """
    Estimate fault distance from S11 sweep.

    Parameters
    ----------
    S11       : complex S11 array, shape (N,)
    freqs     : frequency array [Hz], must be uniformly spaced
    VF        : velocity factor
    noise_std : estimated noise level (used only for reliability flag)

    Returns
    -------
    dict:
        method1_dist   : float [m]   (IFFT method, primary)
        method2_dist   : float [m]   (phase slope, cross-check)
        range_res      : float [m]   (range resolution)
        unambig_range  : float [m]   (unambiguous range)
        reliable       : bool
        warnings       : list of str
        t_axis         : array       (time axis of IFFT response)
        ifft_mag       : array       (|IFFT(S11)|)
        peak_idx       : int         (index of dominant peak)
    """
    freqs = np.asarray(freqs, dtype=float)
    S11   = np.asarray(S11,   dtype=complex)
    N = len(freqs)
    vp = VF * C_LIGHT
    warnings = []

    # Frequency spacing (assume uniform)
    if N > 1:
        df = (freqs[-1] - freqs[0]) / (N - 1)
        B  = freqs[-1] - freqs[0]
    else:
        return _uncertain(warnings, note="Need at least 2 frequency points")

    if B < 1e3:
        return _uncertain(warnings, note="Bandwidth too small (<1 kHz)")

    # Range resolution and unambiguous range
    range_res     = vp / (2.0 * B)
    unambig_range = vp / (2.0 * df) if df > 0 else float('inf')

    # ── Method 1: IFFT ───────────────────────────────────────────────────
    window = np.hanning(N)
    S11_win = S11 * window

    # Zero-pad for better time resolution (factor 8)
    Npad = max(N * 8, 2048)
    S11_pad = np.zeros(Npad, dtype=complex)
    S11_pad[:N] = S11_win

    ifft_raw = np.fft.ifft(S11_pad)
    ifft_mag = np.abs(ifft_raw)

    # Build time axis (assuming freqs start at freqs[0], df spacing)
    # Physical time corresponding to index k: t_k = k/(Npad*df)
    t_axis = np.arange(Npad) / (Npad * df)

    # Ignore DC / direct coupling at bin 0 and 1
    skip = 2
    search_mag = ifft_mag.copy()
    search_mag[:skip] = 0.0
    # Only look in causal half
    search_mag[Npad // 2:] = 0.0

    peak_idx = int(np.argmax(search_mag))
    t_peak = t_axis[peak_idx]
    d1 = vp * t_peak / 2.0

    # Check peak ambiguity (any other peak within 3 dB = factor 0.707)
    peak_val = ifft_mag[peak_idx]
    threshold_3dB = peak_val * (10.0 ** (-3.0 / 20.0))
    other = search_mag.copy()
    # zero out region around main peak (±5 samples)
    lo = max(0, peak_idx - 5)
    hi = min(Npad // 2, peak_idx + 5)
    other[lo:hi] = 0.0
    if np.any(other > threshold_3dB):
        warnings.append("Peak ambiguity: multiple peaks within 3 dB")

    if noise_std > 0.1:
        warnings.append(f"Low SNR (noise_std={noise_std:.2f}): location less reliable")

    if B < 10.0 * range_res:
        warnings.append("Bandwidth provides fewer than 10 resolution cells")

    # ── Method 2: Phase slope ─────────────────────────────────────────────
    phase = np.unwrap(np.angle(S11))
    if N > 1:
        pfit = np.polyfit(freqs, phase, 1)
        slope = pfit[0]           # rad/Hz
        d2 = -(vp / (4.0 * np.pi)) * slope
        warnings.append(
            "Method 2 (phase slope) is biased for L/C discontinuities; "
            "use Method 1 as primary."
        )
    else:
        d2 = float('nan')

    reliable = len([w for w in warnings
                    if 'ambiguity' in w or 'Bandwidth too small' in w]) == 0

    return {
        'method1_dist':   d1,
        'method2_dist':   d2,
        'range_res':      range_res,
        'unambig_range':  unambig_range,
        'reliable':       reliable,
        'warnings':       warnings,
        't_axis':         t_axis,
        'ifft_mag':       ifft_mag,
        'peak_idx':       peak_idx,
    }


def _uncertain(warnings: list, note: str = "") -> dict:
    if note:
        warnings.append(note)
    return {
        'method1_dist':  float('nan'),
        'method2_dist':  float('nan'),
        'range_res':     float('nan'),
        'unambig_range': float('nan'),
        'reliable':      False,
        'warnings':      warnings,
        't_axis':        np.array([]),
        'ifft_mag':      np.array([]),
        'peak_idx':      -1,
    }

