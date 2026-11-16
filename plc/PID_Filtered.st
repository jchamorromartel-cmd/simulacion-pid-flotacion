(* Ampliacion academica IEC 61131-3. No compilada ni validada en PLC real.
   Crear FUNCTION_BLOCK PID_Filtered en OpenPLC e importar declaraciones/cuerpo.
   Kp negativo, unidades cm, s, L/min. Llamar exactamente una vez por dt. *)
FUNCTION_BLOCK PID_Filtered
VAR_INPUT
    Enable : BOOL;
    PV : REAL;
    SP : REAL;
    Qin : REAL;
    Kp : REAL;
    Ti : REAL;
    Td : REAL;
    Tf : REAL;
    Kff : REAL;
    UseFF : BOOL;
    dt : REAL;
    Bias : REAL := 45.0;
    Qmin : REAL := 0.0;
    Qmax : REAL := 100.0;
END_VAR
VAR_OUTPUT
    Qcmd : REAL;
    Raw : REAL;
    P : REAL;
    IUsed : REAL;
    D : REAL;
    Saturated : BOOL;
    ConfigFault : BOOL;
END_VAR
VAR
    IState : REAL;
    PreviousPV : REAL;
    FilteredRate : REAL;
    Error : REAL;
    Alpha : REAL;
    FF : REAL;
    WasEnabled : BOOL;
END_VAR

ConfigFault := (Ti <= 0.0) OR (Tf <= 0.0) OR (dt <= 0.0)
               OR (Td < 0.0) OR (Qmin >= Qmax) OR (Kp >= 0.0);
IF (NOT Enable) OR ConfigFault THEN
    Qcmd := 0.0;
    Raw := 0.0;
    P := 0.0;
    D := 0.0;
    IUsed := 0.0;
    IState := 0.0;
    FilteredRate := 0.0;
    PreviousPV := PV;
    WasEnabled := FALSE;
    Saturated := FALSE;
ELSE
    Error := SP - PV;
    P := Kp * Error;
    IF NOT WasEnabled THEN
        (* Arranque sin golpe P: sesgo inicial; diferente del arranque Python. *)
        PreviousPV := PV;
        FilteredRate := 0.0;
        IState := -P;
    END_IF;
    Alpha := Tf / (Tf + dt);
    FilteredRate := Alpha * FilteredRate
                    + (1.0 - Alpha) * (PV - PreviousPV) / dt;
    D := -Kp * Td * FilteredRate;
    FF := 0.0;
    IF UseFF THEN
        FF := Kff * (Qin - Bias);
    END_IF;
    IUsed := IState;
    Raw := Bias + P + IUsed + D + FF;
    Qcmd := LIMIT(Qmin, Raw, Qmax);
    Saturated := (Raw < Qmin) OR (Raw > Qmax);
    IState := IState + dt * (Kp * Error / Ti + (Qcmd - Raw) / (Ti / 2.0));
    PreviousPV := PV;
    WasEnabled := TRUE;
END_IF;
END_FUNCTION_BLOCK
