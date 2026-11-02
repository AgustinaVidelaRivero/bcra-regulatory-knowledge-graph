#!/usr/bin/env python3
"""indice_puntos.py — U-NAV-DISENO, N5 (mandato firmado en c2ddf5f7, §3 y §4, N5): el índice por punto de las
herramientas de navegación del brazo del grafo (familias_nav.py), sin Neo4j. Solo biblioteca estándar.

Un «punto» es una unidad de la E0 del grafo: `to::unidad`, con la unidad como la numera la E0 (`5.12`, `S5` para una
sección, `A2::3.1` dentro de un subdocumento). `punto::intro`, `punto::cierre`, `punto::chapeau_seccion`,
`punto::intersticial` y `punto::parteN` son bloques del mismo punto: la vista los une.

Lo que arma, desde el kg.json sellado del grafo (sha256 verificado contra grafos.py) y la E0 que declara la config:
  - `puntos.json`: por punto, su TO, su unidad, su título, su tipo (sección o punto), su padre y sus hijos (el árbol de
    `estructura_<to>.json`; un punto de los subdocumentos hereda el prefijo de su sección), sus páginas, sus bloques
    (`chunks_<to>.json`, en el orden de la E0), su texto propio, su herencia (los encabezados y las intros heredadas
    del primer bloque) y sus nodos: los de toda procedencia en el punto, menos el TextoOrdenado, que tiene una en
    cada punto de su TO. Una raíz por TO (clave = el TO) cuelga las secciones de primer nivel;
  - `nodos.json`: por nodo, del kg.json crudo (lo que la vista runtime no lleva a Neo4j): tipo, label, los puntos de
    sus procedencias (`to::punto`), el tramo literal y el rol documental de cada punto (y los de la primera
    procedencia), `termino`, `descripcion`, `umbrales` y la marca de la cola humana;
  - `documentos.json`: el texto que indexan BM25 y el denso, por punto, en el orden canónico (TOs ordenados, árbol en
    preorden): la herencia (o, sin bloques, los títulos de los ancestros), el título si el punto no tiene texto
    propio, el texto propio y, por cada nodo del punto, su descripción, su `termino` y su tramo literal en ese punto
    (familia 1);
  - `indice_bm25.json`: BM25 con el analizador del brazo de fragmentos (mcp_vector/bm25_fragmentos.py: el `spanish`
    de Lucene 9.11.1, k1 1,2 y b 0,75), sobre los documentos;
  - `manifiesto.json`: los sha256 del kg.json, de cada archivo de la E0 leído y de cada archivo de arriba, con los
    parámetros. El denso (`embeddings_docs.npy`) lo agrega construir_denso_puntos.py, en el venv del servidor de
    fragmentos (el .venv del repo no trae torch ni sentence-transformers).
Los archivos se escriben con json.dumps(sort_keys, sin espacios, UTF-8): misma entrada, mismos bytes.

Uso (desde la raíz del repo):
  .venv/bin/python -B data/experiment/banco_mcp/mcp_kg/indice_puntos.py --grafo CLAVE --e0-dir RUTA --salida DIR
  .venv/bin/python -B data/experiment/banco_mcp/mcp_kg/indice_puntos.py --verificar DIR   (re-deriva y compara bytes)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
EXPERIMENT_DIR = BANCO_DIR.parent
REPO_DIR = EXPERIMENT_DIR.parents[1]
for _p in (str(BANCO_DIR / "mcp_vector"), str(EXPERIMENT_DIR / "neo4j")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bm25_fragmentos as BM  # noqa: E402  (el analizador del brazo de fragmentos, sin cambios)

FORMATO = "indice_puntos_nav v1"
BLOQUES = ("intro", "cierre", "chapeau_seccion", "intersticial")
ARCHIVOS = ("puntos.json", "nodos.json", "documentos.json", "indice_bm25.json")
TIPOS_FUERA_DE_PUNTO = ("TextoOrdenado",)   # ver derivar()
_PARTE = re.compile(r"::parte\d+$")


def serializar(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def rel_repo(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO_DIR))
    except ValueError:
        return str(p)


def base_punto(clave: str) -> str:
    """`ext::5.12::intro` -> `ext::5.12`; `cap::4.2.1.2::parte2` -> `cap::4.2.1.2`."""
    clave = _PARTE.sub("", clave)
    for b in BLOQUES:
        if clave.endswith("::" + b):
            return clave[: -len(b) - 2]
    return clave


# --------------------------------------------------------------------------- #
# E0                                                                           #
# --------------------------------------------------------------------------- #
def _clave_estructura(n: dict, prefijo: str | None) -> str:
    base = ("S" + n["numero"]) if n["tipo"] == "seccion" else n["numero"]
    return f"{prefijo}::{base}" if prefijo else base


def _padre_numerico(unidad: str) -> str | None:
    """Padre de una unidad que no está en la estructura: la unidad sin su último número (`3.2.1` -> `3.2`, `3.2` ->
    `S3`), dentro del mismo prefijo de subdocumento."""
    pref, _, u = unidad.rpartition("::")
    if u.startswith("S") or "." not in u:
        return None
    padre = u.rsplit(".", 1)[0]
    padre = padre if "." in padre else "S" + padre
    return f"{pref}::{padre}" if pref else padre


def cargar_e0(e0_dir: Path, tos: list[str]) -> tuple[dict, dict, dict]:
    """(puntos, archivo->to, insumos {archivo: sha256}). Raíz por TO con clave = el TO."""
    puntos, archivos, insumos, duplicados = {}, {}, {}, []
    for to in tos:
        pe, pc = e0_dir / f"estructura_{to}.json", e0_dir / f"chunks_{to}.json"
        insumos[pe.name], insumos[pc.name] = sha256_file(pe), sha256_file(pc)
        est = json.loads(pe.read_text(encoding="utf-8"))
        chunks = json.loads(pc.read_text(encoding="utf-8"))
        puntos[to] = {"clave": to, "to": to, "unidad": None, "titulo": est.get("archivo") or to, "tipo": "to",
                      "padre": None, "hijos": [], "pagina": None, "paginas": [], "bloques": [], "textos": [],
                      "herencia": [], "intro": False, "en_estructura": True, "nodos": []}

        def rec(nodos, padre, prefijo):
            for n in nodos:
                pref = n.get("prefijo") or prefijo
                u = _clave_estructura(n, pref)
                k = f"{to}::{u}"
                if k in puntos:
                    duplicados.append(k)
                    continue
                puntos[k] = {"clave": k, "to": to, "unidad": u, "titulo": (n.get("titulo") or "").strip(),
                             "tipo": n["tipo"], "padre": padre, "hijos": [], "pagina": n.get("pagina"),
                             "paginas": [], "bloques": [], "textos": [], "herencia": [], "intro": False,
                             "en_estructura": True, "nodos": []}
                puntos[padre]["hijos"].append(k)
                rec(n.get("hijos", []), k, pref)
        rec(est.get("secciones", []), to, None)
        for c in chunks:
            archivos.setdefault(c["archivo"], to)
            k = f"{to}::{c['unidad']}"
            if k not in puntos:
                pn = _padre_numerico(c["unidad"])
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
    if duplicados:
        raise SystemExit(f"ABORTO: claves de punto repetidas en la estructura de la E0: {duplicados[:5]}")
    return puntos, archivos, insumos


# --------------------------------------------------------------------------- #
# Nodos (kg.json crudo)                                                        #
# --------------------------------------------------------------------------- #
def cargar_nodos(kg_path: Path) -> tuple[dict, list[str]]:
    """(nodos {id: {...}}, ids en el orden del kg.json)."""
    d = json.loads(kg_path.read_text(encoding="utf-8"))
    nodos, orden = {}, []
    for n in d.get("nodes", []):
        provs = n.get("provenances") or ([n["provenance"]] if n.get("provenance") else [])
        pts, tramos, roles = [], {}, {}
        for pv in provs:
            if isinstance(pv, dict) and pv.get("to") and pv.get("punto"):
                k = base_punto(f"{pv['to']}::{str(pv['punto']).strip()}")
                if k not in pts:
                    pts.append(k)
                if pv.get("tramo") and k not in tramos:
                    tramos[k] = pv["tramo"]
                roles.setdefault(k, pv.get("rol_documental"))
        p = n.get("properties") or {}
        pv0 = next((pv for pv in provs if isinstance(pv, dict)), {})
        tramo = next((pv.get("tramo") for pv in provs if isinstance(pv, dict) and pv.get("tramo")), None)
        nodos[n["id"]] = {"type": n.get("type"), "label": n.get("label") or "", "puntos": pts, "tramo": tramo,
                          "tramo_por_punto": tramos, "rol_por_punto": roles,
                          "rol": pv0.get("rol_documental"), "termino": p.get("termino"),
                          "descripcion": p.get("descripcion") or p.get("description"),
                          "umbrales": p.get("umbrales") if isinstance(p.get("umbrales"), list) else None,
                          "cola": str(p.get("cola_humana")).lower() == "true"}
        orden.append(n["id"])
    return nodos, orden


# --------------------------------------------------------------------------- #
# Documentos e índice                                                          #
# --------------------------------------------------------------------------- #
def orden_canonico(puntos: dict) -> list[str]:
    """TOs ordenados; dentro de cada TO, el árbol en preorden (sin la raíz)."""
    out = []

    def pre(k):
        for h in puntos[k]["hijos"]:
            out.append(h)
            pre(h)
    for to in sorted(k for k, p in puntos.items() if p["tipo"] == "to"):
        pre(to)
    return out


def ancestros(puntos: dict, clave: str) -> list[str]:
    out, k = [], puntos[clave]["padre"]
    while k is not None and puntos[k]["tipo"] != "to":
        out.append(k)
        k = puntos[k]["padre"]
    return out[::-1]


def documento(puntos: dict, nodos: dict, clave: str) -> str:
    p = puntos[clave]
    partes = list(p["herencia"]) if p["herencia"] else [
        f"{puntos[a]['unidad']} {puntos[a]['titulo']}".strip() for a in ancestros(puntos, clave)]
    if not any(t.strip() for t in p["textos"]):
        partes.append(f"{p['unidad']} {p['titulo']}".strip())
    partes += p["textos"]
    for nid in p["nodos"]:
        nd = nodos[nid]
        partes += [str(x) for x in (nd["descripcion"], nd["termino"], nd["tramo_por_punto"].get(clave)) if x]
    vistos, out = set(), []
    for t in partes:
        t = t.strip()
        if t and t not in vistos:
            vistos.add(t)
            out.append(t)
    return "\n".join(out)


def derivar(kg_path: Path, e0_dir: Path) -> dict:
    """Los cuatro archivos (como objetos) y lo que el manifiesto declara de ellos."""
    nodos, orden_nodos = cargar_nodos(kg_path)
    tos = sorted({k.split("::", 1)[0] for nd in nodos.values() for k in nd["puntos"]})
    tos = [t for t in tos if (e0_dir / f"chunks_{t}.json").exists()]
    puntos, archivos, insumos = cargar_e0(e0_dir, tos)
    fuera = 0
    for nid in orden_nodos:
        # El nodo TextoOrdenado tiene una procedencia en cada punto de su TO (las establecida_en derivadas): no es
        # contenido de ningún punto y, en la lista, metería su descripción en todos los documentos.
        if nodos[nid]["type"] in TIPOS_FUERA_DE_PUNTO:
            continue
        for k in nodos[nid]["puntos"]:
            if k in puntos and puntos[k]["tipo"] != "to":
                puntos[k]["nodos"].append(nid)
            else:
                fuera += 1
    claves = orden_canonico(puntos)
    docs = [{"id": k, "texto": documento(puntos, nodos, k)} for k in claves]
    indice = BM.construir(docs)
    return {"puntos": puntos, "nodos": nodos, "documentos": docs, "indice_bm25": indice,
            "declarado": {"tos": tos, "insumos_e0": insumos, "archivo_a_to": archivos, "n_puntos": len(claves),
                          "n_nodos": len(nodos), "procedencias_fuera_de_la_e0": fuera,
                          "puntos_fuera_de_la_estructura": sum(1 for p in puntos.values() if not p["en_estructura"])}}


def escribir(clave_grafo: str, kg_path: Path, kg_sha: str, e0_dir: Path, salida: Path) -> dict:
    d = derivar(kg_path, e0_dir)
    salida.mkdir(parents=True, exist_ok=True)
    shas = {}
    for nombre, obj in zip(ARCHIVOS, (d["puntos"], d["nodos"], d["documentos"], d["indice_bm25"])):
        b = BM.serializar(obj) if nombre == "indice_bm25.json" else serializar(obj)
        (salida / nombre).write_bytes(b)
        shas[nombre] = sha256_bytes(b)
    man_p = salida / "manifiesto.json"
    previo = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {}
    man = {"formato": FORMATO, "unidad": "U-NAV-DISENO, N5", "grafo": clave_grafo, "kg_path": rel_repo(kg_path),
           "kg_sha256": kg_sha, "e0_dir": rel_repo(e0_dir), **d["declarado"], "archivos": shas,
           "bm25": {"analizador": BM.ANALIZADOR, "lucene_version": BM.LUCENE_VERSION, "sha256_stop": BM.SHA256_STOP,
                    "k1": BM.K1, "b": BM.B, "sha256_indice": shas["indice_bm25.json"],
                    "sha256_modulo_bm25": sha256_file(BANCO_DIR / "mcp_vector" / "bm25_fragmentos.py")},
           "composicion_documento": ("herencia del primer bloque (o títulos de los ancestros) + título si no hay texto "
                                     "propio + texto propio de los bloques + descripción, termino y tramo literal de "
                                     "cada nodo del punto; sin repetidos; unidos con salto de línea"),
           "tipos_fuera_de_punto": list(TIPOS_FUERA_DE_PUNTO),
           "sha256_modulo_indice": sha256_file(Path(__file__))}
    if "denso" in previo and previo["denso"].get("sha256_documentos") == shas["documentos.json"]:
        # sin `tiempos_s` (U-NAV-DESDE, corrección A): los tiempos de construcción no entran en lo que se hashea
        man["denso"] = {k: v for k, v in previo["denso"].items() if k != "tiempos_s"}
    man_p.write_bytes(json.dumps(man, ensure_ascii=False, indent=1).encode("utf-8"))
    return man


def verificar(salida: Path) -> dict:
    """Re-deriva desde el kg.json y la E0 del manifiesto y compara los bytes de cada archivo."""
    man = json.loads((salida / "manifiesto.json").read_text(encoding="utf-8"))
    kg_path, e0_dir = REPO_DIR / man["kg_path"], REPO_DIR / man["e0_dir"]
    res = {"kg_sha256": sha256_file(kg_path) == man["kg_sha256"]}
    d = derivar(kg_path, e0_dir)
    for nombre, obj in zip(ARCHIVOS, (d["puntos"], d["nodos"], d["documentos"], d["indice_bm25"])):
        b = BM.serializar(obj) if nombre == "indice_bm25.json" else serializar(obj)
        res[nombre] = sha256_bytes(b) == man["archivos"][nombre] == sha256_file(salida / nombre)
    res["insumos_e0"] = d["declarado"]["insumos_e0"] == man["insumos_e0"]
    if "denso" in man:
        res["embeddings_docs.npy"] = sha256_file(salida / "embeddings_docs.npy") == man["denso"]["sha256_archivo_npy"]
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--grafo")
    ap.add_argument("--e0-dir", type=Path)
    ap.add_argument("--salida", type=Path)
    ap.add_argument("--verificar", type=Path)
    a = ap.parse_args()
    if a.verificar:
        r = verificar(a.verificar.resolve())
        print(json.dumps(r, ensure_ascii=False))
        return 0 if all(r.values()) else 1
    from grafos import GRAFOS, verificar_sha  # noqa: E402  (data/experiment/neo4j, solo import)
    kg_sha = verificar_sha(a.grafo)
    man = escribir(a.grafo, GRAFOS[a.grafo]["path"], kg_sha, (REPO_DIR / a.e0_dir).resolve()
                   if not a.e0_dir.is_absolute() else a.e0_dir, a.salida.resolve())
    print(json.dumps({k: man[k] for k in ("grafo", "kg_sha256", "n_puntos", "n_nodos", "procedencias_fuera_de_la_e0",
                                          "puntos_fuera_de_la_estructura", "archivos")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
