"""U-SEG-OFICIAL, S1-quater, adenda 4 al diseño: prueba de `poblaciones_S1quater_v5.py` contra la versión 4 (mesa, 12-13/10/2026;
USD 0, sin API). Corre las dos versiones en una carpeta nueva, en dos partes:
- A, sobre la E0 de S1-ter: la versión 5 da lo mismo que la 4 salvo que salen, declaradas, las unidades de la adenda 4 (la lista
  sellada fuera del repo, `--adenda-4`);
- B, sobre la E0 corregida de S0-6a-bis (controlada contra su manifiesto): la cobertura de la adenda 4, §1. La versión 4 frena por
  cobertura; la 5 no frena, y saca lo que dicen las opciones 1 y 2.

Uso: python3 -B prueba_adenda_4_S1quater.py --v4 <poblaciones_S1quater_v4.py> --v5 <poblaciones_S1quater_v5.py>
       --e0 <carpeta e0/ de la E0 de S1-ter> --manifest <s1ter/manifest_salida.json> --manifiesto-tos <…_152.json>
       --orden-s1ter <s1ter/tramo_b/orden_lectura_S1ter.json> --diseno-s0-6a <NO_ABRIR_unidades_diseno_guardas_A_S0-6a.json>
       --adenda-3 <NO_ABRIR_unidades_adenda_3_S1quater.json> --adenda-4 <NO_ABRIR_unidades_adenda_4_S1quater.json>
       --e0-corregida <carpeta de la E0 de S0-6a-bis> --manifest-corregida <su manifiesto> --sha-manifest-corregida <su sha256>
       --trabajo <carpeta nueva>

En la parte A, la E0 de S1-ter hace de E0 corregida, como en las pruebas de las adendas 1 a 3: las dos versiones leen los mismos datos
reales, y la diferencia es solo la de la adenda. Con la misma E0, cada unidad de la lista solapa solo consigo misma y ningún documento
queda bajo el umbral. La parte B recalcula por su cuenta lo que tiene que salir. La salida estándar no trae ids: solo ok o MAL por
control.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SHA_MANIFEST = "5e63dff235326c4b2bb73cb95ca409037afa93fbb4903fe89fbd59b17dccc432"   # s1ter/manifest_salida.json
N_GRUPOS = {"vistas_por_la_mesa_antes_del_78": 108,
            "vistas_por_la_mesa_81": 5,
            "vistas_por_la_ejecutora_S0-6a-bis_antes_del_censo": 87,
            "vistas_por_la_ejecutora_S0-6a-bis_despues_del_censo": 29,
            "mostradas_por_archivos_del_registro": 93,
            "en_la_memoria_de_la_mesa": 29,
            "vistas_por_la_ejecutora_S0-6a": 450,
            "vistas_por_la_mesa_82": 0,
            "declaradas_de_diseno_por_la_ejecutora": 0,
            "vistas_como_imagen_en_el_78": 0}   # unidades de la E0 de S1-ter por grupo, fijadas al sellar la adenda 4


def correr(script: Path, a, out: Path, extra: list[str], nuevo: tuple | None = None, frena: bool = False):
    # cada versión corre desde su propia carpeta, junto a una copia de comun_S1quater.py
    e0n, man_n, sha_n = nuevo or (a.e0, a.manifest, SHA_MANIFEST)
    r = subprocess.run([sys.executable, "-B", str(script), "--e0-nuevo", e0n, "--manifest-nuevo", man_n,
                        "--sha-manifest-nuevo", sha_n, "--e0-viejo", a.e0, "--manifest-viejo", a.manifest,
                        "--manifiesto-tos", a.manifiesto_tos, "--orden-s1ter", a.orden_s1ter,
                        "--diseno-s0-6a", a.diseno_s0_6a, "--adenda-3", a.adenda_3, *extra, "--out", str(out)],
                       capture_output=True, text=True)
    if frena:
        return r
    if r.returncode != 0:
        raise SystemExit(f"FRENO: {script.name} no corrió: {r.stderr[-400:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("v4", "v5", "e0", "manifest", "manifiesto_tos", "orden_s1ter", "diseno_s0_6a", "adenda_3", "adenda_4", "e0_corregida",
              "manifest_corregida", "sha_manifest_corregida", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    T = Path(a.trabajo)
    if T.exists():
        raise SystemExit("FRENO: la carpeta de trabajo ya existe")
    for n in ("v4", "v5"):
        (T / n).mkdir(parents=True)
        src = Path(getattr(a, n))
        shutil.copy2(src, T / n / src.name)
        shutil.copy2(Path(a.v4).parent / "comun_S1quater.py", T / n / "comun_S1quater.py")
    p3 = correr(T / "v4" / Path(a.v4).name, a, T / "poblaciones_v4.json", [])
    p4 = correr(T / "v5" / Path(a.v5).name, a, T / "poblaciones_v5.json", ["--adenda-4", a.adenda_4])

    ad4 = json.loads(Path(a.adenda_4).read_text(encoding="utf-8"))
    d4 = set(ad4["ids_e0_S1ter"])
    d3 = set(json.loads(Path(a.adenda_3).read_text(encoding="utf-8"))["ids_e0_S1ter"])
    d2 = set(json.loads(Path(a.diseno_s0_6a).read_text(encoding="utf-8"))["ids_e0_S1ter"])
    orden = json.loads(Path(a.orden_s1ter).read_text(encoding="utf-8"))
    sys.path.insert(0, str(T / "v5"))
    import comun_S1quater as Q  # noqa: E402,PLC0415
    mostradas = set(Q.mostradas_S1ter(orden, Q.E0(Path(a.e0))))
    v4_ids = {u for g in p3["cortes"].values() for u in g["ids"]}
    res = []

    def ok(c: bool, q: str) -> None:
        res.append((c, q))

    n_grupos = N_GRUPOS
    ok({g: len(v["ids"]) for g, v in ad4["grupos"].items()} == n_grupos
       and set().union(*(set(v["ids"]) for v in ad4["grupos"].values())) == d4 and len(d4) == sum(n_grupos.values()),
       "la lista de la adenda 4 trae las unidades esperadas por grupo, y sus grupos la cubren sin repetir")
    ok(not (d4 & mostradas) and not (d4 & d2) and not (d4 & d3),
       "ninguna unidad de la lista está entre las leídas en S1-ter ni en las adendas 2 y 3")
    ok(bool(d4 & v4_ids), "la versión 4 sí tenía unidades de la lista en la población (la adenda hace falta)")
    ok(all(p4["cortes"][e]["ids"] == [u for u in p3["cortes"][e]["ids"] if u not in d4] for e in p3["cortes"]),
       "en cada estrato, la versión 5 da los ids de la versión 4 menos las de la lista, en el mismo orden")
    ok({x["id"] for x in p4["salen_por_adenda_4"]} == d4 & v4_ids and all(x["mismo_id"] for x in p4["salen_por_adenda_4"]),
       "salen por la adenda 4 exactamente las de la lista que estaban en la población, por el mismo id (con la misma E0 no hay otras)")
    ok(all(x["grupos"] and x["motivo"] for x in p4["salen_por_adenda_4"]), "cada una sale declarada, con su grupo y su motivo")
    ok(all(p4[k] == p3[k] for k in ("salen_por_construccion", "salen_por_leidas_en_S1ter", "salen_por_diseno_S0_6a", "salen_por_adenda_3")),
       "salen por construcción, por leídas en S1-ter y por las adendas 2 y 3 las mismas que en la versión 4")
    ok(all(p4[k] == p3[k] for k in ("mostradas_en_S1ter", "ri2_pm_cruzan_fichas", "alineacion_por_to", "umbral_de_cobertura",
                                    "diseno_S0_6a", "adenda_3"))
       and {k: v for k, v in p4["insumos"].items() if k != "adenda_4_sha256"} == p3["insumos"],
       "insumos, unidades mostradas, ri2_pm, alineación, umbral y adendas 2 y 3: iguales (los insumos suman el sha256 de la lista)")
    ok(all(p4["cortes"][e][k] == p3["cortes"][e][k] for e in p3["cortes"] for k in ("semilla", "n", "tos")),
       "semilla, tamaño y documentos de cada estrato: iguales")
    tot = sum(g["unidades"] for g in p4["cortes"].values())
    ok(p4["cortes_total"] == tot and all(abs(g["peso"] - g["unidades"] / tot) < 1e-12 and g["unidades"] == len(g["ids"])
                                         for g in p4["cortes"].values()),
       "los pesos de la versión 5 se recalculan sobre sus unidades")
    # ---- parte B: la E0 corregida de S0-6a-bis
    nuevo = (a.e0_corregida, a.manifest_corregida, a.sha_manifest_corregida)
    r3 = correr(T / "v4" / Path(a.v4).name, a, T / "poblaciones_v4_corregida.json", [], nuevo, frena=True)
    pb = correr(T / "v5" / Path(a.v5).name, a, T / "poblaciones_v5_corregida.json", ["--adenda-4", a.adenda_4], nuevo)
    viejo, nueva = Q.E0(Path(a.e0)), Q.E0(Path(a.e0_corregida))
    tos = sorted(t for g in pb["cortes"].values() for t in g["tos"])
    bajos = pb["cobertura_bajo_el_umbral"]
    sacar = mostradas | d2 | d3 | d4
    al = {t: Q.alinear_to(viejo.chunks(t), nueva.chunks(t)) for t in tos}
    bajos_ind = sorted(t for t in tos if al[t]["cobertura"] < Q.UMBRAL_COBERTURA)
    ok(r3.returncode != 0 and "cubre menos del" in r3.stderr and sorted(bajos) == bajos_ind
       and all(f"'{t}'" in r3.stderr for t in bajos_ind),
       "B. la versión 4 frena por cobertura en la E0 corregida, y nombra los documentos que la versión 5 declara bajo el umbral")
    con_algo = {t for t in bajos_ind if any(u.split("::")[0] == t for u in sacar)}
    ok(all(bajos[t]["tratamiento"] == ("exclusion_sin_orden" if t in con_algo else "sin_freno_nada_que_sacar") for t in bajos_ind),
       "B. la versión 5 no frena, y cada documento bajo el umbral lleva su tratamiento: sin orden si tiene algo que sacar, sin freno si no")
    salen = {x["id"] for k in ("salen_por_construccion", "salen_por_leidas_en_S1ter", "salen_por_diseno_S0_6a", "salen_por_adenda_3",
                                "salen_por_adenda_4") for x in pb[k]}
    quedan = {u for g in pb["cortes"].values() for u in g["ids"]}
    g6 = lambda k: {tuple(k[i:i + 6]) for i in range(len(k) - 5)}  # noqa: E731
    frec = {}
    for d in viejo.tos():
        for c in viejo.chunks(d):
            for g in g6(Q.tokens(c["texto"])):
                frec[g] = frec.get(g, 0) + 1
    deben = set()
    for t in con_algo:
        dist = set().union(*[{g for g in g6(Q.tokens(c["texto"])) if frec[g] <= 2} for c in viejo.chunks(t) if c["id"] in sacar])
        deben |= {c["id"] for c in nueva.chunks(t) if g6(Q.tokens(c["texto"])) & dist}
    ok(bool(deben) and deben <= salen and not (deben & quedan),
       "B. en los documentos con exclusión sin orden, sale toda unidad nueva que comparte un tramo distintivo con una que hay que sacar")
    so = [x for k in ("salen_por_leidas_en_S1ter", "salen_por_diseno_S0_6a", "salen_por_adenda_3", "salen_por_adenda_4")
          for x in pb[k] if x.get("solapa_sin_orden")]
    ok(bool(so) and all(x["id"].split("::")[0] in con_algo and not set(x["solapa_sin_orden"]) & set(x["solapa_con"]) for x in so),
       "B. la exclusión sin orden aparece solo en esos documentos, declarada aparte de lo que da la alineación")
    constr = {x["id"] for x in pb["salen_por_construccion"]}
    esperadas = {c["id"] for t in tos if t not in bajos_ind for c in nueva.chunks(t)
                 if c["id"] not in constr and (c["id"] in sacar or set(al[t]["solapes"][c["id"]]) & sacar)}
    otras = {x["id"] for k in ("salen_por_leidas_en_S1ter", "salen_por_diseno_S0_6a", "salen_por_adenda_3", "salen_por_adenda_4")
             for x in pb[k] if x["id"].split("::")[0] not in bajos_ind}
    ok(esperadas == otras,
       "B. en los demás documentos salen exactamente las del mismo id o las que solapan por la alineación, como en la versión 4")
    for c, q in res:
        print(("ok   " if c else "MAL  ") + q)
    print(f"{sum(c for c, _ in res)} de {len(res)} controles ok")
    sys.exit(0 if all(c for c, _ in res) else 1)


if __name__ == "__main__":
    main()
