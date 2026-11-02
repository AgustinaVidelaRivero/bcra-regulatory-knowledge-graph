#!/usr/bin/env python3
"""aplicar_lectura_tolerante_b64.py — El envoltorio de aplicar_lectura_tolerante_b63.py para B6.4 (la corrección del H-6: la decisión 3 de
la autora del 30/10/2026, en DECISION, tal cual). USD 0: no llama a ningún modelo. No edita el sellado (`5f608a58…`): lo importa con su
sha256 (analizar_b64.importar_sellado) y llama a su main, tal cual.

El sellado no escribe nada si una salida del juez no la lee ni la estricta ni la tolerante (su P5, «no_leidas»; y su P1, si terminó por
max_tokens). El §5 de B6.4: «Lo que la lectura no resuelve va a la adjudicación de la autora, como en B6.3» (55ee1a5a, renglones 197 a
199). Este envoltorio:
  1. busca esas salidas con la misma clasificación que el sellado (su P2 y su P5): por repetición, la fila de la caché de la clave de cada
     respuesta; la estricta (juez.parsear_veredicto, y max_tokens como juez.juzgar) y, si no la lee, la tolerante (aplica y leer); las que
     ninguna lee son las «sin lectura». Controla que cada una tenga su error registrado en errores_r{r}.jsonl con el mismo texto y ningún
     veredicto registrado, que su respuesta esté entre las incompletas de juez/agregados_b63_ciego.json y que esos agregados se reproduzcan
     byte a byte con juez_b63.agregar (el P6 del sellado, sobre lo original);
  2. sin ninguna, corre el sellado sobre banco_b64 tal cual (como en B6.3);
  3. con alguna, arma en --tmp una vista de banco_b64 sin las respuestas que tienen una, con sus tres repeticiones: el estado, con esas
     corridas marcadas (MARCADA) para que el sellado no las rehaga; la meta de cada corrida completa que queda; los veredictos y los errores
     registrados, sin sus renglones; cada caché, en una base nueva con las filas que quedan (con su rowid); y los agregados de la estricta,
     rehechos con juez_b63.agregar, que tienen que ser los originales sin esas respuestas. El sellado corre sobre la vista, sin cambios,
     con su prueba entera (P1 a P8);
  4. con --salida, cada respuesta sin lectura va a la adjudicación entera, en <salida>/agregados_sin_lectura_b64.json: su veredicto
     «requiere_adjudicacion» y todos sus criterios con «sin_consenso» (analizar_b64.MODAL_A_LA_AUTORA), la marca con que el código sellado
     lleva un criterio a la autora. El armado de la adjudicación de B6.4 y el análisis la leen de ahí.
Lo original no se toca: la vista es una copia, nueva en cada corrida. Escribe además su informe en --informe-b64 (sin texto; los ids
opacos, como el sellado). Imprime lo que imprime el sellado y una línea con su informe y su sha256: ninguna cuenta.

  B64_CODIGO_B63=<b63/analisis/codigo de una copia de HEAD> python3 -I -B aplicar_lectura_tolerante_b64.py --salida-b63 <banco_b64>
      --entrada <la entrada de B6.4> --clon <b63/v2/b2 de esa copia> --tmp <carpeta> (--informe <json> | --salida <dir>)
      --informe-b64 <json nuevo>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import analizar_b64 as B  # noqa: E402  (el análisis de B6.4: solo import)

A, AP = B.A, B.AP_SELLADO
DECISION = ("«Una salida del juez que no leen ni la lectura estricta ni la tolerante no puede dejar el análisis sin escribir: va al destino "
            "que fija el §5 del pre-registro, con un envoltorio declarado.» (decisión de la autora del 30/10/2026)")
SIN_LECTURA = "agregados_sin_lectura_b64.json"
MARCADA = "a_la_adjudicacion_sin_lectura"       # en la vista: el sellado rehace solo las corridas «completa»


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def clasificar(B64: Path, e: dict, JB, LT) -> tuple[list[dict], list[dict], dict]:
    """(casos, salidas sin lectura, claves): los casos del sellado (casos_de_b63), las salidas que no leen ni la estricta ni la tolerante
    ({id_opaco, rep, motivo, error_de_la_estricta}) y la clave de la caché de cada (rep, id_opaco), como en el P1 del sellado."""
    K, J = JB.K, JB.J
    casos = AP.casos_de_b63(B64, e, K, JB)
    JD = B64 / "juez"
    sin, claves = [], {}
    for r in AP.REPS:
        ns = J.lc.make_namespace(f"juez_ev2_r{r}", code_ver=J.CODE_VER, thinking=False)
        por_clave: dict = {}
        for f in AP.filas_cache(JD / "cache" / JB.db_path(r, Path(".")).name):
            por_clave.setdefault(f["clave"], []).append(f)
        for c in casos:
            clave = J.lc.compute_key(ns, J.lc.canonical_request(J.construir_kwargs(c["caso"]["pregunta"], c["caso"]["respuesta"],
                                                                                   c["caso"]["criterios"])))
            claves[(r, c["id_opaco"])] = clave
            fs = por_clave.get(clave) or []
            if len(fs) != 1:
                continue                                   # sin su fila, o con dos: lo frena el P1 del sellado
            f = fs[0]
            try:
                if f["stop"] == "max_tokens":              # como juez.juzgar y el sellado: la truncada no se lee
                    raise ValueError("respuesta del juez truncada por max_tokens")
                J.parsear_veredicto(f["texto"], f["n"])
                continue
            except ValueError as x:
                error = str(x)
            if LT.aplica(f["texto"], f["stop"]):
                try:
                    LT.leer(f["texto"], f["n"])
                    continue
                except ValueError:
                    motivo = "la_tolerante_la_rechaza"
            else:
                motivo = "max_tokens" if f["stop"] == "max_tokens" else "la_tolerante_no_aplica"
            sin.append({"id_opaco": c["id_opaco"], "rep": r, "motivo": motivo, "error_de_la_estricta": error})
    return casos, sorted(sin, key=lambda x: (x["id_opaco"], x["rep"])), claves


def controles(B64: Path, casos: list[dict], sin: list[dict], JB) -> dict:
    JD = B64 / "juez"
    err = {r: {x["id_opaco"]: x for x in AP.lj(JD / f"errores_r{r}.jsonl")} for r in AP.REPS}
    ver = {r: {x["id_opaco"] for x in AP.lj(JD / f"veredictos_r{r}.jsonl")} for r in AP.REPS}
    original = (JD / "agregados_b63_ciego.json").read_bytes()
    rehecho = (json.dumps(JB.agregar(JD, {c["id_opaco"]: c["n"] for c in casos}), ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    incompletas = {x["id_opaco"] for x in json.loads(original)["incompletas"]}
    return {"cada_una_con_su_error_registrado_y_sin_veredicto": all(
                x["id_opaco"] in err[x["rep"]] and err[x["rep"]][x["id_opaco"]]["error"] == x["error_de_la_estricta"][:200]
                and x["id_opaco"] not in ver[x["rep"]] for x in sin),
            "sus_respuestas_estan_entre_las_incompletas": {x["id_opaco"] for x in sin} <= incompletas,
            "los_agregados_originales_se_reproducen_byte_a_byte": rehecho == original}


def cache_sin(origen: Path, destino: Path, quedan: set) -> None:
    """Una base nueva con el esquema de la original y solo sus filas de `quedan` (por su clave), con su rowid y en su orden."""
    o = sqlite3.connect(f"file:{origen}?mode=ro&immutable=1", uri=True)
    try:
        ddl = [x[0] for x in o.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY rowid")]
        cur = o.execute("SELECT rowid, * FROM cache ORDER BY rowid")
        cols = [d[0] for d in cur.description][1:]
        filas = [f for f in cur.fetchall() if f[1 + cols.index("key")] in quedan]
    finally:
        o.close()
    d = sqlite3.connect(str(destino))
    try:
        for s in ddl:
            d.execute(s)
        d.executemany(f"INSERT INTO cache (rowid, {', '.join(cols)}) VALUES ({', '.join('?' * (len(cols) + 1))})", filas)
        d.commit()
    finally:
        d.close()


def vista(B64: Path, tmp: Path, casos: list[dict], sin: list[dict], claves: dict, JB) -> tuple[Path, dict]:
    """La vista de banco_b64 sin las respuestas que tienen una salida sin lectura (con sus tres repeticiones), nueva, en --tmp."""
    fuera = {x["id_opaco"] for x in sin}
    sesiones_fuera = {c["sesion"] for c in casos if c["id_opaco"] in fuera}
    tmp.mkdir(parents=True, exist_ok=True)
    V = Path(tempfile.mkdtemp(prefix="vista_b64_", dir=tmp))
    RR, VR = B64 / "resultados" / "real", V / "resultados" / "real"
    st = json.loads((RR / "estado_b63.json").read_text(encoding="utf-8"))
    marcadas = 0
    for blq in st["bloques"].values():
        for f in blq["final"].values():
            if f.get("clasificacion") != "completa":
                continue
            if f["id"] in sesiones_fuera:
                f["clasificacion"] = MARCADA
                marcadas += 1
                continue
            rel = Path(f["salida"].rsplit("/", 1)[0]) / f["id"] / f"meta_{f['id']}.json"
            (VR / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(RR / rel, VR / rel)
    if marcadas != len(fuera):
        raise SystemExit("ABORTO: las corridas de las respuestas sin lectura no son justo las marcadas en la vista")
    (VR / "estado_b63.json").write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    JD, VJ = B64 / "juez", V / "juez"
    (VJ / "cache").mkdir(parents=True)
    for r in AP.REPS:
        for n in (f"veredictos_r{r}.jsonl", f"errores_r{r}.jsonl"):
            lineas = (JD / n).read_text(encoding="utf-8").splitlines(keepends=True) if (JD / n).exists() else []
            (VJ / n).write_text("".join(l for l in lineas if l.strip() and json.loads(l)["id_opaco"] not in fuera), encoding="utf-8")
        quedan = {claves[(r, c["id_opaco"])] for c in casos if c["id_opaco"] not in fuera}
        if quedan & {claves[(r, i)] for i in fuera}:
            raise SystemExit("ABORTO: una fila de la caché es de una respuesta sin lectura y de otra que queda")
        db = JB.db_path(r, Path(".")).name
        cache_sin(JD / "cache" / db, VJ / "cache" / db, quedan)
    agg = JB.agregar(VJ, {c["id_opaco"]: c["n"] for c in casos if c["id_opaco"] not in fuera})
    orig = json.loads((JD / "agregados_b63_ciego.json").read_text(encoding="utf-8"))
    sin_esas = dict(orig, n_casos=orig["n_casos"] - len(fuera), incompletas=[x for x in orig["incompletas"] if x["id_opaco"] not in fuera])
    if agg != sin_esas:
        raise SystemExit("ABORTO: los agregados de la vista no son los originales sin las respuestas sin lectura")
    (VJ / "agregados_b63_ciego.json").write_text(json.dumps(agg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return V, {"corridas_marcadas": marcadas, "agregados_sha256": sha(VJ / "agregados_b63_ciego.json"),
               "estado_sha256": sha(VR / "estado_b63.json")}


def a_la_adjudicacion(casos: list[dict], sin: list[dict]) -> dict:
    """Cada respuesta con una salida sin lectura, entera a la adjudicación (la forma de un agregado de juez_b63.agregar)."""
    n_de = {c["id_opaco"]: c["n"] for c in casos}
    reps = {}
    for x in sin:
        reps.setdefault(x["id_opaco"], []).append(x["rep"])
    return {"que": "las respuestas de B6.4 que van enteras a la adjudicación de la autora porque una de sus tres salidas del juez no la "
                   "leen ni la estricta ni la tolerante (§5; la decisión 3 de la corrección del H-6)",
            "decision": DECISION, "modal_a_la_autora": B.MODAL_A_LA_AUTORA,
            "salidas": [{k: x[k] for k in ("id_opaco", "rep", "motivo", "error_de_la_estricta")} for x in sin],
            "agregados": [{"id_opaco": i, "n_criterios": n_de[i], "veredicto_pregunta": "requiere_adjudicacion",
                           "modales": [B.MODAL_A_LA_AUTORA] * n_de[i], "reps_sin_lectura": rs} for i, rs in sorted(reps.items())]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida-b63", type=Path, required=True, help="banco_b64/ (el nombre del argumento es el del sellado)")
    ap.add_argument("--entrada", type=Path, required=True)
    ap.add_argument("--clon", type=Path, required=True)
    ap.add_argument("--tmp", type=Path, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--informe", type=Path)
    g.add_argument("--salida", type=Path)
    ap.add_argument("--informe-b64", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.informe_b64.exists() or (a.salida is not None and a.salida.exists()):
        raise SystemExit("ABORTO: --informe-b64 o --salida ya existe")
    _, JB = A.importar(a.clon, B.ESPERADO_CODIGO)
    import lectura_tolerante_juez as LT        # noqa: PLC0415  (la del sellado, de banco_mcp/ del clon)
    if sha(Path(LT.__file__)) != AP.SHA_LECTURA:
        raise SystemExit("ABORTO: lectura_tolerante_juez.py no es la de la nota al pie firmada")
    B64 = a.salida_b63.resolve()
    e = AP.cargar_entrada(a.entrada, JB.K)
    casos, sin, claves = clasificar(B64, e, JB, LT)
    ctl = controles(B64, casos, sin, JB)
    fuera = sorted({x["id_opaco"] for x in sin})
    informe = {"que": "el envoltorio de aplicar_lectura_tolerante_b63.py para B6.4 (la decisión 3 de la corrección del H-6)",
               "decision": DECISION,
               "codigo": {Path(__file__).name: sha(Path(__file__)), "aplicar_lectura_tolerante_b63.py": sha(Path(AP.__file__)),
                          "analizar_b64.py": sha(Path(B.__file__)), "juez_b63.py": sha(Path(JB.__file__)),
                          "lectura_tolerante_juez.py": sha(Path(LT.__file__))},
               "controles": ctl,
               "sin_lectura": {"salidas": len(sin), "respuestas": len(fuera),
                               "por_motivo": A.por_clave(x["motivo"] for x in sin),
                               "las_salidas": [[x["id_opaco"], x["rep"], x["motivo"]] for x in sin]},
               "vista": None}
    rc = 1
    if all(ctl.values()):
        base = B64
        if sin:
            base, informe["vista"] = vista(B64, a.tmp, casos, sin, claves, JB)
        resto = ["--salida-b63", str(base), "--entrada", str(a.entrada), "--clon", str(a.clon), "--tmp", str(a.tmp)]
        resto += ["--informe", str(a.informe)] if a.informe is not None else ["--salida", str(a.salida)]
        rc = AP.main(resto)
        informe["sellado"] = {"modo": "informe" if a.informe is not None else "salida", "codigo_de_salida": rc}
        if a.salida is not None and rc == 0:
            (a.salida / SIN_LECTURA).write_text(json.dumps(a_la_adjudicacion(casos, sin), ensure_ascii=False, indent=1) + "\n",
                                                 encoding="utf-8")
            informe["salidas"] = {SIN_LECTURA: sha(a.salida / SIN_LECTURA)}
    a.informe_b64.parent.mkdir(parents=True, exist_ok=True)
    a.informe_b64.write_text(json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"lectura_tolerante_b64: {'controles PASS' if all(ctl.values()) else 'controles FAIL'}; "
          f"informe: {a.informe_b64.name} ({sha(a.informe_b64)})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
