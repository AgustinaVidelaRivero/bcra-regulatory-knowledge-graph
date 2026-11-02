"""probar_cruce_control_36_B64.py — la prueba del cruce de la muestra de control de B6.4 con una lectura de juguete y su sello (mesa, §384,
01/11/2026). Es la de B6.3 (`probar_cruce_control_36_B63.py`) con lo que cambia B6.4. En la carpeta de trabajo que se le pasa (no tiene
que existir) arma carpetas de lectura de juguete con el armado de las fichas de la v2
(`../control_36/material/armar_fichas_control_36_B64.py`, `armar` y `escribir`, que escriben también la copia vacía y la lista de
para_leer/), las llena con una lectura inventada, las sella con el
sellador de la autora (`../control_36/material/sellar_planillas_control_36_B64.py`, copiado por el armado) y las cruza con una clave y unos
agregados de juguete, con desacuerdos puestos a mano, cuyas cifras la prueba calcula por su cuenta: en total, por tipo y por brazo.
Después, los casos en contra. Ningún dato real. Imprime OK o MAL por caso, la salida del cruce de la base y el sha256 de su salida, para
comparar dos corridas byte a byte. USD 0.
  python3 -I -B probar_cruce_control_36_B64.py <carpeta de trabajo>
"""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import math
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MAT = AQUI.parent / "control_36" / "material"


def cargar(nombre: str, p: Path):
    spec = importlib.util.spec_from_file_location(nombre, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


C = cargar("C", AQUI / "cruce_control_36_B64.py")
B = cargar("B", MAT / "armar_fichas_control_36_B64.py")
W = Path(sys.argv[1]).resolve()
if W.exists():
    raise SystemExit("la carpeta de trabajo ya existe")
W.mkdir(parents=True)
NO_REPO = W / "no_es_el_repo"
EST = B.leer_estaticos(MAT)
res = []


def c(nombre, ok):
    res.append(bool(ok))
    print("OK " if ok else "MAL", nombre)


# --- la muestra de juguete: 36 fichas, 12 por brazo y 4 de cada tipo en cada brazo ----------------------------------------- #
TOS = ["to_a", "to_b", "to_c", "to_d", "to_e"]
FICHAS, PREG, RESP = [], {}, {}
for i in range(36):
    b, t = C.BRAZOS[i % 3], C.TIPOS[(i // 3) % 3]
    n = 3 + i % 3
    q = f"QJ{i:02d}"
    FICHAS.append({"ficha": f"C{i + 1:02d}", "id_opaco": f"B63J-jug{i:05d}", "id_pregunta": q, "to": TOS[i % 5], "tipo": t, "brazo": b,
                   "clase": "correcto" if i % 2 else "parcial_o_incorrecto", "id_sesion": f"B63-{q}-r1-{b}", "repeticion": 1,
                   "sha256_respuesta": "", "marca_d10": False, "n_criterios": n})
    PREG[q] = {"pregunta": f"¿Qué pide la pregunta de juguete número {i}?", "to": TOS[i % 5],
               "criterios": [{"criterio": f"El criterio {k} de la pregunta {i}.", "cita_textual": f"La cita {k}."}
                             for k in range(1, n + 1)]}
    RESP[f"C{i + 1:02d}"] = f"La respuesta de juguete número {i}."
CLAVE_BASE = {"semilla": "juguete", "fichas": FICHAS}
r = random.Random(7)
AUTORA = {(f["ficha"], k): ("cumplido" if r.random() < 0.6 else "no_cumplido") for f in FICHAS for k in range(1, f["n_criterios"] + 1)}
CLAS_AUTORA = {f["ficha"]: ("abstencion" if f["ficha"] in ("C04", "C17") else "contenido") for f in FICHAS}
ERROR = {"C02": "afirma un plazo que la norma no da", "C05": "confunde dos sujetos obligados", "C10": "un umbral equivocado",
         "C11": "otro sujeto"}
EXPERTO = {("C01", 1)}
DUDOSA = {("C06", 2)}
MINUTOS = {"C01": "5", "C02": "4,5", "C03": "3 min", "C04": "", "C05": "un rato"}


def veredicto(m):
    return "correcto" if all(x == "cumplido" for x in m) else "incorrecto" if all(x == "no_cumplido" for x in m) else "parcial"


def juez(a_n: int, b_n: int) -> dict:
    """Los modales del juez: los de la autora, con a_n pares en la dirección A y b_n en la B, tomados en orden, más el par «experto»
    C01-1 siempre en desacuerdo; la clasificación, la de la autora salvo en C04."""
    m = dict(AUTORA)
    ca = cb = 0
    for (fi, k), v in sorted(AUTORA.items()):
        if (fi, k) == ("C01", 1):
            continue
        if v == "no_cumplido" and ca < a_n:
            m[(fi, k)], ca = "cumplido", ca + 1
        elif v == "cumplido" and cb < b_n:
            m[(fi, k)], cb = "no_cumplido", cb + 1
    m[("C01", 1)] = "cumplido" if AUTORA[("C01", 1)] == "no_cumplido" else "no_cumplido"
    agr = {"agregados": [{"id_opaco": f["id_opaco"], "n_criterios": f["n_criterios"],
                          "modales": [m[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)],
                          "veredicto_pregunta": veredicto([m[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)]),
                          "clasificacion_respuesta_modal": "contenido" if f["ficha"] == "C04" else CLAS_AUTORA[f["ficha"]]}
                         for f in FICHAS], "incompletas": []}
    return {"modales": m, "agr": agr}


def esperado(J: dict, filtro) -> dict:
    fs = [f for f in FICHAS if filtro(f)]
    ps = [(f, k) for f in fs for k in range(1, f["n_criterios"] + 1)]
    n, acu = len(ps), sum(J["modales"][(f["ficha"], k)] == AUTORA[(f["ficha"], k)] for f, k in ps)
    z = 1.959964
    p = acu / n
    wi = (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)
    acu_r = sum(veredicto([J["modales"][(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)])
                == veredicto([AUTORA[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)]) for f in fs)
    return {"n": n, "acuerdo": acu, "wi": wi, "n_r": len(fs), "acuerdo_r": acu_r}


def carpeta(nombre: str, error_vacio_en=(), sin_cual_en=()) -> tuple:
    """Una carpeta de lectura de juguete armada con el armado de la v2 (con su copia vacía y su lista), llena y sin sellar."""
    A, CV = W / nombre / "para_leer", W / nombre / "copia_vacia"
    B.escribir(NO_REPO, A, CV, B.armar(CLAVE_BASE, PREG, RESP), EST, CLAVE_BASE, RESP, TOS)
    filas = []
    for f in FICHAS:
        for k in range(1, f["n_criterios"] + 1):
            v = "No cumplido" if AUTORA[(f["ficha"], k)] == "no_cumplido" else "cumplido"
            filas.append(dict(zip(B.COLS_CRIT, [f["ficha"], str(k), v,
                                                "", "sí" if (f["ficha"], k) in DUDOSA else "", "Sí" if (f["ficha"], k) in EXPERTO else "no",
                                                "", ""])))
    with open(A / B.PC, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=B.COLS_CRIT)
        w.writeheader()
        w.writerows(filas)
    filas = []
    for f in FICHAS:
        e = "" if f["ficha"] in error_vacio_en else ("sí" if f["ficha"] in ERROR else "no")
        cual = "" if f["ficha"] in sin_cual_en else ERROR.get(f["ficha"], "")
        filas.append(dict(zip(B.COLS_RESP, [f["ficha"], CLAS_AUTORA[f["ficha"]], e, cual if e == "sí" else "",
                                            MINUTOS.get(f["ficha"], "2"), ""])))
    with open(A / B.PR, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=B.COLS_RESP, delimiter=";")
        w.writeheader()
        w.writerows(filas)
    return A, CV


def sellar(A: Path) -> tuple:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cargar(f"sellador_{A.parent.name}", A / "sellar_planillas_control_36_B64.py").main()
    return rc, out.getvalue()


def sello_a_mano(A: Path) -> None:
    """Un sello con la forma del sellador, escrito sin sus controles: para probar que el cruce controla por su cuenta."""
    lin = ["# sello a mano de la prueba", "# sellado: 2026-11-01 00:00:00 -0300"]
    for p in (A / B.PC, A / B.PR):
        b = p.read_bytes()
        lin.append(f"{hashlib.sha256(b).hexdigest()}  {len(b)}  2026-11-01 00:00:00 -0300  {p.name}")
    (A / "sello_control_36_B64.txt").write_text("\n".join(lin) + "\n", encoding="utf-8")


def clave_y_agr(nombre: str, J: dict, fichas=None) -> tuple:
    (W / nombre).mkdir(parents=True, exist_ok=True)
    agr_p, clave_p = W / nombre / "agregados_juguete.json", W / nombre / "clave_juguete.json"
    agr_p.write_text(json.dumps(J["agr"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    clave_p.write_text(json.dumps({"fichas": fichas or FICHAS, "sha256_entradas": {C.AGR: hashlib.sha256(agr_p.read_bytes()).hexdigest()}},
                                  ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return clave_p, hashlib.sha256(clave_p.read_bytes()).hexdigest(), agr_p


def cruzar(A, CV, clave_p, sha_clave, agr_p, salida) -> tuple:
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            C.main([str(A), str(CV), str(clave_p), sha_clave, str(agr_p), str(salida)])
        return "ok", out.getvalue()
    except SystemExit as e:
        return str(e), out.getvalue()


NO_CLAVE, NO_AGR = W / "no_existe_clave.json", W / "no_existe_agregados.json"

# --- la base: la lectura sellada y el cruce, dos veces ----------------------------------------------------------------------- #
A, CV = carpeta("base")
rc, txt = sellar(A)
c("1 el sellador sella la lectura de juguete (con «,» en criterios y «;» en respuestas, mayúsculas y tildes)",
  rc == 0 and (A / "sello_control_36_B64.txt").is_file())
rc2, txt2 = sellar(A)
c("2 el sellador no pisa un sello que ya existe", rc2 == 1 and "no se pisa" in txt2)
J = juez(2, 2)
clave_p, sha_clave, agr_p = clave_y_agr("base", J)
e1, consola = cruzar(A, CV, clave_p, sha_clave, agr_p, W / "base" / "salida_1.json")
e2, _ = cruzar(A, CV, clave_p, sha_clave, agr_p, W / "base" / "salida_2.json")
c("3 el cruce corre dos veces sobre la misma lectura y da la misma salida, byte a byte",
  e1 == e2 == "ok" and (W / "base" / "salida_1.json").read_bytes() == (W / "base" / "salida_2.json").read_bytes())
o = json.loads((W / "base" / "salida_1.json").read_text(encoding="utf-8"))


def coincide(x, esp):
    return (x["criterio"]["n"], x["criterio"]["acuerdo"], x["respuesta"]["n"], x["respuesta"]["acuerdo"]) == \
        (esp["n"], esp["acuerdo"], esp["n_r"], esp["acuerdo_r"]) and abs(x["criterio"]["wilson_inferior_sin_redondear"] - esp["wi"]) < 1e-12


et = esperado(J, lambda f: True)
c("4 las 36 juntas: 144 pares, el acuerdo por criterio, su Wilson inferior y el acuerdo por respuesta son los calculados aparte",
  et["n"] == 144 and coincide(o["total"], et))
c("5 el piso de 0,85 va sobre las 36 juntas, sin redondear, y aquí se alcanza; ni los tipos ni los brazos llevan piso",
  et["wi"] >= 0.85 and o["total"]["piso"]["llega"] is True
  and not any("piso" in x for x in list(o["por_tipo_sin_piso"].values()) + list(o["por_brazo_informativo_sin_piso_ni_prueba"].values())))
c("6 por tipo: 12 respuestas cada uno, con las cifras calculadas aparte",
  all(coincide(o["por_tipo_sin_piso"][t], esperado(J, lambda f, t=t: f["tipo"] == t)) and o["por_tipo_sin_piso"][t]["respuesta"]["n"] == 12
      for t in C.TIPOS))
c("7 por brazo (informativo): 12 respuestas cada uno, con las cifras calculadas aparte, y los brazos suman el total",
  all(coincide(o["por_brazo_informativo_sin_piso_ni_prueba"][b], esperado(J, lambda f, b=b: f["brazo"] == b))
      and o["por_brazo_informativo_sin_piso_ni_prueba"][b]["respuesta"]["n"] == 12 for b in C.BRAZOS)
  and sum(o["por_brazo_informativo_sin_piso_ni_prueba"][b]["criterio"]["n"] for b in C.BRAZOS) == 144)
tc = o["total"]["criterio"]
c("8 las dos direcciones: A 2 más o menos el par de C01, B 2 más o menos el par de C01, 5 desacuerdos en total",
  tc["direccion_A_juez_acredita"] + tc["direccion_B_juez_no_acredita"] == 5 and tc["n"] - tc["acuerdo"] == 5)
c("9 la cifra sin «necesita experto del dominio» saca el par C01-1 (en desacuerdo)",
  o["total"]["criterio_sin_experto_ni_mal_planteado"]["n"] == 143
  and o["total"]["criterio_sin_experto_ni_mal_planteado"]["acuerdo"] == tc["acuerdo"])
por_b = {b: sum(1 for f in FICHAS if f["ficha"] in ERROR and f["brazo"] == b) for b in C.BRAZOS}
por_t = {t: sum(1 for f in FICHAS if f["ficha"] in ERROR and f["tipo"] == t) for t in C.TIPOS}
ef = o["errores_fuera_de_los_criterios"]
c("10 el error fuera de los criterios, por brazo (de 12) y por tipo (de 12), con sus fichas",
  ef["n"] == len(ERROR) and ef["de"] == 36 and ef["fichas"] == sorted(ERROR)
  and {b: v["n"] for b, v in ef["por_brazo"].items()} == por_b and all(v["de"] == 12 for v in ef["por_brazo"].values())
  and {t: v["n"] for t, v in ef["por_tipo"].items()} == por_t and all(v["de"] == 12 for v in ef["por_tipo"].values()))
c("11 abstención o contenido: un desacuerdo (C04); marcas y minutos aparte",
  o["total"]["clasificacion_abstencion_contenido"]["desacuerdos"] == ["C04"]
  and o["marcas_de_la_autora"] == {"dudosa": ["C06-2"], "experto": ["C01-1"], "mal_planteado": []}
  and o["minutos"] == {"con_numero": 34, "vacios": 1, "sin_numero_legible": 1, "total": 12.5 + 2 * 31})
c("12 la salida no trae ningún texto de la autora (ni «cuál» ni la nota), y controla los demás archivos de para_leer/",
  not any(v in json.dumps(o, ensure_ascii=False) for v in ERROR.values())
  and o["insumos"]["archivos_de_para_leer_iguales_a_los_anotados"] == 43
  and o["formato_de_las_planillas"]["archivos_de_mas_en_para_leer"] == [])

# --- el piso no se alcanza --------------------------------------------------------------------------------------------------- #
J2 = juez(12, 10)
clave2, sha2, agr2 = clave_y_agr("base_bajo", J2)
e, _ = cruzar(A, CV, clave2, sha2, agr2, W / "base_bajo" / "salida.json")
o2 = json.loads((W / "base_bajo" / "salida.json").read_text(encoding="utf-8")) if e == "ok" else {}
e2b = esperado(J2, lambda f: True)
c("13 con 23 desacuerdos el Wilson inferior de las 36 queda bajo 0,85 y el cruce lo dice",
  e == "ok" and e2b["wi"] < 0.85 and o2["total"]["piso"]["llega"] is False
  and abs(o2["total"]["criterio"]["wilson_inferior_sin_redondear"] - e2b["wi"]) < 1e-12)

# --- en contra ----------------------------------------------------------------------------------------------------------------- #
A3, CV3 = carpeta("cambiada")
sellar(A3)
with open(A3 / B.PR, "a", encoding="utf-8") as fh:
    fh.write(" ")
e, _ = cruzar(A3, CV3, NO_CLAVE, sha_clave, NO_AGR, W / "cambiada" / "salida.json")
c("14 una planilla cambiada después del sello frena, sin abrir la clave ni los agregados (no existen y no los pidió)",
  "no da el sha256 o los bytes de su sello" in e and not (W / "cambiada" / "salida.json").exists())
A4, CV4 = carpeta("sin_sello")
e, _ = cruzar(A4, CV4, NO_CLAVE, sha_clave, NO_AGR, W / "sin_sello" / "salida.json")
c("15 sin el sello de la autora, frena antes de la clave", e == "FRENO: no hay sello de la autora")
A5, CV5 = carpeta("ficha_cambiada")
sellar(A5)
(A5 / "fichas" / "C07.md").write_text((A5 / "fichas" / "C07.md").read_text(encoding="utf-8") + " ", encoding="utf-8")
e, _ = cruzar(A5, CV5, NO_CLAVE, sha_clave, NO_AGR, W / "ficha_cambiada" / "salida.json")
c("16 una ficha cambiada después del armado frena antes de la clave", "no son los que anotó el armado" in e and "fichas/C07.md" in e)
A6, CV6 = carpeta("estructura")
sellar(A6)
(A6 / B.ESTRUCTURA).write_text((A6 / B.ESTRUCTURA).read_text(encoding="utf-8") + " ", encoding="utf-8")
e, _ = cruzar(A6, CV6, NO_CLAVE, sha_clave, NO_AGR, W / "estructura" / "salida.json")
c("17 la estructura cambiada después del armado frena", "no son los que anotó el armado" in e)
A7, CV7 = carpeta("vacia")
sellar(A7)
(CV7 / "planilla_criterios_control_36_B64_vacia.csv").write_text("x", encoding="utf-8")
e, _ = cruzar(A7, CV7, NO_CLAVE, sha_clave, NO_AGR, W / "vacia" / "salida.json")
c("18 la copia vacía cambiada frena", "la copia vacía" in e)
e, _ = cruzar(A, CV, clave_p, "0" * 64, agr_p, W / "base" / "salida_otra_clave.json")
c("19 una clave que no da el sha256 que imprimió el armado frena",
  e == "FRENO: la clave no da el sha256 que imprimió el armado de las fichas")
otro = W / "base" / "agregados_de_otro_sorteo.json"
otro.write_text(agr_p.read_text(encoding="utf-8") + " ", encoding="utf-8")
e, _ = cruzar(A, CV, clave_p, sha_clave, otro, W / "base" / "salida_otros_agregados.json")
c("20 unos agregados que no son los de la clave del sorteo frenan", e == "FRENO: los agregados del juez no son los del sorteo")
e, _ = cruzar(A, CV, clave_p, sha_clave, agr_p, W / "base" / "salida_1.json")
c("21 no pisa una salida que ya existe", e == "FRENO: la salida ya existe: no se pisa")
A8, CV8 = carpeta("de_mas")
sellar(A8)
(A8 / "planilla_criterios_control_36_B64.xlsx").write_bytes(b"juguete")
clave8, sha8, agr8 = clave_y_agr("de_mas", J)
e, _ = cruzar(A8, CV8, clave8, sha8, agr8, W / "de_mas" / "salida.json")
o8 = json.loads((W / "de_mas" / "salida.json").read_text(encoding="utf-8")) if e == "ok" else {}
c("22 un archivo de más en para_leer/ (una planilla guardada en otro formato) no frena: se lista en la salida",
  e == "ok" and o8["formato_de_las_planillas"]["archivos_de_mas_en_para_leer"] == ["planilla_criterios_control_36_B64.xlsx"])
A9, CV9 = carpeta("error_vacio", error_vacio_en=("C03",))
rc9, txt9 = sellar(A9)
sello_a_mano(A9)
e, _ = cruzar(A9, CV9, NO_CLAVE, sha_clave, NO_AGR, W / "error_vacio" / "salida.json")
c("23 el error fuera de los criterios vacío en una: el sellador no sella, y con un sello a mano el cruce frena antes de la clave",
  rc9 == 1 and "no es sí ni no" in txt9 and e == "FRENO: C03: un valor fuera de la plantilla")
A10, CV10 = carpeta("sin_cual", sin_cual_en=("C05",))
rc10, txt10 = sellar(A10)
sello_a_mano(A10)
e, _ = cruzar(A10, CV10, NO_CLAVE, sha_clave, NO_AGR, W / "sin_cual" / "salida.json")
c("24 un error sin «cuál»: el sellador no sella, y con un sello a mano el cruce frena",
  rc10 == 1 and e == "FRENO: C05: un valor fuera de la plantilla")
mal = [dict(f) for f in FICHAS]
mal[0]["brazo"], mal[1]["brazo"] = mal[1]["brazo"], mal[1]["brazo"]
clave11, sha11, agr11 = clave_y_agr("cuotas", J, mal)
e, _ = cruzar(A, CV, clave11, sha11, agr11, W / "cuotas" / "salida.json")
c("25 una clave sin 12 fichas por brazo frena", e == "FRENO: la clave no trae 12 fichas por brazo y 4 por tipo en cada brazo")

print(f"pruebas: {sum(res)} de {len(res)}")
print("la salida del cruce de la base:")
print(consola, end="")
print("sha256 de la salida del cruce de la base:", hashlib.sha256((W / "base" / "salida_1.json").read_bytes()).hexdigest())
sys.exit(0 if all(res) else 1)
