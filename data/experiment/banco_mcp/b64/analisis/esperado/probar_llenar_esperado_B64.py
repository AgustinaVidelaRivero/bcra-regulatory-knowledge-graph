"""probar_llenar_esperado_B64.py — Mesa, §384 (01/11/2026): la prueba con datos de juguete de `llenar_esperado_B64.py`. Arma, en la carpeta
de trabajo que se le pasa (nueva), un árbol de juguete con las rutas de los comandos del análisis y de la exactitud, y corre `main` del
llenado sin editarlo. Cambia solo dos cosas del módulo: `CONOCIDOS`, por los sha256 de los archivos de juguete, y `leer_plantilla`, que
devuelve la plantilla de HEAD del repo que se le pasa (el árbol de juguete no es un repo). Ningún dato real. Imprime OK o MAL por caso y
sale con 0 solo si todo da. USD 0.
  python3 -I -B probar_llenar_esperado_B64.py <repo> <carpeta de trabajo nueva>
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("L", AQUI / "llenar_esperado_B64.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
REPO, W = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
if W.exists():
    raise SystemExit("la carpeta de trabajo ya existe")
W.mkdir(parents=True)
PLANTILLA = L.leer_plantilla(REPO)
res = []


def c(nombre, ok):
    res.append(bool(ok))
    print(("OK  " if ok else "MAL ") + nombre)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def arbol(nombre: str) -> tuple:
    """Un árbol de juguete: un repo, fuera_del_repo, el scratchpad y la carpeta de la mesa, con un archivo en cada ruta."""
    base = W / nombre
    R, F, SP, M = base / "repo", base / "fuera_del_repo", base / "sp", base / "mesa"
    rs = L.rutas(R, F, SP)
    for k, p in rs.items():
        if k in ("clases_documentos", "lugares"):
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"juguete de {k}\n", encoding="utf-8")
    M.mkdir(parents=True)
    for n in L.MESA:
        (M / n).write_text(f"juguete de la mesa: {n}\n", encoding="utf-8")
    man = {"archivos": [{"ruta": v, "sha256": sha(rs[k])} for k, v in L.EN_EL_MANIFIESTO.items()]}
    rs["manifiesto_fuera"].write_text(json.dumps(man) + "\n", encoding="utf-8")
    L.CONOCIDOS = {k: sha(rs[k]) for k in ("entrada", "manifiesto_fuera", "sello_planilla", "estructura_planilla", "armado_e0")} | \
        {"clases_documentos": sha(M / L.MESA[0]), "lugares": sha(M / L.MESA[1])}
    return R, F, SP, M, rs


def correr(R, F, SP, M) -> tuple:
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = L.main([str(R), str(F), str(SP), str(M)])
        return rc, out.getvalue()
    except SystemExit as e:
        return str(e), out.getvalue()


def nada_escrito(F) -> bool:
    return not (F / "analisis_b64_corr/esperado").exists() and not (F / "analisis_b64_corr/entradas_mesa").exists()


L.leer_plantilla = lambda R: json.loads(json.dumps(PLANTILLA))

R, F, SP, M, rs = arbol("base")
rc, txt = correr(R, F, SP, M)
sal = F / "analisis_b64_corr/esperado/esperado_b64.json"
o = json.loads(sal.read_text(encoding="utf-8")) if sal.exists() else {}
claves = [k for k in PLANTILLA if not k.startswith("_")]
c("1 llena las 16 claves de la plantilla, cada una con el sha256 de su archivo; devueltas, {} sin la carpeta",
  rc == 0 and len(claves) == 16 and sorted(k for k in o if not k.startswith("_")) == sorted(claves) and o["devueltas"] == {}
  and all(o[k] == sha(rs[k] if k not in ("clases_documentos", "lugares") else M / L.MESA[("clases_documentos", "lugares").index(k)])
          for k in claves if k != "devueltas"))
c("2 copia las dos entradas de la mesa a entradas_mesa/, iguales, y conserva las notas de la plantilla",
  all(sha(F / "analisis_b64_corr/entradas_mesa" / n) == sha(M / n) for n in L.MESA)
  and all(o.get(k) == v for k, v in PLANTILLA.items() if k.startswith("_")))
c("3 imprime una línea por clave y el sha256 del JSON escrito",
  len(txt.splitlines()) == 17 and txt.splitlines()[-1] == f"esperado_b64.json: {sha(sal)}")
rc2, _ = correr(R, F, SP, M)
c("4 no pisa: una segunda corrida frena", rc2 == "FRENO: ya existe esperado/esperado_b64.json o entradas_mesa/: no se pisa")

R, F, SP, M, rs = arbol("con_devueltas")
d = F / "b64_material_expertos/devueltas"
d.mkdir(parents=True)
for n in ("experto_1.csv", "experto_2.csv", "NO_ABRIR_experto_3.csv", "nota.txt"):
    (d / n).write_text(f"juguete {n}\n", encoding="utf-8")
rc, _ = correr(R, F, SP, M)
o = json.loads((F / "analisis_b64_corr/esperado/esperado_b64.json").read_text(encoding="utf-8")) if rc == 0 else {}
c("5 devueltas: los dos CSV, cada uno con su sha256; ni el NO_ABRIR_ ni el que no es CSV",
  o.get("devueltas") == {"experto_1.csv": sha(d / "experto_1.csv"), "experto_2.csv": sha(d / "experto_2.csv")})

R, F, SP, M, rs = arbol("sello_cambiado")
rs["sello_planilla"].write_text("otro sello\n", encoding="utf-8")
rc, _ = correr(R, F, SP, M)
c("6 un sello de la adjudicación que no es el controlado frena, sin escribir nada",
  rc == "FRENO: sello_planilla no da el sha256 que se conoce" and nada_escrito(F))

R, F, SP, M, rs = arbol("d10")
rs["d10"].write_text("otro d10\n", encoding="utf-8")
rc, _ = correr(R, F, SP, M)
c("7 un D-10 que no es el del manifiesto frena, sin escribir nada",
  rc == "FRENO: d10 no da el sha256 del manifiesto de lo que queda fuera" and nada_escrito(F))

R, F, SP, M, rs = arbol("falta")
shutil.move(str(rs["agregados_tolerante"]), str(W / "falta" / "apartado.json"))
rc, _ = correr(R, F, SP, M)
c("8 si falta un archivo, frena sin escribir nada", rc == "FRENO: falta el archivo de agregados_tolerante" and nada_escrito(F))

R, F, SP, M, rs = arbol("mesa")
(M / L.MESA[1]).write_text("otros lugares\n", encoding="utf-8")
rc, _ = correr(R, F, SP, M)
c("9 una entrada de la mesa que no es la armada frena, sin escribir nada",
  rc == "FRENO: lugares no da el sha256 que se conoce" and nada_escrito(F))

R, F, SP, M, rs = arbol("plantilla")
L.leer_plantilla = lambda R: json.loads(json.dumps(PLANTILLA)) | {"otra_entrada": None}
rc, _ = correr(R, F, SP, M)
L.leer_plantilla = lambda R: json.loads(json.dumps(PLANTILLA))
c("10 una plantilla con otra clave frena, sin escribir nada",
  rc == "FRENO: las claves de la plantilla no son las rutas de los comandos más devueltas" and nada_escrito(F))

print(f"{sum(res)} de {len(res)} casos dan")
sys.exit(0 if all(res) else 1)
