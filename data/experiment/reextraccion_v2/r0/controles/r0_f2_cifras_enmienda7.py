"""R0, fase 2: las cifras que manda declarar la enmienda 7, §1.5 (USD 0, sin red; solo lee).

Sobre la última versión de cada unidad en corpus_tanda0/salida_r2b/<to>/finales.jsonl de los diez TOs, en HEAD
(git show, antes del anexo) y ahora (después del anexo):
  - la cola de la tanda 0 r2b: unidades con estado cola_humana*, por estado (enmienda 5: 74 de 2.439, 43/29/2);
  - la población de U-LECTURA-ACEPTADAS (mandato, §2): unidades con estado completo_ok_directo, aceptado_con_residuales o
    aceptado_tras_reintento (2.366), por estrato con prompt_r2b.es_item sobre el chunk (ítems 1.003, no ítems 1.363);
  - las unidades de la muestra de L2 (lectura_aceptadas/sellos_l0.json) cuya última versión cambió;
  - las unidades de las 20 que salen de la cola y las que entran.
Uso (desde la raíz del repo): PYTHONDONTWRITEBYTECODE=1 <python> -B r0_f2_cifras_enmienda7.py --salida <json>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REX = AQUI.parents[1]
REPO = REX.parents[2]
sys.path.insert(0, str(REX / "e1_extractor"))
import prompt_r2b                                       # noqa: E402

TOS = ("pro", "cla", "ric", "cap", "ext", "ctacte", "lingob", "polcre", "pagjub", "docvig")
SALIDA = REX / "corpus_tanda0/salida_r2b"
E0 = REX / "e0_chunking/salida_tanda0_r2b"
ACEPTADOS = ("completo_ok_directo", "aceptado_con_residuales", "aceptado_tras_reintento")
LISTA = REPO / "data/experiment/e3_listas/o3/lista_unidades_afectadas_tanda0.json"
SELLOS_L0 = REPO / "data/experiment/lectura_aceptadas/sellos_l0.json"


def ultimas(texto: str) -> dict[str, dict]:
    out = {}
    for x in texto.splitlines():
        if x.strip():
            r = json.loads(x)
            out[r["chunk_id"]] = r
    return out


def head(p: Path) -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{p.relative_to(REPO).as_posix()}"],
                          capture_output=True, check=True, text=True).stdout


def cifras(fin: dict[str, dict], chunks: dict[str, dict]) -> dict:
    est = Counter(r["estado"] for r in fin.values())
    cola = {k: v for k, v in est.items() if k.startswith("cola_humana")}
    acep = [c for c, r in fin.items() if r["estado"] in ACEPTADOS]
    base = lambda c: chunks[c.split("::parte")[0]]          # una parte usa el chunk de su unidad (mandato de L2, §2)
    items = sum(1 for c in acep if prompt_r2b.es_item(base(c)))
    return {"unidades_en_finales": len(fin), "estados": dict(sorted(est.items())),
            "cola": {"total": sum(cola.values()), **dict(sorted(cola.items()))},
            "poblacion_l2": {"N": len(acep), "N1_item": items, "N2_no_item": len(acep) - items}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    chunks = {c["id"]: c for to in TOS for c in json.loads((E0 / f"chunks_{to}.json").read_text(encoding="utf-8"))}
    antes, ahora = {}, {}
    for to in TOS:
        p = SALIDA / to / "finales.jsonl"
        antes.update(ultimas(head(p)))
        ahora.update(ultimas(p.read_text(encoding="utf-8")))
    veinte = {u["chunk_id"] for u in json.loads(LISTA.read_text(encoding="utf-8"))["unidades"]}
    cambian = sorted(c for c in ahora if antes.get(c) != ahora[c])
    muestra = json.loads(SELLOS_L0.read_text(encoding="utf-8"))["sorteo"]["muestra"]     # {estrato: [{"id", ...}]}
    ids_muestra = {x["id"] for v in muestra.values() for x in v}
    res = {"e0_unidades": len(chunks), "antes_head": cifras(antes, chunks), "despues": cifras(ahora, chunks),
           "unidades_cuya_ultima_version_cambia": cambian, "todas_de_las_20": set(cambian) <= veinte,
           "salen_de_la_cola": sorted(c for c in cambian if antes[c]["estado"].startswith("cola")
                                      and not ahora[c]["estado"].startswith("cola")),
           "entran_a_la_cola": sorted(c for c in cambian if not antes[c]["estado"].startswith("cola")
                                      and ahora[c]["estado"].startswith("cola")),
           "siguen_en_la_cola": sorted(c for c in veinte if antes[c]["estado"].startswith("cola")
                                       and ahora[c]["estado"].startswith("cola")),
           "cambio_de_estado": {c: [antes[c]["estado"], antes[c]["n_reintentos"], ahora[c]["estado"],
                                    ahora[c]["n_reintentos"]] for c in sorted(veinte)},
           "muestra_l2": {"unidades": len(ids_muestra),
                          "de_las_20_en_la_muestra": sorted(ids_muestra & veinte),
                          "con_ultima_version_cambiada": sorted(ids_muestra & set(cambian))}}
    a.salida.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("antes_head", "despues", "salen_de_la_cola", "entran_a_la_cola",
                                          "siguen_en_la_cola", "muestra_l2", "todas_de_las_20")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
