#!/usr/bin/env python3
"""construir_denso_puntos.py — U-NAV-DISENO, N5: los embeddings de los documentos del índice por punto (familia 1),
con el modelo denso del bake-off, en el venv del servidor de fragmentos (BANCO_VENV_VECTOR: el .venv del repo no trae
torch ni sentence-transformers).

No reimplementa nada: importa de mcp_vector/construir_indice.py el modelo, su revisión sellada, la carga
(`cargar_modelo`) y la codificación por grupos del bake-off (`codificar`). Los documentos se codifican SIN prompt y las
consultas, en el servidor, CON el prompt `web_search_query` del repo del modelo (la asimetría del bake-off,
docs/decision_modelo_embeddings.md §7-§8). Embeddings L2-normalizados, float32.

Lee `documentos.json` del directorio del índice, verifica su sha256 contra el manifiesto, escribe `embeddings_docs.npy`
y agrega al manifiesto la sección `denso` (modelo, revisión, prompt de consultas con su texto, sha256 de la matriz y
del .npy, sha256 de los documentos y forma). Los tiempos van aparte, en `tiempos_construccion.json`, al lado del
manifiesto y fuera de él (U-NAV-DESDE, corrección A): así el sha256 del manifiesto no depende de la corrida.

Uso: HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $BANCO_VENV_VECTOR/bin/python -B construir_denso_puntos.py <dir del índice>
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VECTOR_DIR = AQUI.parent / "mcp_vector"
if str(VECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(VECTOR_DIR))

import construir_indice as CI  # noqa: E402  (modelo, revisión, carga y codificación del bake-off)
from comun_banco import sha256_file, versiones_entorno  # noqa: E402


def main() -> int:
    import numpy as np
    d = Path(sys.argv[1]).resolve()
    man_p = d / "manifiesto.json"
    man = json.loads(man_p.read_text(encoding="utf-8"))
    sha_docs = sha256_file(d / "documentos.json")
    if sha_docs != man["archivos"]["documentos.json"]:
        raise SystemExit(f"ABORTO: sha256 de documentos.json {sha_docs} != manifiesto {man['archivos']['documentos.json']}")
    docs = json.loads((d / "documentos.json").read_text(encoding="utf-8"))
    t0 = time.time()
    m = CI.cargar_modelo(CI.MAX_SEQ_DEFAULT)
    t_carga = time.time() - t0
    t1 = time.time()
    E, n_grupos, largos = CI.codificar(m, [x["texto"] for x in docs], {})   # SIN prompt (documentos)
    t_idx = time.time() - t1
    E = E.astype("float32")
    np.save(d / "embeddings_docs.npy", E)
    prompts = dict(getattr(m, "prompts", {}) or {})
    man["denso"] = {
        "modelo": CI.MODELO, "revision": CI.REVISION, "dtype": CI.DTYPE, "max_seq_length": CI.MAX_SEQ_DEFAULT,
        "dim": int(E.shape[1]), "prompt_consultas": CI.PROMPT_CONSULTA,
        "prompt_consultas_texto": prompts.get(CI.PROMPT_CONSULTA), "prompt_documentos": None,
        "pooling_y_normalizacion": "del repo del modelo (módulos 1_Pooling / 2_Normalize), normalize_embeddings=True",
        "device": "mps", "agrupacion": {"token_budget": CI.TOKEN_BUDGET, "grupo_max": CI.GRUPO_MAX,
                                        "n_grupos": n_grupos, "max_tokens_documento": max(largos)},
        "shape": list(E.shape), "sha256_matriz": hashlib.sha256(E.tobytes(order="C")).hexdigest(),
        "sha256_archivo_npy": sha256_file(d / "embeddings_docs.npy"), "sha256_documentos": sha_docs,
        "entorno": versiones_entorno(["torch", "transformers", "sentence-transformers", "tokenizers", "numpy"]),
        "construido_con": "banco_mcp/mcp_kg/construir_denso_puntos.py (importa mcp_vector/construir_indice.py)",
    }
    man_p.write_bytes(json.dumps(man, ensure_ascii=False, indent=1).encode("utf-8"))
    tiempos = {"carga_modelo": round(t_carga, 1), "indexacion": round(t_idx, 1)}
    (d / "tiempos_construccion.json").write_bytes(
        json.dumps({"tiempos_s": tiempos}, ensure_ascii=False, indent=1).encode("utf-8"))
    print(json.dumps({k: man["denso"][k] for k in ("shape", "sha256_matriz")} | {"tiempos_s": tiempos}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
