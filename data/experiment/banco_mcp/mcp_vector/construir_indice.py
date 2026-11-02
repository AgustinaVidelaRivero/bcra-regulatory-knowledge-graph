#!/usr/bin/env python3
"""construir_indice.py — Índices locales y determinísticos del brazo de fragmentos
(U-A2.0-banco, pieza ii; A2.1, tramo 1). Denso con `microsoft/harrier-oss-v1-0.6b`
según el laudo `docs/decision_modelo_embeddings.md` §7-§8; BM25 con el analizador
`spanish` de Lucene (bm25_fragmentos.py), sin modelo.

Qué hace, en orden:
  1. Lee un MANIFIESTO DE E0 (`manifiestos_e0/*.json`: directorio, TOs, sha256
     de cada `chunks_<to>.json`, cantidad de pasajes y sha256 del corpus
     esperado) y reconstruye los pasajes en composición PROPIO + HERENCIA, con
     la expresión exacta de `bakeoff_embeddings/code/construir_gold_y_corpus.py`
     ("\\n".join([herencia...] + [propio]), orden canónico por id); verifica
     cada uno contra `sha256_completo` del chunk, cada insumo contra su sha del
     manifiesto y el corpus entero contra `sha256_corpus_esperado`. Con la E0
     vieja (`e0_enm01.json`, `verificacion_bakeoff`), además, contra
     `sha256_corpus` e insumos de `resultados/meta_gold_corpus.json` del
     bake-off. (Ese script no se importa porque su código corre a nivel de
     módulo y escribe archivos en su propio directorio —sellado—; la expresión
     de tres líneas se replica y se verifica por hash, que es una prueba más
     fuerte que el import.)
  2. `--afinidad denso` (default): codifica los pasajes SIN prompt (asimetría
     declarada por los autores del modelo), `float32`, pooling y normalización
     del propio repo del modelo (SentenceTransformer carga
     1_Pooling/2_Normalize de la revisión pinneada), con la MISMA agrupación
     por presupuesto de tokens del bake-off (`e3_medicion.py`:
     TOKEN_BUDGET=8448, GRUPO_MAX=32, batch=len(grupo), device MPS), para que
     la matriz sea byte-idéntica a la del bake-off con la E0 vieja.
     `--afinidad bm25`: construye el índice BM25 de los mismos pasajes; no
     importa torch ni sentence-transformers.
  3. Persiste en --out `pasajes.json` (id, to, archivo, unidad, titulo, tipo,
     paginas, texto, chars, sha256_completo), la matriz
     `embeddings_docs.npy` (float32, C-order) o el índice `indice_bm25.json`
     (bytes canónicos de bm25_fragmentos.serializar), y
     `manifiesto_indice.json` con todos los sha y el manifiesto de E0 usado.

Parámetros sellados del denso (no son flags: cambiarlos es otra config):
  revisión f9b9dc8d367d443f2479d27aa5d8d2850c0774ee · dtype float32 ·
  max_seq_length 32768 · documentos sin prompt · consultas con prompt
  `web_search_query` (lo aplica el servidor, no este script).

Con la E0 vieja, el sha esperado de la matriz (`sha_docs` del bake-off para
harrier) es 12d284d5bce0d1d58f1e4437c47f2177b3145813586069ca72f9103309b28b65.
Con otra E0, el sha esperado es el del manifiesto (null si la matriz es nueva:
se registra y no se compara).

Uso (venv del bake-off / requirements_vector.txt):
    python3 -B construir_indice.py [--out indice] [--max-seq 32768]
    python3 -B construir_indice.py --manifiesto manifiestos_e0/e0_tanda0_r2b_desarrollo.json \\
        --afinidad denso|bm25 --out indice/<dir>
--out es obligatorio salvo con la E0 vieja y el denso (default `indice`, el índice de
U-A2.0-banco).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
EXPERIMENT_DIR = BANCO_DIR.parent
REPO_DIR = EXPERIMENT_DIR.parents[1]
if str(BANCO_DIR) not in sys.path:
    sys.path.insert(0, str(BANCO_DIR))
from comun_banco import rel_repo, sha256_bytes, sha256_file, versiones_entorno  # noqa: E402

MANIFIESTO_DEFAULT = AQUI / "manifiestos_e0" / "e0_enm01.json"
META_BAKEOFF = EXPERIMENT_DIR / "bakeoff_embeddings" / "resultados" / "meta_gold_corpus.json"
HARRIER_BAKEOFF = EXPERIMENT_DIR / "bakeoff_embeddings" / "resultados" / "harrier.json"

MODELO = "microsoft/harrier-oss-v1-0.6b"
REVISION = "f9b9dc8d367d443f2479d27aa5d8d2850c0774ee"
DTYPE = "float32"
MAX_SEQ_DEFAULT = 32768
PROMPT_CONSULTA = "web_search_query"     # SOLO consultas (servidor); documentos: ninguno
TOKEN_BUDGET = 8448                      # e3_medicion.py (bake-off), igualado
GRUPO_MAX = 32


def sha_arr(a) -> str:
    """Misma expresión que `e3_medicion.sha_arr`."""
    return hashlib.sha256(a.astype("float32").tobytes(order="C")).hexdigest()


def cargar_manifiesto(p: Path) -> tuple[dict, dict]:
    man = json.loads(p.read_text(encoding="utf-8"))
    return man, {"id": man["manifiesto_e0"], "ruta": rel_repo(p), "sha256": sha256_file(p),
                 "dir": man["dir"], "n_pasajes": man["n_pasajes"]}


def construir_pasajes(man: dict) -> tuple[list[dict], dict]:
    e0 = REPO_DIR / man["dir"]
    chunks = []
    insumos = {}
    for to in man["tos"]:
        p = e0 / f"chunks_{to}.json"
        insumos[f"chunks_{to}.json"] = sha256_file(p)
        if insumos[p.name] != man["archivos"][p.name]:
            raise SystemExit(f"ABORTO: {p.name} {insumos[p.name]} != manifiesto {man['archivos'][p.name]}")
        chunks.extend(json.loads(p.read_text(encoding="utf-8")))
    chunks.sort(key=lambda c: c["id"])          # orden canónico (bake-off)
    pasajes, pasajes_bakeoff = [], []
    for c in chunks:
        txt = "\n".join([h["texto"] for h in c["herencia"]] + [c["texto"]])
        if sha256_bytes(txt.encode()) != c["sha256_completo"]:
            raise SystemExit(f"ABORTO: composición propio+herencia no reproduce sha256_completo en {c['id']}")
        # forma exacta del bake-off (para verificar sha256_corpus)
        pasajes_bakeoff.append({"id": c["id"], "to": c["to"], "unidad": c["unidad"],
                                "tipo": c["tipo"], "texto": txt, "chars": len(txt)})
        pasajes.append({"id": c["id"], "to": c["to"], "archivo": c["archivo"],
                        "unidad": c["unidad"], "titulo": c["titulo"], "tipo": c["tipo"],
                        "paginas": c["paginas"], "texto": txt, "chars": len(txt),
                        "sha256_completo": c["sha256_completo"]})
    if len(pasajes) != man["n_pasajes"]:
        raise SystemExit(f"ABORTO: {len(pasajes)} pasajes != {man['n_pasajes']}")
    if len({p["id"] for p in pasajes}) != len(pasajes):
        raise SystemExit("ABORTO: ids de pasaje repetidos")
    sha_corpus = hashlib.sha256(json.dumps(pasajes_bakeoff, ensure_ascii=False,
                                           sort_keys=True).encode()).hexdigest()
    if sha_corpus != man["sha256_corpus_esperado"]:
        raise SystemExit(f"ABORTO: sha256_corpus {sha_corpus} != manifiesto {man['sha256_corpus_esperado']}")
    ver = {"insumos_e0": insumos, "sha256_corpus": sha_corpus,
           "composicion": "\"\\n\".join([herencia...] + [propio]) = E0 'completo'",
           "verificado_contra_sha256_completo": True}
    if man.get("verificacion_bakeoff"):
        meta_bk = json.loads(META_BAKEOFF.read_text(encoding="utf-8"))
        if sha_corpus != meta_bk["sha256_corpus"]:
            raise SystemExit(f"ABORTO: sha256_corpus {sha_corpus} != bake-off {meta_bk['sha256_corpus']}")
        for k, v in meta_bk["insumos"].items():
            if k.startswith("chunks_") and insumos[k] != v:
                raise SystemExit(f"ABORTO: {k} cambió respecto del bake-off")
        ver["sha256_corpus_bakeoff"] = meta_bk["sha256_corpus"]
    return pasajes, ver


def cargar_modelo(max_seq: int):
    import torch
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODELO, revision=REVISION, device="mps", trust_remote_code=False,
                            model_kwargs={"dtype": torch.float32})
    m.max_seq_length = max_seq
    return m


def grupos_por_presupuesto(tok, textos: list[str]) -> list[list[int]]:
    """Réplica exacta de `grupos` en e3_medicion.py (bake-off)."""
    largos = [len(tok(t, add_special_tokens=True)["input_ids"]) for t in textos]
    orden = sorted(range(len(textos)), key=lambda i: (largos[i], i))
    gs, cur, curmax = [], [], 0
    for i in orden:
        nm = max(curmax, largos[i])
        if cur and (len(cur) + 1) * nm > TOKEN_BUDGET or len(cur) >= GRUPO_MAX:
            gs.append(cur); cur, curmax = [i], largos[i]
        else:
            cur.append(i); curmax = nm
    if cur:
        gs.append(cur)
    return gs, largos


def codificar(m, textos: list[str], kw: dict):
    """Réplica de `encode` en e3_medicion.py: batch = grupo, normalize, float32."""
    import numpy as np
    import torch
    gs, largos = grupos_por_presupuesto(m.tokenizer, textos)
    partes = {}
    for g in gs:
        v = m.encode([textos[i] for i in g], batch_size=len(g), convert_to_numpy=True,
                     normalize_embeddings=True, show_progress_bar=False, **kw)
        for j, i in enumerate(g):
            partes[i] = v[j]
        torch.mps.empty_cache()
    return np.stack([partes[i] for i in range(len(textos))]).astype("float32"), len(gs), largos


def construir_bm25(pasajes: list[dict], ver: dict, man_e0: dict, out: Path) -> int:
    import unicodedata

    import bm25_fragmentos as BM
    t0 = time.perf_counter()
    indice = BM.construir(pasajes)
    crudo = BM.serializar(indice)
    t_idx = time.perf_counter() - t0
    out.mkdir(parents=True, exist_ok=True)
    (out / "pasajes.json").write_text(json.dumps(pasajes, ensure_ascii=False), encoding="utf-8")
    (out / "indice_bm25.json").write_bytes(crudo)
    man = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "unidad": "A2.1, tramo 1 — índice BM25 del servidor de fragmentos",
        "afinidad": "bm25",
        "manifiesto_e0": man_e0,
        "bm25": {"analizador": BM.ANALIZADOR, "lucene_version": BM.LUCENE_VERSION, "k1": BM.K1, "b": BM.B,
                 "sha256_stop": BM.SHA256_STOP, "n_stop": len(BM.STOP), "max_token": BM.MAX_TOKEN,
                 "n_docs": indice["n_docs"], "doc_count": indice["doc_count"],
                 "sum_total_term_freq": indice["sum_total_term_freq"], "vocabulario": len(indice["df"]),
                 "sha256_indice": sha256_bytes(crudo), "sha256_modulo_bm25": sha256_file(AQUI / "bm25_fragmentos.py"),
                 "bytes": len(crudo)},
        "entorno": versiones_entorno([]) | {"unicodedata": unicodedata.unidata_version},
        "corpus": ver | {"n_pasajes": len(pasajes), "sha256_pasajes_json": sha256_file(out / "pasajes.json")},
        "tiempos_s": {"indexacion": round(t_idx, 1)},
    }
    (out / "manifiesto_indice.json").write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
    print(f"índice BM25 sha={man['bm25']['sha256_indice']} | {indice['n_docs']} docs, "
          f"vocabulario {len(indice['df'])} | {t_idx:.1f}s")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path, default=MANIFIESTO_DEFAULT)
    ap.add_argument("--afinidad", choices=["denso", "bm25"], default="denso")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--max-seq", type=int, default=MAX_SEQ_DEFAULT)
    a = ap.parse_args()
    es_default = a.manifiesto.resolve() == MANIFIESTO_DEFAULT.resolve() and a.afinidad == "denso"
    if a.out is None:
        if not es_default:
            raise SystemExit("--out es obligatorio salvo con la E0 vieja y el denso")
        a.out = AQUI / "indice"
    man, man_e0 = cargar_manifiesto(a.manifiesto)

    t0 = time.perf_counter()
    pasajes, ver = construir_pasajes(man)
    print(f"pasajes: {len(pasajes)} | sha256_corpus OK ({ver['sha256_corpus'][:12]}…) | "
          f"{time.perf_counter()-t0:.1f}s")
    if a.afinidad == "bm25":
        return construir_bm25(pasajes, ver, man_e0, a.out)

    import numpy as np
    t0 = time.perf_counter()
    m = cargar_modelo(a.max_seq)
    t_carga = time.perf_counter() - t0
    t0 = time.perf_counter()
    E, n_grupos, largos = codificar(m, [p["texto"] for p in pasajes], {})   # SIN prompt
    t_idx = time.perf_counter() - t0
    sha_docs = sha_arr(E)
    esperado = man["sha256_matriz_esperado"]
    bakeoff = (json.loads(HARRIER_BAKEOFF.read_text(encoding="utf-8"))["extra"]["sha_docs"]
               if man.get("verificacion_bakeoff") else None)
    if bakeoff is not None and esperado != bakeoff:
        raise SystemExit(f"ABORTO: el manifiesto espera {esperado} y el bake-off {bakeoff}")
    estado = "SIN ESPERADO (matriz nueva)" if esperado is None else ("COINCIDE" if sha_docs == esperado else "DIFIERE")
    print(f"matriz {E.shape} sha={sha_docs} | esperado {esperado} | {estado} | {t_idx:.1f}s, {n_grupos} grupos")

    a.out.mkdir(parents=True, exist_ok=True)
    np.save(a.out / "embeddings_docs.npy", E)
    (a.out / "pasajes.json").write_text(json.dumps(pasajes, ensure_ascii=False), encoding="utf-8")
    prompts = dict(getattr(m, "prompts", {}) or {})
    man_idx = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "unidad": ("U-A2.0-banco — entregable 2 (índice vectorial)" if es_default
                   else "A2.1, tramo 1 — índice denso del servidor de fragmentos"),
        "afinidad": "denso",
        "manifiesto_e0": man_e0,
        "modelo": {"repo": MODELO, "revision": REVISION, "dtype": DTYPE,
                   "max_seq_length": m.max_seq_length, "dim": int(E.shape[1]),
                   "prompt_consultas": PROMPT_CONSULTA,
                   "prompt_consultas_texto": prompts.get(PROMPT_CONSULTA),
                   "prompt_documentos": None, "pooling_y_normalizacion": "del repo del modelo (módulos 1_Pooling / 2_Normalize), normalize_embeddings=True",
                   "device": "mps", "trust_remote_code": False},
        "agrupacion": {"token_budget": TOKEN_BUDGET, "grupo_max": GRUPO_MAX, "n_grupos": n_grupos,
                       "max_tokens_pasaje": max(largos), "n_truncados": sum(1 for L in largos if L > m.max_seq_length)},
        "entorno": versiones_entorno(["torch", "transformers", "sentence-transformers", "tokenizers", "numpy"]),
        "corpus": ver | {"n_pasajes": len(pasajes), "sha256_pasajes_json": sha256_file(a.out / "pasajes.json")},
        "matriz": {"shape": list(E.shape), "sha256_matriz": sha_docs,
                   "sha256_archivo_npy": sha256_file(a.out / "embeddings_docs.npy"),
                   "sha256_matriz_esperado": esperado,
                   "coincide_con_esperado": None if esperado is None else sha_docs == esperado,
                   "sha_docs_bakeoff": bakeoff,
                   "coincide_con_bakeoff": None if bakeoff is None else sha_docs == bakeoff},
        "tiempos_s": {"carga_modelo": round(t_carga, 1), "indexacion": round(t_idx, 1)},
    }
    (a.out / "manifiesto_indice.json").write_text(json.dumps(man_idx, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
    print(json.dumps({k: man_idx[k] for k in ("modelo", "agrupacion", "entorno", "matriz")}, ensure_ascii=False, indent=1))
    return 0 if esperado is None or sha_docs == esperado else 2


if __name__ == "__main__":
    raise SystemExit(main())
