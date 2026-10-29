# Validation Summary

**Overall Accuracy (held-out test set, noise_std=0.02):** 0.9528

## Per-Class Metrics

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| healthy_matched | 1.000 | 1.000 | 1.000 | 60 |
| wrong_load | 1.000 | 0.983 | 0.992 | 60 |
| open_circuit | 1.000 | 1.000 | 1.000 | 60 |
| short_circuit | 0.811 | 1.000 | 0.895 | 60 |
| series_L | 0.968 | 1.000 | 0.984 | 60 |
| shunt_C | 0.978 | 0.733 | 0.838 | 60 |

## Accuracy vs Noise

| Noise σ | Accuracy |
|---------|----------|
| 0.00 | 0.9500 |
| 0.02 | 0.9722 |
| 0.05 | 0.8444 |
| 0.10 | 0.3167 |
| 0.15 | 0.3056 |
| 0.20 | 0.2944 |
| 0.30 | 0.2944 |

## Known Limitations and Failure Cases

- **series_L** and **shunt_C** with small L/C values produce near-zero |Gamma| and are misclassified as `healthy_matched`.
- **open_circuit** vs **short_circuit** disambiguation relies on unwrapped phase; with SNR < 5 dB (noise_std > 0.2) this fails.
- **wrong_load** at very high mismatch (RL/Z0 > 5) can overlap with open/short signatures.
- Location estimate via IFFT is unreliable for L/C faults due to the phase contribution of the discontinuity itself.

> [!IMPORTANT]
> All results are from **simulated data only**. These are NOT hardware measurements.

## Traceability
Every number above traces to a CSV file in `results/csv/`.