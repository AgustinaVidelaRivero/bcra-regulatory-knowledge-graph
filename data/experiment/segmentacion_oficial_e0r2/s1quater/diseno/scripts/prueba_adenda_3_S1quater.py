"""U-SEG-OFICIAL, S1-quater, adenda 3 al diseño: prueba de `poblaciones_S1quater_v4.py` contra la versión 3 (mesa, 12/10/2026; USD 0,
sin API). Corre las dos versiones sobre las mismas entradas, en una carpeta nueva, y controla que la versión 4 dé lo mismo que la 3
salvo que salen, declaradas, las unidades de la adenda 3 (la lista sellada fuera del repo, `--adenda-3`).

Uso: python3 -B prueba_adenda_3_S1quater.py --v3 <poblaciones_S1quater_v3.py> --v4 <poblaciones_S1quater_v4.py>
       --e0 <carpeta e0/ de la E0 de S1-ter> --manifest <s1ter/manifest_salida.json> --manifiesto-tos <…_152.json>
       --orden-s1ter <s1ter/tramo_b/orden_lectura_S1ter.json> --diseno-s0-6a <NO_ABRIR_unidades_diseno_guardas_A_S0-6a.json>
       --adenda-3 <NO_ABRIR_unidades_adenda_3_S1quater.json> --trabajo <carpeta nueva>

La E0 de S1-ter hace de E0 corregida, como en las pruebas de las adendas 1 y 2: las dos versiones leen los mismos datos reales, y
la diferencia es solo la de la adenda. Con la misma E0, cada unidad de la lista solapa solo consigo misma. La salida estándar no
trae ids: solo ok o MAL por control.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SHA_MANIFEST = "5e63dff235326c4b2bb73cb95ca409037afa93fbb4903fe89fbd59b17dccc432"   # s1ter/manifest_salida.json
N_GRUPOS = {"vistas_guardas_A": 9, "vecinas_selftest": 5, "listas_R5a": 6,
            "vistas_por_la_mesa": 262}   # unidades de la E0 de S1-ter por grupo (adenda 3, §0)
N_VECINAS_IDS, N_VECINAS_YA_LEIDAS = 11, 6                  # ids del selftest, y los que ya salen por leídas en S1-ter


def correr(script: Path, a, out: Path, extra: list[str]) -> dict:
    # cada versión corre desde su propia carpeta, junto a una copia de comun_S1quater.py
    r = subprocess.run([sys.executable, "-B", str(script), "--e0-nuevo", a.e0, "--manifest-nuevo", a.manifest,
                        "--sha-manifest-nuevo", SHA_MANIFEST, "--e0-viejo", a.e0, "--manifest-viejo", a.manifest,
                        "--manifiesto-tos", a.manifiesto_tos, "--orden-s1ter", a.orden_s1ter,
                        "--diseno-s0-6a", a.diseno_s0_6a, *extra, "--out", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"FRENO: {script.name} no corrió: {r.stderr[-400:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("v3", "v4", "e0", "manifest", "manifiesto_tos", "orden_s1ter", "diseno_s0_6a", "adenda_3", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    T = Path(a.trabajo)
    if T.exists():
        raise SystemExit("FRENO: la carpeta de trabajo ya existe")
    for n in ("v3", "v4"):
        (T / n).mkdir(parents=True)
        src = Path(getattr(a, n))
        shutil.copy2(src, T / n / src.name)
        shutil.copy2(Path(a.v3).parent / "comun_S1quater.py", T / n / "comun_S1quater.py")
    p3 = correr(T / "v3" / Path(a.v3).name, a, T / "poblaciones_v3.json", [])
    p4 = correr(T / "v4" / Path(a.v4).name, a, T / "poblaciones_v4.json", ["--adenda-3", a.adenda_3])

    ad3 = json.loads(Path(a.adenda_3).read_text(encoding="utf-8"))
    d3 = set(ad3["ids_e0_S1ter"])
    d2 = set(json.loads(Path(a.diseno_s0_6a).read_text(encoding="utf-8"))["ids_e0_S1ter"])
    orden = json.loads(Path(a.orden_s1ter).read_text(encoding="utf-8"))
    sys.path.insert(0, str(T / "v4"))
    import comun_S1quater as Q  # noqa: E402,PLC0415
    mostradas = set(Q.mostradas_S1ter(orden, Q.E0(Path(a.e0))))
    v3_ids = {u for g in p3["cortes"].values() for u in g["ids"]}
    res = []

    def ok(c: bool, q: str) -> None:
        res.append((c, q))

    vec = ad3["grupos"]["vecinas_selftest"]
    ok({g: len(ad3["grupos"][g]["ids"]) for g in N_GRUPOS} == N_GRUPOS
       and set().union(*(set(ad3["grupos"][g]["ids"]) for g in N_GRUPOS)) == d3 and len(d3) == sum(N_GRUPOS.values()),
       "la lista de la adenda 3 trae las unidades esperadas por grupo, y sus grupos la cubren sin repetir")
    ok(not (d3 & mostradas) and not (d3 & d2), "ninguna unidad de la lista está entre las leídas en S1-ter ni en la adenda 2")
    ok(len(vec["mapeo"]) == N_VECINAS_IDS and len(vec["ya_salen_por_leidas_en_S1ter"]) == N_VECINAS_YA_LEIDAS
       and all(set(ids) <= mostradas for ids in vec["ya_salen_por_leidas_en_S1ter"].values()),
       "de los ids del selftest, los que no entran a la lista tienen su texto en unidades leídas en S1-ter (ya salen por el §3)")
    ok(bool(d3 & v3_ids), "la versión 3 sí tenía unidades de la lista en la población (la adenda hace falta)")
    ok(all(p4["cortes"][e]["ids"] == [u for u in p3["cortes"][e]["ids"] if u not in d3] for e in p3["cortes"]),
       "en cada estrato, la versión 4 da los ids de la versión 3 menos las de la lista, en el mismo orden")
    ok({x["id"] for x in p4["salen_por_adenda_3"]} == d3 & v3_ids and all(x["mismo_id"] for x in p4["salen_por_adenda_3"]),
       "salen por la adenda 3 exactamente las de la lista que estaban en la población, por el mismo id (con la misma E0 no hay otras)")
    ok(all(x["grupos"] and x["motivo"] for x in p4["salen_por_adenda_3"]), "cada una sale declarada, con su grupo y su motivo")
    ok(all(p4[k] == p3[k] for k in ("salen_por_construccion", "salen_por_leidas_en_S1ter", "salen_por_diseno_S0_6a")),
       "salen por construcción, por leídas en S1-ter y por la adenda 2 las mismas que en la versión 3")
    ok(all(p4[k] == p3[k] for k in ("mostradas_en_S1ter", "ri2_pm_cruzan_fichas", "alineacion_por_to", "umbral_de_cobertura",
                                    "diseno_S0_6a"))
       and {k: v for k, v in p4["insumos"].items() if k != "adenda_3_sha256"} == p3["insumos"],
       "insumos, unidades mostradas, ri2_pm, alineación, umbral y adenda 2: iguales (los insumos suman el sha256 de la lista)")
    ok(all(p4["cortes"][e][k] == p3["cortes"][e][k] for e in p3["cortes"] for k in ("semilla", "n", "tos")),
       "semilla, tamaño y documentos de cada estrato: iguales")
    tot = sum(g["unidades"] for g in p4["cortes"].values())
    ok(p4["cortes_total"] == tot and all(abs(g["peso"] - g["unidades"] / tot) < 1e-12 and g["unidades"] == len(g["ids"])
                                         for g in p4["cortes"].values()),
       "los pesos de la versión 4 se recalculan sobre sus unidades")
    for c, q in res:
        print(("ok   " if c else "MAL  ") + q)
    print(f"{sum(c for c, _ in res)} de {len(res)} controles ok")
    sys.exit(0 if all(c for c, _ in res) else 1)


if __name__ == "__main__":
    main()
