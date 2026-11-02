"""Punto 1 de S2 (U-SEG-OFICIAL): las diferencias de la E0 corregida contra `b584_particion/`, con las clases del
control de R5 y la atribución por historia de lo que R5 deja en «otra» (solo lectura).

Uso: python -B atribuir_particion_S2.py --r5 <json de r5_escalera_particion.py --comparar --atribuir sobre la E0 corregida>
       --r5-cierre <el mismo control sobre la E0 de e1c9456> --e0 <E0 corregida> --e0-cierre <E0 de e1c9456>
       --e0-c2 <E0 de 9f6361e6> --raiz <copia del repo> --out <json>

El control de R5 (`data/experiment/r2_codigo/r5_escalera_particion.py`, sin editar) clasifica las diferencias de ids
(L, partición no aplicada por tabla, «otra» con su causa K / pie / K y pie / otra) y de texto (tablas, pies, K, pies y K,
arrastre, otra). Su `--atribuir` vuelve a leer el PDF con variantes de K y de pie del código vigente, que no aplican las
reglas de S0: lo que cambió S0 le queda en «otra» (informe de la lectura de R5 de esta unidad).

Entre `e1c9456` (el cierre de U-R2-CODIGO, donde ese control da 0 en «otra»: `r2_codigo/cierre_freno.md:50-72`) y la E0
corregida, el código de E0 cambió solo en C2 de U-R2-CODIGO-2 (`9f6361e6`) y en S0 (`26c65024`, `18d9e056`, `af7ffdd4`,
`2374968a`): `git log e1c9456..HEAD` de los tres archivos de E0. Por eso cada caso de «otra» se atribuye así:
- un id solo de la E0 corregida: si ya estaba en la E0 de e1c9456, «ya en e1c9456» (con la causa que R5 le da ahí);
  si no, y está en la de 9f6361e6, «C2»; si no, «S0»;
- un id solo de la partición: si tampoco estaba en e1c9456, «ya en e1c9456»; si estaba en e1c9456 y no en 9f6361e6,
  «C2»; si seguía en 9f6361e6, «S0». En «ya en e1c9456» va la clase que R5 le da en el cierre: la causa de «otra» (K,
  pie) o, si no está en «otra», partición no aplicada por tabla (el id es la unidad, o una de sus partes, que
  `sub_chunking.json` del cierre declara sin partir por tabla serializada) o L;
- un chunk con texto distinto: si su texto en la E0 corregida es el de e1c9456, «ya en e1c9456»; si no y es el de
  9f6361e6, «C2»; si no, «S0».
Además, como control de las clases que R5 sí asigna (L, tabla, K, pie), cuenta cuántas de esas diferencias no estaban
en e1c9456 (son de S0 o de C2 aunque R5 las ponga en otra clase). No guarda ni imprime texto: solo ids y cuentas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

B584 = "data/experiment/segmentacion_84/b584_particion"


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def chunks(d: Path, to: str) -> list[dict]:
    x = cargar(d / f"chunks_{to}.json")
    return x["chunks"] if isinstance(x, dict) else x


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("--r5", "--r5-cierre", "--e0", "--e0-cierre", "--e0-c2", "--raiz", "--out"):
        ap.add_argument(k, type=Path, required=True)
    a = ap.parse_args()
    r5, r5c = cargar(a.r5), cargar(a.r5_cierre)
    causa_cierre = {}
    for causa, lst in r5c.get("unidades_por_causa", {}).items():
        for x in lst:
            for i in x["solo_b584"] + x["solo_e0_r2"]:
                causa_cierre[(x["to"], i)] = causa
    sub_c = cargar(a.e0_cierre / "sub_chunking.json") or {}
    tabla_np_cierre = {(to, x["id"]) for to, v in sub_c.items() for x in v.get("no_particionables", [])
                       if x.get("motivo") == "tabla_serializada"}
    cache: dict = {}

    def causa_en_cierre(to: str, i: str) -> str:
        if (to, i) in causa_cierre:
            return causa_cierre[(to, i)]
        base = i.rsplit("::parte", 1)[0] if "::parte" in i else i
        if (to, base) in tabla_np_cierre:
            return "partición no aplicada por tabla"
        if "::rep" in i:
            return "L (ids desambiguados)"
        return "no figura"

    def ids(d: Path, to: str) -> set:
        k = (str(d), to)
        if k not in cache:
            cache[k] = {c["id"]: c["texto"] for c in chunks(d, to)}
        return cache[k]

    # 1. ids en «otra» (todas las causas que R5 no reduce a K o pie)
    ids_otra = []
    por_clase_ids = Counter()
    for causa, lst in r5.get("unidades_por_causa", {}).items():
        for x in lst:
            to = x["to"]
            cor, cie, c2 = ids(a.e0, to), ids(a.e0_cierre, to), ids(a.e0_c2, to)
            for lado, lista in (("solo_e0_r2", x["solo_e0_r2"]), ("solo_b584", x["solo_b584"])):
                for i in lista:
                    if causa in ("K", "pie", "K y pie"):
                        clase = f"R5: {causa}"
                        if (lado == "solo_e0_r2" and i not in cie) or (lado == "solo_b584" and i in cie):
                            clase += " (posterior a e1c9456)"
                    elif lado == "solo_e0_r2":
                        clase = ("ya en e1c9456" if i in cie else "C2" if i in c2 else "S0")
                    else:
                        clase = ("ya en e1c9456" if i not in cie else "C2" if i not in c2 else "S0")
                    if clase == "ya en e1c9456":
                        clase += f" (clase de R5 en e1c9456: {causa_en_cierre(to, i)})"
                    por_clase_ids[clase] += 1
                    ids_otra.append({"to": to, "id": i, "lado": lado, "causa_R5": causa, "clase": clase})
    # 2. texto en «otra»
    txt_otra = []
    por_clase_txt = Counter()
    for x in r5.get("texto_distinto_otra", []):
        to, cid = x["to"], x["chunk"]
        tcor, tcie, tc2 = ids(a.e0, to).get(cid), ids(a.e0_cierre, to).get(cid), ids(a.e0_c2, to).get(cid)
        clase = "ya en e1c9456" if tcor == tcie else "C2" if tcor == tc2 else "S0"
        por_clase_txt[clase] += 1
        txt_otra.append({"to": to, "chunk": cid, "clase": clase})
    # 3. control de las clases de ids que R5 asigna: L y tabla, posteriores a e1c9456
    posteriores_L = []
    for f in r5.get("por_to", []):
        if f["ids"].get("ids_desambiguados"):
            to = f["to"]
            cor, cie = ids(a.e0, to), ids(a.e0_cierre, to)
            nuevos = sorted(i for i in cor if i.rsplit("::rep", 1)[0] != i and i not in cie)
            if nuevos:
                posteriores_L.append({"to": to, "ids": nuevos})
    out = {"r5_sha256": sha(a.r5), "r5_cierre_sha256": sha(a.r5_cierre),
           "r5": {k: r5.get(k) for k in ("tos", "faltan", "tos_en_cero_que_la_particion_segmenta", "modo_de_lectura_distinto",
                                         "tos_con_ids_iguales", "diferencias_de_ids_por_clase",
                                         "diferencias_de_ids_otra_por_causa", "chunks_con_texto_distinto_por_clase")},
           "r5_cierre": {k: r5c.get(k) for k in ("tos", "tos_con_ids_iguales", "diferencias_de_ids_por_clase",
                                                 "diferencias_de_ids_otra_por_causa", "chunks_con_texto_distinto_por_clase")},
           "ids_por_clase_historica": dict(sorted(por_clase_ids.items())),
           "texto_otra_por_clase_historica": dict(sorted(por_clase_txt.items())),
           "otra_sin_explicar": {"ids": sum(v for k, v in por_clase_ids.items() if k.startswith("R5: otra")),
                                 "texto": por_clase_txt.get("otra", 0)},
           "tos_por_clase_historica": {k: sorted({x["to"] for x in ids_otra + txt_otra if x["clase"] == k})
                                       for k in sorted(set(por_clase_ids) | set(por_clase_txt))},
           "ids_L_posteriores_a_e1c9456": posteriores_L,
           "ids": ids_otra, "texto": txt_otra}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("r5", "r5_cierre", "ids_por_clase_historica", "texto_otra_por_clase_historica",
                                          "otra_sin_explicar")}, ensure_ascii=False, indent=0)[:4000])
    print({k: len(v) for k, v in out["tos_por_clase_historica"].items()})


if __name__ == "__main__":
    main()
