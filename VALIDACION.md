# Registro de validación

Fecha de trabajo: 16 de noviembre de 2026, zona America/Bogota.

## Entorno y respaldo

Se creó `backups/pre_ampliacion_20261116_135432/` antes de modificar la versión
estable. Incluye app, motor, pruebas, README, dependencias y referencia anterior.
Los respaldos están excluidos de Git. El repositorio es nuevo y solo
corresponde a esta carpeta. Después de la autorización del usuario se publicó
en https://github.com/jchamorromartel-cmd/simulacion-pid-flotacion, rama `main`.
El primer commit publicado es `604bb4f3f9931eaa45ecbd863bb7adf83add696c`;
se comprobó la igualdad del SHA local y remoto tras el push.

Python del entorno local: 3.13.14. Dependencias comprobadas: Streamlit 1.67.0,
Pandas 3.1.1, Plotly 7.1.0, NumPy 2.5.5, ReportLab 4.5.1, pypdf 6.21.4,
Playwright 1.65.2. Las pruebas de navegador usaron Chrome instalado, perfil aislado.

## Pruebas ejecutadas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Resultado: 19 pruebas, todas correctas** en la ejecución final.

| Grupo | Pruebas | Qué verifican |
|---|---:|---|
| Regresión del controlador | 7 | Equilibrio, PID/FF, ruido, saturación y recuperación, signo, retardo exacto, derivada, diferencia de ganancias, convergencia dt |
| Modelo y métricas | 6 | Geometría, balance local/global, registros PID, corrección anti-windup, integrales conocidas, ventana de recuperación, perturbación negativa y entradas inválidas |
| Exportaciones | 5 | CSV leído de vuelta, muestras de animación, PDF legible y resultados, modelo alternativo y caso sin pulso, comparación con IAE cero |
| AppTest | 1 | Nueve secciones, tablas y ejecución sin excepciones con modelo identificado, ruido y dt=0.5 |

El aviso `missing ScriptRunContext` aparece al usar AppTest fuera del servidor;
no es un fallo de la aplicación. No aparecieron advertencias de API obsoleta
en el arranque real del servidor. Se usa `st.iframe` y `width='stretch'`.

También se ejecutó `python verify_simulation.py`: siete pruebas de regresión
correctas y regeneración de CSV/resumen/gráficos en `results/`.
La compilación sintáctica Python mediante `py_compile` fue correcta.

## Navegador y servidor real

```powershell
.\.venv\Scripts\python.exe tests\browser_check.py
```

El script inició un proceso equivalente a `python -m streamlit run app.py` con
puerto local aislado y lo cerró al finalizar. Respuesta de salud HTTP 200.

Se verificó en Chrome:

* Inicio de la aplicación y carga de la animación.
* Nivel mostrado en t=195 s igual al dato del motor para PID y PID + FF.
* Reproducir avanza, Pausar conserva el tiempo y Reiniciar vuelve a t=0.
* Selector de estrategia y control de velocidad operativos.
* Descarga real del PDF desde Streamlit y lectura posterior con pypdf.
* Vista de 390 px, tres tarjetas y contenedor sin desbordamiento horizontal
  de página; el esquema permite desplazamiento interno.
* Cero errores JavaScript no controlados.

Evidencias locales: `artifacts/browser_results.json`, `artifacts/desktop.png`,
`artifacts/mobile.png`, `artifacts/streamlit.log`, `artifacts/downloaded_report.pdf`.
Estos archivos generados están excluidos de Git.

## PDF

Informe nominal: **9 páginas**, leído con pypdf; se comprobó presencia de ecuaciones,
parámetros, resultados nominales y bibliografía. Los gráficos son trazados
vectoriales de los mismos registros. También se generaron informes con modelo
identificado y sin perturbación. Ejemplo local: `artifacts/informe_pid_flotacion.pdf`.

## Resultados de control nominal

Balance geométrico, SP=inicial=30 cm, duración 600 s, dt=1 s, Td=Tf=2 s,
factor Kc=1, Ti/Kff predeterminados, sin ruido. Pulso +12 L/min de 180 a 280 s.

| Celda | IAE PID / FF (cm·s) | Recuperación PID / FF (s desde 280) |
|---|---:|---:|
| 1 | 365.32 / 80.11 | 148 / 60 |
| 2 | 249.84 / 70.78 | 156 / 83 |
| 3 | 321.64 / 39.77 | 189 / 76 |

Ambas estrategias: 0% saturación; error final máximo <0.00022 cm.
Sin perturbación desde equilibrio: 30 cm y 45 L/min constantes.
Las cifras verifican estos escenarios, no estabilidad universal.

## Límites y pendientes

El Ladder entregado es notación textual de redes con ST complementario;
no es un proyecto gráfico OpenPLC importable. No se compiló, no se simuló
en OpenPLC ni se ejecutó en un PLC real. Resta validar el diseño en el editor,
configurar E/S y comprobar el banco físico.

GitHub Actions arrancó automáticamente al publicar. Los resultados pueden consultarse
en https://github.com/jchamorromartel-cmd/simulacion-pid-flotacion/actions .
No se accedió a una sesión autenticada de Streamlit Cloud ni se verificó una URL
pública de la aplicación. Ver `DEPLOYMENT.md` para completar estos pasos.

Las pruebas locales no sustituyen la comprobación de acceso público y el
funcionamiento en el entorno Cloud después de desplegar.
