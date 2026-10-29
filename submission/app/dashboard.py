"""
Streamlit Dashboard – Transmission-Line Fault Diagnosis
=========================================================
Launch: streamlit run app/dashboard.py

This dashboard calls the same core modules as run_all.py.
No logic is duplicated; all computation is delegated to src/.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np

try:
    import streamlit as st
    HAS_ST = True
except ImportError:
    HAS_ST = False
    raise ImportError("Streamlit is required. Install with: pip install streamlit")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from src.model    import sweep, C_LIGHT, gamma_from_z, vswr_from_gamma, return_loss_db
from src.simulate import build_scenario, SCENARIO_NAMES
from src.diagnose import diagnose
from src.locate   import locate_fault
from src.matching import quarter_wave_match
from src.plots    import (plot_scenario_sweep, plot_smith_chart,
                           plot_matching, plot_location_ifft, FIGURE_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TL Fault Diagnosis & Impedance Matching",
    page_icon="📡",
    layout="wide",
)

st.title("📡 Transmission-Line Fault Diagnosis and Impedance Matching")
st.caption(
    "**Software Prototype** – IIT Undergraduate Project, Oct–Nov 2026.  "
    "All results are **simulated**; these are not hardware measurements."
)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar: Parameters
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Parameters")

    st.subheader("Line Parameters")
    Z0 = st.number_input("Z₀ (Ω)", min_value=1.0, max_value=500.0,
                          value=50.0, step=1.0,
                          help="Characteristic impedance of the line")
    VF = st.slider("Velocity Factor", 0.1, 1.0, 0.66, 0.01,
                    help="vp = VF × c; typical coax ≈ 0.66")
    length = st.number_input("Line Length (m)", 0.01, 10.0, 0.3, 0.01)

    st.subheader("Frequency Sweep")
    f_start = st.number_input("f_start (GHz)", 0.1, 20.0, 1.0, 0.1) * 1e9
    f_stop  = st.number_input("f_stop (GHz)", 0.1, 20.0, 5.0, 0.1) * 1e9
    n_pts   = st.slider("# Freq Points", 50, 1000, 500, 50)

    if f_start >= f_stop:
        st.error("f_start must be less than f_stop!")
        st.stop()

    freqs = np.linspace(f_start, f_stop, n_pts)

    st.subheader("Fault / Scenario")
    scenario = st.selectbox("Scenario", SCENARIO_NAMES, index=0)
    fault_pos = st.slider("Fault Position (m)", 0.0, float(length), float(length / 2), 0.01)
    noise_std = st.slider("Noise σ", 0.0, 0.3, 0.0, 0.01,
                           help="Std of complex Gaussian noise on S11")

    # Extra scenario-specific params
    L_val = st.number_input("L (nH) [for series_L]", 0.1, 200.0, 10.0, 0.5) * 1e-9
    C_val = st.number_input("C (pF) [for shunt_C]", 0.1, 200.0, 10.0, 0.5) * 1e-12
    ZL_wrong = st.number_input("ZL wrong (Ω) [for wrong_load]",
                                 1.0, 1000.0, 100.0, 1.0)

    st.subheader("Matching Parameters")
    do_match = st.checkbox("Run Quarter-Wave Matching", value=False)
    ZL_match  = st.number_input("Load to Match (Ω, real)", 1.0, 1000.0, 100.0, 1.0)
    f0_match  = st.number_input("Design Freq f₀ (GHz)", 0.1, 20.0, 2.0, 0.1) * 1e9

# ─────────────────────────────────────────────────────────────────────────────
# Main content
# ─────────────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 2])

# ── Run simulation ────────────────────────────────────────────────────────────
with st.spinner("Simulating..."):
    rng = np.random.default_rng(42)
    try:
        rec = build_scenario(
            scenario, Z0, length, freqs, VF=VF,
            fault_pos=fault_pos,
            L_val=L_val, C_val=C_val,
            ZL_wrong=complex(ZL_wrong),
            noise_std=noise_std, rng=rng,
        )
    except Exception as e:
        st.error(f"Simulation error: {e}")
        st.stop()

res = rec['results']
S11 = res['S11']
f_ghz = freqs / 1e9

# ── Diagnosis ────────────────────────────────────────────────────────────────
dx = diagnose(S11, freqs, Z0)

# ── Location ─────────────────────────────────────────────────────────────────
loc = locate_fault(S11, freqs, VF, noise_std)

# ─────────────────────────────────────────────────────────────────────────────
# Display: Plots
# ─────────────────────────────────────────────────────────────────────────────
with col1:
    st.subheader("Reflection Metrics")
    if HAS_MPL:
        fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
        ax_g, ax_v, ax_r = axes
        mag = np.abs(S11)
        ax_g.plot(f_ghz, mag, 'b-', linewidth=1.5)
        ax_g.set_ylabel('|Γ| = |S11|')
        ax_g.set_ylim(0, 1.05)
        ax_g.axhline(0.05, color='g', linestyle='--', alpha=0.5, label='match threshold')
        ax_g.legend(fontsize=8)
        ax_g.grid(True, alpha=0.3)
        ax_g.set_title(f'Scenario: {scenario}')

        ax_v.plot(f_ghz, res['VSWR'], 'r-', linewidth=1.5)
        ax_v.set_ylabel('VSWR')
        ax_v.set_ylim(1, max(25, np.percentile(res['VSWR'], 95) * 1.2))
        ax_v.grid(True, alpha=0.3)

        ax_r.plot(f_ghz, res['RL_dB'], 'g-', linewidth=1.5)
        ax_r.set_ylabel('Return Loss (dB)')
        ax_r.set_xlabel('Frequency (GHz)')
        ax_r.set_ylim(0, 55)
        ax_r.grid(True, alpha=0.3)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.warning("matplotlib not available; install it to see plots.")

    # Smith chart
    st.subheader("Smith Chart")
    if HAS_MPL:
        from src.plots import _draw_smith_chart_grid, SCENARIO_COLORS
        fig2, ax2 = plt.subplots(figsize=(6, 6))
        _draw_smith_chart_grid(ax2)
        G = res['Gamma_in']
        col_sc = SCENARIO_COLORS.get(scenario, 'blue')
        ax2.plot(G.real, G.imag, color=col_sc, linewidth=1.5, label=scenario)
        ax2.scatter(G.real[0], G.imag[0], color=col_sc, s=40, zorder=5)
        ax2.set_title("Smith Chart – Γ_in")
        ax2.legend(fontsize=8)
        st.pyplot(fig2)
        plt.close(fig2)

with col2:
    # ── Diagnosis card ────────────────────────────────────────────────────
    st.subheader("🔍 Diagnosis")
    diag_label = dx['diagnosis']
    conf = dx['confidence']
    color_map = {
        'high': '🟢', 'medium': '🟡', 'low': '🔴'
    }
    st.metric("Diagnosis", diag_label)
    st.metric("Confidence", f"{color_map.get(conf, '')} {conf}")

    with st.expander("Rules fired & notes"):
        for r in dx['rules_fired']:
            st.write(f"• Rule {r}")
        for n in dx['notes']:
            st.info(n)

    with st.expander("Feature values"):
        feat = dx['features']
        for k, v in feat.items():
            st.write(f"**{k}**: {v:.5f}" if isinstance(v, float) else f"**{k}**: {v}")

    # ── Location card ─────────────────────────────────────────────────────
    st.subheader("📍 Fault Location")
    d1 = loc['method1_dist']
    d2 = loc['method2_dist']
    rr = loc['range_res']
    ur = loc['unambig_range']

    if loc['reliable']:
        st.success(f"Estimated distance (IFFT): **{d1*100:.2f} cm**")
    else:
        st.warning(f"Estimate unreliable. IFFT: {d1*100:.2f} cm")

    st.write(f"Phase-slope (cross-check): {d2*100:.2f} cm" if not np.isnan(d2) else "Phase estimate: N/A")
    st.write(f"Range resolution: {rr*100:.2f} cm")
    st.write(f"Unambiguous range: {ur:.1f} m" if not np.isinf(ur) else "Unambiguous range: ∞")

    for w in loc['warnings']:
        st.caption(f"⚠️ {w}")

    # IFFT plot
    if HAS_MPL and len(loc['t_axis']) > 0:
        vp_disp = VF * C_LIGHT
        d_cm = loc['t_axis'] * vp_disp / 2.0 * 100
        half = len(d_cm) // 2
        fig3, ax3 = plt.subplots(figsize=(6, 3))
        ax3.plot(d_cm[:half], loc['ifft_mag'][:half], 'b-', linewidth=1)
        pidx = loc['peak_idx']
        if 0 <= pidx < half:
            ax3.axvline(d_cm[pidx], color='r', linestyle='--',
                        label=f"Peak @ {d_cm[pidx]:.1f} cm")
        if scenario != 'healthy_matched':
            ax3.axvline(fault_pos * 100, color='g', linestyle='--',
                        label=f"True @ {fault_pos*100:.1f} cm")
        ax3.set_xlabel('Distance (cm)')
        ax3.set_ylabel('|IFFT(S11)|')
        ax3.set_title('Time-Domain (IFFT) Response')
        ax3.legend(fontsize=7)
        ax3.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

    # Key metrics table
    st.subheader("Key Metrics (at mean freq)")
    mean_gamma = float(np.mean(np.abs(S11)))
    mean_vswr  = vswr_from_gamma(mean_gamma)
    mean_rl    = return_loss_db(mean_gamma)
    st.table({
        'Metric': ['Mean |Γ|', 'Mean VSWR', 'Mean RL (dB)'],
        'Value':  [f"{mean_gamma:.4f}", f"{mean_vswr:.2f}", f"{mean_rl:.2f}"],
    })

# ── Quarter-wave matching section ─────────────────────────────────────────────
if do_match:
    st.divider()
    st.subheader("⚡ Quarter-Wave Impedance Matching")
    freqs_match = np.linspace(f_start, f_stop, n_pts)
    m_res = quarter_wave_match(Z0, complex(ZL_match), f0_match, freqs_match, VF)

    if not m_res['valid']:
        st.error(m_res['error_msg'])
    else:
        st.success(
            f"Transformer: Zt = {m_res['Zt']:.2f} Ω, "
            f"lt = {m_res['lt']*100:.2f} cm, "
            f"Usable BW = {m_res['bandwidth_hz']/1e6:.1f} MHz "
            f"(RL ≥ {m_res['rl_threshold']:.0f} dB)"
        )
        if HAS_MPL:
            fig4, axes4 = plt.subplots(1, 3, figsize=(14, 4))
            f_ghz_m = freqs_match / 1e9
            f0_ghz  = f0_match / 1e9
            for ax4, key, ylabel in zip(axes4,
                                         ['Gamma', 'VSWR', 'RL_dB'],
                                         ['|Γ|', 'VSWR', 'RL (dB)']):
                ax4.plot(f_ghz_m, m_res['before'][key], 'r-', label='Before', lw=2)
                ax4.plot(f_ghz_m, m_res['after'][key],  'g-', label='After',  lw=2)
                ax4.axvline(f0_ghz, color='k', ls='--', alpha=0.5, label=f'f₀={f0_ghz:.1f}')
                ax4.set_xlabel('Freq (GHz)')
                ax4.set_ylabel(ylabel)
                ax4.legend(fontsize=7)
                ax4.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig4)
            plt.close(fig4)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "IIT Undergraduate Project | Simulated results only | "
    "Reference: Pozar, *Microwave Engineering*, 4th ed."
)

