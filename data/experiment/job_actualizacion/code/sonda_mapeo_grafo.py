"""Sonda del mapeo delta -> procedencia -> partes afectadas del grafo (sin red).

Pregunta de diseno de la fase 1: dado un Texto Ordenado con contenido
modificado, ¿el grafo permite identificar qué nodos y aristas provienen de ese
documento, y con qué granularidad? La sonda lo mide sobre el grafo vigente en
lugar de suponerlo, y deja explícito qué porción NO es atribuible.

Solo lectura sobre el grafo vigente (zona sellada). Escribe únicamente en el
directorio de la unidad.

Entrada (solo lectura):
  data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json   (grafo vigente)

Salida:
  ../sonda_mapeo_grafo.json

Uso (desde cualquier cwd):
  python3 data/experiment/job_actualizacion/code/sonda_mapeo_grafo.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
UNIDAD = AQUI.parent
EXPERIMENT = UNIDAD.parent
KG = EXPERIMENT / "reextraccion_v2" / "corpus_v2" / "salida_r1" / "kg.json"


def provs(elem: dict) -> list[dict]:
    """Todas las procedencias del elemento: la principal y las acumuladas."""
    lista = elem.get("provenances") or []
    if not lista:
        p = elem.get("provenance") or {}
        lista = [p] if p else []
    return [p for p in lista if p]


def medir(elems: list[dict], etiqueta: str) -> dict:
    con_to = con_chunk = con_pag = 0
    sin_to_con_archivo = 0
    sin_to_sin_archivo: Counter = Counter()
    multi = 0
    por_to: Counter = Counter()
    archivo_a_to: defaultdict[str, set] = defaultdict(set)
    paginas_por_to: defaultdict[str, set] = defaultdict(set)

    for e in elems:
        ps = provs(e)
        p0 = ps[0] if ps else {}
        if len(ps) > 1:
            multi += 1
        if p0.get("to"):
            con_to += 1
        elif p0.get("archivo"):
            if str(p0["archivo"]).lower().endswith(".pdf"):
                sin_to_con_archivo += 1
            else:
                sin_to_sin_archivo[p0["archivo"]] += 1
        else:
            sin_to_sin_archivo["(sin archivo)"] += 1
        if p0.get("chunk_id"):
            con_chunk += 1
        if p0.get("paginas"):
            con_pag += 1
        for p in ps:
            if p.get("to"):
                por_to[p["to"]] += 1
                if p.get("archivo"):
                    archivo_a_to[p["archivo"]].add(p["to"])
                for n in p.get("paginas") or []:
                    paginas_por_to[p["to"]].add(n)

    ambiguos = {a: sorted(t) for a, t in archivo_a_to.items() if len(t) > 1}
    return {
        "total": len(elems),
        "con_to": con_to,
        "sin_to_recuperable_por_archivo": sin_to_con_archivo,
        "no_atribuible_a_ningun_to": dict(sin_to_sin_archivo),
        "con_chunk_id": con_chunk,
        "con_paginas": con_pag,
        "con_mas_de_una_procedencia": multi,
        "por_to": dict(sorted(por_to.items())),
        "paginas_distintas_por_to": {k: len(v) for k, v in sorted(paginas_por_to.items())},
        "archivo_a_to_ambiguo": ambiguos,
        "etiqueta": etiqueta,
    }


def main() -> int:
    kg = json.loads(KG.read_text(encoding="utf-8"))
    nodos, aristas = kg["nodes"], kg["edges"]
    m_nod = medir(nodos, "nodos")
    m_ari = medir(aristas, "aristas")

    # Simulación del mapeo: si cambia el TO X entero, ¿qué se toca?
    def afectados_por_to(to: str) -> dict:
        n = sum(1 for e in nodos if any(p.get("to") == to for p in provs(e)))
        a = sum(1 for e in aristas if any(p.get("to") == to for p in provs(e)))
        return {"nodos": n, "aristas": a}

    tos = sorted(set(m_nod["por_to"]) | set(m_ari["por_to"]))
    simulacion_to = {t: afectados_por_to(t) for t in tos}

    # Granularidad de página: si cambia UNA página del TO, ¿cuántos elementos
    # quedan señalados? Se reporta el promedio y el máximo por TO.
    grano = {}
    for t in tos:
        por_pag_n: Counter = Counter()
        por_pag_a: Counter = Counter()
        for e in nodos:
            for p in provs(e):
                if p.get("to") == t:
                    for n in p.get("paginas") or []:
                        por_pag_n[n] += 1
        for e in aristas:
            for p in provs(e):
                if p.get("to") == t:
                    for n in p.get("paginas") or []:
                        por_pag_a[n] += 1
        tot_n = sum(por_pag_n.values()) or 1
        grano[t] = {
            "paginas_con_nodos": len(por_pag_n),
            "nodos_por_pagina_promedio": round(tot_n / max(1, len(por_pag_n)), 1),
            "nodos_por_pagina_maximo": max(por_pag_n.values()) if por_pag_n else 0,
            "aristas_por_pagina_maximo": max(por_pag_a.values()) if por_pag_a else 0,
        }

    # Elementos anclados en MÁS DE UN TO: un cambio en uno de ellos toca
    # material que también responde a otro documento, así que no se pueden
    # reemplazar a ciegas por TO. Se cuentan y se listan.
    def compartidos(elems: list[dict], clave) -> dict:
        dist: Counter = Counter()
        lista = []
        for e in elems:
            ts = {p["to"] for p in provs(e) if p.get("to")}
            dist[len(ts)] += 1
            if len(ts) > 1:
                lista.append({"elemento": clave(e), "tos": sorted(ts)})
        return {"tos_distintos_por_elemento": dict(sorted(dist.items())),
                "compartidos": len(lista), "detalle": lista}

    comp_nod = compartidos(nodos, lambda e: e.get("id"))
    comp_ari = compartidos(aristas, lambda e: f"{e['source']} -[{e['relation']}]-> {e['target']}")

    salida = {
        "grafo": str(KG.relative_to(EXPERIMENT.parent.parent)),
        "compartidos_entre_tos_nodos": comp_nod,
        "compartidos_entre_tos_aristas": comp_ari,
        "nodos": len(nodos),
        "aristas": len(aristas),
        "cobertura_nodos": m_nod,
        "cobertura_aristas": m_ari,
        "tos_cubiertos_por_el_grafo": tos,
        "afectados_si_cambia_el_to_entero": simulacion_to,
        "granularidad_por_pagina": grano,
    }
    (UNIDAD / "sonda_mapeo_grafo.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
