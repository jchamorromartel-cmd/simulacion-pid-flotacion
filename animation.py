"""Puente entre el motor Python y el reproductor HTML/SVG.

No integra balances ni calcula PID. Se envían resultados de simulation.simulate
al navegador para que los controles recorran las mismas muestras que los gráficos.
"""
import json
from pathlib import Path


def animation_html(runs, config):
    """Devolver HTML autocontenido con ambas estrategias y su paso temporal.

    runs: diccionario estrategia -> registros calculados por el motor.
    config: aporta dt para convertir tiempo de reproducción a índice de muestra.
    Se incluyen niveles, SP, entradas, salidas, órdenes y saturación; el resto
    de los términos PID permanece en los CSV, sin aumentar el contenido enviado.
    """
    keys = ['t', 'qfeed', 'sp'] + [f'{name}{i}' for i in (1, 2, 3)
                                  for name in ('h', 'qin', 'qout', 'cmd', 'sat')]
    # Seleccionar campos sin redondear: el formato visual a dos decimales se hace
    # en JavaScript, manteniendo los datos originales para recorrer la trayectoria.
    data = {mode: [{k: row[k] for k in keys} for row in rows] for mode, rows in runs.items()}
    # JSON estricto rechaza NaN/Infinity. Escapar '<' impide cerrar accidentalmente
    # el script contenedor. La plantilla es local y los datos proceden del motor.
    payload = json.dumps({'runs': data, 'dt': config.dt}, ensure_ascii=True, allow_nan=False).replace('<', '\\u003c')
    # Resolver la ruta respecto a este módulo permite ejecutar desde Cloud o tests.
    template = (Path(__file__).parent / 'assets' / 'animation.html').read_text(encoding='utf-8')
    return template.replace('__SIMULATION_DATA__', payload)
