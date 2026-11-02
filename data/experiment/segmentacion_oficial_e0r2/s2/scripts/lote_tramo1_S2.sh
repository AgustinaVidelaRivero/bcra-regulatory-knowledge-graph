#!/bin/zsh
# Tramo 1 de S2 de U-SEG-OFICIAL, de punta a punta, sobre una copia (USD 0, sin API).
# Uso: zsh lote_tramo1_S2.sh <repo> <trabajo>
#   <repo>: la raíz del repo (solo se lee); <trabajo>: una carpeta nueva fuera del repo.
# Pasos: copia sin .env (la cláusula de los despachos, más NO_ABRIR_*), control por nombre, raíz mínima con el
# código de E0 de la copia, los 152 con correr_152.py, el control contra el manifiesto de S0-6b y la lista.
set -e
R="$1"; T="$2"
S2="data/experiment/segmentacion_oficial_e0r2/s2/scripts"
mkdir -p "$T"
rsync -a --no-links --exclude=/.git --exclude=/.venv --exclude=/.venv-app --exclude=.DS_Store --exclude=__pycache__ \
  --exclude='.env' --exclude='.env.*' --exclude='*.env' --exclude='NO_ABRIR_*' "$R/" "$T/copia/" > "$T/rsync.log" 2>&1
n=$(find "$T/copia" \( -name '.env' -o -name '.env.*' -o -name '*.env' \) | wc -l | tr -d ' ')
[ "$n" = "0" ] || { print -r -- "FRENO: $n .env en la copia"; exit 1; }
zsh "$T/copia/data/experiment/segmentacion_oficial_e0r2/s0_4/scripts/raiz_minima.sh" "$T/copia" "$T/raiz" \
  "$T/copia/data/experiment/reextraccion_v2/e0_chunking"
PY="$R/.venv/bin/python"
export PYTHONDONTWRITEBYTECODE=1
"$PY" -B "$T/copia/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts/correr_152.py" --codigo "$T/raiz" \
  --salida "$T/e0_152" --workers 8
"$PY" -B "$T/copia/$S2/control_e0_contra_manifiesto_S2.py" --e0 "$T/e0_152" \
  --manifiesto "$T/copia/data/experiment/segmentacion_oficial_e0r2/s0_6/b/manifiestos/manifest_salida_e0_152_S0-6b.json" \
  --out "$T/control_e0_S2a.json"
"$PY" -B "$T/copia/$S2/lista_tanda1_S2.py" --e0 "$T/e0_152" --raiz "$T/copia" --out "$T/lista_tanda1_S2.json"
