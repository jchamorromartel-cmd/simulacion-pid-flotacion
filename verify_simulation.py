"""Pruebas reproducibles sin dependencias: python verify_simulation.py."""
from dataclasses import replace
from pathlib import Path
import csv
import json
import unittest
from simulation import Config, simulate, metrics, tuning, KC


class SimulationTests(unittest.TestCase):
    def test_equilibrium(self):
        for model in ('balance', 'paper'):
            for ff in (False, True):
                rows = simulate(Config(model=model, disturbance=0), ff)
                self.assertTrue(all(r[f'h{i}'] == 30 and r[f'qout{i}'] == 45 for r in rows for i in (1, 2, 3)))

    def test_recovery_and_feedforward(self):
        for model in ('balance', 'paper'):
            c = Config(model=model, duration=900)
            pid, ff = [metrics(simulate(c, mode), c) for mode in (False, True)]
            for a, b in zip(pid, ff):
                self.assertLess(a['Error final (cm)'], 0.001)
                self.assertLess(b['IAE (cm s)'], a['IAE (cm s)'])
                self.assertEqual(a['Saturación (%)'], 0)
                self.assertLess(a['Oscilación final bomba (L/min)'], 0.01)

    def test_noise_and_larger_pulse(self):
        for model in ('balance', 'paper'):
            for ff in (False, True):
                c = Config(model=model, duration=900, disturbance=25, noise=True)
                for m in metrics(simulate(c, ff), c):
                    self.assertLess(m['Error final (cm)'], 0.1)
                    # Picos transitorios permitidos con ruido; no ciclo sostenido.
                    self.assertLess(m['Saturación (%)'], 1)

    def test_antiwindup_after_infeasible_pulse(self):
        c = Config(duration=1800, disturbance=70)
        for ff in (False, True):
            rows = simulate(c, ff)
            self.assertTrue(any(r['sat1'] for r in rows))
            self.assertTrue(all(0 <= r[f'cmd{i}'] <= 100 for r in rows for i in (1, 2, 3)))
            for m in metrics(rows, c):
                self.assertLess(m['Error final (cm)'], 0.001)
                self.assertLess(m['Oscilación final bomba (L/min)'], 0.01)

    def test_delay_sign_and_derivative(self):
        c = Config(initial_level=31, duration=40, disturbance=0)
        rows = simulate(c)
        self.assertGreater(rows[0]['cmd1'], 45)  # nivel alto -> más salida
        self.assertTrue(all(r['qout1'] == 45 for r in rows[:7]))
        self.assertEqual(rows[7]['qout1'], rows[0]['cmd1'])
        self.assertNotEqual(rows[8]['d1'], 0)  # PV cambia después del retardo
        self.assertEqual(tuning(Config(model='paper')), KC)
        # Escalón de SP no genera golpe derivativo: PV aún constante.
        step = simulate(Config(sp=31, initial_level=30, disturbance=0))
        self.assertEqual(step[0]['d1'], 0)

    def test_gain_mismatch_still_oscillates_with_antiwindup(self):
        c = Config(original_tuning=True)
        for m in metrics(simulate(c), c):
            self.assertGreater(m['Saturación (%)'], 50)
            self.assertEqual(m['Oscilación final bomba (L/min)'], 100)

    def test_time_step_convergence(self):
        c = Config()
        a = metrics(simulate(c), c)
        fine = replace(c, dt=0.5)
        b = metrics(simulate(fine), fine)
        for x, y in zip(a, b):
            self.assertLess(abs(x['IAE (cm s)']-y['IAE (cm s)'])/y['IAE (cm s)'], 0.06)


def report():
    output = Path('results')
    output.mkdir(exist_ok=True)
    diagnostic = Config(original_tuning=True)
    summary = {'balance_incompatible_Kc_diagnostic': metrics(simulate(diagnostic), diagnostic)}
    charts = []
    for model in ('balance', 'paper'):
        c = Config(model=model)
        runs = {}
        for label, ff in [('PID', False), ('PID_FF', True)]:
            rows = simulate(c, ff)
            runs[label] = rows
            summary[f'{model}_{label}'] = metrics(rows, c)
            with (output / f'{model}_{label}.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0])
                writer.writeheader()
                writer.writerows(rows)
        for variable, lo, hi in [('h', 26, 35), ('qout', 0, 100)]:
            for i in (1, 2, 3):
                lines = []
                for label, color in [('PID', '#e67700'), ('PID_FF', '#007c91')]:
                    points = ' '.join(f'{50+r["t"]:.2f},{220-(r[f"{variable}{i}"]-lo)/(hi-lo)*180:.2f}' for r in runs[label])
                    lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
                charts.append(f'<h3>{model}: {variable}{i} ({"cm" if variable == "h" else "L/min"})</h3><svg viewBox="0 0 700 250"><path d="M50 30V220H650" fill="none" stroke="black"/><text x="5" y="40">{hi}</text><text x="5" y="220">{lo}</text><text x="50" y="245">0 s</text><text x="620" y="245">600 s</text>{"".join(lines)}</svg>')
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Verificación PID</title><style>body{font:16px sans-serif;max-width:900px;margin:auto}svg{width:100%;border:1px solid #ddd}</style><h1>Comparación PID y PID + FF</h1><p>Pulso +12 L/min de 180 a 280 s. Naranja: PID; azul: PID + FF. Valores y métricas completos en CSV y summary.json.</p>'+''.join(charts), encoding='utf-8')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SimulationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    report()
