"""Las unidades que no son de las 40 filas ni de las 286 leídas y me parecen un error de una regla, en cuentas
(U-SEG-OFICIAL, S0-6a-bis; USD 0, solo lectura). La lista (id, regla y motivo) está en un archivo NO_ABRIR_ del paquete;
este script controla que cada id exista en la E0 dada y no sea de las 286 leídas ni de las filas, y cuenta por regla y
por documento, sin ids.

Uso: python -B errores_de_regla_cuentas_S0-6a-bis.py --lista <NO_ABRIR_….json> --e0 <E0> --leidas <json: lista de
       los ids de las 286, o {"unidades": …}> --tsv <TSV de las 40 filas> --out <json>
"""
import argparse
import collections
import csv
import json
from pathlib import Path

ap = argparse.ArgumentParser()
for k in ("lista", "e0", "leidas", "tsv", "out"):
    ap.add_argument(f"--{k}", type=Path, required=True)
a = ap.parse_args()
lista = json.loads(a.lista.read_text(encoding="utf-8"))["unidades"]
le = json.loads(a.leidas.read_text(encoding="utf-8"))
le = le["unidades"] if isinstance(le, dict) else le
leidas = {f if isinstance(f, str) else f["id"] for f in le}
filas = {f["id_unidad_e0"] for f in csv.DictReader(a.tsv.open(encoding="utf-8"), delimiter="\t")}
ids = {}
for p in a.e0.glob("chunks_*.json"):
    for c in json.loads(p.read_text(encoding="utf-8")):
        ids[c["id"]] = p.name
faltan = [x["id"] for x in lista if x["id"] not in ids]
de_diseno = [x["id"] for x in lista if x["id"] in leidas or x["id"] in filas]
por = collections.defaultdict(collections.Counter)
for x in lista:
    por[x["regla"]][x["id"].split("::")[0]] += 1
res = {"unidades": len(lista), "existen_en_la_E0": len(lista) - len(faltan), "de_diseno": len(de_diseno),
       "por_regla_y_documento": {r: dict(sorted(v.items())) for r, v in sorted(por.items())},
       "por_regla": {r: sum(v.values()) for r, v in sorted(por.items())}}
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
if faltan or de_diseno:
    raise SystemExit(f"FRENO: {len(faltan)} ids no existen en la E0 y {len(de_diseno)} son de diseño")
