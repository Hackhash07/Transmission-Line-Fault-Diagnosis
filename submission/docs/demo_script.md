# Demo Script – 5-Minute Timed Narration

**Project:** Transmission-Line Fault Diagnosis and Impedance Matching  
**Duration:** 5 minutes (300 seconds)  
**Presenter:** [Member 5 leads; others support]  
**Note:** All outputs shown are **simulated**. No hardware was used.  
**Video:** No video recording exists. Figures are static PNG backups.

---

## Pre-Demo Checklist

- [ ] Run `python run_all.py` and confirm all outputs are present.
- [ ] Open `streamlit run app/dashboard.py` in a browser tab.
- [ ] Have `results/figures/` open in a file browser as backup.
- [ ] Ensure projector shows the browser at ≥ 1080p.

---

## Narration Script

### [0:00–0:30] Opening and Context (30 s)

**[Presenter says:]**
> "Good morning. Our project is a software prototype for diagnosing faults on RF transmission lines and designing impedance-matching networks.
> We simulate a vector network analyser measuring S11 – the input reflection coefficient – across a frequency sweep, and extract fault information from that.
> All results you will see today are simulated; this is not a hardware demonstration."

**[Slide 1 on screen – Title slide]**

---

### [0:30–1:00] Scenario Setup – Healthy Line (30 s)

**[Click sequence in dashboard:]**
1. Left sidebar → Scenario: `healthy_matched`
2. Z₀ = 50, VF = 0.66, Length = 0.30 m
3. f_start = 1.0 GHz, f_stop = 5.0 GHz, Points = 500
4. Noise σ = 0.00

**[Expected output:]**
- |Γ| plot: flat near zero (< 0.001)
- VSWR: flat at 1.0
- Diagnosis box: **healthy_matched**, confidence HIGH
- Smith chart: dot at centre

**[Presenter says:]**
> "A matched 50-ohm load gives zero reflection everywhere. The Smith chart shows the trace staying at the centre – that is the ideal match point."

---

### [1:00–2:00] Fault Injection and Diagnosis (60 s)

#### Open Circuit (20 s)
**[Click:]** Scenario → `open_circuit`  
**[Expected:]** |Γ| ≈ 1 oscillating, VSWR > 100, Diagnosis: **open_circuit**  
> "Open circuit: full reflection, oscillating due to the round-trip phase with frequency."

#### Short Circuit (20 s)
**[Click:]** Scenario → `short_circuit`  
**[Expected:]** Similar magnitude, but phase shifted by 180°; diagnosis: **short_circuit**  
> "Short circuit also has full reflection, but the phase indicates a negative Γ_L."

#### Series-L Discontinuity (20 s)
**[Click:]** Scenario → `series_L`, L = 30 nH  
**[Expected:]** |Γ| rises with frequency; Diagnosis: **series_L**  
> "A 30-nanohenry inductance in series raises |Γ| at high frequencies – the inductor's impedance grows with frequency, creating more mismatch."

---

### [2:00–3:00] Fault Location (60 s)

**[Click:]** Scenario → `short_circuit`, Fault position = 0.15 m  
**[Observe IFFT plot in dashboard:]**
- Red dashed vertical line at estimated distance ≈ 15 cm
- Green dashed line at true position 15 cm

**[Presenter says:]**
> "Using the windowed IFFT of S11 across 4 GHz bandwidth, we convert the frequency-domain data to a pseudo-time response. The peak corresponds to the round-trip travel time to the fault. With v_p = 0.66c and 4 GHz bandwidth, the range resolution is v_p divided by 2B, which is about **2.5 cm**."

**[Read from sidebar:]**
> "Estimated distance: [read value] cm. True position: 15 cm. Absolute error: [read value] cm. This is within one range-resolution cell."

---

### [3:00–4:00] Quarter-Wave Matching (60 s)

**[Click:]** Enable "Run Quarter-Wave Matching" checkbox  
Set: ZL = 150 Ω, f₀ = 2.0 GHz, Z₀ = 50 Ω

**[Expected output:]**
- Zt = √(50×150) ≈ **86.6 Ω**, lt ≈ **3.3 cm** (at VF=0.66)
- Before matching: |Γ| ≈ 0.5 (RL ≈ 6 dB), flat line
- After matching: |Γ| = 0 at exactly 2.0 GHz, rising away from f₀
- Usable BW (RL ≥ 20 dB): ~ 600–900 MHz

**[Presenter says:]**
> "The quarter-wave transformer with characteristic impedance 86.6 ohms achieves perfect matching at 2 GHz – the return loss goes to infinity exactly at f₀. Away from f₀, matching degrades. The bandwidth where return loss stays above 20 dB is about 800 MHz."

---

### [4:00–4:45] Validation Results (45 s)

**[Switch to slide 13 in PPTX:]**

**[Presenter says:]**
> "We generated 60 randomised cases per fault class on a held-out test set – seed 137, never used for threshold tuning. The overall accuracy is [read from CSV]. Open and short circuits are diagnosed reliably. The main confusion is between small series-L or shunt-C faults and the healthy-matched class, because for small L and C values the |Γ| pattern is nearly identical."

**[Point to accuracy-vs-noise curve, Figure F6:]**
> "Accuracy drops below 70% when noise sigma exceeds 0.20 – this is the practical SNR limit of the rule-based approach."

---

### [4:45–5:00] Limitations and Wrap-Up (15 s)

**[Presenter says:]**
> "Limitations: single-fault assumption, real loads only for quarter-wave matching, and the rule-based classifier cannot handle overlapping L/C signatures well. Future work includes single-stub matching and a machine-learning classifier. Thank you."

---

## Backup Plan

If Streamlit dashboard fails to load:
1. Open `results/figures/F1_scenario_sweep.png` – show all 6 scenarios.
2. Open `results/figures/F4_location_ifft.png` – show TDR result.
3. Open `results/figures/F3_matching_before_after.png` – show matching.
4. Read numbers from `results/csv/classification_report.csv`.

---

## Expected Click Sequence Summary

| Time | Action | Expected Result |
|------|--------|-----------------|
| 0:30 | Scenario = healthy_matched | |Γ| ≈ 0, Diagnosis = healthy |
| 1:00 | Scenario = open_circuit | |Γ| ≈ 1, Diagnosis = open_circuit |
| 1:20 | Scenario = short_circuit | |Γ| ≈ 1, Diagnosis = short_circuit |
| 1:40 | Scenario = series_L, L=30nH | Rising |Γ|, Diagnosis = series_L |
| 2:00 | Scenario = short_circuit, pos=0.15m | IFFT peak ≈ 15 cm |
| 3:00 | Enable matching, ZL=150, f₀=2GHz | Zt=86.6Ω, |Γ|=0 at 2GHz |
| 4:00 | Switch to PPTX slide 13 | Confusion matrix, accuracy |
| 4:45 | PPTX slide 15 | Conclusion |

**Real video:** NO VIDEO EXISTS. All demo outputs come from live code execution.

