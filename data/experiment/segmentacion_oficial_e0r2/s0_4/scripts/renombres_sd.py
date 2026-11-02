"""Regla de sub-documento de S0-4: de los ids que aparecen y desaparecen entre una referencia y una corrida, cuántos
son la misma unidad con otro id (mismo texto propio, mismo sha256_propio: fila F05, más F02 por el rótulo heredado) y
cuántos son unidades nuevas o retiradas de verdad (F19b, con F01 si el texto cambia). Solo lectura.
Uso: python -B renombres_sd.py <ref> <corrida> <tos,coma> <salida.json>"""
import json, sys
from collections import Counter
from pathlib import Path
ref, cor, tos, sal = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3].split(","), Path(sys.argv[4])
out, tot = {}, Counter()
for to in tos:
    a = {c["id"]: c for c in json.loads((ref / f"chunks_{to}.json").read_text())}
    b = {c["id"]: c for c in json.loads((cor / f"chunks_{to}.json").read_text())}
    nuevos, idos = [i for i in b if i not in a], [i for i in a if i not in b]
    por_sha = {}
    for i in idos:
        por_sha.setdefault(a[i]["sha256_propio"], []).append(i)
    renombres, solo_nuevos = [], []
    for i in nuevos:
        lst = por_sha.get(b[i]["sha256_propio"])
        if lst:
            renombres.append([lst.pop(0), i])
        else:
            solo_nuevos.append(i)
    solo_idos = [i for l in por_sha.values() for i in l]
    her = sum(1 for x, y in renombres if a[x]["herencia"] != b[y]["herencia"])
    out[to] = {"renombradas_mismo_texto": len(renombres), "de_ellas_con_otra_herencia": her,
               "nuevas": len(solo_nuevos), "retiradas": len(solo_idos), "ejemplos_renombre": renombres[:5]}
    tot.update({k: v for k, v in out[to].items() if isinstance(v, int)})
sal.write_text(json.dumps({"total": dict(tot), "por_to": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"total": dict(tot), "por_to": {t: {k: v for k, v in r.items() if k != "ejemplos_renombre"} for t, r in out.items()}}, ensure_ascii=False))
