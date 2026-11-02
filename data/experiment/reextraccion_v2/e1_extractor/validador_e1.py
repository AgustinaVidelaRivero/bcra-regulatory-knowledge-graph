"""
validador_e1.py — Validación determinística de la salida del extractor E1 (T3).

Código puro, sin LLM (principio 2.b del diseño: lo determinístico va en
código). Toma el input del tool call del extractor y el chunk de E0, y valida:

  1. Estructura parseable (dict con entities/relations; coerción defensiva de
     listas serializadas como string — lección heredada del schema v2).
  2. Conformidad con el esquema v2: types contra ENTITY_TYPES, predicados y
     firmas de aristas contra la matriz DOMAIN_RANGE, sujetos contra el
     catálogo cerrado (sujeto_id ∈ catálogo; sujeto_id/sujeto_propuesto
     mutuamente excluyentes; padre sugerido fuera de catálogo se anula).
  3. Provenance presente en TODO elemento: campo `punto` obligatorio y dentro
     del conjunto admitido del chunk (punto propio + unidades de herencia).

Todo rechazo queda REGISTRADO con motivo estable (input del mini-ratchet de
E3, que en esta fase solo se registra — no hay re-extracción acá). Los
rechazos son por elemento: un elemento inválido no tumba el chunk; una
estructura no parseable sí (rechazo a nivel chunk).
"""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from dataclasses import dataclass, field

import comun_e1  # noqa: F401  (sys.path para schema)
from comun_e1 import chunk_flaggeado, puntos_admitidos, rol_documental_de_punto
from schema import (
    ENTITY_TYPES,
    PREDICATES,
    SUJETO_PREDICATES,
    SUJETOS_CATALOGO_SET,
    is_valid_triple,
)


@dataclass
class ResultadoValidacion:
    chunk_id: str
    entidades: list[dict] = field(default_factory=list)
    relaciones: list[dict] = field(default_factory=list)
    omisiones_no_prosa: list[str] = field(default_factory=list)
    rechazos: list[dict] = field(default_factory=list)      # motivo registrado
    advertencias: list[dict] = field(default_factory=list)  # registro, no rechazo
    metricas: dict = field(default_factory=dict)
    # U-PROMPT-R2: "r2" cuando la salida venía en la forma r2 y se tradujo (marca que leen la NOTA de E3 y la
    # guarda ampliada del ratchet). None en los perfiles existentes: la clave no aparece en as_dict.
    forma_salida: str | None = None

    @property
    def chunk_rechazado(self) -> bool:
        return any(r["nivel"] == "chunk" for r in self.rechazos)

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "entidades": self.entidades,
            "relaciones": self.relaciones,
            "omisiones_no_prosa": self.omisiones_no_prosa,
            "rechazos": self.rechazos,
            "advertencias": self.advertencias,
            "metricas": self.metricas,
            **({"forma_salida": self.forma_salida} if self.forma_salida is not None else {}),
        }


def _rechazo(nivel: str, motivo: str, detalle: str, elemento=None) -> dict:
    r = {"nivel": nivel, "motivo": motivo, "detalle": detalle}
    if elemento is not None:
        r["elemento"] = elemento
    return r


def _coerce_lista(valor):
    """entities/relations pueden llegar como string JSON (slip conocido del
    extractor v2). Coerción defensiva; si no es lista al final, es None."""
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except json.JSONDecodeError:
            return None
    return valor if isinstance(valor, list) else None


def _str_o_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return None


SEPARADOR_UMBRALES = " | "

# U-PROMPT-R2, P3 (nota del 04/10/2026 al mandato, punto a): con la forma r2, las correcciones de validador_r2
# (alias y forma del tipo y del predicado, sujeto_id fuera del catálogo) se aplican acá, antes de E3, con la misma
# política y el mismo código (pyd_r2/code/validador_r2.py). Candado: el sha de la política de la decisión 10 del
# mandato de U-R2-CODIGO (corpus_v2/r1_e4.py, POLITICA_R2_SHA256).
POLITICA_R2_SHA256 = "82e8752aea1d6ad869d6023d303c0af45182dd9333753681787d7a581ef6d00b"
_CORRECCIONES_R2: tuple | None = None


def correcciones_r2():
    """(validador_r2, política) para las correcciones de la forma r2. Frena si la política no es la del candado."""
    global _CORRECCIONES_R2
    if _CORRECCIONES_R2 is None:
        ruta = comun_e1.REPO / "data" / "experiment" / "pyd_r2" / "code"
        if str(ruta) not in sys.path:
            sys.path.insert(0, str(ruta))
        import validador_r2  # noqa: PLC0415 — solo con la forma r2
        pol = validador_r2.politica_default()
        if pol.sha256 != POLITICA_R2_SHA256:
            raise RuntimeError(f"política r2 con sha {pol.sha256[:12]}… (esperado {POLITICA_R2_SHA256[:12]}…)")
        _CORRECCIONES_R2 = (validador_r2, pol)
    return _CORRECCIONES_R2


def _omision_r2_como_texto(o: dict) -> str | None:
    """Una omisión de la forma r2 como string de omisiones_no_prosa: «[categoría] tramo — nota», con
    «(source → destino)» en relacion_sin_predicado."""
    cat, tramo, nota = (_str_o_none(o.get(k)) for k in ("categoria", "tramo", "nota"))
    if not (cat or tramo or nota):
        return None
    txt = f"[{cat or 'sin_categoria'}] {tramo or ''}".rstrip()
    if nota:
        txt += f" — {nota}"
    if cat == "relacion_sin_predicado" and (o.get("source") or o.get("destino")):
        txt += f" ({o.get('source') or '?'} → {o.get('destino') or '?'})"
    return txt


def proyectar_r2(tool_input: dict) -> tuple[dict, dict]:
    """Traduce la salida de E1 en la forma «r2» a la forma v3 que leen E3 y el ratchet, sobre una COPIA (el crudo
    no se muta; validador_r2 lo lee íntegro). Nota del 03/10/2026 al pie del mandato de U-PROMPT-R2 (punto 4 del
    §10 del diseño):
      - relación de sujeto con `sujeto_mencion` y sin `sujeto_id` → `sujeto_propuesto` = la mención; con
        `sujeto_id`, se descarta el padre sugerido (en r2 el padre va solo sin id);
      - entidad: los tramos de `umbrales` → properties["umbrales"], unidos por « | »; `otras_propiedades` →
        properties, con el prefijo «otras_propiedades.» si la clave ya está;
      - `omisiones` → `omisiones_no_prosa`, un string por omisión.
    El tramo de evidencia no se traduce: es evidencia, no contenido. Devuelve (copia, contadores)."""
    out = copy.deepcopy(tool_input)
    cont: Counter = Counter()
    for nombre in ("entities", "relations"):
        lista = _coerce_lista(out.get(nombre))
        if lista is not None and not isinstance(out.get(nombre), list):
            out[nombre] = lista     # string JSON: la traducción trabaja sobre la lista parseada
    for e in out.get("entities") if isinstance(out.get("entities"), list) else []:
        if not isinstance(e, dict):
            continue
        props = e.get("properties") if isinstance(e.get("properties"), dict) else {}
        umb = e.pop("umbrales", None)
        tramos = [u["tramo"] for u in umb if isinstance(u, dict) and isinstance(u.get("tramo"), str)
                  and u["tramo"].strip()] if isinstance(umb, list) else []
        if tramos:
            props["umbrales"] = SEPARADOR_UMBRALES.join(tramos)
            cont["umbrales_a_properties"] += 1
        otras = e.pop("otras_propiedades", None)
        if isinstance(otras, dict):
            for k, v in otras.items():
                props[k if k not in props else f"otras_propiedades.{k}"] = v
                cont["otras_propiedades_a_properties"] += 1
        if props or "properties" in e:
            e["properties"] = props
    for r in out.get("relations") if isinstance(out.get("relations"), list) else []:
        if not isinstance(r, dict) or r.get("predicate") not in ("aplica_a", "ejecuta"):
            continue
        if _str_o_none(r.get("sujeto_id")) is None:
            mencion = _str_o_none(r.get("sujeto_mencion"))
            if mencion is not None and _str_o_none(r.get("sujeto_propuesto")) is None:
                r["sujeto_propuesto"] = mencion
                cont["mencion_sin_id_a_sujeto_propuesto"] += 1
        elif r.pop("sujeto_propuesto_padre_sugerido", None) is not None:
            cont["padre_sugerido_con_id_descartado"] += 1
    oms = out.pop("omisiones", None)
    if isinstance(oms, list):
        textos = [t for t in (_omision_r2_como_texto(o) for o in oms if isinstance(o, dict)) if t]
        out["omisiones_no_prosa"] = textos
        cont["omisiones_a_omisiones_no_prosa"] += len(textos)
    return out, dict(sorted(cont.items()))


def corregir_r2(tool_input: dict, esquema) -> tuple[dict, list[dict]]:
    """Nota del 04/10/2026 al mandato de U-PROMPT-R2, punto a: las correcciones de validador_r2, antes de E3 y
    sobre una COPIA (el crudo no se muta):
      - tipo de entidad fuera de la lista: forma y alias de la política (validador_r2.resolver_tipo);
      - predicado fuera de la lista: forma y alias (validador_r2.resolver_predicado);
      - `sujeto_propuesto`, que no es campo de la forma r2: se descarta (validador_r2 lo deja en los campos no
        definidos y no lo lee).
    Lo que no resuelve queda como vino y la validación lo rechaza. La del sujeto_id fuera del catálogo se aplica
    en validar_salida, que tiene el catálogo. Devuelve (copia, correcciones)."""
    V, pol = correcciones_r2()
    out = copy.deepcopy(tool_input)
    corr: list[dict] = []
    for nombre in ("entities", "relations"):
        lista = _coerce_lista(out.get(nombre))
        if lista is not None and not isinstance(out.get(nombre), list):
            out[nombre] = lista
    for i, e in enumerate(out.get("entities") if isinstance(out.get("entities"), list) else []):
        if isinstance(e, dict) and e.get("type") not in esquema.entity_types:
            t, trat = V.resolver_tipo(e.get("type"), pol)
            if t is not None:
                corr.append({"elemento": f"entities[{i}]", "campo": "type", "original": e.get("type"),
                             "corregido": t, "tratamiento": trat})
                e["type"] = t
    for i, r in enumerate(out.get("relations") if isinstance(out.get("relations"), list) else []):
        if not isinstance(r, dict):
            continue
        if r.get("predicate") not in esquema.predicates:
            p, trat = V.resolver_predicado(r.get("predicate"), pol)
            if p is not None:
                corr.append({"elemento": f"relations[{i}]", "campo": "predicate", "original": r.get("predicate"),
                             "corregido": p, "tratamiento": trat})
                r["predicate"] = p
        if "sujeto_propuesto" in r:
            corr.append({"elemento": f"relations[{i}]", "campo": "sujeto_propuesto",
                         "original": r.pop("sujeto_propuesto"), "corregido": None,
                         "tratamiento": "fuera_de_la_forma_r2_descartado"})
    return out, corr


def validar_salida(tool_input, chunk: dict, canal_abierto: bool = False,
                   esquema=None) -> ResultadoValidacion:
    """Valida el input del tool call de un chunk. Devuelve elementos aceptados
    (normalizados, con provenance completa {to, archivo, punto, rol_documental})
    y rechazos con motivo registrado.

    canal_abierto (experimental, explícito, default False = comportamiento de
    producción sin cambio alguno): habilita los campos tipo_propuesto (en
    entidades, junto a type) y predicado_propuesto (en relaciones, junto a
    predicate), calcados de sujeto_propuesto. Exclusión mutua exacta con
    type/predicate; los enums no se relajan. Una propuesta transportada por un
    elemento que este validador rechaza NO se pierde para la medición: vive en
    tool_input_crudo (el validador no muta su input).

    esquema (U-CABLE-V3): vocabulario inyectado (perfil_e1.EsquemaValidacion)
    contra el que se validan types, predicados, firmas y sujeto_id. Con el
    default None el comportamiento es EXACTAMENTE el de producción (los
    imports de schema v2 de arriba). En modo v3 el esquema es el CONGELADO
    completo (9 tipos / 13 predicados / catálogo de 102) y además rige la
    normalización de Obligacion.properties.tipo: un valor fuera del enum de 6
    se normaliza a "otra" con contador visible en metricas — REGISTRO, NO
    RECHAZO (resolución 2 del freno 1; vigilancia (5) del laudo de congelado
    con contador separado para el valor retirado requisito_de_estructura)."""
    _ent_types = ENTITY_TYPES if esquema is None else esquema.entity_types
    _preds = PREDICATES if esquema is None else esquema.predicates
    _suj_preds = SUJETO_PREDICATES if esquema is None else esquema.sujeto_predicates
    _suj_set = SUJETOS_CATALOGO_SET if esquema is None else esquema.sujetos_catalogo_set
    _firma = is_valid_triple if esquema is None else esquema.firma_valida
    _tipo_enum = None if esquema is None else esquema.obligacion_tipo_enum
    _tipo_retirados = () if esquema is None else esquema.obligacion_tipo_retirados
    contador_tipo = {"norm": 0, "retirado": 0}

    res = ResultadoValidacion(chunk_id=chunk["id"])
    admitidos = set(puntos_admitidos(chunk))
    forma_r2 = esquema is not None and getattr(esquema, "forma_salida", "v3") == "r2"
    proyeccion: dict = {}
    correcciones: list[dict] = []

    def _fin(n_ent: int, n_rel: int) -> ResultadoValidacion:
        res.metricas = _metricas(res, n_ent, n_rel)
        if forma_r2:
            # U-PROMPT-R2: marca de la forma r2, contadores de la traducción y correcciones, solo en ese perfil.
            res.forma_salida = "r2"
            res.metricas["proyeccion_r2"] = proyeccion
            res.metricas["correcciones_r2"] = correcciones
        if _tipo_enum is not None:
            # Contadores SIEMPRE visibles en modo v3 (el "= 0" es el resultado
            # esperado de la vigilancia y debe verse); NUNCA presentes con
            # esquema None (salida dev byte-idéntica).
            res.metricas["tipo_obligacion_normalizados"] = contador_tipo["norm"]
            res.metricas["tipo_obligacion_requisito_de_estructura"] = \
                contador_tipo["retirado"]
        return res

    # --- Nivel chunk: estructura ---
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError as e:
            res.rechazos.append(_rechazo("chunk", "salida_no_parseable", f"JSON inválido: {e}"))
            return _fin(0, 0)
    if not isinstance(tool_input, dict):
        res.rechazos.append(_rechazo("chunk", "salida_no_dict", f"tipo {type(tool_input).__name__}"))
        return _fin(0, 0)
    if forma_r2:
        tool_input, correcciones = corregir_r2(tool_input, esquema)
        tool_input, proyeccion = proyectar_r2(tool_input)

    entities = _coerce_lista(tool_input.get("entities"))
    relations = _coerce_lista(tool_input.get("relations"))
    if entities is None or relations is None:
        res.rechazos.append(_rechazo(
            "chunk", "entities_o_relations_invalidos",
            "entities/relations ausentes o no-lista (ni siquiera como string JSON)"))
        return _fin(0, 0)

    omisiones = tool_input.get("omisiones_no_prosa") or []
    if isinstance(omisiones, list):
        res.omisiones_no_prosa = [o for o in omisiones if isinstance(o, str) and o.strip()]

    # --- Entidades ---
    by_local: dict[str, dict] = {}
    for i, e in enumerate(entities):
        ref = f"entities[{i}]"
        if not isinstance(e, dict):
            res.rechazos.append(_rechazo("entidad", "entidad_no_dict", ref, e))
            continue
        local_id = _str_o_none(e.get("local_id"))
        etype = e.get("type")
        label = _str_o_none(e.get("label"))
        punto = _str_o_none(e.get("punto"))

        tipo_prop = _str_o_none(e.get("tipo_propuesto")) if canal_abierto else None

        if local_id is None:
            res.rechazos.append(_rechazo("entidad", "local_id_ausente", ref, e))
            continue
        if local_id in by_local:
            res.rechazos.append(_rechazo("entidad", "local_id_duplicado", f"{ref}: '{local_id}'", e))
            continue
        if tipo_prop is not None:
            # Canal abierto: tipo propuesto fuera de esquema. Exclusión mutua
            # exacta con type (calcada de sujeto_id/sujeto_propuesto): un tipo
            # fuera de esquema jamás entra silencioso en el enum.
            if etype is not None:
                res.rechazos.append(_rechazo(
                    "entidad", "tipo_canal_invalido",
                    f"{ref} ({local_id}): requiere exactamente UNO de type/tipo_propuesto", e))
                continue
        elif etype not in _ent_types:
            res.rechazos.append(_rechazo("entidad", "type_invalido", f"{ref}: '{etype}'", e))
            continue
        if label is None:
            res.rechazos.append(_rechazo("entidad", "label_vacio", ref, e))
            continue
        if punto is None:
            res.rechazos.append(_rechazo("entidad", "punto_ausente", f"{ref} ({local_id})", e))
            continue
        if punto not in admitidos:
            res.rechazos.append(_rechazo(
                "entidad", "punto_fuera_de_admitidos",
                f"{ref} ({local_id}): '{punto}' ∉ {sorted(admitidos)}", e))
            continue

        props_in = e.get("properties") or {}
        props = (
            {str(k): ("" if v is None else str(v)) for k, v in props_in.items()}
            if isinstance(props_in, dict) else {}
        )

        # Resolución 2 del freno 1 de U-CABLE-V3 (SOLO modo v3): un valor de
        # Obligacion.properties.tipo fuera del enum congelado se normaliza a
        # "otra" y se CUENTA — registro, no rechazo; el valor retirado
        # requisito_de_estructura lleva contador separado (vigilancia (5)).
        if (_tipo_enum is not None and etype == "Obligacion"
                and "tipo" in props and props["tipo"] not in _tipo_enum):
            original = props["tipo"]
            props["tipo"] = "otra"
            contador_tipo["norm"] += 1
            if original in _tipo_retirados:
                contador_tipo["retirado"] += 1
            res.advertencias.append({
                "tipo": "tipo_obligacion_fuera_de_enum", "local_id": local_id,
                "detalle": f"'{original}' normalizado a 'otra' (registro, no rechazo)"})

        norm = {
            "local_id": local_id,
            "type": etype,
            "label": label,
            "properties": props,
            "provenance": {
                "to": chunk["to"],
                "archivo": chunk["archivo"],
                "punto": punto,
                "rol_documental": rol_documental_de_punto(chunk, punto),
            },
        }
        if canal_abierto:
            # junto a type, análogo a sujeto_propuesto en relaciones: la clave
            # existe en TODA entidad validada de una corrida con canal abierto
            # (None cuando la entidad usa el enum). Con el flag apagado la
            # clave NO existe: salida byte-idéntica a producción.
            norm["tipo_propuesto"] = tipo_prop
        if forma_r2:
            # U-PROMPT-R2, P3: el índice del crudo, para que el ensamblado r2 tome solo lo que pasó por E3 (nota del
            # 04/10/2026, punto b). render_extraccion (comun_e3.py) no lo lee: el mensaje de E3 no cambia.
            norm["indice_crudo"] = i
        by_local[local_id] = norm
        res.entidades.append(norm)

        if len(label.split()) > 12:
            res.advertencias.append({
                "tipo": "label_largo", "local_id": local_id,
                "detalle": f"{len(label.split())} palabras (regla: ≤8, tolerancia 12)"})

    # --- Relaciones ---
    for i, r in enumerate(relations):
        ref = f"relations[{i}]"
        if not isinstance(r, dict):
            res.rechazos.append(_rechazo("relacion", "relacion_no_dict", ref, r))
            continue
        pred = r.get("predicate")
        pred_prop = _str_o_none(r.get("predicado_propuesto")) if canal_abierto else None
        if pred_prop is not None:
            # Canal abierto: predicado propuesto fuera de esquema. Exclusión
            # mutua exacta con predicate (calcada de sujeto_id/sujeto_propuesto).
            if pred is not None:
                res.rechazos.append(_rechazo(
                    "relacion", "predicado_canal_invalido",
                    f"{ref}: requiere exactamente UNO de predicate/predicado_propuesto", r))
                continue
        elif pred not in _preds:
            res.rechazos.append(_rechazo("relacion", "predicado_invalido", f"{ref}: '{pred}'", r))
            continue

        punto = _str_o_none(r.get("punto"))
        if punto is None:
            res.rechazos.append(_rechazo("relacion", "punto_ausente", f"{ref} ({pred})", r))
            continue
        if punto not in admitidos:
            res.rechazos.append(_rechazo(
                "relacion", "punto_fuera_de_admitidos",
                f"{ref} ({pred}): '{punto}' ∉ {sorted(admitidos)}", r))
            continue

        source = _str_o_none(r.get("source"))
        target = _str_o_none(r.get("target"))
        sujeto_id = _str_o_none(r.get("sujeto_id"))
        sujeto_prop = _str_o_none(r.get("sujeto_propuesto"))
        padre_sug = _str_o_none(r.get("sujeto_propuesto_padre_sugerido"))

        if pred_prop is not None:
            # Predicado propuesto: no existe firma en DOMAIN_RANGE contra la
            # cual validar (ni forma de saber si el extremo es un sujeto), así
            # que extremos y sujeto_* pasan normalizados tal como vienen. El
            # anclaje (`punto`) ya se validó arriba como en toda relación.
            pass
        elif pred in _suj_preds:
            # Slip predecible heredado del v2: extremo sujeto mandado además
            # en target (aplica_a) / source (ejecuta) → se ignora ese campo.
            if pred == "aplica_a":
                target = None
            else:
                source = None

            if (sujeto_id is None) == (sujeto_prop is None):
                res.rechazos.append(_rechazo(
                    "relacion", "sujeto_extremo_invalido",
                    f"{ref} ({pred}): requiere exactamente UNO de sujeto_id/sujeto_propuesto", r))
                continue
            if sujeto_id is not None and sujeto_id not in _suj_set:
                if not forma_r2:
                    res.rechazos.append(_rechazo(
                        "relacion", "sujeto_id_fuera_de_catalogo", f"{ref}: '{sujeto_id}'", r))
                    continue
                # Forma r2 (nota del 04/10/2026, punto a): el sujeto_id es una sugerencia; fuera del catálogo, la
                # relación queda con la mención (o el id, como texto) de propuesto, como en validador_r2, que la
                # manda al registro de no mapeados.
                correcciones.append({"elemento": ref, "campo": "sujeto_id", "original": sujeto_id, "corregido": None,
                                     "tratamiento": "fuera_de_catalogo_a_sujeto_propuesto"})
                sujeto_prop, sujeto_id = _str_o_none(r.get("sujeto_mencion")) or sujeto_id, None
            if padre_sug is not None and sujeto_prop is None:
                res.rechazos.append(_rechazo(
                    "relacion", "padre_sugerido_sin_propuesto", ref, r))
                continue
            if padre_sug is not None and padre_sug not in _suj_set:
                padre_sug = None  # pista inválida: se anula, no invalida la relación

            extremo_chunk = source if pred == "aplica_a" else target
            campo = "source" if pred == "aplica_a" else "target"
            if extremo_chunk is None:
                res.rechazos.append(_rechazo(
                    "relacion", "extremo_chunk_ausente", f"{ref} ({pred}): falta {campo}", r))
                continue
            ent = by_local.get(extremo_chunk)
            if ent is None:
                res.rechazos.append(_rechazo(
                    "relacion", "ref_colgante", f"{ref} ({pred}): {campo}='{extremo_chunk}'", r))
                continue
            src_t, tgt_t = (ent["type"], "Sujeto") if pred == "aplica_a" else ("Sujeto", ent["type"])
            if not _firma(src_t, pred, tgt_t):
                res.rechazos.append(_rechazo(
                    "relacion", "firma_invalida", f"{ref}: {src_t} --{pred}--> {tgt_t}", r))
                continue
        else:
            # Forma r2: la mención del sujeto en un predicado que no es de sujeto se rechaza, como en validador_r2.
            if sujeto_id or sujeto_prop or padre_sug or (forma_r2 and _str_o_none(r.get("sujeto_mencion"))):
                res.rechazos.append(_rechazo(
                    "relacion", "sujeto_en_predicado_no_sujeto",
                    f"{ref}: sujeto_* solo vale en {_suj_preds}, no en {pred}", r))
                continue
            if source is None or target is None:
                res.rechazos.append(_rechazo(
                    "relacion", "extremo_chunk_ausente", f"{ref} ({pred}): requiere source y target", r))
                continue
            src_e, tgt_e = by_local.get(source), by_local.get(target)
            if src_e is None or tgt_e is None:
                res.rechazos.append(_rechazo(
                    "relacion", "ref_colgante",
                    f"{ref} ({pred}): source='{source}' target='{target}'", r))
                continue
            if not _firma(src_e["type"], pred, tgt_e["type"]):
                res.rechazos.append(_rechazo(
                    "relacion", "firma_invalida",
                    f"{ref}: {src_e['type']} --{pred}--> {tgt_e['type']}", r))
                continue

        rel_out = {
            "source": source,
            "target": target,
            "predicate": pred,
            "sujeto_id": sujeto_id,
            "sujeto_propuesto": sujeto_prop,
            "sujeto_propuesto_padre_sugerido": padre_sug,
            "provenance": {
                "to": chunk["to"],
                "archivo": chunk["archivo"],
                "punto": punto,
                "rol_documental": rol_documental_de_punto(chunk, punto),
            },
        }
        if canal_abierto:
            # junto a predicate, análogo a sujeto_propuesto: la clave existe
            # en TODA relación validada de una corrida con canal abierto (None
            # cuando la relación usa el enum). Con el flag apagado la clave NO
            # existe: salida byte-idéntica a producción.
            rel_out["predicado_propuesto"] = pred_prop
        if forma_r2:
            rel_out["indice_crudo"] = i     # U-PROMPT-R2, P3: ver la entidad
        res.relaciones.append(rel_out)

    # --- Registro del tratamiento de flags (no rechaza: insumo de E3) ---
    if chunk_flaggeado(chunk):
        extrajo_algo = any(e["type"] != "TextoOrdenado" for e in res.entidades)
        if extrajo_algo and not res.omisiones_no_prosa:
            res.advertencias.append({
                "tipo": "flag_sin_omisiones_declaradas",
                "detalle": "chunk flaggeado tabular/formula con extracción y sin omisiones registradas"})
        if not extrajo_algo and not res.omisiones_no_prosa:
            res.advertencias.append({
                "tipo": "flag_vacio_sin_registro",
                "detalle": "chunk flaggeado sin extracción y sin omisiones registradas"})

    return _fin(len(entities), len(relations))


def _metricas(res: ResultadoValidacion, n_ent_in: int, n_rel_in: int) -> dict:
    por_motivo: dict[str, int] = {}
    for r in res.rechazos:
        por_motivo[r["motivo"]] = por_motivo.get(r["motivo"], 0) + 1
    return {
        "entities_in": n_ent_in,
        "entities_out": len(res.entidades),
        "relations_in": n_rel_in,
        "relations_out": len(res.relaciones),
        "rechazos": len(res.rechazos),
        "rechazos_por_motivo": por_motivo,
        "advertencias": len(res.advertencias),
    }
