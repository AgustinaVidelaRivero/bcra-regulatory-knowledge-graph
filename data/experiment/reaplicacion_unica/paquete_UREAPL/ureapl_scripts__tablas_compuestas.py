"""U-REAPL: la tabla compuesta de ids, por grafo (mandato U-REAPL, §3): id del sello → id del grafo evaluado, con la pieza que lo
cambió, compuesta con las tablas de los pasos (las de `medir_paso.py`, en --trabajo). USD 0, sin API.

Escribe en --salida:
  - `NO_ABRIR_tabla_ids_compuesta_<grafo>.json`: los ids tal cual (no se vuelve a abrir);
  - `tabla_ids_compuesta_<grafo>_por_codigo.json`: código del sello → código del evaluado, con las piezas;
  - `tablas_compuestas.json`: las cuentas (por pieza y por tipo), los ids del sello sin nodo en el evaluado, las dos listas del censo
    reexpresadas y el control del cegamiento (un nodo de una unidad de la muestra sigue cegado con su id del evaluado: sí o no).
Uso, desde la raíz de la copia: <python> -B tablas_compuestas.py --trabajo T --pasos paso2,paso3,paso4,paso5 --sello <dir r2 del paso 1>
       --evaluado <dir r2 del último paso> --grafo con_cola|sin_cola --no-unir <json> --nodos-no-unir <json> --salida S
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import muestra_memoria as MM  # noqa: E402

PIEZA = {"D": "D", "claves": "las claves", "C1": "C1", "remisiones": "las remisiones"}


def cod(i: str) -> str:
    return hashlib.sha256(i.encode("utf-8")).hexdigest()[:12]


def escribir(p: Path, obj) -> str:
    t = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    p.write_text(t, encoding="utf-8")
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--pasos", required=True)
    ap.add_argument("--sello", type=Path, required=True)
    ap.add_argument("--evaluado", type=Path, required=True)
    ap.add_argument("--grafo", required=True)
    ap.add_argument("--no-unir", dest="no_unir", type=Path, required=True)
    ap.add_argument("--nodos-no-unir", dest="nodos_no_unir", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)
    S = json.loads((a.sello / "kg.json").read_text(encoding="utf-8"))
    E = json.loads((a.evaluado / "kg.json").read_text(encoding="utf-8"))
    NS, NE = {n["id"]: n for n in S["nodes"]}, {n["id"]: n for n in E["nodes"]}
    tablas = []
    for p in a.pasos.split(","):
        t = json.loads((a.trabajo / f"{p}_{a.grafo}.json").read_text(encoding="utf-8"))
        tablas.append((t["pieza"], t["tabla"]))
    filas, sin_nodo = [], collections.Counter()
    for i in NS:
        j, piezas = i, []
        for pieza, tb in tablas:
            if j in tb:
                j, piezas = tb[j], piezas + [pieza]
        if j not in NE:
            sin_nodo[NS[i]["type"]] += 1
        if piezas:
            filas.append({"id_sello": i, "id_evaluado": j, "piezas": piezas})
    filas.sort(key=lambda f: f["id_sello"])
    escribir(a.salida / f"NO_ABRIR_tabla_ids_compuesta_{a.grafo}.json", {"grafo": a.grafo, "filas": filas})
    mapa = {f["id_sello"]: f["id_evaluado"] for f in filas}
    m = MM.muestra()
    ciegos_S, ciegos_E = MM.nodos_cegados(S, m), MM.nodos_cegados(E, m)
    cg = ciegos_S | ciegos_E

    def codv(i: str) -> str:
        return "cegado" if i in cg else cod(i)
    sha_cod = escribir(a.salida / f"tabla_ids_compuesta_{a.grafo}_por_codigo.json",
                       [[codv(f["id_sello"]), codv(f["id_evaluado"]), [PIEZA[x] for x in f["piezas"]]] for f in filas])
    siguen = all(mapa.get(i, i) in ciegos_E for i in ciegos_S if mapa.get(i, i) in NE)
    no_unir = json.loads(a.no_unir.read_text(encoding="utf-8"))
    nodos_no_unir = json.loads(a.nodos_no_unir.read_text(encoding="utf-8"))
    res = {"grafo": a.grafo, "filas": len(filas),
           "por_pieza": dict(collections.Counter("+".join(f["piezas"]) for f in filas)),
           "por_tipo": dict(collections.Counter(NS[f["id_sello"]]["type"] for f in filas)),
           "ids_del_sello_sin_nodo_en_el_evaluado_por_tipo": dict(sin_nodo),
           "sha256_por_codigo": sha_cod,
           "filas_por_codigo_con_un_nodo_cegado": sum(1 for f in filas if f["id_sello"] in cg or f["id_evaluado"] in cg),
           "listas_del_censo_reexpresadas": {
               "codigos_que_no_se_unen": {"antes": len(no_unir.get("no_unir", [])), "despues": len(no_unir.get("no_unir", []))},
               "nodos_que_no_se_unen": {"antes": len(nodos_no_unir), "despues": len([mapa.get(i, i) for i in nodos_no_unir])}},
           "cegamiento": {"nodos_cegados_del_sello_que_siguen_cegados_en_el_evaluado": "sí" if siguen else "no"}}
    sha = escribir(a.salida / f"tablas_compuestas_{a.grafo}.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "listas_del_censo_reexpresadas"}, ensure_ascii=False), sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
