"""sellar_planillas_control_36_B63.py — el sello de tus dos planillas de la muestra de control de B6.3 (mesa, unidad C36_a, 29/10/2026).
Es el de la mitad de verificación de Q8 (`sellar_planillas_gold_q12_verificacion.py`) con las planillas de B6.3.

Corre en esta carpeta, sin argumentos. Controla, sin cambiar las planillas:
  - las columnas, los renglones y su orden: los de las planillas que armó la mesa (`estructura_planillas.json`);
  - cada valor obligatorio: el veredicto de cada criterio, cumplido o no_cumplido; «dudosa para mí», «necesita experto del dominio» y
    «criterio mal planteado», sí o no (vacío vale no); de cada respuesta, la clasificación (abstencion o contenido) y «error fuera de los
    criterios», sí o no, con «cuál» si es sí. Mayúsculas y tildes no importan. La nota, el fragmento y los minutos son libres.
  - «error fuera de los criterios» vacío en las 36 (y «cuál» también) vale como la columna que salió, declarada (pre-registro de B6.3,
    §7.3: «Si las horas no dan, es la primera que sale, declarada»); vacío solo en algunas, no se sella.
Si todo pasa, escribe `sello_control_36_B63.txt` con el sha256, los bytes y la hora de cada planilla y la hora del sello. No pisa un sello
que ya existe. Si algo falla, lo lista y no sella. Acepta «,» o «;» y el BOM.
  python3 sellar_planillas_control_36_B63.py
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
PC, PR = AQUI / "planilla_criterios_control_36_B63.csv", AQUI / "planilla_respuestas_control_36_B63.csv"
SELLO = AQUI / "sello_control_36_B63.txt"


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
        print(f"{SELLO.name} ya existe: no se pisa un sello")
        return 1
    est = json.loads((AQUI / "estructura_planillas.json").read_text(encoding="utf-8"))
    errores, salio = [], False
    for p, clave in ((PC, "criterios"), (PR, "respuestas")):
        cols, filas = leer(p)
        if cols != est[clave]["columnas"]:
            errores.append(f"{p.name}: las columnas no son las de la planilla de la mesa")
            continue
        ids = [f[:2] if clave == "criterios" else f[:1] for f in filas]
        if ids != est[clave]["renglones"]:
            errores.append(f"{p.name}: los renglones no son los de la planilla de la mesa, en su orden")
        regs = [dict(zip(cols, f + [""] * (len(cols) - len(f)))) for f in filas]
        if clave == "respuestas":
            salio = bool(regs) and all(not r[cols[2]].strip() and not r[cols[3]].strip() for r in regs)
        for r in regs:
            if clave == "criterios":
                if plegar(r[cols[2]]) not in ("cumplido", "no cumplido"):
                    errores.append(f"{r['ficha']}, criterio {r['criterio']}: el veredicto no es cumplido ni no_cumplido")
                for c in (cols[4], cols[5], cols[6]):
                    if plegar(r[c]) not in ("", "si", "no"):
                        errores.append(f"{r['ficha']}, criterio {r['criterio']}: «{c}» no es sí ni no")
            else:
                if plegar(r[cols[1]]) not in ("abstencion", "contenido"):
                    errores.append(f"{r['ficha']}: la clasificación no es abstencion ni contenido")
                if salio:
                    continue
                e = plegar(r[cols[2]])
                if e not in ("si", "no"):
                    errores.append(f"{r['ficha']}: «error fuera de los criterios» no es sí ni no")
                elif e == "si" and not r[cols[3]].strip():
                    errores.append(f"{r['ficha']}: hay un error fuera de los criterios y falta cuál")
    if errores:
        print(f"NO SE SELLA: {len(errores)} problema(s)")
        for e in errores:
            print(" -", e)
        return 1
    hora = time.strftime("%Y-%m-%d %H:%M:%S %z")
    lin = ["# sello de la lectura de la autora de la muestra de control de B6.3: sha256, bytes, hora de modificación y nombre",
           f"# sellado: {hora}"]
    if salio:
        lin.append("# la columna «error fuera de los criterios» salió, declarada: vacía en las 36")
    for p in (PC, PR):
        b = p.read_bytes()
        lin.append(f"{hashlib.sha256(b).hexdigest()}  {len(b)}  "
                   f"{time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(p.stat().st_mtime))}  {p.name}")
    SELLO.write_text("\n".join(lin) + "\n", encoding="utf-8")
    print(f"SELLADAS las dos planillas -> {SELLO.name}, {hora}" + (" (la columna de error fuera de los criterios salió)" if salio else ""))
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
