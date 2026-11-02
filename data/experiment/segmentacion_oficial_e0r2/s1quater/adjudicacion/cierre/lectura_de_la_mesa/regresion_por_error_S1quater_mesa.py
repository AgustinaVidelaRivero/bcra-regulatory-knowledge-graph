"""U-SEG-OFICIAL, S1-quater: la regresión leída error por error (mesa, 15/10/2026, §100; USD 0). Lectura de la mesa sobre las salidas
selladas del cierre: no cambia ninguna salida ni entra en la cifra (la regresión no tiene cifra; diseño, §6).

Por cada error confirmado de S1-ter de la lista de regresión (`NO_ABRIR_regresion_S1quater.json`, `57b0436d…`), contado una sola vez
(la ficha E2-033 de S1-ter está dos veces, por la marca y por el cierre: `s1quater/sorteo/revision_y_decisiones_sorteo_S1quater_mesa.md`,
§3), mira sus unidades nuevas en la planilla adjudicada de la etapa 2 y en el registro de `aplicar`:
- un error por la marca o por la que sigue persiste si alguna unidad nueva tiene `marca` = `error` (se informa la clase);
- un error de herencia persiste si alguna unidad nueva tiene la herencia confirmada como error;
- un error sin ninguna unidad nueva (la corrección la sacó) no se lee: `persiste` = null;
- además se informan los otros errores confirmados en esas mismas fichas (marca, cierre o herencia), aunque no sean del tipo del origen.
Uso: python3 -I -B regresion_por_error_S1quater_mesa.py <salida del cierre> <carpeta con el orden y la regresión> <json nuevo>
Imprime solo cuentas y documentos; las unidades, en el JSON.
"""
import csv, json, sys
from collections import Counter
from pathlib import Path

D, E, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
if OUT.exists():
    sys.exit("FRENO: la salida ya existe")
r = json.load(open(E / "NO_ABRIR_regresion_S1quater.json", encoding="utf-8"))
o = json.load(open(E / "NO_ABRIR_orden_lectura_S1quater.json", encoding="utf-8"))
f2 = {x["id_opaco"]: x for x in o["etapa_2"]["fichas"]}
id2op = {x["id"]: op for op, x in f2.items()}
pl = {f["ficha"]: f for f in csv.DictReader(open(D / "aplicar/planilla_adjudicada_etapa_2_S1quater.tsv", encoding="utf-8", newline=""),
                                            delimiter="\t")}
reg = json.load(open(D / "aplicar/registro_aplicar_adjudicacion_S1quater.json", encoding="utf-8"))
cie = {c["ficha"]: c for c in reg["cierres_confirmados"]}
her = {h["ficha"] for h in reg["herencias_confirmadas"]}
assert len(f2) == len(pl) == len(r["ids"]) == 60 and set(id2op) == set(r["ids"])
errores = [e for e in r["errores_confirmados_S1ter"] if not (e["ficha"] == "E2-033" and e["por"] == "marca")]
assert len(errores) == 40, len(errores)
salida, usadas = [], set()
for e in errores:
    nuevas = sorted({u for v in e["unidades"] for u in r["unidades_nuevas_de"].get(v, [])})
    sin = [v for v in e["unidades"] if v in r["sin_unidad_nueva"]]
    ops = [id2op[u] for u in nuevas]
    usadas |= set(ops)
    fila_err = [(f2[op]["id"], pl[op]["clase"]) for op in ops if pl[op]["marca"] == "error"]
    her_err = [f2[op]["id"] for op in ops if op in her]
    cie_err = [(f2[op]["id"], cie[op]["clase_que_sigue"]) for op in ops if op in cie]
    dud = [f2[op]["id"] for op in ops if pl[op]["marca"] == "dudosa"]
    persiste = None if not nuevas else (bool(her_err) if e["por"] == "herencia" else bool(fila_err))   # None: sin unidad nueva, no se lee
    salida.append({"ficha_S1ter": e["ficha"], "por": e["por"], "clase_S1ter": e["clase"], "documento": e["unidades"][0].split("::")[0],
                   "unidades_viejas": e["unidades"], "sin_unidad_nueva": sin, "unidades_nuevas": nuevas,
                   "persiste": persiste, "marca_error_en_S1quater": fila_err, "herencia_confirmada_en_S1quater": her_err,
                   "cierre_confirmado_en_S1quater": cie_err, "dudosas": dud})
extra = sorted(set(f2) - usadas)
res = {"nota": "lectura de la mesa sobre las salidas selladas del cierre; la regresión no tiene cifra",
       "errores_S1ter_distintos": len(errores), "por_origen": dict(Counter(x["por"] for x in salida)),
       "persisten": dict(Counter(x["por"] for x in salida if x["persiste"])),
       "persisten_por_documento": dict(Counter(x["documento"] for x in salida if x["persiste"])),
       "no_persisten": dict(Counter(x["por"] for x in salida if x["persiste"] is False)),
       "sin_ninguna_unidad_nueva": [x["ficha_S1ter"] for x in salida if not x["unidades_nuevas"]],
       "fichas_de_la_regresion_fuera_de_los_40": [{"id": f2[op]["id"], "marca": pl[op]["marca"], "clase": pl[op]["clase"],
                                                  "cierre": op in cie, "herencia": op in her} for op in extra],
       "errores": salida}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k not in ("errores",)}, ensure_ascii=False))
for x in salida:
    if x["persiste"] or x["marca_error_en_S1quater"] or x["herencia_confirmada_en_S1quater"] or x["cierre_confirmado_en_S1quater"]:
        print(x["ficha_S1ter"], x["por"], x["clase_S1ter"], x["documento"], "persiste" if x["persiste"] else "no persiste",
              "| fila:", x["marca_error_en_S1quater"], "| herencia:", x["herencia_confirmada_en_S1quater"], "| cierre:", x["cierre_confirmado_en_S1quater"])
