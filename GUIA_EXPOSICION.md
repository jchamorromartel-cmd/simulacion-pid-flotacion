# Guía de exposición: control PID de tres celdas de flotación

## 1. Objetivo y alcance

Demostrar cómo un controlador PID mantiene el nivel de un banco de tres celdas
en serie y cómo un feedforward medido reduce el efecto de cambios de alimentación.
La aplicación es académica, calcula resultados simulados y no controla una planta.
No calcula recuperación de minerales, ley de concentrado ni cinética de flotación.

Guion sugerido de ocho minutos:

1. Presentar problema y referencia (1 min).
2. Explicar el balance y el signo del proceso (1 min).
3. Mostrar parámetros PI originales y extensión PID (1 min).
4. Reproducir el banco y recorrer el pulso de 180 s (2 min).
5. Comparar errores, bombas y recuperación con FF (1 min).
6. Explicar Ladder, exportar PDF y concluir (2 min).

## 2. Artículo científico

Quintanilla et al. publicaron en MethodsX (2023) una metodología de control de
nivel con realimentación y anticipación en un banco experimental de flotación.
La referencia experimental usa **PI**, no un PID con D activo. En este proyecto
se conserva esa distinción: el derivativo filtrado es una ampliación docente.

Referencia completa: Quintanilla, P., Navia, D., Moreno, F., Neethling, S. J. y
Brito-Parada, P. R. (2023). *A methodology to implement a closed-loop
feedback-feedforward level control in a laboratory-scale flotation bank using
peristaltic pumps*. MethodsX, 10, 102081.
https://doi.org/10.1016/j.mex.2023.102081

Fuente consultada: https://pmc.ncbi.nlm.nih.gov/articles/PMC9988547/
Las dimensiones se toman de la descripción del montaje; parámetros y modelos,
de la tabla 2; FF, de las ecuaciones 7–8. Las curvas de nuestra aplicación no son
las curvas experimentales publicadas.

## 3. Funcionamiento del banco

P-4 alimenta la primera celda desde T-1. P-1 extrae de la celda 1 y alimenta la 2;
P-2 extrae de la 2 y alimenta la 3; P-3 descarga la 3. LI-1, LI-2 y LI-3 miden nivel.
El tanque de retorno se representa para explicar el circuito, pero no se simula
su inventario. El caudal de P-4 es la alimentación impuesta con su perturbación.

En cada celda, entrada mayor que salida eleva el nivel; salida mayor lo reduce.
La animación reproduce los mismos registros del modelo que los gráficos y CSV.
Pausar la animación no cambia el cálculo; permite examinar una muestra.

## 4. Modelo matemático y coherencia de unidades

```text
dV/dt = Qin - Qout
V = A h
A = 0.30 m × 0.30 m = 0.09 m² = 900 cm²
Altura = 0.45 m = 45 cm
Volumen geométrico a 45 cm = 0.09 × 0.45 × 1000 = 40.5 L
dh/dt = [1000/(60×900)] (Qin - Qout)
```

Q está en L/min, h en cm y t en segundos. El factor convierte litros a cm³ y
minutos a segundos. La magnitud de ganancia geométrica es 0.0185185 cm/s por L/min.
El proceso es integrador: un caudal neto constante produce una rampa de nivel.

El modelo empírico publicado de extracción es:

```text
Gp_i(s) = (-0.001018/s) exp(-theta_i s)
theta = [7, 6, 3] segundos
```

Es otra aproximación. Su pendiente no coincide con el balance geométrico;
la relación de magnitudes es 18.19. No se modifica el área ni se inventa una
causa física para esa diferencia. El modo identificado adopta la pendiente
empírica para el caudal neto; esa extensión a la alimentación es un supuesto.

Se puede elegir cualquiera de los modelos. Para el balance se ajusta Kc por
0.001018/0.0185185, preservando Kc·k'; para el modelo identificado se conservan
las ganancias del artículo. No se mezclan ambas ganancias sin escalar.

Los retardos se implementan con colas: una orden en t se aplica en t+theta.
El rango de sensor 0–39 cm no es la altura física. El modelo no incluye vaciado,
rebose ni dinámica de espuma: fuera de rango se advierte sin recortar el estado.

## 5. PID y sintonización SIMC

SP: nivel deseado; PV: medición; e = SP − PV. La variable manipulada es la
orden de caudal de cada bomba de salida. Si sube el nivel, e se vuelve negativo;
como Kp es negativo, la salida aumenta. Ese signo produce realimentación correctiva.

```text
Kp = Kc
Ki = Kp/Ti
Kd = Kp×Td
P = Kp×e
D = -Kd×v
v[k] = alpha×v[k-1] + (1-alpha)×(PV[k]-PV[k-1])/dt
alpha = Tf/(Tf+dt)
Qraw = 45 + P + I + D + FF
Qcmd = clip(Qraw, 0, 100)
I[k+1] = I[k] + dt×[Ki×e + (Qcmd-Qraw)/Tt]
Tt = Ti/2
```

Kp se mide en L/min/cm; Ki en L/min/(cm·s); Kd en (L/min)·s/cm.
Ti, Td, Tf y dt se expresan en segundos. El signo menos de D aparece porque
derivamos PV. El filtro atenúa ruido y evita derivar directamente diferencias
de sensor sin filtrar. No hay golpe D ante un cambio aislado de SP.

El anti-windup corrige el estado integral cuando la bomba satura. Sigue la orden
limitada antes del retardo: el caudal retardado no debe confundirse con saturación.

SIMC para integrador: Kc = 1/[k' (tau_c+theta)]. La regla general usa
Ti = min(tau1,4(tau_c+theta)); para integrador ideal se usa 4(tau_c+theta).
Los valores finales del artículo incluyen ajustes experimentales posteriores.

| Celda | Kc original | Ti original (s) | theta (s) | Kff |
|---|---:|---:|---:|---:|
| 1 | -62 | 56 | 7 | 0.8 |
| 2 | -76 | 30 | 6 | 0.8 |
| 3 | -85 | 44 | 3 | 1.0 |

Balance geométrico, factor 1: Kp = [-3.408264,-4.177872,-4.672620].
El panel SIMC muestra Ki y Kd calculados, la referencia y los valores aplicados.
Td=2 s, Tf=2 s y Tt=Ti/2 son decisiones académicas, no parámetros experimentales
del PID del artículo. Cambiar Ti, Kff o el factor exige revisar otra vez la respuesta.

## 6. PID frente a PID + feedforward

PID responde al error de nivel. FF usa el caudal entrante medido para anticipar
su efecto: FF = Kff×(Qin−45). La forma posicional se conserva del simulador.
El artículo expresa incrementos entre muestras; acumular esos incrementos desde
el nominal equivale a esta forma. No se afirma una reproducción exacta del
programa experimental. FF no elimina el efecto del retardo ni reemplaza al PID.

Ensayo recomendado: balance geométrico, SP e inicial 30 cm, 600 s, dt=1 s,
Td=Tf=2 s, factor=1, sin ruido, pulso +12 L/min desde 180 hasta 280 s.

| Celda | IAE PID | IAE PID+FF | Mejora IAE | Recuperación PID / FF |
|---|---:|---:|---:|---:|
| 1 | 365.32 | 80.11 | 78.1% | 148 / 60 s |
| 2 | 249.84 | 70.78 | 71.7% | 156 / 83 s |
| 3 | 321.64 | 39.77 | 87.6% | 189 / 76 s |

Unidades de IAE: cm·s. Son resultados de esta simulación nominal, no del artículo.
No hay saturación en ese ensayo. El error final máximo es menor de 0.00022 cm.
Sin perturbación y desde equilibrio, niveles = 30 cm y bombas = 45 L/min.

IAE integra |e|; ISE integra e² y penaliza más los errores grandes. Las tablas
usan h simulado; el controlador y el gráfico de error usan PV, con ruido opcional.
El sobreimpulso presentado es exceso sobre SP, con porcentaje relativo a |SP|;
no es la fórmula de sobreimpulso relativa a la amplitud de un escalón de consigna.
Establecimiento/recuperación: desde el fin del pulso hasta permanecer en ±0.1 cm
durante el resto del ensayo, con al menos 30 s observados. Un vacío significa que
no se pudo observar o no se recuperó. La saturación es porcentaje de muestras.

## 7. Python y Ladder

`app.py` organiza controles y secciones; `simulation.py` calcula cada muestra;
`animation.py` y `assets/animation.html` reproducen los registros; `reporting.py`
exporta CSV y PDF. `education.py` contiene explicaciones y el diagrama de flujo.

`plc/LADDER.md` contiene las redes de contactos, enclavamientos, alarmas y llamadas
a PID. `PID_Filtered.st` implementa el bloque IEC; `FlotationBank.st` muestra las
tres instancias independientes, señales y mandos. La tarea propuesta es de 1 s.
El diseño se debe llevar al editor gráfico y comprobar en la versión de OpenPLC
disponible. **No fue compilado ni ejecutado en un PLC real.**

En Python los retardos pertenecen al proceso simulado. En PLC pertenecen a la
planta física: no se retrasan otra vez las órdenes. La calibración de LI y bombas
y las direcciones de E/S dependen del montaje. No se inventan direcciones reales.
El reinicio sin golpe proporcional y los umbrales 2/38 cm del ST son ampliaciones;
no deben confundirse con funciones probadas en el experimento. La emergencia
industrial debe tener hardware de seguridad independiente.

## 8. Demostración de los gráficos y exportaciones

En Panel principal seleccionar PID, avanzar a 180 s y reproducir. Observar que el
nivel reacciona antes de que actúe la salida retardada. Pausar en 195 s y cambiar
a PID + FF sin cambiar el instante; comparar niveles y caudales. Reiniciar.

En Gráficos, mostrar nivel/SP, PV, entrada, salida real, orden y error. Diferenciar
Qcmd de Qout: la segunda aparece después del retardo. En Comparación, explicar
IAE e ISE y descargar CSV y PDF. El informe corresponde a la configuración activa.

Si se aumenta mucho el factor de ganancia o se usan tiempos integrales agresivos,
puede perderse la estabilidad. Mostrar advertencias en vez de afirmar que cualquier
combinación funciona. Con ruido, una bomba puede moverse aunque h esté cerca de SP.

## 9. Preguntas del docente

**¿Por qué Kp es negativo?** Porque la bomba extrae: mayor salida reduce nivel.
Con e=SP−PV, ese signo aumenta la extracción cuando el nivel es alto.

**¿Por qué oscilaba la versión anterior?** Aplicaba Kc de la planta identificada
a un balance 18.19 veces más sensible. Anti-windup y saturación por sí solos no
arreglan una sintonización incompatible. También se corrigió un segundo extra de retardo.

**¿Se cambió el modelo para hacerlo estable?** Se preservó el balance geométrico
y se escaló el controlador justificadamente. El modelo identificado es una opción
separada, con los parámetros originales como referencia.

**¿Por qué incluir D si el artículo usa PI?** Es un requisito académico.
Se deriva la medición con filtro y se documenta que no fue parte de la validación original.

**¿Qué hace el anti-windup?** Evita que la integral siga creciendo sin efecto cuando
la bomba ya alcanzó su límite, facilitando la recuperación posterior.

**¿Por qué no es exactamente 30 cm durante la perturbación?** Hay retardo y el
PID necesita responder; FF anticipa, pero no elimina un retardo físico.

**¿Qué demuestra la estabilidad?** Las pruebas muestran recuperación y ausencia de
ciclos sostenidos en los escenarios evaluados. No constituyen una demostración
analítica global para todos los parámetros o una validación industrial.

**¿Qué prueba la animación?** Permite visualizar las muestras del modelo. No es
evidencia de medición en una planta ni un cálculo distinto al de los gráficos.

**¿Se probó el PLC?** No. Se entrega diseño LD y ST complementario para trabajar en
OpenPLC; resta compilar, mapear E/S y validar en un banco seguro.

**¿Qué pasa sin perturbación?** Partiendo del equilibrio, los niveles se mantienen
en SP y los caudales coinciden. Ese caso solo verifica equilibrio; las perturbaciones
y otras condiciones iniciales evalúan recuperación.

**¿Qué es GitHub?** Aloja el código y su historial Git. No ejecuta por sí mismo el
servidor Streamlit. Los cambios públicos se publican solo después de autorización.

**¿Qué hace Streamlit Cloud?** Instala requirements, ejecuta app.py desde la rama
main del repositorio y proporciona una URL pública. No se debe afirmar despliegue
hasta abrir la URL y probar simulación y PDF sin iniciar sesión.

## 10. Conclusiones

El control requiere coherencia entre unidades, ganancia de proceso, signos,
retardos y sintonización. En el ensayo nominal, PID y PID + FF recuperan SP;
FF reduce IAE y tiempo de recuperación. La ampliación mantiene D, anti-windup y
límites explícitos. Los resultados son reproducibles y exportables, con límites
claros sobre lo simulado y lo no validado.

Publicación y despliegue: seguir `DEPLOYMENT.md`. El estado comprobado de pruebas
y los pendientes se registran en `VALIDACION.md`.
