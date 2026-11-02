"""U-SEG-OFICIAL, S1-quater (sorteo), paso 2: control en cuentas de las poblaciones de `poblaciones_S1quater_v5.py` (USD 0, sin API).

Uso: python -B control_poblaciones_S1quater_sorteo.py --poblaciones <NO_ABRIR_poblaciones_S1quater.json> --sha <sha256 sellado>
       --out <json de cuentas>

Lee el JSON de las poblaciones con un script y escribe solo cuentas, sha256 y nombres de documento; nunca ids ni texto de unidades.
- Por estrato: unidades y sha256 de los ids ordenados, recalculado y comparado con el del JSON y con el esperado (la corrida de la
  mesa del 13/10/2026, citada en el despacho de este paso).
- Que los estratos no compartan unidades y que ninguna unidad de un estrato figure en una lista de salida.
- Las listas de salida (cuántas unidades por motivo y por estrato) y los documentos bajo el umbral de cobertura, con su tratamiento.
Sale con código 1 si algo de lo que tiene valor esperado no da.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ESPERADO = {"vigente": (6746, "e6ebad8abe0fe88c3a8f75026f12074d10c031a9766f0863242b7904ec843758"),
            "marcadores": (86, "dea0af647f282d675b0a201a119d69240775eaf1653f18a42480e9cf5d9d553b"),
            "sin_raiz": (897, "6752a7205f4ce83f5e77a10b423dccd98827acf142b0b7043a846105a14a7078")}
LISTAS = ("salen_por_construccion", "salen_por_leidas_en_S1ter", "salen_por_diseno_S0_6a", "salen_por_adenda_3",
          "salen_por_adenda_4")


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--poblaciones", type=Path, required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("FRENO: la salida ya existe")
    b = a.poblaciones.read_bytes()
    c: dict = {"control": "poblaciones de S1-quater (versión 5), en cuentas",
               "hora": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
               "sha256_json": hashlib.sha256(b).hexdigest()}
    c["sha256_json_ok"] = c["sha256_json"] == a.sha
    p = json.loads(b)
    ok = c["sha256_json_ok"]
    estratos = {}
    for e, (n_esp, sha_esp) in ESPERADO.items():
        g = p["cortes"][e]
        ids = g["ids"]
        r = {"unidades": len(ids), "unidades_json": g["unidades"], "sha256_ids_ordenados": sha_ids(sorted(ids)),
             "sha256_json": g["sha256_ids_ordenados"], "ordenados": ids == sorted(ids), "sin_repetir": len(set(ids)) == len(ids),
             "n": g["n"], "semilla": g["semilla"], "documentos": len(g["tos"]), "peso": round(g["peso"], 4)}
        r["ok"] = (r["unidades"] == r["unidades_json"] == n_esp and r["sha256_ids_ordenados"] == r["sha256_json"] == sha_esp
                   and r["ordenados"] and r["sin_repetir"])
        ok = ok and r["ok"]
        estratos[e] = r
    c["estratos"] = estratos
    todos = [i for e in ESPERADO for i in p["cortes"][e]["ids"]]
    c["cortes_total"] = len(todos)
    c["cortes_total_json"] = p["cortes_total"]
    c["estratos_sin_unidades_compartidas"] = len(set(todos)) == len(todos)
    salen = {k: [x["id"] for x in p[k]] for k in LISTAS}
    c["salen"] = {k: {"unidades": len(v), "por_estrato": dict(Counter(x["estrato"] for x in p[k]))} for k, v in salen.items()}
    todas_salen = [i for v in salen.values() for i in v]
    c["salen_total"] = len(todas_salen)
    c["salen_sin_repetir_entre_listas"] = len(set(todas_salen)) == len(todas_salen)
    c["poblacion_y_salen_disjuntas"] = not (set(todos) & set(todas_salen))
    c["salen_por_adenda_4_con_solapa_sin_orden"] = sum(1 for x in p["salen_por_adenda_4"] if x.get("solapa_sin_orden"))
    c["ri2_pm_cruzan_fichas"] = len(p["ri2_pm_cruzan_fichas"])
    c["mostradas_en_S1ter"] = p["mostradas_en_S1ter"]["unidades"]
    c["diseno_S0_6a"] = p["diseno_S0_6a"]["unidades"]
    c["adenda_3"] = {"unidades": p["adenda_3"]["unidades"], "por_grupo": p["adenda_3"]["por_grupo"]}
    c["adenda_4"] = {"unidades": p["adenda_4"]["unidades"], "por_grupo": p["adenda_4"]["por_grupo"]}
    c["documentos_alineados"] = len(p["alineacion_por_to"])
    c["umbral_de_cobertura"] = p["umbral_de_cobertura"]
    c["cobertura_bajo_el_umbral"] = {t: {"cobertura": round(v["cobertura"], 3), "tratamiento": v["tratamiento"],
                                         **({"salen_solo_sin_orden": v["salen_solo_sin_orden"]} if "salen_solo_sin_orden" in v
                                            else {})}
                                     for t, v in sorted(p["cobertura_bajo_el_umbral"].items())}
    c["insumos"] = p["insumos"]
    c["sellado_en_json"] = p["sellado"]
    ok = (ok and c["cortes_total"] == c["cortes_total_json"] and c["estratos_sin_unidades_compartidas"]
          and c["salen_sin_repetir_entre_listas"] and c["poblacion_y_salen_disjuntas"])
    c["ok"] = ok
    a.out.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(c, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
