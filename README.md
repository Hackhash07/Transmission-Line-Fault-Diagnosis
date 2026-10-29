# Transmission-Line Fault Diagnosis & Impedance Matching

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-56%20passed-brightgreen.svg)]()
[![Accuracy](https://img.shields.io/badge/accuracy-95.3%25-success.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Autonomous Virtual Software Prototype** for five IIT undergraduates.  
> *Note: All results are simulated. Never described as hardware measurements.*

---

## Overview

This repository provides a modular, production-grade simulation and diagnostics platform for RF and microwave transmission lines:
- **Core Electromagnetic Model**: Lossless and lossy transmission lines via closed-form $Z_{\text{in}}$ equations and 2-port ABCD matrix cascades (verified to $< 10^{-9}$ relative tolerance).
- **Six Canonical Fault Scenarios**: `healthy_matched`, `wrong_load`, `open_circuit`, `short_circuit`, `series_L` (inductive discontinuity), and `shunt_C` (capacitive discontinuity).
- **Rule-Based Diagnosis**: Classifies fault states using single-port $S_{11}$ features alone without access to ground truth or line parameters (achieving **95.3% test accuracy** on randomized held-out sets).
- **Fault Location (TDR via IFFT)**: Computes physical fault distance via Hann-windowed IFFT pseudo-time reflectometry ($d = v_p t_{\text{peak}} / 2$).
- **Impedance Matching**: Synthesizes quarter-wave transformers ($Z_t = \sqrt{Z_0 R_L}$) with exact cancellation at design frequency $f_0$ and evaluates usable bandwidth ($\text{RL} \ge 20\text{ dB}$).
- **Interactive UI**: Full Streamlit dashboard featuring live Smith charts, frequency sweeps, fault injection, and matching comparisons.
- **Academic Presentation**: 15-slide widescreen `.pptx` presentation with generated figures and typography ($\ge 18\text{ pt}$ body font).

---

## Repository Structure

```
├── TL_Fault_Diagnosis.zip              # Packaged deliverable (1.9 MB)
├── submission/
│   ├── src/                            # Physics, simulation, diagnosis, matching & plots
│   │   ├── model.py                    # Transmission line equations & ABCD cascades
│   │   ├── simulate.py                 # 6 fault classes & cascaded segments
│   │   ├── diagnose.py                 # Rule-based classifier (S11 only)
│   │   ├── locate.py                   # IFFT TDR & phase-slope location
│   │   ├── matching.py                 # Quarter-wave transformer synthesis
│   │   ├── metrics.py                  # Confusion matrix & performance reports
│   │   ├── plots.py                    # Publication-quality headless figures (F1–F8)
│   │   └── validation_experiment.py    # Test evaluation pipeline
│   ├── app/
│   │   └── dashboard.py                # Streamlit interactive web dashboard
│   ├── tests/
│   │   ├── test_model.py               # Boundary conditions & numerical tests
│   │   └── test_diagnose.py            # Classifier interface & isolation tests
│   ├── results/
│   │   ├── csv/                        # Raw experiment metrics & confusion matrix
│   │   ├── figures/                    # High-resolution PNG plots (F1–F8)
│   │   ├── test_report.txt             # Pytest log (56/56 passed)
│   │   └── validation_summary.md       # Validation analysis summary
│   ├── presentation/
│   │   └── TL_Fault_Diagnosis.pptx     # 15-slide presentation
│   ├── docs/
│   │   ├── technical_explanation.md    # Theoretical derivations & hand checks
│   │   ├── demo_script.md              # 5-minute timed presentation script
│   │   ├── storyboard.md               # Slide pacing guide
│   │   ├── submission_checklist.md     # Pre-submission verification checklist
│   │   └── AI_USE_AND_CONTRIBUTIONS.md # Module ownership & disclosure
│   ├── run_all.py                      # Single-command orchestrator (P1 -> P6)
│   ├── requirements.txt                # Python package dependencies
│   ├── PROGRESS.md                     # Phase completion milestones
│   └── README.md                       # Submission documentation
└── .gitignore
```

---

## Quick Start

### 1. Installation
Clone the repository and install required packages:
```bash
git clone https://github.com/Hackhash07/Transmission-Line-Fault-Diagnosis.git
cd Transmission-Line-Fault-Diagnosis/submission
pip install -r requirements.txt
```

### 2. Run Everything End-to-End
Execute the full test suite, simulation sweeps, figure generation, CSV exports, and PPTX compilation in one command:
```bash
python run_all.py
```

### 3. Launch Interactive Web Dashboard
```bash
streamlit run app/dashboard.py
```
Open `http://localhost:8501` in your browser.

### 4. Run Unit Tests Only
```bash
python -m pytest tests/ -v
```

---

## Validation Summary

Evaluated on a randomized held-out test set ($N = 360$, noise $\sigma = 0.02$):
- **Overall Accuracy**: **95.28%**
- **Matched Line**: 100% precision, 100% recall
- **Wrong Load**: 100% precision, 98.3% recall
- **Open Circuit**: 100% precision, 100% recall
- **Short Circuit**: 81.1% precision, 100% recall
- **Series Inductance ($L$)**: 96.8% precision, 100% recall
- **Shunt Capacitance ($C$)**: 97.8% precision, 73.3% recall *(large capacitors $>30\text{ pF}$ act as virtual shorts at 5 GHz)*

---

## Key Figures Generated

| Figure | Description |
|---|---|
| **F1** | Multi-panel $|S_{11}|$, VSWR, and Return Loss sweeps across all 6 scenarios |
| **F2** | Smith Chart polar reflection trajectories toward generator |
| **F3** | Quarter-wave matching before vs. after comparison |
| **F4** | Time-domain reflectometry (IFFT) peak fault localization |
| **F5** | Classification confusion matrix heatmap |
| **F6** | Classification accuracy degradation vs. noise standard deviation |
| **F7** | Reflection magnitude and unwrapped phase across frequency |
| **F8** | Transformer usable bandwidth vs. load mismatch ratio |

---

## Academic References
- Pozar, D. M. *Microwave Engineering*, 4th ed., John Wiley & Sons, 2012 (Ch. 2 & 5).
- Hewlett-Packard, *Time Domain Reflectometry Theory*, Application Note 1304-2.
