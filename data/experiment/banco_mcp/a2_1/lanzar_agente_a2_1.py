#!/usr/bin/env python3
"""lanzar_agente_a2_1.py — Lanza UNA sesión `claude -p` en un brazo de fragmentos de A2.1
(tramo 1: modo init para el aislamiento; tramo 2: smoke y H-B2) y persiste lo mismo que el
lanzador de U-A2.0-banco: prompt, comando, stream, stderr, sesión, log R1 y meta.

Reusa, importándolas, las piezas del lanzador sellado (agentes/lanzar_agente.py):
construir_prompt, flags_estructurales, env_sesion, sha_identidad, slug_proyecto,
parsear_stream, leer_log_r1 y armar_meta, con la vía de credenciales y el modo init tal
cual. Lo propio de A2.1:
  · la config de agentes de A2.1 (a2_1/config_agentes_a2_1.json): los brazos
    `fragmentos_bm25` y `fragmentos_denso`;
  · los archivos de identidad con la config y el código del servidor de cada brazo;
  · `--max-turns` para las sesiones de H-B2 (si no se pasa, el 12 de la config), que se
    registra en meta["hb2"] junto con los conteos que H-B2 caracteriza;
  · la carpeta de configuración y el cwd de la sesión, los del banco (LA.preparar_sesion): config/<session_id>/
    y el cwd compartido, bajo --sesiones; la copia de la sesión, desde esa carpeta (LA.copiar_sesion);
  · en el registro, el lanzador que corrió: este archivo y agentes/lanzar_agente.py.
El cuerpo de `lanzar` replica `lanzar_agente.main` con esas diferencias.

Uso:
  lanzar_agente_a2_1.py --brazo fragmentos_bm25 --id X --pregunta "..." --out <dir> --modo init
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
for _p in (str(BANCO_DIR), str(BANCO_DIR / "agentes")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_agente as LA                                  # noqa: E402  (sellado: solo import)
from comun_banco import rel_repo, sha256_file               # noqa: E402

CONFIG_A21 = AQUI / "config_agentes_a2_1.json"
CONFIG_BASE = BANCO_DIR / "agentes" / "config_agentes.json"


def cargar_cfg(max_turns: int | None = None) -> dict:
    cfg = LA.cargar(CONFIG_A21)
    if cfg["base"]["sha256"] != sha256_file(CONFIG_BASE):
        raise SystemExit("ABORTO: agentes/config_agentes.json no es la base declarada en config_agentes_a2_1.json")
    if max_turns is not None:
        cfg = json.loads(json.dumps(cfg))
        cfg["corte_R5"]["max_turns"] = int(max_turns)
    return cfg


def archivos_identidad(cfg: dict, brazo: str) -> dict:
    """Como LA.archivos_identidad, con la config y el código del servidor del brazo de A2.1."""
    b = cfg["brazos"][brazo]
    rutas = {
        "config_agentes": CONFIG_A21,
        "config_agentes_base": CONFIG_BASE,
        "plantilla_prompt": BANCO_DIR / cfg["prompt"]["plantilla"],
        "bloque_tools": BANCO_DIR / b["bloque_tools"],
        "mcp_config": BANCO_DIR / b["mcp_config"],
        "precios_sellados": LA.PRECIOS,
        "config_servidor": BANCO_DIR / b["config_servidor"],
    }
    for k, r in enumerate(b["archivos_servidor"]):
        rutas["servidor" if k == 0 else f"servidor_{Path(r).stem}"] = BANCO_DIR / r
    rutas["comun_banco"] = BANCO_DIR / "comun_banco.py"
    return {k: {"ruta": rel_repo(v), "sha256": sha256_file(v)} for k, v in rutas.items()}


def env_sesion(cfg: dict, brazo: str, via: str, log_r1: Path, tag: str, modo: str,
               config_cli: Path | None = None) -> tuple[dict, dict]:
    """La del lanzador sellado: los brazos de fragmentos piden el venv del servidor vectorial
    igual que el brazo `vector` de la base, que es lo único que esa función mira del brazo."""
    return LA.env_sesion(cfg, "vector", via, log_r1, tag, modo, config_cli)


def conteos_hb2(lineas: list[str], result: dict | None, log: dict) -> dict:
    """Los conteos que H-B2 caracteriza (a2_1/diseno_HB2.md, §3)."""
    ids_asistente, n_tool_use, n_tool_result, n_user, por_mensaje = [], 0, 0, 0, {}
    for l in lineas:
        try:
            d = json.loads(l)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "assistant":
            msg = d.get("message") or {}
            mid = msg.get("id") or d.get("uuid")
            if mid not in ids_asistente:
                ids_asistente.append(mid)
            k = sum(1 for c in msg.get("content") or [] if isinstance(c, dict) and c.get("type") == "tool_use")
            n_tool_use += k
            por_mensaje[mid] = por_mensaje.get(mid, 0) + k   # stream-json: un evento por bloque, mismo message.id
        elif d.get("type") == "user":
            n_user += 1
            n_tool_result += sum(1 for c in (d.get("message") or {}).get("content") or []
                                 if isinstance(c, dict) and c.get("type") == "tool_result")
    r = result or {}
    return {"num_turns": r.get("num_turns"), "subtype": r.get("subtype"), "is_error": r.get("is_error"),
            "stop_reason": r.get("stop_reason"), "n_mensajes_asistente": len(ids_asistente),
            "n_tool_use": n_tool_use, "n_tool_result": n_tool_result, "n_eventos_user": n_user,
            "n_mensajes_con_tool_use": sum(1 for v in por_mensaje.values() if v),
            "max_tool_use_por_mensaje": max(por_mensaje.values() or [0]),
            "n_llamadas_log_r1": log.get("n_llamadas"), "log_r1_con_fin": log.get("fin") is not None,
            "corte_disparado": r.get("subtype") == "error_max_turns",
            "hay_result": result is not None}


def lanzar(brazo: str, pid: str, pregunta: str, out: Path, modo: str = "init", via: str = "api",
           max_turns: int | None = None, cwd: Path | None = None, timeout_s: float = 900.0,
           sesiones: Path = LA.BANCO_SESIONES) -> dict:
    lanzador = LA.archivos_lanzador(LA.__file__, __file__)
    cfg = cargar_cfg(max_turns)
    if brazo not in cfg["brazos"]:
        raise SystemExit(f"brazo desconocido: {brazo}")
    precios = LA.cargar(LA.PRECIOS)
    out.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())
    config_cli, cwd = LA.preparar_sesion(sesiones, cwd, session_id)
    prompt = LA.construir_prompt(cfg, brazo, pregunta)
    (out / f"prompt_{pid}.txt").write_text(prompt, encoding="utf-8")
    ident = archivos_identidad(cfg, brazo)
    flags = LA.flags_estructurales(cfg, brazo)
    sha_id = LA.sha_identidad(ident, cfg["modelo"], flags, prompt)
    log_r1 = (out / f"log_r1_{pid}.jsonl").resolve()
    env, env_decl = env_sesion(cfg, brazo, via, log_r1, pid, modo, config_cli)
    mcp_json = str(BANCO_DIR / cfg["brazos"][brazo]["mcp_config"])
    cmd = ["claude", cfg["modo_harness"], "-p", prompt, "--model", cfg["modelo"],
           "--output-format", "stream-json", "--verbose", "--tools", "",
           "--strict-mcp-config", "--mcp-config", mcp_json,
           "--permission-mode", "dontAsk", "--allowedTools", cfg["brazos"][brazo]["allowed_tools"],
           "--disallowedTools", LA.DISALLOWED,
           "--max-turns", str(cfg["corte_R5"]["max_turns"]),
           "--max-budget-usd", str(cfg["corte_R5"]["max_budget_usd_por_sesion"]),
           "--session-id", session_id]
    if modo == "init":
        cmd.append("--no-session-persistence")
    claude_version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    comando = {"argv": [("<prompt>" if x == prompt else (rel_repo(x) if x == mcp_json else x)) for x in cmd],
               "flags_estructurales": flags, "cwd": rel_repo(cwd), "env_declarado": env_decl,
               "session_id": session_id, "claude_code_version": claude_version,
               "archivos_identidad": ident, "sha_identidad_pipeline": sha_id, "lanzador": lanzador,
               "lanzado": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out / f"comando_{pid}.json").write_text(json.dumps(comando, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    t0 = time.time()
    stream_path = out / f"stream_{pid}.jsonl"
    with open(stream_path, "w", encoding="utf-8") as fout, open(out / f"stderr_{pid}.txt", "w", encoding="utf-8") as ferr:
        proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=ferr, text=True)
        init_visto = False
        try:
            for linea in proc.stdout:
                fout.write(linea); fout.flush()
                if modo == "init" and '"subtype":"init"' in linea.replace(" ", ""):
                    init_visto = True
                if modo == "init" and init_visto and '"api_retry"' in linea:
                    proc.kill(); break       # modo init: ya está el inventario; nada salió a la API
                if time.time() - t0 > timeout_s:
                    proc.kill(); break
        finally:
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
    duracion = time.time() - t0

    sesion_copia, copia = LA.copiar_sesion(config_cli, cwd, session_id, out, pid, modo == "real")
    lineas = stream_path.read_text(encoding="utf-8").splitlines()
    stream = LA.parsear_stream(lineas)
    log = LA.leer_log_r1(log_r1)
    meta = LA.armar_meta(cfg, brazo, ident, sha_id, comando, stream, log, precios, via, modo, pid,
                         sesion_copia, claude_version)
    meta["unidad"] = "A2.1"
    meta["sesion"] |= copia
    meta["harness_R10"]["lanzador"] = lanzador
    meta["duracion_s"] = round(duracion, 1)
    meta["hb2"] = {"max_turns_efectivo": cfg["corte_R5"]["max_turns"],
                   "max_turns_de_la_config": LA.cargar(CONFIG_A21)["corte_R5"]["max_turns"]} | conteos_hb2(
        lineas, stream["result"], log)
    (out / f"meta_{pid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brazo", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--pregunta", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--modo", choices=["real", "init"], default="init")
    ap.add_argument("--via", choices=["api", "bedrock"], default="api")
    ap.add_argument("--max-turns", type=int, default=None)
    ap.add_argument("--cwd", type=Path, default=None,
                    help="cwd de la sesión (default: <sesiones>/cwd, el compartido)")
    ap.add_argument("--sesiones", type=Path, default=LA.BANCO_SESIONES, help="raíz de las sesiones del banco")
    ap.add_argument("--timeout-s", type=float, default=900.0)
    a = ap.parse_args()
    meta = lanzar(a.brazo, a.id, a.pregunta, a.out, a.modo, a.via, a.max_turns, a.cwd, a.timeout_s, a.sesiones)
    print(json.dumps({"id": a.id, "brazo": a.brazo, "modo": a.modo, "tools": meta["inventario_tools_R6"],
                      "mcp": meta["servidores_mcp"]["en_init"], "completa": meta["completitud_R3"],
                      "costo": meta["tokens_R9"]["costo_recomputado"], "hb2": meta["hb2"],
                      "duracion_s": meta["duracion_s"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
