# Submission Checklist

## Required Items

### Code and Tests
- [ ] All unit tests pass (`python -m pytest tests/ -v`)
- [ ] `results/test_report.txt` exists and shows 0 failures
- [ ] `run_all.py` completes without errors

### Simulation Outputs
- [ ] `results/figures/F1_scenario_sweep.png`
- [ ] `results/figures/F2_smith_chart.png`
- [ ] `results/figures/F3_matching_before_after.png`
- [ ] `results/figures/F4_location_ifft.png`
- [ ] `results/figures/F5_confusion_matrix.png`
- [ ] `results/figures/F6_accuracy_vs_noise.png`
- [ ] `results/figures/F7_gamma_phase.png`
- [ ] `results/figures/F8_matching_bandwidth.png`

### CSVs
- [ ] `results/csv/confusion_matrix.csv`
- [ ] `results/csv/classification_report.csv`
- [ ] `results/csv/accuracy_vs_noise.csv`
- [ ] `results/csv/location_errors.csv`
- [ ] `results/csv/matching_bandwidth.csv`

### Documentation
- [ ] `results/validation_summary.md` – accurate numbers
- [ ] `docs/technical_explanation.md` – hand-checked formulas
- [ ] `docs/demo_script.md` – click sequence verified
- [ ] `docs/AI_USE_AND_CONTRIBUTIONS.md` – names filled in
- [ ] `README.md` – setup and launch instructions tested

### Presentation
- [ ] `presentation/TL_Fault_Diagnosis.pptx` exists
- [ ] Slide count ≤ 15 (verified programmatically)
- [ ] All figures in slides are from `results/figures/` (not hand-made)
- [ ] Body text ≥ 18pt throughout
- [ ] No text overflow or overlap (visually checked)
- [ ] Disclaimer on slide 1: "All results simulated"

### Zip Package
- [ ] Zip file created from `submission/` directory
- [ ] Zip size ≤ 75 MB
- [ ] All paths are relative (no hardcoded absolute paths in README)

---

## Team Personal Checks (Before Submitting)

1. **Run the demo flow end-to-end** (healthy → open → series_L → matching → validation).
   Confirm every expected output appears on screen.

2. **Open `results/csv/classification_report.csv`** and verify the accuracy number on
   slide 13 matches the CSV.

3. **Check AI_USE_AND_CONTRIBUTIONS.md** – fill in real names, dates, and actual module
   contributions. Remove "[PLACEHOLDER]" tags.

4. **Zip the `submission/` directory** and check its size is under 75 MB.

---

## Schedule Reminder

| Date | Milestone |
|------|-----------|
| 1–7 Nov | Team review: read all code, test edge cases |
| 12 Nov | Feature freeze – no new code |
| 13–14 Nov | Rehearse demo with timer |
| 15 Nov | **Submission deadline** |
| 16 Nov | **Showcase** |

