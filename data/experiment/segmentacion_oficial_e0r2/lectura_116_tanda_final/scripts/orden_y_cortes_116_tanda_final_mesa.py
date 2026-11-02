"""Mesa, §119: el orden y los cortes de la lectura corta escalonada de 1.16 en la tanda final (decisión 1 de la autora del 16/10/2026,
sobre la regla de la §118). USD 0, sin API. No lee ninguna ficha ni marca nada.

Uso: python -I -B <este> --cruce <cruce_candidatos_116_con_lecturas.json> --sha-cruce <sha256> --tanda-final <tanda_final_S2c.json>
       --detector <detector_116_S2b.json> --manifiesto-e0 <manifest_salida_e0_152_S0-6b.json> --out <json>

La regla (historia_de_1_16_y_lectura_corta_mesa.md, §4, aprobada):
- población: los documentos de la tanda final con algún candidato del censo de 1.16 sin leer. Leído = leído en S1-bis o S1-ter con el
  mismo texto que hoy (el cruce de la §118);
- orden: random.Random("U-SEG-OFICIAL:1_16:tanda_final:orden").sample(sorted(docs), len(docs));
- primer corte de cada documento: random.Random(f"U-SEG-OFICIAL:1_16:tanda_final:{doc}").choice(sorted(sin_leer));
- segundos cortes, después de los primeros: en los documentos con más candidatos sin leer (a igual cantidad, en el orden de la semilla),
  hasta el tope de 30 cortes en total;
- el segundo corte de un documento (la regla aprobada no lo escribía; lo fija la mesa antes de sellar):
  random.Random(f"U-SEG-OFICIAL:1_16:tanda_final:{doc}:2").choice(sorted(sin_leer sin el primero));
- tramo 1: los primeros 10 cortes; tramo 2: los demás."""
import argparse, hashlib, json, sys, random, platform
ap = argparse.ArgumentParser()
for a in ("--cruce", "--sha-cruce", "--tanda-final", "--detector", "--manifiesto-e0", "--out"):
    ap.add_argument(a, required=True)
A = ap.parse_args()
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
if sha(A.cruce) != A.sha_cruce: sys.exit("FRENO: el cruce no da su sha256")
cruce = json.load(open(A.cruce, encoding="utf-8"))
tf = json.load(open(A.tanda_final, encoding="utf-8")); det = json.load(open(A.detector, encoding="utf-8"))
upt = json.load(open(A.manifiesto_e0, encoding="utf-8"))["unidades_por_to"]
censo = [x["id"] for x in tf["hallazgo_1_16"]["censo"]["lista"]]
filas = {f["id"]: f for f in cruce["candidatos"]["tanda_final"]}
if sorted(filas) != sorted(censo) or len(censo) != 51: sys.exit("FRENO: el cruce no cubre los 51 del censo")
orig = {c["id"] for c in det["candidatos"] if c["criterio"] in ("ambos", "original")}
if not set(censo) <= orig: sys.exit("FRENO: un candidato del censo no está en el criterio original del detector")
leido = {i for i, f in filas.items() if any(l["texto_igual_al_de_hoy"] for l in f["lecturas"])}
sin_leer = {}
for i in censo:
    if i not in leido: sin_leer.setdefault(i.split("::")[0], []).append(i)
docs = sorted(sin_leer)
SEM = "U-SEG-OFICIAL:1_16:tanda_final"
orden = random.Random(f"{SEM}:orden").sample(docs, len(docs))
primero = {d: random.Random(f"{SEM}:{d}").choice(sorted(sin_leer[d])) for d in docs}
cortes = [{"doc": d, "id": primero[d], "corte": 1} for d in orden]
pos = {d: k for k, d in enumerate(orden)}
segundos = sorted((d for d in docs if len(sin_leer[d]) >= 2), key=lambda d: (-len(sin_leer[d]), pos[d]))
for d in segundos:
    if len(cortes) >= 30: break
    resto = sorted(set(sin_leer[d]) - {primero[d]})
    cortes.append({"doc": d, "id": random.Random(f"{SEM}:{d}:2").choice(resto), "corte": 2})
for k, c in enumerate(cortes, 1):
    c["orden"] = k; c["tramo"] = 1 if k <= 10 else 2; c["unidades_del_documento"] = upt[c["doc"]]
out = {"semilla": SEM, "python": platform.python_version(),
       "fuentes": {"cruce": A.sha_cruce, "tanda_final": sha(A.tanda_final), "detector": sha(A.detector), "manifiesto_e0": sha(A.manifiesto_e0)},
       "poblacion": {"documentos": len(docs), "candidatos_sin_leer": sum(len(v) for v in sin_leer.values()),
                     "unidades": sum(upt[d] for d in docs), "leidos_con_el_mismo_texto": len(leido)},
       "cortes": cortes, "tope": 30, "cortes_posibles": len(docs) + sum(1 for d in docs if len(sin_leer[d]) >= 2)}
json.dump(out, open(A.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"documentos": len(docs), "cortes": len(cortes), "segundos": sum(c["corte"] == 2 for c in cortes),
                  "docs_con_2_o_mas": len(segundos), "python": out["python"]}, ensure_ascii=False))
