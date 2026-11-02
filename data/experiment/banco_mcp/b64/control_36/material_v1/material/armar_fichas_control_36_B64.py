"""Arma el material de lectura de la autora para la muestra de control del juez de B6.4: las 36 fichas (C01 a C36), las dos planillas
vacías y su estructura, la copia vacía y el sha256 de cada archivo de para_leer/ (mesa, §383, 01/11/2026). USD 0, sin API.

Es el de B6.3 (`data/experiment/banco_mcp/b63/control_36/sorteo/armar_fichas_control_36_B63.py`) con lo que cambia B6.4:
  - lo corre la autora, sobre la clave que escribió su sorteo, y no la mesa;
  - antes de armar nada, rehace el sorteo sellado del repo (`sortear_control_36_B64.py`, `0c5dcf2c…`) con las mismas entradas y controla
    que dé la misma clave, campo por campo;
  - la meta de cada sesión sale de pasada1/ o de pasada2/, según el estado de la corrida;
  - escribe también la copia vacía de las dos planillas y el sha256 de cada archivo de para_leer/, antes de que la autora empiece;
  - copia a para_leer/ la regla de lectura, la medida del juez, el LEEME y el sellador desde la carpeta de este script.
La ficha trae la pregunta, la respuesta tal cual, sin editarla, y los criterios con su cita textual de la norma, en el orden del archivo
de las preguntas, que es el del juez. No trae el brazo, el veredicto, la sesión, ningún id ni el TO (y por eso tampoco el documento, sus
páginas ni el ancla), ni el tipo.

Uso: python3 -I -B armar_fichas_control_36_B64.py <repo> <banco_b64> <manifiesto_fuera_B64.json> <su sha256> <clave_control_36_B64.json>
     <carpeta para_leer> <carpeta copia_vacia>

Lee, solo lectura:
  - del repo, cada uno igual al de HEAD: el script del sorteo sellado, y por él la entrada sellada de B6.4, su configuración y el código
    del juez de la corrida; el archivo de las 96 preguntas que nombra la entrada, con su sha256;
  - el manifiesto de lo que queda fuera, con el sha256 que se le pasa, y de banco_b64/, con el sha256 del manifiesto, lo que lee el sorteo
    (para rehacerlo) y la meta de cada sesión de la clave, de la que toma solo `final_json_R4.respuesta`: la respuesta tiene que dar el
    sha256 de la clave y recalcular su id opaco;
  - la clave del sorteo.
No escribe en el repo, en banco_b64/ ni en la carpeta de la clave. Imprime solo cuentas y sha256: ningún texto, id, brazo ni veredicto.
"""
import csv
import hashlib
import html
import importlib.util
import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path

RUTA_SORTEO = "data/experiment/banco_mcp/b64/control_36/sorteo/sortear_control_36_B64.py"
SHA_SORTEO = "0c5dcf2cde4e19212e6b54915ae458395da4a8ed1b5f856f89a93eece9866ee2"
COLS_CRIT = ["ficha", "criterio", "veredicto (cumplido / no_cumplido)", "fragmento de la respuesta (opcional)",
             "dudosa para mí (sí/no)", "necesita experto del dominio (sí/no)", "criterio mal planteado (sí/no)", "nota"]
COLS_RESP = ["ficha", "clasificación (abstencion / contenido)", "error fuera de los criterios (sí/no)", "cuál", "minutos", "nota"]
PC, PR = "planilla_criterios_control_36_B64.csv", "planilla_respuestas_control_36_B64.csv"
ESTRUCTURA = "estructura_planillas.json"
ESTATICOS = ["LEEME_primero.md", "regla_de_lectura_control_36_B64.md", "como_se_mide_el_juez_control_36_B64.md",
             "sellar_planillas_control_36_B64.py"]
COPIA_VACIA = "sha256_copia_vacia_control_36_B64.txt"
LISTA_PARA_LEER = "sha256_para_leer_control_36_B64.txt"
# Lo que no puede aparecer fuera del texto de una respuesta: los nombres de los brazos, los prefijos de los ids y de las sesiones, y las
# carpetas de las salidas. El brazo `kg` y los TOs se buscan como palabra entera, más abajo.
MARCAS = ("fragmentos_hibrida", "fragmentos_denso", "kg_n7", "B63J-", "B63-", "id_opaco", "pasada1", "pasada2", "meta_")
ESTILO = ("body{font-family:Georgia,serif;max-width:46rem;margin:2rem auto;padding:0 1rem;line-height:1.5;background:#fff;color:#111}"
          "pre{white-space:pre-wrap;word-wrap:break-word;background:#f6f6f2;padding:.8rem;border-left:3px solid #999}"
          "blockquote{margin:.4rem 0 .8rem 1rem;color:#333;font-style:italic}section{page-break-after:always}")


def frena(m):
    raise SystemExit(f"FRENO: {m}")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------------------------------------------------- #
# La lectura de las entradas                                                                                            #
# --------------------------------------------------------------------------------------------------------------------- #
def cargar_sorteo(repo: Path):
    """El script del sorteo del repo, el sellado e igual al de HEAD, importado sin editarlo."""
    p = repo / RUTA_SORTEO
    b = p.read_bytes()
    if sha256(b) != SHA_SORTEO:
        frena("el script del sorteo del repo no es el sellado (0c5dcf2c…)")
    h = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "show", f"HEAD:{RUTA_SORTEO}"], capture_output=True)
    if h.returncode != 0 or h.stdout != b:
        frena("el script del sorteo no es el de HEAD")
    spec = importlib.util.spec_from_file_location("sortear_control_36_B64", p)
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    return S


def controlar_clave(clave: dict, S) -> None:
    fs = clave.get("fichas") or []
    if [f.get("ficha") for f in fs] != [f"C{i:02d}" for i in range(1, S.N + 1)]:
        frena("las fichas de la clave no son C01 a C36, en su orden")
    if clave.get("semilla") != S.SEMILLA:
        frena("la semilla de la clave no es la del sorteo sellado")
    if len({f["id_pregunta"] for f in fs}) != S.N:
        frena("la clave no trae 36 preguntas distintas")


def ruta_meta(estado_bloques: dict, id_sesion: str, brazo: str) -> str:
    """La meta de la sesión, en pasada1/ o en pasada2/, según el estado de la corrida (`estado_b63.json`, tal cual)."""
    hall = [f for v in estado_bloques.values() for x, f in v["final"].items() if x == brazo and f.get("id") == id_sesion]
    if len(hall) != 1:
        frena("la sesión de una ficha no está una sola vez en el estado de la corrida")
    f = hall[0]
    if f.get("clasificacion") != "completa" or f.get("salida") not in (f"pasada1/{id_sesion}", f"pasada2/{id_sesion}"):
        frena("la sesión de una ficha no es completa, o su salida no está en pasada1/ ni en pasada2/")
    return f"resultados/real/{f['salida']}/meta_{id_sesion}.json"


def controlar_respuesta(JB, f: dict, resp, n_criterios: int) -> None:
    if not isinstance(resp, str) or not resp.strip():
        frena(f"la meta de {f['ficha']} no trae respuesta")
    if JB.sha256_texto(resp) != f["sha256_respuesta"] or \
            JB.id_opaco(f["id_pregunta"], f["brazo"], f["repeticion"], f["sha256_respuesta"]) != f["id_opaco"]:
        frena(f"la respuesta de {f['ficha']} no da el sha256 o el id opaco de la clave")
    if n_criterios != f["n_criterios"]:
        frena(f"{f['ficha']}: el número de criterios no es el de la clave")


def leer_preguntas(repo: Path, S) -> dict:
    """{id: {pregunta, to, criterios: [{criterio, cita_textual}]}}, con el esquema de la entrada sellada y en el orden del archivo."""
    e = json.loads(S.de_head(repo, S.DEL_REPO["entrada"]).decode("utf-8"))
    rp = e["preguntas"]["ruta"]
    pq_b = (Path(rp).expanduser() if rp.startswith("~") else repo / rp).read_bytes()
    if sha256(pq_b) != e["preguntas"]["sha256"]:
        frena("el archivo de las preguntas no da el sha256 de la entrada sellada")
    esq = e["preguntas"]["esquema"]
    lista = json.loads(pq_b.decode("utf-8"))[esq["lista"]]
    return {p[esq["id"]]: {"pregunta": p[esq["pregunta"]], "to": p["to"],
                           "criterios": [{"criterio": c[esq["criterio"]], "cita_textual": c[esq["cita"]]} for c in p[esq["criterios"]]]}
            for p in lista}


def leer_entradas(repo: Path, banco: Path, manifiesto: Path, sha_man: str, clave_p: Path) -> dict:
    S = cargar_sorteo(repo)
    clave_b = clave_p.read_bytes()
    clave = json.loads(clave_b.decode("utf-8"))
    controlar_clave(clave, S)
    sha, filas, rec, salen, n_metas, n_agr = S.leer_real(repo, banco, manifiesto, sha_man)
    if clave.get("sha256_entradas") != sha:
        frena("las entradas de la clave no son las de ahora: algún sha256 cambió desde el sorteo")
    rehecha = S.sortear(filas) | {"poblacion": {"sesiones": S.ESPERADO["sesiones"], "juzgadas": len(rec),
                                                 "con_sus_tres_juicios": n_agr, "elegibles": len(filas)}, "salen": salen}
    if any(clave.get(k) != v for k, v in rehecha.items()):
        frena("la clave no es la que da el sorteo sellado al rehacerlo con las mismas entradas")
    preguntas = leer_preguntas(repo, S)
    man = json.loads(manifiesto.read_bytes().decode("utf-8"))
    idx = {a["ruta"]: a["sha256"] for a in man["archivos"]}

    def del_banco(rel: str) -> bytes:
        b = (banco / rel).read_bytes()
        if idx.get("banco_b64/" + rel) != sha256(b):
            frena("un archivo de banco_b64/ no está en el manifiesto o no da su sha256")
        return b

    estado = json.loads(del_banco(S.DEL_BANCO["estado"]).decode("utf-8"))["bloques"]
    JB = S.cargar_juez(repo)
    respuestas = {}
    for f in clave["fichas"]:
        q = preguntas.get(f["id_pregunta"])
        if q is None:
            frena(f"la pregunta de {f['ficha']} no está en el archivo de las preguntas")
        m = json.loads(del_banco(ruta_meta(estado, f["id_sesion"], f["brazo"])).decode("utf-8"))
        resp = (m.get("final_json_R4") or {}).get("respuesta")
        controlar_respuesta(JB, f, resp, len(q["criterios"]))
        respuestas[f["ficha"]] = resp
    return {"clave": clave, "sha_clave": sha256(clave_b), "preguntas": preguntas, "respuestas": respuestas,
            "tos": sorted({p["to"] for p in preguntas.values()}), "n_metas": n_metas, "n_repo": len(S.DEL_REPO) + 2}


# --------------------------------------------------------------------------------------------------------------------- #
# El armado, en memoria                                                                                                 #
# --------------------------------------------------------------------------------------------------------------------- #
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


def csv_texto(cols: list, filas: list) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=cols)
    w.writeheader()
    w.writerows(filas)
    return s.getvalue()


def armar(clave: dict, preguntas: dict, respuestas: dict) -> dict:
    """{ruta relativa a para_leer/: texto}: las fichas, sueltas y juntas, las dos planillas vacías y su estructura."""
    fs = clave["fichas"]
    out, mds, htmls = {}, [], []
    for f in fs:
        q, resp = preguntas[f["id_pregunta"]], respuestas[f["ficha"]]
        out[f"fichas/{f['ficha']}.md"] = md = ficha_md(f["ficha"], q, resp)
        mds.append(md)
        htmls.append(ficha_html(f["ficha"], q, resp))
    out["fichas_C01_a_C36.md"] = "\n\n---\n\n".join(mds) + "\n"
    out["fichas_C01_a_C36.html"] = (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Fichas de la muestra de control</title><style>" + ESTILO + "</style></head><body>"
        "<h1>Fichas de la muestra de control de B6.4 (C01 a C36)</h1>\n" + "\n".join(htmls) + "</body></html>\n")
    filas_crit = [dict(zip(COLS_CRIT, [f["ficha"], str(i)] + [""] * (len(COLS_CRIT) - 2)))
                  for f in fs for i in range(1, f["n_criterios"] + 1)]
    filas_resp = [dict(zip(COLS_RESP, [f["ficha"]] + [""] * (len(COLS_RESP) - 1))) for f in fs]
    out[PC], out[PR] = csv_texto(COLS_CRIT, filas_crit), csv_texto(COLS_RESP, filas_resp)
    out[ESTRUCTURA] = json.dumps(
        {"criterios": {"columnas": COLS_CRIT, "renglones": [[x["ficha"], x["criterio"]] for x in filas_crit]},
         "respuestas": {"columnas": COLS_RESP, "renglones": [[x["ficha"]] for x in filas_resp]}}, ensure_ascii=False, indent=1) + "\n"
    return out


def controlar(archivos: dict, clave: dict, respuestas: dict, tos: list) -> int:
    """Cada respuesta tal cual en su ficha y en las dos juntas; fuera de las respuestas, ningún id de la clave, marca de brazo o de
    sesión, TO ni el nombre del brazo del grafo. Devuelve cuántos archivos controló."""
    fs = clave["fichas"]
    for f in fs:
        r = respuestas[f["ficha"]]
        if r not in archivos[f"fichas/{f['ficha']}.md"] or r not in archivos["fichas_C01_a_C36.md"] or \
                html.escape(r) not in archivos["fichas_C01_a_C36.html"]:
            frena(f"la respuesta de {f['ficha']} no está tal cual en su ficha")
    ids = [x for f in fs for x in (f["id_opaco"], f["id_sesion"], f["id_pregunta"])]
    palabras = [re.compile(r"(?<![A-Za-z0-9_])" + re.escape(t) + r"(?![A-Za-z0-9_])") for t in list(tos) + ["kg"]]
    sacar = sorted(respuestas.values(), key=len, reverse=True)
    for nombre in sorted(archivos):
        txt = archivos[nombre]
        for r in sacar:
            txt = txt.replace(r, "").replace(html.escape(r), "")
        if any(x in txt for x in ids):
            frena(f"{nombre} trae un id de la clave")
        if any(m in txt for m in MARCAS):
            frena(f"{nombre} trae una marca de brazo o de sesión fuera de una respuesta")
        if any(p.search(txt) for p in palabras):
            frena(f"{nombre} trae un TO o el nombre de un brazo fuera de una respuesta")
    return len(archivos)


def leer_estaticos(carpeta: Path) -> dict:
    return {n: (carpeta / n).read_bytes() for n in ESTATICOS}


# --------------------------------------------------------------------------------------------------------------------- #
# La escritura                                                                                                          #
# --------------------------------------------------------------------------------------------------------------------- #
def escribir(repo: Path, out: Path, copia: Path, archivos: dict, estaticos: dict, clave: dict, respuestas: dict, tos: list) -> int:
    for d in (out, copia):
        r = d.resolve()
        if r == repo or repo in r.parents:
            frena("una carpeta de salida queda dentro del repo")
        if d.exists() and any(d.iterdir()):
            frena(f"la carpeta {d.name} ya tiene archivos: no se pisa")
    (out / "fichas").mkdir(parents=True, exist_ok=True)
    for rel, t in archivos.items():
        with open(out / rel, "w", encoding="utf-8", newline="") as fh:
            fh.write(t)
    for n, b in estaticos.items():
        (out / n).write_bytes(b)
    # Se vuelve a leer del disco, sin traducir los fines de renglón, y se controla otra vez.
    en_disco = {str(p.relative_to(out)): p.read_bytes().decode("utf-8") for p in sorted(out.rglob("*")) if p.is_file()}
    if set(en_disco) != set(archivos) | set(estaticos):
        frena("para_leer/ no tiene exactamente los archivos armados")
    n = controlar(en_disco, clave, respuestas, tos)
    hora = time.strftime("%Y-%m-%d %H:%M:%S %z")
    copia.mkdir(parents=True, exist_ok=True)
    lin_c = ["# sha256  bytes  nombre: la copia de las dos planillas vacías de para_leer/, hecha antes de que la autora empiece",
             f"# copiado: {hora}"]
    for p in (PC, PR):
        b = (out / p).read_bytes()
        v = p.replace(".csv", "_vacia.csv")
        (copia / v).write_bytes(b)
        lin_c.append(f"{sha256(b)}  {len(b)}  {v}")
    (copia / COPIA_VACIA).write_text("\n".join(lin_c) + "\n", encoding="utf-8")
    lin_p = ["# sha256  bytes  ruta (relativa a para_leer/): cada archivo, anotado antes de que la autora empiece", f"# anotado: {hora}"]
    for rel in sorted(en_disco):
        b = (out / rel).read_bytes()
        lin_p.append(f"{sha256(b)}  {len(b)}  {rel}")
    (copia / LISTA_PARA_LEER).write_text("\n".join(lin_p) + "\n", encoding="utf-8")
    return n


def main() -> int:
    repo, banco, manifiesto = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    sha_man, clave_p, out, copia = sys.argv[4], Path(sys.argv[5]).resolve(), Path(sys.argv[6]), Path(sys.argv[7])
    for d in (out, copia):
        if d.exists() and any(d.iterdir()):
            frena(f"la carpeta {d.name} ya tiene archivos: no se pisa")
    ent = leer_entradas(repo, banco, manifiesto, sha_man, clave_p)
    clave, respuestas, tos = ent["clave"], ent["respuestas"], ent["tos"]
    print(f"controles: el script del sorteo es el sellado y el de HEAD; {ent['n_repo']} entradas del repo iguales a HEAD; "
          f"las de banco_b64/ y {ent['n_metas']} metas con el sha256 del manifiesto de lo que queda fuera; "
          "las preguntas, con el sha256 de la entrada sellada")
    print(f"la clave: la que da el sorteo sellado al rehacerlo con las mismas entradas; sha256 {ent['sha_clave']}")
    print("las 36 respuestas: cada una da el sha256 de la clave y su id opaco recalculado")
    archivos = armar(clave, ent["preguntas"], respuestas)
    estaticos = leer_estaticos(Path(__file__).resolve().parent)
    controlar(archivos | {n: b.decode("utf-8") for n, b in estaticos.items()}, clave, respuestas, tos)
    n = escribir(repo, out, copia, archivos, estaticos, clave, respuestas, tos)
    print(json.dumps({"fichas": len(clave["fichas"]), "criterios": sum(f["n_criterios"] for f in clave["fichas"]), "archivos": n,
                      "fichas_con_alguna_marca_de_D10": sum(bool(f["marca_d10"]) for f in clave["fichas"])}, ensure_ascii=False))
    for nm, b in estaticos.items():
        print(f"copiado a para_leer/: {nm}  {sha256(b)}")
    print(f"escritas: para_leer/ ({n} archivos) y copia_vacia/ (las dos planillas vacías, {COPIA_VACIA} y {LISTA_PARA_LEER})")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as ex:  # sin el mensaje: podría traer un valor de los datos
        tb = ex.__traceback__
        while tb.tb_next:
            tb = tb.tb_next
        raise SystemExit(f"FRENO: {type(ex).__name__} en el renglón {tb.tb_lineno} de {Path(tb.tb_frame.f_code.co_filename).name}")
