"""Compara dos manifiestos de la salida de E0 de los 152 (U-SEG-OFICIAL, S0-6b; USD 0, solo lectura): el de S0-6b contra
el de S0-6a-bis, archivo por archivo (`sha256` de cada `e0/<archivo>`), y las unidades. Solo nombres de archivo y cuentas.

Uso: python -B comparar_manifiestos_S0-6b.py --a <manifiesto> --b <manifiesto> --out <json>
"""
import argparse
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser()
for k in ("a", "b", "out"):
    ap.add_argument(f"--{k}", type=Path, required=True)
x = ap.parse_args()
A, B = (json.loads(p.read_text(encoding="utf-8")) for p in (x.a, x.b))
sa, sb = ({k: v["sha256"] for k, v in m["sha256"].items()} for m in (A, B))
dist = sorted(k for k in set(sa) | set(sb) if sa.get(k) != sb.get(k))
res = {"sha256_a": hashlib.sha256(x.a.read_bytes()).hexdigest(), "sha256_b": hashlib.sha256(x.b.read_bytes()).hexdigest(),
       "archivos_a": len(sa), "archivos_b": len(sb), "iguales": len(set(sa) & set(sb)) - len([k for k in dist if k in sa and k in sb]),
       "distintos": dist, "unidades_a": A["unidades"], "unidades_b": B["unidades"],
       "unidades_por_to_iguales": A["unidades_por_to"] == B["unidades_por_to"],
       "codigo_sha256_iguales": A["codigo_sha256"] == B["codigo_sha256"]}
x.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
