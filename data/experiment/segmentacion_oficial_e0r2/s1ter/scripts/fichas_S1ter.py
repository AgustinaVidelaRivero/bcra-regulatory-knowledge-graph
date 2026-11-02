"""U-SEG-OFICIAL, S1-ter-b.3: las fichas de la lectora, desde el orden de lectura sellado (USD 0). No marca.

Uso: python -B fichas_S1ter.py --orden <tramo_b/orden_lectura_S1ter.json> --sha <sha256 sellado> --e0 <s1ter/e0>
       --pdfs <escalado_prep/pdfs> --out <carpeta de la lectora, armada en el scratchpad> --registro <json>
       --planillas <directorio de las planillas vacías>

Escribe en `--out` una subcarpeta por etapa (`etapa_1/`, `etapa_2/`), cada una con sus fichas (`fichas_etapa_N.md`), la
imagen de cada página que muestra (`E1-001_p12.png`; `pdftoppm -r 110 -png -singlefile`, como en S1-bis) y su
`manifest.txt` (sha256, bytes y una línea por archivo). Nada más: ni la lista sellada, ni las semillas, ni nada que diga
población, estrato, regla, tanda o límite declarado.
- Cada ficha muestra solo su id opaco, sus páginas y su texto: el texto que la unidad hereda (los títulos que la
  preceden, sin su tipo) y su texto propio, como sale de E0, con un solo cambio: el marcador de una tabla serializada
  (`[TABLA <to>::tablaNNN | …]` y `[FIN TABLA <to>::tablaNNN]`) se muestra sin el prefijo del TO, porque lo nombra; el
  script se detiene si en una ficha queda «::». Si la unidad es una parte de un punto partido por tamaño,
  lo dice (parte N de M), porque la parte es lo que se califica. No muestra el id de la unidad, el TO, el tipo ni el rol.
- Etapa 1 (lectura de cortes): la unidad.
- Etapa 2 (1.16): la unidad que se califica, con todas sus partes si está partida por tamaño, y la unidad que le sigue
  en el documento (sus páginas y su texto propio). Así, en una lista de (b) se ve el último ítem entero y su cierre
  (decisión 5 de la autora sobre el FRENO S1-ter-a), con el mismo formato que las demás fichas. Imágenes: las páginas de
  la unidad y la primera de la que le sigue.
Escribe además `--registro` (sha256 de cada archivo de la carpeta, por etapa, y el comando de las imágenes) y, en
`--planillas`, una planilla vacía por etapa con los ids opacos y las columnas de la lectura de S1-bis.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

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


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("orden", "sha", "e0", "pdfs", "out", "registro", "planillas"):
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    raw = Path(a.orden).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.sha, "el orden de lectura no da su sha256 sellado"
    orden = json.loads(raw)
    e0, pdfs, out = Path(a.e0), Path(a.pdfs), Path(a.out)
    cache: dict[str, list] = {}

    def chunks(to: str) -> list:
        if to not in cache:
            cache[to] = json.loads((e0 / f"chunks_{to}.json").read_text(encoding="utf-8"))
        return cache[to]

    def por_id(uid: str) -> dict:
        return next(c for c in chunks(uid.split("::")[0]) if c["id"] == uid)

    def partes(uid: str) -> list[dict]:
        L = chunks(uid.split("::")[0])
        exacto = [c for c in L if c["id"] == uid]
        if exacto:
            return exacto
        ps = [c for c in L if RE_PARTE.match(c["id"]) and RE_PARTE.match(c["id"]).group(1) == uid]
        assert ps, uid
        return sorted(ps, key=lambda c: int(RE_PARTE.match(c["id"]).group(2)))

    def siguiente(uid: str) -> dict | None:
        L = chunks(uid.split("::")[0])
        ids = [c["id"] for c in L]
        k = max(ids.index(c["id"]) for c in partes(uid))
        return L[k + 1] if k + 1 < len(L) else None

    def de_m(c: dict) -> str | None:
        m = RE_PARTE.match(c["id"])
        if not m:
            return None
        total = sum(1 for x in chunks(c["id"].split("::")[0]) if RE_PARTE.match(x["id"])
                    and RE_PARTE.match(x["id"]).group(1) == m.group(1))
        return f"{m.group(2)} de {total}"

    def render(to: str, pagina: int, destino: Path) -> None:
        pre = destino.with_suffix("")
        subprocess.run(["pdftoppm", "-r", "110", "-png", "-f", str(pagina), "-l", str(pagina), "-singlefile",
                        str(pdfs / f"{to}.pdf"), str(pre)], check=True, capture_output=True)

    def heredado(c: dict) -> list[str]:
        L = ["- texto heredado:" + ("" if c["herencia"] else " (ninguno)")]
        L += [f"  - «{sin_to(t['texto']).replace(chr(10), ' / ')}»" for t in c["herencia"]]
        return L

    registro = {"comando_imagenes": "pdftoppm -r 110 -png -f p -l p -singlefile", "etapas": {}}
    for etapa in (1, 2):
        d = out / f"etapa_{etapa}"
        d.mkdir(parents=True, exist_ok=False)
        fichas = orden[f"etapa_{etapa}"]["fichas"]
        L = [x.format(n=len(fichas)) for x in CABECERA[etapa]]
        filas = []
        for f in fichas:
            op, uid = f["id_opaco"], f["id"]
            to = uid.split("::")[0]
            ps = partes(uid)
            pags = sorted({p for c in ps for p in c["paginas"]})
            sig = siguiente(uid) if etapa == 2 else None
            img_pags = list(pags)
            if sig is not None and min(sig["paginas"]) not in img_pags:
                img_pags.append(min(sig["paginas"]))
            imgs = []
            for p in img_pags:
                n = f"{op}_p{p}.png"
                render(to, p, d / n)
                imgs.append(n)
            L += [f"## {op}", ""]
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
            filas.append({"ficha": op, "paginas": ",".join(map(str, pags))})
        texto_fichas = "\n".join(L) + "\n"
        if "::" in texto_fichas:
            raise SystemExit(f"FRENO: queda «::» en las fichas de la etapa {etapa}")
        (d / f"fichas_etapa_{etapa}.md").write_text(texto_fichas, encoding="utf-8")
        archivos = sorted(p for p in d.iterdir() if p.is_file() and p.name != ".DS_Store")
        lineas = [f"Carpeta de la lectora, etapa {etapa}: {len(archivos)} archivos (más este manifest)",
                  "sha256  bytes  archivo — descripción"]
        for p in archivos:
            desc = (f"las {len(fichas)} fichas de la etapa {etapa}" if p.suffix == ".md" else
                    f"imagen de la página {p.stem.split('_p')[1]} del PDF, ficha {p.stem.split('_p')[0]}")
            lineas.append(f"{sha(p)}  {p.stat().st_size}  {p.name} — {desc}")
        (d / "manifest.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
        registro["etapas"][f"etapa_{etapa}"] = {"fichas": len(fichas), "imagenes": len(archivos) - 1,
                                               "manifest_sha256": sha(d / "manifest.txt"),
                                               "sha256": {p.name: sha(p) for p in archivos}}
        pl = Path(a.planillas) / f"planilla_etapa_{etapa}_S1ter.tsv"
        with open(pl, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNAS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for x in filas:
                w.writerow({c: x.get(c, "") for c in COLUMNAS})
    Path(a.registro).write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "sha256"} for k, v in registro["etapas"].items()},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
