"""U-REAPL: el control del cegamiento sobre las salidas (criterio de aceptación 7; mandato, §7). USD 0, sin API.

Con la muestra en memoria (`muestra_memoria.py`), recorre los archivos que se le dan (los del paquete, sin los NO_ABRIR_) y cuenta:
  - las apariciones de una unidad de la muestra (su id, seguido de algo que no continúa el id);
  - las apariciones del código (sha256[:12]) de un nodo cegado de los grafos dados: con todas sus procedencias en unidades de la muestra
    (la regla del censo de la mesa: ese nodo no se muestra) y, aparte, con alguna (se cuenta, por archivo);
  - las apariciones del id tal cual de un nodo de una extracción de esos grafos, y de su label si tiene 25 caracteres o más
    (contenido de nodos). No cuentan los Sujetos del catálogo (nivel clase, rol o instancia: el catálogo de resolución, que va al
    paquete por mandato) ni los TextoOrdenado (los documentos).
Imprime solo cuentas: ningún id, unidad ni label. Código de salida 1 si alguna cuenta no es 0.
Uso: <python> -B control_cegamiento_salidas.py --kg <kg.json> [...] --archivos <lista de rutas, una por renglón>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import muestra_memoria as MM  # noqa: E402


def cod(i: str) -> str:
    return hashlib.sha256(i.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg", action="append", required=True)
    ap.add_argument("--archivos", type=Path, required=True)
    a = ap.parse_args()
    m = MM.muestra()
    ciegos, ciegos_alguna, ids, labels = set(), set(), set(), set()
    for p in a.kg:
        kg = json.loads(Path(p).read_text(encoding="utf-8"))
        c = MM.nodos_cegados(kg, m)
        ciegos_alguna |= {cod(i) for i in c}
        ciegos |= {cod(n["id"]) for n in kg["nodes"] if n.get("provenances")
                   and all(MM.en_muestra((p or {}).get("chunk_id"), m) for p in n["provenances"])}
        ext = [n for n in kg["nodes"] if n["type"] != "TextoOrdenado" and not (
            n["type"] == "Sujeto" and (n.get("properties") or {}).get("nivel") in ("clase", "rol", "instancia"))]
        ids |= {n["id"] for n in ext}
        labels |= {n["label"] for n in ext if isinstance(n.get("label"), str) and len(n["label"]) >= 25}
    re_u = re.compile("|".join(re.escape(u) + r"(?![\w.])" for u in sorted(m, key=len, reverse=True)))
    re_c = re.compile(r"\b[0-9a-f]{12}\b")
    archivos = [Path(x) for x in a.archivos.read_text(encoding="utf-8").splitlines() if x.strip()]
    cuentas = {"archivos": 0, "unidades_de_la_muestra": 0, "codigos_de_nodos_cegados": 0, "ids_de_nodos": 0,
               "labels_largos": 0, "archivos_con_algo": 0, "codigos_de_nodos_con_alguna_procedencia_en_la_muestra": 0,
               "por_archivo_con_alguna": {}}
    for p in archivos:
        if p.name.startswith("NO_ABRIR_"):
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        cuentas["archivos"] += 1
        u = len(re_u.findall(t))
        cods = re_c.findall(t)
        c = sum(1 for x in cods if x in ciegos)
        ca = sum(1 for x in cods if x in ciegos_alguna)
        cuentas["codigos_de_nodos_con_alguna_procedencia_en_la_muestra"] += ca
        if ca:
            cuentas["por_archivo_con_alguna"][p.name] = ca
        i = sum(1 for x in ids if x in t) if ("_" in t) else 0
        lab = sum(1 for x in labels if x in t)
        cuentas["unidades_de_la_muestra"] += u
        cuentas["codigos_de_nodos_cegados"] += c
        cuentas["ids_de_nodos"] += i
        cuentas["labels_largos"] += lab
        cuentas["archivos_con_algo"] += bool(u or c or i or lab)
    print(json.dumps(cuentas, ensure_ascii=False))
    return 0 if not cuentas["archivos_con_algo"] else 1


if __name__ == "__main__":
    sys.exit(main())
