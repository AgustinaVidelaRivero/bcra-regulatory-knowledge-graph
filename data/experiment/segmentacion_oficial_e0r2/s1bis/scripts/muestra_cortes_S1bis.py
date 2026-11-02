"""U-SEG-OFICIAL, S1-bis-b.1: sorteo sellado de la muestra de la lectura de cortes, a ciegas (USD 0). No lee ni marca.

Uso: python -B muestra_cortes_S1bis.py --e0 <s1bis/e0> --manifiesto <json> --poblacion <poblacion_muestra_S1bis.json>
       --censo <censo_renglones_S1bis.json> --comparacion <comparacion_censos_S1bis.json> --out <muestra_cortes_S1bis.json>

Sigue `acta_sorteo_S1bis.md` (sellada antes del sorteo):
- primer grupo: por estrato (vigente, marcadores, sin_raiz), los ids de la población recalculados desde `e0/` y el
  manifiesto como en `poblacion_muestra_S1bis.py`, controlados contra la lista y el sha256 de `poblacion_muestra_S1bis.json`;
  `random.Random(f"U-SEG-OFICIAL:cortes:S1-bis:{estrato}").sample(ids, n)`, n = 40, 10 y 40;
- segundo grupo: vacío (ri2_pm sale de esta lectura);
- tercer grupo: los 11 juicios (no segmentables salvo ri_spi), 9 para leer, y ri_pspii y ri_tii con su resultado decidido;
- ri_spi: `random.Random("U-SEG-OFICIAL:cortes:S1-bis:ri_spi").sample(sorted(ids), 10)`;
- censo del hallazgo 1.16 de la tanda 1: los 35 candidatos, todos.
A ciegas: de cada unidad escribe id, TO, grupo, páginas, tipo, rol, herencia y texto propio; ninguna marca de límite
declarado, de TO de la tanda 0 ni de candidato del 1.16 en la muestra. Escribe también las páginas a renderizar.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

SEMILLA = "U-SEG-OFICIAL:cortes:S1-bis"
TAMANOS = {"vigente": 40, "marcadores": 10, "sin_raiz": 40}
JUICIOS_DECIDIDOS = {
    "ri_pspii": {"resultado": "correcta",
                 "decision": "juicio correcto: e0-r2 reconoce sus dos apartados numerados; la clase no segmentable "
                             "descansa en lo corto del documento (acta_sorteo_S1bis.md, §1, decisión 2)"},
    "ri_tii": {"resultado": "limite_declarado",
               "decision": "límite declarado: los apartados en romanos (I a VI) no son numeración de puntos y el "
                           "documento sigue por página; candidato a una regla por lista en la release de E0 antes de la "
                           "tanda en la que caiga (acta_sorteo_S1bis.md, §1, decisión 2)"},
}


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def ficha(c: dict, grupo: str) -> dict:
    return {"id": c["id"], "to": c["to"], "grupo": grupo, "paginas": c["paginas"], "tipo": c["tipo"],
            "rol_bloque": c.get("rol_bloque"), "chars_propio": c["chars_propio"],
            "herencia": [{"tipo": t["tipo"], "texto": t["texto"]} for t in c["herencia"]],
            "texto_propio": c["texto"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0", "manifiesto", "poblacion", "censo", "comparacion", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    man = jl(a.manifiesto)
    pob = jl(a.poblacion)
    chunks = {t["id"]: jl(a.e0 / f"chunks_{t['id']}.json") for t in man["tos"]}
    por_id = {c["id"]: c for ch in chunks.values() for c in ch}
    plenos = [t for t in man["tos"] if t["clase"] == "reconocido_pleno"]

    grupo1, paginas = {}, {}
    for e, n in TAMANOS.items():
        ids = sorted(c["id"] for t in plenos if t["modo_lectura"] == e for c in chunks[t["id"]])
        sellado = pob["primer_grupo"]["estratos"][e]
        assert ids == sellado["ids"] and sha_ids(ids) == sellado["sha256_ids_ordenados"], f"población de {e} distinta"
        sel = random.Random(f"{SEMILLA}:{e}").sample(ids, n)
        grupo1[e] = {"unidades": len(ids), "peso": sellado["peso"], "n": n, "leidas": len(sel),
                     "semilla": f"{SEMILLA}:{e}", "sha256_ids_ordenados": sellado["sha256_ids_ordenados"],
                     "muestra": [ficha(por_id[i], f"G1-{e}") for i in sel]}
    spi_ids = sorted(c["id"] for c in chunks["ri_spi"])
    assert spi_ids == pob["ri_spi"]["ids"], "ri_spi distinto de la población"
    sel_spi = random.Random(f"{SEMILLA}:ri_spi").sample(spi_ids, 10)
    spi = {"unidades": len(spi_ids), "semilla": f"{SEMILLA}:ri_spi", "n": 10, "fuera_del_piso": True,
           "muestra": [ficha(por_id[i], "ri_spi") for i in sel_spi]}
    juicios = {}
    for t in man["tos"]:
        if t["clase"] != "no_segmentable_declarado" or t["id"] == "ri_spi":
            continue
        j = {"paginas_del_pdf": t["paginas"], "via": t["via"], "causa": t.get("causa") or t.get("causa_clase"),
             "unidades_e0r2": [{"id": c["id"], "paginas": c["paginas"], "tipo": c["tipo"],
                                "chars_propio": c["chars_propio"]} for c in chunks[t["id"]]],
             "juicio": "que no tenga una numeración de puntos que la segmentación debió reconocer"}
        if t["id"] in JUICIOS_DECIDIDOS:
            j["decidido"] = JUICIOS_DECIDIDOS[t["id"]]
        juicios[t["id"]] = j
    assert len(juicios) == 11 and set(JUICIOS_DECIDIDOS) <= set(juicios)
    cen = {c["id"]: c for c in jl(a.censo)["hallazgo_1_16"]["lista"]}
    ids116 = jl(a.comparacion)["hallazgo_1_16"]["tanda1"]["ids_s1bis"]
    assert len(ids116) == 35
    c116 = []
    for i in ids116:
        f = ficha(por_id[i], "C116-tanda1")
        f.update({k: cen[i][k] for k in ("padre", "items_de_la_lista", "cierre_candidato", "renglones_despues_del_corte")})
        c116.append(f)

    def agregar(to, ps):
        paginas.setdefault(to, set()).update(ps)
    for g in grupo1.values():
        for u in g["muestra"]:
            agregar(u["to"], u["paginas"])
    for u in spi["muestra"] + c116:
        agregar(u["to"], u["paginas"])
    for to, j in juicios.items():
        if "decidido" not in j:
            agregar(to, range(1, j["paginas_del_pdf"] + 1))
    res = {"acta": "acta_sorteo_S1bis.md (sellada antes del sorteo; sha256 y hora en sellos_S1bis_b.txt)",
           "semilla": SEMILLA, "orden_de_ids": "sorted de Python sobre el id del chunk",
           "a_ciegas": "sin marcas de límite declarado, de TO de la tanda 0 ni de candidato del 1.16 en la muestra",
           "primer_grupo": {"tos": len(plenos), "unidades": pob["primer_grupo"]["unidades"], "estratos": grupo1,
                            "leidas": sum(g["leidas"] for g in grupo1.values())},
           "segundo_grupo": {"to": "ri2_pm", "leidas": 0,
                             "motivo": "sale entero de esta lectura (acta_sorteo_S1bis.md, §1, decisión 3)"},
           "tercer_grupo": {"juicios": len(juicios), "para_leer": sum(1 for j in juicios.values() if "decidido" not in j),
                            "por_to": juicios},
           "ri_spi": spi,
           "censo_1_16_tanda1": {"candidatos": len(c116), "tos": len({u["to"] for u in c116}),
                                 "paginas": len({(u["to"], p) for u in c116 for p in u["paginas"]}),
                                 "caracteres_propios": sum(u["chars_propio"] for u in c116), "lista": c116},
           "paginas_a_renderizar": {to: sorted(ps) for to, ps in sorted(paginas.items())}}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"primer_grupo": {e: {k: g[k] for k in ("unidades", "n", "leidas")} for e, g in grupo1.items()},
                      "ri_spi": {"unidades": spi["unidades"], "leidas": len(sel_spi)},
                      "juicios": len(juicios), "juicios_para_leer": res["tercer_grupo"]["para_leer"],
                      "censo_1_16": {k: v for k, v in res["censo_1_16_tanda1"].items() if k != "lista"},
                      "paginas_a_renderizar": sum(len(v) for v in paginas.values())}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
