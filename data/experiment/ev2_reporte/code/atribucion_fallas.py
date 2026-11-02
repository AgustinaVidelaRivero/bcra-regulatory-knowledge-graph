"""
atribucion_fallas.py — Atribución DETERMINÍSTICA de fallas de EV2 (U-A0 / A0.2).

Regla vinculante: `data/experiment/ev2_reporte/regla_atribucion.md` (Fase A,
laudada y commiteada ANTES de correr sobre datos reales). Este módulo la
implementa tal cual; cualquier cambio de regla es enmienda del .md, no ajuste
del código.

Qué hace: para cada TRAZA del eje de fidelidad (EV2F-*, corrida base
bb89a8e; opcionalmente las 198 re-corridas §7 de 9044a04) clasifica la falla
de ESA respuesta — contra el veredicto de ESA respuesta — en exactamente una
de cuatro clases, mutuamente excluyentes y por precedencia:

  1. ausencia_kg          — el ancla de la pregunta NO resuelve a ningún nodo
                            en ese grafo (regla sellada del censo:
                            resolucion.AnclaIndex, match exacto de punto,
                            contenedores > 10 anclas excluidos).
  2. generacion           — el ancla fue CONSULTADA (algún nodo que la porta
                            recibió `ver_nodo` sin error, o apareció como
                            `vecino_id` en un `ver_vecinos`) y aun así el
                            veredicto es parcial/incorrecto.
  3. vista_no_consultada  — el ancla NO fue consultada pero SÍ vista (algún
                            nodo que la porta apareció en `resultados` de un
                            `buscar_nodos`).
  4. alcanzabilidad       — el ancla está presente y ningún nodo que la porta
                            fue visto ni consultado en toda la traza.

Los veredictos `correcto` NO se atribuyen (se reportan como denominador).
La clasificación auxiliar abstención/contenido del juez es COLUMNA CRUZADA.

Cómo se computa "vista" / "consultada": re-ejecución determinística de los
steps de la traza con harness.GraphIndex sobre el MISMO kg.json (sha256
verificado) — se importa `metrica.evaluar_traza` del pipeline de sintéticas
(la misma función que la métrica de navegabilidad de 5b02d22, sin editar) y
`metrica_ev2.verificar_steps_full` (replay FUERTE contra `steps_full`). Una
divergencia de replay invalida la traza para la atribución y se reporta.

Uso:
  python3 -B atribucion_fallas.py --selftest                # sintético, sin datos reales
  python3 -B atribucion_fallas.py --correr [--incluir-enc]   # Fase B (exige regla commiteada)
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from comun_reporte import (CANONICO, CORRIDA_DIR, ENC_DIR, INSUMOS, ORDEN_GRAFOS,
                           REPO_DIR, SALIDA_DIR, UNIDAD_DIR, cargar, escribir_json,
                           rel_repo, sha256_path, verificar_sellos)

# módulos de la corrida (vía sys.path que arma comun_reporte → comun_ev2)
from comun_ev2 import GRAFOS, cargar_fidelidad, cargar_runtime, indice_anclas, verificar_grafos  # noqa: E402
from metrica_ev2 import verificar_steps_full  # noqa: E402
from metrica import evaluar_traza  # noqa: E402  (sintéticas, sin editar)
from harness import GraphIndex  # noqa: E402
from loader import Edge, KnowledgeGraph, Node  # noqa: E402
from resolucion import AnclaIndex  # noqa: E402

CLASES = ["ausencia_kg", "alcanzabilidad", "vista_no_consultada", "generacion"]
VEREDICTOS_ATRIBUIBLES = ("parcial", "incorrecto")
REGLA_MD = UNIDAD_DIR / "regla_atribucion.md"


# --------------------------------------------------------------------------- #
# Núcleo de la regla                                                            #
# --------------------------------------------------------------------------- #
def parse_ancla(s: str) -> tuple[str, str]:
    """'ext:6.11' -> ('ext', '6.11')."""
    to, punto = s.split(":", 1)
    return to, punto


def resolver_anclas(anclas: list[str], ancla_index: AnclaIndex) -> dict[str, list[str]]:
    """{ancla: [ids de nodo que la portan]} (regla sellada del censo)."""
    return {a: ancla_index.resolver(*parse_ancla(a)) for a in anclas}


def navegacion_de_traza(trace: dict, resueltas: dict[str, list[str]], index: GraphIndex,
                        verificar_replay: bool = True) -> dict:
    """Vista / consultada POR ANCLA (agregación por ancla, como la métrica de
    navegabilidad): un ancla está vista/consultada si ALGÚN nodo que la porta
    lo está. Replay estándar contra `trace.steps` una sola vez."""
    por_ancla = {}
    for a, ids in resueltas.items():
        if not ids:
            por_ancla[a] = {"presente": False, "n_nodos_censo": 0, "vista": False,
                            "consultada": False, "por_nodo": []}
            continue
        ev = evaluar_traza(trace, ids, index, verificar_replay=False)
        vistos = [p for p in ev["por_nodo"] if p["visto"]]
        cons = [p for p in ev["por_nodo"] if p["consultado"]]
        por_ancla[a] = {
            "presente": True, "n_nodos_censo": len(ids),
            "vista": ev["n_visto"] > 0, "consultada": ev["n_consultado"] > 0,
            "vista_en_step": min(p["visto_en_step"] for p in vistos) if vistos else None,
            "consultada_en_step": min(p["consultado_en_step"] for p in cons) if cons else None,
            "consultada_via": sorted({p["consultado_via"] for p in cons}) if cons else [],
            "por_nodo": ev["por_nodo"],
        }
    replay = evaluar_traza(trace, [], index, verificar_replay=verificar_replay)
    return {
        "presente": any(x["presente"] for x in por_ancla.values()),
        "vista": any(x["vista"] for x in por_ancla.values()),
        "consultada": any(x["consultada"] for x in por_ancla.values()),
        "por_ancla": por_ancla,
        "replay_ok": replay["replay_ok"],
        "replay_fallas": replay["replay_fallas"],
    }


def clasificar(veredicto: str, presente: bool, vista: bool, consultada: bool) -> str | None:
    """Precedencia: correcto → None; no presente → ausencia_kg; consultada →
    generacion; vista → vista_no_consultada; si no → alcanzabilidad."""
    if veredicto == "correcto":
        return None
    if veredicto not in VEREDICTOS_ATRIBUIBLES:
        raise ValueError(f"veredicto no atribuible: {veredicto!r}")
    if not presente:
        return "ausencia_kg"
    if consultada:
        return "generacion"
    if vista:
        return "vista_no_consultada"
    return "alcanzabilidad"


def atribuir_payload(payload: dict, anclas: list[str], ancla_index: AnclaIndex,
                     index: GraphIndex, veredicto: str, replay_fuerte: bool = True) -> dict:
    """Atribución de UNA traza persistida (formato runner_ev2: meta / trace /
    steps_full) contra el veredicto de ESA respuesta."""
    resueltas = resolver_anclas(anclas, ancla_index)
    nav = navegacion_de_traza(payload["trace"], resueltas, index, verificar_replay=True)
    fallas_fuerte = verificar_steps_full(payload, index) if replay_fuerte else []
    fj = payload["trace"].get("final_json") or {}
    return {
        "veredicto": veredicto,
        "clase": clasificar(veredicto, nav["presente"], nav["vista"], nav["consultada"]),
        "anclas": anclas,
        "ancla_presente": nav["presente"],
        "ancla_vista": nav["vista"],
        "ancla_consultada": nav["consultada"],
        "por_ancla": nav["por_ancla"],
        "n_steps": len(payload["trace"].get("steps", [])),
        "tool_calls_used": payload["trace"].get("tool_calls_used"),
        "hit_tool_limit": payload["trace"].get("hit_tool_limit"),
        "respondible_flag": fj.get("respondible") if isinstance(fj, dict) else None,
        "replay_ok": nav["replay_ok"],
        "replay_fallas": nav["replay_fallas"],
        "replay_fuerte_ok": not fallas_fuerte,
        "replay_fuerte_fallas": fallas_fuerte,
    }


# --------------------------------------------------------------------------- #
# Veredictos por respuesta (base y §7)                                          #
# --------------------------------------------------------------------------- #
def veredictos_base() -> dict:
    """{(id_pregunta, grafo): {...}} — veredicto de la respuesta BASE: juez v1
    (agregados ciegos b624865); si el juez dio requiere_adjudicacion, el
    definitivo por vía adjudicacion_base (64de678). NUNCA el agregado de §7."""
    tabla = {f["id_opaco"]: f for f in cargar("tabla_base")["filas"]}
    agg = {a["id_opaco"]: a for a in cargar("agregados_base")["agregados"]}
    defs = {d["id_opaco_base"]: d for d in cargar("veredictos_definitivos")["definitivos"]}
    out = {}
    for op, a in agg.items():
        f = tabla[op]
        v = a["veredicto_pregunta"]
        if v == "requiere_adjudicacion":
            d = defs[op]
            assert d["via"] == "adjudicacion_base", (op, d["via"])
            v = d["definitivo"]; marcas = d["marcas_humanas"]; fuente = "adjudicacion_base"
        else:
            marcas = a["modales"]; fuente = "juez_base"
        out[(f["id_pregunta"], f["grafo"])] = {
            "id_opaco": op, "veredicto": v, "fuente_veredicto": fuente,
            "clasificacion_auxiliar": a["clasificacion_respuesta_modal"],
            "marcas": marcas, "n_criterios": len(marcas),
            "n_no_cumplidos": sum(1 for m in marcas if m == "no_cumplido"),
            "sha256_respuesta": f["sha256_respuesta"],
        }
    assert len(out) == 120, len(out)
    return out


def veredictos_enc() -> dict:
    """{(id_pregunta, grafo, rep): {...}} — veredicto de cada RE-CORRIDA §7
    contra sí misma: juez v1 (agregados ciegos 9044a04); votos
    requiere_adjudicacion resueltos por la adjudicación humana cuando la hubo
    (definitivos.resoluciones, vía adjudicacion_s7); los votos ADJ que
    quedaron sin ficha (pares decididos por invariancia) se marcan
    `sin_veredicto_propio` y quedan fuera de la atribución (se cuentan)."""
    tabla = cargar("tabla_enc")["filas"]
    agg = {a["id_opaco"]: a for a in cargar("agregados_enc")["agregados"]}
    defs = cargar("veredictos_definitivos")["definitivos"]
    ws = {f["id_ficha"]: f for f in json.loads(
        (INSUMOS["veredictos_definitivos"].parent / "worksheet_adjudicacion.json").read_text(encoding="utf-8"))["fichas"]}
    resol = {}
    for d in defs:
        for r in d.get("resoluciones", []) or []:
            resol[r["id_opaco_respuesta"]] = (r["veredicto_humano"],
                                              [c["veredicto"] for c in ws[r["id_ficha"]]["criterios"]])
    out = {}
    for f in tabla:
        a = agg[f["id_opaco"]]
        v = a["veredicto_pregunta"]; marcas = a["modales"]; fuente = "juez_enc"
        if v == "requiere_adjudicacion":
            if f["id_opaco"] in resol:
                v, marcas = resol[f["id_opaco"]]; fuente = "adjudicacion_s7"
            else:
                fuente = "sin_veredicto_propio"
        out[(f["id_pregunta"], f["grafo"], f["rep"])] = {
            "id_opaco": f["id_opaco"], "id_opaco_base": f["id_opaco_base"], "tipo": f["tipo"],
            "veredicto": v, "fuente_veredicto": fuente,
            "clasificacion_auxiliar": a["clasificacion_respuesta_modal"],
            "marcas": marcas, "n_criterios": len(marcas),
            "n_no_cumplidos": sum(1 for m in marcas if m == "no_cumplido"),
            "sha256_respuesta": f["sha256_respuesta"], "label": f["label"],
        }
    assert len(out) == 198, len(out)
    return out


# --------------------------------------------------------------------------- #
# Corrida real (Fase B)                                                        #
# --------------------------------------------------------------------------- #
def regla_sellada() -> str | None:
    """Hash del último commit que toca regla_atribucion.md, o None si el
    archivo no está commiteado (la Fase B no corre sin laudo commiteado)."""
    try:
        r = subprocess.run(["git", "log", "-n", "1", "--format=%H", "--", str(REGLA_MD)],
                           cwd=REPO_DIR, capture_output=True, text=True, check=True)
    except Exception:
        return None
    h = r.stdout.strip()
    return h or None


def _agregar(filas: list[dict], clave_extra: str | None = None) -> dict:
    """Tablas agregadas sobre filas atribuidas (todas con clase o correcto)."""
    def tabla3(key_fn):
        t = defaultdict(lambda: defaultdict(Counter))
        for x in filas:
            t[x["grafo"]][key_fn(x)][x["clase"] or "correcto"] += 1
        return {g: {k: dict(c) for k, c in sorted(t[g].items())} for g in ORDEN_GRAFOS if g in t}
    clase_x_grafo = {g: Counter() for g in ORDEN_GRAFOS}
    for x in filas:
        clase_x_grafo[x["grafo"]][x["clase"] or "correcto"] += 1
    # criterios no cumplidos por (grafo, clase)
    crit = defaultdict(lambda: defaultdict(lambda: {"n": 0, "no_cumplidos": 0, "criterios": 0}))
    for x in filas:
        c = crit[x["grafo"]][x["clase"] or "correcto"]
        c["n"] += 1; c["no_cumplidos"] += x["n_no_cumplidos"]; c["criterios"] += x["n_criterios"]
    for g in crit:
        for k, c in crit[g].items():
            c["media_no_cumplidos"] = round(c["no_cumplidos"] / c["n"], 3) if c["n"] else None
            c["tasa_no_cumplidos"] = round(c["no_cumplidos"] / c["criterios"], 4) if c["criterios"] else None
    return {
        "clase_x_grafo": {g: {"nombre": CANONICO[g]["nombre"], **{k: clase_x_grafo[g].get(k, 0)
                                                                    for k in CLASES + ["correcto"]},
                              "n": sum(clase_x_grafo[g].values())} for g in ORDEN_GRAFOS},
        "clase_x_grafo_x_veredicto": tabla3(lambda x: x["veredicto"]),
        "clase_x_grafo_x_auxiliar": tabla3(lambda x: x["clasificacion_auxiliar"]),
        "clase_x_grafo_x_respondible": tabla3(lambda x: str(x["respondible_flag"])),
        "criterios_no_cumplidos_x_grafo_x_clase": {g: dict(crit[g]) for g in ORDEN_GRAFOS if g in crit},
        "replay": {"n": len(filas), "replay_ok": sum(1 for x in filas if x["replay_ok"]),
                   "replay_fuerte_ok": sum(1 for x in filas if x["replay_fuerte_ok"])},
    }


def correr(incluir_enc: bool = False, out_dir: Path | None = None, exigir_sello: bool = True,
           sensibilidad_descendientes: bool = False) -> dict:
    out_dir = out_dir or SALIDA_DIR
    sello = regla_sellada()
    if exigir_sello and sello is None:
        raise SystemExit("regla_atribucion.md NO está commiteada: la Fase B no corre sin laudo sellado. FRENAR.")
    sellos = verificar_sellos()
    verificar_grafos()
    gold = {p["id"]: p["gold"]["ancla"] for p in cargar_fidelidad()}
    vb = veredictos_base()
    filas = []
    censo_anclas = {}
    for g in ORDEN_GRAFOS:
        label = GRAFOS[g]["label"]
        aidx = indice_anclas(g)
        index = GraphIndex(cargar_runtime(g))
        # censo de las 40 anclas de fidelidad en este grafo + diagnóstico de las no
        # resueltas (misma lectura que censo/ausencias_diagnostico.json: crudo =
        # incluyendo contenedores; desc = incluyendo descendientes sin contenedores)
        censo_anclas[g] = {}
        for q, anclas in gold.items():
            censo_anclas[g][q] = {}
            for a in anclas:
                to, punto = parse_ancla(a)
                censo_anclas[g][q][a] = {
                    "n": len(aidx.resolver(to, punto)),
                    "crudo_incl_contenedores": len(aidx.resolver(to, punto, incluir_contenedores=True)),
                    "con_descendientes": len(aidx.resolver(to, punto, incluir_descendientes=True)),
                }
        tdir = CORRIDA_DIR / "trazas" / label
        for p in sorted(tdir.glob("EV2F-*.json")):
            payload = json.loads(p.read_text(encoding="utf-8"))
            assert payload["meta"]["eje"] == "fidelidad" and payload["meta"]["grafo"] == g, p
            q = payload["meta"]["caso_id"]
            v = vb[(q, g)]
            at = atribuir_payload(payload, gold[q], aidx, index, v["veredicto"])
            filas.append({"origen": "base", "id_pregunta": q, "grafo": g, "nombre": CANONICO[g]["nombre"],
                          "label": label, "traza": rel_repo(p), "id_opaco": v["id_opaco"],
                          "fuente_veredicto": v["fuente_veredicto"],
                          "clasificacion_auxiliar": v["clasificacion_auxiliar"],
                          "n_criterios": v["n_criterios"], "n_no_cumplidos": v["n_no_cumplidos"],
                          "marcas": v["marcas"], **at})
    assert len(filas) == 120, len(filas)
    res = {"generado": datetime.now().isoformat(timespec="seconds"),
           "unidad": "U-A0 / A0.2 — atribución determinística de fallas (USD 0)",
           "regla": rel_repo(REGLA_MD), "regla_sha256": sha256_path(REGLA_MD),
           "regla_commit": sello, "sellos_insumos": sellos,
           "grafos": {g: {"nombre": CANONICO[g]["nombre"], "sha256": GRAFOS[g]["sha256"],
                          "path": rel_repo(GRAFOS[g]["path"])} for g in ORDEN_GRAFOS},
           "censo_anclas_fidelidad": censo_anclas,
           "base": {"n_trazas": len(filas), **_agregar(filas), "por_traza": filas}}
    # perfil por pregunta (clase por grafo)
    perfil = defaultdict(dict)
    for x in filas:
        perfil[x["id_pregunta"]][x["grafo"]] = x["clase"] or "correcto"
    res["base"]["perfil_por_pregunta"] = {q: perfil[q] for q in sorted(perfil)}
    res["base"]["perfiles_conteo"] = {"/".join(perfil[q][g] for g in ORDEN_GRAFOS): n
                                      for (q, n) in []}  # placeholder, se llena abajo
    cnt = Counter("/".join(perfil[q][g] for g in ORDEN_GRAFOS) for q in perfil)
    res["base"]["perfiles_conteo"] = {"orden_grafos": ORDEN_GRAFOS, "conteo": dict(cnt.most_common())}

    if incluir_enc:
        ve = veredictos_enc()
        filas_e = []
        excluidas = []
        for g in ORDEN_GRAFOS:
            aidx = indice_anclas(g)
            index = GraphIndex(cargar_runtime(g))
            for rep in (1, 2, 3):
                label = f"ev2_enc_{'run3' if g == 'run_3' else g}_r{rep}"
                tdir = ENC_DIR / "trazas" / label
                for p in sorted(tdir.glob("EV2F-*.json")):
                    payload = json.loads(p.read_text(encoding="utf-8"))
                    q = payload["meta"]["caso_id"]
                    v = ve[(q, g, rep)]
                    if v["fuente_veredicto"] == "sin_veredicto_propio":
                        excluidas.append({"id_pregunta": q, "grafo": g, "rep": rep, "id_opaco": v["id_opaco"]})
                        continue
                    at = atribuir_payload(payload, gold[q], aidx, index, v["veredicto"])
                    filas_e.append({"origen": "enc", "id_pregunta": q, "grafo": g, "rep": rep,
                                    "nombre": CANONICO[g]["nombre"], "label": label, "traza": rel_repo(p),
                                    "id_opaco": v["id_opaco"], "id_opaco_base": v["id_opaco_base"],
                                    "tipo": v["tipo"], "fuente_veredicto": v["fuente_veredicto"],
                                    "clasificacion_auxiliar": v["clasificacion_auxiliar"],
                                    "n_criterios": v["n_criterios"], "n_no_cumplidos": v["n_no_cumplidos"],
                                    "marcas": v["marcas"], **at})
        res["enc"] = {"n_trazas": len(filas_e), "n_excluidas_sin_veredicto_propio": len(excluidas),
                      "excluidas": excluidas, **_agregar(filas_e), "por_traza": filas_e}
    # diagnóstico de anclas de fidelidad no resueltas por grafo
    diag = {}
    for g in ORDEN_GRAFOS:
        cnt = Counter(); det = []
        for q, d in censo_anclas[g].items():
            for a, x in d.items():
                if x["n"] == 0:
                    if x["crudo_incl_contenedores"] == 0 and x["con_descendientes"] > 0:
                        k = "crudo=0,desc>0 (solo sub-puntos: granularidad de ancla)"
                    elif x["crudo_incl_contenedores"] == 0:
                        k = "crudo=0,desc=0 (ausencia total)"
                    else:
                        k = "crudo>=1 (portador es contenedor >10 anclas)"
                    cnt[k] += 1; det.append({"id_pregunta": q, "ancla": a, **x, "diagnostico": k})
        diag[g] = {"nombre": CANONICO[g]["nombre"], "n_anclas_no_resueltas": len(det),
                   "diagnostico": dict(cnt), "detalle": det}
    res["diagnostico_ausencias_fidelidad"] = diag
    res["pares_definitivos"] = pares_definitivos(res)

    if sensibilidad_descendientes:
        # SENSIBILIDAD (fuera de la regla ratificada, informativa, solo trazas
        # base): las ausencia_kg se re-resuelven con incluir_descendientes=True
        # (sub-puntos del punto ancla, contenedores siempre excluidos) y se
        # re-clasifican. No reemplaza la clase primaria.
        sens = []
        for g in ORDEN_GRAFOS:
            aidx = indice_anclas(g)
            index = GraphIndex(cargar_runtime(g))
            for x in filas:
                if x["grafo"] != g or x["clase"] != "ausencia_kg":
                    continue
                payload = json.loads((REPO_DIR / x["traza"]).read_text(encoding="utf-8"))
                resueltas = {a: aidx.resolver(*parse_ancla(a), incluir_descendientes=True) for a in x["anclas"]}
                nav = navegacion_de_traza(payload["trace"], resueltas, index, verificar_replay=False)
                sens.append({"id_pregunta": x["id_pregunta"], "grafo": g, "nombre": CANONICO[g]["nombre"],
                             "veredicto": x["veredicto"], "clase_primaria": "ausencia_kg",
                             "n_nodos_desc": sum(len(v) for v in resueltas.values()),
                             "clase_con_descendientes": clasificar(x["veredicto"], nav["presente"], nav["vista"], nav["consultada"])})
        t = defaultdict(Counter)
        for s in sens:
            t[s["grafo"]][s["clase_con_descendientes"]] += 1
        res["sensibilidad_descendientes_base"] = {
            "nota": "INFORMATIVA, fuera de la regla ratificada: re-clasificación de las trazas base ausencia_kg "
                    "resolviendo el ancla con incluir_descendientes=True (sub-puntos; contenedores excluidos). "
                    "No reemplaza la clase primaria.",
            "reclasificacion_x_grafo": {g: dict(t[g]) for g in ORDEN_GRAFOS}, "detalle": sens}
    escribir_json(out_dir / "atribucion_fallas.json", res)
    (out_dir / "atribucion_fallas.md").write_text(render_md(res), encoding="utf-8")
    (out_dir / "atribucion_por_traza.md").write_text(render_por_traza(res), encoding="utf-8")
    return res


# --------------------------------------------------------------------------- #
# Pares definitivos: clase de la respuesta representativa del veredicto        #
# --------------------------------------------------------------------------- #
def pares_definitivos(res: dict) -> dict:
    """Para cada par (pregunta, grafo) con veredicto DEFINITIVO (64de678), la
    clase de la traza que porta ese veredicto — regla de respuesta
    representativa ratificada como métrica de esta unidad: vías juez_base /
    adjudicacion_base → la traza base; vías juez_enc / adjudicacion_s7 → la
    re-corrida de MENOR rep cuyo veredicto propio coincide con el definitivo.
    Responde la pregunta del mandato (¿los 9-9 incorrectos esconden perfiles
    distintos?) sin mezclar veredictos entre trazas: cada clase sigue siendo la
    de la traza contra su propio veredicto."""
    tabla = {f["id_opaco"]: f for f in cargar("tabla_base")["filas"]}
    defs = cargar("veredictos_definitivos")["definitivos"]
    base = {(x["id_pregunta"], x["grafo"]): x for x in res["base"]["por_traza"]}
    enc = defaultdict(dict)
    for x in res.get("enc", {}).get("por_traza", []):
        enc[(x["id_pregunta"], x["grafo"])][x["rep"]] = x
    filas = []
    for d in defs:
        f = tabla[d["id_opaco_base"]]
        q, g = f["id_pregunta"], f["grafo"]
        if d["via"] in ("juez_base", "adjudicacion_base"):
            x = base[(q, g)]; rep = None
            assert x["veredicto"] == d["definitivo"], (q, g, x["veredicto"], d["definitivo"])
        else:
            if not enc:
                continue   # sin --incluir-enc no hay traza representativa para vías §7
            rep = None
            for r in (1, 2, 3):
                if r in enc[(q, g)] and enc[(q, g)][r]["veredicto"] == d["definitivo"]:
                    rep = r; break
            assert rep is not None, (q, g, d)
            x = enc[(q, g)][rep]
        filas.append({"id_pregunta": q, "grafo": g, "nombre": CANONICO[g]["nombre"], "via": d["via"],
                      "definitivo": d["definitivo"], "traza_representativa": "base" if rep is None else f"enc_r{rep}",
                      "clase": x["clase"], "clasificacion_auxiliar": x["clasificacion_auxiliar"],
                      "n_no_cumplidos": x["n_no_cumplidos"], "n_criterios": x["n_criterios"],
                      "clase_base": base[(q, g)]["clase"], "veredicto_base": base[(q, g)]["veredicto"],
                      "clases_enc": [enc[(q, g)][r]["clase"] if r in enc[(q, g)] else "sin_veredicto_propio"
                                     for r in (1, 2, 3)] if (q, g) in enc else []})
    filas.sort(key=lambda x: (x["id_pregunta"], ORDEN_GRAFOS.index(x["grafo"])))
    t = defaultdict(lambda: defaultdict(Counter))
    for x in filas:
        t[x["grafo"]][x["definitivo"]][x["clase"] or "correcto"] += 1
    perfil_inc = defaultdict(list)
    for x in filas:
        if x["definitivo"] == "incorrecto":
            perfil_inc[x["grafo"]].append({"id_pregunta": x["id_pregunta"], "via": x["via"],
                                           "traza": x["traza_representativa"], "clase": x["clase"],
                                           "aux": x["clasificacion_auxiliar"]})
    return {"regla": pares_definitivos.__doc__.strip(), "n_pares": len(filas),
            "clase_x_grafo_x_definitivo": {g: {v: dict(c) for v, c in sorted(t[g].items())} for g in ORDEN_GRAFOS if g in t},
            "incorrectos_definitivos": {g: perfil_inc[g] for g in ORDEN_GRAFOS},
            "por_par": filas}


# --------------------------------------------------------------------------- #
# Render                                                                       #
# --------------------------------------------------------------------------- #
def _tabla_clase(bloque: dict, titulo: str) -> list[str]:
    L = [f"### {titulo}", "", "| grafo | " + " | ".join(CLASES) + " | correcto (no atribuible) | n |",
         "|---|" + "---|" * (len(CLASES) + 2)]
    for g in ORDEN_GRAFOS:
        r = bloque["clase_x_grafo"][g]
        L.append(f"| {r['nombre']} | " + " | ".join(str(r[c]) for c in CLASES) + f" | {r['correcto']} | {r['n']} |")
    return L + [""]


def _tabla_cruce(cruce: dict, titulo: str, col: str) -> list[str]:
    L = [f"### {titulo}", "", f"| grafo | {col} | " + " | ".join(CLASES) + " | correcto |", "|---|---|" + "---|" * (len(CLASES) + 1)]
    for g in ORDEN_GRAFOS:
        for k, c in cruce.get(g, {}).items():
            L.append(f"| {CANONICO[g]['nombre']} | {k} | " + " | ".join(str(c.get(x, 0)) for x in CLASES) + f" | {c.get('correcto', 0)} |")
    return L + [""]


def _tabla_crit(crit: dict) -> list[str]:
    L = ["### Criterios no cumplidos × grafo × clase (respuesta representativa = la propia)", "",
         "| grafo | clase | n trazas | criterios | no cumplidos | media no cumplidos/traza | tasa no cumplidos |",
         "|---|---|---|---|---|---|---|"]
    for g in ORDEN_GRAFOS:
        for k in CLASES + ["correcto"]:
            c = crit.get(g, {}).get(k)
            if c:
                L.append(f"| {CANONICO[g]['nombre']} | {k} | {c['n']} | {c['criterios']} | {c['no_cumplidos']} | {c['media_no_cumplidos']} | {c['tasa_no_cumplidos']} |")
    return L + [""]


def render_md(res: dict) -> str:
    b = res["base"]
    L = ["# Atribución determinística de fallas — EV2 (U-A0 / A0.2)", "",
         f"Generado {res['generado']}. Regla: `{res['regla']}` (sha256 `{res['regla_sha256'][:12]}…`, "
         f"commit `{(res['regla_commit'] or 'SIN COMMIT')[:7]}`). USD 0, sin API. Determinístico.", "",
         "Grafos (nombre canónico, sha256): " + "; ".join(
             f"{v['nombre']} `{v['sha256'][:8]}` (`{v['path']}`)" for v in res["grafos"].values()) + ".", "",
         f"Replay: {b['replay']['replay_ok']}/{b['replay']['n']} trazas con replay estándar OK y "
         f"{b['replay']['replay_fuerte_ok']}/{b['replay']['n']} con replay fuerte OK.", "",
         "## 1. Corrida base (120 trazas, veredicto de ESA respuesta: juez base + adjudicación de los heredados)", ""]
    L += _tabla_clase(b, "1.a Clase × grafo")
    L += _tabla_cruce(b["clase_x_grafo_x_veredicto"], "1.b Clase × grafo × veredicto", "veredicto")
    L += _tabla_cruce(b["clase_x_grafo_x_auxiliar"], "1.c Clase × grafo × clasificación auxiliar del juez (columna cruzada)", "auxiliar")
    L += _tabla_cruce(b["clase_x_grafo_x_respondible"], "1.d Clase × grafo × flag `respondible` del agente (metadato)", "respondible")
    L += _tabla_crit(b["criterios_no_cumplidos_x_grafo_x_clase"])
    L += ["### 1.e Perfiles por pregunta (KG-Base / KG-Refinado / KG-Reextraído)", "",
          "| perfil | n preguntas |", "|---|---|"]
    for k, n in b["perfiles_conteo"]["conteo"].items():
        L.append(f"| {k} | {n} |")
    L += [""]
    if "enc" in res:
        e = res["enc"]
        L += [f"## 2. Re-corridas §7 ({e['n_trazas']} trazas atribuidas contra su propio veredicto; "
              f"{e['n_excluidas_sin_veredicto_propio']} excluidas sin veredicto propio)", ""]
        L += _tabla_clase(e, "2.a Clase × grafo")
        L += _tabla_cruce(e["clase_x_grafo_x_veredicto"], "2.b Clase × grafo × veredicto", "veredicto")
        L += _tabla_cruce(e["clase_x_grafo_x_auxiliar"], "2.c Clase × grafo × clasificación auxiliar", "auxiliar")
        L += _tabla_crit(e["criterios_no_cumplidos_x_grafo_x_clase"])
    if "pares_definitivos" in res and res["pares_definitivos"]["n_pares"] == 120:
        pd = res["pares_definitivos"]
        L += ["## 3. Pares definitivos (120): clase de la traza representativa del veredicto definitivo", "",
              "Regla ratificada de respuesta representativa (vías juez_base/adjudicacion_base → traza base; "
              "juez_enc/adjudicacion_s7 → re-corrida de menor rep cuyo veredicto propio coincide con el definitivo). "
              "Cada clase sigue siendo la de una traza contra su propio veredicto.", ""]
        L += _tabla_cruce(pd["clase_x_grafo_x_definitivo"], "3.a Clase × grafo × veredicto DEFINITIVO", "definitivo")
        L += ["### 3.b Los incorrectos definitivos, uno por uno (traza representativa, clase, auxiliar)", "",
              "| grafo | id_pregunta | vía | traza | clase | auxiliar |", "|---|---|---|---|---|---|"]
        for g in ORDEN_GRAFOS:
            for x in pd["incorrectos_definitivos"][g]:
                L.append(f"| {CANONICO[g]['nombre']} | {x['id_pregunta']} | {x['via']} | {x['traza']} | {x['clase']} | {x['aux']} |")
        L += [""]
    if "diagnostico_ausencias_fidelidad" in res:
        L += ["## 4. Censo de las 40 anclas de fidelidad por grafo: anclas no resueltas y diagnóstico", "",
              "| grafo | anclas no resueltas | diagnóstico | detalle (id: ancla, crudo/desc) |", "|---|---|---|---|"]
        for g in ORDEN_GRAFOS:
            d = res["diagnostico_ausencias_fidelidad"][g]
            det = "; ".join(f"{x['id_pregunta']}: {x['ancla']} {x['crudo_incl_contenedores']}/{x['con_descendientes']}" for x in d["detalle"])
            L.append(f"| {d['nombre']} | {d['n_anclas_no_resueltas']} | {d['diagnostico']} | {det} |")
        L += [""]
    if "sensibilidad_descendientes_base" in res:
        sb = res["sensibilidad_descendientes_base"]
        L += ["## 4.b Sensibilidad (INFORMATIVA, fuera de la regla ratificada): ausencia_kg base con descendientes", "",
              sb["nota"], "", "| grafo | id_pregunta | veredicto | nodos con descendientes | clase con descendientes |", "|---|---|---|---|---|"]
        for x in sb["detalle"]:
            L.append(f"| {x['nombre']} | {x['id_pregunta']} | {x['veredicto']} | {x['n_nodos_desc']} | {x['clase_con_descendientes']} |")
        L += ["", "Reclasificación × grafo: " + json.dumps(sb["reclasificacion_x_grafo"], ensure_ascii=False), ""]
    hallazgos = UNIDAD_DIR / "code" / "hallazgos_atribucion_texto.md"
    if hallazgos.exists():
        L += ["## 5. Hallazgos numerados", "", hallazgos.read_text(encoding="utf-8").strip(), ""]
    L += ["## Tabla por traza", "", "Ver `atribucion_por_traza.md` (paquete de revisión) y `atribucion_fallas.json` → `base.por_traza` / `enc.por_traza` / `pares_definitivos.por_par`.", ""]
    return "\n".join(L)


def render_por_traza(res: dict) -> str:
    L = ["# Atribución por traza (U-A0 / A0.2)", "",
         "| origen | id_pregunta | grafo | rep | veredicto | fuente | aux | clase | presente | vista (step) | consultada (step, vía) | no cumplidos/n | replay | replay fuerte |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    filas = list(res["base"]["por_traza"]) + list(res.get("enc", {}).get("por_traza", []))
    for x in filas:
        pa = next(iter(x["por_ancla"].values()))
        L.append(f"| {x['origen']} | {x['id_pregunta']} | {x['nombre']} | {x.get('rep', '-')} | {x['veredicto']} | "
                 f"{x['fuente_veredicto']} | {x['clasificacion_auxiliar']} | {x['clase'] or '—'} | {x['ancla_presente']} | "
                 f"{x['ancla_vista']} ({pa.get('vista_en_step')}) | {x['ancla_consultada']} ({pa.get('consultada_en_step')}, {','.join(pa.get('consultada_via', []))}) | "
                 f"{x['n_no_cumplidos']}/{x['n_criterios']} | {x['replay_ok']} | {x['replay_fuerte_ok']} |")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Selftest sintético (sin datos reales)                                        #
# --------------------------------------------------------------------------- #
def _mini_grafo():
    """Mini-grafo sintético con provenances PDF parseables por el censo."""
    DOC = "TO_exterior_cambios_actual.pdf"
    def prov(p): return [{"source_doc": DOC, "location": f"Punto {p}. x"}]
    raw = {"nodes": [
        {"id": "Obligacion_ancla_A", "type": "Obligacion", "label": "Ancla alfa pago exterior",
         "properties": {"descripcion": "contenido del ancla A"}, "provenances": prov("6.11")},
        {"id": "Operacion_vecino_B", "type": "Operacion", "label": "Vecino beta operacion cambio",
         "properties": {}, "provenances": prov("6.12")},
        {"id": "Restriccion_gamma_C", "type": "Restriccion", "label": "Gamma restriccion tope",
         "properties": {}, "provenances": prov("7.1")},
        {"id": "Excepcion_delta_D", "type": "Excepcion", "label": "Delta excepcion pago exterior",
         "properties": {}, "provenances": prov("7.2")},
        # contenedor: porta 11 anclas distintas -> excluido del censo
        {"id": "TextoOrdenado_contenedor", "type": "TextoOrdenado", "label": "Contenedor alfa exterior",
         "properties": {}, "provenances": [{"source_doc": DOC, "location": f"Punto 9.{i}. c"} for i in range(1, 12)]},
    ], "edges": [
        {"source": "Operacion_vecino_B", "target": "Obligacion_ancla_A", "relation": "aplica_a", "properties": {}, "provenances": prov("6.12")},
        {"source": "Obligacion_ancla_A", "target": "Restriccion_gamma_C", "relation": "restringido_por", "properties": {}, "provenances": prov("6.11")},
    ]}
    kg = KnowledgeGraph(run_key="selftest", path=Path("selftest"),
                        nodes=[Node(n["id"], n["type"], n["label"], n["properties"], n["provenances"]) for n in raw["nodes"]],
                        edges=[Edge(e["source"], e["target"], e["relation"], e["properties"], e["provenances"]) for e in raw["edges"]])
    return raw, GraphIndex(kg), AnclaIndex(raw)


def _traza(index: GraphIndex, llamadas: list[tuple[str, dict]], respondible=True) -> dict:
    """Payload sintético construido EJECUTANDO las tools (así el replay pasa)."""
    from metrica import _reejecutar_step
    steps, full = [], []
    for n, (tool, inp) in enumerate(llamadas, 1):
        res = _reejecutar_step(index, {"tool": tool, "input": inp})
        s = json.dumps(res, ensure_ascii=False)
        steps.append({"n": n, "tool": tool, "input": inp,
                      "output_truncado": s if len(s) <= 1200 else s[:1200] + f"… [+{len(s)-1200} chars]",
                      "output_chars": len(s)})
        full.append({"n": n, "tool": tool, "input": inp, "output": res, "output_chars": len(s)})
    return {"meta": {"eje": "fidelidad", "grafo": "selftest", "caso_id": "SELF"},
            "trace": {"steps": steps, "final_json": {"respuesta": "x", "citas": [], "respondible": respondible},
                      "tool_calls_used": len(steps), "hit_tool_limit": False},
            "steps_full": full}


def selftest(out_dir: Path | None = None) -> int:
    out_dir = out_dir or (UNIDAD_DIR / "selftest_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw, index, aidx = _mini_grafo()
    A = ["ext:6.11"]          # ancla presente (Obligacion_ancla_A)
    checks = []
    def chk(nombre, cond, detalle=""):
        checks.append({"check": nombre, "ok": bool(cond), "detalle": detalle}); print(("PASS " if cond else "FAIL ") + nombre + (f"  [{detalle}]" if detalle and not cond else ""))

    # censo sintético
    r = resolver_anclas(["ext:6.11", "ext:8.8", "ext:9.3"], aidx)
    chk("censo: ancla presente resuelve a 1 nodo", r["ext:6.11"] == ["Obligacion_ancla_A"], str(r))
    chk("censo: ancla inexistente resuelve a 0", r["ext:8.8"] == [])
    chk("censo: ancla portada SOLO por contenedor (>10 anclas) resuelve a 0", r["ext:9.3"] == [], str(r))

    # 1. ausencia_kg (ancla no está en el grafo), aunque el agente navegue
    t = _traza(index, [("buscar_nodos", {"consulta": "alfa exterior", "limite": 10}), ("ver_nodo", {"id": "Obligacion_ancla_A"})])
    at = atribuir_payload(t, ["ext:8.8"], aidx, index, "incorrecto")
    chk("clase ausencia_kg", at["clase"] == "ausencia_kg" and at["ancla_presente"] is False, at["clase"])
    # 1b. ausencia_kg por contenedor: el único portador es contenedor
    at = atribuir_payload(t, ["ext:9.3"], aidx, index, "parcial")
    chk("clase ausencia_kg (portador único = contenedor excluido)", at["clase"] == "ausencia_kg", at["clase"])

    # 2. alcanzabilidad: búsquedas que no devuelven el ancla; ver_nodo de otro nodo
    t = _traza(index, [("buscar_nodos", {"consulta": "gamma tope", "limite": 10}), ("ver_nodo", {"id": "Restriccion_gamma_C"})])
    at = atribuir_payload(t, A, aidx, index, "incorrecto")
    chk("clase alcanzabilidad (ni vista ni consultada)", at["clase"] == "alcanzabilidad" and not at["ancla_vista"], at["clase"])
    # 2b. alcanzabilidad con ver_nodo de id inexistente (error) del ancla mal escrito
    t = _traza(index, [("ver_nodo", {"id": "Obligacion_ancla_A_typo"})])
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("clase alcanzabilidad (ver_nodo con error no cuenta como consulta)", at["clase"] == "alcanzabilidad", at["clase"])
    # 2c. ver_vecinos DEL PROPIO nodo ancla sin verlo antes: no es 'consultada' (regla heredada de metrica.py) ni 'vista'
    t = _traza(index, [("ver_vecinos", {"id": "Obligacion_ancla_A", "direccion": "ambas"})])
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("borde: ver_vecinos sobre el propio nodo ancla (sin buscar ni ver_nodo) -> alcanzabilidad", at["clase"] == "alcanzabilidad", at["clase"])

    # 3. vista_no_consultada: aparece en buscar_nodos, nunca ver_nodo ni vecino
    t = _traza(index, [("buscar_nodos", {"consulta": "alfa exterior", "limite": 10}), ("ver_nodo", {"id": "Excepcion_delta_D"})])
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("clase vista_no_consultada", at["clase"] == "vista_no_consultada" and at["ancla_vista"] and not at["ancla_consultada"], at["clase"])
    chk("vista_en_step = 1", at["por_ancla"]["ext:6.11"]["vista_en_step"] == 1)
    # 3b. vista y luego ver_vecinos del PROPIO ancla (sin ver_nodo): sigue vista_no_consultada (borde heredado)
    t = _traza(index, [("buscar_nodos", {"consulta": "alfa exterior", "limite": 10}), ("ver_vecinos", {"id": "Obligacion_ancla_A", "direccion": "salientes"})])
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("borde: vista + ver_vecinos del propio ancla (sin ver_nodo) -> vista_no_consultada", at["clase"] == "vista_no_consultada", at["clase"])
    # 3c. límite de buscar_nodos: el ancla queda fuera del top-k -> no vista
    t = _traza(index, [("buscar_nodos", {"consulta": "delta pago exterior", "limite": 1})])
    top = index.buscar_nodos("delta pago exterior", 1)["resultados"][0]["id"]
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("límite: ancla fuera del top-k -> no vista (alcanzabilidad)",
        top == "Excepcion_delta_D" and at["ancla_vista"] is False and at["clase"] == "alcanzabilidad", f"top={top}")
    t = _traza(index, [("buscar_nodos", {"consulta": "delta pago exterior", "limite": 2})])
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("límite: con top-2 el ancla entra -> vista_no_consultada", at["clase"] == "vista_no_consultada", at["clase"])

    # 4. generacion vía ver_nodo
    t = _traza(index, [("buscar_nodos", {"consulta": "alfa exterior", "limite": 10}), ("ver_nodo", {"id": "Obligacion_ancla_A"})])
    at = atribuir_payload(t, A, aidx, index, "incorrecto")
    chk("clase generacion (ver_nodo del ancla)", at["clase"] == "generacion" and at["por_ancla"]["ext:6.11"]["consultada_via"] == ["ver_nodo"], at["clase"])
    chk("consultada_en_step = 2", at["por_ancla"]["ext:6.11"]["consultada_en_step"] == 2)
    # 4b. generacion vía ver_vecinos: el ancla aparece como vecino_id (nunca vista en buscar_nodos)
    t = _traza(index, [("ver_vecinos", {"id": "Operacion_vecino_B", "direccion": "salientes"})])
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("clase generacion (ancla como vecino_id, nunca vista) — consultada prima sobre no-vista", at["clase"] == "generacion" and not at["ancla_vista"], at["clase"])
    # 4c. ver_vecinos con direccion opuesta no la alcanza
    t = _traza(index, [("ver_vecinos", {"id": "Operacion_vecino_B", "direccion": "entrantes"})])
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("ver_vecinos en dirección opuesta no consulta el ancla -> alcanzabilidad", at["clase"] == "alcanzabilidad", at["clase"])

    # 5. correcto: no atribuible
    t = _traza(index, [("ver_nodo", {"id": "Obligacion_ancla_A"})])
    at = atribuir_payload(t, A, aidx, index, "correcto")
    chk("correcto -> clase None (denominador)", at["clase"] is None)
    try:
        clasificar("requiere_adjudicacion", True, True, True); chk("veredicto no atribuible levanta error", False)
    except ValueError:
        chk("veredicto no atribuible levanta error", True)

    # 6. multi-ancla: presente si alguna resuelve; vista/consultada por ancla (cualquiera)
    t = _traza(index, [("ver_nodo", {"id": "Obligacion_ancla_A"})])
    at = atribuir_payload(t, ["ext:8.8", "ext:6.11"], aidx, index, "parcial")
    chk("multi-ancla: una ausente + una consultada -> generacion", at["clase"] == "generacion" and at["por_ancla"]["ext:8.8"]["presente"] is False, at["clase"])

    # 7. replay: traza manipulada -> divergencia detectada (estándar y fuerte)
    t = _traza(index, [("buscar_nodos", {"consulta": "alfa exterior", "limite": 10})])
    t["trace"]["steps"][0]["output_truncado"] = "{\"consulta\": \"OTRA\"}"; t["trace"]["steps"][0]["output_chars"] = 5
    t["steps_full"][0]["output"] = {"consulta": "OTRA"}
    at = atribuir_payload(t, A, aidx, index, "parcial")
    chk("replay estándar detecta divergencia", at["replay_ok"] is False and at["replay_fallas"])
    chk("replay fuerte detecta divergencia", at["replay_fuerte_ok"] is False)

    # 8. determinismo: dos corridas idénticas
    t = _traza(index, [("buscar_nodos", {"consulta": "alfa exterior", "limite": 10}), ("ver_nodo", {"id": "Obligacion_ancla_A"})])
    a1 = atribuir_payload(t, A, aidx, index, "parcial"); a2 = atribuir_payload(t, A, aidx, index, "parcial")
    chk("determinismo: salida idéntica en dos corridas", json.dumps(a1, sort_keys=True) == json.dumps(a2, sort_keys=True))

    # 9. precedencia completa sobre la tabla de verdad
    tv = [(False, False, False, "ausencia_kg"), (False, True, True, "ausencia_kg"),
          (True, False, False, "alcanzabilidad"), (True, True, False, "vista_no_consultada"),
          (True, False, True, "generacion"), (True, True, True, "generacion")]
    chk("tabla de verdad de precedencia (6 filas)", all(clasificar("parcial", p, v, c) == e for p, v, c, e in tv))

    n_ok = sum(1 for c in checks if c["ok"])
    print(f"selftest atribución: {n_ok}/{len(checks)} PASS")
    escribir_json(out_dir / "selftest_atribucion.json", {"generado": datetime.now().isoformat(timespec="seconds"),
                                                          "n_checks": len(checks), "n_ok": n_ok, "checks": checks})
    return 0 if n_ok == len(checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--correr", action="store_true", help="Fase B: exige regla_atribucion.md commiteada")
    ap.add_argument("--incluir-enc", action="store_true", help="tabla separada de las 198 re-corridas §7")
    ap.add_argument("--sensibilidad-descendientes", action="store_true",
                    help="informativo: re-clasifica las ausencia_kg base resolviendo con descendientes")
    ap.add_argument("--verificar-estructura", action="store_true",
                    help="Fase A: solo conteos de los veredictos por respuesta (base 120 / §7 198); "
                         "no abre trazas ni atribuye nada")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.selftest:
        return selftest(args.out)
    if args.verificar_estructura:
        verificar_sellos()
        vb = veredictos_base(); ve = veredictos_enc()
        print("base: n =", len(vb), "| veredicto:", dict(Counter(v["veredicto"] for v in vb.values())),
              "| fuente:", dict(Counter(v["fuente_veredicto"] for v in vb.values())),
              "| aux:", dict(Counter(v["clasificacion_auxiliar"] for v in vb.values())))
        print("base atribuibles (parcial+incorrecto):", sum(1 for v in vb.values() if v["veredicto"] in VEREDICTOS_ATRIBUIBLES),
              "| por grafo:", {g: dict(Counter(v["veredicto"] for (q, gg), v in vb.items() if gg == g)) for g in ORDEN_GRAFOS})
        print("enc: n =", len(ve), "| veredicto:", dict(Counter(v["veredicto"] for v in ve.values())),
              "| fuente:", dict(Counter(v["fuente_veredicto"] for v in ve.values())))
        print("regla commiteada:", regla_sellada())
        return 0
    if args.correr:
        res = correr(incluir_enc=args.incluir_enc, out_dir=args.out,
                     sensibilidad_descendientes=args.sensibilidad_descendientes)
        b = res["base"]
        print(json.dumps(b["clase_x_grafo"], ensure_ascii=False, indent=1))
        print("replay:", b["replay"])
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
