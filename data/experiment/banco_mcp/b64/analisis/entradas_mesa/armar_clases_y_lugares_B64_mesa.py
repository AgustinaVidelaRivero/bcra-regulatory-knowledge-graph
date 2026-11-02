"""armar_clases_y_lugares_B64_mesa.py — Mesa, §384 (01/11/2026): las dos entradas del análisis de B6.4 que el H-6 dejó con su forma y sin
llenar (`analizar_b64.py`, `controlar_clases`, `anclas_fuera_de_los_46` y `lugares_que_cambiaron`; la forma, aceptada por la autora el
30/10/2026 entre las cuatro elecciones del H-6):
  - `clases_documentos_B64.json`: {elegibles, clases}. Los 46 elegibles del §3.1 y las cuatro clases del mismo §3.1, con el tamaño que
    fija `analizar_b64.TAMANO_DE_CLASE`:
      · anclas_de_las_96_de_B63 (37): el TO de cada ancla de las 96 de B6.3, del archivo de preguntas que nombra su entrada sellada;
      · N3 (14): el TO (campo `to`) de las 30 preguntas de N3, del archivo que nombra `entrada_n6.json` (como `conteos_N3_mesa.py`, §344);
      · evaluacion_final (15): `data/experiment/esq/documentos_excluidos_evaluacion_final.json`;
      · tanda_0 (5): el conjunto `tanda0` de `data/experiment/esq/elegibles_B63_O2_2026-10-15/elegibles_O2_mesa.py`, el que usó el sorteo
        de B6.3;
  - `lugares_B64.json`: {lugares: [{lugar, id, sorteado, final}]}, uno por pregunta aprobada. El lugar sale del id de la pregunta
    (`B64-O<ola>-L<lugar>`, con `-R<n>` si es un reemplazo); lo sorteado (documento, unidad y clase), del sorteo sellado de B6.4
    (`sorteo_B64.json`, `44d67b7b…`); lo final, el TO y el ancla de la pregunta aprobada, y la clase de ese TO entre los 46.
Lee solo por código, del repo en HEAD y de los archivos que nombran las entradas, con su sha256: de las preguntas, solo su id, su TO y sus
anclas (nunca un texto). Escribe los dos JSON en la carpeta que se le pasa (no pisa) e imprime solo cuentas y sha256. USD 0.
  python3 -I -B armar_clases_y_lugares_B64_mesa.py <repo> <elegibles_B64.json> <sorteo_B64.json> <carpeta de salida, nueva>
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SHA_ELEGIBLES = "be47abcc"          # el prefijo que cita el §3.1 del pre-registro de B6.4 (`elegibles_B64.json`, `be47abcc…`)
SHA_SORTEO = "44d67b7bc7fe663bb6e06f8d32f83fbe42d423cc1d6321fcc9eb45c39110ec0c"
TAMANO = {"anclas_de_las_96_de_B63": 37, "N3": 14, "evaluacion_final": 15, "tanda_0": 5}


def frena(m):
    raise SystemExit(f"FRENO: {m}")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def head(repo: Path, rel: str) -> bytes:
    p = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "show", f"HEAD:{rel}"], capture_output=True)
    if p.returncode != 0:
        frena(f"{rel} no está en HEAD")
    return p.stdout


def de_la_entrada(repo: Path, rel: str) -> list:
    """Las preguntas del archivo que nombra una entrada de HEAD, con su sha256."""
    e = json.loads(head(repo, rel))
    rp = e["preguntas"]["ruta"]
    b = (Path(rp).expanduser() if rp.startswith("~") else repo / rp).read_bytes()
    if sha(b) != e["preguntas"]["sha256"]:
        frena(f"las preguntas que nombra {rel} no dan su sha256")
    return e, json.loads(b)["preguntas"]


def clases(repo: Path, eleg: dict) -> dict:
    elegibles = [d["documento"] for v in eleg["por_clase"].values() for d in v]
    e63, p63 = de_la_entrada(repo, "data/experiment/banco_mcp/b63/entrada_B63.json")
    ids63 = set(e63["preguntas"]["ids_en_orden"])
    anclas63 = sorted({a["unidad"].split("::", 1)[0] for q in p63 if q["id"] in ids63 for a in q["anclas"]})
    _, n3 = de_la_entrada(repo, "data/experiment/banco_mcp/n6/entrada_n6.json")
    docs_n3 = sorted({q["to"] for q in n3})
    exc = json.loads(head(repo, "data/experiment/esq/documentos_excluidos_evaluacion_final.json"))
    ef = sorted({d if isinstance(d, str) else d.get("id") for d in exc["documentos"]})
    codigo = head(repo, "data/experiment/esq/elegibles_B63_O2_2026-10-15/elegibles_O2_mesa.py").decode("utf-8")
    m = re.search(r"^tanda0 = \{([^}]*)\}$", codigo, re.M)
    if not m:
        frena("no está el conjunto tanda0 en elegibles_O2_mesa.py")
    t0 = sorted(re.findall(r'"([a-z0-9_]+)"', m.group(1)))
    out = {"que": "las clases de documentos del §3.1 del pre-registro de B6.4, para analizar_b64.py (mesa, §384)",
           "elegibles": elegibles,
           "clases": {"anclas_de_las_96_de_B63": anclas63, "N3": docs_n3, "evaluacion_final": ef, "tanda_0": t0}}
    if len(set(elegibles)) != 46 or len(elegibles) != 46:
        frena("los elegibles no son 46")
    if {k: len(set(v)) for k, v in out["clases"].items()} != TAMANO:
        frena("las clases no tienen el tamaño del §3.1")
    if set(elegibles) & (set(docs_n3) | set(ef) | set(t0) | set(anclas63)):
        frena("un elegible está en una de las cuatro clases")
    return out


def lugares(repo: Path, so: dict, eleg: dict) -> dict:
    clase_de = {d["documento"]: c for c, v in eleg["por_clase"].items() for d in v}
    e64, p64 = de_la_entrada(repo, "data/experiment/banco_mcp/b64/entrada_B64.json")
    ids = e64["preguntas"]["ids_en_orden"]
    por_id = {q["id"]: q for q in p64}
    if sorted(por_id) != sorted(ids) or len(p64) != 96 or len(ids) != 96:
        frena("las preguntas aprobadas no son las 96 de la entrada")
    sorteado = {(o["ola"], x["lugar"]): x for o in so["olas"] for x in o["lugares"]}
    if len(sorteado) != 96:
        frena("el sorteo no trae 96 lugares")
    filas, usados = [], set()
    for q in ids:
        m = re.fullmatch(r"B64-O(\d+)-L(\d+)(?:-R\d+)?", q)
        if not m:
            frena("un id de pregunta sin la forma B64-O<ola>-L<lugar>")
        k = (int(m.group(1)), int(m.group(2)))
        if k not in sorteado or k in usados:
            frena("una pregunta sin su lugar en el sorteo, o dos preguntas en el mismo lugar")
        usados.add(k)
        s, p = sorteado[k], por_id[q]
        anclas = [a["unidad"] for a in p["anclas"] if a["rol"] == "ancla"]
        if len(anclas) != 1 or anclas[0].split("::", 1)[0] != p["to"] or p["to"] not in clase_de:
            frena("una pregunta sin una sola ancla en su TO, o con su TO fuera de los 46")
        filas.append({"lugar": f"O{k[0]}-L{k[1]:02d}", "id": q,
                      "sorteado": {"documento": s["to"], "unidad": s["unidad"], "clase": s["clase"]},
                      "final": {"documento": p["to"], "unidad": anclas[0], "clase": clase_de[p["to"]]}})
    return {"que": "lo sorteado y lo final de cada lugar de B6.4, para analizar_b64.py (mesa, §384)", "lugares": filas}


def main() -> int:
    repo, el_p, so_p, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    if out.exists():
        frena("la carpeta de salida ya existe")
    el_b, so_b = el_p.read_bytes(), so_p.read_bytes()
    if not sha(el_b).startswith(SHA_ELEGIBLES) or sha(so_b) != SHA_SORTEO:
        frena("los elegibles o el sorteo de B6.4 no son los sellados")
    eleg, so = json.loads(el_b), json.loads(so_b)
    if so["entradas"]["elegibles_sha256"] != sha(el_b):
        frena("el sorteo no se hizo sobre estos elegibles")
    cl, lu = clases(repo, eleg), lugares(repo, so, eleg)
    out.mkdir(parents=True)
    for nombre, d in (("clases_documentos_B64.json", cl), ("lugares_B64.json", lu)):
        (out / nombre).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"clases: {len(cl['elegibles'])} elegibles; " + "; ".join(f"{k} {len(v)}" for k, v in cl["clases"].items()))
    print(f"lugares: {len(lu['lugares'])}, uno por pregunta aprobada, cada uno con su sorteado y su final")
    for nombre in ("clases_documentos_B64.json", "lugares_B64.json"):
        print(f"{nombre}: {sha((out / nombre).read_bytes())}")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
