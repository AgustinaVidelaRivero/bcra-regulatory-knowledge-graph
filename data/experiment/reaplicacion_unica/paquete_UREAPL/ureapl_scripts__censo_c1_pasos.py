"""U-REAPL: el censo de C1 en los pasos (mandato U-REAPL, §3; despacho, punto 7). USD 0, sin API.

Las colisiones son las del C1 sellado, con `cuenta_C` y `codigo_normalizado` de `med_desamb/parte2/tamanos_desamb_mesa.py` y
`e2_lib` de la copia (el código de HEAD), como las arma el script del censo de la mesa (`censo_c1_con_control_de_la_muestra_mesa.py`,
`c9d41233…`), con su regla de la muestra en memoria (una procedencia de una unidad de la muestra no cuenta como visible). Controla:
  - que las colisiones (código normalizado y nodos) del paso 2 son las del paso 1, en los dos grafos (D no toca ninguna Comunicacion);
  - que el sello sin cola da las cuentas de `conteos_acumulado_tres_tandas_sin_cola.json` (`5e609b56…`);
  - con --uniones (el `uniones_c1.json` del paso 4) y --tablas, que las uniones son las colisiones del censo, código por código y nodo por
    nodo, con los ids llevados por las tablas de los pasos 2 y 3.
Escribe en --salida `censo_c1_pasos.json` (cuentas y, por colisión, el sha256[:12] del código normalizado y los códigos de sus nodos).

Uso, desde la raíz de la copia: <python> -B censo_c1_pasos.py --kg <etiqueta>=<kg.json> [...] --conteos <json> --salida <dir>
       [--uniones <etiqueta del kg>=<uniones_c1.json> --tablas <trabajo paso2>,<trabajo paso3>]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import muestra_memoria as MM  # noqa: E402

T_PATH = Path("data/experiment/med_desamb/parte2/tamanos_desamb_mesa.py")
E2_DIR = Path("data/experiment/reextraccion_v2/e2_reduce")


def cod(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()[:12]


def cargar_T():
    s = importlib.util.spec_from_file_location("tamanos_desamb_mesa", str(T_PATH))
    T = importlib.util.module_from_spec(s)
    s.loader.exec_module(T)
    return T, T.cargar_e2lib(str(E2_DIR))


def censo(T, E, kb: bytes, m: frozenset) -> tuple[dict, list]:
    kg = json.loads(kb)
    C = T.cuenta_C(E, [(hashlib.sha256(kb).hexdigest()[:8], kg)])
    nodos = {n["id"]: n for n in kg["nodes"]}
    cols = C["colisiones_para_leer"]
    toca_n, no_dec, ocultos, para_leer = 0, 0, [], 0
    for c in cols:
        filas_v, tos_v, toca = [], set(), False
        for f in c["filas"]:
            n = nodos.get(f["id"], {})
            prov = n.get("provenances") or []
            vis = [p for p in prov if p.get("chunk_id") not in m]
            if len(vis) < len(prov):
                toca = True
            if prov and not vis:
                ocultos.append(f["id"])
                continue
            filas_v.append(f)
            tos_v |= {p.get("to") for p in vis if p.get("to")}
        toca_n += toca
        era = len(c["filas"]) >= 2
        if toca and (not filas_v or (era and (len(filas_v) < 2 or len(tos_v) < 2))):
            no_dec += 1
            ocultos += [f["id"] for f in filas_v]
            continue
        para_leer += 1
    out = {"kg_sha256": hashlib.sha256(kb).hexdigest(), "nodos_comunicacion": C["nodos_comunicacion"], "colisiones": len(cols),
           "nodos_en_colisiones": sum(c["nodos"] for c in cols),
           "colisiones_con_2_nodos_o_mas": sum(1 for c in cols if c["nodos"] >= 2),
           "documentos_por_colision_max": max((len(c["tos"]) for c in cols), default=0),
           "nodos_por_colision_max": max((c["nodos"] for c in cols), default=0),
           "colisiones_que_tocan_la_muestra": toca_n, "colisiones_que_no_se_pueden_decidir_sin_la_muestra": no_dec,
           "nodos_que_no_se_unen_por_la_muestra": len(ocultos), "colisiones_para_leer": para_leer}
    lista = [(c["codigo_normalizado"], sorted(f["id"] for f in c["filas"])) for c in cols]
    return out, lista


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg", action="append", required=True)
    ap.add_argument("--conteos", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--uniones", default=None)
    ap.add_argument("--tablas", default=None)
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)
    T, E = cargar_T()
    m = MM.muestra()
    res, listas = {}, {}
    for x in a.kg:
        et, p = x.split("=", 1)
        res[et], listas[et] = censo(T, E, Path(p).read_bytes(), m)
    out = {"conteos": res}
    comp = {}
    for g in ("con_cola", "sin_cola"):
        if f"paso1_{g}" in listas and f"paso2_{g}" in listas:
            comp[g] = listas[f"paso1_{g}"] == listas[f"paso2_{g}"]
    out["colisiones_del_paso_2_iguales_a_las_del_paso_1"] = comp
    esperado = json.loads(a.conteos.read_text(encoding="utf-8"))
    if "paso1_sin_cola" in res:
        out["sello_sin_cola_igual_a_los_conteos_del_censo"] = {k: [esperado[k], res["paso1_sin_cola"].get(k)] for k in esperado
                                                              if esperado[k] != res["paso1_sin_cola"].get(k)} or True
    out["colisiones_por_codigo"] = {et: [{"codigo_normalizado_sha12": cod(c), "nodos": [cod(i) for i in ids]} for c, ids in li]
                                    for et, li in listas.items()}
    if a.uniones:
        et, p = a.uniones.split("=", 1)
        un = json.loads(Path(p).read_text(encoding="utf-8"))
        mapa: dict = {}
        for t in (a.tablas or "").split(","):
            if t:
                tb = json.loads(Path(t).read_text(encoding="utf-8"))["tabla"]
                mapa = {k: tb.get(v, v) for k, v in mapa.items()}
                for k, v in tb.items():
                    mapa.setdefault(k, v)
        cen = {c: sorted(mapa.get(i, i) for i in ids) for c, ids in listas[et]}
        uni = {}
        for u in un:
            ids = sorted(x["id_con_la_guarda"] for x in u["nodos"])
            uni[u.get("codigo_normalizado") or u.get("codigo")] = ids
        out["uniones_contra_el_censo"] = {
            "uniones": len(uni), "colisiones_del_censo": len(cen),
            "mismos_codigos": sorted(cod(str(k)) for k in uni) == sorted(cod(str(k)) for k in cen),
            "mismos_nodos": {cod(str(k)): uni.get(k) == cen.get(k) for k in set(uni) | set(cen)},
            "claves_de_una_union": sorted({k for u in un for k in u.keys()})}
    t = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    (a.salida / "censo_c1_pasos.json").write_text(t, encoding="utf-8")
    print(json.dumps({"conteos": {k: {kk: v[kk] for kk in ("nodos_comunicacion", "colisiones", "nodos_en_colisiones",
                                                            "colisiones_que_tocan_la_muestra")} for k, v in res.items()},
                      "paso2_igual_paso1": comp, "sello_sin_cola_igual": out.get("sello_sin_cola_igual_a_los_conteos_del_censo"),
                      "uniones": {k: v for k, v in (out.get("uniones_contra_el_censo") or {}).items() if k != "mismos_nodos"},
                      "uniones_mismos_nodos": all((out.get("uniones_contra_el_censo") or {}).get("mismos_nodos", {}).values()),
                      "sha256": hashlib.sha256(t.encode()).hexdigest()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
