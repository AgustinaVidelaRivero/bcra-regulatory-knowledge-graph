"""Marca 2 de 4.g de S2 (U-SEG-OFICIAL): ¿cambiaron los roles de página con la E0 corregida? (solo lectura)

Uso: python -B roles_pagina_S2.py --e0 <salida de E0 de los 152> --raiz <copia del repo> --out <json>

Compara, página por página, el rol de la E0 corregida (`pies_<to>.json`, `paginas_detalle[].rol`; para los 5 de
desarrollo, `reextraccion_v2/e0_chunking/salida_tanda0_r2b/pies_<to>.json`) con el rol que usó la tabla de las formas
del contenido (`reports/verificaciones_tesis/VERIF-FORMAS-SEG/recuento_formas_texto_completo.json`, `por_to.<to>.
paginas_por_rol_rangos`, `293fe8df`), que reconstruye los roles con el e0_lib legado. Al lado, la cuenta por rol de
`conteos.json` contra `conteos_b584.json` (y `salida_tanda0/conteos.json` para el desarrollo).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

VERIF = "reports/verificaciones_tesis/VERIF-FORMAS-SEG/recuento_formas_texto_completo.json"
T0R2B = "data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b"
T0LEG = "data/experiment/reextraccion_v2/e0_chunking/salida_tanda0"
B584 = "data/experiment/segmentacion_84/b584_particion/conteos_b584.json"


def expandir(rangos: dict) -> dict[int, str]:
    out = {}
    for rol, txt in rangos.items():
        for parte in str(txt).split(","):
            parte = parte.strip()
            if not parte:
                continue
            if "-" in parte:
                a, b = parte.split("-")
                for p in range(int(a), int(b) + 1):
                    out[p] = rol
            else:
                out[int(parte)] = rol
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("--e0", "--raiz", "--out"):
        ap.add_argument(k, type=Path, required=True)
    a = ap.parse_args()
    v = json.loads((a.raiz / VERIF).read_text(encoding="utf-8"))["por_to"]
    c_cor = json.loads((a.e0 / "conteos.json").read_text(encoding="utf-8"))
    c_t0 = json.loads((a.raiz / T0R2B / "conteos.json").read_text(encoding="utf-8"))
    c_leg = json.loads((a.raiz / B584).read_text(encoding="utf-8"))
    c_t0l = json.loads((a.raiz / T0LEG / "conteos.json").read_text(encoding="utf-8"))
    por_to, cambios = {}, Counter()
    for to in sorted(v):
        d = a.e0 if to in c_cor else a.raiz / T0R2B
        pies = json.loads((d / f"pies_{to}.json").read_text(encoding="utf-8"))
        cor = {p["pagina"]: p["rol"] for p in pies["paginas_detalle"]}
        ver = expandir(v[to]["paginas_por_rol_rangos"])
        distintas = sorted(p for p in set(cor) | set(ver) if cor.get(p) != ver.get(p))
        pares = Counter(f"{ver.get(p)} -> {cor.get(p)}" for p in distintas)
        cc = (c_cor.get(to) or c_t0.get(to))["roles_pagina"]
        cl = (c_leg.get(to) or c_t0l.get(to))["roles_pagina"]
        if distintas or cc != cl:
            por_to[to] = {"paginas_distintas": len(distintas), "paginas": distintas[:40], "cambios": dict(pares),
                          "cuenta_corregida": cc, "cuenta_legada": cl, "cuenta_igual": cc == cl}
            cambios.update(pares)
    out = {"verif_sha256": hashlib.sha256((a.raiz / VERIF).read_bytes()).hexdigest(), "tos": len(v),
           "tos_con_paginas_de_otro_rol": sum(1 for x in por_to.values() if x["paginas_distintas"]),
           "paginas_de_otro_rol": sum(x["paginas_distintas"] for x in por_to.values()),
           "tos_con_cuenta_por_rol_distinta": sum(1 for x in por_to.values() if not x["cuenta_igual"]),
           "cambios_por_par_de_roles": dict(cambios.most_common()), "por_to": por_to}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: x for k, x in out.items() if k != "por_to"}, ensure_ascii=False))
    print({t: (x["paginas_distintas"], x["cambios"]) for t, x in por_to.items()})


if __name__ == "__main__":
    main()
