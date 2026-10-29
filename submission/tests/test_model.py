"""
Unit Tests – Transmission-Line Model
=====================================
All reference values were computed by hand or by substituting symbolic
expressions (shown inline as comments) before running the code.

Hand-calculation examples:
  1. Matched 50Ω: Z0=ZL=50, any β, any l → Zin=50 exactly
     Proof: tanh arg in numerator and denominator cancel => Zin = Z0.

  2. Open-circuit, quarter-wave: ZL→∞, βl=π/2
     Zin = Z0*(ZL + jZ0*tan(π/2))/(Z0 + jZL*tan(π/2))
     ABCD: tanh(jπ/2) = j*tan(π/2) → ∞ limit → Zin = Z0²/ZL → 0
     Numerically: ZL=1e9 Ω, l=λ/4 → Zin ≈ Z0²/ZL = 2500/1e9 ≈ 0 Ω.

  3. Short-circuit, half-wave: ZL=0, βl=π
     Zin = Z0*(0 + jZ0*tan(π))/(Z0 + j*0*tan(π)) = 0 (tan π = 0)
     => Zin = 0. Short is reproduced at input for half-wave length.

  4. Gamma: ZL=100, Z0=50 → Γ=(100-50)/(100+50)=50/150=1/3≈0.333
     VSWR = (1+1/3)/(1-1/3) = (4/3)/(2/3) = 2.0
     RL = -20*log10(1/3) = 20*log10(3) ≈ 9.54 dB
"""

import sys
import os
import unittest
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.model import (zin_scalar, zin_abcd_scalar, gamma_from_z,
                        vswr_from_gamma, return_loss_db,
                        verify_abcd_vs_closedform, C_LIGHT, _LARGE_ZL, sweep)
from src.simulate import build_scenario, SCENARIO_NAMES, generate_dataset
from src.diagnose import diagnose


class TestMatchedLine(unittest.TestCase):
    """Matched line: ZL = Z0 => Zin = Z0 for any f and l."""

    def _check(self, Z0, f_hz, l_m, VF=1.0):
        Zin = zin_scalar(Z0, complex(Z0), l_m, f_hz, VF)
        self.assertAlmostEqual(Zin.real, Z0, places=6,
            msg=f"Matched line Zin.real ≠ Z0 at Z0={Z0},f={f_hz},l={l_m}")
        self.assertAlmostEqual(Zin.imag, 0.0, places=6,
            msg=f"Matched line Zin.imag ≠ 0 at Z0={Z0},f={f_hz},l={l_m}")

    def test_50ohm_1GHz(self):
        self._check(50, 1e9, 0.1)

    def test_75ohm_500MHz(self):
        self._check(75, 500e6, 0.25)

    def test_100ohm_2GHz(self):
        self._check(100, 2e9, 0.5)

    def test_long_line(self):
        self._check(50, 1e9, 10.0)

    def test_with_attenuation(self):
        """Matched line with attenuation still gives Zin ≈ Z0."""
        Zin = zin_scalar(50, complex(50), 0.1, 1e9, 1.0, alpha=0.01)
        self.assertAlmostEqual(Zin.real, 50.0, places=3)


class TestOpenShortCircuit(unittest.TestCase):
    """Open and short-circuit boundary conditions."""

    def test_open_circuit_halfwave(self):
        """Open circuit reproduced at input for half-wave line."""
        Z0, f = 50.0, 1e9
        vp = C_LIGHT
        l = vp / (2 * f)   # half wavelength
        Zin = zin_scalar(Z0, complex(_LARGE_ZL), l, f)
        # Should be very large (open reproduced)
        self.assertGreater(abs(Zin), 1e6,
            msg=f"Open half-wave Zin={Zin} should be very large")

    def test_open_circuit_quarterwave(self):
        """Open circuit transforms to short circuit through quarter-wave."""
        Z0, f = 50.0, 1e9
        vp = C_LIGHT
        l = vp / (4 * f)   # quarter wavelength
        Zin = zin_scalar(Z0, complex(_LARGE_ZL), l, f)
        # Zin ≈ Z0^2/ZL → 0 (near short)
        self.assertLess(abs(Zin), 10.0,
            msg=f"Open quarter-wave Zin={abs(Zin)} should be near 0")

    def test_short_circuit_halfwave(self):
        """Short circuit reproduced at input for half-wave line."""
        Z0, f = 50.0, 1e9
        vp = C_LIGHT
        l = vp / (2 * f)
        ZL = complex(1e-9, 0.0)   # near-zero
        Zin = zin_scalar(Z0, ZL, l, f)
        self.assertLess(abs(Zin), 1e-3,
            msg=f"Short half-wave Zin={abs(Zin):.6e} should be near 0")

    def test_short_circuit_quarterwave(self):
        """Short circuit transforms to open through quarter-wave."""
        Z0, f = 50.0, 1e9
        vp = C_LIGHT
        l = vp / (4 * f)
        ZL = complex(1e-9, 0.0)
        Zin = zin_scalar(Z0, ZL, l, f)
        self.assertGreater(abs(Zin), 1e3,
            msg=f"Short quarter-wave Zin={abs(Zin):.2e} should be large")


class TestReflectionCoefficient(unittest.TestCase):
    """
    Hand-calculated Gamma, VSWR, RL reference cases.
    Ref: Pozar §2.3
    """

    def test_gamma_100_ohm_load(self):
        """ZL=100, Z0=50: Gamma=(100-50)/(100+50)=1/3"""
        G = gamma_from_z(complex(100), 50.0)
        self.assertAlmostEqual(abs(G), 1 / 3, places=6)

    def test_gamma_matched(self):
        """ZL=Z0=50: Gamma=0"""
        G = gamma_from_z(complex(50), 50.0)
        self.assertAlmostEqual(abs(G), 0.0, places=10)

    def test_gamma_open(self):
        """ZL=inf: Gamma=+1"""
        G = gamma_from_z(complex(_LARGE_ZL), 50.0)
        self.assertAlmostEqual(abs(G), 1.0, delta=0.01)

    def test_gamma_short(self):
        """ZL=0: Gamma=-1"""
        G = gamma_from_z(complex(1e-9), 50.0)
        self.assertAlmostEqual(abs(G), 1.0, delta=0.01)

    def test_vswr_2(self):
        """Gamma=1/3 => VSWR=2"""
        vswr = vswr_from_gamma(1 / 3)
        self.assertAlmostEqual(vswr, 2.0, places=6)

    def test_return_loss_100ohm(self):
        """ZL=100, Z0=50: RL = 20*log10(3) ≈ 9.5424 dB"""
        rl = return_loss_db(1 / 3)
        self.assertAlmostEqual(rl, 20 * np.log10(3), places=5)

    def test_return_loss_matched(self):
        """Matched: RL = inf (capped to floor)"""
        rl = return_loss_db(0.0)
        self.assertGreater(rl, 100)   # large positive number

    def test_vswr_capped(self):
        """VSWR is capped and never returns inf/NaN for |Gamma|=1."""
        vswr = vswr_from_gamma(1.0)
        self.assertFalse(np.isnan(vswr))
        self.assertFalse(np.isinf(vswr))
        self.assertGreater(vswr, 1e4)


class TestABCDVerification(unittest.TestCase):
    """ABCD cascade must agree with closed-form to 1e-9."""

    def _verify(self, Z0, ZL, l, f, VF=1.0):
        verify_abcd_vs_closedform(Z0, ZL, l, f, VF, tol=1e-9)

    def test_matched_50(self):
        self._verify(50, complex(50), 0.15, 1e9)

    def test_mismatch(self):
        self._verify(50, complex(100), 0.2, 2e9)

    def test_reactive_load(self):
        self._verify(50, complex(0, 75), 0.1, 1e9)

    def test_open_approx(self):
        self._verify(50, complex(1e8), 0.1, 1e9)


class TestFrequencySweep(unittest.TestCase):
    """Sweep returns expected shapes and physical values."""

    def test_sweep_shapes(self):
        freqs = np.linspace(1e9, 3e9, 100)
        res = sweep(50, complex(50), 0.2, freqs)
        for key in ('freqs', 'Zin', 'Gamma_in', 'VSWR', 'RL_dB', 'S11'):
            self.assertEqual(res[key].shape, (100,), msg=f"Shape mismatch for {key}")

    def test_matched_sweep_gamma_near_zero(self):
        freqs = np.linspace(1e9, 3e9, 50)
        res = sweep(50, complex(50), 0.2, freqs)
        self.assertLess(np.max(np.abs(res['S11'])), 1e-6)

    def test_open_sweep_gamma_near_one(self):
        freqs = np.linspace(0.1e9, 3e9, 50)
        res = sweep(50, complex(1e9), 0.2, freqs)
        self.assertGreater(np.mean(np.abs(res['S11'])), 0.9)

    def test_noise_adds_and_clips(self):
        freqs = np.linspace(1e9, 3e9, 50)
        rng = np.random.default_rng(0)
        res = sweep(50, complex(50), 0.2, freqs, noise_std=0.5, rng=rng)
        # All |S11| must remain <= 1
        self.assertTrue(np.all(np.abs(res['S11']) <= 1.0001))

    def test_vswr_lower_bounded_one(self):
        freqs = np.linspace(1e9, 3e9, 50)
        res = sweep(50, complex(50), 0.2, freqs)
        self.assertTrue(np.all(res['VSWR'] >= 1.0))

    def test_no_nan_in_open(self):
        freqs = np.linspace(1e9, 3e9, 200)
        res = sweep(50, complex(1e9), 0.2, freqs)
        for key in ('Zin', 'Gamma_in', 'VSWR', 'RL_dB'):
            self.assertFalse(np.any(np.isnan(res[key].real)),
                             msg=f"NaN in {key}")

    def test_no_nan_in_short(self):
        freqs = np.linspace(1e9, 3e9, 200)
        res = sweep(50, complex(1e-9), 0.2, freqs)
        for key in ('Zin', 'Gamma_in', 'VSWR', 'RL_dB'):
            self.assertFalse(np.any(np.isnan(res[key].real)),
                             msg=f"NaN in {key}")


class TestScenarioBuilder(unittest.TestCase):
    """Scenario builder creates correct scenario structure."""

    def test_all_scenarios_exist(self):
        freqs = np.linspace(1e9, 3e9, 50)
        for name in SCENARIO_NAMES:
            rec = build_scenario(name, 50, 0.2, freqs)
            self.assertIn('results', rec)
            self.assertIn('truth', rec)

    def test_healthy_low_gamma(self):
        freqs = np.linspace(1e9, 3e9, 50)
        rec = build_scenario('healthy_matched', 50, 0.2, freqs)
        mean_g = np.mean(np.abs(rec['results']['S11']))
        self.assertLess(mean_g, 0.01)

    def test_open_high_gamma(self):
        freqs = np.linspace(1e9, 3e9, 50)
        rec = build_scenario('open_circuit', 50, 0.2, freqs)
        mean_g = np.mean(np.abs(rec['results']['S11']))
        self.assertGreater(mean_g, 0.9)

    def test_truth_label_matches_name(self):
        freqs = np.linspace(1e9, 3e9, 50)
        for name in SCENARIO_NAMES:
            rec = build_scenario(name, 50, 0.2, freqs)
            self.assertEqual(rec['truth']['scenario'], name)


class TestDiagnoseInterfaceContract(unittest.TestCase):
    """
    Critical: diagnose() must NOT have access to ZL, fault_pos, or any
    ground-truth data in its signature or implementation.
    This test checks the function signature strictly.
    """

    def test_diagnose_signature_no_groundtruth(self):
        import inspect
        sig = inspect.signature(diagnose)
        param_names = list(sig.parameters.keys())
        forbidden = ['ZL', 'fault_pos', 'label', 'truth',
                     'ground_truth', 'true_label']
        for f in forbidden:
            self.assertNotIn(f, param_names,
                msg=f"diagnose() must NOT have parameter '{f}' (ground-truth leak)")

    def test_diagnose_takes_only_s11_freqs_z0(self):
        import inspect
        sig = inspect.signature(diagnose)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ['S11', 'freqs', 'Z0'],
            msg=f"diagnose() parameters should be [S11, freqs, Z0], got {params}")

    def test_diagnose_returns_dict(self):
        freqs = np.linspace(1e9, 3e9, 50)
        S11 = np.zeros(50, dtype=complex)
        res = diagnose(S11, freqs, 50.0)
        self.assertIsInstance(res, dict)
        for key in ('diagnosis', 'confidence', 'features', 'rules_fired', 'notes'):
            self.assertIn(key, res, msg=f"Missing key '{key}' in diagnose output")

    def test_healthy_diagnosed_correctly(self):
        freqs = np.linspace(1e9, 3e9, 50)
        rec = build_scenario('healthy_matched', 50, 0.2, freqs)
        S11 = rec['results']['S11']
        res = diagnose(S11, freqs, 50.0)
        self.assertEqual(res['diagnosis'], 'healthy_matched')

    def test_dataset_labels_separate_from_S11(self):
        """
        Verify dataset records carry truth and results as separate keys.
        The S11 array must not be the same object as any truth field.
        """
        freqs = np.linspace(1e9, 3e9, 20)
        dataset = generate_dataset(50, 0.2, freqs, n_per_class=2, seed=7)
        for rec in dataset:
            self.assertIn('results', rec)
            self.assertIn('truth', rec)
            # truth dict should NOT contain S11
            self.assertNotIn('S11', rec['truth'])
            # results should NOT contain 'scenario' (truth label)
            self.assertNotIn('scenario', rec['results'])


class TestVariousImpedances(unittest.TestCase):
    """Additional hand-calculated reference cases."""

    def test_50_to_75_gamma(self):
        """Z0=50, ZL=75: Gamma=(75-50)/(75+50)=25/125=0.2"""
        G = gamma_from_z(complex(75), 50.0)
        self.assertAlmostEqual(abs(G), 0.2, places=6)
        vswr = vswr_from_gamma(0.2)
        self.assertAlmostEqual(vswr, 1.5, places=6)

    def test_reactive_load_gamma_magnitude(self):
        """Z0=50, ZL=j50: |Gamma|=(j50-50)/(j50+50) => |Gamma|=1 (pure reactive)"""
        G = gamma_from_z(complex(0, 50), 50.0)
        self.assertAlmostEqual(abs(G), 1.0, places=6)

    def test_zin_no_nan_at_singularity(self):
        """Test that near-singularity (tan(βl)→∞) does not produce NaN."""
        Z0 = 50.0
        ZL = complex(75)
        f = 1e9
        vp = C_LIGHT
        # Approach quarter-wave length (singularity for finite ZL)
        l_qw = vp / (4 * f)
        for factor in [0.999, 1.0, 1.001]:
            Zin = zin_scalar(Z0, ZL, l_qw * factor, f)
            self.assertFalse(np.isnan(Zin.real),
                msg=f"NaN at factor={factor}")
            self.assertFalse(np.isinf(Zin.real),
                msg=f"Inf at factor={factor}")


if __name__ == '__main__':
    unittest.main(verbosity=2)

