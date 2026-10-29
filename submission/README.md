# README – Transmission-Line Fault Diagnosis and Impedance Matching

## Overview

Software prototype for five-member IIT undergraduate project.
Simulates, diagnoses, and locates faults on RF transmission lines, and
designs quarter-wave impedance-matching transformers.

**All results are simulated. No hardware was used.**

---

## Quick Start

### 1. Install dependencies

```bash
pip install numpy scipy matplotlib pandas streamlit python-pptx pillow seaborn
```

Minimum Python: 3.9+. Tested on Python 3.13.

### 2. Run everything end-to-end

```bash
cd submission
python run_all.py
```

This will:
- Run all unit tests (P1 gate)
- Generate all 8 figures in `results/figures/`
- Save all CSVs in `results/csv/`
- Generate the PPTX in `presentation/`

### 3. Launch the interactive dashboard

```bash
cd submission
streamlit run app/dashboard.py
```

Open `http://localhost:8501` in your browser.

### 4. Run tests only

```bash
cd submission
python -m pytest tests/ -v
```

### 5. Re-run simulation only (skip tests)

```bash
cd submission
python run_all.py --skip-tests --skip-pptx
```

Or directly:

```bash
cd submission
python -m src.validation_experiment
```

### 6. Generate PPTX only

```bash
cd submission
python docs/generate_pptx.py
```

---

## Project Structure

```
submission/
├── src/
│   ├── model.py              # TL impedance, ABCD, Γ, VSWR, RL, sweep
│   ├── simulate.py           # Six fault scenarios, ABCD cascades
│   ├── diagnose.py           # Rule-based classifier (S11 only)
│   ├── locate.py             # IFFT TDR + phase-slope location
│   ├── matching.py           # Quarter-wave transformer design
│   ├── metrics.py            # Confusion matrix, precision/recall, CSV export
│   ├── plots.py              # All 8 matplotlib figures
│   └── validation_experiment.py  # Full validation pipeline
├── app/
│   └── dashboard.py          # Streamlit interactive dashboard
├── tests/
│   ├── test_model.py         # Model + scenario unit tests
│   └── test_diagnose.py      # Diagnose, locate, matching tests
├── results/
│   ├── csv/                  # All numeric results as CSV
│   ├── figures/              # All 8 PNG figures
│   ├── test_report.txt       # pytest output
│   └── validation_summary.md # Human-readable summary
├── presentation/
│   └── TL_Fault_Diagnosis.pptx  # 15-slide presentation
├── docs/
│   ├── technical_explanation.md  # Theory, hand-checks, references
│   ├── demo_script.md            # 5-min timed narration + click sequence
│   ├── storyboard.md             # Slide timing and design notes
│   ├── submission_checklist.md   # Pre-submission checklist
│   └── AI_USE_AND_CONTRIBUTIONS.md  # Disclosure + team roles
├── run_all.py                # Single-command orchestrator
├── requirements.txt          # Python dependencies
├── PROGRESS.md               # Phase completion log
└── README.md                 # This file
```

---

## Reproducing Results

All random seeds are fixed:
- Calibration set: `seed=42`
- Test set: `seed=137`
- Noise runs: `seed=99`

To reproduce exactly:

```bash
python run_all.py --skip-pptx   # fast reproduction without PPTX
```

Every number in the slides traces to a file in `results/csv/`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: streamlit` | `pip install streamlit` |
| `ModuleNotFoundError: matplotlib` | `pip install matplotlib` |
| `ModuleNotFoundError: pptx` | `pip install python-pptx` |
| Streamlit won't open | Check `http://localhost:8501`; try `--server.port 8502` |
| Figures missing after run_all | Check `results/figures/`; re-run `python -m src.validation_experiment` |
| Test failures | Run `python -m pytest tests/ -v --tb=long` for details |
| PPTX figure placeholders | Run validation first (`python -m src.validation_experiment`), then `python docs/generate_pptx.py` |

---

## Team Schedule

| Dates | Task |
|-------|------|
| 1–7 Nov 2026 | Code review: each member reads their assigned modules |
| 8–11 Nov | Fix any issues found during review |
| 12 Nov | Feature freeze – no new features after this date |
| 13–14 Nov | Rehearse 5-min demo with timer |
| 15 Nov | **Submission deadline** |
| 16 Nov | **Showcase** |

---

## References

- Pozar, D.M. *Microwave Engineering*, 4th ed. Wiley, 2012.
  (Sections 2.1–2.4, 4.1, 5.1) — **[team to verify page numbers]**
- Hewlett-Packard. *Time Domain Reflectometry*, Application Note 1304-2.
  — **[team to verify: unconfirmed]**

---

## Notes

- `streamlit` cannot be launched headlessly without a browser; screenshots
  are not automatically captured. Use figures in `results/figures/` as backups.
- The dashboard imports from `src/`; always run from the `submission/` directory.
- Python path: `run_all.py` and `dashboard.py` both add the project root to `sys.path`.

