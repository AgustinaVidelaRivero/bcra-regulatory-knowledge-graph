"""
empalme_subgrafo.py — U-MANT, etapa M2 (e): procedimiento de empalme de un
subgrafo re-extraído, demostrado en seco (USD 0, sin API, sin red).

Dos demostraciones (procedimiento completo en
data/experiment/mantenimiento/procedimiento_empalme.md):

  dirigida      Reproduce los ensamblados sellados de la tanda 0 (`1b8916c`) a
                partir de la salida base (corpus_tanda0/salida/, E1→E3 de los
                diez TOs) y de las tres unidades de cap re-extraídas
                (cap::3.1.14.1, cap::4.2.1.2, cap::4.3.3.1, tomadas de
                corpus_tanda0/salida_dirigida/). Pasos: copia la base al
                directorio de trabajo; en cada TO afectado sustituye los
                registros de las unidades re-extraídas (extracciones_e1.jsonl,
                finales.jsonl, veredictos.jsonl, cola_humana.jsonl); re-compacta
                E1 y cierra E2 del TO con las funciones del runner; corre
                tanda0/code/ensamblar_tanda0.py para los tres manifiestos de
                ensamblado; compara el sha256 de cada kg.json con el sellado.

  renumeracion  Sobre la E0 de pro (tanda 0), incorpora un punto antes de
                pro::2.3 con la misma renumeración del selftest de M1 (V24) y
                muestra que una firma de contenido sin números identifica a las
                unidades que solo cambiaron de número.

Todo se escribe bajo --trabajo, que tiene que estar fuera del repo; el repo se
lee en solo lectura. El ensamblador corre como proceso aparte con
PYTHONDONTWRITEBYTECODE=1 y -B.

Uso, desde la raíz del repo:
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
    data/experiment/mantenimiento/code/empalme_subgrafo.py dirigida \\
    --trabajo <dir fuera del repo> --out <json>
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
    data/experiment/mantenimiento/code/empalme_subgrafo.py renumeracion --out <json>
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[3]
REX = REPO / "data" / "experiment" / "reextraccion_v2"
T0 = REX / "corpus_tanda0"
BASE = T0 / "salida"
REEXTRAIDAS = T0 / "salida_dirigida"
MANIF = REX / "manifiestos"
MANIFIESTO_CORRIDA = MANIF / "tanda0_10tos.json"
ENSAMBLADOR = REPO / "data" / "experiment" / "tanda0" / "code" / "ensamblar_tanda0.py"
ENSAMBLADOS = {"ens_desarrollo": "tanda0_ens_desarrollo.json",
               "ens_cinco": "tanda0_ens_cinco.json",
               "ens_diez": "tanda0_ens_diez.json"}
UNIDADES_REEXTRAIDAS = ("cap::3.1.14.1", "cap::4.2.1.2", "cap::4.3.3.1")
ARCHIVOS_POR_UNIDAD = ("extracciones_e1.jsonl", "finales.jsonl", "veredictos.jsonl",
                       "cola_humana.jsonl")


def sha256_archivo(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def leer_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def escribir_jsonl(p: Path, regs: list[dict]) -> None:
    with p.open("w", encoding="utf-8") as f:
        for r in regs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _fuera_del_repo(p: Path) -> Path:
    p = p.resolve()
    if str(p).startswith(str(REPO.resolve())):
        raise SystemExit("FRENO: --trabajo tiene que estar fuera del repo")
    return p


# ------------------------------------------------------------------------- #
# Paso 4 del procedimiento: sustitución de las salidas de las unidades       #
# ------------------------------------------------------------------------- #

def sustituir(salida_to: Path, fuente_to: Path, unidades: set[str]) -> dict:
    """En cada archivo por unidad del TO: saca todas las líneas de las
    unidades afectadas y agrega, en su orden de origen, las líneas de esas
    unidades que trae la fuente re-extraída. El resto queda byte a byte."""
    out = {}
    for nombre in ARCHIVOS_POR_UNIDAD:
        base = leer_jsonl(salida_to / nombre)
        nuevos = [r for r in leer_jsonl(fuente_to / nombre) if r.get("chunk_id") in unidades]
        quedan = [r for r in base if r.get("chunk_id") not in unidades]
        escribir_jsonl(salida_to / nombre, quedan + nuevos)
        out[nombre] = {"lineas_base": len(base), "quitadas": len(base) - len(quedan),
                       "agregadas": len(nuevos)}
    return out


def demo_dirigida(trabajo: Path) -> dict:
    trabajo = _fuera_del_repo(trabajo)
    if trabajo.exists():
        shutil.rmtree(trabajo)
    trabajo.mkdir(parents=True)
    salida = trabajo / "salida_empalmada"
    shutil.copytree(BASE, salida)                                     # paso 1: copia de la base

    por_to: dict[str, set[str]] = {}
    for u in UNIDADES_REEXTRAIDAS:
        por_to.setdefault(u.split("::", 1)[0], set()).add(u)

    # Pasos 4 y 5: sustitución y E2 en código del TO afectado (runner_corpus).
    sys.path.insert(0, str(REX / "corpus_v2"))
    import runner_corpus as rc        # noqa: PLC0415 — solo import; configura al importarse
    import manifiesto_corpus          # noqa: PLC0415
    rc.configurar(manifiesto_corpus.cargar(MANIFIESTO_CORRIDA))
    sustitucion, e2 = {}, {}
    for to, us in sorted(por_to.items()):
        sustitucion[to] = sustituir(salida / to, REEXTRAIDAS / to, us)
        rc.compactar_e1(to, salida)
        rep = rc.cerrar_e2(to, salida)
        e2[to] = {"nodes_total": rep["nodes_total"], "edges_total": rep["edges_total"],
                  "sha256_grafo": sha256_archivo(salida / to / f"grafo_{to}.json"),
                  "sha256_grafo_sellado": sha256_archivo(REEXTRAIDAS / to / f"grafo_{to}.json")}
        e2[to]["igual_al_sellado"] = e2[to]["sha256_grafo"] == e2[to]["sha256_grafo_sellado"]

    # Paso 6: re-ensamblado, proceso aparte, sin bytecode.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    ens = {}
    for nombre, man in ENSAMBLADOS.items():
        dst = trabajo / nombre
        r = subprocess.run([sys.executable, "-B", str(ENSAMBLADOR), "--manifiesto", str(MANIF / man),
                            "--entrada", str(salida), "--salida", str(dst)],
                           cwd=str(REPO), env=env, capture_output=True, text=True, check=False)
        reg = {"codigo_salida": r.returncode}
        for rel in ("kg.json", "r1/kg.json"):
            obs, sel = dst / rel, T0 / nombre / rel
            reg[rel] = {"sha256": sha256_archivo(obs) if obs.exists() else None,
                        "sha256_sellado": sha256_archivo(sel)}
            reg[rel]["igual_al_sellado"] = reg[rel]["sha256"] == reg[rel]["sha256_sellado"]
        if r.returncode != 0:
            reg["stderr"] = r.stderr[-600:]
        ens[nombre] = reg
    iguales = sum(1 for v in ens.values() for k in ("kg.json", "r1/kg.json") if v[k]["igual_al_sellado"])
    return {"demostracion": "dirigida",
            "base": str(BASE.relative_to(REPO)), "fuente_reextraidas": str(REEXTRAIDAS.relative_to(REPO)),
            "unidades_reextraidas": list(UNIDADES_REEXTRAIDAS),
            "sustitucion": sustitucion, "e2_por_to_afectado": e2, "ensamblados": ens,
            "kg_iguales_al_sellado": f"{iguales} de {2 * len(ens)}",
            "veredicto": "OK" if iguales == 2 * len(ens) and all(v["igual_al_sellado"] for v in e2.values())
            else "FRENO"}


# ------------------------------------------------------------------------- #
# Renumeración: firma de contenido sin números                               #
# ------------------------------------------------------------------------- #

RE_NUMERAL = re.compile(r"^(\d+(?:\.\d+)*)\.?\s*")


def firma_contenido(c: dict) -> str:
    """Todo lo que entra al request de E1 salvo los números de punto: tipo,
    archivo, TO, título, marcas de E0, tipo y texto de cada bloque heredado y
    texto propio, con el numeral inicial quitado. Las remisiones internas a
    otros puntos ('ver punto 2.4') quedan: si la fuente las actualiza, el texto
    cambió de verdad."""
    def sin_num(t: str) -> str:
        return RE_NUMERAL.sub("", t, count=1)
    d = {"tipo": c.get("tipo"), "rol_bloque": c.get("rol_bloque"), "archivo": c["archivo"],
         "to": c["to"], "titulo": c["titulo"], "flags": c.get("flags"),
         "herencia": [(h["tipo"], sin_num(h["texto"])) for h in c.get("herencia", [])],
         "texto": sin_num(c["texto"])}
    return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def demo_renumeracion() -> dict:
    sys.path.insert(0, str(AQUI))
    import selftest_clave_cache as S   # noqa: PLC0415 — renumeración de V24 y armado de claves
    ar = S.Armado()
    to, antes = S.RENUMERACION["to"], S.RENUMERACION["insertar_antes_de"]
    chunks = S.cargar_chunks(to)
    padre, ultimo = antes.rsplit(".", 1)
    nivel = antes.count(".")
    hermanos = {".".join(u.split(".")[:nivel + 1]) for c in chunks
                for u in [c["unidad"]] + [h["unidad_origen"] for h in c.get("herencia", [])]
                if len(u.split(".")) > nivel and ".".join(u.split(".")[:nivel]) == padre}
    renum = sorted((h for h in hermanos if int(h.rsplit(".", 1)[1]) >= int(ultimo)),
                   key=lambda h: int(h.rsplit(".", 1)[1]))
    mapa = {h: f"{padre}.{int(h.rsplit('.', 1)[1]) + 1}" for h in renum}
    viejas = {firma_contenido(c): c["id"] for c in chunks}
    claves_viejas = {ar.k_e1(c) for c in chunks}
    nuevas = []
    for c in chunks:
        c2 = copy.deepcopy(c)
        c2["unidad"] = S._renombrar_unidad(c["unidad"], mapa)
        c2["texto"] = S._renombrar_texto(c["texto"], mapa)
        for h in c2.get("herencia", []):
            h["unidad_origen"] = S._renombrar_unidad(h["unidad_origen"], mapa)
            h["texto"] = S._renombrar_texto(h["texto"], mapa)
        nuevas.append(c2)
    miss = [c for c in nuevas if ar.k_e1(c) not in claves_viejas]
    solo_numero = [c for c in miss if firma_contenido(c) in viejas]
    contenido_nuevo = [c for c in miss if firma_contenido(c) not in viejas]
    colisiones = len(viejas) != len(chunks)
    return {"demostracion": "renumeracion", "to": to, "insertar_antes_de": antes,
            "puntos_renumerados": mapa, "unidades_del_to": len(chunks),
            "firmas_de_contenido_unicas_en_la_e0_vieja": len(viejas),
            "firmas_repetidas_en_la_e0_vieja": colisiones,
            "claves_e1_que_no_estan_en_la_cache_vieja": len(miss),
            "de_ellas_solo_cambio_de_numero": len(solo_numero),
            "de_ellas_contenido_nuevo": len(contenido_nuevo),
            "pares_viejo_nuevo_por_firma": sorted(
                [viejas[firma_contenido(c)], c["unidad"]] for c in solo_numero)[:50],
            "veredicto": "OK" if len(solo_numero) == len(miss) == 42 and not contenido_nuevo
            else "REVISAR"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("demo", choices=("dirigida", "renumeracion"))
    ap.add_argument("--trabajo", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.demo == "dirigida":
        if a.trabajo is None:
            ap.error("dirigida requiere --trabajo (fuera del repo)")
        res = demo_dirigida(a.trabajo)
    else:
        res = demo_renumeracion()
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8")
    resumen = {k: v for k, v in res.items() if k not in ("pares_viejo_nuevo_por_firma",)}
    print(json.dumps(resumen, ensure_ascii=False, indent=1)[:3000])
    return 0 if res["veredicto"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
