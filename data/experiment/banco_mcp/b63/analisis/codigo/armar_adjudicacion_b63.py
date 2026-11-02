#!/usr/bin/env python3
"""armar_adjudicacion_b63.py — La población y el material de la adjudicación de la autora de B6.3 (análisis A), con la forma de la mitad
de verificación de Q8 (ev2_juez/gold_q12_verificacion/codigo/armar_fichas_gold_q12_verificacion_mesa.py). USD 0, sin API.

La población: las respuestas cuyo veredicto de pregunta es `requiere_adjudicacion` (ev2_juez/mapping.py:10-13), de la lectura estricta
(juez/agregados_b63_ciego.json) y de las que la lectura tolerante agregó con sus tres lecturas (salidas/aplicacion/
agregados_de_las_que_no_se_leian_b63.json, después del sello). De cada una, los criterios cuyo modal es `dudoso` o `sin_consenso`: esos
los marca la autora; los demás conservan el modal del juez. El brazo se recupera solo para la clave, por el id opaco recalculado
(juez_b63.id_opaco, con caso_ciego), nunca con juez/desanonimizacion_SOLO_MESA/.

Escribe:
  - en <para_leer> (que tiene que estar vacía): una ficha por respuesta, A01 en adelante, en el orden de la semilla
    B63:adjudicacion:v1 (random.Random(semilla).shuffle de los ids opacos ordenados), en fichas/Ann.md y todas juntas en .md y .html;
    la planilla (un renglón por criterio que se adjudica: «cumplido» o «no cumplido» y un comentario libre), su estructura, su copia
    vacía con su sha256, el LEEME_primero.md y el sellador de la planilla. Cada ficha trae la pregunta, todos sus criterios con su cita
    textual y la respuesta, tal cual, y marca los criterios que se adjudican. Sin el brazo, sin ningún veredicto del juez, sin la sesión,
    sin el id de la pregunta ni el TO;
  - en <clave> (que no puede existir; va solo en el paquete de la revisión): por ficha, el id opaco, la pregunta, el brazo, la
    repetición, la sesión, los criterios que se adjudican y el modal del juez de los demás;
  - en <informe>: las cuentas y los sha256, sin imprimirse.
Imprime solo el total de respuestas que van a la adjudicación y el total de criterios que marca la autora.

  python3 -I -B armar_adjudicacion_b63.py --salida-b63 <banco_b63> --entrada <entrada_B63.json de HEAD> --clon <b63/v2/b2 de una copia>
      --aplicacion <salidas/aplicacion> --para-leer <adjudicacion/para_leer> --clave <clave_para_despues> --informe <json>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SEMILLA = "B63:adjudicacion:v1"
ADJUDICA = ("dudoso", "sin_consenso")
COLUMNAS = ["ficha", "criterio", "veredicto (cumplido / no_cumplido)", "comentario"]
PLANILLA = "planilla_adjudicacion_b63.csv"
MARCAS = ("fragmentos_hibrida", "fragmentos_denso", "B63J-", "B63-", "id_opaco")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cerco(texto: str) -> str:
    """Un cerco de código más largo que cualquier tira de comillas invertidas de la respuesta, para que vaya tal cual."""
    n, k = 3, 0
    for ch in texto:
        k = k + 1 if ch == "`" else 0
        n = max(n, k + 1)
    return "`" * n


LEEME = """# La adjudicación de B6.3: qué hay en esta carpeta y cómo se lee

Para leer a ciegas, antes de ver cualquier cifra de B6.3. La decisión: «Lo dudoso de B6.3, todo para mí.» (registro, §9). El
veredicto de estas respuestas lo pone tu adjudicación, no el mapping del juez (`docs/preregistro_evaluacion_fidelidad_ev2.md:39-41`).

## Qué hay

- **{n_fichas} fichas, {primera} a {ultima}** (`fichas/`), y las mismas todas juntas en `{md}`, y en `{html}` para leer en el navegador.
  Cada ficha trae la pregunta, la respuesta tal cual la vio el juez y todos los criterios del gold, cada uno con su cita textual.
- **Los criterios que adjudicás** van marcados **A ADJUDICAR** en cada ficha. Los demás no los marcás: conservan lo que dio el juez.
  En total son {n_criterios}.
- **`{planilla}`:** la planilla, un renglón por criterio que adjudicás, vacía. Su copia vacía, `{vacia}`, con su sha256 en
  `{vacia_sha}`.
- **`sellar_planilla_adjudicacion_b63.py`:** el sello de la planilla, al terminar.

Las fichas no dicen de qué sistema sale cada respuesta, ni traen ningún veredicto del juez, la sesión ni el documento. Algunas respuestas
nombran su fuente («el grafo», «los fragmentos») o sus herramientas: van tal cual las vio el juez, y eso se declara (D-10). Juzgás el
contenido, no la fuente que nombra.

## Cómo leés cada criterio marcado

Es la misma vara del juez (`data/experiment/ev2_juez/prompt_juez_v1.md:17-23`) y la de Q8:
- **cumplido:** la respuesta contiene el contenido normativo que exige el criterio. No hace falta literalidad: vale la equivalencia
  normativa, con los mismos sujetos, calificadores, modalidades, plazos y umbrales;
- **no cumplido:** el contenido falta, o la respuesta afirma algo que lo contradice.

Elegís siempre una de las dos. El comentario es libre: ahí va si dudaste, si el criterio te parece mal planteado o si pide un experto
del dominio. Leés de {primera} a {ultima}, en ese orden; si corregís una ficha anterior, lo anotás en su comentario.

## Lo que no abrís mientras leés

- nada de B6.3 en `fuera_del_repo/banco_b63/` ni en el repo (`data/experiment/banco_mcp/b63/real/`): los juicios del juez y las
  sesiones de cada sistema;
- la clave, que dice de qué sistema sale cada ficha: está en el paquete de la revisión, no en esta carpeta;
- ningún resumen, conversación ni salida de un modelo sobre estas respuestas.

## Al terminar

1. Exportás la planilla a CSV (con «,» o con «;»), con este mismo nombre, en esta carpeta.
2. Corrés, desde esta carpeta: `python3 sellar_planilla_adjudicacion_b63.py`. Controla la planilla y escribe
   `sello_adjudicacion_b63.txt`. No pisa un sello que ya existe.
3. Avisás. Con eso, la etapa C calcula el veredicto de cada respuesta: el mapping de EV2 sobre tus marcas y el modal del juez de los
   demás criterios.
"""

SELLADOR = '''"""sellar_planilla_adjudicacion_b63.py — el sello de tu planilla de la adjudicación de B6.3 (análisis A). Tiene la forma del sellador
de Q8 (ev2_juez/gold_q12_verificacion/para_leer/sellar_planillas_gold_q12_verificacion.py), con una sola planilla.

Corre en esta carpeta, sin argumentos. Controla, sin cambiar la planilla:
  - su estructura: `estructura_planilla_adjudicacion_b63.json`, con su sha256 (el de abajo); y las columnas, los renglones y su orden de
    la planilla, los de esa estructura;
  - el veredicto de cada renglón: cumplido o no cumplido (mayúsculas, tildes y el guion bajo no importan). El comentario es libre.
Si todo pasa, escribe `sello_adjudicacion_b63.txt` con el sha256, los bytes y la hora de la planilla y la hora del sello. No pisa un
sello que ya existe. Si algo falla, lo lista y no sella. Acepta «,» o «;» y el BOM.
  python3 sellar_planilla_adjudicacion_b63.py
"""
import csv
import hashlib
import io
import json
import sys
import time
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLANILLA = AQUI / "planilla_adjudicacion_b63.csv"
ESTRUCTURA = AQUI / "estructura_planilla_adjudicacion_b63.json"
SHA_ESTRUCTURA = "__SHA_ESTRUCTURA__"
SELLO = AQUI / "sello_adjudicacion_b63.txt"


def plegar(s):
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").replace("_", " ").split())


def leer(p):
    t = p.read_bytes().decode("utf-8-sig")
    pr = t.splitlines()[0] if t else ""
    d = ";" if pr.count(";") > pr.count(",") else ","
    filas = [f for f in csv.reader(io.StringIO(t), delimiter=d) if any(x.strip() for x in f)]
    return [c.strip() for c in filas[0]], [[c.strip() for c in f] for f in filas[1:]]


def main():
    if SELLO.exists():
        raise SystemExit(f"{SELLO.name} ya existe: no se pisa un sello")
    if hashlib.sha256(ESTRUCTURA.read_bytes()).hexdigest() != SHA_ESTRUCTURA:
        raise SystemExit(f"NO SE SELLA: {ESTRUCTURA.name} no es la que armó la mesa (su sha256)")
    est = json.loads(ESTRUCTURA.read_text(encoding="utf-8"))
    errores = []
    cols, filas = leer(PLANILLA)
    if cols != est["columnas"]:
        errores.append(f"{PLANILLA.name}: las columnas no son las de la planilla de la mesa")
    else:
        if [f[:2] for f in filas] != est["renglones"]:
            errores.append(f"{PLANILLA.name}: los renglones no son los de la planilla de la mesa, en su orden")
        for f in filas:
            r = dict(zip(cols, f + [""] * (len(cols) - len(f))))
            if plegar(r[cols[2]]) not in ("cumplido", "no cumplido"):
                errores.append(f"{r['ficha']}, criterio {r['criterio']}: el veredicto no es cumplido ni no cumplido")
    if errores:
        print(f"NO SE SELLA: {len(errores)} problema(s)")
        for e in errores:
            print(" -", e)
        return 1
    hora = time.strftime("%Y-%m-%d %H:%M:%S %z")
    b = PLANILLA.read_bytes()
    lin = ["# sello de la adjudicación de la autora de B6.3: sha256, bytes, hora de modificación y nombre", f"# sellado: {hora}",
           f"{hashlib.sha256(b).hexdigest()}  {len(b)}  "
           f"{time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(PLANILLA.stat().st_mtime))}  {PLANILLA.name}"]
    SELLO.write_text("\\n".join(lin) + "\\n", encoding="utf-8")
    print(f"SELLADA la planilla -> {SELLO.name}, {hora}")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
'''


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida-b63", type=Path, required=True)
    ap.add_argument("--entrada", type=Path, required=True)
    ap.add_argument("--clon", type=Path, required=True)
    ap.add_argument("--aplicacion", type=Path, required=True)
    ap.add_argument("--para-leer", type=Path, required=True)
    ap.add_argument("--clave", type=Path, required=True)
    ap.add_argument("--informe", type=Path, required=True)
    a = ap.parse_args(argv)
    clon = a.clon.resolve()
    for p in (str(AQUI), str(clon), str(clon.parents[2])):
        if p not in sys.path:
            sys.path.insert(0, p)
    import aplicar_lectura_tolerante_b63 as AP  # noqa: PLC0415  (cargar_entrada y casos_de_b63: el mismo caso que la aplicación)
    import juez_b63 as JB                       # noqa: PLC0415
    K, M = JB.K, JB.M
    PL, CL = a.para_leer.resolve(), a.clave.resolve()
    if PL.exists() and any(PL.iterdir()):
        raise SystemExit("ABORTO: --para-leer no está vacía")
    if CL.exists():
        raise SystemExit("ABORTO: --clave ya existe")
    B63 = a.salida_b63.resolve()
    e = AP.cargar_entrada(a.entrada, K)
    casos = {c["id_opaco"]: c for c in AP.casos_de_b63(B63, e, K, JB)}

    # La población
    estricta = json.loads((B63 / "juez" / "agregados_b63_ciego.json").read_text(encoding="utf-8"))
    tolerante = json.loads((a.aplicacion / "agregados_de_las_que_no_se_leian_b63.json").read_text(encoding="utf-8"))
    control = {"las_de_la_tolerante_son_las_incompletas_de_la_estricta":
               sorted(x["id_opaco"] for x in tolerante["agregados"]) == sorted(x["id_opaco"] for x in estricta["incompletas"]),
               "sin_ids_en_las_dos": not ({x["id_opaco"] for x in tolerante["agregados"]} & {x["id_opaco"] for x in estricta["agregados"]}),
               "todos_los_ids_son_casos": all(x["id_opaco"] in casos for x in estricta["agregados"] + tolerante["agregados"])}
    if not all(control.values()):
        raise SystemExit(f"ABORTO: los agregados no dan: {[k for k, v in control.items() if not v]}")
    agregados = [dict(x, lectura="estricta") for x in estricta["agregados"]] + \
                [dict(x, lectura="con_lectura_tolerante") for x in tolerante["agregados"]]
    pob = [x for x in agregados if x["veredicto_pregunta"] == "requiere_adjudicacion"]
    for x in pob:
        if M.veredicto_pregunta(x["modales"]) != "requiere_adjudicacion" or not any(m in ADJUDICA for m in x["modales"]):
            raise SystemExit("ABORTO: un veredicto de pregunta que no sale del mapping de sus modales")
    ids = sorted(x["id_opaco"] for x in pob)
    random.Random(SEMILLA).shuffle(ids)
    ancho = max(2, len(str(len(ids))))
    por_id = {x["id_opaco"]: x for x in pob}

    # Las fichas y la planilla
    (PL / "fichas").mkdir(parents=True, exist_ok=True)
    fichas_md, fichas_html, renglones, clave = [], [], [], []
    for k, i in enumerate(ids, 1):
        ficha = f"A{k:0{ancho}d}"
        c, ag = casos[i], por_id[i]
        caso = c["caso"]
        adj = [n for n, m in enumerate(ag["modales"], 1) if m in ADJUDICA]
        cr = cerco(caso["respuesta"])
        md = [f"# Ficha {ficha}", "", "## Pregunta", "", caso["pregunta"], "", "## Respuesta (tal cual, sin tocar)", "",
              f"{cr}text", caso["respuesta"], cr, "", "## Criterios", "",
              f"Los que adjudicás van marcados **A ADJUDICAR** ({len(adj)} de {len(caso['criterios'])}). Los demás no los marcás.", ""]
        h = [f"<section><h2>Ficha {ficha}</h2>", f"<h3>Pregunta</h3><p>{html.escape(caso['pregunta'])}</p>",
             f"<h3>Respuesta (tal cual)</h3><pre>{html.escape(caso['respuesta'])}</pre>",
             f"<h3>Criterios</h3><p>Los que adjudicás van marcados <b>A ADJUDICAR</b> ({len(adj)} de {len(caso['criterios'])}).</p><ol>"]
        for n, cc in enumerate(caso["criterios"], 1):
            marca = " — **A ADJUDICAR**" if n in adj else " — (no se adjudica)"
            md += [f"**{n}.** {cc['criterio']}{marca}", "", f"> Cita de la norma: «{cc['cita_textual']}»", ""]
            h.append(f"<li>{html.escape(cc['criterio'])} <b>{'A ADJUDICAR' if n in adj else '(no se adjudica)'}</b>"
                     f"<blockquote>«{html.escape(cc['cita_textual'])}»</blockquote></li>")
            if n in adj:
                renglones.append([ficha, str(n)])
        md += ["## Lo que anotás", "", "En la planilla, un renglón por cada criterio marcado A ADJUDICAR: «cumplido» o «no cumplido», y un "
               "comentario libre.", ""]
        h.append("</ol></section>")
        (PL / "fichas" / f"{ficha}.md").write_text("\n".join(md), encoding="utf-8")
        fichas_md.append("\n".join(md))
        fichas_html.append("\n".join(h))
        clave.append({"ficha": ficha, "id_opaco": i, "pregunta": c["qid"], "brazo": c["brazo"], "repeticion": c["r"],
                      "sesion": c["sesion"], "lectura": ag["lectura"], "n_criterios": len(caso["criterios"]),
                      "criterios_que_se_adjudican": adj,
                      "modal_del_juez_de_los_demas": {str(n): m for n, m in enumerate(ag["modales"], 1) if n not in adj}})
    primera, ultima = f"A{1:0{ancho}d}", f"A{len(ids):0{ancho}d}"
    nombre_md, nombre_html = f"fichas_{primera}_a_{ultima}.md", f"fichas_{primera}_a_{ultima}.html"
    (PL / nombre_md).write_text("\n\n---\n\n".join(fichas_md) + "\n", encoding="utf-8")
    estilo = ("body{font-family:Georgia,serif;max-width:46rem;margin:2rem auto;padding:0 1rem;line-height:1.5}"
              "pre{white-space:pre-wrap;background:#f6f6f2;padding:.8rem;border-left:3px solid #999}"
              "blockquote{margin:.4rem 0 .8rem 1rem;color:#333;font-style:italic}section{page-break-after:always}")
    (PL / nombre_html).write_text(
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Fichas de la adjudicación de B6.3</title><style>" + estilo +
        f"</style></head><body><h1>Fichas de la adjudicación de B6.3 ({primera} a {ultima})</h1>\n" + "\n".join(fichas_html) +
        "</body></html>\n", encoding="utf-8")
    for nombre in (PLANILLA, PLANILLA.replace(".csv", "_vacia.csv")):
        with open(PL / nombre, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(COLUMNAS)
            w.writerows([[f, n, "", ""] for f, n in renglones])
    vacia = PLANILLA.replace(".csv", "_vacia.csv")
    (PL / vacia.replace(".csv", ".sha256")).write_text(f"{sha(PL / vacia)}  {vacia}\n", encoding="utf-8")
    (PL / "estructura_planilla_adjudicacion_b63.json").write_text(
        json.dumps({"columnas": COLUMNAS, "renglones": renglones}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (PL / "sellar_planilla_adjudicacion_b63.py").write_text(
        SELLADOR.replace("__SHA_ESTRUCTURA__", sha(PL / "estructura_planilla_adjudicacion_b63.json")), encoding="utf-8")
    (PL / "LEEME_primero.md").write_text(LEEME.format(
        n_fichas=len(ids), primera=primera, ultima=ultima, md=nombre_md, html=nombre_html, n_criterios=len(renglones),
        planilla=PLANILLA, vacia=vacia, vacia_sha=vacia.replace(".csv", ".sha256")), encoding="utf-8")

    # El control de las fichas: ningún id, sesión, pregunta ni marca de brazo fuera del texto de la respuesta (como Q8)
    resps = [casos[i]["caso"]["respuesta"] for i in ids]
    fallas = []
    for p in sorted(PL.rglob("*")):
        if p.is_file() and p.suffix in (".md", ".html", ".csv", ".json"):
            t = p.read_text(encoding="utf-8")
            for r in resps:
                t = t.replace(r, "").replace(html.escape(r), "")
            for f in clave:
                for x in (f["id_opaco"], f["sesion"], f["pregunta"]):
                    if x in t:
                        fallas.append(f"{p.name}: un id de la clave")
            if any(m in t for m in MARCAS) or any(b in t for b in ("kg", "grafo")) and p.suffix == ".csv":
                fallas.append(f"{p.name}: una marca de brazo fuera de una respuesta")
    if fallas:
        raise SystemExit(f"ABORTO: las fichas traen lo que no tienen que traer: {sorted(set(fallas))[:5]}")
    CL.mkdir(parents=True)
    (CL / "clave_adjudicacion_b63.json").write_text(json.dumps(
        {"que": "la clave de la adjudicación de B6.3 (análisis A): de cada ficha, su respuesta y su brazo. Solo en el paquete.",
         "semilla": SEMILLA, "orden": "random.Random(semilla).shuffle de los ids opacos ordenados", "fichas": clave},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    con_marca = sum(any(m in r.lower() for m in ("fragmento", "grafo", "bm25", "denso", "knowledge graph", "nodo")) for r in resps)
    a.informe.parent.mkdir(parents=True, exist_ok=True)
    a.informe.write_text(json.dumps(
        {"control": control, "respuestas_a_la_adjudicacion": len(ids), "criterios_que_marca_la_autora": len(renglones),
         "respuestas_que_nombran_grafo_fragmentos_o_nodos": con_marca,
         "de_la_estricta": sum(f["lectura"] == "estricta" for f in clave), "de_la_tolerante": sum(f["lectura"] != "estricta" for f in clave),
         "para_leer": {str(p.relative_to(PL)): sha(p) for p in sorted(PL.rglob("*")) if p.is_file()},
         "clave": {str(p.relative_to(CL)): sha(p) for p in sorted(CL.rglob("*")) if p.is_file()},
         "codigo": {Path(__file__).name: sha(Path(__file__)), "aplicar_lectura_tolerante_b63.py": sha(Path(AP.__file__)),
                    "juez_b63.py": sha(Path(JB.__file__)), "mapping.py": sha(Path(M.__file__))}},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"respuestas_a_la_adjudicacion": len(ids), "criterios_que_marca_la_autora": len(renglones)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
