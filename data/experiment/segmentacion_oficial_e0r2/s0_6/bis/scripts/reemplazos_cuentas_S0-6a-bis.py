"""Las reglas por lista que reemplazan las generales, en cuentas (U-SEG-OFICIAL, S0-6a-bis; USD 0, solo lectura): resume la
salida de `s0_6/scripts/reemplazos_S0-6a.py` por lista reemplazada, regla general y documento, sin ítems ni ids (el
detalle por unidad va en el archivo NO_ABRIR_ del paquete). Con C ajustada, R5-a sigue por lista en las listas de
LISTAS_R5A_S0_6: esas se cuentan aparte (`listas_r5a_S0-6a-bis.py`).

Uso: python -B reemplazos_cuentas_S0-6a-bis.py --reemplazos <json> --out <json>
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--reemplazos", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
r = json.loads(a.reemplazos.read_text(encoding="utf-8"))
grupos = defaultdict(lambda: {"listas": 0, "unidades": 0, "iguales_con_la_regla_sola": 0, "iguales_en_la_corregida": 0})
for x in r["por_lista"]:
    g = grupos[(x["lista"], x["regla_general"], x["to"])]
    g["listas"] += 1
    for k in ("unidades", "iguales_con_la_regla_sola", "iguales_en_la_corregida"):
        g[k] += x[k]
out = {"por_lista_regla_y_documento": [{"lista": l, "regla_general": rg, "to": to, **v}
                                       for (l, rg, to), v in sorted(grupos.items())]}
tot = defaultdict(lambda: defaultdict(int))
for (l, rg, _), v in grupos.items():
    for k, n in v.items():
        tot[f"{l}→{rg}"][k] += n
out["totales"] = {k: dict(v) for k, v in sorted(tot.items())}
a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out["totales"], ensure_ascii=False))
