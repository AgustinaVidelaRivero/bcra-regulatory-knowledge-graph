"""U-SEG-OFICIAL, S0-6b: control por contenido de las anclas de la tabla de reprocesamiento al código de E0 (mesa, 13/10/2026; USD 0,
sin API; solo lectura). Lo pide la decisión de la autora del 13/10/2026 (hoja de la mesa, §83): el script de anclas de S0-5b, con el
código aplicado como «antes» y como «después», compara el código consigo mismo y no detecta un ancla que apunta a otras líneas.

Toma las citas `archivo.py:N` o `:N-M` a `e0_lib.py` y `correr_e0.py` de la tabla vieja (la de HEAD antes de S0-6b) y de la nueva
(la corregida, hasta el renglón `--hasta-nueva`, sin la nota nueva), con la misma regla que `s0_5/b/scripts/anclas_e0_tabla_S0-5b.py`
(una cita sin archivo es del último archivo nombrado en el mismo renglón), y las empareja por fila (o por el comienzo del renglón, en
las notas) y por orden. Controla:
1. Las mismas filas y notas, con la misma cantidad de citas; F19b tiene una más (la de las reglas de S0-5 pasa a dos) y F19d es nueva.
2. Las 26 citas que el parche deja iguales o mueve: los renglones de la cita vieja en el código de S0-5b son iguales, byte a byte, a
   los de la cita nueva en el código aplicado.
3. La cita de F19b a las reglas de S0-5, `correr_e0.py:140-210`. El parche cambia `_r5` (su docstring y tres renglones de los
   reemplazos de S0-6a), así que el bloque viejo no es igual a ninguna unión de rangos nuevos. Pasa a dos citas:
   - `:140-205`, las constantes de S0-5: iguales, byte a byte, a los renglones 140-205 de S0-5b;
   - `:246-252`, `_r5`: exactamente el nodo `def _r5` del código aplicado, con su primer y su último renglón iguales a los
     renglones 208 y 210 de S0-5b; lo que cambia entre ellos es lo que agrega el parche.
4. F19d cita exactamente las anclas de `F19D`, en ese orden, y cada una por su contenido:
   - «nodos»: los nodos de primer nivel del código aplicado que caen en el rango son exactamente los nombrados, enteros, y son
     nuevos (no están en S0-5b), salvo `_r5`, que el parche cambia; fuera de esos nodos, el rango solo tiene renglones en blanco y
     comentarios que agrega el parche; empieza en el primer renglón del primer nodo o en un comentario agregado, y termina en el
     último renglón del último nodo o en un comentario agregado. (No se exige que el diff marque como agregado cada renglón de un
     nodo nuevo: el diff puede emparejar un renglón común, como un `return`, con uno viejo.)
   - «tramo»: el rango cae dentro de la función nombrada, y su primer y su último renglón los agrega el parche;
   - «docstring»: el rango cae dentro del docstring del módulo y todos sus renglones los agrega el parche;
   - entre todas las anclas de «nodos», están todos los nodos de primer nivel que el parche agrega.
Imprime ok o MAL por control, sin texto del código. Sale con 1 si algo da MAL.

Uso: python3 -I -B control_anclas_contenido_S0-6b_mesa.py --tabla-vieja <md> --tabla-nueva <md> --hasta-nueva N
       --codigo-viejo <dir S0-5b> --codigo-nuevo <dir aplicado> --parche <parche_e0_S0-6a-bis.diff>
"""
import argparse
import ast
import re
import sys
from pathlib import Path

ARCH = ("e0_lib.py", "correr_e0.py")
RX = re.compile(r"`([^`]*?)(?:([A-Za-z0-9_./]+\.py))?:(\d+)(?:-(\d+))?`")
F19B_S05 = ("correr_e0.py", 140, 210)
F19D = [
    ("correr_e0.py", 207, 252, "nodos", ["REGLAS_S0_6", "TOS_TANDA0_SIN_S0_6", "REEMPLAZOS_S0_6", "LISTAS_R5A_S0_6", "_r6", "_sd_s04", "_r5"]),
    ("correr_e0.py", 851, 860, "nodos", ["_filas_tabla_a"]),
    ("correr_e0.py", 1444, 1448, "tramo", "procesar_tablas_r2"),
    ("correr_e0.py", 1492, 1492, "tramo", "escalera_e0_r2"),
    ("correr_e0.py", 1518, 1525, "tramo", "escalera_e0_r2"),
    ("correr_e0.py", 1697, 1718, "tramo", "correr"),
    ("e0_lib.py", 228, 243, "docstring", None),
    ("e0_lib.py", 550, 655, "nodos", ["LARGO_RENGLON_TITULO_B", "MAX_RENGLONES_TITULO_B", "RE_DIGITOS_G", "RE_PUNTOS_G",
                                      "RE_DIGITO_O_PUNTO_G", "DIST_NUMERO_PARTIDO_G", "RE_NUM_PEGADO_H", "RE_PIE_FORMULARIO_K",
                                      "RE_CARATULA_J", "MAX_RENGLONES_CARATULA_J", "MAX_CHARS_CELDA_F", "TOL_COL_C",
                                      "MAX_SALTO_RECUADRO_I", "MIN_HUECO_COLUMNAS_I", "RE_APARTADO_A", "RE_NUMERACION_A",
                                      "RE_CON_NUMERO_A", "GAP_BLOQUE_A",
                                      "RANGO_SUBDOC_A,RANGO_BANDA_A,RANGO_APARTADO_A,RANGO_TITULO_A"]),
    ("e0_lib.py", 766, 779, "nodos", ["MAX_RENGLONES_TITULO_L"]),
    ("e0_lib.py", 794, 851, "nodos", ["lineas_de_indice_l"]),
    ("e0_lib.py", 1716, 1829, "nodos", ["unir_numero_partido_g", "_partes_i", "leer_recuadro_por_columna_i", "es_caratula_j",
                                        "_bloque_tope_f"]),
    ("e0_lib.py", 2067, 2073, "tramo", "parsear_cuerpo"),
    ("e0_lib.py", 2273, 2274, "tramo", "parsear_cuerpo"),
    ("e0_lib.py", 3163, 3364, "nodos", ["_pos_c", "_distancia_c", "_col_propia_c", "_comparte_columna_c", "_col_parrafo_c",
                                        "_parrafos_c", "_elegir_c", "_nombre_c", "asignar_por_columna_c"]),
    ("e0_lib.py", 3367, 3658, "nodos", ["_texto_banda_a", "_rango_a", "dividir_a"]),
    ("e0_lib.py", 3661, 3707, "nodos", ["mover_encabezado_tabla_f"]),
    ("e0_lib.py", 4085, 4095, "nodos", ["_marca_hijo", "_es_raiz_subdoc"]),
    ("e0_lib.py", 4324, 4367, "nodos", ["clase_encabezado_b"]),
    ("e0_lib.py", 4572, 4589, "tramo", "construir_chunks"),
]

ap = argparse.ArgumentParser()
for k in ("tabla_vieja", "tabla_nueva", "codigo_viejo", "codigo_nuevo", "parche"):
    ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
ap.add_argument("--hasta-nueva", dest="hasta", type=int, required=True)
a = ap.parse_args()
viejo = {f: (a.codigo_viejo / f).read_text(encoding="utf-8").splitlines() for f in ARCH}
nuevo_src = {f: (a.codigo_nuevo / f).read_text(encoding="utf-8") for f in ARCH}
nuevo = {f: s.splitlines() for f, s in nuevo_src.items()}
res = []


def ok(c: bool, q: str) -> None:
    res.append((bool(c), q))


def citas(md: Path, hasta: int | None) -> dict[str, list]:
    out: dict[str, list] = {}
    for n, l in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        if hasta and n > hasta:
            break
        actual = None
        for m in RX.finditer(l):
            if m.group(2):
                actual = m.group(2).rsplit("/", 1)[-1]
            if actual not in ARCH:
                continue
            et = l.split("|")[1].strip() if l.startswith("|") else l.strip()[:12]
            out.setdefault(et, []).append((actual, int(m.group(3)), int(m.group(4) or m.group(3))))
    return out


def nodos(f: str) -> list[tuple[int, int, str]]:
    out = []
    for n in ast.parse(nuevo_src[f]).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            k = n.name
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            ts = n.targets if isinstance(n, ast.Assign) else [n.target]
            k = ",".join(ast.unparse(t).strip("()").replace(" ", "") for t in ts)
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
            k = "<docstring>"
        else:
            k = "<" + type(n).__name__ + ">"
        out.append((n.lineno, n.end_lineno, k))
    return out


def nombres_viejos(f: str) -> set[str]:
    s = set()
    for n in ast.parse("\n".join(viejo[f])).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            s.add(n.name)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            ts = n.targets if isinstance(n, ast.Assign) else [n.target]
            s.add(",".join(ast.unparse(t).strip("()").replace(" ", "") for t in ts))
    return s


# renglones del código aplicado que agrega el parche
agregados: dict[str, set[int]] = {}
actual, k = None, 0
for l in a.parche.read_text(encoding="utf-8").splitlines():
    if l.startswith("+++ "):
        actual = l[4:].split("/")[-1].strip(); agregados.setdefault(actual, set()); continue
    m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", l)
    if m:
        k = int(m.group(1)); continue
    if actual is None or l.startswith("--- ") or l.startswith("diff "):
        continue
    if l.startswith("+"):
        agregados[actual].add(k); k += 1
    elif not l.startswith("-"):
        k += 1

cv, cn = citas(a.tabla_vieja, None), citas(a.tabla_nueva, a.hasta)
ok(set(cn) - set(cv) == {"F19d"} and not set(cv) - set(cn), "1. las mismas filas y notas con citas, más F19d")
ok(all(len(cn[e]) == len(cv[e]) + (1 if e == "F19b" else 0) for e in cv if e in cn),
   "1. la misma cantidad de citas en cada fila y nota, y una más en F19b")
n26 = 0
for e, lv in cv.items():
    ln = cn.get(e, [])
    j = 0
    for (f, i, fin) in lv:
        if (f, i, fin) == F19B_S05 and e == "F19b":
            dos = ln[j:j + 2]; j += 2
            r5 = [x for x in nodos("correr_e0.py") if x[2] == "_r5"]
            ok(len(dos) == 2 and dos[0] == ("correr_e0.py", 140, 205) and viejo[f][139:205] == nuevo[f][139:205],
               "3. F19b, las constantes de S0-5: `correr_e0.py:140-205`, iguales byte a byte a S0-5b")
            ok(len(dos) == 2 and len(r5) == 1 and dos[1] == ("correr_e0.py", r5[0][0], r5[0][1])
               and nuevo[f][r5[0][0] - 1] == viejo[f][207] and nuevo[f][r5[0][1] - 1] == viejo[f][209],
               "3. F19b, `_r5`: exactamente su nodo en el código aplicado, con el primer y el último renglón de S0-5b")
            continue
        if j >= len(ln):
            ok(False, f"2. {e}: falta una cita"); continue
        f2, i2, fin2 = ln[j]; j += 1
        n26 += 1
        ok(f2 == f and fin - i == fin2 - i2 and viejo[f][i - 1:fin] == nuevo[f2][i2 - 1:fin2] and fin2 <= len(nuevo[f2]),
           f"2. {e}: `{f}:{i}-{fin}` → `{f2}:{i2}-{fin2}`, los mismos renglones byte a byte")
ok(n26 == 26, f"2. son 26 citas iguales o movidas (da {n26})")
f19d = cn.get("F19d", [])
ok(f19d == [(f, i, fin) for f, i, fin, _, _ in F19D], "4. F19d cita exactamente sus anclas, en orden")
cubiertos = {f: set() for f in ARCH}
for f, i, fin, tipo, det in F19D:
    ns = nodos(f)
    dentro = [x for x in ns if not (x[1] < i or x[0] > fin)]
    if tipo == "nodos":
        en_nodos = set().union(*[set(range(x[0], x[1] + 1)) for x in dentro]) if dentro else set()
        coment = lambda k: k in agregados[f] and nuevo[f][k - 1].strip().startswith("#")  # noqa: E731
        lineas_ok = all(k in en_nodos or not nuevo[f][k - 1].strip() or coment(k) for k in range(i, fin + 1))
        bordes = dentro and (i == dentro[0][0] or coment(i)) and (fin == dentro[-1][1] or coment(fin))
        son_nuevos = all(x[2] not in nombres_viejos(f) or x[2] == "_r5" for x in dentro)
        ok([x[2] for x in dentro] == det and all(i <= x[0] and x[1] <= fin for x in dentro) and lineas_ok and bool(bordes)
           and son_nuevos,
           f"4. F19d `{f}:{i}-{fin}`: exactamente los nodos {', '.join(det)[:80]}")
        cubiertos[f] |= {x[2] for x in dentro}
    elif tipo == "tramo":
        fun = [x for x in ns if x[2] == det]
        ok(len(fun) == 1 and fun[0][0] <= i and fin <= fun[0][1] and i in agregados[f] and fin in agregados[f],
           f"4. F19d `{f}:{i}-{fin}`: dentro de {det}, y empieza y termina en renglones del parche")
    else:
        doc = [x for x in ns if x[2] == "<docstring>" and x[0] == 1]
        ok(len(doc) == 1 and doc[0][0] <= i and fin <= doc[0][1] and all(k in agregados[f] for k in range(i, fin + 1)),
           f"4. F19d `{f}:{i}-{fin}`: dentro del docstring del módulo, todo agregado por el parche")
for f in ARCH:
    nuevos = {x[2] for x in nodos(f) if not x[2].startswith("<")} - nombres_viejos(f)
    ok(nuevos <= cubiertos[f], f"4. {f}: los {len(nuevos)} nodos de primer nivel que agrega el parche están en anclas de F19d")
for c, q in res:
    print(("ok   " if c else "MAL  ") + q)
print(f"{sum(c for c, _ in res)} de {len(res)} controles ok")
sys.exit(0 if all(c for c, _ in res) else 1)
