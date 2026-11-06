"""Adjudicador del job: clasifica los deltas y mapea al grafo. SIN RED.

Corre sobre lo que el runner persistió, de modo que una corrida se puede
re-adjudicar cuantas veces haga falta sin volver a pedirle nada al sitio.

SOLO LECTURA sobre la línea base sellada y sobre el grafo vigente. Escribe
únicamente en ../corridas/<fecha>/.

Uso (desde cualquier cwd):
  python3 data/experiment/job_actualizacion/code/adjudicar_deltas.py [--fecha AAAA-MM-DD]

Salidas:
  ../corridas/<fecha>/tabla_deltas.json
  ../corridas/<fecha>/mapeo_grafo.json

El reporte se redacta aparte, con code/reporte_corrida.py, para que se pueda
regenerar sin volver a adjudicar.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_job as L                                              # noqa: E402

KG = L.EXPERIMENT / "reextraccion_v2" / "corpus_v2" / "salida_r1" / "kg.json"
ESPACIOS = re.compile(r"\s+")


def normalizar(txt: str) -> str:
    return ESPACIOS.sub(" ", txt or "").strip()


def diff_por_pagina(viejo: Path, nuevo: Path) -> dict:
    """Páginas del PDF nuevo cuyo texto difiere del viejo.

    Con igual cantidad de páginas, compara una a una. Con distinta cantidad,
    alinea las secuencias de páginas y reporta las que se agregaron o
    reemplazaron. Si no puede leer alguno de los dos, lo declara y no estima.
    """
    try:
        _, tv = L.texto_paginas(viejo, None)
        _, tn = L.texto_paginas(nuevo, None)
    except Exception as exc:                      # noqa: BLE001 — se reporta textual
        return {"paginas_modificadas": None,
                "motivo_sin_diff_fino": f"pdf_anterior_ilegible: "
                                        f"{type(exc).__name__}: {exc}"}
    pv = [normalizar(tv[i]) for i in sorted(tv)]
    pn = [normalizar(tn[i]) for i in sorted(tn)]

    if len(pv) == len(pn):
        cambiadas = [i + 1 for i, (a, b) in enumerate(zip(pv, pn)) if a != b]
        return {"paginas_modificadas": cambiadas,
                "paginas_eliminadas": [],
                "alineacion": "una_a_una",
                "paginas_anterior": len(pv), "paginas_actual": len(pn),
                "motivo_sin_diff_fino": None}

    sm = difflib.SequenceMatcher(None, pv, pn, autojunk=False)
    modificadas, eliminadas = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert"):
            modificadas.extend(range(j1 + 1, j2 + 1))
        if tag in ("replace", "delete"):
            eliminadas.extend(range(i1 + 1, i2 + 1))
    return {"paginas_modificadas": sorted(modificadas),
            "paginas_eliminadas": sorted(eliminadas),
            "alineacion": "por_secuencia",
            "paginas_anterior": len(pv), "paginas_actual": len(pn),
            "motivo_sin_diff_fino": None}


def firma_procedencia(p: dict | None) -> tuple:
    """Lo que el documento DECLARA sobre su propia procedencia, comparable."""
    p = p or {}
    return (p.get("portada_comunicacion"), p.get("texto_ordenado_al"),
            tuple(p.get("pie_comunicaciones") or []))


def muestra_del_cambio(viejo: Path, nuevo: Path, pagina: int,
                       max_frag: int = 2, max_chars: int = 160) -> list[dict]:
    """Fragmentos concretos que aparecen o se reemplazan en una página.

    Sirve para que el reporte diga QUÉ cambió y no solo cuántas páginas. Es una
    muestra, no el diff completo: el artefacto manda.
    """
    try:
        _, tv = L.texto_paginas(viejo, [pagina - 1])
        _, tn = L.texto_paginas(nuevo, [pagina - 1])
    except Exception as exc:                      # noqa: BLE001
        return [{"error": f"{type(exc).__name__}: {exc}"}]
    a, b = normalizar(tv.get(pagina - 1, "")), normalizar(tn.get(pagina - 1, ""))
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal" or len(out) >= max_frag:
            continue
        frag = {"tipo": tag, "pagina": pagina}
        if tag in ("replace", "delete"):
            frag["antes"] = a[i1:i2][:max_chars]
        if tag in ("replace", "insert"):
            frag["ahora"] = b[j1:j2][:max_chars]
        # los fragmentos triviales (un par de caracteres) no informan
        if max(len(frag.get("antes", "")), len(frag.get("ahora", ""))) >= 12:
            out.append(frag)
    return out


def provs(elem: dict) -> list[dict]:
    lista = elem.get("provenances") or []
    if not lista:
        p = elem.get("provenance") or {}
        lista = [p] if p else []
    return [p for p in lista if p]


def cargar_grafo() -> tuple[dict, dict]:
    kg = json.loads(KG.read_text(encoding="utf-8"))
    # archivo -> to, para recuperar los elementos de esqueleto sin 'to'
    arch_a_to: dict[str, str] = {}
    for it in kg["nodes"] + kg["edges"]:
        for p in provs(it):
            if p.get("to") and p.get("archivo"):
                arch_a_to.setdefault(p["archivo"], p["to"])
    return kg, arch_a_to


def tos_de(elem: dict, arch_a_to: dict) -> set[str]:
    out = set()
    for p in provs(elem):
        if p.get("to"):
            out.add(p["to"])
        elif p.get("archivo") and p["archivo"] in arch_a_to:
            out.add(arch_a_to[p["archivo"]])
    return out


def mapear(kg: dict, arch_a_to: dict, to: str, paginas: list[int] | None) -> dict:
    """Nodos y aristas que provienen del TO, opcionalmente restringidos a páginas."""
    sel_p = set(paginas) if paginas else None

    def toca(elem: dict) -> bool:
        for p in provs(elem):
            t = p.get("to") or arch_a_to.get(p.get("archivo") or "")
            if t != to:
                continue
            if sel_p is None:
                return True
            if set(p.get("paginas") or []) & sel_p:
                return True
        return False

    def chunks_de(elem: dict) -> set[str]:
        """Chunks del elemento que corresponden a ESTE TO y, si hay filtro de
        páginas, SOLO a las páginas seleccionadas. Sin el filtro, un nodo que
        toca una página modificada arrastraría también sus chunks de páginas
        intactas, inflando la cuenta."""
        out = set()
        for p in provs(elem):
            t = p.get("to") or arch_a_to.get(p.get("archivo") or "")
            if t != to or not p.get("chunk_id"):
                continue
            if sel_p is not None and not (set(p.get("paginas") or []) & sel_p):
                continue
            out.add(p["chunk_id"])
        return out

    nodos = [n for n in kg["nodes"] if toca(n)]
    aristas = [e for e in kg["edges"] if toca(e)]
    chunks = sorted({c for it in nodos + aristas for c in chunks_de(it)})
    compartidos = [{"nodo": n["id"], "tos": sorted(tos_de(n, arch_a_to))}
                   for n in nodos if len(tos_de(n, arch_a_to)) > 1]
    return {"nodos_afectados": len(nodos), "aristas_afectadas": len(aristas),
            "chunk_ids_afectados": len(chunks),
            "chunk_ids": chunks,
            "compartidos_con_otros_tos": compartidos}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fecha", default=date.today().isoformat())
    args = ap.parse_args(argv)
    dir_c = L.CORRIDAS / args.fecha
    if not (dir_c / "observaciones.json").exists():
        print(f"FRENO: falta {dir_c}/observaciones.json. Corré el runner primero.",
              file=sys.stderr)
        return 2

    base = L.linea_base()
    obs = json.loads((dir_c / "observaciones.json").read_text(encoding="utf-8"))
    filas_idx, duplicadas = L.leer_indice(dir_c / "indice_crudo.json")
    idx = {f["id"]: f for f in filas_idx}

    # --- procedencia de la línea base (se lee del PDF original, no se infiere)
    proc_base: dict[str, dict] = {}
    for ident, b in base.items():
        proc_base[ident] = L.procedencia(b["pdf"]) if b["pdf"].exists() else \
            {"limite_declarado": "pdf_de_linea_base_ausente"}

    # --- tabla de deltas --------------------------------------------------
    tabla: dict[str, dict] = {}
    for ident in sorted(set(idx) | set(base)):
        b, o, e = base.get(ident), obs.get(ident), idx.get(ident)
        fila = {
            "id": ident,
            # El grafo y el manifiesto de desarrollo indexan por OTRO id que el
            # índice: ver la nota de identidad en lib_job.linea_base().
            "id_interno": b["id_interno"] if b else ident,
            "grupo": b["grupo"] if b else "alta_posterior",
            "categoria": (e or b or {}).get("categoria", "desconocida"),
            "titulo_indice": e["titulo"] if e else None,
            "archivo_indice": e["archivo"] if e else None,
            "url": (e or b)["url"],
            "url_linea_base": b["url"] if b else None,
            "sha_anterior": b["sha256"] if b else None,
            "sha_actual": (o or {}).get("sha256"),
            "bytes_anterior": int(b["bytes"]) if b and b.get("bytes") else None,
            "bytes_actual": (o or {}).get("bytes"),
            "paginas_anterior": int(b["paginas"]) if b and b.get("paginas") else None,
            "paginas_actual": (o or {}).get("paginas"),
            "visto_primera_vez": b["adquisicion"] if b else args.fecha,
            "visto_ultima_vez": args.fecha if e else (b["adquisicion"] if b else None),
            "corridas_observado": 1 if e else 0,
            "causa_no_verificable": None,
            "presunta_renombrada_de": None,
            "procedencia_anterior": proc_base.get(ident),
            "procedencia_actual": (o or {}).get("procedencia"),
            "cabeceras_http": (o or {}).get("cabeceras"),
            "paginas_modificadas": None,
            "motivo_sin_diff_fino": None,
            # ¿el documento movió su propia declaración de procedencia?
            # Un sha distinto con procedencia quieta es un cambio que el
            # documento no anuncia: la señal de cambio es el sha, no lo que
            # el documento dice de sí mismo.
            "procedencia_movio": None,
            "muestra_del_cambio": None,
            "mapeo_grafo": None,
        }
        if e is None:
            fila["clasificacion"] = "desaparecido_del_indice"
        elif o is None or o.get("estado") != "descargado":
            fila["clasificacion"] = "no_verificable"
            fila["causa_no_verificable"] = (o or {}).get("error", "sin observación")
        elif b is None:
            fila["clasificacion"] = "nuevo_en_indice"
        elif fila["sha_actual"] == fila["sha_anterior"]:
            fila["clasificacion"] = "sin_cambio"
        else:
            fila["clasificacion"] = "contenido_modificado"
        tabla[ident] = fila

    # anotación de presunto renombre: título exacto compartido entre un alta y
    # una baja de la MISMA corrida. Es anotación, no clasificación: no fusiona.
    bajas = {f["titulo_indice"] or base[i]["titulo"]: i
             for i, f in tabla.items() if f["clasificacion"] == "desaparecido_del_indice"}
    for ident, f in tabla.items():
        if f["clasificacion"] == "nuevo_en_indice" and f["titulo_indice"] in bajas:
            f["presunta_renombrada_de"] = bajas[f["titulo_indice"]]

    # --- diff fino sobre los modificados ----------------------------------
    for ident, f in tabla.items():
        if f["clasificacion"] != "contenido_modificado":
            continue
        f["procedencia_movio"] = (firma_procedencia(f["procedencia_anterior"])
                                  != firma_procedencia(f["procedencia_actual"]))
        viejo, nuevo = base[ident]["pdf"], dir_c / "pdfs" / f"{ident}.pdf"
        if not viejo.exists():
            f["motivo_sin_diff_fino"] = "pdf_anterior_ausente"
            continue
        f |= diff_por_pagina(viejo, nuevo)
        pm = f.get("paginas_modificadas") or []
        if pm:
            f["muestra_del_cambio"] = muestra_del_cambio(viejo, nuevo, pm[0])

    # --- mapeo al grafo ---------------------------------------------------
    kg, arch_a_to = cargar_grafo()
    cubiertos = {p.get("to") for it in kg["nodes"] + kg["edges"]
                 for p in provs(it) if p.get("to")}
    mapeo = {"grafo": str(KG.relative_to(L.REPO)),
             "grafo_sha256": hashlib.sha256(KG.read_bytes()).hexdigest(),
             "tos_cubiertos": sorted(cubiertos), "por_to": {}}
    for ident, f in tabla.items():
        if f["clasificacion"] != "contenido_modificado":
            continue
        interno = f["id_interno"]
        if interno not in cubiertos:
            f["mapeo_grafo"] = {"fuera_de_alcance":
                                "el grafo vigente no cubre este TO"}
            mapeo["por_to"][ident] = f["mapeo_grafo"]
            continue
        grueso = mapear(kg, arch_a_to, interno, None)
        fino = (mapear(kg, arch_a_to, interno, f["paginas_modificadas"])
                if f.get("paginas_modificadas") else None)
        det = {"id_en_el_grafo": interno,
               "to_entero": grueso, "restringido_a_paginas_modificadas": fino,
               "paginas_modificadas": f.get("paginas_modificadas"),
               "motivo_sin_diff_fino": f.get("motivo_sin_diff_fino")}
        f["mapeo_grafo"] = {
            "grafo": mapeo["grafo"],
            "nodos_afectados": grueso["nodos_afectados"],
            "aristas_afectadas": grueso["aristas_afectadas"],
            "nodos_afectados_por_pagina": fino["nodos_afectados"] if fino else None,
            "aristas_afectadas_por_pagina": fino["aristas_afectadas"] if fino else None,
            "chunk_ids_afectados": (fino or grueso)["chunk_ids_afectados"],
            "compartidos_con_otros_tos": (fino or grueso)["compartidos_con_otros_tos"],
            "fuera_de_alcance": None,
        }
        mapeo["por_to"][ident] = det

    # --- agregados desglosados POR CORPUS ---------------------------------
    def resumen(ids: list[str]) -> dict:
        c = Counter(tabla[i]["clasificacion"] for i in ids)
        return {"total": len(ids), **{k: c.get(k, 0) for k in
                ("sin_cambio", "contenido_modificado", "nuevo_en_indice",
                 "desaparecido_del_indice", "no_verificable")}}

    por_grupo = {g: resumen([i for i, f in tabla.items() if f["grupo"] == g])
                 for g in ("desarrollo_5", "inventariado_152", "alta_posterior")}

    salida = {
        "fecha_corrida": args.fecha,
        "ventanas_por_corpus": {
            g: {"adquisicion": L.ADQUISICION[g]["fecha"],
                "fuente_de_la_fecha": L.ADQUISICION[g]["fuente"]}
            for g in L.ADQUISICION},
        "indice_de_hoy": {"entradas": sum(len(json.loads(
            (dir_c / "indice_crudo.json").read_text(encoding="utf-8"))[c])
            for _, c in L.CATEGORIAS),
            "urls_unicas": len(idx), "duplicadas": duplicadas},
        "delta_conjunto_desarrollo": {
            "resumen": por_grupo["desarrollo_5"],
            "por_to": {i: {k: tabla[i][k] for k in
                           ("id_interno", "clasificacion",
                            "sha_anterior", "sha_actual",
                            "bytes_anterior", "bytes_actual", "paginas_anterior",
                            "paginas_actual", "procedencia_anterior",
                            "procedencia_actual", "paginas_modificadas",
                            "motivo_sin_diff_fino", "mapeo_grafo")}
                       for i, f in tabla.items() if f["grupo"] == "desarrollo_5"}},
        "delta_inicial_vs_descarga_original": {
            "desglosado_por_corpus": por_grupo,
            "advertencia": "Las ventanas son distintas por corpus; un agregado "
                           "único escondería de qué lado viene el material.",
            "ids_por_clase": {
                k: sorted(i for i, f in tabla.items() if f["clasificacion"] == k)
                for k in ("contenido_modificado", "nuevo_en_indice",
                          "desaparecido_del_indice", "no_verificable")},
            "modificados_por_movimiento_de_procedencia": {
                "con_procedencia_movida": sorted(
                    i for i, f in tabla.items() if f["procedencia_movio"] is True),
                "con_procedencia_quieta": sorted(
                    i for i, f in tabla.items() if f["procedencia_movio"] is False),
                "lectura": "Un sha distinto con procedencia declarada quieta es "
                           "un cambio que el documento no anuncia. Confirma que "
                           "la señal de cambio tiene que ser el sha del "
                           "contenido, y no lo que el documento declara de sí "
                           "mismo ni la cabecera HTTP."}},
        "tabla": tabla,
    }
    (dir_c / "tabla_deltas.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    (dir_c / "mapeo_grafo.json").write_text(
        json.dumps(mapeo, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({k: v for k, v in salida.items() if k != "tabla"},
                     ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
