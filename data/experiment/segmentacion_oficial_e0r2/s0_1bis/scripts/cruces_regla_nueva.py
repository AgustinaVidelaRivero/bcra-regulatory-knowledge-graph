"""S0-1 bis: cruce de una regla nueva (8 o 9) con las reglas 2, 6, 7 y T, sobre los TOs que la regla nueva toca.
Para cada regla X se comparan cuatro corridas: con todas (A), con todas menos X (A-X), sin la regla nueva (B) y sin
la regla nueva ni X (B-X). X actúa en un TO si sus chunks o su estructura cambian al apagarla; la regla nueva actúa
igual con y sin X si el conjunto de ids de los chunks que agrega y que quita es el mismo. Solo lectura.

Uso: python -B cruces_regla_nueva.py <runs> <A> <B> <prefijo A-X> <prefijo B-X> <tos,coma> <salida.json>
(los directorios A-X y B-X son <prefijo>_<X> para X en r2, r6, r7 y r1r7t)"""
import json
import sys
from pathlib import Path

runs, A, B, pa, pb, tos, sal = sys.argv[1:8]
runs, tos = Path(runs), tos.split(",")


def arch(run: str, k: str, to: str) -> bytes:
    p = runs / run / f"{k}_{to}.json"
    if not p.exists():
        p = runs / run / "por_to" / to / f"{k}_{to}.json"
    return p.read_bytes()


def ids(run: str, to: str) -> list:
    return [(c["id"], c["sha256_completo"]) for c in json.loads(arch(run, "chunks", to))]


def actua(r1: str, r2: str, to: str) -> bool:
    return any(arch(r1, k, to) != arch(r2, k, to) for k in ("chunks", "estructura", "tablas"))


def delta(r1: str, r2: str, to: str):
    a, b = set(ids(r1, to)), set(ids(r2, to))
    return sorted(b - a), sorted(a - b)


out = {}
for x in ("r2", "r6", "r7", "r1r7t"):
    fila = {}
    for to in tos:
        fila[to] = {
            "x_actua_con_la_nueva": actua(A, f"{pa}_{x}", to),
            "x_actua_sin_la_nueva": actua(B, f"{pb}_{x}", to),
            "la_nueva_actua_igual_con_y_sin_x": delta(B, A, to) == delta(f"{pb}_{x}", f"{pa}_{x}", to),
        }
    out[x] = fila
Path(sal).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for x, fila in out.items():
    print(x, {to: "".join("SN"[not v] for v in f.values()) for to, f in fila.items()})
