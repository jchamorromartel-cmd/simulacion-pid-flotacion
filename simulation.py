"""Motor independiente de Streamlit; unidades: cm, s y L/min."""
from collections import deque
from dataclasses import dataclass
import math
import random

KC = (-62.0, -76.0, -85.0)
TI = (56.0, 30.0, 44.0)
THETA = (7.0, 6.0, 3.0)
KFF = (0.8, 0.8, 1.0)
PAPER_GAIN = 0.001018  # magnitud de k' identificado, tabla 2
BALANCE_GAIN = 1000.0 / (60.0 * 900.0)
Q_BASE, Q_MIN, Q_MAX = 45.0, 0.0, 100.0
AREA_M2, HEIGHT_M = 0.30 * 0.30, 0.45
AREA_CM2 = AREA_M2 * 10000
SENSOR_MAX_CM = 39.0


@dataclass(frozen=True)
class Config:
    duration: float = 600.0
    dt: float = 1.0
    sp: float = 30.0
    td: float = 2.0
    filter_time: float = 2.0
    gain_factor: float = 1.0
    disturbance: float = 12.0
    disturbance_at: float = 180.0
    disturbance_duration: float = 100.0
    noise: bool = False
    seed: int = 42
    model: str = 'balance'
    initial_level: float = 30.0
    original_tuning: bool = False  # solo diagnóstico de la incompatibilidad
    ti: tuple = TI
    kff: tuple = KFF


def tuning(c):
    """Conservar Kc*k' al cambiar del modelo identificado al geométrico."""
    scale = PAPER_GAIN / BALANCE_GAIN if c.model == 'balance' and not c.original_tuning else 1.0
    return tuple(k * scale * c.gain_factor for k in KC)


def simulate(c=Config(), feedforward=False):
    if c.model not in ('balance', 'paper'):
        raise ValueError('Modelo desconocido')
    scalars = (c.duration, c.dt, c.sp, c.initial_level, c.td, c.filter_time,
               c.gain_factor, c.disturbance, c.disturbance_at, c.disturbance_duration)
    if not all(math.isfinite(v) for v in scalars):
        raise ValueError('Los parámetros deben ser finitos')
    if c.dt <= 0 or c.duration <= 0 or c.td < 0 or c.filter_time <= 0 or c.gain_factor <= 0:
        raise ValueError('Tiempos y ganancia fuera de rango')
    if c.disturbance < -Q_BASE or c.disturbance_duration <= 0 or c.disturbance_at < 0:
        raise ValueError('Perturbación no válida: caudal de alimentación negativo o tiempo inválido')
    if len(c.ti) != 3 or len(c.kff) != 3 or not all(math.isfinite(x) and x > 0 for x in c.ti) or not all(math.isfinite(x) and 0 <= x <= 1 for x in c.kff):
        raise ValueError('Se requieren tres Ti positivos y tres Kff entre 0 y 1')
    if not math.isclose(c.duration / c.dt, round(c.duration / c.dt)):
        raise ValueError('La duración debe ser múltiplo de dt')
    steps = [round(delay / c.dt) for delay in THETA]
    if any(n < 1 or not math.isclose(n * c.dt, delay) for n, delay in zip(steps, THETA)):
        raise ValueError('dt debe dividir exactamente los retardos')
    gain = BALANCE_GAIN if c.model == 'balance' else PAPER_GAIN
    kc = tuning(c)
    rng = random.Random(c.seed)
    h = [c.initial_level] * 3
    previous = h.copy()
    derivative = [0.0] * 3
    integral = [0.0] * 3  # contribución integral en L/min
    pumps = [deque([Q_BASE] * n) for n in steps]
    alpha = c.filter_time / (c.filter_time + c.dt)
    records = []
    for k in range(round(c.duration / c.dt) + 1):
        now = k * c.dt
        qfeed = Q_BASE + (c.disturbance if c.disturbance_at <= now < c.disturbance_at + c.disturbance_duration else 0.0)
        # Leer todas las salidas antes de calcular órdenes: u(t-theta), no theta+dt.
        qout = [p.popleft() for p in pumps]
        qin = [qfeed, qout[0], qout[1]]
        record = {'t': now, 'qfeed': qfeed, 'disturbance': qfeed-Q_BASE, 'sp': c.sp}
        for i in range(3):
            pv = h[i] + (rng.gauss(0, 0.06) if c.noise else 0.0)
            derivative[i] = alpha * derivative[i] + (1-alpha) * (pv-previous[i]) / c.dt
            e = c.sp - pv
            p = kc[i] * e
            d = -kc[i] * c.td * derivative[i]
            # Forma absoluta respecto al sesgo; equivalente a acumular incrementos de Qin.
            ff = c.kff[i] * (qin[i] - Q_BASE) if feedforward else 0.0
            raw = Q_BASE + p + integral[i] + d + ff
            command = min(Q_MAX, max(Q_MIN, raw))
            # Back-calculation sobre la orden limitada, nunca sobre la salida retardada.
            tracking_time = c.ti[i] / 2.0
            integral_used = integral[i]
            integral[i] += c.dt * (kc[i] * e / c.ti[i] + (command-raw) / tracking_time)
            pumps[i].append(command)
            previous[i] = pv
            record.update({f'h{i+1}': h[i], f'pv{i+1}': pv,
                           f'qin{i+1}': qin[i], f'qout{i+1}': qout[i],
                           f'cmd{i+1}': command, f'raw{i+1}': raw,
                           f'p{i+1}': p, f'i{i+1}': integral_used, f'd{i+1}': d,
                           f'i_next{i+1}': integral[i], f'ff{i+1}': ff,
                           f'e{i+1}': e, f'v{i+1}': derivative[i],
                           f'sat{i+1}': raw < Q_MIN or raw > Q_MAX})
        records.append(record)
        # Sin recortar niveles: no ocultar inestabilidad destruyendo volumen.
        h = [h[i] + c.dt * gain * (qin[i]-qout[i]) for i in range(3)]
    return records


def metrics(records, c):
    """Integrales trapezoidales y recuperación observada, no prueba analítica.

    Sobreimpulso: exceso positivo sobre SP, normalizado por |SP|; no por
    amplitud de escalón porque el ensayo nominal es una perturbación de caudal.
    Establecimiento: permanecer en ±0.1 cm hasta fin, mínimo 30 s observados.
    """
    if len(records) < 2:
        raise ValueError('Se requieren al menos dos muestras')
    result = []
    for i in range(1, 4):
        errors = [abs(r[f'h{i}']-c.sp) for r in records]
        tail = [r for r in records if r['t'] >= c.duration-60]
        end = c.disturbance_at + c.disturbance_duration
        bad = [r['t'] for r in records if r['t'] >= end and abs(r[f'h{i}']-c.sp) > 0.1]
        recovery = None if end > records[-1]['t'] or (bad and bad[-1] >= records[-1]['t']) else (max(0.0, bad[-1]+c.dt-end) if bad else 0.0)
        if recovery is not None and records[-1]['t'] - end - recovery < 30:
            recovery = None
        overshoot = max(0.0, max(r[f'h{i}']-c.sp for r in records))
        intervals = [b['t']-a['t'] for a, b in zip(records, records[1:])]
        result.append({'Celda': i,
                       'IAE (cm s)': sum((errors[j]+errors[j+1])*dt/2 for j, dt in enumerate(intervals)),
                       'ISE (cm² s)': sum((errors[j]**2+errors[j+1]**2)*dt/2 for j, dt in enumerate(intervals)),
                       'Sobreimpulso (cm)': overshoot,
                       'Sobreimpulso sobre SP (%)': 100*overshoot/abs(c.sp) if c.sp else None,
                       'Desviación máxima (cm)': max(errors),
                       'Error final (cm)': errors[-1],
                       'Saturación (%)': 100*sum(r[f'sat{i}'] for r in records)/len(records),
                       'Oscilación final bomba (L/min)': max(r[f'qout{i}'] for r in tail)-min(r[f'qout{i}'] for r in tail),
                       'Recuperación ±0.1 cm tras retiro (s)': recovery})
    return result
