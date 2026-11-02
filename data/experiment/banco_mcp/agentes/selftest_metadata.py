#!/usr/bin/env python3
"""selftest_metadata.py — Traza de ejemplo que CUMPLE el contrato de metadata,
producida SIN modelo (U-A2.0-banco, entregable 5; costo USD 0).

Qué hace:
  1. Lanza el brazo KG en modo init (USD 0) para obtener un `system/init` real
     (tools, servidores, versión del CLI, permissionMode).
  2. Ejecuta llamadas REALES contra el servidor MCP del KG (cliente falso, misma
     expansión del JSON de MCP que usa Claude Code) — el log R1 es real.
  3. Arma un stream-json SINTÉTICO con la forma del de Claude Code (mensajes
     assistant con tool_use + usage, user con tool_result, result con
     modelUsage) usando esos outputs reales, y lo pasa por el MISMO parser y
     constructor de metadata del lanzador (`parsear_stream`, `armar_meta`).
  4. Verifica que `completitud_R3.completa == true`, que el mapa R7 coincide y
     que el costo recomputado sale de los precios sellados.
  5. Identidad por hash (entregable 6): dos lanzamientos en modo init con
     `--via api` y `--via bedrock` producen el mismo `sha_identidad_pipeline`.

El origen sintético queda marcado en `meta.origen = "selftest_sintetico"`:
NO es una traza del banco y no se atribuye.

Uso:
  BANCO_VENV_VECTOR=<venv> .venv/bin/python -B selftest_metadata.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
REPO_DIR = BANCO_DIR.parents[2]
for _p in (str(BANCO_DIR), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from cliente_falso import ClienteFalso                                  # noqa: E402
from comun_banco import rel_repo, sha256_file                            # noqa: E402
import lanzar_agente as LA                                               # noqa: E402

OUT = AQUI / "resultados" / "selftest"
PLAN = [("mcp__kg__buscar_nodos", {"consulta": "efectivo mínimo", "limite": 3}),
        ("mcp__kg__ver_nodo", {"id": "Obligacion_integracion_de_capital_minimo_e22e8b"}),
        ("mcp__kg__ver_vecinos", {"id": "Obligacion_integracion_de_capital_minimo_e22e8b", "direccion": "salientes"})]


def expandir(s, env):
    return re.sub(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}", lambda m: env.get(m.group(1), m.group(2) or ""), s)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = LA.cargar(LA.CONFIG_AGENTES)
    precios = LA.cargar(LA.PRECIOS)
    pregunta = "¿Qué obligaciones fija la normativa sobre la integración del capital mínimo?"

    # 1) init real (USD 0) por las dos vías -> identidad por hash
    shas = {}
    for via in ("api", "bedrock"):
        subprocess.run([sys.executable, "-B", str(LA.__file__), "--brazo", "kg", "--id", f"SELF-{via}",
                        "--pregunta", pregunta, "--out", str(OUT), "--modo", "init", "--via", via],
                       check=False, capture_output=True, text=True)
        shas[via] = json.loads((OUT / f"comando_SELF-{via}.json").read_text())["sha_identidad_pipeline"]
    identidad_ok = shas["api"] == shas["bedrock"]
    init = LA.parsear_stream((OUT / "stream_SELF-api.jsonl").read_text().splitlines())["init"]
    comando = json.loads((OUT / "comando_SELF-api.json").read_text())

    # 2) llamadas reales al servidor por el MISMO JSON de MCP
    env = dict(os.environ, BANCO_REPO=str(REPO_DIR))
    d = json.loads((BANCO_DIR / cfg["brazos"]["kg"]["mcp_config"]).read_text())["mcpServers"]["kg"]
    log_r1 = OUT / "log_r1_SELFTEST.jsonl"
    if log_r1.exists():
        log_r1.unlink()
    e = {k: expandir(v, dict(env, BANCO_LOG_R1=str(log_r1), BANCO_SESION_TAG="SELFTEST")) for k, v in d["env"].items()}
    cmd = [expandir(d["command"], env)] + [expandir(a, env) for a in d["args"]]
    salidas = []
    with ClienteFalso(cmd, env=e) as cli:
        for name, args in PLAN:
            salidas.append(cli.llamar(name.rsplit("__", 1)[-1], args))

    # 3) stream sintético con la forma de Claude Code
    sid = str(uuid.uuid4())
    init = dict(init, session_id=sid)
    lineas = [json.dumps(init, ensure_ascii=False)]
    modelo = cfg["modelo"]
    usos_tokens = []
    for k, ((name, args), out) in enumerate(zip(PLAN, salidas)):
        tuid = f"toolu_selftest_{k+1:02d}"
        usage = {"input_tokens": 40 + 30 * k, "output_tokens": 60, "cache_creation_input_tokens": 9000 if k == 0 else 0,
                 "cache_read_input_tokens": 0 if k == 0 else 9000 + 1500 * k}
        usos_tokens.append(usage)
        lineas.append(json.dumps({"type": "assistant", "uuid": str(uuid.uuid4()), "session_id": sid,
                                  "message": {"model": modelo, "role": "assistant", "stop_reason": "tool_use", "usage": usage,
                                              "content": [{"type": "tool_use", "id": tuid, "name": name, "input": args}]}}, ensure_ascii=False))
        lineas.append(json.dumps({"type": "user", "uuid": str(uuid.uuid4()), "session_id": sid,
                                  "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tuid,
                                                                            "content": [{"type": "text", "text": out}]}]}}, ensure_ascii=False))
    final = {"respuesta": "[selftest sintético: sin modelo] La integración del capital mínimo está regulada en el TO de capitales mínimos.",
             "citas": ["TO_capitales_minimos_actual.pdf | Punto 1.3. Integración."], "respondible": True}
    usage_f = {"input_tokens": 200, "output_tokens": 120, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 14000}
    usos_tokens.append(usage_f)
    lineas.append(json.dumps({"type": "assistant", "uuid": str(uuid.uuid4()), "session_id": sid,
                              "message": {"model": modelo, "role": "assistant", "stop_reason": "end_turn", "usage": usage_f,
                                          "content": [{"type": "text", "text": json.dumps(final, ensure_ascii=False)}]}}, ensure_ascii=False))
    mu = {modelo: {"inputTokens": sum(u["input_tokens"] for u in usos_tokens),
                   "outputTokens": sum(u["output_tokens"] for u in usos_tokens),
                   "cacheCreationInputTokens": sum(u["cache_creation_input_tokens"] for u in usos_tokens),
                   "cacheReadInputTokens": sum(u["cache_read_input_tokens"] for u in usos_tokens)},
          "claude-haiku-4-5-20251001": {"inputTokens": 507, "outputTokens": 13, "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0}}
    lineas.append(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 4, "session_id": sid,
                              "result": json.dumps(final, ensure_ascii=False), "total_cost_usd": 0.5, "modelUsage": mu,
                              "permission_denials": []}, ensure_ascii=False))
    stream_path = OUT / "stream_SELFTEST.jsonl"
    stream_path.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    # 4) metadata con el MISMO constructor del lanzador
    stream = LA.parsear_stream(lineas)
    log = LA.leer_log_r1(log_r1)
    ident = LA.archivos_identidad(cfg, "kg")
    meta = LA.armar_meta(cfg, "kg", ident, shas["api"], comando, stream, log, precios, "api", "selftest",
                         "SELFTEST", None, comando["claude_code_version"])
    meta["origen"] = "selftest_sintetico (stream construido sin modelo sobre llamadas MCP reales; NO es una traza del banco)"
    (OUT / "meta_SELFTEST.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    p = precios["modelos"]
    esperado = round(sum((mu[m]["inputTokens"] * p[m]["input"] + mu[m]["cacheCreationInputTokens"] * p[m]["cache_write_5m"]
                          + mu[m]["cacheReadInputTokens"] * p[m]["cache_read"] + mu[m]["outputTokens"] * p[m]["output"]) / 1e6
                         for m in mu), 6)
    res = {"generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "unidad": "U-A2.0-banco — selftest del contrato de metadata (entregable 5) e identidad por hash (6)",
           "identidad_por_hash": {"sha_via_api": shas["api"], "sha_via_bedrock": shas["bedrock"], "iguales": identidad_ok},
           "completitud_R3": meta["completitud_R3"],
           "mapa_R7_coincide": all(x["coincide_tool_input"] for x in meta["mapa_R7"]) and len(meta["mapa_R7"]) == len(PLAN),
           "inventario_R6_coincide": meta["inventario_tools_R6"]["coincide"],
           "modelos_R8": meta["modelos_R8"]["inventario_observado"],
           "costo_R9": {"recomputado": meta["tokens_R9"]["costo_recomputado"]["total_usd"], "esperado": esperado,
                        "cli_contraste": meta["tokens_R9"]["total_cost_usd_cli_solo_para_contraste"],
                        "ok": meta["tokens_R9"]["costo_recomputado"]["total_usd"] == esperado},
           "claves_contrato_presentes": sorted(meta.keys()),
           "meta": rel_repo(OUT / "meta_SELFTEST.json"), "stream": rel_repo(stream_path), "log_r1": rel_repo(log_r1)}
    res["PASS"] = bool(identidad_ok and meta["completitud_R3"]["completa"] and res["mapa_R7_coincide"]
                       and res["inventario_R6_coincide"] and res["costo_R9"]["ok"])
    (OUT / "selftest_metadata.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "claves_contrato_presentes"}, ensure_ascii=False, indent=1))
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
