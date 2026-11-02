"""
r1_e4.py — B1.2: E4 DETERMINÍSTICO (sin LLM) sobre el grafo ya fusionado
cross-TO (salida de r1_invariantes.merge_grafos_guardado).

(a) resolver_propuestos: Sujeto propuesto (nivel=propuesto, cuarentena) →
    id del catálogo cerrado (esquema_v2_clases.json: 65 clases/instancias +
    5 roles) SOLO por criterios de igualdad declarados, en este orden y sin
    ambigüedad (si dos criterios apuntan a ids distintos → cuarentena con
    motivo "ambiguo"):
      label_exacto          norm(label) == norm(label_catálogo)
      alias_exacto          norm(label) == norm(alias declarado)
      id_slug               slug(label) == slug del id del catálogo
      label_singularizado   norm(label sin paréntesis), singularizando cada
                            token, == ídem del label del catálogo
      alias_en_parentesis   la sigla entre paréntesis del label es alias
                            declarado Y (el padre_sugerido coincide con ese
                            id O no hay padre_sugerido)
    Lo que no resuelve queda en cuarentena tal cual (nivel=propuesto,
    cuarentena=true, padre_sugerido si lo hubo). NUNCA se crea una clase.
    Al resolver: el nodo propuesto desaparece, su provenance se acumula en
    el nodo del catálogo (se crea desde el catálogo si no existía en el
    grafo), sus aristas se re-apuntan (dedup de triplas con provenances
    acumuladas) y el nodo del catálogo recibe `alias_resueltos` (lista) para
    conservar el alias (principio 2.e: merge aditivo, reversible, registrado).

(b) canonizar_texto_ordenado: un único nodo TextoOrdenado por TO, con id y
    `archivo` derivados de la provenance (archivo del PDF según E0). Todo
    otro nodo TextoOrdenado cuyas provenances pertenecen a un TO (p. ej. el
    emitido por ric::4.1.1.4 con archivo="normas sobre Capitales mínimos…")
    se elimina y sus aristas se re-apuntan al canónico, con registro.

(c) filtrar_conflictos: de los conflictos de properties (intra-TO de E2 +
    cross-TO del merge), `materia`/`version` de TextoOrdenado salen del
    registro de conflictos y quedan como VARIANTES (insumo descriptivo);
    el resto (Operacion.tipo, *.descripcion, …) se persiste como
    conflictos REALES, sin resolver (insumo de un E4-LLM futuro).
"""

from __future__ import annotations

import json
import re
from copy import deepcopy

import r1_comun as C
from e2_lib import slugify_full                    # noqa: E402 (se importa)

PROPS_VARIANTE_TO = ("materia", "version")


# ----------------------------------------------------------------------- #
# (a) resolución de propuestos                                            #
# ----------------------------------------------------------------------- #
def _singular(w: str) -> str:
    if len(w) > 4 and w.endswith("es") and w[-3] in "lrndzsjy":
        return w[:-2]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def _norm_sing(s: str) -> str:
    return " ".join(_singular(w) for w in C.norm(s).split())


def _sin_parentesis(s: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", s or "")


def _parentesis(s: str) -> str | None:
    m = re.search(r"\(([^)]+)\)", s or "")
    return m.group(1) if m else None


def indice_catalogo(catalogo: dict) -> dict[tuple[str, str], str]:
    """(criterio, clave) → id del catálogo. Construido una sola vez."""
    idx: dict[tuple[str, str], str] = {}

    def put(k: tuple[str, str], i: str) -> None:
        # Si dos entradas del catálogo colisionan en una clave, la clave se
        # marca ambigua y no resuelve (nunca se elige en silencio).
        if k in idx and idx[k] != i:
            idx[k] = "__AMBIGUO__"
        else:
            idx.setdefault(k, i)

    entradas = [(e["id"], e["label"], e.get("alias") or []) for e in catalogo["clases"]]
    entradas += [(r["id"], r["label"], []) for r in catalogo["roles"]]
    for i, label, alias in entradas:
        put(("label_exacto", C.norm(label)), i)
        put(("id_slug", i[len("Sujeto_"):]), i)
        put(("label_singularizado", _norm_sing(_sin_parentesis(label))), i)
        for a in alias:
            put(("alias_exacto", C.norm(a)), i)
    return idx


def resolver_label(label: str, padre_sugerido: str | None,
                   idx: dict[tuple[str, str], str]) -> tuple[str | None, str, list[tuple[str, str]]]:
    """→ (id_resuelto | None, motivo, candidatos). Determinístico."""
    cands: list[tuple[str, str]] = []
    for crit, clave in (("label_exacto", C.norm(label)),
                        ("alias_exacto", C.norm(label)),
                        ("id_slug", slugify_full(label)),
                        ("label_singularizado", _norm_sing(_sin_parentesis(label)))):
        hit = idx.get((crit, clave))
        if hit and hit != "__AMBIGUO__":
            cands.append((crit, hit))
    sigla = _parentesis(label)
    if sigla:
        hit = idx.get(("alias_exacto", C.norm(sigla)))
        if hit and hit != "__AMBIGUO__" and (padre_sugerido in (None, "", hit)):
            cands.append(("alias_en_parentesis", hit))
    ids = {i for _, i in cands}
    if not cands:
        return None, "sin_match_en_catalogo", cands
    if len(ids) > 1:
        return None, "ambiguo", cands
    return cands[0][1], "resuelto_por_" + "+".join(sorted({c for c, _ in cands})), cands


def resolver_propuestos(kg: dict, catalogo: dict) -> dict:
    """Muta kg (nodes/edges). Devuelve registro con tabla por propuesto."""
    idx = indice_catalogo(catalogo)
    info_cat: dict[str, dict] = {}
    for e in catalogo["clases"]:
        info_cat[e["id"]] = {"label": e["label"], "nivel": e["nivel"]}
    for r in catalogo["roles"]:
        info_cat[r["id"]] = {"label": r["label"], "nivel": "rol"}

    nodes_by_id = {n["id"]: n for n in kg["nodes"]}
    tabla: list[dict] = []
    remap: dict[str, str] = {}
    for n in list(kg["nodes"]):
        if n["type"] != "Sujeto" or n.get("properties", {}).get("nivel") != "propuesto":
            continue
        padre = n["properties"].get("padre_sugerido")
        rid, motivo, cands = resolver_label(n["label"], padre, idx)
        fila = {"id_propuesto": n["id"], "label": n["label"], "padre_sugerido": padre,
                "n_provenances": len(n.get("provenances", [])),
                "candidatos": [list(c) for c in cands]}
        if rid is None:
            fila.update({"estado": "cuarentena", "motivo": motivo,
                         "resuelto_a": None})
            tabla.append(fila)
            continue
        if rid not in info_cat:
            raise RuntimeError(f"resolución a id fuera de catálogo: {rid}")
        fila.update({"estado": "resuelto", "motivo": motivo, "resuelto_a": rid,
                     "label_catalogo": info_cat[rid]["label"]})
        tabla.append(fila)
        remap[n["id"]] = rid
        destino = nodes_by_id.get(rid)
        if destino is None:
            destino = {"id": rid, "type": "Sujeto", "label": info_cat[rid]["label"],
                       "properties": {"nivel": info_cat[rid]["nivel"]},
                       "provenance": dict(n["provenance"]), "provenances": []}
            nodes_by_id[rid] = destino
            kg["nodes"].append(destino)
            fila["nodo_catalogo_creado"] = True
        vistos = {C.prov_key(p) for p in destino.get("provenances", [])}
        for p in n.get("provenances", []):
            if C.prov_key(p) not in vistos:
                destino.setdefault("provenances", []).append(p)
                vistos.add(C.prov_key(p))
        ar = destino["properties"].setdefault("alias_resueltos", [])
        if n["label"] not in ar:
            ar.append(n["label"])
        kg["nodes"].remove(n)
        del nodes_by_id[n["id"]]

    aristas_reapuntadas = _reapuntar(kg, remap)
    return {"tabla": tabla, "remap": remap, "aristas_reapuntadas": aristas_reapuntadas,
            "n_resueltos": sum(1 for f in tabla if f["estado"] == "resuelto"),
            "n_cuarentena": sum(1 for f in tabla if f["estado"] == "cuarentena"),
            "motivos": C.conteo([{"m": f["motivo"]} for f in tabla], "m")}


def _reapuntar(kg: dict, remap: dict[str, str]) -> int:
    """Re-apunta aristas según remap, fusionando triplas duplicadas con
    provenances acumuladas (dedup exacto). Devuelve cuántas se re-apuntaron."""
    if not remap:
        return 0
    edges_by_key: dict[tuple, dict] = {}
    n_re = 0
    for e in kg["edges"]:
        s, t = e["source"], e["target"]
        ns, nt = remap.get(s, s), remap.get(t, t)
        if (ns, nt) != (s, t):
            n_re += 1
            e["source"], e["target"] = ns, nt
        k = (ns, e["relation"], nt)
        if k in edges_by_key:
            m = edges_by_key[k]
            vistos = {C.prov_key(p) for p in m.get("provenances", [])}
            for p in e.get("provenances", []):
                if C.prov_key(p) not in vistos:
                    m.setdefault("provenances", []).append(p)
                    vistos.add(C.prov_key(p))
        else:
            edges_by_key[k] = e
    kg["edges"] = list(edges_by_key.values())
    return n_re


# ----------------------------------------------------------------------- #
# (b) TextoOrdenado solo desde provenance                                 #
# ----------------------------------------------------------------------- #
def id_texto_ordenado_canonico(archivo: str) -> str:
    # Misma convención de id de E2: TextoOrdenado_<slug(archivo)>.
    return f"TextoOrdenado_{slugify_full(archivo)}"


def canonizar_texto_ordenado(kg: dict) -> dict:
    archivos = {to: C.archivo_de_to(to) for to in C.TOS_ORDEN}
    canon = {to: id_texto_ordenado_canonico(a) for to, a in archivos.items()}
    nodes_by_id = {n["id"]: n for n in kg["nodes"]}
    registro: list[dict] = []
    remap: dict[str, str] = {}
    for n in list(kg["nodes"]):
        if n["type"] != "TextoOrdenado":
            continue
        tos = sorted({p["to"] for p in n.get("provenances", [])})
        if len(tos) != 1:
            raise RuntimeError(f"TextoOrdenado con provenance de {tos}: {n['id']}")
        to = tos[0]
        cid = canon[to]
        if n["id"] == cid:
            n["properties"]["archivo"] = archivos[to]
            continue
        destino = nodes_by_id.get(cid)
        if destino is None:
            raise RuntimeError(f"falta el TextoOrdenado canónico de {to}: {cid}")
        registro.append({"id_eliminado": n["id"], "label": n["label"],
                         "properties": deepcopy(n["properties"]),
                         "provenances": deepcopy(n.get("provenances", [])),
                         "reasignado_a": cid, "to": to,
                         "motivo": "TextoOrdenado espurio: el archivo emitido por E1 no es el "
                                   "del PDF del TO (provenance.archivo); la identidad del TO "
                                   "se toma SOLO de la provenance"})
        vistos = {C.prov_key(p) for p in destino.get("provenances", [])}
        for p in n.get("provenances", []):
            if C.prov_key(p) not in vistos:
                destino["provenances"].append(p)
                vistos.add(C.prov_key(p))
        remap[n["id"]] = cid
        kg["nodes"].remove(n)
        del nodes_by_id[n["id"]]
    n_re = _reapuntar(kg, remap)
    return {"canonicos": canon, "archivos": archivos, "eliminados": registro,
            "aristas_reapuntadas": n_re}


# ----------------------------------------------------------------------- #
# (c) filtro de ruido en conflictos                                       #
# ----------------------------------------------------------------------- #
def filtrar_conflictos(conflictos_intra: list[dict], conflictos_cross: list[dict]) -> dict:
    """conflictos_intra: items de e2_lib (id, property, conservado, descartado,
    chunk_id) con campo `to` agregado; conflictos_cross: items de
    ensamblar_corpus.merge_grafos (nivel, id, property, gana, pierde, to_perdedor)."""
    reales: list[dict] = []
    variantes: dict[str, dict[str, list[str]]] = {}
    n_var = 0
    for c in conflictos_intra:
        tipo = c["id"].split("_", 1)[0]
        if tipo == "TextoOrdenado" and c["property"] in PROPS_VARIANTE_TO:
            v = variantes.setdefault(c["id"], {}).setdefault(c["property"], [])
            for val in (c["conservado"], c["descartado"]):
                if val not in v:
                    v.append(val)
            n_var += 1
        else:
            reales.append({"origen": "intra_to", "to": c.get("to"), "tipo": tipo, **c})
    for c in conflictos_cross:
        tipo = c["id"].split("_", 1)[0]
        if tipo == "TextoOrdenado" and c["property"] in PROPS_VARIANTE_TO:
            v = variantes.setdefault(c["id"], {}).setdefault(c["property"], [])
            for val in (c["gana"], c["pierde"]):
                if val not in v:
                    v.append(val)
            n_var += 1
        else:
            reales.append({"origen": "cross_to", "tipo": tipo, **c})
    return {
        "n_total": len(conflictos_intra) + len(conflictos_cross),
        "n_variantes_to": n_var,
        "n_reales": len(reales),
        "reales_por_tipo_property": C.conteo(
            [{"k": f"{r['tipo']}.{r['property']}"} for r in reales], "k"),
        "variantes_texto_ordenado": variantes,
        "conflictos_reales": reales,
    }


# ----------------------------------------------------------------------- #
# (d) Perfil r2: resolución de sujetos por relación, entre E3 y E2,       #
#     y registro de no mapeados (L-ESQ-R2 §3.3 y §4; diseño de            #
#     U-LISTAS-NOMAP, P-c1 a P-c3 y P-d1 a P-d3; U-R2-CODIGO R3.b y c)     #
# ----------------------------------------------------------------------- #
PREDICADOS_SUJETO_R2 = ("aplica_a", "ejecuta")
CRITERIOS_R1 = ("label_exacto", "alias_exacto")
CRITERIOS_R2 = ("id_slug", "label_singularizado", "alias_en_parentesis")
# R3, lista inicial cerrada de expresiones colectivas, tomada de la redacción
# del prompt (prompt_e1.py:110: «las entidades», «los sujetos obligados»);
# se compara la mención normalizada, sin el artículo inicial.
EXPRESIONES_COLECTIVAS_R3 = ("entidades", "sujetos obligados", "entidad")
# U-OMISIONES-COD, grupo B, ítem f′ (opción (ii), elegida en la firma de la v7): el singular «entidad» es expresión de
# R3 solo en un TO con rol. En un TO sin rol no es expresión de R3: da `sin_match` y sigue la regla de siempre (la
# sugerencia del modelo, o cuarentena si no la hay); la parte A de la enmienda 6 no lo alcanza.
EXPRESIONES_SINGULARES_R3 = ("entidad",)
ARTICULOS = ("el", "la", "los", "las")


def _sin_articulo(s: str) -> str:
    w = C.norm(s).split()
    return " ".join(w[1:] if w and w[0] in ARTICULOS else w)


RE_ARTICULO_INICIAL = re.compile(r"^\s*(?:el|la|los|las)\s+", re.I)


def indice_desde_lista(filas: list[list[str]]) -> dict[tuple[str, str], str]:
    """El índice de E4 generado del catálogo r2 (indice_e4_r2.json: filas
    [criterio, clave, id], con __AMBIGUO__ donde dos entradas colisionan), en
    la forma de `indice_catalogo`."""
    return {(c, k): i for c, k, i in filas}


def _prefijos(idx: dict[tuple[str, str], str]) -> list[tuple[str, str]]:
    """(clave, id) para el calificador: label exacto, alias exacto y label
    singularizado, de más largo a más corto."""
    out = [(k, i) for (c, k), i in idx.items()
           if c in ("label_exacto", "alias_exacto", "label_singularizado") and k]
    return sorted(set(out), key=lambda x: (-len(x[0]), x[0], x[1]))


def resolver_mencion_r2(mencion: str, padre: str | None, idx: dict, prefijos: list,
                        rol_del_to: str | None) -> dict:
    """Reglas sobre la mención (P-c1): R1 label o alias exacto; R2 slug,
    singular o alias entre paréntesis; calificador (la mención empieza con el
    label o alias de una clase y sigue con texto: se resuelve a la clase y se
    guarda el calificador; L-ESQ-R2 §3.3); R3 expresión colectiva → sujeto por
    defecto del TO. Las reglas leen la mención sin su artículo inicial (la
    mención se copia con artículos; el catálogo no los lleva). Devuelve la
    regla que resuelve, el id, los candidatos y el motivo cuando no resuelve."""
    rid, motivo, cands = resolver_label(RE_ARTICULO_INICIAL.sub("", mencion), padre, idx)
    out = {"regla": None, "id": None, "criterios": sorted({c for c, _ in cands}),
           "candidatos": [list(c) for c in cands], "calificador": None, "motivo": None}
    if motivo == "ambiguo":
        out["motivo"] = "ambiguo"
        return out
    if rid is not None:
        crits = {c for c, _ in cands}
        out["regla"] = "R1" if crits & set(CRITERIOS_R1) else "R2"
        out["id"] = rid
        return out
    m_norm = C.norm(mencion)
    m_sing = _norm_sing(_sin_parentesis(mencion))
    hallados = []
    for clave, i in prefijos:
        if i == "__AMBIGUO__":
            continue
        for forma in (m_norm, m_sing, _sin_articulo(mencion)):
            if forma.startswith(clave + " ") and len(forma) > len(clave) + 1:
                hallados.append((len(clave), i, forma[len(clave) + 1:]))
                break
    if hallados:
        largo = max(h[0] for h in hallados)
        ids = sorted({h[1] for h in hallados if h[0] == largo})
        if len(ids) > 1:
            out["motivo"] = "ambiguo"
            out["candidatos"] = [["calificador", i] for i in ids]
            return out
        out.update(regla="R2_calificador", id=ids[0],
                   calificador=next(h[2] for h in hallados if h[0] == largo and h[1] == ids[0]))
        return out
    if _sin_articulo(mencion) in EXPRESIONES_COLECTIVAS_R3:
        if rol_del_to:
            out.update(regla="R3", id=rol_del_to)
            return out
        if _sin_articulo(mencion) not in EXPRESIONES_SINGULARES_R3:
            out["motivo"] = "colectivo_sin_sujeto_por_defecto"
            return out
    out["motivo"] = "sin_match"
    return out


MOTIVOS_PARTE_A = ("colectivo_sin_sujeto_por_defecto", "sin_mencion", "mencion_no_verificada")


def resolver_relaciones_r2(registros: list[dict], idx: dict, rol_por_archivo: dict,
                           versiones: dict, parte_a: bool = False) -> dict:
    """Resolución por relación de las relaciones de sujeto validadas por el
    perfil r2. Regla de decisión (L-ESQ-R2 §3.3, punto 5): la regla textual
    gana solo con R1; con R2, el calificador o R3 gana la sugerencia del
    modelo si la hay; sin regla, la sugerencia del modelo (R4). Siempre se
    registran los dos ids. Una mención que no verifica (`no`) no resuelve:
    queda la sugerencia del modelo o el registro (P-b4).

    `parte_a` (enmienda 6 a L-ESQ-R2, parte A, firmada el 06/10/2026; la
    cadena la activa en r2b): en un documento sin alcance (sin entrada en
    `rol_por_archivo`), la sugerencia del modelo no reemplaza a un sujeto que
    el texto no identifica. La expresión colectiva de la lista de R3 (regla 1,
    motivo `colectivo_sin_sujeto_por_defecto`) y la relación sin mención o con
    una mención que no verifica (regla 2, `sin_mencion` o
    `mencion_no_verificada`) van a cuarentena, después de R1 y antes de R4; la
    fila guarda la sugerencia y la mención del modelo. Con False (default),
    la regla de siempre.

    Muta cada relación de sujeto agregando `sujeto_id_resuelto` y
    `metodo_resolucion` (o, sin resolver, la clave de su fila del registro).
    Devuelve las filas de resolucion_sujetos.jsonl y las del registro de no
    mapeados (cuarentena, y resueltas a una clase con calificador como
    candidatas a id)."""
    prefijos = _prefijos(idx)
    resolucion, registro = [], []
    for reg in registros:
        val = reg.get("validacion") or {}
        cid, to = reg["chunk_id"], reg["to"]
        ents = {e["local_id"]: e for e in val.get("entidades", [])}
        rol = (rol_por_archivo.get(reg["archivo"]) or {}).get("rol_id")
        sin_alcance = parte_a and reg["archivo"] not in rol_por_archivo
        for r in val.get("relaciones", []):
            if r["predicate"] not in PREDICADOS_SUJETO_R2:
                continue
            extremo = r["source"] if r["predicate"] == "aplica_a" else r["target"]
            ent = ents.get(extremo) or {}
            mencion, nivel = r.get("sujeto_mencion"), r.get("mencion_verificada")
            modelo = r.get("sujeto_id_modelo")
            regla = (resolver_mencion_r2(mencion, r.get("padre_sugerido"), idx, prefijos, rol)
                     if mencion and nivel in ("exacta", "tokens") else
                     {"regla": None, "id": None, "criterios": [], "candidatos": [], "calificador": None,
                      "motivo": "mencion_no_verificada" if mencion else "sin_mencion"})
            final, metodo = None, None
            if regla["regla"] == "R1":
                final, metodo = regla["id"], "R1_" + "+".join(c for c in regla["criterios"] if c in CRITERIOS_R1)
            elif sin_alcance and regla["motivo"] in MOTIVOS_PARTE_A:
                pass                    # enmienda 6, parte A: cuarentena con la sugerencia guardada
            elif modelo:
                final, metodo = modelo, "R4_sugerencia_modelo"
            elif regla["regla"] == "R2":
                final, metodo = regla["id"], "R2_" + "+".join(regla["criterios"])
            elif regla["regla"] in ("R2_calificador", "R3"):
                final, metodo = regla["id"], regla["regla"]
            desacuerdo = bool(regla["id"] and modelo and regla["id"] != modelo)
            clave = {"to": to, "chunk_id": cid, "e0_sha256_completo": reg.get("e0_sha256_completo"),
                     "indice_relacion": r.get("indice_crudo"), "punto": r["punto"], "predicado": r["predicate"]}
            fila = {**clave, "mencion": mencion, "sujeto_mencion_modelo": r.get("sujeto_mencion_modelo"),
                    "mencion_verificada": nivel, "sujeto_id_modelo": modelo,
                    "regla_texto": regla["regla"], "id_regla_texto": regla["id"],
                    "criterios": regla["criterios"], "calificador": regla["calificador"],
                    "resuelto_a": final, "metodo_resolucion": metodo or "cuarentena",
                    "desacuerdo_regla_modelo": desacuerdo, "catalogo_sha256": versiones["catalogo_sha256"]}
            resolucion.append(fila)
            r["sujeto_id_resuelto"] = final
            r["metodo_resolucion"] = metodo or "cuarentena"
            if metodo == "R2_calificador":
                r["calificador"] = regla["calificador"]
            estado = None
            if final is None:
                id_crudo = (r.get("originales") or {}).get("sujeto_id")
                motivo = ("id_fuera_de_catalogo" if id_crudo else
                          "mencion_no_verificada" if nivel == "no" else regla["motivo"] or "sin_match")
                estado = "cuarentena"
            elif regla["regla"] == "R2_calificador" and final == regla["id"]:
                motivo, estado = "calificador", "resuelto_a_clase"
            if estado:
                registro.append({
                    **clave, "extremo_local_id": extremo, "extremo_tipo": ent.get("type"),
                    "extremo_label": ent.get("label"), "mencion": mencion,
                    "sujeto_mencion_modelo": r.get("sujeto_mencion_modelo"), "mencion_verificada": nivel,
                    "sujeto_id_modelo": modelo, "sujeto_id_crudo": (r.get("originales") or {}).get("sujeto_id"),
                    "padre_sugerido_crudo": r.get("padre_sugerido_crudo"),
                    "padre_sugerido": r.get("padre_sugerido"), "motivo": motivo,
                    "candidatos": regla["candidatos"], "calificador": regla["calificador"],
                    "categoria_no_mapeo": None, **versiones, "estado": estado,
                    "resuelto_a": final, "metodo": metodo,
                    "catalogo_sha256_resolucion": versiones["catalogo_sha256"] if final else None,
                    "id_nodo": None})
                if estado == "cuarentena":
                    r["registro_no_mapeados"] = {k: clave[k] for k in ("chunk_id", "indice_relacion")}
    return {"resolucion": resolucion, "registro": registro,
            "resumen": {"relaciones_de_sujeto": len(resolucion),
                        "por_metodo": C.conteo([{"m": f["metodo_resolucion"]} for f in resolucion], "m"),
                        "desacuerdos_regla_modelo": sum(f["desacuerdo_regla_modelo"] for f in resolucion),
                        "registro_por_estado": C.conteo([{"e": f["estado"]} for f in registro], "e"),
                        "registro_por_motivo": C.conteo([{"m": f["motivo"]} for f in registro], "m")}}


def reresolver_registro(filas: list[dict], idx: dict, rol_por_archivo: dict, archivo_por_to: dict,
                        catalogo_sha256: str) -> dict:
    """P-d3: re-resolución por programa de las filas en cuarentena cuando
    cambia el sha256 del catálogo. Cada fila se decide con la misma regla que
    `resolver_relaciones_r2` (R2-2 de U-RERESOL-CAT, decisión 2): R1 sobre la
    mención verificada; si la fila guarda una sugerencia del modelo (solo la
    parte A de la enmienda 6 deja una en cuarentena), sigue en cuarentena
    mientras el documento no tenga alcance y, si lo recibe, gana la sugerencia
    (R4), aunque la mención no verifique; sin sugerencia, R2, el calificador o
    R3 sobre la mención verificada. Una fila que resuelve pasa a `resuelto`
    (al calificador, `resuelto_a_clase`, como en la cadena) con el sha nuevo.
    Idempotente: re-aplicada con el mismo índice, no cambia nada. El método se
    escribe como en `resolver_relaciones_r2` (W2: `R1_` y `R2_` con sus
    criterios; el calificador y R3, con el nombre de la regla)."""
    prefijos = _prefijos(idx)
    out, cambiadas = [], 0
    for f in filas:
        g = dict(f)
        if f["estado"] == "cuarentena":
            archivo = archivo_por_to.get(f["to"])
            rol = (rol_por_archivo.get(archivo) or {}).get("rol_id")
            modelo = f.get("sujeto_id_modelo")
            r = (resolver_mencion_r2(f["mencion"], f.get("padre_sugerido"), idx, prefijos, rol)
                 if f.get("mencion") and f.get("mencion_verificada") in ("exacta", "tokens") else None)
            motivo = r["motivo"] if r else ("mencion_no_verificada" if f.get("mencion") else "sin_mencion")
            final, metodo = None, None
            if r and r["regla"] == "R1":
                final, metodo = r["id"], "R1_" + "+".join(c for c in r["criterios"] if c in CRITERIOS_R1)
            elif modelo and archivo not in rol_por_archivo and motivo in MOTIVOS_PARTE_A:
                pass                    # parte A: sigue en cuarentena mientras el documento no tenga alcance
            elif modelo:
                final, metodo = modelo, "R4_sugerencia_modelo"
            elif r and r["id"]:
                final, metodo = r["id"], ("R2_" + "+".join(r["criterios"]) if r["regla"] == "R2" else r["regla"])
            if final:
                g.update(estado="resuelto_a_clase" if metodo == "R2_calificador" else "resuelto", resuelto_a=final,
                         metodo=metodo, catalogo_sha256_resolucion=catalogo_sha256)
                if r and metodo != "R4_sugerencia_modelo":
                    g["calificador"] = r["calificador"]
                cambiadas += 1
        out.append(g)
    return {"filas": out, "resueltas_ahora": cambiadas, "catalogo_sha256": catalogo_sha256}


# ----------------------------------------------------------------------- #
# Insumos del perfil r2, con candado (decisión 10 del mandato de           #
# U-R2-CODIGO): catálogo r2 por sha256 (c3ad1581…, bd2122d) y política con #
# el sha de 57a8dd2. Los módulos de pyd_r2 se importan, no se editan.      #
# ----------------------------------------------------------------------- #
PYD_R2_CODE = C.REPO / "data" / "experiment" / "pyd_r2" / "code"
GENERADOS_R2 = C.REPO / "data" / "experiment" / "catalogo_unico" / "generados_r2"
POLITICA_R2_SHA256 = "82e8752aea1d6ad869d6023d303c0af45182dd9333753681787d7a581ef6d00b"
ARCHIVOS_CATALOGO_R2 = ("indice_e4_r2.json", "labels_e2_r2.json", "rol_por_to_r2.json",
                        "entrada_esqueleto_r2.json")


def _pyd_r2():
    import sys as _sys  # noqa: PLC0415
    if str(PYD_R2_CODE) not in _sys.path:
        _sys.path.insert(0, str(PYD_R2_CODE))


def modulo_modelos_r2():
    _pyd_r2()
    import modelos_r2  # noqa: PLC0415
    return modelos_r2


def modulo_validador_r2():
    _pyd_r2()
    import validador_r2  # noqa: PLC0415
    return validador_r2


def catalogo_r2() -> dict:
    """Generados del catálogo r2 (U-CAT-UNICO): cada archivo con el sha256 de
    manifest_generados_r2.json, y el manifiesto con el sha del catálogo que
    fija modelos_r2. Frena ante cualquier diferencia."""
    import hashlib as _h  # noqa: PLC0415
    M = modulo_modelos_r2()
    man = json.loads((GENERADOS_R2 / "manifest_generados_r2.json").read_text(encoding="utf-8"))
    if man["catalogo_sha256"] != M.CATALOGO_R2_SHA256:
        raise RuntimeError("candado del catálogo r2: el manifiesto de generados no es del catálogo de modelos_r2")
    datos = {}
    for nombre in ARCHIVOS_CATALOGO_R2:
        b = (GENERADOS_R2 / nombre).read_bytes()
        if _h.sha256(b).hexdigest() != man["archivos"][nombre]:
            raise RuntimeError(f"candado del catálogo r2: {nombre} no coincide con su manifiesto")
        datos[nombre] = json.loads(b.decode("utf-8"))
    return {"catalogo_sha256": M.CATALOGO_R2_SHA256,
            "indice": indice_desde_lista(datos["indice_e4_r2.json"]),
            "labels": datos["labels_e2_r2.json"], "rol_por_to": datos["rol_por_to_r2.json"],
            "entrada_esqueleto": datos["entrada_esqueleto_r2.json"],
            "entrada_esqueleto_path": GENERADOS_R2 / "entrada_esqueleto_r2.json"}


# ----------------------------------------------------------------------- #
# Catálogo de resolución (R2 de U-RERESOL-CAT, W2): el del request más una #
# lista de ampliaciones que solo agrega. Lo lee el código (E4, E2, merge   #
# entre TOs, esqueleto, S19 y la suite) y puede crecer entre tandas; el    #
# request de E1 (bloque, enum y tool schema) sale solo del catálogo del    #
# request y no lo lee.                                                     #
# ----------------------------------------------------------------------- #
FORMATO_RESOLUCION_R2 = "generados_resolucion_r2/1"
MANIFIESTO_RESOLUCION_R2 = "manifest_generados_resolucion_r2.json"
ARCHIVOS_RESOLUCION_R2 = ARCHIVOS_CATALOGO_R2 + ("ids_s19_r2.json", "catalogo_suite_r2.json")


def catalogo_resolucion_r2(directorio) -> dict:
    """Generados del catálogo de resolución, con su candado: el manifiesto
    tiene que derivar del catálogo del request que fija modelos_r2; la lista
    de ampliaciones, el catálogo compuesto (sin ampliaciones, el compuesto es
    el del request) y cada generado tienen que dar el sha256 del manifiesto; y
    los ids del request tienen que estar todos (el catálogo de resolución solo
    agrega). Devuelve lo mismo que `catalogo_r2()`, con el sha del compuesto,
    más el conjunto de ids de resolución (reemplaza a SUJETOS_R2_SET en E2 y
    en el merge entre TOs), las rutas de los ids de S19 y del catálogo de la
    suite y las tres versiones. Frena ante cualquier diferencia."""
    import hashlib as _h  # noqa: PLC0415
    from pathlib import Path as _Path  # noqa: PLC0415
    M = modulo_modelos_r2()
    d = _Path(directorio)
    man = json.loads((d / MANIFIESTO_RESOLUCION_R2).read_text(encoding="utf-8"))

    def sha(p) -> str:
        return _h.sha256(p.read_bytes()).hexdigest()
    if man.get("formato") != FORMATO_RESOLUCION_R2:
        raise RuntimeError(f"candado del catálogo de resolución: formato {man.get('formato')!r}")
    if man["catalogo_request_sha256"] != M.CATALOGO_R2_SHA256:
        raise RuntimeError("candado del catálogo de resolución: no deriva del catálogo del request de modelos_r2")
    if sha(d / man["ampliaciones"]) != man["ampliaciones_sha256"]:
        raise RuntimeError("candado del catálogo de resolución: la lista de ampliaciones no coincide con su manifiesto")
    if man["n_ampliaciones"] == 0:
        if man["catalogo_sha256"] != M.CATALOGO_R2_SHA256:
            raise RuntimeError("candado del catálogo de resolución: sin ampliaciones, el compuesto es el del request")
    elif sha(d / man["catalogo"]) != man["catalogo_sha256"]:
        raise RuntimeError("candado del catálogo de resolución: el catálogo compuesto no coincide con su manifiesto")
    datos = {}
    for nombre in ARCHIVOS_RESOLUCION_R2:
        b = (d / nombre).read_bytes()
        if _h.sha256(b).hexdigest() != man["archivos"][nombre]:
            raise RuntimeError(f"candado del catálogo de resolución: {nombre} no coincide con su manifiesto")
        datos[nombre] = json.loads(b.decode("utf-8"))
    ids = frozenset(datos["ids_s19_r2.json"])
    if not M.SUJETOS_R2_SET <= ids:
        raise RuntimeError("candado del catálogo de resolución: faltan ids del request (el catálogo de resolución "
                           "solo agrega)")
    return {"catalogo_sha256": man["catalogo_sha256"],
            "indice": indice_desde_lista(datos["indice_e4_r2.json"]),
            "labels": datos["labels_e2_r2.json"], "rol_por_to": datos["rol_por_to_r2.json"],
            "entrada_esqueleto": datos["entrada_esqueleto_r2.json"],
            "entrada_esqueleto_path": d / "entrada_esqueleto_r2.json",
            "sujetos_set": ids, "ids_s19_path": d / "ids_s19_r2.json",
            "catalogo_suite_path": d / "catalogo_suite_r2.json",
            "versiones_catalogo": {"catalogo_request_sha256": man["catalogo_request_sha256"],
                                   "ampliaciones_sha256": man["ampliaciones_sha256"],
                                   "n_ampliaciones": man["n_ampliaciones"],
                                   "catalogo_resolucion_sha256": man["catalogo_sha256"]}}
