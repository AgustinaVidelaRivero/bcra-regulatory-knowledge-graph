"""La tabla de reprocesamiento corregida por S0-6b (U-SEG-OFICIAL; decisión 4 de la autora: «F19b: lo corrige S0-6b junto
con la F19d, con el control de las 27 anclas»; USD 0, sin API).

Uso: python -B corregir_tabla_S0-6b.py --tabla <tabla de HEAD> --out <tabla corregida>

Sobre la tabla de HEAD (antes del parche de S0-6a-bis):
1. las 14 citas al código de E0 que el parche mueve pasan al rango que da
   `s0_6/bis/controles/anclas_e0_tabla_S0-6a-bis.txt` (el mismo bloque, entero, en otro rango);
2. la cita de F19b a las reglas de S0-5, `correr_e0.py:140-210`, pasa a dos: `:140-205` (las constantes de S0-5) y
   `:246-252` (`_r5`, que el parche cambia);
3. la fila F19d (las reglas generales de S0-6a y S0-6a-bis) entra después de F19b, con las anclas del despacho de S0-6b;
4. una nota fechada al final del archivo (§6), como las del 08/10/2026 y del 10/10/2026, que no se editan.
Cada texto viejo tiene que aparecer exactamente una vez en su renglón; si no, el script frena sin escribir. Imprime el
renglón anterior a la nota nueva (el `--hasta-nueva` del control de anclas por contenido).
"""
import argparse
import sys
from pathlib import Path

# (comienzo del renglón, texto viejo, texto nuevo)
CAMBIOS = [
    ("| F16b |", "`correr_e0.py:1688-1689`; `e0_lib.py:1391-1421`", "`correr_e0.py:1767-1768`; `e0_lib.py:1602-1632`"),
    ("| F18a |", "`e0_chunking/e0_lib.py:925-979`, `:1718-1719`", "`e0_chunking/e0_lib.py:1131-1185`, `:2068-2069`"),
    ("| F18b |", "`e0_lib.py:1718-1719`", "`e0_lib.py:2068-2069`"),
    ("| F19b |", "`:432-444` (regla 6)", "`:474-486` (regla 6)"),
    ("| F19b |", "`:681-690` (regla 9)", "`:723-732` (regla 9)"),
    ("| F19b |", "`:1393` (T)", "`:1452` (T)"),
    ("| F19b |", "`e0_lib.py:377` (regla 8)", "`e0_lib.py:394` (regla 8)"),
    ("| F19b |", "`:642` (regla 3, ampliación)", "`:782` (regla 3, ampliación)"),
    ("| F19b |",
     "`:140-210` (reglas de S0-5, de `REGLAS_S0_5` a `_r5`, con `LISTAS_R5A_S0_5`, `ROTULOS_POR_LISTA_S0_5` y "
     "`RAICES_POR_LISTA_S0_5`)",
     "`:140-205` (reglas de S0-5: sus constantes, de `REGLAS_S0_5` a `RAICES_POR_LISTA_S0_5`, con `LISTAS_R5A_S0_5` y "
     "`ROTULOS_POR_LISTA_S0_5`), `:246-252` (`_r5`)"),
    ("| F20 |", "`correr_e0.py:368-429`, `:448-486`", "`correr_e0.py:410-471`, `:490-528`"),
    ("| F21 |", "`e0_lib.py:3193-3268`", "`e0_lib.py:4170-4245`"),
    ("- **F18a.**", "(`e0_lib.py:1718-1719`)", "(`e0_lib.py:2068-2069`)"),
]

F19D = ("| F19d | Release de E0 (e0-r2) con reglas generales antes de una tanda, con la tanda 0 fuera por lista: reglas que "
        "crean, quitan o cambian unidades de las tandas siguientes sin cambiar la tanda 0 | E0 e0-r2 de las tandas "
        "siguientes; la de la tanda 0, byte a byte igual | en la tanda 0, nada; en las siguientes, las unidades nuevas y "
        "las que cambian texto o herencia entran a E1 y E3 por F19b y F01 a F03, cuando esa tanda se extraiga | cambia "
        "(en las tandas siguientes: las unidades nuevas y las que cambian texto o herencia; en la tanda 0, no cambia) | "
        "cambia (en las tandas siguientes, las mismas; en la tanda 0, no cambia) | ninguna en la tanda 0 | 9 (como F19b) | "
        "`correr_e0.py:207-252` (las constantes de S0-6, `_r6`, `_sd_s04` y `_r5`), `:851-860` (`_filas_tabla_a`), "
        "`:1444-1448` (B, D y M en `procesar_tablas_r2`), `:1492` (A en `escalera_e0_r2`), `:1518-1525` (A, E, F1, G, H, "
        "I, J, K y L en `escalera_e0_r2`), `:1697-1718` (R5-a, A, C y F2 en `correr`); `e0_lib.py:228-243` (el docstring "
        "del módulo), `:550-655` (las constantes de A, B, C, F, G, H, I, J y K), `:766-779` (L y M), `:794-851` "
        "(`lineas_de_indice_l`), `:1716-1829` (G, I, J y F), `:2067-2073` (la carátula de A en `parsear_cuerpo`), "
        "`:2273-2274` (L en `parsear_cuerpo`), `:3163-3364` (C), `:3367-3658` (A), `:3661-3707` (F2), `:4085-4095` "
        "(`_marca_hijo` y `_es_raiz_subdoc`), `:4324-4367` (B), `:4572-4589` (M en `construir_chunks`) | R24 (las "
        "unidades nuevas y las que cambian de las tandas siguientes; sin variación propia: en la tanda 0 no ocurre) |")

NOTA = """- **Anclas al código de E0 corridas por el parche de S0-6a-bis, corregidas el 13/10/2026 (S0-6b, por decisión de la autora).** El
  parche que aplicó S0-6b (`a0f291c4…`; `e0_lib.py` `d89aab1a…`, `correr_e0.py` `78c54c4c…`) corrió 14 de las 27 citas al código de E0:
  F16b `correr_e0.py:1688-1689 → :1767-1768` y `e0_lib.py:1391-1421 → :1602-1632`; F18a `e0_lib.py:925-979 → :1131-1185` y
  `:1718-1719 → :2068-2069`, igual en F18b y en la nota de F18a; F19b `correr_e0.py:432-444 → :474-486`, `:681-690 → :723-732` y
  `:1393 → :1452`, y `e0_lib.py:377 → :394` y `:642 → :782`; F20 `correr_e0.py:368-429 → :410-471` y `:448-486 → :490-528`; F21
  `e0_lib.py:3193-3268 → :4170-4245`. La cita de F19b a las reglas de S0-5, de `REGLAS_S0_5` a `_r5`, no se encuentra entera en el
  código aplicado, porque el parche cambia `_r5` (su docstring y tres renglones de los reemplazos de S0-6a): pasa a dos, `:140-205`,
  las constantes de S0-5, de `REGLAS_S0_5` a `RAICES_POR_LISTA_S0_5`, iguales byte a byte a las de S0-5b, y `:246-252`, `_r5`, en su
  lugar nuevo. Las otras 12 citas no cambian. Entra la fila F19d (las reglas generales de S0-6a y
  S0-6a-bis, A a M), con anclas al código aplicado. Verificadas por contenido contra el código de E0 de S0-5b y el aplicado, con el
  parche (`segmentacion_oficial_e0r2/s0_6/b/scripts/control_anclas_contenido_S0-6b_mesa.py`; la salida, en
  `segmentacion_oficial_e0r2/s0_6/b/controles/control_anclas_contenido_S0-6b.txt`)."""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tabla", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    lineas = a.tabla.read_text(encoding="utf-8").split("\n")
    for comienzo, viejo, nuevo in CAMBIOS:
        cand = [i for i, l in enumerate(lineas) if l.startswith(comienzo)]
        if len(cand) != 1 or lineas[cand[0]].count(viejo) != 1:
            sys.exit(f"FRENO: {comienzo} {viejo[:40]}: renglones {len(cand)}, apariciones "
                     f"{lineas[cand[0]].count(viejo) if cand else 0}")
        lineas[cand[0]] = lineas[cand[0]].replace(viejo, nuevo)
    f19b = [i for i, l in enumerate(lineas) if l.startswith("| F19b |")]
    if len(f19b) != 1 or any(l.startswith("| F19d |") for l in lineas):
        sys.exit("FRENO: F19b no es única o F19d ya existe")
    lineas.insert(f19b[0] + 1, F19D)
    while lineas and lineas[-1] == "":
        lineas.pop()
    hasta = len(lineas)
    a.out.write_text("\n".join(lineas) + "\n" + NOTA + "\n", encoding="utf-8")
    print(f"cambios {len(CAMBIOS)}; F19d en el renglón {f19b[0] + 2}; renglón anterior a la nota nueva: {hasta}")


if __name__ == "__main__":
    main()
