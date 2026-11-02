#!/usr/bin/env python3
"""herramientas_seco.py — Lo que comparten el selftest y la corrida en seco de B6.3: ningún dato real y USD 0.

  · cli_en_path: una carpeta con un `claude` que corre el CLI falso del banco (paralelo/cli_falso/claude_falso.py) o el de B6.3
    (seco/claude_falso_b63.py) con el intérprete de esta corrida, por su ruta absoluta: la copia del repo no tiene .venv, y el
    `claude` del banco lo busca relativo a su carpeta. Con `version`, uno cuyo `--version` da otra versión;
  · entrada_de_juguete: una entrada sellada de juguete (comun_b63.py), con la configuración, los servidores y las preguntas de
    seco/, el juez de EV2 con el sha256 de esta copia y BANCO_VENV_VECTOR; se puede pedir sin él o con uno que no existe;
  · juez_simulado: el juez de EV2 (juez.construir_kwargs, juzgar) sobre el SDK real con un transporte simulado
    (httpx.MockTransport, sin red) y la caché del repo (llm_cache.CachingClient), como construir_cliente_real sin la clave: guarda
    cada pedido para controlarlo y cuenta los que llegan al transporte (los que se pagarían);
  · Prueba: un proceso propio que solo espera su entrada estándar (sin sleep);
  · Registrador: anota la línea de comandos de cada subprocess.run y Popen de un módulo (guardas_lote, el lanzador del lote).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent                       # b63/seco
B63 = AQUI.parent
BANCO_DIR = B63.parent
REPO = BANCO_DIR.parents[2]                                 # la raíz del repo (comun_banco.REPO_DIR)
CF_BANCO = BANCO_DIR / "paralelo" / "cli_falso" / "claude_falso.py"
CF_B63 = AQUI / "claude_falso_b63.py"
CLAVE_DE_RELLENO = "sin-clave-corrida-en-seco"
VENV_VECTOR = "venvs/banco_vector_py312"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(REPO.resolve()))


def cli_en_path(tmp: Path, nombre: str, falso: Path = CF_B63, version: str | None = None) -> Path:
    d = tmp / nombre
    d.mkdir(parents=True, exist_ok=True)
    otra = (f'if [ "$1" = "--version" ]; then echo "{version} (CLI falso de prueba de la guarda)"; exit 0; fi\n' if version else "")
    (d / "claude").write_text(f'#!/bin/sh\n{otra}exec "{sys.executable}" -B "{falso}" "$@"\n', encoding="utf-8")
    (d / "claude").chmod(0o755)
    return d


def entrada_de_juguete(tmp: Path, nombre: str, ids: list[str], *, k: int = 1, tope: float = 50.0, freno: float = 40.0, P: int = 3,
                       venv: str | None = VENV_VECTOR, python: str | None = None, mutar=None) -> tuple[Path, str]:
    from importlib import import_module
    K = import_module("comun_b63")
    cfg = AQUI / "config_agentes_b63_juguete.json"
    ev2 = BANCO_DIR.parent / "ev2_juez"
    brazos = {"kg": "grafo", "fragmentos_bm25": "fragmentos_principal", "fragmentos_denso": "fragmentos_denso"}
    e = {"unidad": "B6.3, corrida en seco: entrada sellada DE JUGUETE",
         "preguntas": {"ruta": rel(AQUI / "preguntas_juguete_b63.json"), "sha256": sha(AQUI / "preguntas_juguete_b63.json"),
                       "ids_en_orden": ids},
         "k": k, "config_agentes": {"ruta": rel(cfg), "sha256": sha(cfg)},
         "brazos": {b: {"rol": r, "config_servidor": {"ruta": rel(AQUI / f"config_servidor_juguete_{b}.json"),
                                                      "sha256": sha(AQUI / f"config_servidor_juguete_{b}.json")}}
                    for b, r in brazos.items()},
         "R5": {"max_turns": 32, "tope_tool_calls_prompt": 30, "max_budget_usd": 1.8}, "tope_usd": tope, "freno_usd": freno, "P": P,
         "juez": {"archivos": [{"ruta": rel(ev2 / f), "sha256": sha(ev2 / f)} for f in ("juez.py", "mapping.py", "prompt_juez_v1.md")]}}
    if venv is not None:
        e["banco_venv_vector"] = {"ruta": venv, "python": python or K.version_python(K.ruta_de_rel(venv)) or "3.12"}
    if mutar:
        mutar(e)
    p = tmp / f"entrada_{nombre}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p, sha(p)


def juez_simulado(cache_dir: Path, pedidos: list, mal_formadas: str = "[[juez:malformada]]", al_pedido=None):
    """La fábrica de clientes del juez con un transporte simulado. `pedidos` recibe el cuerpo de cada pedido que llega al
    transporte (un pedido que la caché contesta no llega); `al_pedido`, si se pasa, lo mira antes de contestarlo."""
    import anthropic
    import httpx
    J = sys.modules["juez"]
    JB = sys.modules["juez_b63"]

    def handler(req: "httpx.Request") -> "httpx.Response":
        body = json.loads(req.content)
        pedidos.append(body)
        if al_pedido is not None:
            al_pedido(body)
        msg = body["messages"][0]["content"]
        n = int(re.search(r"CRITERIOS \((\d+)\):", msg).group(1))
        if mal_formadas in msg:
            texto = "salida del juez simulado sin ningún objeto"
        else:
            texto = json.dumps({"clasificacion_respuesta": "contenido",
                                "criterios": [{"indice": i, "veredicto": "cumplido", "fragmento": None, "justificacion": "simulada"}
                                              for i in range(1, n + 1)]})
        return httpx.Response(200, json={"id": f"msg_simulado_{len(pedidos)}", "type": "message", "role": "assistant",
                                         "model": body["model"], "content": [{"type": "text", "text": texto}],
                                         "stop_reason": "end_turn", "stop_sequence": None,
                                         "usage": {"input_tokens": 1200, "output_tokens": 400}})

    def f(rep: int, label: str):
        real = anthropic.Anthropic(api_key="sk-ant-prueba-transporte-simulado", max_retries=0,
                                   http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        return J.lc.CachingClient(real, domain="juez_ev2", db_path=J.db_path_rep(rep, cache_dir, JB.DB_PREFIX),
                                  namespace=J.lc.make_namespace(f"juez_ev2_r{rep}", code_ver=J.CODE_VER, thinking=False),
                                  thinking_enabled=False, run_label=label)
    return f


class Prueba:
    """Un proceso propio que solo espera su entrada estándar (sin sleep); al cerrarla, termina y el padre lo espera."""

    def __init__(self, argv: list[str]):
        self.argv = argv
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def cerrar(self) -> int:
        self.p.stdin.close()
        return self.p.wait()


def guion_de_prueba(tmp: Path, nombre: str) -> Path:
    p = tmp / nombre
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("import sys\nsys.stdin.read()\n", encoding="utf-8")
    return p


def reloj_que_cruza_la_medianoche(n_cambio: int):
    """Las primeras n_cambio-1 sesiones que empiezan, el 26/10/2026 a las 23:59 (hora local); desde la n_cambio, el 27/10 a las 00:01."""
    antes, despues, k = datetime(2026, 10, 26, 23, 59).timestamp(), datetime(2026, 10, 27, 0, 1).timestamp(), [0]

    def reloj() -> float:
        k[0] += 1
        return antes if k[0] < n_cambio else despues
    return reloj


class Registrador:
    """En lugar del módulo subprocess de otro módulo: anota la línea de comandos de cada run y Popen, y delega."""

    def __init__(self, lineas: list):
        self.lineas = lineas

    def __getattr__(self, n):
        return getattr(subprocess, n)

    def run(self, argv, *a, **kw):
        self.lineas.append(list(map(str, argv)))
        return subprocess.run(argv, *a, **kw)

    def Popen(self, argv, *a, **kw):                     # noqa: N802
        self.lineas.append(list(map(str, argv)))
        return subprocess.Popen(argv, *a, **kw)
