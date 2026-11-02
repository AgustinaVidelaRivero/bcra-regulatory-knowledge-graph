"""U-SEG-OFICIAL, S1-quater (fichas): prueba de `control_fichas_S1quater_fichas.py` con una carpeta inventada (USD 0, sin API).

Uso: python -B prueba_control_fichas_S1quater_fichas.py --trabajo <carpeta nueva>

Arma una carpeta de la lectora inventada (dos fichas en la etapa 1, una en la etapa 2, con ids inventados), su registro y sus
planillas, con el formato de `fichas_S1quater.py`. El control tiene que dar ok sobre ella y MAL en cada una de las roturas: una
imagen de más, una ficha sin imagen, un archivo ajeno, una planilla con una marca, un manifest con una fila de menos y un orden que
no da su sello. Imprime solo «ok» o «MAL» por caso.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
COLUMNAS = ["ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def armar(T: Path) -> tuple[Path, str]:
    orden = {"etapa_1": {"fichas": [{"id_opaco": "E1-001", "id": "inventada_1"}, {"id_opaco": "E1-002", "id": "inventada_2"}]},
             "etapa_2": {"fichas": [{"id_opaco": "E2-001", "id": "inventada_3", "unidades_calificadas": ["inventada_3"]}]}}
    T.mkdir(parents=True)
    (T / "orden.json").write_text(json.dumps(orden), encoding="utf-8")
    reg = {"etapas": {}}
    for n, ops in ((1, ["E1-001", "E1-002"]), (2, ["E2-001"])):
        d = T / "carpeta" / f"etapa_{n}"
        d.mkdir(parents=True)
        L = [f"# etapa {n}", ""]
        for op in ops:
            L += [f"## {op}", "", "```text", "## renglón del texto que no es una ficha", "```", ""]
            (d / f"{op}_p1.png").write_bytes(op.encode())
        (d / f"fichas_etapa_{n}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        archivos = sorted(p for p in d.iterdir() if p.is_file())
        (d / "manifest.txt").write_text("\n".join([f"Carpeta, etapa {n}", "sha256  bytes  archivo — descripción"]
                                                  + [f"{sha(p)}  {p.stat().st_size}  {p.name} — x" for p in archivos]) + "\n",
                                        encoding="utf-8")
        pl = T / "planillas" / f"planilla_etapa_{n}_S1quater.tsv"
        pl.parent.mkdir(exist_ok=True)
        with open(pl, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNAS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for op in ops:
                w.writerow({c: (op if c == "ficha" else "1" if c == "paginas" else "") for c in COLUMNAS})
        reg["etapas"][f"etapa_{n}"] = {"fichas": len(ops), "imagenes": len(ops), "manifest_sha256": sha(d / "manifest.txt"),
                                       "sha256": {p.name: sha(p) for p in archivos},
                                       "numero_por_ficha": {op: "sin número" for op in ops}, "planilla_sha256": sha(pl)}
    (T / "registro.json").write_text(json.dumps(reg), encoding="utf-8")
    return T, sha(T / "orden.json")


def control(T: Path, sha_orden: str, nombre: str) -> int:
    r = subprocess.run([sys.executable, "-B", str(AQUI / "control_fichas_S1quater_fichas.py"), "--carpeta", str(T / "carpeta"),
                        "--registro", str(T / "registro.json"), "--planillas", str(T / "planillas"), "--orden",
                        str(T / "orden.json"), "--sha-orden", sha_orden, "--out", str(T / f"{nombre}.json")],
                       capture_output=True, text=True)
    return r.returncode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trabajo", type=Path, required=True)
    a = ap.parse_args()
    if a.trabajo.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    res = []
    T, s = armar(a.trabajo / "base")
    res.append((control(T, s, "base") == 0, "la carpeta inventada da ok"))

    def roto(nombre: str, romper, que: str, sha_orden: str | None = None) -> None:
        R = a.trabajo / nombre
        shutil.copytree(T, R)
        for p in R.glob("*.json"):
            if p.name not in ("orden.json", "registro.json"):
                p.unlink()
        romper(R)
        res.append((control(R, sha_orden or s, nombre) == 1, que))

    roto("imagen_de_mas", lambda R: (R / "carpeta/etapa_1/E1-009_p1.png").write_bytes(b"x"),
         "MAL con una imagen de un id opaco ajeno")
    roto("ficha_sin_imagen", lambda R: (R / "carpeta/etapa_1/E1-002_p1.png").unlink(), "MAL con una ficha sin imagen")
    roto("archivo_ajeno", lambda R: (R / "carpeta/etapa_2/notas.txt").write_text("x"), "MAL con un archivo ajeno en una etapa")
    roto("raiz", lambda R: (R / "carpeta/notas.txt").write_text("x"), "MAL con un archivo en la raíz de la carpeta")

    def marcar(R: Path) -> None:
        p = R / "planillas/planilla_etapa_1_S1quater.tsv"
        p.write_text(p.read_text(encoding="utf-8").replace("E1-002\t1\t", "E1-002\t1\terror"), encoding="utf-8")
    roto("planilla_marcada", marcar, "MAL con una planilla que trae una marca")

    def manifest_corto(R: Path) -> None:
        p = R / "carpeta/etapa_2/manifest.txt"
        p.write_text("\n".join(p.read_text(encoding="utf-8").splitlines()[:-1]) + "\n", encoding="utf-8")
    roto("manifest_corto", manifest_corto, "MAL con un manifest con una fila de menos")
    roto("orden_sin_sello", lambda R: None, "frena con un orden que no da su sello", "0" * 64)
    for b, q in res:
        print(("ok   " if b else "MAL  ") + q)
    print(f"{sum(b for b, _ in res)} de {len(res)} casos ok")
    sys.exit(0 if all(b for b, _ in res) else 1)


if __name__ == "__main__":
    main()
