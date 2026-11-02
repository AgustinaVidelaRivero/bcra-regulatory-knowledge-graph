#!/usr/bin/env python3
"""armar_entrada_B64.py (b64/v1, B6.4) — La entrada sellada de B6.4 (H-3), con la forma de b63/entrada_B63.json, armada por código
desde el archivo de las preguntas aprobadas, que recibe con su sha256 como argumentos. Ese archivo lo arma la mesa: una lista `preguntas`
en su raíz y, en cada una, `id`, `pregunta`, `criterios[*].{criterio, cita_textual, unidad}`, `tipo`, `to` y `anclas`. USD 0: no llama a
ningún modelo ni levanta nada.

De dónde sale cada campo:
  · preguntas: la ruta y el sha256 del archivo de las aprobadas; `ids_en_orden`, el orden del archivo; `esquema`, el de B6.3 (lista,
    id, pregunta, criterios, criterio y cita_textual);
  · k = 3 (pre-registro de B6.4, `55ee1a5a`, §4, como en B6.3);
  · R5 (32, 30 y 1,80), P y el pico de una sesión, el Neo4j de B6.3 con su huella, el venv del banco con su `pip freeze` y el juez de
    EV2 con sus sha256: los de b63/entrada_B63.json, tal cual (controlada antes por su sha256, `32e2b18c…`);
  · config_agentes: b64/v1/config_agentes_b64.json, con su sha256;
  · brazos: kg (rol «grafo», N7c+), kg_n7 (rol «grafo_sin_corregir», N7, D-10), fragmentos_hibrida («fragmentos_principal») y
    fragmentos_denso («fragmentos_denso»), cada uno con la config de su servidor, la que nombra config_agentes_b64.json, y su sha256;
    kg_n7 lleva además `marcas_d10`: la forma de cita del grafo (juez_b63.CITAS_POR_ROL["grafo"]), que su rol no trae, así sus marcas
    de D-10 son las del grafo;
  · tope_usd 144 y freno_usd 115 (§12), para los cuatro brazos, el agente y el juez juntos;
  · declarado: lo de B6.4 que se declara (D-4, D-10, el tope, el orden y, en la del humo, el humo).
Con --humo arma además la entrada del humo de D-5 (entrada_B64_humo.json, en la carpeta de --salida): la misma, con una sola pregunta, la
primera del orden, y k = 1: el humo es «1 pregunta por los 4 brazos» (§4), cuatro sesiones.
Frena con el 10, sin escribir nada, si el archivo no da su sha256, si no son 96 preguntas, si a una le falta un campo o lo trae vacío, si
un id se repite o no es un id que admita el runner, o si una salida ya existe y difiere. Nunca imprime ni copia el texto de una pregunta,
un criterio, una cita, una unidad ni un ancla: solo ids, cuentas y sha256.
Uso: python3 -I -B armar_entrada_B64.py --preguntas <archivo> --sha256-preguntas <hex> --salida <entrada_B64.json> [--humo]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b64/v1
BANCO_DIR = AQUI.parents[1]
REPO_DIR = BANCO_DIR.parents[2]                             # banco_mcp → experiment → data → la raíz del repo
CONFIG = AQUI / "config_agentes_b64.json"
ENTRADA_B63 = BANCO_DIR / "b63" / "entrada_B63.json"
ENTRADA_B63_SHA256 = "32e2b18cc2f5c96c67ed46d1f8b21af390d220a6f41b1102a47d3239c482bd54"
N_PREGUNTAS = 96
K = 3
TOPE_USD, FRENO_USD = 144.0, 115.0
DE_B63 = ("R5", "P", "pico_sesion_gb", "neo4j", "banco_venv_vector", "juez")
ESQUEMA = {"lista": "preguntas", "id": "id", "pregunta": "pregunta", "criterios": "criterios", "criterio": "criterio",
           "cita": "cita_textual"}
CAMPOS = ("id", "pregunta", "criterios", "tipo", "to", "anclas")
CAMPOS_CRITERIO = ("criterio", "cita_textual", "unidad")
ROLES = {"kg": "grafo", "kg_n7": "grafo_sin_corregir", "fragmentos_hibrida": "fragmentos_principal",
         "fragmentos_denso": "fragmentos_denso"}
MARCAS_D10_KG_N7 = [r"\bnodos?\b"]                           # juez_b63.CITAS_POR_ROL["grafo"] (lo controla el selftest)
ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")      # comun_b63.ID_VALIDO (el de agentes/lanzar_lote_paralelo.py)
HUMO = "entrada_B64_humo.json"


class Freno(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ruta_para_la_entrada(p: Path) -> str:
    """Relativa al repo si está en él; con «~/» si está en la carpeta personal (como la de B6.3); si no, absoluta."""
    p = p.resolve()
    if p.is_relative_to(REPO_DIR.resolve()):
        return str(p.relative_to(REPO_DIR.resolve()))
    if p.is_relative_to(Path.home().resolve()):
        return str(Path("~") / p.relative_to(Path.home().resolve()))
    return str(p)


def vacio(v) -> bool:
    return v is None or (isinstance(v, (str, list, dict)) and not (v.strip() if isinstance(v, str) else v))


def leer_preguntas(ruta: Path, sha: str) -> list[dict]:
    """Las preguntas aprobadas, controladas. Ningún mensaje trae su texto: solo ids, posiciones y nombres de campos."""
    if not ruta.is_file():
        raise Freno("no existe el archivo de las preguntas aprobadas")
    s = sha256_bytes(ruta.read_bytes())
    if s != sha:
        raise Freno(f"el archivo de las preguntas aprobadas da {s[:12]}…, no el sha256 del argumento {sha[:12]}…")
    d = json.loads(ruta.read_text(encoding="utf-8"))
    lista = d.get(ESQUEMA["lista"]) if isinstance(d, dict) else None
    if not isinstance(lista, list):
        raise Freno("el archivo no trae una lista `preguntas` en su raíz")
    if len(lista) != N_PREGUNTAS:
        raise Freno(f"son {len(lista)} preguntas, no {N_PREGUNTAS}")
    vistos: set[str] = set()
    for i, q in enumerate(lista, 1):
        if not isinstance(q, dict):
            raise Freno(f"la pregunta {i} del archivo no es un objeto")
        qid = q.get("id")
        quien = f"la pregunta {i} ({qid})" if isinstance(qid, str) and ID_VALIDO.match(qid) else f"la pregunta {i}"
        for c in CAMPOS:
            if c not in q or vacio(q[c]):
                raise Freno(f"a {quien} le falta `{c}` o lo trae vacío")
        if not isinstance(qid, str) or not ID_VALIDO.match(qid):
            raise Freno(f"la pregunta {i} trae un id que el runner no admite")
        if qid in vistos:
            raise Freno(f"el id {qid} se repite")
        vistos.add(qid)
        if not isinstance(q["pregunta"], str) or not isinstance(q["criterios"], list):
            raise Freno(f"{quien}: `pregunta` no es un texto o `criterios` no es una lista")
        for j, c in enumerate(q["criterios"], 1):
            if not isinstance(c, dict):
                raise Freno(f"{quien}: el criterio {j} no es un objeto")
            for k in CAMPOS_CRITERIO:
                if k not in c or vacio(c[k]):
                    raise Freno(f"{quien}: al criterio {j} le falta `{k}` o lo trae vacío")
            if not isinstance(c["criterio"], str) or not isinstance(c["cita_textual"], str):
                raise Freno(f"{quien}: el criterio {j} no trae su texto o su cita como texto")
    return lista


def armar(ruta: Path, sha: str) -> tuple[dict, dict, dict]:
    """(entrada, entrada del humo, resumen sin texto)."""
    lista = leer_preguntas(ruta, sha)
    if sha256_bytes(ENTRADA_B63.read_bytes()) != ENTRADA_B63_SHA256:
        raise Freno("b63/entrada_B63.json no da su sha256")
    b63 = json.loads(ENTRADA_B63.read_text(encoding="utf-8"))
    if not CONFIG.is_file():
        raise Freno("no existe config_agentes_b64.json (lo arma armar_config_agentes_b64.py)")
    cfg_bytes = CONFIG.read_bytes()
    cfg = json.loads(cfg_bytes.decode("utf-8"))
    if set(cfg["brazos"]) != set(ROLES):
        raise Freno(f"los brazos de config_agentes_b64.json son {sorted(cfg['brazos'])}, no {sorted(ROLES)}")
    brazos = {}
    for b, rol in ROLES.items():
        rel = cfg["brazos"][b]["config_servidor"]
        s = sha256_bytes((BANCO_DIR / rel).read_bytes())
        if s != cfg["sha256_de_cada_archivo"].get(rel):
            raise Freno(f"la config del servidor de {b} no da el sha256 de config_agentes_b64.json")
        brazos[b] = {"rol": rol, "config_servidor": {"ruta": "data/experiment/banco_mcp/" + rel, "sha256": s}}
    for b in ("fragmentos_hibrida", "fragmentos_denso"):
        if brazos[b] != b63["brazos"][b]:
            raise Freno(f"el brazo {b} no es el de la entrada de B6.3")
    if brazos["kg_n7"]["config_servidor"] != b63["brazos"]["kg"]["config_servidor"]:
        raise Freno("la config del servidor de kg_n7 no es la del grafo de B6.3")
    brazos["kg_n7"]["marcas_d10"] = list(MARCAS_D10_KG_N7)
    ids = [q["id"] for q in lista]
    entrada = {
        "unidad": "B6.4: la entrada sellada (H-3), con las 96 preguntas aprobadas, los cuatro brazos, k, el tope y el freno "
                  "(b64/v1/armar_entrada_B64.py)",
        "preguntas": {"ruta": ruta_para_la_entrada(ruta), "sha256": sha, "ids_en_orden": ids, "esquema": dict(ESQUEMA)},
        "k": K,
        "config_agentes": {"ruta": str(CONFIG.resolve().relative_to(REPO_DIR.resolve())), "sha256": sha256_bytes(cfg_bytes)},
        "brazos": brazos,
        **{c: b63[c] for c in ("R5",)},
        "tope_usd": TOPE_USD, "freno_usd": FRENO_USD,
        **{c: b63[c] for c in ("P", "pico_sesion_gb", "neo4j", "banco_venv_vector", "juez")},
        "declarado": {
            "preregistro": {"ruta": "docs/preregistro_B6_4_evaluacion_confirmatoria_varios_puntos.md", "firmado_en": "55ee1a5a"},
            "de_la_entrada_de_B63": {"ruta": "data/experiment/banco_mcp/b63/entrada_B63.json", "sha256": ENTRADA_B63_SHA256,
                                     "campos": list(DE_B63) + ["brazos.fragmentos_hibrida", "brazos.fragmentos_denso",
                                                               "brazos.kg.config_servidor (en kg_n7)"]},
            "k": "3, como en B6.3 (pre-registro de B6.4, §4)",
            "tope": "USD 144 con el freno en 115, para los cuatro brazos, el agente y el juez juntos (§12)",
            "D-4": "las tres etiquetas del runner de B6.3, tal cual: la semilla del orden B63:orden_corridas:v1, el prefijo del id de "
                   "sesión B63- y la sal del id opaco del juez B63:id_opaco_juez:v1; el orden y los ids salen distintos porque llevan "
                   "el id de la pregunta de B6.4",
            "brazo_del_grafo": "kg: N7c+, la configuración que adoptó la regla de B2 (H-7 y H-8; nota al pie del pre-registro)",
            "D-10": "kg_n7: el grafo sin corregir (N7, el brazo kg de B6.3), cuarto brazo, fuera de Holm; sus marcas de D-10 son las "
                    "del grafo: sus herramientas, de config_agentes_b64.json, y la forma de cita del grafo, en marcas_d10",
            "orden_de_las_preguntas": "el del archivo de las preguntas aprobadas"}}
    humo = json.loads(json.dumps(entrada))
    humo["unidad"] = ("B6.4: la entrada del humo de D-5, con la primera pregunta del orden de las aprobadas y los cuatro brazos, una vez "
                      "(b64/v1/armar_entrada_B64.py --humo)")
    humo["preguntas"]["ids_en_orden"] = ids[:1]
    humo["k"] = 1
    humo["declarado"]["humo"] = ("D-5: un humo pago de 1 pregunta por los 4 brazos (pre-registro, §4: unos USD 0,35, NO VERIFICADO): "
                                 "la primera del orden de las aprobadas, k = 1, cuatro sesiones; lo demás, como la entrada de B6.4")
    resumen = {"preguntas": len(lista), "por_tipo": dict(sorted(Counter(str(q["tipo"]) for q in lista).items())),
               "criterios": sum(len(q["criterios"]) for q in lista), "sha256_preguntas": sha,
               "brazos": {b: x["rol"] for b, x in brazos.items()}, "k": K, "tope_usd": TOPE_USD, "freno_usd": FRENO_USD}
    return entrada, humo, resumen


def escribir(p: Path, obj: dict) -> str:
    nuevo = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
    if p.exists() and p.read_text(encoding="utf-8") != nuevo:
        raise Freno(f"{p.name} ya existe y difiere de la que se arma")
    return nuevo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preguntas", type=Path, required=True)
    ap.add_argument("--sha256-preguntas", required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--humo", action="store_true")
    a = ap.parse_args(argv)
    try:
        entrada, humo, resumen = armar(a.preguntas, a.sha256_preguntas)
        salidas = [(a.salida, entrada)] + ([(a.salida.parent / HUMO, humo)] if a.humo else [])
        textos = [(p, escribir(p, obj)) for p, obj in salidas]
    except Freno as ex:
        print(f"FRENO (USD 0): {ex}")
        return 10
    for p, t in textos:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
        resumen[p.stem] = {"ruta": ruta_para_la_entrada(p), "sha256": sha256_bytes(t.encode("utf-8"))}
    if a.humo:
        resumen[Path(HUMO).stem]["ids_en_orden"] = humo["preguntas"]["ids_en_orden"]
        resumen[Path(HUMO).stem]["k"] = humo["k"]
    print(json.dumps(resumen, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
