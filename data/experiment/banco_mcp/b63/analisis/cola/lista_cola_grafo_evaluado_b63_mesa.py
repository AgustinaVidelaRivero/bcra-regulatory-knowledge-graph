"""lista_cola_grafo_evaluado_b63_mesa.py — mesa, §329 (29/10/2026): la lista CANDIDATA de las unidades de la cola humana del grafo
evaluado de B6.3 (`KG_Acumulado_Tandas0y1yFinal_r2b_sincola`, `576c9725…`), para la cifra aparte del §8.2. No es una lista sellada: la
prepara la mesa para que la autora decida. Sigue el antecedente de A2.2
(`data/experiment/controles_a2_2/lista_cola_desarrollo_r2b_rs1_mesa.py`, §267): la cola son las unidades cuyo estado en su última
versión es `cola_humana*` en los `finales.jsonl` de las extracciones, aquí las
de las tres tandas (`reextraccion_v2/corpus_tanda0`, `corpus_tanda1` y `corpus_tanda_final`, `salida_r2b/<to>/finales.jsonl`). La
controla:
  · contra las marcas del grafo con la cola (`reaplicacion_unica/acumulado/ens_128_r2b/r2/kg.json.gz`, con su sha256 del sello del grafo
    evaluado): `cola_humana` y `cola_chunks` de cada nodo;
  · contra el grafo evaluado, sin la cola, que no lleva ningún nodo marcado;
  · los TOs de las fuentes son los del grafo.
Solo lectura del repo, por `git show HEAD`. Imprime solo cuentas y sí o no. USD 0.
  python3 -I -B lista_cola_grafo_evaluado_b63_mesa.py <repo> <salida.json, que no existe>
"""
import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO, OUT = sys.argv[1], Path(sys.argv[2])
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
show = lambda p: subprocess.run(["git", "--no-optional-locks", "-C", REPO, "show", f"HEAD:{p}"],  # noqa: E731
                                capture_output=True, check=True).stdout
ls = lambda p: subprocess.run(["git", "--no-optional-locks", "-C", REPO, "ls-files", "--", p],  # noqa: E731
                              capture_output=True, check=True, text=True).stdout.split()
res = []


def c(n, ok, det=""):
    res.append(bool(ok))
    print("OK " if ok else "MAL", n, det)


sello = json.loads(show("data/experiment/reaplicacion_unica/sello_grafo_evaluado.json"))["grafos"]
gr = {}
for k in ("ens_128_r2b", "ens_128_r2b_sincola"):
    gz = show(sello[k]["directorio"] + "kg.json.gz")
    kgb = gzip.decompress(gz)
    c(f"{k}: el .gz y el kg.json dan su sha256 del sello", sha(gz) == sello[k]["gz_sha256"] and sha(kgb) == sello[k]["kg_json_sha256"])
    gr[k] = json.loads(kgb)
tos_grafo = sorted({p["to"] for n in gr["ens_128_r2b"]["nodes"] for p in n.get("provenances") or [] if p.get("to")})
fuentes, ult = {}, {}
for t in ("corpus_tanda0", "corpus_tanda1", "corpus_tanda_final"):
    for p in ls(f"data/experiment/reextraccion_v2/{t}/salida_r2b"):
        if not p.endswith("/finales.jsonl") or "NO_ABRIR_" in p or "_SOLO_MESA" in p:
            continue
        b = show(p)
        fuentes[p] = sha(b)
        for linea in b.decode("utf-8").splitlines():
            if linea.strip():
                o = json.loads(linea)
                ult[o["chunk_id"]] = o["estado"]
tos_f = sorted({k.split("::")[0] for k in ult})
c("los TOs de las fuentes son los 128 del grafo", tos_f == tos_grafo and len(tos_grafo) == 128, f"{len(tos_f)} y {len(tos_grafo)}")
cola = sorted(k for k, v in ult.items() if str(v).startswith("cola_humana"))
marcadas = set()
for n in gr["ens_128_r2b"]["nodes"]:
    pr = n.get("properties") or {}
    if str(pr.get("cola_humana")).lower() == "true":
        marcadas.update(pr.get("cola_chunks") or [])
c("las unidades marcadas en el grafo con la cola son las de la regla", marcadas == set(cola),
  f"marcadas {len(marcadas)}, de la regla {len(cola)}, solo marcadas {len(marcadas - set(cola))}, "
  f"solo de la regla {len(set(cola) - marcadas)}")
c("el grafo evaluado, sin la cola, no lleva ningún nodo marcado",
  not any(str((n.get("properties") or {}).get("cola_humana")).lower() == "true" for n in gr["ens_128_r2b_sincola"]["nodes"]))
tanda_de = {f.split("/")[-2]: f.split("/")[3].removeprefix("corpus_") for f in fuentes}   # .../corpus_<t>/salida_r2b/<to>/finales.jsonl
c("cada TO está en una sola tanda", len(tanda_de) == len(fuentes) == 128)
por_tanda = Counter(tanda_de[k.split("::")[0]] for k in cola)
texto = "".join(x + "\n" for x in cola)
salida = {"estado": "CANDIDATA, PREPARADA por la mesa (§329) y NO SELLADA: la decide la autora",
          "grafo": "KG_Acumulado_Tandas0y1yFinal_r2b_sincola", "kg_sha256": sello["ens_128_r2b_sincola"]["kg_json_sha256"],
          "control": {"grafo_con_la_cola": sello["ens_128_r2b"]["directorio"] + "kg.json.gz",
                      "kg_sha256": sello["ens_128_r2b"]["kg_json_sha256"]},
          "regla": ("estado cola_humana* como última versión en los finales.jsonl de las tres tandas, como en A2.2 "
                    "(data/experiment/controles_a2_2/lista_cola_desarrollo_r2b_rs1_mesa.py)"),
          "fuentes": dict(sorted(fuentes.items())), "n": len(cola), "por_tanda": dict(sorted(por_tanda.items())),
          "por_estado": dict(sorted(Counter(ult[x] for x in cola).items())), "ids": cola,
          "sha256_de_la_lista": sha(texto.encode()), "forma_de_la_lista": "los ids ordenados, uno por renglón, con salto final"}
OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("n", len(cola), "| por tanda", dict(sorted(por_tanda.items())), "| fuentes", len(fuentes), "| sha256 del archivo",
      sha(OUT.read_bytes()))
print(f"controles: {sum(res)} de {len(res)}")
sys.exit(0 if all(res) else 1)
