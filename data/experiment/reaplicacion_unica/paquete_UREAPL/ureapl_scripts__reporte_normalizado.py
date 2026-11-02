"""Compara dos reporte_ensamblado_r2.json con las rutas de su --salida y de su raíz normalizadas (el reporte guarda la ruta
de su salida y, absolutas, las de la raíz donde corrió: todo lo anterior a «/data/experiment/» o a «/ureapl/» pasa a <RAIZ>). Imprime True/False y, si difieren, las claves de primer nivel que difieren.
Uso: python3 -I -B reporte_normalizado.py <reporte A> <salida A> <reporte B> <salida B>"""
import json, re, sys
def cargar(p, salida):
    t = open(p, encoding="utf-8").read()
    t = t.replace(salida, "<SALIDA>")
    t = re.sub(r'"/[^"]*?/(data/experiment/|ureapl/)', r'"<RAIZ>/\1', t)
    return json.loads(t)
a = cargar(sys.argv[1], sys.argv[2]); b = cargar(sys.argv[3], sys.argv[4])
iguales = a == b
print(iguales, [] if iguales else sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)))
