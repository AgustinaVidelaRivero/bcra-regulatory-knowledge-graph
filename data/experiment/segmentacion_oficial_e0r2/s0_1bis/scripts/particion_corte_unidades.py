"""S0-1 bis, A: `particionar_por_corte` (la partición por corte del perfil r2 que usa el runner de E1) sobre cada
unidad de una salida de E0, con el código de una copia. Solo lectura. Escribe {id: {"partes": [...] | None,
"informe": {...}}} con el texto, la herencia y el sha256 de cada parte, para comparar dos códigos byte a byte.

Uso: python -B particion_corte_unidades.py <raíz de la copia> <dir de E0> <salida.json>
(con el prototipo, S0_REGLAS elige las reglas y S0_RAZON_E1 la razón de tokens por carácter)"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
raiz, d, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(raiz / "data/experiment/reextraccion_v2/e0_chunking"))
import correr_e0 as CE  # noqa: E402
out = {}
for p in sorted(d.glob("chunks_*.json")):
    for c in json.loads(p.read_text(encoding="utf-8")):
        partes, info = CE.particionar_por_corte(c)
        out[c["id"]] = {"partes": partes, "informe": info}
sal.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
print(len(out), "unidades;", sum(1 for v in out.values() if v["partes"]), "partibles")
