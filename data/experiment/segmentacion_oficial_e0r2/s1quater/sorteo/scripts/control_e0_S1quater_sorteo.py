"""U-SEG-OFICIAL, S1-quater (sorteo), paso 1: control de la E0 regenerada contra el manifiesto de S0-6b (USD 0, sin API).

Uso: python -B control_e0_S1quater_sorteo.py --e0 <salida de correr_152.py> --manifest <manifest_salida_e0_152_S0-6b.json>
       --sha-manifest <sha256 sellado> --out <json de cuentas>

Controla, sin imprimir ids ni texto de unidades:
- el sha256 del manifiesto;
- que la carpeta tenga exactamente los archivos `e0/…` del manifiesto (los subdirectorios de trabajo de `correr_152.py`, como
  `por_to/`, no cuentan), y que cada uno dé su sha256;
- las unidades: la suma de las listas `chunks_<to>.json` contra `unidades` del manifiesto, y TO por TO contra `unidades_por_to`.
Escribe solo cuentas y sha256. Sale con código 1 si algo no da.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--sha-manifest", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("FRENO: la salida ya existe")
    c: dict = {"control": "E0 regenerada contra el manifiesto de S0-6b",
               "hora": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")}
    c["manifest_sha256"] = sha(a.manifest)
    c["manifest_sha256_ok"] = c["manifest_sha256"] == a.sha_manifest
    m = json.loads(a.manifest.read_bytes())
    e0 = {k[3:]: v["sha256"] for k, v in m["sha256"].items() if k.startswith("e0/")}
    presentes = {p.name for p in a.e0.iterdir() if p.is_file() and p.name != ".DS_Store"}
    c["archivos_manifiesto"] = len(e0)
    c["archivos_carpeta"] = len(presentes)
    c["faltan"] = len(set(e0) - presentes)
    c["sobran"] = len(presentes - set(e0))
    c["sha256_distinto"] = sum(1 for n, h in e0.items() if n in presentes and sha(a.e0 / n) != h)
    por_to = {p.name[len("chunks_"):-len(".json")]: len(json.loads(p.read_text(encoding="utf-8")))
              for p in sorted(a.e0.glob("chunks_*.json"))}
    c["tos"] = len(por_to)
    c["tos_manifiesto"] = m.get("tos")
    c["unidades"] = sum(por_to.values())
    c["unidades_manifiesto"] = m.get("unidades")
    esperado = m.get("unidades_por_to") or {}
    c["tos_con_cuenta_distinta"] = sum(1 for t in set(por_to) | set(esperado) if por_to.get(t) != esperado.get(t))
    c["ok"] = (c["manifest_sha256_ok"] and c["faltan"] == 0 and c["sobran"] == 0 and c["sha256_distinto"] == 0
               and c["archivos_carpeta"] == c["archivos_manifiesto"] and c["unidades"] == c["unidades_manifiesto"]
               and c["tos"] == c["tos_manifiesto"] and c["tos_con_cuenta_distinta"] == 0)
    a.out.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in c.items():
        print(f"{k}: {v}")
    sys.exit(0 if c["ok"] else 1)


if __name__ == "__main__":
    main()
