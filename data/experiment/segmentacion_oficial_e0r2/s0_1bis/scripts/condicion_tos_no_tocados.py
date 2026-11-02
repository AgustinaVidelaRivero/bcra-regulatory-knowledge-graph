"""S0-1 bis, condición 2: los TOs que las reglas nuevas no tocan salen byte a byte iguales a la corrida final de S0-1.
Compara dos salidas de E0 de los 152 TOs: los archivos por TO (`<tipo>_<to>.json`) y, en cada archivo agregado (un
dict por TO), la entrada de cada TO. Lista los TOs con alguna diferencia y controla que estén entre los declarados.
Solo lectura. Uso: python -B condicion_tos_no_tocados.py <base> <nueva> <tos declarados, coma> <salida.json>"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

base, nueva, declarados, sal = Path(sys.argv[1]), Path(sys.argv[2]), set(sys.argv[3].split(",")), Path(sys.argv[4])
AGREGADOS = ("divergencias_indice_cuerpo.json", "conteos.json", "cobertura.json", "correcciones.json",
             "sub_chunking.json", "encabezados_conservados.json", "ids_desambiguados.json")
TIPOS = ("chunks", "estructura", "indice", "pies", "tablas")
por_to_b = sorted(p.name for t in TIPOS for p in base.glob(f"{t}_*.json"))
por_to_n = sorted(p.name for t in TIPOS for p in nueva.glob(f"{t}_*.json"))
assert por_to_b == por_to_n, "conjuntos de archivos por TO distintos"
tos = sorted({n.split("_", 1)[1][:-5] for n in por_to_b if n.startswith("chunks_")})
distintos_por_to: dict = {}
for n in por_to_b:
    if (base / n).read_bytes() != (nueva / n).read_bytes():
        tipo, to = n.split("_", 1)[0], n.split("_", 1)[1][:-5]
        distintos_por_to.setdefault(to, []).append(tipo)
distintos_agregados: dict = {}
for a in AGREGADOS:
    db = json.loads((base / a).read_text(encoding="utf-8")) if (base / a).exists() else {}
    dn = json.loads((nueva / a).read_text(encoding="utf-8")) if (nueva / a).exists() else {}
    for to in sorted(set(db) | set(dn)):
        if json.dumps(db.get(to), ensure_ascii=False, sort_keys=False) != json.dumps(dn.get(to), ensure_ascii=False,
                                                                                    sort_keys=False):
            distintos_agregados.setdefault(to, []).append(a)
tocados = sorted(set(distintos_por_to) | set(distintos_agregados))
version_igual = (base / "version_e0.json").read_bytes() == (nueva / "version_e0.json").read_bytes()
out = OrderedDict([("base", base.name), ("nueva", nueva.name), ("tos", len(tos)), ("version_e0_igual", version_igual),
                   ("archivos_por_to", len(por_to_b)), ("tos_con_diferencias", tocados),
                   ("fuera_de_los_declarados", sorted(set(tocados) - declarados)),
                   ("declarados_sin_diferencias", sorted(declarados - set(tocados))),
                   ("tos_iguales_byte_a_byte", len(tos) - len(tocados)),
                   ("por_to", {t: distintos_por_to.get(t, []) for t in tocados}),
                   ("agregados", {t: distintos_agregados.get(t, []) for t in tocados})])
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
