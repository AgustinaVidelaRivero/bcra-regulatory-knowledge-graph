#!/usr/bin/env python3
"""adaptador_banco.py — Adaptador de trazas del BANCO (transporte MCP) al formato
del repo (U-A2.0-banco, entregable 7). Módulo NUEVO que IMPORTA el adaptador del
gate (`gate/code/adaptador_cc.py`, sellado) y no lo edita.

Fuente de verdad y índice (laudo R1):
  · el LOG R1 del servidor MCP (`log_r1_<id>.jsonl`) aporta la ENTRADA y la
    SALIDA ÍNTEGRAS de cada llamada (`output_str`, la cadena exacta que viajó
    al cliente) — es la fuente de verdad del contenido;
  · la sesión de Claude Code (`stream_<id>.jsonl`, salida stream-json; o el
    jsonl de sesión) aporta el ORDEN, los `tool_use_id`, qué llamadas vio el
    modelo y el JSON final — es el índice.

Reconciliación (R7): la k-ésima tool call MCP de la sesión ↔ la k-ésima
`llamada` del log del proceso de ESA sesión. Se verifica tool e input
(igualdad exacta) y, cuando la sesión trae el texto del tool_result sin
truncar, `sha256(texto) == output_sha256` del log. Si el log no tiene la
llamada, o tool/input no coinciden, el step se marca `rechazado` con motivo y
el payload deja de ser atribuible: ningún step se descarta en silencio
(principio del gate: `alcanzabilidad` se afirma por ausencia).

Marca de completitud (R3): sin `result` exitoso, o con `tool_use` sin
`tool_result` (corte de sesión), o con log sin `fin`, el payload lleva
`atribuible: false` y se excluye de la métrica; nunca se atribuye.

Payload producido (misma forma que consume `atribucion_fallas.atribuir_payload`,
verificada en el gate):
    {"meta": {...}, "trace": {"question", "steps": [{n, tool, input, output_truncado,
     output_chars}], "final_json", "tool_calls_used", "hit_tool_limit"},
     "steps_full": [{n, tool, input, output, output_chars}], "gate": {...}, "banco": {...}}

Uso:
  adaptador_banco.py --dir <dir con stream_<id>.jsonl + log_r1_<id>.jsonl> --id <id> --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
GATE_CODE = BANCO_DIR / "gate" / "code"
for _p in (str(BANCO_DIR), str(GATE_CODE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Adaptador del gate: IMPORTADO (sellado). Se reusan el truncado del harness,
# el lector de jsonl, el enmascarado de rutas y las constantes de tools.
from adaptador_cc import TOOLS_VALIDAS, _truncar, enmascarar, leer_sesion  # noqa: E402
from comun_banco import rel_repo, sha256_bytes  # noqa: E402

VERSION = "1.0"


def _texto_tool_result(bloque: dict) -> str | None:
    c = bloque.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return None


def leer_stream(path: Path) -> dict:
    """Índice de sesión desde stream-json (o jsonl de sesión: misma forma de mensajes)."""
    init, result, usos, resultados, orden = None, None, [], {}, 0
    for L in leer_sesion(path):
        d = L["json"]
        if d is None:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            init = d
        elif d.get("type") == "result":
            result = d
        elif d.get("type") in ("assistant", "user"):
            for c in (d.get("message") or {}).get("content", []) or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use":
                    orden += 1
                    usos.append({"orden": orden, "tool_use_id": c.get("id"), "name": c.get("name"),
                                 "input": c.get("input") or {}, "linea": L["nro"], "uuid": d.get("uuid"),
                                 "timestamp": d.get("timestamp")})
                elif c.get("type") == "tool_result":
                    resultados[c.get("tool_use_id")] = {"texto": _texto_tool_result(c), "linea": L["nro"],
                                                        "is_error": c.get("is_error")}
    return {"init": init, "result": result, "usos": usos, "resultados": resultados}


def leer_log(path: Path) -> dict:
    lineas = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {"inicio": next((l for l in lineas if l["evento"] == "inicio"), None),
            "fin": next((l for l in lineas if l["evento"] == "fin"), None),
            "llamadas": [l for l in lineas if l["evento"] == "llamada"],
            "sha256": sha256_bytes(path.read_bytes())}


def final_json_de(result: dict | None) -> dict | None:
    if not result:
        return None
    t = result.get("result") or ""
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        return None
    try:
        d = json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None
    return d if all(k in d for k in ("respuesta", "citas", "respondible")) else None


def adaptar(stream_path: Path, log_path: Path, meta_extra: dict | None = None,
            servidor: str | None = None) -> dict:
    ses = leer_stream(stream_path)
    log = leer_log(log_path)
    srv = servidor or (log["inicio"] or {}).get("servidor") or "mcp_kg"
    prefijo = "mcp__" + {"mcp_kg": "kg", "mcp_vector": "vector"}.get(srv, srv) + "__"
    usos_mcp = [u for u in ses["usos"] if str(u["name"]).startswith("mcp__")]
    ajenos = [u for u in ses["usos"] if not str(u["name"]).startswith("mcp__")]

    steps, full, mapa, rechazos, incidencias = [], [], [], [], []
    corte = False
    n = 0
    for k, u in enumerate(usos_mcp):
        tool = str(u["name"])[len(prefijo):] if str(u["name"]).startswith(prefijo) else str(u["name"]).rsplit("__", 1)[-1]
        r = ses["resultados"].get(u["tool_use_id"])
        if r is None:
            corte = True
            incidencias.append({"tool_use_id": u["tool_use_id"], "tool": tool, "input": u["input"],
                                "motivo": "tool_use sin tool_result (corte de sesión)"})
            continue
        n += 1
        ll = log["llamadas"][k] if k < len(log["llamadas"]) else None
        entrada = {"n": n, "tool_use_id": u["tool_use_id"], "linea_tool_use": u["linea"],
                   "linea_tool_result": r["linea"], "uuid_asistente": u.get("uuid"),
                   "timestamp": u.get("timestamp"), "transporte": "mcp",
                   "call_id_log": ll["call_id"] if ll else None, "n_log": ll["n"] if ll else None}
        motivo = None
        if ll is None:
            motivo = "sin llamada correspondiente en el log R1"
        elif ll["tool"] != tool or ll["input"] != u["input"]:
            motivo = f"log R1 no coincide: log=({ll['tool']}, {json.dumps(ll['input'], ensure_ascii=False)}) sesión=({tool}, {json.dumps(u['input'], ensure_ascii=False)})"
        elif ll["output_str"] is None:
            motivo = f"el servidor registró error: {ll['error']}"
        elif tool not in TOOLS_VALIDAS and srv == "mcp_kg":
            motivo = f"tool fuera del contrato v1: {tool}"
        if motivo:
            rechazos.append(entrada | {"motivo_rechazo": motivo})
            steps.append({"n": n, "tool": tool, "input": u["input"], "output_truncado": None, "output_chars": None})
            mapa.append(entrada | {"ok": False})
            continue
        s = ll["output_str"]                       # ÍNTEGRO, del servidor
        texto_ses = r["texto"]
        igual = (texto_ses == s) if texto_ses is not None else None
        truncado_por_transporte = (texto_ses is not None and texto_ses != s)
        steps.append({"n": n, "tool": tool, "input": u["input"],
                      "output_truncado": _truncar(s), "output_chars": len(s)})
        full.append({"n": n, "tool": tool, "input": u["input"], "output": json.loads(s), "output_chars": len(s)})
        mapa.append(entrada | {"ok": True, "output_sha256_log": ll["output_sha256"],
                               "sesion_igual_al_log": igual,
                               "sesion_truncada_por_transporte": truncado_por_transporte,
                               "chars_sesion": None if texto_ses is None else len(texto_ses),
                               "chars_log": len(s)})
        incidencias.append({"n": n, "fuente_output": "log_r1", "igual_a_la_sesion": igual, "chars": len(s)})

    fj = final_json_de(ses["result"])
    res = ses["result"] or {}
    completa = bool(res.get("subtype") == "success" and not res.get("is_error") and fj is not None
                    and log["fin"] is not None and len(log["llamadas"]) == len(usos_mcp) and not corte)
    motivos = []
    if res.get("subtype") != "success" or res.get("is_error"): motivos.append(f"result.subtype={res.get('subtype')}")
    if fj is None: motivos.append("sin JSON final del contrato R4")
    if log["fin"] is None: motivos.append("log R1 sin línea fin")
    if len(log["llamadas"]) != len(usos_mcp): motivos.append(f"log {len(log['llamadas'])} llamadas vs sesión {len(usos_mcp)} tool_use MCP")
    if corte: motivos.append("corte de sesión")
    atribuible = completa and not rechazos
    fuente = (log["inicio"] or {}).get("fuente") or {}
    payload = {
        "meta": {
            "unidad": "U-A2.0-banco", "origen": "claude_code_session+mcp_log_r1", "transporte": "mcp",
            "adaptador": rel_repo(Path(__file__)), "adaptador_version": VERSION,
            "adaptador_gate_importado": rel_repo(GATE_CODE / "adaptador_cc.py"),
            "servidor": srv, "config_sha256_servidor": (log["inicio"] or {}).get("config_sha256"),
            "grafo": fuente.get("kg_path"), "grafo_sha256": fuente.get("kg_sha256") or fuente.get("sha256_matriz"),
            "stream": rel_repo(stream_path), "log_r1": rel_repo(log_path), "log_r1_sha256": log["sha256"],
            "session_id": (ses["init"] or {}).get("session_id") or res.get("session_id"),
            "contrato_tools": "v1",
            "generado": datetime.now().isoformat(timespec="seconds"),
        } | (meta_extra or {}),
        "trace": {"question": (meta_extra or {}).get("pregunta"), "steps": steps, "final_json": fj,
                  "tool_calls_used": len(steps),
                  # R5: no existe hit_tool_limit del harness; se reporta el corte del banco aparte
                  "hit_tool_limit": False},
        "steps_full": full,
        "gate": {"corte_sesion": corte, "atribuible": atribuible, "n_steps_adaptados": len(steps),
                 "mapa_steps": mapa, "incidencias": incidencias, "rechazos": rechazos},
        "banco": {"completitud_R3": {"completa": completa, "motivos": motivos},
                  "n_tool_use_mcp": len(usos_mcp), "n_tool_use_ajenos": len(ajenos),
                  "ajenos": [{"name": a["name"], "tool_use_id": a["tool_use_id"]} for a in ajenos],
                  "n_llamadas_log": len(log["llamadas"]),
                  "corte_R5": {"num_turns": res.get("num_turns"), "subtype": res.get("subtype")},
                  "steps_con_sesion_truncada": sum(1 for m in mapa if m.get("sesion_truncada_por_transporte"))},
    }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    p = adaptar(a.dir / f"stream_{a.id}.jsonl", a.dir / f"log_r1_{a.id}.jsonl", {"caso_id": a.id})
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"{a.id}.json").write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{a.id}: {p['gate']['n_steps_adaptados']} steps | corte={p['gate']['corte_sesion']} | "
          f"atribuible={p['gate']['atribuible']} | rechazos={len(p['gate']['rechazos'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
