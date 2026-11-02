"""Cifras del punto 3 de S2 (U-SEG-OFICIAL) sobre la E0 corregida, con la partición legada al lado (solo lectura).

Uso: python -B cifras_punto3_S2.py --e0 <salida de E0 de los 152> --raiz <copia del repo> --out <json>

- TOs por vía (`s1ter/manifiesto/segmentacion_oficial_e0r2_152.json`, `via`, `818c3a43`) y por modo de lectura (E0
  corregida, `conteos.json`; legada, `conteos_b584.json`).
- Páginas y unidades por clase (`particion_152.json`, `clase`; ri_spi y ri_con en su fila propia, por su razón vigente,
  las decisiones 1 y 2 de la enmienda 8, con la nota de que en la partición legada eran no segmentables) y por categoría.
- Unidades, chunks terminales (`punto_terminal` y `seccion_sin_puntos`) y mini-chunks por rol, de `chunks_<to>.json`.
- Unidades partidas por tamaño (`sub_chunking.json`): particiones, partes, partes sobre el umbral; sin partir, por motivo.
- Tablas (`tablas_<to>.json`): TOs donde corre la lectura de tablas, TOs con tablas, tablas por origen y estado, tablas
  serializadas (`serializacion.serializada`), y unidades con una tabla serializada (`flags.tablas_e0[].serializada`).
- Ids desambiguados por TO (`ids_desambiguados.json`, regla L) y, de esos, los chunks que quedan en páginas de rol
  índice (`pies_<to>.json`, `paginas_detalle[].rol`): «chunks de índice que quedan».
- Encabezados conservados por K, por TO (`encabezados_conservados.json`; solo la cantidad, no el texto).
- Los no segmentables y los parciales, con sus páginas.
No imprime ni guarda texto de unidades.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

B584 = "data/experiment/segmentacion_84/b584_particion"
MAN152 = "data/experiment/segmentacion_oficial_e0r2/s1ter/manifiesto/segmentacion_oficial_e0r2_152.json"
INVENTARIO = "data/experiment/escalado_prep/inventario_tos.csv"
RAZON_VIGENTE = {"ri_spi": "enmienda 8, decisión 1", "ri_con": "enmienda 8, decisión 2"}
NOTA_LEGADA = "en la partición legada era no segmentable (docs/protocolo_entre_tandas.md:163-166)"


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--raiz", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    e0, r = a.e0, a.raiz
    conteos = cargar(e0 / "conteos.json")
    c_leg = cargar(r / B584 / "conteos_b584.json")
    part = cargar(r / B584 / "particion_152.json")["por_to"]
    man = {t["id"]: t for t in cargar(r / MAN152)["tos"]}
    import csv
    cat = {x["id"]: x["categoria"] for x in csv.DictReader(open(r / INVENTARIO, encoding="utf-8"))}
    tos = sorted(conteos)
    assert len(tos) == 152 and set(man) == set(tos) == set(part)

    def clase(t: str) -> str:
        if t in RAZON_VIGENTE:
            return "ri_spi_y_ri_con"
        return part[t]["clase"]

    out: dict = {"fuentes": {k: sha(r / k) for k in (f"{B584}/conteos_b584.json", f"{B584}/particion_152.json", MAN152, INVENTARIO)},
                 "e0_conteos_sha256": sha(e0 / "conteos.json"), "nota_ri_spi_ri_con": {t: [RAZON_VIGENTE[t], NOTA_LEGADA]
                                                                                       for t in RAZON_VIGENTE}}
    # vía y modo
    out["via_por_modo"] = {"corregida": {}, "legada": {}}
    for t in tos:
        v = man[t]["via"]
        for lado, m in (("corregida", conteos[t].get("modo_lectura")), ("legada", c_leg[t].get("modo_lectura"))):
            out["via_por_modo"][lado].setdefault(v, Counter())[m] += 1
    out["via_por_modo"] = {l: {v: dict(sorted(c.items())) for v, c in d.items()} for l, d in out["via_por_modo"].items()}
    out["via"] = dict(sorted(Counter(man[t]["via"] for t in tos).items()))
    # por TO, sobre los chunks
    filas = {}
    for t in tos:
        ch = cargar(e0 / f"chunks_{t}.json")
        tipos = Counter(c["tipo"] for c in ch)
        minis = Counter(c.get("rol_bloque") for c in ch if c["tipo"] == "mini_chunk")
        con_tabla = sum(1 for c in ch if any(y.get("serializada") for y in (c.get("flags", {}).get("tablas_e0") or [])))
        tj = cargar(e0 / f"tablas_{t}.json")
        filas[t] = {"paginas": conteos[t]["paginas"], "unidades": len(ch), "por_tipo": dict(tipos),
                    "mini_por_rol": dict(minis), "clase": clase(t), "categoria": cat[t],
                    "tablas": len(tj["tablas"]),
                    "tablas_por_origen": dict(Counter(x["origen"] for x in tj["tablas"])),
                    "tablas_por_estado": dict(Counter(x["estado"] for x in tj["tablas"])),
                    "tablas_serializadas": sum(1 for x in tj["tablas"] if (x.get("serializacion") or {}).get("serializada")),
                    "unidades_con_tabla_serializada": con_tabla,
                    "unidades_legadas": part[t]["unidades"], "paginas_legadas": part[t]["paginas"]}

    def sumar(ts):
        tipos, minis = Counter(), Counter()
        for t in ts:
            tipos.update(filas[t]["por_tipo"])
            minis.update(filas[t]["mini_por_rol"])
        return {"tos": len(ts), "paginas": sum(filas[t]["paginas"] for t in ts),
                "unidades": sum(filas[t]["unidades"] for t in ts), "por_tipo": dict(sorted(tipos.items())),
                "mini_por_rol": dict(sorted((str(k), v) for k, v in minis.items())),
                "unidades_legadas": sum(filas[t]["unidades_legadas"] for t in ts),
                "paginas_legadas": sum(filas[t]["paginas_legadas"] for t in ts)}
    por_clase = defaultdict(list)
    por_cat = defaultdict(list)
    for t in tos:
        por_clase[filas[t]["clase"]].append(t)
        por_cat[filas[t]["categoria"]].append(t)
    out["por_clase"] = {k: {**sumar(v), "lista": v if len(v) <= 14 else None} for k, v in sorted(por_clase.items())}
    out["por_categoria"] = {k: sumar(v) for k, v in sorted(por_cat.items())}
    out["total"] = sumar(tos)
    tot = out["total"]["por_tipo"]
    out["unidades_totales"] = out["total"]["unidades"]
    out["chunks_terminales"] = tot.get("punto_terminal", 0) + tot.get("seccion_sin_puntos", 0)
    out["mini_chunks"] = tot.get("mini_chunk", 0)
    assert out["chunks_terminales"] == sum(conteos[t]["chunks_terminales"] for t in tos)
    assert out["mini_chunks"] == sum(conteos[t]["mini_chunks"] for t in tos)
    # partidas por tamaño
    sub = cargar(e0 / "sub_chunking.json")
    part_tam = {t: {"particiones": [{"id": p["id"], "chars_propio": p["chars_propio"], "n_partes": p["n_partes"],
                                     "partes_sobre_umbral": len(p.get("partes_sobre_umbral") or [])}
                                    for p in v.get("particiones", [])],
                    "no_particionables": [{"id": x["id"], "chars_propio": x["chars_propio"], "motivo": x["motivo"]}
                                          for x in v.get("no_particionables", [])]} for t, v in sorted(sub.items())}
    out["partidas_por_tamano"] = {
        "umbral_chars": next(iter(sub.values()))["umbral_chars"], "objetivo_chars_parte": next(iter(sub.values()))["objetivo_chars_parte"],
        "unidades_partidas": sum(len(v["particiones"]) for v in part_tam.values()),
        "partes": sum(p["n_partes"] for v in part_tam.values() for p in v["particiones"]),
        "partes_sobre_umbral": sum(p["partes_sobre_umbral"] for v in part_tam.values() for p in v["particiones"]),
        "sin_partir": sum(len(v["no_particionables"]) for v in part_tam.values()),
        "sin_partir_por_motivo": dict(Counter(x["motivo"] for v in part_tam.values() for x in v["no_particionables"])),
        "por_to": part_tam}
    # tablas
    out["tablas"] = {"tos_donde_corre": sum(1 for t in tos if (e0 / f"tablas_{t}.json").exists()),
                     "tos_con_tablas": sum(1 for t in tos if filas[t]["tablas"]),
                     "tablas": sum(filas[t]["tablas"] for t in tos),
                     "tablas_por_origen": dict(sum((Counter(filas[t]["tablas_por_origen"]) for t in tos), Counter())),
                     "tablas_por_estado": dict(sum((Counter(filas[t]["tablas_por_estado"]) for t in tos), Counter())),
                     "tablas_serializadas": sum(filas[t]["tablas_serializadas"] for t in tos),
                     "tos_con_tabla_serializada": sum(1 for t in tos if filas[t]["tablas_serializadas"]),
                     "unidades_con_tabla_serializada": sum(filas[t]["unidades_con_tabla_serializada"] for t in tos),
                     "tos_con_unidades_con_tabla_serializada": sum(1 for t in tos if filas[t]["unidades_con_tabla_serializada"])}
    # ids desambiguados e índice
    ids_d = cargar(e0 / "ids_desambiguados.json") if (e0 / "ids_desambiguados.json").exists() else {}
    indice = {}
    for t, lst in sorted(ids_d.items()):
        pies = cargar(e0 / f"pies_{t}.json")
        rol_pag = {p["pagina"]: p["rol"] for p in pies["paginas_detalle"]}
        ch = {c["id"]: c for c in cargar(e0 / f"chunks_{t}.json")}
        filas_t = []
        for x in lst:
            c = ch.get(x["id"])
            roles = sorted({rol_pag.get(p) for p in (c["paginas"] if c else [])}, key=str)
            filas_t.append({"id": x["id"], "id_e0_original": x["id_e0_original"], "roles_de_sus_paginas": roles})
        indice[t] = {"ids_desambiguados": len(lst),
                     "en_paginas_de_indice": sum(1 for f in filas_t if "indice" in f["roles_de_sus_paginas"]),
                     "filas": filas_t}
    out["ids_desambiguados"] = {"tos": len(indice), "total": sum(v["ids_desambiguados"] for v in indice.values()),
                                "en_paginas_de_indice": sum(v["en_paginas_de_indice"] for v in indice.values()),
                                "por_to": indice}
    k = cargar(e0 / "encabezados_conservados.json") if (e0 / "encabezados_conservados.json").exists() else {}
    out["encabezados_conservados_K"] = {"tos": sum(1 for v in k.values() if v), "lineas": sum(len(v) for v in k.values()),
                                        "por_to": {t: len(v) for t, v in sorted(k.items()) if v}}
    # no segmentables y parciales
    ns = sorted(t for t in tos if part[t]["clase"] == "no_segmentable_declarado")
    pa = sorted(t for t in tos if part[t]["clase"] == "parcial_declarado")
    out["no_segmentables_y_parciales"] = {
        "no_segmentables_en_la_E0_corregida": [{"to": t, "paginas": filas[t]["paginas"], "unidades": filas[t]["unidades"],
                                                 "por_tipo": filas[t]["por_tipo"], "modo": conteos[t].get("modo_lectura")}
                                                for t in ns if t not in RAZON_VIGENTE],
        "ri_spi_y_ri_con": [{"to": t, "paginas": filas[t]["paginas"], "unidades": filas[t]["unidades"],
                             "por_tipo": filas[t]["por_tipo"], "modo": conteos[t].get("modo_lectura"),
                             "razon_vigente": RAZON_VIGENTE[t], "nota": NOTA_LEGADA} for t in sorted(RAZON_VIGENTE)],
        "parciales": [{"to": t, "paginas": filas[t]["paginas"], "unidades": filas[t]["unidades"],
                       "por_tipo": filas[t]["por_tipo"], "modo": conteos[t].get("modo_lectura"),
                       "via": man[t]["via"], "via_resto": man[t].get("via_resto")} for t in pa],
        "legado": {"no_segmentables": {"tos": len(ns), "paginas": sum(part[t]["paginas"] for t in ns),
                                       "unidades": sum(part[t]["unidades"] for t in ns)},
                   "parciales": {"tos": len(pa), "paginas": sum(part[t]["paginas"] for t in pa),
                                 "unidades": sum(part[t]["unidades"] for t in pa)}}}
    out["por_to"] = filas
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("via", "via_por_modo", "unidades_totales", "chunks_terminales", "mini_chunks",
                                          "tablas", "encabezados_conservados_K")}, ensure_ascii=False))
    print({k: (v["tos"], v["paginas"], v["unidades"], v["unidades_legadas"]) for k, v in out["por_clase"].items()})
    print({k: (v["tos"], v["paginas"], v["unidades"]) for k, v in out["por_categoria"].items()})
    print({k: v for k, v in out["partidas_por_tamano"].items() if k != "por_to"})
    print({k: v for k, v in out["ids_desambiguados"].items() if k != "por_to"},
          {t: (v["ids_desambiguados"], v["en_paginas_de_indice"]) for t, v in out["ids_desambiguados"]["por_to"].items()})
    print(out["no_segmentables_y_parciales"]["legado"])


if __name__ == "__main__":
    main()
