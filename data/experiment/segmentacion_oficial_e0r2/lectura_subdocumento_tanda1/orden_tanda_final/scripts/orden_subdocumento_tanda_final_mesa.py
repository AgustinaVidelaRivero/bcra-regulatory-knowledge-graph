"""Mesa, §119: el orden de la lectura de los límites de sub-documento de la tanda final, condicional: se lee solo si los 14 de la tanda 1
confirman el rasgo (decisión 1 de la autora del 16/10/2026, §118). La regla es la de la decisión 1 de la §117, con el tope de 30 por
rasgo (decisión 2 de la §119). USD 0, sin API. No lee nada ni marca nada.

Uso: python -I -B <este> --censo <censo_sd_152_S2b.json> --tanda-final <tanda_final_S2c.json> --manifiesto-e0 <manifest E0 S0-6b> --out <json>

- población: los límites que detecta limites_subdocumento en los documentos de la tanda final que no están en la lista de la regla;
- orden de los documentos: random.Random("U-SEG-OFICIAL:subdocumento:tanda_final:orden").sample(sorted(docs), len(docs));
- primer corte de cada documento (un límite): random.Random(f"U-SEG-OFICIAL:subdocumento:tanda_final:{doc}").choice(límites ordenados
  por página y top);
- segundos cortes y siguientes: en los documentos con más límites sin leer (a igual cantidad, en el orden de la semilla), uno por
  documento por vuelta, con random.Random(f"U-SEG-OFICIAL:subdocumento:tanda_final:{doc}:{k}").choice(los que quedan), hasta 30."""
import argparse, hashlib, json, sys, random, platform
ap = argparse.ArgumentParser()
for a in ("--censo", "--tanda-final", "--manifiesto-e0", "--out"):
    ap.add_argument(a, required=True)
A = ap.parse_args()
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
censo = json.load(open(A.censo, encoding="utf-8"))
if hashlib.sha256(json.dumps(censo, sort_keys=True, ensure_ascii=False).encode()).hexdigest() != \
        "899db5d198d18d8cff53b3aca5f77e464ab6e61ce9e29d5a2c7dc46ca59acf13":
    sys.exit("FRENO: el censo no da su sha256 canónico")
tf = json.load(open(A.tanda_final, encoding="utf-8")); upt = json.load(open(A.manifiesto_e0, encoding="utf-8"))["unidades_por_to"]
final = set(tf["tanda_final"]["lista"]); regla = set(censo["lista"])
lim = {to: sorted(({"pagina": x["pagina"], "top": x["top"], "forma": x["forma"], "prefijo": x["prefijo"], "titulo": x["titulo"]}
                   for x in v), key=lambda y: (y["pagina"], y["top"]))
       for to, v in censo["por_to"].items() if to in final and to not in regla}
lim = {k: v for k, v in lim.items() if v}
esperado = tf["subdocumento"]["detecciones"]
if sum(len(v) for v in lim.values()) != esperado["limites"] or len(lim) != esperado["tos"]:
    sys.exit("FRENO: la población no da los límites y documentos de tanda_final_S2c.json")
SEM = "U-SEG-OFICIAL:subdocumento:tanda_final"
docs = sorted(lim); orden = random.Random(f"{SEM}:orden").sample(docs, len(docs)); pos = {d: k for k, d in enumerate(orden)}
resto = {d: list(lim[d]) for d in docs}; cortes = []; vuelta = 1
clave = lambda y: (y["pagina"], y["top"])
while len(cortes) < 30 and any(resto.values()):
    grupo = orden if vuelta == 1 else sorted((d for d in docs if resto[d]), key=lambda d: (-len(resto[d]), pos[d]))
    for d in grupo:
        if len(cortes) >= 30 or not resto[d]: continue
        sem = f"{SEM}:{d}" if vuelta == 1 else f"{SEM}:{d}:{vuelta}"
        x = random.Random(sem).choice(sorted(resto[d], key=clave)); resto[d].remove(x)
        cortes.append({"doc": d, "vuelta": vuelta, **x})
    vuelta += 1
for k, c in enumerate(cortes, 1): c["orden"] = k; c["unidades_del_documento"] = upt[c["doc"]]
out = {"semilla": SEM, "python": platform.python_version(), "condicional": "se lee solo si los 14 de la tanda 1 confirman el rasgo",
       "fuentes": {"censo_canonico": "899db5d1", "tanda_final": sha(A.tanda_final), "manifiesto_e0": sha(A.manifiesto_e0)},
       "poblacion": {"documentos": len(docs), "limites": sum(len(v) for v in lim.values()), "unidades": sum(upt[d] for d in docs)},
       "tope": 30, "cortes": cortes}
json.dump(out, open(A.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"documentos": len(docs), "limites": out["poblacion"]["limites"], "cortes": len(cortes),
                  "vueltas": max(c["vuelta"] for c in cortes), "python": out["python"]}, ensure_ascii=False))
