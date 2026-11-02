#!/bin/zsh
# Mesa, §387 (01/11/2026): reproduce el análisis y la exactitud de cita de B6.4 sobre una copia, con las mismas semillas y los mismos
# argumentos que los comandos llenos de la §384 (corrida_analisis_B64.zsh y corrida_exactitud_de_cita_B64.zsh), y compara byte a byte
# las dos salidas con las de la autora (e0511054… y 3defc8a1…). Lo que cambia respecto de esos comandos:
#   - el código de B6.4 es una copia de analisis_b64_corr/codigo/, controlada contra lista_H6_corr.txt, y la lista contra su sello;
#   - los dos clones de HEAD y las salidas van a <trabajo>, una carpeta nueva del scratchpad de la sesión;
#   - las salidas se llaman igual que las de la autora (analisis/ y exactitud_de_cita/), porque el JSON guarda el nombre de cada carpeta.
# Las entradas se leen donde están, en solo lectura. Antes y después saca la foto del repo (HEAD, origin/main, git status y el índice)
# y la de las carpetas de entrada de fuera_del_repo (ruta, bytes y mtime de cada archivo, sin las marcas), y las compara.
# Imprime solo horas, códigos de salida, sha256 y, si una salida difiere, las rutas de claves que difieren: ningún valor. USD 0.
# Uso: zsh reproducir_analisis_y_exactitud_B64_mesa.zsh <trabajo, que no existe> <carpeta de este script>
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"; T="$1"; AQUI="$2"
PY="${BCRA_KG_PYTHON:-python3}"; H6="$F/analisis_b64_corr"; SA="$H6/salidas/a"; PL="$H6/adjudicacion/para_leer"
ESPERADO="$H6/esperado/esperado_b64.json"; SHA_ESPERADO=7b70ce7e230ff41c1dc6993677073b6b2f8da403168e6f0ee6142a9b55dffba1
ANA_SHA=e05110545684a7b1a68e41278e7d2137cc244e8d2c113a2e1aa8b8a405a58ae8
EXA_SHA=3defc8a175be0c93d89eb430001fbee9b3e884d02148a1a467e0ea69dab25c23
ENTRADA="$R/data/experiment/banco_mcp/b64/entrada_B64.json"; MANIFIESTO="$F/banco_b64/manifiesto_fuera_B64.json"
D10="$F/banco_b64/juez/d10_b63.json"; FECHAS="$F/banco_b64/resultados/real/fechas_b63.json"
CLASES="$H6/entradas_mesa/clases_documentos_B64.json"; LUGARES="$H6/entradas_mesa/lugares_B64.json"; EXPERTOS="$F/b64_material_expertos"
CLAVE="$F/banco_b64_sp_382/clave_para_despues_B64/clave_adjudicacion_b64.json"; BANCO="$F/banco_b64"
E0="$R/data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b"
ARMADO_E0="$R/data/experiment/tanda_final/t3/acumulado/armado_acumulado_128_tf.json"; UCITA="$R/scripts/ucita2_indicadores_banco.py"
[[ -e "$T" ]] && { print -r -- "FRENO: $T ya existe"; exit 30; }
mkdir -p "$T/foto" "$T/a" || exit 30

foto() {   # $1: antes o después
  { date '+%Y-%m-%d %H:%M:%S %z'
    git -C "$R" --no-optional-locks rev-parse HEAD origin/main
    git -C "$R" --no-optional-locks status --porcelain | shasum -a 256
    git -C "$R" --no-optional-locks ls-files -s | shasum -a 256 } > "$T/foto/repo_$1.txt"
  for d in analisis_b64_corr banco_b64 banco_b64_sp_382 banco_b64_control_36 b64_material_expertos; do
    ( cd "$F/$d" && find . \( -name 'NO_ABRIR_*' -o -name '*_SOLO_MESA*' -o -name '.env*' -o -name 'tripletas_t_v3' \) -prune \
        -o -type f -exec stat -f '%z %m %N' {} + | LC_ALL=C sort -k3 )
  done > "$T/foto/entradas_$1.txt"
}
foto antes
print -r -- "foto de antes: $(head -1 "$T/foto/repo_antes.txt"); $(wc -l < "$T/foto/entradas_antes.txt" | tr -d ' ') archivos de entrada"

# 1. El código de B6.4: la lista contra su sello, la copia contra la lista
grep -qF "sha256: $(shasum -a 256 "$H6/lista_H6_corr.txt" | cut -c1-64)" "$H6/sello_H6_corr.txt" || { print -r -- "FRENO: la lista no es la del sello"; exit 31; }
cp -R "$H6/codigo" "$T/codigo" || exit 31
n=0
for f in "$T"/codigo/*(.); do
  grep -qF "$(shasum -a 256 "$f" | cut -c1-64)  $(stat -f %z "$f")  codigo/${f:t}" "$H6/lista_H6_corr.txt" || { print -r -- "FRENO: no es el de la lista: ${f:t}"; exit 31; }
  (( n++ ))
done
print -r -- "el código copiado: $n archivos, cada uno con el sha256 y los bytes de lista_H6_corr.txt"

# 2. Los dos clones de HEAD, con las mismas rutas que los comandos llenos, y sus sha256
for cual in analisis exactitud; do
  mkdir "$T/clon_head_${cual}_B64" || exit 32
done
git -C "$R" --no-optional-locks archive HEAD \
  data/experiment/banco_mcp/b63/v2/b2/comun_b63.py data/experiment/banco_mcp/b63/v2/b2/juez_b63.py \
  data/experiment/banco_mcp/comun_banco.py data/experiment/banco_mcp/lectura_tolerante_juez.py \
  data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py data/experiment/ev2_juez/prompt_juez_v1.md \
  data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/analisis/codigo/analizar_b63.py data/experiment/banco_mcp/b63/analisis/codigo/aplicar_lectura_tolerante_b63.py \
  | tar -x -C "$T/clon_head_analisis_B64" || { print -r -- "FRENO: no se pudo armar el clon del análisis"; exit 32; }
git -C "$R" --no-optional-locks archive HEAD \
  data/experiment/banco_mcp/b63/v2/b2/comun_b63.py data/experiment/banco_mcp/b63/v2/b2/juez_b63.py \
  data/experiment/banco_mcp/comun_banco.py data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py \
  data/experiment/ev2_juez/prompt_juez_v1.md data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/analisis/codigo/analizar_b63.py data/experiment/banco_mcp/b63/analisis/codigo/aplicar_lectura_tolerante_b63.py \
  data/experiment/banco_mcp/b63/analisis/codigo/exactitud_de_cita_9_4_b63.py \
  data/experiment/banco_mcp/mcp_kg/familias_nav_rel.py data/experiment/banco_mcp/mcp_kg/familias_nav_rel_amp.py \
  | tar -x -C "$T/clon_head_exactitud_B64" || { print -r -- "FRENO: no se pudo armar el clon de la exactitud"; exit 32; }
XA="$T/clon_head_analisis_B64/data/experiment"; CA="$XA/banco_mcp/b63/analisis/codigo"
XE="$T/clon_head_exactitud_B64/data/experiment"; CE="$XE/banco_mcp/b63/analisis/codigo"
typeset -A SHA
SHA=("$CA/analizar_b63.py" 9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb
     "$CA/aplicar_lectura_tolerante_b63.py" 5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372
     "$CE/analizar_b63.py" 9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb
     "$CE/aplicar_lectura_tolerante_b63.py" 5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372
     "$CE/exactitud_de_cita_9_4_b63.py" 5207941b4a54dd2e7071e5d1438fe0b664c0cfd2df56794614ab56de4e6f272a
     "$XE/banco_mcp/mcp_kg/familias_nav_rel.py" 1b368333838b3d090b923e7d4b3db31751b7e06946ccc31038b4d41a30f125a7
     "$XE/banco_mcp/mcp_kg/familias_nav_rel_amp.py" d5e9aff19bd7d26143b0a9b7a7074844d90bac6405a2dd1a30bd119ff46f9022
     "$R/data/experiment/banco_mcp/b64/v1/juez_b63.py" 4fa095019dfa5d085ca5eeff1acc40f05f50ee482de9e649d9d042d03012e53b
     "$R/data/experiment/banco_mcp/b64/v1/comun_b63.py" 631037e968174a5743869a27d0a5b4275cf5bb5cdaa2bc1dfc3a49890d6998cc
     "$UCITA" 3a58e5be33f2e7b1903c7c07ccfba00ef135f3b8da930f62490449577810e920
     "$ESPERADO" "$SHA_ESPERADO")
for f s in "${(@kv)SHA}"; do
  [[ "$(shasum -a 256 "$f" | cut -c1-64)" == "$s" ]] || { print -r -- "FRENO: no da su sha256: ${f:t}"; exit 32; }
done
print -r -- "los dos clones y los fijos dan su sha256 (${#SHA} archivos)"

# 3. El análisis, con los mismos argumentos que el comando lleno salvo el código, el clon y la salida
print -r -- "el análisis empieza: $(date '+%H:%M:%S')"
cd "$T" && B64_CODIGO_B63="$CA" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$T/codigo/analizar_b64.py" --clon "$XA/banco_mcp/b63/v2/b2" \
  --entrada "$ENTRADA" --manifiesto-fuera "$MANIFIESTO" --banco-b64 "$BANCO" \
  --agregados "$SA/aplicacion/juez_con_lectura_tolerante/agregados_b63_ciego.json" \
  --agregados-tolerante "$SA/aplicacion/agregados_de_las_que_no_se_leian_b63.json" \
  --veredictos-tolerante "$SA/aplicacion/veredictos_lectura_tolerante_b63.jsonl" \
  --agregados-sin-lectura "$SA/aplicacion/agregados_sin_lectura_b64.json" \
  --planilla "$PL/planilla_adjudicacion_b64.csv" --sello-planilla "$PL/sello_adjudicacion_b64.txt" \
  --estructura-planilla "$PL/estructura_planilla_adjudicacion_b64.json" --clave-adjudicacion "$CLAVE" \
  --d10 "$D10" --fechas "$FECHAS" --clases-documentos "$CLASES" --lugares "$LUGARES" --expertos "$EXPERTOS" \
  --esperado "$ESPERADO" --salida "$T/a/analisis" > "$T/a/consola_analisis_B64.txt" 2>&1
print -r -- "el análisis termina: $(date '+%H:%M:%S'), sale con $?"

# 4. La exactitud de cita, igual
print -r -- "la exactitud empieza: $(date '+%H:%M:%S')"
cd "$T" && B64_CODIGO_B63="$CE" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$T/codigo/exactitud_de_cita_9_4_b64.py" \
  --clon "$XE/banco_mcp/b63/v2/b2" --entrada "$ENTRADA" --manifiesto-fuera "$MANIFIESTO" --banco-b64 "$BANCO" --e0 "$E0" \
  --armado-e0 "$ARMADO_E0" --ucita "$UCITA" --esperado "$ESPERADO" --salida "$T/a/exactitud_de_cita" \
  > "$T/a/consola_exactitud_de_cita_B64.txt" 2>&1
print -r -- "la exactitud termina: $(date '+%H:%M:%S'), sale con $?"

# 5. La comparación, byte a byte; si difiere, las rutas de claves que difieren, sin valores
for par in "analisis/analisis_B64.json $ANA_SHA" "exactitud_de_cita/exactitud_de_cita_B64.json $EXA_SHA"; do
  rel="${par% *}"; s="${par#* }"
  if [[ ! -f "$T/a/$rel" ]]; then print -r -- "MAL $rel: la reproducción no lo escribió"; continue; fi
  n="$(shasum -a 256 "$T/a/$rel" | cut -c1-64)"
  if [[ "$n" == "$s" ]] && cmp -s "$T/a/$rel" "$SA/$rel"; then
    print -r -- "OK  $rel: idéntico byte a byte al de la autora ($s)"
  else
    print -r -- "MAL $rel: da $n, y el de la autora $s"
    PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$AQUI/rutas_que_difieren_mesa.py" "$SA/$rel" "$T/a/$rel"
  fi
done

foto después
cmp -s "$T/foto/entradas_antes.txt" "$T/foto/entradas_después.txt" && print -r -- "OK  las carpetas de entrada no cambiaron" \
  || print -r -- "MAL las carpetas de entrada cambiaron"
cmp -s <(tail -n +2 "$T/foto/repo_antes.txt") <(tail -n +2 "$T/foto/repo_después.txt") && print -r -- "OK  el repo no cambió" \
  || print -r -- "MAL el repo cambió"
print -r -- "foto de después: $(head -1 "$T/foto/repo_después.txt")"
exit 0
