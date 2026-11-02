#!/usr/bin/env python3
"""controlar_juez_b64.py — El juez de la corrida de B6.4 y el que importa el análisis (la corrección del H-6). USD 0: no ejecuta ninguno de
los dos; los lee por su árbol sintáctico (ast).

La corrida usa b64/v1/juez_b63.py (H-4, `4fa09501…`), con su b64/v1/comun_b63.py (`631037e9…`). El análisis importa el juez_b63.py de
B6.3 de HEAD (b63/v2/b2, `266dd6f0…`, por analizar_b63.importar y analizar_b64.ESPERADO_CODIGO["juez_b63"]), con el comun_b63.py de esa
carpeta (`0100be8f…`). Este control:
  1. busca en el código del análisis lo que usa de juez_b63 (`JB.<nombre>`) y de comun_b63 (`K.<nombre>` y `JB.K.<nombre>`): los cuatro
     archivos sellados de B6.3 que se importan (analizar_b64.SELLADO, con su sha256) y los de B6.4 (analizar_b64.py,
     aplicar_lectura_tolerante_b64.py, armar_adjudicacion_b64.py y exactitud_de_cita_9_4_b64.py); las pruebas no cuentan;
  2. compara cada uno de esos nombres en las dos versiones de su módulo (ast.dump de su definición: una función, una clase, una
     asignación o un import), y lo que cada uno usa del mismo módulo, hasta cerrar;
  3. informa, aparte, todo lo de nivel de módulo que difiere entre las dos versiones (y si difiere el docstring), para ver qué toca el
     diff de H-4.
Escribe --salida (que no puede existir); imprime una línea por módulo y el sha256 de la salida. Sale con 0 si todo lo que usa el análisis
es igual, y con 10 (FRENO) si algo difiere.

  B64_CODIGO_B63=<b63/analisis/codigo de una copia de HEAD> python3 -I -B controlar_juez_b64.py --juez-head <b63/v2/b2/juez_b63.py>
      --comun-head <b63/v2/b2/comun_b63.py> --juez-corrida <b64/v1/juez_b63.py> --comun-corrida <b64/v1/comun_b63.py> --salida <json>
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import analizar_b64 as B  # noqa: E402  (solo import: SELLADO y CODIGO_B63)

SHA = {"juez_head": "266dd6f0c3a4c6c0146a5d37657ff14826e93a4c5f2585711dd22f420ce094d2",
       "comun_head": "0100be8f85c425749574adad9cf7c922a0030f4ac5ebdb12f4c83e5b7bcc9b4b",
       "juez_corrida": "4fa095019dfa5d085ca5eeff1acc40f05f50ee482de9e649d9d042d03012e53b",
       "comun_corrida": "631037e968174a5743869a27d0a5b4275cf5bb5cdaa2bc1dfc3a49890d6998cc"}
DE_B64 = ("analizar_b64.py", "aplicar_lectura_tolerante_b64.py", "armar_adjudicacion_b64.py", "exactitud_de_cita_9_4_b64.py")
ATRIBUTO = "atributo del módulo, no código (JB.__file__: la ruta de su archivo, para su sha256)"


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leer(p: Path, esperado: str, nombre: str) -> bytes:
    b = Path(p).read_bytes()
    if sha_b(b) != esperado:
        raise SystemExit(f"FRENO: {nombre} no da su sha256")
    return b


def usados(arboles: dict) -> tuple[dict, dict]:
    """({nombre de juez_b63: [archivos]}, {nombre de comun_b63: [archivos]}) del código del análisis."""
    jb, k = {}, {}
    for archivo, arbol in arboles.items():
        for n in ast.walk(arbol):
            if not isinstance(n, ast.Attribute):
                continue
            v = n.value
            if isinstance(v, ast.Name) and v.id == "JB":
                jb.setdefault(n.attr, set()).add(archivo)
            elif (isinstance(v, ast.Name) and v.id == "K") or (isinstance(v, ast.Attribute) and v.attr == "K"
                                                                and isinstance(v.value, ast.Name) and v.value.id == "JB"):
                k.setdefault(n.attr, set()).add(archivo)
    return {x: sorted(v) for x, v in sorted(jb.items())}, {x: sorted(v) for x, v in sorted(k.items())}


def definiciones(arbol: ast.Module) -> dict:
    """{nombre: nodo} de lo de nivel de módulo: funciones, clases, asignaciones e imports (el último, si se repite)."""
    out = {}
    for n in arbol.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                for x in ast.walk(t):
                    if isinstance(x, ast.Name):
                        out[x.id] = n
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out[(a.asname or a.name).split(".")[0]] = n
    return out


def nombres_en(nodo: ast.AST) -> set:
    return {x.id for x in ast.walk(nodo) if isinstance(x, ast.Name)}


def comparar(raices: list[str], viejo: ast.Module, nuevo: ast.Module) -> dict:
    """Cada nombre de `raices` y lo que usa del módulo, hasta cerrar: {nombre: {tipo, igual}}."""
    dv, dn = definiciones(viejo), definiciones(nuevo)
    out, pila = {}, list(raices)
    while pila:
        x = pila.pop()
        if x in out:
            continue
        a, b = dv.get(x), dn.get(x)
        if x.startswith("__") and x.endswith("__"):
            out[x] = {"tipo": ATRIBUTO, "igual": None}
            continue
        if a is None and b is None:
            out[x] = {"tipo": "no es de nivel de módulo", "igual": False}
            continue
        tipo = {ast.FunctionDef: "funcion", ast.AsyncFunctionDef: "funcion", ast.ClassDef: "clase", ast.Import: "import",
                ast.ImportFrom: "import"}.get(type(a or b), "asignacion")
        out[x] = {"tipo": tipo, "igual": a is not None and b is not None and ast.dump(a) == ast.dump(b)}
        if tipo not in ("import",):
            pila += sorted((nombres_en(a) | (nombres_en(b) if b is not None else set())) & (set(dv) | set(dn)) - {x})
    return dict(sorted(out.items()))


def lo_que_difiere(viejo: ast.Module, nuevo: ast.Module) -> dict:
    dv, dn = definiciones(viejo), definiciones(nuevo)
    nombradas = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign, ast.Import, ast.ImportFrom)
    otras = [[ast.dump(n) for n in m.body[1:] if not isinstance(n, nombradas)] for m in (viejo, nuevo)]
    return {"docstring": ast.get_docstring(viejo) != ast.get_docstring(nuevo),
            "nombres": sorted(x for x in set(dv) | set(dn) if x not in dv or x not in dn or ast.dump(dv[x]) != ast.dump(dn[x])),
            "las_demas_sentencias_de_nivel_de_modulo_iguales": otras[0] == otras[1]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    for a in ("juez_head", "comun_head", "juez_corrida", "comun_corrida"):
        ap.add_argument("--" + a.replace("_", "-"), type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.salida.exists():
        raise SystemExit("FRENO: --salida ya existe")
    m = {k: ast.parse(leer(getattr(a, k), SHA[k], k)) for k in SHA}
    codigo = {n: leer(B.CODIGO_B63 / n, s, n) for n, s in B.SELLADO.items()} | {n: (AQUI / n).read_bytes() for n in DE_B64}
    jb, k = usados({n: ast.parse(b) for n, b in codigo.items()})
    cj = comparar(list(jb), m["juez_head"], m["juez_corrida"])
    ck = comparar(list(k), m["comun_head"], m["comun_corrida"])
    dj, dk = lo_que_difiere(m["juez_head"], m["juez_corrida"]), lo_que_difiere(m["comun_head"], m["comun_corrida"])
    out = {"que": "el juez de la corrida de B6.4 (b64/v1, H-4) y el que importa el análisis (b63/v2/b2 de HEAD): lo que usa el análisis, "
                  "igual en los dos (la corrección del H-6)",
           "archivos": dict(SHA),
           "codigo_del_analisis": {n: sha_b(b) for n, b in sorted(codigo.items())},
           "juez_b63": {"usado_por_el_analisis": jb, "comparado": cj,
                        "todo_igual": all(v["igual"] for v in cj.values() if v["tipo"] != ATRIBUTO),
                        "lo_que_difiere_en_el_modulo": dj,
                        "el_diff_toca_solo_la_cabecera_BANCO_DIR_y_CITAS_POR_ROL":
                            dj == {"docstring": True, "nombres": ["BANCO_DIR", "CITAS_POR_ROL"],
                                   "las_demas_sentencias_de_nivel_de_modulo_iguales": True}},
           "comun_b63": {"usado_por_el_analisis": k, "comparado": ck,
                         "todo_igual": all(v["igual"] for v in ck.values() if v["tipo"] != ATRIBUTO),
                         "lo_que_difiere_en_el_modulo": dk}}
    out["todo_lo_que_usa_el_analisis_es_igual"] = out["juez_b63"]["todo_igual"] and out["comun_b63"]["todo_igual"]
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for nombre in ("juez_b63", "comun_b63"):
        print(f"{'PASS' if out[nombre]['todo_igual'] else 'FAIL'}  {nombre}: "
              f"{sum(1 for v in out[nombre]['comparado'].values() if v['tipo'] != ATRIBUTO)} nombres comparados")
    print(f"control del juez: {'PASS' if out['todo_lo_que_usa_el_analisis_es_igual'] else 'FRENO'}; salida sha256 {sha_b(a.salida.read_bytes())}")
    return 0 if out["todo_lo_que_usa_el_analisis_es_igual"] else 10


if __name__ == "__main__":
    raise SystemExit(main())
