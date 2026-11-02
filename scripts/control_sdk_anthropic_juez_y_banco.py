"""Control, a USD 0 y sin red, del SDK y de la versión de la API con que corren el juez de B6.3 y el banco, fijados hasta que termine
B6.3: anthropic 0.100.0 del .venv del repo, que manda `anthropic-version: 2023-06-01`. Con la versión 2026-10-21, `temperature` da 400
en todos los modelos aun en su valor por defecto, y el SDK 1.0 la quitó de `messages.create` (TypeError); el juez de B6.3
(`data/experiment/ev2_juez/juez.py`, mandato Q8) usa claude-sonnet-4-6 con temperatura 0.

Frena (código 1) si algo cambió:
  1. el intérprete no es el python del .venv de un repo con el juez de B6.3;
  2. el SDK instalado no es anthropic 0.100.0;
  3. un pedido del juez, armado con su `construir_kwargs` y mandado por el SDK a un transporte simulado (httpx.MockTransport, sin
     red), no lleva `anthropic-version: 2023-06-01`, el modelo claude-sonnet-4-6 y `temperature` 0, o lleva `anthropic-beta`;
  4. el cliente real del juez (`construir_cliente_real`) deja de ser `anthropic.Anthropic(max_retries=3)`, sin otras opciones. Se lee por
     su árbol de sintaxis: el control no lo llama, porque carga el .env;
  5. algún .py del juez, del banco (`data/experiment/banco_mcp/`) o de la caché (`evaluacion/llm_cache.py`) fija una versión de la API,
     cabeceras por defecto o extra, o betas.
El agente del banco no pasa por este SDK: corre con el CLI de Claude Code, cuya versión es variable sellada del banco
(`banco_mcp/agentes/config_agentes.json`) y la controla su lanzador. Este control no la mira.

Imprime solo OK o FRENO por control, sin ninguna clave: no lee ningún .env, y la del transporte simulado es una cadena de prueba.
Uso, desde la raíz del repo: .venv/bin/python -I -B scripts/control_sdk_anthropic_juez_y_banco.py
"""
import ast
import importlib.metadata
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
JUEZ = RAIZ / "data" / "experiment" / "ev2_juez" / "juez.py"
SDK_FIJADO, VERSION_API, MODELO, TEMPERATURA = "0.100.0", "2023-06-01", "claude-sonnet-4-6", 0.0
VEDADO = re.compile(r"anthropic[-_]version|default_headers|extra_headers|anthropic[-_]beta|\bbetas\b", re.I)
res = {}


def control(nombre, ok):
    res[nombre] = bool(ok)


control("1. el intérprete es el python del .venv de un repo con el juez de B6.3",
        sys.prefix != sys.base_prefix and Path(sys.prefix).name == ".venv"
        and (Path(sys.prefix).parent / "data" / "experiment" / "ev2_juez" / "juez.py").is_file())
try:
    import anthropic
    import httpx
    instalado = importlib.metadata.version("anthropic")
except Exception:  # noqa: BLE001
    anthropic = httpx = None
    instalado = None
control(f"2. el SDK instalado es anthropic {SDK_FIJADO}", instalado == SDK_FIJADO and getattr(anthropic, "__version__", None) == SDK_FIJADO)

visto = {}


def transporte(pedido):
    visto["cabeceras"] = {k.lower(): v for k, v in pedido.headers.items()}
    visto["cuerpo"] = json.loads(pedido.content)
    return httpx.Response(200, json={"id": "msg_prueba", "type": "message", "role": "assistant", "model": MODELO,
                                     "content": [{"type": "text", "text": "{}"}], "stop_reason": "end_turn",
                                     "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})


ok3 = False
if anthropic is not None:
    try:
        sys.path.insert(0, str(JUEZ.parent))
        import juez as J  # noqa: E402
        cliente = anthropic.Anthropic(api_key="clave-de-prueba", max_retries=0,
                                      http_client=httpx.Client(transport=httpx.MockTransport(transporte)))
        cliente.messages.create(**J.construir_kwargs("pregunta de prueba", "respuesta de prueba",
                                                     [{"criterio": "criterio de prueba", "cita_textual": "cita de prueba"}]))
        cab, cuerpo = visto["cabeceras"], visto["cuerpo"]
        ok3 = (cab.get("anthropic-version") == VERSION_API and "anthropic-beta" not in cab and cuerpo.get("model") == MODELO
               and cuerpo.get("temperature") == TEMPERATURA and J.MODELO == MODELO and J.TEMPERATURE == TEMPERATURA)
    except Exception:  # noqa: BLE001
        ok3 = False
control(f"3. el pedido del juez, por el SDK, lleva anthropic-version {VERSION_API}, {MODELO} y temperature 0, sin betas", ok3)

arbol = ast.parse(JUEZ.read_text(encoding="utf-8"))
llamadas = [n for f in ast.walk(arbol) if isinstance(f, ast.FunctionDef) and f.name == "construir_cliente_real"
            for n in ast.walk(f) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "Anthropic"]
control("4. el cliente real del juez es anthropic.Anthropic(max_retries=3), sin otras opciones",
        len(llamadas) == 1 and not llamadas[0].args and [(k.arg, ast.literal_eval(k.value)) for k in llamadas[0].keywords] == [("max_retries", 3)])

fuentes = sorted({*JUEZ.parent.glob("*.py"), *(RAIZ / "data" / "experiment" / "banco_mcp").rglob("*.py"),
                  RAIZ / "data" / "experiment" / "evaluacion" / "llm_cache.py"})
con = [p for p in fuentes if "NO_ABRIR_" not in p.name and VEDADO.search(p.read_text(encoding="utf-8", errors="replace"))]
control(f"5. ningún .py del juez, del banco ni de la caché ({len(fuentes)}) fija una versión de la API, cabeceras o betas", not con)

for n, ok in res.items():
    print("OK    " if ok else "FRENO ", n)
if con:
    print("       los que la fijan:", ", ".join(str(p.relative_to(RAIZ)) for p in con))
print("control del SDK y de la versión de la API:", "OK" if all(res.values()) else "FRENO")
sys.exit(0 if all(res.values()) else 1)
