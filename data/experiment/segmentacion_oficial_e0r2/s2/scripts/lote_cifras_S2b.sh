#!/bin/zsh
# Tramo 2 de S2 de U-SEG-OFICIAL: health-check de la tanda 1, ablación, resúmenes y cifras_segmentacion_oficial.md, desde
# las salidas crudas (USD 0, sin API).
# Uso: zsh lote_cifras_S2b.sh <repo> <copia> <raíz mínima> <E0 corregida> <historicas> <lote> <trabajo>
#   <historicas>: salida de lote_e0_historicas_S2b.sh (e0_92b45d6, e0_e1c9456, e0_9f6361e6);
#   <lote>: salida de lote_tramo2_S2b.sh (r5_*.json, censo_renglones_S2b.json, detector_116_S2b.json, censo_sd_152_S2b.json);
#   <trabajo>: carpeta nueva; ahí quedan cifras/ (los JSON de s2/cifras/) y cifras_segmentacion_oficial.md.
set -e
R="$1"; C="$2"; RZ="$3"; E0="$4"; H="$5"; L="$6"; T="$7"
PY="$R/.venv/bin/python"
export PYTHONDONTWRITEBYTECODE=1
SC="$C/data/experiment/segmentacion_oficial_e0r2/s2/scripts"
M="$C/data/experiment/segmentacion_oficial_e0r2/s0_6/b/manifiestos/manifest_salida_e0_152_S0-6b.json"
mkdir -p "$T/cifras" "$T/hc"
args=()
for t in $("$PY" -B -c "import json,sys; print(' '.join(f['to'] for f in json.load(open(sys.argv[1]))['filas']))" \
           "$C/data/experiment/segmentacion_oficial_e0r2/s2/lista_tanda1_S2.json"); do
  args+=(--pdf "$RZ/data/experiment/escalado_prep/pdfs/$t.pdf")
done
"$PY" -B "$RZ/data/experiment/reextraccion_v2/e0_chunking/healthcheck_e0.py" "${args[@]}" --salida "$T/hc/healthcheck_tanda1_S2b.json" > "$T/hc/stdout.txt"
"$PY" -B "$SC/resumen_healthcheck_S2.py" --hc "$T/hc/healthcheck_tanda1_S2b.json" --e0 "$E0" --manifiesto "$M" --out "$T/cifras/resumen_healthcheck_tanda1_S2b.json" > /dev/null
"$PY" -B "$SC/comparar_e0_historicas_S2.py" --e0 "92b45d6=$H/e0_92b45d6" --e0 "e1c9456=$H/e0_e1c9456" --e0 "9f6361e6=$H/e0_9f6361e6" \
  --e0 "corregida=$E0" --out "$T/cifras/comparar_e0_historicas_S2b.json" > /dev/null
"$PY" -B "$SC/atribuir_particion_S2.py" --r5 "$L/r5_corregida.json" --r5-cierre "$L/r5_e1c9456.json" --e0 "$E0" --e0-cierre "$H/e0_e1c9456" \
  --e0-c2 "$H/e0_9f6361e6" --raiz "$C" --out "$T/cifras/atribucion_particion_S2b.json" > /dev/null
"$PY" -B "$SC/escalera_r5_S2.py" --r5-r5 "$L/r5_92b45d6.json" --r5-cierre "$L/r5_e1c9456.json" \
  --historicas "$T/cifras/comparar_e0_historicas_S2b.json" --out "$T/cifras/escalera_r5_S2b.json" > /dev/null
"$PY" -B "$SC/cifras_punto3_S2.py" --e0 "$E0" --raiz "$C" --out "$T/cifras/cifras_punto3_S2b.json" > /dev/null
"$PY" -B "$SC/cifras_conjuntos_clases_S2.py" --e0 "$E0" --raiz "$C" --out "$T/cifras/cifras_conjuntos_clases_S2b.json" > /dev/null
"$PY" -B "$SC/ablacion_b582_S2.py" --codigo "$RZ" --e0 "$E0" --trabajo "$T/ablacion" --out "$T/cifras/ablacion_b582_S2b.json" --workers 4 > /dev/null
"$PY" -B "$SC/reglas_por_to_S2.py" --e0 "$E0" --raiz "$C" --ablacion "$T/cifras/ablacion_b582_S2b.json" --out "$T/cifras/reglas_por_to_S2b.json" > /dev/null
"$PY" -B "$SC/p7_en_la_corregida_S2.py" --e0 "$E0" --raiz "$C" --trabajo "$T/p7" --out "$T/cifras/p7_en_la_corregida_S2b.json" > /dev/null
"$PY" -B "$SC/roles_pagina_S2.py" --e0 "$E0" --raiz "$C" --out "$T/cifras/roles_pagina_S2b.json" > /dev/null
"$PY" -B "$SC/resumen_censos_S2.py" --lote "$L" --e0 "$E0" --raiz "$C" \
  --lista "$C/data/experiment/segmentacion_oficial_e0r2/s2/lista_tanda1_S2.json" --out "$T/cifras/censos_S2b.json" > /dev/null
"$PY" -B "$SC/cifras_s1quater_S2.py" --raiz "$C" --out "$T/cifras/s1quater_S2b.json" > /dev/null
"$PY" -B "$SC/marcas_4g_S2.py" --cifras "$T/cifras" --e0 "$E0" --raiz "$C" --out "$T/cifras/marcas_4g_S2b.json" > /dev/null
"$PY" -B "$SC/generar_cifras_S2.py" --cifras "$T/cifras" --out "$T/cifras_segmentacion_oficial.md"
