#!/usr/bin/env python3
"""aplicar_lectura_tolerante_b63.py — La lectura tolerante (lectura_tolerante_juez.py) sobre las salidas del juez de B6.3 que no se
leen como JSON, con su prueba (la nota al pie firmada del pre-registro de B6.3, docs/preregistro_B6_3_evaluacion_final.md:886-913: la
de N6, n6/aplicar_lectura_tolerante_n6.py, con sus P1 a P8, adaptada a B6.3). USD 0: no llama a ningún modelo. Lee la salida de B6.3
sin escribir en ella (las cachés del juez, en solo lectura e inmutables) y no abre desanonimizacion_SOLO_MESA/.

Cada repetición del juez de B6.3 corrió en su hilo, con su base, mientras corrían las sesiones (b63/v2/b2/juez_b63.py, TresJueces):
el orden de las filas no sigue un orden ciego fijo. Por eso la fila de la respuesta i en la caché de la repetición r es la de su clave,
la del pedido (llm_cache.compute_key con el espacio de nombres de esa repetición y canonical_request de juez.construir_kwargs), y el caso
de cada respuesta se rehace desde lo que la corrida guardó: el estado (resultados/real/estado_b63.json), la respuesta de la meta de su
sesión (la de correr_b63.respuesta_de) y las preguntas de la entrada sellada, con su id opaco recalculado (juez_b63.caso_ciego). La
prueba lo controla contra lo que el juez registró.

La prueba (P1 a P8), toda tiene que dar; si no, sale con 1 y no escribe nada fuera de su informe:
  P1 las claves: los ids opacos de las respuestas completas, distintos, son los que registró el juez; en cada caché, una fila por
     pedido distinto (dos respuestas con el mismo pedido, la misma pregunta y el mismo texto de respuesta, comparten su fila: la caché
     no lo pide dos veces), cada respuesta con la fila de su clave, sin filas de más, con la hora creciente, el espacio de nombres del
     juez de EV2 de esa repetición y `end_turn`;
  P2 la correspondencia: cada fila que la lectura estricta (`juez.parsear_veredicto`) lee da el veredicto registrado de su id en
     veredictos_r{r}.jsonl, con sus tokens; cada fila que no lee da el error registrado de su id en errores_r{r}.jsonl, con el mismo
     texto (sus 200 primeros caracteres, como los registra el juez de B6.3); cada renglón registrado se usa una vez;
  P3 los criterios: N, el del pedido («CRITERIOS (N):»), es el de las preguntas de la entrada, el de los veredictos registrados de ese
     id, y el mismo en las 3 cachés;
  P4 las lecturas: en cada salida que la estricta lee, la tolerante da lo mismo;
  P5 las que no se leen: la lectura tolerante aplica justo a las salidas que la estricta rechaza por JSON, y en cada una da un veredicto
     por criterio, con los N índices en orden y una clasificación;
  P6 los agregados: juez_b63.agregar, sin editarlo, sobre los veredictos registrados, reproduce byte a byte juez/agregados_b63_ciego.json;
  P7 con las que no se leían: los agregados juntan todas las respuestas, sin ninguna incompleta, y los de antes quedan iguales;
  P8 en contra: la lectura tolerante rechaza seis salidas armadas a mano (un índice de menos, uno fuera de orden, un veredicto fuera
     del dominio, uno separado de su índice, dos clasificaciones y un índice de más dentro de un fragmento) y lee bien dos.

Escribe (con --salida <dir>, que no puede existir): <dir>/juez_con_lectura_tolerante/ con los veredictos_r{1,2,3}.jsonl de B6.3 más
los de la lectura tolerante, marcados, y su agregados_b63_ciego.json de todas las respuestas; <dir>/veredictos_lectura_tolerante_b63.jsonl,
solo los de la lectura tolerante; <dir>/agregados_de_las_que_no_se_leian_b63.json, el agregado de esas respuestas con sus tres lecturas;
y <dir>/informe_lectura_tolerante_b63.json. Sin --salida, solo corre la prueba y escribe el informe en --informe. La carpeta de trabajo
de P7 va en --tmp (nada en la carpeta temporal del sistema).
Imprime solo si da cada prueba y sha256: ningún veredicto, ninguna cuenta, pregunta, criterio ni respuesta (despacho de B6.3, análisis A).

  python3 -I -B aplicar_lectura_tolerante_b63.py --salida-b63 <banco_b63> --entrada <entrada_B63.json de HEAD>
      --clon <la carpeta b63/v2/b2 de una copia de HEAD> --tmp <carpeta> (--informe <json> | --salida <dir>)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPS = (1, 2, 3)
N_CRITERIOS = re.compile(r"\n\nCRITERIOS \((\d+)\):\n")
SHA_LECTURA = "191e65bba5527f4f4b6ea2fe826b2b9bcee37d9979c666fa9d61af6c4d13fc06"     # la de la nota al pie firmada


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lj(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def texto_de(raw: str) -> str:
    return "".join(b.get("text", "") for b in json.loads(raw).get("content", []) if b.get("type") == "text")


def filas_cache(db: Path) -> list[dict]:
    con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    try:
        rs = con.execute("SELECT rowid, key, created_at, namespace, stop_reason, input_tokens, output_tokens, model, request_json, "
                         "raw_json FROM cache ORDER BY rowid").fetchall()
    finally:
        con.close()
    out = []
    for rowid, key, ca, ns, stop, it, ot, model, req, raw in rs:
        m = N_CRITERIOS.search(json.loads(req)["messages"][0]["content"])
        out.append({"rowid": rowid, "clave": key, "creado": datetime.fromisoformat(ca), "namespace": ns, "stop": stop,
                    "input_tokens": it, "output_tokens": ot, "modelo": model, "n": int(m.group(1)) if m else None,
                    "texto": texto_de(raw)})
    return out


def respuesta_de(out_lote: Path, sid: str) -> str | None:
    """La de correr_b63.respuesta_de (b63/v2/b2/correr_b63.py:211-214), tal cual: la respuesta final de la meta de la sesión."""
    m = json.loads((out_lote / sid / f"meta_{sid}.json").read_text(encoding="utf-8"))
    r = (m.get("final_json_R4") or {}).get("respuesta")
    return r if isinstance(r, str) and r.strip() else None


def casos_de_b63(B63: Path, e: dict, K, JB) -> list[dict]:
    """Los casos que vio el juez, rehechos desde lo guardado: por bloque (K.orden_bloques) y brazo, la sesión final completa, su
    respuesta y su caso ciego (JB.caso_ciego, con el id opaco). El brazo queda solo en memoria, para la clave de la adjudicación."""
    preguntas = K.cargar_preguntas(e)
    st = json.loads((B63 / "resultados" / "real" / "estado_b63.json").read_text(encoding="utf-8"))
    out = []
    for b in K.orden_bloques(e["preguntas"]["ids_en_orden"], e["k"], sorted(e["brazos"])):
        for x, f in sorted(st["bloques"][b["bloque"]]["final"].items()):
            if f.get("clasificacion") != "completa":
                continue
            resp = respuesta_de(B63 / "resultados" / "real" / f["salida"].rsplit("/", 1)[0], f["id"])
            c = JB.caso_ciego(b["qid"], x, b["r"], resp, preguntas)
            out.append({"id_opaco": c["id_opaco"], "qid": b["qid"], "r": b["r"], "brazo": x, "sesion": f["id"], "caso": c,
                        "n": len(c["criterios"])})
    return out


def cargar_entrada(ruta: Path, K) -> dict:
    """La entrada sellada (b63/entrada_B63.json de HEAD) con la ruta de sus preguntas, controlada por su sha256."""
    e = json.loads(Path(ruta).read_text(encoding="utf-8"))
    p = Path(os.path.expanduser(e["preguntas"]["ruta"]))
    if sha(p) != e["preguntas"]["sha256"]:
        raise SystemExit("ABORTO: las preguntas de la entrada sellada no dan su sha256")
    e["_rutas"] = {"preguntas": p}
    return e


def pruebas_en_contra(LT) -> dict:
    def sal(crits, cl='"clasificacion_respuesta": "contenido", '):
        return "{" + cl + '"criterios": [' + ", ".join(crits) + "]}"
    c = lambda k, v, frag="null": f'{{"indice": {k}, "veredicto": "{v}", "fragmento": {frag}, "justificacion": "x"}}'  # noqa: E731
    malas = {
        "un índice de menos": (sal([c(1, "cumplido")]), 2),
        "un índice fuera de orden": (sal([c(2, "cumplido"), c(1, "dudoso")]), 2),
        "un veredicto fuera del dominio": (sal([c(1, "cumplido"), c(2, "parcial")]), 2),
        "un veredicto separado de su índice": (sal(['{"indice": 1, "fragmento": null, "veredicto": "cumplido"}']), 1),
        "dos clasificaciones": (sal([c(1, "cumplido")], cl='"clasificacion_respuesta": "contenido", '
                                    '"clasificacion_respuesta": "abstencion", '), 1),
        "un índice de más dentro de un fragmento": (sal([c(1, "cumplido", '"dice "indice": 2, sin escapar"'), c(2, "dudoso")]), 2),
    }
    out = {}
    for k, (t, n) in malas.items():
        try:
            LT.leer(t, n)
            out[k] = "la leyó (mal)"
        except ValueError:
            out[k] = "la rechaza"
    buenas = {"con comillas sin escapar en el fragmento": (sal([c(1, "cumplido", '"dice "tal cosa" en el punto"'),
                                                                 c(2, "no_cumplido")]), 2, ["cumplido", "no_cumplido"]),
              "con la clave del veredicto repetida": (sal(['{"indice": 1, "veredicto": "dudoso", "fragmento": null, '
                                                           '"veredicto": "cumplido", "justificacion": "x"}']), 1, ["cumplido"])}
    for k, (t, n, esp) in buenas.items():
        try:
            r = LT.leer(t, n)
            out[k] = "la lee bien" if [x["veredicto"] for x in r["criterios"]] == esp else "la lee mal"
        except ValueError:
            out[k] = "la rechaza (mal)"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida-b63", type=Path, required=True)
    ap.add_argument("--entrada", type=Path, required=True, help="b63/entrada_B63.json de una copia de HEAD")
    ap.add_argument("--clon", type=Path, required=True, help="la carpeta banco_mcp/b63/v2/b2 de donde se importan el juez y comun")
    ap.add_argument("--tmp", type=Path, required=True, help="la carpeta de trabajo de P7 (no la carpeta temporal del sistema)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--informe", type=Path)
    g.add_argument("--salida", type=Path)
    a = ap.parse_args(argv)
    clon = a.clon.resolve()
    for p in (str(clon), str(clon.parents[2])):
        if p not in sys.path:
            sys.path.insert(0, p)
    import juez_b63 as JB                       # noqa: PLC0415  (solo import: agregar, caso_ciego, el juez de EV2)
    import lectura_tolerante_juez as LT         # noqa: PLC0415
    K, J = JB.K, JB.J
    if sha(Path(LT.__file__)) != SHA_LECTURA:
        raise SystemExit("ABORTO: lectura_tolerante_juez.py no es la de la nota al pie firmada")
    if a.salida is not None and a.salida.exists():
        raise SystemExit("ABORTO: --salida ya existe")
    B63 = a.salida_b63.resolve()
    JD = B63 / "juez"
    e = cargar_entrada(a.entrada, K)
    casos_b63 = casos_de_b63(B63, e, K, JB)
    ids = sorted(c["id_opaco"] for c in casos_b63)
    caso_de = {c["id_opaco"]: c for c in casos_b63}
    ver = {r: lj(JD / f"veredictos_r{r}.jsonl") for r in REPS}
    err = {r: lj(JD / f"errores_r{r}.jsonl") for r in REPS}
    filas = {r: filas_cache(JD / "cache" / JB.db_path(r, Path(".")).name) for r in REPS}
    P, falla = {}, []

    # P1
    ns_esperado = {r: J.lc.make_namespace(f"juez_ev2_r{r}", code_ver=J.CODE_VER, thinking=False) for r in REPS}
    clave_de = {(r, c["id_opaco"]): J.lc.compute_key(ns_esperado[r], J.lc.canonical_request(J.construir_kwargs(
        c["caso"]["pregunta"], c["caso"]["respuesta"], c["caso"]["criterios"]))) for r in REPS for c in casos_b63}
    registrados = {x["id_opaco"] for r in REPS for x in ver[r] + err[r]}
    p1 = {"ids": len(ids), "ids_distintos": len(set(ids)), "ids_iguales_a_los_registrados": set(ids) == registrados}
    fila_de = {}
    for r in REPS:
        fs = filas[r]
        por_clave = {}
        for f in fs:
            por_clave.setdefault(f["clave"], []).append(f)
        de_casos = {i: por_clave.get(clave_de[(r, i)], []) for i in ids}
        fila_de[r] = {i: v[0] for i, v in de_casos.items() if len(v) == 1}
        claves_resp = {clave_de[(r, i)] for i in ids}
        p1[f"r{r}"] = {"filas": len(fs), "claves_distintas": len(por_clave), "pedidos_distintos": len(claves_resp),
                       "respuestas_con_una_fila_de_su_clave": len(fila_de[r]),
                       "filas_de_mas": len(set(por_clave) - {clave_de[(r, i)] for i in ids}),
                       "hora_creciente": all(x["creado"] < y["creado"] for x, y in zip(fs, fs[1:])),
                       "espacio_de_nombres": all(x["namespace"] == ns_esperado[r] for x in fs),
                       "end_turn": sum(x["stop"] == "end_turn" for x in fs)}
    P["P1"] = p1
    n_ids = len(ids)
    if len(set(ids)) != n_ids or not p1["ids_iguales_a_los_registrados"] or any(
            p1[f"r{r}"] != {"filas": p1[f"r{r}"]["pedidos_distintos"], "claves_distintas": p1[f"r{r}"]["pedidos_distintos"],
                            "pedidos_distintos": p1[f"r{r}"]["pedidos_distintos"], "respuestas_con_una_fila_de_su_clave": n_ids,
                            "filas_de_mas": 0, "hora_creciente": True, "espacio_de_nombres": True,
                            "end_turn": p1[f"r{r}"]["pedidos_distintos"]} for r in REPS):
        falla.append("P1")

    # P2, P3, P4 y P5
    n_de, rescate, usados_v, usados_e = {}, [], Counter(), Counter()
    p2 = {"veredictos_iguales": 0, "errores_iguales": 0, "distintos": 0}
    p4 = {"iguales": 0, "distintas": 0}
    p5 = {"aplica_en_las_rechazadas_por_json": 0, "aplica_en_otras": 0, "leidas": 0, "no_leidas": 0,
          "criterios_con_mas_de_un_veredicto": 0}
    v_por = {r: {x["id_opaco"]: x for x in ver[r]} for r in REPS}
    e_por = {r: {x["id_opaco"]: x for x in err[r]} for r in REPS}
    for r in REPS:
        for i in ids:
            f = fila_de[r].get(i)
            if f is None:
                continue
            n_de.setdefault(i, set()).add(f["n"])
            try:
                if f["stop"] == "max_tokens":                # como juez.juzgar: la truncada no se lee
                    raise ValueError("respuesta del juez truncada por max_tokens")
                estricta = J.parsear_veredicto(f["texto"], f["n"])
            except ValueError as x:
                estricta, error = None, str(x)
            if estricta is not None:
                reg = v_por[r].get(i)
                ok = (reg is not None and reg["clasificacion_respuesta"] == estricta["clasificacion_respuesta"]
                      and reg["criterios"] == estricta["criterios"] and reg["meta"]["input_tokens"] == f["input_tokens"]
                      and reg["meta"]["output_tokens"] == f["output_tokens"])
                p2["veredictos_iguales" if ok else "distintos"] += 1
                usados_v[(r, i)] += 1
                try:
                    p4["iguales" if LT.igual_a_la_estricta(LT.leer(f["texto"], f["n"]), estricta) else "distintas"] += 1
                except ValueError:
                    p4["distintas"] += 1
                p5["aplica_en_otras"] += LT.aplica(f["texto"], f["stop"])
                continue
            reg = e_por[r].get(i)
            ok = reg is not None and reg["error"] == error[:200]
            p2["errores_iguales" if ok else "distintos"] += 1
            usados_e[(r, i)] += 1
            por_json = LT.aplica(f["texto"], f["stop"])
            if not por_json:
                p5["no_leidas"] += 1
                continue
            try:
                t = LT.leer(f["texto"], f["n"])
            except ValueError:
                p5["no_leidas"] += 1
                continue
            p5["aplica_en_las_rechazadas_por_json"] += 1
            p5["leidas"] += 1
            p5["criterios_con_mas_de_un_veredicto"] += sum(c["veredictos_en_el_criterio"] > 1 for c in t["criterios"])
            rescate.append({"id_opaco": i, "rep": r, "clasificacion_respuesta": t["clasificacion_respuesta"],
                            "criterios": [{"indice": c["indice"], "veredicto": c["veredicto"]} for c in t["criterios"]],
                            "meta": {"modelo": f["modelo"], "stop_reason": f["stop"], "input_tokens": f["input_tokens"],
                                     "output_tokens": f["output_tokens"], "clave_de_la_cache": f["clave"],
                                     "fila_de_la_cache": f["rowid"]},
                            "lectura": "tolerante", "lectura_sha256": sha(Path(LT.__file__)),
                            "error_de_la_estricta": error})
    p2["renglones_registrados"] = sum(len(v) for v in ver.values()) + sum(len(v) for v in err.values())
    p2["renglones_usados_una_vez"] = sum(1 for v in usados_v.values() if v == 1) + sum(1 for v in usados_e.values() if v == 1)
    P["P2"] = p2
    if p2["distintos"] or p2["renglones_usados_una_vez"] != p2["renglones_registrados"] \
            or p2["veredictos_iguales"] + p2["errores_iguales"] != 3 * n_ids:
        falla.append("P2")
    reg_n = {i: len(x["criterios"]) for r in REPS for i, x in v_por[r].items()}
    p3 = {"ids_con_un_solo_N": sum(1 for v in n_de.values() if len(v) == 1 and None not in v),
          "N_igual_al_registrado": sum(1 for i, nn in reg_n.items() if n_de.get(i) == {nn}), "ids_con_veredicto": len(reg_n),
          "N_igual_al_de_las_preguntas": sum(1 for i in ids if n_de.get(i) == {caso_de[i]["n"]})}
    P["P3"] = p3
    if p3["ids_con_un_solo_N"] != n_ids or p3["N_igual_al_registrado"] != p3["ids_con_veredicto"] \
            or p3["N_igual_al_de_las_preguntas"] != n_ids:
        falla.append("P3")
    P["P4"] = p4
    if p4["distintas"] or p4["iguales"] != sum(len(v) for v in ver.values()):
        falla.append("P4")
    P["P5"] = p5
    if p5["aplica_en_otras"] or p5["no_leidas"] or p5["leidas"] != sum(len(v) for v in err.values()) \
            or p5["aplica_en_las_rechazadas_por_json"] != p5["leidas"]:
        falla.append("P5")

    # P6 y P7
    casos = {i: caso_de[i]["n"] for i in ids}
    original = (JD / "agregados_b63_ciego.json").read_bytes()
    rehecho = (json.dumps(JB.agregar(JD, casos), ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    P["P6"] = {"reproduce_byte_a_byte": rehecho == original, "sha256_original": hashlib.sha256(original).hexdigest()}
    if rehecho != original:
        falla.append("P6")
    a.tmp.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=a.tmp) as td:
        tj = Path(td)
        for r in REPS:
            lineas = (JD / f"veredictos_r{r}.jsonl").read_text(encoding="utf-8")
            extra = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rescate if x["rep"] == r)
            (tj / f"veredictos_r{r}.jsonl").write_text(lineas + extra, encoding="utf-8")
        agg_t = JB.agregar(tj, casos)
        textos_t = {r: (tj / f"veredictos_r{r}.jsonl").read_text(encoding="utf-8") for r in REPS}
    antes = {x["id_opaco"]: x for x in json.loads(original)["agregados"]}
    despues = {x["id_opaco"]: x for x in agg_t["agregados"]}
    P["P7"] = {"n_agregados": agg_t["n_agregados"], "incompletas": len(agg_t["incompletas"]),
               "los_de_antes_iguales": sum(1 for i, x in antes.items() if despues.get(i) == x), "antes": len(antes)}
    if agg_t["n_agregados"] != n_ids or agg_t["incompletas"] or P["P7"]["los_de_antes_iguales"] != len(antes):
        falla.append("P7")

    # P8
    P["P8"] = pruebas_en_contra(LT)
    if any(v not in ("la rechaza", "la lee bien") for v in P["P8"].values()) or len(P["P8"]) != 8:
        falla.append("P8")

    informe = {"unidad": "B6.3, análisis A: la lectura tolerante de las salidas del juez que no se leen como JSON (nota al pie 229)",
               "codigo": {"lectura_tolerante_juez.py": sha(Path(LT.__file__)), Path(__file__).name: sha(Path(__file__)),
                          "juez_b63.py": sha(Path(JB.__file__)), "juez.py": sha(Path(J.__file__)),
                          "mapping.py": sha(Path(JB.M.__file__))},
               "juez": {"code_ver": J.CODE_VER, "prompt_sha256": J.PROMPT_SHA256, "modelo": J.MODELO},
               "entradas": {**{f"juez/{n}": sha(JD / n) for n in ["agregados_b63_ciego.json"]
                               + [f"veredictos_r{r}.jsonl" for r in REPS] + [f"errores_r{r}.jsonl" for r in REPS]},
                            **{f"juez/cache/{JB.db_path(r, Path('.')).name}": sha(JD / "cache" / JB.db_path(r, Path(".")).name)
                               for r in REPS},
                            "resultados/real/estado_b63.json": sha(B63 / "resultados" / "real" / "estado_b63.json"),
                            "entrada_B63.json": sha(a.entrada), "preguntas": e["preguntas"]["sha256"]},
               "prueba": P, "prueba_da": not falla, "fallan": falla,
               "las_que_no_se_leian": sorted([x["id_opaco"], x["rep"]] for x in rescate)}
    if a.salida is not None and not falla:
        sal = a.salida
        (sal / "juez_con_lectura_tolerante").mkdir(parents=True)
        for r in REPS:
            (sal / "juez_con_lectura_tolerante" / f"veredictos_r{r}.jsonl").write_text(textos_t[r], encoding="utf-8")
        (sal / "juez_con_lectura_tolerante" / "agregados_b63_ciego.json").write_text(
            json.dumps(agg_t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (sal / "veredictos_lectura_tolerante_b63.jsonl").write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rescate), encoding="utf-8")
        rescatadas = {x["id_opaco"] for x in rescate}
        (sal / "agregados_de_las_que_no_se_leian_b63.json").write_text(json.dumps(
            {"agregados": [x for x in agg_t["agregados"] if x["id_opaco"] in rescatadas]}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        informe["salidas"] = {str(p.relative_to(sal)): sha(p) for p in sorted(sal.rglob("*")) if p.is_file()}
        destino = sal / "informe_lectura_tolerante_b63.json"
    else:
        destino = a.informe if a.informe is not None else None
    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(informe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"prueba": {k: ("PASS" if k not in falla else "FAIL") for k in P}, "prueba_da": not falla, "fallan": falla},
                     ensure_ascii=False))
    if destino is not None:
        print(f"informe: {destino.name} ({sha(destino)})")
    return 0 if not falla else 1


if __name__ == "__main__":
    raise SystemExit(main())
