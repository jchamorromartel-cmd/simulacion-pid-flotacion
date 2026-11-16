# Entrega: simulación PID de tres celdas de flotación

## Acceso al simulador

Aplicación web: https://simulacion-pid-flotacion.streamlit.app/

Código e historial: https://github.com/jchamorromartel-cmd/simulacion-pid-flotacion

## Contenido del trabajo

El proyecto permite comparar PID y PID + feedforward en tres celdas conectadas
en serie. Incluye animación de resultados, modelos alternativos, sintonización,
gráficos, métricas y exportaciones CSV/PDF. Los resultados son simulados.

* `app.py`: archivo principal de la interfaz Streamlit.
* `simulation.py`: modelos matemáticos, PID, anti-windup, retardos y métricas.
* `animation.py` y `assets/animation.html`: reproducción de los resultados.
* `reporting.py`: exportación CSV y generación del informe PDF.
* `education.py`: ecuaciones y explicaciones mostradas en la aplicación.
* `plc/LADDER.md`: redes Ladder textuales; `plc/*.st`: bloques Structured Text.
* `GUIA_EXPOSICION.md`: explicación del proyecto y preguntas para la exposición.
* `README.md`: instalación, metodología y resultados de referencia.
* `VALIDACION.md`: pruebas ejecutadas y límites de la validación.
* `tests/` y `verify_simulation.py`: comprobaciones reproducibles.
* `informes/informe_resultados.pdf`: ejemplo del ensayo nominal incluido en el ZIP.

El archivo `app_original.py.reference` conserva una versión histórica; no es
el punto de entrada. El código vigente se ejecuta con `app.py`.

## Ejecución local

Extraer el ZIP completo y abrir una terminal en la carpeta que contiene `app.py`.
Se recomienda Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

En Linux/macOS, sustituir `.\.venv\Scripts\python.exe` por `.venv/bin/python`.
No abrir solo `app.py` mediante doble clic: requiere los módulos y dependencias.
El ZIP no incluye el entorno virtual; se instala mediante `requirements.txt`.

## Dónde revisar el modelo

En `simulation.py`, las constantes documentan unidades y parámetros; `tuning`
adapta la ganancia al modelo seleccionado. `simulate` implementa el controlador
y el balance; el bloque **4g** actualiza el nivel mediante Euler explícito:

```text
h[k+1] = h[k] + dt × b × (Qin[k] − Qout[k])
```

`metrics` calcula IAE, ISE, sobreimpulso, recuperación y saturación. El artículo
de referencia utiliza PI; la derivada filtrada es una ampliación del proyecto.
El diseño Ladder/ST no se ha compilado ni ejecutado en un PLC real.

## Referencia científica

Quintanilla, P., Navia, D., Moreno, F., Neethling, S. J. y Brito-Parada, P. R.
(2023). A methodology to implement a closed-loop feedback-feedforward level
control in a laboratory-scale flotation bank using peristaltic pumps.
MethodsX, 10, 102081. https://doi.org/10.1016/j.mex.2023.102081
