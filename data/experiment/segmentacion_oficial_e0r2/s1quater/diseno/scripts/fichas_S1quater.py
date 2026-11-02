"""U-SEG-OFICIAL, S1-quater: las fichas de la lectora, desde el orden de lectura sellado (mesa, 11/10/2026; USD 0). No marca.
Fijado y sellado antes de que exista la E0 corregida (`../diseno_S1quater.md`, §5).

Uso: python3 -B fichas_S1quater.py --orden <orden_lectura_S1quater.json> --sha-orden <sha256 sellado> --e0 <e0/ de la E0 corregida>
       --pdfs <escalado_prep/pdfs> --out <carpeta de la lectora, nueva, en el scratchpad> --registro <json nuevo>
       --planillas <carpeta nueva para las planillas vacías> [--sufijo S1quater]

Las fichas de S1-ter en su forma final (la de S1-ter-b2: `s1ter/scripts/fichas_S1ter.py` más `s1ter/scripts/fichas_numero_S1ter.py`),
armadas en una sola pasada. Las constantes de formato (encabezados, columnas, marcador de tabla, regla del número y su renglón) son
copia literal de esos dos scripts en HEAD `79ca1943`.
- Etapa 1 (las 90 de cortes): cada ficha muestra su id opaco, el número que la segmentación le asignó a la unidad, sus páginas con
  la imagen de cada una, el texto heredado y el texto propio. Si la unidad es una parte de un punto partido por tamaño, lo dice.
- Etapa 2 (la regresión): la unidad que se califica (todas sus partes, si está partida) y la que le sigue en el documento, con la
  imagen de cada página de las dos.
- No muestra el id de la unidad, el TO, el tipo, el rol, el estrato ni la población; frena si en una ficha queda «::».
- Escribe `--registro` (sha256 de cada archivo de la carpeta, por etapa) y, en `--planillas`, una planilla vacía por etapa con los
  ids opacos y las columnas de la lectura de S1-ter.
Con el orden y la E0 de S1-ter (`--sufijo S1ter`), reproduce byte a byte las dos carpetas finales de S1-ter (`prueba_S1quater.py`).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_S1quater as Q  # noqa: E402

# ---- copia literal de s1ter/scripts/fichas_S1ter.py:34-51 ----
COLUMNAS = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
RE_PARTE = re.compile(r"^(.*)::parte(\d+)$")
RE_MARCA_TABLA = re.compile(r"\[(FIN )?TABLA [^\s|\]]+::(tabla\d+)")


def sin_to(texto: str) -> str:
    """El texto de E0 con el marcador de tabla sin el prefijo del TO."""
    return RE_MARCA_TABLA.sub(r"[\1TABLA \2", texto)
CABECERA = {
    1: ["# Lectura de segmentación — etapa 1", "",
        "{n} fichas, en el orden de lectura. Cada ficha trae su id, las páginas del PDF donde está la unidad (con la imagen "
        "de cada una en esta carpeta), el texto que la unidad hereda (los títulos que la preceden) y su texto propio, como "
        "sale de la segmentación.", ""],
    2: ["# Lectura de segmentación — etapa 2", "",
        "{n} fichas, en el orden de lectura. Cada ficha trae la unidad que se califica (las páginas del PDF donde está, con "
        "la imagen de cada una en esta carpeta, el texto que hereda y su texto propio) y la unidad que le sigue en el "
        "documento (sus páginas y su texto propio), para ver dónde termina la primera y dónde empieza la segunda.", ""]}
# ---- copia literal de s1ter/scripts/fichas_numero_S1ter.py:28-30 y :39-41 ----
RX_NUMERO = re.compile(r"(?:[A-Z]\.)?\d+(?:\.\d+)*|[A-Z](?:\.\d+)+")
RENGLON = "- número que le asignó la segmentación: "


def numero(unidad: str) -> str:
    seg = [s for s in unidad.split("::") if RX_NUMERO.fullmatch(s)]
    return seg[-1] if seg else "sin número"
# ---- fin de las copias ----

COMANDO_IMAGENES = "pdftoppm -r 110 -png -f p -l p -singlefile"


def heredado(c: dict) -> list[str]:
    L = ["- texto heredado:" + ("" if c["herencia"] else " (ninguno)")]
    L += [f"  - «{sin_to(t['texto']).replace(chr(10), ' / ')}»" for t in c["herencia"]]
    return L


def escribir_manifest(d: Path, n_fichas: int, etapa: int) -> None:
    archivos = sorted(p for p in d.iterdir() if p.is_file() and p.name not in ("manifest.txt", ".DS_Store"))
    lineas = [f"Carpeta de la lectora, etapa {etapa}: {len(archivos)} archivos (más este manifest)",
              "sha256  bytes  archivo — descripción"]
    for p in archivos:
        desc = (f"las {n_fichas} fichas de la etapa {etapa}" if p.suffix == ".md" else
                f"imagen de la página {p.stem.split('_p')[1]} del PDF, ficha {p.stem.split('_p')[0]}")
        lineas.append(f"{Q.sha(p)}  {p.stat().st_size}  {p.name} — {desc}")
    (d / "manifest.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("orden", "sha_orden", "e0", "pdfs", "out", "registro", "planillas"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    ap.add_argument("--sufijo", default="S1quater")
    a = ap.parse_args()
    orden = json.loads(Q.leer_sellado(Path(a.orden), a.sha_orden, "el orden de lectura"))
    e0, pdfs, out, pl_dir = Q.E0(Path(a.e0)), Path(a.pdfs), Path(a.out), Path(a.planillas)
    if out.exists() or pl_dir.exists() or Path(a.registro).exists():
        raise SystemExit("FRENO: la carpeta, las planillas o el registro ya existen")
    pl_dir.mkdir(parents=True)

    def de_m(c: dict) -> str | None:
        m = RE_PARTE.match(c["id"])
        if not m:
            return None
        total = sum(1 for x in e0.chunks(c["id"].split("::")[0]) if RE_PARTE.match(x["id"])
                    and RE_PARTE.match(x["id"]).group(1) == m.group(1))
        return f"{m.group(2)} de {total}"

    def render(to: str, pagina: int, destino: Path) -> None:
        subprocess.run(["pdftoppm", "-r", "110", "-png", "-f", str(pagina), "-l", str(pagina), "-singlefile",
                        str(pdfs / f"{to}.pdf"), str(destino.with_suffix(""))], check=True, capture_output=True)

    registro = {"comando_imagenes": COMANDO_IMAGENES, "regla_del_numero": RX_NUMERO.pattern, "renglon": RENGLON, "etapas": {}}
    for etapa in (1, 2):
        fichas = orden[f"etapa_{etapa}"]["fichas"]
        if not fichas:
            registro["etapas"][f"etapa_{etapa}"] = {"fichas": 0}
            continue
        d = out / f"etapa_{etapa}"
        d.mkdir(parents=True)
        L = [x.format(n=len(fichas)) for x in CABECERA[etapa]]
        filas, num = [], {}
        for f in fichas:
            op, uid = f["id_opaco"], f["id"]
            to = uid.split("::")[0]
            ps = e0.partes(uid)
            pags = sorted({p for c in ps for p in c["paginas"]})
            sig = e0.siguiente(uid) if etapa == 2 else None
            img_pags = list(pags)
            if sig is not None and min(sig["paginas"]) not in img_pags:
                img_pags.append(min(sig["paginas"]))
            imgs = []
            for p in img_pags:
                n = f"{op}_p{p}.png"
                render(to, p, d / n)
                imgs.append(n)
            num[op] = numero(e0.por_id(uid if etapa == 1 else f["unidades_calificadas"][0])["unidad"])
            L += [f"## {op}", "", RENGLON + num[op]]
            if etapa == 1:
                c = ps[0]
                L.append(f"- páginas: {', '.join(map(str, pags))} (imágenes: {', '.join(f'`{i}`' for i in imgs)})")
                if de_m(c):
                    L.append(f"- esta unidad es la parte {de_m(c)} de un punto partido por tamaño")
                L += heredado(c) + ["- texto propio:", "", "```text", sin_to(c["texto"]), "```", ""]
            else:
                L.append(f"- páginas de la unidad: {', '.join(map(str, pags))} (imágenes: "
                         f"{', '.join(f'`{i}`' for i in imgs)})")
                L += heredado(ps[0])
                if len(ps) > 1:
                    L.append(f"- texto propio: la unidad está partida por tamaño en {len(ps)} partes, una después de otra")
                    for k, c in enumerate(ps, 1):
                        L += ["", f"  parte {k} de {len(ps)}:", "", "```text", sin_to(c["texto"]), "```"]
                    L.append("")
                else:
                    L += ["- texto propio:", "", "```text", sin_to(ps[0]["texto"]), "```", ""]
                if sig is None:
                    L += ["- la unidad que le sigue: ninguna (es la última unidad del documento)", ""]
                else:
                    L += [f"- la unidad que le sigue en el documento: páginas {', '.join(map(str, sig['paginas']))}; "
                          f"su texto propio:", "", "```text", sin_to(sig["texto"]), "```", ""]
                    for p in sig["paginas"]:
                        img = d / f"{op}_p{p}.png"
                        if not img.exists():
                            render(to, p, img)
            filas.append({"ficha": op, "paginas": ",".join(map(str, pags))})
        texto_fichas = "\n".join(L) + "\n"
        if "::" in texto_fichas:
            raise SystemExit(f"FRENO: queda «::» en las fichas de la etapa {etapa}")
        (d / f"fichas_etapa_{etapa}.md").write_text(texto_fichas, encoding="utf-8")
        escribir_manifest(d, len(fichas), etapa)
        archivos = sorted(p for p in d.iterdir() if p.is_file() and p.name != "manifest.txt")
        registro["etapas"][f"etapa_{etapa}"] = {"fichas": len(fichas), "imagenes": len(archivos) - 1,
                                               "manifest_sha256": Q.sha(d / "manifest.txt"),
                                               "sha256": {p.name: Q.sha(p) for p in archivos}, "numero_por_ficha": num}
        pl = pl_dir / f"planilla_etapa_{etapa}_{a.sufijo}.tsv"
        with open(pl, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNAS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for x in filas:
                w.writerow({c: x.get(c, "") for c in COLUMNAS})
        registro["etapas"][f"etapa_{etapa}"]["planilla_sha256"] = Q.sha(pl)
    Path(a.registro).write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"fichas escritas en {out}; registro {a.registro}, sha256 {Q.sha(Path(a.registro))}")


if __name__ == "__main__":
    main()
