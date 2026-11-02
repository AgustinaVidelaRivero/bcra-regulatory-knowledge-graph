#!/usr/bin/env python3
"""lanzar_agente_n6_prueba.py — Lanza UNA sesión `claude -p` en un brazo de N6 (el grafo con el servidor de navegación o
una de las dos configuraciones de fragmentos del acumulado) con la configuración de prueba de U-BANCO-PARALELO
(paralelo/config_agentes_n6_prueba.json), y persiste lo mismo que el lanzador de U-A2.0-banco: prompt, comando, stream,
stderr, sesión, log R1 y meta. Tiene la interfaz de agentes/lanzar_agente.py, así que lo corre el lanzador del lote.

Reusa, importándolas sin editarlas, las piezas del lanzador sellado (agentes/lanzar_agente.py): construir_prompt,
flags_estructurales, env_sesion, sha_identidad, preparar_sesion, copiar_sesion, parsear_stream, leer_log_r1 y armar_meta,
con la vía de credenciales y el modo init tal cual; y de a2_1/lanzar_agente_a2_1.py, los conteos de H-B2. Lo propio:
  · la configuración de prueba de N6 (o la de --config-agentes, que usa el control negativo del test de aislamiento);
  · el entorno de la sesión, el de LA.env_sesion para el brazo `vector` en los tres brazos: los de fragmentos piden el venv
    del servidor de fragmentos, y el del grafo también, para el codificador de consultas de su familia 1 (el servidor
    del grafo corre en el .venv del repo, que fija su JSON de MCP);
  · los archivos de identidad con la configuración y el código del servidor de cada brazo;
  · en el registro, el lanzador que corrió: este archivo y agentes/lanzar_agente.py.
El cuerpo de `lanzar` replica `lanzar_agente_a2_2.lanzar` con esas diferencias.

Uso:
  lanzar_agente_n6_prueba.py --brazo kg --id X --pregunta "..." --out <dir> --modo init --sesiones <raíz>
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
for _p in (str(BANCO_DIR), str(BANCO_DIR / "agentes"), str(BANCO_DIR / "a2_1")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_agente as LA                                  # noqa: E402  (sellado: solo import)
import lanzar_agente_a2_1 as L21                            # noqa: E402  (A2.1: solo import)
from comun_banco import rel_repo, sha256_file               # noqa: E402

CONFIG_N6 = AQUI / "config_agentes_n6_prueba.json"


def cargar_cfg(ruta: Path = CONFIG_N6) -> dict:
    cfg = LA.cargar(ruta)
    if cfg["base"]["sha256"] != sha256_file(BANCO_DIR / cfg["base"]["ruta"]):
        raise SystemExit(f"ABORTO: {cfg['base']['ruta']} no es la base declarada en {rel_repo(ruta)}")
    return cfg


def archivos_identidad(cfg: dict, brazo: str, ruta_cfg: Path) -> dict:
    """Como LA.archivos_identidad, con la configuración y el código del servidor del brazo."""
    b = cfg["brazos"][brazo]
    rutas = {
        "config_agentes": ruta_cfg,
        "config_agentes_base": BANCO_DIR / cfg["base"]["ruta"],
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
    """La del lanzador sellado (lista cerrada, §83, §84 y §88) con el venv del servidor de fragmentos en los tres brazos."""
    return LA.env_sesion(cfg, "vector", via, log_r1, tag, modo, config_cli)


def lanzar(brazo: str, pid: str, pregunta: str, out: Path, modo: str = "init", via: str = "api",
           cwd: Path | None = None, timeout_s: float = 1800.0, sesiones: Path = LA.BANCO_SESIONES,
           ruta_cfg: Path = CONFIG_N6) -> dict:
    lanzador = LA.archivos_lanzador(LA.__file__, __file__)
    cfg = cargar_cfg(ruta_cfg)
    if brazo not in cfg["brazos"]:
        raise SystemExit(f"brazo desconocido: {brazo}")
    precios = LA.cargar(LA.PRECIOS)
    out.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())
    config_cli, cwd = LA.preparar_sesion(sesiones, cwd, session_id)
    prompt = LA.construir_prompt(cfg, brazo, pregunta)
    (out / f"prompt_{pid}.txt").write_text(prompt, encoding="utf-8")
    ident = archivos_identidad(cfg, brazo, ruta_cfg)
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
    meta["unidad"] = "U-BANCO-PARALELO (configuración de prueba de N6)"
    meta["sesion"] |= copia
    meta["harness_R10"]["lanzador"] = lanzador
    meta["duracion_s"] = round(duracion, 1)
    meta["hb2"] = {"max_turns_efectivo": cfg["corte_R5"]["max_turns"],
                   "max_turns_de_la_config": cfg["corte_R5"]["max_turns"]} | L21.conteos_hb2(lineas, stream["result"], log)
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
    ap.add_argument("--cwd", type=Path, default=None, help="cwd de la sesión (default: <sesiones>/cwd, el compartido)")
    ap.add_argument("--sesiones", type=Path, default=LA.BANCO_SESIONES, help="raíz de las sesiones del banco")
    ap.add_argument("--timeout-s", type=float, default=1800.0)
    ap.add_argument("--config-agentes", type=Path, default=CONFIG_N6)
    a = ap.parse_args()
    meta = lanzar(a.brazo, a.id, a.pregunta, a.out, a.modo, a.via, a.cwd, a.timeout_s, a.sesiones, a.config_agentes)
    print(json.dumps({"brazo": a.brazo, "modo": a.modo, "tools_coinciden": meta["inventario_tools_R6"]["coincide"],
                      "mcp": meta["servidores_mcp"]["en_init"], "completa": meta["completitud_R3"]["completa"],
                      "costo": meta["tokens_R9"]["costo_recomputado"]["total_usd"], "duracion_s": meta["duracion_s"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
