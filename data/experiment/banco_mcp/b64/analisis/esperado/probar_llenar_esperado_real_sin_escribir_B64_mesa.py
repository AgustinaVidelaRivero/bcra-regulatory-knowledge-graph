"""probar_llenar_esperado_real_sin_escribir_B64_mesa.py — Mesa, §384 (01/11/2026): el seco del llenado de los esperados sobre las rutas
reales, sin escribir nada. Importa `llenar_esperado_B64.py` sin editarlo y llama a `leer_plantilla`, `rutas`, `devueltas` y `llenar` con
las rutas reales, como `main`, salvo en dos cosas: no escribe, y en lugar de la clave de la adjudicación de la autora (que la mesa no abre)
le pasa un archivo propio, y de la clave controla solo que exista. Así controla, antes de que la autora lo corra, que estén todos los
archivos y que den los sha256 que se conocen. Imprime solo OK, cuentas y los sha256 que ya se conocen. USD 0.
  python3 -I -B probar_llenar_esperado_real_sin_escribir_B64_mesa.py <repo> <fuera_del_repo> <scratchpad del análisis> <carpeta de la
    mesa> <un archivo cualquiera, en lugar de la clave>
"""
import importlib.util
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("L", AQUI / "llenar_esperado_B64.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
R, F, SP, M, EN_LUGAR = (Path(x).resolve() for x in sys.argv[1:6])
plantilla = L.leer_plantilla(R)
rs = L.rutas(R, F, SP)
print("la clave de la adjudicación existe (no se abre):", rs["clave_adjudicacion"].is_file())
man = json.loads(rs["manifiesto_fuera"].read_bytes())
idx = {a["ruta"]: a["sha256"] for a in man["archivos"]}
dev = L.devueltas(F)
out = L.llenar(plantilla, rs | {"clases_documentos": M / L.MESA[0], "lugares": M / L.MESA[1], "clave_adjudicacion": EN_LUGAR},
               L.CONOCIDOS, idx, dev)
print(f"llenar: {sum(1 for k in out if not k.startswith('_'))} claves; las que se conocen dan su sha256: "
      f"{all(out[k] == v for k, v in L.CONOCIDOS.items())}; el D-10 y las fechas dan el del manifiesto: "
      f"{all(out[k] == idx[v] for k, v in L.EN_EL_MANIFIESTO.items())}; planillas devueltas hoy: {len(dev)}")
print("no escribió nada: no existen esperado/ ni entradas_mesa/:",
      not (F / "analisis_b64_corr/esperado").exists() and not (F / "analisis_b64_corr/entradas_mesa").exists())
