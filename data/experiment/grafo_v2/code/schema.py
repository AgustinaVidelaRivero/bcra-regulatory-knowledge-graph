"""Pydantic models para la salida estructurada del extractor — v2 (Manera B).

Cambio central v2 (spec_extraccion_v2.md §2 y §4.1): el LLM ya NO crea nodos de
sujeto. El type EntidadFinanciera desaparece del vocabulario del LLM (quedan 6
tipos de entidad) y el sujeto de aplica_a/ejecuta se ELIGE de un catálogo
cerrado inyectado desde ../esquema_v2_clases.json (enum en el tool schema), con
válvula de cuarentena vía sujeto_propuesto.

Aprendizajes Run 2 heredados: relations con default_factory=list; coerción
defensiva de tipos en properties.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# === SCHEMA CERRADO v2: 6 tipos de entidad visibles al LLM (sin sujeto) ===

ENTITY_TYPES = (
    "Comunicacion",
    "TextoOrdenado",
    "Operacion",
    "Restriccion",
    "Excepcion",
    "Obligacion",
)
EntityType = Literal[
    "Comunicacion",
    "TextoOrdenado",
    "Operacion",
    "Restriccion",
    "Excepcion",
    "Obligacion",
]

PREDICATES = (
    "establecida_en",
    "referencia",
    "modificada_por",
    "aplica_a",
    "regula",
    "exceptua",
    "exceptua_obligacion",
    "prohibe",
    "limita",
    "ejecuta",
    "requiere",
    "condiciona",
)
Predicate = Literal[
    "establecida_en",
    "referencia",
    "modificada_por",
    "aplica_a",
    "regula",
    "exceptua",
    "exceptua_obligacion",
    "prohibe",
    "limita",
    "ejecuta",
    "requiere",
    "condiciona",
]

# Predicados cuyo extremo sujeto viene del catálogo (sujeto_id / sujeto_propuesto),
# no de una entidad del chunk.
SUJETO_PREDICATES = ("aplica_a", "ejecuta")

# Relaciones de esqueleto (spec §2): las escribe SOLO assemble.py al cargar el
# catálogo. NO entran en el vocabulario del LLM ni en el filtro de extracción.
RELACIONES_ESQUELETO = (
    "subclase_de",
    "miembro_de",
    "instancia_de",
    "parte_de",
)


# === CATÁLOGO DE SUJETOS (esquema_v2_clases.json, cargado en import) ===

CATALOGO_PATH = Path(__file__).resolve().parent.parent / "esquema_v2_clases.json"

with CATALOGO_PATH.open(encoding="utf-8") as _f:
    _CATALOGO = json.load(_f)

CATALOGO_VERSION: str = _CATALOGO["version"]

# TODOS los ids del catálogo: clases + instancias (array "clases") y roles.
SUJETOS_CATALOGO: list[str] = (
    [e["id"] for e in _CATALOGO["clases"]] + [r["id"] for r in _CATALOGO["roles"]]
)
SUJETOS_CATALOGO_SET: frozenset[str] = frozenset(SUJETOS_CATALOGO)

if len(SUJETOS_CATALOGO) != len(SUJETOS_CATALOGO_SET):
    raise RuntimeError(f"esquema_v2_clases.json tiene ids duplicados ({CATALOGO_PATH})")

# Mapeo TO (nombre exacto del PDF) → rol de alcance de ese TO, con labels de
# miembros para interpolar en el mensaje de usuario (spec §4.2, lista por-TO).
_LABEL_BY_ID = {e["id"]: e["label"] for e in _CATALOGO["clases"]}

ROL_POR_TO: dict[str, dict] = {
    r["to"]: {
        "rol_id": r["id"],
        "label": r["label"],
        "miembros_ids": list(r["miembros"]),
        "miembros_labels": [_LABEL_BY_ID[m] for m in r["miembros"]],
    }
    for r in _CATALOGO["roles"]
}


def _sujetos_prompt() -> str:
    """Catálogo compacto para el system prompt: una línea por entrada
    ("id — label (alias: ...)"), agrupado por rama para legibilidad."""
    clases = _CATALOGO["clases"]
    by_id = {e["id"]: e for e in clases}

    def rama_de(e: dict) -> str:
        # Ancestro directo bajo la raíz (o la raíz misma).
        cur = e
        while True:
            padre = cur.get("padre") if cur["nivel"] == "clase" else cur.get("instancia_de")
            if padre is None or padre == "Sujeto_sujeto":
                return cur["id"]
            cur = by_id[padre]

    def linea(e: dict) -> str:
        alias = e.get("alias") or []
        alias_txt = f" (alias: {', '.join(alias)})" if alias else ""
        marca = " [instancia]" if e["nivel"] == "instancia" else ""
        return f"{e['id']} — {e['label']}{alias_txt}{marca}"

    RAMAS = [
        ("Sujeto_sujeto_regulado", "Sujetos regulados"),
        ("Sujeto_contraparte", "Contrapartes"),
        ("Sujeto_organismo_publico", "Organismos públicos (clases e instancias)"),
        ("Sujeto_estructura", "Estructuras y vehículos"),
        ("Sujeto_sujeto", "Raíz"),
    ]
    grupos: dict[str, list[str]] = {rid: [] for rid, _ in RAMAS}
    for e in clases:
        grupos[rama_de(e)].append(linea(e))

    out: list[str] = []
    for rid, titulo in RAMAS:
        if not grupos[rid]:
            continue
        out.append(f"## {titulo}")
        out.extend(grupos[rid])
    out.append("## Roles de alcance por TO")
    for r in _CATALOGO["roles"]:
        out.append(f"{r['id']} — {r['label']} [rol del TO {r['to']}]")
    return "\n".join(out)


SUJETOS_PROMPT: str = _sujetos_prompt()


# Tabla dominio/rango v2. Para aplica_a/ejecuta el extremo sujeto se anota con
# el pseudo-tipo "Sujeto" (catálogo): NO es un entity type del LLM; el filtro
# valida ese extremo por sujeto_id/sujeto_propuesto, no por type de entidad.
DOMAIN_RANGE: dict[str, tuple[set[str], set[str]]] = {
    "establecida_en":        ({"Restriccion", "Obligacion", "Excepcion", "Operacion"}, {"TextoOrdenado"}),
    "referencia":            ({"TextoOrdenado"}, {"Comunicacion"}),
    "modificada_por":        ({"TextoOrdenado"}, {"Comunicacion"}),
    "aplica_a":              ({"Restriccion", "Obligacion"}, {"Sujeto"}),
    "regula":                ({"Restriccion", "Obligacion"}, {"Operacion"}),
    "exceptua":              ({"Excepcion"}, {"Restriccion"}),
    "exceptua_obligacion":   ({"Excepcion"}, {"Obligacion"}),
    "prohibe":               ({"Restriccion"}, {"Operacion"}),
    "limita":                ({"Restriccion"}, {"Operacion"}),
    "ejecuta":               ({"Sujeto"}, {"Operacion"}),
    "requiere":              ({"Operacion"}, {"Obligacion"}),
    "condiciona":            ({"Obligacion"}, {"Operacion"}),
}


# === MODELOS PYDANTIC ===

class EntityOut(BaseModel):
    """Entidad extraída por el LLM."""
    local_id: str = Field(description="Identificador local dentro del chunk (e.g., 'e1', 'e2'). Usado para referenciar en relations.")
    type: EntityType = Field(description="Tipo de entidad (uno de los 6).")
    label: str = Field(description="Etiqueta legible humana (ej. 'Comunicación A 7825', 'Restricción de financiación al sector público').")
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Propiedades de la entidad (key=str, value=str). Ver schema.md para propiedades requeridas por tipo.",
    )

    @field_validator("label")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("label no puede estar vacío")
        return v

    @model_validator(mode="before")
    @classmethod
    def coerce_properties_to_str(cls, data):
        """Coerce property values to strings.

        El LLM tiende a devolver enteros/floats para campos como 'numero',
        'umbral', 'plazo' aunque el schema diga string. Coerción robusta evita
        validaciones rotas por trivialidades de tipo (Run 1+2 lección).
        """
        if isinstance(data, dict) and "properties" in data and isinstance(data["properties"], dict):
            data["properties"] = {
                str(k): ("" if v is None else str(v))
                for k, v in data["properties"].items()
            }
        return data


class RelationOut(BaseModel):
    """Relación de un chunk.

    v2: para aplica_a/ejecuta el extremo sujeto NO es una entidad del chunk —
    va en sujeto_id (id del catálogo) O sujeto_propuesto (texto libre →
    cuarentena), mutuamente excluyentes. aplica_a lleva la norma en `source`
    (el sujeto es el destino); ejecuta lleva la operación en `target` (el
    sujeto es el origen).
    """
    source: str | None = Field(default=None, description="local_id de la entidad source (no se usa para el extremo sujeto de ejecuta).")
    target: str | None = Field(default=None, description="local_id de la entidad target (no se usa para el extremo sujeto de aplica_a).")
    predicate: Predicate = Field(description="Tipo de relación (uno de los 12).")
    sujeto_id: str | None = Field(default=None, description="SOLO aplica_a/ejecuta: id exacto del catálogo de sujetos.")
    sujeto_propuesto: str | None = Field(default=None, description="SOLO aplica_a/ejecuta: sujeto fuera de catálogo (texto libre, va a cuarentena).")
    sujeto_propuesto_padre_sugerido: str | None = Field(default=None, description="Opcional junto a sujeto_propuesto: id del catálogo sugerido como padre.")

    @model_validator(mode="before")
    @classmethod
    def coerce_empty_to_none(cls, data):
        """El LLM suele mandar "" en campos que no usa: "" → None antes de
        validar. Además, el extremo sujeto no va en target (aplica_a) ni en
        source (ejecuta): si el LLM los manda igual, se ignoran (evita que un
        slip predecible tumbe la validación del chunk entero)."""
        if isinstance(data, dict):
            for k in ("source", "target", "sujeto_id", "sujeto_propuesto", "sujeto_propuesto_padre_sugerido"):
                v = data.get(k)
                if isinstance(v, str) and not v.strip():
                    data[k] = None
            if data.get("predicate") == "aplica_a":
                data["target"] = None
            elif data.get("predicate") == "ejecuta":
                data["source"] = None
        return data

    @model_validator(mode="after")
    def validar_extremo_sujeto(self):
        es_sujeto = self.predicate in SUJETO_PREDICATES
        if es_sujeto:
            # Mutuamente excluyentes y exactamente uno presente.
            if (self.sujeto_id is None) == (self.sujeto_propuesto is None):
                raise ValueError(
                    f"{self.predicate} requiere exactamente UNO de sujeto_id o sujeto_propuesto"
                )
            if self.sujeto_propuesto_padre_sugerido is not None and self.sujeto_propuesto is None:
                raise ValueError("sujeto_propuesto_padre_sugerido solo acompaña a sujeto_propuesto")
            if self.predicate == "aplica_a" and self.source is None:
                raise ValueError("aplica_a requiere source (la norma del chunk)")
            if self.predicate == "ejecuta" and self.target is None:
                raise ValueError("ejecuta requiere target (la operación del chunk)")
        else:
            if self.sujeto_id or self.sujeto_propuesto or self.sujeto_propuesto_padre_sugerido:
                raise ValueError(f"sujeto_* solo es válido en {SUJETO_PREDICATES}, no en {self.predicate}")
            if self.source is None or self.target is None:
                raise ValueError(f"{self.predicate} requiere source y target")
        return self


class ExtractionOut(BaseModel):
    """Salida estructurada del LLM para un chunk."""
    entities: list[EntityOut] = Field(default_factory=list)
    relations: list[RelationOut] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_lists_from_json_string(cls, data):
        """Algunas veces el LLM devuelve entities/relations como STRING JSON
        (en lugar de array). Coercer si es el caso."""
        import json as _json
        if isinstance(data, dict):
            for key in ("entities", "relations"):
                v = data.get(key)
                if isinstance(v, str):
                    try:
                        parsed = _json.loads(v)
                        if isinstance(parsed, list):
                            data[key] = parsed
                    except _json.JSONDecodeError:
                        pass  # Pydantic dará error claro abajo
        return data


# === FUNCIONES DE VALIDACIÓN POST-EXTRACCIÓN ===

def is_valid_triple(source_type: str, predicate: str, target_type: str) -> bool:
    """Valida (dominio, predicado, rango) contra DOMAIN_RANGE.

    Para los predicados con extremo sujeto, ese extremo se pasa como el
    pseudo-tipo "Sujeto" (lo hace filter_extraction; el LLM nunca lo produce)."""
    if predicate not in DOMAIN_RANGE:
        return False
    dom, ran = DOMAIN_RANGE[predicate]
    return source_type in dom and target_type in ran


def filter_extraction(extraction: ExtractionOut) -> tuple[ExtractionOut, dict[str, int]]:
    """Filtra entities/relations contra el schema cerrado v2.

    Devuelve (extracción_filtrada, métricas) donde métricas cuenta descartes por causa.
    La estructura sujeto_id/sujeto_propuesto ya fue validada por Pydantic; acá
    se filtra el contenido: sujeto_id fuera de catálogo se descarta (no debería
    ocurrir con el enum del tool schema — defensivo), y un padre sugerido fuera
    de catálogo se anula (es una pista, no invalida la relación).
    """
    metrics = {
        "entities_in": len(extraction.entities),
        "entities_out": 0,
        "relations_in": len(extraction.relations),
        "relations_out": 0,
        "rel_dropped_unknown_predicate": 0,
        "rel_dropped_dangling_ref": 0,
        "rel_dropped_domain_range": 0,
        "rel_dropped_sujeto_invalido": 0,
    }

    # Entities ya están validadas a nivel Literal por Pydantic. Pasan todas.
    out_entities = list(extraction.entities)
    metrics["entities_out"] = len(out_entities)

    by_local: dict[str, EntityOut] = {e.local_id: e for e in out_entities}

    out_relations: list[RelationOut] = []
    for r in extraction.relations:
        # Pydantic ya bloquea predicados fuera de la lista. Defensivo igual.
        if r.predicate not in DOMAIN_RANGE:
            metrics["rel_dropped_unknown_predicate"] += 1
            continue

        if r.predicate in SUJETO_PREDICATES:
            # Extremo de chunk: la norma (aplica_a) o la operación (ejecuta).
            if r.predicate == "aplica_a":
                ent = by_local.get(r.source)
                src_type, tgt_type = (ent.type if ent else None), "Sujeto"
            else:  # ejecuta
                ent = by_local.get(r.target)
                src_type, tgt_type = "Sujeto", (ent.type if ent else None)
            if ent is None:
                metrics["rel_dropped_dangling_ref"] += 1
                continue
            if not is_valid_triple(src_type, r.predicate, tgt_type):
                metrics["rel_dropped_domain_range"] += 1
                continue
            # Extremo catálogo.
            if r.sujeto_id is not None and r.sujeto_id not in SUJETOS_CATALOGO_SET:
                metrics["rel_dropped_sujeto_invalido"] += 1
                continue
            if r.sujeto_propuesto is not None and not r.sujeto_propuesto.strip():
                metrics["rel_dropped_sujeto_invalido"] += 1
                continue
            if (
                r.sujeto_propuesto_padre_sugerido is not None
                and r.sujeto_propuesto_padre_sugerido not in SUJETOS_CATALOGO_SET
            ):
                r = r.model_copy(update={"sujeto_propuesto_padre_sugerido": None})
            out_relations.append(r)
            continue

        src = by_local.get(r.source)
        tgt = by_local.get(r.target)
        if src is None or tgt is None:
            metrics["rel_dropped_dangling_ref"] += 1
            continue
        if not is_valid_triple(src.type, r.predicate, tgt.type):
            metrics["rel_dropped_domain_range"] += 1
            continue
        out_relations.append(r)

    metrics["relations_out"] = len(out_relations)
    return ExtractionOut(entities=out_entities, relations=out_relations), metrics


def empty_metrics() -> dict[str, int]:
    return {
        "entities_in": 0,
        "entities_out": 0,
        "relations_in": 0,
        "relations_out": 0,
        "rel_dropped_unknown_predicate": 0,
        "rel_dropped_dangling_ref": 0,
        "rel_dropped_domain_range": 0,
        "rel_dropped_sujeto_invalido": 0,
    }


def merge_metrics(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    out = empty_metrics()
    for k in out:
        out[k] = a.get(k, 0) + b.get(k, 0)
    return out
