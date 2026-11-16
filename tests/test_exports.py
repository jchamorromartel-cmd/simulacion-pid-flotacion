import csv
import json
import re
import unittest
from dataclasses import replace
from io import BytesIO, StringIO
from pypdf import PdfReader
from simulation import Config, simulate
from reporting import csv_bytes, comparison, pdf_report
from animation import animation_html


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Config()
        cls.runs = {'PID': simulate(cls.c), 'PID + FF': simulate(cls.c, True)}

    def test_csv_roundtrip(self):
        for label, rows in self.runs.items():
            data = list(csv.DictReader(StringIO(csv_bytes(rows).decode('utf-8-sig'))))
            self.assertEqual(len(data), len(rows))
            for a, b in zip(data, rows):
                self.assertAlmostEqual(float(a['h3']), b['h3'])
                self.assertEqual(float(a['t']), b['t'])

    def test_animation_uses_actual_model_samples(self):
        html = animation_html(self.runs, self.c)
        raw = re.search(r'const payload=(.*);\n', html).group(1)
        payload = json.loads(raw)
        for label in self.runs:
            for i in (0, 180, 195, 280, 600):
                self.assertEqual(payload['runs'][label][i]['h2'], self.runs[label][i]['h2'])
                self.assertEqual(payload['runs'][label][i]['cmd3'], self.runs[label][i]['cmd3'])
        self.assertNotIn('__SIMULATION_DATA__', html)

    def test_pdf_is_readable_and_contains_method_and_results(self):
        b = pdf_report(self.c, self.runs)
        self.assertTrue(b.startswith(b'%PDF-'))
        reader = PdfReader(BytesIO(b))
        self.assertGreaterEqual(len(reader.pages), 8)
        text = '\n'.join(p.extract_text() for p in reader.pages)
        for term in ('0.09', '0.001018', '365.323', '80.112', '56', 'Back-calculation', 'Referencias'):
            self.assertIn(term, text)
        self.assertGreater(len(reader.pages[-1].get_contents().get_data()), 100)

    def test_pdf_alternate_model_and_no_disturbance(self):
        for c in (replace(self.c, model='paper'), replace(self.c, disturbance=0)):
            b = pdf_report(c, {'PID': simulate(c), 'PID + FF': simulate(c, True)})
            text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(b)).pages)
            self.assertIn('Conclusiones', text)

    def test_comparison_zero_and_normal(self):
        normal = comparison(self.runs, self.c)
        self.assertTrue(all(r['Mejora IAE (cm s) (%)'] > 70 for r in normal))
        c = replace(self.c, disturbance=0)
        zero = comparison({'PID': simulate(c), 'PID + FF': simulate(c, True)}, c)
        self.assertTrue(all(r['Mejora IAE (cm s) (%)'] is None for r in zero))


if __name__ == '__main__':
    unittest.main()
