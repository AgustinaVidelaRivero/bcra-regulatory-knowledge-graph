#!/usr/bin/env python3
"""formas_error_b63.py — Las formas reales del error del CLI, a USD 0 (etapa b1 del runner de B6.3; decisión de la autora del
26/10/2026: «Opción (d): la sesión queda incompleta, no cuenta como correcta en el análisis principal, sale del de sensibilidad y se
declara, y el lote frena cuando junta 3 formas desconocidas.»).

El CLI real (`claude` del PATH; la versión sellada de A2.2, 2.1.241), con los flags sellados de A2.2 y el entorno que arma el
lanzador (LA.env_sesion por paralelo/lanzar_agente_n6_prueba.env_sesion: la lista cerrada, su carpeta de configuración propia y el cwd
fuera de git; nunca la configuración del asistente de la carpeta personal), lanzado directo, sin el lote y sin el runner, sobre la configuración de juguete de b63/seco/ (su
servidor MCP de juguete: ni el grafo ni los índices) y una pregunta de prueba que no sale de ningún conjunto. Cinco casos, uno a la vez:
  puerto_cerrado    ANTHROPIC_BASE_URL a 127.0.0.1:9, el del modo init del lanzador (nada escucha ahí);
  http_429, http_500, http_529   ANTHROPIC_BASE_URL a seco/servidor_errores_b63.py, que contesta ese error y cuenta los pedidos;
  clave_invalida    sin ANTHROPIC_BASE_URL: la API, con una clave inválida que arma este script (no es ninguna clave real; nunca se
                    imprime ni se guarda): la API la rechaza sin llegar al modelo. Corre al final y solo si antes corrió al menos un
                    caso del servidor, todos sus POST trajeron esa clave (el HEAD de su prueba de conexión no trae ninguna) y el
                    system/init dice que la clave sale del entorno. --casos elige cuáles corren.
En todos, la clave de la sesión es esa clave inválida.
Por caso, sin el texto de ningún pedido: si hay `result`, su `subtype` y su `is_error`; los eventos system/api_retry (cuántos, sus
`error_status` y su `error`); el código de salida, la duración y, del servidor, los pedidos que recibió. Después controla por código que
la clave no esté en ninguna salida (el stream, el stderr y la transcripción; el `.claude.json` de la carpeta de configuración no se abre).
Las salidas de las sesiones quedan en --tmp, fuera del repo; el resultado, en --resultado.
Uso: env -i PATH HOME BANCO_VENV_VECTOR=<venv> <python> -B data/experiment/banco_mcp/b63/v2/formas_error_b63.py --tmp <dir> --resultado <json>
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

AQUI = Path(__file__).resolve().parent
B63 = AQUI.parent
BANCO_DIR = B63.parent
for _p in (str(BANCO_DIR), str(BANCO_DIR / "agentes"), str(BANCO_DIR / "paralelo"), str(AQUI / "seco")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_agente as LA                                  # noqa: E402  (sellado: solo import)
import lanzar_agente_n6_prueba as N6P                       # noqa: E402  (solo import)
from servidor_errores_b63 import ServidorErrores            # noqa: E402

CFG = B63 / "seco" / "config_agentes_b63_juguete.json"
BRAZO = "kg"
PREGUNTA = "Pregunta de prueba de las formas del error de B6.3: sin modelo."
PUERTO_CERRADO = "http://127.0.0.1:9"
TIMEOUT_S = 900.0
CASOS = ("http_429", "http_500", "http_529", "puerto_cerrado", "clave_invalida")


def armar(cfg: dict, raiz: Path, pid: str, clave: str, base_url: str | None) -> dict:
    """La sesión como la arma paralelo/lanzar_agente_n6_prueba.lanzar en modo real, con la clave inválida y la URL base del caso."""
    out = raiz / "salida" / pid
    out.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())
    config_cli, cwd = LA.preparar_sesion(raiz / "sesiones", None, session_id)
    prompt = LA.construir_prompt(cfg, BRAZO, PREGUNTA)
    log_r1 = (out / f"log_r1_{pid}.jsonl").resolve()
    env, _ = N6P.env_sesion(cfg, BRAZO, "api", log_r1, pid, "init", config_cli)   # el modo init: la clave del entorno, sin la real
    env["ANTHROPIC_API_KEY"] = clave
    if base_url is None:
        env.pop("ANTHROPIC_BASE_URL", None)
    else:
        env["ANTHROPIC_BASE_URL"] = base_url
    mcp_json = str(BANCO_DIR / cfg["brazos"][BRAZO]["mcp_config"])
    cmd = ["claude", cfg["modo_harness"], "-p", prompt, "--model", cfg["modelo"], "--output-format", "stream-json", "--verbose",
           "--tools", "", "--strict-mcp-config", "--mcp-config", mcp_json, "--permission-mode", "dontAsk",
           "--allowedTools", cfg["brazos"][BRAZO]["allowed_tools"], "--disallowedTools", LA.DISALLOWED,
           "--max-turns", str(cfg["corte_R5"]["max_turns"]), "--max-budget-usd", str(cfg["corte_R5"]["max_budget_usd_por_sesion"]),
           "--session-id", session_id]
    return {"pid": pid, "out": out, "cwd": cwd, "config_cli": config_cli, "session_id": session_id, "env": env, "cmd": cmd,
            "nombres_del_entorno": sorted(env)}


def correr(s: dict) -> dict:
    t0 = time.time()
    with open(s["out"] / "stream.jsonl", "w", encoding="utf-8") as fo, open(s["out"] / "stderr.txt", "w", encoding="utf-8") as fe:
        p = subprocess.Popen(s["cmd"], cwd=str(s["cwd"]), env=s["env"], stdin=subprocess.DEVNULL, stdout=fo, stderr=fe)
        try:
            rc = p.wait(timeout=TIMEOUT_S)                   # la espera del padre sobre su hijo, con un plazo
            corte = False
        except subprocess.TimeoutExpired:
            p.kill()
            rc = p.wait()
            corte = True
    return {"rc": rc, "duracion_s": round(time.time() - t0, 1), "cortada_por_el_plazo_de_la_prueba": corte}


def forma(stream: Path) -> dict:
    """Del stream, sin ningún texto: el system/init (de dónde sale la clave, la versión), el result (subtype, is_error, num_turns) y
    los system/api_retry (error_status y error)."""
    init, result, retries, tipos = None, None, [], []
    for linea in stream.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue
        tipos.append(f"{d.get('type')}/{d.get('subtype') or ''}")
        if d.get("type") == "system" and d.get("subtype") == "init":
            init = {"apiKeySource": d.get("apiKeySource"), "claude_code_version": d.get("claude_code_version")}
        elif d.get("type") == "system" and d.get("subtype") == "api_retry":
            retries.append({"error_status": d.get("error_status"), "error": d.get("error")})
        elif d.get("type") == "result":
            result = {"subtype": d.get("subtype"), "is_error": d.get("is_error"), "num_turns": d.get("num_turns"),
                      "api_error_status": d.get("api_error_status"), "terminal_reason": d.get("terminal_reason"),
                      "tiene_modelUsage": bool(d.get("modelUsage")), "claves": sorted(d)}
    return {"init": init, "hay_result": result is not None, "result": result, "api_retry": len(retries),
            "api_retry_error_status": sorted({str(r["error_status"]) for r in retries}),
            "api_retry_error": sorted({str(r["error"]) for r in retries}),
            "eventos": {t: tipos.count(t) for t in sorted(set(tipos))}}


def clave_en(rutas: list[Path], clave: str) -> int:
    return sum(1 for p in rutas if p.is_file() and clave in p.read_text(encoding="utf-8", errors="replace"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp", type=Path, required=True)
    ap.add_argument("--resultado", type=Path, required=True)
    ap.add_argument("--casos", default=",".join(CASOS), help="los casos, en su orden (clave_invalida exige uno del servidor antes)")
    a = ap.parse_args()
    casos = [c for c in a.casos.split(",") if c]
    if any(c not in CASOS for c in casos):
        raise SystemExit(f"casos desconocidos: {casos}")
    if not os.environ.get("BANCO_VENV_VECTOR"):
        raise SystemExit("falta BANCO_VENV_VECTOR (el servidor de juguete corre con su Python)")
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ABORTO: hay una ANTHROPIC_API_KEY en el entorno; esta medición corre sin ninguna clave real")
    tmp = a.tmp.resolve()
    if tmp.is_relative_to(LA.REPO_DIR) or LA.dentro_de_git(tmp) is not None:
        raise SystemExit("ABORTO: --tmp dentro del repo o de git")
    cfg = N6P.cargar_cfg(CFG)
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    if not version.startswith(cfg["claude_code_version_sellada"]) or "falso" in version:
        raise SystemExit(f"ABORTO: el claude del PATH no es el real sellado ({version!r})")
    clave = f"sk-ant-api03-prueba-b63-invalida-{secrets.token_hex(24)}"
    srv = ServidorErrores(clave)
    res = {"que": "las formas reales del error del CLI (USD 0)", "claude_version": version, "config": LA.rel_repo(CFG),
           "brazo": BRAZO, "timeout_de_la_prueba_s": TIMEOUT_S, "casos": {}}
    try:
        for caso in casos:
            if caso == "clave_invalida":
                antes = res["casos"]
                http = [c for c in antes.values() if c.get("codigo_http")]
                ok = bool(http) and all(
                    c["pedidos_del_servidor"].get(f"{c['codigo_http']}|POST:otra_clave_o_ninguna|", 0) == 0
                    and c["pedidos_del_servidor"].get(f"{c['codigo_http']}|POST:clave_inválida_del_pedido|", 0)
                    == c["pedidos_del_servidor"].get(f"{c['codigo_http']}|POST|/v1/messages", -1)
                    and (c["forma"]["init"] or {}).get("apiKeySource") == "ANTHROPIC_API_KEY" for c in http)
                if not ok:
                    res["casos"][caso] = {"no_corrido": "un POST al servidor no trajo la clave inválida, ningún caso del servidor corrió "
                                                        "antes, o la clave no salía del entorno"}
                    continue
            # la clave inválida va a la API: sin ANTHROPIC_BASE_URL (un `.get(caso) or srv.url(...)` la mandaba al servidor local)
            base = PUERTO_CERRADO if caso == "puerto_cerrado" else None if caso == "clave_invalida" else srv.url(caso.split("_")[1])
            s = armar(cfg, tmp / caso, caso.upper(), clave, base)
            r = correr(s)
            f = forma(s["out"] / "stream.jsonl")
            transcripcion = s["config_cli"] / "projects" / LA.slug_proyecto(s["cwd"]) / f"{s['session_id']}.jsonl"
            r |= {"forma": f, "url_base": "la API" if base is None else ("127.0.0.1:9" if base == PUERTO_CERRADO else f"servidor local /c{caso.split('_')[1]}"),
                  "nombres_del_entorno": s["nombres_del_entorno"], "transcripcion": transcripcion.is_file(),
                  "salidas_con_la_clave": clave_en([s["out"] / "stream.jsonl", s["out"] / "stderr.txt", transcripcion], clave)}
            if caso.startswith("http_"):
                r["codigo_http"] = caso.split("_")[1]
                r["pedidos_del_servidor"] = {k: v for k, v in srv.cuentas().items() if k.startswith(r["codigo_http"] + "|")}
            res["casos"][caso] = r
            print(f"{caso}: rc {r['rc']}, {r['duracion_s']} s, result {f['hay_result']}, "
                  f"subtype {(f['result'] or {}).get('subtype')}, is_error {(f['result'] or {}).get('is_error')}, "
                  f"api_retry {f['api_retry']} {f['api_retry_error_status']}", flush=True)
    finally:
        srv.cerrar()
        del clave
    a.resultado.parent.mkdir(parents=True, exist_ok=True)
    a.resultado.write_text(json.dumps(res, ensure_ascii=False, indent=1).replace(str(tmp), "<tmp>").replace(str(Path.home()), "$HOME")
                           + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
