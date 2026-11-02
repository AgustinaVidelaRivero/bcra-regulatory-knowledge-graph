#!/usr/bin/env python3
"""herramientas_b64.py (b64/v1/seco, B6.4) — Lo que usan el selftest y la corrida en seco del runner de B6.4 (b64/v1). USD 0, sin
ningún dato real: todo es de juguete.

Lo de B6.3 se importa sin copiarlo: b63/v2/b2/seco/herramientas_b2.py, cargado por su ruta (como claude_falso_b63.py carga el CLI falso
del banco), con los CLI falsos de la máquina, el cliente falso del juez, el juez simulado (el SDK real con un transporte simulado, sin
red), el doble del Neo4j, los procesos de prueba propios, las ventanas de 30 caracteres y las claves de relleno. Lo nuevo:
  · entrada_b64: una entrada sellada DE JUGUETE con la forma de la de B6.4 (la de armar_entrada_B64.py: el esquema de B6.3, los cuatro
    roles y `marcas_d10` en kg_n7), sobre la configuración de juguete de cuatro brazos de esta carpeta (config_agentes_b64_juguete.json:
    kg, kg_n7, fragmentos_bm25 y fragmentos_denso; los nombres de juguete de B6.3 más el cuarto, para que los planes del CLI falso de
    B6.3, que nombran kg y fragmentos_bm25, sigan valiendo);
  · a_esquema_b64: pasa un archivo de preguntas de juguete de B6.3 (el esquema de EV2, gold.criterios) al de las aprobadas de B6.4
    (criterios en la raíz de cada pregunta, con su unidad, y tipo, to y anclas), con el mismo texto: así las corridas usan el esquema de
    la entrada de B6.4;
  · aprobadas_de_juguete: un archivo de preguntas aprobadas DE JUGUETE, con la forma que arma la mesa (96, o las que se pidan), para
    armar_entrada_B64.py.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                       # b64/v1/seco
V1 = AQUI.parent
BANCO_DIR = V1.parents[1]
B63 = BANCO_DIR / "b63"
REPO = BANCO_DIR.parents[2]                                 # la raíz del repo (banco_mcp → experiment → data → raíz)
_spec = importlib.util.spec_from_file_location("herramientas_b2", B63 / "v2" / "b2" / "seco" / "herramientas_b2.py")
H2 = importlib.util.module_from_spec(_spec)
sys.modules["herramientas_b2"] = H2
_spec.loader.exec_module(H2)                                 # lo de B6.3: solo import

sha, rel, bin_falso, ClienteJuez, juez_simulado = H2.sha, H2.rel, H2.bin_falso, H2.ClienteJuez, H2.juez_simulado
Neo4jDoble, Prueba, ProcesoConNombre, ventanas = H2.Neo4jDoble, H2.Prueba, H2.ProcesoConNombre, H2.ventanas
VENV_VECTOR, PIP_FREEZE_SELLADO, HUELLA_B63 = H2.VENV_VECTOR, H2.PIP_FREEZE_SELLADO, H2.HUELLA_B63
CLAVE_INVALIDA_DE_RELLENO, CLAVE_DE_RELLENO, MARCA_COMILLAS = H2.CLAVE_INVALIDA_DE_RELLENO, H2.CLAVE_DE_RELLENO, H2.MARCA_COMILLAS
CONFIG_JUGUETE = AQUI / "config_agentes_b64_juguete.json"
BRAZOS_JUGUETE = {"kg": "grafo", "kg_n7": "grafo_sin_corregir", "fragmentos_bm25": "fragmentos_principal",
                  "fragmentos_denso": "fragmentos_denso"}
ESQUEMA_B64 = {"lista": "preguntas", "id": "id", "pregunta": "pregunta", "criterios": "criterios", "criterio": "criterio",
               "cita": "cita_textual"}                       # el de armar_entrada_B64.ESQUEMA (lo controlan el selftest y el seco)
MARCAS_D10_GRAFO = [r"\bnodos?\b"]                           # las del grafo, como armar_entrada_B64.MARCAS_D10_KG_N7
TIPOS_JUGUETE = ("agregacion_de_juguete", "remision_de_juguete", "condicion_de_juguete")


def entrada_b64(tmp: Path, nombre: str, ids: list[str], *, preguntas: Path, k: int = 1, P: int = 1, pico: float = 3.0,
                tope: float = 50.0, freno: float = 40.0, mutar=None) -> tuple[Path, str]:
    """Una entrada sellada DE JUGUETE de B6.4, sobre la configuración de juguete de cuatro brazos y las preguntas que se pidan (con el
    esquema de B6.4)."""
    import importlib
    K = importlib.import_module("comun_b63")
    ev2 = BANCO_DIR.parent / "ev2_juez"
    cfg = json.loads(CONFIG_JUGUETE.read_text(encoding="utf-8"))
    brazos = {}
    for b, r in BRAZOS_JUGUETE.items():
        cs = BANCO_DIR / cfg["brazos"][b]["config_servidor"]
        brazos[b] = {"rol": r, "config_servidor": {"ruta": rel(cs), "sha256": sha(cs)}}
    brazos["kg_n7"]["marcas_d10"] = list(MARCAS_D10_GRAFO)
    e = {"unidad": "B6.4, selftest y seco: entrada sellada DE JUGUETE",
         "preguntas": {"ruta": str(Path(preguntas).resolve()), "sha256": sha(preguntas), "ids_en_orden": ids, "esquema": dict(ESQUEMA_B64)},
         "k": k, "config_agentes": {"ruta": rel(CONFIG_JUGUETE), "sha256": sha(CONFIG_JUGUETE)}, "brazos": brazos,
         "R5": {"max_turns": 32, "tope_tool_calls_prompt": 30, "max_budget_usd": 1.8}, "tope_usd": tope, "freno_usd": freno,
         "P": P, "pico_sesion_gb": pico, "neo4j": {"uri": "bolt://127.0.0.1:47687", "huella_contenido": HUELLA_B63},
         "banco_venv_vector": {"ruta": VENV_VECTOR, "python": K.version_python(K.ruta_de_rel(VENV_VECTOR)) or "3.12",
                               "pip_freeze_sha256": PIP_FREEZE_SELLADO},
         "juez": {"archivos": [{"ruta": rel(ev2 / f), "sha256": sha(ev2 / f)} for f in ("juez.py", "mapping.py", "prompt_juez_v1.md")]}}
    if mutar:
        mutar(e)
    p = tmp / f"entrada_{nombre}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p, sha(p)


def a_esquema_b64(origen: Path, destino: Path) -> Path:
    """Las preguntas de juguete de B6.3 (gold.criterios) con el esquema de las aprobadas de B6.4, el mismo texto."""
    d = json.loads(Path(origen).read_text(encoding="utf-8"))
    out = []
    for i, q in enumerate(d["preguntas"]):
        out.append({"id": q["id"], "pregunta": q["pregunta"],
                    "criterios": [{"criterio": c["criterio"], "cita_textual": c["cita_textual"], "unidad": f"JUG-{q['id']}-u{j}"}
                                  for j, c in enumerate(q["gold"]["criterios"], 1)],
                    "tipo": TIPOS_JUGUETE[i % 3], "to": "TO de juguete", "anclas": [f"JUG-{q['id']}-u1"]})
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"preguntas": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return destino


def aprobadas_de_juguete(destino: Path, n: int = 96, *, mutar=None) -> tuple[Path, str]:
    """Un archivo de preguntas aprobadas DE JUGUETE con la forma que arma la mesa: n preguntas, 32 de cada tipo de juguete, en un orden
    que no es el alfabético de sus ids (el orden del archivo es el de la entrada)."""
    qs = []
    for i in range(n):
        qid = f"JUG64-O{i % 6 + 1}-L{i // 6 + 1:02d}"
        qs.append({"id": qid, "pregunta": f"Pregunta de juguete {i + 1} de B6.4, sobre una norma inventada [[b63:normal]]",
                   "criterios": [{"criterio": f"criterio de juguete {j} de la pregunta {i + 1}",
                                  "cita_textual": f"cita de juguete {j} de la pregunta {i + 1}", "unidad": f"JUG-{i + 1}-u{j}"}
                                 for j in (1, 2, 3)],
                   "tipo": TIPOS_JUGUETE[i % 3], "to": f"TO de juguete {i % 4 + 1}",
                   "anclas": [{"rol": "ancla", "unidad": f"JUG-{i + 1}-u1"}, {"rol": "otro_punto", "unidad": f"JUG-{i + 1}-u2"}]})
    d = {"unidad": "B6.4, selftest y seco: preguntas aprobadas DE JUGUETE (no es ninguna pregunta real)", "preguntas": qs}
    if mutar:
        mutar(d)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return destino, hashlib.sha256(destino.read_bytes()).hexdigest()
