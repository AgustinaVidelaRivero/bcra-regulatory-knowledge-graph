#!/usr/bin/env python3
"""codificador_consultas.py — U-NAV-DISENO, N5: proceso auxiliar de la familia 1 que codifica las consultas con el
modelo denso del bake-off. Corre en el venv del servidor de fragmentos (BANCO_VENV_VECTOR); lo lanza el servidor del
grafo (familias_nav.py), que corre en el .venv del repo, sin torch.

La codificación es la del servidor de fragmentos (mcp_vector/servidor_mcp_vector.py, IndiceVectorial.embed_consulta):
el prompt `web_search_query` del repo del modelo, normalize_embeddings=True, float32. Al arrancar carga el modelo con
la revisión sellada (mcp_vector/construir_indice.cargar_modelo) y verifica que el texto de ese prompt sea el del
manifiesto del índice; si no, sale sin atender nada.

Protocolo, una línea JSON por mensaje:
  al arrancar  -> {"listo": true, "modelo", "revision", "prompt_consultas_texto", "dim"}  (o {"error": ...})
  {"consulta": str}  -> {"v": <base64 de los float32 del vector>}  (o {"error": ...})
Uso: $BANCO_VENV_VECTOR/bin/python -B codificador_consultas.py <manifiesto.json del índice>
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VECTOR_DIR = AQUI.parent / "mcp_vector"
if str(VECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(VECTOR_DIR))


def _enviar(obj) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> int:
    man = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["denso"]
    try:
        import construir_indice as CI
        m = CI.cargar_modelo(man["max_seq_length"])
        prompt = (getattr(m, "prompts", {}) or {}).get(man["prompt_consultas"])
        if (CI.MODELO, CI.REVISION) != (man["modelo"], man["revision"]) or prompt != man["prompt_consultas_texto"]:
            _enviar({"error": "el modelo, su revisión o el texto del prompt de consultas no son los del manifiesto"})
            return 1
    except Exception as e:  # el servidor del grafo informa el error en la llamada
        _enviar({"error": f"{type(e).__name__}: {e}"})
        return 1
    _enviar({"listo": True, "modelo": CI.MODELO, "revision": CI.REVISION, "prompt_consultas_texto": prompt,
             "dim": man["dim"]})
    for linea in sys.stdin:
        try:
            q = json.loads(linea)["consulta"]
            v = m.encode([q], batch_size=1, convert_to_numpy=True, normalize_embeddings=True,
                         show_progress_bar=False, prompt_name=man["prompt_consultas"])[0].astype("float32")
            _enviar({"v": base64.b64encode(v.tobytes(order="C")).decode("ascii")})
        except Exception as e:
            _enviar({"error": f"{type(e).__name__}: {e}"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
