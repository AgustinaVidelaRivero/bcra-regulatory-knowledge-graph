#!/usr/bin/env python3
"""herramientas_b1bis.py (v2/b1bis) — Lo que usan el selftest y la corrida en seco de la etapa b1 bis del runner de B6.3. Es
b63/v2/seco/herramientas_b1.py (etapa b1) con las rutas de esta carpeta, las dos claves de relleno (la inválida, la que el CLI falso de
la b1 bis contesta con la forma del 401; y la buena, cualquier otra), `ProcesoConNombre` (un proceso de prueba propio con el nombre
de un guion en su ruta, que ninguna guarda cuenta, porque no es de Python) y `ventanas` (las de 30 caracteres de un texto).
Lo de la etapa b1, para el selftest de la etapa b1 del runner de B6.3 (USD 0, sin datos reales, sin Neo4j y sin Docker):
  · bin_falso: una carpeta para el PATH con un `claude` falso (solo `--version`, con la marca de falso), un `vm_stat` y un `sysctl`
    falsos (con las páginas y el swap que se pidan) y un `docker` falso (la memoria de la VM, la salud y el uso del contenedor que se
    pidan). Son guiones de shell que solo imprimen: no lanzan nada;
  · entrada_v2: una entrada sellada de juguete con los campos de la etapa b1, sobre la configuración de juguete de b63/seco/ (o la de
    R5 B de b63/v2/seco/) y las preguntas que se pidan;
  · ClienteJuez: un cliente falso del juez (messages.create) que cuenta sus llamadas; juez_simulado: el SDK real con un transporte
    simulado y la caché del repo, como juez.construir_cliente_real sin la clave ni la red;
  · Neo4jDoble: un doble de cargar_kg y del driver, con la huella y el KG_Meta que se pidan;
  · Prueba: un proceso propio que solo espera su entrada estándar (sin sleep).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                       # b63/v2/b1bis/seco
B1BIS = AQUI.parent
V2 = B1BIS.parent
B63 = V2.parent
BANCO_DIR = B63.parent
REPO = BANCO_DIR.parents[2]                                 # la raíz del repo (banco_mcp → experiment → data → raíz)
VENV_VECTOR = "venvs/banco_vector_py312"
PIP_FREEZE_SELLADO = "24f4c0644699e4ffcd952a27ea572d6ccbae88e63382e5b1441fdae0479fb4cb"     # el del §5 (registro, :5424)
HUELLA_B63 = "2645da6d01795d520f3c4ab5e237050c530238061f849cd7d1e0170be9223463"             # la de la decisión 8 (registro, :5928)
CLAVE_INVALIDA_DE_RELLENO = "clave-de-relleno-invalida-b1bis"   # no es ninguna clave: el CLI falso de la b1 bis da con ella el 401
CLAVE_DE_RELLENO = "clave-de-relleno-buena-b1bis"               # no es ninguna clave: con ella, el plan de cada pregunta


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(REPO.resolve()))


def _guion(d: Path, nombre: str, cuerpo: str) -> None:
    (d / nombre).write_text("#!/bin/sh\n" + cuerpo, encoding="utf-8")
    (d / nombre).chmod(0o755)


def bin_falso(tmp: Path, nombre: str, *, version: str = "2.1.241 (CLI falso del selftest de B6.3-b1)", paginas: dict | None = None,
              swap_mb: float = 100.0, memsize: int = 17_179_869_184, vm_bytes: int = 2_684_354_560, salud: str = "healthy",
              uso_contenedor: str = "512MiB / 2.5GiB") -> Path:
    d = tmp / nombre
    d.mkdir(parents=True, exist_ok=True)
    _guion(d, "claude", f'if [ "$1" = "--version" ]; then echo "{version}"; exit 0; fi\nexit 2\n')
    p = paginas or {"free": 100000, "active": 300000, "inactive": 200000, "speculative": 10000, "wired down": 150000,
                    "occupied by compressor": 50000}
    vm = "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n" + "".join(f"Pages {k}:{' ' * 20}{v}.\n" for k, v in p.items())
    _guion(d, "vm_stat", "cat <<'FIN'\n" + vm + "FIN\n")
    _guion(d, "sysctl", 'case "$2" in vm.swapusage) echo "total = 2048.00M  used = ' + f"{swap_mb:.2f}" +
           'M  free = 1948.00M  (encrypted)";; hw.memsize) echo "' + str(memsize) + '";; *) exit 1;; esac\n')
    _guion(d, "docker", 'case "$1" in info) echo "' + str(vm_bytes) + '";; inspect) echo "' + salud + '";; stats) echo "' + uso_contenedor
           + '";; *) exit 3;; esac\n')
    return d


def entrada_v2(tmp: Path, nombre: str, ids: list[str], *, preguntas: Path | None = None, k: int = 1, P: int = 1, pico: float = 3.0,
               tope: float = 50.0, freno: float = 40.0, r5: str = "A", mutar=None) -> tuple[Path, str]:
    import importlib
    K = importlib.import_module("comun_b63")
    seco = B63 / "seco"
    cfg = (V2 / "seco" / "config_agentes_b63_juguete_r5b.json") if r5 == "B" else (seco / "config_agentes_b63_juguete.json")
    pr = preguntas or (seco / "preguntas_juguete_b63.json")
    ev2 = BANCO_DIR.parent / "ev2_juez"
    brazos = {"kg": "grafo", "fragmentos_bm25": "fragmentos_principal", "fragmentos_denso": "fragmentos_denso"}
    R5 = {"A": {"max_turns": 32, "tope_tool_calls_prompt": 30, "max_budget_usd": 1.8},
          "B": {"max_turns": 47, "tope_tool_calls_prompt": 45, "max_budget_usd": 3.3}}[r5]
    e = {"unidad": "B6.3-b1, selftest: entrada sellada DE JUGUETE",
         "preguntas": {"ruta": rel(pr), "sha256": sha(pr), "ids_en_orden": ids}, "k": k,
         "config_agentes": {"ruta": rel(cfg), "sha256": sha(cfg)},
         "brazos": {b: {"rol": r, "config_servidor": {"ruta": rel(seco / f"config_servidor_juguete_{b}.json"),
                                                      "sha256": sha(seco / f"config_servidor_juguete_{b}.json")}}
                    for b, r in brazos.items()},
         "R5": R5, "tope_usd": tope, "freno_usd": freno, "P": P, "pico_sesion_gb": pico,
         "neo4j": {"uri": "bolt://127.0.0.1:47687", "huella_contenido": HUELLA_B63},
         "banco_venv_vector": {"ruta": VENV_VECTOR, "python": K.version_python(K.ruta_de_rel(VENV_VECTOR)) or "3.12",
                               "pip_freeze_sha256": PIP_FREEZE_SELLADO},
         "juez": {"archivos": [{"ruta": rel(ev2 / f), "sha256": sha(ev2 / f)} for f in ("juez.py", "mapping.py", "prompt_juez_v1.md")]}}
    if mutar:
        mutar(e)
    p = tmp / f"entrada_{nombre}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p, sha(p)


class ClienteJuez:
    """El cliente falso del juez: contesta un JSON válido (todos cumplidos) o, con [[juez:malformada]] en la respuesta, uno mal formado."""

    def __init__(self):
        self.n = 0
        self.messages = self

    def create(self, **kw):
        self.n += 1
        msg = kw["messages"][0]["content"]
        n = int(re.search(r"CRITERIOS \((\d+)\):", msg).group(1))
        texto = "sin objeto" if "[[juez:malformada]]" in msg else json.dumps({"clasificacion_respuesta": "contenido", "criterios": [
            {"indice": i, "veredicto": "cumplido", "fragmento": None, "justificacion": "prueba"} for i in range(1, n + 1)]})

        class B:
            type, text = "text", texto

        class U:
            input_tokens, output_tokens = 1000, 300

        class Resp:
            content, stop_reason, usage, model = [B()], "end_turn", U(), "claude-sonnet-4-6"
        return Resp()


def juez_simulado(cache_dir: Path, pedidos: list):
    """El juez de EV2 sobre el SDK real con un transporte simulado (sin red) y la caché del repo, una base por repetición."""
    import anthropic
    import httpx
    J, JB = sys.modules["juez"], sys.modules["juez_b63"]

    def handler(req):
        body = json.loads(req.content)
        pedidos.append(1)                                    # se cuenta, sin guardar el pedido
        n = int(re.search(r"CRITERIOS \((\d+)\):", body["messages"][0]["content"]).group(1))
        texto = json.dumps({"clasificacion_respuesta": "contenido", "criterios": [
            {"indice": i, "veredicto": "cumplido", "fragmento": None, "justificacion": "simulada"} for i in range(1, n + 1)]})
        return httpx.Response(200, json={"id": f"msg_simulado_{len(pedidos)}", "type": "message", "role": "assistant",
                                         "model": body["model"], "content": [{"type": "text", "text": texto}], "stop_reason": "end_turn",
                                         "stop_sequence": None, "usage": {"input_tokens": 1200, "output_tokens": 400}})

    def f(rep: int, label: str):
        real = anthropic.Anthropic(api_key="sk-ant-prueba-transporte-simulado", max_retries=0,
                                   http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        return J.lc.CachingClient(real, domain="juez_ev2", db_path=J.db_path_rep(rep, cache_dir, JB.DB_PREFIX),
                                  namespace=J.lc.make_namespace(f"juez_ev2_r{rep}", code_ver=J.CODE_VER, thinking=False),
                                  thinking_enabled=False, run_label=label)
    return f


class Neo4jDoble:
    """Un doble de cargar_kg (leer_meta, huella_neo4j) y de abrir_driver, con la huella de contenido y el KG_Meta que se pidan."""

    def __init__(self, huella: str, kg_sha: str, falla: bool = False):
        self.huella, self.kg_sha, self.falla = huella, kg_sha, falla

    def abrir(self):
        doble = self

        class D:
            def verify_connectivity(self):
                if doble.falla:
                    raise ConnectionError("doble")

            def close(self):
                pass
        return D()

    def leer_meta(self, driver, grafo):
        return {"kg_sha256": self.kg_sha}

    def huella_neo4j(self, driver, grafo):
        return {"n_nodos": 10, "n_aristas": 20, "estado": "e" * 64, "contenido": self.huella}


class Prueba:
    """Un proceso propio que solo espera su entrada estándar (sin sleep); al cerrarla, termina y el padre lo espera."""

    def __init__(self, argv: list[str]):
        self.argv = argv
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def cerrar(self) -> int:
        self.p.stdin.close()
        return self.p.wait()


class ProcesoConNombre:
    """Un proceso de prueba propio que lleva en su línea de comandos la ruta <carpeta del token>/<nombre> y solo espera su entrada
    estándar: `/bin/sh -c 'read x' <ruta>` (la ruta es su $0). No es un proceso de Python, así que la guarda de otro paso pago de
    cualquier paso que corra (guardas_lote: `script_python` y el nombre del guion) no lo cuenta; su línea de comandos sí trae el nombre,
    que es lo que mira el patrón. La lee `ps -p <su pid>`: ningún pgrep."""

    def __init__(self, carpeta: Path, nombre: str):
        carpeta.mkdir(parents=True, exist_ok=True)
        self.ruta = carpeta / nombre
        self.ruta.write_text("# proceso de prueba propio: no corre\n", encoding="utf-8")
        self.argv = ["/bin/sh", "-c", "read x", str(self.ruta)]
        self.p = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def linea(self) -> str:
        return subprocess.run(["ps", "-p", str(self.p.pid), "-o", "args="], capture_output=True, text=True).stdout.strip()

    def cerrar(self) -> int:
        self.p.stdin.close()
        return self.p.wait()


def ventanas(texto: str, n: int = 30) -> list[str]:
    """Todas las ventanas de n caracteres de un texto (el texto entero si es más corto)."""
    return [texto[i:i + n] for i in range(max(1, len(texto) - n + 1))]
