#!/usr/bin/env python3
"""comun_banco.py — piezas compartidas por los dos servidores MCP del banco
(U-A2.0-banco): log R1, sha de configuración, rutas y versiones.

R1 (docs/laudo_gate_trazabilidad.md): el registro del lado del servidor es la
FUENTE DE VERDAD de cada tool call; la sesión de Claude Code es solo el índice.
Por eso cada línea del log lleva la entrada y la salida ÍNTEGRAS (la cadena
exacta que viajó al cliente, sin truncar), un id de llamada, timestamp y el sha
de la configuración con la que corría el servidor.

Formato del log (JSONL, una línea por evento; `evento` ∈ {inicio, llamada, fin}):

  inicio  {evento, servidor, version_servidor, pid, timestamp, config, config_sha256,
           fuente: {...sha de la fuente de datos...}, entorno: {python, libs},
           sesion_tag, cwd, argv}
  llamada {evento, call_id, n, rpc_request_id, timestamp, duracion_ms, servidor,
           config_sha256, sesion_tag, tool, input, output_str, output_chars,
           output_sha256, error}
  fin     {evento, servidor, pid, timestamp, n_llamadas}

`call_id` = "<servidor>-<pid>-<n>" (único por proceso; Claude Code lanza un
proceso de servidor por sesión). `n` es el contador de llamadas del proceso:
es la base del mapa R7 (n -> tool_use_id), que arma el adaptador cruzando el
orden con la sesión y verificando `output_sha256` contra el texto que la sesión
registró.

Variables de entorno que leen los servidores (todas opcionales):
  BANCO_LOG_R1    ruta del archivo de log (default: logs/<servidor>_<utc>_<pid>.jsonl
                  bajo data/experiment/banco_mcp/)
  BANCO_SESION_TAG etiqueta libre que se copia a cada línea (p. ej. el id de la
                  pregunta de la corrida) para correlacionar log <-> sesión.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BANCO_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = BANCO_DIR.parent
REPO_DIR = EXPERIMENT_DIR.parents[1]
LOGS_DIR = BANCO_DIR / "logs"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def sha256_json(obj) -> str:
    """sha256 de la serialización canónica (sort_keys, sin espacios, UTF-8)."""
    return sha256_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":")).encode("utf-8"))


def ahora_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def rel_repo(p: Path | str) -> str:
    """Ruta relativa al repo; fuera del repo, con el home colapsado a `~`.
    Ninguna ruta absoluta de la máquina queda en un artefacto persistido."""
    p = Path(p).resolve()
    try:
        return str(p.relative_to(REPO_DIR))
    except ValueError:
        try:
            return "~/" + str(p.relative_to(Path.home()))
        except ValueError:
            return str(p)


def cargar_config(path: Path) -> tuple[dict, str]:
    """Config sellada: el sha es el del ARCHIVO tal cual está en disco (no de
    su forma canónica), para que cualquier edición —incluso de comentarios o
    espacios— cambie el sello."""
    return json.loads(path.read_text(encoding="utf-8")), sha256_file(path)


def versiones_entorno(modulos: list[str]) -> dict:
    import importlib.metadata as md
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for m in modulos:
        try:
            out[m] = md.version(m)
        except md.PackageNotFoundError:
            out[m] = None
    return out


class LogR1:
    """Escritor del log R1. Append-only, flush por línea."""

    def __init__(self, servidor: str, version_servidor: str, config: dict,
                 config_sha256: str, fuente: dict, entorno: dict,
                 ruta: Path | None = None):
        self.servidor = servidor
        self.version = version_servidor
        self.config_sha256 = config_sha256
        self.sesion_tag = os.environ.get("BANCO_SESION_TAG")
        self.pid = os.getpid()
        self.n = 0
        self.cerrado = False
        if ruta is None:
            env = os.environ.get("BANCO_LOG_R1")
            if env:
                ruta = Path(env)
            else:
                LOGS_DIR.mkdir(parents=True, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                ruta = LOGS_DIR / f"{servidor}_{ts}_{self.pid}.jsonl"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta = ruta
        self._f = open(ruta, "a", encoding="utf-8")
        self._escribir({
            "evento": "inicio", "servidor": servidor, "version_servidor": version_servidor,
            "pid": self.pid, "timestamp": ahora_utc(), "config": config,
            "config_sha256": config_sha256, "fuente": fuente, "entorno": entorno,
            "sesion_tag": self.sesion_tag, "cwd": rel_repo(Path.cwd()),
            # rutas relativas al repo: ninguna ruta absoluta de la máquina queda persistida
            "argv": [Path(a).name if i == 0 else (rel_repo(a) if Path(a).exists() else a)
                     for i, a in enumerate(sys.argv)],
        })

    def _escribir(self, d: dict) -> None:
        self._f.write(json.dumps(d, ensure_ascii=False) + "\n")
        self._f.flush()

    def nuevo_call_id(self) -> tuple[int, str]:
        self.n += 1
        return self.n, f"{self.servidor}-{self.pid}-{self.n}"

    def llamada(self, n: int, call_id: str, rpc_request_id, tool: str, arguments: dict,
                output_str: str | None, t0: float, error: str | None = None) -> None:
        self._escribir({
            "evento": "llamada", "call_id": call_id, "n": n,
            "rpc_request_id": rpc_request_id, "timestamp": ahora_utc(),
            "duracion_ms": round((time.perf_counter() - t0) * 1000, 3),
            "servidor": self.servidor, "config_sha256": self.config_sha256,
            "sesion_tag": self.sesion_tag, "tool": tool, "input": arguments,
            "output_str": output_str,
            "output_chars": None if output_str is None else len(output_str),
            "output_sha256": None if output_str is None else sha256_bytes(output_str.encode("utf-8")),
            "error": error,
        })

    def fin(self) -> None:
        if self.cerrado:
            return
        self.cerrado = True
        self._escribir({"evento": "fin", "servidor": self.servidor, "pid": self.pid,
                        "timestamp": ahora_utc(), "n_llamadas": self.n})
        self._f.close()


def serializar_payload(obj) -> str:
    """LA serialización del harness congelado (harness.py:512):
    `json.dumps(result, ensure_ascii=False)`. Es la cadena exacta que el agente
    del harness recibió como tool_result y contra la que el replay estándar
    compara (output_truncado / output_chars). No se cambia ni un separador."""
    return json.dumps(obj, ensure_ascii=False)
