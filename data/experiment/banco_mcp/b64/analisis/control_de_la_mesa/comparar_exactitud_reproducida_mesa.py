"""comparar_exactitud_reproducida_mesa.py — Mesa, §387 (01/11/2026): por qué la exactitud de cita reproducida no da el sha256 de la de la
autora. Compara, en las dos pasadas (la principal y la informativa):
  1. el JSON de la exactitud: qué rutas de claves difieren;
  2. la salida del instrumento de citas (`trabajo_exactitud_de_cita/ucita_B63.json`): qué insumos difieren y en qué campo; si cada ruta
     que difiere es la misma desde `/a/exactitud_de_cita/` (la carpeta de salida); si los sha256 de todos los insumos son iguales; y si el
     resto del JSON, sin los insumos, es igual;
  3. el sha256 que el JSON de la exactitud guarda de cada salida del instrumento, contra el del archivo;
  4. las sesiones que la función sellada copió a la carpeta de trabajo: el sha256 de cada archivo, en las dos corridas.
Imprime solo cuentas, nombres de campos y booleanos: ningún valor. USD 0.
  python3 -I -B comparar_exactitud_reproducida_mesa.py <salidas/a de la autora> <a/ de la reproducción>
"""
import hashlib
import json
import sys
from pathlib import Path

SA, RA = (Path(x) for x in sys.argv[1:3])
CORTE = "/a/exactitud_de_cita/"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
ok = {}


def rutas(a, b, r=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            yield from ((r + "." + k + " (falta en una)",) if k not in a or k not in b else rutas(a[k], b[k], r + "." + k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            yield r + " (largos distintos)"
        for i, (x, y) in enumerate(zip(a, b)):
            yield from rutas(x, y, f"{r}[{i}]")
    elif a != b:
        yield r


def leer(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


ea, eb = leer(SA / "exactitud_de_cita/exactitud_de_cita_B64.json"), leer(RA / "exactitud_de_cita/exactitud_de_cita_B64.json")
d = list(rutas(ea, eb))
print(f"1. el JSON de la exactitud: difieren {len(d)} rutas de claves: {d}")
ok["1 solo difieren los sha256 de las dos salidas del instrumento"] = \
    sorted(d) == [".informativa.instrumento.salida_sha256", ".principal.instrumento.salida_sha256"]
for pasada, sub in (("principal", ""), ("informativa", "informativa/")):
    ta = SA / "exactitud_de_cita" / sub / "trabajo_exactitud_de_cita"
    tb = RA / "exactitud_de_cita" / sub / "trabajo_exactitud_de_cita"
    ua, ub = leer(ta / "ucita_B63.json"), leer(tb / "ucita_B63.json")
    ia, ib = ua["insumos"], ub["insumos"]
    dif = [k for k in ia if ia[k] != ib.get(k)]
    campos = sorted({c for k in dif for c in set(ia[k]) | set(ib[k]) if ia[k].get(c) != ib[k].get(c)})
    misma = [k for k in dif if CORTE in ia[k]["ruta"] and CORTE in ib[k]["ruta"]
             and ia[k]["ruta"].split(CORTE, 1)[1] == ib[k]["ruta"].split(CORTE, 1)[1]]
    shas = all(ia[k].get(c) == ib[k].get(c) for k in ia for c in ("sha256", "sha256_cierre", "n_archivos"))
    fuera = sum(1 for k in ia if k not in dif and CORTE not in ia[k]["ruta"])
    resto_a = {k: v for k, v in ua.items() if k != "insumos"}
    resto_b = {k: v for k, v in ub.items() if k != "insumos"}
    print(f"2. {pasada}: {len(ia)} insumos en la autora y {len(ib)} en la reproducción; difieren {len(dif)}, solo en {campos}; "
          f"{len(misma)} de esas rutas son iguales desde {CORTE}; los {len(ia) - len(dif)} iguales están fuera de la carpeta de salida "
          f"({fuera})")
    ok[f"2 {pasada}: los insumos difieren solo en la ruta de la carpeta de salida, y sus sha256 son iguales"] = \
        set(ia) == set(ib) and campos == ["ruta"] and len(misma) == len(dif) and shas and fuera == len(ia) - len(dif)
    ok[f"2 {pasada}: sin los insumos, la salida del instrumento es igual"] = resto_a == resto_b
    ok[f"3 {pasada}: el JSON de la exactitud guarda el sha256 del archivo del instrumento, en las dos corridas"] = \
        ea[pasada]["instrumento"]["salida_sha256"] == sha(ta / "ucita_B63.json") \
        and eb[pasada]["instrumento"]["salida_sha256"] == sha(tb / "ucita_B63.json")
    for n in ("anclas.json", "mapa_sesiones.json"):
        ok[f"4 {pasada}: {n} es igual byte a byte"] = sha(ta / n) == sha(tb / n)
    fa = {str(p.relative_to(ta / "sesiones")): sha(p) for p in sorted((ta / "sesiones").rglob("*")) if p.is_file()}
    fb = {str(p.relative_to(tb / "sesiones")): sha(p) for p in sorted((tb / "sesiones").rglob("*")) if p.is_file()}
    ok[f"4 {pasada}: las sesiones copiadas son las mismas, archivo por archivo ({len(fa)} y {len(fb)})"] = fa == fb
for k, v in ok.items():
    print(("OK  " if v else "MAL ") + k)
print(f"{sum(ok.values())} de {len(ok)} controles dan")
