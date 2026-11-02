"""S0-4a-bis (U-SEG-OFICIAL), USD 0, solo lectura: anclas de la fila F19b de la tabla de reprocesamiento sobre otro
código. Mapea cada renglón ancla del código de E0 de `26c6502` al renglón con el mismo contenido en el código nuevo
(difflib sobre los renglones; un ancla dentro de un bloque reemplazado se marca), y muestra el renglón en los dos.
Uso: python -B anclas_f19b.py <dir código 26c6502> <dir código nuevo> [<dir código nuevo> …]"""
import difflib
import sys
from pathlib import Path

ANCLAS = {"correr_e0.py": [(95, 100), (327, 339), (576, 585), (1266, 1266)],
          "e0_lib.py": [(352, 352), (473, 473)]}
viejo, nuevos = Path(sys.argv[1]), [Path(x) for x in sys.argv[2:]]
for f, rangos in ANCLAS.items():
    a = (viejo / f).read_text(encoding="utf-8").splitlines()
    for nd in nuevos:
        b = (nd / f).read_text(encoding="utf-8").splitlines()
        mapa = {}
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    mapa[i1 + k + 1] = j1 + k + 1
        for x, y in rangos:
            nx, ny = mapa.get(x), mapa.get(y)
            cont = all(mapa.get(k) == nx + (k - x) for k in range(x, y + 1)) if nx else False
            print(f"{nd.name} {f}:{x}-{y} -> {nx}-{ny} {'contiguo' if cont else 'NO CONTIGUO'} | {a[x-1].strip()[:70]}")
