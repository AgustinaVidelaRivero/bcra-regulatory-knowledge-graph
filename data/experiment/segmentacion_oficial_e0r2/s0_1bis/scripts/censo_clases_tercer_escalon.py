"""S0-1 bis, A: clases de las unidades grandes (las de S0-1: A no se parten y pasan el reintento con la mediana; B se
parten y la parte mayor lo pasa; C en el borde; D la parte mayor entra con la razón máxima) con la partición por
corte de E1 del código de una copia, y la capacidad del tercer escalón (40.960 tokens) como parámetro: la razón de
tokens por carácter del tercer escalón (`--razon-e3`, que el prototipo lee de S0_RAZON_E1) decide dónde rige la
partición por renglones en E1 y si la unidad (o su parte mayor) entra en el tercer escalón. Solo lectura.

Uso: python -B censo_clases_tercer_escalon.py --e0 <dir> --codigo <copia> --razon-e3 <r> --out <json>
     [--razon-mediana 1.175 --razon-max 1.498]"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.dont_write_bytecode = True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--razon-e3", type=float, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--razon-mediana", type=float, default=1.175)
    ap.add_argument("--razon-max", type=float, default=1.498)
    a = ap.parse_args()
    os.environ["S0_RAZON_E1"] = repr(a.razon_e3)
    sys.path.insert(0, str(a.codigo / "data/experiment/reextraccion_v2/e0_chunking"))
    import correr_e0 as CE  # noqa: PLC0415

    T2, T3 = 16384, 40960
    cap_med, cap_max, cap3 = T2 / a.razon_mediana, T2 / a.razon_max, T3 / a.razon_e3
    chunks = [c for p in sorted(a.e0.glob("chunks_*.json")) for c in json.loads(p.read_text(encoding="utf-8"))]
    filas = []
    for c in (c for c in chunks if c["chars_propio"] > cap_max):
        if c.get("sub_chunk"):
            partes, info = None, {"motivo": "parte_de_E0"}
        else:
            partes, info = CE.particionar_por_corte(c)
        m = max(s["chars_propio"] for s in partes) if partes else c["chars_propio"]
        if partes is None:
            clase = "A" if c["chars_propio"] > cap_med else "C"
        elif m > cap_med:
            clase = "B"
        elif m > cap_max:
            clase = "C"
        else:
            clase = "D"
        filas.append(OrderedDict([
            ("id", c["id"]), ("to", c["to"]), ("chars_propio", c["chars_propio"]), ("partible", partes is not None),
            ("motivo", info.get("motivo")), ("renglones_e1", info.get("renglones_r6")),
            ("partes", [s["chars_propio"] for s in partes] if partes else None), ("parte_mayor", m),
            ("clase", clase),
            ("tercer_escalon", None if clase in ("C", "D") else ("entra" if m <= cap3 else "no_entra"))]))
    out = OrderedDict([
        ("e0", a.e0.name), ("codigo", a.codigo.name),
        ("capacidad", {"reintento_mediana": round(cap_med, 1), "reintento_max": round(cap_max, 1),
                       "razon_tercer_escalon": a.razon_e3, "tercer_escalon": round(cap3, 1)}),
        ("unidades", len(filas)), ("clases", dict(sorted(Counter(f["clase"] for f in filas).items()))),
        ("sin_salida", [f["id"] for f in filas if f["tercer_escalon"] == "no_entra"]),
        ("al_tercer_escalon", [f["id"] for f in filas if f["tercer_escalon"] == "entra"]),
        ("con_renglones_en_e1", {f["id"]: f["renglones_e1"] for f in filas if f["renglones_e1"]}),
        ("filas", filas)])
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "filas"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
