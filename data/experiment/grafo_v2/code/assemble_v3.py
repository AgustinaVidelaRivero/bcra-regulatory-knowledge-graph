"""Re-ensamblado v3 del grafo v2 — corrige las pérdidas del ensamblado v2.

No re-extrae nada: consume el MISMO caché de extracción (`cache_v2/full`, 508
resultados, uno por chunk, bijección verificada 508↔508). Lo único que cambia
acá es qué se hace con lo ya extraído, de modo que todo el delta contra
`grafo_v2/kg.json` sea atribuible al ensamblado y a nada más.

Pérdidas que corrige (medidas sobre el ensamblado v2 vigente):

1. **Chunks de articulado descartados por colisión de `chunk_id`.**
   `chunk_id = {doc}::{numbering}` no identifica un pasaje: la misma numeración
   aparece en el índice, en el articulado y en la tabla "norma de origen". El
   ensamblado v2 agrupaba por ese id y se quedaba con "el que más entidades
   extrajo", heurística que premia a la tabla de correspondencias (una lista de
   códigos de Comunicación) por sobre el articulado (prosa normativa).
   Medido: 53 chunks de articulado — 95.226 chars, 429 entidades ya extraídas y
   pagadas — no aportaban un solo nodo.
   Fix: el driver es `chunks_all.json`, no el glob del caché. Cada chunk se
   resuelve a su archivo de caché por hash y entra por separado, con su rol
   documental (`chunk_roles.py`). No hay desempate: dejó de haber empate.

2. **Colapso de `Operacion` por usar un campo categórico como clave de dedup.**
   El slug de `Operacion` era `properties.tipo`, que el extractor llena con
   valores de categoría. 56 operaciones distintas caían en
   `Operacion_presentacion_informativa` y 30 en `Operacion_calculo`: un nodo con
   el label de la primera y las aristas de todas.
   Fix: clave por el label del hecho.

3. **Colisión de prefijo en Restriccion/Obligacion/Excepcion.**
   El slug truncaba la descripción a 80 chars, así que dos hechos distintos con
   los mismos primeros 80 chars normalizados se fundían en uno.
   Fix: el id sigue siendo legible (80 chars) pero lleva sufijo de hash del slug
   COMPLETO. Descripciones equivalentes siguen mergeando; distintas ya no.

4. **Evidencia descartada en cada merge.**
   Al mergear un nodo repetido se conservaba solo la provenance del primero, y
   una arista repetida vista desde otro pasaje se descartaba entera (1.227 en el
   ensamblado v2). Fix: se acumula `provenances` (lista completa). `provenance`
   sigue siendo el primer avistaje, así que todo consumidor actual —loader de la
   Fase 2.3, harness, app— lee exactamente lo mismo que hoy.
   NOTA: para explotar `provenances` hay que registrar un `adapter_key` en
   `app/main.py`; sin eso el grafo se lee igual que el v2.

5. **Reporte que informaba 100% de cobertura teniendo 20% del corpus afuera.**
   `coverage_by_doc` se calculaba sobre los chunks sobrevivientes al desempate,
   no sobre los chunks reales. Fix: la cobertura se mide contra `chunks_all` y
   hay una aserción dura — si un chunk que aportó entidades no deja ningún nodo
   ni arista, el reporte lo lista y el proceso termina con código 2.

Lo que este re-ensamblado NO puede arreglar (queda congelado en el texto y la
`location` con que los chunks se enviaron a la API) está documentado en
`docs/backlog_reextraccion.md`: es la lista de defectos que ameritan re-extraer.

Uso:
    python assemble_v3.py                  # cuerpo + tabla_norma_origen (default)
    python assemble_v3.py --roles cuerpo   # solo articulado
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import chunk_roles as CR
import chunker as CH
from assemble import DOC_MATERIA, build_skeleton
from extract import PROMPT_HASH
from schema import (
    ENTITY_TYPES,
    PREDICATES,
    RELACIONES_ESQUELETO,
    SUJETO_PREDICATES,
    is_valid_triple,
)


RUN_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = RUN_DIR / "code" / "cache_v2"
OUT_DIR = RUN_DIR / "reensamblado_v3"

# Roles documentales que aportan nodos. El índice queda afuera por defecto: es
# la lista de títulos del propio articulado, no agrega ningún hecho. La tabla de
# norma de origen SÍ entra — es contenido real del TO (qué Comunicación originó
# cada punto); lo que estaba mal no era que existiera, era que desplazaba al
# articulado.
ROLES_DEFAULT = (CR.ROL_CUERPO, CR.ROL_TABLA)


def slugify_full(s: str) -> str:
    """Slug normalizado SIN truncar (lowercase, sin acentos, ascii)."""
    if not s:
        return "empty"
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s or "empty"


def _id_estable(full_slug: str, max_len: int = 80) -> str:
    """Id legible pero sin colisión de prefijo: 80 chars + hash del slug entero.

    El hash se calcula sobre el slug normalizado completo, no sobre el texto
    crudo, para que diferencias irrelevantes (puntuación final, acentos, espacios
    dobles) sigan mergeando como antes.
    """
    return f"{full_slug[:max_len]}_{hashlib.sha1(full_slug.encode('utf-8')).hexdigest()[:6]}"


def entity_slug_v3(e: dict[str, Any]) -> str:
    t = e["type"]
    p = e.get("properties") or {}
    label = e.get("label", "") or ""
    if t == "Comunicacion":
        return slugify_full(str(p.get("codigo") or p.get("numero") or label))
    if t == "TextoOrdenado":
        return slugify_full(str(p.get("archivo") or p.get("_doc") or p.get("materia") or label))
    if t == "Operacion":
        # v3: por label. `properties.tipo` es categórico y funde operaciones
        # distintas (ver docstring, pérdida 2).
        return _id_estable(slugify_full(label or str(p.get("tipo") or "")))
    if t in ("Restriccion", "Obligacion", "Excepcion"):
        return _id_estable(slugify_full(str(p.get("descripcion") or label)))
    return _id_estable(slugify_full(label))


def cargar_chunks_con_rol() -> list[dict[str, Any]]:
    """chunks_all.json + rol documental + path del resultado de extracción."""
    chunks = json.loads((CACHE_DIR / "chunks_all.json").read_text(encoding="utf-8"))
    roles = CR.roles_para_chunks_all(chunks, CH.SUBSET)
    cache_root = CACHE_DIR / "full"
    out: list[dict[str, Any]] = []
    faltantes: list[str] = []
    for c in chunks:
        c = dict(c)
        c["rol"] = roles[CR.clave_chunk(c["chunk_id"], c["text"])]
        h = hashlib.sha1(
            f"{c['chunk_id']}|{c['text']}|{PROMPT_HASH}".encode("utf-8")
        ).hexdigest()[:12]
        safe = c["chunk_id"].replace("/", "_").replace("::", "__")[:80]
        fp = cache_root / f"{safe}__{h}.json"
        if not fp.exists():
            faltantes.append(c["chunk_id"])
            continue
        c["_cache_path"] = fp
        out.append(c)
    if faltantes:
        raise RuntimeError(
            f"{len(faltantes)} chunks sin resultado de extracción en {cache_root}: "
            f"{faltantes[:5]}. El caché no cubre el corpus; re-extraer antes de ensamblar."
        )
    return out


def assemble_v3(roles_activos: tuple[str, ...]) -> dict[str, Any]:
    chunks = cargar_chunks_con_rol()

    nodes_by_id, edges_set, esqueleto_counts = build_skeleton()
    skeleton_ids = set(nodes_by_id.keys())
    for n in nodes_by_id.values():
        n["provenances"] = [dict(n["provenance"])]
        n["rol_fuente"] = "esqueleto"
    for e in edges_set.values():
        e["provenances"] = [dict(e["provenance"])]
        e["rol_fuente"] = "esqueleto"

    stats: dict[str, Any] = {
        "por_rol": {},
        "chunks_procesados": 0,
        "chunks_excluidos_por_rol": 0,
        "chunks_con_error": 0,
        "raw_entities": 0,
        "raw_relations": 0,
        "merged_entities": 0,
        "prov_nodo": 0,
        "prov_arista": 0,
        "dropped": {
            "invalid_type": 0, "invalid_predicate": 0,
            "relacion_esqueleto_desde_cache": 0, "dangling": 0,
            "domain_range": 0, "sujeto_id_invalido": 0, "sujeto_propuesto_vacio": 0,
        },
    }
    for c in chunks:
        stats["por_rol"][c["rol"]] = stats["por_rol"].get(c["rol"], 0) + 1

    cuarentena: dict[str, dict[str, Any]] = {}
    aporte_por_chunk: dict[str, dict[str, Any]] = {}

    def add_prov(obj: dict[str, Any], doc: str, location: str,
                 reg: dict[str, Any] | None = None) -> bool:
        prov = {"source_doc": doc, "location": location}
        if prov not in obj["provenances"]:
            obj["provenances"].append(prov)
            if reg is not None:
                reg["provenances"] += 1
            return True
        return False

    for c in chunks:
        rol, doc, location, chunk_id = c["rol"], c["doc"], c["location"], c["chunk_id"]
        clave = f"{chunk_id}#{c['_cache_path'].stem[-12:]}"

        if rol not in roles_activos:
            stats["chunks_excluidos_por_rol"] += 1
            continue

        data = json.loads(c["_cache_path"].read_text(encoding="utf-8"))
        if data.get("error"):
            stats["chunks_con_error"] += 1
            continue
        stats["chunks_procesados"] += 1

        entities = data.get("entities", [])
        relations = data.get("relations", [])
        reg = aporte_por_chunk.setdefault(clave, {
            "chunk_id": chunk_id, "rol": rol, "location": location,
            "chars": c["char_count"], "entidades_extraidas": len(entities),
            "nodos": 0, "aristas": 0, "provenances": 0,
        })

        local_to_global: dict[str, str] = {}

        for e in entities:
            stats["raw_entities"] += 1
            etype = e.get("type")
            if etype not in ENTITY_TYPES:
                stats["dropped"]["invalid_type"] += 1
                continue
            if etype == "TextoOrdenado":
                e.setdefault("properties", {}).setdefault("archivo", doc)
            gid = f"{etype}_{entity_slug_v3(e)}"
            local_to_global[e["local_id"]] = gid

            if gid in nodes_by_id:
                existing = nodes_by_id[gid]
                for k, v in (e.get("properties") or {}).items():
                    existing["properties"].setdefault(k, v)
                if add_prov(existing, doc, location, reg):
                    stats["prov_nodo"] += 1
                stats["merged_entities"] += 1
                continue

            props = dict(e.get("properties") or {})
            if etype == "TextoOrdenado":
                props.setdefault("archivo", doc)
                if doc in DOC_MATERIA:
                    props.setdefault("materia", DOC_MATERIA[doc])
                props.setdefault("version", "vigente")
            nodes_by_id[gid] = {
                "id": gid, "type": etype, "label": e.get("label", ""), "properties": props,
                "provenance": {"source_doc": doc, "location": location},
                "provenances": [{"source_doc": doc, "location": location}],
                "rol_fuente": rol,
            }
            reg["nodos"] += 1

        def resolver_sujeto(r: dict[str, Any]) -> str | None:
            sujeto_id = r.get("sujeto_id")
            propuesto = r.get("sujeto_propuesto")
            if sujeto_id:
                if sujeto_id not in skeleton_ids:
                    stats["dropped"]["sujeto_id_invalido"] += 1
                    return None
                return sujeto_id
            if not propuesto or not str(propuesto).strip():
                stats["dropped"]["sujeto_propuesto_vacio"] += 1
                return None
            label = str(propuesto).strip()
            gid = f"Sujeto_propuesto_{slugify_full(label)[:80]}"
            padre = r.get("sujeto_propuesto_padre_sugerido")
            if gid not in nodes_by_id:
                props: dict[str, Any] = {"nivel": "propuesto", "cuarentena": True}
                if padre:
                    props["padre_sugerido"] = padre
                nodes_by_id[gid] = {
                    "id": gid, "type": "Sujeto", "label": label, "properties": props,
                    "provenance": {"source_doc": doc, "location": location},
                    "provenances": [{"source_doc": doc, "location": location}],
                    "rol_fuente": rol,
                }
            regc = cuarentena.setdefault(gid, {
                "id": gid, "label": label, "padres_sugeridos": [],
                "chunk_ids": [], "apariciones": 0,
            })
            regc["apariciones"] += 1
            if chunk_id not in regc["chunk_ids"]:
                regc["chunk_ids"].append(chunk_id)
            if padre and padre not in regc["padres_sugeridos"]:
                regc["padres_sugeridos"].append(padre)
            return gid

        def add_edge(src: str, pred: str, tgt: str) -> None:
            key = (src, pred, tgt)
            if key in edges_set:
                if add_prov(edges_set[key], doc, location, reg):
                    stats["prov_arista"] += 1
                return
            edges_set[key] = {
                "source": src, "target": tgt, "relation": pred,
                "provenance": {"source_doc": doc, "location": location},
                "provenances": [{"source_doc": doc, "location": location}],
                "rol_fuente": rol,
            }
            reg["aristas"] += 1

        for r in relations:
            stats["raw_relations"] += 1
            pred = r.get("predicate")
            if pred in RELACIONES_ESQUELETO:
                stats["dropped"]["relacion_esqueleto_desde_cache"] += 1
                continue
            if pred not in PREDICATES:
                stats["dropped"]["invalid_predicate"] += 1
                continue

            if pred in SUJETO_PREDICATES:
                ent_gid = local_to_global.get(
                    r.get("source") if pred == "aplica_a" else r.get("target")
                )
                ent_node = nodes_by_id.get(ent_gid) if ent_gid else None
                if ent_node is None:
                    stats["dropped"]["dangling"] += 1
                    continue
                valido = (
                    is_valid_triple(ent_node["type"], pred, "Sujeto")
                    if pred == "aplica_a"
                    else is_valid_triple("Sujeto", pred, ent_node["type"])
                )
                if not valido:
                    stats["dropped"]["domain_range"] += 1
                    continue
                sujeto_gid = resolver_sujeto(r)
                if sujeto_gid is None:
                    continue
                if pred == "aplica_a":
                    add_edge(ent_gid, pred, sujeto_gid)
                else:
                    add_edge(sujeto_gid, pred, ent_gid)
                continue

            src_gid = local_to_global.get(r.get("source"))
            tgt_gid = local_to_global.get(r.get("target"))
            if src_gid is None or tgt_gid is None:
                stats["dropped"]["dangling"] += 1
                continue
            src_node, tgt_node = nodes_by_id.get(src_gid), nodes_by_id.get(tgt_gid)
            if src_node is None or tgt_node is None:
                stats["dropped"]["dangling"] += 1
                continue
            if not is_valid_triple(src_node["type"], pred, tgt_node["type"]):
                stats["dropped"]["domain_range"] += 1
                continue
            add_edge(src_gid, pred, tgt_gid)

    nodes = list(nodes_by_id.values())
    edges = list(edges_set.values())

    # Aserción de cobertura: ningún chunk con entidades extraídas puede terminar
    # sin dejar rastro. Es exactamente el fallo que el reporte v2 no veía.
    # "Rastro" = nodo nuevo, arista nueva, o una cita agregada a algo existente:
    # un chunk que solo repite hechos ya vistos aporta evidencia, no estructura.
    mudos = [r for r in aporte_por_chunk.values()
             if r["entidades_extraidas"] > 0 and r["nodos"] == 0
             and r["aristas"] == 0 and r["provenances"] == 0]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "kg.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    cuarentena_list = sorted(cuarentena.values(), key=lambda c: (-c["apariciones"], c["id"]))
    (OUT_DIR / "cuarentena.json").write_text(
        json.dumps(cuarentena_list, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_type: dict[str, int] = {}
    by_rol: dict[str, int] = {}
    for n in nodes:
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        by_rol[n["rol_fuente"]] = by_rol.get(n["rol_fuente"], 0) + 1
    by_relation: dict[str, int] = {}
    for ed in edges:
        by_relation[ed["relation"]] = by_relation.get(ed["relation"], 0) + 1

    activos = len(chunks) - stats["chunks_excluidos_por_rol"]
    report = {
        "roles_activos": list(roles_activos),
        "chunks": {
            "total_en_chunks_all": len(chunks),
            "por_rol": stats["por_rol"],
            "procesados": stats["chunks_procesados"],
            "excluidos_por_rol": stats["chunks_excluidos_por_rol"],
            "con_error_en_cache": stats["chunks_con_error"],
            "cobertura_pct": round(stats["chunks_procesados"] / max(activos, 1) * 100, 1),
        },
        "raw_entities": stats["raw_entities"],
        "raw_relations": stats["raw_relations"],
        "merged_entities": stats["merged_entities"],
        "provenances_acumuladas": {"nodo": stats["prov_nodo"], "arista": stats["prov_arista"]},
        "dropped": stats["dropped"],
        "esqueleto": {"nodos": len(skeleton_ids), "aristas": sum(esqueleto_counts.values())},
        "cuarentena": {"propuestos": len(cuarentena_list)},
        "nodes_total": len(nodes),
        "edges_total": len(edges),
        "density": round(len(edges) / max(len(nodes), 1), 3),
        "nodes_by_type": by_type,
        "nodes_by_rol_fuente": by_rol,
        "edges_by_relation": by_relation,
        "chunks_mudos": mudos,
        "aporte_por_chunk": sorted(aporte_por_chunk.values(),
                                   key=lambda r: -r["entidades_extraidas"]),
    }
    (OUT_DIR / "assemble_v3_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", nargs="+", default=list(ROLES_DEFAULT),
                    choices=[CR.ROL_CUERPO, CR.ROL_TABLA, CR.ROL_INDICE],
                    help="roles que aportan nodos (default: cuerpo + tabla_norma_origen)")
    args = ap.parse_args()
    report = assemble_v3(tuple(args.roles))

    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("aporte_por_chunk", "chunks_mudos")},
                     ensure_ascii=False, indent=2), flush=True)
    print(f"\nKG: {OUT_DIR / 'kg.json'}", flush=True)
    mudos = report["chunks_mudos"]
    if mudos:
        print(f"\nFALLA DE COBERTURA: {len(mudos)} chunks extrajeron entidades y no "
              f"dejaron nodos ni aristas:", flush=True)
        for m in mudos[:20]:
            print(f"  {m['chunk_id']} ({m['rol']}, {m['entidades_extraidas']} ent) "
                  f"{m['location'][:70]}", flush=True)
        return 2
    print("\nCobertura OK: todo chunk activo con entidades extraídas dejó rastro.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
