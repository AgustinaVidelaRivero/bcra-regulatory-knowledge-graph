#!/usr/bin/env python3
"""Selftest de scripts/muestra_aristas_obs12.py (gate 8 de la fase 2 de B6.0).

Solo stdlib. Dos bloques:

(i)  Grafo sintético mínimo escrito acá mismo (aristas de extracción, de
     referencia, de esqueleto —con rol_fuente arriba y con rol_fuente solo en
     provenance— y padre_sugerido; una tripla duplicada; un chunk_id sin texto
     en E0; un TO sin archivo chunks_<to>.json; un provenance sin `to`; y,
     aparte, el mismo grafo con dos aristas `remite_a` del perfil r2, que se
     restan del universo igual que `referencia` —U-R2-CODIGO, R5.d—).
     Verifica el universo, el orden, el conteo de triplas duplicadas, el
     NO ENCONTRADO, los índices del sorteo, los códigos de salida del CLI y la
     byte-identidad de dos corridas. Escribe solo en un directorio temporal
     que se borra al terminar.

(ii) Corrida sobre r1 (data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json,
     sha256 0226e947…) con semilla 20260927 y --out reports/obs12_selftest_r1/:
     dos corridas byte-idénticas en el JSON (cmp y sha256), n = 12.010,
     0 triplas duplicadas, 30 índices distintos e iguales a los de la decisión 8
     del mandato, ninguna arista de la muestra con relation == 'referencia' ni
     rol_fuente == 'esqueleto', textos_no_encontrados = 0 y distribución de
     relaciones igual a la de la decisión 8.

Uso:
    PYTHONDONTWRITEBYTECODE=1 python3 scripts/selftest_muestra_aristas_obs12.py

Sale con código 0 si todos los casos pasan, 1 si alguno falla.
"""

import hashlib
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
RUTA_SCRIPT = os.path.join(AQUI, "muestra_aristas_obs12.py")

_spec = importlib.util.spec_from_file_location("muestra_aristas_obs12", RUTA_SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

# Bloque (ii): r1 y el resultado esperado (mandato U-OBS12-SORTEO, decisiones 7 y 8)
R1_KG = os.path.join(REPO, "data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json")
R1_KG_REL = "data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json"
R1_SHA = "0226e9477baee02d772bbfecee78a49441b189d0e0512ca5e22956dfb084196a"
R1_OUT_REL = "reports/obs12_selftest_r1"
R1_SEMILLA = 20260927
R1_N = 12010
R1_INDICES = [115, 200, 1159, 1168, 1270, 1750, 1973, 2184, 2334, 3031,
              3215, 3913, 4162, 4792, 5095, 5131, 5754, 5920, 6626, 7628,
              7971, 8111, 8265, 8531, 8821, 10078, 10277, 10433, 10884, 11167]
R1_RELACIONES = {"establecida_en": 11, "aplica_a": 8, "regula": 6,
                 "limita": 3, "exceptua": 1, "condiciona": 1}

# --------------------------------------------------------------------------- #
# Infraestructura mínima de casos
# --------------------------------------------------------------------------- #

RESULTADOS = []  # (bloque, nombre, ok, detalle)


def caso(bloque, nombre):
    def deco(fn):
        def wrapper(*a, **kw):
            try:
                fn(*a, **kw)
                RESULTADOS.append((bloque, nombre, True, ""))
                print("  OK   %s" % nombre)
            except Exception as exc:  # noqa: BLE001
                det = "%s: %s" % (type(exc).__name__, exc)
                RESULTADOS.append((bloque, nombre, False, det))
                print("  FAIL %s -> %s" % (nombre, det))
                traceback.print_exc()
        return wrapper
    return deco


def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def correr_cli(args, cwd=REPO):
    return subprocess.run([sys.executable, RUTA_SCRIPT] + args, cwd=cwd, env=ENV,
                          capture_output=True, text=True)


# --------------------------------------------------------------------------- #
# Bloque (i): grafo sintético
# --------------------------------------------------------------------------- #

def _prov(to, punto, chunk_id, rol_documental="punto_propio", **extra):
    p = {"to": to, "archivo": "TO_%s.pdf" % (to or "x"), "punto": punto,
         "rol_documental": rol_documental, "chunk_id": chunk_id,
         "paginas": [1], "ancestros": []}
    p.update(extra)
    return p


def _nodo(nid, tipo, label, props=None):
    return {"id": nid, "type": tipo, "label": label, "properties": props or {},
            "provenance": _prov("syn", "1.1", "syn::1.1"),
            "provenances": [_prov("syn", "1.1", "syn::1.1")]}


def _arista(s, r, t, prov, props=None, rol_fuente=None):
    e = {"source": s, "target": t, "relation": r, "provenance": prov, "provenances": [prov]}
    if props is not None:
        e["properties"] = props
    if rol_fuente is not None:
        e["rol_fuente"] = rol_fuente
    return e


def grafo_sintetico():
    nodes = [
        _nodo("Norma_A", "Norma", "Norma A", {"x": 1}),
        _nodo("Norma_B", "Norma", "Norma B"),
        _nodo("Sujeto_C", "Sujeto", "Sujeto C"),
        _nodo("Sujeto_D", "Sujeto", "Sujeto D"),
        _nodo("Excepcion_E", "Excepcion", "Excepción E"),
        _nodo("TO_Z", "TextoOrdenado", "TO Z"),
    ]
    # Orden deliberadamente desordenado respecto de la tripla.
    edges = [
        # extracción (dentro del universo)
        _arista("Norma_B", "regula", "Sujeto_C", _prov("syn", "1.2", "syn::1.2")),
        _arista("Norma_A", "regula", "Sujeto_C", _prov("syn", "1.1", "syn::1.1"), {"p": 1}),
        # referencia (fuera del universo)
        _arista("Excepcion_E", "referencia", "Norma_A", _prov("syn", "1.3", "syn::1.3"),
                {"clase": "interna"}, rol_fuente="referencia_cruzada"),
        # esqueleto con rol_fuente arriba (fuera del universo)
        _arista("Sujeto_D", "subclase_de", "Sujeto_C",
                _prov(None, "Punto 9", None, rol_documental="esqueleto"), rol_fuente="esqueleto"),
        # esqueleto con rol_fuente SOLO en provenance (fuera del universo, por el fallback de A4.1)
        _arista("Sujeto_C", "subclase_de", "Sujeto_D",
                _prov(None, "Punto 9", None, rol_documental="esqueleto", rol_fuente="esqueleto")),
        # padre_sugerido (DENTRO del universo)
        _arista("Sujeto_D", "padre_sugerido", "Sujeto_C", _prov("syn", "1.2", "syn::1.2"),
                {"flag": "padre_sugerido_no_laudado"}, rol_fuente="cuarentena_flaggeada"),
        # tripla duplicada de la primera de extracción (dentro; se cuenta 1 duplicada)
        _arista("Norma_A", "regula", "Sujeto_C", _prov("syn", "1.4", "syn::1.4")),
        # extracción con chunk_id inexistente en chunks_syn.json -> NO ENCONTRADO
        _arista("Norma_A", "aplica_a", "Sujeto_D", _prov("syn", "7.7", "syn::7.7")),
        # extracción con TO sin archivo chunks_<to>.json -> NO ENCONTRADO
        _arista("Norma_B", "establecida_en", "TO_Z", _prov("zzz", "2.1", "zzz::2.1")),
        # extracción con provenance sin `to` (se resuelve por el prefijo del chunk_id)
        _arista("Excepcion_E", "exceptua", "Norma_B", _prov(None, "1.3", "syn::1.3")),
    ]
    return {"nodes": nodes, "edges": edges}


CHUNKS_SYN = [
    {"id": "syn::1.1", "to": "syn", "archivo": "TO_syn.pdf", "unidad": "1.1", "titulo": "Uno",
     "texto": "1.1. Texto del punto uno.\nSegunda línea.", "herencia": [
         {"tipo": "encabezado", "unidad_origen": "S1", "texto": "Sección 1.", "paginas": [1]}],
     "paginas": [1]},
    {"id": "syn::1.2", "to": "syn", "archivo": "TO_syn.pdf", "unidad": "1.2", "titulo": "Dos",
     "texto": "1.2. Texto del punto dos.", "herencia": [], "paginas": [1]},
    {"id": "syn::1.3", "to": "syn", "archivo": "TO_syn.pdf", "unidad": "1.3", "titulo": "Tres",
     "texto": "1.3. Texto del punto tres.", "herencia": [], "paginas": [2]},
    {"id": "syn::1.4", "to": "syn", "archivo": "TO_syn.pdf", "unidad": "1.4", "titulo": "Cuatro",
     "texto": "1.4. Texto del punto cuatro.", "herencia": [], "paginas": [2]},
]

# Universo esperado del sintético, ya ordenado por la tripla:
UNIVERSO_ESPERADO = [
    ("Excepcion_E", "exceptua", "Norma_B"),
    ("Norma_A", "aplica_a", "Sujeto_D"),
    ("Norma_A", "regula", "Sujeto_C"),      # chunk syn::1.1 (primera en el kg)
    ("Norma_A", "regula", "Sujeto_C"),      # chunk syn::1.4 (duplicada, después por orden estable)
    ("Norma_B", "establecida_en", "TO_Z"),
    ("Norma_B", "regula", "Sujeto_C"),
    ("Sujeto_D", "padre_sugerido", "Sujeto_C"),
]


def preparar_sintetico(tmp):
    kg_ruta = os.path.join(tmp, "kg_sintetico.json")
    e0_dir = os.path.join(tmp, "e0")
    os.makedirs(e0_dir)
    with open(kg_ruta, "w", encoding="utf-8") as f:
        json.dump(grafo_sintetico(), f, ensure_ascii=False, indent=1)
    with open(os.path.join(e0_dir, "chunks_syn.json"), "w", encoding="utf-8") as f:
        json.dump(CHUNKS_SYN, f, ensure_ascii=False, indent=1)
    return kg_ruta, e0_dir


def bloque_i():
    print("Bloque (i): grafo sintético")
    tmp = tempfile.mkdtemp(prefix="obs12_selftest_")
    try:
        kg_ruta, e0_dir = preparar_sintetico(tmp)
        kg = grafo_sintetico()

        @caso("i", "universo: resta referencia y esqueleto (arriba y en provenance), conserva padre_sugerido")
        def c1():
            ext, conteos = mod.universo(kg["edges"])
            assert conteos["total_aristas"] == 10, conteos
            assert conteos["referencia_restadas"] == 1, conteos
            assert conteos["esqueleto_restadas"] == 2, conteos
            assert conteos["solapamiento_referencia_esqueleto"] == 0, conteos
            assert conteos["n"] == 7, conteos
            rels = [e["relation"] for e in ext]
            assert "referencia" not in rels and "subclase_de" not in rels, rels
            assert rels.count("padre_sugerido") == 1, rels
        c1()

        @caso("i", "orden: tripla (source, relation, target) lexicográfico y estable")
        def c2():
            ext, _ = mod.universo(kg["edges"])
            ordenado = mod.ordenar(ext)
            assert [mod.tripla(e) for e in ordenado] == UNIVERSO_ESPERADO, [mod.tripla(e) for e in ordenado]
            # estabilidad: la duplicada con chunk syn::1.1 viene antes que la de syn::1.4
            dups = [e for e in ordenado if mod.tripla(e) == ("Norma_A", "regula", "Sujeto_C")]
            assert [d["provenance"]["chunk_id"] for d in dups] == ["syn::1.1", "syn::1.4"]
        c2()

        @caso("i", "triplas_duplicadas: cuenta 1 y detalla la tripla con veces=2")
        def c3():
            ext, _ = mod.universo(kg["edges"])
            n_dup, det = mod.triplas_duplicadas(mod.ordenar(ext))
            assert n_dup == 1, n_dup
            assert det == [{"source": "Norma_A", "relation": "regula", "target": "Sujeto_C", "veces": 2}], det
        c3()

        @caso("i", "sortear: índices ascendentes iguales a random.Random(semilla).sample(range(n), k)")
        def c4():
            for sem in (1, 20260927, 99):
                assert mod.sortear(7, 3, sem) == sorted(random.Random(sem).sample(range(7), 3))
            assert mod.sortear(7, 7, 5) == list(range(7))
        c4()

        out_a = os.path.join(tmp, "out_a")

        @caso("i", "CLI con --n 7 (universo completo): NO ENCONTRADO x2, textos_no_encontrados=2, textos y herencia correctos")
        def c5():
            r = correr_cli(["--kg", kg_ruta, "--semilla", "1", "--n", "7", "--e0", e0_dir, "--out", out_a])
            assert r.returncode == 0, r.stderr
            s = json.load(open(os.path.join(out_a, "muestra_obs12.json"), encoding="utf-8"))
            assert s["n"] == 7 and s["k"] == 7 and s["indices"] == list(range(7)), (s["n"], s["k"], s["indices"])
            assert s["triplas_duplicadas"] == 1
            assert s["textos_no_encontrados"] == 2, s["textos_no_encontrados"]
            assert s["kg_sha256"] == sha256_archivo(kg_ruta)
            assert s["kg_ruta"] == kg_ruta and s["e0"] == e0_dir
            por_idx = {a["indice"]: a for a in s["aristas"]}
            # índice 1: Norma_A aplica_a Sujeto_D, chunk syn::7.7 inexistente
            assert por_idx[1]["texto_ancla"] == "NO ENCONTRADO: syn::7.7", por_idx[1]["texto_ancla"]
            assert por_idx[1]["herencia"] is None
            # índice 4: Norma_B establecida_en TO_Z, archivo chunks_zzz.json inexistente
            assert por_idx[4]["texto_ancla"] == "NO ENCONTRADO: zzz::2.1", por_idx[4]["texto_ancla"]
            # índice 2: Norma_A regula Sujeto_C (chunk syn::1.1) con texto y herencia del chunk
            assert por_idx[2]["texto_ancla"] == CHUNKS_SYN[0]["texto"]
            assert por_idx[2]["herencia"] == CHUNKS_SYN[0]["herencia"]
            assert por_idx[2]["properties"] == {"p": 1}
            # índice 3: la duplicada (chunk syn::1.4), properties null porque no tiene
            assert por_idx[3]["texto_ancla"] == CHUNKS_SYN[3]["texto"]
            assert por_idx[3]["properties"] is None
            # índice 0: provenance sin `to`, resuelto por el prefijo del chunk_id
            assert por_idx[0]["relation"] == "exceptua"
            assert por_idx[0]["texto_ancla"] == CHUNKS_SYN[2]["texto"]
            # índice 6: padre_sugerido con su rol_fuente
            assert por_idx[6]["relation"] == "padre_sugerido" and por_idx[6]["rol_fuente"] == "cuarentena_flaggeada"
            # nodos: id, type, label, properties
            assert por_idx[2]["source"] == {"id": "Norma_A", "type": "Norma", "label": "Norma A", "properties": {"x": 1}}
            # texto: el literal NO ENCONTRADO aparece exactamente 2 veces en el JSON
            txt = open(os.path.join(out_a, "muestra_obs12.json"), encoding="utf-8").read()
            assert txt.count("NO ENCONTRADO") == 2, txt.count("NO ENCONTRADO")
            # el md existe y numera 1..7
            md = open(os.path.join(out_a, "muestra_obs12.md"), encoding="utf-8").read()
            assert "## 7 · índice 6" in md and "## 1 · índice 0" in md
            assert "NO ENCONTRADO: syn::7.7" in md
            assert s["relaciones_en_muestra"] == {"regula": 3, "aplica_a": 1, "establecida_en": 1,
                                                  "exceptua": 1, "padre_sugerido": 1}, s["relaciones_en_muestra"]
        c5()

        @caso("i", "CLI con --n 3 (default de k es 30 > n=7: exige --n): índices del sorteo y k")
        def c6():
            out = os.path.join(tmp, "out_k3")
            r = correr_cli(["--kg", kg_ruta, "--semilla", "20260927", "--n", "3", "--e0", e0_dir, "--out", out])
            assert r.returncode == 0, r.stderr
            s = json.load(open(os.path.join(out, "muestra_obs12.json"), encoding="utf-8"))
            assert s["k"] == 3 and s["indices"] == sorted(random.Random(20260927).sample(range(7), 3))
            assert len(s["aristas"]) == 3 and [a["indice"] for a in s["aristas"]] == s["indices"]
        c6()

        @caso("i", "byte-identidad: dos corridas con los mismos argumentos dan el mismo JSON (otro --out y mismo --out)")
        def c7():
            out_b = os.path.join(tmp, "out_b")
            r = correr_cli(["--kg", kg_ruta, "--semilla", "1", "--n", "7", "--e0", e0_dir, "--out", out_b])
            assert r.returncode == 0, r.stderr
            ja = open(os.path.join(out_a, "muestra_obs12.json"), "rb").read()
            jb = open(os.path.join(out_b, "muestra_obs12.json"), "rb").read()
            assert ja == jb
            # mismo --out, sobrescribe idéntico
            r = correr_cli(["--kg", kg_ruta, "--semilla", "1", "--n", "7", "--e0", e0_dir, "--out", out_a])
            assert r.returncode == 0, r.stderr
            assert open(os.path.join(out_a, "muestra_obs12.json"), "rb").read() == ja
        c7()

        @caso("i", "semillas distintas dan índices distintos (n=7, k=3, semillas 1 y 2)")
        def c8():
            assert mod.sortear(7, 3, 1) != mod.sortear(7, 3, 2)
        c8()

        @caso("i", "sin --out: código 2, mensaje y nada escrito")
        def c9():
            vacio = os.path.join(tmp, "vacio")
            os.makedirs(vacio)
            r = correr_cli(["--kg", kg_ruta, "--semilla", "1", "--n", "3", "--e0", e0_dir], cwd=vacio)
            assert r.returncode == 2, (r.returncode, r.stderr)
            assert "--out" in r.stderr
            assert os.listdir(vacio) == [], os.listdir(vacio)
        c9()

        @caso("i", "--n mayor que el universo: código 2 y nada escrito")
        def c10():
            out = os.path.join(tmp, "out_grande")
            r = correr_cli(["--kg", kg_ruta, "--semilla", "1", "--n", "8", "--e0", e0_dir, "--out", out])
            assert r.returncode == 2, (r.returncode, r.stderr)
            assert not os.path.exists(out)
        c10()

        @caso("i", "--kg inexistente: código 2")
        def c11():
            r = correr_cli(["--kg", os.path.join(tmp, "no_existe.json"), "--semilla", "1",
                            "--out", os.path.join(tmp, "out_x")])
            assert r.returncode == 2, (r.returncode, r.stderr)
        c11()

        @caso("i", "--help: código 0 y lista las cinco opciones")
        def c12():
            r = correr_cli(["--help"])
            assert r.returncode == 0
            for op in ("--kg", "--semilla", "--out", "--n", "--e0"):
                assert op in r.stdout, op
        c12()

        @caso("i", "--e0 inexistente: no frena, todos los textos NO ENCONTRADO")
        def c13():
            out = os.path.join(tmp, "out_sin_e0")
            r = correr_cli(["--kg", kg_ruta, "--semilla", "1", "--n", "7",
                            "--e0", os.path.join(tmp, "e0_que_no_existe"), "--out", out])
            assert r.returncode == 0, r.stderr
            s = json.load(open(os.path.join(out, "muestra_obs12.json"), encoding="utf-8"))
            assert s["textos_no_encontrados"] == 7 and s["e0_chunks_sha256"] == {}
        c13()

        @caso("i", "sin remite_a: ni remite_a_restadas ni nota en la regla (salida como antes)")
        def c14():
            out = os.path.join(tmp, "out_sin_remite")
            r = correr_cli(["--kg", kg_ruta, "--semilla", "1", "--n", "7", "--e0", e0_dir, "--out", out])
            assert r.returncode == 0, r.stderr
            s = json.load(open(os.path.join(out, "muestra_obs12.json"), encoding="utf-8"))
            assert "remite_a_restadas" not in s and "remite_a" not in s["regla"], sorted(s)
            assert s["regla"] == mod.REGLA
        c14()

        @caso("i", "remite_a (perfil r2): se resta del universo igual que referencia y se informa")
        def c15():
            kg2 = grafo_sintetico()
            kg2["edges"].append(_arista("Excepcion_E", "remite_a", "Norma_A", _prov("syn", "1.3", "syn::1.3"),
                                        {"alcance": "interna", "destino": "syn::1.1",
                                         "evidencia": "punto 1.1."}))
            kg2["edges"].append(_arista("Norma_B", "remite_a", "TO_Z", _prov("syn", "1.2", "syn::1.2"),
                                        {"alcance": "to_entero", "destino": "zzz",
                                         "evidencia": "TO Z"}))
            ext, conteos = mod.universo(kg2["edges"])
            assert conteos["total_aristas"] == 12 and conteos["remite_a_restadas"] == 2, conteos
            assert conteos["n"] == 7 and "remite_a" not in [e["relation"] for e in ext], conteos
            ruta2 = os.path.join(tmp, "kg_remite.json")
            with open(ruta2, "w", encoding="utf-8") as f:
                json.dump(kg2, f, ensure_ascii=False, indent=1)
            out = os.path.join(tmp, "out_remite")
            r = correr_cli(["--kg", ruta2, "--semilla", "1", "--n", "7", "--e0", e0_dir, "--out", out])
            assert r.returncode == 0, r.stderr
            s = json.load(open(os.path.join(out, "muestra_obs12.json"), encoding="utf-8"))
            assert s["remite_a_restadas"] == 2 and s["n"] == 7 and "remite_a" in s["regla"], s["regla"]
            assert "remite_a restadas" in open(os.path.join(out, "muestra_obs12.md"), encoding="utf-8").read()
        c15()

        @caso("i", "la referencia con rol_fuente referencia_cruzada se resta una sola vez (como referencia)")
        def c16():
            ext, conteos = mod.universo(kg["edges"])
            assert "remite_a_restadas" not in conteos and conteos["referencia_restadas"] == 1, conteos
            assert mod.remisiones.es_remision(kg["edges"][2]), kg["edges"][2]
        c16()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Bloque (ii): r1
# --------------------------------------------------------------------------- #

def bloque_ii():
    print("Bloque (ii): r1 (%s)" % R1_KG_REL)
    out_dir = os.path.join(REPO, R1_OUT_REL)
    ruta_json = os.path.join(out_dir, "muestra_obs12.json")
    ruta_md = os.path.join(out_dir, "muestra_obs12.md")
    tmp = tempfile.mkdtemp(prefix="obs12_selftest_r1_")
    estado = {}
    try:
        @caso("ii", "sha256 de r1 kg.json = %s…" % R1_SHA[:8])
        def d1():
            sha = sha256_archivo(R1_KG)
            print("       sha256 %s  %s" % (sha, R1_KG_REL))
            assert sha == R1_SHA, sha
        d1()

        @caso("ii", "primera corrida (semilla %d, --out %s/): código 0" % (R1_SEMILLA, R1_OUT_REL))
        def d2():
            r = correr_cli(["--kg", R1_KG_REL, "--semilla", str(R1_SEMILLA), "--out", R1_OUT_REL])
            assert r.returncode == 0, r.stderr
            print("       " + r.stdout.strip().replace("\n", "\n       "))
            estado["sha1"] = sha256_archivo(ruta_json)
            shutil.copyfile(ruta_json, os.path.join(tmp, "muestra_obs12_corrida1.json"))
        d2()

        @caso("ii", "segunda corrida: JSON byte-idéntico (cmp sin salida y sha256 iguales)")
        def d3():
            r = correr_cli(["--kg", R1_KG_REL, "--semilla", str(R1_SEMILLA), "--out", R1_OUT_REL])
            assert r.returncode == 0, r.stderr
            estado["sha2"] = sha256_archivo(ruta_json)
            print("       sha256 corrida 1: %s" % estado["sha1"])
            print("       sha256 corrida 2: %s" % estado["sha2"])
            cmp = subprocess.run(["cmp", os.path.join(tmp, "muestra_obs12_corrida1.json"), ruta_json],
                                 capture_output=True, text=True)
            print("       cmp: código %d, salida %r" % (cmp.returncode, cmp.stdout + cmp.stderr))
            assert cmp.returncode == 0 and cmp.stdout == "" and cmp.stderr == ""
            assert estado["sha1"] == estado["sha2"]
        d3()

        s = json.load(open(ruta_json, encoding="utf-8"))

        @caso("ii", "n = %d (total 17772 − referencia 5680 − esqueleto 82) y triplas_duplicadas = 0" % R1_N)
        def d4():
            assert s["n"] == R1_N, s["n"]
            assert (s["total_aristas"], s["referencia_restadas"], s["esqueleto_restadas"],
                    s["solapamiento_referencia_esqueleto"]) == (17772, 5680, 82, 0), s
            assert s["triplas_duplicadas"] == 0 and s["triplas_duplicadas_detalle"] == []
            assert s["kg_sha256"] == R1_SHA and s["semilla"] == R1_SEMILLA and s["k"] == 30
        d4()

        @caso("ii", "30 índices distintos, ascendentes, iguales a la decisión 8 del mandato")
        def d5():
            idx = s["indices"]
            assert len(idx) == 30 and len(set(idx)) == 30 and idx == sorted(idx)
            assert idx == R1_INDICES, idx
            assert [a["indice"] for a in s["aristas"]] == idx
        d5()

        @caso("ii", "ninguna arista de la muestra con relation == 'referencia' ni rol_fuente == 'esqueleto'")
        def d6():
            for a in s["aristas"]:
                assert a["relation"] != "referencia", a["indice"]
                rf = a["rol_fuente"] or (a["provenance"] or {}).get("rol_fuente")
                assert rf != "esqueleto", a["indice"]
        d6()

        @caso("ii", "textos_no_encontrados = 0 y el literal NO ENCONTRADO no aparece en el JSON")
        def d7():
            assert s["textos_no_encontrados"] == 0, s["textos_no_encontrados"]
            txt = open(ruta_json, encoding="utf-8").read()
            assert txt.count("NO ENCONTRADO") == 0
            for a in s["aristas"]:
                assert isinstance(a["texto_ancla"], str) and a["texto_ancla"], a["indice"]
                assert isinstance(a["herencia"], list), a["indice"]
        d7()

        @caso("ii", "distribución de relaciones = decisión 8 (establecida_en 11, aplica_a 8, regula 6, limita 3, exceptua 1, condiciona 1)")
        def d8():
            assert s["relaciones_en_muestra"] == R1_RELACIONES, s["relaciones_en_muestra"]
            assert sum(s["relaciones_en_muestra"].values()) == 30
        d8()

        @caso("ii", "el md existe, lleva sha y semilla en el encabezado y numera 1..30")
        def d9():
            md = open(ruta_md, encoding="utf-8").read()
            assert R1_SHA in md and "Semilla: %d" % R1_SEMILLA in md
            assert "## 1 · índice 115 ·" in md and "## 30 · índice 11167 ·" in md
            assert "## 31 ·" not in md
        d9()

        @caso("ii", "--out contiene exactamente los dos archivos de salida")
        def d10():
            assert sorted(os.listdir(out_dir)) == ["muestra_obs12.json", "muestra_obs12.md"], os.listdir(out_dir)
        d10()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #

def main():
    bloque_i()
    bloque_ii()
    print()
    for b in ("i", "ii"):
        tot = [r for r in RESULTADOS if r[0] == b]
        ok = [r for r in tot if r[2]]
        print("Bloque (%s): %d/%d casos OK" % (b, len(ok), len(tot)))
    fallos = [r for r in RESULTADOS if not r[2]]
    print("TOTAL: %d/%d casos OK" % (len(RESULTADOS) - len(fallos), len(RESULTADOS)))
    if fallos:
        print("FALLOS:")
        for b, nombre, _, det in fallos:
            print("  (%s) %s -> %s" % (b, nombre, det))
        return 1
    print("SELFTEST EN VERDE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
