"""todos_los_criterios_en_el_grafo_mesa.py — Mesa, §395 (01/11/2026): todos los criterios de evaluación de B6.3, B6.4 y EV2 (U6) que
aparecen enteros en algún texto del grafo evaluado, palabra por palabra (`\\w+`, NFC, en minúsculas), sin el filtro de largo de la §392
(40 caracteres y 6 palabras) y sean o no también una cita del gold. De cada uno que aparece:
  - su fuente, el id de su pregunta, su número de criterio y el sha256 corto de su forma normalizada por espacios (ids, no texto);
  - sus palabras y sus caracteres, y si pasaba el filtro de la §392;
  - si también es una cita del gold, que la regla de la fuga cuenta como cita: si sus palabras son, enteras, las de alguna cita
    (`cita_textual` de B6.3, B6.4 y U6, y lo que la regla de claves de la §392 toma como cita en los 4.653 archivos gold de `C`), y si
    son las de la cita de su propio criterio;
  - si está entre los 15 de la §392 (`las_15_coincidencias.json` de la §393);
  - en cuántos textos y elementos del grafo aparece, y en qué campos.
Las fuentes: las preguntas de B6.3 (`preguntas_96_B63.json`, `a5993d5b…`, del paquete de la mesa), las aprobadas de B6.4 y los
criterios de U6 de `C`; el grafo (`kg.json.gz`) de `C`. Nunca imprime ni escribe un texto: ids, sha256 cortos, campos y cuentas.
Escribe la lista de los que aparecen en <salida.json>. USD 0.
  python3 -I -B todos_los_criterios_en_el_grafo_mesa.py <repo> <fuera_del_repo> <las_15_coincidencias.json> <salida.json>
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

R, F, L15, OUT = (Path(x).resolve() for x in sys.argv[1:5])
C = "c190505c3ac63bf9d7cf51b94e3be04358cd7832"
B63 = F / ("hoja_de_ruta_tanda1_mesa/decisiones_317_mesa/entrada/"
           "salida/preguntas_96_B63.json")
B64 = "data/experiment/banco_mcp/b64/preguntas/aprobadas_B64.json"
U6 = "data/experiment/exploracion/u6_fidelidad/criterios_u6.json"
GRAFO = "data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz"
W = re.compile(r"\w+")
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731


def p(*x):
    print(*x, flush=True)


def git(*a, entrada=None):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(R), *a], capture_output=True, check=True, input=entrada).stdout


def pal(s):
    return tuple(W.findall(unicodedata.normalize("NFC", s).casefold()))


def norm(s):
    return " ".join(s.split())


crit = []      # (fuente, id de la pregunta, número, texto del criterio, texto de su cita)
b63 = B63.read_bytes()
assert sha(b63).startswith("a5993d5b"), "FRENO: las preguntas de B6.3 no son las de la entrada"
for q in json.loads(b63)["preguntas"]:
    for i, c in enumerate(q.get("criterios", []), 1):
        crit.append(("B6.3", q["id"], i, c["criterio"], c.get("cita_textual") or ""))
b64 = git("show", f"{C}:{B64}")
assert sha(b64).startswith("2ce2ac81"), "FRENO: las aprobadas de B6.4 de C no son las de la entrada"
for q in json.loads(b64)["preguntas"]:
    for i, c in enumerate(q.get("criterios", []), 1):
        crit.append(("B6.4", q["id"], i, c["criterio"], c.get("cita_textual") or ""))
for q in json.loads(git("show", f"{C}:{U6}"))["preguntas"]:
    for i, c in enumerate((q.get("gold") or {}).get("criterios", []), 1):
        crit.append(("EV2 (U6)", q["id"], i, c["criterio"], c.get("cita_textual") or ""))
filtro = lambda t: len(norm(t)) >= 40 and len(W.findall(t)) >= 6  # noqa: E731
p(f"criterios: {len(crit)} (por fuente: {dict(collections.Counter(c[0] for c in crit))}); pasan el filtro de la §392 (40 caracteres y "
  f"6 palabras): {sum(filtro(c[3]) for c in crit)}; no lo pasan: {dict(collections.Counter(c[0] for c in crit if not filtro(c[3])))}")

# --- las citas del gold, por sus palabras enteras
citas = collections.defaultdict(set)


def tipo_de(k):
    k = k.lower()
    if "pregunt" in k or "question" in k or k in ("enunciado", "query", "consulta"):
        return "pregunta"
    if "criteri" in k or "rubric" in k or any(x in k for x in ("respuesta_esperada", "expected_answer", "gold_answer",
                                                              "respuesta_correcta")):
        return "criterio"
    if "cita" in k or "quote" in k:
        return "cita"
    return None


def recoger(x, fuente, tipo=None):
    if isinstance(x, dict):
        for k, v in x.items():
            recoger(v, fuente, tipo_de(str(k)) or (tipo if str(k).lower() in ("texto", "text", "contenido", "valor") else None))
    elif isinstance(x, list):
        for v in x:
            recoger(v, fuente, tipo)
    elif isinstance(x, str) and tipo == "cita":
        citas[pal(x)].add(fuente)


for f, q, i, t, ct in crit:
    if ct:
        citas[pal(ct)].add(f"cita_textual de {f}")
rutas_gold = [r for r in (F / "publicacion_minima/t2/rutas_gold_C.txt").read_text(encoding="utf-8").splitlines() if r]
arbol = {}
for ln in git("ls-tree", "-r", "-z", C, "--", *sorted({str(Path(r).parent) for r in rutas_gold})).decode().split("\0"):
    if ln:
        meta, ruta = ln.split("\t", 1)
        arbol[ruta] = meta.split()[2]
for k in range(0, len(rutas_gold), 400):
    lote = rutas_gold[k:k + 400]
    crudo, pos = git("cat-file", "--batch", entrada="\n".join(arbol[r] for r in lote).encode() + b"\n"), 0
    for r in lote:
        fin = crudo.index(b"\n", pos)
        n = int(crudo[pos:fin].split()[2])
        t = crudo[fin + 1:fin + 1 + n].decode("utf-8", "replace")
        pos = fin + 1 + n + 1
        try:
            recoger(json.loads(t), "gold de C")
        except json.JSONDecodeError:
            for ln in t.splitlines():
                try:
                    recoger(json.loads(ln), "gold de C")
                except json.JSONDecodeError:
                    continue
p(f"citas del gold, distintas por sus palabras: {len(citas)}")

# --- el grafo, texto por texto
toks = [pal(c[3]) for c in crit]
por_primera = collections.defaultdict(list)
for j, t in enumerate(toks):
    if t:
        por_primera[t[0]].append(j)
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


hall = collections.defaultdict(list)
for col in ("nodes", "edges"):
    for el in kg.get(col, []):
        for camino, s in textos_de(el):
            t = pal(s)
            vistos = set()
            for i, w in enumerate(t):
                for j in por_primera.get(w, ()):
                    if j not in vistos and t[i:i + len(toks[j])] == toks[j]:
                        vistos.add(j)
                        hall[j].append((f"{col}.{camino}", sha(str(el.get("id")).encode())[:12]))
de_15 = {(c["pregunta"], c["criterio"]) for c in json.loads(L15.read_text(encoding="utf-8"))["coincidencias"]}
lista = []
por_largo = collections.Counter()
for j in sorted(hall, key=lambda j: (crit[j][0], crit[j][1], crit[j][2])):
    f, q, i, t, ct = crit[j]
    if len(toks[j]) < 6:
        por_largo[len(toks[j])] += 1
    lista.append({"fuente": f, "pregunta": q, "criterio": i, "sha256": sha(norm(t).encode())[:8], "palabras": len(toks[j]),
                  "caracteres": len(norm(t)), "pasa_el_filtro_de_la_392": filtro(t), "es_cita_del_gold": bool(citas.get(toks[j])),
                  "de_que_citas": sorted(citas.get(toks[j], ())), "es_su_propia_cita": bool(ct) and pal(ct) == toks[j],
                  "entre_las_15": (q, i) in de_15, "textos_del_grafo": len(hall[j]), "elementos": len({e for _, e in hall[j]}),
                  "campos": dict(sorted(collections.Counter(c for c, _ in hall[j]).items()))})
p(f"criterios enteros en algún texto del grafo: {len(lista)}; de menos de 6 palabras, por largo: {dict(sorted(por_largo.items()))}")
p(f"   de 6 palabras o más: {sum(x['palabras'] >= 6 for x in lista)}; de ellos, entre los 15: "
  f"{sum(x['entre_las_15'] for x in lista if x['palabras'] >= 6)}; también citas del gold: "
  f"{sum(x['es_cita_del_gold'] for x in lista if x['palabras'] >= 6)}")
for x in lista:
    if x["palabras"] >= 6 and not x["entre_las_15"] or x["es_cita_del_gold"]:
        p(f"   {x['fuente']} | {x['pregunta']} | criterio {x['criterio']} | {x['sha256']} | {x['palabras']} palabras, {x['caracteres']} "
          f"caracteres | pasa el filtro de la §392: {x['pasa_el_filtro_de_la_392']} | cita del gold: {x['es_cita_del_gold']} "
          f"{x['de_que_citas']} | su propia cita: {x['es_su_propia_cita']} | entre los 15: {x['entre_las_15']} | "
          f"{x['textos_del_grafo']} textos de {x['elementos']} elementos | {x['campos']}")
p(f"los 15 de la §392, todos en esta búsqueda: {de_15 <= {(x['pregunta'], x['criterio']) for x in lista}}")
OUT.write_text(json.dumps({"criterios_en_el_grafo": lista}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
