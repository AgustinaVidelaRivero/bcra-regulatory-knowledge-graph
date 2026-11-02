"""Anclas de la tabla de reprocesamiento al código de E0, antes y después del parche de S0-5a-bis (S0-5b; solo
lectura, sobre copias). Para cada cita `archivo.py:N` o `:N-M` de `e0_lib.py` o `correr_e0.py` en las filas de la
tabla y en sus notas vigentes, toma esos renglones del código de S0-4b y los busca en el código aplicado: la cita
queda igual, se mueve (el mismo bloque, entero, en otro rango) o no se encuentra entera.
Una cita sin archivo (`:N-M`) es del último archivo nombrado en la misma fila.
Uso: python -B anclas_e0_tabla_S0-5b.py <tabla.md> <dir S0-4b> <dir aplicado> [--desde N] [--hasta M]"""
import argparse
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("tabla", type=Path)
ap.add_argument("antes", type=Path)
ap.add_argument("despues", type=Path)
ap.add_argument("--hasta", type=int, default=None, help="último renglón de la tabla que se lee (excluye notas históricas)")
a = ap.parse_args()
ARCH = ("e0_lib.py", "correr_e0.py")
cod = {(k, f): (getattr(a, k) / f).read_text(encoding="utf-8").splitlines() for k in ("antes", "despues") for f in ARCH}
RX = re.compile(r"`([^`]*?)(?:([A-Za-z0-9_./]+\.py))?:(\d+)(?:-(\d+))?`")

filas = []
for n, l in enumerate(a.tabla.read_text(encoding="utf-8").splitlines(), 1):
    if a.hasta and n > a.hasta:
        break
    actual = None
    for m in RX.finditer(l):
        f = m.group(2)
        if f:
            actual = f.rsplit("/", 1)[-1]
        if actual not in ARCH:
            continue
        ini = int(m.group(3)); fin = int(m.group(4) or m.group(3))
        etiqueta = (l.split("|")[1].strip() if l.startswith("|") else l.strip()[:12])
        filas.append((n, etiqueta, actual, ini, fin, m.group(0)))

print(f"{len(filas)} citas a e0_lib.py o correr_e0.py en {a.tabla.name}" + (f" (renglones 1 a {a.hasta})" if a.hasta else ""))
print("renglón | fila | cita | estado | rango en el código aplicado | primer renglón citado (S0-4b)")
cuenta = {}
for n, et, f, ini, fin, txt in filas:
    viejo = cod[("antes", f)][ini - 1:fin]
    nuevo = cod[("despues", f)]
    k = len(viejo)
    pos = [i for i in range(len(nuevo) - k + 1) if nuevo[i:i + k] == viejo]
    vpos = [i for i in range(len(cod[("antes", f)]) - k + 1) if cod[("antes", f)][i:i + k] == viejo]
    if not pos:
        estado, rango = "NO SE ENCUENTRA ENTERA", "—"
    elif len(pos) != len(vpos):
        estado, rango = f"AMBIGUA ({len(vpos)} apariciones antes, {len(pos)} después)", "—"
    elif pos[vpos.index(ini - 1)] == ini - 1:
        estado, rango = "igual", f"{ini}-{fin}" if fin != ini else f"{ini}"
    else:
        p = pos[vpos.index(ini - 1)] + 1
        estado = "se mueve" + (f" (aparición {vpos.index(ini - 1) + 1} de {len(pos)}, antes y después)"
                               if len(pos) > 1 else "")
        rango = f"{p}-{p + k - 1}" if k > 1 else f"{p}"
    cuenta[estado.split(" (")[0]] = cuenta.get(estado.split(" (")[0], 0) + 1
    print(f"{n} | {et} | {f}:{ini}" + (f"-{fin}" if fin != ini else "") + f" | {estado} | {rango} | «{viejo[0].strip()[:90]}»")
print("por estado:", cuenta)
