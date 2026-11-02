#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extracto_grafo_ejemplo.py — un punto real del corpus y lo que el grafo hizo con él.

Produce un extracto LEGIBLE del grafo vigente para revisión externa: el texto de
una unidad del Texto Ordenado, y a continuación los nodos y las aristas que esa
unidad generó, con su provenance. Existe porque el `kg.json` vigente pesa 27 MB y
no se puede inspeccionar rápido: este archivo permite ver el esquema funcionando
sobre material que el revisor puede ir a leer al PDF oficial.

Todo sale del grafo y del corpus sellados; nada se escribe a mano.

Uso:  python3 scripts/extracto_grafo_ejemplo.py [--unidad ext::7.6::intro]
Escribe: docs/ejemplo_una_norma_en_el_grafo.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KG = REPO / "data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json"
CHUNKS = REPO / "data/experiment/reextraccion_v2/e0_chunking/salida_enm01"
SALIDA = REPO / "docs/ejemplo_una_norma_en_el_grafo.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unidad", default="ext::7.6::intro")
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args()

    kg = json.loads(KG.read_text(encoding="utf-8"))
    to = a.unidad.split("::")[0]
    chunks = json.loads((CHUNKS / f"chunks_{to}.json").read_text(encoding="utf-8"))
    ch = next(c for c in chunks if c["id"] == a.unidad)

    def cid(n):
        return (n.get("provenance") or {}).get("chunk_id")

    nodos = [n for n in kg["nodes"] if cid(n) == a.unidad]
    ids = {n["id"] for n in nodos}
    aristas = [e for e in kg["edges"]
               if e.get("source") in ids and e.get("target") in ids]
    salientes = [e for e in kg["edges"]
                 if (e.get("source") in ids) ^ (e.get("target") in ids)]

    L = []
    L.append("# Una norma real, y lo que el grafo hizo con ella\n")
    L.append("Extracto del grafo vigente **KG-Reextraído-r1** para revisión externa. "
             "Generado por `scripts/extracto_grafo_ejemplo.py` desde los artefactos "
             "sellados; **nada acá está escrito a mano**.\n")
    L.append(f"- Unidad: `{a.unidad}` — punto **{ch['unidad']}** de "
             f"«{ch.get('titulo','').strip()}»")
    L.append(f"- Documento: `{ch['archivo']}` · página(s) {ch.get('paginas')}")
    L.append(f"- Grafo: `{KG.relative_to(REPO)}` "
             f"({len(kg['nodes'])} nodos / {len(kg['edges'])} aristas)")
    L.append(f"- Esta unidad produjo **{len(nodos)} nodos** y **{len(aristas)} "
             f"aristas internas**; además la alcanzan o salen de ella "
             f"**{len(salientes)} aristas** hacia otras unidades.\n")

    L.append("## 1. El texto de la norma\n")
    L.append("Es lo que el extractor recibió, tal como está en el Texto Ordenado.\n")
    L.append("```text")
    L.append(ch["texto"].strip())
    L.append("```\n")

    L.append("## 2. Los nodos que produjo\n")
    L.append("Cada nodo lleva su `type` del vocabulario cerrado y su `provenance`: "
             "documento, punto y página. Esa procedencia por elemento es la que "
             "permite auditar cualquier afirmación contra el PDF oficial.\n")
    L.append("| tipo | label | punto | página(s) |")
    L.append("|---|---|---|---|")
    for n in sorted(nodos, key=lambda x: (x.get("type") or "", x.get("label") or "")):
        pr = n.get("provenance") or {}
        lab = (n.get("label") or "").replace("|", "\\|")
        L.append(f"| `{n.get('type')}` | {lab} | `{pr.get('punto')}` | "
                 f"{pr.get('paginas')} |")
    L.append("")

    L.append("## 3. Las aristas entre ellos\n")
    L.append("Las relaciones son del vocabulario cerrado, y cada una tiene una "
             "firma dominio/rango declarada en el esquema.\n")
    lab = {n["id"]: (n.get("label") or n["id"]) for n in kg["nodes"]}
    tip = {n["id"]: n.get("type") for n in kg["nodes"]}
    L.append("| origen (tipo) | relación | destino (tipo) |")
    L.append("|---|---|---|")
    for e in aristas:
        s, t_ = e["source"], e["target"]
        L.append(f"| {lab[s]} (`{tip[s]}`) | **`{e['relation']}`** | "
                 f"{lab[t_]} (`{tip[t_]}`) |")
    L.append("")

    if salientes:
        L.append("## 4. Aristas que cruzan a otras unidades\n")
        L.append("El grafo conecta más allá del punto: acá se ve la diferencia con "
                 "un índice de fragmentos, donde cada fragmento queda aislado.\n")
        L.append("| origen (tipo) | relación | destino (tipo) | unidad del destino |")
        L.append("|---|---|---|---|")
        for e in salientes:
            s, t_ = e["source"], e["target"]
            otro = t_ if s in ids else s
            n_otro = next((n for n in kg["nodes"] if n["id"] == otro), {})
            L.append(f"| {lab.get(s,s)} (`{tip.get(s)}`) | **`{e['relation']}`** | "
                     f"{lab.get(t_,t_)} (`{tip.get(t_)}`) | "
                     f"`{cid(n_otro) or '—'}` |")
        L.append("")

    L.append("---\n")
    L.append("Para regenerarlo: `python3 scripts/extracto_grafo_ejemplo.py "
             f"--unidad {a.unidad}`\n")

    Path(a.out).write_text("\n".join(L), encoding="utf-8")
    print(f"escrito: {a.out}  ({len(nodos)} nodos, {len(aristas)} aristas internas, "
          f"{len(salientes)} cruzadas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
