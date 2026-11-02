"""
r1_provenance.py — B1.4: provenance rica. A cada provenance de nodo y
arista (y al campo `provenance` principal) se le AGREGAN, sin quitar ningún
campo existente:
  chunk_id   id del chunk de E0 (salida_enm01) cuyo texto contiene el
             segmento: punto_propio → "<to>::<punto>"; bloque_<rol> →
             "<to>::<punto>::<rol>"; herencia_<tipo> → el chunk emisor
             (el hijo que extrajo el elemento desde su cadena de herencia;
             si varios chunks lo emitieron, el primero en orden documental,
             con la lista completa en `chunks_emisores`).
  paginas    páginas del PDF del segmento (chunk.paginas; para herencia,
             las páginas del tramo heredado).
  ancestros  cadena de herencia estructural del chunk (unidad_origen de
             chunk.herencia, de la sección al contenedor inmediato).
Provenances de esqueleto (rol_documental=esqueleto) y de referencia cruzada
(= del nodo origen) reciben chunk_id=None / paginas=[] / ancestros=[] y
[rol esqueleto] respectivamente; se reportan aparte.

Verificación: todo nodo y arista con los tres campos; ancestros
consistentes con estructura_<to>.json (cada ancestro es unidad del mapa y
es prefijo estructural del punto: 'S3' ⊂ '3.1' ⊂ '3.1.3').
"""

from __future__ import annotations

import r1_comun as C


def _indice_chunks(to: str) -> dict[str, dict]:
    return {c["id"]: c for c in C.cargar_chunks_enm01(to)}


def _emisores(por_to: dict) -> dict[tuple[str, str, str], list[str]]:
    """(to, punto, rol_documental) → chunk_ids emisores en orden documental,
    desde los registros E1 ensamblados (aceptados + cola flaggeada)."""
    out: dict[tuple[str, str, str], list[str]] = {}
    for to, d in por_to.items():
        chunks = C.cargar_chunks_enm01(to)
        orden = {c["id"]: i for i, c in enumerate(chunks)}
        regs = d.get("registros") or C.cargar_extracciones_finales(to)
        regs = [r for r in regs if r.get("validacion")]
        regs.sort(key=lambda r: orden.get(r["chunk_id"], 10**9))
        for r in regs:
            val = r["validacion"]
            for coll in ("entidades", "relaciones"):
                for e in val.get(coll, []):
                    p = e.get("provenance") or {}
                    k = (p.get("to"), p.get("punto"), p.get("rol_documental"))
                    lst = out.setdefault(k, [])
                    if r["chunk_id"] not in lst:
                        lst.append(r["chunk_id"])
    return out


def enriquecer(kg: dict, por_to: dict) -> dict:
    chunks = {to: _indice_chunks(to) for to in C.TOS_ORDEN}
    emisores = _emisores(por_to)
    unidades = {}
    import r1_referencias as R
    for to in C.TOS_ORDEN:
        unidades[to] = R.unidades_e0(to)

    stats = {"provenances": 0, "extraccion": 0, "esqueleto": 0, "sin_chunk": 0,
             "herencia_multi_emisor": 0}
    inconsistencias: list[dict] = []

    def enriquecer_prov(p: dict) -> None:
        stats["provenances"] += 1
        rol = p.get("rol_documental")
        to = p.get("to")
        if rol == "esqueleto" or to not in C.TOS_ORDEN:
            p.setdefault("chunk_id", None)
            p.setdefault("paginas", [])
            p.setdefault("ancestros", [])
            stats["esqueleto"] += 1
            return
        punto = p["punto"]
        cid = None
        if rol == "punto_propio":
            cid = f"{to}::{punto}"
        elif rol.startswith("bloque_"):
            cid = f"{to}::{punto}::{rol[len('bloque_'):]}"
        else:
            em = emisores.get((to, punto, rol), [])
            if em:
                cid = em[0]
                if len(em) > 1:
                    p["chunks_emisores"] = list(em)
                    stats["herencia_multi_emisor"] += 1
        ch = chunks[to].get(cid) if cid else None
        if ch is None:
            stats["sin_chunk"] += 1
            inconsistencias.append({"prov": dict(p), "motivo": "chunk no encontrado"})
            p["chunk_id"] = cid
            p["paginas"] = []
            p["ancestros"] = []
            return
        ancestros = []
        for h in ch.get("herencia", []):
            if h["unidad_origen"] not in ancestros:
                ancestros.append(h["unidad_origen"])
        if rol.startswith("herencia_"):
            tramos = [h for h in ch.get("herencia", []) if h["unidad_origen"] == punto]
            paginas = sorted({pg for h in tramos for pg in h.get("paginas", [])})
            # ancestros del tramo heredado = los que lo preceden en la cadena
            idx = ancestros.index(punto) if punto in ancestros else len(ancestros)
            ancestros_p = ancestros[:idx]
        else:
            paginas = list(ch.get("paginas", []))
            # un mini-chunk hereda el encabezado de SU propia unidad: no es ancestro
            ancestros_p = [a for a in ancestros if a != punto]
        p["chunk_id"] = cid
        p["paginas"] = paginas
        p["ancestros"] = ancestros_p
        stats["extraccion"] += 1
        # consistencia con estructura
        for a in ancestros_p:
            if a not in unidades[to]:
                inconsistencias.append({"prov": dict(p), "motivo": f"ancestro {a} no está en E0"})
        cadena = ancestros_p + [punto]
        for a, b in zip(cadena, cadena[1:]):
            if not _es_prefijo_estructural(a, b):
                inconsistencias.append({"prov": dict(p), "motivo": f"{a} no es prefijo de {b}"})

    for n in kg["nodes"]:
        enriquecer_prov(n["provenance"])
        for p in n.get("provenances", []):
            enriquecer_prov(p)
    for e in kg["edges"]:
        enriquecer_prov(e["provenance"])
        for p in e.get("provenances", []):
            enriquecer_prov(p)

    faltan_n = [n["id"] for n in kg["nodes"] if not all(
        "chunk_id" in p and "paginas" in p and "ancestros" in p for p in n["provenances"])]
    faltan_e = [(e["source"], e["relation"], e["target"]) for e in kg["edges"] if not all(
        "chunk_id" in p and "paginas" in p and "ancestros" in p for p in e["provenances"])]
    con_chunk_n = sum(1 for n in kg["nodes"] if any(p.get("chunk_id") for p in n["provenances"]))
    con_chunk_e = sum(1 for e in kg["edges"] if any(p.get("chunk_id") for p in e["provenances"]))
    resumen = {
        **stats,
        "nodos_sin_campos": len(faltan_n), "aristas_sin_campos": len(faltan_e),
        "nodos_con_chunk_id": con_chunk_n, "nodos_total": len(kg["nodes"]),
        "aristas_con_chunk_id": con_chunk_e, "aristas_total": len(kg["edges"]),
        "inconsistencias_estructura": len(inconsistencias),
    }
    return {"resumen": resumen, "inconsistencias": inconsistencias[:200]}


def _es_prefijo_estructural(a: str, b: str) -> bool:
    if a.startswith("S"):
        return b.startswith("S") is False and b.split(".")[0] == a[1:]
    return b.startswith(a + ".")
