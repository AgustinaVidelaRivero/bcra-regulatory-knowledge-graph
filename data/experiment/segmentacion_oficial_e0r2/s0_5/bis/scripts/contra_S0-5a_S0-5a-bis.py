"""La diferencia entre la salida de S0-5a y la de S0-5a-bis, unidad por unidad, con la regla de cada lado
(U-SEG-OFICIAL; USD 0, solo lectura de las salidas).

Uso: python -B contra_S0-5a_S0-5a-bis.py --s04b <E0 de S0-4b> --s05a <E0 de S0-5a> --bis <E0 de S0-5a-bis>
       --claves-s05a <claves_S0-5a.json> --claves-bis <claves_S0-5a-bis.json> --out <json>

Cada unidad (por id) que difiere entre S0-5a y S0-5a-bis (creada en una y no en la otra, o con otro contenido) se
explica con las listas de claves de las dos etapas (cada clave con la regla que la causa contra S0-4b):
- «revertida»: S0-5a la cambiaba y S0-5a-bis la deja como en S0-4b;
- «nueva»: S0-5a la dejaba como en S0-4b y S0-5a-bis la cambia;
- «las dos»: las dos la cambian, de otro modo.
Una unidad que difiere sin estar en ninguna de las dos listas es una diferencia sin explicar, y se lista.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("s04b", "s05a", "bis", "claves_s05a", "claves_bis", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    k5 = {f["clave"]: f for f in jl(a.claves_s05a)["filas"]}
    kb = {f["clave"]: f for f in jl(a.claves_bis)["filas"]}
    filas, sin_explicar = [], []
    tos = sorted(p.name[len("chunks_"):-5] for p in a.bis.glob("chunks_*.json"))
    for to in tos:
        if (a.s05a / f"chunks_{to}.json").read_bytes() == (a.bis / f"chunks_{to}.json").read_bytes():
            continue
        c0 = {c["id"]: c for c in jl(a.s04b / f"chunks_{to}.json")}
        c5 = {c["id"]: c for c in jl(a.s05a / f"chunks_{to}.json")}
        cb = {c["id"]: c for c in jl(a.bis / f"chunks_{to}.json")}
        for i in sorted(set(c5) | set(cb)):
            if c5.get(i) == cb.get(i):
                continue
            en5, enb = i in k5, i in kb
            if en5 and not enb:
                clase = "revertida"
                ok = cb.get(i) == c0.get(i)
            elif enb and not en5:
                clase = "nueva"
                ok = c5.get(i) == c0.get(i)
            elif en5 and enb:
                clase = "las dos"
                ok = True
            else:
                clase, ok = "sin explicar", False
            fila = {"to": to, "id": i, "clase": clase,
                    "S0-5a": {"evento": k5[i]["evento"], "reglas": k5[i]["reglas"]} if en5 else None,
                    "S0-5a-bis": {"evento": kb[i]["evento"], "reglas": kb[i]["reglas"]} if enb else None,
                    "consistente": ok}
            filas.append(fila)
            if not ok:
                sin_explicar.append(fila)
    grupo = collections.Counter(
        (f["clase"], ",".join(f["S0-5a"]["reglas"]) if f["S0-5a"] else "-",
         ",".join(f["S0-5a-bis"]["reglas"]) if f["S0-5a-bis"] else "-") for f in filas)
    res = {"unidades_que_difieren": len(filas), "tos": len({f["to"] for f in filas}),
           "por_clase": dict(collections.Counter(f["clase"] for f in filas)),
           "por_clase_y_reglas": [{"clase": c, "reglas_S0-5a": r5, "reglas_S0-5a-bis": rb, "unidades": n}
                                  for (c, r5, rb), n in sorted(grupo.items())],
           "por_to": dict(collections.Counter(f["to"] for f in filas)),
           "sin_explicar_o_inconsistentes": sin_explicar, "filas": filas}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "filas"}, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
