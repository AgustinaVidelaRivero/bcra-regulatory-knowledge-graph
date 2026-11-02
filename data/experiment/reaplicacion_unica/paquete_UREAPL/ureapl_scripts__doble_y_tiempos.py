"""U-REAPL: la doble armada del grafo evaluado (precisión 4 de la firma) y los tiempos de las corridas. USD 0, sin API.

  doble <dir A> <dir B> <salida A> <salida B>: los archivos de `<A>/r2/` y `<B>/r2/`, uno por uno: byte a byte iguales, salvo
      `reporte_ensamblado_r2.json`, que guarda la ruta de su --salida y, absolutas, las de la raíz (se compara con esas rutas
      normalizadas, como `reporte_normalizado.py`); el sha256 de cada `kg.json`.
  tiempos <consola> [...]: de cada consola de `cadena_t3_tf.sh` / `cadena_ureapl.sh`, el inicio, el fin, el rc, los segundos (real)
      de /usr/bin/time y la memoria máxima.
Imprime JSON.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normalizado(p: Path, salida: str):
    t = p.read_text(encoding="utf-8").replace(salida, "<SALIDA>")
    return json.loads(re.sub(r'"/[^"]*?/(data/experiment/|ureapl/)', r'"<RAIZ>/\1', t))


def doble(a: Path, b: Path, sa: str, sb: str) -> dict:
    fa = {p.relative_to(a / "r2").as_posix() for p in (a / "r2").rglob("*") if p.is_file()}
    fb = {p.relative_to(b / "r2").as_posix() for p in (b / "r2").rglob("*") if p.is_file()}
    distintos = sorted(f for f in fa & fb if f != "reporte_ensamblado_r2.json" and sha(a / "r2" / f) != sha(b / "r2" / f))
    rep = normalizado(a / "r2/reporte_ensamblado_r2.json", sa) == normalizado(b / "r2/reporte_ensamblado_r2.json", sb)
    return {"archivos": [len(fa), len(fb)], "solo_en_uno": sorted(fa ^ fb), "distintos_salvo_el_reporte": distintos,
            "reporte_igual_con_rutas_normalizadas": rep, "kg_sha256": [sha(a / "r2/kg.json"), sha(b / "r2/kg.json")],
            "kg_bytes": (a / "r2/kg.json").stat().st_size,
            "iguales": not (fa ^ fb) and not distintos and rep and sha(a / "r2/kg.json") == sha(b / "r2/kg.json")}


def tiempos(ps: list[str]) -> dict:
    out = {}
    for p in ps:
        t = Path(p).read_text(encoding="utf-8", errors="replace")
        g = lambda rx: (re.search(rx, t, re.M) or [None, None])[1]  # noqa: E731
        out[Path(p).name] = {"inicio": g(r"^inicio (\S+ \S+)"), "fin": g(r"^fin (\S+ \S+)"), "rc": g(r"^rc=(\d+)"),
                             "segundos": g(r"^\s*([\d.]+) real"), "memoria_max_bytes": g(r"^\s*(\d+)\s+maximum resident set size")}
    return out


if __name__ == "__main__":
    if sys.argv[1] == "doble":
        print(json.dumps(doble(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], sys.argv[5]), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(tiempos(sys.argv[2:]), ensure_ascii=False, indent=1))
