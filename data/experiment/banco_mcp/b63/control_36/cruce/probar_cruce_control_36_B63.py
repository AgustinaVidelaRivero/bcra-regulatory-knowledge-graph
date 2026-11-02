"""probar_cruce_control_36_B63.py — la prueba del cruce de la muestra de control de B6.3 con una lectura de juguete y su sello (mesa,
unidad C36_a, 29/10/2026). En la carpeta de trabajo que se le pasa (no tiene que existir) arma carpetas de lectura de juguete con las
planillas del armador (`../sorteo/armar_fichas_control_36_B63.py`, `escribir_planillas`), las llena con una lectura inventada, las sella
con el sellador de la autora (`../para_leer/sellar_planillas_control_36_B63.py`, copiado tal cual) y las cruza con una clave y unos
agregados de juguete, con desacuerdos puestos a mano, cuyas cifras la prueba calcula por su cuenta. Después, los casos en contra: una
planilla cambiada después del sello, sin sello, la estructura cambiada, los agregados de otro sorteo, y los rechazos del sellador. Ningún
dato real. Imprime OK o MAL por caso, la salida del cruce de la base y el sha256 de su salida, para comparar dos corridas byte a byte.
USD 0.
  python3 -I -B probar_cruce_control_36_B63.py <carpeta de trabajo>
"""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import math
import random
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def cargar(nombre: str, p: Path):
    spec = importlib.util.spec_from_file_location(nombre, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


C = cargar("C", AQUI / "cruce_control_36_B63.py")
B = cargar("B", AQUI.parent / "sorteo" / "armar_fichas_control_36_B63.py")
SELLADOR = AQUI.parent / "para_leer" / "sellar_planillas_control_36_B63.py"
W = Path(sys.argv[1])
if W.exists():
    raise SystemExit("la carpeta de trabajo ya existe")
W.mkdir(parents=True)
res = []


def c(nombre, ok):
    res.append(bool(ok))
    print("OK " if ok else "MAL", nombre)


# --- la muestra de juguete: 36 fichas, 12 por brazo, 9 y 3 por tipo en cada uno -------------------------------------------- #
FICHAS = []
for i in range(36):
    t = "dato_directo" if i % 4 == 3 else "varios_puntos"
    FICHAS.append({"ficha": f"C{i + 1:02d}", "id_opaco": f"B63J-jug{i:05d}", "id_pregunta": f"QJ{i:02d}", "to": f"to_{i % 5}", "tipo": t,
                   "brazo": C.BRAZOS[i % 3], "clase": "correcto" if i % 2 else "parcial_o_incorrecto",
                   "n_criterios": 3 + i % 3 if t == "varios_puntos" else 1 + i % 2})
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


def juez(a_vp: int, b_vp: int, b_dd: int) -> dict:
    """Los modales del juez: los de la autora, con a_vp pares de varios puntos en la dirección A, b_vp en la B y b_dd de dato directo
    en la B, tomados en orden; la clasificación, la de la autora salvo en C04."""
    m = dict(AUTORA)
    cuenta = {"A_vp": 0, "B_vp": 0, "B_dd": 0}
    for (fi, k), v in sorted(AUTORA.items()):
        t = next(f["tipo"] for f in FICHAS if f["ficha"] == fi)
        if t == "varios_puntos" and v == "no_cumplido" and cuenta["A_vp"] < a_vp and (fi, k) != ("C01", 1):
            m[(fi, k)], cuenta["A_vp"] = "cumplido", cuenta["A_vp"] + 1
        elif t == "varios_puntos" and v == "cumplido" and cuenta["B_vp"] < b_vp and (fi, k) != ("C01", 1):
            m[(fi, k)], cuenta["B_vp"] = "no_cumplido", cuenta["B_vp"] + 1
        elif t == "dato_directo" and v == "cumplido" and cuenta["B_dd"] < b_dd:
            m[(fi, k)], cuenta["B_dd"] = "no_cumplido", cuenta["B_dd"] + 1
    m[("C01", 1)] = "cumplido" if AUTORA[("C01", 1)] == "no_cumplido" else "no_cumplido"    # el par marcado «experto», en desacuerdo
    agr = {"agregados": [{"id_opaco": f["id_opaco"], "n_criterios": f["n_criterios"],
                          "modales": [m[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)],
                          "veredicto_pregunta": veredicto([m[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)]),
                          "clasificacion_respuesta_modal": "contenido" if f["ficha"] == "C04" else CLAS_AUTORA[f["ficha"]]}
                         for f in FICHAS], "incompletas": []}
    return {"modales": m, "agr": agr}


def esperado(J: dict, tipo: str) -> dict:
    ps = [(f, k) for f in FICHAS if f["tipo"] == tipo for k in range(1, f["n_criterios"] + 1)]
    n, acu = len(ps), sum(J["modales"][(f["ficha"], k)] == AUTORA[(f["ficha"], k)] for f, k in ps)
    z = 1.959964
    p = acu / n
    wi = (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)
    fs = [f for f in FICHAS if f["tipo"] == tipo]
    acu_r = sum(veredicto([J["modales"][(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)])
                == veredicto([AUTORA[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)]) for f in fs)
    return {"n": n, "acuerdo": acu, "wi": wi, "n_r": len(fs), "acuerdo_r": acu_r}


def carpeta(nombre: str, error=True, valor_malo=False, error_a_medias=False) -> tuple:
    """Una carpeta de lectura de juguete, con su copia_vacia, llena y sin sellar."""
    A, CV = W / nombre / "para_leer", W / nombre / "copia_vacia"
    A.mkdir(parents=True)
    CV.mkdir(parents=True)
    B.escribir_planillas(A, [(f["ficha"], f["n_criterios"]) for f in FICHAS])
    shutil.copyfile(SELLADOR, A / SELLADOR.name)
    (CV / C.LISTA_MESA).write_text("# sha256  bytes  ruta\n" + "".join(
        f"{hashlib.sha256((A / n).read_bytes()).hexdigest()}  {(A / n).stat().st_size}  {n}\n"
        for n in sorted(x.name for x in A.iterdir())), encoding="utf-8")
    filas = []
    for f in FICHAS:
        for k in range(1, f["n_criterios"] + 1):
            filas.append(dict(zip(B.COLS_CRIT, [f["ficha"], str(k), "No cumplido" if AUTORA[(f["ficha"], k)] == "no_cumplido" else "cumplido",
                                                "", "sí" if (f["ficha"], k) in DUDOSA else "", "Sí" if (f["ficha"], k) in EXPERTO else "no",
                                                "", ""])))
    if valor_malo:
        filas[3][B.COLS_CRIT[2]] = "quizás"
    with open(A / B.PC, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=B.COLS_CRIT)
        w.writeheader()
        w.writerows(filas)
    filas = []
    for i, f in enumerate(FICHAS):
        e = ("sí" if f["ficha"] in ERROR else "no") if error and not (error_a_medias and i % 2) else ""
        filas.append(dict(zip(B.COLS_RESP, [f["ficha"], CLAS_AUTORA[f["ficha"]], e, ERROR.get(f["ficha"], "") if e == "sí" else "",
                                            MINUTOS.get(f["ficha"], "2"), ""])))
    with open(A / B.PR, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=B.COLS_RESP, delimiter=";")
        w.writeheader()
        w.writerows(filas)
    return A, CV


def sellar(A: Path) -> tuple:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cargar(f"sellador_{A.parent.name}", A / SELLADOR.name).main()
    return rc, out.getvalue()


def clave_y_agr(nombre: str, J: dict) -> tuple:
    agr_p, clave_p = W / nombre / "agregados_juguete.json", W / nombre / "clave_juguete.json"
    agr_p.write_text(json.dumps(J["agr"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    clave_p.write_text(json.dumps({"fichas": FICHAS, "sha256_entradas": {C.AGR: hashlib.sha256(agr_p.read_bytes()).hexdigest()}},
                                  ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return clave_p, agr_p


def cruzar(A, CV, clave_p, agr_p, salida) -> tuple:
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            C.main([str(A), str(CV), str(clave_p), str(agr_p), str(salida)])
        return "ok", out.getvalue()
    except SystemExit as e:
        return str(e), out.getvalue()


# --- la base: la lectura sellada y el cruce, dos veces ------------------------------------------------------------------- #
A, CV = carpeta("base")
rc, txt = sellar(A)
c("el sellador sella la lectura de juguete (con «,» en criterios y «;» en respuestas, mayúsculas y tildes)",
  rc == 0 and (A / "sello_control_36_B63.txt").is_file() and "salió" not in (A / "sello_control_36_B63.txt").read_text(encoding="utf-8"))
rc2, txt2 = sellar(A)
c("el sellador no pisa un sello que ya existe", rc2 == 1 and "no se pisa" in txt2)
J = juez(2, 1, 1)
clave_p, agr_p = clave_y_agr("base", J)
e1, consola = cruzar(A, CV, clave_p, agr_p, W / "base" / "salida_1.json")
e2, _ = cruzar(A, CV, clave_p, agr_p, W / "base" / "salida_2.json")
c("el cruce corre dos veces sobre la misma lectura y da la misma salida, byte a byte",
  e1 == e2 == "ok" and (W / "base" / "salida_1.json").read_bytes() == (W / "base" / "salida_2.json").read_bytes())
o = json.loads((W / "base" / "salida_1.json").read_text(encoding="utf-8"))
ok = True
for t in C.TIPOS:
    x, esp = o["por_tipo"][t], esperado(J, t)
    ok &= (x["criterio"]["n"], x["criterio"]["acuerdo"], x["respuesta"]["n"], x["respuesta"]["acuerdo"]) == \
          (esp["n"], esp["acuerdo"], esp["n_r"], esp["acuerdo_r"]) and abs(x["criterio"]["wilson_inferior_sin_redondear"] - esp["wi"]) < 1e-12
c("por tipo: los pares, el acuerdo por criterio, su Wilson inferior y el acuerdo por respuesta son los calculados aparte", ok)
vp = o["por_tipo"]["varios_puntos"]
c("varios puntos: el piso de 0,85 se compara sin redondear y aquí se alcanza; dato directo, sin piso",
  esperado(J, "varios_puntos")["wi"] >= 0.85 and vp["piso"]["llega"] is True and "piso" not in o["por_tipo"]["dato_directo"])
c("las dos direcciones: A 2 en varios puntos más el par de C01, B 1 en varios puntos y 1 en dato directo",
  vp["criterio"]["direccion_A_juez_acredita"] + vp["criterio"]["direccion_B_juez_no_acredita"] == 4
  and o["por_tipo"]["dato_directo"]["criterio"]["direccion_B_juez_no_acredita"] == 1
  and o["por_tipo"]["total"]["criterio"]["n"] == vp["criterio"]["n"] + o["por_tipo"]["dato_directo"]["criterio"]["n"])
c("la cifra sin «necesita experto del dominio» saca el par C01-1 (en desacuerdo) y sube el acuerdo",
  vp["criterio_sin_experto_ni_mal_planteado"]["n"] == vp["criterio"]["n"] - 1
  and vp["criterio_sin_experto_ni_mal_planteado"]["acuerdo"] == vp["criterio"]["acuerdo"])
por_b = {b: sum(1 for f in FICHAS if f["ficha"] in ERROR and f["brazo"] == b) for b in C.BRAZOS}
ef = o["errores_fuera_de_los_criterios"]
c("el error fuera de los criterios, contado por brazo (de 12) y por tipo, con sus fichas",
  not ef["salio_declarada"] and ef["n"] == len(ERROR) and ef["fichas"] == sorted(ERROR)
  and {b: v["n"] for b, v in ef["por_brazo"].items()} == por_b and all(v["de"] == 12 for v in ef["por_brazo"].values())
  and sum(v["n"] for v in ef["por_tipo"].values()) == len(ERROR))
c("abstención o contenido: un desacuerdo (C04); marcas y minutos aparte",
  o["por_tipo"]["total"]["clasificacion_abstencion_contenido"]["desacuerdos"] == ["C04"]
  and o["marcas_de_la_autora"] == {"dudosa": ["C06-2"], "experto": ["C01-1"], "mal_planteado": []}
  and o["minutos"] == {"con_numero": 34, "vacios": 1, "sin_numero_legible": 1, "total": 12.5 + 2 * 31})
c("la salida no trae ningún texto de la autora (ni «cuál» ni la nota)", not any(v in json.dumps(o, ensure_ascii=False) for v in ERROR.values()))

# --- el piso no se alcanza ----------------------------------------------------------------------------------------------- #
J2 = juez(12, 10, 0)
(W / "base_bajo").mkdir()
clave2, agr2 = clave_y_agr("base_bajo", J2)
e, _ = cruzar(A, CV, clave2, agr2, W / "base_bajo" / "salida.json")
o2 = json.loads((W / "base_bajo" / "salida.json").read_text(encoding="utf-8"))
c("con 23 desacuerdos en varios puntos el Wilson inferior queda bajo 0,85 y el cruce lo dice",
  e == "ok" and o2["por_tipo"]["varios_puntos"]["piso"]["llega"] is False
  and abs(o2["por_tipo"]["varios_puntos"]["criterio"]["wilson_inferior_sin_redondear"] - esperado(J2, "varios_puntos")["wi"]) < 1e-12)

# --- en contra ----------------------------------------------------------------------------------------------------------- #
A3, CV3 = carpeta("cambiada")
sellar(A3)
with open(A3 / B.PR, "a", encoding="utf-8") as fh:
    fh.write(" ")
e, _ = cruzar(A3, CV3, W / "no_existe_clave.json", W / "no_existe_agregados.json", W / "cambiada" / "salida.json")
c("una planilla cambiada después del sello frena, sin abrir la clave ni los agregados (no existen y no los pidió)",
  e.startswith("FRENO") and "no da el sha256 o los bytes de su sello" in e and not (W / "cambiada" / "salida.json").exists())
A4, CV4 = carpeta("sin_sello")
e, _ = cruzar(A4, CV4, W / "no_existe_clave.json", W / "no_existe_agregados.json", W / "sin_sello" / "salida.json")
c("sin el sello de la autora, frena antes de la clave", e == "FRENO: no hay sello de la autora")
A5, CV5 = carpeta("estructura")
sellar(A5)
(A5 / C.ESTRUCTURA).write_text((A5 / C.ESTRUCTURA).read_text(encoding="utf-8") + " ", encoding="utf-8")
e, _ = cruzar(A5, CV5, W / "no_existe_clave.json", W / "no_existe_agregados.json", W / "estructura" / "salida.json")
c("la estructura cambiada después de que la mesa anotó su sha256 frena", "no es la que anotó la mesa" in e)
otro = W / "base" / "agregados_de_otro_sorteo.json"
otro.write_text(agr_p.read_text(encoding="utf-8") + " ", encoding="utf-8")
e, _ = cruzar(A, CV, clave_p, otro, W / "base" / "salida_otro.json")
c("unos agregados que no son los de la clave del sorteo frenan", e == "FRENO: los agregados del juez no son los del sorteo")
A6, _ = carpeta("valor_malo", valor_malo=True)
rc, txt = sellar(A6)
c("el sellador no sella un veredicto fuera de la plantilla", rc == 1 and "NO SE SELLA" in txt and not (A6 / "sello_control_36_B63.txt").exists())
A7, _ = carpeta("error_a_medias", error_a_medias=True)
rc, txt = sellar(A7)
c("el sellador no sella la columna de error vacía solo en algunas", rc == 1 and "no es sí ni no" in txt)
A8, CV8 = carpeta("sin_error", error=False)
rc, txt = sellar(A8)
e, _ = cruzar(A8, CV8, clave_p, agr_p, W / "sin_error" / "salida.json")
o8 = json.loads((W / "sin_error" / "salida.json").read_text(encoding="utf-8")) if e == "ok" else {}
c("la columna de error vacía en las 36: se sella como la que salió, declarada, y el cruce lo informa",
  rc == 0 and "salió, declarada" in (A8 / "sello_control_36_B63.txt").read_text(encoding="utf-8")
  and o8.get("errores_fuera_de_los_criterios") == {"salio_declarada": True})

print(f"pruebas: {sum(res)} de {len(res)}")
print("la salida del cruce de la base:")
print(consola, end="")
print("sha256 de la salida del cruce de la base:", hashlib.sha256((W / "base" / "salida_1.json").read_bytes()).hexdigest())
