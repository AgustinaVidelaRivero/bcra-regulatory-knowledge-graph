#!/usr/bin/env python3
"""claude_falso_b63.py (v2/b2, etapa b2) — El de la b1 bis (b63/v2/b1bis/seco/claude_falso_b63.py) con los planes de la b2
(planes_b63_seco_b2.json, de esta carpeta: `juez_comillas`, cuya respuesta trae la marca [[juez:comillas]] de la salida del juez que no se
lee). Lo de la b1 bis: El CLI falso de la corrida en seco de B6.3: el de b63/v2/seco/ (etapa b1), con las
formas reales del error de b63/v2/b1bis/formas_reales_b63.json (las de la b1, con la clase propia de la clave inválida), y con lo de la
b1 bis:
  · el `result` de una forma real trae su api_error_status y su terminal_reason, si se midieron (la clave inválida: 401 y api_error);
  · la clave de relleno inválida (CLAVE_INVALIDA_DE_RELLENO en ANTHROPIC_API_KEY, la que pone la prueba) da, en toda sesión con la
    marca [[b63:<plan>]], la forma real de la clave inválida, sea cual sea su plan; con otra clave, su plan: así una prueba frena el
    lote con la clave inválida y lo retoma con la buena;
  · un plan con `citas` las pone en el JSON final; uno con `result_fijo` ({subtype, is_error}) termina con ese result, sin modelUsage
    (una forma que no es ninguna de las medidas);
  · los planes de b63/v2/b1bis/seco/planes_b63_seco_b1bis.json, además de los de la etapa a y los de la b1.
Lo demás, tal cual. Ningún modelo y ninguna petición a la API: costo USD 0.

  · `--version` y toda pregunta sin la marca [[b63:<plan>]]: el CLI falso del banco, tal cual (claude_falso.main), con sus planes
    [[seco:<plan>]] (entre ellos, el que cambia la versión de su system/init);
  · con la marca [[b63:<plan>]] (planes_b63_seco.json), el mismo camino que el del banco (el servidor MCP de la sesión desde su JSON,
    por el cliente falso; system/init; un tool_use y su tool_result por llamada; la transcripción), y además:
      - `corte`: termina con un `result` de corte (error_max_turns o error_max_budget_usd, con is_error), como el CLI real;
      - `falla_infra_hasta` n: en los intentos 1 a n (el sufijo -i<k> del id de la sesión, que le llega en BANCO_SESION_TAG) termina
        con eventos system/api_retry y, según `forma_infra`, sin `result` («sin_result») o con un `result` con is_error y el subtype
        error_during_execution («is_error»); la forma del CLI real ante un error de la API, NO VERIFICADA;
      - `respuesta`, por tipo de servidor: el texto de la respuesta final (con una marca del brazo, o la marca [[juez:malformada]]
        para el transporte simulado del juez);
      - `aplica_a`: los brazos a los que se aplica el plan; los demás corren el plan `normal`;
      - `marca_disco`: el primer tool_result de la transcripción trae la marca de un resultado guardado en disco (la que busca
        `a2_1/correr_a2_1.py`, `control_disco`);
      - `claude_json`: el `.claude.json` de juguete que escribe en la carpeta de configuración de la sesión (para la lectura acotada
        de `tengu_velvet_ibis`).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                       # b63/v2/b2/seco
BANCO_DIR = AQUI.parents[3]
CF_PATH = BANCO_DIR / "paralelo" / "cli_falso" / "claude_falso.py"
_spec = importlib.util.spec_from_file_location("claude_falso", CF_PATH)
CF = importlib.util.module_from_spec(_spec)
sys.modules["claude_falso"] = CF
_spec.loader.exec_module(CF)                       # el CLI falso del banco: solo import

PLANES = BANCO_DIR / "b63" / "seco" / "planes_b63_seco.json"   # los de la etapa a
PLANES_V2 = BANCO_DIR / "b63" / "v2" / "seco" / "planes_b63_seco_v2.json"   # los de las formas reales (b1)
PLANES_B1BIS = AQUI / "planes_b63_seco_b1bis.json"           # los de la b1 bis (la copia de esta carpeta, igual)
PLANES_B2 = AQUI / "planes_b63_seco_b2.json"                 # los de la b2
FORMAS = AQUI.parent / "formas_reales_b63.json"               # las de la b1 bis
CLAVE_INVALIDA_DE_RELLENO = "clave-de-relleno-invalida-b1bis"  # no es ninguna clave: la pone la prueba para la forma del 401
MARCA = re.compile(r"\[\[b63:([A-Za-z0-9_-]+)\]\]")
TAG = re.compile(r"^B63-(?P<q>.+)-r(?P<r>\d+)-(?P<brazo>.+?)(?:-i(?P<i>\d+))?$")


def main(argv: list[str]) -> int:
    a = CF.leer_args(argv)
    if "--version" in a["flags"]:
        return CF.main(argv)
    prompt = a["-p"]
    m = MARCA.search(prompt)
    if not m:
        return CF.main(argv)
    planes = (json.loads(PLANES.read_text(encoding="utf-8"))["planes"] | json.loads(PLANES_V2.read_text(encoding="utf-8"))["planes"]
              | json.loads(PLANES_B1BIS.read_text(encoding="utf-8"))["planes"] | json.loads(PLANES_B2.read_text(encoding="utf-8"))["planes"])
    sid, model = a["--session-id"], a["--model"]
    t = TAG.match(os.environ.get("BANCO_SESION_TAG", ""))
    brazo, intento = (t.group("brazo"), int(t.group("i") or 1)) if t else ("", 1)
    plan = planes[m.group(1)]
    if plan.get("aplica_a") is not None and brazo not in plan["aplica_a"]:
        plan = planes["normal"]
    if os.environ.get("ANTHROPIC_API_KEY") == CLAVE_INVALIDA_DE_RELLENO:
        plan = planes["clave_invalida"]
    (srv, s), = json.loads(Path(a["--mcp-config"]).read_text(encoding="utf-8"))["mcpServers"].items()
    sub = plan.get("por_servidor", {}).get(srv) or planes["normal"]["por_servidor"][srv]
    env = dict(os.environ)
    cmd = [CF.expandir(s["command"], env)] + [CF.expandir(x, env) for x in s.get("args", [])]
    e = {k: CF.expandir(v, env) for k, v in (s.get("env") or {}).items()}
    transcripcion, cwd = [], Path.cwd()

    def emitir(ev: dict, a_la_transcripcion: bool = True) -> None:
        print(json.dumps(ev, ensure_ascii=False), flush=True)
        if a_la_transcripcion:
            transcripcion.append(ev | {"sessionId": sid, "timestamp": CF.ahora()})

    def guardar_transcripcion() -> None:
        if "--no-session-persistence" in a["flags"]:
            return
        slug = str(cwd).replace("/", "-").replace(" ", "-").replace("_", "-")
        d = Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / slug
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"{sid}.jsonl", "w", encoding="utf-8") as f:
            for ev in transcripcion:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    if plan.get("claude_json") is not None:
        (Path(os.environ["CLAUDE_CONFIG_DIR"]) / ".claude.json").write_text(json.dumps(plan["claude_json"]), encoding="utf-8")
    transcripcion.append({"type": "user", "sessionId": sid, "timestamp": CF.ahora(), "version": CF.VERSION,
                          "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}})
    cli = CF.ClienteFalso(cmd, env=e, timeout_s=600)
    cli.__enter__()
    nombres = sorted(f"mcp__{srv}__{x['name']}" for x in cli.listar_tools())
    emitir({"type": "system", "subtype": "init", "cwd": str(cwd), "session_id": sid, "tools": nombres,
            "mcp_servers": [{"name": srv, "status": "connected"}], "model": model,
            "permissionMode": a.get("--permission-mode"), "apiKeySource": "ANTHROPIC_API_KEY",
            "claude_code_version": plan.get("version_init", CF.VERSION_SELLADA)}, a_la_transcripcion=False)
    if plan.get("forma_real") and intento <= plan.get("hasta_el_intento", 99):
        # la forma real: el CLI falla en su primer pedido a la API, sin ninguna tool (num_turns 1)
        cli.__exit__(None, None, None)
        f = next(x for x in json.loads(FORMAS.read_text(encoding="utf-8"))["formas"] if x["caso"] == plan["forma_real"])
        status = f["api_retry_error_status"][0] if f["api_retry_error_status"] else None
        for k in range(1, f["api_retry"] + 1):
            emitir({"type": "system", "subtype": "api_retry", "attempt": k,
                    "error_status": int(status) if status and status.isdigit() else None,
                    "error": (f.get("api_retry_error") or [None])[0], "session_id": sid}, a_la_transcripcion=False)
        if f["hay_result"]:
            r = {"type": "result", "subtype": f["subtype"], "is_error": f["is_error"], "num_turns": 1, "session_id": sid,
                 "total_cost_usd": 0, "permission_denials": []}
            if isinstance(f.get("api_error_status"), int):
                r["api_error_status"] = f["api_error_status"]
            if f.get("terminal_reason") and not str(f["terminal_reason"]).startswith("no medido"):
                r["terminal_reason"] = f["terminal_reason"]
            emitir(r, a_la_transcripcion=False)
        guardar_transcripcion()
        return f["rc"]
    if plan.get("result_fijo"):
        cli.__exit__(None, None, None)
        emitir({"type": "result", "subtype": plan["result_fijo"]["subtype"], "is_error": plan["result_fijo"]["is_error"], "num_turns": 1,
                "session_id": sid, "permission_denials": []}, a_la_transcripcion=False)
        guardar_transcripcion()
        return 1
    for k, ll in enumerate(sub["llamadas"], 1):
        tid = f"toolu_falso_{sid[:8]}_{k}"
        emitir({"type": "assistant", "uuid": f"{sid[:8]}-a{k}",
                "message": {"id": f"msg_falso_{sid[:8]}_{k}", "model": model, "role": "assistant", "stop_reason": "tool_use",
                            "content": [{"type": "tool_use", "id": tid, "name": f"mcp__{srv}__{ll['tool']}", "input": ll["input"]}],
                            "usage": {"input_tokens": 10, "output_tokens": 50}}})
        r = cli.llamar_crudo(ll["tool"], ll["input"])
        texto = "".join(getattr(c, "text", "") for c in r.content)
        if k == 1 and plan.get("marca_disco"):
            texto = "<persisted-output> resultado de juguete guardado en disco"
        emitir({"type": "user", "uuid": f"{sid[:8]}-u{k}",
                "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "is_error": bool(r.isError),
                                                         "content": [{"type": "text", "text": texto}]}]}})
    cli.__exit__(None, None, None)                       # el servidor escribe su línea `fin`
    n = len(sub["llamadas"])
    u = plan.get("uso") or {"inputTokens": 1000, "outputTokens": 300, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}
    costo = (u["inputTokens"] * CF.PRECIO["input"] + u["cacheCreationInputTokens"] * CF.PRECIO["cache_write_5m"]
             + u["cacheReadInputTokens"] * CF.PRECIO["cache_read"] + u["outputTokens"] * CF.PRECIO["output"]) / 1e6
    if plan.get("falla_infra_hasta") and intento <= plan["falla_infra_hasta"]:
        for k in (1, 2):
            emitir({"type": "system", "subtype": "api_retry", "attempt": k, "error_status": 529, "error": "overloaded_error",
                    "session_id": sid}, a_la_transcripcion=False)
        guardar_transcripcion()
        if plan.get("forma_infra") == "is_error":
            emitir({"type": "result", "subtype": "error_during_execution", "is_error": True, "num_turns": n,
                    "session_id": sid, "permission_denials": []}, a_la_transcripcion=False)
            return 1
        sys.stderr.write("CLI falso de B6.3: la sesión termina sin result, por su plan (falla de infraestructura)\n")
        return 1
    if plan.get("corte"):
        emitir({"type": "result", "subtype": plan["corte"], "is_error": True, "num_turns": n + 1, "session_id": sid,
                "total_cost_usd": round(costo, 6), "permission_denials": [], "errors": [],
                "modelUsage": {model: u | {"costUSD": round(costo, 6)}}}, a_la_transcripcion=False)
        guardar_transcripcion()
        return 1
    texto = (plan.get("respuesta") or {}).get(srv) or planes["normal"]["respuesta"][srv]
    final = json.dumps({"respuesta": f"{texto} (sesión de juguete {sid[:8]})",
                        "citas": plan.get("citas", []), "respondible": True}, ensure_ascii=False)
    emitir({"type": "assistant", "uuid": f"{sid[:8]}-a{n + 1}",
            "message": {"id": f"msg_falso_{sid[:8]}_{n + 1}", "model": model, "role": "assistant", "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": final}], "usage": {"input_tokens": 10, "output_tokens": 50}}})
    emitir({"type": "result", "subtype": "success", "is_error": False, "num_turns": n + 1, "result": final, "session_id": sid,
            "total_cost_usd": round(costo, 6), "permission_denials": [],
            "modelUsage": {model: u | {"costUSD": round(costo, 6)}}}, a_la_transcripcion=False)
    guardar_transcripcion()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
