# Simulación PID de flotación en Python

Basado en Quintanilla et al. (2023), DOI https://doi.org/10.1016/j.mex.2023.102081

**Importante:** el artículo utiliza PI y PI+feedforward. El término derivativo (Td) de esta aplicación es una ampliación didáctica; no se afirma que los autores hayan probado PID completo. No se conecta a un PLC real.

## Aplicación ampliada

Se conservan el motor estable, los modelos alternativos y los gráficos anteriores.
El respaldo previo a esta ampliación está en `backups/pre_ampliacion_*` (solo local,
excluido de Git). El archivo `app_original.py.reference` conserva la primera versión.

La interfaz contiene nueve secciones: panel con animación; configuración PID;
modelo; sintonización SIMC; gráficos; comparación y exportaciones; algoritmos;
Ladder; conclusiones. El esquema SVG incluye T-1, P-1/P-2/P-3/P-4, LI-1/LI-2/LI-3
y tuberías. Reproducir, Pausar, Reiniciar, velocidad y control de tiempo actúan
sobre las muestras reales del simulador. No hay una segunda simulación en JavaScript.

Se pueden ajustar SP, nivel inicial, duración, dt, factor de Kc, Ti por celda,
Td, filtro Tf, Kff, perturbación, ruido y semilla. Los valores por defecto conservan
el caso estable verificado. El cambio de parámetros vuelve a calcular ambos ensayos.

Los resultados incluyen IAE, ISE, sobreimpulso, error final, recuperación,
saturación y variación final de caudales, además del porcentaje de mejora.
Se grafican nivel/SP, PV, entradas, salidas retardadas, órdenes, error y perturbación.
CSV exporta todas las muestras. El PDF incluye configuración activa, metodología,
ecuaciones, tablas, gráficos vectoriales, comparación, conclusiones y referencias.

| Archivo | Función |
|---|---|
| `app.py` | Aplicación Streamlit y secciones |
| `simulation.py` | Modelo, PID, colas, saturación, métricas |
| `animation.py`, `assets/animation.html` | Reproductor de datos con SVG y controles |
| `reporting.py` | CSV, comparación y PDF |
| `education.py` | Explicación, tablas SIMC y diagrama de flujo |
| `plc/` | Diseño Ladder textual y ST complementario, sin validación de PLC |
| `tests/`, `verify_simulation.py` | Pruebas automáticas y reproducción de resultados |
| `GUIA_EXPOSICION.md` | Guion, fórmulas y preguntas para el docente |
| `DEPLOYMENT.md` | Publicación y pasos mínimos de Streamlit Cloud |
| `VALIDACION.md` | Pruebas ejecutadas y límites de validación |

Las dependencias de pruebas se instalan con `python -m pip install -r requirements-dev.txt`.
Ejecutar `python -m unittest discover -s tests -v`. La prueba de navegador
`python tests/browser_check.py` usa Chrome/Edge instalado o Chromium de Playwright;
inicia un servidor local temporal, no accede a perfiles personales.
`.github/workflows/tests.yml` deja preparada la ejecución en GitHub Actions;
no se afirma que haya corrido en GitHub antes de publicar.

## Windows / Visual Studio Code

1. Instala Python 3.12 y VS Code con la extensión **Python** (también probado localmente con 3.13.14).
2. Abre esta carpeta en VS Code: Archivo > Abrir carpeta.
3. Abre Terminal > Nueva terminal y ejecuta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

4. Abre la URL que aparece en la terminal (normalmente http://localhost:8501).
5. Cambia parámetros desde el panel izquierdo. Guarda `app.py` y Streamlit permitirá volver a ejecutar la simulación.

Si PowerShell bloquea la activación, puedes usar directamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Para usar Codex en VS Code, abre el proyecto y pídele que inspeccione `app.py` y `README.md`. Revisa los cambios propuestos antes de aceptarlos.

## Modelo

Tres balances de volumen en serie, con bombas retardadas, control PID con derivada filtrada sobre la medición, límites de caudal y anti-windup. Se comparan PID y PID + feedforward mediante IAE. Parámetros Kc, Ti, theta y Kff tomados de la tabla 2 y ecuaciones del artículo; Td y supuestos de simulación son añadidos.

## Revisión y corrección del controlador

Fuente consultada: [artículo completo, tabla 2 y ecuaciones 7–8](https://pmc.ncbi.nlm.nih.gov/articles/PMC9988547/).
El archivo previo se conserva en `app_original.py.reference`.

La causa dominante era mezclar el balance geométrico, con magnitud de ganancia
1000/(60×900) = 0.0185185 cm/s por L/min, con ganancias del controlador ajustadas
para una planta identificada con magnitud 0.001018. La relación es 18.19.
El signo original de Kc es correcto: aumentar la extracción reduce el nivel;
con e = SP − PV, un nivel alto necesita una orden de bomba mayor.

Se conservan dos alternativas seleccionables, sin modificar silenciosamente una planta:

* **Balance geométrico (predeterminado):** mismo balance anterior y mismas unidades;
  Kc se multiplica por 0.001018/0.0185185 para conservar el producto Kc·k'.
  Resulta Kc = [−3.408264, −4.177872, −4.672620] L/min/cm.
* **Identificado del artículo:** Gp = −0.001018 exp(−θs)/s; se usan
  Kc = [−62, −76, −85]. Se extiende al banco mediante el caudal neto de cada celda.
  Es una aproximación empírica, no se identifica con el balance geométrico.

En ambos se conservan Ti = [56, 30, 44] s, θ = [7, 6, 3] s y
Kff = [0.8, 0.8, 1] como valores predeterminados y referencia; Ti y Kff son ajustables.
El factor del panel multiplica la sintonización compatible,
no cambia el proceso. Td = 2 s es una ampliación docente, no un parámetro original.

Correcciones y ajustes adicionales:

* La derivada ya tenía el signo adecuado y actuaba sobre PV. Ahora se especifica
  su filtro mediante Tf = 2 s y α = Tf/(Tf+dt), independiente del paso elegido.
  D = −Kc·Td·v; no se elimina la acción D. Antes α = 0.8 estaba fijado al muestreo.
* El anti-windup anterior era condicional y no resolvía la incompatibilidad de
  ganancias. Se sustituye por back-calculation, con integral en L/min y Tt = Ti/2.
  Sigue la orden limitada a 0–100, incluyendo FF, antes de la cola de retardo.
  Seguir la salida retardada introduciría una corrección integral falsa.
* La cola anterior aplicaba θ+1 s. Ahora una orden emitida en t aparece
  exactamente en t+θ. Se leen todas las salidas antes de calcular nuevas órdenes.
* Se elimina el recorte artificial del estado a 0–39 cm: ocultaba pérdida de
  control y destruía el balance de volumen. Se muestran advertencias al exceder
  el rango de sensor. El modelo lineal no representa vaciado ni rebose;
  trayectorias fuera de rango requieren otro modelo físico para interpretarlas.
* Las bombas mantienen sus límites didácticos 0–100 L/min, sin añadir límites
  de velocidad ni filtros de actuador para esconder oscilaciones.
* FF conserva la desviación absoluta respecto a 45 L/min del simulador previo.
  La ecuación 8 del artículo usa incrementos entre muestras. Acumular esos
  incrementos desde el nominal equivale a la forma absoluta aquí usada;
  añadir un incremento aislado a un PID posicional solo produciría un impulso.
  Esta elección se documenta y no se presenta como reproducción exacta del código experimental.

## Verificación reproducible

Ejecuta `python verify_simulation.py` (solo biblioteca estándar). Las siete pruebas
cubren equilibrio sin perturbación, recuperación y comparación FF en ambos modelos,
ruido y pulso de 25 L/min, saturación con pulso temporal imposible de 70 L/min,
signo, retardo exacto, acción D y convergencia al reducir dt a 0.5 s.
La prueba de diagnóstico vuelve a aplicar Kc original al balance geométrico,
aun con el nuevo filtro y anti-windup: las bombas siguen recorriendo 0–100 L/min
y saturan más del 62% del registro nominal. Esto aísla la incompatibilidad de
ganancias; no es una ejecución exacta del archivo anterior.
La prueba imposible sirve para verificar recuperación del integrador, no validez
física de los niveles extremos. Las pruebas no garantizan toda combinación del panel.

Resultados del balance conservado, SP = 30 cm, dt = 1 s, Td = 2 s,
pulso +12 L/min entre 180 y 280 s, registro hasta 600 s, sin ruido:

| Celda | IAE PID (cm·s) | IAE PID+FF | Desviación máxima PID / FF (cm) | Recuperación PID / FF (s) |
|---|---:|---:|---:|---:|
| 1 | 365.32 | 80.11 | 3.08 / 1.63 | 148 / 60 |
| 2 | 249.84 | 70.78 | 2.82 / 1.77 | 156 / 83 |
| 3 | 321.64 | 39.77 | 3.13 / 0.91 | 189 / 76 |

Recuperación = tiempo desde 280 s hasta permanecer en ±0.1 cm durante el resto
del registro, con al menos 30 s observados. En ambas estrategias no hay saturación en el caso nominal;
el error final es menor de 0.00022 cm. Sin perturbación se mantiene exactamente
30 cm y 45 L/min. Con ruido y pulso de 25 L/min aparecen picos transitorios
de saturación inferiores al 1% del registro de 900 s; el modelo identificado
produce mayor variación de bombas por su Kc elevado. No se afirma ausencia de ruido.

El script genera `results/comparison.html` con gráficos y `results/summary.json`
con métricas, además de cuatro CSV. Streamlit muestra las mismas comparaciones
y permite descargar órdenes, caudales reales, términos P/I/D y saturación.

## Publicación

El repositorio local usa `main`. Publicar solo después de autorización expresa,
con el nombre nuevo `simulacion-pid-flotacion`; no se debe tocar `minedu-saas`.
`tools/publish_github.py` limita cuenta y nombre y evita credenciales en archivos.
Seguir [DEPLOYMENT.md](DEPLOYMENT.md). No hay una URL pública confirmada todavía.
