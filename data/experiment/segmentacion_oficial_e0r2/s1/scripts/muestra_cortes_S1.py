"""U-SEG-OFICIAL, S1, punto 7: sorteo sellado de la muestra de la lectura de cortes (USD 0). No lee ni marca.

Uso: python -B muestra_cortes_S1.py --e0 <salida de la corrida> --manifiesto <json> --controles <controles_S1.json>
       --out <muestra_cortes_S1.json>

Criterio, muestra y semilla de la tercera nota al pie del mandato (`2faff14`), con las precisiones de la nota de
`26c6502` y del despacho de S1:
- semilla `U-SEG-OFICIAL:cortes:2026-10-05`;
- primer grupo: las unidades de los TOs reconocidos plenos (clase de `particion_152.json`, en el manifiesto), por
  estrato = modo de lectura (`conteos_b584.json`, campo `modo_lectura`, en el manifiesto), con el rótulo literal del
  estrato (vigente, marcadores, sin_raiz); ids = todos los chunks de los TOs del estrato, ordenados con `sorted`;
  `random.Random(f"{semilla}:{estrato}").sample(ids, n)` con n = 40, 10 y 40; si el estrato tiene menos, todas;
- segundo grupo: todas las unidades por punto de ri2_pm (regla de `no_segmentables_limite/l2_regla_parciales.md`,
  calculada en `controles_S1.json`);
- tercer grupo: un juicio por cada no segmentable declarado, menos ri_spi; de ri_spi, 10 unidades con
  `random.Random(f"{semilla}:ri_spi").sample(ids, 10)` sobre sus ids ordenados.
Escribe, de cada unidad, id, TO, páginas, tipo y texto propio; de cada estrato del primer grupo, sus unidades (el
peso); y la lista de páginas a renderizar.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

SEMILLA = "U-SEG-OFICIAL:cortes:2026-10-05"
TAMANOS = {"vigente": 40, "marcadores": 10, "sin_raiz": 40}
TANDA0 = ("ctacte", "lingob", "polcre", "pagjub", "docvig")


def ficha(c: dict) -> dict:
    return {"id": c["id"], "to": c["to"], "paginas": c["paginas"], "tipo": c["tipo"],
            "rol_bloque": c.get("rol_bloque"), "texto_propio": c["texto"], "tanda0": c["to"] in TANDA0}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0", "manifiesto", "controles", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    man = json.loads(a.manifiesto.read_text(encoding="utf-8"))
    ctl = json.loads(a.controles.read_text(encoding="utf-8"))
    chunks = {t["id"]: json.loads((a.e0 / f"chunks_{t['id']}.json").read_text(encoding="utf-8")) for t in man["tos"]}
    por_id = {c["id"]: c for ch in chunks.values() for c in ch}

    plenos = [t for t in man["tos"] if t["clase"] == "reconocido_pleno"]
    total_primer = sum(len(chunks[t["id"]]) for t in plenos)
    grupo1, paginas = {}, {}
    for estrato in TAMANOS:
        tos = sorted(t["id"] for t in plenos if t["modo_lectura"] == estrato)
        ids = sorted(c["id"] for to in tos for c in chunks[to])
        n = TAMANOS[estrato]
        sel = random.Random(f"{SEMILLA}:{estrato}").sample(ids, n) if len(ids) >= n else list(ids)
        grupo1[estrato] = {"tos": len(tos), "lista_tos": tos, "unidades": len(ids),
                           "peso": len(ids) / total_primer, "n": n, "leidas": len(sel),
                           "semilla": f"{SEMILLA}:{estrato}",
                           "muestra": [ficha(por_id[i]) for i in sel]}
    ids_pm = ctl["ri2_pm"]["ids_por_punto"]
    grupo2 = {"to": "ri2_pm", "regla": "no_segmentables_limite/l2_regla_parciales.md", "unidades": len(ids_pm),
              "cruzan_fichas": ctl["ri2_pm"]["cruzan_fichas"],
              "muestra": [ficha(por_id[i]) for i in ids_pm]}
    nos = [t for t in man["tos"] if t["clase"] == "no_segmentable_declarado"]
    grupo3 = {}
    for t in nos:
        if t["id"] == "ri_spi":
            continue
        ch = chunks[t["id"]]
        grupo3[t["id"]] = {"paginas_del_pdf": t["paginas"], "via": t["via"],
                           "causa": t.get("causa") or t.get("causa_clase"),
                           "unidades_e0r2": [{"id": c["id"], "paginas": c["paginas"], "tipo": c["tipo"]} for c in ch],
                           "juicio": "que no tenga una numeración de puntos que la segmentación debió reconocer"}
    ids_spi = sorted(c["id"] for c in chunks["ri_spi"])
    sel_spi = random.Random(f"{SEMILLA}:ri_spi").sample(ids_spi, 10)
    spi = {"unidades": len(ids_spi), "semilla": f"{SEMILLA}:ri_spi", "n": 10,
           "muestra": [ficha(por_id[i]) for i in sel_spi]}

    def agregar(to, ps):
        paginas.setdefault(to, set()).update(ps)
    for g in grupo1.values():
        for u in g["muestra"]:
            agregar(u["to"], u["paginas"])
    for u in grupo2["muestra"] + spi["muestra"]:
        agregar(u["to"], u["paginas"])
    for to, g in grupo3.items():
        agregar(to, range(1, g["paginas_del_pdf"] + 1))
    res = {"semilla": SEMILLA, "criterio": "tercera nota al pie del mandato (2faff14); precisiones de 26c6502 y del "
                                           "despacho de S1",
           "orden_de_ids": "sorted de Python sobre el id del chunk",
           "primer_grupo": {"tos": len(plenos), "unidades": total_primer, "estratos": grupo1,
                            "leidas": sum(g["leidas"] for g in grupo1.values())},
           "segundo_grupo": grupo2, "tercer_grupo": grupo3, "ri_spi": spi,
           "paginas_a_renderizar": {to: sorted(ps) for to, ps in sorted(paginas.items())}}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"primer_grupo": {e: {k: g[k] for k in ("tos", "unidades", "peso", "leidas")}
                                       for e, g in grupo1.items()},
                      "total_primer": total_primer, "ri2_pm": len(ids_pm), "tercer_grupo": len(grupo3),
                      "ri_spi": {"unidades": len(ids_spi), "leidas": len(sel_spi)},
                      "tanda0_en_la_muestra": sum(u["tanda0"] for g in grupo1.values() for u in g["muestra"]),
                      "paginas_a_renderizar": sum(len(v) for v in paginas.values())}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
