"""U-SEG-OFICIAL, S1-quater (sorteo), paso 3: control en cuentas de la lista de regresión de `regresion_S1quater.py` (USD 0, sin API).

Uso: python -B control_regresion_S1quater_sorteo.py --regresion <NO_ABRIR_regresion_S1quater.json> --sha <sha256 sellado>
       --out <json de cuentas>

Lee el JSON de la regresión con un script y escribe solo cuentas y sha256; nunca ids, texto ni nombres de documento.
- La lista: unidades y sha256 de los ids ordenados, recalculado y comparado con el del JSON y con el esperado (la corrida de la mesa
  citada en el despacho de este paso).
- Los errores confirmados de S1-ter, por origen (`marca`, `la_que_sigue`, `herencia`); las unidades viejas y las nuevas.
- Las unidades viejas sin unidad nueva que las solape: cuántas, y su reparto por documento como lista anónima de cuentas, con la
  marca de si la cobertura de ese documento queda bajo el umbral.
Sale con código 1 si algo de lo que tiene valor esperado no da.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

N_ESPERADO = 60
SHA_ESPERADO = "57e904461ab0f5b6cfbc8baae0cac870a2b6ddb92fddc24197cfa2621f7f5cb8"
SIN_NUEVA_ESPERADO = 3
UMBRAL = 0.95


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regresion", type=Path, required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("FRENO: la salida ya existe")
    b = a.regresion.read_bytes()
    c: dict = {"control": "lista de regresión de S1-quater, en cuentas",
               "hora": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
               "sha256_json": hashlib.sha256(b).hexdigest()}
    c["sha256_json_ok"] = c["sha256_json"] == a.sha
    r = json.loads(b)
    ids = r["ids"]
    c["unidades"] = len(ids)
    c["sha256_ids_ordenados"] = sha_ids(sorted(ids))
    c["sha256_ids_ordenados_json"] = r["sha256_ids_ordenados"]
    c["ordenados_y_sin_repetir"] = ids == sorted(set(ids))
    c["errores_confirmados_S1ter"] = len(r["errores_confirmados_S1ter"])
    c["errores_por_origen"] = dict(Counter(x["por"] for x in r["errores_confirmados_S1ter"]))
    c["errores_sin_unidades"] = sum(1 for x in r["errores_confirmados_S1ter"] if not x["unidades"])
    c["unidades_viejas"] = len(r["unidades_viejas"])
    c["documentos_de_las_viejas"] = len(r["cobertura_por_to"])
    c["documentos_bajo_el_umbral"] = sum(1 for v in r["cobertura_por_to"].values() if v < UMBRAL)
    sin = r["sin_unidad_nueva"]
    c["sin_unidad_nueva"] = len(sin)
    por_doc = Counter(u.split("::")[0] for u in sin)
    c["sin_unidad_nueva_por_documento"] = sorted(([n, r["cobertura_por_to"][t] < UMBRAL] for t, n in por_doc.items()),
                                                 reverse=True)
    c["sin_unidad_nueva_formato"] = "[unidades, cobertura del documento bajo el umbral]"
    c["nuevas_unidas_desde_viejas"] = len({n for v in r["unidades_nuevas_de"].values() for n in v})
    c["insumos"] = r["insumos"]
    c["sellado_en_json"] = r["sellado"]
    ok = (c["sha256_json_ok"] and c["unidades"] == N_ESPERADO and c["sha256_ids_ordenados"] == c["sha256_ids_ordenados_json"]
          == SHA_ESPERADO and c["ordenados_y_sin_repetir"] and c["sin_unidad_nueva"] == SIN_NUEVA_ESPERADO
          and c["nuevas_unidas_desde_viejas"] == c["unidades"])
    c["ok"] = ok
    a.out.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(c, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
