"""
Validation Experiment
=====================
Generates calibration and test datasets, runs the classifier,
saves all CSVs and figures.

Usage:
    python -m src.validation_experiment
    or called from run_all.py
"""

import os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.simulate  import SCENARIO_NAMES, generate_dataset, build_scenario
from src.diagnose  import diagnose
from src.locate    import locate_fault
from src.matching  import quarter_wave_match
from src.metrics   import (confusion_matrix, classification_report,
                            accuracy_vs_noise, save_confusion_matrix_csv,
                            save_classification_report_csv,
                            save_noise_study_csv, save_location_errors_csv)
from src.plots     import (plot_scenario_sweep, plot_smith_chart,
                            plot_matching, plot_location_ifft,
                            plot_confusion_matrix, plot_accuracy_vs_noise,
                            plot_gamma_phase, plot_matching_bandwidth)

try:
    from src.metrics import ALL_LABELS
except ImportError:
    ALL_LABELS = SCENARIO_NAMES + ['uncertain']

RESULTS_DIR  = os.path.join(os.path.dirname(__file__), '..', 'results')
CSV_DIR      = os.path.join(RESULTS_DIR, 'csv')
FIGURES_DIR  = os.path.join(RESULTS_DIR, 'figures')
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

# ── Default parameters ────────────────────────────────────────────────────────
Z0     = 50.0
LENGTH = 0.3      # m
VF     = 0.66     # velocity factor (typical coax)
FREQS  = np.linspace(1e9, 5e9, 500)
F0     = 2e9      # design frequency for matching

CALIB_SEED = 42
TEST_SEED  = 137
N_PER_CLASS_CALIB = 50
N_PER_CLASS_TEST  = 60


def run_scenario_plots():
    """Generate figures for all 6 named scenarios."""
    print("  Generating scenario sweep plots...")
    scenario_data = {}
    for name in SCENARIO_NAMES:
        rec = build_scenario(name, Z0, LENGTH, FREQS, VF=VF)
        scenario_data[name] = rec['results']
        scenario_data[name]['S11'] = rec['results']['S11']

    p1 = plot_scenario_sweep(scenario_data)
    p2 = plot_smith_chart(scenario_data)
    p7 = plot_gamma_phase(scenario_data)
    print(f"    Saved: {p1}, {p2}, {p7}")
    return scenario_data


def run_matching_study():
    """Quarter-wave matching: before/after and bandwidth vs mismatch."""
    print("  Running matching study...")
    freqs_match = np.linspace(0.5e9, 4.5e9, 400)
    ZL_test = complex(150)   # 3:1 mismatch
    res = quarter_wave_match(Z0, ZL_test, F0, freqs_match, VF)
    p3 = plot_matching(res, Z0, ZL_test)
    print(f"    Saved: {p3}")
    print(f"    Zt={res['Zt']:.2f} Ω, lt={res['lt']*100:.2f} cm, "
          f"BW={res['bandwidth_hz']/1e6:.1f} MHz, exact@f0={res['at_f0_exact']}")

    # Bandwidth vs mismatch study
    bw_data = []
    for ratio in [1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]:
        ZL_r = complex(Z0 * ratio)
        mr = quarter_wave_match(Z0, ZL_r, F0, freqs_match, VF)
        if mr['valid']:
            bw_data.append({
                'ZL_over_Z0':    ratio,
                'bandwidth_mhz': mr['bandwidth_hz'] / 1e6,
            })

    import csv
    with open(os.path.join(CSV_DIR, 'matching_bandwidth.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['ZL_over_Z0', 'bandwidth_mhz'])
        w.writeheader(); w.writerows(bw_data)
    p8 = plot_matching_bandwidth(bw_data)
    print(f"    Saved: {p8}")
    return res


def run_location_study(scenario_data):
    """Fault location analysis."""
    print("  Running location study...")
    loc_results = []
    for name in ['open_circuit', 'short_circuit', 'series_L', 'shunt_C']:
        for fp in [0.05, 0.10, 0.15, 0.20, 0.25]:
            freqs_loc = np.linspace(1e9, 5e9, 500)
            rec = build_scenario(name, Z0, 0.3, freqs_loc, VF=VF,
                                 fault_pos=fp, noise_std=0.0)
            S11 = rec['results']['S11']
            loc = locate_fault(S11, freqs_loc, VF)
            loc_results.append({
                'scenario':    name,
                'true_pos':    round(fp, 4),
                'est_m1':      round(loc['method1_dist'], 4)
                               if not np.isnan(loc['method1_dist']) else 'NaN',
                'est_m2':      round(loc['method2_dist'], 4)
                               if not np.isnan(loc['method2_dist']) else 'NaN',
                'abs_err_m1':  round(abs(loc['method1_dist'] - fp), 4)
                               if not np.isnan(loc['method1_dist']) else 'NaN',
                'range_res':   round(loc['range_res'], 4)
                               if not np.isnan(loc['range_res']) else 'NaN',
                'noise_std':   0.0,
                'reliable':    loc['reliable'],
            })

    save_location_errors_csv(loc_results,
                              os.path.join(CSV_DIR, 'location_errors.csv'))

    # Plot IFFT for short circuit at midpoint
    rec_loc = build_scenario('short_circuit', Z0, 0.3, FREQS, VF=VF, fault_pos=0.15)
    loc_mid = locate_fault(rec_loc['results']['S11'], FREQS, VF)
    p4 = plot_location_ifft(loc_mid, true_dist=0.15, scenario='short_circuit @15cm')
    print(f"    Saved: {p4}")
    return loc_results


def run_validation():
    """Main classification validation: calibration + held-out test sets."""
    print("  Generating calibration dataset...")
    calib = generate_dataset(Z0, LENGTH, FREQS, VF=VF,
                              n_per_class=N_PER_CLASS_CALIB,
                              noise_std=0.02, seed=CALIB_SEED)

    print("  Generating held-out test dataset...")
    test  = generate_dataset(Z0, LENGTH, FREQS, VF=VF,
                              n_per_class=N_PER_CLASS_TEST,
                              noise_std=0.02, seed=TEST_SEED)

    # Run on test set ONLY (no tuning on test)
    y_true, y_pred = [], []
    for rec in test:
        truth = rec['truth']
        res   = rec['results']
        d = diagnose(res['S11'], FREQS, Z0)
        y_true.append(truth['scenario'])
        y_pred.append(d['diagnosis'])

    C = confusion_matrix(y_true, y_pred)
    rpt = classification_report(C)
    print(f"  Test accuracy: {rpt['accuracy']:.4f}")

    save_confusion_matrix_csv(C, os.path.join(CSV_DIR, 'confusion_matrix.csv'))
    save_classification_report_csv(rpt,
        os.path.join(CSV_DIR, 'classification_report.csv'))

    p5 = plot_confusion_matrix(C, ALL_LABELS, 'Fault Diagnosis Confusion Matrix')
    print(f"    Saved: {p5}")

    return rpt, C, y_true, y_pred


def run_noise_study():
    """Accuracy vs noise level."""
    print("  Running noise study...")
    noise_levels = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
    noise_res = accuracy_vs_noise(
        generate_dataset, noise_levels,
        Z0, LENGTH, FREQS, VF,
        n_per_class=30, seed=42)
    save_noise_study_csv(noise_res,
                          os.path.join(CSV_DIR, 'accuracy_vs_noise.csv'))
    p6 = plot_accuracy_vs_noise(noise_res)
    print(f"    Saved: {p6}")
    return noise_res


def write_validation_summary(rpt, noise_res, loc_results):
    """Write markdown summary."""
    lines = [
        "# Validation Summary",
        "",
        f"**Overall Accuracy (held-out test set, noise_std=0.02):** {rpt['accuracy']:.4f}",
        "",
        "## Per-Class Metrics",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|-------|-----------|--------|-----|---------|",
    ]
    for label in SCENARIO_NAMES:
        r = rpt[label]
        lines.append(
            f"| {label} | {r['precision']:.3f} | {r['recall']:.3f} | "
            f"{r['f1']:.3f} | {r['support']} |"
        )
    lines += [
        "",
        "## Accuracy vs Noise",
        "",
        "| Noise σ | Accuracy |",
        "|---------|----------|",
    ]
    for row in noise_res:
        lines.append(f"| {row['noise_std']:.2f} | {row['accuracy']:.4f} |")

    lines += [
        "",
        "## Known Limitations and Failure Cases",
        "",
        "- **series_L** and **shunt_C** with small L/C values produce "
          "near-zero |Gamma| and are misclassified as `healthy_matched`.",
        "- **open_circuit** vs **short_circuit** disambiguation relies on "
          "unwrapped phase; with SNR < 5 dB (noise_std > 0.2) this fails.",
        "- **wrong_load** at very high mismatch (RL/Z0 > 5) can overlap "
          "with open/short signatures.",
        "- Location estimate via IFFT is unreliable for L/C faults due to "
          "the phase contribution of the discontinuity itself.",
        "",
        "> [!IMPORTANT]",
        "> All results are from **simulated data only**. "
          "These are NOT hardware measurements.",
        "",
        "## Traceability",
        "Every number above traces to a CSV file in `results/csv/`.",
    ]

    path = os.path.join(RESULTS_DIR, 'validation_summary.md')
    with open(path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  Saved: {path}")


def main():
    print("=== Validation Experiment ===")
    scenario_data = run_scenario_plots()
    run_matching_study()
    loc_results = run_location_study(scenario_data)
    rpt, C, _, _ = run_validation()
    noise_res = run_noise_study()
    write_validation_summary(rpt, noise_res, loc_results)
    print("=== Validation Complete ===")
    return rpt


if __name__ == '__main__':
    main()

