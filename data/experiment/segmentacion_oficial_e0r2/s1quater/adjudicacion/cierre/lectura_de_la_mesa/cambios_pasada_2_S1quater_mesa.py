"""U-SEG-OFICIAL, S1-quater: qué cambió la pasada 2 respecto de la pasada 1, por columna (mesa, 15/10/2026, §100; USD 0). Solo cuentas.
Uso: python3 -I -B cambios_pasada_2_S1quater_mesa.py <entradas> <json nuevo>"""
import json, sys
from collections import Counter
from pathlib import Path
E, OUT = Path(sys.argv[1]), Path(sys.argv[2])
if OUT.exists(): sys.exit("FRENO: la salida ya existe")
ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue", "subclase_que_sigue", "herencia", "nota")
def filas(p, n):
    t = p.read_text(encoding="utf-8")[:-1].split("\n"); cab = t[0].split("\t")
    return {r.split("\t")[0]: dict(zip(cab, r.split("\t")))  for r in t[1:]}
res = {}
for e in (1, 2):
    p1 = filas(E / f"pasada_1/adjudicacion_pasada_1_etapa_{e}.tsv", e)
    p2 = filas(E / f"pasada_2/adjudicacion_pasada_2_etapa_{e}.tsv", e)
    por_col = Counter(c for f, r in p2.items() for c in ADJ[1:] if r[c] != p1[f][c])
    solo_nota = sum(1 for f, r in p2.items() if [c for c in ADJ[1:] if r[c] != p1[f][c]] == ["nota"])
    marca = Counter(f"{p1[f]['marca']}->{r['marca']}" for f, r in p2.items() if r["marca"] != p1[f]["marca"])
    sin_tildes = sum(1 for f, r in p2.items() if r["nota"] != p1[f]["nota"] and r["nota"].startswith(p1[f]["nota"]))
    res[f"etapa_{e}"] = {"fichas_en_la_pasada_2": len(p2), "cambios_por_columna": dict(por_col), "solo_cambia_la_nota": solo_nota,
                         "cambios_de_marca": dict(marca), "nota_nueva_que_empieza_con_la_vieja": sin_tildes}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
