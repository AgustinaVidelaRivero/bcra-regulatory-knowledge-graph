#!/usr/bin/env python3
"""adaptador_sesiones.py — Adaptador jsonl→traza del circuito de intake (Motor 2).

Convierte sesiones de la app de chat (app/sessions/**/*.jsonl) en trazas
diagnosticables por el verificador validado, SIN llamar a ningún LLM (USD 0)
y SIN tocar módulos sellados: el adaptador fabrica la ENTRADA que
`verifier_pilot.load_rep` / `verificador.build_falla_context` esperan; los
módulos congelados no se editan.

Diseño (laudo D1, modo sin-gold):
  · Solo se procesan respuestas con voto 👎 (`tipo: "feedback"`, `voto: "down"`).
    El laudo humano es el SÍNTOMA — acá no hay juez porque no hay respuesta
    esperada. El rep declara `sin_gold: "laudo_humano"` y porta el comentario
    del 👎 en `sintoma_humano`; el stub de juez lleva step1/step2 explícitamente
    VACÍOS (el builder congelado ya tolera ese caso con su fallback propio:
    "el juez no expuso afirmaciones desagregadas").
  · `raw_turns_agent` se RECONSTRUYE desde `tools_llamadas` (un turno por tool
    call, sin bloques thinking — la app corre el agente sin extended thinking):
    el JOIN duro raw↔steps de `_thinking_por_turno` exige esa consistencia.
  · Los resultados COMPLETOS de las tools (la app los guarda sin truncar) se
    preservan verbatim en `tools_llamadas_completas` y en `origen.json` — los
    módulos congelados recuperan nodos vistos desde cache/calls.db, donde las
    llamadas de la app NO están; el material queda disponible para el builder
    futuro sin depender de esa caché.

Salidas (únicas escrituras, bajo data/backlog/intake/):
  · trazas/<session>_<turno>/traza.json   — lista [rep] load_rep-compatible.
  · trazas/<session>_<turno>/origen.json  — líneas verbatim de turno + feedback.
  · cola_intake.jsonl                     — una línea por caso, estado
    `pendiente_de_triage`. NO escribe en backlog.jsonl (las altas al backlog
    son post-triage humano, otra unidad).

Guarda de material quemado: si la pregunta (normalizada) coincide con alguna de
EV1/CQ/CQN/CQN2, la línea se marca `territorio_quemado: true` con set e id del
match. No se descarta: el laudo de qué hacer es humano.

Idempotencia: clave `session+turno` — re-correr sobre el mismo jsonl no duplica
líneas de la cola (los casos ya presentes se saltean; una clave repetida con
origen DISTINTO se reporta como conflicto y no se escribe).

Uso, desde la raíz del repo:
    python3 scripts/adaptador_sesiones.py app/sessions/<archivo>.jsonl [...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INTAKE_DIR = REPO_ROOT / "data" / "backlog" / "intake"
TRAZAS_DIR = INTAKE_DIR / "trazas"
COLA_PATH = INTAKE_DIR / "cola_intake.jsonl"

# Espejo del truncado del harness/verificador (TRUNC=1200): los steps de una
# traza post-hoc llevan output_truncado en ese formato exacto.
TRUNC = 1200

# Sets de material QUEMADO (EV1/CQ/CQN/CQN2): no sirven como re-test ni
# objetivo. Se indexan todas las variantes de redacción disponibles.
SETS_QUEMADOS = {
    "EV1": [
        "data/experiment/evaluacion_escalon1/EV1_preguntas.json",
        "data/experiment/evaluacion_escalon1/EV1_runtime.json",
    ],
    "CQ": [
        "data/experiment/evaluacion/queries/eval_set_v1.json",
        "data/experiment/evaluacion/queries/eval_set_v2.json",
        "data/experiment/evaluacion/queries/eval_set_v2_nuevas.json",
    ],
    "CQN": [
        "data/experiment/evaluacion/queries/eval_set_cqn.json",
        "data/experiment/evaluacion/queries/eval_set_cqn_runtime.json",
    ],
    "CQN2": [
        "data/experiment/evaluacion/queries/eval_set_cqn2.json",
        "data/experiment/evaluacion/queries/eval_set_cqn2_runtime.json",
    ],
}
_CAMPOS_PREGUNTA = ("pregunta", "pregunta_original", "redaccion_ajustada")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def normalizar(s: str) -> str:
    """Normalización para el match de quemado: minúsculas, sin tildes, solo
    tokens alfanuméricos separados por un espacio (misma familia que el
    pre-ranking léxico del pilot del verificador)."""
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", s))


def _iter_items(data):
    """Itera los dicts-pregunta de un archivo de set, sea lista plana o
    {"preguntas": [...]} (los formatos observados en el repo)."""
    if isinstance(data, list):
        yield from (x for x in data if isinstance(x, dict))
    elif isinstance(data, dict):
        pregs = data.get("preguntas")
        if isinstance(pregs, list):
            yield from (x for x in pregs if isinstance(x, dict))


def indice_quemado() -> dict:
    """texto_normalizado -> (set, id). Un archivo listado pero ausente aborta
    ruidoso: una guarda de quemado incompleta es peor que ninguna."""
    idx = {}
    for nombre_set, rutas in SETS_QUEMADOS.items():
        for ruta in rutas:
            p = REPO_ROOT / ruta
            if not p.exists():
                raise RuntimeError(
                    f"Set quemado listado pero ausente: {ruta}. La guarda no "
                    "puede quedar incompleta en silencio; revisá SETS_QUEMADOS.")
            data = json.load(open(p, encoding="utf-8"))
            for item in _iter_items(data):
                for campo in _CAMPOS_PREGUNTA:
                    valor = item.get(campo)
                    if not isinstance(valor, str):
                        # p. ej. `redaccion_ajustada` es booleano en CQN: no es texto de pregunta
                        continue
                    norm = normalizar(valor)
                    if norm and norm not in idx:
                        idx[norm] = (nombre_set, item.get("id"))
    return idx


def _truncate(s: str, n: int = TRUNC) -> str:
    """Espejo exacto de _truncate del verificador (formato del output_truncado)."""
    return s if len(s) <= n else s[:n] + f"… [+{len(s)-n} chars]"


def construir_rep(turno: dict, feedback: dict, archivo_rel: str) -> dict:
    """Arma el rep load_rep-compatible desde la línea de turno + la de feedback."""
    tools = turno.get("tools_llamadas") or []
    steps, raw_turns = [], []
    for i, t in enumerate(tools, start=1):
        resultado_str = json.dumps(t.get("resultado"), ensure_ascii=False)
        steps.append({
            "n": i,
            "tool": t.get("tool"),
            "input": t.get("argumentos"),
            "output_truncado": _truncate(resultado_str),
        })
        # Un turno reconstruido por tool call, con UN bloque tool_use espejo del
        # step: satisface el JOIN verificado raw↔steps del builder congelado.
        # Sin bloques thinking: la app corre el agente sin extended thinking.
        raw_turns.append({
            "reconstruido": True,
            "fuente": "tools_llamadas del jsonl de la app (adaptador_sesiones)",
            "raw": {
                "content": [{
                    "type": "tool_use",
                    "id": f"toolu_app_{i:03d}",
                    "name": t.get("tool"),
                    "input": t.get("argumentos"),
                }],
            },
        })

    return {
        "origen": "app_feedback",
        "archivo_origen": archivo_rel,
        "session_id": turno.get("session_id"),
        "turno": turno.get("turno"),
        "usuario": turno.get("usuario"),
        "run": turno.get("run_id"),
        "backend": turno.get("backend"),
        "modelo": turno.get("modelo"),
        "categoria": "app_feedback",
        "sin_gold": "laudo_humano",
        "sintoma_humano": {
            "voto": feedback.get("voto"),
            "comentario": feedback.get("comentario"),
            "ts_feedback": feedback.get("ts"),
            "declaracion": (
                "Modo sin-gold: el sintoma lo pone el laudo humano (voto 👎 en "
                "la app). No hay juez porque no hay respuesta esperada; el "
                "diagnostico lo pone el verificador validado."),
        },
        "trace": {
            "question": turno.get("pregunta"),
            "final_json": turno.get("respuesta"),
            "steps": steps,
        },
        # Stub de juez EXPLÍCITAMENTE vacío (sin juez inventado): el builder
        # congelado renderiza sus fallbacks propios sobre estas listas vacías.
        "judge": {
            "stub": "sin_gold: laudo_humano — sin juez; listas vacías a propósito",
            "step1": {
                "patas_de_la_pregunta": [],
                "afirmaciones_verificables": [],
                "reportes_de_alcance": [],
            },
            "step2": {"verificaciones": []},
        },
        "raw_turns_agent": raw_turns,
        # Resultados COMPLETOS de las tools, verbatim de la app (sustituto del
        # recover_seen de calls.db, donde las llamadas de la app no están).
        "tools_llamadas_completas": tools,
    }


def parsear_sesion(path: Path):
    """Devuelve (turnos, downs): turnos[(session_id, turno)] = línea;
    downs[(session_id, turno)] = ÚLTIMA línea de feedback down (archivo
    append-only: la última línea es el estado final del voto)."""
    turnos, downs = {}, {}
    with path.open(encoding="utf-8") as f:
        for nro, cruda in enumerate(f, start=1):
            cruda = cruda.strip()
            if not cruda:
                continue
            try:
                d = json.loads(cruda)
            except json.JSONDecodeError:
                print(f"  [aviso] {path.name}:{nro}: línea no-JSON, salteada")
                continue
            clave = (d.get("session_id"), d.get("turno"))
            if d.get("tipo") == "turno":
                turnos[clave] = d
            elif d.get("tipo") == "feedback" and d.get("voto") == "down":
                downs[clave] = d
    return turnos, downs


def casos_existentes() -> dict:
    """caso_id -> archivo_origen de las líneas ya presentes en la cola."""
    existentes = {}
    if COLA_PATH.exists():
        for cruda in COLA_PATH.open(encoding="utf-8"):
            cruda = cruda.strip()
            if not cruda:
                continue
            d = json.loads(cruda)
            existentes[d.get("caso_id")] = d.get("archivo_origen")
    return existentes


def procesar(archivos: list[Path]) -> dict:
    idx_quemado = indice_quemado()
    existentes = casos_existentes()
    resumen = {"nuevos": 0, "salteados": 0, "conflictos": 0,
               "sin_turno": 0, "quemados": 0}

    TRAZAS_DIR.mkdir(parents=True, exist_ok=True)
    with COLA_PATH.open("a", encoding="utf-8") as cola:
        for path in archivos:
            archivo_rel = str(path.resolve().relative_to(REPO_ROOT))
            turnos, downs = parsear_sesion(path)
            print(f"== {archivo_rel}: {len(turnos)} turnos, {len(downs)} votos 👎")
            for clave in sorted(downs, key=lambda c: (str(c[0]), c[1] or 0)):
                session_id, nro_turno = clave
                caso_id = f"{session_id}_{nro_turno}"
                feedback = downs[clave]
                turno = turnos.get(clave)
                if turno is None:
                    print(f"  [aviso] 👎 sin línea de turno para {caso_id}: salteado")
                    resumen["sin_turno"] += 1
                    continue
                if caso_id in existentes:
                    if existentes[caso_id] != archivo_rel:
                        print(f"  [CONFLICTO] {caso_id} ya está en la cola con "
                              f"origen {existentes[caso_id]!r} ≠ {archivo_rel!r}: "
                              "NO se escribe; resolver a mano.")
                        resumen["conflictos"] += 1
                    else:
                        print(f"  [idempotencia] {caso_id} ya en la cola: salteado")
                        resumen["salteados"] += 1
                    continue

                rep = construir_rep(turno, feedback, archivo_rel)
                caso_dir = TRAZAS_DIR / caso_id
                caso_dir.mkdir(parents=True, exist_ok=True)
                with (caso_dir / "traza.json").open("w", encoding="utf-8") as f:
                    json.dump([rep], f, ensure_ascii=False, indent=1)
                with (caso_dir / "origen.json").open("w", encoding="utf-8") as f:
                    json.dump({"archivo": archivo_rel, "turno": turno,
                               "feedback": feedback}, f, ensure_ascii=False, indent=1)

                match = idx_quemado.get(normalizar(turno.get("pregunta") or ""))
                linea = {
                    "caso_id": caso_id,
                    "session": session_id,
                    "turno": nro_turno,
                    "usuario": turno.get("usuario"),
                    "pregunta": turno.get("pregunta"),
                    "grafo": turno.get("run_id"),
                    "ts": turno.get("ts"),
                    "ts_feedback": feedback.get("ts"),
                    "voto": feedback.get("voto"),
                    "comentario": feedback.get("comentario"),
                    "traza": str((caso_dir / "traza.json").relative_to(REPO_ROOT)),
                    "archivo_origen": archivo_rel,
                    "estado": "pendiente_de_triage",
                    "territorio_quemado": bool(match),
                    "quemado_match": ({"set": match[0], "id": match[1]}
                                      if match else None),
                    "ts_intake": _now_iso(),
                }
                cola.write(json.dumps(linea, ensure_ascii=False) + "\n")
                cola.flush()
                existentes[caso_id] = archivo_rel
                resumen["nuevos"] += 1
                if match:
                    resumen["quemados"] += 1
                    print(f"  [QUEMADO] {caso_id}: match {match[0]}/{match[1]} "
                          "(marcado, no descartado — laudo humano)")
                print(f"  [alta] {caso_id} → {linea['traza']}")
    return resumen


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Adaptador jsonl→traza (Motor 2): sesiones con 👎 → cola de intake.")
    ap.add_argument("jsonl", nargs="+", type=Path,
                    help="uno o más jsonl de sesiones de la app")
    args = ap.parse_args()
    for p in args.jsonl:
        if not p.exists():
            print(f"ERROR: no existe {p}", file=sys.stderr)
            return 1
    resumen = procesar(args.jsonl)
    print(f"\nResumen: {json.dumps(resumen, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
