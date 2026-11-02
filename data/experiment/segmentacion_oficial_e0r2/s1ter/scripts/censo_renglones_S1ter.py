"""U-SEG-OFICIAL, S1-ter.4: censo de renglones del PDF fuera de toda unidad y de todo rol (USD 0, sin API).

Uso: python -B censo_renglones_S1ter.py --e0 <salida de la corrida> --manifiesto <json> --lineas <caché de lineas_152.py>
       --regla <s1/regla_censo_renglones_S1.md> --cambio <s1bis/regla_censo_renglones_S1bis.md> --pro <salida_tanda0_r2b>
       --out <json>

Copia de `s1bis/scripts/censo_renglones_S1bis.py` sin cambios en la lógica (solo este docstring): aplica la regla de
`s1/regla_censo_renglones_S1.md` (versión 2, sellada en S1) con el cambio de S1-bis (`s1bis/regla_censo_renglones_S1bis.md`,
sellado en S1-bis: el prefijo de sub-documento en el id del ítem del hallazgo 1.16). S1-ter no cambia la regla. La
clave `hallazgo_1_16` de esta salida es el criterio ORIGINAL del 1.16 (el de S1-bis) y queda solo para compararla con
los 121 candidatos de S1-bis: el censo del 1.16 de S1-ter es el del detector corregido
(`s0_5/scripts/detector_116.py`, unión del criterio original con la corrección). `--pro` es la E0 de la tanda 0
(`e0_chunking/salida_tanda0_r2b/`), solo para la calibración de la regla del hallazgo 1.16 en `pro::1.1.2.7`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PAGINAS_INDICE_S02 = {("adfsp", 3), ("ceninf", 2), ("cirmo3", 3), ("cirmo3", 4), ("nmaeef", 2), ("nmaeef", 14),
                      ("ri2_ae", 13)}
RE_MAYUS = re.compile(r"^[A-ZÁÉÍÓÚÑ]")


def nt(s: str) -> str:
    return " ".join(s.split())


def forma(s: str) -> str:
    return " ".join(re.sub(r"\d+", "#", s.casefold()).split())


def corrido(l) -> bool:
    return l[4] == 0 and len(l[3]) >= 55


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def renglones_sin_tabla(texto: str) -> list[str]:
    out, en_tabla = [], False
    for ln in texto.split("\n"):
        if ln.startswith("[TABLA "):
            en_tabla = True
        if not en_tabla:
            out.append(ln)
        if ln.startswith("[FIN TABLA "):
            en_tabla = False
    return out


def cortes(texto: str) -> list[int]:
    ls = texto.split("\n")
    return [i for i in range(1, len(ls)) if RE_MAYUS.match(ls[i].strip())
            and ls[i - 1].rstrip().endswith((".", ":"))]


def caso_116(e0: Path, to: str) -> tuple[list[dict], int, list[dict]]:
    """Regla del hallazgo 1.16 (último ítem de una lista con un corte de párrafo que los anteriores no tienen), con el
    prefijo de sub-documento de la raíz en el id del ítem (cambio de S1-bis)."""
    est = jl(e0 / f"estructura_{to}.json")
    ch = {c["id"]: c for c in jl(e0 / f"chunks_{to}.json")}
    casos, listas, sin_chunk = [], 0, []

    def visitar(nodo, pref):
        nonlocal listas
        hijos = [h for h in nodo.get("hijos", []) if h.get("tipo") == "punto"]
        if len(hijos) >= 2 and all(not h.get("hijos") for h in hijos):
            listas += 1
            ids = [f"{to}::{pref}::{h['numero']}" if pref else f"{to}::{h['numero']}" for h in hijos]
            textos = [ch.get(i) for i in ids]
            if not all(textos):
                sin_chunk.append({"padre": nodo.get("numero"), "prefijo": pref,
                                  "items_sin_chunk": [i for i, t in zip(ids, textos) if not t]})
            if all(textos):
                ult = textos[-1]
                c_ult = cortes(ult["texto"])
                if c_ult and not any(cortes(t["texto"]) for t in textos[:-1]):
                    ls = ult["texto"].split("\n")
                    casos.append({"id": ult["id"], "paginas": ult["paginas"], "padre": nodo.get("numero"),
                                  "prefijo": pref,
                                  "items_de_la_lista": len(hijos), "cierre_candidato": ls[c_ult[0]],
                                  "renglones_despues_del_corte": len(ls) - c_ult[0]})
        for h in nodo.get("hijos", []):
            visitar(h, pref)
    for s in est["secciones"]:
        visitar(s, s.get("prefijo"))
    return casos, listas, sin_chunk


def censo_to(e0: Path, to: str, lin: list) -> dict:
    ch = jl(e0 / f"chunks_{to}.json")
    roles = [d["rol"] for d in jl(e0 / f"pies_{to}.json")["paginas_detalle"]]
    est = jl(e0 / f"estructura_{to}.json")
    tab = jl(e0 / f"tablas_{to}.json") if (e0 / f"tablas_{to}.json").exists() else {"tablas": []}
    U: dict[str, list] = defaultdict(list)
    H: dict[str, list] = defaultdict(list)
    T: dict[tuple, int] = Counter()
    for c in ch:
        ps = set(c["paginas"])
        for r in renglones_sin_tabla(c["texto"]):
            if nt(r):
                U[nt(r)].append([ps, c["id"], False])
    vistos = set()
    for c in ch:
        for tr in c["herencia"]:
            if tr["tipo"] != "encabezado" or (tr["unidad_origen"], tr["texto"]) in vistos:
                continue
            vistos.add((tr["unidad_origen"], tr["texto"]))
            for r in tr["texto"].split("\n"):
                if nt(r):
                    H[nt(r)].append([set(tr.get("paginas") or []), tr["unidad_origen"], False])
    con_dueno = 0
    for t in tab["tablas"]:
        if not (t.get("chunk") or t.get("chunk_dueno") or t.get("chunks")):
            continue
        con_dueno += 1
        for s in t["segmentos"]:
            for l in s.get("lineas_e0", []):
                T[(l["pagina"], nt(l["texto"]))] += 1
    desc = Counter((d["pagina"], nt(d["texto"])) for d in est["accounting"]["detalle_descartes"])
    formas = defaultdict(set)
    for d in est["accounting"]["detalle_descartes"]:
        formas[forma(d["texto"])].add(d["pagina"])

    def consumir(dic, k, p, misma):
        for e in dic.get(k, []):
            if not e[2] and ((p in e[0]) if misma else (p not in e[0])):
                e[2] = True
                return e[1]
        return None

    clase: dict[tuple, str] = {}
    for pi, pag in enumerate(lin):
        p = pi + 1
        for li, l in enumerate(pag):
            k = nt(l[3])
            if consumir(U, k, p, True):
                clase[(p, li)] = "en_unidad"
            elif consumir(H, k, p, True):
                clase[(p, li)] = "en_unidad_encabezado"
            elif T[(p, k)] > 0:
                T[(p, k)] -= 1
                clase[(p, li)] = "en_unidad_tabla"
    for pi, pag in enumerate(lin):
        p = pi + 1
        if roles[pi] != "cuerpo":
            continue
        for li, l in enumerate(pag):
            if (p, li) in clase:
                continue
            k = nt(l[3])
            if consumir(U, k, p, False) or consumir(H, k, p, False):
                clase[(p, li)] = "en_unidad_otra_pagina"
    lista, pag_pi = [], []
    cuenta = Counter()
    for pi, pag in enumerate(lin):
        p = pi + 1
        rol = roles[pi]
        if rol in ("portada", "indice") and p != 1:
            pag_pi.append({"pagina": p, "rol": rol, "renglones": len(pag),
                           "texto_corrido": sum(corrido(l) for l in pag),
                           "en_unidad": sum(1 for li in range(len(pag)) if (p, li) in clase),
                           "texto": [l[3] for l in pag]})
        for li, l in enumerate(pag):
            if (p, li) in clase:
                cuenta[clase[(p, li)]] += 1
                continue
            if rol != "cuerpo":
                cuenta["lista_portada_indice" if rol in ("portada", "indice") and p != 1 else f"rol:{rol}"] += 1
                continue
            k = nt(l[3])
            if desc[(p, k)] > 0:
                desc[(p, k)] -= 1
                if len(formas[forma(l[3])] - {p}) > 0:
                    cuenta["encabezado_o_pie_repetido"] += 1
                    continue
                c_ = "encabezado_o_pie_no_repetido"
            else:
                c_ = "sin_unidad_ni_rol"
            cuenta[c_] += 1
            lista.append({"pagina": p, "renglon": li + 1, "clase": c_, "texto": l[3], "texto_corrido": corrido(l)})
    sin_par = sum(1 for v in U.values() for e in v if not e[2])
    return {"renglones_pdf": sum(len(p) for p in lin), "cuenta": dict(sorted(cuenta.items())),
            "censo": len(lista), "lista": lista, "paginas_portada_indice_no_primeras": pag_pi,
            "tablas_con_dueno": con_dueno, "renglones_de_unidades_sin_par_en_el_pdf": sin_par}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0", "manifiesto", "lineas", "regla", "cambio", "pro", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    man = jl(a.manifiesto)
    por_to, casos116, listas116, sin_chunk116 = {}, [], 0, {}
    for t in man["tos"]:
        to = t["id"]
        por_to[to] = censo_to(a.e0, to, jl(a.lineas / f"{to}.json"))
        cs, nl, sc = caso_116(a.e0, to)
        casos116 += cs
        listas116 += nl
        if sc:
            sin_chunk116[to] = sc
    cal, _, _ = caso_116(a.pro, "pro")
    listados = {(to, d["pagina"]) for to, v in por_to.items() for d in v["paginas_portada_indice_no_primeras"]}
    total = Counter()
    for v in por_to.values():
        total.update(v["cuenta"])
    pp = [(to, d) for to, v in por_to.items() for d in v["paginas_portada_indice_no_primeras"]]
    res = {"regla": {"archivo": a.regla.name, "sha256": hashlib.sha256(a.regla.read_bytes()).hexdigest()},
           "cambio_de_s1bis": {"archivo": a.cambio.name, "sha256": hashlib.sha256(a.cambio.read_bytes()).hexdigest()},
           "tos": len(por_to),
           "renglones_pdf": sum(v["renglones_pdf"] for v in por_to.values()),
           "cuenta_total": dict(sorted(total.items())),
           "censo_total": sum(v["censo"] for v in por_to.values()),
           "censo_por_clase": dict(Counter(d["clase"] for v in por_to.values() for d in v["lista"])),
           "censo_por_to": {to: v["censo"] for to, v in por_to.items() if v["censo"]},
           "paginas_con_renglones_en_el_censo": len({(to, d["pagina"]) for to, v in por_to.items()
                                                     for d in v["lista"]}),
           "paginas_portada_indice_no_primeras": {
               "paginas": len(pp), "tos": len({to for to, _ in pp}),
               "renglones": sum(d["renglones"] for _, d in pp),
               "con_texto_corrido": sum(1 for _, d in pp if d["texto_corrido"]),
               "renglones_texto_corrido": sum(d["texto_corrido"] for _, d in pp),
               "con_renglones_en_unidad": sum(1 for _, d in pp if d["en_unidad"]),
               "por_rol": dict(Counter(d["rol"] for _, d in pp))},
           "control_paginas_indice_s0_2": {"esperadas": sorted(map(list, PAGINAS_INDICE_S02)),
                                           "en_la_lista": sorted(map(list, PAGINAS_INDICE_S02 & listados)),
                                           "faltan": sorted(map(list, PAGINAS_INDICE_S02 - listados))},
           "renglones_de_unidades_sin_par_en_el_pdf": sum(v["renglones_de_unidades_sin_par_en_el_pdf"]
                                                         for v in por_to.values()),
           "hallazgo_1_16": {"listas_revisadas": listas116, "casos": len(casos116),
                             "tos": len({c["id"].split("::")[0] for c in casos116}),
                             "por_to": dict(sorted(Counter(c["id"].split("::")[0] for c in casos116).items())),
                             "con_prefijo_de_subdocumento": sum(1 for c in casos116 if c["prefijo"]),
                             "listas_con_items_sin_chunk": {"listas": sum(len(v) for v in sin_chunk116.values()),
                                                            "por_to": sin_chunk116},
                             "calibracion_pro": {"encuentra_pro_1.1.2.7": any(c["id"] == "pro::1.1.2.7" for c in cal),
                                                 "casos_en_pro": [c["id"] for c in cal]},
                             "lista": casos116},
           "por_to": por_to}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("por_to",)} | {
        "hallazgo_1_16": {k: v for k, v in res["hallazgo_1_16"].items() if k != "lista"}},
        ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
