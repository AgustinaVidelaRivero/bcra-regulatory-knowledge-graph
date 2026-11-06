"""
selftest_control_sitio.py — U-MANT, etapa M2 (d): alteraciones simuladas sobre
copias de la línea de base, cada una con su aviso y solo el suyo.

Copia el índice y los 157 PDFs de la corrida del 2026-09-07 a un directorio de
trabajo FUERA del repo (--trabajo, obligatorio; el script frena si cae dentro
del repo), altera las copias y corre control_sitio.controlar sobre cada caso:

  base  sin alteración, re-midiendo todo           → código 0, sin aviso.md
  A1    una entrada sin la clave `titulo_truncado`  → solo S2
  A2    una entrada menos                           → solo S3
  A3    una URL con otro patrón                     → solo S4
  A4    un PDF sin portada (sin su página 1)         → solo S5
  A5    un PDF sin marcadores de página de E0        → solo S7
  A6    respuesta sin la lista `textos_ordenados`   → solo S1 (S2 a S4 no se miden)
  A7    un PDF sin el pie «Versión … COMUNICACIÓN»  → solo S6

A1 a A5 son las del mandato; A6 y A7 cubren los dos supuestos restantes.
Además verifica que la réplica de líneas de E0 del control
(control_sitio._lineas_e0) da el mismo texto que e0_lib.extraer_lineas en las
páginas de sondeo de tres PDFs.

Los PDFs alterados se escriben con pypdf: A4 quita la página 1; A5 y A7 quitan
bloques de texto (BT … ET) del pie, identificados por su posición (y < 80) y
por su texto. Ningún archivo del repo se escribe salvo --out.

Uso, desde la raíz del repo:
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
    data/experiment/mantenimiento/control_sitio/selftest_control_sitio.py \\
    --trabajo <dir fuera del repo> \\
    --out data/experiment/mantenimiento/control_sitio/selftest_control_sitio.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import control_sitio as C  # noqa: E402

PDF_ALTERADO = "capmin"            # TO de desarrollo, con portada, pie y marcadores
RE_MARCADOR = re.compile(r"^(Vigencia|P[aá]gina|\d{1,2}/\d{1,2}/\d{2,4}$)")
Y_PIE = 80.0                       # bloques de texto por debajo de esta altura (pt)
PDFS_REPLICA = ("ribspc", "ri_spi", "snp_psp")


# ------------------------------------------------------------------------- #
# Alteraciones de PDF                                                        #
# ------------------------------------------------------------------------- #

def _texto(op: bytes, args) -> str:
    from pypdf.generic import ByteStringObject, TextStringObject

    def s(o):
        return str(o) if isinstance(o, (TextStringObject, ByteStringObject, str)) else ""
    if op == b"Tj":
        return s(args[0])
    if op == b"TJ":
        return "".join(s(x) for x in args[0])
    return ""


def quitar_bloques(src: Path, dst: Path, pred) -> int:
    """Copia src en dst sin los bloques BT … ET cuyo texto y altura cumplen pred."""
    import pypdf
    from pypdf.generic import ContentStream
    w = pypdf.PdfWriter(clone_from=str(src))
    quitados = 0
    for page in w.pages:
        cs = ContentStream(page.get_contents(), w)
        nuevos, bloque, y, txt = [], None, 0.0, ""
        for args, op in cs.operations:
            if op == b"BT":
                bloque, y, txt = [(args, op)], 0.0, ""
                continue
            if bloque is not None:
                bloque.append((args, op))
                if op in (b"Td", b"TD"):
                    y += float(args[1])
                elif op == b"Tm":
                    y = float(args[5])
                txt += _texto(op, args)
                if op == b"ET":
                    if pred(txt.strip(), y):
                        quitados += 1
                    else:
                        nuevos.extend(bloque)
                    bloque = None
                continue
            nuevos.append((args, op))
        cs.operations = nuevos
        page.replace_contents(cs)
    w.write(str(dst))
    return quitados


def quitar_portada(src: Path, dst: Path) -> None:
    import pypdf
    w = pypdf.PdfWriter(clone_from=str(src))
    w.remove_page(0)
    w.write(str(dst))


# ------------------------------------------------------------------------- #
# Casos                                                                      #
# ------------------------------------------------------------------------- #

def preparar(trabajo: Path) -> tuple[Path, Path, dict]:
    trabajo.mkdir(parents=True, exist_ok=True)
    pdfs_base = trabajo / "copia_pdfs_corrida"
    pdfs_base.mkdir(exist_ok=True)
    for p in sorted((C.CORRIDA_BASE / "pdfs").glob("*.pdf")):
        d = pdfs_base / p.name
        if not d.exists():
            shutil.copyfile(p, d)
    indice = trabajo / "indice_base.json"
    shutil.copyfile(C.CORRIDA_BASE / "indice_crudo.json", indice)
    return pdfs_base, indice, json.loads(indice.read_text(encoding="utf-8"))


def dir_pdfs(trabajo: Path, pdfs_base: Path, nombre: str, reemplazo: Path | None) -> Path:
    """Directorio del caso: enlaces a las copias base, y el PDF alterado como
    archivo propio en lugar del suyo."""
    d = trabajo / f"pdfs_caso_{nombre}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    for p in sorted(pdfs_base.glob("*.pdf")):
        if reemplazo is not None and p.stem == PDF_ALTERADO:
            shutil.copyfile(reemplazo, d / p.name)
        else:
            (d / p.name).symlink_to(p)
    return d


def correr_caso(nombre: str, indice: Path, pdfs: Path, trabajo: Path, esperado: set[str],
                remedir: bool = False) -> dict:
    salida = trabajo / f"salida_{nombre}"
    if salida.exists():
        shutil.rmtree(salida)
    codigo = C.controlar(indice, pdfs, salida, C.LINEA_BASE_DEFAULT, remedir_todo=remedir)
    res = json.loads((salida / "resultado_control.json").read_text(encoding="utf-8"))
    rotos = {r["supuesto"] for r in res["rotos"]}
    aviso = salida / "aviso.md"
    en_aviso = sorted(set(re.findall(r"^## (S\d)", aviso.read_text(encoding="utf-8"), re.M))) \
        if aviso.exists() else []
    ok = (rotos == esperado and sorted(esperado) == en_aviso
          and codigo == (1 if esperado else 0) and aviso.exists() == bool(esperado))
    return {"caso": nombre, "esperado": sorted(esperado), "rotos": sorted(rotos),
            "supuestos_en_aviso_md": en_aviso, "codigo_salida": codigo,
            "aviso_md_escrito": aviso.exists(),
            "estado_por_supuesto": res["estado_por_supuesto"],
            "pdfs_medidos": res["pdfs_medidos"],
            "mediciones_reutilizadas_por_sha": res["mediciones_reutilizadas_por_sha"],
            "detalle_rotos": [{"supuesto": r["supuesto"], "linea_base": r["linea_base"],
                               "observado": r["observado"]} for r in res["rotos"]],
            "ok": ok}


def chequeo_replica_e0() -> dict:
    import pdfplumber
    out = {}
    for t in PDFS_REPLICA:
        pdf = C.CORRIDA_BASE / "pdfs" / f"{t}.pdf"
        completas = C.E0.extraer_lineas(pdf)
        with pdfplumber.open(str(pdf)) as d:
            idxs = C.L.paginas_de_sondeo(len(d.pages))
            iguales = all(C._lineas_e0(d.pages[i]) == [l.texto for l in completas[i]] for i in idxs)
        out[t] = {"paginas_comparadas": len(idxs), "iguales": iguales}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    trabajo = a.trabajo.resolve()
    if str(trabajo).startswith(str(C.REPO.resolve())):
        print("FRENO: --trabajo tiene que estar fuera del repo.", file=sys.stderr)
        return 2
    pdfs_base, indice_base, crudo = preparar(trabajo)
    casos = []

    # base
    d0 = dir_pdfs(trabajo, pdfs_base, "base", None)
    casos.append(correr_caso("base", indice_base, d0, trabajo, set(), remedir=True))

    def indice_alterado(nombre, fn) -> Path:
        c = json.loads(json.dumps(crudo))
        fn(c)
        p = trabajo / f"indice_{nombre}.json"
        p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        return p

    def a1(c):
        del c["textos_ordenados"][0]["titulo_truncado"]

    def a2(c):
        assert c["regimenes_informativos"][1]["archivo"] != "t-optico.pdf"
        del c["regimenes_informativos"][1]

    def a3(c):
        it = c["textos_ordenados"][1]
        it["url"] = "https://www.bcra.gob.ar/Pdfs/Texord/" + it["archivo"]

    def a6(c):
        del c["textos_ordenados"]

    for nombre, fn, esp in (("A1_clave_faltante", a1, {"S2"}),
                            ("A2_entrada_menos", a2, {"S3"}),
                            ("A3_url_otro_patron", a3, {"S4"}),
                            ("A6_lista_faltante", a6, {"S1"})):
        casos.append(correr_caso(nombre, indice_alterado(nombre, fn), d0, trabajo, esp))

    src = pdfs_base / f"{PDF_ALTERADO}.pdf"
    alterados = trabajo / "pdfs_alterados"
    alterados.mkdir(exist_ok=True)
    p4 = alterados / f"{PDF_ALTERADO}_sin_portada.pdf"
    quitar_portada(src, p4)
    p5 = alterados / f"{PDF_ALTERADO}_sin_marcadores.pdf"
    n5 = quitar_bloques(src, p5, lambda t, y: y < Y_PIE and bool(RE_MARCADOR.match(t)))
    p7 = alterados / f"{PDF_ALTERADO}_sin_pie.pdf"
    n7 = quitar_bloques(src, p7, lambda t, y: y < Y_PIE and t.startswith("Versi"))
    for nombre, pdf, esp in (("A4_pdf_sin_portada", p4, {"S5"}),
                             ("A5_pdf_sin_marcadores", p5, {"S7"}),
                             ("A7_pdf_sin_pie", p7, {"S6"})):
        r = correr_caso(nombre, indice_base, dir_pdfs(trabajo, pdfs_base, nombre, pdf), trabajo, esp)
        casos.append(r)
    bloques = {"A5_bloques_quitados": n5, "A7_bloques_quitados": n7}

    replica = chequeo_replica_e0()
    resultado = {
        "selftest": "U-MANT M2 — control de los supuestos del sitio",
        "linea_base_sha256": C.sha256_archivo(C.LINEA_BASE_DEFAULT),
        "pdf_alterado": PDF_ALTERADO,
        "bloques_de_pie_quitados": bloques,
        "replica_lineas_e0": replica,
        "casos": casos,
        "casos_ok": sum(1 for c in casos if c["ok"]),
        "casos_total": len(casos),
    }
    resultado["veredicto"] = ("OK" if resultado["casos_ok"] == len(casos)
                              and all(v["iguales"] for v in replica.values()) else "FRENO")
    texto = json.dumps(resultado, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if a.out:
        a.out.write_text(texto, encoding="utf-8")
    for c in casos:
        print(f"{c['caso']:24s} esperado={c['esperado']} rotos={c['rotos']} "
              f"aviso={c['supuestos_en_aviso_md']} codigo={c['codigo_salida']} "
              f"{'OK' if c['ok'] else 'MAL'}")
    print("réplica de líneas de E0:", replica)
    print("VEREDICTO:", resultado["veredicto"])
    return 0 if resultado["veredicto"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
