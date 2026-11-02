"""U-SEG-OFICIAL, S1-ter.4: el censo de renglones de S1-ter contra el de S1-bis, y el 1.16 con el criterio original
(USD 0, sin API).

Uso: python -B comparar_censos_S1ter.py --censo <censo_renglones_S1ter.json> --explicacion <explicacion_censo_S1ter.json>
       --s1bis-censo <s1bis/censo_renglones_S1bis.json> --s1bis-explicacion <s1bis/explicacion_censo_S1bis.json>
       --e0 <salida de S1-ter> --out <json>

Copia de `s1bis/scripts/comparar_censos_S1bis.py` con la referencia corrida un paso (S1-bis en lugar de S1) y las claves
de la salida en consecuencia; la lógica, igual. No cambia ninguna cifra: las pone al lado. Un renglón se identifica por
(TO, página, texto); un candidato del hallazgo 1.16, por su id. El 1.16 que se compara acá es el del criterio ORIGINAL
(la clave `hallazgo_1_16` de los dos censos); el de S1-ter es el del detector corregido, en `censos/`. La lista de la
tanda 1 es la de `s1bis/regla_censo_renglones_S1bis.md` (los 20 del ejemplo del §7 del protocolo entre tandas, con
ri_pgn en lugar de ri_cc).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

TANDA1 = ("ayccef", "expaef", "opefci", "adrei", "ri_ccna", "ri_pgn", "ri_rml", "ri_gerc", "snp_cheq", "ceninf",
          "cirmo3", "snp_tr", "lingeef", "depaho", "cajasc", "manori", "efemin", "nmcief", "ri_dcpc", "ri_oc")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def renglones(cen: dict) -> Counter:
    return Counter((to, d["pagina"], d["texto"]) for to, v in cen["por_to"].items() for d in v["lista"])


def sin_explicacion(exp: dict) -> Counter:
    return Counter((to, f["pagina"], f["texto"]) for to, fs in exp["por_to"].items() for f in fs
                   if f["explicacion_posterior"] == "sin_explicacion")


def lista(c: Counter) -> list:
    return [{"to": k[0], "pagina": k[1], "texto": k[2], "veces": n} for k, n in sorted(c.items())]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("censo", "explicacion", "s1bis_censo", "s1bis_explicacion", "e0", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    c2, e2, c1, e1 = jl(a.censo), jl(a.explicacion), jl(a.s1bis_censo), jl(a.s1bis_explicacion)
    r1, r2 = renglones(c1), renglones(c2)
    s1, s2 = sin_explicacion(e1), sin_explicacion(e2)
    h1 = {c["id"]: c for c in c1["hallazgo_1_16"]["lista"]}
    h2 = {c["id"]: c for c in c2["hallazgo_1_16"]["lista"]}
    t1 = {i for i in h1 if i.split("::")[0] in TANDA1}
    t2 = {i for i in h2 if i.split("::")[0] in TANDA1}
    chars = {c["id"]: c["chars_propio"] for to in {i.split("::")[0] for i in t2}
             for c in jl(a.e0 / f"chunks_{to}.json")}
    mismo = sorted(i for i in set(h1) & set(h2)
                   if (h1[i]["cierre_candidato"], h1[i]["paginas"]) == (h2[i]["cierre_candidato"], h2[i]["paginas"]))
    res = {
        "renglones_del_censo": {"s1bis": c1["censo_total"], "s1ter": c2["censo_total"],
                                "por_clase_s1bis": c1["censo_por_clase"], "por_clase_s1ter": c2["censo_por_clase"],
                                "en_los_dos": sum((r1 & r2).values()),
                                "solo_en_s1bis": lista(r1 - r2), "solo_en_s1ter": lista(r2 - r1),
                                "paginas_s1ter": c2["paginas_con_renglones_en_el_censo"],
                                "tos_s1ter": len(c2["censo_por_to"])},
        "sin_explicacion": {"s1bis": sum(s1.values()), "s1ter": sum(s2.values()),
                            "quedan": sum((s1 & s2).values()), "salen": lista(s1 - s2), "entran": lista(s2 - s1),
                            "tos_s1ter": len({k[0] for k in s2}), "lista_s1ter": lista(s2)},
        "hallazgo_1_16_criterio_original": {
            "s1bis": {"casos": len(h1), "tos": len({i.split('::')[0] for i in h1})},
            "s1ter": {"casos": len(h2), "tos": len({i.split('::')[0] for i in h2})},
            "en_los_dos": len(set(h1) & set(h2)), "en_los_dos_con_el_mismo_cierre_y_paginas": len(mismo),
            "solo_en_s1bis": sorted(set(h1) - set(h2)), "solo_en_s1ter": sorted(set(h2) - set(h1)),
            "tanda1": {"lista": list(TANDA1),
                       "s1bis": {"casos": len(t1), "tos": len({i.split('::')[0] for i in t1})},
                       "s1ter": {"casos": len(t2), "tos": len({i.split('::')[0] for i in t2}),
                                 "por_to": dict(sorted(Counter(i.split("::")[0] for i in t2).items())),
                                 "paginas": len({(i.split("::")[0], p) for i in t2 for p in h2[i]["paginas"]}),
                                 "caracteres_propios_de_los_candidatos": sum(chars[i] for i in t2)},
                       "solo_en_s1bis": sorted(t1 - t2), "solo_en_s1ter": sorted(t2 - t1),
                       "ids_s1ter": sorted(t2)}}}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    v = json.loads(json.dumps(res))
    for k in ("solo_en_s1bis", "solo_en_s1ter"):
        v["renglones_del_censo"][k] = len(v["renglones_del_censo"][k])
    v["sin_explicacion"]["lista_s1ter"] = len(v["sin_explicacion"]["lista_s1ter"])
    v["hallazgo_1_16_criterio_original"]["tanda1"]["ids_s1ter"] = len(
        v["hallazgo_1_16_criterio_original"]["tanda1"]["ids_s1ter"])
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
