"""probar_cruce_sobre_la_v1_B64.py — Mesa, §385 (01/11/2026): que el cruce de la muestra de 36 de B6.4 (`cruce_control_36_B64.py`, el de
la §384, sin cambios) corre igual sobre una para_leer/ armada con el material v1 (§383) que sobre una armada con la v2 (§384). Las dos
versiones difieren solo en la medida y en la regla; el armado, el sellador y el LEEME son los mismos. El cruce controla los archivos de
para_leer/ contra la lista que escribió el armado al armarla, no contra los sha256 de una versión.

Arma, con cada versión y su propio armado, la misma lectura de juguete, la sella con su sellador y la cruza con la misma clave y los mismos
agregados de juguete. Controla que el cruce no frene con la v1, que su salida sea byte a byte la de la v2, que la medida y la regla de la
para_leer/ de la v1 sean las de la v1, y que una regla de la v1 cambiada después del armado frene. Ningún dato real. Imprime OK o MAL
por caso y sale con 0 solo si todo da. USD 0.
  python3 -I -B probar_cruce_sobre_la_v1_B64.py <cruce_control_36_B64.py> <material v1> <material v2> <carpeta de trabajo nueva>
"""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import random
import sys
from pathlib import Path

CRUCE, V1, V2, W = (Path(x).resolve() for x in sys.argv[1:5])
if W.exists():
    raise SystemExit("la carpeta de trabajo ya existe")
W.mkdir(parents=True)


def cargar(nombre, p):
    spec = importlib.util.spec_from_file_location(nombre, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


C = cargar("C", CRUCE)
B1 = cargar("B1", V1 / "armar_fichas_control_36_B64.py")
B2 = cargar("B2", V2 / "armar_fichas_control_36_B64.py")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
res = []


def c(nombre, ok):
    res.append(bool(ok))
    print(("OK  " if ok else "MAL ") + nombre)


TOS = ["to_a", "to_b", "to_c", "to_d", "to_e"]
FICHAS, PREG, RESP = [], {}, {}
for i in range(36):
    b, t, n, q = C.BRAZOS[i % 3], C.TIPOS[(i // 3) % 3], 3 + i % 3, f"QJ{i:02d}"
    FICHAS.append({"ficha": f"C{i + 1:02d}", "id_opaco": f"B63J-jug{i:05d}", "id_pregunta": q, "to": TOS[i % 5], "tipo": t, "brazo": b,
                   "clase": "correcto" if i % 2 else "parcial_o_incorrecto", "id_sesion": f"B63-{q}-r1-{b}", "repeticion": 1,
                   "sha256_respuesta": "", "marca_d10": False, "n_criterios": n})
    PREG[q] = {"pregunta": f"¿Qué pide la pregunta de juguete número {i}?", "to": TOS[i % 5],
               "criterios": [{"criterio": f"El criterio {k} de la pregunta {i}.", "cita_textual": f"La cita {k}."}
                             for k in range(1, n + 1)]}
    RESP[f"C{i + 1:02d}"] = f"La respuesta de juguete número {i}."
CLAVE = {"semilla": "juguete", "fichas": FICHAS}
r = random.Random(11)
AUTORA = {(f["ficha"], k): ("cumplido" if r.random() < 0.6 else "no_cumplido") for f in FICHAS for k in range(1, f["n_criterios"] + 1)}
JUEZ = dict(AUTORA)
for k in sorted(AUTORA)[:3]:
    JUEZ[k] = "cumplido" if AUTORA[k] == "no_cumplido" else "no_cumplido"


def veredicto(m):
    return "correcto" if all(x == "cumplido" for x in m) else "incorrecto" if all(x == "no_cumplido" for x in m) else "parcial"


AGR = {"agregados": [{"id_opaco": f["id_opaco"], "n_criterios": f["n_criterios"],
                      "modales": [JUEZ[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)],
                      "veredicto_pregunta": veredicto([JUEZ[(f["ficha"], k)] for k in range(1, f["n_criterios"] + 1)]),
                      "clasificacion_respuesta_modal": "contenido"} for f in FICHAS], "incompletas": []}
agr_p, clave_p = W / "agregados_juguete.json", W / "clave_juguete.json"
agr_p.write_text(json.dumps(AGR, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
clave_p.write_text(json.dumps({"fichas": FICHAS, "sha256_entradas": {C.AGR: sha(agr_p)}}, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")


def armar_y_leer(nombre, B, MAT):
    A, CV = W / nombre / "para_leer", W / nombre / "copia_vacia"
    B.escribir(W / "no_es_el_repo", A, CV, B.armar(CLAVE, PREG, RESP), B.leer_estaticos(MAT), CLAVE, RESP, TOS)
    with open(A / B.PC, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=B.COLS_CRIT)
        w.writeheader()
        w.writerows(dict(zip(B.COLS_CRIT, [f["ficha"], str(k), AUTORA[(f["ficha"], k)], "", "", "", "", ""]))
                    for f in FICHAS for k in range(1, f["n_criterios"] + 1))
    with open(A / B.PR, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=B.COLS_RESP)
        w.writeheader()
        w.writerows(dict(zip(B.COLS_RESP, [f["ficha"], "contenido", "sí" if f["ficha"] == "C03" else "no",
                                           "uno" if f["ficha"] == "C03" else "", "2", ""])) for f in FICHAS)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cargar(f"sellador_{nombre}", A / "sellar_planillas_control_36_B64.py").main()
    return A, CV, rc


def cruzar(A, CV, salida):
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            C.main([str(A), str(CV), str(clave_p), sha(clave_p), str(agr_p), str(salida)])
        return "ok", out.getvalue()
    except SystemExit as e:
        return str(e), out.getvalue()


A1, CV1, rc1 = armar_y_leer("v1", B1, V1)
A2, CV2, rc2 = armar_y_leer("v2", B2, V2)
c("1 la misma lectura de juguete se sella con el sellador de la v1 y con el de la v2", rc1 == 0 and rc2 == 0)
c("2 la para_leer/ de la v1 trae la medida y la regla de la v1, distintas de las de la v2",
  sha(A1 / "como_se_mide_el_juez_control_36_B64.md") == sha(V1 / "como_se_mide_el_juez_control_36_B64.md")
  and sha(A1 / "regla_de_lectura_control_36_B64.md") == sha(V1 / "regla_de_lectura_control_36_B64.md")
  and sha(A1 / "como_se_mide_el_juez_control_36_B64.md") != sha(A2 / "como_se_mide_el_juez_control_36_B64.md")
  and sha(A1 / "regla_de_lectura_control_36_B64.md") != sha(A2 / "regla_de_lectura_control_36_B64.md"))
e1, con1 = cruzar(A1, CV1, W / "v1" / "salida.json")
e2, con2 = cruzar(A2, CV2, W / "v2" / "salida.json")
c("3 el cruce no frena sobre la para_leer/ de la v1: controla sus 43 archivos contra la lista de su armado",
  e1 == "ok" and json.loads((W / "v1" / "salida.json").read_text(encoding="utf-8"))["insumos"]
  ["archivos_de_para_leer_iguales_a_los_anotados"] == 43)
c("4 la salida y la consola del cruce son byte a byte las mismas sobre la v1 y sobre la v2",
  e2 == "ok" and (W / "v1" / "salida.json").read_bytes() == (W / "v2" / "salida.json").read_bytes() and con1 == con2)
o = json.loads((W / "v1" / "salida.json").read_text(encoding="utf-8"))
c("5 sobre la v1 da las cifras por brazo (informativas) y la principal con su piso, sobre los 144 pares",
  sorted(o["por_brazo_informativo_sin_piso_ni_prueba"]) == sorted(C.BRAZOS) and o["total"]["criterio"]["n"] == 144
  and o["total"]["criterio"]["acuerdo"] == 141 and "piso" in o["total"])
A3, CV3, _ = armar_y_leer("v1_regla_cambiada", B1, V1)
(A3 / "regla_de_lectura_control_36_B64.md").write_text((A3 / "regla_de_lectura_control_36_B64.md").read_text(encoding="utf-8") + " ",
                                                       encoding="utf-8")
e3, _ = cruzar(A3, CV3, W / "v1_regla_cambiada" / "salida.json")
c("6 una regla de la v1 cambiada después del armado frena, antes de abrir la clave",
  "no son los que anotó el armado" in e3 and "regla_de_lectura" in e3)
print(f"{sum(res)} de {len(res)} casos dan. sha256 de la salida sobre la v1: {sha(W / 'v1' / 'salida.json')}")
sys.exit(0 if all(res) else 1)
