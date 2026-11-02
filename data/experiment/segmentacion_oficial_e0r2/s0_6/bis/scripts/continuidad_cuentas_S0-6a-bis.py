"""El control de continuidad de la numeración antes y después, en cuentas (U-SEG-OFICIAL, S0-6a-bis; solo lectura; sin ids
ni texto: los rótulos y las unidades de cada salto van en el archivo NO_ABRIR_ del paquete).

Uso: python -B continuidad_cuentas_S0-6a-bis.py --antes <control> --despues <control> [--primera <control de S0-6a>]
       --out <json>

Un salto se identifica como en `s0_5/scripts/lista_continuidad_S0-5a.py` (TO, sub-documento y rótulo). Por TO: saltos
antes y después, por clase, cerrados y nuevos; en total, lo mismo.
"""
import argparse
import collections
import json
from pathlib import Path


def key(f: dict) -> tuple:
    return (f["to"], f.get("subdocumento") or "", f["rotulo"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", type=Path, required=True)
    ap.add_argument("--despues", type=Path, required=True)
    ap.add_argument("--primera", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    A = {key(f): f for f in json.loads(a.antes.read_text(encoding="utf-8"))["filas"]}
    B = {key(f): f for f in json.loads(a.despues.read_text(encoding="utf-8"))["filas"]}
    tos = sorted({k[0] for k in A} | {k[0] for k in B})
    por_to = {}
    for to in tos:
        a_ = [k for k in A if k[0] == to]
        b_ = [k for k in B if k[0] == to]
        por_to[to] = {"antes": len(a_), "despues": len(b_),
                      "despues_por_clase": dict(collections.Counter(B[k]["clase"] for k in b_)),
                      "cerrados": sum(1 for k in a_ if k not in B), "nuevos": sum(1 for k in b_ if k not in A)}
    res = {"antes": len(A), "despues": len(B),
           "antes_por_clase": dict(collections.Counter(f["clase"] for f in A.values())),
           "despues_por_clase": dict(collections.Counter(f["clase"] for f in B.values())),
           "cerrados": sum(1 for k in A if k not in B), "nuevos": sum(1 for k in B if k not in A),
           "por_to": por_to}
    if a.primera:
        P = {key(f) for f in json.loads(a.primera.read_text(encoding="utf-8"))["filas"]}
        res["primera_corrida_S0-6a"] = {"saltos": len(P), "nuevos_de_la_primera_que_siguen": sum(1 for k in B if k not in A and k in P),
                                        "nuevos_de_la_primera_que_cierran": sum(1 for k in P if k not in A and k not in B)}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_to"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
