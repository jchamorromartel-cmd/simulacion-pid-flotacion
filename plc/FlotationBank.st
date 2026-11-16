(* Programa conceptual. Configurar tarea ciclica de 1000 ms.
   Asignar las variables a E/S solo despues de calibrar los instrumentos.
   NO es un programa de seguridad certificado. La E-stop real requiere
   circuito de seguridad independiente. No se han validado compilacion ni E/S. *)
PROGRAM FlotationBank
VAR
    Start : BOOL;
    Stop : BOOL;
    ResetAlarm : BOOL;
    EStopOK : BOOL;
    SensorHealthy1 : BOOL;
    SensorHealthy2 : BOOL;
    SensorHealthy3 : BOOL;
    LI1 : REAL := 30.0;
    LI2 : REAL := 30.0;
    LI3 : REAL := 30.0;
    Qin1 : REAL := 45.0;
    Qin2 : REAL := 45.0;
    Qin3 : REAL := 45.0;
    SP1 : REAL := 30.0;
    SP2 : REAL := 30.0;
    SP3 : REAL := 30.0;
    UseFF : BOOL := TRUE;
    (* TRUE = balance geometrico; FALSE = modelo identificado de referencia.
       Esta seleccion no sustituye la identificacion de una planta real. *)
    GeometricModel : BOOL := TRUE;
    ScaleK : REAL;
    Run : BOOL;
    AlarmLatched : BOOL;
    LevelAlarm : BOOL;
    Trip : BOOL;
    StartEdge : R_TRIG;
    ResetEdge : R_TRIG;
    P1 : PID_Filtered;
    P2 : PID_Filtered;
    P3 : PID_Filtered;
    Pump1Cmd : REAL;
    Pump2Cmd : REAL;
    Pump3Cmd : REAL;
    Pump4Cmd : REAL;
    AlarmSaturation : BOOL;
END_VAR

StartEdge(CLK := Start);
ResetEdge(CLK := ResetAlarm);
LevelAlarm := (LI1 < 2.0) OR (LI1 > 38.0)
              OR (LI2 < 2.0) OR (LI2 > 38.0)
              OR (LI3 < 2.0) OR (LI3 > 38.0);
Trip := (NOT EStopOK) OR (NOT SensorHealthy1) OR (NOT SensorHealthy2)
        OR (NOT SensorHealthy3) OR LevelAlarm;
IF Trip THEN
    AlarmLatched := TRUE;
ELSIF ResetEdge.Q THEN
    AlarmLatched := FALSE;
END_IF;
(* Trip y Stop tienen prioridad; Reset no arranca las bombas. *)
IF Trip OR AlarmLatched OR Stop THEN
    Run := FALSE;
ELSIF StartEdge.Q AND NOT ResetEdge.Q THEN
    Run := TRUE;
END_IF;

ScaleK := 1.0;
IF GeometricModel THEN
    ScaleK := 0.001018 / (1000.0 / (60.0 * 900.0));
END_IF;
P1(Enable := Run, PV := LI1, SP := SP1, Qin := Qin1,
   Kp := -62.0 * ScaleK, Ti := 56.0, Td := 2.0, Tf := 2.0,
   Kff := 0.8, UseFF := UseFF, dt := 1.0);
P2(Enable := Run, PV := LI2, SP := SP2, Qin := Qin2,
   Kp := -76.0 * ScaleK, Ti := 30.0, Td := 2.0, Tf := 2.0,
   Kff := 0.8, UseFF := UseFF, dt := 1.0);
P3(Enable := Run, PV := LI3, SP := SP3, Qin := Qin3,
   Kp := -85.0 * ScaleK, Ti := 44.0, Td := 2.0, Tf := 2.0,
   Kff := 1.0, UseFF := UseFF, dt := 1.0);
Pump1Cmd := P1.Qcmd;
Pump2Cmd := P2.Qcmd;
Pump3Cmd := P3.Qcmd;
Pump4Cmd := 0.0;
IF Run THEN
    Pump4Cmd := 45.0;
END_IF;
AlarmSaturation := P1.Saturated OR P2.Saturated OR P3.Saturated;
(* Sin colas de retardo: en PLC son propiedad del proceso fisico.
   Qin2/Qin3 deben ser caudales medidos, no las ordenes Pump1Cmd/Pump2Cmd.
   Salidas en L/min: calibrar conversion a rpm/4-20 mA segun cada bomba. *)
END_PROGRAM
