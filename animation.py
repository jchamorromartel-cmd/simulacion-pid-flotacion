"""Reproductor HTML/SVG local: las únicas trayectorias son muestras del motor."""
import json
from pathlib import Path


def animation_html(runs, config):
    keys = ['t', 'qfeed', 'sp'] + [f'{name}{i}' for i in (1, 2, 3)
                                  for name in ('h', 'qin', 'qout', 'cmd', 'sat')]
    data = {mode: [{k: row[k] for k in keys} for row in rows] for mode, rows in runs.items()}
    payload = json.dumps({'runs': data, 'dt': config.dt}, ensure_ascii=True, allow_nan=False).replace('<', '\\u003c')
    template = (Path(__file__).parent / 'assets' / 'animation.html').read_text(encoding='utf-8')
    return template.replace('__SIMULATION_DATA__', payload)
