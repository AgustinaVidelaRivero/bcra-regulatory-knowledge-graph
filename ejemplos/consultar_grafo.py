#!/usr/bin/env python3
"""Carga el grafo evaluado y lo consulta sin instalar nada: Python 3.9 o posterior, solo la biblioteca estándar.

Comprueba la huella del archivo contra su sello antes de cargarlo y usa las tres herramientas básicas del agente
(buscar_nodos, ver_nodo y ver_vecinos), con el código de data/experiment/evaluacion/. No escribe nada en el árbol: el JSON
se descomprime en una carpeta temporal. Las herramientas de navegación de la evaluación necesitan Neo4j y los índices.

  python3 ejemplos/consultar_grafo.py                  las cuentas del grafo
  python3 ejemplos/consultar_grafo.py --buscar TEXTO   los nodos que coinciden con TEXTO
  python3 ejemplos/consultar_grafo.py --nodo ID        un nodo, con su procedencia
  python3 ejemplos/consultar_grafo.py --vecinos ID     las aristas de un nodo
"""
import argparse
import collections
import gzip
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
RAIZ = Path(__file__).resolve().parents[1]
GRAFO = RAIZ / "data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz"
sys.path.insert(0, str(RAIZ / "data/experiment/evaluacion"))


def cargar():
    comprimido = GRAFO.read_bytes()
    sello = json.loads(Path(f"{GRAFO}.sello.json").read_text(encoding="utf-8"))
    if hashlib.sha256(comprimido).hexdigest() != sello["gz_sha256"]:
        raise SystemExit("El archivo comprimido no da el sha256 de su sello.")
    crudo = gzip.decompress(comprimido)
    if hashlib.sha256(crudo).hexdigest() != sello["kg_json_sha256"]:
        raise SystemExit("El JSON no da el sha256 de su sello.")
    return crudo, sello["kg_json_sha256"]


def main():
    ap = argparse.ArgumentParser(description="Consulta el grafo evaluado, en memoria.")
    ap.add_argument("--buscar")
    ap.add_argument("--nodo")
    ap.add_argument("--vecinos")
    ap.add_argument("--limite", type=int, default=10)
    a = ap.parse_args()
    crudo, huella = cargar()
    print(f"Huella comprobada: {huella}")
    if not (a.buscar or a.nodo or a.vecinos):
        g = json.loads(crudo)
        print(f"Nodos: {len(g['nodes'])}. Aristas: {len(g['edges'])}.")
        for tipo, n in collections.Counter(x["type"] for x in g["nodes"]).most_common():
            print(f"  {tipo}: {n}")
        return
    from harness import GraphIndex
    from loader import load_graph_from_path
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "kg.json"
        ruta.write_bytes(crudo)
        indice = GraphIndex(load_graph_from_path(ruta))
    if a.buscar:
        salida = indice.buscar_nodos(a.buscar, a.limite)
    elif a.nodo:
        salida = indice.ver_nodo(a.nodo)
    else:
        salida = indice.ver_vecinos(a.vecinos, "ambas", a.limite)
    print(json.dumps(salida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
