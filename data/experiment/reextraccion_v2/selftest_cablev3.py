"""
selftest_cablev3.py — U-CABLE-V3: selftest del cableado del prefijo v3 a
producción (fase 2). USD 0 / sin red: todo corre con stubs, material sellado
que se LEE (salida_enm01, corpus_v2/salida, e0_dry, PDFs de escalado_prep) y
directorios temporales.

Bloques (diseño aprobado §5 + resoluciones 1 y 2 del freno 1):
  B1  candados: el perfil v3 recomputa sha/hash contra el sello de U-B5.4
      (literales PROPIOS de este selftest) y FRENA si el módulo v3 reportara
      otro sha (simulación por monkeypatch, restaurada).
  B2  mensajes: chunk dev byte-idéntico a producción; TO con rol nuevo
      (traval) con línea de alcance y guarda de ejecuta; mapeo a clase
      (ayccef) con el id de CLASE como «sujeto por defecto del TO»; ri2_ci
      (dos clases, variante declarada); hueco (docvig) sin línea.
  B3  validador con esquema v3 — POR EXTENSIÓN (resolución 1): los 102
      sujetos uno a uno, los 9 tipos uno a uno, los 13 predicados uno a uno
      (instancia mínima de firma válida cada uno), conteos recomputados;
      rechazos: 5 retirados, rol viejo de snp_cec, type/predicate fuera del
      vocabulario congelado. Resolución 2: properties.tipo dentro del enum
      pasa tal cual; fuera de enum normalizado a "otra" y contado;
      requisito_de_estructura contado aparte; default (esquema None) SIN
      cambio, verificado contra registros REALES persistidos de la corrida
      dev (igualdad de dicts contra extracciones_e1_compact.jsonl).
  B4  namespaces: el del perfil v3 lleva 54a111e2175f; el default es el
      histórico; nunca colisionan.
  B5  manifiesto sintético v3 (PDFs reales de escalado_prep, solo lectura):
      carga con perfil_e1 "v3_b54"; adversariales de roles v3 (clase mal
      declarada, ri2_ci con string, hueco con rol, entrada silenciada).
  B6  runner: fase E1 stub en proceso (los requests llevan el system v3,
      sha recomputado) + corrida --stub completa por subprocess (banner con
      el perfil, exit 0, reanudación idempotente sin duplicar).
  B7  ratchet: la re-extracción usa el prefijo del perfil (v3 byte-idéntico
      al de la fase E1; feedback después del breakpoint); default
      byte-idéntico al histórico.
  B8  E2 con esquema y labels v3: ensambla Potestad/condicion_de y nodos de
      sujeto v3 con label y nivel reales (cero fallback); el default
      byte-idéntico lo cubre P5 de selftest_manifiesto (declarado).

Uso:  .venv/bin/python3 <ruta>/selftest_cablev3.py   (corrible desde cwd ajeno)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent                   # reextraccion_v2/
REPO = AQUI.parents[2]
for sub in ("e1_extractor", "e3_verificador", "e2_reduce", "corpus_v2"):
    sys.path.insert(0, str(AQUI / sub))
sys.path.insert(0, str(AQUI))

import comun_e1                         # noqa: E402
import prompt_e1                        # noqa: E402
import perfil_e1                        # noqa: E402
import cliente_e1                       # noqa: E402
import validador_e1                     # noqa: E402
import ratchet_e3                       # noqa: E402
import e2_lib                           # noqa: E402
import manifiesto_corpus as MC          # noqa: E402
import runner_corpus as RC              # noqa: E402

PY = sys.executable
E0_DRY = REPO / "data" / "experiment" / "escalado_prep" / "e0_dry"
PDFS = REPO / "data" / "experiment" / "escalado_prep" / "pdfs"
SALIDA_SELLADA = AQUI / "corpus_v2" / "salida"

# Literales del sello de U-B5.4 — PROPIOS de este selftest, independientes de
# los del shim (doble candado).
SHA_V3 = "35e88c2dd0a2920302c29005b08ab9689405606d4bd5fcf8fb7ce807b1a3c512"
HASH_V3 = "54a111e2175f"

_n = 0
_fallos = 0


def check(desc: str, ok: bool, detalle: str = "") -> None:
    global _n, _fallos
    _n += 1
    if not ok:
        _fallos += 1
    print(f"[{_n:2d}] {'ok   ' if ok else 'FALLO'} {desc}"
          + (f" — {detalle}" if detalle else ""), flush=True)


def chunk_dry(to: str, idx: int = 0) -> dict:
    with (E0_DRY / to / f"chunks_{to}.json").open(encoding="utf-8") as f:
        return json.load(f)[idx]


# ========================================================================= #
# B1 — candados del perfil v3                                               #
# ========================================================================= #

def b1_candados():
    p3 = perfil_e1.perfil("v3_b54")
    import prompt_v3_b54 as v3  # ya en sys.path vía el perfil

    check("B1 sha del prefijo v3 recomputado == sello U-B5.4",
          hashlib.sha256(v3.PREFIJO_SISTEMA_V3.encode("utf-8")).hexdigest() == SHA_V3)
    check("B1 hash canónico (system+tools) v3 == sello",
          hashlib.sha256(v3.PREFIJO_CANONICO_V3.encode("utf-8")).hexdigest()[:12]
          == HASH_V3 == p3.prefijo_hash)

    # El perfil FRENA si el módulo v3 reportara otro sha (monkeypatch,
    # restaurado; el registro memoizado se limpia para forzar reconstrucción).
    orig = v3.PREFIJO_SHA256_V3
    perfil_e1._cache.pop("v3_b54", None)
    try:
        v3.PREFIJO_SHA256_V3 = "0" * 64
        try:
            perfil_e1.perfil("v3_b54")
            freno = False
        except RuntimeError:
            freno = True
    finally:
        v3.PREFIJO_SHA256_V3 = orig
        perfil_e1._cache.pop("v3_b54", None)
    check("B1 el perfil FRENA (RuntimeError) ante un sha que no reproduce el "
          "sello", freno)
    p3b = perfil_e1.perfil("v3_b54")
    check("B1 restaurado, el perfil vuelve a construirse con el hash sellado",
          p3b.prefijo_hash == HASH_V3)
    try:
        perfil_e1.perfil("v9_inexistente")
        check("B1 perfil desconocido → ValueError", False, "no falló")
    except ValueError as e:
        check("B1 perfil desconocido → ValueError", "desconocido" in str(e))
    return p3b


# ========================================================================= #
# B2 — mensajes                                                             #
# ========================================================================= #

def b2_mensajes(p3):
    import prompt_v3_b54 as v3

    c_dev = comun_e1.cargar_chunks(("pro",), e0_dir=comun_e1.E0_SALIDA_ENM01)[0]
    kw = p3.build_request_kwargs(c_dev, model="claude-haiku-4-5")
    check("B2 chunk dev: mensaje v3 BYTE-IDÉNTICO al de producción",
          kw["messages"][0]["content"] == prompt_e1.build_user_message(c_dev))
    check("B2 chunk dev: system v3 en bloque único con cache_control (D1) y "
          "texto == prefijo v3 sellado",
          isinstance(kw["system"], list) and len(kw["system"]) == 1
          and kw["system"][0]["cache_control"] == {"type": "ephemeral"}
          and hashlib.sha256(kw["system"][0]["text"].encode("utf-8")).hexdigest() == SHA_V3)
    check("B2 chunk dev: tools == [TOOL_SCHEMA_V3] (enum de 102)",
          kw["tools"] == [v3.TOOL_SCHEMA_V3] and len(
              kw["tools"][0]["input_schema"]["properties"]["relations"]["items"]
              ["properties"]["sujeto_id"]["enum"]) == 102)

    m_rol = p3.build_user_message(chunk_dry("traval"))
    check("B2 TO con rol nuevo (traval): línea de alcance con el rol",
          "Alcance de este TO: Sujeto_rol_alcance_traval = {" in m_rol)
    check("B2 TO con rol nuevo: guarda de ejecuta presente",
          "NO es el ejecutor por defecto en ejecuta." in m_rol)

    m_cl = p3.build_user_message(chunk_dry("ayccef"))
    check("B2 mapeo a clase (ayccef): el id de CLASE como sujeto por defecto "
          "del TO (decisión 2)",
          "usá Sujeto_entidad_financiera como sujeto" in m_cl
          and "Alcance de este TO:" in m_cl)

    m_2c = p3.build_user_message(chunk_dry("ri2_ci"))
    check("B2 ri2_ci (dos clases): variante declarada de la línea",
          "usá Sujeto_casa_de_cambio o Sujeto_agencia_de_cambio como sujeto, "
          "según corresponda" in m_2c)

    m_hueco = p3.build_user_message(chunk_dry("docvig"))
    check("B2 hueco (docvig): SIN línea de alcance (válvula abierta)",
          "Alcance de este TO:" not in m_hueco)


# ========================================================================= #
# B3 — validador con esquema v3, POR EXTENSIÓN (resolución 1) + resolución 2 #
# ========================================================================= #

CHUNK_FX = {"id": "fx::1.1", "to": "fx", "archivo": "traval.pdf",
            "unidad": "1.1", "titulo": "t 1.1", "tipo": "punto_terminal",
            "herencia": [], "flags": {}}


def _val(tool_input, esquema):
    return validador_e1.validar_salida(tool_input, CHUNK_FX, esquema=esquema)


def b3_validador(p3):
    import prompt_v3_b54 as v3
    import prompt_congelado as pc
    esq = p3.esquema

    # --- 102 sujetos, uno a uno (aplica_a desde una Obligacion) ---
    ok_s = 0
    for s in v3.SUJETOS_CATALOGO_V3:
        ti = {"entities": [
                {"local_id": "to", "type": "TextoOrdenado", "label": "TO", "punto": "1.1"},
                {"local_id": "o1", "type": "Obligacion", "label": "deber", "punto": "1.1"}],
              "relations": [
                {"source": "o1", "predicate": "aplica_a", "punto": "1.1",
                 "sujeto_id": s}]}
        r = _val(ti, esq)
        ok_s += (len(r.relaciones) == 1 and not r.rechazos)
    check("B3 catálogo v3 POR EXTENSIÓN: los 102 sujetos aceptados (102/102 "
          "recomputado)", ok_s == len(v3.SUJETOS_CATALOGO_V3) == 102,
          f"{ok_s}/102")

    # --- 9 tipos, uno a uno ---
    ok_t = 0
    for t in esq.entity_types:
        r = _val({"entities": [{"local_id": "e1", "type": t, "label": "x",
                                "punto": "1.1"}], "relations": []}, esq)
        ok_t += (len(r.entidades) == 1 and not r.rechazos)
    check("B3 tipos congelados POR EXTENSIÓN: 9/9 aceptados uno a uno",
          ok_t == len(esq.entity_types) == 9, f"{ok_t}/9")

    # --- 13 predicados, uno a uno, con instancia mínima de firma válida ---
    ok_p = 0
    for pred in esq.predicates:
        dom, ran = pc.DOMAIN_RANGE_CONGELADO[pred]
        if pred in esq.sujeto_predicates:
            tipo_chunk = sorted((dom if pred == "aplica_a" else ran) - {"Sujeto"})[0]
            ti = {"entities": [{"local_id": "e1", "type": tipo_chunk,
                                "label": "x", "punto": "1.1"}],
                  "relations": [{("source" if pred == "aplica_a" else "target"): "e1",
                                 "predicate": pred, "punto": "1.1",
                                 "sujeto_id": "Sujeto_bcra"}]}
        else:
            ti = {"entities": [
                    {"local_id": "e1", "type": sorted(dom)[0], "label": "a", "punto": "1.1"},
                    {"local_id": "e2", "type": sorted(ran)[0], "label": "b", "punto": "1.1"}],
                  "relations": [{"source": "e1", "target": "e2",
                                 "predicate": pred, "punto": "1.1"}]}
        r = _val(ti, esq)
        ok_p += (len(r.relaciones) == 1 and not r.rechazos)
    check("B3 predicados congelados POR EXTENSIÓN: 13/13 aceptados con firma "
          "válida (condicion_de incluido)",
          ok_p == len(esq.predicates) == 13, f"{ok_p}/13")

    # --- rechazos: 5 retirados + rol viejo de snp_cec, uno a uno ---
    rechazados = 0
    para_rechazo = list(v3.RETIROS_V3) + ["Sujeto_rol_alcance_snp_cec"]
    for s in para_rechazo:
        ti = {"entities": [{"local_id": "o1", "type": "Obligacion",
                            "label": "deber", "punto": "1.1"}],
              "relations": [{"source": "o1", "predicate": "aplica_a",
                             "punto": "1.1", "sujeto_id": s}]}
        r = _val(ti, esq)
        rechazados += any(x["motivo"] == "sujeto_id_fuera_de_catalogo"
                          for x in r.rechazos)
    check("B3 rechazos: 5 retirados + rol viejo de snp_cec (6/6, motivo "
          "sujeto_id_fuera_de_catalogo)", rechazados == 6, f"{rechazados}/6")

    r = _val({"entities": [{"local_id": "e1", "type": "TipoInventado",
                            "label": "x", "punto": "1.1"}], "relations": []}, esq)
    check("B3 type fuera del vocabulario congelado rechazado",
          any(x["motivo"] == "type_invalido" for x in r.rechazos))
    r = _val({"entities": [{"local_id": "e1", "type": "Obligacion", "label": "x",
                            "punto": "1.1"}],
              "relations": [{"source": "e1", "target": "e1",
                             "predicate": "regulado_por", "punto": "1.1"}]}, esq)
    check("B3 predicate fuera del vocabulario congelado rechazado",
          any(x["motivo"] == "predicado_invalido" for x in r.rechazos))

    # --- resolución 2: normalización de Obligacion.properties.tipo ---
    def _ob(tipo):
        return {"entities": [{"local_id": "o1", "type": "Obligacion",
                              "label": "deber", "punto": "1.1",
                              "properties": {"tipo": tipo}}], "relations": []}
    r = _val(_ob("calculo"), esq)
    check("B3 resol.2: valor del enum pasa tal cual, contadores en 0",
          r.entidades[0]["properties"]["tipo"] == "calculo"
          and r.metricas["tipo_obligacion_normalizados"] == 0
          and r.metricas["tipo_obligacion_requisito_de_estructura"] == 0)
    r = _val(_ob("deber_generico"), esq)
    check("B3 resol.2: fuera de enum → 'otra', contado y con advertencia "
          "(registro, no rechazo)",
          r.entidades[0]["properties"]["tipo"] == "otra" and not r.rechazos
          and r.metricas["tipo_obligacion_normalizados"] == 1
          and r.metricas["tipo_obligacion_requisito_de_estructura"] == 0
          and any(a["tipo"] == "tipo_obligacion_fuera_de_enum"
                  for a in r.advertencias))
    r = _val(_ob("requisito_de_estructura"), esq)
    check("B3 resol.2: requisito_de_estructura → 'otra' con contador SEPARADO "
          "(vigilancia (5))",
          r.entidades[0]["properties"]["tipo"] == "otra"
          and r.metricas["tipo_obligacion_normalizados"] == 1
          and r.metricas["tipo_obligacion_requisito_de_estructura"] == 1)
    r = validador_e1.validar_salida(_ob("deber_generico"), CHUNK_FX)  # default
    check("B3 resol.2: default (esquema None): properties.tipo queda tal "
          "cual y SIN claves de contadores",
          r.entidades[0]["properties"]["tipo"] == "deber_generico"
          and "tipo_obligacion_normalizados" not in r.metricas)

    # --- no-regresión del default contra registros REALES persistidos ---
    chunks_pro = {c["id"]: c for c in comun_e1.cargar_chunks(
        ("pro",), e0_dir=comun_e1.E0_SALIDA_ENM01)}
    n_cmp = n_ok = 0
    with (SALIDA_SELLADA / "pro" / "extracciones_e1_compact.jsonl").open(
            encoding="utf-8") as f:
        for linea in f:
            if n_cmp >= 25:
                break
            reg = json.loads(linea)
            if reg.get("error") or reg.get("tool_input_crudo") is None:
                continue
            c = chunks_pro.get(reg["chunk_id"])
            if c is None:
                continue
            n_cmp += 1
            v = validador_e1.validar_salida(reg["tool_input_crudo"], c).as_dict()
            n_ok += (v == reg["validacion"])
    check("B3 default sin regresión: re-validación de registros reales dev == "
          "validación persistida (igualdad de dicts)",
          n_cmp == 25 and n_ok == n_cmp, f"{n_ok}/{n_cmp}")


# ========================================================================= #
# B4 — namespaces                                                           #
# ========================================================================= #

def b4_namespaces(p3):
    ns_def = cliente_e1.namespace_e1()
    ns_v3 = cliente_e1.namespace_e1(prefijo_hash=p3.prefijo_hash_para_namespace)
    check("B4 namespace default == histórico (hash de producción dev)",
          f"-p{prompt_e1.PREFIJO_HASH}" in ns_def
          and ns_def == cliente_e1.namespace_e1(prefijo_hash=None))
    check("B4 namespace v3 lleva el hash sellado y NO colisiona con el "
          "histórico", f"-p{HASH_V3}" in ns_v3 and ns_v3 != ns_def)
    ns_abierto = cliente_e1.namespace_e1(canal_abierto=True)
    check("B4 namespace del canal abierto intacto y distinto de ambos",
          ns_abierto not in (ns_def, ns_v3))


# ========================================================================= #
# B5 — manifiesto sintético v3                                              #
# ========================================================================= #

TOS_FX = ("traval", "ayccef", "ri2_ci", "docvig")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _manifiesto_v3(tmp: Path, e0_dir: Path) -> dict:
    def rol_de(to):
        if to == "traval":
            return "Sujeto_rol_alcance_traval"
        if to == "ayccef":
            return "Sujeto_entidad_financiera"
        if to == "ri2_ci":
            return ["Sujeto_casa_de_cambio", "Sujeto_agencia_de_cambio"]
        return None  # docvig: hueco
    return {
        "version": "1", "nombre": "fxv3",
        "descripcion": "corpus sintético del selftest de U-CABLE-V3",
        "perfil_e1": "v3_b54",
        "tos": [{"id": to, "archivo": f"{to}.pdf",
                 "pdf": str((PDFS / f"{to}.pdf").relative_to(REPO)),
                 "sha256_pdf": _sha(PDFS / f"{to}.pdf"),
                 "rol_alcance": rol_de(to)} for to in TOS_FX],
        "orden_corrida": list(TOS_FX),
        "oraculo": {"mapa_territorio": None, "limitaciones_e0": []},
        "limites": {"tope_global_usd": 1.0, "margen_unidad_usd": 0.05,
                    "estimado_usd": {to: {"e1": 0.0, "e3": 0.0} for to in TOS_FX},
                    "checkpoint_cada": {}, "chequeos_hits": []},
        "tests_respuesta_conocida": None,
        "rutas": {"e0_salida": str(e0_dir)},
        "indice_fragmentos": None,
    }


def _escribir_man(d: dict, tmp: Path, nombre: str) -> Path:
    d = json.loads(json.dumps(d))
    d["nombre"] = nombre
    p = tmp / f"{nombre}.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return p


def _chunks_fx(e0_dir: Path) -> None:
    e0_dir.mkdir(parents=True, exist_ok=True)
    for to in TOS_FX:
        chunks = [{"id": f"{to}::1.{i}", "to": to, "archivo": f"{to}.pdf",
                   "unidad": f"1.{i}", "titulo": f"t 1.{i}",
                   "tipo": "punto_terminal", "herencia": [], "flags": {},
                   "texto": f"Texto sintético del punto 1.{i} del TO {to}."}
                  for i in (1, 2)]
        (e0_dir / f"chunks_{to}.json").write_text(
            json.dumps(chunks, ensure_ascii=False), encoding="utf-8")


def b5_manifiesto(tmp: Path):
    e0_dir = tmp / "fx_e0"
    _chunks_fx(e0_dir)
    base = _manifiesto_v3(tmp, e0_dir)
    man = MC.cargar(_escribir_man(base, tmp, "fxv3"))
    check("B5 manifiesto sintético v3 carga (perfil v3, roles v3, hueco null)",
          man.perfil_e1 == "v3_b54" and man.ids == list(TOS_FX))

    adversos = [
        ("clase mal declarada (rol en vez de clase)", "fxv3_a",
         lambda d: d["tos"][1].update(rol_alcance="Sujeto_rol_alcance_ayccef"),
         "≠ rol del catálogo"),
        ("ri2_ci con string en vez de lista", "fxv3_b",
         lambda d: d["tos"][2].update(rol_alcance="Sujeto_casa_de_cambio"),
         "clase_ids"),
        ("hueco (docvig) con rol declarado", "fxv3_c",
         lambda d: d["tos"][3].update(rol_alcance="Sujeto_rol_fantasma"),
         "no declara rol"),
        ("entrada del catálogo silenciada con null", "fxv3_d",
         lambda d: d["tos"][0].update(rol_alcance=None),
         "no se silencia"),
    ]
    for desc, nombre, mutar, frag in adversos:
        d = json.loads(json.dumps(base))
        mutar(d)
        try:
            MC.cargar(_escribir_man(d, tmp, nombre))
            check(f"B5 adversarial rechazado: {desc}", False, "cargó sin error")
        except MC.ErrorManifiesto as e:
            check(f"B5 adversarial rechazado: {desc}", frag in str(e),
                  str(e)[:70])
    return man


# ========================================================================= #
# B6 — runner con perfil v3 (stub)                                          #
# ========================================================================= #

def b6_runner(tmp: Path, man):
    # (a) fase E1 en proceso: el stub captura el sha del system de cada request.
    RC.configurar(man)
    salida_a = tmp / "stub_a"
    salida_a.mkdir()
    estado = RC.Estado(salida_a)
    stub = RC.StubE1Corpus()
    RC.fase_e1("traval", stub, estado, salida_a, None, None, None)
    check("B6 fase E1 (stub, en proceso): TODOS los requests llevan el system "
          "v3 (sha recomputado == sello)",
          len(stub.system_shas) == 2 and set(stub.system_shas) == {SHA_V3})
    jsonl = salida_a / "traval" / "extracciones_e1.jsonl"
    regs = [json.loads(x) for x in jsonl.read_text(encoding="utf-8").splitlines()]
    check("B6 fase E1: validaciones con contadores v3 visibles (vigilancia (5) "
          "en 0)",
          all(r["validacion"]["metricas"]
              .get("tipo_obligacion_normalizados") == 0 for r in regs))
    resumen = json.loads((salida_a / "traval" / "resumen_e1.json")
                         .read_text(encoding="utf-8"))
    check("B6 resumen_e1 del TO v3 con los dos contadores de la resolución 2",
          resumen.get("tipo_obligacion_normalizados") == 0
          and resumen.get("tipo_obligacion_requisito_de_estructura") == 0)

    # (b) corrida --stub completa por subprocess + reanudación idempotente.
    salida_b = tmp / "stub_b"
    cmd = [PY, str(AQUI / "corpus_v2" / "runner_corpus.py"), "--stub",
           "--salida", str(salida_b), "--manifiesto", str(man.path)]
    r1 = subprocess.run(cmd, capture_output=True, text=True)
    check("B6 corrida --stub completa (4 TOs, E1→E3→E2) termina bien",
          r1.returncode == 0, (r1.stderr or "")[-120:])
    check("B6 banner declara el perfil y el hash v3",
          "perfil E1 v3_b54" in r1.stdout and HASH_V3 in r1.stdout)
    check("B6 grafos E2 generados para los 4 TOs",
          all((salida_b / to / f"grafo_{to}.json").exists() for to in TOS_FX))
    n_lineas = sum(1 for _ in (salida_b / "traval" / "extracciones_e1.jsonl")
                   .open(encoding="utf-8"))
    r2 = subprocess.run(cmd, capture_output=True, text=True)
    n_lineas2 = sum(1 for _ in (salida_b / "traval" / "extracciones_e1.jsonl")
                    .open(encoding="utf-8"))
    check("B6 reanudación idempotente: segunda corrida saltea fases cerradas y "
          "no duplica",
          r2.returncode == 0 and "ya cerrada — se saltea" in r2.stdout
          and n_lineas == n_lineas2, f"{n_lineas} vs {n_lineas2}")

    # restaurar el estado de módulo del runner (manifiesto de desarrollo).
    RC.configurar(MC.cargar(RC.MANIFIESTO_DEFAULT))
    check("B6 runner restaurado al manifiesto default (perfil produccion_dev)",
          RC.PERFIL.nombre == "produccion_dev")


# ========================================================================= #
# B7 — ratchet con el perfil de la corrida                                  #
# ========================================================================= #

FALTANTES_FX = [{"tipo": "clausula_omitida", "ubicacion": "final",
                 "severidad": "alta", "cita_textual_del_fuente": "x"}]


def b7_ratchet(p3):
    import prompt_v3_b54 as v3
    c_dev = comun_e1.cargar_chunks(("pro",), e0_dir=comun_e1.E0_SALIDA_ENM01)[0]
    kw_hist = prompt_e1.build_request_kwargs(c_dev, model="claude-haiku-4-5")
    kw_def = ratchet_e3.build_reextraccion_kwargs(
        c_dev, FALTANTES_FX, model="claude-haiku-4-5")
    check("B7 default: prefijo (system+tools) byte-idéntico al histórico y "
          "feedback tras el breakpoint",
          kw_def["system"] == kw_hist["system"]
          and kw_def["tools"] == kw_hist["tools"]
          and kw_def["messages"][0]["content"].startswith(
              prompt_e1.build_user_message(c_dev))
          and ratchet_e3.MARCA_REINTENTO in kw_def["messages"][0]["content"])

    c_tv = chunk_dry("traval")
    kw_v3 = ratchet_e3.build_reextraccion_kwargs(
        c_tv, FALTANTES_FX, model="claude-haiku-4-5", perfil=p3)
    kw_e1_v3 = p3.build_request_kwargs(c_tv, model="claude-haiku-4-5")
    check("B7 perfil v3: el reintento usa el MISMO prefijo v3 que la fase E1 "
          "de su corrida (system+tools byte-idénticos)",
          kw_v3["system"] == kw_e1_v3["system"]
          and kw_v3["tools"] == [v3.TOOL_SCHEMA_V3]
          and kw_v3["messages"][0]["content"].startswith(
              p3.build_user_message(c_tv))
          and ratchet_e3.MARCA_REINTENTO in kw_v3["messages"][0]["content"])


# ========================================================================= #
# B8 — E2 con esquema y labels v3                                           #
# ========================================================================= #

def b8_e2(tmp: Path, p3):
    fxdir = tmp / "fx_e2_e0"
    fxdir.mkdir()
    chunk = {"id": "fxv::1.1", "to": "fxv", "archivo": "traval.pdf",
             "unidad": "1.1", "titulo": "t 1.1", "tipo": "punto_terminal",
             "herencia": [], "flags": {}, "texto": "x"}
    (fxdir / "chunks_fxv.json").write_text(
        json.dumps([chunk], ensure_ascii=False), encoding="utf-8")

    ti = {"entities": [
            {"local_id": "to", "type": "TextoOrdenado", "label": "TO fx", "punto": "1.1"},
            {"local_id": "p1", "type": "Potestad", "label": "potestad fx", "punto": "1.1"},
            {"local_id": "c1", "type": "Condicion", "label": "condicion fx", "punto": "1.1"},
            {"local_id": "o1", "type": "Obligacion", "label": "deber fx", "punto": "1.1"},
            {"local_id": "op1", "type": "Operacion", "label": "operacion fx", "punto": "1.1"}],
          "relations": [
            {"source": "p1", "target": "to", "predicate": "establecida_en", "punto": "1.1"},
            {"source": "c1", "target": "o1", "predicate": "condicion_de", "punto": "1.1"},
            {"source": "o1", "predicate": "aplica_a", "punto": "1.1",
             "sujeto_id": "Sujeto_rol_alcance_traval"},
            {"target": "op1", "predicate": "ejecuta", "punto": "1.1",
             "sujeto_id": "Sujeto_camara_electronica_de_compensacion"}]}
    val = validador_e1.validar_salida(ti, chunk, esquema=p3.esquema)
    check("B8 cadena validador→E2: extracción v3 íntegra aceptada (5 ent, "
          "4 rel, 0 rechazos)",
          len(val.entidades) == 5 and len(val.relaciones) == 4
          and not val.rechazos)

    jl = tmp / "fxv.jsonl"
    jl.write_text(json.dumps({"chunk_id": "fxv::1.1", "error": None,
                              "validacion": val.as_dict()},
                             ensure_ascii=False) + "\n", encoding="utf-8")
    res = e2_lib.reducir("fxv", jl, censo_oraculo=e2_lib.SIN_ORACULO,
                         e0_dir=fxdir, limitaciones={},
                         esquema=p3.esquema, labels_catalogo=p3.labels_catalogo)
    nodos = {n["id"]: n for n in res["grafo"]["nodes"]}
    rol = nodos.get("Sujeto_rol_alcance_traval")
    cec = nodos.get("Sujeto_camara_electronica_de_compensacion")
    check("B8 E2 v3: Potestad y condicion_de ensamblados sin rechazos",
          res["reporte"]["nodes_by_type"].get("Potestad") == 1
          and res["reporte"]["edges_by_relation"].get("condicion_de") == 1
          and not res["reporte"]["rechazos_e2"])
    check("B8 E2 v3: nodos de sujeto con label y nivel REALES del catálogo "
          "v3 (cero fallback)",
          rol is not None and cec is not None
          and rol["label"] == "Sujetos comprendidos (Transportadoras de valores)"
          and rol["properties"]["nivel"] == "rol"
          and cec["label"].startswith("Cámaras electrónicas de compensación")
          and cec["properties"]["nivel"] == "clase"
          and "sujetos_sin_label_catalogo" not in res["reporte"]["stats"])
    # El default byte-idéntico de E2 lo demuestra P5 de selftest_manifiesto
    # (paridad de grafo/reporte/censo contra los artefactos sellados).


# ========================================================================= #

def main() -> int:
    p3 = b1_candados()
    b2_mensajes(p3)
    b3_validador(p3)
    b4_namespaces(p3)
    with tempfile.TemporaryDirectory(prefix="selftest_cablev3_") as td:
        tmp = Path(td)
        man = b5_manifiesto(tmp)
        b6_runner(tmp, man)
        b7_ratchet(p3)
        b8_e2(tmp, p3)

    print(f"\nselftest cable v3: {_n - _fallos}/{_n}"
          + ("" if not _fallos else f"  ({_fallos} FALLOS)"), flush=True)
    return 0 if not _fallos else 1


if __name__ == "__main__":
    sys.exit(main())
