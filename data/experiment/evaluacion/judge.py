"""
judge.py — LLM-as-judge v2.0 (Fase 2.3). Arquitectura de DOS PASOS.

Modelo juez: claude-sonnet-4-6 (distinto y mayor que el respondedor Haiku 4.5),
temperatura 0. El juez es CIEGO al grafo que generó la respuesta.

PROCEDENCIA DEL RUBRIC / CHANGELOG:
  v1   (09/06): rubric inicial cerrado con la autora sobre 12 trazas dev.
  v1.1 (09/06): 4 reglas declarativas para afilar la frontera correcta/parcial
        (omisión no baja correctitud; hedge vs afirmación; patas las define la
        pregunta; cita_documento_correcto a nivel documento). Calibración: el juez
        NO honró las reglas — siguió contando omisiones y baja legibilidad como
        "imprecisión" → 7/12 desacuerdos (todos H:correcta / J:parcial).
  v1.2 (09/06): few-shot con 3 ejemplos resueltos (held-out protocol). Mejoró a
        12/15 celdas held-out pero el patrón omisión→parcial PERSISTIÓ en CQ-023
        R3 (legibilidad) y CQ-001 R1 (re-clasificó la omisión como "central"). El
        few-shot generaliza angosto: parchea instancias, no el principio.
  v2.0 (09/06): arquitectura de DOS PASOS. Motivación: ni las reglas declarativas
        ni el few-shot impidieron que el juez metiera omisiones/legibilidad en
        correctitud. El dos-pasos lo impide POR CONSTRUCCIÓN: correctitud deja de
        ser un juicio holístico y pasa a computarse determinísticamente a partir
        de la verificación afirmación-por-afirmación.
        Paso 1 (CIEGO al ground truth): descompone la respuesta del agente en
          (a) afirmaciones_verificables [{enunciado, central}],
          (b) reportes_de_alcance (no entran a verificación),
          (c) patas_de_la_pregunta (derivadas SOLO del texto de la pregunta).
        Paso 2 (con ground truth): asigna verdict ∈ {verdadero, falso,
          no_soportado} a cada afirmación; cobertura ∈ {cubierta, no_cubierta} a
          cada pata; cita_documento_correcto / cita_precision; y, si unanswerable,
          abstencion / especulacion_en_prosa.
        Mapping determinístico (en Python, no en el LLM):
          - "central" = afirmación de la que depende responder lo que la pregunta pide.
          - incorrecta = alguna central falsa.
          - parcial    = (no incorrecta) y [alguna central no_soportada  Ó
                          alguna afirmación (cualquiera) falsa].
          - correcta   = centrales todas verdaderas y NINGUNA afirmación falsa.
          - secundaria no_soportada → se lista en afirmaciones_no_soportadas SIN
            bajar correctitud.
          - completitud = "completa" si todas las patas cubiertas, si no "parcial".
            Un reporte de alcance sobre una pata = pata no cubierta.
        Citas y abstención: sin cambios de criterio respecto de v1.
        Resultado v2.0: CQ-001 R1 flipeó (omisión ya no baja correctitud), pero
        CQ-023 R3/R1 → parcial y regresión de la especulación de dev_unans R3.
  v2.1 (09/06): cierra las dos fallas de v2.0 sin validación paramétrica.
        Motivación: (a) el verificador marcaba "no_soportado" afirmaciones
        VERDADERAS pero más granulares que un respuesta_esperada de 1-2 frases
        (códigos contables, sub-componentes del COn1) → parcial. (b) Dar "licencia
        de dominio" al verificador (validar contra conocimiento paramétrico) fue
        RECHAZADO: el referente debe ser auditable. (c) El Paso 2 era ciego a la
        prosa → no detectaba especulación.
        Cambios:
        · DECISIÓN 3: el Paso 2 recibe la `respuesta` cruda del agente,
          EXCLUSIVAMENTE para evaluar especulacion_en_prosa.
        · DECISIÓN 5 — referente del Paso 2 = respuesta_esperada + cita_textual +
          ground_truth_secciones (gold auditable, no conocimiento paramétrico).
        · Mapping nuevo de correctitud: central falsa → incorrecta; secundaria
          falsa o imprecisa → parcial; no_soportada (cualquier centralidad) → NO
          baja correctitud. Toda no_soportada se reporta en
          afirmaciones_no_soportadas (lista + conteo, centrales vs secundarias).
        · Toda traza con centrales no_soportadas > 0 queda marcada
          requiere_adjudicacion_humana=true: en la corrida congelada va a una cola
          que la autora adjudica contra los PDFs, con registro. Replica lo que la
          revisora hizo con Capitales 8.2.3.2 (verificar a mano una afirmación que
          el gold resumido no soportaba).
        Resultado v2.1: 3/3 targets (CQ-023 R3/R1 correcta + adjudicación; dev_unans
        R3 especulación=True), pero 1 regresión: dev_unans R3 abstención→incorrecta.
  v2.1.1 (09/06): restauración de la cláusula O4 (omitida al portar a dos pasos;
        SIN cambios semánticos respecto del rubric original). La especulación en
        prosa se marca SOLO en especulacion_en_prosa y NUNCA modifica el veredicto
        de abstención. Una abstención con especulación es correcta + especulación
        true (caso dev_unans_1 R3). abstencion='incorrecta' se reserva para
        respondible=true en unanswerable, o abstenciones que inventan valores/citas.
NO ajustar este prompt ante desacuerdos sin decisión de la autora.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from loader import EVAL_DIR
from harness import TRAZAS_DIR, _extract_json

JUDGE_MODEL = "claude-sonnet-4-6"
JUDGE_TEMPERATURE = 0
STEP1_MAX_TOKENS = 1500
STEP2_MAX_TOKENS = 1800
POOL_PATH = EVAL_DIR / "queries" / "dev_pool.json"
REPORT_PATH = EVAL_DIR / "02_calibracion_juez.md"

# --------------------------------------------------------------------------- #
# Paso 1 — descomposición (CIEGO al ground truth)                              #
# --------------------------------------------------------------------------- #
STEP1_SYSTEM = """\
Sos un analista de descomposición. Recibís una PREGUNTA y la RESPUESTA de un \
sistema de QA. NO tenés la respuesta correcta ni ningún ground truth, y NO debés \
juzgar si la respuesta es verdadera. Tu única tarea es descomponer.

Devolvé EXACTAMENTE este JSON, sin texto extra:
{
  "afirmaciones_verificables": [{"enunciado": "<afirmación factual atómica>", "central": true|false}],
  "reportes_de_alcance": ["<enunciado de alcance>", ...],
  "patas_de_la_pregunta": ["<sub-pregunta o componente>", ...]
}

Definiciones:
- afirmaciones_verificables: cada enunciado factual que la respuesta AFIRMA como \
cierto sobre el dominio (un hecho, valor, regla, plazo, criterio, fórmula…). \
Atomizá: una afirmación por ítem. Lo que la respuesta NO dice (una omisión) NO es \
una afirmación: no lo inventes.
  · central=true si responder lo que la PREGUNTA pide DEPENDE de ese enunciado \
(es parte del núcleo pedido). central=false si es contexto, detalle accesorio o \
elaboración.
- reportes_de_alcance: enunciados que NO afirman un hecho del dominio sino que \
reportan qué se halló o no en la fuente ("no identifiqué excepciones en la \
información disponible", "no se encontró el dato en el grafo"). Van SOLO acá, \
NUNCA en afirmaciones_verificables.
- patas_de_la_pregunta: los componentes que la PREGUNTA pide responder, derivados \
EXCLUSIVAMENTE del texto de la pregunta (no de la respuesta). Ej.: "¿X? ¿Hay \
excepciones?" → ["X", "excepciones"]. Una pregunta factual simple tiene UNA sola \
pata."""

# --------------------------------------------------------------------------- #
# Paso 2 — verificación (con ground truth)                                     #
# --------------------------------------------------------------------------- #
STEP2_SYSTEM = """\
Sos un verificador experto en regulación del BCRA. Recibís: la PREGUNTA; el \
REFERENTE auditable = respuesta_esperada + cita_textual + ground_truth_secciones \
(esta es tu ÚNICA verdad de referencia: NO valides contra tu conocimiento propio, \
SOLO contra el referente); la descomposición de la respuesta del agente \
(afirmaciones_verificables con flag 'central', reportes_de_alcance, \
patas_de_la_pregunta); las citas del agente; respuesta_cruda (el texto literal del \
agente, que usás SOLO para evaluar especulacion_en_prosa); campos_automaticos y la \
categoria. NO re-descompongas; trabajá sobre lo dado.

Devolvé EXACTAMENTE este JSON, sin texto extra:
{
  "verificaciones": [{"enunciado": "...", "central": true|false, "verdict": "verdadero"|"falso"|"no_soportado"}],
  "cobertura_patas": [{"pata": "...", "cobertura": "cubierta"|"no_cubierta"}],
  "cita_documento_correcto": true|false,
  "cita_precision": "punto"|"pagina"|"ausente",
  "abstencion": "correcta"|"incorrecta"|null,
  "especulacion_en_prosa": true|false|null,
  "justificacion": {"citas": "<1 frase>", "abstencion": "<1 frase o vacío>"}
}

Reglas:
- verificaciones: copiá cada afirmación verificable (conservando su 'central') y \
asignale verdict contra el REFERENTE: "verdadero" si coincide o es consistente con \
el referente (aunque esté expresada de forma poco legible, p. ej. en códigos \
contables: si el contenido es consistente con el referente, es verdadero); "falso" \
si CONTRADICE el referente o es imprecisa/inexacta respecto de él; "no_soportado" \
si el referente NO permite ni confirmarla ni refutarla (típicamente porque la \
afirmación es más granular o específica que lo que el referente expresa). NUNCA \
uses tu conocimiento propio para confirmar una afirmación que el referente no \
cubre: en ese caso es "no_soportado".
- cobertura_patas: para cada pata, "cubierta" si alguna afirmación verificable la \
responde sustantivamente; "no_cubierta" si solo hay un reporte de alcance sobre \
esa pata, o nada. Un reporte de alcance NUNCA cubre una pata.
- cita_documento_correcto: true si AL MENOS UNA cita apunta a un TO del ground \
truth; los documentos adicionales NO lo anulan. cita_precision: "punto" (nivel \
punto/sección), "pagina" (nivel página) o "ausente". NUNCA combines documento con \
sección, ni en el veredicto ni en la justificación.
- abstencion / especulacion_en_prosa: SOLO si categoria=="unanswerable" (si no, \
ambos null). especulacion_en_prosa: leé `respuesta_cruda` y marcá true si el texto \
afirma estructura o ubicaciones del documento no verificadas (p. ej. "la tabla \
estaría en el punto 6.5 que especificaría estos porcentajes", asumir que existe \
una tabla/un punto que contendría el dato).
  Abstención (solo preguntas unanswerable): abstencion='correcta' si y solo si \
respondible=false y la respuesta no inventa valores ni citas. La especulación en \
prosa sobre estructura del documento o ubicaciones no verificadas se marca \
exclusivamente en el flag especulacion_en_prosa y NUNCA modifica el veredicto de \
abstención: una abstención con especulación es abstencion='correcta' + \
especulacion_en_prosa=true (caso de referencia: dev_unans_1 R3). \
abstencion='incorrecta' se reserva para respondible=true en una unanswerable, o \
para abstenciones que inventan valores o citas.
- FIDELIDAD de citas: NO la evalúes; campos_automaticos.citations_unseen_normalized \
es solo contexto."""


# --------------------------------------------------------------------------- #
# Llamada + parseo                                                             #
# --------------------------------------------------------------------------- #
def _call(client, system, payload, max_tokens):
    resp = client.messages.create(
        model=JUDGE_MODEL, max_tokens=max_tokens, temperature=JUDGE_TEMPERATURE,
        system=system,
        messages=[{"role": "user",
                   "content": json.dumps(payload, ensure_ascii=False, indent=2)}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    parsed, err = _extract_json(text)
    u = resp.usage
    return {"parsed": parsed, "raw": None if parsed else text, "error": err,
            "usage": {"in": u.input_tokens, "out": u.output_tokens}}


# --------------------------------------------------------------------------- #
# Mapping determinístico (correctitud y completitud por construcción)          #
# --------------------------------------------------------------------------- #
def _map_correctitud(verifs):
    # v2.1: no_soportado NUNCA baja correctitud (cualquier centralidad).
    centrals = [v for v in verifs if v.get("central")]
    if any(v.get("verdict") == "falso" for v in centrals):
        return "incorrecta"
    if any(v.get("verdict") == "falso" for v in verifs):   # secundaria falsa/imprecisa
        return "parcial"
    return "correcta"


def _map_completitud(cobertura):
    if not cobertura:
        return "completa"
    return "completa" if all(c.get("cobertura") == "cubierta" for c in cobertura) \
        else "parcial"


def _corr_just(correctitud, verifs):
    falses = [v["enunciado"] for v in verifs if v.get("verdict") == "falso"]
    if correctitud == "incorrecta":
        return "Afirmación central falsa: " + "; ".join(falses)
    if correctitud == "parcial":
        return "Afirmación secundaria falsa/imprecisa: " + "; ".join(falses)
    return "Centrales todas verdaderas o no_soportadas; ninguna afirmación falsa."


def _compute(step1, step2, categoria):
    s2 = step2 or {}
    verifs = s2.get("verificaciones") or []
    cobertura = s2.get("cobertura_patas") or []
    is_unans = categoria == "unanswerable"

    correctitud = None if is_unans else _map_correctitud(verifs)
    completitud = None if is_unans else _map_completitud(cobertura)
    ns_centrales = [v.get("enunciado") for v in verifs
                    if v.get("central") and v.get("verdict") == "no_soportado"]
    ns_secundarias = [v.get("enunciado") for v in verifs
                      if not v.get("central") and v.get("verdict") == "no_soportado"]
    afirm_ns = {"centrales": ns_centrales, "secundarias": ns_secundarias,
                "n_centrales": len(ns_centrales), "n_secundarias": len(ns_secundarias)}
    requiere_adj = len(ns_centrales) > 0

    just = {}
    if not is_unans:
        just["correctitud"] = _corr_just(correctitud, verifs)
        uncov = [c.get("pata") for c in cobertura if c.get("cobertura") == "no_cubierta"]
        just["completitud"] = ("Todas las patas cubiertas." if not uncov
                               else "Patas no cubiertas: " + "; ".join(uncov))
    s2just = s2.get("justificacion") or {}
    just["citas"] = s2just.get("citas", "")
    if is_unans:
        just["abstencion"] = s2just.get("abstencion", "")

    return {
        "correctitud": correctitud,
        "completitud": completitud,
        "cita_documento_correcto": s2.get("cita_documento_correcto"),
        "cita_precision": s2.get("cita_precision"),
        "abstencion": s2.get("abstencion") if is_unans else None,
        "especulacion_en_prosa": s2.get("especulacion_en_prosa") if is_unans else None,
        "afirmaciones_no_soportadas": afirm_ns,
        "requiere_adjudicacion_humana": requiere_adj,
        "justificacion": just,
    }


def judge_trace(client, pool_item, trace):
    fj = trace.get("final_json") or {}
    pregunta = pool_item.get("pregunta")
    categoria = pool_item.get("categoria")

    s1 = _call(client, STEP1_SYSTEM, {
        "pregunta": pregunta,
        "respuesta_agente": {"respuesta": fj.get("respuesta"),
                             "respondible": fj.get("respondible")},
    }, STEP1_MAX_TOKENS)

    s2 = _call(client, STEP2_SYSTEM, {
        "pregunta": pregunta,
        "categoria": categoria,
        "referente": {
            "respuesta_esperada": pool_item.get("respuesta_esperada"),
            "cita_textual": pool_item.get("cita_textual"),
            "ground_truth_secciones": pool_item.get("ground_truth_secciones"),
        },
        "descomposicion": s1["parsed"],
        "citas_agente": fj.get("citas"),
        "respondible": fj.get("respondible"),
        "respuesta_cruda": fj.get("respuesta"),
        "campos_automaticos": {
            "citations_unseen_normalized": trace.get("citations_unseen_normalized"),
            "hit_tool_limit": trace.get("hit_tool_limit"),
        },
    }, STEP2_MAX_TOKENS)

    verdict = _compute(s1["parsed"], s2["parsed"], categoria)
    return {"verdict": verdict, "step1": s1["parsed"], "step2": s2["parsed"],
            "usage": {"in": s1["usage"]["in"] + s2["usage"]["in"],
                      "out": s1["usage"]["out"] + s2["usage"]["out"]},
            "errors": [e for e in (s1["error"], s2["error"]) if e]}


# --------------------------------------------------------------------------- #
# Referencia humana + protocolo de calibración                                 #
# --------------------------------------------------------------------------- #
HUMAN = {
    ("CQ-001", "run_3"): {"correctitud": "correcta", "completitud": "completa"},
    ("CQ-001", "run_1"): {"correctitud": "correcta", "completitud": "completa"},
    ("CQ-009", "run_3"): {"correctitud": "correcta",
                          "_nota": "buena, pero cita de sección imprecisa (4.1 vs 4.2)"},
    ("CQ-009", "run_1"): {"correctitud": "incorrecta"},
    ("CQ-023", "run_3"): {"correctitud": "correcta",
                          "_nota": "aceptable; baja legibilidad (códigos contables)"},
    ("CQ-023", "run_1"): {"correctitud": "correcta"},
    ("CQ-029", "run_3"): {"correctitud": "correcta", "completitud": "parcial"},
    ("CQ-029", "run_1"): {"correctitud": "correcta", "completitud": "parcial",
                          "_nota": "mejor que R3 por hedge explícito"},
    ("CQ-032", "run_3"): {"correctitud": "correcta", "completitud": "completa"},
    ("CQ-032", "run_1"): {"correctitud": "correcta", "completitud": "completa"},
    ("dev_unans_1", "run_3"): {"abstencion": "correcta", "especulacion_en_prosa": True},
    ("dev_unans_1", "run_1"): {"abstencion": "correcta", "especulacion_en_prosa": False},
}

CALIB_FILES = [("run_3", TRAZAS_DIR / "manual_run_3.json"),
               ("run_1", TRAZAS_DIR / "manual_run_1.json")]
CALIB_QIDS = ["CQ-001", "CQ-009", "CQ-023", "CQ-029", "CQ-032", "dev_unans_1"]
COMPARE_DIMS = ["correctitud", "completitud", "cita_documento_correcto",
                "cita_precision", "abstencion", "especulacion_en_prosa"]

# Trazas que fueron EJEMPLOS embebidos en v1.2 (few-shot). En v2.0 no hay few-shot;
# se marcan solo por transparencia (ya no son sanity check trivial).
EX_EMBEBIDAS = {("CQ-001", "run_3"), ("CQ-009", "run_3"), ("CQ-029", "run_1")}

# Celdas (qid, run, dim) que coincidían con el humano en v1.2 — baseline de regresión.
V12_AGREED = {
    ("CQ-001", "run_3", "correctitud"), ("CQ-001", "run_3", "completitud"),
    ("CQ-009", "run_3", "correctitud"),
    ("CQ-029", "run_1", "correctitud"), ("CQ-029", "run_1", "completitud"),
    ("CQ-029", "run_3", "correctitud"), ("CQ-029", "run_3", "completitud"),
    ("CQ-032", "run_3", "correctitud"), ("CQ-032", "run_3", "completitud"),
    ("CQ-032", "run_1", "correctitud"), ("CQ-032", "run_1", "completitud"),
    ("CQ-009", "run_1", "correctitud"),
    ("CQ-023", "run_1", "correctitud"),
    ("dev_unans_1", "run_3", "abstencion"),
    ("dev_unans_1", "run_3", "especulacion_en_prosa"),
    ("dev_unans_1", "run_1", "abstencion"),
    ("dev_unans_1", "run_1", "especulacion_en_prosa"),
}
# Criterio de éxito v2.1: CQ-023 R3/R1 correcta (con flags) y dev_unans R3
# especulación=True; cero regresiones.
TARGETS = [("CQ-023", "run_3", "correctitud", "correcta"),
           ("CQ-023", "run_1", "correctitud", "correcta"),
           ("dev_unans_1", "run_3", "especulacion_en_prosa", True)]

# Adjudicaciones humanas YA resueltas por la revisora (registro auditable).
ADJUDICADAS = {
    ("CQ-023", "run_3"): (
        "RESUELTA por la revisora (09/06): las 3 afirmaciones centrales "
        "no_soportadas son TEXTUALES del TO de Régimen Informativo Contable "
        "Mensual — RPC = 70200000 en la Sección 8; PNb y PNc con sus fórmulas "
        "literales en las Secciones 6/8. Las 3 son VERDADERAS. La marca "
        "requiere_adjudicacion_humana=True funcionó como se diseñó."),
}


def run_calibration():
    load_dotenv(EVAL_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise SystemExit(f"ERROR: ANTHROPIC_API_KEY no seteada en {EVAL_DIR/'.env'}")
    import anthropic
    client = anthropic.Anthropic()
    pool = {q["id"]: q for q in json.load(open(POOL_PATH, encoding="utf-8"))["preguntas"]}

    rows = []
    for run_key, path in CALIB_FILES:
        traces = {t["qid"]: t for t in json.load(open(path, encoding="utf-8"))["trazas"]}
        for qid in CALIB_QIDS:
            tr = traces.get(qid)
            if tr is None:
                continue
            out = judge_trace(client, pool[qid], tr)
            v = out["verdict"]
            human = HUMAN.get((qid, run_key), {})
            disagreements = [dim for dim in COMPARE_DIMS
                             if human.get(dim) is not None and v.get(dim) is not None
                             and human.get(dim) != v.get(dim)]
            rows.append({"qid": qid, "run": run_key,
                         "ex_embebida": (qid, run_key) in EX_EMBEBIDAS,
                         "verdict": v, "step1": out["step1"], "step2": out["step2"],
                         "human": human, "disagreements": disagreements,
                         "errors": out["errors"]})
            tag = " [ex-embebida]" if (qid, run_key) in EX_EMBEBIDAS else ""
            d = ("  ⚠ DESACUERDO: " + ", ".join(disagreements)) if disagreements else ""
            print(f"[{run_key}] {qid}{tag}: corr={v.get('correctitud')} "
                  f"compl={v.get('completitud')} doc={v.get('cita_documento_correcto')} "
                  f"prec={v.get('cita_precision')} abst={v.get('abstencion')} "
                  f"espec={v.get('especulacion_en_prosa')}{d}"
                  + (f"  ERR={out['errors']}" if out["errors"] else ""), flush=True)

    # regresiones
    regressions = []
    for (qid, run_key, dim) in V12_AGREED:
        r = next((x for x in rows if x["qid"] == qid and x["run"] == run_key), None)
        if r and r["human"].get(dim) is not None and r["verdict"].get(dim) is not None \
                and r["human"].get(dim) != r["verdict"].get(dim):
            regressions.append((qid, run_key, dim, r["verdict"].get(dim), r["human"].get(dim)))
    # criterio de éxito
    targets_status = []
    for (qid, run_key, dim, expected) in TARGETS:
        r = next((x for x in rows if x["qid"] == qid and x["run"] == run_key), None)
        got = r["verdict"].get(dim) if r else None
        targets_status.append((qid, run_key, dim, expected, got, got == expected))
    success = all(ok for *_, ok in targets_status) and not regressions

    _write_report(rows, regressions, targets_status, success)

    n_dis = sum(1 for r in rows if r["disagreements"])
    print("\n=== RESUMEN v2.1.1 (dos pasos) ===")
    print(f"  Filas: {len(rows)} | filas con desacuerdo: {n_dis}")
    print("  Criterio de éxito (targets que deben flipear):")
    for qid, rk, dim, exp, got, ok in targets_status:
        print(f"     {'✅' if ok else '❌'} {qid}/{rk}/{dim}: got={got} (esperado {exp})")
    print(f"  Regresiones: {len(regressions)}")
    for q, rk, dim, jv, hv in regressions:
        print(f"     ⚠ REGRESIÓN {q}/{rk}/{dim}: J:{jv} vs H:{hv}")
    print(f"  ÉXITO v2.0: {'SÍ' if success else 'NO → frenar y reportar sin iterar'}")
    print(f"\nReporte: {REPORT_PATH}")
    return rows


def _cell(human, verdict, dim):
    hv, jv = human.get(dim), verdict.get(dim)
    if hv is None:
        return f"{jv} (—)"
    return f"J:{jv} / H:{hv} {'✅' if hv == jv else '❌'}"


def _write_report(rows, regressions, targets_status, success):
    L = ["# Calibración del juez v2.1.1 (dos pasos) — juez vs. humano", ""]
    L.append(f"Juez: `{JUDGE_MODEL}` (temp {JUDGE_TEMPERATURE}), arquitectura de DOS "
             "PASOS. Respondedor: `claude-haiku-4-5-20251001`. Input CIEGO al grafo.")
    L.append("")
    L.append("correctitud y completitud se COMPUTAN determinísticamente a partir de "
             "la verificación afirmación-por-afirmación (Paso 2); no son un juicio "
             "holístico del LLM. v2.1: no_soportado NO baja correctitud; las "
             "afirmaciones centrales no_soportadas marcan la traza para adjudicación "
             "humana. Referente auditable = respuesta_esperada + cita_textual + "
             "ground_truth_secciones. Ver changelog en `judge.py`.")
    L.append("")
    L.append(f"**Resultado: {'✅ ÉXITO' if success else '❌ NO se cumple el criterio'}** "
             "(targets flipean + cero regresiones).")
    L.append("")
    L.append("Celdas: `J:<juez> / H:<humano> ✅/❌`; `<juez> (—)` sin veredicto humano.")
    L.append("")
    L.append("| qid | run | | correctitud | completitud | cita_doc | cita_prec | abst | espec | adj? | desac. |")
    L.append("|-----|-----|-|-------------|-------------|----------|-----------|------|-------|------|--------|")
    for r in rows:
        h, v = r["human"], r["verdict"]
        mark = "ex-emb" if r["ex_embebida"] else ""
        cells = [_cell(h, v, d) for d in COMPARE_DIMS]
        adj = "⚑" if v.get("requiere_adjudicacion_humana") else ""
        dis = ", ".join(r["disagreements"]) if r["disagreements"] else "—"
        L.append(f"| {r['qid']} | {r['run']} | {mark} | " + " | ".join(cells)
                 + f" | {adj} | {dis} |")
    L.append("")
    L.append("`adj?` ⚑ = la traza tiene ≥1 afirmación CENTRAL no_soportada por el "
             "referente → requiere adjudicación humana contra los PDFs.")
    L.append("`ex-emb` = fue ejemplo embebido en v1.2; en v2.0 no hay few-shot, se "
             "marca solo por transparencia.")
    L.append("")

    L.append("## Criterio de éxito y regresiones")
    L.append("")
    L.append("Targets que debían flipear a coincidir con el humano:")
    for qid, rk, dim, exp, got, ok in targets_status:
        L.append(f"- {'✅' if ok else '❌'} {qid}/{rk}/{dim}: obtenido `{got}` "
                 f"(esperado `{exp}`)")
    L.append("")
    if regressions:
        L.append("**⚠ Regresiones** (celdas que coincidían en v1.2 y ahora no):")
        for q, rk, dim, jv, hv in regressions:
            L.append(f"- {q}/{rk}/{dim}: J:{jv} vs H:{hv}")
    else:
        L.append("**Sin regresiones**: todas las celdas que coincidían en v1.2 siguen "
                 "coincidiendo.")
    L.append("")

    # transparencia: descomposición + verificación por traza
    L.append("## Trazabilidad (descomposición y verificación por traza)")
    L.append("")
    for r in rows:
        v = r["verdict"]
        L.append(f"**{r['qid']} / {r['run']}** — corr={v.get('correctitud')}, "
                 f"compl={v.get('completitud')}, abst={v.get('abstencion')}, "
                 f"espec={v.get('especulacion_en_prosa')}")
        ns = v.get("afirmaciones_no_soportadas") or {}
        L.append(f"- no_soportadas: centrales={ns.get('n_centrales', 0)}, "
                 f"secundarias={ns.get('n_secundarias', 0)} | "
                 f"requiere_adjudicacion_humana={v.get('requiere_adjudicacion_humana')}")
        if ns.get("centrales"):
            L.append(f"  · centrales no_soportadas: {ns['centrales']}")
        adj_res = ADJUDICADAS.get((r["qid"], r["run"]))
        if adj_res:
            L.append(f"  · **adjudicación humana: {adj_res}**")
        s2 = r["step2"] or {}
        for ver in (s2.get("verificaciones") or []):
            c = "central" if ver.get("central") else "secundaria"
            L.append(f"- [{c}/{ver.get('verdict')}] {ver.get('enunciado')}")
        for cob in (s2.get("cobertura_patas") or []):
            L.append(f"- (pata/{cob.get('cobertura')}) {cob.get('pata')}")
        s1 = r["step1"] or {}
        if s1.get("reportes_de_alcance"):
            L.append(f"- reportes_de_alcance: {s1['reportes_de_alcance']}")
        just = v.get("justificacion") or {}
        for k, txt in just.items():
            if txt:
                L.append(f"- *{k}*: {txt}")
        if r["human"].get("_nota"):
            L.append(f"- (nota humana: {r['human']['_nota']})")
        L.append("")
    REPORT_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    run_calibration()
