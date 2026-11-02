"""probar_fichas_y_sellador_control_36_B64.py — la prueba con datos de juguete del armado de las fichas y del sellador de las planillas
de la muestra de control de B6.4, antes de su sello (mesa, §383, 01/11/2026). USD 0, sin API, ningún dato real.

Importa `material/armar_fichas_control_36_B64.py` sin editarlo, y por él el sorteo sellado del repo y el código del juez de la corrida
(`id_opaco` y `sha256_texto` de `b64/v1/juez_b63.py`). Arma 36 fichas de juguete, con respuestas que traen comillas invertidas, HTML,
fines de renglón \r\n, marcas de brazo y de TO, y recorre las ramas del armado (el armado, los controles, la escritura y sus frenos, la
clave, la meta en pasada1/ o pasada2/, la respuesta) y las del sellador (lo que sella y lo que no). Imprime OK o MAL por caso y, al
final, el sha256 del material de juguete que no depende de la hora, para comparar dos corridas byte a byte. Sale con 0 solo si todo da.
  python3 -I -B probar_fichas_y_sellador_control_36_B64.py <repo> <carpeta de trabajo nueva>
"""
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("B", AQUI / "material" / "armar_fichas_control_36_B64.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
REPO, TRABAJO = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
if TRABAJO.exists():
    raise SystemExit("la carpeta de trabajo ya existe")
TRABAJO.mkdir(parents=True)
S = B.cargar_sorteo(REPO)
JB = S.cargar_juez(REPO)
res = []


def caso(nombre, ok):
    res.append(bool(ok))
    print(("OK  " if ok else "MAL ") + nombre)


def frena_con(fn, *a, contiene=""):
    try:
        fn(*a)
    except SystemExit as e:
        return str(e).startswith("FRENO:") and contiene in str(e)
    return False


# ------------------------------------------------------------------------------------------------------------------- #
# Los datos de juguete                                                                                                #
# ------------------------------------------------------------------------------------------------------------------- #
TOS = ["to_a", "to_b", "to_c"]
TRUCOS = {1: "con código:\n```py\nx = 1\n```\ny un tramo ```` largo", 2: "con <b>HTML</b> & \"comillas\" y 'simples'",
          3: "según los fragmentos_hibrida y el grafo", 4: "del to_a y en kg", 5: "con fin de renglón\r\nde Windows\r\n",
          6: "con la marca B63J- y pasada2", 7: "nombra QX08 dentro de la respuesta"}


def datos():
    preguntas, respuestas, fichas = {}, {}, []
    for i in range(1, 37):
        qid, brazo, r, tipo = f"QX{i:02d}", S.BRAZOS[i % 3], 1 + i % 3, S.TIPOS[(i // 3) % 3]
        n = 2 + i % 4
        preguntas[qid] = {"pregunta": f"¿Qué dice la pregunta de juguete número {i}?", "to": TOS[i % 3],
                          "criterios": [{"criterio": f"El criterio {j} de la pregunta {i}.",
                                         "cita_textual": f"La cita {j}, primer renglón.\nSegundo renglón de la cita {j}."}
                                        for j in range(1, n + 1)]}
        resp = f"Respuesta de juguete {i}. " + TRUCOS.get(i, "")
        s = JB.sha256_texto(resp)
        fichas.append({"ficha": f"C{i:02d}", "id_opaco": JB.id_opaco(qid, brazo, r, s), "id_pregunta": qid, "to": TOS[i % 3], "tipo": tipo,
                       "brazo": brazo, "clase": "correcto" if i % 2 else "parcial_o_incorrecto", "id_sesion": f"B63-{qid}-r{r}-{brazo}",
                       "repeticion": r, "sha256_respuesta": s, "marca_d10": i in (3, 6), "n_criterios": n})
        respuestas[f"C{i:02d}"] = resp
    return {"semilla": S.SEMILLA, "fichas": fichas}, preguntas, respuestas


clave, preguntas, respuestas = datos()
EST = B.leer_estaticos(AQUI / "material")
EST_T = {n: b.decode("utf-8") for n, b in EST.items()}
N_CRIT = sum(f["n_criterios"] for f in clave["fichas"])

# 1-6: el armado en memoria y sus controles
arch = B.armar(clave, preguntas, respuestas)
caso("1 el armado da 36 fichas sueltas, las dos juntas, las dos planillas y su estructura (41 archivos)",
     len(arch) == 41 and sum(1 for k in arch if k.startswith("fichas/")) == 36)
caso("2 los controles pasan sobre lo armado y los cuatro archivos de la mesa (45)",
     B.controlar(arch | EST_T, clave, respuestas, TOS) == 45)
caso("3 cada respuesta va tal cual en su ficha, también con \\r\\n y comillas invertidas",
     all(respuestas[f["ficha"]] in arch[f"fichas/{f['ficha']}.md"] for f in clave["fichas"]))
caso("4 el cerco de la ficha con comillas invertidas es más largo que el tramo más largo de la respuesta",
     "`````text" in arch["fichas/C01.md"] and arch["fichas/C02.md"].count("```text") == 1)
est = json.loads(arch[B.ESTRUCTURA])
caso(f"5 las planillas: {N_CRIT} renglones de criterios y 36 de respuestas, con las columnas de la estructura, en el orden de la clave",
     len(est["criterios"]["renglones"]) == N_CRIT and len(est["respuestas"]["renglones"]) == 36
     and arch[B.PR].splitlines()[0].split(",")[2] == "error fuera de los criterios (sí/no)"
     and [r[0] for r in est["respuestas"]["renglones"]] == [f["ficha"] for f in clave["fichas"]])
fuera = "".join(v for k, v in arch.items())
for r in sorted(respuestas.values(), key=len, reverse=True):
    fuera = fuera.replace(r, "")
caso("6 fuera de las respuestas, ningún brazo, tipo, clase, id, sesión ni TO (kg, como palabra entera: «background» la trae)",
     not any(x in fuera for x in ("fragmentos", "agregacion", "remision", "condicion_excepcion", "correcto", "B63", "QX", "to_"))
     and not re.search(r"(?<![A-Za-z0-9_])kg(?![A-Za-z0-9_])", fuera) and "kg" in fuera)


# 7-12: los frenos de los controles
def con(cambio):
    q = json.loads(json.dumps(preguntas))
    cambio(q)
    return B.armar(clave, q, respuestas)


caso("7 un criterio con la palabra kg frena", frena_con(B.controlar, con(lambda q: q["QX05"]["criterios"][0].update(
    criterio="Pesa 3 kg.")), clave, respuestas, TOS, contiene="TO o el nombre de un brazo"))
caso("8 una pregunta con el código de un TO frena", frena_con(B.controlar, con(lambda q: q["QX09"].update(
    pregunta="¿Qué dice to_b?")), clave, respuestas, TOS, contiene="TO o el nombre de un brazo"))
caso("9 una cita con el prefijo del id opaco frena", frena_con(B.controlar, con(lambda q: q["QX10"]["criterios"][1].update(
    cita_textual="ver B63J-")), clave, respuestas, TOS, contiene="marca de brazo"))
caso("10 una pregunta que trae su id frena", frena_con(B.controlar, con(lambda q: q["QX11"].update(
    pregunta="QX11: ¿qué dice?")), clave, respuestas, TOS, contiene="un id de la clave"))
caso("11 un criterio con el nombre del cuarto brazo frena", frena_con(B.controlar, con(lambda q: q["QX12"]["criterios"][0].update(
    criterio="como kg_n7")), clave, respuestas, TOS, contiene="marca de brazo"))
caso("12 un archivo de la mesa con una carpeta de las salidas frena",
     frena_con(B.controlar, arch | EST_T | {"LEEME_primero.md": EST_T["LEEME_primero.md"] + "pasada2"}, clave, respuestas, TOS,
               contiene="LEEME_primero.md trae una marca"))

# 13-15: la escritura
out, copia = TRABAJO / "base" / "para_leer", TRABAJO / "base" / "copia_vacia"
n = B.escribir(REPO, out, copia, arch, EST, clave, respuestas, TOS)
lista = [ln.split("  ") for ln in (copia / B.LISTA_PARA_LEER).read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
caso("13 la escritura vuelve a leer del disco y controla 45 archivos; la lista de para_leer/ da el sha256 y los bytes de cada uno",
     n == 45 and len(lista) == 45 and all(hashlib.sha256((out / r).read_bytes()).hexdigest() == h and int(b) == (out / r).stat().st_size
                                          for h, b, r in lista))
caso("14 la copia vacía trae las dos planillas iguales byte a byte, y \\r\\n queda tal cual en el disco",
     (copia / "planilla_criterios_control_36_B64_vacia.csv").read_bytes() == (out / B.PC).read_bytes()
     and (copia / "planilla_respuestas_control_36_B64_vacia.csv").read_bytes() == (out / B.PR).read_bytes()
     and b"\r\nde Windows\r\n" in (out / "fichas" / "C05.md").read_bytes())
caso("15 no pisa una para_leer/ con archivos, y no escribe dentro del repo",
     frena_con(B.escribir, REPO, out, TRABAJO / "otra_copia", arch, EST, clave, respuestas, TOS, contiene="ya tiene archivos")
     and frena_con(B.escribir, TRABAJO, TRABAJO / "x" / "para_leer", TRABAJO / "x" / "copia", arch, EST, clave, respuestas, TOS,
                   contiene="dentro del repo")
     and not (TRABAJO / "otra_copia").exists() and not (TRABAJO / "x").exists())

# 16-18: la clave, la meta y la respuesta
c2 = json.loads(json.dumps(clave))
c2["fichas"][0], c2["fichas"][1] = c2["fichas"][1], c2["fichas"][0]
c3 = json.loads(json.dumps(clave))
c3["semilla"] = "otra"
c4 = json.loads(json.dumps(clave))
c4["fichas"][1]["id_pregunta"] = c4["fichas"][0]["id_pregunta"]
caso("16 la clave: fichas fuera de orden, otra semilla o una pregunta repetida frenan; la buena pasa",
     frena_con(B.controlar_clave, c2, S, contiene="C01 a C36") and frena_con(B.controlar_clave, c3, S, contiene="semilla")
     and frena_con(B.controlar_clave, c4, S, contiene="36 preguntas") and not frena_con(B.controlar_clave, clave, S))
est_b = {"b1": {"final": {"kg": {"clasificacion": "completa", "id": "S1", "intento": 1, "salida": "pasada1/S1"},
                          "fragmentos_denso": {"clasificacion": "completa", "id": "S2", "intento": 2, "salida": "pasada2/S2"},
                          "fragmentos_hibrida": {"clasificacion": "incompleta_otra", "id": "S3", "intento": 1, "salida": "pasada1/S3"}}},
         "b2": {"final": {"kg": {"clasificacion": "completa", "id": "S4", "intento": 1, "salida": "otra/S4"},
                          "fragmentos_denso": {"clasificacion": "completa", "id": "S5", "intento": 1, "salida": "pasada1/S5"}}},
         "b3": {"final": {"fragmentos_denso": {"clasificacion": "completa", "id": "S5", "intento": 1, "salida": "pasada1/S5"}}}}
caso("17 la meta: de pasada1/ y de pasada2/ según el estado; frenan la sesión que no está, la incompleta, la de otra salida y la repetida",
     B.ruta_meta(est_b, "S1", "kg") == "resultados/real/pasada1/S1/meta_S1.json"
     and B.ruta_meta(est_b, "S2", "fragmentos_denso") == "resultados/real/pasada2/S2/meta_S2.json"
     and frena_con(B.ruta_meta, est_b, "S9", "kg", contiene="una sola vez")
     and frena_con(B.ruta_meta, est_b, "S1", "fragmentos_denso", contiene="una sola vez")
     and frena_con(B.ruta_meta, est_b, "S3", "fragmentos_hibrida", contiene="no es completa")
     and frena_con(B.ruta_meta, est_b, "S4", "kg", contiene="no es completa")
     and frena_con(B.ruta_meta, est_b, "S5", "fragmentos_denso", contiene="una sola vez"))
f0 = clave["fichas"][0]
f_otro = dict(f0, brazo=next(b for b in S.BRAZOS if b != f0["brazo"]))
caso("18 la respuesta: la buena pasa; frenan la cambiada en un carácter, la de otro brazo, la vacía y otro número de criterios",
     not frena_con(B.controlar_respuesta, JB, f0, respuestas["C01"], f0["n_criterios"])
     and frena_con(B.controlar_respuesta, JB, f0, respuestas["C01"] + " ", f0["n_criterios"], contiene="sha256 o el id opaco")
     and frena_con(B.controlar_respuesta, JB, f_otro, respuestas["C01"], f0["n_criterios"], contiene="sha256 o el id opaco")
     and frena_con(B.controlar_respuesta, JB, f0, "  ", f0["n_criterios"], contiene="no trae respuesta")
     and frena_con(B.controlar_respuesta, JB, f0, None, f0["n_criterios"], contiene="no trae respuesta")
     and frena_con(B.controlar_respuesta, JB, f0, respuestas["C01"], f0["n_criterios"] + 1, contiene="número de criterios"))

# 19-30: el sellador, sobre copias de la para_leer/ de juguete
CR, RR = est["criterios"]["renglones"], est["respuestas"]["renglones"]
CC, CRS = est["criterios"]["columnas"], est["respuestas"]["columnas"]
k = [0]


def planillas(crit=None, resp=None, sep=",", bom=False, extra=""):
    k[0] += 1
    d = TRABAJO / f"sello_{k[0]:02d}"
    shutil.copytree(out, d)
    crit = crit or [[f, c, "cumplido" if int(c) % 2 else "No_Cumplido", "", "sí" if c == "2" else "", "", "NO", ""] for f, c in CR]
    resp = resp or [[f[0], "contenido" if i % 5 else "Abstención", "Sí" if i % 7 == 0 else "no", "un error" if i % 7 == 0 else "", "",
                     ""] for i, f in enumerate(RR)]
    for p, cols, filas in ((B.PC, CC, crit), (B.PR, CRS, resp)):
        t = "\r\n".join(sep.join(f'"{x}"' if (sep in x or '"' in x) else x for x in fila) for fila in [cols] + filas) + "\r\n" + extra
        (d / p).write_bytes(("﻿" if bom else "").encode("utf-8") + t.encode("utf-8"))
    return d


def sellar(d):
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "sellar_planillas_control_36_B64.py")], cwd=d, capture_output=True,
                       text=True)
    return p.returncode, p.stdout


def sella(d):
    rc, so = sellar(d)
    return rc == 0 and so.startswith("SELLADAS") and (d / "sello_control_36_B64.txt").exists() and \
        len((d / "sello_control_36_B64.txt").read_text(encoding="utf-8").splitlines()) == 4


def no_sella(d, contiene):
    rc, so = sellar(d)
    return rc == 1 and so.startswith("NO SE SELLA") and contiene in so and not (d / "sello_control_36_B64.txt").exists()


d = planillas()
caso("19 el sellador sella las dos planillas llenas, con mayúsculas y tildes", sella(d))
caso("20 no pisa un sello que ya existe", sellar(d)[0] == 1 and "no se pisa" in sellar(d)[1])
caso("21 con «;», el BOM y renglones vacíos al final, sella", sella(planillas(sep=";", bom=True, extra="\r\n;;;\r\n")))
d = planillas()
(d / B.PC).write_bytes((d / B.PC).read_bytes().replace(b",nota\r\n", b",notas\r\n", 1))
caso("22 una columna cambiada no se sella", no_sella(d, "las columnas no son"))
cr = [[f, c, "cumplido", "", "", "", "", ""] for f, c in CR]
cr[0], cr[1] = cr[1], cr[0]
caso("23 los renglones en otro orden no se sellan", no_sella(planillas(crit=cr), "los renglones no son"))
cr = [[f, c, "si" if (f, c) == tuple(CR[3]) else "cumplido", "", "", "", "", ""] for f, c in CR]
caso("24 un veredicto que no es cumplido ni no_cumplido no se sella", no_sella(planillas(crit=cr), "el veredicto no es"))
cr = [[f, c, "cumplido", "", "quizás" if (f, c) == tuple(CR[5]) else "", "", "", ""] for f, c in CR]
caso("25 una marca que no es sí ni no no se sella", no_sella(planillas(crit=cr), "no es sí ni no"))
rr = [[f[0], "contenido", "sí" if i == 4 else "no", "", "", ""] for i, f in enumerate(RR)]
caso("26 un error fuera de los criterios sin cuál no se sella", no_sella(planillas(resp=rr), "falta cuál"))
rr = [[f[0], "contenido", "", "", "", ""] for f in RR]
caso("27 la columna de error fuera de los criterios vacía en las 36 no se sella (B6.4 no la deja salir)",
     no_sella(planillas(resp=rr), "NO SE SELLA: 36 problema"))
rr = [[f[0], "a medias" if i == 0 else "contenido", "no", "", "", ""] for i, f in enumerate(RR)]
caso("28 una clasificación que no es abstencion ni contenido no se sella", no_sella(planillas(resp=rr), "la clasificación no es"))
d = planillas()
(d / B.PR).rename(TRABAJO / f"sello_{k[0]:02d}_planilla_apartada.csv")
caso("29 si falta una planilla, no se sella", no_sella(d, "falta planilla_respuestas"))
cr = [[f, c, "cumplido", "", "", "", "", ""] for f, c in CR[:-1]]
caso("30 con un renglón de menos, no se sella", no_sella(planillas(crit=cr), "los renglones no son"))

h = hashlib.sha256()
for p in sorted(out.rglob("*")):
    if p.is_file():
        h.update(str(p.relative_to(out)).encode() + b"\0" + p.read_bytes() + b"\0")
print(f"{sum(res)} de {len(res)} casos dan. sha256 del material de juguete: {h.hexdigest()}")
sys.exit(0 if all(res) else 1)
