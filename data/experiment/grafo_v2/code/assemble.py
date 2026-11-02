"""Ensambla kg.json a partir de los resultados cacheados por chunk — v2.

Cambios v2 (spec_extraccion_v2.md §4.3) sobre el assemble de run_3:
- Paso 0 nuevo: inyección del esqueleto desde ../esquema_v2_clases.json
  (nodos Sujeto de clases/instancias/roles + aristas subclase_de/miembro_de/
  instancia_de/parte_de), ANTES de procesar el caché.
- Resolución de sujetos: sujeto_id referencia directa al esqueleto (sin merge);
  sujeto_propuesto → nodo Sujeto nivel=propuesto en cuarentena (dedup exacto
  por slug) + entrada en cuarentena.json.
- Se APAGA el merge difuso de EntidadFinanciera del assemble v1 (truncado de
  prefijos + pasada post-hoc por categoria): sin extracción libre de sujetos
  no hay nada que mergear — el mecanismo que fabricó los duplicados muere.
  El dedup general por tipo+slug para los 6 types de contenido queda igual.
- Validación dominio/rango contra la matriz v2 (pseudo-tipo "Sujeto" como
  rango de aplica_a y dominio de ejecuta). Las relaciones de esqueleto solo
  pueden originarse en el paso 0; si aparecen en el caché se descartan.

Aprendizajes Run 1 + Run 2 que se conservan:
- Dedup por slug normalizado (lowercase, sin acentos, sin espacios → underscore).
- IDs únicos: <tipo>_<slug>. Si colisionan tipo+slug, se mergea (first-write-wins).
- provenance OBLIGATORIA en cada nodo y cada edge (protocolo b).

Uso:
    python assemble.py smoke    # ensambla desde cache_v2/smoke/
    python assemble.py full     # ensambla desde cache_v2/full/
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from schema import (
    CATALOGO_PATH,
    DOMAIN_RANGE,
    ENTITY_TYPES,
    PREDICATES,
    RELACIONES_ESQUELETO,
    SUJETO_PREDICATES,
    is_valid_triple,
)


RUN_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = RUN_DIR / "code" / "cache_v2"

# Cap de detalle de descartes en el reporte (el conteo por motivo es completo;
# el detalle por tripleta se acota para que el reporte del full run sea legible).
MAX_DROPPED_DETAIL = 200


# Materias asignadas por nombre de archivo
DOC_MATERIA = {
    "TO_capitales_minimos_actual.pdf": "capitales_minimos",
    "TO_clasificacion_deudores_actual.pdf": "clasificacion_deudores",
    "TO_exterior_cambios_actual.pdf": "exterior_cambios",
    "TO_proteccion_usuarios_servicios_financieros_actual.pdf": "proteccion_usuarios",
    "TO_regimen_informativo_contable_mensual_actual.pdf": "regimen_informativo",
}


def slugify(s: str, max_len: int = 80) -> str:
    """Normaliza a slug: lowercase, sin acentos, ascii, _ entre palabras."""
    if not s:
        return "empty"
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    if not s:
        return "empty"
    return s[:max_len]


# NOTA v2 (spec §4.3): acá vivían la singularización heurística y el merge por
# prefijo/categoria de EntidadFinanciera del assemble v1. Se ELIMINAN: eran
# maquinaria de fusión difusa de sujetos extraídos libremente, y en v2 el LLM
# no extrae sujetos (elige del catálogo). Los propuestos de cuarentena se
# dedupean EXACTO por slug, sin heurísticas.


def entity_slug(entity: dict[str, Any]) -> str:
    """Slug clave para dedup por tipo de entidad (6 types de contenido v2)."""
    t = entity["type"]
    props = entity.get("properties", {})
    label = entity.get("label", "")
    if t == "Comunicacion":
        code = props.get("codigo") or props.get("numero") or label
        return slugify(str(code))
    if t == "TextoOrdenado":
        # Dedup por archivo (invariante por PDF), NO por materia (text-libre del LLM).
        # Esto garantiza exactamente 1 TextoOrdenado por PDF.
        archivo = props.get("archivo") or props.get("_doc") or ""
        if not archivo:
            archivo = props.get("materia") or label
        return slugify(str(archivo))
    if t == "Operacion":
        tipo = props.get("tipo") or label
        return slugify(str(tipo))
    if t in ("Restriccion", "Obligacion", "Excepcion"):
        # Estos son hechos normativos concretos: cada extracción es prácticamente única.
        # Slug = type + descripción acortada para que rara vez colisione, salvo paráfrasis casi exactas.
        desc = props.get("descripcion") or label
        return slugify(str(desc), max_len=80)
    return slugify(label)


# ================================================================
# Paso 0 — Esqueleto (spec §4.3): nodos Sujeto + aristas de esqueleto
# desde esquema_v2_clases.json, ANTES de procesar el caché.
# ================================================================

def build_skeleton() -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str, str], dict[str, Any]], dict[str, int]]:
    """Construye los nodos y aristas de esqueleto desde el catálogo.

    Devuelve (nodes_by_id, edges_set, conteos_por_relacion)."""
    catalogo = json.loads(CATALOGO_PATH.read_text(encoding="utf-8"))

    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_set: dict[tuple[str, str, str], dict[str, Any]] = {}
    esqueleto_counts = {rel: 0 for rel in RELACIONES_ESQUELETO}

    def add_edge(src: str, rel: str, tgt: str, provenance: dict[str, Any]) -> None:
        key = (src, rel, tgt)
        if key in edges_set:
            return
        edges_set[key] = {
            "source": src,
            "target": tgt,
            "relation": rel,
            "provenance": dict(provenance),
        }
        esqueleto_counts[rel] += 1

    # Clases e instancias (array "clases")
    for entry in catalogo["clases"]:
        props: dict[str, Any] = {"nivel": entry["nivel"]}
        if entry.get("alias"):
            props["alias"] = list(entry["alias"])
        if entry["nivel"] == "instancia":
            # Resto de los campos de la instancia (instancia_de, parte_de).
            props["instancia_de"] = entry["instancia_de"]
            if "parte_de" in entry:
                props["parte_de"] = entry["parte_de"]
        nodes_by_id[entry["id"]] = {
            "id": entry["id"],
            "type": "Sujeto",
            "label": entry["label"],
            "properties": props,
            "provenance": dict(entry["provenance"]),
        }

    # Roles
    for rol in catalogo["roles"]:
        prov = rol.get("provenance") or {"source_doc": rol["to"], "location": "Sección de alcance del TO"}
        nodes_by_id[rol["id"]] = {
            "id": rol["id"],
            "type": "Sujeto",
            "label": rol["label"],
            "properties": {"nivel": "rol"},
            "provenance": {"source_doc": rol["to"], "location": prov.get("location", "Sección de alcance del TO")},
        }

    # Aristas de esqueleto (con provenance del catálogo)
    for entry in catalogo["clases"]:
        if entry["nivel"] == "clase" and entry.get("padre"):
            add_edge(entry["id"], "subclase_de", entry["padre"], entry["provenance"])
        if entry["nivel"] == "instancia":
            add_edge(entry["id"], "instancia_de", entry["instancia_de"], entry["provenance"])
            if "parte_de" in entry:
                add_edge(entry["id"], "parte_de", entry["parte_de"], entry["provenance"])
    for rol in catalogo["roles"]:
        for miembro in rol["miembros"]:
            add_edge(miembro, "miembro_de", rol["id"], rol["provenance"])

    # Chequeo interno: toda arista de esqueleto une nodos del esqueleto.
    for (src, rel, tgt) in edges_set:
        if src not in nodes_by_id or tgt not in nodes_by_id:
            raise RuntimeError(f"Esqueleto inconsistente: {src} --{rel}--> {tgt} referencia un id inexistente")

    return nodes_by_id, edges_set, esqueleto_counts


def assemble(cache_root: Path, kg_out: Path, report_out: Path, cuarentena_out: Path) -> dict[str, Any]:
    """Lee todos los chunks cacheados en cache_root y ensambla kg.json.

    v2: arranca del esqueleto inyectado y resuelve los sujetos de
    aplica_a/ejecuta contra él (o contra cuarentena)."""
    files = sorted(cache_root.glob("*.json"))
    if not files:
        raise RuntimeError(f"No hay archivos en {cache_root}")

    # ---- Paso 0: esqueleto ----
    nodes_by_id, edges_set, esqueleto_counts = build_skeleton()
    skeleton_ids = set(nodes_by_id.keys())
    n_esqueleto_nodes = len(skeleton_ids)

    # ----------------------------------------------------------------
    # Dedup por chunk_id: el chunker puede producir múltiples chunks con
    # el mismo chunk_id (ej. cuando "1.1." aparece varias veces en el texto:
    # una vez como header real, otras como referencias cruzadas). En el cache
    # quedan varios .json para el mismo chunk_id. Acá agrupamos y elegimos
    # el "mejor" — el que más entidades extrajo (asumido como el header real).
    # ----------------------------------------------------------------
    results_by_chunk_id: dict[str, list[dict[str, Any]]] = {}
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  WARN: no pude leer {fp.name}: {e}", flush=True)
            continue
        if not isinstance(data, dict) or "chunk_id" not in data:
            continue  # archivos auxiliares en el cache dir (chunks_*.json, reportes)
        cid = data["chunk_id"]
        results_by_chunk_id.setdefault(cid, []).append(data)

    best_results: list[dict[str, Any]] = []
    dedup_redundant = 0
    for cid, group in results_by_chunk_id.items():
        if len(group) == 1:
            best_results.append(group[0])
            continue
        # Hay duplicados. Filtrar primero los que tuvieron error.
        valid = [r for r in group if not r.get("error")]
        if not valid:
            best_results.append(group[0])  # mantener uno para registro
            dedup_redundant += len(group) - 1
            continue
        # De los válidos, elegir el de más entidades (luego más relaciones).
        best = max(valid, key=lambda r: (len(r.get("entities", [])), len(r.get("relations", []))))
        best_results.append(best)
        dedup_redundant += len(group) - 1

    chunks_with_error = 0
    chunks_ok = 0
    chunks_total = 0

    raw_entities = 0
    raw_relations = 0
    dropped_invalid_type = 0
    dropped_invalid_predicate = 0
    dropped_esqueleto_desde_cache = 0
    dropped_dangling = 0
    dropped_domain_range = 0
    dropped_sujeto_id_invalido = 0
    dropped_sujeto_propuesto_vacio = 0
    dropped_duplicate_edge = 0
    merged_entities = 0
    dropped_detail: list[dict[str, Any]] = []

    edges_sujeto_a_esqueleto = 0
    edges_sujeto_a_propuestos = 0

    # Cuarentena: slug → registro (spec §4.3)
    cuarentena: dict[str, dict[str, Any]] = {}

    per_doc_chunks_with_content: dict[str, int] = {}
    per_doc_chunks_total: dict[str, int] = {}

    def drop(motivo: str, chunk_id: str, r: dict[str, Any]) -> None:
        if len(dropped_detail) < MAX_DROPPED_DETAIL:
            dropped_detail.append({
                "motivo": motivo,
                "chunk_id": chunk_id,
                "predicate": r.get("predicate"),
                "source": r.get("source"),
                "target": r.get("target"),
                "sujeto_id": r.get("sujeto_id"),
                "sujeto_propuesto": r.get("sujeto_propuesto"),
            })

    def resolver_sujeto(r: dict[str, Any], doc: str, location: str, chunk_id: str) -> str | None:
        """Devuelve el gid del sujeto de una tripleta aplica_a/ejecuta, creando
        el nodo propuesto en cuarentena si corresponde. None = descartar."""
        nonlocal dropped_sujeto_id_invalido, dropped_sujeto_propuesto_vacio
        sujeto_id = r.get("sujeto_id")
        propuesto = r.get("sujeto_propuesto")
        if sujeto_id:
            if sujeto_id not in skeleton_ids:
                dropped_sujeto_id_invalido += 1
                drop("sujeto_id_invalido", chunk_id, r)
                return None
            return sujeto_id
        if not propuesto or not str(propuesto).strip():
            dropped_sujeto_propuesto_vacio += 1
            drop("sujeto_propuesto_vacio", chunk_id, r)
            return None
        label = str(propuesto).strip()
        slug = slugify(label)  # dedup EXACTO por slug normalizado (sin heurísticas)
        gid = f"Sujeto_propuesto_{slug}"
        padre_sugerido = r.get("sujeto_propuesto_padre_sugerido")
        if gid not in nodes_by_id:
            props: dict[str, Any] = {"nivel": "propuesto", "cuarentena": True}
            if padre_sugerido:
                props["padre_sugerido"] = padre_sugerido
            nodes_by_id[gid] = {
                "id": gid,
                "type": "Sujeto",
                "label": label,
                "properties": props,
                "provenance": {"source_doc": doc, "location": location},
            }
        reg = cuarentena.setdefault(gid, {
            "id": gid,
            "label": label,
            "padres_sugeridos": [],
            "chunk_ids": [],
            "apariciones": 0,
        })
        reg["apariciones"] += 1
        if chunk_id not in reg["chunk_ids"]:
            reg["chunk_ids"].append(chunk_id)
        if padre_sugerido and padre_sugerido not in reg["padres_sugeridos"]:
            reg["padres_sugeridos"].append(padre_sugerido)
        return gid

    for data in best_results:
        chunks_total += 1
        doc = data.get("doc", "")
        location = data.get("location", "")
        chunk_id = data.get("chunk_id", "")
        per_doc_chunks_total[doc] = per_doc_chunks_total.get(doc, 0) + 1

        if data.get("error"):
            chunks_with_error += 1
            continue
        chunks_ok += 1

        local_to_global: dict[str, str] = {}

        entities = data.get("entities", [])
        relations = data.get("relations", [])

        if entities:
            per_doc_chunks_with_content[doc] = per_doc_chunks_with_content.get(doc, 0) + 1

        for e in entities:
            raw_entities += 1
            etype = e.get("type")
            if etype not in ENTITY_TYPES:
                # Incluye cualquier "Sujeto"/"EntidadFinanciera" que se filtrara
                # desde un caché viejo: los sujetos solo entran por esqueleto/cuarentena.
                dropped_invalid_type += 1
                continue
            # Inyectar archivo en properties de TextoOrdenado ANTES del slug
            # para que el dedup sea por archivo (1 nodo por PDF, garantizado).
            if etype == "TextoOrdenado":
                e_props = e.setdefault("properties", {})
                if "archivo" not in e_props and doc:
                    e_props["archivo"] = doc
            slug = entity_slug(e)
            gid = f"{etype}_{slug}"
            # (v2: acá vivía el merge por prefijo de EntidadFinanciera — eliminado, spec §4.3)

            local_to_global[e["local_id"]] = gid

            if gid in nodes_by_id:
                # Merge: first-write-wins para properties (no sobreescribimos),
                # pero acumulamos en `properties` los campos nuevos no vistos.
                existing = nodes_by_id[gid]
                for k, v in e.get("properties", {}).items():
                    if k not in existing["properties"]:
                        existing["properties"][k] = v
                merged_entities += 1
                continue

            # TextoOrdenado: si el chunk no trae materia, la inferimos del nombre de archivo
            props = dict(e.get("properties", {}))
            if etype == "TextoOrdenado":
                if "archivo" not in props and doc:
                    props["archivo"] = doc
                if "materia" not in props and doc in DOC_MATERIA:
                    props["materia"] = DOC_MATERIA[doc]
                if "version" not in props:
                    props["version"] = "vigente"

            nodes_by_id[gid] = {
                "id": gid,
                "type": etype,
                "label": e.get("label", ""),
                "properties": props,
                "provenance": {
                    "source_doc": doc,
                    "location": location,
                },
            }

        for r in relations:
            raw_relations += 1
            pred = r.get("predicate")
            if pred in RELACIONES_ESQUELETO:
                # Las relaciones de esqueleto SOLO se originan en el paso 0;
                # desde el caché se descartan siempre (spec §4.3).
                dropped_esqueleto_desde_cache += 1
                drop("relacion_esqueleto_desde_cache", chunk_id, r)
                continue
            if pred not in PREDICATES:
                dropped_invalid_predicate += 1
                drop("predicado_invalido", chunk_id, r)
                continue

            if pred in SUJETO_PREDICATES:
                # v2: el extremo sujeto viene del catálogo o va a cuarentena.
                if pred == "aplica_a":
                    ent_gid = local_to_global.get(r.get("source"))
                else:  # ejecuta
                    ent_gid = local_to_global.get(r.get("target"))
                ent_node = nodes_by_id.get(ent_gid) if ent_gid else None
                if ent_node is None:
                    dropped_dangling += 1
                    drop("referencia_colgante", chunk_id, r)
                    continue
                # Validación dominio/rango con el pseudo-tipo "Sujeto" (matriz v2).
                if pred == "aplica_a":
                    valido = is_valid_triple(ent_node["type"], pred, "Sujeto")
                else:
                    valido = is_valid_triple("Sujeto", pred, ent_node["type"])
                if not valido:
                    dropped_domain_range += 1
                    drop("dominio_rango_invalido", chunk_id, r)
                    continue
                sujeto_gid = resolver_sujeto(r, doc, location, chunk_id)
                if sujeto_gid is None:
                    continue
                if pred == "aplica_a":
                    src_gid, tgt_gid = ent_gid, sujeto_gid
                else:
                    src_gid, tgt_gid = sujeto_gid, ent_gid
                key = (src_gid, pred, tgt_gid)
                if key in edges_set:
                    dropped_duplicate_edge += 1
                    continue
                edges_set[key] = {
                    "source": src_gid,
                    "target": tgt_gid,
                    "relation": pred,
                    "provenance": {"source_doc": doc, "location": location},
                }
                if sujeto_gid in skeleton_ids:
                    edges_sujeto_a_esqueleto += 1
                else:
                    edges_sujeto_a_propuestos += 1
                continue

            src_gid = local_to_global.get(r.get("source"))
            tgt_gid = local_to_global.get(r.get("target"))
            if src_gid is None or tgt_gid is None:
                dropped_dangling += 1
                drop("referencia_colgante", chunk_id, r)
                continue
            src_node = nodes_by_id.get(src_gid)
            tgt_node = nodes_by_id.get(tgt_gid)
            if src_node is None or tgt_node is None:
                dropped_dangling += 1
                drop("referencia_colgante", chunk_id, r)
                continue
            if not is_valid_triple(src_node["type"], pred, tgt_node["type"]):
                dropped_domain_range += 1
                drop("dominio_rango_invalido", chunk_id, r)
                continue
            key = (src_gid, pred, tgt_gid)
            if key in edges_set:
                dropped_duplicate_edge += 1
                continue
            edges_set[key] = {
                "source": src_gid,
                "target": tgt_gid,
                "relation": pred,
                "provenance": {
                    "source_doc": doc,
                    "location": location,
                },
            }

    # NOTA v2 (spec §4.3): acá vivía la pasada post-hoc de merge de
    # EntidadFinanciera por `categoria` normalizada (con redirect de edges).
    # ELIMINADA: en v2 los sujetos del esqueleto se referencian por id (no hay
    # merge posible) y los propuestos se dedupean exacto por slug al crearse.

    nodes = list(nodes_by_id.values())
    edges = list(edges_set.values())

    kg = {"nodes": nodes, "edges": edges}
    kg_out.parent.mkdir(parents=True, exist_ok=True)
    kg_out.write_text(json.dumps(kg, ensure_ascii=False, indent=2), encoding="utf-8")

    # cuarentena.json — junto al kg de salida (spec §4.3; existe aunque esté vacío)
    cuarentena_list = sorted(cuarentena.values(), key=lambda c: (-c["apariciones"], c["id"]))
    cuarentena_out.parent.mkdir(parents=True, exist_ok=True)
    cuarentena_out.write_text(
        json.dumps(cuarentena_list, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Reporte de ensamblaje
    by_type: dict[str, int] = {}
    sujeto_by_nivel: dict[str, int] = {}
    for n in nodes:
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        if n["type"] == "Sujeto":
            nivel = n["properties"].get("nivel", "sin_nivel")
            sujeto_by_nivel[nivel] = sujeto_by_nivel.get(nivel, 0) + 1
    by_relation: dict[str, int] = {}
    for ed in edges:
        by_relation[ed["relation"]] = by_relation.get(ed["relation"], 0) + 1

    coverage: dict[str, dict[str, Any]] = {}
    for d, total in per_doc_chunks_total.items():
        with_content = per_doc_chunks_with_content.get(d, 0)
        coverage[d] = {
            "chunks_total": total,
            "chunks_with_content": with_content,
            "coverage_pct": round(with_content / total * 100, 1) if total else 0.0,
        }

    report = {
        "cache_root": str(cache_root),
        "cache_files": len(files),
        "unique_chunk_ids": len(results_by_chunk_id),
        "redundant_cache_files_dedup": dedup_redundant,
        "chunks_total": chunks_total,
        "chunks_ok": chunks_ok,
        "chunks_with_error": chunks_with_error,
        "raw_entities": raw_entities,
        "raw_relations": raw_relations,
        "merged_entities": merged_entities,
        "esqueleto": {
            "nodos": n_esqueleto_nodes,
            "aristas": esqueleto_counts,
            "aristas_total": sum(esqueleto_counts.values()),
        },
        "cuarentena": {
            "propuestos": len(cuarentena_list),
            "apariciones_total": sum(c["apariciones"] for c in cuarentena_list),
            "detalle": [
                {"id": c["id"], "label": c["label"], "apariciones": c["apariciones"],
                 "padres_sugeridos": c["padres_sugeridos"]}
                for c in cuarentena_list
            ],
        },
        "edges_sujeto": {
            "hacia_esqueleto": edges_sujeto_a_esqueleto,
            "hacia_propuestos": edges_sujeto_a_propuestos,
        },
        "dropped": {
            "invalid_type": dropped_invalid_type,
            "invalid_predicate": dropped_invalid_predicate,
            "relacion_esqueleto_desde_cache": dropped_esqueleto_desde_cache,
            "dangling": dropped_dangling,
            "domain_range": dropped_domain_range,
            "sujeto_id_invalido": dropped_sujeto_id_invalido,
            "sujeto_propuesto_vacio": dropped_sujeto_propuesto_vacio,
            "duplicate_edge": dropped_duplicate_edge,
        },
        "dropped_detail": dropped_detail,
        "nodes_total": len(nodes),
        "edges_total": len(edges),
        "density": round(len(edges) / max(len(nodes), 1), 3),
        "nodes_by_type": by_type,
        "sujeto_by_nivel": sujeto_by_nivel,
        "edges_by_relation": by_relation,
        "coverage_by_doc": coverage,
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("smoke", "full"):
        print("Uso: python assemble.py {smoke|full}")
        return 1
    mode = sys.argv[1]
    cache_root = CACHE_DIR / mode

    if mode == "smoke":
        kg_out = CACHE_DIR / "kg_smoke.json"
        report_out = CACHE_DIR / "assemble_smoke.json"
        cuarentena_out = CACHE_DIR / "cuarentena_smoke.json"
    else:
        kg_out = RUN_DIR / "kg.json"
        report_out = CACHE_DIR / "assemble_full.json"
        cuarentena_out = RUN_DIR / "cuarentena.json"

    report = assemble(cache_root, kg_out, report_out, cuarentena_out)
    print(f"\nEnsamblado {mode}:", flush=True)
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    print(f"\nKG: {kg_out}", flush=True)
    print(f"Reporte: {report_out}", flush=True)
    print(f"Cuarentena: {cuarentena_out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
