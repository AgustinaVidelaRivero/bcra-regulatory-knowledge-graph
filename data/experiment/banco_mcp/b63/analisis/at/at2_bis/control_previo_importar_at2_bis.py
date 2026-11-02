"""El control previo de la AT2-bis, antes de leer ningún dato: carga analizar_b63 desde la carpeta que se le pasa a
--codigo-analisis, con el sha256 de analizar_b63.py antes de importarlo, y llama a analizar_b63.importar(<clon>/data/experiment/
banco_mcp/b63/v2/b2, analizar_b63.ESPERADO). Nada más. Imprime «ok»; si falla, solo el nombre del módulo que falta o el tipo
del error, nunca su mensaje. Lo que el código importado imprima se descarta (se dice solo si imprimió algo).
Uso: python -I -B control_previo_importar.py <carpeta del código del análisis> <clon>"""
import contextlib
import hashlib
import importlib.util
import io
import sys
from pathlib import Path

SHA_ANALIZAR = "9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb"
codigo, clon = Path(sys.argv[1]), Path(sys.argv[2])
p = codigo / "analizar_b63.py"
if hashlib.sha256(p.read_bytes()).hexdigest() != SHA_ANALIZAR:
    print("FRENO: analizar_b63.py no da su sha256")
    raise SystemExit(10)
print("analizar_b63.py: sha256 igual al de HEAD, antes de importarlo")
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        spec = importlib.util.spec_from_file_location("analizar_b63", p)
        A = importlib.util.module_from_spec(spec)
        sys.modules["analizar_b63"] = A
        spec.loader.exec_module(A)
        A.importar(clon / "data/experiment/banco_mcp/b63/v2/b2", A.ESPERADO)
except ModuleNotFoundError as ex:
    print(f"falta el módulo: {ex.name}")
    raise SystemExit(1)
except BaseException as ex:  # noqa: BLE001  (sin el mensaje: puede traer un id o un texto)
    print(f"error: {type(ex).__name__}")
    raise SystemExit(1)
print(f"lo importado imprimió algo: {'sí (descartado)' if buf.getvalue() else 'no'}")
print("ok")
