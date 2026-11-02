"""las_coincidencias_y_la_norma_v2_mesa.py — Mesa, §395 (01/11/2026): la v2 de `las_15_coincidencias_y_la_norma_mesa.py` (§393),
para todos los criterios de evaluación que aparecen enteros en el grafo evaluado, sin piso de largo (la lista de
`todos_los_criterios_en_el_grafo_mesa.py`). Cambia tres cosas, y nada del método:
  - los criterios salen de esa lista, no de una fija de 15;
  - en los campos del grafo mira todos los textos, también los de menos de 30 caracteres (la v1 los salteaba: un criterio de 4
    palabras puede estar en un label);
  - cada fila lleva además si el criterio también es una cita del gold, de la misma lista.
Lo demás, igual: a. los campos del grafo; b. si está entero en una unidad de la E0 y la secuencia de palabras seguidas más larga con
una sola unidad; c. la clase, con el umbral de 0,80 fijado en la §393. Controla que las 15 de la §393 den, campo por campo, la misma
fila que en `las_15_coincidencias.json`. Nunca imprime ni escribe un texto: ids, campos, sha256 cortos, cuentas y fracciones. USD 0.
  python3 -I -B las_coincidencias_y_la_norma_v2_mesa.py <repo> <fuera_del_repo> <todos_los_criterios_en_el_grafo.json>
      <las_15_coincidencias.json> <salida.json>
"""
import collections
import gzip
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

R, F, LISTA, L15, OUT = (Path(x).resolve() for x in sys.argv[1:6])
C = "c190505c3ac63bf9d7cf51b94e3be04358cd7832"
B63 = F / ("hoja_de_ruta_tanda1_mesa/decisiones_317_mesa/entrada/"
           "salida/preguntas_96_B63.json")
B64 = "data/experiment/banco_mcp/b64/preguntas/aprobadas_B64.json"
U6 = "data/experiment/exploracion/u6_fidelidad/criterios_u6.json"
GRAFO = "data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz"
E0 = "data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b/"
LISTA_J = json.loads(LISTA.read_text(encoding="utf-8"))["criterios_en_el_grafo"]
LAS_15 = {(x["fuente"], x["pregunta"], x["criterio"]) for x in LISTA_J}   # el nombre de la v1; ahora son todas
CITA = {(x["fuente"], x["pregunta"], x["criterio"]): x["es_cita_del_gold"] for x in LISTA_J}
UMBRAL = 0.80
W = re.compile(r"\w+")
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731


def git(*a):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(R), *a], capture_output=True, check=True).stdout


def toks(s):
    return W.findall(unicodedata.normalize("NFC", s).casefold())


crit = {}
b63 = B63.read_bytes()
assert sha(b63).startswith("a5993d5b")
for q in json.loads(b63)["preguntas"]:
    for i, c in enumerate(q.get("criterios", []), 1):
        crit[("B6.3", q["id"], i)] = c["criterio"] if isinstance(c, dict) else c
b64 = git("show", f"{C}:{B64}")
assert sha(b64).startswith("2ce2ac81")
for q in json.loads(b64)["preguntas"]:
    for i, c in enumerate(q.get("criterios", []), 1):
        crit[("B6.4", q["id"], i)] = c["criterio"] if isinstance(c, dict) else c
for q in json.loads(git("show", f"{C}:{U6}"))["preguntas"]:
    for i, c in enumerate((q.get("gold") or {}).get("criterios", []), 1):
        crit[("EV2 (U6)", q["id"], i)] = c["criterio"] if isinstance(c, dict) else c
assert LAS_15 <= set(crit), "FRENO: falta alguna de las 15"
T = {k: toks(crit[k]) for k in LAS_15}

# a. los campos del grafo
kg = json.loads(gzip.decompress(git("show", f"{C}:{GRAFO}")))


def textos_de(x, camino=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from textos_de(v, f"{camino}.{k}" if camino else k)
    elif isinstance(x, list):
        for v in x:
            yield from textos_de(v, camino + "[]")
    elif isinstance(x, str):
        yield camino, x


def contiene(t, c):
    n = len(c)
    return any(t[i:i + n] == c for i in range(len(t) - n + 1) if t[i] == c[0])


campos = {k: collections.Counter() for k in LAS_15}
elementos = {k: set() for k in LAS_15}
primeras = {k: T[k][0] for k in LAS_15}
for col in ("nodes", "edges"):
    for el in kg.get(col, []):
        for camino, s in textos_de(el):
            t = toks(s)
            ts = set(t)
            for k in LAS_15:
                if primeras[k] in ts and contiene(t, T[k]):
                    campos[k][f"{col}.{camino}"] += 1
                    elementos[k].add(sha(str(el.get("id")).encode())[:12])

# b. la E0: entero, y la secuencia de palabras seguidas más larga, por unidad
textos = set()


def rec(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("texto", "texto_propio", "text", "contenido", "titulo") and isinstance(v, str):
                textos.add(v)
            else:
                rec(v)
    elif isinstance(x, list):
        for v in x:
            rec(v)


for ln in git("ls-tree", "-r", "--name-only", C, "--", E0).decode().splitlines():
    if ln.endswith(".json"):
        rec(json.loads(git("show", f"{C}:{ln}")))
pos = {k: collections.defaultdict(list) for k in LAS_15}
for k in LAS_15:
    for i, w in enumerate(T[k]):
        pos[k][w].append(i)
mejor = {k: 0 for k in LAS_15}
entero = {k: 0 for k in LAS_15}
for s in textos:
    u = toks(s)
    us = set(u)
    for k in LAS_15:
        c, p = T[k], pos[k]
        if not (us & p.keys()):
            continue
        if len(u) >= len(c) and contiene(u, c):
            entero[k] += 1
        for j, w in enumerate(u):
            for i in p.get(w, ()):
                if i and j and u[j - 1] == c[i - 1]:
                    continue
                n = 0
                while i + n < len(c) and j + n < len(u) and c[i + n] == u[j + n]:
                    n += 1
                if n > mejor[k]:
                    mejor[k] = n

filas = []
for k in sorted(LAS_15):
    f, q, i = k
    n = len(T[k])
    fr = mejor[k] / n
    clase = "texto de la norma" if entero[k] else "casi texto de la norma" if fr >= UMBRAL else "redactado"
    filas.append({"fuente": f, "pregunta": q, "criterio": i, "sha256": sha(" ".join(crit[k].split()).encode())[:8], "palabras": n,
                  "campos": dict(sorted(campos[k].items())), "elementos": len(elementos[k]),
                  "entero_en_unidades_de_la_E0": entero[k], "secuencia_mas_larga_con_la_E0": mejor[k],
                  "fraccion": round(fr, 3), "clase": clase, "es_cita_del_gold": CITA[k]})
OUT.write_text(json.dumps({"umbral_casi": UMBRAL, "textos_de_la_E0": len(textos), "coincidencias": filas}, ensure_ascii=False,
                          indent=1) + "\n", encoding="utf-8")
print(f"textos distintos de la E0: {len(textos)}; umbral de «casi texto de la norma»: {UMBRAL}")
for r in filas:
    print(f"{r['fuente']} | {r['pregunta']} | criterio {r['criterio']} | {r['sha256']} | {r['palabras']} palabras | campos {r['campos']} "
          f"| {r['elementos']} elementos | entero en {r['entero_en_unidades_de_la_E0']} unidades | secuencia más larga con la E0 "
          f"{r['secuencia_mas_larga_con_la_E0']} ({r['fraccion']:.0%}) | {r['clase']} | cita del gold: {r['es_cita_del_gold']}")
print(f"por clase: {dict(collections.Counter(r['clase'] for r in filas))}")
v1 = {(r["fuente"], r["pregunta"], r["criterio"]): r for r in json.loads(L15.read_text(encoding="utf-8"))["coincidencias"]}
fila = {(x["fuente"], x["pregunta"], x["criterio"]): {c: v for c, v in x.items() if c != "es_cita_del_gold"} for x in filas}
print(f"por fuente y clase: {dict(sorted(collections.Counter((r['fuente'], r['clase']) for r in filas).items()))}")
print(f"también citas del gold: {sum(r['es_cita_del_gold'] for r in filas)}; las 15 de la §393, con la misma fila: "
      f"{sum(fila.get(k) == r for k, r in v1.items())} de {len(v1)}")
