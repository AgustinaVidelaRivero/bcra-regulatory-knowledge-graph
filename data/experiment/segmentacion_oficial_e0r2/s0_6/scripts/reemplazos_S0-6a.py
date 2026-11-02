"""Las reglas por lista que reemplazan las reglas generales de S0-6a (U-SEG-OFICIAL; USD 0, sin API): qué da la regla
general en las unidades que tocaba cada lista (mandato de S0-6a, §2).

Uso: python -B reemplazos_S0-6a.py --codigo <dir de correr_e0.py> --base <E0 de S0-5b> --regla c=<E0 con C sola> …
       --final <E0 corregida> --out <json>

Las listas salen del código (`LISTAS_R5A_S0_5`, `TOS_TITULO_BLOQUE_S0_5`, `RAICES_POR_LISTA_S0_5`,
`ROTULOS_POR_LISTA_S0_5`). Unidades que tocaba cada lista, en la E0 de S0-5b (donde la lista corría):
- R5-a (reemplazada por C): por lista, el último ítem (o sus partes), los cierres de su madre (`<madre>::cierre…`) y las unidades
  que heredan esos cierres;
- R5-a′ (reemplazada por A, ri_oc): las unidades `Sbloque<k>` de la lista y las que heredan algo de ellas;
- R5-g (reemplazada por E, ri_oc): la raíz de la lista y las unidades que la heredan;
- R5-f (reemplazada por H, ri_ccna): los puntos de la lista y las unidades que los heredan.
Por unidad: si la regla general sola (y la E0 corregida) dan la misma unidad (mismo id, sha256 propio, páginas y
herencia), o qué cambia. Solo ids y campos: sin texto.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CAMPOS = ("sha256_propio", "paginas", "herencia")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def chunks(d: Path, to: str) -> dict:
    return {c["id"]: c for c in jl(d / f"chunks_{to}.json")}


def comparar(b: dict, f: dict | None) -> list[str]:
    return ["id"] if f is None else [k for k in CAMPOS if b.get(k) != f.get(k)]


def madre(num: str) -> str:
    return num.rsplit(".", 1)[0] if "." in num else f"S{num}"


def heredan(base: dict, ids: set[str], origenes: set[str]) -> set[str]:
    """Las unidades cuya herencia tiene un tramo cuyo origen es uno de `origenes` (unidad de origen)."""
    return {i for i, c in base.items() if i not in ids and any(t["unidad_origen"] in origenes for t in c["herencia"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--regla", action="append", default=[])
    ap.add_argument("--final", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(a.codigo))
    import correr_e0 as CE
    reglas = dict(x.split("=", 1) for x in a.regla)
    casos = []      # (lista, regla general, to, unidades tocadas, detalle de la lista)
    for to, items in sorted(CE.LISTAS_R5A_S0_5.items()):
        base = chunks(a.base, to)
        for item, rango in items.items():
            m = madre(item)
            cierres = {i for i in base if i == f"{to}::{m}::cierre" or i.startswith(f"{to}::{m}::cierre::")}
            ids = {i for i in base if i == f"{to}::{item}" or i.startswith(f"{to}::{item}::parte")} | cierres     # o sus partes
            ids |= {i for i in heredan(base, ids, {m}) if any(t["unidad_origen"] == m and t["tipo"] == "cierre"
                                                               for t in base[i]["herencia"])}
            casos.append(("R5-a", "c", to, ids, {"item": item, "rango": rango is not None, "cierres_en_S0-5b": sorted(cierres)}))
    for to in sorted(CE.TOS_TITULO_BLOQUE_S0_5):
        base = chunks(a.base, to)
        bl = {i for i in base if i.split("::")[1].startswith("Sbloque")}
        orig = {i.split("::")[1].split("::")[0] for i in bl}
        casos.append(("R5-a′", "a", to, bl | heredan(base, bl, orig), {"bloques_en_S0-5b": sorted(bl)}))
    for to, raices in sorted(CE.RAICES_POR_LISTA_S0_5.items()):
        base = chunks(a.base, to)
        orig = {f"S{r[2]}" for r in raices}
        ids = {i for i in base if i.split("::")[1] in orig} | heredan(base, set(), orig)
        casos.append(("R5-g", "e", to, ids, {"raices": sorted(orig)}))
    for to, rot in sorted(CE.ROTULOS_POR_LISTA_S0_5.items()):
        if CE.REEMPLAZOS_S0_6["r5f"][1] is not None and to not in CE.REEMPLAZOS_S0_6["r5f"][1]:
            continue
        base = chunks(a.base, to)
        nums = {r[2] for r in rot}
        puntos = {i for i in base if i.split("::")[-1] in nums}
        orig = {i.split("::", 1)[1] for i in puntos}
        casos.append(("R5-f", "h", to, puntos | heredan(base, puntos, orig), {"rotulos": sorted(nums), "puntos_en_S0-5b": sorted(puntos)}))
    out = []
    for lista, regla, to, ids, det in casos:
        base = chunks(a.base, to)
        sola = chunks(Path(reglas[regla]), to)
        fin = chunks(a.final, to)
        filas = []
        for i in sorted(ids):
            cs, cf = comparar(base[i], sola.get(i)), comparar(base[i], fin.get(i))
            filas.append({"id": i, "con_la_regla_sola": cs or "igual", "en_la_corregida": cf or "igual"})
        out.append({"lista": lista, "regla_general": regla, "to": to, **det, "unidades": len(filas),
                    "iguales_con_la_regla_sola": sum(1 for f in filas if f["con_la_regla_sola"] == "igual"),
                    "iguales_en_la_corregida": sum(1 for f in filas if f["en_la_corregida"] == "igual"),
                    "por_unidad": filas})
    res = {"por_lista": out,
           "resumen": {l: {"listas": sum(1 for x in out if x["lista"] == l),
                           "unidades": sum(x["unidades"] for x in out if x["lista"] == l),
                           "iguales_con_la_regla_sola": sum(x["iguales_con_la_regla_sola"] for x in out if x["lista"] == l),
                           "listas_iguales_con_la_regla_sola": sum(1 for x in out if x["lista"] == l
                                                                  and x["iguales_con_la_regla_sola"] == x["unidades"])}
                       for l in ("R5-a", "R5-a′", "R5-g", "R5-f")}}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res["resumen"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
