"""
Fault Diagnosis Module
======================
Rule-based classifier using S11 features only.

IMPORTANT CONTRACT
------------------
The classifier is given:
  - S11   : complex array of shape (N,)  [Gamma_in with optional noise]
  - freqs : real array of shape (N,)     [Hz]
  - Z0    : float [Ω]

It MUST NOT receive Zin, ZL, fault_pos, or any ground-truth label.
A unit test in tests/test_model.py asserts this interface contract.

Rule Documentation
------------------
All thresholds and rationale are stated explicitly here so they can be
audited and revised.

Feature extraction:
  - mag_mean        : mean(|S11|) over all freqs
  - mag_std         : std(|S11|)
  - mag_low         : mean(|S11| at lowest 25% of freqs)
  - mag_high        : mean(|S11| at highest 25% of freqs)
  - trend           : mag_high - mag_low (positive => rising with freq)
  - phase_mean      : mean of unwrapped phase
  - phase_first     : raw angle of S11 at lowest frequency
  - phase_slope     : linear slope of unwrapped phase vs freq
  - deembedded_real : real part of reflection coefficient de-embedded to fault
  - deembedded_imag : imag part of reflection coefficient de-embedded to fault

Decision tree (checked in order):
  R1: mag_mean < THR_MATCH (0.05)
      => healthy_matched (nearly zero reflection)
  R2: Reactive Discontinuity (trend > 0.005 or mag_std > 0.035)
      Both series-L and shunt-C show reflection magnitude rising with frequency.
      Disambiguation via de-embedded reflection plane:
      - deembedded_imag >= 0: series_L (inductive reactance in upper half-plane)
      - deembedded_imag < 0 : shunt_C (capacitive admittance in lower half-plane)
  R3: 0.05 <= mag_mean < 0.70 and flat trend
      => wrong_load (steady resistive mismatch)
  R4: mag_mean >= 0.70 (near-total reflection)
      - deembedded_real >= 0: open_circuit (Gamma_L ≈ +1)
      - deembedded_real < 0 : short_circuit (Gamma_L ≈ -1)
  R5: Otherwise
      => uncertain

Known failure cases:
  - Very small L or C values produce near-zero reflection, resembling healthy_matched.
  - Very large C values (> 30 pF) act as an RF short circuit across the line,
    showing near-flat |Gamma| ≈ 1.0 which can be classified as short_circuit.
  - High noise levels (noise_std > 0.2) obscure small trends.
"""

import numpy as np

# Thresholds (calibrated on calibration set; see validation_experiment.py)
THR_MATCH   = 0.05   # |Gamma| mean below which line is considered matched
THR_HIGH    = 0.70   # |Gamma| mean above which reflection is near total
THR_TREND   = 0.005  # minimum frequency trend indicating reactive fault


def extract_features(S11: np.ndarray, freqs: np.ndarray) -> dict:
    """
    Extract scalar features from the S11 sweep.

    Parameters
    ----------
    S11   : complex array, shape (N,)
    freqs : real array, shape (N,)

    Returns
    -------
    dict of named scalar features
    """
    mag = np.abs(S11)
    N = len(mag)
    quarter = max(1, N // 4)

    mag_mean  = float(np.mean(mag))
    mag_std   = float(np.std(mag))
    mag_low   = float(np.mean(mag[:quarter]))
    mag_high  = float(np.mean(mag[-quarter:]))
    trend     = mag_high - mag_low

    phase = np.unwrap(np.angle(S11))
    phase_mean = float(np.mean(phase))
    phase_var  = float(np.var(phase))
    phase_first = float(np.angle(S11[0])) if N > 0 else 0.0

    if len(freqs) > 1:
        pfit = np.polyfit(freqs, phase, 1)
        phase_slope = float(pfit[0])   # rad/Hz
    else:
        phase_slope = 0.0

    # Estimate distance via IFFT peak for de-embedding
    if N > 1:
        df = (freqs[-1] - freqs[0]) / (N - 1)
        window = np.hanning(N)
        Npad = max(N * 8, 2048)
        S11_pad = np.zeros(Npad, dtype=complex)
        S11_pad[:N] = S11 * window
        ifft_mag = np.abs(np.fft.ifft(S11_pad))
        t_axis = np.arange(Npad) / (Npad * df)
        search_mag = ifft_mag.copy()
        search_mag[0:2] = 0.0
        search_mag[Npad // 2:] = 0.0
        pidx = int(np.argmax(search_mag))
        vp_nominal = 3e8 * 0.66
        d_est = vp_nominal * t_axis[pidx] / 2.0

        beta = 2.0 * np.pi * freqs / vp_nominal
        gamma_disc = S11 * np.exp(2j * beta * d_est)
        deembedded_real = float(np.mean(gamma_disc.real))
        deembedded_imag = float(np.mean(gamma_disc.imag))
    else:
        deembedded_real = float(S11[0].real) if N > 0 else 0.0
        deembedded_imag = float(S11[0].imag) if N > 0 else 0.0

    return {
        'mag_mean':        mag_mean,
        'mag_std':         mag_std,
        'mag_low':         mag_low,
        'mag_high':        mag_high,
        'trend':           trend,
        'phase_mean':      phase_mean,
        'phase_first':     phase_first,
        'phase_var':       phase_var,
        'phase_slope':     phase_slope,
        'deembedded_real': deembedded_real,
        'deembedded_imag': deembedded_imag,
    }


def diagnose(S11: np.ndarray, freqs: np.ndarray, Z0: float) -> dict:
    """
    Classify transmission-line fault using S11 features only.

    Parameters
    ----------
    S11   : complex S11 array (no Zin, no ZL, no ground truth)
    freqs : frequency array [Hz]
    Z0    : characteristic impedance [Ω]

    Returns
    -------
    dict:
        diagnosis  : one of SCENARIO_NAMES + ['uncertain']
        confidence : 'high' | 'medium' | 'low'
        features   : dict of extracted features
        rules_fired: list of rule labels that matched
        notes      : list of human-readable notes
    """
    assert isinstance(S11, np.ndarray),  "S11 must be a numpy array"
    assert isinstance(freqs, np.ndarray),"freqs must be a numpy array"
    assert S11.shape == freqs.shape,     "S11 and freqs must have same length"

    feat = extract_features(S11, freqs)
    rules_fired = []
    notes = []

    mm = feat['mag_mean']
    ms = feat['mag_std']
    tr = feat['trend']
    de_re = feat['deembedded_real']
    de_im = feat['deembedded_imag']

    # ── R1: Matched line ──────────────────────────────────────────────────
    if mm < THR_MATCH:
        rules_fired.append('R1')
        notes.append(f"|Gamma| mean={mm:.3f} < {THR_MATCH} => matched")
        return _result('healthy_matched', 'high', feat, rules_fired, notes)

    # ── R2: Reactive Discontinuity (Series L or Shunt C) ─────────────────
    if tr > THR_TREND or ms > 0.035:
        if de_im >= 0:
            rules_fired.append('R5')
            notes.append(f"Rising trend ({tr:.3f}) with inductive phase (Im={de_im:+.2f}) => series_L")
            return _result('series_L', 'medium' if mm > 0.2 else 'low', feat, rules_fired, notes)
        else:
            rules_fired.append('R6')
            notes.append(f"Rising trend ({tr:.3f}) with capacitive phase (Im={de_im:+.2f}) => shunt_C")
            return _result('shunt_C', 'medium' if mm > 0.2 else 'low', feat, rules_fired, notes)

    # ── R3: Wrong Load (Resistive Mismatch) ───────────────────────────────
    if THR_MATCH <= mm < THR_HIGH:
        rules_fired.append('R7')
        notes.append(f"Flat moderate |Gamma| mean={mm:.3f} => wrong_load")
        return _result('wrong_load', 'high' if ms < 0.04 else 'medium', feat, rules_fired, notes)

    # ── R4: Total Reflection (Open vs Short) ──────────────────────────────
    if mm >= THR_HIGH:
        if de_re >= 0:
            rules_fired.append('R2a')
            notes.append(f"High reflection (|Gamma|={mm:.2f}) with positive real reflection => open_circuit")
            return _result('open_circuit', 'high' if ms < 0.04 else 'medium', feat, rules_fired, notes)
        else:
            rules_fired.append('R2b')
            notes.append(f"High reflection (|Gamma|={mm:.2f}) with negative real reflection => short_circuit")
            return _result('short_circuit', 'high' if ms < 0.04 else 'medium', feat, rules_fired, notes)

    # ── Default: Uncertain ────────────────────────────────────────────────
    rules_fired.append('R8')
    notes.append("No clear rule matched; features ambiguous")
    return _result('uncertain', 'low', feat, rules_fired, notes)


def _result(label: str, confidence: str, feat: dict,
            rules: list, notes: list) -> dict:
    return {
        'diagnosis':   label,
        'confidence':  confidence,
        'features':    feat,
        'rules_fired': list(rules),
        'notes':       list(notes),
    }
