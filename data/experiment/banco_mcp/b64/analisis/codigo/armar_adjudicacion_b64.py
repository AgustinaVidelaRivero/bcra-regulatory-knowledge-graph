#!/usr/bin/env python3
"""armar_adjudicacion_b64.py — La población y el material de la adjudicación de la autora de B6.4 (§5: «Lo que la lectura no resuelve va
a la adjudicación de la autora, como en B6.3.»). Adaptado de `armar_adjudicacion_b63.py` (`32daed5c…`, HEAD 80085175), que se importa sin
editarlo, con su sha256 (analizar_b64.SELLADO): de él salen el cerco de la respuesta (cerco), las columnas de la planilla (COLUMNAS), los
modales que se adjudican (ADJUDICA), las marcas de brazo del control de las fichas (MARCAS, más kg_n7) y el sellador de la planilla
(SELLADOR, con los nombres de los archivos de B6.4). USD 0, sin API.

Lo que hace falta al análisis (analizar_b64.py) para leer la adjudicación: la planilla, su estructura y la clave que lleva cada ficha a su id
opaco y a su brazo. El de B6.3 corre igual sobre las salidas de B6.4, pero escribe un material rotulado B6.3 (el LEEME, los nombres, la
semilla), que la autora leería al adjudicar: por eso se adapta.

La población, como en B6.3: las respuestas cuyo veredicto de pregunta es `requiere_adjudicacion` (ev2_juez/mapping.py:10-13), de la
lectura estricta (juez/agregados_b63_ciego.json, el nombre que deja el runner de B6.3) y de las que la lectura tolerante agregó con sus
tres lecturas (agregados_de_las_que_no_se_leian_b63.json, el nombre que deja aplicar_lectura_tolerante_b63.py). De cada una, los
criterios cuyo modal es `dudoso` o `sin_consenso`: esos los marca la autora; los demás conservan el modal del juez. El brazo se recupera
solo para la clave, por el id opaco recalculado (juez_b63.caso_ciego, por aplicar_lectura_tolerante_b63.casos_de_b63), nunca con
juez/desanonimizacion_SOLO_MESA/.
La corrección del H-6 (la decisión 3, aplicar_lectura_tolerante_b64.DECISION): también las respuestas a las que una salida del juez sin
lectura (ni la estricta ni la tolerante la leen) les deja sin una de sus tres lecturas (agregados_sin_lectura_b64.json, que deja
aplicar_lectura_tolerante_b64.py): van enteras, con todos sus criterios para la autora.

Escribe:
  - en <para_leer> (que tiene que estar vacía): una ficha por respuesta, A01 en adelante, en el orden de la semilla
    B64:adjudicacion:v1 (random.Random(semilla).shuffle de los ids opacos ordenados), en fichas/Ann.md y todas juntas en .md y .html;
    la planilla, su estructura, su copia vacía con su sha256, el LEEME_primero.md y el sellador de la planilla. Cada ficha trae la
    pregunta, todos sus criterios con su cita textual y la respuesta, tal cual, y marca los criterios que se adjudican. Sin el brazo,
    sin ningún veredicto del juez, sin la sesión, sin el id de la pregunta ni el TO;
  - en <clave> (que no puede existir; va solo en el paquete de la revisión): por ficha, el id opaco, la pregunta, el brazo, la
    repetición, la sesión, los criterios que se adjudican y el modal del juez de los demás;
  - en <informe>: las cuentas y los sha256, sin imprimirse.
Imprime solo el total de respuestas que van a la adjudicación y el total de criterios que marca la autora.

  B64_CODIGO_B63=<b63/analisis/codigo de una copia de HEAD> python3 -I -B armar_adjudicacion_b64.py --salida-b64 <banco_b64>
      --entrada <la entrada de B6.4> --clon <b63/v2/b2 de esa copia> --aplicacion <la salida de la lectura tolerante>
      --para-leer <adjudicacion/para_leer> --clave <clave_para_despues> --informe <json>
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
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import analizar_b64 as B  # noqa: E402  (solo import)
import aplicar_lectura_tolerante_b64 as T  # noqa: E402  (solo import: el nombre de su salida)

A = B.A
AA = B.importar_sellado("armar_adjudicacion_b63.py")
SEMILLA = "B64:adjudicacion:v1"
PLANILLA = "planilla_adjudicacion_b64.csv"
ESTRUCTURA = "estructura_planilla_adjudicacion_b64.json"
SELLADOR_NOMBRE = "sellar_planilla_adjudicacion_b64.py"
MARCAS = AA.MARCAS + (B.CUARTO,)


def sellador_b64() -> str:
    """El sellador de B6.3 (armar_adjudicacion_b63.SELLADOR) con los nombres de los archivos y el rótulo de B6.4; nada más cambia."""
    s = AA.SELLADOR.replace("adjudicacion_b63.", "adjudicacion_b64.").replace("de B6.3 (análisis A)", "de B6.4") \
                   .replace("de la autora de B6.3", "de la autora de B6.4")
    if "b63" in s or "B6.3" in s or s.count("adjudicacion_b64.") != AA.SELLADOR.count("adjudicacion_b63."):
        raise SystemExit("ABORTO: el sellador de B6.3 no tiene la forma esperada")
    return s


LEEME = """# La adjudicación de B6.4: qué hay en esta carpeta y cómo se lee

Para leer a ciegas, antes de ver cualquier cifra de B6.4. El pre-registro de B6.4 (§5): «Lo que la lectura no resuelve va a la
adjudicación de la autora, como en B6.3.» El veredicto de estas respuestas lo pone tu adjudicación, no el mapping del juez
(`docs/preregistro_evaluacion_fidelidad_ev2.md:39-41`).

## Qué hay

- **{n_fichas} fichas, {primera} a {ultima}** (`fichas/`), y las mismas todas juntas en `{md}`, y en `{html}` para leer en el navegador.
  Cada ficha trae la pregunta, la respuesta tal cual la vio el juez y todos los criterios del gold, cada uno con su cita textual.
- **Los criterios que adjudicás** van marcados **A ADJUDICAR** en cada ficha. Los demás no los marcás: conservan lo que dio el juez.
  En total son {n_criterios}. Una ficha con todos sus criterios marcados es una respuesta a la que le falta una de las tres lecturas
  del juez (§5): va entera a tu adjudicación.
- **`{planilla}`:** la planilla, un renglón por criterio que adjudicás, vacía. Su copia vacía, `{vacia}`, con su sha256 en
  `{vacia_sha}`.
- **`{sellador}`:** el sello de la planilla, al terminar.

Las fichas no dicen de qué sistema sale cada respuesta, ni traen ningún veredicto del juez, la sesión ni el documento. Algunas respuestas
nombran su fuente («el grafo», «los fragmentos») o sus herramientas: van tal cual las vio el juez, y eso se declara (§7). Juzgás el
contenido, no la fuente que nombra.

## Cómo leés cada criterio marcado

Es la misma vara del juez (`data/experiment/ev2_juez/prompt_juez_v1.md:17-23`) y la de B6.3:
- **cumplido:** la respuesta contiene el contenido normativo que exige el criterio. No hace falta literalidad: vale la equivalencia
  normativa, con los mismos sujetos, calificadores, modalidades, plazos y umbrales;
- **no cumplido:** el contenido falta, o la respuesta afirma algo que lo contradice.

Elegís siempre una de las dos. El comentario es libre: ahí va si dudaste, si el criterio te parece mal planteado o si pide un experto
del dominio. Leés de {primera} a {ultima}, en ese orden; si corregís una ficha anterior, lo anotás en su comentario.

## Lo que no abrís mientras leés

- nada de B6.4 en `fuera_del_repo/banco_b64/`: los juicios del juez y las sesiones de cada sistema;
- la clave, que dice de qué sistema sale cada ficha: está en el paquete de la revisión, no en esta carpeta;
- ningún resumen, conversación ni salida de un modelo sobre estas respuestas.

## Al terminar

1. Exportás la planilla a CSV (con «,» o con «;»), con este mismo nombre, en esta carpeta.
2. Corrés, desde esta carpeta: `python3 {sellador}`. Controla la planilla y escribe `sello_adjudicacion_b64.txt`. No pisa un sello que
   ya existe.
3. Avisás. Con eso, el análisis de B6.4 calcula el veredicto de cada respuesta: el mapping de EV2 sobre tus marcas y el modal del juez
   de los demás criterios.
"""


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida-b64", type=Path, required=True)
    ap.add_argument("--entrada", type=Path, required=True)
    ap.add_argument("--clon", type=Path, required=True)
    ap.add_argument("--aplicacion", type=Path, required=True)
    ap.add_argument("--para-leer", type=Path, required=True)
    ap.add_argument("--clave", type=Path, required=True)
    ap.add_argument("--informe", type=Path, required=True)
    a = ap.parse_args(argv)
    AP, JB = A.importar(a.clon, B.ESPERADO_CODIGO)
    K, M = JB.K, JB.M
    PL, CL = a.para_leer.resolve(), a.clave.resolve()
    if PL.exists() and any(PL.iterdir()):
        raise SystemExit("ABORTO: --para-leer no está vacía")
    if CL.exists():
        raise SystemExit("ABORTO: --clave ya existe")
    B64 = a.salida_b64.resolve()
    e = AP.cargar_entrada(a.entrada, K)
    if sorted(e["brazos"]) != sorted(B.BRAZOS):
        raise SystemExit("ABORTO: los brazos de la entrada no son los cuatro de B6.4")
    casos = {c["id_opaco"]: c for c in AP.casos_de_b63(B64, e, K, JB)}
    sellador = sellador_b64()

    # La población
    estricta = json.loads((B64 / "juez" / "agregados_b63_ciego.json").read_text(encoding="utf-8"))
    tolerante = json.loads((a.aplicacion / "agregados_de_las_que_no_se_leian_b63.json").read_text(encoding="utf-8"))
    sin_lectura = json.loads((a.aplicacion / T.SIN_LECTURA).read_text(encoding="utf-8"))
    ids_e, ids_t, ids_s = ({x["id_opaco"] for x in g["agregados"]} for g in (estricta, tolerante, sin_lectura))
    control = {"las_de_la_tolerante_y_las_sin_lectura_son_las_incompletas_de_la_estricta":
               sorted(x["id_opaco"] for x in tolerante["agregados"] + sin_lectura["agregados"])
               == sorted(x["id_opaco"] for x in estricta["incompletas"]),
               "sin_ids_en_dos": not (ids_t & ids_e or ids_s & ids_e or ids_s & ids_t),
               "las_sin_lectura_van_enteras": all(x["veredicto_pregunta"] == "requiere_adjudicacion"
                                                  and x["modales"] == [B.MODAL_A_LA_AUTORA] * x["n_criterios"]
                                                  for x in sin_lectura["agregados"]),
               "todos_los_ids_son_casos": all(x["id_opaco"] in casos for x in estricta["agregados"] + tolerante["agregados"]
                                              + sin_lectura["agregados"])}
    if not all(control.values()):
        raise SystemExit(f"ABORTO: los agregados no dan: {[k for k, v in control.items() if not v]}")
    agregados = [dict(x, lectura="estricta") for x in estricta["agregados"]] + \
                [dict(x, lectura="con_lectura_tolerante") for x in tolerante["agregados"]] + \
                [dict(x, lectura="sin_lectura") for x in sin_lectura["agregados"]]
    pob = [x for x in agregados if x["veredicto_pregunta"] == "requiere_adjudicacion"]
    for x in pob:
        if M.veredicto_pregunta(x["modales"]) != "requiere_adjudicacion" or not any(m in AA.ADJUDICA for m in x["modales"]):
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
        adj = [n for n, m in enumerate(ag["modales"], 1) if m in AA.ADJUDICA]
        cr = AA.cerco(caso["respuesta"])
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
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Fichas de la adjudicación de B6.4</title><style>" + estilo +
        f"</style></head><body><h1>Fichas de la adjudicación de B6.4 ({primera} a {ultima})</h1>\n" + "\n".join(fichas_html) +
        "</body></html>\n", encoding="utf-8")
    for nombre in (PLANILLA, PLANILLA.replace(".csv", "_vacia.csv")):
        with open(PL / nombre, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(AA.COLUMNAS)
            w.writerows([[f, n, "", ""] for f, n in renglones])
    vacia = PLANILLA.replace(".csv", "_vacia.csv")
    (PL / vacia.replace(".csv", ".sha256")).write_text(f"{sha(PL / vacia)}  {vacia}\n", encoding="utf-8")
    (PL / ESTRUCTURA).write_text(json.dumps({"columnas": AA.COLUMNAS, "renglones": renglones}, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    (PL / SELLADOR_NOMBRE).write_text(sellador.replace("__SHA_ESTRUCTURA__", sha(PL / ESTRUCTURA)), encoding="utf-8")
    (PL / "LEEME_primero.md").write_text(LEEME.format(
        n_fichas=len(ids), primera=primera, ultima=ultima, md=nombre_md, html=nombre_html, n_criterios=len(renglones),
        planilla=PLANILLA, vacia=vacia, vacia_sha=vacia.replace(".csv", ".sha256"), sellador=SELLADOR_NOMBRE), encoding="utf-8")

    # El control de las fichas: ningún id, sesión, pregunta ni marca de brazo fuera del texto de la respuesta (como en B6.3)
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
    (CL / "clave_adjudicacion_b64.json").write_text(json.dumps(
        {"que": "la clave de la adjudicación de B6.4: de cada ficha, su respuesta y su brazo. Solo en el paquete.",
         "semilla": SEMILLA, "orden": "random.Random(semilla).shuffle de los ids opacos ordenados", "fichas": clave},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    con_marca = sum(any(m in r.lower() for m in ("fragmento", "grafo", "bm25", "denso", "knowledge graph", "nodo")) for r in resps)
    a.informe.parent.mkdir(parents=True, exist_ok=True)
    a.informe.write_text(json.dumps(
        {"control": control, "respuestas_a_la_adjudicacion": len(ids), "criterios_que_marca_la_autora": len(renglones),
         "respuestas_que_nombran_grafo_fragmentos_o_nodos": con_marca,
         "de_la_estricta": sum(f["lectura"] == "estricta" for f in clave),
         "de_la_tolerante": sum(f["lectura"] == "con_lectura_tolerante" for f in clave),
         "sin_lectura": sum(f["lectura"] == "sin_lectura" for f in clave),
         "por_brazo": {b: sum(f["brazo"] == b for f in clave) for b in B.BRAZOS},
         "sin_lectura_por_brazo": {b: sum(f["brazo"] == b and f["lectura"] == "sin_lectura" for f in clave) for b in B.BRAZOS},
         "para_leer": {str(p.relative_to(PL)): sha(p) for p in sorted(PL.rglob("*")) if p.is_file()},
         "clave": {str(p.relative_to(CL)): sha(p) for p in sorted(CL.rglob("*")) if p.is_file()},
         "codigo": {Path(__file__).name: sha(Path(__file__)), "armar_adjudicacion_b63.py": sha(Path(AA.__file__)),
                    "aplicar_lectura_tolerante_b64.py": sha(Path(T.__file__)),
                    "aplicar_lectura_tolerante_b63.py": sha(Path(AP.__file__)), "juez_b63.py": sha(Path(JB.__file__)),
                    "mapping.py": sha(Path(M.__file__))}},
        ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"respuestas_a_la_adjudicacion": len(ids), "criterios_que_marca_la_autora": len(renglones)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
