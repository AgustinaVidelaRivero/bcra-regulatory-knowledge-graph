"""
r1_cola_flaggeada.py — B1.6: la cola humana ingresa al grafo FLAGGEADA.

(1) inyectar_cola(to, registros): las unidades de cola humana (finales.jsonl
    con validacion_final=None; 80 en el corpus) ingresan con sus elementos
    E1 VÁLIDOS — la validación base de E1 persistida en
    extracciones_e1_compact.jsonl (last-wins por chunk_id; ya pasó
    validador_e1 sin rechazo de nivel chunk). No se usa ninguna
    re-extracción de los reintentos (no están persistidas como validación;
    solo sus veredictos) — declarado. El registro lleva estado_e3 = veredicto
    de la cola y cola_humana=True.
(2) flaggear_grafo(grafo, info): todo nodo/arista con alguna provenance
    emitida por un chunk de cola recibe properties.estado_e3 (veredicto(s)),
    properties.cola_humana="true" y properties.cola_chunks (lista). Una
    provenance de herencia compartida con chunks aceptados también queda
    flaggeada (sobre-flag conservador, declarado).
(3) recomputar_politica(): recomputo DERIVADO, sin API (precedente
    e3_verificador/recompute_politica_enm01.py), de los veredictos ya pagados
    (veredictos.jsonl) bajo dos guardias nuevas encima de ratchet_e3.
    evaluar_veredicto (laudos A+B vigentes):
      B-ext: la guardia estructural del LAUDO B se extiende a CUALQUIER tipo
             de faltante (no solo enumeracion_incompleta): mini-chunk
             ordenador (':' final) con descendientes en el corpus + cita
             verificada que ES la cláusula ordenadora → no bloquea.
      cita=label: un faltante cuya cita verificada, normalizada
             (comun_e3.normalizar_para_cita), es IGUAL al label o a la
             descripcion de un elemento extraído de la unidad (o está
             contenida en su descripcion) no bloquea: el verificador señala
             como ausente algo que la extracción representa. Se aplica a
             los veredictos base con la validación E1 base; en las
             re-verificaciones se aplica solo B-ext (la re-extracción no
             está persistida) — caveat declarado.
    Trayectoria por unidad: igual que el precedente (completo_ok_directo /
    aceptado_con_residuales / aceptado_tras_reintento / cola_*). Reporta
    cuántas unidades cambian de estado respecto de finales.jsonl. NINGUNA
    llamada a E3; los estados del grafo r1 son los MEDIDOS (finales.jsonl),
    el recomputo es informativo.
"""

from __future__ import annotations

from copy import deepcopy

import r1_comun as C

import comun_e3                                   # noqa: E402 (importado)
import ratchet_e3                                 # noqa: E402 (importado)


# ----------------------------------------------------------------------- #
# (1) inyección                                                           #
# ----------------------------------------------------------------------- #
def inyectar_cola(to: str, registros: list[dict]) -> tuple[list[dict], dict]:
    finales = C.cargar_finales(to)
    e1 = C.cargar_e1_compact(to)
    cola = {cid: f for cid, f in finales.items() if f.get("validacion_final") is None}
    out: list[dict] = []
    info = {"to": to, "unidades": {}, "claves_prov": {}, "sin_e1_valido": []}
    for r in registros:
        cid = r["chunk_id"]
        if cid in cola:
            base = e1.get(cid)
            val = (base or {}).get("validacion")
            rechazo_chunk = bool(val) and any(x.get("nivel") == "chunk" for x in val.get("rechazos", []))
            if base is None or base.get("error") or not val or rechazo_chunk:
                info["sin_e1_valido"].append(cid)
                out.append(r)          # queda rechazado como antes
                continue
            estado = cola[cid]["estado"]
            nuevo = {"chunk_id": cid, "error": None, "estado_e3": estado,
                     "cola_humana": True, "validacion": deepcopy(val)}
            out.append(nuevo)
            info["unidades"][cid] = {"estado_e3": estado,
                                     "n_entidades": len(val.get("entidades", [])),
                                     "n_relaciones": len(val.get("relaciones", []))}
            for coll in ("entidades", "relaciones"):
                for e in val.get(coll, []):
                    p = e.get("provenance") or {}
                    k = (p.get("to"), p.get("punto"), p.get("rol_documental"))
                    info["claves_prov"].setdefault(k, set()).add(cid)
        else:
            out.append(r)
    info["resumen"] = {"unidades_cola": len(cola), "ingresadas": len(info["unidades"]),
                       "sin_e1_valido": info["sin_e1_valido"],
                       "por_estado": C.conteo([{"e": u["estado_e3"]} for u in info["unidades"].values()], "e")}
    return out, info


def flaggear_grafo(grafo: dict, info: dict) -> dict:
    claves = info["claves_prov"]
    unidades = info["unidades"]
    n_n = n_e = 0

    def flag(obj: dict) -> bool:
        chunks = set()
        for p in obj.get("provenances", []):
            k = (p.get("to"), p.get("punto"), p.get("rol_documental"))
            chunks |= claves.get(k, set())
        if not chunks:
            return False
        props = obj.setdefault("properties", {})
        props["cola_humana"] = "true"
        props["cola_chunks"] = sorted(chunks)
        props["estado_e3"] = "; ".join(sorted({unidades[c]["estado_e3"] for c in chunks}))
        return True

    for n in grafo["nodes"]:
        n_n += flag(n)
    for e in grafo["edges"]:
        n_e += flag(e)
    info["resumen"]["nodos_flaggeados"] = n_n
    info["resumen"]["aristas_flaggeadas"] = n_e
    return info["resumen"]


# ----------------------------------------------------------------------- #
# (3) recomputo de política                                               #
# ----------------------------------------------------------------------- #
def _guardia_b_ext(f: dict, chunk: dict, unidades_corpus: set[str]) -> bool:
    if chunk.get("tipo") != "mini_chunk" or not f.get("cita_verificada"):
        return False
    if not ratchet_e3._bloque_abre_enumeracion(chunk):
        return False
    if not ratchet_e3._origen_tiene_descendientes(chunk, unidades_corpus):
        return False
    cita_n = comun_e3.normalizar_para_cita(f.get("cita_textual_del_fuente") or "")
    return cita_n.endswith(":") and cita_n in comun_e3.normalizar_para_cita(chunk["texto"])


def _guardia_cita_label(f: dict, validacion: dict | None) -> bool:
    if not validacion or not f.get("cita_verificada"):
        return False
    cita_n = comun_e3.normalizar_para_cita(f.get("cita_textual_del_fuente") or "")
    if len(cita_n) < 12:
        return False
    for e in validacion.get("entidades", []):
        lab = comun_e3.normalizar_para_cita(e.get("label") or "")
        desc = comun_e3.normalizar_para_cita(str((e.get("properties") or {}).get("descripcion") or ""))
        if cita_n == lab or (desc and (cita_n == desc or cita_n in desc)):
            return True
    return False


def _evaluar_ext(tool_input, chunk: dict, unidades_corpus: set[str],
                 validacion: dict | None) -> dict:
    ev = ratchet_e3.evaluar_veredicto(tool_input, chunk, unidades_corpus)
    ev["faltantes_bloqueantes"] = []
    ev["bloqueantes_utilizables"] = []
    ev["residuales"] = []
    ev["guardias_nuevas"] = {"b_ext": 0, "cita_label": 0}
    for f in ev["faltantes"]:
        b_ext = (not f.get("estructural_no_bloqueante")) and _guardia_b_ext(f, chunk, unidades_corpus)
        c_lab = _guardia_cita_label(f, validacion)
        if b_ext:
            ev["guardias_nuevas"]["b_ext"] += 1
        if c_lab:
            ev["guardias_nuevas"]["cita_label"] += 1
        f["bloqueante"] = (f.get("severidad") in ratchet_e3.SEVERIDAD_BLOQUEANTE
                           and not f.get("estructural_no_bloqueante") and not b_ext and not c_lab)
        if f["bloqueante"]:
            ev["faltantes_bloqueantes"].append(f)
            if f.get("cita_verificada"):
                ev["bloqueantes_utilizables"].append(f)
        else:
            ev["residuales"].append(f)
    ev["aceptable"] = (not ev["incoherencias"] and not ev["faltantes_bloqueantes"]
                       and tool_input.get("veredicto") in ("completo_ok", "faltantes_detectados")
                       if isinstance(tool_input, dict) else False)
    return ev


def recomputar_politica() -> dict:
    por_to = {}
    cambios: list[dict] = []
    tot = {"unidades": 0, "cambian": 0, "cola_medida": 0, "cola_recomputada": 0,
           "guardias_b_ext": 0, "guardias_cita_label": 0}
    for to in C.TOS_ORDEN:
        chunks = {c["id"]: c for c in comun_e3.cargar_chunks((to,), e0_dir=comun_e3.E0_SALIDA_ENM01)}
        unidades_corpus = {c["unidad"] for c in chunks.values()}
        vered = C.cargar_veredictos(to)
        finales = C.cargar_finales(to)
        e1 = C.cargar_e1_compact(to)
        base: dict[str, dict] = {}
        rever: dict[str, dict] = {}
        for v in vered:      # last-wins (filas duplicadas de relanzamientos, declarado en el runner)
            if v["fase"] == "verificacion" and v["intento"] == 0:
                base[v["chunk_id"]] = v
            elif v["fase"] == "re_verificacion":
                rever[v["chunk_id"]] = v
        derivado = {}
        for cid, v in base.items():
            if cid not in finales:
                continue
            chunk = chunks[cid]
            val = (e1.get(cid) or {}).get("validacion")
            ev = _evaluar_ext(v["tool_input"], chunk, unidades_corpus, val)
            g = dict(ev["guardias_nuevas"])
            if ev["es_completo_ok"]:
                est = "completo_ok_directo"
            elif ev["aceptable"]:
                est = "aceptado_con_residuales"
            elif not ev["bloqueantes_utilizables"]:
                est = "cola_humana_veredicto_inutilizable"
            elif cid in rever:
                ev2 = _evaluar_ext(rever[cid]["tool_input"], chunk, unidades_corpus, None)
                g["b_ext"] += ev2["guardias_nuevas"]["b_ext"]
                est = "aceptado_tras_reintento" if (ev2["es_completo_ok"] or ev2["aceptable"]) else "cola_humana"
            else:
                est = "cola_humana_reintento_no_persistido"
            medido = finales[cid]["estado"]
            derivado[cid] = {"medido": medido, "recomputado": est, "guardias": g}
            tot["unidades"] += 1
            tot["guardias_b_ext"] += g["b_ext"]
            tot["guardias_cita_label"] += g["cita_label"]
            if medido.startswith("cola_humana"):
                tot["cola_medida"] += 1
            if est.startswith("cola_humana"):
                tot["cola_recomputada"] += 1
            if medido != est:
                tot["cambian"] += 1
                cambios.append({"to": to, "chunk_id": cid, "medido": medido, "recomputado": est,
                                "guardias": g})
        por_to[to] = {"unidades": len(derivado),
                      "medido": C.conteo([{"e": d["medido"]} for d in derivado.values()], "e"),
                      "recomputado": C.conteo([{"e": d["recomputado"]} for d in derivado.values()], "e"),
                      "cambian": sum(1 for d in derivado.values() if d["medido"] != d["recomputado"])}
    return {"total": tot, "por_to": por_to, "cambios": cambios,
            "transiciones": C.conteo([{"t": f"{c['medido']} -> {c['recomputado']}"} for c in cambios], "t"),
            "caveats": [
                "Recomputo derivado sobre veredictos ya pagados; cero llamadas a E3.",
                "cita=label se aplica solo al veredicto base (validación E1 base persistida); en "
                "re-verificaciones solo B-ext (la re-extracción del reintento no está persistida).",
                "Unidades cuyo veredicto base tiene bloqueantes bajo la política nueva pero sin "
                "re-verificación persistida (no reintentadas en la corrida) quedan como "
                "cola_humana_reintento_no_persistido: no se puede derivar sin pagar.",
                "Los estados del grafo r1 son los MEDIDOS (finales.jsonl); el recomputo es informativo.",
            ]}
