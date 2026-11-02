"""U-REAPL, cegamiento (mandato, §7; §7 bis de U-PROC-HERENCIA): la muestra de U-MED-VERIF-FICHAS, solo en memoria.

El orden del sorteo (`NO_ABRIR_sorteo_U-MED-VERIF.json`, el único NO_ABRIR_ que se abre), la lista de exclusión (los ids de
`unidades_a_la_vista_T4.json` en `0c2befad`, leída con `git show`, más las 7 unidades de la mesa) y las 30 primeras del orden que no
están en ella, con `ids_en` y `listas_de_ids` del script del censo de la mesa (`censo_c1_con_control_de_la_muestra_mesa.py`), que se
toman de su fuente por su árbol de sintaxis, sin ejecutar el resto del script. Ninguna función de este módulo imprime ni escribe la
muestra ni su tamaño: devuelven un conjunto que vive en memoria.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SORTEO = Path(__import__("os").environ.get("BCRA_KG_FUERA_DEL_REPO") or Path(__file__).resolve().parents[4] / "fuera_del_repo") / "tesis_escritura/U-MED-VERIF/fichas/NO_ABRIR_sorteo_U-MED-VERIF.json"
CENSO = (Path(__import__("os").environ.get("BCRA_KG_FUERA_DEL_REPO") or Path(__file__).resolve().parents[4] / "fuera_del_repo") / ""
         "hoja_de_ruta_tanda1_mesa/decisiones_239_mesa/censo_c1/censo_c1_con_control_de_la_muestra_mesa.py")
SHA_SORTEO = "e27796ce9eecafc6aeda66898a69d86099e133e5069e9a6f3d6113d40d2f8e32"
SHA_T4 = "5ec9753dc9f8caa51a37a884c542efe38416a41d575a030b24ababbf9c60b17d"
SHA_CENSO = "c9d41233c51e52f92efbaa60330330656248acccd6dc0424340349f3c2a81ee5"
MESA = ["depaho::3.12.3.2", "depaho::3.12.3.3", "snp_tr::2.2.11", "depaho::4.4.5.1", "depaho::4.4.5.2", "efemin::2.4::cierre",
        "efemin::3.1.4"]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _funciones_del_censo() -> dict:
    fuente = CENSO.read_bytes()
    if _sha(fuente) != SHA_CENSO:
        raise SystemExit("FRENO: el script del censo no es el sellado")
    arbol = ast.parse(fuente.decode("utf-8"))
    partes = [n for n in arbol.body if (isinstance(n, ast.FunctionDef) and n.name in ("ids_en", "listas_de_ids"))
              or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ID" for t in n.targets))]
    if len(partes) != 3:
        raise SystemExit("FRENO: no ubico ids_en, listas_de_ids e ID en el script del censo")
    ns = {"re": re}
    exec(compile(ast.Module(body=partes, type_ignores=[]), str(CENSO), "exec"), ns)  # noqa: S102
    return ns


def muestra() -> frozenset:
    ns = _funciones_del_censo()
    bs = SORTEO.read_bytes()
    if _sha(bs) != SHA_SORTEO:
        raise SystemExit("FRENO: el sorteo no es el sellado")
    cands = ns["listas_de_ids"](json.loads(bs), [])
    if not cands:
        raise SystemExit("FRENO: no ubico el orden del sorteo")
    orden = max(cands, key=len)
    if len(set(orden)) != len(orden):
        raise SystemExit("FRENO: el orden tiene ids repetidos")
    t4 = subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), "show",
                         "0c2befad:data/experiment/tanda1/t3/muestras/unidades_a_la_vista_T4.json"],
                        capture_output=True, check=True).stdout
    if _sha(t4) != SHA_T4:
        raise SystemExit("FRENO: la lista de exclusión no es la del despacho")
    excl = set(ns["ids_en"](json.loads(t4), [])) | set(MESA)
    m = [u for u in orden if u not in excl][:30]
    if len(m) != 30:
        raise SystemExit("FRENO: la muestra recalculada no da la cuenta del despacho")
    return frozenset(m)


def en_muestra(chunk_id, m: frozenset) -> bool:
    """La unidad o una de sus partes (el id de la unidad más «::»): de más, nunca de menos."""
    if not isinstance(chunk_id, str):
        return False
    return chunk_id in m or any(chunk_id.startswith(u + "::") for u in m)


def nodos_cegados(kg: dict, m: frozenset) -> set:
    """Los nodos con alguna procedencia en una unidad de la muestra (en cualquier grafo y con cualquier id)."""
    return {n["id"] for n in kg["nodes"] if any(en_muestra((p or {}).get("chunk_id"), m) for p in (n.get("provenances") or []))
            or en_muestra((n.get("provenance") or {}).get("chunk_id"), m)}
