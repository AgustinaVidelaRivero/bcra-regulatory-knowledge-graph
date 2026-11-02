"""Control del §4 de S0-6a (U-SEG-OFICIAL; USD 0, sin API): las unidades leídas en S1-ter, en la E0 de S0-5b y en la
corregida.

Uso: python -B control_leidas_S0-6a.py --comun <dir de comun_S1quater.py> --orden <orden_lectura_S1ter.json>
       --base <E0 de S0-5b> --final <E0 corregida> --regla a=<dir> … --tsv <errores_confirmados_S1ter.tsv>
       --out <json> [--md <md con texto>]

Las leídas son las de `mostradas_S1ter` (del diseño sellado de S1-quater, importada sin cambios, con la clase `E0` y
`leer_sellado` del mismo módulo, que esa función necesita: la E0 que leyó S1-ter y el orden sellado). Por unidad: el corte
sigue igual si la unidad corregida tiene el mismo id, el mismo sha256 propio y las mismas páginas; la herencia, si es
igual tramo por tramo. Lo que se juzgó de cada unidad en S1-ter (mandato, §4): el corte de la unidad de cada ficha (o de
sus partes), el corte de la que le sigue y, en la etapa 2, la herencia de la unidad de la ficha; cada pregunta es error
confirmado si tiene fila en el TSV (por ficha y pregunta) y correcta si no la tiene. Un cambio queda fuera del FRENO solo
si su pregunta tiene fila en el TSV (corte con fila de la_unidad o la_que_sigue; herencia con fila de la_herencia); todo
otro cambio va al FRENO («al_freno»), con lo juzgado y con las reglas que, solas (cada configuración de una regla
prendida), cambian esa unidad. Si el id ya no está, se listan las unidades corregidas que solapan su texto
(`solapes_S0_6a.py`). El JSON lleva ids, campos y reglas; el texto va solo al --md (el FRENO puede mostrar el de las leídas).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

CAMPOS = ("sha256_propio", "paginas", "herencia")


def comparar(b: dict, f: dict | None) -> list[str]:
    if f is None:
        return ["id"]
    return [k for k in CAMPOS if b.get(k) != f.get(k)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comun", type=Path, required=True)
    ap.add_argument("--orden", type=Path, required=True)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--final", type=Path, required=True)
    ap.add_argument("--regla", action="append", default=[])
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--md", type=Path)
    ap.add_argument("--solo-al-freno", action="store_true", help="atribuye por regla solo los cambios que van al FRENO")
    a = ap.parse_args()
    sys.path.insert(0, str(a.comun))
    import comun_S1quater as Q     # sin cambios: mostradas_S1ter, y la E0 y el orden sellado que necesita
    sys.path.insert(0, str(Path(__file__).parent))
    from solapes_S0_6a import solapes

    orden = json.loads(Q.leer_sellado(a.orden, Q.SHA_ORDEN_S1TER, "el orden de S1-ter"))
    viejo, nuevo = Q.E0(a.base), Q.E0(a.final)
    reglas = {r: Q.E0(Path(d)) for r, d in (x.split("=", 1) for x in a.regla)}
    leidas = Q.mostradas_S1ter(orden, viejo)
    filas = list(csv.DictReader(a.tsv.open(encoding="utf-8"), delimiter="\t"))
    con_fila = {(f["ficha"], f["pregunta"]): f for f in filas}
    preguntas: dict[str, list[dict]] = {}

    def juzgada(uid: str, ficha: str, pregunta: str) -> None:
        f = con_fila.get((ficha, pregunta))
        preguntas.setdefault(uid, []).append(
            {"ficha": ficha, "pregunta": pregunta, "veredicto": "error_confirmado" if f else "correcta",
             **({"clase": f["clase"], "subclase": f["subclase"]} if f else {})})

    for f in orden["etapa_1"]["fichas"]:
        juzgada(f["id"], f["id_opaco"], "la_unidad")
    for f in orden["etapa_2"]["fichas"]:
        for c in viejo.partes(f["id"]):
            juzgada(c["id"], f["id_opaco"], "la_unidad")
            juzgada(c["id"], f["id_opaco"], "la_herencia")
        sig = viejo.siguiente(f["id"])
        if sig is not None:
            juzgada(sig["id"], f["id_opaco"], "la_que_sigue")
    if set(preguntas) != set(leidas):
        raise SystemExit("FRENO: las unidades con preguntas no son las leídas")
    usadas = {(q["ficha"], q["pregunta"]) for v in preguntas.values() for q in v}
    filas_sin_unidad = sorted(f"{k[0]}|{k[1]}" for k in set(con_fila) - usadas)
    alin = {}
    out = []
    for uid, etapa in leidas.items():
        to = uid.split("::")[0]
        b = viejo.por_id(uid)
        fin = {c["id"]: c for c in nuevo.chunks(to)}
        f = fin.get(uid)
        campos = comparar(b, f)
        corte_igual = not ({"id", "sha256_propio", "paginas"} & set(campos))
        herencia_igual = "herencia" not in campos and "id" not in campos
        qs = preguntas[uid]
        err_corte = any(q["veredicto"] == "error_confirmado" and q["pregunta"] in ("la_unidad", "la_que_sigue") for q in qs)
        err_her = any(q["veredicto"] == "error_confirmado" and q["pregunta"] == "la_herencia" for q in qs)
        al_freno = []
        if not corte_igual and not err_corte:
            al_freno.append("corte")
        if not herencia_igual and not err_her:
            al_freno.append("herencia")
        fila = {"id": uid, "etapa": etapa, "preguntas_S1ter": qs, "corte_igual": corte_igual,
                "herencia_igual": herencia_igual, "campos": campos, "al_freno": al_freno}
        if campos and (al_freno or not a.solo_al_freno):
            solas = []
            igual_sola = []
            for r, e in reglas.items():
                if not (e.d / f"chunks_{to}.json").exists():
                    raise SystemExit(f"FRENO: falta chunks_{to}.json en la corrida de la regla {r}")
                fr = {c["id"]: c for c in e.chunks(to)}.get(uid)
                if comparar(b, fr):
                    solas.append(r)
                    if fr == f:
                        igual_sola.append(r)
            fila["reglas_solas"] = solas
            fila["igual_a_la_regla_sola"] = igual_sola
            if f is None:
                if to not in alin:
                    alin[to] = solapes(viejo.chunks(to), nuevo.chunks(to))
                fila["solapan_en_la_corregida"] = sorted(i for i, s in alin[to].items() if uid in s)
        out.append(fila)
    cambiadas = [x for x in out if x["campos"]]
    def juzgada_her(x):
        return any(q["pregunta"] == "la_herencia" for q in x["preguntas_S1ter"])

    res = {"leidas": len(out), "por_etapa": {e: sum(1 for x in out if x["etapa"] == e) for e in ("etapa_1", "etapa_2")},
           "corte_igual": sum(x["corte_igual"] for x in out), "herencia_igual": sum(x["herencia_igual"] for x in out),
           "iguales": len(out) - len(cambiadas), "cambiadas": len(cambiadas),
           "al_freno": sum(1 for x in out if x["al_freno"]),
           "al_freno_por_lo_que_cambia": {
               "corte_juzgado_correcto": sum(1 for x in out if "corte" in x["al_freno"]),
               "herencia_juzgada_correcta": sum(1 for x in out if "herencia" in x["al_freno"] and juzgada_her(x)),
               "herencia_no_juzgada": sum(1 for x in out if "herencia" in x["al_freno"] and not juzgada_her(x))},
           "fuera_del_freno_por_fila_del_tsv": sum(1 for x in cambiadas if not x["al_freno"]),
           "filas_del_tsv_sin_unidad_leida": filas_sin_unidad,
           "unidades": out}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "unidades"}, ensure_ascii=False, indent=1))
    if a.md:
        with a.md.open("w", encoding="utf-8") as fh:
            for x in (c for c in cambiadas if "reglas_solas" in c):
                b = viejo.por_id(x["id"])
                f = {c["id"]: c for c in nuevo.chunks(x["id"].split("::")[0])}.get(x["id"])
                fh.write(f"### {x['id']} · {x['etapa']} · campos {x['campos']} · reglas solas {x['reglas_solas']} "
                         f"(igual a la regla sola: {x['igual_a_la_regla_sola']})\n")
                fh.write(f"- al FRENO: {x['al_freno'] or 'no (fila del TSV)'}; juzgado en S1-ter: "
                         + "; ".join(f"{q['ficha']} {q['pregunta']} {q['veredicto']}" for q in x["preguntas_S1ter"]) + "\n")
                fh.write(f"- antes: págs {b['paginas']}, {b['texto'].count(chr(10)) + 1} renglones: {b['texto'][:160]!r} … "
                         f"{b['texto'][-120:]!r}\n")
                if f is None:
                    fh.write(f"- después: el id no está; solapan {x.get('solapan_en_la_corregida')}\n")
                else:
                    fh.write(f"- después: págs {f['paginas']}, {f['texto'].count(chr(10)) + 1} renglones: "
                             f"{f['texto'][:160]!r} … {f['texto'][-120:]!r}\n")
                if "herencia" in x["campos"]:
                    ha = [(t["tipo"], t["unidad_origen"], t["texto"][:90]) for t in b["herencia"]]
                    hb = [(t["tipo"], t["unidad_origen"], t["texto"][:90]) for t in (f or {}).get("herencia", [])]
                    fh.write("- herencia antes:\n" + "".join(f"    - {t}\n" for t in ha))
                    fh.write("- herencia después:\n" + "".join(f"    - {t}\n" for t in hb))
                fh.write("\n")


if __name__ == "__main__":
    main()
