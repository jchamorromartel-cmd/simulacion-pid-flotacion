import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_default_and_alternate_configs(self):
        app = AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=60)
        self.assertFalse(app.exception, str(app.exception))
        self.assertEqual(len(app.tabs), 9)
        self.assertGreaterEqual(len(app.dataframe), 4)
        app.selectbox[0].select('Identificado del artículo').run(timeout=60)
        self.assertFalse(app.exception, str(app.exception))
        app.checkbox[0].check().run(timeout=60)
        self.assertFalse(app.exception, str(app.exception))
        app.selectbox[1].select(0.5).run(timeout=60)
        self.assertFalse(app.exception, str(app.exception))


if __name__ == '__main__':
    unittest.main()
