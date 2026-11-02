"""Resumen por TO del health-check de E0 (healthcheck_e0.py) contra la E0 corregida (U-SEG-OFICIAL, S2; solo lectura).

Uso: python -B resumen_healthcheck_S2.py --hc <healthcheck.json> --e0 <salida de E0 de los 152>
       --manifiesto <manifest_salida_e0_152_S0-6b.json> --out <json>

Por TO: las cuatro señales (cid, páginas sin sección, unidades grandes, cobertura), el veredicto y el modo de lectura del
health-check; al lado, el modo y la cobertura de la E0 corregida (conteos.json, cobertura.json), las unidades de
`unidades_por_to` y los ids de chunk repetidos de `chunks_<to>.json`. Como complemento (el health-check corre el
pipeline de e0_lib sin el driver de e0-r2 y no reproduce `correr_e0`), dos señales medidas sobre la E0 corregida con
la misma definición: los avisos `pagina_cuerpo_sin_seccion` de `estructura_<to>.json` y los chunks terminales con más
caracteres propios que el umbral del health-check. No copia las muestras de texto del health-check
(`senales.cid.muestras`): solo cuentas, páginas e ids de unidad.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hc", type=Path, required=True)
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--manifiesto", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    hc = json.loads(a.hc.read_text(encoding="utf-8"))
    upt = json.loads(a.manifiesto.read_text(encoding="utf-8"))["unidades_por_to"]
    conteos = json.loads((a.e0 / "conteos.json").read_text(encoding="utf-8"))
    cobertura = json.loads((a.e0 / "cobertura.json").read_text(encoding="utf-8"))
    filas = {}
    for to, r in hc.items():
        s = r["senales"]
        ch = json.loads((a.e0 / f"chunks_{to}.json").read_text(encoding="utf-8"))
        rep = sum(v - 1 for v in Counter(c["id"] for c in ch).values() if v > 1)
        ps = s["paginas_sin_seccion"]
        est = json.loads((a.e0 / f"estructura_{to}.json").read_text(encoding="utf-8"))
        sin_sec_e0 = [x for x in est["avisos"] if x["tipo"] == "pagina_cuerpo_sin_seccion"]
        grandes_e0 = sorted(((c["unidad"], c["chars_propio"]) for c in ch
                             if c["tipo"] != "mini_chunk" and c["chars_propio"] > s["unidades_anomalas_por_tamano"]["umbral_chars"]),
                            key=lambda x: -x[1])
        tam = s["unidades_anomalas_por_tamano"]
        filas[to] = {
            "veredicto_hc": r["veredicto"],
            "modo_lectura_hc": r["modo_lectura"],
            "modo_lectura_e0": conteos[to].get("modo_lectura"),
            "unidades_hc": r["unidades_extraccion"],
            "unidades_por_to": upt[to],
            "unidades_iguales": r["unidades_extraccion"] == upt[to],
            "cid_lineas": s["cid"]["lineas"], "cid_paginas": s["cid"]["paginas"],
            "sin_pagina_de_cuerpo": ps["sin_pagina_de_cuerpo"],
            "secciones_parseadas": ps["secciones_parseadas"],
            "avisos_pagina_cuerpo_sin_seccion": ps["avisos_pagina_cuerpo_sin_seccion"],
            "paginas_cuerpo_sin_seccion": ps["paginas"],
            "unidades_grandes": len(tam["anomalas"]),
            "unidades_grandes_ids": [(x["unidad"], x["chars_propio"]) for x in tam["anomalas"]],
            "umbral_chars": tam["umbral_chars"],
            "cobertura_exacta_hc": s["cobertura_no_exacta"] is None,
            "cobertura_exacta_e0": cobertura[to]["cobertura_exacta"],
            "ids_chunk_repetidos_e0": rep,
            # complemento: las mismas señales sobre la E0 corregida (no las pide el despacho; ver el docstring)
            "e0_avisos_pagina_cuerpo_sin_seccion": len(sin_sec_e0),
            "e0_paginas_cuerpo_sin_seccion": sorted({x["pagina"] for x in sin_sec_e0}),
            "e0_unidades_grandes": len(grandes_e0),
            "e0_unidades_grandes_ids": grandes_e0,
        }
    frena = sorted(t for t, f in filas.items()
                   if not f["cobertura_exacta_hc"] or not f["cobertura_exacta_e0"] or f["ids_chunk_repetidos_e0"])
    out = {"hc_sha256": hashlib.sha256(a.hc.read_bytes()).hexdigest(), "tos": len(filas),
           "frena_por_cobertura_o_ids": frena,
           "unidades_distintas": sorted(t for t, f in filas.items() if not f["unidades_iguales"]),
           "modo_distinto": sorted(t for t, f in filas.items() if f["modo_lectura_hc"] != f["modo_lectura_e0"]),
           "veredictos": dict(sorted(Counter("sano" if f["veredicto_hc"] == "sano" else "+".join(f["veredicto_hc"])
                                             for f in filas.values()).items())),
           "filas": filas}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "filas"}, ensure_ascii=False))
    for to, f in filas.items():
        print(to, f["veredicto_hc"], f["modo_lectura_hc"], f["modo_lectura_e0"], f["unidades_hc"], f["unidades_por_to"],
              "cid", f["cid_lineas"], "sinsec", f["avisos_pagina_cuerpo_sin_seccion"], f["sin_pagina_de_cuerpo"],
              f["secciones_parseadas"], "grandes", f["unidades_grandes"], "cob", f["cobertura_exacta_hc"],
              f["cobertura_exacta_e0"], "rep", f["ids_chunk_repetidos_e0"], "| e0 sinsec", f["e0_avisos_pagina_cuerpo_sin_seccion"],
              "e0 grandes", f["e0_unidades_grandes"])


if __name__ == "__main__":
    main()
