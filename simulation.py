"""Modelos matemáticos, PID y métricas del banco de tres celdas.

Este archivo contiene los cálculos; app.py solo configura y presenta resultados.
Para revisar el modelo, seguir este orden:
1. Constantes: geometría, parámetros publicados y supuestos de operación.
2. Config: condiciones de un ensayo, sin estado mutable del controlador.
3. tuning: adaptación de Kc al modelo elegido, conservando la referencia.
4. simulate: retardos, PID y balance de volumen, muestra a muestra.
5. metrics: evaluación de las trayectorias que devuelve simulate.

Unidades internas: nivel en cm, tiempo en s y caudales en L/min.
Referencia: Quintanilla et al. (2023), tabla 2, DOI 10.1016/j.mex.2023.102081.
El artículo valida PI; el término D filtrado es una extensión de este proyecto.
"""
from collections import deque
from dataclasses import dataclass
import math
import random

# 1. REFERENCIA PUBLICADA. La posición 0/1/2 corresponde a celda 1/2/3.
# Kc es negativo porque aumentar la extracción disminuye el nivel.
KC = (-62.0, -76.0, -85.0)  # L/min por cm; Kp en la forma paralela
TI = (56.0, 30.0, 44.0)
THETA = (7.0, 6.0, 3.0)
KFF = (0.8, 0.8, 1.0)
# MODELO IDENTIFICADO: Gp(s) = -PAPER_GAIN * exp(-theta*s) / s.
# Se guarda la magnitud positiva; el signo negativo aparece en Qin-Qout.
PAPER_GAIN = 0.001018  # cm/s por L/min; |k'| de la tabla 2
# MODELO GEOMÉTRICO: dV/dt=Qin-Qout y V=A*h, con A=900 cm².
# 1000 convierte L a cm³; 60 convierte minutos a segundos.
# dh/dt = BALANCE_GAIN*(Qin-Qout), con h en cm y t en s.
BALANCE_GAIN = 1000.0 / (60.0 * 900.0)
# Sesgo y límites didácticos del actuador; no son una calibración de bombas reales.
Q_BASE, Q_MIN, Q_MAX = 45.0, 0.0, 100.0
# Dimensiones físicas: 0.30×0.30 m de sección y 0.45 m de altura (40.5 L).
AREA_M2, HEIGHT_M = 0.30 * 0.30, 0.45
AREA_CM2 = AREA_M2 * 10000
SENSOR_MAX_CM = 39.0
# Los 39 cm son el rango de sensor; no la altura de 45 cm de la celda.


@dataclass(frozen=True)
class Config:
    """Parámetros de entrada de una simulación reproducible.

    duration/dt: horizonte y período de muestreo; sp/initial_level: cm.
    td/filter_time: tiempo derivativo Td y constante del filtro Tf, en s.
    ti: tres tiempos integrales en s; kff: tres ganancias sin dimensiones.
    disturbance: incremento de alimentación en L/min; su inicio y ancho son s.
    model='balance': balance geométrico; model='paper': pendiente identificada.
    gain_factor multiplica Kc después de adaptarlo al modelo; no cambia la planta.
    frozen=True evita cambiar parámetros mientras se ejecuta o almacena un ensayo.
    """
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
    """Devolver los tres Kp aplicados, expresados en L/min/cm.

    El balance geométrico tiene una pendiente 18.19 veces mayor que la empírica.
    Se escala el controlador por |k'_paper|/|k'_balance|, sin alterar el área ni
    la ecuación de proceso. Así se conserva Kc*k' en ambos modelos y se mantienen
    Ti y los retardos. No constituye una nueva identificación experimental.
    original_tuning=True omite esa adaptación solo para reproducir el diagnóstico.
    """
    scale = PAPER_GAIN / BALANCE_GAIN if c.model == 'balance' and not c.original_tuning else 1.0
    return tuple(k * scale * c.gain_factor for k in KC)


def simulate(c=Config(), feedforward=False):
    """Simular tres celdas en serie y devolver una lista de registros temporales.

    Estado del proceso: h, tres niveles. Estados del PID: integral, derivative
    y previous, independientes para cada celda. Estado del retardo: pumps.
    feedforward=False/True permite comparar estrategias con iguales condiciones.

    Se usa Euler explícito para el nivel y el integrador del PID. El filtro
    derivativo usa alpha=Tf/(Tf+dt). Se registran las variables en t[k] antes
    de avanzar el balance a t[k+1]. La última fila es el estado final observado;
    el avance posterior a esa fila no se devuelve ni cuenta en las métricas.
    """
    # 2. VALIDACIÓN. Rechazar tiempos, modelos y parámetros que no se pueden
    # interpretar físicamente o discretizar con las colas de retardo elegidas.
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
    # Cada retardo debe equivaler a un número entero de muestras: N=theta/dt.
    # No se redondea un retardo arbitrario silenciosamente; se comprueba abajo.
    steps = [round(delay / c.dt) for delay in THETA]
    if any(n < 1 or not math.isclose(n * c.dt, delay) for n, delay in zip(steps, THETA)):
        raise ValueError('dt debe dividir exactamente los retardos')
    # 3. SELECCIÓN DEL MODELO. En ambos: dh/dt=b*(Qin-Qout).
    # balance: b=1000/(60*A); paper: b=0.001018. Aplicar b empírico también
    # a la entrada es una extensión al banco, no otra identificación publicada.
    gain = BALANCE_GAIN if c.model == 'balance' else PAPER_GAIN
    kc = tuning(c)
    # Generador local y misma semilla para comparar PID/FF con el mismo ruido.
    rng = random.Random(c.seed)
    h = [c.initial_level] * 3
    # Inicializar PV previa al nivel inicial evita un golpe D ficticio al arrancar.
    previous = h.copy()
    derivative = [0.0] * 3
    integral = [0.0] * 3  # contribución integral en L/min
    # Antes de t=0 se supone que las bombas operaban a 45 L/min.
    # La cola contiene las órdenes pendientes de actuar; no modela un lag adicional.
    pumps = [deque([Q_BASE] * n) for n in steps]
    alpha = c.filter_time / (c.filter_time + c.dt)
    records = []
    # 4. BUCLE DISCRETO: cada iteración calcula una muestra de las tres celdas.
    for k in range(round(c.duration / c.dt) + 1):
        now = k * c.dt
        # Perturbación rectangular: el extremo inicial se incluye y el final no.
        # Ejemplo nominal: Qfeed=57 entre 180 y 280 s; fuera de allí Qfeed=45.
        qfeed = Q_BASE + (c.disturbance if c.disturbance_at <= now < c.disturbance_at + c.disturbance_duration else 0.0)
        # Leer todas las salidas antes de calcular órdenes: u(t-theta), no theta+dt.
        qout = [p.popleft() for p in pumps]
        # Acoplamiento físico: Qin2=Qout1 y Qin3=Qout2. Se emplean salidas
        # reales retardadas, nunca órdenes futuras aún pendientes en la cola.
        qin = [qfeed, qout[0], qout[1]]
        record = {'t': now, 'qfeed': qfeed, 'disturbance': qfeed-Q_BASE, 'sp': c.sp}
        for i in range(3):
            # 4a. MEDICIÓN. h es el estado real simulado; PV añade ruido opcional
            # gaussiano de sigma=0.06 cm. El sensor no modifica el balance.
            pv = h[i] + (rng.gauss(0, 0.06) if c.noise else 0.0)
            # 4b. DERIVADA FILTRADA SOBRE PV (cm/s), no sobre el error.
            # Tf*v_dot+v=PV_dot se discretiza con alpha=Tf/(Tf+dt).
            # Al cambiar solo SP, esta expresión no genera golpe derivativo.
            derivative[i] = alpha * derivative[i] + (1-alpha) * (pv-previous[i]) / c.dt
            # 4c. PID COMPLETO: Kp=kc; Ki=kc/Ti; Kd=kc*Td.
            # Si PV>SP, e<0 y Kp<0: P aumenta la extracción para bajar el nivel.
            e = c.sp - pv
            p = kc[i] * e
            d = -kc[i] * c.td * derivative[i]  # D=-Kd*dPV_filtrada/dt, L/min
            # Forma absoluta respecto al sesgo; equivalente a acumular incrementos de Qin.
            ff = c.kff[i] * (qin[i] - Q_BASE) if feedforward else 0.0
            # El integral ya está expresado en L/min; no se multiplica otra vez
            # por Kp. La suma es posicional y se realiza alrededor de Q_BASE.
            raw = Q_BASE + p + integral[i] + d + ff
            # 4d. SATURACIÓN. Orden aplicable a la bomba, limitada a 0..100 L/min.
            command = min(Q_MAX, max(Q_MIN, raw))
            # Back-calculation sobre la orden limitada, nunca sobre la salida retardada.
            # 4e. ANTI-WINDUP: I_dot=Ki*e+(Qcmd-Qraw)/Tt, con Tt=Ti/2.
            # Si no satura, Qcmd-Qraw=0 y queda la integral normal. Al saturar,
            # la corrección empuja I hacia una orden realizable. Tt es un ajuste
            # adicional de este simulador; no es un parámetro PI del artículo.
            tracking_time = c.ti[i] / 2.0
            integral_used = integral[i]
            integral[i] += c.dt * (kc[i] * e / c.ti[i] + (command-raw) / tracking_time)
            # Guardar la orden para que aparezca exactamente theta segundos después.
            pumps[i].append(command)
            previous[i] = pv
            # 4f. TRAZABILIDAD. P, I usado, D y FF permiten reconstruir raw.
            # i_next es el estado actualizado para la próxima muestra, distinto
            # del I que produjo la orden actual. El sufijo 1/2/3 identifica celda.
            record.update({f'h{i+1}': h[i], f'pv{i+1}': pv,
                           f'qin{i+1}': qin[i], f'qout{i+1}': qout[i],
                           f'cmd{i+1}': command, f'raw{i+1}': raw,
                           f'p{i+1}': p, f'i{i+1}': integral_used, f'd{i+1}': d,
                           f'i_next{i+1}': integral[i], f'ff{i+1}': ff,
                           f'e{i+1}': e, f'v{i+1}': derivative[i],
                           f'sat{i+1}': raw < Q_MIN or raw > Q_MAX})
        records.append(record)
        # 4g. MODELO MATEMÁTICO DISCRETIZADO (Euler explícito):
        # h[k+1]=h[k]+dt*b*(Qin[k]-Qout[k]). Aquí se integra el balance,
        # no en la animación ni en las funciones que dibujan las ecuaciones.
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
        # Evaluación respecto al nivel h sin ruido: error de seguimiento real
        # simulado. El error que ve el controlador, SP-PV, se guarda aparte en eN.
        errors = [abs(r[f'h{i}']-c.sp) for r in records]
        tail = [r for r in records if r['t'] >= c.duration-60]
        end = c.disturbance_at + c.disturbance_duration
        # Recuperación: buscar la última salida de la banda ±0.1 cm tras el pulso.
        # None significa que no se observó recuperación suficiente en el horizonte.
        bad = [r['t'] for r in records if r['t'] >= end and abs(r[f'h{i}']-c.sp) > 0.1]
        recovery = None if end > records[-1]['t'] or (bad and bad[-1] >= records[-1]['t']) else (max(0.0, bad[-1]+c.dt-end) if bad else 0.0)
        if recovery is not None and records[-1]['t'] - end - recovery < 30:
            recovery = None
        # Sobreimpulso unilateral sobre SP; la desviación máxima usa ambos signos.
        overshoot = max(0.0, max(r[f'h{i}']-c.sp for r in records))
        intervals = [b['t']-a['t'] for a, b in zip(records, records[1:])]
        # IAE = integral |e| dt; ISE = integral e² dt, por regla trapezoidal.
        # Se usa el intervalo real entre registros, evitando sumar una muestra
        # extra de duración. Saturación es % de muestras, no número de ciclos.
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
