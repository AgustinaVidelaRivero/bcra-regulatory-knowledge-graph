#!/bin/zsh
# Arma el prototipo de S0-5a (código final + interruptor S0_5_REGLAS) y su raíz mínima. Uso: armar_proto.sh <scratchpad s05> <repo>
S="$1"; R="$2"
rm -rf "$S/codigo/proto"; mkdir -p "$S/codigo/proto"; cp "$S/codigo/final/"* "$S/codigo/proto/"
/usr/bin/python3 - "$S/codigo/proto/correr_e0.py" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
a = 'TOS_TANDA0_SIN_S0_5 = frozenset({"cap", "cla", "ext", "pro", "ric", "ctacte", "lingob", "polcre", "pagjub", "docvig"})\n'
b = a + """# Interruptores del prototipo de S0-5a (no van al repo): S0_5_REGLAS, lista separada por comas de las reglas de
# REGLAS_S0_5 que corren; NINGUNA, ninguna; sin la variable, o con TODAS, todas.
import os as _os_prototipo
_sel_prototipo = _os_prototipo.environ.get("S0_5_REGLAS")
if _sel_prototipo is not None and _sel_prototipo != "TODAS":
    REGLAS_S0_5 = REGLAS_S0_5 & frozenset(x for x in _sel_prototipo.split(",") if x)
"""
assert s.count(a) == 1
p.write_text(s.replace(a, b), encoding="utf-8")
PY
for f in e0_lib.py correr_e0.py selftest_e0.py; do cp "$S/codigo/proto/$f" "$S/raices/proto/data/experiment/reextraccion_v2/e0_chunking/$f"; done
shasum -a 256 "$S/codigo/final/"* "$S/codigo/proto/"* | awk '{print substr($1,1,16), $2}' | sed "s#$S/##"
