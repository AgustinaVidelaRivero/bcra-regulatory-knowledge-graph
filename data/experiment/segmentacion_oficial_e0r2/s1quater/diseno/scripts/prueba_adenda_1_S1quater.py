"""U-SEG-OFICIAL, S1-quater, adenda 1 al diseño: prueba de `poblaciones_S1quater_v2.py` contra la versión 1 (mesa, 12/10/2026; USD 0,
sin API). Corre las dos versiones sobre las mismas entradas, en una carpeta nueva, y controla que la versión 2 dé lo mismo que la 1
salvo que las unidades de los cinco documentos de la tanda 0 que están entre los 152 salen por construcción, declaradas.

Uso: python3 -B prueba_adenda_1_S1quater.py --v1 <poblaciones_S1quater.py> --v2 <poblaciones_S1quater_v2.py>
       --e0 <carpeta e0/ de la E0 de S1-ter> --manifest <s1ter/manifest_salida.json> --manifiesto-tos <…_152.json>
       --orden-s1ter <s1ter/tramo_b/orden_lectura_S1ter.json> --tanda0 <reextraccion_v2/manifiestos/tanda0_10tos_r2b.json>
       --trabajo <carpeta nueva>

La E0 de S1-ter hace de E0 corregida: así las dos versiones leen los mismos datos reales, y la diferencia es solo la de la adenda.
La salida estándar no trae cifras: solo ok o MAL por control.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def correr(script: Path, a, out: Path) -> dict:
    # cada versión corre desde su propia carpeta, junto a una copia de comun_S1quater.py
    r = subprocess.run([sys.executable, "-B", str(script), "--e0-nuevo", a.e0, "--manifest-nuevo", a.manifest,
                        "--sha-manifest-nuevo", SHA_MANIFEST, "--e0-viejo", a.e0, "--manifest-viejo", a.manifest,
                        "--manifiesto-tos", a.manifiesto_tos, "--orden-s1ter", a.orden_s1ter, "--out", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"FRENO: {script.name} no corrió: {r.stderr[-400:]}")
    return json.loads(out.read_text(encoding="utf-8"))


SHA_MANIFEST = "5e63dff235326c4b2bb73cb95ca409037afa93fbb4903fe89fbd59b17dccc432"   # s1ter/manifest_salida.json


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("v1", "v2", "e0", "manifest", "manifiesto_tos", "orden_s1ter", "tanda0", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    T = Path(a.trabajo)
    if T.exists():
        raise SystemExit("FRENO: la carpeta de trabajo ya existe")
    for n in ("v1", "v2"):
        (T / n).mkdir(parents=True)
        src = Path(getattr(a, n))
        shutil.copy2(src, T / n / src.name)
        shutil.copy2(Path(a.v1).parent / "comun_S1quater.py", T / n / "comun_S1quater.py")
    p1 = correr(T / "v1" / Path(a.v1).name, a, T / "poblaciones_v1.json")
    p2 = correr(T / "v2" / Path(a.v2).name, a, T / "poblaciones_v2.json")

    sys.path.insert(0, str(T / "v2"))
    import poblaciones_S1quater_v2 as V2  # noqa: E402,PLC0415
    diez = {t["id"] for t in json.loads(Path(a.tanda0).read_text(encoding="utf-8"))["tos"]}
    en_152 = {t["id"] for t in json.loads(Path(a.manifiesto_tos).read_text(encoding="utf-8"))["tos"]}
    t0 = diez & en_152   # lo esperado; la versión 2 tiene que dar exactamente esto
    es_t0 = lambda u: u.split("::")[0] in t0  # noqa: E731
    res = []

    def ok(c: bool, q: str) -> None:
        res.append((c, q))

    ok(set(V2.TANDA0_FUERA) == t0, "TANDA0_FUERA son exactamente los documentos de la tanda 0 que están en el manifiesto de los 152")
    ok(all(es_t0(u) is False for g in p2["cortes"].values() for u in g["ids"]), "la versión 2 no deja ninguna unidad de esos documentos en la población")
    ok(any(es_t0(u) for g in p1["cortes"].values() for u in g["ids"]), "la versión 1 sí las tenía (la adenda hace falta)")
    ok(all(p2["cortes"][e]["ids"] == [u for u in p1["cortes"][e]["ids"] if not es_t0(u)] for e in p1["cortes"]),
       "en cada estrato, la versión 2 da los ids de la versión 1 menos los de esos documentos, en el mismo orden")
    t0_v1 = {(e, u) for e, g in p1["cortes"].items() for u in g["ids"] if es_t0(u)} | \
            {(x["estrato"], x["id"]) for x in p1["salen_por_leidas_en_S1ter"] if es_t0(x["id"])}
    c1 = {(x["estrato"], x["id"], x["motivo"]) for x in p1["salen_por_construccion"]}
    c2 = {(x["estrato"], x["id"], x["motivo"]) for x in p2["salen_por_construccion"]}
    ok(c2 == c1 | {(e, u, V2.TANDA0) for e, u in t0_v1}, "salen por construcción las de la versión 1 más todas las de esos documentos, con el motivo de la adenda")
    ok([x for x in p2["salen_por_leidas_en_S1ter"]] == [x for x in p1["salen_por_leidas_en_S1ter"] if not es_t0(x["id"])],
       "salen por leídas en S1-ter las de la versión 1 menos las de esos documentos, que ya salieron por construcción")
    ok(all(p2[k] == p1[k] for k in ("insumos", "mostradas_en_S1ter", "ri2_pm_cruzan_fichas", "alineacion_por_to", "umbral_de_cobertura")),
       "insumos, unidades mostradas, ri2_pm, alineación y umbral: iguales")
    ok(all(p2["cortes"][e][k] == p1["cortes"][e][k] for e in p1["cortes"] for k in ("semilla", "n", "tos")),
       "semilla, tamaño y documentos de cada estrato: iguales")
    tot = sum(g["unidades"] for g in p2["cortes"].values())
    ok(p2["cortes_total"] == tot and all(abs(g["peso"] - g["unidades"] / tot) < 1e-12 and g["unidades"] == len(g["ids"])
                                         for g in p2["cortes"].values()),
       "los pesos de la versión 2 se recalculan sobre sus unidades")
    for c, q in res:
        print(("ok   " if c else "MAL  ") + q)
    print(f"{sum(c for c, _ in res)} de {len(res)} controles ok")
    sys.exit(0 if all(c for c, _ in res) else 1)


if __name__ == "__main__":
    main()
