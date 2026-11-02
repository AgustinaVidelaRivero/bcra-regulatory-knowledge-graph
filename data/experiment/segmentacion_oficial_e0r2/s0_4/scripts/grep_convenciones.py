"""Grep de convenciones de S0-4a (CLAUDE.md §5): nombres de personas, origen conversacional de una decisión y rutas
absolutas, con un control positivo. Los nombres no se escriben en este archivo ni en su salida: se toman de
`git config user.name` del repo (partido en palabras) y en la salida figuran como nombre_1, nombre_2…
Uso: python -B grep_convenciones.py <repo> <archivo o directorio> … > salida.txt"""
import collections
import os
import re
import subprocess
import sys

repo, rutas = sys.argv[1], sys.argv[2:]
nombre = subprocess.run(["git", "-C", repo, "config", "user.name"], capture_output=True, text=True).stdout.strip()
palabras = [p.lower() for p in re.findall(r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[a-záéíóúñ]+", nombre) if len(p) > 2]
TERMINOS = [(f"nombre_{i}", re.escape(p)) for i, p in enumerate(palabras, 1)] + [
    ("sl" "ack", r"sl[a]ck"), ("whats" "app", r"whats[a]pp"), ("ma" "il", r"\bm[a]il\b|e-m[a]il"), ("cor" "reo", r"cor[r]eo"),
    ("reunion", r"reuni[oó]n"), ("como_dijo", r"como d[i]jo"), ("segun_x", r"seg[uú]n (el|la) (m[a]il|mensaje)"),
    ("pedido_por", r"pedido por"), ("me_pidio", r"me pidi"), ("mentor", r"mentor"), ("prof" "esor", r"prof[e]sor"),
    ("ruta_users", r"/Use[r]s/"), ("ruta_tmp", r"/priv[a]te/tmp|claude-501"),
]
RX = [(k, re.compile(p, re.I)) for k, p in TERMINOS]

control = " ".join(["x " + (palabras[int(k.split("_")[1]) - 1] if k.startswith("nombre_") else
                             {"ma" "il": "ma" "il", "reunion": "reunión", "segun_x": "según el ma" "il", "me_pidio": "me pidió",
                              "ruta_users": "/Us" "ers/", "ruta_tmp": "/private" "/tmp", "como_dijo": "como di" "jo",
                             "pedido_por": "pedido por"}.get(k, k)) for k, _ in TERMINOS])
falta = [k for k, rx in RX if not rx.search(control)]
print(f"control positivo: {len(TERMINOS) - len(falta)} de {len(TERMINOS)} términos encontrados"
      + (f"; FALTAN {falta}" if falta else ""))

archivos = []
for r in rutas:
    if os.path.isdir(r):
        archivos += [os.path.join(r, f) for f in sorted(os.listdir(r)) if os.path.isfile(os.path.join(r, f))]
    else:
        archivos.append(r)
tot = collections.Counter()
print(f"archivos revisados: {len(archivos)}")
for f in archivos:
    t = open(f, encoding="utf-8", errors="replace").read()
    for k, rx in RX:
        for m in rx.finditer(t):
            tot[k] += 1
            ctx = t[max(0, m.start() - 45):m.end() + 35].replace("\n", " ")
            if k.startswith("nombre_"):
                ctx = "(contexto omitido)"
            print(f"{os.path.basename(f)}\t{k}\t{ctx}")
print("total por término:", dict(sorted(tot.items())), "— total", sum(tot.values()))
