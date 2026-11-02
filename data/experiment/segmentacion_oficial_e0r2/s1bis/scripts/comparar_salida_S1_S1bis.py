"""U-SEG-OFICIAL, S1-bis: la salida de E0 de S1-bis contra la de S1, por TO (USD 0, sin API). No lee ni marca.

Uso: python -B comparar_salida_S1_S1bis.py --s1-e0 <salida de E0 de S1> --e0 <salida de S1-bis> --manifiesto <json>
       --out <json>

Por TO: si los cinco archivos (chunks, estructura, indice, pies, tablas) salen byte a byte iguales a S1, las unidades
de cada corrida y los ids que entran y salen. Aparte, para las decisiones del FRENO S1-bis-a: las unidades de ri2_pm
que cambian respecto de S1 y en qué campos, y los ids de ri_spi que entran y salen.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

POR_TO = ("chunks", "estructura", "indice", "pies", "tablas")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("s1_e0", "e0", "manifiesto", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    man = jl(a.manifiesto)
    por_to, cambios = {}, {}
    for t in man["tos"]:
        to = t["id"]
        iguales = {p: (a.s1_e0 / f"{p}_{to}.json").read_bytes() == (a.e0 / f"{p}_{to}.json").read_bytes() for p in POR_TO}
        c1 = {c["id"]: c for c in jl(a.s1_e0 / f"chunks_{to}.json")}
        c2 = {c["id"]: c for c in jl(a.e0 / f"chunks_{to}.json")}
        por_to[to] = {"clase": t["clase"], "iguales_a_s1": all(iguales.values()), "archivos_iguales": iguales,
                      "unidades_s1": len(c1), "unidades_s1bis": len(c2),
                      "ids_solo_en_s1": sorted(set(c1) - set(c2)), "ids_solo_en_s1bis": sorted(set(c2) - set(c1))}
        if to in ("ri2_pm", "ri_spi"):
            cambios[to] = {i: sorted(k for k in c1[i] if c1[i][k] != c2[i].get(k)) for i in sorted(set(c1) & set(c2))
                           if c1[i] != c2[i]}
    res = {"tos": len(por_to),
           "tos_iguales_a_s1": sorted(t for t, v in por_to.items() if v["iguales_a_s1"]),
           "tos_distintos_de_s1": sorted(t for t, v in por_to.items() if not v["iguales_a_s1"]),
           "tos_con_otras_unidades": sorted(t for t, v in por_to.items() if v["unidades_s1"] != v["unidades_s1bis"]),
           "unidades_s1": sum(v["unidades_s1"] for v in por_to.values()),
           "unidades_s1bis": sum(v["unidades_s1bis"] for v in por_to.values()),
           "no_plenos_distintos_de_s1": sorted(t for t, v in por_to.items()
                                               if not v["iguales_a_s1"] and v["clase"] != "reconocido_pleno"),
           "unidades_que_cambian": cambios,
           "por_to": por_to}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) and k.startswith("tos_") else v) for k, v in res.items()
                      if k != "por_to"} | {"ri_spi": {k: por_to["ri_spi"][k] for k in ("unidades_s1", "unidades_s1bis",
                                                                                      "ids_solo_en_s1",
                                                                                      "ids_solo_en_s1bis")}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
