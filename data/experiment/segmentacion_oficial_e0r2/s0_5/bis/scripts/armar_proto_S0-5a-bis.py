"""Arma el prototipo de S0-5a-bis: el código final más el interruptor de las reglas (S0_5_REGLAS) y el de la medición de
la tanda 0 (S0_5_TANDA0), antes de `_r5`. No va al repo: es el que corre el censo por regla.
Uso: python -B armar_proto_S0-5a-bis.py <correr_e0.py final> <correr_e0.py del prototipo>"""
import sys
from pathlib import Path

INTERRUPTOR = """
# Interruptor del prototipo de S0-5a-bis (no va al repo): S0_5_REGLAS, lista separada por comas de las reglas de
# REGLAS_S0_5 que corren; NINGUNA, ninguna; sin la variable, o con TODAS, todas.
import os as _os_prototipo
_sel_prototipo = _os_prototipo.environ.get("S0_5_REGLAS")
if _sel_prototipo is not None and _sel_prototipo != "TODAS":
    REGLAS_S0_5 = REGLAS_S0_5 & frozenset(x for x in _sel_prototipo.split(",") if x)
# Medición de la tanda 0 (no va al repo): S0_5_TANDA0=1 deja correr las reglas también en la tanda 0
if _os_prototipo.environ.get("S0_5_TANDA0") == "1":
    TOS_TANDA0_SIN_S0_5 = frozenset()
"""
ANCLA = "\n\ndef _r5(regla: str, to: str, lista: frozenset | None = None) -> bool:"
s = Path(sys.argv[1]).read_text(encoding="utf-8")
assert s.count(ANCLA) == 1
Path(sys.argv[2]).write_text(s.replace(ANCLA, INTERRUPTOR + ANCLA), encoding="utf-8")
