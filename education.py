"""Secciones de explicación para la exposición académica."""
from pathlib import Path
import pandas as pd
import streamlit as st
from simulation import KC, TI, THETA, KFF, tuning

ROOT = Path(__file__).parent


def pid_section(c):
    st.subheader('Convención de signos y PID completo')
    st.write('SP es el nivel deseado; PV es la lectura del sensor. Si PV supera SP, e es negativo. '
             'Con Kp negativo, la contribución proporcional aumenta la extracción y reduce el nivel.')
    st.latex(r'e=SP-PV,\quad K_p=K_c,\quad K_i=K_p/T_i,\quad K_d=K_pT_d')
    st.latex(r'Q_{raw}=Q_0+K_p e+I-K_d v+FF')
    st.latex(r'v_k=\alpha v_{k-1}+(1-\alpha)(PV_k-PV_{k-1})/\Delta t,\quad \alpha=T_f/(T_f+\Delta t)')
    st.latex(r'I_{k+1}=I_k+\Delta t\left(K_i e_k+\frac{Q_{cmd,k}-Q_{raw,k}}{T_t}\right),\quad T_t=T_i/2')
    st.write('La derivada se aplica sobre la medición: D = −Kd·v. Kd conserva el signo de Kp; '
             'el signo menos aparece por derivar PV. El filtro limita la amplificación de ruido. '
             'El anti-windup descarga el integrador cuando la orden alcanza los límites; sigue la orden antes del retardo.')
    st.dataframe(pd.DataFrame([
        {'Variable': 'SP / PV / e', 'Significado': 'Consigna / medición / SP − PV', 'Unidad': 'cm'},
        {'Variable': 'Kp', 'Significado': 'Ganancia proporcional', 'Unidad': 'L/min/cm'},
        {'Variable': 'Ki', 'Significado': 'Ganancia integral = Kp/Ti', 'Unidad': 'L/min/(cm·s)'},
        {'Variable': 'Kd', 'Significado': 'Ganancia derivativa = Kp·Td', 'Unidad': '(L/min)·s/cm'},
        {'Variable': 'Ti / Td / Tf / dt', 'Significado': 'Tiempo integral / derivativo / filtro / muestreo', 'Unidad': 's'},
        {'Variable': 'Qcmd / Qout', 'Significado': 'Variable manipulada: orden limitada / caudal retardado real', 'Unidad': 'L/min'},
    ]), hide_index=True, width='stretch')
    st.caption(f'Configuración activa: Td={c.td:g} s, Tf={c.filter_time:g} s, dt={c.dt:g} s. '
               'La ampliación D es académica. No se atribuye a la validación PI del artículo.')


def model_section():
    st.subheader('Del balance de volumen al nivel')
    st.latex(r'\frac{dV_i}{dt}=Q_{in,i}-Q_{out,i},\quad V_i=A h_i,\quad A=0.30\cdot0.30=0.09\ \mathrm{m^2}')
    st.write('La altura física es 0.45 m = 45 cm y la capacidad geométrica es 40.5 L. '
             'El rango de lectura del sensor 0–39 cm es distinto de la altura de la celda.')
    st.latex(r'\frac{dh_i}{dt}=\frac{1000}{60\cdot900}(Q_{in,i}-Q_{out,i})=0.0185185(Q_{in,i}-Q_{out,i})')
    st.write('Conversión: 1 L = 1000 cm³, 1 min = 60 s y A = 900 cm². '
             'Así, un desequilibrio de 1 L/min produce una pendiente de 0.0185185 cm/s. '
             'La dinámica integra el caudal neto: si entrada y salida no coinciden, el nivel no queda constante.')
    st.latex(r'G_{p,i}(s)=\frac{-0.001018}{s}\exp(-\theta_i s),\quad \theta=[7,6,3]\ \mathrm{s}')
    st.write('La función identificada describe la respuesta de nivel a extracción, con ganancia negativa. '
             'Su pendiente no coincide con el balance geométrico: la relación es 18.19. '
             'Se ofrecen ambos como modelos alternativos, sin alterar el área para forzar igualdad. '
             'El modo identificado extiende la pendiente al caudal neto para conectar el banco; '
             'el artículo no identifica aquí una función independiente de alimentación.')
    st.write('Para conservar el comportamiento al usar el balance, se escala Kc por '
             '0.001018/0.0185185; Ti y θ permanecen iguales. No es una nueva identificación experimental. '
             'Las colas reproducen exactamente Qout(t)=Qcmd(t−θ); el caudal real de una celda alimenta la siguiente.')
    st.latex(r'Q_{in,1}=Q_{feed},\quad Q_{in,2}=Q_{out,1},\quad Q_{in,3}=Q_{out,2}')
    st.warning('Modelo de nivel simplificado: no calcula recuperación metalúrgica, espuma, sólidos ni dinámica del tanque T-1. '
               'No se recortan niveles para ocultar inestabilidad; fuera del rango, el modelo lineal deja de ser una representación física suficiente.')


def simc_section(c):
    st.subheader('SIMC para procesos integradores')
    st.latex(r'K_c=\frac{1}{k^{\prime}(\tau_c+\theta)},\quad T_i=\min(\tau_1,4(\tau_c+\theta))')
    st.write('Para el integrador ideal, la regla usual da Ti = 4(τc + θ). τc expresa la rapidez deseada; '
             'una respuesta más rápida exige mayor acción de control. Los valores finales del artículo '
             'incluyen ajustes experimentales y se conservan como referencia, sin afirmar que todos '
             'se deducen de una sola sustitución en la regla inicial.')
    data = []
    for i, kp in enumerate(tuning(c)):
        data.append({'Celda': i+1, 'Kc publicado': KC[i], 'Ti publicado (s)': TI[i],
                     'Kp aplicado': kp, 'Ki aplicado': kp/c.ti[i], 'Kd aplicado': kp*c.td,
                     'Ti aplicado (s)': c.ti[i], 'Td añadido (s)': c.td, 'Tf añadido (s)': c.filter_time,
                     'θ (s)': THETA[i], 'Kff publicado': KFF[i], 'Kff aplicado': c.kff[i]})
    st.dataframe(pd.DataFrame(data), hide_index=True, width='stretch')
    st.caption('Las ganancias aplicadas incluyen el modelo seleccionado y el factor del panel. '
               'Un Kc adecuado para una planta no se traslada a otra con ganancia distinta sin justificarlo.')


def algorithms_section():
    st.subheader('Algoritmo por muestra')
    st.code('''inicializar h, I, filtro y colas en equilibrio
para t = 0, dt, ..., duración:
    aplicar el pulso a Qfeed
    leer todas las salidas retardadas Qout
    formar Qin = [Qfeed, Qout1, Qout2]
    medir PV = h + ruido opcional
    calcular e, derivada filtrada, P, I, D y FF
    limitar Qraw -> Qcmd
    actualizar I con anti-windup
    guardar estado, órdenes y términos usados
    poner Qcmd en cada cola
    integrar h += dt * b * (Qin - Qout)
calcular IAE, ISE, recuperación y saturación
reproducir registros / exportar CSV y PDF''', language='text')
    st.graphviz_chart('''digraph { rankdir=TB; node [shape=box, style=rounded];
        inicio [label="Inicializar estados y colas"];
        entrada [label="Perturbación y salidas retardadas"];
        pid [label="PV → error → P + I + D filtrada + FF"];
        limitar [label="Saturación → anti-windup → nuevas órdenes"];
        balance [label="Guardar datos → balance de volumen"];
        mas [shape=diamond,label="¿Quedan muestras?"];
        fin [label="Métricas, gráficos, animación, exportación"];
        inicio -> entrada -> pid -> limitar -> balance -> mas;
        mas -> entrada [label="Sí"]; mas -> fin [label="No"];
    }''', width='stretch')
    st.write('`simulation.py` contiene el motor independiente; `animation.py` inserta sus muestras '
             'en el reproductor; `reporting.py` calcula la comparación y genera archivos; '
             '`app.py` organiza la interacción. `iN` registra el integral usado en la orden '
             'actual e `i_nextN` el estado para la siguiente muestra.')
    for name in ('simulation.py', 'animation.py', 'reporting.py', 'app.py'):
        with st.expander(name):
            st.code((ROOT/name).read_text(encoding='utf-8'), language='python')


def plc_section():
    st.subheader('PLC: Ladder y Structured Text')
    st.info('Diseño académico con variables IEC 61131-3. No compilado ni ejecutado en OpenPLC o PLC real. '
            'El Ladder textual se debe dibujar en el editor; no se presenta como proyecto gráfico importable.')
    st.markdown((ROOT/'plc'/'LADDER.md').read_text(encoding='utf-8'))
    for name in ('PID_Filtered.st', 'FlotationBank.st'):
        with st.expander(name):
            content = (ROOT/'plc'/name).read_text(encoding='utf-8')
            st.code(content, language='text')
            st.download_button(f'Descargar {name}', content, name, key=name)
    st.download_button('Descargar diseño Ladder', (ROOT/'plc'/'LADDER.md').read_bytes(), 'LADDER.md')


def conclusions_section(summaries):
    st.subheader('Interpretación de esta ejecución')
    for label, rows in summaries.items():
        st.write(f"**{label}:** error final máximo {max(r['Error final (cm)'] for r in rows):.5f} cm; "
                 f"saturación máxima {max(r['Saturación (%)'] for r in rows):.2f}%. "
                 'Revisar también los transitorios y el tiempo de recuperación.')
    st.write('Feedforward actúa cuando cambia el caudal entrante medido; feedback corrige el error residual. '
             'Una mejora negativa en la tabla indica que FF empeoró esa métrica. '
             'Los resultados son simulados y no acreditan estabilidad para todas las configuraciones.')
    st.markdown('''Referencias:

* [Quintanilla et al. (2023), MethodsX 10, 102081](https://pmc.ncbi.nlm.nih.gov/articles/PMC9988547/).
* [Skogestad (2004), reglas SIMC](https://doi.org/10.4173/mic.2004.2.2).
* [OpenPLC Editor](https://edge.autonomylogic.com/docs/openplc-editor/overview/).
* [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).
''')
    guide = ROOT/'GUIA_EXPOSICION.md'
    if guide.exists():
        st.download_button('Descargar guía de exposición', guide.read_bytes(), guide.name)
