"""Simulación académica; ejecutar: streamlit run app.py."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from simulation import Config, simulate, metrics, tuning, KC, TI, THETA, KFF
from animation import animation_html
from reporting import csv_bytes, comparison, pdf_report
from education import (pid_section, model_section, simc_section,
                       algorithms_section, plc_section, conclusions_section)


@st.cache_data(show_spinner=False)
def calculate_runs(config):
    return {label: simulate(config, ff) for label, ff in [('PID', False), ('PID + FF', True)]}


@st.cache_data(show_spinner=False)
def build_pdf(config):
    return pdf_report(config, calculate_runs(config))


def main():
    st.set_page_config(page_title='PID de flotación', layout='wide')
    st.markdown('''<style>
    .block-container{padding-top:2rem;max-width:1450px}
    [data-testid="stMetric"]{background:#eaf1f4;padding:1rem;border-radius:12px}
    [data-testid="stTabs"] button{font-weight:600}
    @media(max-width:600px){.block-container{padding:1rem}.stMain h1{font-size:1.9rem}}
    </style>''', unsafe_allow_html=True)
    st.title('Control PID de nivel en tres celdas de flotación')
    st.caption('Quintanilla et al. (2023), MethodsX 10, 102081. Simulación, no datos experimentales.')
    st.info('El artículo utiliza PI + feedforward. Aquí se conserva un PID completo con derivada filtrada sobre PV como extensión didáctica.')
    with st.sidebar:
        st.header('Configuración')
        model = st.selectbox('Modelo', ['Balance geométrico conservado', 'Identificado del artículo'])
        duration = st.slider('Duración (s)', 180, 900, 600, 30)
        sp = st.slider('Nivel objetivo (cm)', 10.0, 37.0, 30.0, 0.5)
        td = st.slider('Tiempo derivativo Td (s)', 0.5, 10.0, 2.0, 0.5)
        factor = st.slider('Factor de Kc sobre ajuste compatible', 0.2, 2.0, 1.0, 0.1)
        disturbance = st.slider('Perturbación (L/min)', 0.0, 25.0, 12.0, 1.0)
        at = st.slider('Inicio de perturbación (s)', 30, 450, 180, 10)
        noise = st.checkbox('Ruido de sensor (σ = 0.06 cm)', False)
        seed = st.number_input('Semilla', 0, 100000, 42)
        with st.expander('Ajustes adicionales documentados'):
            initial_level = st.number_input('Nivel inicial (cm)', 1.0, 38.0, float(sp), 0.5)
            filter_time = st.slider('Filtro derivativo Tf (s)', 0.5, 10.0, 2.0, 0.5)
            dt = st.selectbox('Paso de cálculo dt (s)', [1.0, 0.5, 0.25])
            pulse_duration = st.slider('Duración del pulso (s)', 20, 200, 100, 10)
            ti_values = tuple(st.number_input(f'Ti celda {i+1} (s)', 5.0, 300.0, float(TI[i]), 1.0) for i in range(3))
            kff_values = tuple(st.slider(f'Kff celda {i+1}', 0.0, 1.0, float(KFF[i]), 0.05) for i in range(3))
        st.caption('Cambiar parámetros vuelve a calcular ambos ensayos. La reproducción vuelve al inicio.')
    c = Config(duration=duration, sp=sp, initial_level=initial_level, td=td, gain_factor=factor,
               disturbance=disturbance, disturbance_at=at, noise=noise, seed=int(seed),
               model='balance' if model.startswith('Balance') else 'paper', filter_time=filter_time,
               dt=dt, ti=ti_values, kff=kff_values, disturbance_duration=pulse_duration)
    st.caption('Balance: Kc original × 0.001018/0.0185185. Identificado: Kc original. '
               'Ti, Kff y filtro configurables; retardos originales; anti-windup Tt = Ti/2. '
               'Cambiar los controles requiere volver a evaluar la respuesta.')
    if at >= duration:
        st.warning('La perturbación empieza fuera del intervalo simulado.')
    elif at + pulse_duration >= duration:
        st.warning('Amplía la duración para observar la recuperación después del pulso.')
    runs = calculate_runs(c)
    summaries = {label: metrics(rows, c) for label, rows in runs.items()}
    tabs = st.tabs(['Panel principal', 'Configuración PID', 'Modelo matemático', 'Sintonización SIMC',
                    'Gráficos y resultados', 'Comparación y exportación', 'Algoritmos y código',
                    'Código Ladder del PLC', 'Conclusiones y referencias'])
    with tabs[0]:
        st.subheader('Banco de flotación · reproducción de resultados')
        st.write('Selecciona una estrategia y recorre el tiempo. Los niveles y caudales proceden de las mismas muestras que los gráficos.')
        st.iframe(animation_html(runs, c), height=900, width='stretch', alt='Animación interactiva del banco de flotación')
    with tabs[1]:
        pid_section(c)
    with tabs[2]:
        model_section()
        st.subheader('Parámetros de referencia y aplicados')
        st.dataframe(pd.DataFrame({'Celda': [1, 2, 3], 'Kc artículo': KC, 'Kc aplicado': tuning(c),
                                  'Ti (s)': c.ti, 'Retardo (s)': THETA, 'Td añadido (s)': [td]*3, 'Kff': c.kff}), hide_index=True)
        st.subheader('Modelo y controlador')
        st.latex(r'\dot h_i=b(Q_{in,i}-Q_{out,i}),\quad b_{balance}=1000/(60\cdot900),\quad b_{articulo}=0.001018')
        st.latex(r'e=SP-PV,\quad Q_{raw}=45+K_c e+I-K_cT_d v+K_{ff}(Q_{in}-45)')
        st.latex(r'v_k=\alpha v_{k-1}+(1-\alpha)(PV_k-PV_{k-1})/\Delta t,\quad \alpha=T_f/(T_f+\Delta t)')
        st.latex(r'Q_{cmd}=\mathrm{clip}(Q_{raw},0,100),\quad I_{k+1}=I_k+\Delta t[K_ce/T_i+(Q_{cmd}-Q_{raw})/T_t]')
        st.write('Salida Qout(t) = Qcmd(t − θ). El anti-windup sigue la orden saturada antes del retardo. '
                 'Cada salida real alimenta la siguiente celda. El estado no se recorta. '
                 f'Supuestos: bombas 0–100 L/min, pulso de {pulse_duration} s, caudal nominal 45 L/min; '
                 '0–39 cm es rango de sensor, no altura física máxima. '
                 'FF usa desviación respecto al caudal nominal; ver diferencias con ecuación 8 en README.')
        st.markdown('[Artículo y tabla 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC9988547/)')

    with tabs[3]:
        simc_section(c)
    with tabs[4]:
        for variable, title, unit in [('h', 'Niveles y setpoint', 'Nivel (cm)'), ('qout', 'Caudales reales de las bombas', 'L/min'), ('pv', 'Lecturas de sensores PV', 'cm'), ('qin', 'Caudales de entrada', 'L/min'), ('cmd', 'Señales de control limitadas', 'L/min'), ('e', 'Error medido SP-PV', 'cm')]:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                subplot_titles=[f'Celda / bomba {i}' for i in (1, 2, 3)])
            for label, rows in runs.items():
                for i in (1, 2, 3):
                    fig.add_trace(go.Scatter(x=[r['t'] for r in rows], y=[r[f'{variable}{i}'] for r in rows],
                                  name=f'{i}: {label}', line=dict(dash='dot' if label == 'PID' else 'solid')), row=i, col=1)
            for i in (1, 2, 3):
                fig.update_yaxes(title_text=unit, row=i, col=1)
                if variable in ('h', 'pv'):
                    fig.add_hline(y=sp, line_dash='dash', row=i, col=1)
                elif variable in ('qout', 'qin', 'cmd'):
                    for limit in (0, 100):
                        fig.add_hline(y=limit, line_dash='dash', line_color='gray', row=i, col=1)
            fig.update_xaxes(title_text='Tiempo (s)', row=3, col=1)
            fig.update_layout(height=700, title=title, hovermode='x unified')
            st.plotly_chart(fig, width='stretch')

        disturbance_fig = go.Figure()
        disturbance_fig.add_trace(go.Scatter(x=[r['t'] for r in runs['PID']],
                                             y=[r['disturbance'] for r in runs['PID']], name='Perturbación de alimentación', line_shape='hv'))
        disturbance_fig.update_layout(title='Perturbación respecto a 45 L/min', xaxis_title='Tiempo (s)', yaxis_title='L/min')
        st.plotly_chart(disturbance_fig, width='stretch')
    with tabs[5]:
        st.subheader('Comparación cuantitativa')
        cols = st.columns(3)
        for i, col in enumerate(cols):
            before = summaries['PID'][i]['IAE (cm s)']
            after = summaries['PID + FF'][i]['IAE (cm s)']
            col.metric(f'Celda {i+1}: IAE con FF', f'{after:.2f} cm·s',
                       f'{100*(before-after)/before:.1f}% mejora' if before else 'Sin error')
        st.dataframe(pd.DataFrame([dict(Modo=label, **row) for label, rows in summaries.items() for row in rows]), hide_index=True)
        st.caption('Recuperación: desde el fin del pulso hasta permanecer en ±0.1 cm hasta el final, con al menos 30 s observados; vacío = no observable o no recuperado. Oscilación final: pico a pico en los últimos 60 s. IAE e ISE usan el estado h; el error graficado usa PV.')
        for label, rows in runs.items():
            if any(r[f'h{i}'] < 0 or r[f'h{i}'] > 39 for r in rows for i in (1, 2, 3)):
                st.warning(f'{label}: nivel fuera del rango de sensor 0–39 cm. No se recorta el estado para ocultar la pérdida de control.')

        st.subheader('Mejora por celda')
        st.dataframe(pd.DataFrame(comparison(runs, c)), hide_index=True, width='stretch')
        for label, rows in runs.items():
            st.download_button(f'Descargar {label}', csv_bytes(rows),
                               f"{label.replace(' ', '_')}.csv", 'text/csv')
        st.download_button('Descargar tabla de comparación CSV', csv_bytes(comparison(runs, c)), 'comparacion.csv', 'text/csv')
        # on_click=ignore conserva la reproducción al descargar.
        st.download_button('Descargar informe PDF', build_pdf(c), 'informe_pid_flotacion.pdf',
                           'application/pdf', on_click='ignore')
    with tabs[6]:
        algorithms_section()
    with tabs[7]:
        plc_section()
    with tabs[8]:
        conclusions_section(summaries)



if __name__ == '__main__':
    main()
