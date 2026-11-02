"""armar_aprobadas_B64_mesa.py — mesa, §373 (31/10/2026): el archivo de las 96 preguntas aprobadas de B6.4, el que recibe
`b64/v1/armar_entrada_B64.py` (H-3), desde tus cuatro revisiones selladas: las olas (§205), los reubicados (§207), la R1 (§209) y la R2.
Antes de escribir, controla, y frena si algo no da:
  · cada sello de revisión, por su sha256 (el de la R2 llega por argumento), y cada archivo que nombra, por su sha256 y sus bytes;
  · cada salida generada (las seis olas, los reubicados, la R1 y la R2) y las dos listas de rechazadas, por su sha256;
  · que cada marcada tenga justo los ids de su salida, con `aprueba` en sí o no; y que las rechazadas de las olas y de la R1 sean las de
    sus listas selladas (`rechazadas_B64_R1.json` y `rechazadas_B64_R2.json`);
  · que las aprobadas sean 96, una por lugar (B64-O<1..6>-L<01..16>), con ids que no se repiten;
  · decisión 4 de la autora (31/10/2026): que sean 32 por tipo (agregación, remisión y condición o excepción). Si no dan, frena antes
    de sellar: el armador de la entrada no lo controla;
  · que cada una traiga `pregunta`, sus criterios con `criterio`, `cita_textual` y `unidad`, `tipo`, `to` y `anclas`, sin vacíos.
Escribe, en la carpeta de salida, que tiene que estar vacía, `aprobadas_B64.json` (una lista `preguntas` en su raíz, en el orden de los
lugares, cada una solo con esos seis campos) y `sello_aprobadas_B64.txt` (su sha256, sus bytes y la hora). De las marcadas lee solo `id` y
`aprueba`, nunca `motivo_si_no`. Imprime solo ids, cuentas y sha256: nunca el texto de una pregunta, un criterio o una cita. USD 0.
  python3 -I -B armar_aprobadas_B64_mesa.py <fuera_del_repo> <carpeta de salida> --sello-r2 <sha256 del sello de la revisión de la R2>
    [--prueba <JSON con los sha256 esperados>]   (con --prueba, los esperados salen del JSON: es para el selftest, con datos de juguete)
    [--carpeta-r2 <carpeta>]   (la revisión de la R2 en otra carpeta: es para probarlo sobre los datos reales con una R2 simulada,
                                antes de que exista tu revisión; el sábado no se usa)
"""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ARGS = sys.argv[1:]
FUERA, SAL = Path(ARGS[0]), Path(ARGS[1])
SELLO_R2 = ARGS[ARGS.index("--sello-r2") + 1] if "--sello-r2" in ARGS else None
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
ESPERADOS = {
    # los sellos de tus revisiones (registro de la mesa, §205, §207 y §209); el de la R2, por argumento
    "sello_olas": "95d20ce42631152aebc26ce7668943a10ff8088c48ada9e4fd3523234d5bd942",
    "sello_reubicados": "4e7fdb52411766cc29125cbbd4d767e958baf07fb7e35bdc505aa3ee0af06039",
    "sello_R1": "1aa8fb79eac89f1cafdfaf3139860235b1a35ca4799763332ffa573d60b3eb43",
    # las salidas generadas, selladas (sello_ola_<n>.txt, sello_reubicados.txt, sello_reemplazos_R1.txt y sello_reemplazos_R2.txt)
    "olas/ola_1.json": "3fbfebf1394ea4086334d79a07809ec7b2bb2206698dbb008f0855c5ea1c05ee",
    "olas/ola_2.json": "7b2d62fbeb799e9c38649255ab771d7cc196c1d0a5a9b2574cf1c643dc50952c",
    "olas/ola_3.json": "b130c2dc1bd0c918cbc6039f642cfcf4bfca389da54ed856a1e69c68daf524c2",
    "olas/ola_4.json": "d07824d1c25c87c9c207291b781ed7c54f70fbccdfa2912efee665ac035ee415",
    "olas/ola_5.json": "ce6243e2c482fe3531842d4b1ef0cd6363bb9ab76d278de912e7a6b34c5d75ba",
    "olas/ola_6.json": "f0fb478e08dc4c1ff0ad6674b4256d2cf53c81b1ed79117cb4c2428556b7c685",
    "olas/reubicados_O6_L15_L16.json": "85d0b727b5057a1edf6cd3932a9b384569d1badf1374459bf854e0bb7c8124d7",
    "olas/reemplazos_R1_B64.json": "952ab8fb4c737face52000b0ef12eee91d04b19778a278ef821336ffbfca557e",
    "olas/reemplazos_R2_B64.json": "5b1c1dd9ce5f60247fd4a6f305e50134bed2abbd681ee870fe1d422bb36a7b6b",
    "insumos/rechazadas_B64_R1.json": "cef551bbf0ab313128a5f69e657ba3e18aeb309768ec457c37a72b2589296d33",
    "insumos/rechazadas_B64_R2.json": "d2801f974026aca4ca7ef4dca9779172092250665e52d17f66440777a1643fa8",
}
if "--prueba" in ARGS:
    ESPERADOS = json.loads(Path(ARGS[ARGS.index("--prueba") + 1]).read_text(encoding="utf-8"))
ESPERADOS["sello_R2"] = SELLO_R2
TIPOS = ("agregacion", "remision", "condicion_excepcion")
CAMPOS = ("id", "pregunta", "criterios", "tipo", "to", "anclas")
REVISIONES = (  # (nombre, carpeta, sello, marcada, salidas generadas que revisó)
    ("olas", "revision_b64_olas_1_a_6", "sello_hoja_revision_B64.txt", "hoja_revision_B64_olas_1_a_6_marcada.csv",
     [f"olas/ola_{i}.json" for i in range(1, 7)]),
    ("reubicados", "revision_b64_reubicados", "sello_hoja_revision_B64_reubicados.txt", "hoja_revision_B64_reubicados_marcada.csv",
     ["olas/reubicados_O6_L15_L16.json"]),
    ("R1", "revision_b64_reemplazos_R1", "sello_hoja_revision_B64_reemplazos_R1.txt", "hoja_revision_B64_reemplazos_R1_marcada.csv",
     ["olas/reemplazos_R1_B64.json"]),
    ("R2", "revision_b64_reemplazos_R2", "sello_hoja_revision_B64_reemplazos_R2.txt", "hoja_revision_B64_reemplazos_R2_marcada.csv",
     ["olas/reemplazos_R2_B64.json"]),
)


def frena(m):
    raise SystemExit(f"FRENO: {m}")


def vacio(x):
    return x is None or (isinstance(x, (str, list, dict)) and len(x) == 0) or (isinstance(x, str) and not x.strip())


if not SELLO_R2 or not re.fullmatch(r"[0-9a-f]{64}", SELLO_R2):
    frena("falta --sello-r2 con el sha256 del sello de tu revisión de la R2")
if SAL.exists() and any(SAL.iterdir()):
    frena("la carpeta de salida no está vacía")
B = FUERA / "b64_p2"


def leer_controlado(rel):
    b = (B / rel).read_bytes()
    if sha(b) != ESPERADOS[rel]:
        frena(f"{rel} no da su sha256")
    return json.loads(b)


cuentas, aprobadas = {}, []
for nombre, carpeta, sello, marcada, salidas in REVISIONES:
    rev = Path(ARGS[ARGS.index("--carpeta-r2") + 1]) if nombre == "R2" and "--carpeta-r2" in ARGS else FUERA / carpeta
    s = rev / sello
    if not s.is_file() or sha(s.read_bytes()) != ESPERADOS[f"sello_{nombre}"]:
        frena(f"el sello de tu revisión de {nombre} no es el esperado")
    for l in s.read_text(encoding="utf-8").splitlines():
        if l and not l.startswith("#"):
            h, by, _, archivo = l.split("  ", 3)
            b = (rev / Path(archivo.strip()).name).read_bytes()
            if sha(b) != h or str(len(b)) != by:
                frena(f"{nombre}: {Path(archivo.strip()).name} no da el sha256 o los bytes de su sello")
    preg = {q["id"]: q for rel in salidas for q in leer_controlado(rel)["preguntas"]}
    filas = [{"id": r["id"], "aprueba": r["aprueba"]} for r in csv.DictReader(open(rev / marcada, encoding="utf-8"))]
    if sorted(r["id"] for r in filas) != sorted(preg) or len(filas) != len(preg):
        frena(f"la marcada de {nombre} no tiene justo los ids de su salida")
    if any(r["aprueba"] not in ("sí", "no") for r in filas):
        frena(f"la marcada de {nombre} tiene filas sin «sí» ni «no» en aprueba")
    si = [r["id"] for r in filas if r["aprueba"] == "sí"]
    cuentas[nombre] = {"filas": len(filas), "aprobadas": len(si), "rechazadas": len(filas) - len(si)}
    rech = {r["id"] for r in filas if r["aprueba"] == "no"}
    if nombre == "olas" and rech != {r["id"] for r in leer_controlado("insumos/rechazadas_B64_R1.json")["rechazadas"]}:
        frena("las rechazadas de las olas no son las de rechazadas_B64_R1.json")
    if nombre == "R1" and rech != {r["id"] for r in leer_controlado("insumos/rechazadas_B64_R2.json")["rechazadas"]}:
        frena("las rechazadas de la R1 no son las de rechazadas_B64_R2.json")
    if nombre == "R2" and rech:
        frena(f"la R2 tiene {len(rech)} rechazadas: hace falta una R3 antes de armar las 96")
    aprobadas += [preg[i] for i in si]


def lugar(qid):
    m = re.match(r"^B64-O(\d)-L(\d\d)(?:-R\d)?$", qid)
    return (int(m.group(1)), int(m.group(2))) if m else None


ids = [q["id"] for q in aprobadas]
lugares = [lugar(i) for i in ids]
if len(aprobadas) != 96:
    frena(f"son {len(aprobadas)} aprobadas, no 96")
if len(set(ids)) != 96:
    frena("un id se repite")
if None in lugares or sorted(lugares) != [(o, l) for o in range(1, 7) for l in range(1, 17)]:
    frena("las aprobadas no son una por lugar, de B64-O1-L01 a B64-O6-L16")
tipos = Counter(q.get("tipo") for q in aprobadas)
if dict(tipos) != {t: 32 for t in TIPOS}:
    frena(f"no son 32 por tipo: {dict(sorted(tipos.items()))} (decisión 4)")
salida = []
for q in sorted(aprobadas, key=lambda x: lugar(x["id"])):
    for c in CAMPOS:
        if c not in q or vacio(q[c]):
            frena(f"a {q['id']} le falta `{c}` o lo trae vacío")
    crit = [{k: c[k] for k in ("criterio", "cita_textual", "unidad")} for c in q["criterios"]]
    if any(vacio(v) for c in crit for v in c.values()):
        frena(f"{q['id']}: un criterio con un campo vacío")
    anc = [{"rol": a["rol"], "unidad": a["unidad"]} for a in q["anclas"]]
    if sum(a["rol"] == "ancla" for a in anc) != 1:
        frena(f"{q['id']}: no tiene una sola ancla con rol «ancla»")
    salida.append({"id": q["id"], "pregunta": q["pregunta"], "criterios": crit, "tipo": q["tipo"], "to": q["to"], "anclas": anc})
out = {"de": "las 96 preguntas aprobadas de B6.4, desde las cuatro revisiones selladas de la autora (armar_aprobadas_B64_mesa.py, §373)",
       "sellos": {k: v for k, v in sorted(ESPERADOS.items())}, "cuentas": cuentas, "preguntas": salida}
SAL.mkdir(parents=True, exist_ok=True)
f = SAL / "aprobadas_B64.json"
f.write_bytes((json.dumps(out, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
ahora = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
(SAL / "sello_aprobadas_B64.txt").write_text(
    "# sello de la mesa (§373): sha256, bytes, hora y nombre del archivo de las 96 aprobadas de B6.4\n"
    f"{sha(f.read_bytes())}  {f.stat().st_size}  {ahora}  aprobadas_B64.json\n", encoding="utf-8")
print("revisiones:", json.dumps(cuentas, ensure_ascii=False))
ronda = Counter((re.search(r"-(R\d)$", i) or [None, "olas_y_reubicados"])[1] for i in ids)
print("aprobadas:", len(salida), "| por tipo:", json.dumps(dict(sorted(tipos.items())), ensure_ascii=False),
      "| por ronda:", json.dumps(dict(ronda), ensure_ascii=False))
print("aprobadas_B64.json:", sha(f.read_bytes()), "|", f.stat().st_size, "bytes")
