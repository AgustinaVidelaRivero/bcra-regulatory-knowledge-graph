#!/usr/bin/env python3
"""guardas_lote_r5.py — Las guardas del lanzador del lote con correr_b63.py en el patrón de otro paso pago (U-BANCO-R5-a; decisión
de la autora del 26/10/2026: «correr_b63.py entra en el patrón de otro paso pago de todo comando que pueda
correr mientras corre B6.3, y en el de pgrep para esperar»).

Importa paralelo/guardas_lote.py de HEAD sin editarlo (BASE) y cambia solo el patrón del paso pago:
  pago        PATRON_PAGO = BASE.PATRON_PAGO + `|correr_b63\\.py`, con el mismo filtro por nombre de guion que BASE
              (BASE.script_python: de lo que da pgrep quedan solo los procesos de Python que corren un script con un nombre del
              patrón; un shell, un `grep`, un editor o el `pgrep` de otra guarda que nombran el patrón no cuentan) y sin el árbol
              propio: los ancestros del proceso que corre la guarda (así el lote que lanza correr_b63.py no se ve a sí mismo) y los
              descendientes del lote que se pase;
  pgrep       la espera de un comando que aguarda a que termine un paso pago: los pids de `pgrep -f`, con el mismo patrón (el
              lanzador del lote no la usa);
  extraccion  la de BASE, con el PATRON_EXTRACCION de este módulo (el de BASE, el de la §198).
El patrón se puede pasar por parámetro (`patron`, o --patron en la línea de comandos) o cambiar en el módulo (PATRON_PAGO, como el
patrón de prueba de un runner): así las pruebas usan nombres propios y ningún `pgrep` de una prueba lleva en su línea de comandos
el patrón real. PATRON_PAGO_REAL guarda el real aunque una prueba cambie PATRON_PAGO.

Imprime solo el pid y el nombre del script de lo que encuentra, nunca la línea entera ni el entorno. Ninguna espera programada.
Uso: guardas_lote_r5.py pago [--patron P] | extraccion      (código 7 o 9 si encuentra algo; 0 si no)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import guardas_lote as BASE                      # noqa: E402  (HEAD: solo import)

SUFIJO_B63 = r"|correr_b63\.py"
PATRON_PAGO = BASE.PATRON_PAGO + SUFIJO_B63
PATRON_PAGO_REAL = PATRON_PAGO                   # el de arriba, aunque una prueba cambie PATRON_PAGO
PATRON_EXTRACCION = BASE.PATRON_EXTRACCION
CODIGO_PAGO = BASE.CODIGO_PAGO
CODIGO_EXTRACCION = BASE.CODIGO_EXTRACCION
tabla_procesos = BASE.tabla_procesos
ancestros = BASE.ancestros
descendientes = BASE.descendientes
script_python = BASE.script_python


def pgrep(patron: str | None = None) -> set[int]:
    """Los pids de `pgrep -f` con el patrón (por defecto, PATRON_PAGO), sin filtrar: lo que usa un comando para esperar."""
    r = subprocess.run(["pgrep", "-f", patron or PATRON_PAGO], capture_output=True, text=True)
    return {int(x) for x in r.stdout.split() if x.isdigit()}


def otro_paso_pago(raiz_lote: int | None = None, patron: str | None = None) -> list[dict]:
    """Los pasos pagos que corren, salvo el árbol propio: [{pid, script}]. Como BASE.otro_paso_pago, con el patrón de este
    módulo (o el que se pase) en lugar del de BASE."""
    patron = patron or PATRON_PAGO
    pids = pgrep(patron)
    tabla = tabla_procesos()
    yo = os.getpid()
    propios = ancestros(yo, tabla) | {yo} | descendientes(yo, tabla)
    if raiz_lote is not None:
        propios |= {raiz_lote} | descendientes(raiz_lote, tabla)
    hallados = []
    for pid in sorted(pids - propios):
        if pid not in tabla:
            continue                       # terminó entre pgrep y ps
        guion = script_python(tabla[pid][1])
        if guion and re.search(patron, BASE._nombre(guion)):
            hallados.append({"pid": pid, "script": BASE._nombre(guion)})
    return hallados


def extraccion_corriendo() -> list[dict]:
    """La de BASE con el PATRON_EXTRACCION de este módulo (el de BASE, salvo que una prueba lo cambie aquí, como lo hace el
    fijar_patron_de_prueba de b63/correr_b63.py sobre el módulo de guardas que importa)."""
    tabla = tabla_procesos()
    yo = os.getpid()
    propios = ancestros(yo, tabla) | {yo}
    pat = re.compile(PATRON_EXTRACCION)
    hallados = []
    for pid, (_, args) in sorted(tabla.items()):
        if pid in propios:
            continue
        m = pat.search(args)
        if m:
            hallados.append({"pid": pid, "script": m.group(3) + ".py"})
    return hallados


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args[:1] == ["pago"] and (len(args) == 1 or (len(args) == 3 and args[1] == "--patron")):
        h = otro_paso_pago(patron=args[2] if len(args) == 3 else None)
        for x in h:
            print(f"FRENO: otro paso pago corriendo: pid {x['pid']} ({x['script']})")
        if not h:
            print("guarda de otro paso pago: ninguno")
        return CODIGO_PAGO if h else 0
    if args == ["extraccion"]:
        h = extraccion_corriendo()
        for x in h:
            print(f"FRENO: extracción corriendo: pid {x['pid']} ({x['script']})")
        if not h:
            print("control de la extracción: ninguna")
        return CODIGO_EXTRACCION if h else 0
    sys.stderr.write("uso: guardas_lote_r5.py pago [--patron P] | extraccion\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
