"""U-SEG-OFICIAL, S1-quater (sorteo), paso 4: control en cuentas de la muestra y el orden de `sorteo_S1quater.py` (USD 0, sin API).

Uso: python -B control_sorteo_S1quater_sorteo.py --poblaciones <NO_ABRIR_poblaciones_S1quater.json> --sha-poblaciones <sha256>
       --regresion <NO_ABRIR_regresion_S1quater.json> --sha-regresion <sha256> --muestra <NO_ABRIR_muestra_S1quater.json>
       --sha-muestra <sha256> --orden <NO_ABRIR_orden_lectura_S1quater.json> --sha-orden <sha256> --out <json de cuentas>

Lee los cuatro JSON con un script y escribe solo cuentas y sha256; nunca ids ni texto de unidades.
- Rehace el sorteo por su cuenta, con las semillas del diseño (`diseno_S1quater.md`, §4), sin importar los scripts del diseño, y lo
  compara con la muestra y con el orden de la etapa 1.
- La muestra: 40 / 10 / 40, 90 unidades distintas, cada una de la población de su estrato, ninguna de la regresión.
- El orden: en la etapa 1, 90 fichas `E1-001`… con las 90 de la muestra; en la etapa 2, 60 fichas `E2-001`… con la regresión, en el
  orden de sus ids.
Sale con código 1 si algo no da.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime
from pathlib import Path

ESTRATOS = {"vigente": 40, "marcadores": 10, "sin_raiz": 40}
SEMILLA = "U-SEG-OFICIAL:cortes:S1-quater"
SEMILLA_ORDEN = "U-SEG-OFICIAL:cortes:S1-quater:orden"


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def leer(p: Path, esperado: str) -> tuple[dict, bool]:
    b = p.read_bytes()
    return json.loads(b), hashlib.sha256(b).hexdigest() == esperado


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("poblaciones", "sha_poblaciones", "regresion", "sha_regresion", "muestra", "sha_muestra", "orden", "sha_orden",
              "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        raise SystemExit("FRENO: la salida ya existe")
    pob, ok_p = leer(Path(a.poblaciones), a.sha_poblaciones)
    reg, ok_r = leer(Path(a.regresion), a.sha_regresion)
    mue, ok_m = leer(Path(a.muestra), a.sha_muestra)
    ord_, ok_o = leer(Path(a.orden), a.sha_orden)
    c: dict = {"control": "muestra y orden de S1-quater, en cuentas",
               "hora": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
               "sha256_ok": {"poblaciones": ok_p, "regresion": ok_r, "muestra": ok_m, "orden": ok_o}}
    # el sorteo rehecho por su cuenta
    rehecha = {e: random.Random(f"{SEMILLA}:{e}").sample(sorted(pob["cortes"][e]["ids"]), n) for e, n in ESTRATOS.items()}
    ids_90 = [i for v in rehecha.values() for i in v]
    orden_rehecho = random.Random(SEMILLA_ORDEN).sample(sorted(ids_90), len(ids_90))
    estratos = {}
    for e, n in ESTRATOS.items():
        m = mue["cortes"][e]["muestra"]
        estratos[e] = {"muestra": len(m), "n": n, "igual_al_sorteo_rehecho": m == rehecha[e],
                       "todas_de_su_poblacion": set(m) <= set(pob["cortes"][e]["ids"]),
                       "poblacion": mue["cortes"][e]["poblacion"],
                       "sha256_poblacion_igual": mue["cortes"][e]["sha256_poblacion"] == pob["cortes"][e]["sha256_ids_ordenados"]}
    c["estratos"] = estratos
    m90 = [i for e in ESTRATOS for i in mue["cortes"][e]["muestra"]]
    c["muestra_total"] = len(m90)
    c["muestra_distintas"] = len(set(m90))
    c["muestra_sha256_ids_90_ordenados"] = sha_ids(sorted(m90))
    c["muestra_sha256_ids_90_ordenados_json"] = mue["cortes_ids_90_sha256_ordenados"]
    c["muestra_y_regresion_disjuntas"] = not (set(m90) & set(reg["ids"]))
    c["muestra_cita_las_entradas"] = (mue["poblaciones_sha256"] == a.sha_poblaciones and mue["regresion_sha256"] == a.sha_regresion)
    e1 = ord_["etapa_1"]["fichas"]
    e2 = ord_["etapa_2"]["fichas"]
    c["etapa_1"] = {"fichas": len(e1),
                    "ids_opacos_seguidos": [f["id_opaco"] for f in e1] == [f"E1-{k:03d}" for k in range(1, len(e1) + 1)],
                    "igual_al_orden_rehecho": [f["id"] for f in e1] == orden_rehecho,
                    "mismas_unidades_que_la_muestra": sorted(f["id"] for f in e1) == sorted(m90),
                    "estrato_correcto": all(f["id"] in mue["cortes"][f["estrato"]]["muestra"] for f in e1),
                    "por_estrato": {e: sum(1 for f in e1 if f["estrato"] == e) for e in ESTRATOS},
                    "semilla_del_orden": ord_["etapa_1"]["semilla_del_orden"] == SEMILLA_ORDEN}
    c["etapa_2"] = {"fichas": len(e2),
                    "ids_opacos_seguidos": [f["id_opaco"] for f in e2] == [f"E2-{k:03d}" for k in range(1, len(e2) + 1)],
                    "igual_a_la_regresion_en_orden": [f["id"] for f in e2] == reg["ids"],
                    "calificada_es_la_unidad": all(f["unidades_calificadas"] == [f["id"]] for f in e2),
                    "poblacion_regresion": all(f["poblacion"] == "regresion" for f in e2)}
    c["sellado_en_json"] = {"muestra": mue["sellado"], "orden": ord_["sellado"], "python": mue["python"]}
    ok = (all(c["sha256_ok"].values())
          and all(v["muestra"] == v["n"] and v["igual_al_sorteo_rehecho"] and v["todas_de_su_poblacion"]
                  and v["sha256_poblacion_igual"] for v in estratos.values())
          and c["muestra_total"] == c["muestra_distintas"] == 90
          and c["muestra_sha256_ids_90_ordenados"] == c["muestra_sha256_ids_90_ordenados_json"]
          and c["muestra_y_regresion_disjuntas"] and c["muestra_cita_las_entradas"]
          and c["etapa_1"]["fichas"] == 90 and all(v for k, v in c["etapa_1"].items() if isinstance(v, bool))
          and c["etapa_1"]["por_estrato"] == ESTRATOS
          and c["etapa_2"]["fichas"] == len(reg["ids"]) and all(v for k, v in c["etapa_2"].items() if isinstance(v, bool)))
    c["ok"] = ok
    out.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(c, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
