#!/usr/bin/env python3
"""guardas_lote.py — Las dos guardas de los pasos pagos del lanzador en paralelo (U-BANCO-PARALELO), sin dependencias
fuera de la biblioteca estándar, para que las use el lanzador del lote y el comando pago del humo.

  pago        otro paso pago corriendo (registro de decisiones, §55; la guarda de T, §118): `pgrep -f` con el patrón del
              renglón 16 de a2_2/guardas_a2_2.zsh más `correr_prueba_T_v2\\.py`, tal cual. De lo que da pgrep quedan solo
              los procesos de Python que corren un script con ese nombre: un shell, un `grep` o un editor que nombren el
              script no cuentan, ni el árbol propio (los ancestros, porque el comando que lanza la guarda puede nombrar el
              patrón, y los descendientes del proceso que se pase, que son las sesiones del lote).
  extraccion  una extracción corriendo (§55, «lo pago va en secuencia, nunca al lado de una extracción»): sobre
              `ps -axo pid=,ppid=,args=`, el patrón PATRON_EXTRACCION (el de la §198, que ve rutas con espacios), sin los
              ancestros propios.

Las dos imprimen solo el pid y el nombre del script de lo que encuentran, nunca la línea entera ni el entorno (la
lectura es `ps ... args=`, que no trae el entorno). Ninguna espera.

Uso: guardas_lote.py pago | extraccion      (código 7 o 9 si encuentra algo; 0 si no)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

# a2_2/guardas_a2_2.zsh:16 (HEAD 2addcf32), más correr_prueba_T_v2\.py (la guarda de T, registro de decisiones, §118).
PATRON_PAGO = (r"correr_juez_v2\.py|run_posthoc\.py|runner_corpus\.py|lanzar_t|correr_tanda|ensamblar_tanda0\.py|"
               r"correr_a2_1\.py|correr_smoke\.py|correr_a2_2\.py|juez_a2_2\.py" r"|correr_prueba_T_v2\.py")
# El runner de la extracción o un lanzador de tanda, tal cual el de la §198 (despacho de U-BANCO-PARALELO, punto 5 del
# «seguí»): el de antes (punto 4.e) no veía un script con un espacio en su ruta, como la del repo («carpeta con espacios»).
# RUTA_CON_ESPACIOS toma una ruta absoluta que cruza espacios seguidos de algo que no es una opción, sin pasar por otro
# `.py` que termine un argumento.
RUTA_CON_ESPACIOS = r"/(?:(?!\.py(?:\s|$))\S|\s(?=[^\s-]))*?/"
PATRON_EXTRACCION = (r"(^|/)python[0-9.]*\s+(-\S+\s+)*(?:" + RUTA_CON_ESPACIOS
                     + r"|\S*?)(runner_corpus|lanzar_t[0-9a-z_]*|correr_tanda[0-9a-z_]*)\.py(\s|$)")
# Un intérprete de Python al principio de la línea (su ruta puede tener espacios), sus opciones y el script, hasta su
# `.py`: lo que separa un paso pago de un shell, un `grep` o un editor que lo nombran.
_PYTHON_Y_SCRIPT = re.compile(r"^(?:\S.*?/)?python[0-9.]*(?:\s+-\S+)*\s+(.+?\.py)(?=\s|$)", re.IGNORECASE)
CODIGO_PAGO = 7
CODIGO_EXTRACCION = 9


def tabla_procesos() -> dict[int, tuple[int, str]]:
    """pid -> (ppid, args), de `ps -axo pid=,ppid=,args=` (sin el entorno)."""
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,args="], capture_output=True, text=True, check=True).stdout
    t = {}
    for linea in out.splitlines():
        p = linea.split(None, 2)
        if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
            t[int(p[0])] = (int(p[1]), p[2] if len(p) > 2 else "")
    return t


def ancestros(pid: int, tabla: dict) -> set[int]:
    vistos = set()
    while pid in tabla and pid not in vistos and pid > 1:
        vistos.add(pid)
        pid = tabla[pid][0]
    return vistos


def descendientes(pid: int, tabla: dict) -> set[int]:
    hijos: dict[int, list[int]] = {}
    for q, (pp, _) in tabla.items():
        hijos.setdefault(pp, []).append(q)
    out, pila = set(), [pid]
    while pila:
        for h in hijos.get(pila.pop(), []):
            if h not in out:
                out.add(h)
                pila.append(h)
    return out


def script_python(args: str) -> str | None:
    """El script que corre un proceso de Python (su ruta tal como está en la línea), o None si no es Python con un script."""
    m = _PYTHON_Y_SCRIPT.match(args)
    return m.group(1) if m else None


def _nombre(ruta: str) -> str:
    return ruta.rstrip("/").rsplit("/", 1)[-1]


def otro_paso_pago(raiz_lote: int | None = None) -> list[dict]:
    """Los pasos pagos que corren, salvo el árbol propio: [{pid, script}]."""
    r = subprocess.run(["pgrep", "-f", PATRON_PAGO], capture_output=True, text=True)
    pids = {int(x) for x in r.stdout.split() if x.isdigit()}
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
        if guion and re.search(PATRON_PAGO, _nombre(guion)):
            hallados.append({"pid": pid, "script": _nombre(guion)})
    return hallados


def extraccion_corriendo() -> list[dict]:
    """Las extracciones que corren, salvo los ancestros propios: [{pid, script}]."""
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
    if argv[1:] == ["pago"]:
        h = otro_paso_pago()
        for x in h:
            print(f"FRENO: otro paso pago corriendo: pid {x['pid']} ({x['script']})")
        if not h:
            print("guarda de otro paso pago: ninguno")
        return CODIGO_PAGO if h else 0
    if argv[1:] == ["extraccion"]:
        h = extraccion_corriendo()
        for x in h:
            print(f"FRENO: extracción corriendo: pid {x['pid']} ({x['script']})")
        if not h:
            print("control de la extracción: ninguna")
        return CODIGO_EXTRACCION if h else 0
    sys.stderr.write("uso: guardas_lote.py pago | extraccion\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
