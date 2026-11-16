# Diseño Ladder para OpenPLC

Se entrega lógica LD en notación textual de peldaños y los bloques ST complementarios.
No es un archivo gráfico nativo importable ni se ha compilado o ejecutado en OpenPLC.
Crear los POUs y dibujar los peldaños en el editor; consultar la versión instalada.
Los nombres y las conexiones se corresponden con `FlotationBank.st`.

Símbolos: `[ X ]` contacto normalmente abierto, `[/X]` contacto negado,
`( X )` bobina, `(S X)` SET, `(R X)` RESET. Los comparadores y PID son cajas FB.
Ejecutar redes en el orden indicado en tarea cíclica de **1000 ms**.

```text
Red 1: flancos (R_TRIG evita rearranque al mantener START pulsado)
|----[ R_TRIG StartEdge(CLK=Start) ]---------------------------|
|----[ R_TRIG ResetEdge(CLK=ResetAlarm) ]----------------------|

Red 2: alarmas (cajas LT/GT por cada LI; OR entre resultados)
|--[ LT LI1 2 ]--+--------------------------------(LevelAlarm)|
|--[ GT LI1 38 ]-|
|--[ LT LI2 2 ]--|
|--[ GT LI2 38 ]-|
|--[ LT LI3 2 ]--|
|--[ GT LI3 38 ]-|

Red 3: OR de condiciones de disparo
|--[/EStopOK]---------+-------------------------------(Trip)--|
|--[/SensorHealthy1]--|
|--[/SensorHealthy2]--|
|--[/SensorHealthy3]--|
|--[LevelAlarm]-------|

Red 4: retención de alarma, disparo prioritario
|--[ResetEdge.Q]--[/Trip]--------------------(R AlarmLatched)--|
|--[Trip]----------------------------------(S AlarmLatched)--|

Red 5: marcha con arranque deliberado; reset simultáneo no arranca
|--[StartEdge.Q]--[/ResetEdge.Q]--[/Stop]--[/Trip]--[/AlarmLatched]--(S Run)--|
|--[Stop]---------+------------------------------------(R Run)--|
|--[Trip]---------|
|--[AlarmLatched]-|

Red 6: tres FB llamados SIEMPRE, con Enable conectado a Run
|--[ PID_Filtered P1: Enable=Run PV=LI1 SP=SP1 Qin=Qin1 ]-------|
|--[ PID_Filtered P2: Enable=Run PV=LI2 SP=SP2 Qin=Qin2 ]-------|
|--[ PID_Filtered P3: Enable=Run PV=LI3 SP=SP3 Qin=Qin3 ]-------|
   Kp = [-62,-76,-85]*ScaleK; Ti=[56,30,44]; Td=Tf=2; dt=1
   Kff=[0.8,0.8,1]; UseFF=UseFF; Bias=45; Qmin=0; Qmax=100

Red 7: salidas de bombas (cajas MOVE / SEL)
|--[MOVE P1.Qcmd -> Pump1Cmd]---------------------------------|
|--[MOVE P2.Qcmd -> Pump2Cmd]---------------------------------|
|--[MOVE P3.Qcmd -> Pump3Cmd]---------------------------------|
|--[SEL G=Run IN0=0 IN1=45 -> Pump4Cmd]------------------------|

Red 8: alarma de saturación (informativa, sin disparo)
|--[P1.Saturated]--+-----------------------(AlarmSaturation)---|
|--[P2.Saturated]--|
|--[P3.Saturated]--|
```

El bloque PID debe ejecutarse también cuando `Run=FALSE`: su entrada Enable
lleva la condición, no un contacto que omita la llamada. De otro modo podría
mantener la última salida. El ST incluido aplica esa misma prioridad.

## Variables y señales

| Variable | Tipo IEC | Unidad / función |
|---|---|---|
| LI1, LI2, LI3 | REAL | Nivel calibrado, cm; rango sensor 0–39 |
| SP1, SP2, SP3 | REAL | Consignas, cm |
| Qin1, Qin2, Qin3 | REAL | Caudales medidos, L/min |
| Start, Stop, ResetAlarm | BOOL | Mandos del operador |
| EStopOK | BOOL | Permisivo de emergencia, TRUE = circuito sano |
| SensorHealthy1..3 | BOOL | Diagnóstico de cada sensor |
| Pump1Cmd..4Cmd | REAL | Referencias de caudal, L/min |
| AlarmLatched, LevelAlarm | BOOL | Alarmas retenida y de nivel |
| P1, P2, P3 | PID_Filtered | Estados independientes del controlador |
| ScaleK | REAL | 1 para referencia identificada; 0.054972 para balance |

No se asignan direcciones `%IW` o `%QW` ficticias: dependen del hardware y driver.
Las señales crudas deben escalarse a cm y L/min; las salidas deben calibrarse a
rpm o corriente. El artículo no proporciona una calibración universal para ello.

## Diferencias con Python

Python calcula un proceso simulado y aplica colas de 7/6/3 s. El programa PLC
controla un proceso externo, que ya contiene esos retardos. Añadir otras colas
duplicaría el retardo. Python arranca en equilibrio con I=0; el FB ST tiene
arranque/reinicio sin golpe proporcional con I=-Kp·e. El FF puede producir un
cambio inicial si Qin no es el nominal. Los umbrales 2/38 cm y el enclavamiento
son supuestos docentes adicionales; no pertenecen al experimento original.

No ejecutar ambos `FlotationBank` ST y redes LD equivalentes sobre las mismas
salidas. Elegir una implementación; el ST sirve de referencia para dibujar LD.
La emergencia real exige circuito independiente: estas redes no certifican seguridad.

Referencia: https://edge.autonomylogic.com/docs/openplc-editor/overview/
