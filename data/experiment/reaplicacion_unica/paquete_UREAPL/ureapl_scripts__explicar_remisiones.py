"""U-REAPL: la diferencia de las cuentas de la opción B entre el acumulado de las tandas 0 y 1 (las del mandato de las remisiones y
del registro, §62) y el de las tres tandas (el paso 5), cita por cita. USD 0, sin API.

Por cada ensamblado dado, las citas que la opción B resuelve (`remision_a_subpuntos` = B en el registro de remisiones), con la clave
del detector (`r1_referencias.py:1397`: chunk_id, evidencia y unidad citada), su celda (tanda del origen → tanda del destino) y sus
pares origen → nodo (sin el origen). Compara la celda «tandas 0 y 1 → tandas 0 y 1» del de las tres tandas con un ensamblado de las
tandas 0 y 1: las citas que están en uno solo, y las que están en los dos con otra cuenta de pares, con la causa que se ve sin abrir
contenido (destinos con otra cantidad de nodos, otros orígenes). Solo cuentas y códigos (sha256[:12] del chunk_id + evidencia + destino).
Uso, desde la raíz de la copia: <python> -B explicar_remisiones.py --tres <dir r2 del paso 5> --cero-uno <dir r2> [--cero-uno-b <dir r2>]
       --salida <json>
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
MANIFIESTOS = {"tanda0": "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos_r2b.json",
               "tanda1": "data/experiment/reextraccion_v2/manifiestos/tanda1_20tos_r2b.json",
               "tanda_final": "data/experiment/reextraccion_v2/manifiestos/tanda_final_98tos_r2b.json"}


def tanda_de_to() -> dict:
    return {to: t for t, p in MANIFIESTOS.items() for to in json.loads(Path(p).read_text(encoding="utf-8"))["orden_corrida"]}


def citas_b(r2: Path, t_de: dict) -> dict:
    reg = json.loads((r2 / "remisiones_registro.json").read_text(encoding="utf-8"))
    out: dict = {}
    for c in reg:
        for d in c["destinos"]:
            if d.get("remision_a_subpuntos") != "B":
                continue
            k = (c.get("chunk_id") or json.dumps(c.get("procedencia"), ensure_ascii=False, sort_keys=True), c["evidencia"], d["destino"])
            e = out.setdefault(k, {"celda": f"{t_de.get((c.get('procedencia') or {}).get('to'), '?')}→"
                                            f"{t_de.get(d['destino'].split('::')[0], '?')}", "pares": set(), "nodos": set(),
                                   "origenes": set(), "unidades": set()})
            e["origenes"] |= set(c["origenes"])
            e["nodos"] |= set(d["nodos"])
            e["unidades"] |= set(d.get("unidades") or [])
            e["pares"] |= {(o, i) for o in c["origenes"] for i in d["nodos"] if o != i}
    return out


def resumen(r2: Path) -> dict:
    rep = json.loads((r2 / "reporte_ensamblado_r2.json").read_text(encoding="utf-8"))
    return (rep.get("remite_a") or {}).get("remisiones_a_subpuntos")


def cod(k: tuple) -> str:
    return hashlib.sha256("|".join(k).encode("utf-8")).hexdigest()[:12]


def comparar(tres: dict, cu: dict) -> dict:
    t01 = {k: v for k, v in tres.items() if v["celda"] in ("tanda0→tanda0", "tanda0→tanda1", "tanda1→tanda0", "tanda1→tanda1")}
    solo3, solo01 = sorted(set(t01) - set(cu)), sorted(set(cu) - set(t01))
    ambos = set(t01) & set(cu)
    distinta = []
    for k in sorted(ambos):
        a, b = t01[k], cu[k]
        if len(a["pares"]) != len(b["pares"]):
            distinta.append({"cita": cod(k), "pares": [len(b["pares"]), len(a["pares"])],
                             "nodos_destino": [len(b["nodos"]), len(a["nodos"])], "origenes": [len(b["origenes"]), len(a["origenes"])],
                             "unidades_iguales": a["unidades"] == b["unidades"]})
    return {"citas_tres_0y1": len(t01), "citas_cero_uno": len(cu), "solo_en_las_tres": [cod(k) for k in solo3],
            "solo_en_cero_uno": [cod(k) for k in solo01],
            "pares_tres_0y1": sum(len(v["pares"]) for v in t01.values()), "pares_cero_uno": sum(len(v["pares"]) for v in cu.values()),
            "pares_de_las_citas_solo_en_las_tres": sum(len(t01[k]["pares"]) for k in solo3),
            "pares_de_las_citas_solo_en_cero_uno": sum(len(cu[k]["pares"]) for k in solo01),
            "citas_en_los_dos_con_otra_cuenta_de_pares": distinta}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tres", type=Path, required=True)
    ap.add_argument("--cero-uno", dest="cu", type=Path, required=True)
    ap.add_argument("--cero-uno-b", dest="cub", type=Path, default=None)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    t_de = tanda_de_to()
    tres = citas_b(a.tres, t_de)
    out = {"resumen_tres": resumen(a.tres), "resumen_cero_uno": resumen(a.cu),
           "tres_contra_cero_uno": comparar(tres, citas_b(a.cu, t_de))}
    if a.cub:
        out["resumen_cero_uno_b"] = resumen(a.cub)
        out["tres_contra_cero_uno_b"] = comparar(tres, citas_b(a.cub, t_de))
    t = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    a.salida.write_text(t, encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: (vv if not isinstance(vv, list) else len(vv)) for kk, vv in v.items()})
                      for k, v in out.items()}, ensure_ascii=False))
    print("sha256:", hashlib.sha256(t.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
