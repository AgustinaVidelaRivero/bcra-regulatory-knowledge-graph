"""U-SEG-OFICIAL, S1-quater: la lista de regresión, las unidades con error confirmado en S1-ter llevadas a la E0 corregida (mesa,
11/10/2026; USD 0, sin API). Fijado y sellado antes de que exista la E0 corregida (`../diseno_S1quater.md`, §6). No entra en la
cifra de S1-quater.

Uso: python3 -B regresion_S1quater.py --adjudicada-1 <planilla adjudicada de la etapa 1> --sha-adjudicada-1 <sha256 sellado>
       --adjudicada-2 <de la etapa 2> --sha-adjudicada-2 <sha256> --registro-adjudicacion <json de aplicar_adjudicacion_S1ter.py>
       --sha-registro-adjudicacion <sha256> --orden-s1ter <s1ter/tramo_b/orden_lectura_S1ter.json>
       --e0-viejo <s1ter/e0> --manifest-viejo <s1ter/manifest_salida.json>
       --e0-nuevo <e0/ de la E0 corregida> --manifest-nuevo <su manifiesto> --sha-manifest-nuevo <sha256> --out <json nuevo>

Las entradas son las salidas de `s1ter/scripts/aplicar_adjudicacion_S1ter.py` sobre la adjudicación final de S1-ter (la pasada 1
corregida por la pasada 2). Una unidad de S1-ter tiene un error confirmado si:
- su ficha quedó con `marca` `error` en la planilla adjudicada: en la etapa 1, la unidad; en la etapa 2, sus unidades calificadas;
- la autora confirmó un error en la unidad que sigue (`cierres_confirmados`): la unidad que sigue a la de la ficha;
- la autora confirmó un error en lo heredado (`herencias_confirmadas`): las unidades calificadas de la ficha.
Cada una se lleva a la E0 corregida con `comun_S1quater.alinear_to`: las unidades nuevas que solapan su texto propio. La lista de
regresión son esas unidades nuevas, sin repetir y ordenadas por id. Una unidad vieja sin unidad nueva que la solape queda
declarada. La salida estándar no trae cifras.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_S1quater as Q  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("adjudicada_1", "sha_adjudicada_1", "adjudicada_2", "sha_adjudicada_2", "registro_adjudicacion",
              "sha_registro_adjudicacion", "orden_s1ter", "e0_viejo", "manifest_viejo", "e0_nuevo", "manifest_nuevo",
              "sha_manifest_nuevo", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        raise SystemExit("FRENO: la salida ya existe")
    Q.verificar_e0(Path(a.e0_viejo), Path(a.manifest_viejo), Q.SHA_MANIFEST_SALIDA_S1TER, "la E0 de S1-ter")
    Q.verificar_e0(Path(a.e0_nuevo), Path(a.manifest_nuevo), a.sha_manifest_nuevo, "la E0 corregida")
    orden = json.loads(Q.leer_sellado(Path(a.orden_s1ter), Q.SHA_ORDEN_S1TER, "el orden de lectura de S1-ter"))
    planillas = {e: list(csv.DictReader(io.StringIO(Q.leer_sellado(Path(p), s, f"la planilla adjudicada {e}").decode("utf-8")),
                                        delimiter="\t"))
                 for e, p, s in ((1, a.adjudicada_1, a.sha_adjudicada_1), (2, a.adjudicada_2, a.sha_adjudicada_2))}
    reg = json.loads(Q.leer_sellado(Path(a.registro_adjudicacion), a.sha_registro_adjudicacion, "el registro de la adjudicación"))
    viejo, nuevo = Q.E0(Path(a.e0_viejo)), Q.E0(Path(a.e0_nuevo))

    fichas = {f["id_opaco"]: (e, f) for e in (1, 2) for f in orden[f"etapa_{e}"]["fichas"]}
    for e in (1, 2):
        if sorted(f["ficha"] for f in planillas[e]) != sorted(op for op, (ee, _) in fichas.items() if ee == e):
            raise SystemExit(f"FRENO: la planilla adjudicada {e} no trae una vez cada ficha del orden de S1-ter")

    def calificadas(op: str) -> list[str]:
        e, f = fichas[op]
        return [f["id"]] if e == 1 else list(f["unidades_calificadas"])

    errores: list[dict] = []
    for e in (1, 2):
        for fila in planillas[e]:
            if fila["marca"] == "error":
                errores.append({"ficha": fila["ficha"], "por": "marca", "clase": fila["clase"], "unidades": calificadas(fila["ficha"])})
    for c in reg.get("cierres_confirmados", []):
        sig = viejo.siguiente(fichas[c["ficha"]][1]["id"])
        errores.append({"ficha": c["ficha"], "por": "la_que_sigue", "clase": c["clase_que_sigue"],
                        "unidades": [sig["id"]] if sig else []})
    for h in reg.get("herencias_confirmadas", []):
        errores.append({"ficha": h["ficha"], "por": "herencia", "clase": None, "unidades": calificadas(h["ficha"])})

    viejas = sorted({u for x in errores for u in x["unidades"]})
    por_to: dict[str, dict] = {}
    for t in sorted({u.split("::")[0] for u in viejas}):
        por_to[t] = Q.alinear_to(viejo.chunks(t), nuevo.chunks(t))
    nuevas_de: dict[str, list[str]] = {}
    for u in viejas:
        sol = por_to[u.split("::")[0]]["solapes"]
        nuevas_de[u] = sorted(n for n, vs in sol.items() if u in vs)
    nuevas = sorted({n for v in nuevas_de.values() for n in v})
    res = {"unidad": "U-SEG-OFICIAL, S1-quater: lista de regresión (no entra en la cifra)",
           "sellado": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
           "insumos": {"adjudicada_1_sha256": a.sha_adjudicada_1, "adjudicada_2_sha256": a.sha_adjudicada_2,
                       "registro_adjudicacion_sha256": a.sha_registro_adjudicacion, "orden_S1ter_sha256": Q.SHA_ORDEN_S1TER,
                       "manifest_e0_corregida_sha256": a.sha_manifest_nuevo},
           "errores_confirmados_S1ter": errores, "unidades_viejas": viejas, "unidades_nuevas_de": nuevas_de,
           "sin_unidad_nueva": [u for u in viejas if not nuevas_de[u]],
           "cobertura_por_to": {t: v["cobertura"] for t, v in por_to.items()},
           "ids": nuevas, "sha256_ids_ordenados": Q.sha_ids(nuevas)}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"lista de regresión escrita en {out}; sha256 {Q.sha(out)}")


if __name__ == "__main__":
    main()
