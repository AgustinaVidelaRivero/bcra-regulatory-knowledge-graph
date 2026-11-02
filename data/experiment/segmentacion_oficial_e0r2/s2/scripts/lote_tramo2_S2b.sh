#!/bin/zsh
# Tramo 2 de S2 de U-SEG-OFICIAL: controles de R5 y censos sobre la E0 corregida, en secuencia (USD 0, sin API).
# Uso: zsh lote_tramo2_S2b.sh <repo> <copia> <raíz mínima> <E0 corregida> <historicas> <trabajo>
#   <repo>: solo para el python del .venv; <copia>: copia del repo sin .env (el rsync de la cláusula);
#   <raíz mínima>: la de s0_4/scripts/raiz_minima.sh; <historicas>: la salida de lote_e0_historicas_S2b.sh, con
#   raiz_<commit>/ (con b584_particion/ y r2_codigo/ copiados de <copia>) y e0_<commit>/; <trabajo>: carpeta de salida.
# Todo va en secuencia: manual pide unos 5 GB por lectura.
set -e
R="$1"; C="$2"; RZ="$3"; E0="$4"; H="$5"; T="$6"
PY="$R/.venv/bin/python"
export PYTHONDONTWRITEBYTECODE=1
S="data/experiment/segmentacion_oficial_e0r2"
mkdir -p "$T"
paso() { print -r -- "$1 $(date '+%F %T')" >> "$T/tiempos.txt"; }
paso "inicio r5 corregida"
"$PY" -B "$C/data/experiment/r2_codigo/r5_escalera_particion.py" --comparar --atribuir --salida "$E0" --out "$T/r5_corregida.json" > "$T/r5_corregida.log" 2>&1
paso "inicio r5 e1c9456"
"$PY" -B "$H/raiz_e1c9456/data/experiment/r2_codigo/r5_escalera_particion.py" --comparar --atribuir --salida "$H/e0_e1c9456" --out "$T/r5_e1c9456.json" > "$T/r5_e1c9456.log" 2>&1
paso "inicio r5 92b45d6"
"$PY" -B "$H/raiz_92b45d6/data/experiment/r2_codigo/r5_escalera_particion.py" --comparar --atribuir --salida "$H/e0_92b45d6" --out "$T/r5_92b45d6.json" > "$T/r5_92b45d6.log" 2>&1
paso "inicio cache de renglones"
mkdir -p "$T/lineas"
"$PY" -B "$C/$S/s0_1/scripts/lineas_152.py" "$C" "$T/lineas" --workers 4 > "$T/lineas.log" 2>&1
paso "inicio censo de renglones"
"$PY" -B "$C/$S/s1bis/scripts/censo_renglones_S1bis.py" --e0 "$E0" --manifiesto "$C/$S/s1ter/manifiesto/segmentacion_oficial_e0r2_152.json" \
  --lineas "$T/lineas" --regla "$C/$S/s1/regla_censo_renglones_S1.md" --cambio "$C/$S/s1bis/regla_censo_renglones_S1bis.md" \
  --pro "$C/data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b" --out "$T/censo_renglones_S2b.json" > "$T/censo_renglones.log" 2>&1
paso "inicio detector 1.16"
"$PY" -B "$C/$S/s0_5/scripts/detector_116.py" --e0 "$E0" --out "$T/detector_116_S2b.json" > "$T/detector_116.log" 2>&1
paso "inicio censo de sub-documentos"
"$PY" -B "$C/$S/s0_4/scripts/censo_sd_152.py" --codigo "$RZ" --corrida "$E0" --g3 "$C/$S/s0_3/censos/g3_raices_sucesoras_rechazadas.json" \
  --salida "$T/censo_sd_152_S2b.json" --workers 4 > "$T/censo_sd.log" 2>&1
paso "fin"
