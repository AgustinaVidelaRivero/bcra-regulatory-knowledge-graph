"""
selftest_manifiesto.py — U-B5.1: batería de paridad byte a byte de la
parametrización por manifiesto (diseño aprobado en el freno 1) + validaciones
del loader + modo sin oráculo + gancho del índice de fragmentos.

USD 0 / sin LLM: toda comparación es contra artefactos vigentes/sellados del
corpus de desarrollo (que se LEEN, jamás se escriben) o contra corridas stub/
offline en directorios temporales. La comparación de E1/E3 es por REQUEST
construido (byte a byte, y presencia de su key en la caché sellada — copiada
a temporal para consultarla sin tocar los archivos originales).

Puntos:
  P1  loader: el manifiesto de desarrollo carga; 10 manifiestos adversariales
      fallan con el mensaje correcto.
  P2  E0: corrida parametrizada completa → sha256 de los 20 artefactos == los
      de e0_chunking/salida_enm01 (≈40 s: re-parsea los 5 PDFs).
  P3  E1: requests de los 1.763 chunks byte-idénticos (carga vía manifiesto
      vs legacy) y TODOS con key presente en la caché sellada (0 misses
      proyectados para una re-corrida).
  P4  E3: ídem para los 1.762 pares aceptados (primer request de verificación
      desde las extracciones compactas selladas).
  P5  E2: reducir() parametrizado sobre los insumos sellados → grafo/reporte/
      censo byte a byte vs salida/<to>/, 5/5 TOs; limitaciones del manifiesto
      == literal de e2_lib (laudo D-d).
  P6  ensamblado: kg.json / reporte_ensamblado.json / tests byte a byte vs
      los sellos del manifiesto (8e2eadee… / 98ee43e5… / 5bf4ffd7…).
  P7  runner (stub, pro completo): huella normalizada == la golden capturada
      con el runner PRE-edición (comando en GOLDEN_STUB_PRO).
  P8  modo sin oráculo: corpus sintético → nivel_mapa {"modo":"sin_oraculo"}
      sin KeyError; oráculo declarado sin el TO → ValueError con mensaje.
  P9  gancho: indice_fragmentos se expone verbatim y NINGÚN módulo del
      pipeline lo consume.
  P10 U-PROMPT-R2, perfil r2b (manifiesto tanda0_10tos_r2b, E0 de C2 de
      U-R2-CODIGO-2, salida_tanda0_r2b, desde T1 de U-REEXT-T0):
      requests de E1 de las 2.439 unidades y de E3 sobre una salida simulada
      (validada con la traducción r2), byte a byte en doble corrida sin API;
      prefijo de E1 idéntico entre unidades y con el sha congelado; prefijo de
      E3 sin cambio; NOTAS r2 contadas; runner con clientes simulados (pro) en
      doble corrida con huella idéntica, E2 r2 activado por el perfil y la
      lista de exenciones de la ampliación en el resumen de E3.
  P11 U-PROMPT-R2, sellado v3_b54 de la tanda 0: las keys de E1 de las 2.434
      unidades y las de E3 de los pares de la salida sellada están en las
      cachés; la validación v3 recomputada del crudo es byte a byte la guardada.

Uso:  .venv/bin/python3 selftest_manifiesto.py [--saltear-e0]
      (--saltear-e0 solo para iteración de desarrollo: omite P2, el punto
      más lento; la corrida de cierre va SIN el flag)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent                   # reextraccion_v2/
for sub in ("e1_extractor", "e3_verificador", "e2_reduce", "corpus_v2"):
    sys.path.insert(0, str(AQUI / sub))
sys.path.insert(0, str(AQUI))

import manifiesto_corpus as MC          # noqa: E402
import comun_e1                         # noqa: E402
import prompt_e1                        # noqa: E402
import cliente_e1                       # noqa: E402
import comun_e3                         # noqa: E402
import prompt_e3                        # noqa: E402
import cliente_e3                       # noqa: E402
import e2_lib                           # noqa: E402
import ensamblar_corpus as EC           # noqa: E402
import llm_cache as lc                  # noqa: E402

PY = sys.executable
MANIFIESTO_DEV = MC.MANIFIESTOS_DIR / "desarrollo_5tos.json"
E0_REF = AQUI / "e0_chunking" / "salida_enm01"
SALIDA_SELLADA = AQUI / "corpus_v2" / "salida"
DB_E1 = AQUI / "e1_extractor" / "cache" / "e1_extraccion.db"
DB_E3 = AQUI / "e3_verificador" / "cache" / "e3_verificacion.db"
MODEL_E1 = "claude-haiku-4-5"
MODEL_E3 = "claude-sonnet-5"

_n = 0
_fallos = 0


def check(desc: str, ok: bool, detalle: str = "") -> None:
    global _n, _fallos
    _n += 1
    if not ok:
        _fallos += 1
    print(f"[{_n}] {'ok   ' if ok else 'FALLO'} {desc}"
          + (f" — {detalle}" if detalle else ""), flush=True)


def sha_texto(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


# ========================================================================= #
# P1 — loader: manifiesto de desarrollo + adversariales                     #
# ========================================================================= #

def _mutado(base: dict, tmp: Path, nombre: str, mutar) -> Path:
    d = copy.deepcopy(base)
    mutar(d)
    d["nombre"] = nombre
    p = tmp / f"{nombre}.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return p


def p1_loader(tmp: Path) -> "MC.Manifiesto":
    man = MC.cargar(MANIFIESTO_DEV)
    check("P1 el manifiesto de desarrollo carga y valida",
          man.ids == ["pro", "cla", "ric", "cap", "ext"]
          and man.orden_corrida == ["pro", "cla", "ric", "cap", "ext"]
          and man.tiene_oraculo and man.tests_respuesta_conocida == "dev5")
    check("P1 perfil_e1 ausente = default produccion_dev (U-CABLE-V3: el "
          "manifiesto dev no se edita)",
          man.perfil_e1 == "produccion_dev")

    base = json.loads(MANIFIESTO_DEV.read_text(encoding="utf-8"))
    casos = [
        ("orden no-permutación", "fx_orden",
         lambda d: d["orden_corrida"].pop(), "permutación"),
        ("id duplicado", "fx_dup",
         lambda d: d["tos"].append(dict(d["tos"][0])), "duplicados"),
        ("rol del catálogo silenciado con null", "fx_rol_null",
         lambda d: d["tos"][0].update(rol_alcance=None), "no se silencia"),
        ("rol distinto del catálogo", "fx_rol_dif",
         lambda d: d["tos"][0].update(rol_alcance="Sujeto_rol_alcance_capmin"),
         "≠ rol del catálogo"),
        # U-CABLE-V3 (candado C6 versionado con justificación): B5.4 ya pobló
        # la tabla TO→rol; el mensaje del gap dejó de decir "puebla B5.4" y
        # ahora exige null o el circuito de refinamiento. El caso adversarial
        # sigue siendo el mismo; solo cambia el fragmento esperado.
        ("rol declarado sin rol en catálogo", "fx_rol_gap",
         lambda d: (d["tos"].append({**d["tos"][0], "id": "zzz",
                                     "archivo": "TO_fantasma.pdf",
                                     "rol_alcance": "Sujeto_rol_fantasma"}),
                    d["orden_corrida"].append("zzz"),
                    d["limites"]["estimado_usd"].update(
                        zzz={"e1": 0.0, "e3": 0.0})),
         "no declara rol"),
        # U-CABLE-V3: el campo perfil_e1 con valor fuera del registro frena.
        ("perfil_e1 desconocido", "fx_perfil",
         lambda d: d.update(perfil_e1="v9_inexistente"),
         "perfil_e1 desconocido"),
        ("limitaciones sin oráculo", "fx_lim_sin_ora",
         lambda d: d["oraculo"].update(mapa_territorio=None),
         "sin oráculo"),
        ("PDF inexistente", "fx_pdf",
         lambda d: d["tos"][0].update(pdf="data/no_existe.pdf"),
         "PDF inexistente"),
        ("sha256 de PDF incorrecto", "fx_sha",
         lambda d: d["tos"][0].update(sha256_pdf="0" * 64), "no coincide"),
        ("suite de tests desconocida", "fx_suite",
         lambda d: d.update(tests_respuesta_conocida="otra"), "desconocida"),
        ("estimado_usd incompleto", "fx_est",
         lambda d: d["limites"]["estimado_usd"].pop("pro"), "CADA id"),
    ]
    for desc, nombre, mutar, frag in casos:
        p = _mutado(base, tmp, nombre, mutar)
        try:
            MC.cargar(p)
            check(f"P1 adversarial rechazado: {desc}", False, "cargó sin error")
        except MC.ErrorManifiesto as e:
            check(f"P1 adversarial rechazado: {desc}", frag in str(e),
                  str(e)[:70])
    return man


# ========================================================================= #
# P2 — paridad E0                                                           #
# ========================================================================= #

def p2_e0(tmp: Path) -> None:
    salida = tmp / "e0"
    r = subprocess.run(
        [PY, str(AQUI / "e0_chunking" / "correr_e0.py"),
         "--salida", str(salida), "--manifiesto", str(MANIFIESTO_DEV)],
        capture_output=True, text=True)
    check("P2 correr_e0 --manifiesto termina bien", r.returncode == 0,
          (r.stderr or "")[-120:])
    a = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(salida.glob("*.json"))}
    b = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(E0_REF.glob("*.json"))}
    difs = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    check("P2 paridad E0: sha256 de los 20 artefactos == salida_enm01",
          len(a) == len(b) == 20 and not difs, f"difs={difs}")


# ========================================================================= #
# P3/P4 — requests E1/E3 byte a byte + keys en las cachés selladas          #
# ========================================================================= #

def _keys_db(original: Path, tmp: Path) -> set[str]:
    """Copia la db sellada (con -wal/-shm si existen) a temporal y lee las
    keys: la original jamás se abre — ni siquiera en modo lectura."""
    dest = tmp / original.name
    shutil.copy2(original, dest)
    for suf in ("-wal", "-shm"):
        p = Path(str(original) + suf)
        if p.exists():
            shutil.copy2(p, Path(str(dest) + suf))
    con = sqlite3.connect(dest)
    try:
        return {r[0] for r in con.execute("SELECT key FROM cache")}
    finally:
        con.close()


def p3_requests_e1(man, tmp: Path) -> None:
    keys = _keys_db(DB_E1, tmp)
    ns = cliente_e1.namespace_e1()
    tot = ig = hit = 0
    for to in man.orden_corrida:
        ch_man = comun_e1.cargar_chunks((to,), e0_dir=man.e0_salida)
        ch_leg = comun_e1.cargar_chunks((to,), e0_dir=comun_e1.E0_SALIDA_ENM01)
        for a, b in zip(ch_man, ch_leg):
            ca = lc.canonical_request(prompt_e1.build_request_kwargs(a, model=MODEL_E1))
            cb = lc.canonical_request(prompt_e1.build_request_kwargs(b, model=MODEL_E1))
            tot += 1
            ig += (ca == cb)
            hit += (lc.compute_key(ns, ca) in keys)
    check("P3 requests E1 byte a byte (manifiesto vs legacy)",
          tot == 1763 and ig == tot, f"{ig}/{tot}")
    check("P3 keys E1 en la caché sellada (0 misses proyectados)",
          hit == tot, f"{hit}/{tot}")


def p4_requests_e3(man, tmp: Path) -> None:
    keys = _keys_db(DB_E3, tmp)
    ns = cliente_e3.namespace_e3()
    tot = ig = hit = 0
    for to in man.orden_corrida:
        ch_man = comun_e3.cargar_chunks((to,), e0_dir=man.e0_salida)
        ch_leg = comun_e3.cargar_chunks((to,), e0_dir=comun_e3.E0_SALIDA_ENM01)
        regs = comun_e3.cargar_extracciones(
            SALIDA_SELLADA / to / "extracciones_e1_compact.jsonl")
        for (c1, v1), (c2, v2) in zip(comun_e3.pares_de(ch_man, regs),
                                      comun_e3.pares_de(ch_leg, regs)):
            ca = lc.canonical_request(prompt_e3.build_request_kwargs(c1, v1, model=MODEL_E3))
            cb = lc.canonical_request(prompt_e3.build_request_kwargs(c2, v2, model=MODEL_E3))
            tot += 1
            ig += (ca == cb)
            hit += (lc.compute_key(ns, ca) in keys)
    check("P4 requests E3 byte a byte (manifiesto vs legacy)",
          tot == 1762 and ig == tot, f"{ig}/{tot}")
    check("P4 keys E3 en la caché sellada (0 misses proyectados)",
          hit == tot, f"{hit}/{tot}")


# ========================================================================= #
# P5 — paridad E2 sobre los insumos sellados                                #
# ========================================================================= #

def p5_e2(man) -> None:
    check("P5 limitaciones del manifiesto == literal LIMITACIONES_E0 (D-d)",
          man.limitaciones_e0() == e2_lib.LIMITACIONES_E0)
    for to in man.orden_corrida:
        res = e2_lib.reducir(
            to, SALIDA_SELLADA / to / f"extracciones_finales_{to}.jsonl",
            censo_oraculo=None, e0_dir=man.e0_salida,
            limitaciones=man.limitaciones_e0())
        g_ok = res["grafo_json"] == (SALIDA_SELLADA / to / f"grafo_{to}.json"
                                     ).read_text(encoding="utf-8")
        r_ok = json.dumps(res["reporte"], ensure_ascii=False, indent=1) == \
            (SALIDA_SELLADA / to / f"reporte_e2_{to}.json").read_text(encoding="utf-8")
        c_ok = json.dumps(res["censo"], ensure_ascii=False, indent=1) == \
            (SALIDA_SELLADA / to / f"censo_{to}.json").read_text(encoding="utf-8")
        check(f"P5 paridad E2 {to}: grafo/reporte/censo byte a byte",
              g_ok and r_ok and c_ok,
              f"grafo={g_ok} reporte={r_ok} censo={c_ok}")


# ========================================================================= #
# P6 — paridad del ensamblado final                                         #
# ========================================================================= #

def p6_ensamblado(man) -> None:
    orden = tuple(man.orden_corrida)
    grafos = {to: json.loads((SALIDA_SELLADA / to / f"grafo_{to}.json"
                              ).read_text(encoding="utf-8")) for to in orden}
    res = EC.ensamblar(grafos, orden, man.tests_respuesta_conocida)
    check("P6 kg.json == sello del manifiesto (8e2eadee…)",
          sha_texto(res["kg_json"]) == man.sellos["kg"])
    rep = json.dumps(res["reporte"], ensure_ascii=False, indent=1)
    check("P6 reporte_ensamblado == sello (98ee43e5…)",
          sha_texto(rep) == man.sellos["reporte_ensamblado"])
    tst = json.dumps(res["tests"], ensure_ascii=False, indent=1)
    check("P6 tests_respuesta_conocida == sello (5bf4ffd7…)",
          sha_texto(tst) == man.sellos["tests_respuesta_conocida"])


# ========================================================================= #
# P7 — runner stub vs golden pre-edición                                    #
# ========================================================================= #
# Golden capturada ANTES de editar runner_corpus.py, con:
#   .venv/bin/python3 runner_corpus.py --stub --salida <tmp> --tos pro
# y la huella normalizada de huella_stub() (ts fuera; prefijo de salida →
# "<SALIDA>"). Cualquier cambio de comportamiento del runner la rompe.

GOLDEN_STUB_PRO = {
    "checkpoints/checkpoint_pro_e1_cierre.json": "919976b9098005f0b8d290b89f710e59d483f10ba82c1f848e4ae2371e9b1774",
    "checkpoints/checkpoint_pro_e3_cierre.json": "0a831f52e2061e04deb3fcb5375117fef5d5fa7124915729ca68e6a5f39b6e41",
    "estado_corpus.json": "b662a26ae7512b3af80f6476a30653b76765b4cdd082545edd7bd96ef9e0612d",
    "pro/censo_pro.json": "cdb0321d33e4f6e2c7dff17f3117117afb28b6d8e426250a9be345978a7fc172",
    "pro/extracciones_e1.jsonl": "6eb82610d173549cc9750ceb72e8611d9d2e7f3c9e4ea670159af30946d803c0",
    "pro/extracciones_e1_compact.jsonl": "6eb82610d173549cc9750ceb72e8611d9d2e7f3c9e4ea670159af30946d803c0",
    "pro/extracciones_finales_pro.jsonl": "256dafb20b92062ea4ad1e3db744b321ef4286606f91e3c5eb0a3a17dd01d666",
    "pro/finales.jsonl": "b3fad874711198bda891893eb9761f2c8b5a7fab0e677aa1404b3d94b8bab4c1",
    "pro/grafo_pro.json": "1addf7f0e213b751c613db1e9a2e0c7f6049b42c4d9bd8e79492f5abf4623f51",
    "pro/reporte_e2_pro.json": "9cd93d69ea7657fba835b77ed842d3a012daf82a1559b93ecf79d29207f27936",
    "pro/resumen_e1.json": "b92df1362c89d2889e9e9275d4cfd6403f7dc5080113a1d371789811c34fadb4",
    "pro/resumen_e3.json": "45e1945f7369b21aa46e28e8ed86cdd0db07114d48a0fedb0ec36944d6f6984b",
    "pro/veredictos.jsonl": "fd388e34d7c3c2b8c6016a73a5a8941601422e6f4a1678ecb3fb36f95478583b",
    "ultimo_checkpoint.json": "0a831f52e2061e04deb3fcb5375117fef5d5fa7124915729ca68e6a5f39b6e41",
}


def huella_stub(salida: Path) -> dict:
    """Huella normalizada de una corrida stub: ts fuera (no determinístico),
    prefijo del directorio de salida → '<SALIDA>' (aparece en el campo
    `extracciones` del reporte E2)."""
    pref = str(salida)
    out = {}
    for p in sorted(salida.rglob("*")):
        if not p.is_file():
            continue
        texto = p.read_text(encoding="utf-8").replace(pref, "<SALIDA>")
        if p.suffix == ".json":
            obj = json.loads(texto)
            if isinstance(obj, dict):
                obj.pop("ts", None)
            texto = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"))
        out[str(p.relative_to(salida))] = sha_texto(texto)
    return out


def p7_runner_stub(tmp: Path) -> None:
    salida = tmp / "stub"
    r = subprocess.run(
        [PY, str(AQUI / "corpus_v2" / "runner_corpus.py"), "--stub",
         "--salida", str(salida), "--tos", "pro",
         "--manifiesto", str(MANIFIESTO_DEV)],
        capture_output=True, text=True)
    check("P7 runner stub (pro completo) termina bien", r.returncode == 0,
          (r.stderr or "")[-120:])
    h = huella_stub(salida)
    difs = sorted(k for k in set(h) | set(GOLDEN_STUB_PRO)
                  if h.get(k) != GOLDEN_STUB_PRO.get(k))
    check("P7 huella del runner parametrizado == golden pre-edición (14 archivos)",
          not difs and len(h) == len(GOLDEN_STUB_PRO), f"difs={difs}")


# ========================================================================= #
# P8 — modo sin oráculo (corpus sintético)                                  #
# ========================================================================= #

def _chunk_fx(cid: str, unidad: str) -> dict:
    return {"id": cid, "to": "fxa", "archivo": "fx.pdf", "unidad": unidad,
            "titulo": f"t {unidad}", "tipo": "punto_terminal",
            "herencia": [], "flags": {}}


def _reg_fx(cid: str, punto: str) -> dict:
    prov = {"to": "fxa", "archivo": "fx.pdf", "punto": punto,
            "rol_documental": "punto_propio"}
    return {"chunk_id": cid, "error": None, "validacion": {
        "chunk_id": cid,
        "entidades": [
            {"local_id": "to", "type": "TextoOrdenado", "label": "TO fx",
             "properties": {"archivo": "fx.pdf"}, "provenance": dict(prov)},
            {"local_id": "e1", "type": "Obligacion", "label": f"Deber {punto}",
             "properties": {"descripcion": f"Deber del punto {punto}."},
             "provenance": dict(prov)}],
        "relaciones": [
            {"source": "e1", "target": "to", "predicate": "establecida_en",
             "sujeto_id": None, "sujeto_propuesto": None,
             "sujeto_propuesto_padre_sugerido": None, "provenance": dict(prov)}],
        "omisiones_no_prosa": [], "rechazos": [], "advertencias": [],
        "metricas": {}}}


def p8_sin_oraculo(tmp: Path) -> None:
    fxdir = tmp / "fx_e0"
    fxdir.mkdir()
    chunks = [_chunk_fx("fxa::1.1", "1.1"), _chunk_fx("fxa::1.2", "1.2")]
    (fxdir / "chunks_fxa.json").write_text(
        json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    jl = tmp / "fx_extracciones.jsonl"
    jl.write_text("".join(json.dumps(_reg_fx(c["id"], c["unidad"]),
                                     ensure_ascii=False) + "\n"
                          for c in chunks), encoding="utf-8")

    res = e2_lib.reducir("fxa", jl, censo_oraculo=e2_lib.SIN_ORACULO,
                         e0_dir=fxdir, limitaciones={})
    nm = res["censo"]["nivel_mapa"]
    nc = res["censo"]["nivel_chunk"]
    check("P8 sin oráculo: reducir corre y nivel_mapa declara el modo",
          nm == {"modo": "sin_oraculo"}, str(nm))
    check("P8 sin oráculo: nivel_chunk corre completo (2/2 cubiertas)",
          nc["unidades"] == 2 and nc["cubiertas"] == 2)
    check("P8 sin oráculo: el grafo se ensambla (3 nodos, 2 aristas)",
          res["reporte"]["nodes_total"] == 3
          and res["reporte"]["edges_total"] == 2,
          f"{res['reporte']['nodes_total']}/{res['reporte']['edges_total']}")

    try:
        e2_lib.reducir("fxa", jl, censo_oraculo={"otro": {}}, e0_dir=fxdir,
                       limitaciones={})
        check("P8 oráculo sin el TO → error con mensaje", False, "no falló")
    except ValueError as e:
        check("P8 oráculo sin el TO → error con mensaje (no KeyError pelado)",
              "sin entrada para el TO" in str(e), str(e)[:70])


# ========================================================================= #
# P9 — gancho del índice de fragmentos                                      #
# ========================================================================= #

def p9_gancho(tmp: Path) -> None:
    base = json.loads(MANIFIESTO_DEV.read_text(encoding="utf-8"))
    cfg = {"granularidad": "chunk_e0", "salida": "indice_fx/"}
    p = _mutado(base, tmp, "fx_gancho",
                lambda d: d.update(indice_fragmentos=cfg))
    man = MC.cargar(p)
    check("P9 gancho: indice_fragmentos se expone verbatim",
          man.indice_fragmentos == cfg)
    check("P9 gancho: null también es válido (manifiesto de desarrollo)",
          MC.cargar(MANIFIESTO_DEV).indice_fragmentos is None)

    consumidores = []
    for rel in ("e0_chunking/correr_e0.py", "e2_reduce/e2_lib.py",
                "e2_reduce/correr_e2.py", "corpus_v2/runner_corpus.py",
                "corpus_v2/ensamblar_corpus.py"):
        if "indice_fragmentos" in (AQUI / rel).read_text(encoding="utf-8"):
            consumidores.append(rel)
    check("P9 gancho: cero consumidores en el pipeline (solo el loader)",
          not consumidores, str(consumidores))


# ========================================================================= #

# ========================================================================= #
# P10/P11 — U-PROMPT-R2: perfil r2b y sellado v3_b54                         #
# ========================================================================= #
MANIFIESTO_R2B = MC.MANIFIESTOS_DIR / "tanda0_10tos_r2b.json"
MANIFIESTO_T0 = MC.MANIFIESTOS_DIR / "tanda0_10tos.json"
SALIDA_T0 = AQUI / "corpus_tanda0" / "salida"


def p10_r2b(tmp: Path) -> None:
    import perfil_e1          # noqa: PLC0415
    import validador_e1       # noqa: PLC0415
    import prompt_r2b         # noqa: PLC0415
    import runner_corpus as RC  # noqa: PLC0415
    man = MC.cargar(MANIFIESTO_R2B)
    pf = perfil_e1.perfil(man.perfil_e1)
    # U-REEXT-T0, T1: el manifiesto r2b lee la E0 de C2 de U-R2-CODIGO-2 (salida_tanda0_r2b, 9f6361e), que suma 5
    # unidades en ric (2.434 → 2.439)
    check("P10 manifiesto r2b: perfil r2b, E0 salida_tanda0_r2b, forma de salida r2",
          pf.nombre == "r2b" and man.e0_salida.name == "salida_tanda0_r2b" and pf.esquema.forma_salida == "r2")
    tot = ig = 0
    prefijos = set()
    tot3 = ig3 = n_enc = n_tab = 0
    for to in man.orden_corrida:
        for c in comun_e1.cargar_chunks((to,), e0_dir=man.e0_salida):
            a = pf.build_request_kwargs(c, model=RC.MODEL_E1)
            b = pf.build_request_kwargs(json.loads(json.dumps(c)), model=RC.MODEL_E1)
            tot += 1
            ig += lc.canonical_request(a) == lc.canonical_request(b)
            prefijos.add(json.dumps({k: a[k] for k in ("system", "tools", "tool_choice")}, sort_keys=True,
                                    ensure_ascii=False))
            ti = {"entities": [{"local_id": "to", "type": "TextoOrdenado", "label": to,
                                "punto": comun_e1.puntos_admitidos(c)[0]}], "relations": [], "omisiones": []}
            val = validador_e1.validar_salida(ti, c, esquema=pf.esquema).as_dict()
            m1 = prompt_e3.build_request_kwargs(c, val, model=RC.MODEL_E3)
            m2 = prompt_e3.build_request_kwargs(json.loads(json.dumps(c)), json.loads(json.dumps(val)),
                                                model=RC.MODEL_E3)
            tot3 += 1
            ig3 += lc.canonical_request(m1) == lc.canonical_request(m2)
            msg = m1["messages"][0]["content"]
            n_enc += "es el encabezado de una lista" in msg
            n_tab += "tablas serializadas por E0 (bloques [TABLA" in msg
    check("P10 requests E1 r2b byte a byte en doble corrida (2.439 unidades)", tot == 2439 and ig == tot,
          f"{ig}/{tot}")
    unico = json.loads(next(iter(prefijos))) if len(prefijos) == 1 else {}
    check("P10 prefijo E1 r2b idéntico entre unidades, con el sha congelado y el tool schema de la generación P2",
          len(prefijos) == 1
          and hashlib.sha256(unico["system"][0]["text"].encode()).hexdigest() == prompt_r2b.PREFIJO_SHA256_R2B_ESPERADO
          and unico["system"][-1].get("cache_control") == {"type": "ephemeral"}
          and unico["tools"][0] == prompt_r2b.TOOL_SCHEMA_R2B,
          f"prefijos distintos: {len(prefijos)}")
    check("P10 namespace E1 r2b derivado del hash congelado",
          cliente_e1.namespace_e1(prefijo_hash=pf.prefijo_hash_para_namespace)
          == "e1_extraccion|cv=e1-extractor-v1-p322c5a23e9b7|think=0")  # re-congelado en P3c-2
    check("P10 requests E3 sobre la salida r2 simulada, byte a byte en doble corrida", tot3 == 2439 and ig3 == tot3,
          f"{ig3}/{tot3}")
    # P3c-2, punto f: cap::tabla037 pasa a residual, y cap::6.2.2.6, que no trae otra tabla serializada, deja de
    # llevar la NOTA de tablas confiables (37 → 36). Con la E0 de C2 (U-REEXT-T0, T1): ric::4.3.3 deja de llevarla y
    # pasan a llevarla ric::4.4.1 a ric::4.4.4 (data/experiment/r2_codigo2/freno_c2.md:68): 36 − 1 + 4 = 39.
    check("P10 NOTAS r2 de E3: 212 encabezados de lista y 39 unidades con tabla serializada confiable",
          n_enc == 212 and n_tab == 39, f"encabezados={n_enc} tablas={n_tab}")
    check("P10 prefijo de E3 sin cambio (candado 21a836c7de6d)", prompt_e3.PREFIJO_HASH == "21a836c7de6d")
    huellas = []
    for i in (1, 2):
        sal = tmp / f"r2b_stub_{i}"
        r = subprocess.run([PY, str(AQUI / "corpus_v2" / "runner_corpus.py"), "--stub", "--salida", str(sal),
                            "--tos", "pro", "--manifiesto", str(MANIFIESTO_R2B)], capture_output=True, text=True)
        huellas.append((r.returncode, huella_stub(sal), sal))
    (rc1, h1, s1), (rc2, h2, _s2) = huellas
    res3 = json.loads((s1 / "pro" / "resumen_e3.json").read_text(encoding="utf-8")) if rc1 == 0 else {}
    check("P10 runner r2b con clientes simulados (pro): termina bien y la huella es idéntica en doble corrida",
          rc1 == rc2 == 0 and h1 == h2, f"rc={rc1},{rc2}")
    check("P10 runner r2b: el perfil activa el E2 r2 y el resumen de E3 lista las exenciones de la ampliación",
          (s1 / "pro" / "grafo_r2_pro.json").exists() and "exenciones_ampliacion_laudo_b" in res3
          and res3.get("unidades_eximidas_ampliacion") == [])


def p11_sellado_v3(tmp: Path) -> None:
    import perfil_e1          # noqa: PLC0415
    import validador_e1       # noqa: PLC0415
    import runner_corpus as RC  # noqa: PLC0415
    man = MC.cargar(MANIFIESTO_T0)
    pf = perfil_e1.perfil(man.perfil_e1)
    keys1 = _keys_db(DB_E1, tmp)
    ns1 = cliente_e1.namespace_e1(prefijo_hash=pf.prefijo_hash_para_namespace)
    tot = hit = 0
    for to in man.orden_corrida:
        for c in comun_e1.cargar_chunks((to,), e0_dir=man.e0_salida):
            tot += 1
            hit += lc.compute_key(ns1, lc.canonical_request(pf.build_request_kwargs(c, model=RC.MODEL_E1))) in keys1
    check("P11 v3_b54: keys E1 de las 2.434 unidades de la tanda 0 en la caché (prefijo sellado intacto)",
          tot == 2434 and hit == tot, f"{hit}/{tot}")
    keys3 = _keys_db(DB_E3, tmp)
    ns3 = cliente_e3.namespace_e3()
    tot3 = hit3 = 0
    for to in man.orden_corrida:
        chunks = comun_e3.cargar_chunks((to,), e0_dir=man.e0_salida)
        regs = comun_e3.cargar_extracciones(SALIDA_T0 / to / "extracciones_e1_compact.jsonl")
        for c, v in comun_e3.pares_de(chunks, regs):
            tot3 += 1
            hit3 += lc.compute_key(ns3, lc.canonical_request(
                prompt_e3.build_request_kwargs(c, v, model=RC.MODEL_E3))) in keys3
    check("P11 v3_b54: keys E3 de los pares de la salida sellada de la tanda 0 en la caché (mensaje sin cambio)",
          tot3 > 0 and hit3 == tot3, f"{hit3}/{tot3}")
    tot_v = ig_v = 0
    for to in man.orden_corrida:
        chunks = {c["id"]: c for c in comun_e1.cargar_chunks((to,), e0_dir=man.e0_salida)}
        for linea in (SALIDA_T0 / to / "extracciones_e1.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(linea)
            if r.get("tool_input_crudo") is None or r.get("validacion") is None:
                continue
            tot_v += 1
            d = validador_e1.validar_salida(r["tool_input_crudo"], chunks[r["chunk_id"]],
                                            esquema=pf.esquema).as_dict()
            ig_v += json.dumps(d, ensure_ascii=False, sort_keys=True) == json.dumps(r["validacion"], ensure_ascii=False,
                                                                                    sort_keys=True)
    check("P11 v3_b54: validación recomputada del crudo de la tanda 0 == la guardada (validador_e1 sin cambio en v3)",
          tot_v > 0 and ig_v == tot_v, f"{ig_v}/{tot_v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saltear-e0", action="store_true",
                    help="omite P2 (el punto lento) — SOLO para iterar en "
                         "desarrollo; la corrida de cierre va sin este flag")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="selftest_manifiesto_") as td:
        tmp = Path(td)
        man = p1_loader(tmp)
        if args.saltear_e0:
            print("[--saltear-e0] P2 OMITIDO (corrida de desarrollo)", flush=True)
        else:
            p2_e0(tmp)
        p3_requests_e1(man, tmp)
        p4_requests_e3(man, tmp)
        p5_e2(man)
        p6_ensamblado(man)
        p7_runner_stub(tmp)
        p8_sin_oraculo(tmp)
        p9_gancho(tmp)
        p10_r2b(tmp)
        p11_sellado_v3(tmp)

    print(f"\nselftest manifiesto: {_n - _fallos}/{_n}"
          + ("" if not _fallos else f"  ({_fallos} FALLOS)"), flush=True)
    return 0 if not _fallos else 1


if __name__ == "__main__":
    sys.exit(main())
