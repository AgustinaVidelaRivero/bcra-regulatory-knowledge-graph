"""probar_armar_aprobadas_B64_mesa.py — mesa, §373 (31/10/2026): la prueba del armador de las 96 aprobadas, con datos de juguete (ningún
texto real). Arma en <tmp> un fuera_del_repo de juguete: seis olas (94 preguntas), 2 reubicados, 16 R1 y 4 R2, sus listas de
rechazadas, cuatro revisiones con su marcada y su sello, y los sha256 esperados (--prueba). Corre el armador en cada caso, en una
carpeta de salida nueva, y controla su código, su mensaje y si escribió:
  T1  todo bien: 96, 32 por tipo; dos corridas dan el mismo archivo, byte a byte;
  T2  una aprobada de las olas cambia de tipo (33, 31 y 32): frena por la decisión 4, sin escribir;
  T3  la R2 trae una rechazada: frena (hace falta una R3);
  T4  --sello-r2 que no es el del sello: frena;  T5  sin --sello-r2: frena;
  T6  la carpeta de salida no está vacía: frena;
  T7  una ola que no da su sha256: frena;
  T8  las rechazadas de la R1 no son las de la lista de la R2: frena;
  T9  un criterio con la cita vacía: frena;
  T10 una marcada con una fila sin «sí» ni «no»: frena;
  T11 un archivo del sello de una revisión que no da sus bytes: frena.
  python3 -I -B probar_armar_aprobadas_B64_mesa.py <tmp>
"""
import copy
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

TMP = Path(sys.argv[1])
ARMADOR = Path(__file__).resolve().parent / "armar_aprobadas_B64_mesa.py"
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
TIPOS = ("agregacion", "remision", "condicion_excepcion")


def pregunta(qid, tipo):
    to = "doc" + qid[5:7].lower()
    return {"id": qid, "pregunta": f"pregunta de juguete {qid}", "tipo": tipo, "to": to, "clase": "RI",
            "criterios": [{"criterio": f"criterio {j}", "cita_textual": f"cita de juguete {j}", "unidad": f"{to}::{j}"} for j in (1, 2)],
            "anclas": [{"rol": "ancla", "unidad": f"{to}::1"}, {"rol": "otro_punto", "unidad": f"{to}::2"}]}


def datos():
    """Las 96 aprobadas finales tienen 32 por tipo: el tipo de un lugar es el de su índice módulo 3; los reemplazos lo heredan."""
    lug = [(o, l) for o in range(1, 7) for l in range(1, 17)]
    tipo = {x: TIPOS[i % 3] for i, x in enumerate(lug)}
    base = lambda o, l: f"B64-O{o}-L{l:02d}"  # noqa: E731
    olas = {o: [pregunta(base(o, l), tipo[(o, l)]) for l in range(1, 17) if not (o == 6 and l > 14)] for o in range(1, 7)}
    reub = [pregunta(base(6, l), tipo[(6, l)]) for l in (15, 16)]
    rech_olas = [base(o, l) for o, l in lug if l in (3, 6, 9, 12) and not (o == 6 and l > 14)][:16]
    r1 = [pregunta(i + "-R1", tipo[(int(i[5]), int(i[8:10]))]) for i in rech_olas]
    rech_r1 = [q["id"] for q in r1[:4]]
    r2 = [pregunta(i[:-3] + "-R2", tipo[(int(i[5]), int(i[8:10]))]) for i in rech_r1]
    return olas, reub, rech_olas, r1, rech_r1, r2


def escribir(raiz, olas, reub, rech_olas, r1, rech_r1, r2, marca=None):
    """Escribe el fuera_del_repo de juguete y devuelve los sha256 esperados y el del sello de la R2."""
    b = raiz / "b64_p2"
    (b / "olas").mkdir(parents=True)
    (b / "insumos").mkdir()
    esp = {}

    def w(rel, obj):
        f = b / rel
        f.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        esp[rel] = sha(f.read_bytes())
    for o, qs in olas.items():
        w(f"olas/ola_{o}.json", {"ola": o, "preguntas": qs})
    w("olas/reubicados_O6_L15_L16.json", {"preguntas": reub})
    w("olas/reemplazos_R1_B64.json", {"ronda": "R1", "preguntas": r1})
    w("olas/reemplazos_R2_B64.json", {"ronda": "R2", "preguntas": r2})
    w("insumos/rechazadas_B64_R1.json", {"rechazadas": [{"id": i} for i in rech_olas]})
    w("insumos/rechazadas_B64_R2.json", {"rechazadas": [{"id": i} for i in rech_r1]})
    revs = (("olas", "revision_b64_olas_1_a_6", "sello_hoja_revision_B64.txt", "hoja_revision_B64_olas_1_a_6_marcada.csv",
             [q["id"] for qs in olas.values() for q in qs], set(rech_olas)),
            ("reubicados", "revision_b64_reubicados", "sello_hoja_revision_B64_reubicados.txt",
             "hoja_revision_B64_reubicados_marcada.csv", [q["id"] for q in reub], set()),
            ("R1", "revision_b64_reemplazos_R1", "sello_hoja_revision_B64_reemplazos_R1.txt",
             "hoja_revision_B64_reemplazos_R1_marcada.csv", [q["id"] for q in r1], set(rech_r1)),
            ("R2", "revision_b64_reemplazos_R2", "sello_hoja_revision_B64_reemplazos_R2.txt",
             "hoja_revision_B64_reemplazos_R2_marcada.csv", [q["id"] for q in r2], set()))
    for nombre, carpeta, sello, marcada, ids, no in revs:
        rev = raiz / carpeta
        rev.mkdir()
        buf = io.StringIO()
        wr = csv.DictWriter(buf, ["id", "aprueba", "motivo_si_no", "tipo_se_sostiene", "lectura_N2_se_confirma"], lineterminator="\n")
        wr.writeheader()
        for i in ids:
            a = "no" if i in no else "sí"
            if marca and marca[0] == nombre and marca[1] == i:
                a = marca[2]
            wr.writerow({"id": i, "aprueba": a, "motivo_si_no": "motivo de juguete" if a == "no" else "", "tipo_se_sostiene": "sí",
                         "lectura_N2_se_confirma": ""})
        (rev / marcada).write_text(buf.getvalue(), encoding="utf-8")
        (rev / marcada.replace("_marcada", "").replace("hoja_", "exportacion_")).write_text("exportación de juguete\n", encoding="utf-8")
        (rev / marcada.replace("_marcada", "")).write_text("hoja de juguete\n", encoding="utf-8")
        lineas = ["# sello de juguete"]
        for f in sorted(p for p in rev.iterdir()):
            lineas.append(f"{sha(f.read_bytes())}  {f.stat().st_size}  2026-10-31 00:00:00  {f.name}")
        (rev / sello).write_text("\n".join(lineas) + "\n", encoding="utf-8")
        esp[f"sello_{nombre}"] = sha((rev / sello).read_bytes())
    sello_r2 = esp.pop("sello_R2")
    (raiz / "esperados.json").write_text(json.dumps(esp, indent=1) + "\n", encoding="utf-8")
    return esp, sello_r2


def correr(raiz, sello_r2, salida, extra=()):
    args = [sys.executable, "-I", "-B", str(ARMADOR), str(raiz), str(salida), "--prueba", str(raiz / "esperados.json")]
    if sello_r2 is not None:
        args += ["--sello-r2", sello_r2]
    r = subprocess.run(args + list(extra), capture_output=True, text=True)
    escribio = salida.exists() and any(salida.iterdir()) if salida.exists() else False
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "", escribio


RES = []


def caso(nombre, que, ok, det):
    RES.append((nombre, ok))
    print(("PASA " if ok else "FALLA ") + f"{nombre} {que} | {det}", flush=True)


TMP.mkdir(parents=True, exist_ok=True)
if any(TMP.iterdir()):
    raise SystemExit("la carpeta de la prueba no está vacía")
D = datos()
# T1
r = TMP / "t1"
esp, s2 = escribir(r, *D)
c1, m1, e1 = correr(r, s2, r / "salida_1")
c2, m2, e2 = correr(r, s2, r / "salida_2")
iguales = (r / "salida_1/aprobadas_B64.json").read_bytes() == (r / "salida_2/aprobadas_B64.json").read_bytes() if e1 and e2 else False
d = json.loads((r / "salida_1/aprobadas_B64.json").read_text(encoding="utf-8")) if e1 else {"preguntas": []}
campos_ok = all(sorted(q) == sorted(("id", "pregunta", "criterios", "tipo", "to", "anclas")) for q in d["preguntas"])
caso("T1", "todo bien, dos veces", c1 == 0 and c2 == 0 and iguales and len(d["preguntas"]) == 96 and campos_ok,
     f"códigos {c1} y {c2}; iguales {iguales}; {len(d['preguntas'])} preguntas; solo los seis campos {campos_ok}")
# T2: una aprobada de la ola 1 (L01) pasa a otro tipo
olas, reub, ro, r1, rr1, r2 = copy.deepcopy(D)
q = next(x for x in olas[1] if x["id"] == "B64-O1-L01")
q["tipo"] = "remision" if q["tipo"] != "remision" else "agregacion"
r = TMP / "t2"
esp, s2 = escribir(r, olas, reub, ro, r1, rr1, r2)
c, m, e = correr(r, s2, r / "salida")
caso("T2", "33, 31 y 32: frena por la decisión 4", c != 0 and "no son 32 por tipo" in m and not e, f"código {c}; escribió {e}; {m[:90]}")
# T3: la R2 con una rechazada
r = TMP / "t3"
esp, s2 = escribir(r, *D, marca=("R2", D[5][0]["id"], "no"))
c, m, e = correr(r, s2, r / "salida")
caso("T3", "la R2 con una rechazada: frena", c != 0 and "hace falta una R3" in m and not e, f"código {c}; escribió {e}; {m[:90]}")
# T4 y T5
r = TMP / "t4"
esp, s2 = escribir(r, *D)
c, m, e = correr(r, "0" * 64, r / "salida")
caso("T4", "--sello-r2 equivocado: frena", c != 0 and "revisión de R2 no es el esperado" in m and not e, f"código {c}; {m[:90]}")
c, m, e = correr(r, None, r / "salida_b")
caso("T5", "sin --sello-r2: frena", c != 0 and "falta --sello-r2" in m and not e, f"código {c}; {m[:90]}")
# T6
(r / "salida_c").mkdir()
(r / "salida_c" / "algo.txt").write_text("x\n", encoding="utf-8")
c, m, e = correr(r, s2, r / "salida_c")
caso("T6", "la salida no está vacía: frena", c != 0 and "no está vacía" in m, f"código {c}; {m[:90]}")
# T7: una ola cambiada después de sellar
r = TMP / "t7"
esp, s2 = escribir(r, *D)
f = r / "b64_p2/olas/ola_3.json"
f.write_text(f.read_text(encoding="utf-8") + " ", encoding="utf-8")
c, m, e = correr(r, s2, r / "salida")
caso("T7", "una ola que no da su sha256: frena", c != 0 and "ola_3.json no da su sha256" in m and not e, f"código {c}; {m[:90]}")
# T8: la R1 rechaza otra que la de la lista
olas, reub, ro, r1, rr1, r2 = copy.deepcopy(D)
r = TMP / "t8"
esp, s2 = escribir(r, olas, reub, ro, r1, rr1, r2, marca=("R1", r1[10]["id"], "no"))
c, m, e = correr(r, s2, r / "salida")
caso("T8", "las rechazadas de la R1 no son las de la lista: frena", c != 0 and "rechazadas_B64_R2.json" in m and not e,
     f"código {c}; {m[:90]}")
# T9: un criterio con la cita vacía en una aprobada de la R1
olas, reub, ro, r1, rr1, r2 = copy.deepcopy(D)
r1[10]["criterios"][0]["cita_textual"] = "  "
r = TMP / "t9"
esp, s2 = escribir(r, olas, reub, ro, r1, rr1, r2)
c, m, e = correr(r, s2, r / "salida")
caso("T9", "un criterio con la cita vacía: frena", c != 0 and "un criterio con un campo vacío" in m and not e, f"código {c}; {m[:90]}")
# T10: una fila sin sí ni no
r = TMP / "t10"
esp, s2 = escribir(r, *D, marca=("reubicados", D[1][0]["id"], "quizás"))
c, m, e = correr(r, s2, r / "salida")
caso("T10", "una fila sin sí ni no: frena", c != 0 and "sin «sí» ni «no»" in m and not e, f"código {c}; {m[:90]}")
# T11: un archivo del sello de una revisión cambiado
r = TMP / "t11"
esp, s2 = escribir(r, *D)
f = r / "revision_b64_reubicados" / "hoja_revision_B64_reubicados.csv"
f.write_text("hoja de juguete, cambiada\n", encoding="utf-8")
c, m, e = correr(r, s2, r / "salida")
caso("T11", "un archivo del sello que no da sus bytes: frena", c != 0 and "no da el sha256 o los bytes" in m and not e,
     f"código {c}; {m[:90]}")
print(f"{sum(ok for _, ok in RES)} de {len(RES)}")
raise SystemExit(0 if all(ok for _, ok in RES) else 1)
