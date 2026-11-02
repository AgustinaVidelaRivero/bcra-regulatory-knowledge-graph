"""Arma el prototipo de S0-6a: el código final más el interruptor de las reglas (S0_6_REGLAS) y el de la medición de la
tanda 0 (S0_6_TANDA0), antes de `_r6`. No va al repo: es el que corre el censo por regla.
Uso: python -B armar_proto_S0-6a.py <correr_e0.py final> <correr_e0.py del prototipo>"""
import sys
from pathlib import Path

INTERRUPTOR = """
# Interruptor del prototipo de S0-6a (no va al repo): S0_6_REGLAS, lista separada por comas de las reglas de REGLAS_S0_6
# que corren; NINGUNA, ninguna; sin la variable, o con TODAS, todas.
import os as _os_prototipo
_sel_prototipo = _os_prototipo.environ.get("S0_6_REGLAS")
if _sel_prototipo is not None and _sel_prototipo != "TODAS":
    REGLAS_S0_6 = REGLAS_S0_6 & frozenset(x for x in _sel_prototipo.split(",") if x)
# Medición de la tanda 0 (no va al repo): S0_6_TANDA0=1 deja correr las reglas de S0-6a también en la tanda 0
if _os_prototipo.environ.get("S0_6_TANDA0") == "1":
    TOS_TANDA0_SIN_S0_6 = frozenset()
"""
ANCLA = "\n\ndef _r6(regla: str, to: str) -> bool:"
s = Path(sys.argv[1]).read_text(encoding="utf-8")
assert s.count(ANCLA) == 1
Path(sys.argv[2]).write_text(s.replace(ANCLA, INTERRUPTOR + ANCLA), encoding="utf-8")
