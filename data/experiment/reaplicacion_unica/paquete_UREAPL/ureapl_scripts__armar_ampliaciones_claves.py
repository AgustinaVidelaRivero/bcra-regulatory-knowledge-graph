"""U-REAPL, las claves del catálogo: arma la lista de ampliaciones del catálogo de resolución (formato
`ampliaciones_resolucion_r2/1` de `reresolucion_catalogo/reresolver_catalogo.py`) desde los veredictos de la segunda pasada
y el material de las claves. USD 0, sin API.

  - `nuevo:<id>|padre:<p>` → `alta_id` con ese id y ese padre; `label`, la forma de la clave más frecuente en el material
    (la que más relaciones del registro reúne: la suma de `filas_del_registro` de las filas del material con esa mención;
    si empatan, la primera en orden alfabético), sin su artículo inicial y con la primera letra en mayúscula; `alias`
    vacío y `definicion` nula;
  - `alias:<id>` → `alta_alias` de ese id, con esa misma forma (sin artículo y con la mayúscula) como alias;
  - `no entra` → nada.
El artículo inicial se saca con la regla con que E4 lo saca de la mención antes de comparar (`r1_e4.RE_ARTICULO_INICIAL`;
r1_e4.py:344: «la mención se copia con artículos; el catálogo no los lleva»): con él, el label o el alias no iguala a
ninguna de sus menciones. Es un apartamiento del despacho, que pedía la forma tal cual, decidido por la autora;
`--variante literal` arma la lista del despacho, solo para el registro de las dos variantes.
La `evidencia` de cada una: las filas del registro sellado (`no_mapeados_sujetos.jsonl` del acumulado sin cola) en
cuarentena, con la mención verificada (exacta o tokens) y esa clave, solo de las unidades (chunk_id) que trae el material
para esa clave. La clave de una mención es la del material: `_norm_sing(_sin_parentesis(mención sin artículo inicial))`
de r1_e4 (el script controla que reproduce la clave de todas las filas y formas del material). Las altas van en un orden
en que cada padre y cada id de un alias existe antes de usarse (el de los veredictos, con los que dependen de un id nuevo
después de su alta).

Frena (código 1) si un sha256 de entrada no es el sellado, si la clave no se reproduce, si un veredicto no tiene forma
conocida, si una ampliación queda sin evidencia o si el orden no se puede armar. La consola lleva solo cuentas y
sha256: ninguna clave, forma ni texto.

Uso, desde la raíz de la copia del repo:
  PYTHONDONTWRITEBYTECODE=1 <repo>/.venv/bin/python -B <este script> --veredictos V --material M --registro R --salida A.json
      [--variante sin_articulo|literal]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "data/experiment/tanda0/code")
import ensamblar_tanda0 as ENS  # noqa: E402

E4 = ENS.E4
SHA = {"veredictos": "e1be992688a5614a022c37760559ebb11cc7f68a26f5ca1edd1943614593a09b",
       "material": "5fcca72a24897233fae9c42eb038f4cb7818ce2522b22bca38afb871fba33172",
       "registro": "25ba55c88ed9c1e3f11838e023bb48d2793dd895b4749f84032293c814838352",
       "catalogo_request": "c3ad15811c7ea5fa2d0f6cbd56dc775c38dcffd0ae8874c22f5f45c1e82d3a83"}
CATALOGO_REQUEST = Path("data/experiment/catalogo_unico/catalogo_sujetos_r2.json")
APROBACION = "lectura de la autora, segunda pasada, sellada el 23/10/2026 a las 11:27:46 (claves_marcada.csv, 973654f0…)"
FUENTE_EV = ("no_mapeados_sujetos.jsonl de data/experiment/tanda_final/t3/acumulado/ens_128_r2b_sincola/r2 "
             "(sellado, 25ba55c8…): cuarentena, mención verificada, con la clave")
VERIFICADAS = ("exacta", "tokens")
RE_NUEVO = re.compile(r"nuevo:(Sujeto_[A-Za-z0-9_]+)\|padre:(Sujeto_[A-Za-z0-9_]+)")
RE_ALIAS = re.compile(r"alias:(Sujeto_[A-Za-z0-9_]+)")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def clave(m: str) -> str:
    return E4._norm_sing(E4._sin_parentesis(E4.RE_ARTICULO_INICIAL.sub("", m or "")))


def freno(msg: str) -> None:
    print("FRENO:", msg)
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--veredictos", type=Path, required=True)
    ap.add_argument("--material", type=Path, required=True)
    ap.add_argument("--registro", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--variante", choices=("sin_articulo", "literal"), default="sin_articulo")
    a = ap.parse_args()
    datos = {"veredictos": a.veredictos.read_bytes(), "material": a.material.read_bytes(), "registro": a.registro.read_bytes(),
             "catalogo_request": CATALOGO_REQUEST.read_bytes()}
    for k, b in datos.items():
        if sha_bytes(b) != SHA[k]:
            freno(f"el sha256 de {k} no es el sellado")
    ver = json.loads(datos["veredictos"])
    if ver.get("material_sha256") != SHA["material"]:
        freno("los veredictos no son de este material")
    mat = [json.loads(x) for x in datos["material"].decode("utf-8").splitlines() if x.strip()]
    reg = [json.loads(x) for x in datos["registro"].decode("utf-8").splitlines() if x.strip()]
    cat = json.loads(datos["catalogo_request"])
    ids_request = {s["id"] for s in cat["sujetos"]}

    por_clave = {m["clave"]: m for m in mat}
    if len(por_clave) != len(mat) or [m["clave"] for m in mat] != [v["clave"] for v in ver["veredictos"]]:
        freno("las claves del material y de los veredictos no son las mismas, en el mismo orden")
    n_formas = sum(len(m["formas"]) for m in mat)
    n_filas = sum(len(m["filas"]) for m in mat)
    if not all(clave(f) == m["clave"] for m in mat for f in m["formas"]) or \
            not all(clave(r["mencion"]) == m["clave"] for m in mat for r in m["filas"]):
        freno("la función de la clave no reproduce la clave del material")
    if not all(r["mencion"] in m["formas"] for m in mat for r in m["filas"]):
        freno("una mención del material no está entre las formas de su clave")

    # el registro sellado, por clave: cuarentena con la mención verificada
    reg_por_clave = defaultdict(list)
    for r in reg:
        if r["estado"] == "cuarentena" and r["mencion_verificada"] in VERIFICADAS:
            reg_por_clave[clave(r["mencion"])].append(r)

    ampl, cuentas, por_k = [], Counter(), {}
    empates = 0
    for k, v in enumerate(ver["veredictos"], 1):
        m = por_clave[v["clave"]]
        cod = v["codigo"]
        if cod == "no entra":
            cuentas["no entra"] += 1
            continue
        peso = Counter()
        for r in m["filas"]:
            peso[r["mencion"]] += r["filas_del_registro"]
        maximo = max(peso[f] for f in m["formas"])
        mejores = sorted(f for f in m["formas"] if peso[f] == maximo)
        empates += len(mejores) > 1
        forma = mejores[0]
        cuentas["formas_elegidas_con_articulo_inicial"] += bool(E4.RE_ARTICULO_INICIAL.match(forma))
        cuentas["formas_elegidas_con_parentesis"] += "(" in forma
        if a.variante == "sin_articulo":
            forma = E4.RE_ARTICULO_INICIAL.sub("", forma)
        texto = forma[:1].upper() + forma[1:]
        unidades = {r["chunk_id"] for r in m["filas"]}
        ev = sorted(({"to": r["to"], "chunk_id": r["chunk_id"], "indice_relacion": r["indice_relacion"],
                      "fuente": FUENTE_EV} for r in reg_por_clave.get(v["clave"], []) if r["chunk_id"] in unidades),
                    key=lambda e: (e["to"], e["chunk_id"], e["indice_relacion"]))
        if not ev:
            freno(f"veredicto {k}: sin evidencia en el registro sellado")
        if (mn := RE_NUEVO.fullmatch(cod)):
            item = {"operacion": "alta_id", "id": mn.group(1), "label": texto, "alias": [], "padre": mn.group(2),
                    "definicion": None, "evidencia": ev, "aprobacion": APROBACION}
            cuentas["alta_id"] += 1
        elif (ma := RE_ALIAS.fullmatch(cod)):
            item = {"operacion": "alta_alias", "id": ma.group(1), "alias": texto, "evidencia": ev, "aprobacion": APROBACION}
            cuentas["alta_alias"] += 1
        else:
            freno(f"veredicto {k}: código sin forma conocida")
        cuentas["filas_de_evidencia"] += len(ev)
        por_k[k] = item
        ampl.append((k, item))

    # orden: el de los veredictos, con cada alta después de la del id nuevo que usa (su padre o el id del alias)
    nuevos = {it["id"]: k for k, it in ampl if it["operacion"] == "alta_id"}
    if len(nuevos) != cuentas["alta_id"]:
        freno("un id nuevo aparece en dos altas")
    hecho, orden, esperan, demoradas = set(ids_request), [], [], 0

    def usa(k: int) -> str:
        it = por_k[k]
        return it["padre"] if it["operacion"] == "alta_id" else it["id"]

    def poner(k: int) -> None:
        orden.append(k)
        if por_k[k]["operacion"] == "alta_id":
            hecho.add(por_k[k]["id"])

    for k, _ in ampl:
        if usa(k) not in hecho:
            esperan.append(k)
            demoradas += 1
            continue
        poner(k)
        while (listas := [x for x in esperan if usa(x) in hecho]):
            esperan.remove(listas[0])
            poner(listas[0])
    if esperan:
        freno(f"{len(esperan)} altas usan un id que no existe en el catálogo ni en las altas")
    movidas = demoradas

    salida = {"formato": "ampliaciones_resolucion_r2/1", "catalogo_request_sha256": SHA["catalogo_request"],
              "ampliaciones": [por_k[k] for k in orden]}
    texto = json.dumps(salida, ensure_ascii=False, indent=1) + "\n"
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(texto, encoding="utf-8")
    padres_nuevos = sum(1 for k in orden if por_k[k]["operacion"] == "alta_id" and por_k[k]["padre"] in nuevos)
    alias_de_nuevos = sum(1 for k in orden if por_k[k]["operacion"] == "alta_alias" and por_k[k]["id"] in nuevos)
    print(json.dumps({"veredictos": len(ver["veredictos"]), "formas_del_material": n_formas, "filas_del_material": n_filas,
                      **dict(cuentas), "claves_con_empate_de_formas": empates, "altas_con_padre_nuevo": padres_nuevos,
                      "alias_de_un_id_nuevo": alias_de_nuevos, "altas_que_esperan_a_su_id": movidas,
                      "ampliaciones": len(orden)}, ensure_ascii=False))
    print("sha256 de la lista:", sha_bytes(texto.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
