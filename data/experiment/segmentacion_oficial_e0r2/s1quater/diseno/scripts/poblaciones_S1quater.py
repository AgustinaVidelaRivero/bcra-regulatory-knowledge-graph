"""U-SEG-OFICIAL, S1-quater: las poblaciones de la lectura de cortes sobre la E0 corregida, SIN SORTEAR (mesa, 11/10/2026; USD 0,
sin API). Fijado y sellado antes de que exista la E0 corregida (`../diseno_S1quater.md`, §2 y §3).

Uso: python3 -B poblaciones_S1quater.py --e0-nuevo <carpeta e0/ de la E0 corregida> --manifest-nuevo <su manifiesto>
       --sha-manifest-nuevo <sha256 sellado> --e0-viejo <s1ter/e0> --manifest-viejo <s1ter/manifest_salida.json>
       --manifiesto-tos <s1ter/manifiesto/segmentacion_oficial_e0r2_152.json> --orden-s1ter <s1ter/tramo_b/orden_lectura_S1ter.json>
       --out <json nuevo>

Las mismas poblaciones que S1-ter (`s1ter/scripts/poblaciones_S1ter.py`, parte 1, y `poblaciones_finales_S1ter.py`), sobre la E0
corregida:
- los tres estratos por el `modo_lectura` del manifiesto de TOs de S1-ter: `vigente`, `marcadores` y `sin_raiz`, con las unidades
  de los TOs reconocidos plenos y, en `sin_raiz`, las de ri_spi; tamaños 40 / 10 / 40;
- la misma regla de construcción: salen, declaradas, las unidades de `manual`, `ri_ao`, `optico` y `plandecuentas`, las de los TOs
  de vía por página y las de ri2_pm que cruzan una página de ficha de registro (calculadas sobre la E0 corregida con la regla de
  `s1ter/scripts/controles_S1ter.py`);
- y salen, declaradas, las unidades ya leídas en S1-ter (`comun_S1quater.excluir`): las del mismo id que una unidad que mostró
  una ficha de S1-ter, y las que solapan su texto propio.
El sha256 de cada población es `sha256("\\n".join(ids ordenados))`, como en S1-ter. La salida estándar no trae cifras.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_S1quater as Q  # noqa: E402

ENM = "docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md (e82e22f)"
NO_SE_CONSTRUYEN_TO = {"manual": f"histórico, fuera del recurso ({ENM}, Parte III, punto 1)",
                       "ri_ao": f"derogado, fuera del recurso ({ENM}, Parte III, punto 2)",
                       "optico": f"referencia, fuera del recurso ({ENM}, Parte II.2, punto 5)",
                       "plandecuentas": f"referencia, fuera del recurso ({ENM}, Parte II.2, punto 5)"}
VIA_PAGINA = f"vía por página: su prosa entra con la tanda 3 por la vía de páginas, no por su E0 ({ENM}, Parte II.2, punto 1)"
CRUZA_FICHAS = f"ri2_pm, unidad que cruza fichas: bloque B, release posterior ({ENM}, Parte II.2, punto 4)"


def cruzan_fichas_ri2_pm(e0: Q.E0) -> list[str]:
    """La regla de `s1ter/scripts/controles_S1ter.py` (ri2_pm): una unidad cruza fichas si alguna página de ficha de registro
    (rol `ficha_registro` en `pies_ri2_pm.json`) cae entre su primera y su última página."""
    roles = [d["rol"] for d in e0.json_de("pies_ri2_pm.json")["paginas_detalle"]]
    fichas = {i + 1 for i, r in enumerate(roles) if r == "ficha_registro"}
    return [c["id"] for c in e0.chunks("ri2_pm") if any(min(c["paginas"]) <= f <= max(c["paginas"]) for f in fichas)]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0_nuevo", "manifest_nuevo", "sha_manifest_nuevo", "e0_viejo", "manifest_viejo", "manifiesto_tos",
              "orden_s1ter", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        raise SystemExit("FRENO: la salida ya existe")
    Q.verificar_e0(Path(a.e0_viejo), Path(a.manifest_viejo), Q.SHA_MANIFEST_SALIDA_S1TER, "la E0 de S1-ter")
    m_nuevo = Q.verificar_e0(Path(a.e0_nuevo), Path(a.manifest_nuevo), a.sha_manifest_nuevo, "la E0 corregida")
    man = json.loads(Q.leer_sellado(Path(a.manifiesto_tos), Q.SHA_MANIFIESTO_TOS_S1TER, "el manifiesto de TOs de S1-ter"))
    orden = json.loads(Q.leer_sellado(Path(a.orden_s1ter), Q.SHA_ORDEN_S1TER, "el orden de lectura de S1-ter"))
    viejo, nuevo = Q.E0(Path(a.e0_viejo)), Q.E0(Path(a.e0_nuevo))

    tos_man = {t["id"]: t for t in man["tos"]}
    if tos_man["ri_spi"]["modo_lectura"] != "sin_raiz":
        raise SystemExit("FRENO: ri_spi no está en sin_raiz en el manifiesto de TOs")
    plenos = [t for t in man["tos"] if t["clase"] == "reconocido_pleno"]
    tos_estrato = {e: sorted([t["id"] for t in plenos if t["modo_lectura"] == e] + (["ri_spi"] if e == "sin_raiz" else []))
                   for e in Q.ESTRATOS}
    tos_lectura = sorted(t for v in tos_estrato.values() for t in v)

    cruzan = set(cruzan_fichas_ri2_pm(nuevo)) if "ri2_pm" in tos_lectura else set()

    def motivo(uid: str) -> str | None:
        to = uid.split("::")[0]
        if to in NO_SE_CONSTRUYEN_TO:
            return NO_SE_CONSTRUYEN_TO[to]
        if tos_man[to]["via"] == "por_pagina":
            return VIA_PAGINA
        if uid in cruzan:
            return CRUZA_FICHAS
        return None

    mostradas = Q.mostradas_S1ter(orden, viejo)
    ex = Q.excluir(viejo, nuevo, set(mostradas), tos_lectura)
    salen_construccion, salen_leidas, estratos = [], [], {}
    for e in Q.ESTRATOS:
        ids = []
        for t in tos_estrato[e]:
            for c in nuevo.chunks(t):
                m = motivo(c["id"])
                if m:
                    salen_construccion.append({"estrato": e, "id": c["id"], "motivo": m})
                elif c["id"] in ex["excluidas"]:
                    salen_leidas.append({"estrato": e, "id": c["id"], **ex["excluidas"][c["id"]]})
                else:
                    ids.append(c["id"])
        ids = sorted(ids)
        if len(ids) != len(set(ids)):
            raise SystemExit(f"FRENO: ids repetidos en el estrato {e}")
        estratos[e] = {"semilla": f"{Q.SEMILLA}:{e}", "n": Q.ESTRATOS[e], "tos": tos_estrato[e], "unidades": len(ids),
                       "sha256_ids_ordenados": Q.sha_ids(ids), "ids": ids}
        if len(ids) < Q.ESTRATOS[e]:
            raise SystemExit(f"FRENO: el estrato {e} tiene menos unidades que su tamaño")
    total = sum(g["unidades"] for g in estratos.values())
    for g in estratos.values():
        g["peso"] = g["unidades"] / total
    res = {"unidad": "U-SEG-OFICIAL, S1-quater: poblaciones de la lectura de cortes sobre la E0 corregida, sin sortear",
           "sellado": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
           "insumos": {"manifest_e0_corregida_sha256": a.sha_manifest_nuevo,
                       "version_e0_corregida": m_nuevo.get("version_e0"), "commit_codigo_e0_corregida": m_nuevo.get("commit_codigo"),
                       "manifest_e0_S1ter_sha256": Q.SHA_MANIFEST_SALIDA_S1TER,
                       "manifiesto_tos_sha256": Q.SHA_MANIFIESTO_TOS_S1TER, "orden_S1ter_sha256": Q.SHA_ORDEN_S1TER},
           "criterio": "los estratos y la regla de construcción de S1-ter (poblaciones_S1ter.py, parte 1, y "
                       "poblaciones_finales_S1ter.py), sobre la E0 corregida, menos las unidades ya leídas en S1-ter",
           "cortes": estratos, "cortes_total": total,
           "mostradas_en_S1ter": {"unidades": len(mostradas), "sha256_ids_ordenados": Q.sha_ids(sorted(mostradas))},
           "salen_por_construccion": salen_construccion,
           "ri2_pm_cruzan_fichas": sorted(cruzan),
           "salen_por_leidas_en_S1ter": salen_leidas,
           "alineacion_por_to": ex["alineacion"], "umbral_de_cobertura": Q.UMBRAL_COBERTURA}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"poblaciones escritas en {out}; sha256 {Q.sha(out)}")


if __name__ == "__main__":
    main()
