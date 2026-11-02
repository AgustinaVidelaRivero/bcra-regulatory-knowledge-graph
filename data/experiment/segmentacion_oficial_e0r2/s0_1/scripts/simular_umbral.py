"""Regla 6 (d) de S0-1: qué movería bajar el umbral de la partición por tamaño de E0 (hoy 26.182, estricto) a un
valor dado, sobre una salida de E0: unidades entre el umbral nuevo y 26.182 (sin contar partes), sus TOs y cuántas
partes darían con la partición del prototipo (respetando tablas, con renglones). Solo lectura.

Uso: S0_REGLAS=r6 python -B simular_umbral.py <dir E0> <raíz del prototipo> <umbral> <salida.json>"""
import collections
import glob
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
d, proto, umbral, sal = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(proto / "data/experiment/reextraccion_v2/e0_chunking"))
import correr_e0 as CE  # noqa: E402
cs = [c for p in sorted(glob.glob(str(d / "chunks_*.json"))) for c in json.load(open(p, encoding="utf-8"))]
sel = [c for c in cs if umbral - 1 < c["chars_propio"] <= CE.UMBRAL_CHARS_SUBCHUNK and not c.get("sub_chunk")]
filas = []
for c in sel:
    p = CE._particionar_texto(c["texto"], respetar_tablas=True, renglones=CE.OBJETIVO_CHARS_PARTE)
    filas.append({"id": c["id"], "chars_propio": c["chars_propio"], "partes": len(p["grupos"]) if p else 1})
out = {"e0": d.name, "umbral": umbral, "unidades": len(sel), "tos": dict(collections.Counter(c["to"] for c in sel)),
       "partes": sum(f["partes"] for f in filas), "filas": filas}
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(out["unidades"], "unidades,", len(out["tos"]), "TOs,", out["partes"], "partes")
