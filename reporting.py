"""CSV e informe PDF vectorial, sin navegador ni servicios externos."""
import csv
from dataclasses import asdict
from io import BytesIO, StringIO
from xml.sax.saxutils import escape
from simulation import metrics, tuning, KC, THETA


def csv_bytes(rows):
    buffer = StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8-sig')


def comparison(runs, config):
    summaries = {label: metrics(rows, config) for label, rows in runs.items()}
    out = []
    for i in range(3):
        a, b = summaries['PID'][i], summaries['PID + FF'][i]
        row = {'Celda': i+1}
        for key in ('IAE (cm s)', 'ISE (cm² s)'):
            row[f'{key} PID'] = a[key]
            row[f'{key} PID + FF'] = b[key]
            row[f'Mejora {key} (%)'] = 100*(a[key]-b[key])/a[key] if a[key] else None
        out.append(row)
    return out


def pdf_report(config, runs):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.graphics.shapes import Drawing, Line, PolyLine, String, Rect
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=42, leftMargin=42,
                            topMargin=40, bottomMargin=40, title='Simulación PID de tres celdas de flotación',
                            author='Simulador académico de flotación')
    styles = getSampleStyleSheet()
    styles['BodyText'].leading = 14
    story = []

    def paragraph(text, style='BodyText'):
        story.append(Paragraph(text, styles[style]))
        story.append(Spacer(1, 8))

    def table(rows, widths):
        data = [[Paragraph(escape(str(v)), styles['BodyText']) for v in row] for row in rows]
        t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dfedef')),
                               ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#bad0d6')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 6)]))
        story.extend([t, Spacer(1, 12)])

    paragraph('Control PID de tres celdas de flotación', 'Title')
    paragraph('Informe de resultados simulados', 'Heading2')
    paragraph('Simulador académico basado en Quintanilla et al. (2023). No reproduce mediciones experimentales ni se conecta a un PLC real. El artículo utiliza PI; el término derivativo es una ampliación docente.')
    paragraph('Metodología y configuración', 'Heading2')
    table([['Parámetro', 'Valor'],
           ['Modelo', config.model], ['Duración / dt', f'{config.duration:g} s / {config.dt:g} s'],
           ['SP / nivel inicial', f'{config.sp:g} / {config.initial_level:g} cm'],
           ['Perturbación rectangular', f'{config.disturbance:g} L/min desde {config.disturbance_at:g} s durante {config.disturbance_duration:g} s'],
           ['Derivada / filtro', f'Td = {config.td:g} s; Tf = {config.filter_time:g} s'],
           ['Ruido de PV', f'{config.noise}; sigma = 0.06 cm; semilla = {config.seed}'],
           ['Bombas / sesgo', '0 a 100 L/min / 45 L/min'],
           ['Anti-windup', 'Back-calculation, Tt = Ti/2']], [165, 340])
    paragraph('Modelo matemático y unidades', 'Heading2')
    paragraph('dV/dt = Qin - Qout; V = A h. A = 0.30 × 0.30 = 0.09 m²; altura = 0.45 m; volumen geométrico máximo = 40.5 L. Para h en cm, Q en L/min y t en s: dh/dt = 1000/(60 × 900) (Qin - Qout).')
    paragraph('El modelo identificado utiliza Gp(s) = (-0.001018/s) exp(-theta s). Su pendiente empírica difiere del balance geométrico por un factor 18.19. No se fuerza esa coincidencia cambiando el área. En modo paper, aplicar la misma pendiente a Qin es una extensión al banco mediante el caudal neto, no una identificación experimental de la trayectoria de perturbación.')
    story.append(PageBreak())
    paragraph('Control y sintonización', 'Heading1')
    paragraph('Proceso integrador: un desequilibrio de caudales mantiene una pendiente de nivel. Al aumentar la extracción, baja el nivel: ganancia de proceso negativa y Kc negativo para e = SP - PV.')
    paragraph('SIMC para proceso integrador: Kc = 1/[k prima (tau c + theta)]; Ti = 4(tau c + theta) para el integrador ideal. En la regla general Ti = min(tau1, 4(tau c + theta)). Los valores finales publicados incluyen ajustes experimentales; no se obtienen todos sustituyendo theta en una única fórmula.')
    rows = [['Celda', 'Kc ref.', 'Kp aplicado', 'Ki', 'Kd', 'Ti / theta (s)']]
    for i, kp in enumerate(tuning(config)):
        rows.append([i+1, KC[i], f'{kp:.4f}', f'{kp/config.ti[i]:.5f}', f'{kp*config.td:.4f}', f'{config.ti[i]:g} / {THETA[i]:g}'])
    table(rows, [40, 65, 95, 80, 80, 145])
    paragraph('Kp = Kc; Ki = Kp/Ti; Kd = Kp Td. La contribución D es -Kd v porque la derivada actúa sobre PV, no sobre el error. No hay golpe derivativo por cambiar SP.')
    paragraph('v[k] = alpha v[k-1] + (1-alpha)(PV[k]-PV[k-1])/dt; alpha = Tf/(Tf+dt). Qraw = 45 + Kp e + I - Kd v + FF. Qcmd = clip(Qraw, 0, 100). I[k+1] = I[k] + dt (Ki e + (Qcmd-Qraw)/Tt).')
    paragraph('Qout(t) = Qcmd(t-theta), con theta = 7, 6 y 3 s. El anti-windup sigue Qcmd, antes del retardo. FF = Kff (Qin-45), con Kff = '+escape(str(config.kff))+'. Se conserva la forma absoluta respecto al nominal del simulador; la ecuación 8 del artículo expresa incrementos entre muestras. Solo su acumulación equivale a esta forma posicional.')
    paragraph('Métricas y criterios', 'Heading2')
    paragraph('IAE = integral |SP-h| dt; ISE = integral (SP-h)² dt, ambas por trapecios. Se calculan sobre el estado simulado h; el controlador usa PV, que puede contener ruido. Sobreimpulso = max(0, max(h-SP)), porcentaje respecto a |SP|; no es el porcentaje clásico de un escalón de SP. Recuperación/establecimiento: desde el fin del pulso hasta permanecer en ±0.1 cm hasta finalizar, con al menos 30 s observados. No observado se indica como N/O. Saturación: fracción de muestras con orden sin limitar fuera de rango.')
    story.append(PageBreak())
    paragraph('Comparación PID frente a PID + feedforward', 'Heading1')
    summary = {name: metrics(rows, config) for name, rows in runs.items()}
    for name, rows in summary.items():
        paragraph(name, 'Heading2')
        values = [['Celda', 'IAE', 'ISE', 'Pico + (cm)', 'Sat. %', 'Recup. s']]
        for row in rows:
            r = row['Recuperación ±0.1 cm tras retiro (s)']
            values.append([row['Celda'], f"{row['IAE (cm s)']:.3f}", f"{row['ISE (cm² s)']:.3f}",
                           f"{row['Sobreimpulso (cm)']:.3f}", f"{row['Saturación (%)']:.2f}", 'N/O' if r is None else f'{r:.1f}'])
        table(values, [45, 95, 100, 100, 75, 90])
    for row in comparison(runs, config):
        value = row['Mejora IAE (cm s) (%)']
        paragraph(f"Celda {row['Celda']}: mejora de IAE = {value:.2f}%." if value is not None else f"Celda {row['Celda']}: mejora porcentual no definida porque IAE PID = 0.")
    paragraph('Conclusiones de esta ejecución', 'Heading2')
    for name, rows in summary.items():
        worst = max(r['Error final (cm)'] for r in rows)
        saturation = max(r['Saturación (%)'] for r in rows)
        paragraph(f'{escape(name)}: error final máximo = {worst:.5f} cm; saturación máxima = {saturation:.2f}%. Estas cifras describen el horizonte simulado, no garantizan estabilidad para cualquier sintonización.')
    out_of_range = any(r[f'h{i}'] < 0 or r[f'h{i}'] > 39 for data in runs.values() for r in data for i in (1, 2, 3))
    paragraph('Hay niveles fuera del rango 0-39 cm. No interpretar estados extremos como predicción física de vaciado/rebose.' if out_of_range else 'Los niveles permanecen dentro del rango de sensor 0-39 cm en esta ejecución.')

    def chart(variable, cell, title, unit, extra=None):
        drawing = Drawing(505, 190)
        x0, y0, w, h = 48, 30, 440, 130
        arrays = [(label, [r['t'] for r in data], [r[f'{variable}{cell}'] for r in data]) for label, data in runs.items()]
        values = [v for _, _, ys in arrays for v in ys]
        if extra is not None:
            values += [extra]
        lo, hi = min(values), max(values)
        margin = max((hi-lo)*0.1, 0.05)
        lo, hi = lo-margin, hi+margin
        drawing.add(String(0, 177, title, fontName='Helvetica-Bold', fontSize=10))
        drawing.add(Line(x0, y0, x0+w, y0, strokeColor=colors.grey))
        drawing.add(Line(x0, y0, x0, y0+h, strokeColor=colors.grey))
        for value, yy in [(lo, y0), (hi, y0+h)]:
            drawing.add(String(0, yy, f'{value:.2f}', fontSize=8))
        drawing.add(String(x0, 10, '0 s', fontSize=8))
        drawing.add(String(x0+w-30, 10, f'{config.duration:g} s', fontSize=8))
        drawing.add(String(0, y0+h+3, unit, fontSize=8))
        if extra is not None:
            yy = y0+(extra-lo)/(hi-lo)*h
            drawing.add(Line(x0, yy, x0+w, yy, strokeColor=colors.grey, strokeDashArray=[3, 3]))
        for (label, xs, ys), color in zip(arrays, ['#d77700', '#007f86']):
            points = [coordinate for x, y in zip(xs, ys) for coordinate in (x0+x/config.duration*w, y0+(y-lo)/(hi-lo)*h)]
            drawing.add(PolyLine(points, strokeColor=colors.HexColor(color), strokeWidth=1.1))
        return drawing

    for variable, title, unit in [('h', 'Niveles', 'cm'), ('qout', 'Caudales reales', 'L/min'),
                                   ('qin', 'Caudales de entrada', 'L/min'), ('cmd', 'Órdenes de bombas', 'L/min'),
                                   ('e', 'Error medido SP-PV', 'cm')]:
        story.append(PageBreak())
        paragraph(title, 'Heading1')
        paragraph('Naranja: PID. Verde azulado: PID + FF. Línea discontinua: SP en gráficos de nivel.')
        for i in (1, 2, 3):
            story.append(chart(variable, i, f'Celda {i}', unit, config.sp if variable == 'h' else None))
    story.append(PageBreak())
    paragraph('Algoritmo y alcance del PLC', 'Heading1')
    paragraph('Inicializar niveles, integral, filtro y colas en el equilibrio. Por muestra: aplicar perturbación; leer salidas retardadas; formar entradas en serie; leer PV; calcular P, I, D y FF; limitar órdenes; actualizar integral con anti-windup; guardar datos; integrar caudal neto. La animación reproduce exactamente estos registros y no modifica la simulación.')
    paragraph('Se entrega un bloque PID en Structured Text y un diseño Ladder con variables IEC 61131-3. No se ha compilado ni ejecutado en OpenPLC o PLC real. En un PLC los retardos corresponden al proceso físico: no se deben retrasar además las órdenes salvo en un banco de simulación. La parada de emergencia y las alarmas son un diseño académico; la seguridad de una instalación exige ingeniería y hardware específicos.')
    paragraph('Referencias', 'Heading1')
    paragraph('Quintanilla, P.; Navia, D.; Moreno, F.; Neethling, S. J.; Brito-Parada, P. R. (2023). A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps. MethodsX, 10, 102081. DOI: 10.1016/j.mex.2023.102081.')
    paragraph('Texto completo: https://pmc.ncbi.nlm.nih.gov/articles/PMC9988547/')
    paragraph('Skogestad, S. (2004). Simple analytic rules for model reduction and PID controller tuning. Modeling, Identification and Control, 25(2), 85-120. DOI: 10.4173/mic.2004.2.2.')
    paragraph('OpenPLC Editor: https://edge.autonomylogic.com/docs/openplc-editor/overview/')
    paragraph('Streamlit Community Cloud: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app')

    def footer(canvas, _doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(42, 22, f'Resultados simulados · modelo {config.model} · dt {config.dt:g} s')
        canvas.drawRightString(A4[0]-42, 22, f'Página {_doc.page}')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
