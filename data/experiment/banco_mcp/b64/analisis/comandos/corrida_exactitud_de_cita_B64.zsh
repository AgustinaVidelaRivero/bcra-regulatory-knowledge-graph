#!/bin/zsh
# La exactitud de cita de B6.4 (§9): exactitud_de_cita_9_4_b64.py, con el instrumento de citas del repo, que corre desde el repo en solo
# lectura. Con la corrección del H-6 (decisión 2), el instrumento corre dos veces: la principal, sin las dos secciones de N7c+ en las
# copias de los log_r1, y la informativa, sin el recorte; los literales de esas secciones salen del código de N7c+ del clon de HEAD.
# Controla antes los sha256: la lista y el sello de la corrección del H-6 y el código de B6.4 en ellos, el código de B6.3 y el de N7c+ en
# un clon de HEAD (por rutas explícitas), el juez de la corrida (b64/v1), el instrumento y el JSON de los esperados, lleno (la exactitud
# frena si una entrada no da el suyo). El manifiesto, el de H-4 (corrida_manifiesto_fuera_B64.zsh). Lo que todavía no existe va como
# PENDIENTE, y el comando no corre hasta que se llene.
# Uso: zsh corrida_exactitud_de_cita_B64.zsh <scratchpad>
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"; SP="$1"
PY="${BCRA_KG_PYTHON:-python3}"; H6="$F/analisis_b64_corr"; SA="$H6/salidas/a"
ESPERADO="PENDIENTE"           # la copia llena de codigo/esperado_b64_plantilla.json
SHA_ESPERADO="PENDIENTE"       # su sha256
ENTRADA="PENDIENTE"            # H-3: la entrada de B6.4
MANIFIESTO="$F/banco_b64/manifiesto_fuera_B64.json"    # H-4: correr_b63.py --manifiesto-fuera (corrida_manifiesto_fuera_B64.zsh)
E0="PENDIENTE"                 # la E0 del grafo evaluado (en B6.3, data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b)
ARMADO_E0="PENDIENTE"          # su armado (en B6.3, tanda_final/t3/acumulado/armado_acumulado_128_tf.json de HEAD)
BANCO="$F/banco_b64"
UCITA="$R/scripts/ucita2_indicadores_banco.py"
for v in ESPERADO SHA_ESPERADO ENTRADA MANIFIESTO E0 ARMADO_E0; do
  [[ "${(P)v}" == PENDIENTE ]] && { print -r -- "falta llenar $v"; exit 22; }
done
# 1. La lista y el sello de la corrección del H-6, y el código de B6.4 en la lista
grep -qF "sha256: $(shasum -a 256 "$H6/lista_H6_corr.txt" | cut -c1-64)" "$H6/sello_H6_corr.txt" || { print -r -- "la lista no es la del sello de la corrección del H-6"; exit 20; }
for f in codigo/exactitud_de_cita_9_4_b64.py codigo/analizar_b64.py codigo/selftest_exactitud_de_cita_9_4_b64.py; do
  grep -qF "$(shasum -a 256 "$H6/$f" | cut -c1-64)  $(stat -f %z "$H6/$f")  $f" "$H6/lista_H6_corr.txt" || { print -r -- "no es el de la lista: $f"; exit 20; }
done
# 2. El clon de HEAD, solo con lo que se importa y lee, por rutas explícitas, y sus sha256; el juez de la corrida; el instrumento; el JSON
#    de los esperados
mkdir "$SP/clon_head_exactitud_B64" && git -C "$R" --no-optional-locks archive HEAD \
  data/experiment/banco_mcp/b63/v2/b2/comun_b63.py data/experiment/banco_mcp/b63/v2/b2/juez_b63.py \
  data/experiment/banco_mcp/comun_banco.py data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py \
  data/experiment/ev2_juez/prompt_juez_v1.md data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/analisis/codigo/analizar_b63.py data/experiment/banco_mcp/b63/analisis/codigo/aplicar_lectura_tolerante_b63.py \
  data/experiment/banco_mcp/b63/analisis/codigo/exactitud_de_cita_9_4_b63.py \
  data/experiment/banco_mcp/mcp_kg/familias_nav_rel.py data/experiment/banco_mcp/mcp_kg/familias_nav_rel_amp.py \
  | tar -x -C "$SP/clon_head_exactitud_B64" || { print -r -- "no se pudo armar el clon"; exit 21; }
X="$SP/clon_head_exactitud_B64/data/experiment"; C="$X/banco_mcp/b63/analisis/codigo"
typeset -A SHA
SHA=("$C/analizar_b63.py" 9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb
     "$C/aplicar_lectura_tolerante_b63.py" 5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372
     "$C/exactitud_de_cita_9_4_b63.py" 5207941b4a54dd2e7071e5d1438fe0b664c0cfd2df56794614ab56de4e6f272a
     "$X/banco_mcp/mcp_kg/familias_nav_rel.py" 1b368333838b3d090b923e7d4b3db31751b7e06946ccc31038b4d41a30f125a7
     "$X/banco_mcp/mcp_kg/familias_nav_rel_amp.py" d5e9aff19bd7d26143b0a9b7a7074844d90bac6405a2dd1a30bd119ff46f9022
     "$R/data/experiment/banco_mcp/b64/v1/juez_b63.py" 4fa095019dfa5d085ca5eeff1acc40f05f50ee482de9e649d9d042d03012e53b
     "$R/data/experiment/banco_mcp/b64/v1/comun_b63.py" 631037e968174a5743869a27d0a5b4275cf5bb5cdaa2bc1dfc3a49890d6998cc
     "$UCITA" 3a58e5be33f2e7b1903c7c07ccfba00ef135f3b8da930f62490449577810e920
     "$ESPERADO" "$SHA_ESPERADO")
for f s in "${(@kv)SHA}"; do
  [[ "$(shasum -a 256 "$f" | cut -c1-64)" == "$s" ]] || { print -r -- "no da su sha256: ${f:t}"; exit 20; }
done
# 3. La corrida
cd "$SP" && B64_CODIGO_B63="$C" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$H6/codigo/exactitud_de_cita_9_4_b64.py" \
  --clon "$X/banco_mcp/b63/v2/b2" --entrada "$ENTRADA" --manifiesto-fuera "$MANIFIESTO" --banco-b64 "$BANCO" --e0 "$E0" \
  --armado-e0 "$ARMADO_E0" --ucita "$UCITA" --esperado "$ESPERADO" --salida "$SA/exactitud_de_cita" > "$SA/consola_exactitud_de_cita_B64.txt" 2>&1
print -r -- "$?" > "$SA/codigo_de_salida_exactitud_de_cita_B64.txt"
exit 0
