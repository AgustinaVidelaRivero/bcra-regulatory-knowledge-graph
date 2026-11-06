"""Sonda de procedencia documental sobre el corpus YA descargado (sin red).

Pregunta de diseno de la fase 1 de la unidad: ¿el sitio expone de qué
comunicación proviene cada versión de un Texto Ordenado, o hay que declarar el
límite? La sonda la responde con medición, no con supuesto: recorre los 157 TOs
ya en disco y cuenta cuántos publican la procedencia y bajo qué forma.

Dos formas observadas en el propio corpus, ambas impresas por la fuente:
  P (portada) — «-Última comunicación incorporada: "A" NNNN-» y
                «Texto ordenado al DD/MM/AA» en la carátula.
  F (pie)     — «Versión: Na. COMUNICACIÓN "A" NNNN» al pie de la página,
                acompanado de "Vigencia: DD/MM/AAAA". Esta forma es por PÁGINA,
                no por documento: es la que habilita el mapeo a nivel de unidad.

Solo lectura. No toca red. Escribe únicamente en el directorio de la unidad.

Entradas (solo lectura):
  data/experiment/escalado_prep/descarga_log.json          (los 152 ids)
  data/experiment/escalado_prep/pdfs/<id>.pdf              (152)
  data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json (los 5)
  data/experiment/subset/<archivo>.pdf                     (5)

Salida:
  ../sonda_procedencia.json

Uso (desde cualquier cwd):
  python3 data/experiment/job_actualizacion/code/sonda_procedencia.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
UNIDAD = AQUI.parent
EXPERIMENT = UNIDAD.parent
REPO = EXPERIMENT.parent.parent
PREP = EXPERIMENT / "escalado_prep"

PAGS_CABECERA = 3      # páginas iniciales que se leen enteras
PAGS_MUESTRA = 5       # páginas repartidas por el cuerpo, para medir el pie

RE_PORTADA = re.compile(
    r"[Úú]ltima\s+comunicaci[óo]n\s+incorporada\s*:\s*[\"“”']?\s*([A-Z])\s*"
    r"[\"“”']?\s*(\d{3,5})", re.IGNORECASE)
RE_TEXTO_ORDENADO = re.compile(
    r"[Tt]exto\s+ordenado\s+al\s+(\d{1,2}/\d{1,2}/\d{2,4})")
RE_PIE = re.compile(
    r"Versi[óo]n\s*:\s*(\d+)\s*[ºa°]?\s*\.?\s*COMUNICACI[ÓO]N\s*[\"“”']?\s*"
    r"([A-Z])\s*[\"“”']?\s*(\d{3,5})", re.IGNORECASE)
# El número de comunicación a veces sale con glifos no mapeados: la portada
# está impresa pero sus dígitos no se extraen. Se cuenta aparte, no como falta
# de la fuente.
RE_PORTADA_ILEGIBLE = re.compile(
    r"[Úú]ltima\s+comunicaci[óo]n\s+incorporada", re.IGNORECASE)
RE_CID = re.compile(r"\(cid:\d+\)")


def paginas_a_leer(total: int) -> list[int]:
    """Índices 0-based: las primeras PAGS_CABECERA más una muestra repartida."""
    cab = list(range(min(PAGS_CABECERA, total)))
    if total <= PAGS_CABECERA:
        return cab
    paso = max(1, total // (PAGS_MUESTRA + 1))
    muestra = [min(total - 1, paso * k) for k in range(1, PAGS_MUESTRA + 1)]
    return sorted(set(cab) | set(muestra))


def sondear(pdf: Path) -> dict:
    import pdfplumber
    try:
        with pdfplumber.open(str(pdf)) as doc:
            total = len(doc.pages)
            idxs = paginas_a_leer(total)
            textos = {i: (doc.pages[i].extract_text() or "") for i in idxs}
    except Exception as exc:                      # noqa: BLE001 — se reporta textual
        return {"error": f"{type(exc).__name__}: {exc}"}

    cabecera = "\n".join(textos[i] for i in sorted(textos) if i < PAGS_CABECERA)
    mp = RE_PORTADA.search(cabecera)
    mt = RE_TEXTO_ORDENADO.search(cabecera)

    pies = {}
    for i in sorted(textos):
        m = RE_PIE.search(textos[i])
        if m:
            pies[i + 1] = {"version": m.group(1),
                           "letra": m.group(2).upper(),
                           "numero": m.group(3)}

    ilegible = bool(RE_PORTADA_ILEGIBLE.search(cabecera)) and not mp \
        and bool(RE_CID.search(cabecera))

    return {
        "paginas": total,
        "paginas_leidas": len(textos),
        "portada_comunicacion": f"{mp.group(1).upper()} {mp.group(2)}" if mp else None,
        "portada_ilegible_por_glifos": ilegible,
        "texto_ordenado_al": mt.group(1) if mt else None,
        "pie_paginas_con_senal": len(pies),
        "pie_comunicaciones": sorted({f"{v['letra']} {v['numero']}"
                                      for v in pies.values()}),
        "pie_por_pagina": pies,
    }


def objetivo() -> list[tuple[str, str, Path]]:
    """(grupo, id, ruta) para los 157: 152 inventariados + 5 de desarrollo."""
    filas: list[tuple[str, str, Path]] = []
    log = json.loads((PREP / "descarga_log.json").read_text(encoding="utf-8"))
    for ident in sorted(log):
        filas.append(("inventariado_152", ident, PREP / "pdfs" / f"{ident}.pdf"))
    man = json.loads(
        (EXPERIMENT / "reextraccion_v2" / "manifiestos" / "desarrollo_5tos.json")
        .read_text(encoding="utf-8"))
    for to in man["tos"]:
        filas.append(("desarrollo_5", to["id"], REPO / to["pdf"]))
    return filas


def main() -> int:
    filas = objetivo()
    res, faltantes = {}, []
    for grupo, ident, ruta in filas:
        if not ruta.exists():
            faltantes.append({"grupo": grupo, "id": ident, "ruta": str(ruta)})
            continue
        r = sondear(ruta)
        r["grupo"] = grupo
        res[ident] = r
        print(f"{ident:28s} portada={str(r.get('portada_comunicacion')):10s} "
              f"pie={r.get('pie_paginas_con_senal')}/{r.get('paginas_leidas')}",
              flush=True)

    def ids(cond):
        return sorted(i for i, r in res.items() if cond(r))

    con_portada = ids(lambda r: r.get("portada_comunicacion"))
    con_pie = ids(lambda r: r.get("pie_paginas_con_senal"))
    con_alguna = sorted(set(con_portada) | set(con_pie))
    sin_ninguna = sorted(set(res) - set(con_alguna))
    ilegibles = ids(lambda r: r.get("portada_ilegible_por_glifos"))
    pags_leidas = sum(r.get("paginas_leidas", 0) for r in res.values())
    pags_con_pie = sum(r.get("pie_paginas_con_senal", 0) for r in res.values())

    salida = {
        "objetivo": len(filas),
        "leidos": len(res),
        "faltantes": faltantes,
        "errores_de_lectura": ids(lambda r: r.get("error")),
        "parametros": {"paginas_cabecera": PAGS_CABECERA,
                       "paginas_muestra_cuerpo": PAGS_MUESTRA},
        "cobertura_por_to": {
            "con_portada": len(con_portada),
            "con_pie": len(con_pie),
            "con_alguna_forma": len(con_alguna),
            "solo_portada": len(set(con_portada) - set(con_pie)),
            "solo_pie": len(set(con_pie) - set(con_portada)),
            "con_ambas": len(set(con_pie) & set(con_portada)),
            "sin_ninguna": len(sin_ninguna),
            "portada_ilegible_por_glifos": len(ilegibles),
        },
        "cobertura_por_pagina_muestreada": {
            "paginas_leidas": pags_leidas,
            "paginas_con_pie": pags_con_pie,
        },
        "sin_ninguna_ids": sin_ninguna,
        "portada_ilegible_ids": ilegibles,
        "por_grupo": {
            g: {"total": sum(1 for r in res.values() if r["grupo"] == g),
                "con_alguna_forma": sum(1 for i in con_alguna if res[i]["grupo"] == g)}
            for g in ("inventariado_152", "desarrollo_5")},
        "por_to": dict(sorted(res.items())),
    }
    (UNIDAD / "sonda_procedencia.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n" + json.dumps({k: v for k, v in salida.items()
                             if k not in ("por_to", "sin_ninguna_ids")},
                            ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
