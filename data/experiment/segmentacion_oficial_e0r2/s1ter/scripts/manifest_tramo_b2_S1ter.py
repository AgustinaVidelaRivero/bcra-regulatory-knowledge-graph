"""U-SEG-OFICIAL, S1-ter-b2: `tramo_b2/manifest_tramo_b2_S1ter.json` (sha256 de lo que escribió S1-ter-b2 en `s1ter/` y del
`manifest.txt` de cada etapa de la carpeta de la lectora) (USD 0).

Uso: python -B manifest_tramo_b2_S1ter.py --s1ter <carpeta s1ter> --lectora <carpeta de la lectora>

Recorre `s1ter/tramo_b2/` (salvo este manifiesto y el FRENO, que cita su sha256) y los scripts nuevos de S1-ter-b2. Ningún
`.DS_Store` entra.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCRIPTS = ("fichas_numero_S1ter.py", "controles_fichas_numero_S1ter.py", "aplicar_adjudicacion_S1ter.py",
           "prueba_aplicar_adjudicacion_S1ter.py", "manifest_tramo_b2_S1ter.py")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1ter", type=Path, required=True)
    ap.add_argument("--lectora", type=Path, required=True)
    a = ap.parse_args()
    arch = {}
    for p in sorted((a.s1ter / "tramo_b2").rglob("*")):
        if p.is_file() and p.name not in ("manifest_tramo_b2_S1ter.json", ".DS_Store") and not p.name.startswith("FRENO_"):
            arch[p.relative_to(a.s1ter).as_posix()] = {"sha256": sha(p), "bytes": p.stat().st_size}
    for n in SCRIPTS:
        p = a.s1ter / "scripts" / n
        arch[f"scripts/{n}"] = {"sha256": sha(p), "bytes": p.stat().st_size}
    m = {"unidad": "U-SEG-OFICIAL, S1-ter-b2 (mandato firmado en e543cb2)",
         "carpeta_de_la_lectora": {"ruta": "$BCRA_KG_FUERA_DEL_REPO/lecturas_ciegas/lectura_segmentacion_s1ter/",
                                   "manifest_por_etapa": {d.name: sha(d / "manifest.txt")
                                                          for d in sorted(a.lectora.iterdir()) if d.is_dir()}},
         "archivos": len(arch), "sha256": arch}
    (a.s1ter / "tramo_b2" / "manifest_tramo_b2_S1ter.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n",
                                                                       encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k != "sha256"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
