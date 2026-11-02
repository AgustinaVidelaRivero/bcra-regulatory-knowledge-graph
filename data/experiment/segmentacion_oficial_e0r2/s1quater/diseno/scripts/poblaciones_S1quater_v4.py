"""U-SEG-OFICIAL, S1-quater: las poblaciones de la lectura de cortes sobre la E0 corregida, SIN SORTEAR (mesa, 11/10/2026; USD 0,
sin API). Las versiones 1 y 2 se fijaron y sellaron antes de que exista la E0 corregida (`../diseno_S1quater.md`, §2 y §3); la 3 y la 4,
antes del sorteo, con la E0 corregida de S0-6a ya hecha y sin usarla (`../adenda_2_diseno_S1quater.md` y
`../adenda_3_diseno_S1quater.md`).

Versión 2 (mesa, 12/10/2026; `../adenda_1_diseno_S1quater.md`): la única diferencia con la versión 1, que no cambia, es que salen
por construcción, declaradas, las unidades de los cinco documentos de la tanda 0 que están entre los 152 (`TANDA0_FUERA`). La
tanda 0 queda fuera de la corrección de E0 de S0-6a, así que no tiene la E0 corregida que mide S1-quater (decisión de la autora del
12/10/2026).

Versión 3 (mesa, 12/10/2026; `../adenda_2_diseno_S1quater.md`): la única diferencia con la versión 2, que no cambia, es que salen
también, declaradas, las unidades de diseño de S0-6a: las de la E0 de S1-ter que la ejecutora miró al agregar dos guardas a la regla
A, que después revirtió (decisión de la autora del 12/10/2026). Salen como las leídas en S1-ter (§3 del diseño): por el mismo id o
porque solapan su texto propio. Sus ids no van al repo: los trae una lista fuera del repo, `--diseno-s0-6a`, controlada por su sha256
(`SHA_DISENO_S0_6A`).

Versión 4 (mesa, 12/10/2026; `../adenda_3_diseno_S1quater.md`): la única diferencia con la versión 3, que no cambia, es que salen
también, declaradas, las unidades de la adenda 3 (decisión de la autora del 12/10/2026): las de la E0 de S1-ter que mostró la misma
salida de la sesión de S0-6a sin motivar las guardas de A, las vecinas de las filas que mira el selftest del parche de S0-6a, las
de las 3 listas de R5-a cuyas unidades no son filas ni leídas, y las que la mesa vio al revisar S0-6a.
Salen con el mismo mecanismo que las leídas y las de diseño: por el mismo id o porque solapan su texto propio. Sus ids tampoco van
al repo: los trae una lista fuera del repo, `--adenda-3`, controlada por su sha256 (`SHA_ADENDA_3`). Una unidad que sale por
construcción, por leída o por la adenda 2 sale por eso, aunque también esté en la lista de la adenda 3.

Uso: python3 -B poblaciones_S1quater_v4.py --e0-nuevo <carpeta e0/ de la E0 corregida> --manifest-nuevo <su manifiesto>
       --sha-manifest-nuevo <sha256 sellado> --e0-viejo <s1ter/e0> --manifest-viejo <s1ter/manifest_salida.json>
       --manifiesto-tos <s1ter/manifiesto/segmentacion_oficial_e0r2_152.json> --orden-s1ter <s1ter/tramo_b/orden_lectura_S1ter.json>
       --diseno-s0-6a <NO_ABRIR_unidades_diseno_guardas_A_S0-6a.json> --adenda-3 <NO_ABRIR_unidades_adenda_3_S1quater.json>
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
TANDA0_FUERA = frozenset({"ctacte", "lingob", "polcre", "pagjub", "docvig"})   # los cinco de la tanda 0 que están entre los 152
TANDA0 = ("tanda 0: queda fuera de la corrección de E0 de S0-6a, así que no tiene la E0 corregida que mide S1-quater "
          "(decisión de la autora del 12/10/2026; ../adenda_1_diseno_S1quater.md)")
VIA_PAGINA = f"vía por página: su prosa entra con la tanda 3 por la vía de páginas, no por su E0 ({ENM}, Parte II.2, punto 1)"
CRUZA_FICHAS = f"ri2_pm, unidad que cruza fichas: bloque B, release posterior ({ENM}, Parte II.2, punto 4)"
SHA_DISENO_S0_6A = "1703861cbbc7abd9b913797fed2a6a73485adc5d4d3aace3cc11aed555abae71"  # NO_ABRIR_unidades_diseno_guardas_A_S0-6a.json
DISENO_S0_6A = ("unidad de diseño de S0-6a: la ejecutora agregó dos guardas a la regla A mirando su texto y las revirtió "
                "(decisión de la autora del 12/10/2026; ../adenda_2_diseno_S1quater.md)")
SHA_ADENDA_3 = "7337f854c58f0d5fb962e18c843ed2350640221e63de1d7ac46eaab11429c500"  # NO_ABRIR_unidades_adenda_3_S1quater.json
ADENDA_3 = {"vistas_guardas_A": "unidad que la ejecutora de S0-6a vio en la salida que miró para las guardas de A, sin que las "
                                "motivara (decisión de la autora del 12/10/2026; ../adenda_3_diseno_S1quater.md)",
            "vecinas_selftest": "unidad vecina de una fila, que mira el selftest del parche de S0-6a (decisión de la autora del "
                                "12/10/2026; ../adenda_3_diseno_S1quater.md)",
            "listas_R5a": "unidad de una de las 3 listas de R5-a de unidades no leídas, que S0-6a-bis compara con la página (decisión "
                          "de la autora del 12/10/2026; ../adenda_3_diseno_S1quater.md)",
            "vistas_por_la_mesa": "unidad cuyo texto quedó a la vista de la mesa al revisar S0-6a (decisión de la autora del "
                                  "12/10/2026; ../adenda_3_diseno_S1quater.md)"}


def cruzan_fichas_ri2_pm(e0: Q.E0) -> list[str]:
    """La regla de `s1ter/scripts/controles_S1ter.py` (ri2_pm): una unidad cruza fichas si alguna página de ficha de registro
    (rol `ficha_registro` en `pies_ri2_pm.json`) cae entre su primera y su última página."""
    roles = [d["rol"] for d in e0.json_de("pies_ri2_pm.json")["paginas_detalle"]]
    fichas = {i + 1 for i, r in enumerate(roles) if r == "ficha_registro"}
    return [c["id"] for c in e0.chunks("ri2_pm") if any(min(c["paginas"]) <= f <= max(c["paginas"]) for f in fichas)]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0_nuevo", "manifest_nuevo", "sha_manifest_nuevo", "e0_viejo", "manifest_viejo", "manifiesto_tos",
              "orden_s1ter", "diseno_s0_6a", "adenda_3", "out"):
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
    dis = json.loads(Q.leer_sellado(Path(a.diseno_s0_6a), SHA_DISENO_S0_6A, "la lista de unidades de diseño de S0-6a"))
    diseno = set(dis["ids_e0_S1ter"])
    faltan_d = sorted(u for u in diseno if not any(c["id"] == u for c in viejo.chunks(u.split("::")[0])))
    if not diseno or faltan_d:
        raise SystemExit(f"FRENO: la lista de unidades de diseño está vacía o trae unidades que no están en la E0 de S1-ter: {len(faltan_d)}")
    ad3 = json.loads(Q.leer_sellado(Path(a.adenda_3), SHA_ADENDA_3, "la lista de unidades de la adenda 3"))
    grupo3 = {u: g for g in ADENDA_3 for u in ad3["grupos"][g]["ids"]}
    adenda3 = set(ad3["ids_e0_S1ter"])
    faltan_3 = sorted(u for u in adenda3 if not any(c["id"] == u for c in viejo.chunks(u.split("::")[0])))
    if not adenda3 or set(grupo3) != adenda3 or faltan_3 or adenda3 & diseno:
        raise SystemExit("FRENO: la lista de la adenda 3 está vacía, sus grupos no la cubren, trae unidades que no están en la E0 de "
                         f"S1-ter o repite unidades de la adenda 2: {len(faltan_3)}")

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
        if to in TANDA0_FUERA:
            return TANDA0
        if tos_man[to]["via"] == "por_pagina":
            return VIA_PAGINA
        if uid in cruzan:
            return CRUZA_FICHAS
        return None

    mostradas = Q.mostradas_S1ter(orden, viejo)
    ex = Q.excluir(viejo, nuevo, set(mostradas), tos_lectura)
    ex_d = Q.excluir(viejo, nuevo, diseno, tos_lectura)
    ex_3 = Q.excluir(viejo, nuevo, adenda3, tos_lectura)
    salen_construccion, salen_leidas, salen_diseno, salen_3, estratos = [], [], [], [], {}
    for e in Q.ESTRATOS:
        ids = []
        for t in tos_estrato[e]:
            for c in nuevo.chunks(t):
                m = motivo(c["id"])
                if m:
                    salen_construccion.append({"estrato": e, "id": c["id"], "motivo": m})
                elif c["id"] in ex["excluidas"]:
                    salen_leidas.append({"estrato": e, "id": c["id"], **ex["excluidas"][c["id"]]})
                elif c["id"] in ex_d["excluidas"]:
                    salen_diseno.append({"estrato": e, "id": c["id"], "motivo": DISENO_S0_6A, **ex_d["excluidas"][c["id"]]})
                elif c["id"] in ex_3["excluidas"]:
                    x = ex_3["excluidas"][c["id"]]
                    grupos = sorted({grupo3[u] for u in ([c["id"]] if x["mismo_id"] else []) + x["solapa_con"]})
                    salen_3.append({"estrato": e, "id": c["id"], "grupos": grupos,
                                    "motivo": "; ".join(ADENDA_3[g] for g in grupos), **x})
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
    res = {"unidad": "U-SEG-OFICIAL, S1-quater: poblaciones de la lectura de cortes sobre la E0 corregida, sin sortear (versión 4)",
           "sellado": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
           "insumos": {"manifest_e0_corregida_sha256": a.sha_manifest_nuevo,
                       "version_e0_corregida": m_nuevo.get("version_e0"), "commit_codigo_e0_corregida": m_nuevo.get("commit_codigo"),
                       "manifest_e0_S1ter_sha256": Q.SHA_MANIFEST_SALIDA_S1TER,
                       "manifiesto_tos_sha256": Q.SHA_MANIFIESTO_TOS_S1TER, "orden_S1ter_sha256": Q.SHA_ORDEN_S1TER,
                       "diseno_S0_6a_sha256": SHA_DISENO_S0_6A, "adenda_3_sha256": SHA_ADENDA_3},
           "criterio": "los estratos y la regla de construcción de S1-ter (poblaciones_S1ter.py, parte 1, y "
                       "poblaciones_finales_S1ter.py), sobre la E0 corregida, menos las unidades ya leídas en S1-ter y menos las de los "
                       "cinco documentos de la tanda 0 que están entre los 152 (adenda 1 al diseño), menos las unidades de diseño de "
                       "S0-6a (adenda 2 al diseño) y menos las de la adenda 3 al diseño",
           "cortes": estratos, "cortes_total": total,
           "mostradas_en_S1ter": {"unidades": len(mostradas), "sha256_ids_ordenados": Q.sha_ids(sorted(mostradas))},
           "salen_por_construccion": salen_construccion,
           "ri2_pm_cruzan_fichas": sorted(cruzan),
           "salen_por_leidas_en_S1ter": salen_leidas,
           "diseno_S0_6a": {"unidades": len(diseno), "sha256_ids_ordenados": Q.sha_ids(sorted(diseno))},
           "salen_por_diseno_S0_6a": salen_diseno,
           "adenda_3": {"unidades": len(adenda3), "sha256_ids_ordenados": Q.sha_ids(sorted(adenda3)),
                        "por_grupo": {g: len(ad3["grupos"][g]["ids"]) for g in ADENDA_3}},
           "salen_por_adenda_3": salen_3,
           "alineacion_por_to": ex["alineacion"], "umbral_de_cobertura": Q.UMBRAL_COBERTURA}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"poblaciones escritas en {out}; sha256 {Q.sha(out)}")


if __name__ == "__main__":
    main()
