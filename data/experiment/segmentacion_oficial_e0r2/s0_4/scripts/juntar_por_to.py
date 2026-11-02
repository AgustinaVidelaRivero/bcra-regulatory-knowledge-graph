"""Junta en un directorio de salida las corridas por TO de varias corridas de `correr_152.py` (las de `por_to/`) y
rehace los archivos por TO y los agregados con el mismo criterio que `correr_152.py` (cada agregado es un dict por TO;
se juntan en orden de TO). Sirve para correr el TO más pesado (manual) aparte, sin dos lecturas suyas a la vez.
Uso: python -B juntar_por_to.py <destino> <corrida> [<corrida> ...]   (un TO no puede estar en dos corridas)"""
import json
import shutil
import sys
from pathlib import Path

AGREGADOS = ("divergencias_indice_cuerpo.json", "conteos.json", "cobertura.json", "correcciones.json",
             "sub_chunking.json", "encabezados_conservados.json", "ids_desambiguados.json")
dest = Path(sys.argv[1])
fuentes = [Path(x) for x in sys.argv[2:]]
if dest.exists():
    shutil.rmtree(dest)
(dest / "por_to").mkdir(parents=True)
vistos = {}
for f in fuentes:
    for d in sorted((f / "por_to").iterdir()):
        if d.name in vistos:
            raise SystemExit(f"{d.name} está en {vistos[d.name]} y en {f}")
        vistos[d.name] = f
        shutil.copytree(d, dest / "por_to" / d.name)
tos = sorted(vistos)
agregados = {n: {} for n in AGREGADOS}
for to in tos:
    for p in sorted((dest / "por_to" / to).glob("*.json")):
        if p.name in AGREGADOS:
            agregados[p.name].update(json.loads(p.read_text(encoding="utf-8")))
        else:
            shutil.copyfile(p, dest / p.name)
for n, v in agregados.items():
    if v:
        (dest / n).write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
print("juntados", len(tos), "TOs en", dest)
