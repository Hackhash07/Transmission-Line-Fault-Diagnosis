"""
Plots Module
============
Generates all figures for the project using matplotlib.
All figures are saved to results/figures/.

Figures produced:
  F1  scenario_sweep.png     – |Gamma|, VSWR, RL vs freq, all 6 scenarios
  F2  smith_chart.png        – Smith chart overlay, all 6 scenarios
  F3  matching_before_after.png – RL before/after quarter-wave matching
  F4  location_ifft.png      – IFFT time-domain response for fault location
  F5  confusion_matrix.png   – Heatmap
  F6  accuracy_vs_noise.png  – Accuracy curve
  F7  gamma_phase.png        – |Gamma| and phase vs frequency
  F8  matching_bandwidth.png – BW vs mismatch ratio study
"""

import numpy as np
import os
import warnings

try:
    import matplotlib
    matplotlib.use('Agg')   # headless / non-interactive
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    warnings.warn("matplotlib not available; plots will not be generated.")

FIGURE_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'figures')

SCENARIO_COLORS = {
    'healthy_matched': '#2ca02c',
    'wrong_load':      '#1f77b4',
    'open_circuit':    '#d62728',
    'short_circuit':   '#ff7f0e',
    'series_L':        '#9467bd',
    'shunt_C':         '#8c564b',
}


def _savefig(fig, name: str, dpi: int = 150):
    os.makedirs(FIGURE_DIR, exist_ok=True)
    path = os.path.join(FIGURE_DIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# F1: Scenario sweep (|Gamma|, VSWR, RL)
# ─────────────────────────────────────────────────────────────────────────────

def plot_scenario_sweep(scenario_data: dict, title: str = "") -> str:
    """
    scenario_data: {name: sweep_result_dict}
    Returns path to saved figure.
    """
    if not HAS_MPL:
        return ""
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    ax_g, ax_v, ax_r = axes

    for name, res in scenario_data.items():
        f_ghz = res['freqs'] / 1e9
        col = SCENARIO_COLORS.get(name, 'gray')
        mag = np.abs(res['S11'])
        ax_g.plot(f_ghz, mag, color=col, label=name, linewidth=1.5)
        ax_v.plot(f_ghz, res['VSWR'], color=col, linewidth=1.5)
        ax_r.plot(f_ghz, res['RL_dB'], color=col, linewidth=1.5)

    ax_g.set_ylabel('|Γ| (|S11|)')
    ax_g.set_ylim(0, 1.05)
    ax_g.legend(loc='upper right', fontsize=8)
    ax_g.axhline(0.05, color='gray', linestyle='--', alpha=0.5, label='matched threshold')
    ax_g.set_title(title or 'Reflection Coefficient vs Frequency (6 Scenarios)')
    ax_g.grid(True, alpha=0.3)

    ax_v.set_ylabel('VSWR')
    ax_v.set_ylim(1, 20)
    ax_v.grid(True, alpha=0.3)

    ax_r.set_ylabel('Return Loss (dB)')
    ax_r.set_ylim(0, 50)
    ax_r.invert_yaxis()  # convention: higher RL = better match, plotted downward
    ax_r.set_xlabel('Frequency (GHz)')
    ax_r.grid(True, alpha=0.3)

    plt.tight_layout()
    return _savefig(fig, 'F1_scenario_sweep.png')


# ─────────────────────────────────────────────────────────────────────────────
# F2: Smith chart
# ─────────────────────────────────────────────────────────────────────────────

def _draw_smith_chart_grid(ax):
    """Draw the constant-r and constant-x circles on a Smith chart axes."""
    theta = np.linspace(0, 2 * np.pi, 360)
    # Unit circle (|Gamma| = 1)
    ax.plot(np.cos(theta), np.sin(theta), 'k-', linewidth=1.0)

    # Constant resistance circles: r = 0,0.5,1,2,5
    for r in [0, 0.5, 1.0, 2.0, 5.0]:
        center_x = r / (1 + r)
        radius   = 1.0 / (1 + r)
        ax.plot(center_x + radius * np.cos(theta),
                radius * np.sin(theta),
                'b-', linewidth=0.5, alpha=0.4)
        ax.text(center_x + radius, 0, f'{r}', fontsize=6, ha='left', va='bottom', color='blue')

    # Constant reactance arcs: x = ±0.5, ±1, ±2
    for x in [0.5, 1.0, 2.0, -0.5, -1.0, -2.0]:
        center_x = 1.0
        center_y = 1.0 / x
        radius_a = abs(1.0 / x)
        phi = np.linspace(-np.pi, np.pi, 360)
        xc = center_x + radius_a * np.cos(phi)
        yc = center_y + radius_a * np.sin(phi)
        mask = np.abs(xc) <= 1.05
        ax.plot(xc[mask], yc[mask], 'g-', linewidth=0.5, alpha=0.4)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.set_aspect('equal')
    ax.axhline(0, color='k', linewidth=0.5, alpha=0.3)
    ax.axvline(0, color='k', linewidth=0.5, alpha=0.3)
    ax.set_xlabel('Re(Γ)')
    ax.set_ylabel('Im(Γ)')


def plot_smith_chart(scenario_data: dict) -> str:
    if not HAS_MPL:
        return ""
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    _draw_smith_chart_grid(ax)

    for name, res in scenario_data.items():
        G = res['Gamma_in']
        col = SCENARIO_COLORS.get(name, 'gray')
        ax.plot(G.real, G.imag, color=col, label=name, linewidth=1.5, alpha=0.8)
        # Mark start (low freq)
        ax.scatter(G.real[0], G.imag[0], color=col, s=30, zorder=5)

    ax.set_title('Smith Chart – Input Reflection Coefficient (6 Scenarios)')
    ax.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    return _savefig(fig, 'F2_smith_chart.png')


# ─────────────────────────────────────────────────────────────────────────────
# F3: Quarter-wave matching before/after
# ─────────────────────────────────────────────────────────────────────────────

def plot_matching(match_result: dict, Z0: float, ZL: complex) -> str:
    if not HAS_MPL or not match_result.get('valid', False):
        return ""
    freqs = match_result['freqs'] / 1e9
    f0    = match_result['f0'] / 1e9
    b = match_result['before']
    a = match_result['after']

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    for ax, key, ylabel in zip(axes,
                                ['Gamma', 'VSWR', 'RL_dB'],
                                ['|Γ|', 'VSWR', 'Return Loss (dB)']):
        ax.plot(freqs, b[key], 'r-', label='Before matching', linewidth=2)
        ax.plot(freqs, a[key], 'g-', label='After matching',  linewidth=2)
        ax.axvline(f0, color='k', linestyle='--', alpha=0.5, label=f'f₀={f0:.2f} GHz')
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylim(0, 1.05)
    axes[1].set_ylim(1, 20)
    axes[2].axhline(match_result['rl_threshold'], color='orange',
                    linestyle=':', label=f"BW threshold ({match_result['rl_threshold']:.0f} dB)")
    axes[2].legend(fontsize=8)

    zt = match_result['Zt']
    lt = match_result['lt'] * 100   # cm
    bw_mhz = match_result['bandwidth_hz'] / 1e6
    fig.suptitle(
        f'Quarter-Wave Matching: Z0={Z0}Ω, ZL={ZL.real:.0f}Ω, '
        f'Zt={zt:.1f}Ω, lt={lt:.2f}cm, BW={bw_mhz:.1f}MHz',
        fontsize=11
    )
    plt.tight_layout()
    return _savefig(fig, 'F3_matching_before_after.png')


# ─────────────────────────────────────────────────────────────────────────────
# F4: IFFT location
# ─────────────────────────────────────────────────────────────────────────────

def plot_location_ifft(loc_result: dict, true_dist: float = None,
                       scenario: str = "") -> str:
    if not HAS_MPL:
        return ""
    t = loc_result.get('t_axis', np.array([]))
    mag = loc_result.get('ifft_mag', np.array([]))
    if len(t) == 0:
        return ""

    vp = 3e8   # approximate for display
    d_axis = t * vp / 2.0 * 100  # cm

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(d_axis[:len(d_axis)//2], mag[:len(mag)//2], 'b-', linewidth=1)

    pidx = loc_result.get('peak_idx', -1)
    if 0 <= pidx < len(d_axis):
        ax.axvline(d_axis[pidx], color='r', linestyle='--',
                   label=f"Est. {d_axis[pidx]:.1f} cm")

    if true_dist is not None:
        ax.axvline(true_dist * 100, color='g', linestyle='--',
                   label=f"True {true_dist*100:.1f} cm")

    ax.set_xlabel('Distance (cm)')
    ax.set_ylabel('|IFFT(S11)| (a.u.)')
    ax.set_title(f'Time-Domain Fault Location via IFFT – {scenario}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return _savefig(fig, 'F4_location_ifft.png')


# ─────────────────────────────────────────────────────────────────────────────
# F5: Confusion matrix heatmap
# ─────────────────────────────────────────────────────────────────────────────

def plot_confusion_matrix(C: np.ndarray, labels: list, title: str = "") -> str:
    if not HAS_MPL:
        return ""
    fig, ax = plt.subplots(figsize=(9, 7))

    try:
        import seaborn as sns
        sns.heatmap(C, annot=True, fmt='d', cmap='Blues',
                    xticklabels=labels, yticklabels=labels, ax=ax)
    except ImportError:
        im = ax.imshow(C, cmap='Blues')
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, str(C[i, j]), ha='center', va='center', fontsize=8)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        plt.colorbar(im, ax=ax)

    ax.set_xlabel('Predicted Label')
    ax.set_ylabel('True Label')
    ax.set_title(title or 'Confusion Matrix – Fault Diagnosis')
    plt.tight_layout()
    return _savefig(fig, 'F5_confusion_matrix.png')


# ─────────────────────────────────────────────────────────────────────────────
# F6: Accuracy vs noise
# ─────────────────────────────────────────────────────────────────────────────

def plot_accuracy_vs_noise(noise_results: list) -> str:
    if not HAS_MPL or not noise_results:
        return ""
    ns   = [r['noise_std'] for r in noise_results]
    acc  = [r['accuracy']  for r in noise_results]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ns, acc, 'bo-', linewidth=2, markersize=6)
    ax.set_xlabel('Noise Standard Deviation (|S11| scale)')
    ax.set_ylabel('Accuracy')
    ax.set_ylim(0, 1.05)
    ax.set_title('Diagnosis Accuracy vs. Noise Level')
    ax.axhline(0.9, color='orange', linestyle='--', alpha=0.7, label='90% threshold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return _savefig(fig, 'F6_accuracy_vs_noise.png')


# ─────────────────────────────────────────────────────────────────────────────
# F7: Gamma and phase vs freq
# ─────────────────────────────────────────────────────────────────────────────

def plot_gamma_phase(scenario_data: dict) -> str:
    if not HAS_MPL:
        return ""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    for name, res in scenario_data.items():
        f_ghz = res['freqs'] / 1e9
        col = SCENARIO_COLORS.get(name, 'gray')
        ax1.plot(f_ghz, np.abs(res['S11']), color=col, label=name, linewidth=1.5)
        ax2.plot(f_ghz, np.unwrap(np.angle(res['S11'])) * 180 / np.pi,
                 color=col, linewidth=1.5)

    ax1.set_ylabel('|Γ_in| = |S11|')
    ax1.set_ylim(0, 1.05)
    ax1.legend(fontsize=8, loc='upper right')
    ax1.set_title('Reflection Coefficient Magnitude and Phase')
    ax1.grid(True, alpha=0.3)

    ax2.set_ylabel('Phase(Γ_in) [degrees]')
    ax2.set_xlabel('Frequency (GHz)')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    return _savefig(fig, 'F7_gamma_phase.png')


# ─────────────────────────────────────────────────────────────────────────────
# F8: Matching bandwidth vs mismatch ratio
# ─────────────────────────────────────────────────────────────────────────────

def plot_matching_bandwidth(match_bw_data: list) -> str:
    """
    match_bw_data: list of {ZL_over_Z0: float, bandwidth_mhz: float}
    """
    if not HAS_MPL or not match_bw_data:
        return ""
    ratios = [d['ZL_over_Z0']    for d in match_bw_data]
    bws    = [d['bandwidth_mhz'] for d in match_bw_data]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ratios, bws, 'rs-', linewidth=2, markersize=6)
    ax.set_xlabel('ZL / Z0 (Mismatch Ratio)')
    ax.set_ylabel('Usable Bandwidth (MHz, RL ≥ 20 dB)')
    ax.set_title('Quarter-Wave Transformer: Bandwidth vs Mismatch')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return _savefig(fig, 'F8_matching_bandwidth.png')

