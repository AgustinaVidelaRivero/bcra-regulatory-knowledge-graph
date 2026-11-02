#!/usr/bin/env python3
"""lanzador_falso_ventana.py — Un lanzador de una sesión falso, para el selftest de la ventana de B6.3 (etapa b1): la interfaz de
agentes/lanzar_agente.py (la que usa el lanzador del lote), sin ningún CLI, ningún servidor y ningún modelo. Escribe en <out>/ lo que
el lote y el runner leen de una sesión (el comando, el stream con su system/init y su result, y la meta) con la forma que pide el plan
de la marca [[ventana:<plan>]] de la pregunta, según el intento (el sufijo -i<k> del id):
  ok           completa (R3), con una respuesta de juguete;
  infra1       en el intento 1, la forma real de un 429 (formas_reales_b63.json); desde el 2, completa;
  infra3       la forma real de un 429 en los tres intentos;
  desconocida  un result con is_error y un subtype que no es ninguna forma conocida;
  corte        un result de corte por --max-turns.
Uso (lo arma el lanzador del lote): lanzador_falso_ventana.py --brazo X --id Y --pregunta "..." --out <dir> --modo real --sesiones <raíz>
"""
from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FORMAS = AQUI.parent / "formas_reales_b63.json"
MARCA = re.compile(r"\[\[ventana:([a-z0-9_]+)\]\]")


def forma_429() -> dict:
    f = next(x for x in json.loads(FORMAS.read_text(encoding="utf-8"))["formas"] if x["caso"] == "http_429")
    return f


def main() -> int:
    ap = argparse.ArgumentParser()
    for x in ("--brazo", "--id", "--pregunta", "--modo", "--via"):
        ap.add_argument(x, default="api" if x == "--via" else None)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sesiones", type=Path, required=True)
    ap.add_argument("--timeout-s", type=float, default=1800.0)
    a = ap.parse_args()
    m = re.search(r"-i(\d+)$", a.id)
    intento = int(m.group(1)) if m else 1
    plan = (MARCA.search(a.pregunta or "") or [None, "ok"])[1]
    sid = str(uuid.uuid4())
    cfg = (a.sesiones / "config" / sid).resolve()
    cfg.mkdir(parents=True)
    a.out.mkdir(parents=True, exist_ok=True)
    comando = {"argv": ["claude", "--bare", "-p", "<prompt>", "--max-turns", "32", "--max-budget-usd", "1.8", "--session-id", sid],
               "session_id": sid, "env_declarado": {"CLAUDE_CONFIG_DIR": str(cfg), "entorno_de_la_sesion": {"PATH": "x", "HOME": "x"}}}
    (a.out / f"comando_{a.id}.json").write_text(json.dumps(comando) + "\n", encoding="utf-8")
    ev = [{"type": "system", "subtype": "init", "claude_code_version": "2.1.241", "session_id": sid}]
    completa, respuesta = False, None
    if plan == "ok" or (plan == "infra1" and intento > 1):
        completa, respuesta = True, f"Respuesta de juguete de la ventana ({a.id})."
        ev.append({"type": "result", "subtype": "success", "is_error": False, "result": "{}", "session_id": sid,
                   "modelUsage": {"claude-sonnet-5": {"inputTokens": 10, "outputTokens": 10, "cacheReadInputTokens": 0,
                                                      "cacheCreationInputTokens": 0}}})
    elif plan in ("infra1", "infra3"):
        f = forma_429()
        ev += [{"type": "system", "subtype": "api_retry", "error_status": int(s) if s.isdigit() else None, "session_id": sid}
               for s in f["api_retry_error_status"]]
        if f["hay_result"]:
            ev.append({"type": "result", "subtype": f["subtype"], "is_error": f["is_error"], "session_id": sid})
    elif plan == "desconocida":
        ev.append({"type": "result", "subtype": "error_de_prueba_desconocido", "is_error": True, "session_id": sid})
    elif plan == "corte":
        ev.append({"type": "result", "subtype": "error_max_turns", "is_error": True, "session_id": sid,
                   "modelUsage": {"claude-sonnet-5": {"inputTokens": 10, "outputTokens": 10, "cacheReadInputTokens": 0,
                                                      "cacheCreationInputTokens": 0}}})
    (a.out / f"stream_{a.id}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in ev), encoding="utf-8")
    uso = next((x.get("modelUsage") for x in ev if x["type"] == "result" and x.get("modelUsage")), None)
    meta = {"modelos_R8": {"uso_por_modelo": uso}, "tokens_R9": {"costo_recomputado": {"total_usd": 0.0001 if uso else 0.0},
                                                                 "total_cost_usd_cli_solo_para_contraste": None},
            "completitud_R3": {"completa": completa, "motivos_incompleta": [] if completa else ["plan de la ventana"]},
            "mapa_R7": [], "log_r1": {"existe": True, "n_llamadas": 0}, "corte_R5": {"tope_tool_calls_prompt": 30},
            "final_json_R4": {"respuesta": respuesta, "citas": [], "respondible": True} if completa else None,
            "control_disco": {"FRENA": False}, "valor_remoto_por_tool": {"archivo": "no existe"}, "duracion_s": 0.1}
    (a.out / f"meta_{a.id}.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
