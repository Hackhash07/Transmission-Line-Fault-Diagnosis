# Technical Explanation
## Transmission-Line Fault Diagnosis and Impedance Matching

### Reference
Pozar, D.M. *Microwave Engineering*, 4th ed., Wiley, 2012.  
All section references below are to Pozar unless otherwise noted.

---

## 1. Transmission-Line Theory (§2.1–2.3)

A uniform transmission line is characterised by its distributed parameters:
resistance R, inductance L, conductance G, capacitance C (per unit length).
For a lossless line, R = G = 0.

The **propagation constant** is:

$$
\gamma = \alpha + j\beta, \quad
\beta = \frac{2\pi f}{v_p}, \quad
v_p = \text{VF} \cdot c
$$

where c = 299 792 458 m/s and VF is the velocity factor (0 < VF ≤ 1).

### 1.1 Input Impedance

For a line of length l, characteristic impedance Z₀, load impedance ZL:

$$
Z_{\text{in}} = Z_0 \frac{Z_L + Z_0 \tanh(\gamma l)}{Z_0 + Z_L \tanh(\gamma l)}
$$

For a lossless line (α = 0), tanh(jβl) = j tan(βl):

$$
Z_{\text{in}} = Z_0 \frac{Z_L + jZ_0 \tan(\beta l)}{Z_0 + jZ_L \tan(\beta l)}
$$

**Hand check 1 – Matched load (ZL = Z0):**
Numerator = Z0 + jZ0 tan(βl) = Z0 (1 + j tan)
Denominator = Z0 + jZ0 tan(βl) = Z0 (1 + j tan)
Ratio = 1 → Zin = Z0 for all f, l. ✓

**Hand check 2 – Open circuit, quarter-wave (ZL → ∞, βl = π/2):**
Dividing numerator and denominator by ZL:
Zin → Z0 · (1 + jZ0/ZL · tan) / (Z0/ZL + j tan) → Z0 · 0 / (j·∞) = 0 (short at input). ✓

**Hand check 3 – Short circuit, half-wave (ZL = 0, βl = π):**
Zin = Z0 · (0 + jZ0 tan π) / (Z0 + 0) = 0 (tan π = 0). ✓

### 1.2 ABCD Matrix

The ABCD matrix of a uniform TL section (Pozar Table 4.1):

$$
\begin{bmatrix} A & B \\ C & D \end{bmatrix} =
\begin{bmatrix} \cosh(\gamma l) & Z_0 \sinh(\gamma l) \\ \sinh(\gamma l)/Z_0 & \cosh(\gamma l) \end{bmatrix}
$$

Input impedance from ABCD:

$$
Z_{\text{in}} = \frac{A Z_L + B}{C Z_L + D}
$$

This formula is identical to the closed form above. The code verifies agreement to relative error < 1×10⁻⁹.

---

## 2. Reflection Coefficient and Derived Quantities (§2.3)

**Reference plane:** All quantities are referred to the **input port** (z = 0).

$$
\Gamma = \frac{Z - Z_0}{Z + Z_0}
$$

- Γ_L is the reflection coefficient at the load (z = l).
- Γ_in is the reflection coefficient at the input (z = 0).

For a lossless line: Γ_in = Γ_L · e^{−2jβl}.

$$
\text{VSWR} = \frac{1 + |\Gamma|}{1 - |\Gamma|} \quad [\text{capped at } 10^6]
$$

$$
\text{RL} = -20 \log_{10} |\Gamma| \quad [\text{dB, floor at } |\Gamma| = 10^{-9}]
$$

**Hand check 4 – ZL=100 Ω, Z0=50 Ω:**
Γ = (100−50)/(100+50) = 50/150 = 1/3 ≈ 0.333
VSWR = (1 + 1/3)/(1 − 1/3) = (4/3)/(2/3) = 2.0
RL = −20 log₁₀(1/3) = 20 log₁₀(3) ≈ **9.54 dB** ✓

---

## 3. Fault Scenarios

| Scenario | ZL or Discontinuity | Expected |Γ|| Frequency Trend |
|---|---|---|---|
| healthy_matched | ZL = Z0 | ≈ 0 | Flat (near zero) |
| wrong_load | ZL = 2Z0 | 0.33 | Flat (moderate) |
| open_circuit | ZL → ∞ | ≈ 1 | Oscillating |
| short_circuit | ZL → 0 | ≈ 1 | Oscillating |
| series_L | jωL (ABCD cascade) | Rising | Rises with f |
| shunt_C | jωC (ABCD cascade) | Falling | Falls with f |

For series-L and shunt-C, the line is split at the fault position, and ABCD matrices are cascaded: M_total = M_A · M_disc · M_B.

---

## 4. Fault Diagnosis (Rule-Based)

The classifier receives **only S11, freqs, Z0** – no ZL, no fault_pos, no truth label.

Feature extraction:
- **mag_mean**: mean |S11| over all frequencies
- **trend**: mean(|S11| at high freqs) − mean(|S11| at low freqs)
- **phase_mean**: mean of unwrapped phase

Rules (in order, first match wins):
1. mag_mean < 0.05 → **healthy_matched**
2. mag_mean > 0.85 AND std < 0.05 → open or short (distinguished by phase)
3. mag_mean > 0.7 AND trend < −0.1 → **open_circuit**
4. mag_mean > 0.7 AND trend > +0.1 → **short_circuit**
5. trend > 0.08 AND std > 0.04 → **series_L**
6. trend < −0.08 AND std > 0.04 → **shunt_C**
7. 0.05 ≤ mag_mean ≤ 0.5 AND std < 0.08 → **wrong_load**
8. else → **uncertain**

Known failures: small L/C, overlapping signatures, high noise.

---

## 5. Fault Location (TDR via IFFT)

**Method 1 (Primary):**
1. Apply Hann window to S11(f): reduces spectral leakage.
2. Zero-pad by factor 8 for time resolution.
3. IFFT → pseudo-time domain.
4. Find peak after the DC region (skip first 1% of samples).
5. d = v_p · t_peak / 2 (round-trip factor of 2).

Range resolution: Δd = v_p / (2B), where B = f_max − f_min.
Unambiguous range: d_max = v_p / (2·Δf).

**Method 2 (Cross-check):**
Unwrapped phase slope: d = −(v_p / 4π) · (dφ/df).
This is biased for L/C discontinuities (the discontinuity adds its own phase shift).

---

## 6. Quarter-Wave Matching (§5.1)

For a real load resistance R_L:

$$
Z_t = \sqrt{Z_0 R_L}, \quad l_t = \frac{v_p}{4 f_0}
$$

At f₀: βl_t = π/2, Z_in = Z_t²/R_L = Z0·R_L/R_L = Z0. Perfect match.

Usable bandwidth: defined as frequencies where RL ≥ 20 dB.
From Pozar §5.1, bandwidth decreases as the mismatch ratio R_L/Z0 increases.

**Restriction:** Complex loads cannot be matched with a single quarter-wave section. The code returns a clear error message and does not attempt to proceed.

---

## 7. Numerical Safeguards

| Singularity | Guard |
|---|---|
| ZL = ∞ (open) | Replaced by ZL = 10⁹ Ω |
| ZL ≈ 0 (short) | ZL = 10⁻⁶ Ω |
| tan(βl) → ±∞ | Handled by tanh formulation; denominator check |
| |Γ| → 1 | VSWR capped at 10⁶; RL floor at 10⁻⁹ |
| ABCD denom → 0 | Return 10⁹ Ω |

