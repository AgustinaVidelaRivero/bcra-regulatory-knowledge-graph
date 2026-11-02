"""Listado de los ids que cambian en los 152 TOs con todas las reglas de S0, por TO, con la regla de cada evento
(USD 0). Lee la comparación (`comparar_e0.py`) y la atribución (`atribuir.py`).

Uso: python -B ids_que_cambian.py <comparacion.json> <atribucion.json> <salida.json>
"""
import json
import sys
from collections import Counter, OrderedDict

sys.dont_write_bytecode = True
cmp_, atr = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
out = OrderedDict()
tot = Counter()
for to, r in cmp_["por_to"].items():
    a = atr["por_to"].get(to, {})
    out[to] = OrderedDict([
        ("reglas", a.get("reglas")),
        ("chunks_antes_despues", r["chunks"]),
        ("ids_nuevos", r["ids_nuevos"]),
        ("ids_que_desaparecen", r["ids_que_desaparecen"]),
        ("orden_igual_en_comunes", r["orden_igual_en_comunes"]),
        ("chunks_que_cambian", sorted(r["cambian"])),
        ("solo_herencia", r["cambian_solo_en_la_herencia"]),
        ("renglones_ganados", len(r["renglones_ganados"])),
        ("renglones_que_salen_del_texto", len(r["renglones_perdidos"])),
        ("eventos_por_regla", a.get("eventos")),
        ("interaccion", a.get("interaccion"))])
    tot["ids_nuevos"] += len(r["ids_nuevos"])
    tot["ids_que_desaparecen"] += len(r["ids_que_desaparecen"])
    tot["chunks_que_cambian"] += len(r["cambian"])
res = OrderedDict([("tos_que_cambian", len(out)),
                   ("tos_con_ids_que_cambian", sum(1 for v in out.values() if v["ids_nuevos"] or v["ids_que_desaparecen"])),
                   ("totales", dict(tot)), ("tos_por_regla", atr.get("tos_por_regla")), ("por_to", out)])
open(sys.argv[3], "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({k: v for k, v in res.items() if k != "por_to"}, ensure_ascii=False))
