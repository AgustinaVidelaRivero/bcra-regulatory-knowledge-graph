"""Control duro de S0-4: los TOs de la tanda 0 que están en la corrida de los 152 (ctacte, lingob, polcre, pagjub y
docvig) dan, byte a byte, sus archivos de `salida_tanda0_r2b/`; y sus entradas de los siete agregados son iguales (o
faltan en los dos lados). Solo lectura. Uso: python -B control_tanda0_en_152.py <dir 152> <salida_tanda0_r2b>"""
import json
import sys
from pathlib import Path

d152, t0 = Path(sys.argv[1]), Path(sys.argv[2])
AGREGADOS = ("divergencias_indice_cuerpo.json", "conteos.json", "cobertura.json", "correcciones.json",
             "sub_chunking.json", "encabezados_conservados.json", "ids_desambiguados.json")
tos = sorted({p.name.split("_", 1)[1][:-5] for p in t0.glob("chunks_*.json")}
             & {p.name.split("_", 1)[1][:-5] for p in d152.glob("chunks_*.json")})
iguales, distintos = 0, []
for to in tos:
    for pref in ("chunks", "estructura", "indice", "tablas", "pies"):
        a, b = d152 / f"{pref}_{to}.json", t0 / f"{pref}_{to}.json"
        if a.exists() and b.exists() and a.read_bytes() == b.read_bytes():
            iguales += 1
        else:
            distintos.append(f"{pref}_{to}.json")
ag = {"iguales": 0, "ausentes_en_los_dos": 0, "distintos": []}
for n in AGREGADOS:
    pa, pb = d152 / n, t0 / n
    ja = json.loads(pa.read_text(encoding="utf-8")) if pa.exists() else {}
    jb = json.loads(pb.read_text(encoding="utf-8")) if pb.exists() else {}
    for to in tos:
        if to not in ja and to not in jb:
            ag["ausentes_en_los_dos"] += 1
        elif ja.get(to) == jb.get(to):
            ag["iguales"] += 1
        else:
            ag["distintos"].append(f"{n}:{to}")
print(json.dumps({"tos": tos, "archivos_por_to_iguales": iguales, "archivos_por_to_distintos": distintos,
                  "agregados": ag}, ensure_ascii=False))
