#!/bin/zsh
# Controles duros de S0-4a-ter sobre las corridas de lote_ter.sh (USD 0, solo lectura). Uso: controles_ter.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
T0=copia/data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b
M=copia/data/experiment/segmentacion_oficial_e0r2/s1/manifest_salida.json
O=ter/censos/controles_S0-4a-ter.txt; O0=ter/censos/tanda0_S0-4a-ter.txt
c() { PYTHONDONTWRITEBYTECODE=1 "$PY" -B s0_4/scripts/cmp_dirs.py "$@"; }
{
echo "Tanda 0 de S0-4a-ter: cada corrida (correr_tanda0_par.py de S0-4a, los diez TOs del manifiesto tanda0_10tos.json) contra salida_tanda0_r2b/ del repo (en la copia), byte a byte. Código: impl4ter (sin interruptores) o proto4ter (S0_4_REGLAS)."
for x in t0_ter_final:TODAS t0_ter_off:ninguna t0_ter_bis:las_de_S0-4a-bis t0_ter_sdr1:S0-4a-bis+sdr1 t0_ter_apl:S0-4a-bis+apl t0_ter_sdl:S0-4a-bis+sdl t0_ter_sdlh:S0-4a-bis+sdlh t0_ter_sdla:S0-4a-bis+sdla t0_ter_nuevas:solo_las_cinco_nuevas t0_ter_final2:TODAS_segunda; do
  echo "${x%%:*} [${x##*:}]: $(c ter/corridas/${x%%:*} $T0 | head -1)"; done
echo "t0_ter_final2 contra t0_ter_final: $(c ter/corridas/t0_ter_final2 ter/corridas/t0_ter_final | head -1)"
} > "$O0"
{
echo "Controles de configuración de S0-4a-ter sobre los 152 (cmp_dirs.py, byte a byte, los 768 archivos del primer nivel; cada corrida se armó con juntar_por_to.py desde la corrida sin manual y la de manual)"
echo "reglas nuevas prendidas, final (impl4ter) contra S0-4a-bis final (bis/corridas/bis_final): $(c ter/corridas/ter_final bis/corridas/bis_final | tr '\n' ' ')"
echo "reglas nuevas apagadas (proto4ter, las de S0-4a-bis) contra S0-4a-bis final: $(c ter/corridas/ter_bis bis/corridas/bis_final | head -1)"
echo "todo apagado (proto4ter, S0_4_REGLAS=\"\") contra S1 (corridas/base): $(c ter/corridas/ter_off corridas/base | head -1)"
echo "todo apagado contra los sha256 de los 768 archivos e0/ de s1/manifest_salida.json (ee7c07c): $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B bis/scripts/contra_manifiesto_s1.py ter/corridas/ter_off $M)"
echo "doble corrida: ter_final2 contra ter_final (impl4ter): $(c ter/corridas/ter_final2 ter/corridas/ter_final | head -1)"
echo "prototipo (proto4ter, TODAS) contra el código sin interruptores (ter_final), en los 64 TOs que cambian contra S1: $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B bis/scripts/por_to_iguales.py ter/corridas/ter_proto ter/corridas/ter_final "$(cat ter/tos_cambian_ter.txt)")"
echo "tanda 0 dentro de los 152 (ter_final): $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B s0_4/scripts/control_tanda0_en_152.py ter/corridas/ter_final $T0)"
echo "tanda 0 dentro de los 152 (ter_final2): $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B s0_4/scripts/control_tanda0_en_152.py ter/corridas/ter_final2 $T0)"
echo "corridas de prueba de los seis TOs (p_todas, prototipo) contra la final: $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B bis/scripts/por_to_iguales.py ter/corridas/p_todas ter/corridas/ter_final ri_oc,ri_ccna,ri_sef,nmcief,ri_icpipsp,ri_cc)"
} > "$O"
cat "$O0" "$O"
