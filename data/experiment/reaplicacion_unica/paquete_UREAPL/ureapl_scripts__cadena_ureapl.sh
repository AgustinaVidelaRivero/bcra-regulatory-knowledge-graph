#!/bin/bash
# U-REAPL: data/experiment/tanda_final/t3/scripts/cadena_t3_tf.sh con un solo agregado: las banderas de la re-aplicación,
# después de los cinco argumentos, van al final del comando, antes de --salida. Sin banderas, el comando es el mismo.
# USD 0, sin API.
# Uso: cadena_ureapl.sh <python> <copia> <grafo> <salida> <consola> [banderas de la re-aplicación...]
#   <grafo>: tf98 | tf98_sincola | tf_tramo1 | tf_tramo1_sincola (la tanda y el tramo 1, con los manifiestos de T1)
#            acum128 | acum128_sincola (las tres tandas) | acum60 | acum60_sincola (las tandas 0 y 1 con el tramo 1)
#            tf_tramo1_raya | tf_tramo1_raya_sincola (solo para la prueba: el tramo 1 con la variante con la raya)
#   <salida>: el --salida del ensamblado; si es relativa, es relativa a la raíz de la copia.
set -u
PY="$1"; CP="$2"; G="$3"; OUT="$4"; CON="$5"; shift 5; EXTRA=("$@")
export PYTHONDONTWRITEBYTECODE=1; unset ANTHROPIC_API_KEY
cd "$CP" || exit 2
X=data/experiment/reextraccion_v2; M1=data/experiment/tanda_final/t1/ensamblado/manifiestos
A=data/experiment/tanda_final/t3/acumulado; P=data/experiment/tanda_final/t3/prueba_raya_tramo1/manifiestos
ENT=$X/corpus_tanda_final/salida_r2b; E0=$X/e0_chunking/salida_tanda_final_r2b
ENS=data/experiment/tanda0/code/ensamblar_tanda0.py
case "$G" in
  tf98)                   set -- --manifiesto $M1/tanda_final_ens_98_r2b.json --entrada $ENT --e0-r2 $E0 ;;
  tf98_sincola)           set -- --manifiesto $M1/tanda_final_ens_98_r2b_sincola.json --entrada $ENT --e0-r2 $E0 --sin-cola ;;
  tf_tramo1)              set -- --manifiesto $M1/tanda_final_ens_tramo1_r2b.json --entrada $ENT --e0-r2 $E0 ;;
  tf_tramo1_sincola)      set -- --manifiesto $M1/tanda_final_ens_tramo1_r2b_sincola.json --entrada $ENT --e0-r2 $E0 --sin-cola ;;
  tf_tramo1_raya)         set -- --manifiesto $P/tanda_final_ens_tramo1_r2b_raya.json --entrada $ENT --e0-r2 $E0 ;;
  tf_tramo1_raya_sincola) set -- --manifiesto $P/tanda_final_ens_tramo1_r2b_raya_sincola.json --entrada $ENT --e0-r2 $E0 --sin-cola ;;
  acum128)                set -- --manifiesto $A/manifiestos/tanda_final_acumulado_ens_128_r2b.json --entrada $A/entrada_acumulado_128_r2b --e0-r2 $A/e0_acumulado_128_r2b ;;
  acum128_sincola)        set -- --manifiesto $A/manifiestos/tanda_final_acumulado_ens_128_r2b_sincola.json --entrada $A/entrada_acumulado_128_r2b --e0-r2 $A/e0_acumulado_128_r2b --sin-cola ;;
  acum60)                 set -- --manifiesto $A/manifiestos/tanda_final_acumulado_ens_60_tramo1_r2b.json --entrada $A/entrada_acumulado_60_r2b --e0-r2 $A/e0_acumulado_60_r2b ;;
  acum60_sincola)         set -- --manifiesto $A/manifiestos/tanda_final_acumulado_ens_60_tramo1_r2b_sincola.json --entrada $A/entrada_acumulado_60_r2b --e0-r2 $A/e0_acumulado_60_r2b --sin-cola ;;
  *) echo "grafo desconocido: $G"; exit 2 ;;
esac
{
  echo "inicio $(date '+%Y-%m-%d %H:%M:%S') grafo=$G"
  /usr/bin/time -l "$PY" -B $ENS "$@" ${EXTRA[@]+"${EXTRA[@]}"} --salida "$OUT"
  echo "rc=$?"
  echo "fin $(date '+%Y-%m-%d %H:%M:%S')"
} > "$CON" 2>&1
