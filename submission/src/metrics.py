"""
Metrics Module
==============
Compute confusion matrix, precision, recall, accuracy, and accuracy-vs-noise
for the fault diagnosis classifier.

All numbers produced here are directly saved to CSV so that every slide
figure can be traced to a file.
"""

import numpy as np
import csv
import os

from .simulate import SCENARIO_NAMES


ALL_LABELS = SCENARIO_NAMES + ['uncertain']


def confusion_matrix(y_true: list, y_pred: list) -> np.ndarray:
    """
    Compute confusion matrix [rows=true, cols=pred] for ALL_LABELS.

    Parameters
    ----------
    y_true, y_pred : lists of label strings

    Returns
    -------
    C : int ndarray shape (K, K)
    """
    K = len(ALL_LABELS)
    label_idx = {l: i for i, l in enumerate(ALL_LABELS)}
    C = np.zeros((K, K), dtype=int)
    for t, p in zip(y_true, y_pred):
        i = label_idx.get(t, K - 1)   # unknown -> 'uncertain'
        j = label_idx.get(p, K - 1)
        C[i, j] += 1
    return C


def classification_report(C: np.ndarray) -> dict:
    """
    Compute per-class precision, recall, F1, and overall accuracy.
    'uncertain' class is excluded from accuracy computation.

    Returns
    -------
    dict: {label: {'precision', 'recall', 'f1', 'support'}, ...,
           'accuracy': float}
    """
    K = len(ALL_LABELS)
    report = {}
    total_correct = 0
    total_support = 0

    for i, label in enumerate(ALL_LABELS):
        tp = int(C[i, i])
        fp = int(np.sum(C[:, i]) - tp)
        fn = int(np.sum(C[i, :]) - tp)
        support = int(np.sum(C[i, :]))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
               if (precision + recall) > 0 else 0.0)

        report[label] = {
            'precision': round(precision, 4),
            'recall':    round(recall, 4),
            'f1':        round(f1, 4),
            'support':   support,
        }
        if label != 'uncertain':
            total_correct += tp
            total_support += support

    report['accuracy'] = round(total_correct / total_support, 4) \
                         if total_support > 0 else 0.0
    return report


def accuracy_vs_noise(dataset_builder,
                      noise_levels: list,
                      Z0: float, length: float,
                      freqs: np.ndarray, VF: float,
                      n_per_class: int = 50,
                      seed: int = 99) -> list:
    """
    Run diagnosis over multiple noise levels and return accuracy at each.

    Parameters
    ----------
    dataset_builder : callable matching simulate.generate_dataset signature
    noise_levels    : list of noise_std values to test
    Z0, length, freqs, VF : passed to dataset_builder
    n_per_class     : samples per class
    seed            : random seed

    Returns
    -------
    list of dicts: [{'noise_std': float, 'accuracy': float}, ...]
    """
    from .diagnose import diagnose

    results = []
    for ns in noise_levels:
        dataset = dataset_builder(
            Z0, length, freqs, VF=VF,
            n_per_class=n_per_class, noise_std=ns, seed=seed)
        y_true, y_pred = [], []
        for rec in dataset:
            truth = rec['truth']
            res   = rec['results']
            d     = diagnose(res['S11'], freqs, Z0)
            y_true.append(truth['scenario'])
            y_pred.append(d['diagnosis'])
        C = confusion_matrix(y_true, y_pred)
        rpt = classification_report(C)
        results.append({'noise_std': float(ns), 'accuracy': rpt['accuracy']})
    return results


def save_confusion_matrix_csv(C: np.ndarray, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['true\\pred'] + ALL_LABELS)
        for i, label in enumerate(ALL_LABELS):
            writer.writerow([label] + list(C[i]))


def save_classification_report_csv(report: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['label', 'precision', 'recall', 'f1', 'support'])
        for label in ALL_LABELS + ['accuracy']:
            if label == 'accuracy':
                writer.writerow(['OVERALL_ACCURACY', '', '', '',
                                 f"{report['accuracy']:.4f}"])
            else:
                r = report[label]
                writer.writerow([label, r['precision'], r['recall'],
                                 r['f1'], r['support']])


def save_noise_study_csv(noise_results: list, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['noise_std', 'accuracy'])
        for row in noise_results:
            writer.writerow([row['noise_std'], row['accuracy']])


def save_location_errors_csv(loc_results: list, path: str):
    """
    loc_results: list of dicts with keys:
      scenario, true_pos, est_pos_m1, est_pos_m2, abs_err_m1, abs_err_m2,
      noise_std, bandwidth_hz
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not loc_results:
        return
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(loc_results[0].keys())
        for row in loc_results:
            writer.writerow(row.values())

