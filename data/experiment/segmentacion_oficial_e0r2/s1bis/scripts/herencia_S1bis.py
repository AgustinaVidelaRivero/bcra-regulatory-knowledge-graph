"""U-SEG-OFICIAL, S1-bis.5: herencia por unidad y unidades con el recorte del punto (h) de C2 de U-R2-CODIGO-2 (USD 0).

Uso: python -B herencia_S1bis.py --copia <raíz de una copia> --e0 <salida de la corrida> --manifiesto <json>
       --s1 <s1/herencia_S1.json> --out <json>

Copia de `s1/scripts/herencia_S1.py` con un agregado: la cifra de S1 (`s1/herencia_S1.json`: 52 unidades en 8 TOs) como
segunda referencia, con la diferencia por TO y la lista de ids que entran y salen; en la diferencia con C2, la clave de
la cifra de esta corrida pasa de `s1` a `s1bis`. Lo demás, igual.

- Herencia de una unidad: la suma de los caracteres del texto de sus tramos de herencia (`herencia` del chunk), tal
  como sale de E0 (con el recorte aplicado).
- Recorte: el chunk trae `herencia_recortada` (lo declara `e0_lib.recortar_herencia`, con el tope
  `correr_e0.TOPE_HERENCIA_E0_R2`, que se lee del código de la copia). De cada una: TO, texto propio, herencia, la
  herencia antes del recorte (la de ahora, sin las líneas marcador, más lo omitido), el bloque recortado con más
  caracteres omitidos y el tramo heredado mayor que queda.
- Cifra de referencia: FRENO C2 de U-R2-CODIGO-2 (`r2_codigo2/freno_c2.md:69`; por TO en
  `r2_codigo2/salidas/c2_e0.json`, `particion_152.unidades_con_herencia_recortada`): 93 unidades en 9 TOs.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("copia", "e0", "manifiesto", "s1", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    ex = a.copia / "data/experiment"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ex / "reextraccion_v2/e0_chunking"))
    import correr_e0 as CE
    import e0_lib as E0
    U, B = CE.TOPE_HERENCIA_E0_R2
    prefijo_marca = E0.MARCA_RECORTE_HERENCIA.split("{n}")[0]
    man = json.loads(a.manifiesto.read_text(encoding="utf-8"))
    c2 = json.loads((ex / "r2_codigo2/salidas/c2_e0.json").read_text(encoding="utf-8"))
    c2r = c2["particion_152"]["unidades_con_herencia_recortada"]
    maximos, recortadas, sobre_u = {}, [], []
    for t in man["tos"]:
        to = t["id"]
        ch = json.loads((a.e0 / f"chunks_{to}.json").read_text(encoding="utf-8"))
        mx = None
        for c in ch:
            her = sum(len(tr["texto"]) for tr in c["herencia"])
            if mx is None or her > mx["herencia"]:
                mx = {"id": c["id"], "herencia": her, "chars_propio": c["chars_propio"]}
            if her > U:
                sobre_u.append({"id": c["id"], "herencia": her})
            if c.get("herencia_recortada"):
                marcas = [tr for tr in c["herencia"] if tr["texto"].startswith(prefijo_marca)]
                omit = sum(b["caracteres_omitidos"] for b in c["herencia_recortada"])
                mayor_rec = max(c["herencia_recortada"], key=lambda b: b["caracteres_omitidos"])
                tramos = [tr for tr in c["herencia"] if not tr["texto"].startswith(prefijo_marca)]
                mayor = max(tramos, key=lambda tr: len(tr["texto"])) if tramos else None
                recortadas.append({
                    "to": to, "id": c["id"], "tipo": c["tipo"], "es_parte": "::parte" in c["id"],
                    "chars_propio": c["chars_propio"], "herencia": her,
                    "herencia_antes_del_recorte": her - sum(len(m["texto"]) for m in marcas) + omit,
                    "bloque_recortado_mayor": mayor_rec,
                    "tramo_heredado_mayor": None if mayor is None else
                    {"tipo": mayor["tipo"], "unidad_origen": mayor["unidad_origen"], "caracteres": len(mayor["texto"])}})
        maximos[to] = mx
    por_to = Counter(r["to"] for r in recortadas)
    dif = {to: {"c2": c2r["por_to"].get(to, 0), "s1bis": por_to.get(to, 0)}
           for to in sorted(set(por_to) | set(c2r["por_to"])) if c2r["por_to"].get(to, 0) != por_to.get(to, 0)}
    glob = max(maximos.values(), key=lambda d: d["herencia"])
    s1 = json.loads(a.s1.read_text(encoding="utf-8"))
    ids_s1 = {r["id"] for r in s1["recortadas"]}
    ids_s1bis = {r["id"] for r in recortadas}
    dif_s1 = {to: {"s1": s1["por_to"].get(to, 0), "s1bis": por_to.get(to, 0)}
              for to in sorted(set(por_to) | set(s1["por_to"])) if s1["por_to"].get(to, 0) != por_to.get(to, 0)}
    res = {"tope_herencia_e0_r2": {"U": U, "B": B, "fuente": "correr_e0.TOPE_HERENCIA_E0_R2"},
           "herencia_maxima_global": glob,
           "herencia_maxima_por_to": maximos,
           "unidades_con_recorte": len(recortadas), "tos_con_recorte": len(por_to),
           "partes_con_recorte": sum(r["es_parte"] for r in recortadas),
           "por_to": dict(sorted(por_to.items())),
           "referencia_c2": {"unidades": c2r["total"], "tos": c2r["tos"], "por_to": c2r["por_to"],
                             "fuente": "r2_codigo2/freno_c2.md:69; r2_codigo2/salidas/c2_e0.json"},
           "diferencia_con_c2_por_to": dif,
           "referencia_s1": {"unidades": s1["unidades_con_recorte"], "tos": s1["tos_con_recorte"],
                             "por_to": s1["por_to"], "fuente": "s1/herencia_S1.json"},
           "diferencia_con_s1_por_to": dif_s1,
           "ids_solo_en_s1": sorted(ids_s1 - ids_s1bis), "ids_solo_en_s1bis": sorted(ids_s1bis - ids_s1),
           "unidades_con_herencia_sobre_U": sobre_u,
           "recortadas": recortadas}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("herencia_maxima_por_to", "recortadas")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
