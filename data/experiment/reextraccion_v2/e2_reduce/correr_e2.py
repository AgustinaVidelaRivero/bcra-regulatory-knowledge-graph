"""
correr_e2.py — CLI de la corrida E2 (reduce) para un TO.

Uso:
    python3 correr_e2.py --to pro \
        --extracciones ../e1_extractor/salida/faseB_pro/extracciones.jsonl

Escribe en salida/: grafo_<to>.json, fanin_<to>.json, censo_<to>.json,
reporte_e2_<to>.json. Si la guarda de fan-in detecta ausentes, duplicados o
inesperados, ABORTA sin escribir grafo (solo persiste el reporte de fan-in),
salvo --permitir-parcial explícito — en cuyo caso el reporte queda marcado
`parcial: true`. Código puro, cero LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from e2_lib import BASE, E0_SALIDA, SIN_ORACULO, FanInError, TOS, reducir

SALIDA = BASE / "salida"


def _cargar_manifiesto(ruta: str):
    sys.path.insert(0, str(BASE.parents[0]))
    import manifiesto_corpus
    return manifiesto_corpus.cargar(Path(ruta))


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True)
    ap.add_argument("--extracciones", required=True, type=Path)
    ap.add_argument("--permitir-parcial", action="store_true",
                    help="ensambla aun con fan-in no apto; el reporte queda "
                         "marcado parcial (jamás es el default)")
    ap.add_argument("--e0-dir", type=Path, default=None,
                    help="salida de E0 a usar como mapa (default: la sellada, "
                         "o rutas.e0_salida con --manifiesto; para la "
                         "enmienda 01: e0_chunking/salida_enm01)")
    ap.add_argument("--sufijo", default="",
                    help="sufijo de los archivos de salida (p. ej. _enm01), "
                         "para no pisar la corrida sellada")
    ap.add_argument("--manifiesto", default=None,
                    help="manifiesto de corpus (U-B5.1): TOs válidos, e0_dir, "
                         "limitaciones y modo sin oráculo salen de él")
    args = ap.parse_args()

    man = _cargar_manifiesto(args.manifiesto) if args.manifiesto else None
    tos_validos = man.ids if man is not None else list(TOS)
    if args.to not in tos_validos:
        ap.error(f"--to {args.to!r} no está en {tos_validos}")
    e0_dir = args.e0_dir if args.e0_dir is not None else \
        (man.e0_salida if man is not None else E0_SALIDA)

    SALIDA.mkdir(parents=True, exist_ok=True)
    suf = args.sufijo
    try:
        res = reducir(args.to, args.extracciones,
                      permitir_parcial=args.permitir_parcial,
                      censo_oraculo=(None if man is None or man.tiene_oraculo
                                     else SIN_ORACULO),
                      e0_dir=e0_dir,
                      limitaciones=(man.limitaciones_e0()
                                    if man is not None else None))
    except FanInError as e:
        _dump(SALIDA / f"fanin_{args.to}{suf}.json", e.fanin)
        print(f"ABORTADO — {e}", flush=True)
        print(f"Reporte de fan-in: {SALIDA / f'fanin_{args.to}{suf}.json'}", flush=True)
        return 2

    (SALIDA / f"grafo_{args.to}{suf}.json").write_text(res["grafo_json"] + "\n",
                                                       encoding="utf-8")
    _dump(SALIDA / f"fanin_{args.to}{suf}.json", res["fanin"])
    _dump(SALIDA / f"censo_{args.to}{suf}.json", res["censo"])
    _dump(SALIDA / f"reporte_e2_{args.to}{suf}.json", res["reporte"])

    r = res["reporte"]
    print(json.dumps({k: r[k] for k in
                      ("to", "parcial", "fanin", "nodes_total", "edges_total",
                       "nodes_by_type", "edges_by_relation", "stats",
                       "cuarentena", "sha256_grafo")},
                     ensure_ascii=False, indent=2), flush=True)
    nc, nm = r["censo"]["nivel_chunk"], r["censo"]["nivel_mapa"]
    print(f"\nCenso nivel chunk: {nc['cubiertas']}/{nc['unidades']} cubiertas, "
          f"{len(nc['ausencias'])} ausencias", flush=True)
    for a in nc["ausencias"]:
        print(f"  - {a['unidad']} ({a['chunk_id']}): {a['diagnostico']}", flush=True)
    if nm.get("modo") == "sin_oraculo":
        print("Censo nivel mapa: sin oráculo (corpus sin mapa de territorio)",
              flush=True)
    else:
        print(f"Censo nivel mapa: {nm['cubiertas']}/{nm['unidades']} cubiertas, "
              f"{len(nm['ausencias'])} ausencias", flush=True)
        for a in nm["ausencias"]:
            print(f"  - {a['unidad']}: {a['diagnostico']}", flush=True)
    if r["rechazos_e2"]:
        print(f"\nRECHAZOS E2 (re-validación): {len(r['rechazos_e2'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
