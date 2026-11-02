"""Vuelca los negativos de las leídas (salida de `s0_6/scripts/negativos_leidas_S0-6a.py`) en NEGATIVOS_LEIDAS_S06 de
`selftest_e0.py` (U-SEG-OFICIAL, S0-6a-bis; corre sobre una copia del código, nunca sobre el repo).

Uso: python -B negativos_al_selftest_S0-6a-bis.py --negativos <json> --selftest <selftest_e0.py> --tos <to,to,…>

Reemplaza el cuerpo del diccionario (de `NEGATIVOS_LEIDAS_S06: dict[str, tuple[str, str, str]] = {` a su `}`) y controla
que los TOs de la corrida sean los de TOS_S06.
"""
import argparse
import ast
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--negativos", type=Path, required=True)
ap.add_argument("--selftest", type=Path, required=True)
ap.add_argument("--tos", required=True)
a = ap.parse_args()
neg = json.loads(a.negativos.read_text(encoding="utf-8"))
s = a.selftest.read_text(encoding="utf-8")
ini = "NEGATIVOS_LEIDAS_S06: dict[str, tuple[str, str, str]] = {\n"
i = s.index(ini) + len(ini)
j = s.index("\n}\n", i)
tos_st = next(ast.literal_eval(n.value) for n in ast.parse(s).body
              if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "TOS_S06" for t in n.targets))
assert set(tos_st) == set(a.tos.split(",")) == set(neg["tos"]), "los TOs no son los de TOS_S06"
cuerpo = "\n".join(f'    "{uid}": ("{", ".join(v["origen"])}", "{v["fija"]}", "{v["sha16_S0-5b"]}"),'
                   for uid, v in sorted(neg["unidades"].items()))
a.selftest.write_text(s[:i] + cuerpo + s[j:], encoding="utf-8")
print(f"{len(neg['unidades'])} negativos ({neg['solo_corte']} solo de corte) en {len(tos_st)} TOs")
