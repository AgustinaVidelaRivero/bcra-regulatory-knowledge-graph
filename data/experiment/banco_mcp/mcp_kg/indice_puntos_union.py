#!/usr/bin/env python3
"""indice_puntos_union.py — U-INDICES-EVAL, etapa b: la versión nueva del índice por punto (familia 1), con la unión por
clave (opción (a), decidida por la autora el 26/10/2026), para el grafo evaluado de B6.3, cuya E0 tiene claves de
sección repetidas en tres TOs (ri_secoexpo, ri_transpa y ri_tsa) y hace abortar a cargar_e0 de HEAD.

Importa mcp_kg/indice_puntos.py de HEAD, sin editarlo, y cambia dos funciones (las dos, en este archivo):
  - `cargar_e0`: ante una clave repetida en la estructura no aborta: junta sus apariciones en un solo punto con esa
    clave. Los hijos de todas sus apariciones van en el orden de la primera aparición, sin repetir; los bloques, en el
    orden de la E0, y las páginas, unidas (como en HEAD); el título, el padre y la página son los de la primera
    aparición, y las demás apariciones se cuentan. Un hijo que cerraría un ciclo no se agrega, y se cuenta. Sin claves
    repetidas en la estructura, llama a la `cargar_e0` de HEAD: el camino del código es el de HEAD.
  - `orden_canonico`: con la unión, un punto puede quedar en la lista de hijos de dos padres, y el preorden de HEAD lo
    emitiría dos veces (un documento repetido en el índice). La versión nueva es el preorden de HEAD con cada punto una
    sola vez, en su primera posición (decisión de la autora del 26/10/2026). Sin puntos en dos listas, da lo mismo.
Las cuentas de la unión (claves unidas, apariciones, hijos cortados y repetidos sacados del orden, por TO) quedan
aparte, en `ULTIMAS_CUENTAS`, y van a la salida de main y a `--cuentas`; no entran en los archivos del índice. El
manifiesto del índice suma `version_indice_puntos`: este archivo, su sha256 y las dos funciones que cambia.

Uso (desde la raíz de la copia, como indice_puntos.py):
  .venv/bin/python -B data/experiment/banco_mcp/mcp_kg/indice_puntos_union.py --grafo CLAVE --e0-dir RUTA --salida DIR [--cuentas JSON]
  .venv/bin/python -B data/experiment/banco_mcp/mcp_kg/indice_puntos_union.py --verificar DIR
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import indice_puntos as IP  # noqa: E402  (HEAD, sin editar)

CARGAR_E0_HEAD = IP.cargar_e0
ORDEN_CANONICO_HEAD = IP.orden_canonico
ULTIMAS_CUENTAS: dict = {}


def _alcanza(puntos: dict, desde: str, hasta: str) -> bool:
    """Si `hasta` está en el subárbol de `desde` (por las listas de hijos)."""
    pila, vistos = [desde], set()
    while pila:
        k = pila.pop()
        if k == hasta:
            return True
        if k in vistos:
            continue
        vistos.add(k)
        pila.extend(puntos[k]["hijos"])
    return False


def claves_repetidas(to: str, est: dict) -> Counter:
    """Las claves de punto que aparecen más de una vez en la estructura de un TO (con `_clave_estructura` de HEAD)."""
    vistas = Counter()

    def rec(nodos, prefijo):
        for n in nodos:
            pref = n.get("prefijo") or prefijo
            vistas[f"{to}::{IP._clave_estructura(n, pref)}"] += 1
            rec(n.get("hijos", []), pref)
    rec(est.get("secciones", []), None)
    return Counter({k: v for k, v in vistas.items() if v > 1})


def unir_estructura(to: str, est: dict, puntos: dict, cuentas: dict) -> None:
    """El `rec` de cargar_e0 de HEAD, con la unión por clave en lugar del aborto."""

    def rec(nodos, padre, prefijo):
        for n in nodos:
            pref = n.get("prefijo") or prefijo
            u = IP._clave_estructura(n, pref)
            k = f"{to}::{u}"
            if k in puntos:
                cuentas["apariciones_extra"][k] += 1
                if k not in puntos[padre]["hijos"]:
                    if padre == k or _alcanza(puntos, k, padre):
                        cuentas["hijos_cortados"].append([padre, k])
                    else:
                        puntos[padre]["hijos"].append(k)
                rec(n.get("hijos", []), k, pref)
                continue
            puntos[k] = {"clave": k, "to": to, "unidad": u, "titulo": (n.get("titulo") or "").strip(),
                         "tipo": n["tipo"], "padre": padre, "hijos": [], "pagina": n.get("pagina"),
                         "paginas": [], "bloques": [], "textos": [], "herencia": [], "intro": False,
                         "en_estructura": True, "nodos": []}
            puntos[padre]["hijos"].append(k)
            rec(n.get("hijos", []), k, pref)
    rec(est.get("secciones", []), to, None)


def cargar_e0_con_cuentas(e0_dir: Path, tos: list[str]) -> tuple[dict, dict, dict, dict]:
    """(puntos, archivo->to, insumos, cuentas). Sin claves repetidas, la de HEAD."""
    ests = {to: json.loads((e0_dir / f"estructura_{to}.json").read_text(encoding="utf-8")) for to in tos}
    repetidas = {to: claves_repetidas(to, est) for to, est in ests.items()}
    if not any(repetidas.values()):
        puntos, archivos, insumos = CARGAR_E0_HEAD(e0_dir, tos)
        return puntos, archivos, insumos, {"camino": "HEAD", "claves_unidas": 0, "apariciones": 0,
                                           "hijos_cortados": 0, "por_to": {}}
    puntos, archivos, insumos = {}, {}, {}
    cu = {"apariciones_extra": Counter(), "hijos_cortados": []}
    for to in tos:
        pe, pc = e0_dir / f"estructura_{to}.json", e0_dir / f"chunks_{to}.json"
        insumos[pe.name], insumos[pc.name] = IP.sha256_file(pe), IP.sha256_file(pc)
        est = ests[to]
        chunks = json.loads(pc.read_text(encoding="utf-8"))
        puntos[to] = {"clave": to, "to": to, "unidad": None, "titulo": est.get("archivo") or to, "tipo": "to",
                      "padre": None, "hijos": [], "pagina": None, "paginas": [], "bloques": [], "textos": [],
                      "herencia": [], "intro": False, "en_estructura": True, "nodos": []}
        unir_estructura(to, est, puntos, cu)
        for c in chunks:                                   # el resto, como cargar_e0 de HEAD
            archivos.setdefault(c["archivo"], to)
            k = f"{to}::{c['unidad']}"
            if k not in puntos:
                pn = IP._padre_numerico(c["unidad"])
                padre = f"{to}::{pn}" if pn and f"{to}::{pn}" in puntos else to
                puntos[k] = {"clave": k, "to": to, "unidad": c["unidad"],
                             "titulo": re.sub(r"^\[bloque [^\]]*\]\s*", "", c.get("titulo") or "").strip(),
                             "tipo": "seccion" if c["unidad"].rpartition("::")[2].startswith("S") else "punto",
                             "padre": padre, "hijos": [], "pagina": (c.get("paginas") or [None])[0], "paginas": [],
                             "bloques": [], "textos": [], "herencia": [], "intro": False, "en_estructura": False,
                             "nodos": []}
                puntos[padre]["hijos"].append(k)
            p = puntos[k]
            p["bloques"].append(c["id"])
            p["textos"].append(c.get("texto") or "")
            p["paginas"] = sorted(set(p["paginas"]) | set(c.get("paginas") or []))
            if c.get("rol_bloque") == "intro":
                p["intro"] = True
            if not p["herencia"]:
                p["herencia"] = [h.get("texto") or "" for h in c.get("herencia") or []]
    por_to = {}
    for k, extra in cu["apariciones_extra"].items():
        d = por_to.setdefault(k.split("::", 1)[0], {"claves_unidas": [], "apariciones": 0, "hijos_cortados": []})
        d["claves_unidas"].append(k)
        d["apariciones"] += 1 + extra
    for padre, hijo in cu["hijos_cortados"]:
        por_to.setdefault(hijo.split("::", 1)[0], {"claves_unidas": [], "apariciones": 0,
                                                    "hijos_cortados": []})["hijos_cortados"].append([padre, hijo])
    for d in por_to.values():
        d["claves_unidas"].sort()
    cuentas = {"camino": "union", "claves_unidas": len(cu["apariciones_extra"]),
               "apariciones": sum(1 + v for v in cu["apariciones_extra"].values()),
               "hijos_cortados": len(cu["hijos_cortados"]), "por_to": dict(sorted(por_to.items()))}
    return puntos, archivos, insumos, cuentas


def cargar_e0(e0_dir: Path, tos: list[str]) -> tuple[dict, dict, dict]:
    """La firma de cargar_e0 de HEAD (la que llama derivar); las cuentas quedan en ULTIMAS_CUENTAS."""
    puntos, archivos, insumos, cuentas = cargar_e0_con_cuentas(e0_dir, tos)
    ULTIMAS_CUENTAS.clear()
    ULTIMAS_CUENTAS.update(cuentas)
    return puntos, archivos, insumos


def orden_canonico(puntos: dict) -> list[str]:
    """El preorden de HEAD, con cada punto una sola vez, en su primera posición."""
    vistos, out = set(), []
    for k in ORDEN_CANONICO_HEAD(puntos):
        if k not in vistos:
            vistos.add(k)
            out.append(k)
    ULTIMAS_CUENTAS["repetidos_sacados_del_orden"] = len(ORDEN_CANONICO_HEAD(puntos)) - len(out)
    return out


def usar_version_nueva() -> None:
    """Pone las dos funciones en el módulo de HEAD, en memoria, para que derivar, escribir y verificar las usen."""
    IP.cargar_e0 = cargar_e0
    IP.orden_canonico = orden_canonico


def campo_version() -> dict:
    return {"archivo": IP.rel_repo(Path(__file__)), "sha256": IP.sha256_file(Path(__file__)),
            "funciones_cambiadas": ["cargar_e0", "orden_canonico"],
            "base": {"archivo": IP.rel_repo(Path(IP.__file__)), "sha256": IP.sha256_file(Path(IP.__file__))}}


def escribir(clave_grafo: str, kg_path: Path, kg_sha: str, e0_dir: Path, salida: Path) -> dict:
    """IP.escribir con la versión nueva, y el manifiesto con `version_indice_puntos` (misma serialización)."""
    usar_version_nueva()
    man = IP.escribir(clave_grafo, kg_path, kg_sha, e0_dir, salida)
    man["version_indice_puntos"] = campo_version()
    (salida / "manifiesto.json").write_bytes(json.dumps(man, ensure_ascii=False, indent=1).encode("utf-8"))
    return man


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--grafo")
    ap.add_argument("--e0-dir", type=Path)
    ap.add_argument("--salida", type=Path)
    ap.add_argument("--cuentas", type=Path)
    ap.add_argument("--verificar", type=Path)
    a = ap.parse_args()
    usar_version_nueva()
    if a.verificar:
        r = IP.verificar(a.verificar.resolve())
        print(json.dumps(r | {"cuentas": ULTIMAS_CUENTAS}, ensure_ascii=False))
        return 0 if all(r.values()) else 1
    from grafos import GRAFOS, verificar_sha  # noqa: E402  (data/experiment/neo4j, solo import)
    kg_sha = verificar_sha(a.grafo)
    man = escribir(a.grafo, GRAFOS[a.grafo]["path"], kg_sha, (IP.REPO_DIR / a.e0_dir).resolve()
                   if not a.e0_dir.is_absolute() else a.e0_dir, a.salida.resolve())
    if a.cuentas:
        a.cuentas.write_text(json.dumps(ULTIMAS_CUENTAS, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("grafo", "kg_sha256", "n_puntos", "n_nodos", "procedencias_fuera_de_la_e0",
                                          "puntos_fuera_de_la_estructura", "archivos", "version_indice_puntos")}
                     | {"cuentas": ULTIMAS_CUENTAS}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
