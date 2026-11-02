"""carpetas_de_las_transcripciones_mesa.py — Mesa, §394 (01/11/2026): en qué carpetas buscó la §393 las transcripciones de la
generación, para escribir el alcance. Solo nombres de carpetas y cuentas de archivos: no abre ninguna transcripción.
  - Las dos que busca `el_grafo_en_las_sesiones_de_la_generacion_mesa.py` (§393), con su misma regla: la carpeta de
    `la configuración del asistente de la carpeta personal/projects/` cuyo nombre es la ruta de `fuera_del_repo/b63_p2` o `fuera_del_repo/b64_p2` con «/», « » y «_» por «-»;
    adentro, `*.jsonl` (las sesiones) y `*/subagents/*.jsonl` (sus subagentes).
  - Las otras carpetas de `la configuración del asistente de la carpeta personal/projects/`: cuántas son, cuántas son de una carpeta de `fuera_del_repo`, y de esas, las de B6.3 o
    B6.4, con sus cuentas. Ninguna se buscó.
Los nombres van con la carpeta personal cambiada por `<carpeta personal>`. USD 0.
  python3 -I -B carpetas_de_las_transcripciones_mesa.py <fuera_del_repo>
"""
import sys
from pathlib import Path

F = Path(sys.argv[1]).resolve()
P = Path.home() / ".claude" / "projects"


def nombre(ruta: Path) -> str:
    return "-" + str(ruta).strip("/").replace("/", "-").replace(" ", "-").replace("_", "-")


CASA = nombre(Path.home())
san = lambda n: n.replace(CASA, "<carpeta personal>", 1)  # noqa: E731
cuentas = lambda d: (len(list(d.glob("*.jsonl"))), len(list(d.glob("*/subagents/*.jsonl"))))  # noqa: E731
buscadas = {sub: P / nombre(F / sub) for sub in ("b63_p2", "b64_p2")}
print("las dos carpetas que buscó la §393 (sesiones y subagentes):")
for sub, d in buscadas.items():
    print(f"   {sub}: la configuración del asistente de la carpeta personal/projects/{san(d.name)}/ | existe {d.is_dir()} | {cuentas(d) if d.is_dir() else '-'}")
todas = sorted(x for x in P.iterdir() if x.is_dir())
de_fuera = [x for x in todas if x.name.startswith(nombre(F))]
print(f"carpetas en la configuración del asistente de la carpeta personal/projects/: {len(todas)}; de una carpeta de fuera_del_repo: {len(de_fuera)}; buscadas: "
      f"{sum(d in todas for d in buscadas.values())}")
print("las de fuera_del_repo que nombran B6.3 o B6.4 y no se buscaron (sesiones y subagentes):")
for x in de_fuera:
    resto = x.name[len(nombre(F)):]
    if x not in buscadas.values() and any(k in resto for k in ("b63", "b64")):
        print(f"   la configuración del asistente de la carpeta personal/projects/{san(x.name)}/ | {cuentas(x)}")
raiz = P / nombre(F)
print(f"la de fuera_del_repo misma, sin subcarpeta, no se buscó: existe {raiz.is_dir()} | {cuentas(raiz) if raiz.is_dir() else '-'}")
repo = P / nombre(Path(__file__).resolve().parents[5])
print(f"la del repo, no se buscó: existe {repo.is_dir()} | {cuentas(repo) if repo.is_dir() else '-'}")
