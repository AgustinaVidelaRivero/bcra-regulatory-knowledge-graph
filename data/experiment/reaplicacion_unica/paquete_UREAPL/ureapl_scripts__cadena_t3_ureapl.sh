#!/bin/bash
# U-REAPL: data/experiment/tanda1/t3/scripts/cadena_t3.sh con un solo agregado: las banderas de la re-aplicación, después de
# los cinco argumentos, van al final del comando, antes de --salida (para explicar la diferencia de las remisiones).
# B6.1, tanda 1, T3, punto 3: una cadena de ensamblado sobre una copia del repo (nunca sobre el repo), con el método del re-sellado
# (data/experiment/resellado_t0/scripts/cadena_rs1.sh). USD 0, sin API.
# Uso: cadena_t3.sh <python> <copia> <grafo> <salida> <consola>
#   <grafo>: t1_veinte | t1_veinte_sincola (la tanda 1, manifiestos del 94) | acum_treinta | acum_treinta_sincola (el acumulado de
#            las tandas 0 y 1, manifiestos derivados en t3/acumulado/manifiestos/)
#   <salida>: el --salida del ensamblado; si es relativa, es relativa a la raíz de la copia.
set -u
PY="$1"; CP="$2"; G="$3"; OUT="$4"; CON="$5"; shift 5; EXTRA=("$@")
export PYTHONDONTWRITEBYTECODE=1; unset ANTHROPIC_API_KEY
cd "$CP" || exit 2
X=data/experiment/reextraccion_v2; MAN=$X/manifiestos; A=data/experiment/tanda1/t3/acumulado
ENS=data/experiment/tanda0/code/ensamblar_tanda0.py
case "$G" in
  t1_veinte)            set -- --manifiesto $MAN/tanda1_ens_veinte_r2b.json --entrada $X/corpus_tanda1/salida_r2b --e0-r2 $X/e0_chunking/salida_tanda1_r2b ;;
  t1_veinte_sincola)    set -- --manifiesto $MAN/tanda1_ens_veinte_r2b_sincola.json --entrada $X/corpus_tanda1/salida_r2b --e0-r2 $X/e0_chunking/salida_tanda1_r2b --sin-cola ;;
  acum_treinta)         set -- --manifiesto $A/manifiestos/acumulado_ens_treinta_r2b.json --entrada $A/entrada_acumulado_r2b --e0-r2 $A/e0_acumulado_r2b ;;
  acum_treinta_sincola) set -- --manifiesto $A/manifiestos/acumulado_ens_treinta_r2b_sincola.json --entrada $A/entrada_acumulado_r2b --e0-r2 $A/e0_acumulado_r2b --sin-cola ;;
  *) echo "grafo desconocido: $G"; exit 2 ;;
esac
{
  echo "inicio $(date '+%Y-%m-%d %H:%M:%S') grafo=$G"
  /usr/bin/time -l "$PY" -B $ENS "$@" ${EXTRA[@]+"${EXTRA[@]}"} --salida "$OUT"
  echo "rc=$?"
  echo "fin $(date '+%Y-%m-%d %H:%M:%S')"
} > "$CON" 2>&1
