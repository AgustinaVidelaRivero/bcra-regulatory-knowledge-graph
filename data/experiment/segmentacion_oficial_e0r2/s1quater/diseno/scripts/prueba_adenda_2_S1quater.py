"""U-SEG-OFICIAL, S1-quater, adenda 2 al diseño: prueba de `poblaciones_S1quater_v3.py` contra la versión 2 (mesa, 12/10/2026; USD 0,
sin API). Corre las dos versiones sobre las mismas entradas, en una carpeta nueva, y controla que la versión 3 dé lo mismo que la 2
salvo que salen, declaradas, las unidades de diseño de S0-6a (la lista sellada fuera del repo, `--diseno-s0-6a`).

Uso: python3 -B prueba_adenda_2_S1quater.py --v2 <poblaciones_S1quater_v2.py> --v3 <poblaciones_S1quater_v3.py>
       --e0 <carpeta e0/ de la E0 de S1-ter> --manifest <s1ter/manifest_salida.json> --manifiesto-tos <…_152.json>
       --orden-s1ter <s1ter/tramo_b/orden_lectura_S1ter.json> --diseno-s0-6a <NO_ABRIR_unidades_diseno_guardas_A_S0-6a.json>
       --trabajo <carpeta nueva>

La E0 de S1-ter hace de E0 corregida, como en la prueba de la adenda 1: así las dos versiones leen los mismos datos reales, y la
diferencia es solo la de la adenda. Con la misma E0, cada unidad de diseño solapa solo consigo misma. La salida estándar no trae
cifras ni ids: solo ok o MAL por control.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SHA_MANIFEST = "5e63dff235326c4b2bb73cb95ca409037afa93fbb4903fe89fbd59b17dccc432"   # s1ter/manifest_salida.json
TO_DISENO = "ri_oc"   # el documento de las dos guardas (DISENO_S0-6a.md, §6)
N_DISENO = 4          # el preámbulo y tres unidades del Anexo II, en la E0 de S1-ter


def correr(script: Path, a, out: Path, extra: list[str]) -> dict:
    # cada versión corre desde su propia carpeta, junto a una copia de comun_S1quater.py
    r = subprocess.run([sys.executable, "-B", str(script), "--e0-nuevo", a.e0, "--manifest-nuevo", a.manifest,
                        "--sha-manifest-nuevo", SHA_MANIFEST, "--e0-viejo", a.e0, "--manifest-viejo", a.manifest,
                        "--manifiesto-tos", a.manifiesto_tos, "--orden-s1ter", a.orden_s1ter, *extra, "--out", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"FRENO: {script.name} no corrió: {r.stderr[-400:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("v2", "v3", "e0", "manifest", "manifiesto_tos", "orden_s1ter", "diseno_s0_6a", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    T = Path(a.trabajo)
    if T.exists():
        raise SystemExit("FRENO: la carpeta de trabajo ya existe")
    for n in ("v2", "v3"):
        (T / n).mkdir(parents=True)
        src = Path(getattr(a, n))
        shutil.copy2(src, T / n / src.name)
        shutil.copy2(Path(a.v2).parent / "comun_S1quater.py", T / n / "comun_S1quater.py")
    p2 = correr(T / "v2" / Path(a.v2).name, a, T / "poblaciones_v2.json", [])
    p3 = correr(T / "v3" / Path(a.v3).name, a, T / "poblaciones_v3.json", ["--diseno-s0-6a", a.diseno_s0_6a])

    d = set(json.loads(Path(a.diseno_s0_6a).read_text(encoding="utf-8"))["ids_e0_S1ter"])
    orden = json.loads(Path(a.orden_s1ter).read_text(encoding="utf-8"))
    sys.path.insert(0, str(T / "v3"))
    import comun_S1quater as Q  # noqa: E402,PLC0415
    mostradas = set(Q.mostradas_S1ter(orden, Q.E0(Path(a.e0))))
    res = []

    def ok(c: bool, q: str) -> None:
        res.append((c, q))

    ok(len(d) == N_DISENO and all(u.split("::")[0] == TO_DISENO for u in d),
       "la lista de diseño trae las unidades esperadas, todas del documento de las dos guardas")
    ok(not (d & mostradas), "ninguna unidad de diseño está entre las leídas en S1-ter (si no, ya salían por leídas)")
    ok(any(u in d for g in p2["cortes"].values() for u in g["ids"]), "la versión 2 sí las tenía en la población (la adenda hace falta)")
    ok(all(p3["cortes"][e]["ids"] == [u for u in p2["cortes"][e]["ids"] if u not in d] for e in p2["cortes"]),
       "en cada estrato, la versión 3 da los ids de la versión 2 menos las unidades de diseño, en el mismo orden")
    ok({x["id"] for x in p3["salen_por_diseno_S0_6a"]} == d and all(x["mismo_id"] for x in p3["salen_por_diseno_S0_6a"]),
       "salen por diseño exactamente las de la lista, por el mismo id (con la misma E0 no hay otras)")
    ok(p3["salen_por_construccion"] == p2["salen_por_construccion"] and p3["salen_por_leidas_en_S1ter"] == p2["salen_por_leidas_en_S1ter"],
       "salen por construcción y por leídas en S1-ter las mismas que en la versión 2")
    ok(all(p3[k] == p2[k] for k in ("mostradas_en_S1ter", "ri2_pm_cruzan_fichas", "alineacion_por_to", "umbral_de_cobertura"))
       and {k: v for k, v in p3["insumos"].items() if k != "diseno_S0_6a_sha256"} == p2["insumos"],
       "insumos, unidades mostradas, ri2_pm, alineación y umbral: iguales (los insumos suman el sha256 de la lista)")
    ok(all(p3["cortes"][e][k] == p2["cortes"][e][k] for e in p2["cortes"] for k in ("semilla", "n", "tos")),
       "semilla, tamaño y documentos de cada estrato: iguales")
    tot = sum(g["unidades"] for g in p3["cortes"].values())
    ok(p3["cortes_total"] == tot and all(abs(g["peso"] - g["unidades"] / tot) < 1e-12 and g["unidades"] == len(g["ids"])
                                         for g in p3["cortes"].values()),
       "los pesos de la versión 3 se recalculan sobre sus unidades")
    for c, q in res:
        print(("ok   " if c else "MAL  ") + q)
    print(f"{sum(c for c, _ in res)} de {len(res)} controles ok")
    sys.exit(0 if all(c for c, _ in res) else 1)


if __name__ == "__main__":
    main()
