#!/bin/zsh
# Tramo 3 de S2 de U-SEG-OFICIAL: la tanda final, su health-check y el re-censo de la release de E0, y el documento de cifras
# completo (USD 0, sin API).
# Uso: zsh lote_tramo3_S2c.sh <repo> <copia> <raíz mínima> <E0 corregida> <historicas> <lote> <trabajo>
#   los mismos argumentos que lote_cifras_S2b.sh, que corre primero (los 13 JSON del tramo 2 y el documento sin el tramo 3);
#   después: la lista de la tanda final, el health-check de sus PDFs, su resumen, tanda_final_S2.py con el resumen y el
#   documento con el §7. En <trabajo>/cifras quedan los 15 JSON de s2/cifras/ y en <trabajo> el documento.
set -e
R="$1"; C="$2"; RZ="$3"; E0="$4"; H="$5"; L="$6"; T="$7"
PY="$R/.venv/bin/python"
export PYTHONDONTWRITEBYTECODE=1
SC="$C/data/experiment/segmentacion_oficial_e0r2/s2/scripts"
M="$C/data/experiment/segmentacion_oficial_e0r2/s0_6/b/manifiestos/manifest_salida_e0_152_S0-6b.json"
zsh "$SC/lote_cifras_S2b.sh" "$R" "$C" "$RZ" "$E0" "$H" "$L" "$T"
mkdir -p "$T/hc_tanda_final"
"$PY" -B "$SC/tanda_final_S2.py" --e0 "$E0" --raiz "$C" --censos "$L" --out "$T/hc_tanda_final/tanda_final_sin_hc.json" > /dev/null
args=()
for t in $("$PY" -B -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))['tanda_final']['lista']))" \
           "$T/hc_tanda_final/tanda_final_sin_hc.json"); do
  args+=(--pdf "$RZ/data/experiment/escalado_prep/pdfs/$t.pdf")
done
"$PY" -B "$RZ/data/experiment/reextraccion_v2/e0_chunking/healthcheck_e0.py" "${args[@]}" \
  --salida "$T/hc_tanda_final/healthcheck_tanda_final_S2c.json" > "$T/hc_tanda_final/stdout.txt"
"$PY" -B "$SC/resumen_healthcheck_S2.py" --hc "$T/hc_tanda_final/healthcheck_tanda_final_S2c.json" --e0 "$E0" --manifiesto "$M" \
  --out "$T/cifras/resumen_healthcheck_tanda_final_S2c.json" > /dev/null
"$PY" -B "$SC/tanda_final_S2.py" --e0 "$E0" --raiz "$C" --censos "$L" --hc "$T/cifras/resumen_healthcheck_tanda_final_S2c.json" \
  --out "$T/cifras/tanda_final_S2c.json" > /dev/null
"$PY" -B "$SC/generar_cifras_S2.py" --cifras "$T/cifras" --out "$T/cifras_segmentacion_oficial.md"
