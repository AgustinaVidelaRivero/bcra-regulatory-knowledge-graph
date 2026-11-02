"""Arma el material de lectura de la autora para la muestra de control del juez de B6.3: las 36 fichas (C01 a C36), las dos planillas
vacías y su estructura (mesa, unidad C36_a, 29/10/2026). Es `ev2_juez/gold_q12_verificacion/codigo/armar_fichas_gold_q12_verificacion_mesa.py`
con lo que pide B6.3: la ficha trae la pregunta, sus criterios con su cita textual de la norma y la respuesta, tal cual, sin editarla; no
trae el brazo, el veredicto, la sesión ni el TO (y por eso tampoco el documento, sus páginas ni el ancla), ni el tipo. USD 0, sin API.

Uso: python3 -I -B armar_fichas_control_36_B63.py <repo> <banco_b63> <clave_control_36_B63.json> <carpeta para_leer>

Lee, solo lectura:
  - la clave del sorteo (qué respuesta va en cada ficha);
  - del repo, cada uno igual al de HEAD, la entrada sellada de B6.3 y el manifiesto de sus salidas fuera del repo; el archivo de las 96
    preguntas que nombra la entrada, con su sha256: de cada pregunta de la clave, su texto y sus criterios con su cita, en el orden del
    archivo, que es el del juez (`comun_b63.cargar_preguntas`);
  - de cada sesión de la clave, solo `final_json_R4.respuesta` de su meta en banco_b63/resultados/real/pasada1/, con el sha256 del
    manifiesto; la respuesta tiene que dar el sha256 de la clave y recalcular su id opaco con `juez_b63.id_opaco`.
No lee ningún veredicto. No escribe en el repo ni en banco_b63/. Imprime solo cuentas.
"""
import csv
import hashlib
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

COLS_CRIT = ["ficha", "criterio", "veredicto (cumplido / no_cumplido)", "fragmento de la respuesta (opcional)",
             "dudosa para mí (sí/no)", "necesita experto del dominio (sí/no)", "criterio mal planteado (sí/no)", "nota"]
COLS_RESP = ["ficha", "clasificación (abstencion / contenido)", "error fuera de los criterios (sí/no)", "cuál", "minutos", "nota"]
PC, PR = "planilla_criterios_control_36_B63.csv", "planilla_respuestas_control_36_B63.csv"
ESTRUCTURA = "estructura_planillas.json"
# Lo que no puede aparecer fuera del texto de una respuesta: los brazos de fragmentos, los prefijos de los ids y de las sesiones.
MARCAS = ("fragmentos_hibrida", "fragmentos_denso", "B63J-", "B63-", "id_opaco", "pasada1", "meta_")
ESTILO = ("body{font-family:Georgia,serif;max-width:46rem;margin:2rem auto;padding:0 1rem;line-height:1.5;background:#fff;color:#111}"
          "pre{white-space:pre-wrap;word-wrap:break-word;background:#f6f6f2;padding:.8rem;border-left:3px solid #999}"
          "blockquote{margin:.4rem 0 .8rem 1rem;color:#333;font-style:italic}section{page-break-after:always}")


def frena(m):
    raise SystemExit(f"FRENO: {m}")


def escribir_planillas(out: Path, fichas: list) -> None:
    """Las dos planillas vacías y su estructura. fichas: [(id de la ficha, cuántos criterios)], en su orden."""
    filas_crit = [dict(zip(COLS_CRIT, [f, str(i)] + [""] * (len(COLS_CRIT) - 2))) for f, n in fichas for i in range(1, n + 1)]
    filas_resp = [dict(zip(COLS_RESP, [f] + [""] * (len(COLS_RESP) - 1))) for f, _ in fichas]
    for nombre, cols, filas in ((PC, COLS_CRIT, filas_crit), (PR, COLS_RESP, filas_resp)):
        with open(out / nombre, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(filas)
    (out / ESTRUCTURA).write_text(json.dumps(
        {"criterios": {"columnas": COLS_CRIT, "renglones": [[x["ficha"], x["criterio"]] for x in filas_crit]},
         "respuestas": {"columnas": COLS_RESP, "renglones": [[x["ficha"]] for x in filas_resp]}},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def cerca(t: str) -> str:
    """Un cerco de código más largo que cualquier tramo de comillas invertidas de la respuesta, para que vaya tal cual."""
    return "`" * max(3, max((len(m) for m in re.findall(r"`+", t)), default=0) + 1)


def ficha_md(fid: str, q: dict, resp: str) -> str:
    fe = cerca(resp)
    md = [f"# Ficha {fid}", "", "## Pregunta", "", q["pregunta"], "", "## Respuesta (tal cual, sin tocar)", "", f"{fe}text", resp, fe, "",
          "## Criterios", ""]
    for i, c in enumerate(q["criterios"], 1):
        md += [f"**{i}.** {c['criterio']}", ""]
        md += [("> " + ln) if ln else ">" for ln in f"Cita de la norma: «{c['cita_textual']}»".split("\n")] + [""]
    md += ["## Lo que anotás", "", "En las dos planillas: un renglón por criterio y uno por respuesta (ver la regla de lectura).", ""]
    return "\n".join(md)


def ficha_html(fid: str, q: dict, resp: str) -> str:
    h = [f"<section id='{fid}'><h2>Ficha {fid}</h2>", f"<h3>Pregunta</h3><p>{html.escape(q['pregunta'])}</p>",
         f"<h3>Respuesta (tal cual)</h3><pre>{html.escape(resp)}</pre><h3>Criterios</h3><ol>"]
    for c in q["criterios"]:
        h.append(f"<li>{html.escape(c['criterio'])}<blockquote>Cita de la norma: «{html.escape(c['cita_textual'])}»</blockquote></li>")
    h.append("</ol></section>")
    return "\n".join(h)


def main() -> None:
    repo, banco, clave_p, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]), Path(sys.argv[4])
    spec = importlib.util.spec_from_file_location("S", Path(__file__).with_name("sortear_control_36_B63.py"))
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    if out.exists() and any(out.iterdir()):
        frena("la carpeta para_leer ya tiene archivos: no se pisa")
    clave = json.loads(clave_p.read_text(encoding="utf-8"))
    e = json.loads(S.de_head(repo, S.DEL_REPO["entrada"]).decode("utf-8"))
    man = json.loads(S.de_head(repo, S.DEL_REPO["manifiesto"]).decode("utf-8"))
    idx = {a["ruta"]: a["sha256"] for a in man["archivos"]}
    rp = e["preguntas"]["ruta"]
    pq_b = (Path(rp).expanduser() if rp.startswith("~") else repo / rp).read_bytes()
    if hashlib.sha256(pq_b).hexdigest() != e["preguntas"]["sha256"] or clave["sha256_entradas"]["preguntas"] != e["preguntas"]["sha256"]:
        frena("el archivo de las preguntas no da el sha256 de la entrada sellada")
    esq = e["preguntas"]["esquema"]
    lista = json.loads(pq_b.decode("utf-8"))[esq["lista"]]
    preguntas = {p[esq["id"]]: {"pregunta": p[esq["pregunta"]], "to": p["to"],
                                "criterios": [{"criterio": c[esq["criterio"]], "cita_textual": c[esq["cita"]]} for c in p[esq["criterios"]]]}
                 for p in lista}
    JB = S.cargar_juez(repo)
    respuestas = {}
    for f in clave["fichas"]:
        rel = f"resultados/real/pasada1/{f['id_sesion']}/meta_{f['id_sesion']}.json"
        b = (banco / rel).read_bytes()
        if idx.get("banco_b63/" + rel) != hashlib.sha256(b).hexdigest():
            frena(f"la meta de {f['ficha']} no está en el manifiesto o no da su sha256")
        resp = json.loads(b.decode("utf-8"))["final_json_R4"]["respuesta"]
        if JB.sha256_texto(resp) != f["sha256_respuesta"] or JB.id_opaco(f["id_pregunta"], f["brazo"], f["repeticion"],
                                                                           f["sha256_respuesta"]) != f["id_opaco"]:
            frena(f"la respuesta de {f['ficha']} no da el sha256 o el id opaco de la clave")
        if len(preguntas[f["id_pregunta"]]["criterios"]) != f["n_criterios"]:
            frena(f"{f['ficha']}: el número de criterios no es el de la clave")
        respuestas[f["ficha"]] = resp
    if [f["ficha"] for f in clave["fichas"]] != [f"C{i:02d}" for i in range(1, 37)]:
        frena("las fichas de la clave no son C01 a C36, en su orden")

    (out / "fichas").mkdir(parents=True, exist_ok=True)
    mds, htmls = [], []
    for f in clave["fichas"]:
        q, resp = preguntas[f["id_pregunta"]], respuestas[f["ficha"]]
        md = ficha_md(f["ficha"], q, resp)
        (out / "fichas" / f"{f['ficha']}.md").write_text(md, encoding="utf-8")
        mds.append(md)
        htmls.append(ficha_html(f["ficha"], q, resp))
    (out / "fichas_C01_a_C36.md").write_text("\n\n---\n\n".join(mds) + "\n", encoding="utf-8")
    (out / "fichas_C01_a_C36.html").write_text(
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Fichas de la muestra de control</title><style>" + ESTILO + "</style></head><body>"
        "<h1>Fichas de la muestra de control de B6.3 (C01 a C36)</h1>\n" + "\n".join(htmls) + "</body></html>\n", encoding="utf-8")
    escribir_planillas(out, [(f["ficha"], f["n_criterios"]) for f in clave["fichas"]])

    # Los controles: cada respuesta tal cual en su ficha; fuera de las respuestas, ningún id, marca de brazo ni TO.
    for f in clave["fichas"]:
        r = respuestas[f["ficha"]]
        if r not in (out / "fichas" / f"{f['ficha']}.md").read_text(encoding="utf-8") or html.escape(r) not in \
                (out / "fichas_C01_a_C36.html").read_text(encoding="utf-8"):
            frena(f"la respuesta de {f['ficha']} no está tal cual en su ficha")
    tos = sorted({p["to"] for p in preguntas.values()})
    n_arch = 0
    for p in sorted(out.rglob("*")):
        if not p.is_file():
            continue
        n_arch += 1
        txt = p.read_text(encoding="utf-8")
        for r in sorted(respuestas.values(), key=len, reverse=True):
            txt = txt.replace(r, "").replace(html.escape(r), "")
        for f in clave["fichas"]:
            if any(x in txt for x in (f["id_opaco"], f["id_sesion"], f["id_pregunta"])):
                frena(f"{p.name} trae un id de la clave")
        if any(m in txt for m in MARCAS):
            frena(f"{p.name} trae una marca de brazo o de sesión fuera de una respuesta")
        if any(re.search(r"(?<![A-Za-z0-9_])" + re.escape(t) + r"(?![A-Za-z0-9_])", txt) for t in tos + ["kg"]):
            frena(f"{p.name} trae un TO o el nombre de un brazo fuera de una respuesta")
    print(json.dumps({"fichas": len(clave["fichas"]), "criterios": sum(f["n_criterios"] for f in clave["fichas"]), "archivos": n_arch,
                      "fichas_con_alguna_marca_de_D10": sum(bool(f["marca_d10"]) for f in clave["fichas"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
