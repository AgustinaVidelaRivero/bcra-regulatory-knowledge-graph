"""U-SEG-OFICIAL, S1-bis-b.3: fichas de lectura y planillas de marcas vacías, desde la muestra sellada (USD 0). No marca.

Uso: python -B fichas_lectura_S1bis.py --muestra <muestra_cortes_S1bis.json> --renders <renders_S1-bis-b.json>
       --out <directorio del paquete>

Escribe en `--out`:
- `fichas_lectura_S1-bis-b.md`: una ficha por unidad de la muestra (primer grupo, ri_spi), por juicio (tercer grupo) y por
  candidato del censo del hallazgo 1.16 de la tanda 1, con su id, TO, grupo, páginas (y la imagen de cada una), tipo, rol,
  herencia y texto propio, como sale de E0; de un candidato del 1.16, además, la lista y el cierre candidato;
- `planilla_marcas_S1-bis-b.tsv`: una fila por unidad leída y por juicio, con las columnas de la lectura de S1 vacías salvo
  los dos juicios decididos (`acta_sorteo_S1bis.md`, §1);
- `planilla_1_16_S1-bis-b.tsv`: una fila por candidato del censo del 1.16, con las mismas columnas.
A ciegas, como la muestra: ninguna marca de límite declarado, de TO de la tanda 0 ni de candidato del 1.16 en la muestra.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

COLUMNAS = ("fila", "grupo", "id", "to", "paginas", "tipo", "marca", "clase", "subclase", "subclase_adicional",
            "limpieza", "nota")


def imagenes(to: str, paginas, renders: dict) -> str:
    out = []
    for p in paginas:
        n = f"{to}_p{p}.png"
        out.append(f"`{n}`" if n in renders else f"`{n}` (falta)")
    return ", ".join(out)


def bloque(u: dict, fila: int, renders: dict) -> list[str]:
    L = [f"### {fila}. {u['grupo']} — `{u['id']}`", "",
         f"- TO: {u['to']}; páginas: {', '.join(map(str, u['paginas']))} ({imagenes(u['to'], u['paginas'], renders)})",
         f"- tipo: {u['tipo']}; rol: {u['rol_bloque']}; caracteres propios: {u['chars_propio']}"]
    if "cierre_candidato" in u:
        L.append(f"- lista: hijos de `{u['padre']}`, {u['items_de_la_lista']} ítems; cierre candidato: «{u['cierre_candidato']}» "
                 f"({u['renglones_despues_del_corte']} renglones desde el corte)")
    L.append("- herencia:" + ("" if u["herencia"] else " (ninguna)"))
    L += [f"  - {t['tipo']}: «{t['texto'].replace(chr(10), ' / ')}»" for t in u["herencia"]]
    L += ["", "```text", u["texto_propio"], "```", ""]
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=Path, required=True)
    ap.add_argument("--renders", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    m = json.loads(a.muestra.read_text(encoding="utf-8"))
    renders = json.loads(a.renders.read_text(encoding="utf-8"))["sha256"]
    leidas = [u for g in m["primer_grupo"]["estratos"].values() for u in g["muestra"]] + m["ri_spi"]["muestra"]
    filas, L = [], ["# U-SEG-OFICIAL — S1-bis-b: fichas de lectura de cortes", "",
                    "Generadas desde `muestra_cortes_S1bis.json` (sellada; sha256 y hora en `sellos_S1bis_b.txt`). Criterio: la "
                    "nota del mandato de `2faff14` (lectura de cortes contra la página renderizada) y `acta_sorteo_S1bis.md`. "
                    "Las imágenes están en `paginas_S1-bis-b/` (`pdftoppm -r 110`). Las marcas van en `planilla_marcas_S1-bis-b.tsv` "
                    "y `planilla_1_16_S1-bis-b.tsv`.", "",
                    "## Primer grupo (90) y ri_spi (10, fuera del piso)", ""]
    for i, u in enumerate(leidas, 1):
        L += bloque(u, i, renders)
        filas.append({"fila": i, "grupo": u["grupo"], "id": u["id"], "to": u["to"],
                      "paginas": ",".join(map(str, u["paginas"])), "tipo": u["tipo"]})
    L += ["## Tercer grupo: juicios (11; 9 para leer)", "",
          "Juicio: que el documento no tenga una numeración de puntos que la segmentación debió reconocer.", ""]
    n = len(leidas)
    for to, j in m["tercer_grupo"]["por_to"].items():
        n += 1
        ps = list(range(1, j["paginas_del_pdf"] + 1))
        L.append(f"### {n}. G3-juicio — {to}")
        L.append("")
        if "decidido" in j:
            L.append(f"- **decidido antes de leer:** {j['decidido']['decision']}; no se vuelve a juzgar")
        else:
            L.append(f"- páginas del PDF: {j['paginas_del_pdf']} ({imagenes(to, ps, renders)})")
        L.append(f"- vía: {j['via']}; causa de la clase: {j['causa']}")
        L.append(f"- unidades de e0-r2 ({len(j['unidades_e0r2'])}): "
                 + "; ".join(f"`{x['id']}` (pp. {','.join(map(str, x['paginas']))}, {x['chars_propio']} caracteres)"
                             for x in j["unidades_e0r2"]))
        L.append("")
        f = {"fila": n, "grupo": "G3-juicio", "id": "(juicio del documento)", "to": to,
             "paginas": f"1-{j['paginas_del_pdf']}", "tipo": "juicio"}
        if "decidido" in j:
            f["marca"] = j["decidido"]["resultado"]
            f["nota"] = "decidido antes de leer (acta_sorteo_S1bis.md, §1, decisión 2)"
        filas.append(f)
    L += ["## Censo del hallazgo 1.16 de la tanda 1 (35 candidatos; cifra aparte del piso)", "",
          "Mismo criterio de cortes. Caso del hallazgo: el cierre de la lista queda dentro del último ítem. Un candidato que "
          "también salga en la muestra se lee en los dos y cuenta en los dos.", ""]
    f116 = []
    for i, u in enumerate(m["censo_1_16_tanda1"]["lista"], 1):
        L += bloque(u, i, renders)
        f116.append({"fila": i, "grupo": u["grupo"], "id": u["id"], "to": u["to"],
                     "paginas": ",".join(map(str, u["paginas"])), "tipo": u["tipo"]})
    (a.out / "fichas_lectura_S1-bis-b.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for nombre, fs in (("planilla_marcas_S1-bis-b.tsv", filas), ("planilla_1_16_S1-bis-b.tsv", f116)):
        with open(a.out / nombre, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNAS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for f in fs:
                w.writerow({c: f.get(c, "") for c in COLUMNAS})
    faltan = sum(1 for x in L if "(falta)" in x)
    print(json.dumps({"fichas_leidas": len(leidas), "juicios": n - len(leidas), "candidatos_1_16": len(f116),
                      "filas_planilla": len(filas), "imagenes_que_faltan": faltan}, ensure_ascii=False))


if __name__ == "__main__":
    main()
