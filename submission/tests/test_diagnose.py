"""
Unit Tests – Diagnosis and Location modules.
"""
import sys, os, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.simulate import build_scenario, SCENARIO_NAMES
from src.diagnose import diagnose
from src.locate   import locate_fault
from src.matching import quarter_wave_match


class TestDiagnose(unittest.TestCase):

    def setUp(self):
        self.freqs = np.linspace(1e9, 3e9, 200)
        self.Z0 = 50.0

    def _diag(self, name, **kw):
        rec = build_scenario(name, self.Z0, 0.3, self.freqs, **kw)
        S11 = rec['results']['S11']
        return diagnose(S11, self.freqs, self.Z0)

    def test_healthy_matched(self):
        d = self._diag('healthy_matched')
        self.assertEqual(d['diagnosis'], 'healthy_matched')

    def test_open_circuit(self):
        d = self._diag('open_circuit')
        self.assertIn(d['diagnosis'], ['open_circuit', 'uncertain'])

    def test_short_circuit(self):
        d = self._diag('short_circuit')
        self.assertIn(d['diagnosis'], ['short_circuit', 'uncertain'])

    def test_wrong_load(self):
        d = self._diag('wrong_load', ZL_wrong=complex(150))
        self.assertIn(d['diagnosis'], ['wrong_load', 'uncertain'])

    def test_series_L(self):
        d = self._diag('series_L', L_val=30e-9)
        self.assertIn(d['diagnosis'], ['series_L', 'uncertain'])

    def test_shunt_C(self):
        d = self._diag('shunt_C', C_val=30e-12)
        self.assertIn(d['diagnosis'], ['shunt_C', 'uncertain'])

    def test_confidence_returned(self):
        d = self._diag('healthy_matched')
        self.assertIn(d['confidence'], ['high', 'medium', 'low'])


class TestLocate(unittest.TestCase):

    def setUp(self):
        self.freqs = np.linspace(1e9, 5e9, 500)
        self.Z0 = 50.0
        self.VF = 0.66

    def test_locate_short_circuit(self):
        true_pos = 0.15   # m
        rec = build_scenario('short_circuit', self.Z0, 0.3, self.freqs,
                             VF=self.VF)
        S11 = rec['results']['S11']
        loc = locate_fault(S11, self.freqs, self.VF)
        # Should produce a numeric estimate
        self.assertFalse(np.isnan(loc['method1_dist']))

    def test_locate_returns_range_res(self):
        rec = build_scenario('open_circuit', self.Z0, 0.3, self.freqs, VF=self.VF)
        S11 = rec['results']['S11']
        loc = locate_fault(S11, self.freqs, self.VF)
        self.assertGreater(loc['range_res'], 0)

    def test_single_freq_returns_uncertain(self):
        S11   = np.array([complex(0.5, 0.1)])
        freqs = np.array([1e9])
        loc = locate_fault(S11, freqs, 1.0)
        self.assertFalse(loc['reliable'])


class TestMatching(unittest.TestCase):

    def setUp(self):
        self.Z0 = 50.0
        self.freqs = np.linspace(0.5e9, 2.5e9, 300)
        self.f0 = 1.5e9

    def test_valid_match_100_ohm(self):
        res = quarter_wave_match(self.Z0, complex(100), self.f0, self.freqs)
        self.assertTrue(res['valid'])
        self.assertAlmostEqual(res['Zt'], np.sqrt(50 * 100), places=4)

    def test_exact_at_f0(self):
        res = quarter_wave_match(self.Z0, complex(100), self.f0, self.freqs)
        self.assertTrue(res['at_f0_exact'])

    def test_complex_load_rejected(self):
        res = quarter_wave_match(self.Z0, complex(75, 30), self.f0, self.freqs)
        self.assertFalse(res['valid'])
        self.assertIn('complex', res['error_msg'].lower())

    def test_negative_load_rejected(self):
        res = quarter_wave_match(self.Z0, complex(-50), self.f0, self.freqs)
        self.assertFalse(res['valid'])

    def test_before_gamma_constant(self):
        """Before matching, |Gamma| should be constant (no freq dep for pure R)."""
        res = quarter_wave_match(self.Z0, complex(100), self.f0, self.freqs)
        before_g = res['before']['Gamma']
        self.assertAlmostEqual(float(np.std(before_g)), 0.0, places=6)

    def test_bandwidth_positive(self):
        res = quarter_wave_match(self.Z0, complex(200), self.f0, self.freqs)
        self.assertGreaterEqual(res['bandwidth_hz'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

