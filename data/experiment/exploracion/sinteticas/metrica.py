"""
metrica.py — Recall determinístico de gold en traza (§7 del diseño). Sin juez.

Dado un trace JSON del formato del harness (dict con `steps`: cada step con
`tool`, `input`, `output_truncado`, `output_chars`) y un gold RESUELTO a nodos
de un grafo (ids locales, salidos de resolucion.AnclaIndex.censo), computa por
nodo gold:

  VISTO       — el id apareció en los resultados de algún `buscar_nodos`.
  CONSULTADO  — el nodo recibió `ver_nodo` (sin error) o llegó por
                `ver_vecinos` (apareció como vecino_id en el output, dentro
                del cap de 40 por dirección del harness).
  BRECHA      — visto y no consultado (selección post-búsqueda, mecanismo 4
                de las notas de adjudicación U6).

Cómo se computa — re-ejecución determinística:
Las trazas persistidas truncan los outputs de tool a 1200 chars
(harness.TRUNC_TOOL_OUTPUT), así que el output loggeado NO alcanza para saber
qué ids devolvió un buscar_nodos. Pero las tres tools del harness son
funciones PURAS del grafo y del input (búsqueda léxica rankeada determinística,
adyacencia en orden de archivo), y el input de cada step está completo en la
traza. La métrica re-ejecuta cada step con harness.GraphIndex sobre el MISMO
kg.json y computa contra el output completo. `verificar_replay=True` valida
esa premisa: el output re-ejecutado debe coincidir con `output_truncado` en
el prefijo persistido (y en `output_chars` exacto); cualquier divergencia se
reporta y invalida la corrida (grafo distinto o harness cambiado).

Detalle de fidelidad: el harness ejecuta ver_vecinos SOLO con (id, direccion)
— el cap de 40 es el default y ningún caller pasa `limite` — y buscar_nodos
con (consulta, limite). La re-ejecución replica exactamente esa firma
(harness.GraphAgent._run_tool).
"""

from __future__ import annotations

import json
from pathlib import Path

from comun import index_runtime, KG_VIGENTE
from harness import GraphIndex, TRUNC_TOOL_OUTPUT


def _reejecutar_step(index: GraphIndex, step: dict) -> dict:
    tool, args = step.get("tool"), step.get("input") or {}
    if tool == "buscar_nodos":
        return index.buscar_nodos(args.get("consulta", ""),
                                  args.get("limite", 10))
    if tool == "ver_nodo":
        return index.ver_nodo(args.get("id", ""))
    if tool == "ver_vecinos":
        return index.ver_vecinos(args.get("id", ""),
                                 args.get("direccion", "ambas"))
    return {"error": f"tool desconocida: {tool}"}


def _check_replay(step: dict, result_str: str) -> str | None:
    """None si el replay coincide con lo persistido; sino el motivo."""
    logged = step.get("output_truncado")
    chars = step.get("output_chars")
    if logged is None:
        return None   # traza sin output loggeado: no hay contra qué verificar
    prefijo = result_str[:TRUNC_TOOL_OUTPUT]
    logged_prefijo = logged.split("… [+", 1)[0]
    if prefijo != logged_prefijo:
        return "prefijo_distinto"
    if chars is not None and chars != len(result_str):
        return f"output_chars_distinto: {chars} != {len(result_str)}"
    return None


def evaluar_traza(trace: dict, gold_ids: list, index: GraphIndex,
                  verificar_replay: bool = True) -> dict:
    """Métrica §7 para una traza contra un gold resuelto a ids locales."""
    gold = list(dict.fromkeys(gold_ids))    # dedup, orden estable
    vistos: dict[str, int] = {}
    consultados: dict[str, dict] = {}
    replay_fallas = []

    for step in trace.get("steps", []):
        res = _reejecutar_step(index, step)
        if verificar_replay:
            falla = _check_replay(step, json.dumps(res, ensure_ascii=False))
            if falla:
                replay_fallas.append({"n": step.get("n"),
                                      "tool": step.get("tool"),
                                      "motivo": falla})
        tool = step.get("tool")
        if tool == "buscar_nodos":
            for r in res.get("resultados", []):
                nid = r.get("id")
                if nid in gold and nid not in vistos:
                    vistos[nid] = step.get("n")
        elif tool == "ver_nodo":
            nid = res.get("id")   # presente solo si el nodo existe (sin error)
            if nid in gold and nid not in consultados:
                consultados[nid] = {"via": "ver_nodo", "n": step.get("n")}
        elif tool == "ver_vecinos":
            for lista in (res.get("salientes") or []), (res.get("entrantes") or []):
                for v in lista:
                    nid = v.get("vecino_id")
                    if nid in gold and nid not in consultados:
                        consultados[nid] = {"via": "ver_vecinos",
                                            "n": step.get("n")}

    por_nodo = []
    for nid in gold:
        visto = nid in vistos
        consultado = nid in consultados
        por_nodo.append({
            "nodo": nid,
            "visto": visto,
            "visto_en_step": vistos.get(nid),
            "consultado": consultado,
            "consultado_via": consultados.get(nid, {}).get("via"),
            "consultado_en_step": consultados.get(nid, {}).get("n"),
            "brecha_visto_sin_consultar": visto and not consultado,
        })
    n = len(gold)
    n_visto = sum(1 for p in por_nodo if p["visto"])
    n_consultado = sum(1 for p in por_nodo if p["consultado"])
    n_brecha = sum(1 for p in por_nodo if p["brecha_visto_sin_consultar"])
    return {
        "n_gold": n,
        "n_visto": n_visto,
        "n_consultado": n_consultado,
        "n_brecha_visto_sin_consultar": n_brecha,
        "recall_visto": (n_visto / n) if n else None,
        "recall_consultado": (n_consultado / n) if n else None,
        "por_nodo": por_nodo,
        "replay_ok": not replay_fallas,
        "replay_fallas": replay_fallas,
    }


def evaluar_por_anclas(trace: dict, anclas: list, ancla_index,
                       index: GraphIndex,
                       verificar_replay: bool = True) -> dict:
    """Agregación POR ANCLA de la métrica §7 — la lectura primaria para golds
    expresados en anclas de provenance.

    Motivación (medida sobre el grafo vigente): la granularidad de ancla es
    gruesa — mediana 29 nodos por ancla tras excluir contenedores — así que el
    recall nodo a nodo diluye el resultado con nodos hermanos del mismo punto.
    A nivel ancla: un ancla está VISTA/CONSULTADA si ALGÚN nodo que la porta
    (censo sin contenedores) lo está. Un ancla que no resuelve en este grafo
    es AUSENCIA (dato de fidelidad): se reporta aparte y NO entra al recall de
    navegabilidad (§4 del diseño).
    """
    por_ancla, ausentes = [], []
    detalle_nodos = {}
    for a in anclas:
        ids = ancla_index.resolver(a["to"], a["ancla"])
        if not ids:
            ausentes.append(f"{a['to']}:{a['ancla']}")
            continue
        ev = evaluar_traza(trace, ids, index, verificar_replay=False)
        detalle_nodos[f"{a['to']}:{a['ancla']}"] = ev["por_nodo"]
        por_ancla.append({
            "ancla": f"{a['to']}:{a['ancla']}",
            "n_nodos_censo": len(ids),
            "vista": ev["n_visto"] > 0,
            "consultada": ev["n_consultado"] > 0,
            "brecha_vista_sin_consultar": ev["n_visto"] > 0
                                          and ev["n_consultado"] == 0,
        })
    # el replay se verifica una sola vez (mismos steps para todas las anclas)
    replay = evaluar_traza(trace, [], index, verificar_replay=verificar_replay)
    n = len(por_ancla)
    n_vista = sum(1 for p in por_ancla if p["vista"])
    n_cons = sum(1 for p in por_ancla if p["consultada"])
    return {
        "n_anclas": n,
        "n_vistas": n_vista,
        "n_consultadas": n_cons,
        "n_brecha": sum(1 for p in por_ancla
                        if p["brecha_vista_sin_consultar"]),
        "recall_vista": (n_vista / n) if n else None,
        "recall_consultada": (n_cons / n) if n else None,
        "anclas_ausentes_en_este_grafo": ausentes,
        "por_ancla": por_ancla,
        "detalle_nodos": detalle_nodos,
        "replay_ok": replay["replay_ok"],
        "replay_fallas": replay["replay_fallas"],
    }


def evaluar_archivo_posthoc(path_traza: Path, gold_ids: list,
                            index: GraphIndex | None = None) -> list:
    """Convenience para archivos de posthoc_run/traces/ (lista de reps, cada
    una con clave `trace`). Devuelve una evaluación por rep."""
    if index is None:
        index = index_runtime(KG_VIGENTE)
    with open(path_traza, encoding="utf-8") as f:
        reps = json.load(f)
    return [evaluar_traza(rep["trace"], gold_ids, index) for rep in reps]
