"""Cifras 4.a, 4.b, 4.c y 4.e de S2 (U-SEG-OFICIAL), sobre la E0 corregida y sobre la partición legada (solo lectura).

Uso: python -B cifras_conjuntos_clases_S2.py --e0 <salida de E0 de los 152> --raiz <copia del repo> --out <json>

Fuentes por lado:
- corregida: los 152 de --e0 (chunks_<to>.json, estructura_<to>.json, conteos.json); los 5 de desarrollo de la e0-r2 de la
  tanda 0, `reextraccion_v2/e0_chunking/salida_tanda0_r2b/` (`9f6361e`);
- legada: los 152 de `segmentacion_84/b584_particion/<to>/` y `conteos_b584.json`; los 5 de desarrollo de
  `reextraccion_v2/e0_chunking/salida_tanda0/` (la fuente de `reports/u_insumos_cap/u_insumos_i1.py:262-277`).

Definiciones, las del reporte legado (`reports/u_insumos_cap/u_insumos_i1.py`, `ded3494`), sin adaptar:
- unidad (R3): cada elemento de `chunks_<to>.json`; tipo, el campo `tipo` de primer nivel; los mini-chunks, también por
  `rol_bloque` (`:329-332`);
- punto de la estructura (R12, `:370-385`): los nodos de `estructura.secciones`, recorridos por `hijos`, con
  `tipo == "punto"`; terminal, sin `hijos`; contenedor, con `hijos`. Las secciones no cuentan.
- categoría: `escalado_prep/inventario_tos.csv` para los 152; para los 5 de desarrollo, la lista del índice oficial
  (`u_insumos_i1.py:220-228`, que copia `escalado_prep/code/construir_inventario.py:34-45`).
Conjuntos (decisión 6, 1A): desarrollo = cap, cla, ext, pro, ric; validación = los 10 de origen ESQ-2 de
`esq/documentos_excluidos_evaluacion_final.json`; universo = los 152. Se solapan.
4.c (decisión 6, 3A y 3B): 3A = los que la E0 lee sin raíz (`sin_raiz` y su variante `sin_raiz_letra`) menos los no
segmentables, con los parciales aparte; 3B = los que no tienen ninguna unidad de sección (`unidad` que empieza con
`S<n>`); como segunda lectura de 3B, los que no tienen ninguna sección no sintética en `estructura.secciones`
(la clave `sintetica` de `e0_lib.serializar_estructura`). 4.e: los tres grupos de `particion_152.json` (`clase`).
ri_spi y ri_con (agregado 4 del «seguí» de S2): en la E0 corregida van por su razón vigente, las decisiones 1 y 2 de la
enmienda 8, y no como no segmentables; en la partición legada eran no segmentables. Se cuentan una sola vez.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

EXP = "data/experiment"
B584 = f"{EXP}/segmentacion_84/b584_particion"
T0_R2B = f"{EXP}/reextraccion_v2/e0_chunking/salida_tanda0_r2b"
T0_LEG = f"{EXP}/reextraccion_v2/e0_chunking/salida_tanda0"
INVENTARIO = f"{EXP}/escalado_prep/inventario_tos.csv"
INDICE_OFICIAL = f"{EXP}/escalado_prep/indice_oficial_raw.json"
EXCLUIDOS = f"{EXP}/esq/documentos_excluidos_evaluacion_final.json"
SUBSET_ARCHIVOS = {"t-excbio.pdf": "ext", "t-capmin.pdf": "cap", "t-cladeu.pdf": "cla",
                   "t-pusf.pdf": "pro", "t-RI-CM.pdf": "ric"}
CATEGORIAS = [("normativa_general", "textos_ordenados"), ("regimen_informativo", "regimenes_informativos")]
DESARROLLO = ["cap", "cla", "ext", "pro", "ric"]
RAZON_VIGENTE = {"ri_spi": "enmienda 8, decisión 1 (error de corte confirmado en S1-quater)",
                 "ri_con": "enmienda 8, decisión 2 (cadenas de encabezados heredados, BKL-0044)"}
NOTA_LEGADA = "en la partición legada era no segmentable (docs/protocolo_entre_tandas.md:163-166)"
RE_SECCION = re.compile(r"^S\d+(::|$)")


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def puntos(estructura: dict) -> tuple[int, int]:
    term = cont = 0

    def rec(n: dict) -> None:
        nonlocal term, cont
        if n.get("tipo") == "punto":
            if n.get("hijos"):
                cont += 1
            else:
                term += 1
        for h in n.get("hijos", []):
            rec(h)
    for s in estructura["secciones"]:
        rec(s)
    return term, cont


def por_to(chunks: list[dict], estructura: dict, paginas: int, modo: str | None) -> dict:
    tipos = Counter(c["tipo"] for c in chunks)
    minis = Counter(c.get("rol_bloque") for c in chunks if c["tipo"] == "mini_chunk")
    t, k = puntos(estructura)
    return {"unidades": len(chunks), "por_tipo": dict(sorted(tipos.items())),
            "mini_por_rol": dict(sorted((str(a), b) for a, b in minis.items())),
            "puntos_terminales": t, "puntos_contenedores": k, "puntos": t + k, "paginas": paginas,
            "modo_lectura": modo,
            "unidades_de_seccion": sum(1 for c in chunks if RE_SECCION.match(c["unidad"])),
            "secciones_no_sinteticas": sum(1 for s in estructura["secciones"] if not s.get("sintetica"))}


def sumar(filas: list[dict]) -> dict:
    tipos, minis = Counter(), Counter()
    for f in filas:
        tipos.update(f["por_tipo"])
        minis.update(f["mini_por_rol"])
    pt = sum(f["puntos_terminales"] for f in filas)
    p = sum(f["puntos"] for f in filas)
    return {"tos": len(filas), "unidades": sum(f["unidades"] for f in filas), "por_tipo": dict(sorted(tipos.items())),
            "mini_por_rol": dict(sorted(minis.items())), "paginas": sum(f["paginas"] for f in filas),
            "puntos": p, "puntos_terminales": pt,
            "porcentaje_terminales": round(100 * pt / p, 1) if p else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--raiz", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    r = a.raiz
    inv = {x["id"]: x for x in csv.DictReader(open(r / INVENTARIO, encoding="utf-8"))}
    indice = cargar(r / INDICE_OFICIAL)
    cat_dev = {}
    for cat, clave in CATEGORIAS:
        for it in indice[clave]:
            if it["archivo"] in SUBSET_ARCHIVOS:
                cat_dev[SUBSET_ARCHIVOS[it["archivo"]]] = cat
    assert sorted(cat_dev) == DESARROLLO
    validacion = sorted(d["id"] for d in cargar(r / EXCLUIDOS)["documentos"] if d["origen"].startswith("ESQ-2"))
    assert len(validacion) == 10
    part = cargar(r / B584 / "particion_152.json")["por_to"]
    c_leg = cargar(r / B584 / "conteos_b584.json")
    c_cor = cargar(a.e0 / "conteos.json")
    c_t0r2b = cargar(r / T0_R2B / "conteos.json")
    c_t0leg = cargar(r / T0_LEG / "conteos.json")
    tos152 = sorted(part)
    assert set(inv) == set(tos152)
    cat = {**{t: inv[t]["categoria"] for t in tos152}, **cat_dev}

    lado: dict[str, dict[str, dict]] = {"corregida": {}, "legada": {}}
    for t in tos152:
        lado["corregida"][t] = por_to(cargar(a.e0 / f"chunks_{t}.json"), cargar(a.e0 / f"estructura_{t}.json"),
                                      c_cor[t]["paginas"], c_cor[t].get("modo_lectura"))
        lado["legada"][t] = por_to(cargar(r / B584 / t / f"chunks_{t}.json"),
                                   cargar(r / B584 / t / f"estructura_{t}.json"),
                                   c_leg[t]["paginas"], c_leg[t].get("modo_lectura"))
    for t in DESARROLLO:
        lado["corregida"][t] = por_to(cargar(r / T0_R2B / f"chunks_{t}.json"), cargar(r / T0_R2B / f"estructura_{t}.json"),
                                      c_t0r2b[t]["paginas"], c_t0r2b[t].get("modo_lectura", "vigente"))
        lado["legada"][t] = por_to(cargar(r / T0_LEG / f"chunks_{t}.json"), cargar(r / T0_LEG / f"estructura_{t}.json"),
                                   c_t0leg[t]["paginas"], c_t0leg[t].get("modo_lectura", "vigente"))

    conjuntos = {"desarrollo": DESARROLLO, "validacion": validacion, "universo_152": tos152}
    out: dict = {"fuentes": {k: sha(r / k) for k in (INVENTARIO, INDICE_OFICIAL, EXCLUIDOS, f"{B584}/particion_152.json",
                                                      f"{B584}/conteos_b584.json", f"{T0_R2B}/conteos.json",
                                                      f"{T0_LEG}/conteos.json")},
                 "e0_conteos_sha256": sha(a.e0 / "conteos.json"),
                 "conjuntos_tos": conjuntos, "categoria_desarrollo": cat_dev}
    # 4.a
    out["4a"] = {l: {c: sumar([lado[l][t] for t in ts]) for c, ts in conjuntos.items()} for l in lado}
    out["4a"]["legada"]["tanda0_5"] = sumar([lado["legada"][t] for t in ["ctacte", "docvig", "lingob", "pagjub", "polcre"]])
    # 4.b, sobre los 157
    tos157 = tos152 + DESARROLLO
    out["4b"] = {l: {k: sumar([lado[l][t] for t in tos157 if cat[t] == k])
                     for k in ("normativa_general", "regimen_informativo")} for l in lado}
    for l in lado:
        out["4b"][l]["total_157"] = sumar([lado[l][t] for t in tos157])
    # 4.c
    no_seg_leg = sorted(t for t in tos152 if part[t]["clase"] == "no_segmentable_declarado")
    parciales = sorted(t for t in tos152 if part[t]["clase"] == "parcial_declarado")
    no_seg_cor = sorted(t for t in no_seg_leg if t not in RAZON_VIGENTE)
    c4 = {}
    for l, no_seg in (("corregida", no_seg_cor), ("legada", no_seg_leg)):
        sin_raiz = sorted(t for t in tos157 if (lado[l][t]["modo_lectura"] or "").startswith("sin_raiz"))
        a3 = sorted(t for t in sin_raiz if t not in no_seg and t not in parciales)
        b3 = sorted(t for t in tos157 if lado[l][t]["unidades_de_seccion"] == 0)
        b3e = sorted(t for t in tos157 if lado[l][t]["secciones_no_sinteticas"] == 0)
        c4[l] = {"sin_raiz": len(sin_raiz),
                 "3A": {"tos": len(a3), "lista": a3},
                 "3A_en_parte": {"tos": len([t for t in parciales if t in sin_raiz]),
                                 "lista": [t for t in parciales if t in sin_raiz]},
                 "no_segmentables": {"tos": len(no_seg), "lista": no_seg},
                 "3B": {"tos": len(b3), "lista": b3},
                 "3A_no_3B": sorted(set(a3) - set(b3)), "3B_no_3A": sorted(set(b3) - set(a3)),
                 "3B_estructura": {"tos": len(b3e), "lista": b3e},
                 "3A_no_3B_estructura": sorted(set(a3) - set(b3e)), "3B_estructura_no_3A": sorted(set(b3e) - set(a3)),
                 "modo_por_to_sin_raiz_letra": sorted(t for t in sin_raiz if lado[l][t]["modo_lectura"] == "sin_raiz_letra")}
    c4["corregida"]["ri_spi_y_ri_con"] = {t: {"modo": lado["corregida"][t]["modo_lectura"],
                                              "unidades": lado["corregida"][t]["unidades"],
                                              "en_3A": t in c4["corregida"]["3A"]["lista"],
                                              "razon_vigente": RAZON_VIGENTE[t], "nota": NOTA_LEGADA}
                                          for t in RAZON_VIGENTE}
    out["4c"] = c4
    # 4.e
    grupos = {"puntos_de_principio_a_fin": sorted(t for t in tos152 if part[t]["clase"] == "reconocido_pleno"),
              "fichas_y_listados": parciales}
    g = {}
    for l, no_seg in (("corregida", no_seg_cor), ("legada", no_seg_leg)):
        g[l] = {k: {**sumar([lado[l][t] for t in ts]), "lista": ts} for k, ts in grupos.items()}
        g[l]["no_segmentables"] = {**sumar([lado[l][t] for t in no_seg]), "lista": no_seg}
        if l == "corregida":
            g[l]["ri_spi_y_ri_con"] = {**sumar([lado[l][t] for t in RAZON_VIGENTE]), "lista": sorted(RAZON_VIGENTE),
                                       "razon_vigente": RAZON_VIGENTE, "nota": NOTA_LEGADA}
        assert sum(x["tos"] for x in g[l].values()) == 152
    out["4e"] = g
    out["por_to"] = lado
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for l in lado:
        print(l, "4a", {c: (v["tos"], v["unidades"], v.get("puntos_terminales"), v.get("puntos")) for c, v in out["4a"][l].items()})
        print(l, "4b", {c: (v["tos"], v["puntos"], v["puntos_terminales"], v["porcentaje_terminales"]) for c, v in out["4b"][l].items()})
        print(l, "4c", {k: (v["tos"] if isinstance(v, dict) and "tos" in v else (len(v) if isinstance(v, list) else v)) for k, v in c4[l].items() if k != "ri_spi_y_ri_con"})
        print(l, "4c 3B estructura vs 3A", c4[l]["3A_no_3B_estructura"], c4[l]["3B_estructura_no_3A"])
        print(l, "4e", {k: (v["tos"], v["paginas"], v["unidades"]) for k, v in g[l].items()})


if __name__ == "__main__":
    main()
