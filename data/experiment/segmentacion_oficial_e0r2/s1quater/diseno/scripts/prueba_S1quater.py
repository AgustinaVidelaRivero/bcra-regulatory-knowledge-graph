"""U-SEG-OFICIAL, S1-quater: prueba de los scripts del diseño (mesa, 11/10/2026; USD 0, sin API). No sortea nada real.

Uso, sobre una COPIA (CLAUDE.md §4.l): python3 -B prueba_S1quater.py --copia <carpeta con s1ter/ y pdfs/> --s1ter-scripts <copia de
       s1ter/scripts de HEAD> --planillas-s1ter <copia de s1ter/tramo_b de HEAD> --trabajo <carpeta nueva>

- Casos sintéticos: la alineación (igual, corte corrido, partida, unida, id cambiado, texto nuevo, restos quitados), la exclusión,
  el sorteo (con una población inventada) y la regresión (con marcas inventadas sobre los ids de las fichas de S1-ter).
- Con los datos de S1-ter, sin marcas: las fichas reproducen byte a byte las dos carpetas finales de S1-ter y sus planillas vacías;
  las poblaciones sobre la misma E0 dan las de S1-ter menos las unidades que mostró S1-ter; una E0 «corregida» inventada (una unidad
  mostrada partida en dos, un corte corrido hacia la unidad que sigue y un id cambiado) da las exclusiones esperadas.
La salida trae solo «ok» o «MAL» por caso, con texto fijo: ninguna cifra ni marca de S1-ter.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_S1quater as Q  # noqa: E402
import sorteo_S1quater as S  # noqa: E402

AQUI = Path(__file__).resolve().parent
res: list[tuple[bool, str]] = []


def ok(c, q):
    res.append((bool(c), q))


def u(uid: str, texto: str) -> dict:
    return {"id": uid, "texto": texto, "sha256_propio": hashlib.sha256(texto.encode("utf-8")).hexdigest()}


def frena(f) -> bool:
    try:
        f()
    except SystemExit as ex:
        return str(ex).startswith("FRENO")
    return False


def correr(args: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B"] + [str(x) for x in args], capture_output=True, text=True, cwd=cwd)


def sinteticos(T: Path) -> None:
    ok(Q.tokens("Refinancia-\nción del Pérez, 3.5 %") == ["refinanciacion", "del", "perez", "3", "5"],
       "tokens: une el guion de fin de renglón, saca tildes y deja letras y dígitos")
    A = u("d::1", "Primer punto con su texto propio completo.")
    B = u("d::2", "Segundo punto, que dice otra cosa distinta. Y termina acá.")
    C = u("d::3", "Tercer punto final del documento.")
    al = Q.alinear_to([A, B, C], [A, B, C])
    ok(al["solapes"] == {"d::1": ["d::1"], "d::2": ["d::2"], "d::3": ["d::3"]} and al["cobertura"] == 1.0, "alineación: igual")
    A2 = u("d::1", A["texto"] + " Segundo punto, que dice otra cosa distinta.")
    B2 = u("d::2", "Y termina acá.")
    al = Q.alinear_to([A, B, C], [A2, B2, C])
    ok(al["solapes"]["d::1"] == ["d::1", "d::2"] and al["solapes"]["d::2"] == ["d::2"] and al["solapes"]["d::3"] == ["d::3"],
       "alineación: el corte corrido hace que la primera solape las dos viejas")
    Ba, Bb = u("d::2::a", "Segundo punto, que dice otra cosa distinta."), u("d::2::b", "Y termina acá.")
    al = Q.alinear_to([A, B, C], [A, Ba, Bb, C])
    ok(al["solapes"]["d::2::a"] == ["d::2"] and al["solapes"]["d::2::b"] == ["d::2"], "alineación: una unidad partida en dos")
    AB = u("d::1", A["texto"] + " " + B["texto"])
    al = Q.alinear_to([A, B, C], [AB, C])
    ok(al["solapes"]["d::1"] == ["d::1", "d::2"], "alineación: dos unidades unidas en una")
    al = Q.alinear_to([A, B, C], [A, u("d::9", B["texto"]), C])
    ok(al["solapes"]["d::9"] == ["d::2"], "alineación: el mismo texto con otro id")
    N = u("d::1bis", "Párrafo nuevo que la segmentación vieja no traía en ninguna parte.")
    al = Q.alinear_to([A, B, C], [A, N, B, C])
    ok(al["solapes"]["d::1bis"] == [] and al["cobertura"] == 1.0, "alineación: el texto nuevo no solapa ninguna vieja")
    largo = " ".join(f"termino{k} de la norma" for k in range(100))           # una unidad de unos 400 tokens
    Bl = u("d::2", largo)
    al = Q.alinear_to([A, u("d::2", largo + " Página 12 de 40 Comunicación A 9999"), C], [A, Bl, C])
    ok(al["solapes"]["d::2"] == ["d::2"] and al["cobertura"] >= Q.UMBRAL_COBERTURA,
       "alineación: quitar los restos de un pie de una unidad larga la deja en su lugar y la cobertura sobre el umbral")
    # exclusión, con dos E0 inventadas
    for nombre, chunks in (("viejo", [A, B, C]), ("nuevo", [A2, B2, u("d::3b", C["texto"])])):
        (T / nombre).mkdir(parents=True)
        (T / nombre / "chunks_d.json").write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    ex = Q.excluir(Q.E0(T / "viejo"), Q.E0(T / "nuevo"), {"d::2"}, ["d"])
    ok(set(ex["excluidas"]) == {"d::1", "d::2"} and ex["excluidas"]["d::1"] == {"mismo_id": False, "solapa_con": ["d::2"]}
       and ex["excluidas"]["d::2"]["mismo_id"], "exclusión: sale la del mismo id y la que solapa una mostrada; la otra queda")
    ex = Q.excluir(Q.E0(T / "viejo"), Q.E0(T / "nuevo"), {"d::3"}, ["d"])
    ok(set(ex["excluidas"]) == {"d::3b"}, "exclusión: una mostrada con otro id sale por su texto")
    (T / "nuevo_mal").mkdir()
    (T / "nuevo_mal" / "chunks_d.json").write_text(json.dumps([u("d::1", "Texto que no tiene nada que ver con nada.")]),
                                                   encoding="utf-8")
    ok(frena(lambda: Q.excluir(Q.E0(T / "viejo"), Q.E0(T / "nuevo_mal"), set(), ["d"])),
       "exclusión: frena si la alineación cubre menos que el umbral")
    ok(frena(lambda: Q.excluir(Q.E0(T / "viejo"), Q.E0(T / "nuevo"), set(), ["d", "falta"])), "exclusión: frena si falta un TO")
    # sorteo, con una población inventada
    pob = {"cortes": {}}
    for e, n in Q.ESTRATOS.items():
        ids = sorted(f"inv{e}::{k}" for k in range(n * 3))
        pob["cortes"][e] = {"semilla": f"{Q.SEMILLA}:{e}", "n": n, "unidades": len(ids), "sha256_ids_ordenados": Q.sha_ids(ids),
                            "ids": ids}
    cortes, orden, estrato_de = S.sortear(pob)
    ok(all(cortes[e]["muestra"] == random.Random(f"U-SEG-OFICIAL:cortes:S1-quater:{e}").sample(pob["cortes"][e]["ids"], n)
           for e, n in Q.ESTRATOS.items()), "sorteo: cada estrato con su cadena, como S1-ter")
    ok(orden == random.Random("U-SEG-OFICIAL:cortes:S1-quater:orden").sample(sorted(orden), len(orden)) and len(set(orden)) == 90,
       "sorteo: el orden de las 90 con su semilla, sin agrupar por estrato")
    ok(S.sortear(pob) == (cortes, orden, estrato_de), "sorteo: otra corrida da lo mismo")
    malo = json.loads(json.dumps(pob))
    malo["cortes"]["vigente"]["ids"] = malo["cortes"]["vigente"]["ids"][1:]
    ok(frena(lambda: S.sortear(malo)), "sorteo: frena si una población no es la sellada")


def con_datos(cop: Path, scr: Path, pls: Path, T: Path) -> None:
    orden_p = cop / "s1ter/tramo_b/orden_lectura_S1ter.json"
    e0v = cop / "s1ter/e0"
    man_v = cop / "s1ter/manifest_salida.json"
    man_tos = cop / "s1ter/manifiesto/segmentacion_oficial_e0r2_152.json"
    # 1. las copias literales del formato
    fq = (AQUI / "fichas_S1quater.py").read_text(encoding="utf-8").split("\n")
    f1 = (scr / "fichas_S1ter.py").read_text(encoding="utf-8").split("\n")
    fn = (scr / "fichas_numero_S1ter.py").read_text(encoding="utf-8").split("\n")
    i = fq.index("# ---- copia literal de s1ter/scripts/fichas_S1ter.py:34-51 ----") + 1
    j = fq.index("# ---- copia literal de s1ter/scripts/fichas_numero_S1ter.py:28-30 y :39-41 ----") + 1
    k = fq.index("# ---- fin de las copias ----")
    ok(fq[i:j - 1] == f1[33:50] and fq[j:j + 2] == [fn[27], fn[29]] and fq[j + 2:k] == ["", ""] + fn[38:41],
       "las constantes de formato son copia literal de los dos scripts de fichas de S1-ter")
    # 2. las fichas reproducen las dos carpetas finales de S1-ter
    r = correr([AQUI / "fichas_S1quater.py", "--orden", orden_p, "--sha-orden", Q.SHA_ORDEN_S1TER, "--e0", e0v, "--pdfs",
                cop / "pdfs", "--out", T / "fichas/carpeta", "--registro", T / "fichas/registro.json", "--planillas",
                T / "fichas/planillas", "--sufijo", "S1ter"], cop)
    b2 = json.loads((cop / "s1ter/tramo_b2/fichas_numero_registro_S1ter.json").read_text(encoding="utf-8"))
    reg = json.loads((T / "fichas/registro.json").read_text(encoding="utf-8")) if r.returncode == 0 else {"etapas": {}}
    ok(r.returncode == 0 and all(reg["etapas"][e]["manifest_sha256"] == b2["etapas"][e]["manifest_despues"]
                                 for e in ("etapa_1", "etapa_2")),
       "fichas: con el orden y la E0 de S1-ter, las dos carpetas son byte a byte las finales de S1-ter")
    ok(all(Q.sha(T / f"fichas/planillas/planilla_etapa_{e}_S1ter.tsv") == Q.sha(pls / f"planilla_etapa_{e}_S1ter.tsv")
           for e in (1, 2)), "fichas: las planillas vacías son las de S1-ter")
    r2 = correr([AQUI / "fichas_S1quater.py", "--orden", orden_p, "--sha-orden", "0" * 64, "--e0", e0v, "--pdfs", cop / "pdfs",
                 "--out", T / "fichas_mal/c", "--registro", T / "fichas_mal/r.json", "--planillas", T / "fichas_mal/p"], cop)
    ok(r2.returncode != 0 and not (T / "fichas_mal").exists(), "fichas: un orden que no da su sello no arma nada")
    # 3. poblaciones sobre la misma E0
    base = [AQUI / "poblaciones_S1quater.py", "--e0-viejo", e0v, "--manifest-viejo", man_v, "--manifiesto-tos", man_tos,
            "--orden-s1ter", orden_p]
    r = correr(base + ["--e0-nuevo", e0v, "--manifest-nuevo", man_v, "--sha-manifest-nuevo", Q.SHA_MANIFEST_SALIDA_S1TER,
                       "--out", T / "pob_identidad.json"], cop)
    fin = json.loads((cop / "s1ter/tramo_b/poblaciones_finales_S1ter.json").read_text(encoding="utf-8"))
    orden = json.loads(orden_p.read_text(encoding="utf-8"))
    viejo = Q.E0(e0v)
    mostradas = Q.mostradas_S1ter(orden, viejo)
    p = json.loads((T / "pob_identidad.json").read_text(encoding="utf-8")) if r.returncode == 0 else None
    ok(p is not None and all(p["cortes"][e]["ids"] == sorted(set(fin["cortes"][e]["ids"]) - set(mostradas)) for e in Q.ESTRATOS),
       "poblaciones, misma E0: las de S1-ter menos las unidades que mostró S1-ter")
    ok(p is not None and all(x["mismo_id"] and x["solapa_con"] == [x["id"]] for x in p["salen_por_leidas_en_S1ter"])
       and all(v["cobertura"] == 1.0 for v in p["alineacion_por_to"].values()),
       "poblaciones, misma E0: salen solo por el mismo id, con cobertura completa")
    ok(p is not None and sorted(x["id"] for x in p["salen_por_construccion"])
       == sorted(s["id"] for s in fin["salen"] if s["poblacion"].startswith("cortes")),
       "poblaciones, misma E0: la regla de construcción saca las mismas que en S1-ter")
    # 4. una E0 «corregida» inventada: una unidad mostrada partida en dos, con su última palabra corrida a la que sigue, y una
    #    unidad no mostrada de otro TO con otro id
    pob_ids = {i for g in p["cortes"].values() for i in g["ids"]}
    tos_pob = {t for g in p["cortes"].values() for t in g["tos"]}

    def sirve(i: str) -> bool:
        if Q.RE_PARTE.match(i):
            return False
        pal = viejo.por_id(i)["texto"].split(" ")
        s = viejo.siguiente(i)
        return len(pal) >= 12 and any(t.isalpha() for t in Q.tokens(pal[-1])) and s is not None and s["id"] in pob_ids

    elegida = next(i for i in sorted(f["id"] for f in orden["etapa_1"]["fichas"]) if sirve(i))
    to = elegida.split("::")[0]
    otro_to = next(t for t in sorted(tos_pob) if t != to and any(c["id"] in pob_ids for c in viejo.chunks(t)))
    renombrar = next(c["id"] for c in viejo.chunks(otro_to) if c["id"] in pob_ids)

    def con(c: dict, texto: str, nid: str | None = None) -> dict:
        d = dict(c)
        d["texto"], d["sha256_propio"] = texto, hashlib.sha256(texto.encode("utf-8")).hexdigest()
        if nid:
            d["id"] = nid
        return d

    nuevo = T / "e0_inventada"
    shutil.copytree(e0v, nuevo)
    ch = json.loads((nuevo / f"chunks_{to}.json").read_text(encoding="utf-8"))
    k = next(n for n, c in enumerate(ch) if c["id"] == elegida)
    pal = ch[k]["texto"].split(" ")
    mitad = len(pal) // 2
    sig = ch[k + 1]
    ch[k:k + 2] = [con(ch[k], " ".join(pal[:mitad]), elegida + "::a"), con(ch[k], " ".join(pal[mitad:-1]), elegida + "::b"),
                   con(sig, pal[-1] + " " + sig["texto"])]
    (nuevo / f"chunks_{to}.json").write_text(json.dumps(ch, ensure_ascii=False, indent=1), encoding="utf-8")
    cho = json.loads((nuevo / f"chunks_{otro_to}.json").read_text(encoding="utf-8"))
    renombrada = renombrar + "::renombrada"
    cho = [con(c, c["texto"], renombrada) if c["id"] == renombrar else c for c in cho]
    (nuevo / f"chunks_{otro_to}.json").write_text(json.dumps(cho, ensure_ascii=False, indent=1), encoding="utf-8")
    man_n = {"version_e0": "inventada para la prueba", "commit_codigo": None,
             "sha256": {f"e0/{x.name}": {"sha256": Q.sha(x)} for x in sorted(nuevo.iterdir()) if x.is_file()}}
    (T / "manifest_inventado.json").write_text(json.dumps(man_n, ensure_ascii=False), encoding="utf-8")
    r = correr(base + ["--e0-nuevo", nuevo, "--manifest-nuevo", T / "manifest_inventado.json", "--sha-manifest-nuevo",
                       Q.sha(T / "manifest_inventado.json"), "--out", T / "pob_inventada.json"], cop)
    q = json.loads((T / "pob_inventada.json").read_text(encoding="utf-8")) if r.returncode == 0 else None
    salen = {x["id"]: x for x in q["salen_por_leidas_en_S1ter"]} if q else {}
    ok(q is not None and all(salen.get(elegida + s, {}).get("solapa_con") == [elegida] for s in ("::a", "::b")),
       "E0 inventada: las dos partes de una unidad mostrada salen por solapar su texto")
    ok(q is not None and sig["id"] in salen and salen[sig["id"]]["solapa_con"] == [elegida] and not salen[sig["id"]]["mismo_id"],
       "E0 inventada: la que sigue, con el corte corrido hacia ella, sale por solapar la mostrada")
    todas_q = {i for g in q["cortes"].values() for i in g["ids"]} if q else set()
    ok(renombrada in todas_q and renombrar not in todas_q,
       "E0 inventada: una unidad no mostrada con otro id queda en la población, con su id nuevo")
    ok(todas_q == (pob_ids - {sig["id"], renombrar}) | {renombrada}, "E0 inventada: fuera de esos casos, la población no cambia")
    # 5. la regresión, con marcas inventadas sobre los ids de las fichas de S1-ter
    f1s = orden["etapa_1"]["fichas"]
    f2s = orden["etapa_2"]["fichas"]
    e1_err, e2_err, e2_her = f1s[4]["id_opaco"], f2s[2]["id_opaco"], f2s[19]["id_opaco"]
    e2_cierre = next(f["id_opaco"] for f in f2s[9:] if viejo.siguiente(f["id"]) is not None)
    for e, fs, err in ((1, f1s, e1_err), (2, f2s, e2_err)):
        with open(T / f"adjudicada_{e}.tsv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional",
                                               "limpieza", "nota"), delimiter="\t", lineterminator="\n")
            w.writeheader()
            for f in fs:
                w.writerow({"ficha": f["id_opaco"], "paginas": "1", "marca": "error" if f["id_opaco"] == err else "correcta",
                            "clase": "corte" if f["id_opaco"] == err else ""})
    (T / "registro_adj.json").write_text(json.dumps({"cierres_confirmados": [{"ficha": e2_cierre, "clase_que_sigue": "corte"}],
                                                     "herencias_confirmadas": [{"ficha": e2_her}]}), encoding="utf-8")
    args = ["--adjudicada-1", T / "adjudicada_1.tsv", "--sha-adjudicada-1", Q.sha(T / "adjudicada_1.tsv"),
            "--adjudicada-2", T / "adjudicada_2.tsv", "--sha-adjudicada-2", Q.sha(T / "adjudicada_2.tsv"),
            "--registro-adjudicacion", T / "registro_adj.json", "--sha-registro-adjudicacion", Q.sha(T / "registro_adj.json"),
            "--orden-s1ter", orden_p, "--e0-viejo", e0v, "--manifest-viejo", man_v]
    r = correr([AQUI / "regresion_S1quater.py"] + args + ["--e0-nuevo", e0v, "--manifest-nuevo", man_v, "--sha-manifest-nuevo",
                                                         Q.SHA_MANIFEST_SALIDA_S1TER, "--out", T / "regresion_igual.json"], cop)
    g = json.loads((T / "regresion_igual.json").read_text(encoding="utf-8")) if r.returncode == 0 else None
    por_op = {f["id_opaco"]: f for f in f1s + f2s}
    esperadas = sorted({por_op[e1_err]["id"], *por_op[e2_err]["unidades_calificadas"],
                        viejo.siguiente(por_op[e2_cierre]["id"])["id"], *por_op[e2_her]["unidades_calificadas"]})
    ok(g is not None and g["unidades_viejas"] == esperadas and g["ids"] == esperadas and not g["sin_unidad_nueva"],
       "regresión, misma E0: marca, unidad que sigue y herencia dan las unidades esperadas, y cada una se lleva a sí misma")
    ok(g is not None and all(f["id"] not in g["ids"] for f in f1s if f["id_opaco"] != e1_err),
       "regresión: las fichas sin error confirmado no entran")
    r2 = correr([AQUI / "regresion_S1quater.py"] + args[:3] + ["0" * 64] + args[4:] + ["--e0-nuevo", e0v, "--manifest-nuevo",
                                                                                       man_v, "--sha-manifest-nuevo",
                                                                                       Q.SHA_MANIFEST_SALIDA_S1TER, "--out",
                                                                                       T / "regresion_mal.json"], cop)
    ok(r2.returncode != 0 and not (T / "regresion_mal.json").exists(), "regresión: una planilla que no da su sello no arma nada")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("copia", "s1ter_scripts", "planillas_s1ter", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    if a.trabajo.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    (a.trabajo / "sinteticos").mkdir(parents=True)
    sinteticos(a.trabajo / "sinteticos")
    con_datos(a.copia.resolve(), a.s1ter_scripts.resolve(), a.planillas_s1ter.resolve(), a.trabajo.resolve())
    for b, q in res:
        print(("ok   " if b else "MAL  ") + q)
    print(f"{sum(b for b, _ in res)} de {len(res)} casos ok")
    sys.exit(0 if all(b for b, _ in res) else 1)


if __name__ == "__main__":
    main()
