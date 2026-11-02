"""Genera el documento de lectura tipo_pregunta_lectura.md a partir de la hoja.

Una sección por pregunta en el orden de la columna `orden`: título con orden,
id y to; la pregunta; el ancla; los criterios numerados; el texto del ancla tal
cual está en la hoja. Al final, la sección «Tipos» copiada literal de la regla.
Misma lógica que la corrida inline de U-EV2-TIPO-2; `--out` permite reproducir
a otra ruta sin tocar el archivo sellado.
"""
import argparse, csv, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
D = REPO / "data/experiment/exploracion/ev2_fidelidad"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoja", default=str(D / "tipo_pregunta_hoja.csv"))
    ap.add_argument("--regla", default=str(D / "regla_tipo_pregunta.md"))
    ap.add_argument("--out", default=str(D / "tipo_pregunta_lectura.md"))
    a = ap.parse_args()
    OUT = Path(a.out)
    assert not OUT.exists(), "FRENO: lectura ya existe"
    rows = list(csv.DictReader(open(a.hoja, encoding="utf-8", newline="")))
    rows.sort(key=lambda r: int(r["orden"]))
    assert len(rows) == 40
    regla = open(a.regla, encoding="utf-8").read()
    m = re.search(r"^## Tipos\n(.*?)(?=^## )", regla, flags=re.S | re.M)
    tipos_block = "## Tipos\n" + m.group(1)
    out = []
    for r in rows:
        out.append(f"## Orden {r['orden']} — {r['id']} — {r['to']}\n\n")
        out.append(f"Pregunta: {r['pregunta']}\n\n")
        out.append(f"Ancla: {r['ancla']}\n\n")
        out.append("Criterios:\n\n")
        for i, c in enumerate(r["criterios"].split(" | "), 1):
            out.append(f"{i}. {c}\n")
        out.append("\nTexto del ancla:\n\n")
        out.append(r["texto_ancla"] + "\n\n")
    out.append(tipos_block.rstrip("\n") + "\n")
    text = "".join(out)
    OUT.write_text(text, encoding="utf-8")
    md = OUT.read_text(encoding="utf-8")
    print("secciones '## Orden':", len(re.findall(r"^## Orden \d+ — EV2F-\d{3} — [a-z]{3}$", md, flags=re.M)))
    print("texto_ancla verbatim en md (40 esperado):", sum(1 for r in rows if ("\n\n" + r["texto_ancla"] + "\n\n") in md))
    print("bloque Tipos al final (literal de la regla):", md.endswith(tipos_block.rstrip("\n") + "\n"))
    print("escrito:", OUT)


if __name__ == "__main__":
    main()
