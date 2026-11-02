"""U-SEG-OFICIAL, S1-ter-b: `tramo_b/manifest_tramo_b_S1ter.json` (sha256 de lo que escribió el tramo b en `s1ter/` y de la
carpeta de la lectora, y los comandos) (USD 0).

Uso: python -B manifest_tramo_b_S1ter.py --s1ter <carpeta s1ter> --lectora <carpeta de la lectora>

Recorre `s1ter/tramo_b/` (salvo este manifiesto) y los scripts del tramo b; de la carpeta de la lectora, el sha256 del
`manifest.txt` de cada etapa. El FRENO del tramo queda fuera, porque cita el sha256 de este manifiesto. Ningún
`.DS_Store` entra.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCRIPTS = ("poblaciones_finales_S1ter.py", "sorteo_S1ter.py", "reproducir_sorteo_S1ter.py", "fichas_S1ter.py",
           "control_ciego_fichas_S1ter.py", "verificar_carpeta_lectora_S1ter.py", "cifras_lectura_S1ter.py",
           "lista_para_la_autora_S1ter.py", "prueba_cifras_S1ter.py", "manifest_tramo_b_S1ter.py")
COMANDOS = [
    "scripts/poblaciones_finales_S1ter.py --poblaciones poblaciones_S1ter.json --controles controles_S1ter.json "
    "--manifiesto manifiesto/segmentacion_oficial_e0r2_152.json --out tramo_b/poblaciones_finales_S1ter.json",
    "scripts/sorteo_S1ter.py --poblaciones-finales tramo_b/poblaciones_finales_S1ter.json --sha <sha sellado> "
    "--muestra tramo_b/muestra_S1ter.json --orden tramo_b/orden_lectura_S1ter.json",
    "scripts/reproducir_sorteo_S1ter.py tramo_b > tramo_b/controles/reproduccion_sorteo_S1ter_b.txt",
    "scripts/fichas_S1ter.py --orden tramo_b/orden_lectura_S1ter.json --sha <sha sellado> --e0 e0 "
    "--pdfs <copia>/data/experiment/escalado_prep/pdfs --out <carpeta en el scratchpad> "
    "--registro tramo_b/fichas_registro_S1ter.json --planillas tramo_b",
    "ditto <carpeta en el scratchpad> <carpeta de la lectora>",
    "scripts/control_ciego_fichas_S1ter.py <carpeta de la lectora> manifiesto/segmentacion_oficial_e0r2_152.json "
    "tramo_b/orden_lectura_S1ter.json > tramo_b/controles/control_ciego_carpeta_lectora_S1ter_b.txt",
    "scripts/verificar_carpeta_lectora_S1ter.py <carpeta de la lectora> > tramo_b/controles/verificacion_carpeta_lectora_S1ter_b.txt",
    "scripts/prueba_cifras_S1ter.py --orden tramo_b/orden_lectura_S1ter.json --sha-orden <sha sellado> "
    "--poblaciones-finales tramo_b/poblaciones_finales_S1ter.json --poblaciones poblaciones_S1ter.json "
    "--trabajo <scratchpad> > tramo_b/prueba_cifras_S1ter_b.txt",
    "scripts/lista_para_la_autora_S1ter.py --vacia --out tramo_b/lista_para_la_autora_S1ter_vacia.md",
    "después de la lectura: scripts/lista_para_la_autora_S1ter.py --orden … --sha-orden … --planilla-1 … --planilla-2 … "
    "--out …; y, después de la adjudicación, scripts/cifras_lectura_S1ter.py --orden … --sha-orden … "
    "--poblaciones-finales … --poblaciones poblaciones_S1ter.json --planilla-1 … --planilla-2 … --out …",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1ter", type=Path, required=True)
    ap.add_argument("--lectora", type=Path, required=True)
    a = ap.parse_args()
    arch = {}
    for p in sorted((a.s1ter / "tramo_b").rglob("*")):
        if p.is_file() and p.name not in ("manifest_tramo_b_S1ter.json", ".DS_Store"):
            arch[p.relative_to(a.s1ter).as_posix()] = {"sha256": sha(p), "bytes": p.stat().st_size}
    for n in SCRIPTS:
        p = a.s1ter / "scripts" / n
        arch[f"scripts/{n}"] = {"sha256": sha(p), "bytes": p.stat().st_size}
    m = {"unidad": "U-SEG-OFICIAL, S1-ter-b (mandato firmado en e543cb2)", "comandos": COMANDOS,
         "carpeta_de_la_lectora": {"ruta": "$BCRA_KG_FUERA_DEL_REPO/lecturas_ciegas/lectura_segmentacion_s1ter/",
                                   "manifest_por_etapa": {d.name: sha(d / "manifest.txt")
                                                          for d in sorted(a.lectora.iterdir()) if d.is_dir()}},
         "archivos": len(arch), "sha256": arch}
    (a.s1ter / "tramo_b" / "manifest_tramo_b_S1ter.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n",
                                                                     encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k not in ("sha256", "comandos")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
