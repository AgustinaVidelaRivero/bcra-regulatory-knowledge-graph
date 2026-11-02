"""U-SEG-OFICIAL, S1-ter-b.1: las poblaciones finales de S1-ter, con las decisiones de la autora sobre el FRENO S1-ter-a,
SELLADAS ANTES DE SORTEAR (USD 0, sin API).

Uso: python -B poblaciones_finales_S1ter.py --poblaciones <poblaciones_S1ter.json> --controles <controles_S1ter.json>
       --manifiesto <manifiesto de S1-ter> --out <json>

Parte de `poblaciones_S1ter.json` (tramo a, sha256 controlado acá) y aplica, en este orden:
1. decisión 1: las 9 listas de (b) que también son candidatas del detector salen de (a); si una unidad de (b) está entre
   los 35 de regresión, sale de ese bloque, declarada; si una de las 51 unidades de la sección 3 de ri_oc está en (a),
   el script se detiene antes de escribir;
2. decisiones 2 y 3: sale de cortes, de (a) y de (b), declarada, toda unidad cuya E0 no se construye en ninguna tanda,
   según las enmiendas firmadas a las adendas 1 y 2 del laudo B5.5 (`e82e22f`):
   - `manual` (histórico, Parte III, punto 1) y `ri_ao` (derogado, Parte III, punto 2);
   - `optico` y `plandecuentas` (referencia, Parte II.2, punto 5);
   - las unidades de e0-r2 de los 9 TOs de vía por página (su prosa entra con la tanda 3 por la vía de páginas, Parte
     II.2, punto 1);
   - las 2 unidades de ri2_pm que cruzan fichas (bloque B, Parte II.2, punto 4; `controles_S1ter.json`, `ri2_pm`);
   - se quedan las unidades por punto de ri2_pm (Parte II.2, punto 3, `:57`) y ri_spi (Parte II.2, punto 2, se construye
     con la tanda 3 si su unidad de E0 cerró), declarado.
3. Compara con los valores esperados de la decisión 3 y se detiene si alguno no da.
El sha256 de cada población es `sha256("\\n".join(ids ordenados))`, como en `poblaciones_S1ter.py`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

SHA_POBLACIONES = "a1313bd6a614b85a21da1714fbe2a90bf5c62882da6794970dd8b67983b68853"
ENM = "docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md (e82e22f)"
NO_SE_CONSTRUYEN_TO = {"manual": f"histórico, fuera del recurso ({ENM}, Parte III, punto 1)",
                       "ri_ao": f"derogado, fuera del recurso ({ENM}, Parte III, punto 2)",
                       "optico": f"referencia, fuera del recurso ({ENM}, Parte II.2, punto 5)",
                       "plandecuentas": f"referencia, fuera del recurso ({ENM}, Parte II.2, punto 5)"}
VIA_PAGINA = f"vía por página: su prosa entra con la tanda 3 por la vía de páginas, no por su E0 ({ENM}, Parte II.2, punto 1)"
CRUZA_FICHAS = f"ri2_pm, unidad que cruza fichas: bloque B, release posterior ({ENM}, Parte II.2, punto 4)"
ESPERADOS = {"vigente": (8063, "733cd66b0de4ed4b28a08c0c5e38339ea90cb7ccebcc4415fe8ffda1212f508a"),
             "marcadores": (192, "6637ad1df7a2154c79f641e922550c1048bc6ca6bd329c6e00143b599cf5bdd2"),
             "sin_raiz": (1313, "1fec4bef4a1cd8e9b740ceed72518b8b50240d582411dd706b1b429bb74f7348"),
             "c116_a": (245, "23a8f6056fdd2eccdc27d664c5368b92895938452dd2be07b6a380a6c90b0066")}
TOTAL_CORTES, TOTAL_B = 9568, 36


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("poblaciones", "controles", "manifiesto", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    raw = a.poblaciones.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA_POBLACIONES, "poblaciones_S1ter.json no da su sha256 sellado"
    pob = json.loads(raw)
    man = json.loads(a.manifiesto.read_text(encoding="utf-8"))
    via = {t["id"]: t["via"] for t in man["tos"]}
    cruzan = set(json.loads(a.controles.read_text(encoding="utf-8"))["ri2_pm"]["cruzan_fichas"])
    assert len(cruzan) == 2

    def motivo(uid: str) -> str | None:
        to = uid.split("::")[0]
        if to in NO_SE_CONSTRUYEN_TO:
            return NO_SE_CONSTRUYEN_TO[to]
        if via[to] == "por_pagina":
            return VIA_PAGINA
        if uid in cruzan:
            return CRUZA_FICHAS
        return None

    salen: list[dict] = []

    def filtrar(nombre: str, ids: list[str]) -> list[str]:
        out = []
        for i in ids:
            m = motivo(i)
            if m:
                salen.append({"poblacion": nombre, "id": i, "motivo": m})
            else:
                out.append(i)
        return sorted(out)

    # cortes
    cortes = {e: filtrar(f"cortes:{e}", g["ids"]) for e, g in pob["cortes"]["estratos"].items()}
    # 1.16 (a): decisión 1, después la regla de construcción
    b = pob["c116_b"]
    listas_b = [x["lista"] for x in b["listas_r5a"]]
    sec3 = b["ri_oc"]["seccion_3"]["ids"]
    a0 = pob["c116_a"]["ids"]
    nueve = sorted(set(a0) & set(listas_b + ["ri_oc::S2"]))
    assert nueve == sorted(pob["c116_a"]["variante_sin_las_listas_de_b"]["salen"]) and len(nueve) == 9
    for i in nueve:
        salen.append({"poblacion": "c116_a", "id": i, "motivo": "lista de (b) que también es candidata del detector: (b) "
                                                                "se lee entera (decisión 1 de la autora sobre el FRENO S1-ter-a)"})
    if set(sec3) & set(a0):
        raise SystemExit(f"FRENO: unidades de la sección 3 de ri_oc en (a): {sorted(set(sec3) & set(a0))}")
    c116_a = filtrar("c116_a", [i for i in a0 if i not in set(nueve)])
    # 1.16 (b): las 34 listas (con sus partes, si el último ítem está partido), ri_oc::S2 y la sección 3
    fijos_b = filtrar("c116_b", listas_b + ["ri_oc::S2"])
    for x in b["listas_r5a"]:
        for u in [x["cierre_id"]] + [p["id"] for p in x["ultimo_item_partido_por_tamano"]]:
            assert motivo(u) is None, f"la unidad {u} de (b) no se construye"
    sec3_f = filtrar("c116_b:seccion_3_ri_oc", sec3)
    # regresión
    reg0 = [r["id"] for r in pob["regresion"]["lista"]]
    de_b_en_reg = sorted(set(reg0) & set(fijos_b + sec3_f))
    for i in de_b_en_reg:
        salen.append({"poblacion": "regresion", "id": i, "motivo": "unidad de (b): sale del bloque de regresión "
                                                                   "(decisión 1 de la autora sobre el FRENO S1-ter-a)"})
    reg = sorted(i for i in reg0 if i not in set(de_b_en_reg))
    reg_sin_construir = [i for i in reg if motivo(i)]

    obtenido = {e: (len(v), sha_ids(v)) for e, v in cortes.items()} | {"c116_a": (len(c116_a), sha_ids(c116_a))}
    dif = {k: {"esperado": ESPERADOS[k], "obtenido": obtenido[k]} for k in ESPERADOS if ESPERADOS[k] != obtenido[k]}
    total_cortes = sum(len(v) for v in cortes.values())
    total_b = len(fijos_b) + (1 if sec3_f else 0)
    if dif or total_cortes != TOTAL_CORTES or total_b != TOTAL_B:
        raise SystemExit("FRENO: las poblaciones finales no dan los valores esperados: "
                         + json.dumps({"diferencias": dif, "total_cortes": total_cortes, "total_b": total_b},
                                      ensure_ascii=False))
    pesos = {e: len(v) / total_cortes for e, v in cortes.items()}
    res = {"criterio": "decisiones 1 a 3 de la autora sobre el FRENO S1-ter-a, aplicadas a poblaciones_S1ter.json "
                       f"({SHA_POBLACIONES}); sha256 de cada población = sha256 de sus ids ordenados unidos por salto",
           "sellado": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
           "cortes": {e: {"unidades": len(v), "peso": pesos[e], "n": pob["cortes"]["estratos"][e]["n"],
                          "semilla": f"U-SEG-OFICIAL:cortes:S1-ter:{e}", "sha256_ids_ordenados": sha_ids(v), "ids": v}
                      for e, v in cortes.items()},
           "cortes_total": total_cortes,
           "c116_a": {"unidades": len(c116_a), "n": 30, "semilla": "U-SEG-OFICIAL:1_16:S1-ter",
                      "sha256_ids_ordenados": sha_ids(c116_a), "ids": c116_a},
           "c116_b": {"total": total_b, "fijos": {"unidades": len(fijos_b), "sha256_ids_ordenados": sha_ids(fijos_b),
                                                  "ids": fijos_b},
                      "seccion_3_ri_oc": {"unidades": len(sec3_f), "semilla": "U-SEG-OFICIAL:1_16:S1-ter:ri_oc",
                                          "sha256_ids_ordenados": sha_ids(sec3_f), "ids": sec3_f},
                      "listas": {x["lista"]: {"unidades_del_ultimo_item": ([x["lista"]] if x["ultimo_item"] else
                                                                           [p["id"] for p in
                                                                            x["ultimo_item_partido_por_tamano"]]),
                                              "cierre": x["cierre_id"], "clase_mesa": x["clase_mesa"]}
                                 for x in b["listas_r5a"]}},
           "regresion": {"unidades": len(reg), "sha256_ids_ordenados": sha_ids(reg), "ids": reg,
                         "salen_por_ser_de_b": de_b_en_reg, "sin_construir": reg_sin_construir},
           "salen": salen,
           "salen_por_poblacion": {k: sum(1 for s in salen if s["poblacion"] == k)
                                   for k in sorted({s["poblacion"] for s in salen})},
           "se_quedan_declarados": {
               "ri_spi": f"se construye con la tanda 3 si su unidad de E0 cerró ({ENM}, Parte II.2, punto 2); sus 92 "
                         "unidades siguen en cortes:sin_raiz",
               "ri2_pm_por_punto": f"sus unidades por punto se construyen con la tanda 3 ({ENM}, Parte II.2, punto 3, :57): "
                                   "ri2_pm::2.2.3 y ri2_pm::3.5.5 siguen en (a) y ri2_pm::1.6 en (b)"},
           "controles": {"seccion_3_en_a": sorted(set(sec3) & set(c116_a)), "a_con_b": sorted(set(c116_a) & set(fijos_b)),
                         "b_en_regresion": de_b_en_reg}}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"sellado": res["sellado"],
                      "cortes": {e: {k: v for k, v in g.items() if k != "ids"} for e, g in res["cortes"].items()},
                      "cortes_total": total_cortes,
                      "c116_a": {k: v for k, v in res["c116_a"].items() if k != "ids"},
                      "c116_b": {"total": total_b, "fijos": res["c116_b"]["fijos"]["unidades"],
                                 "sha_fijos": res["c116_b"]["fijos"]["sha256_ids_ordenados"],
                                 "seccion_3": res["c116_b"]["seccion_3_ri_oc"]["unidades"]},
                      "regresion": {k: v for k, v in res["regresion"].items() if k != "ids"},
                      "salen_por_poblacion": res["salen_por_poblacion"], "controles": res["controles"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
