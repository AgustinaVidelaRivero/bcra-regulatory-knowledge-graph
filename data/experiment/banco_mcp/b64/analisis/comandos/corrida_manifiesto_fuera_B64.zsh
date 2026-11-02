#!/bin/zsh
# El manifiesto de lo que queda fuera del repo en B6.4 (la corrección del H-6): el runner de H-4 commiteado, b64/v1/correr_b63.py con
# --manifiesto-fuera (b64/v1/correr_b63.py:722-729), desde la raíz del repo y con el Python de su .venv (como comando_b64.zsh: env -i, con
# PATH y HOME). Corre después de la corrida y antes del análisis: lo leen corrida_analisis_B64.zsh y corrida_exactitud_de_cita_B64.zsh.
# Escribe $F/banco_b64/manifiesto_fuera_B64.json: por archivo de banco_b64/resultados/real/ y de banco_b64/juez/, su ruta («banco_b64/…»),
# su tamaño y su sha256, sin texto (una carpeta *_SOLO_MESA* o NO_ABRIR_*, solo por su nombre). Al lado, su consola y su código de salida.
# Frena sin escribir si el manifiesto (o su consola) ya existe, o si falta alguna de las dos carpetas. Controla antes la lista y el sello
# de la corrección del H-6, el sha256 del runner (los de la lista de H-4) y el de la entrada. Lo que todavía no existe va como PENDIENTE,
# y el comando no corre hasta que se llene. Imprime la consola del runner y el sha256 del manifiesto.
# Uso: zsh corrida_manifiesto_fuera_B64.zsh
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"
H6="$F/analisis_b64_corr"; PY="$R/.venv/bin/python"; V="data/experiment/banco_mcp/b64/v1"
ENTRADA="data/experiment/banco_mcp/b64/entrada_B64.json"     # H-3: la entrada de B6.4, relativa a la raíz del repo
SHA_ENTRADA="PENDIENTE"        # H-3: su sha256
OUT="$F/banco_b64/resultados/real"; JUEZ="$F/banco_b64/juez"
MANIFIESTO="$F/banco_b64/manifiesto_fuera_B64.json"; CONSOLA="$F/banco_b64/consola_manifiesto_fuera_B64.txt"
CODIGO="$F/banco_b64/codigo_de_salida_manifiesto_fuera_B64.txt"
for v in SHA_ENTRADA; do [[ "${(P)v}" == PENDIENTE ]] && { print -r -- "falta llenar $v"; exit 22; }; done
# 1. Si ya existe, no se pisa; las dos carpetas de la corrida
for f in "$MANIFIESTO" "$CONSOLA" "$CODIGO"; do [[ -e "$f" ]] && { print -r -- "ya existe: ${f:t}"; exit 23; }; done
[[ -d "$OUT" && -d "$JUEZ" ]] || { print -r -- "falta banco_b64/resultados/real o banco_b64/juez"; exit 23; }
# 2. La lista y el sello de la corrección del H-6
grep -qF "sha256: $(shasum -a 256 "$H6/lista_H6_corr.txt" | cut -c1-64)" "$H6/sello_H6_corr.txt" || { print -r -- "la lista no es la del sello de la corrección del H-6"; exit 20; }
# 3. El runner de H-4 en el repo (los sha256 de runner_b64/lista_H34.txt), su Python y la entrada
typeset -A SHA
SHA=("$R/$V/correr_b63.py" 7cb219bced53abbd4c681147524410f12173b3a574b572b52278f5f7946554eb
     "$R/$V/comun_b63.py" 631037e968174a5743869a27d0a5b4275cf5bb5cdaa2bc1dfc3a49890d6998cc
     "$R/$V/juez_b63.py" 4fa095019dfa5d085ca5eeff1acc40f05f50ee482de9e649d9d042d03012e53b
     "$R/$V/lanzar_agente_b63.py" e1445d21393c1282be0be061fa00e4e772a98b6423bbf115215db66482edc217
     "$R/$ENTRADA" "$SHA_ENTRADA")
for f s in "${(@kv)SHA}"; do
  [[ "$(shasum -a 256 "$f" | cut -c1-64)" == "$s" ]] || { print -r -- "no da su sha256: ${f:t}"; exit 20; }
done
[[ -x "$PY" ]] || { print -r -- "no está el Python del .venv del repo"; exit 21; }
# 4. El manifiesto
cd "$R" && env -i PATH=/usr/bin:/bin HOME="$HOME" PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$V/correr_b63.py" --entrada "$ENTRADA" \
  --sha256-entrada "$SHA_ENTRADA" --modo real --out "$OUT" --juez-dir "$JUEZ" --manifiesto-fuera "$MANIFIESTO" > "$CONSOLA" 2>&1
rc=$?
print -r -- "$rc" > "$CODIGO"
print -r -- "$(<"$CONSOLA")"
[[ "$rc" == 0 && -f "$MANIFIESTO" ]] || { print -r -- "el runner no escribió el manifiesto (sale con $rc)"; exit 24; }
print -r -- "manifiesto_fuera_B64.json: $(shasum -a 256 "$MANIFIESTO" | cut -c1-64)"
exit 0
