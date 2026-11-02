"""Límites declarados de S0-5a, con su cifra (U-SEG-OFICIAL; USD 0, solo lectura de las salidas).

Uso: python -B limites_S0-5a.py --e0 <E0 de S0-5a, los 152> --t0-ref <salida_tanda0_r2b> --t0-sin <E0 de la tanda 0
       con las reglas sin la exclusión> --out <json>

Los del §3 del mandato (criterio del punto 4 de la autora: en la tanda 1, regla por lista en S0-5; si no, límite y
grupo 2), leídos en la salida final:
- limpieza fuera de la tanda 1 (grupo 2): el tercer renglón del recuadro del encabezado como texto del preámbulo
  (`ri_iepsp::S0`, `ri_ieccm::S0`) y el encabezado de columna repetido dentro de `ri_icpipsp::A1C3::S2`;
- ri_secoexpo: la numeración que vuelve a empezar en el bloque A.2, dentro de `ri_secoexpo::S17` (grupo 2; si sale en
  el sorteo de S1-ter, cuenta como error);
- `ri_mmsef::2.2::intro`: una sola unidad (no es error de corte; no cambia).
Y los de esta etapa: lo que las reglas cambiarían en la tanda 0, que queda fuera por lista (por TO, las unidades
creadas, quitadas y cambiadas contra `salida_tanda0_r2b/`).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ENCABEZADO_COLUMNA = "Requerimiento normativo Procedimiento aplicado"


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0", "t0_ref", "t0_sin", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()

    def u(uid: str) -> dict | None:
        return {c["id"]: c for c in jl(a.e0 / f"chunks_{uid.split('::')[0]}.json")}.get(uid)

    res: dict = {}
    for uid in ("ri_iepsp::S0", "ri_ieccm::S0"):
        c = u(uid)
        res[uid] = {"paginas": c["paginas"], "caracteres": c["chars_propio"], "texto": c["texto"],
                    "renglon_del_recuadro": c["texto"].split("\n")[1] if "\n" in c["texto"] else None,
                    "grupo": 2, "tanda1": False}
    icp = {c["id"]: c for c in jl(a.e0 / "chunks_ri_icpipsp.json")}
    rep = {i: c["texto"].split("\n").count(ENCABEZADO_COLUMNA) for i, c in icp.items()
           if ENCABEZADO_COLUMNA in c["texto"].split("\n")}
    res["ri_icpipsp::A1C3::S2"] = {"renglon": ENCABEZADO_COLUMNA, "unidades_que_lo_llevan": rep,
                                   "caracteres_de_la_unidad": icp["ri_icpipsp::A1C3::S2"]["chars_propio"],
                                   "paginas": icp["ri_icpipsp::A1C3::S2"]["paginas"], "grupo": 2, "tanda1": False}
    s17 = u("ri_secoexpo::S17")
    res["ri_secoexpo::S17"] = {"paginas": s17["paginas"], "caracteres": s17["chars_propio"],
                               "empieza": s17["texto"][:80], "grupo": 2, "tanda1": False,
                               "si_sale_en_S1-ter": "cuenta como error"}
    m = u("ri_mmsef::2.2::intro")
    res["ri_mmsef::2.2::intro"] = {"paginas": m["paginas"], "caracteres": m["chars_propio"],
                                   "unidades_2.2_intro": sum(1 for c in jl(a.e0 / "chunks_ri_mmsef.json")
                                                             if c["id"] == "ri_mmsef::2.2::intro")}
    t0 = {}
    ref = sorted(a.t0_ref.glob("chunks_*.json"))
    if not ref or not any(a.t0_sin.glob("chunks_*.json")):
        raise SystemExit(f"sin chunks en {a.t0_ref} o en {a.t0_sin}")
    for p in ref:
        x = {c["id"]: c for c in jl(p)}
        y = {c["id"]: c for c in jl(a.t0_sin / p.name)}
        if x == y:
            continue
        t0[p.name[7:-5]] = {"unidades": [len(x), len(y)], "creadas": sorted(set(y) - set(x)),
                            "quitadas": sorted(set(x) - set(y)),
                            "cambiadas": sorted(i for i in set(x) & set(y) if x[i] != y[i])}
    res["tanda0_fuera_de_S0-5a"] = {
        "tos": sorted(t0), "creadas": sum(len(v["creadas"]) for v in t0.values()),
        "quitadas": sum(len(v["quitadas"]) for v in t0.values()),
        "cambiadas": sum(len(v["cambiadas"]) for v in t0.values()), "por_to": t0}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk not in ("por_to", "texto")} if isinstance(v, dict) else v)
                      for k, v in res.items()}, ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main()
