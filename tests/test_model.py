import math
import unittest
from dataclasses import replace
from simulation import Config, simulate, metrics, BALANCE_GAIN, AREA_M2, HEIGHT_M, Q_BASE


class ModelTests(unittest.TestCase):
    def test_geometry_and_local_volume_balance(self):
        self.assertAlmostEqual(AREA_M2, 0.09)
        self.assertAlmostEqual(AREA_M2*HEIGHT_M*1000, 40.5)
        c = Config(dt=0.5)
        rows = simulate(c, True)
        for a, b in zip(rows, rows[1:]):
            for i in (1, 2, 3):
                change_litres = (b[f'h{i}']-a[f'h{i}'])*0.9
                net_litres = c.dt*(a[f'qin{i}']-a[f'qout{i}'])/60
                self.assertAlmostEqual(change_litres, net_litres, places=12)
            # Conexiones y conservación de todo el banco.
            self.assertEqual(a['qin2'], a['qout1'])
            self.assertEqual(a['qin3'], a['qout2'])
            self.assertAlmostEqual(sum((b[f'h{i}']-a[f'h{i}'])*0.9 for i in (1, 2, 3)),
                                   c.dt*(a['qfeed']-a['qout3'])/60, places=12)

    def test_recorded_pid_and_antiwindup_reconstruct_order(self):
        c = Config(disturbance=70, duration=900)
        rows = simulate(c, True)
        saturated = 0
        for r in rows:
            for i in (1, 2, 3):
                self.assertAlmostEqual(r[f'raw{i}'], Q_BASE+r[f'p{i}']+r[f'i{i}']+r[f'd{i}']+r[f'ff{i}'])
                self.assertEqual(r[f'cmd{i}'], min(100, max(0, r[f'raw{i}'])))
                if r[f'sat{i}']:
                    saturated += 1
                    correction = (r[f'cmd{i}']-r[f'raw{i}'])/(c.ti[i-1]/2)
                    self.assertLess(correction*(r[f'raw{i}']-r[f'cmd{i}']), 0)
        self.assertGreater(saturated, 0)

    def test_analytic_constant_error_metrics(self):
        c = Config(duration=100, disturbance_at=0, disturbance_duration=10)
        records = []
        for t in range(101):
            r = {'t': t}
            for i in (1, 2, 3):
                r.update({f'h{i}': 32, f'qout{i}': 45, f'sat{i}': False})
            records.append(r)
        for m in metrics(records, c):
            self.assertEqual(m['IAE (cm s)'], 200)
            self.assertEqual(m['ISE (cm² s)'], 400)
            self.assertEqual(m['Sobreimpulso (cm)'], 2)
            self.assertAlmostEqual(m['Sobreimpulso sobre SP (%)'], 100*2/30)
            self.assertIsNone(m['Recuperación ±0.1 cm tras retiro (s)'])

    def test_short_or_absent_recovery_is_not_claimed(self):
        for c in (Config(duration=180), Config(duration=300)):
            for m in metrics(simulate(c), c):
                self.assertIsNone(m['Recuperación ±0.1 cm tras retiro (s)'])

    def test_negative_disturbance_and_all_dt(self):
        for dt in (1, 0.5, 0.25):
            c = Config(dt=dt, disturbance=-12)
            for m in metrics(simulate(c, True), c):
                self.assertLess(m['Error final (cm)'], 0.001)
                self.assertEqual(m['Saturación (%)'], 0)

    def test_invalid_parameters(self):
        c = Config()
        for changes in ({'dt': 0}, {'dt': 0.3}, {'td': -1}, {'ti': (0, 30, 44)},
                        {'kff': (1, 2, 3)}, {'disturbance': -46}, {'filter_time': 0},
                        {'sp': math.nan}, {'duration': 10.2}, {'model': 'invalid'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                simulate(replace(c, **changes))


if __name__ == '__main__':
    unittest.main()
