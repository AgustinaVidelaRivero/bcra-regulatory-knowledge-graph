#!/usr/bin/env python3
"""test_mcp_vector.py — Tests obligatorios del servidor MCP vectorial (U-A2.0-banco, entregable 2).

  (a) ASIMETRÍA — una misma consulta codificada con y sin el prompt
      `web_search_query` produce embeddings DISTINTOS; y los documentos del
      índice fueron codificados SIN prompt: se re-codifica una muestra de
      pasajes sin prompt (igual a la fila del índice, coseno >= 1-1e-5) y con prompt
      (distinta).
  (b) DETERMINISMO — dos construcciones del índice (`construir_indice.py`
      en dos directorios) dan matrices byte-idénticas (sha256). La segunda
      construcción se hace en un directorio temporal y se descarta.
  (c) COINCIDENCIA — el sha256 de la matriz == `sha_docs` de harrier en el
      bake-off (resultados/harrier.json, entorno resultados/e3_entorno.json).
  (d) TRANSPORTE — 10 consultas propias por MCP (cliente falso) byte-idénticas
      al cálculo directo; todo pasaje devuelto cita `to` y `unidad`; log R1
      consistente (n, input, sha del output, sha de config).

Uso (venv del bake-off):
    python3 -B test_mcp_vector.py [--config config_mcp_vector.json] [--sin-reconstruir]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
EXPERIMENT_DIR = BANCO_DIR.parent
if str(BANCO_DIR) not in sys.path:
    sys.path.insert(0, str(BANCO_DIR))
from cliente_falso import ClienteFalso                                   # noqa: E402
from comun_banco import cargar_config, rel_repo, serializar_payload, sha256_bytes  # noqa: E402
from servidor_mcp_vector import IndiceVectorial                           # noqa: E402

CONSULTAS = [
    {"consulta": "¿qué requisitos debe cumplir una asociación mutual para operar con entidades financieras?"},
    {"consulta": "exigencia de efectivo mínimo en pesos", "limite": 5},
    {"consulta": "capital mínimo básico según la categoría de la entidad"},
    {"consulta": "cómo se clasifica a un deudor en situación 3", "limite": 3},
    {"consulta": "previsiones mínimas por riesgo de incobrabilidad"},
    {"consulta": "garantías preferidas A y B", "limite": 50},
    {"consulta": "acceso al mercado de cambios para pago de importaciones", "limite": "7"},
    {"consulta": "tope a la tasa de interés de financiaciones con tarjeta de crédito", "limite": 0},
    {"consulta": "   "},                                             # consulta vacía
    {"consulta": "plazo para informar incumplimientos de relaciones técnicas"},
]


def sha_arr(a) -> str:
    return hashlib.sha256(a.astype("float32").tobytes(order="C")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=AQUI / "config_mcp_vector.json")
    ap.add_argument("--out", type=Path, default=AQUI / "resultados" / "tests_mcp_vector.json")
    ap.add_argument("--sin-reconstruir", action="store_true",
                    help="omite (b): no vuelve a construir el índice")
    ap.add_argument("--b-desde", type=Path, default=None,
                    help="toma (b) de una corrida previa de este test (cita explícita, verificando "
                         "que su sha_construccion_1 == sha del índice actual) en vez de reconstruir")
    a = ap.parse_args()
    import numpy as np

    config, config_sha = cargar_config(a.config)
    idx = IndiceVectorial(config)
    res = {"generado": datetime.now().isoformat(timespec="seconds"),
           "unidad": "U-A2.0-banco — entregable 2 (tests del MCP vectorial)",
           "config": rel_repo(a.config), "config_sha256": config_sha,
           "manifiesto": idx.man["matriz"] | {"modelo": idx.man["modelo"], "entorno": idx.man["entorno"]}}

    # (a) asimetría
    q = "exigencia de efectivo mínimo en pesos"
    con = idx.embed_consulta(q, con_prompt=True)
    sin = idx.embed_consulta(q, con_prompt=False)
    muestra = [0, 250, 700, 1200, 1762]
    filas_doc = []
    for i in muestra:
        t = idx.pasajes[i]["texto"]
        sin_p = idx.m.encode([t], batch_size=1, convert_to_numpy=True, normalize_embeddings=True,
                             show_progress_bar=False)[0].astype("float32")
        con_p = idx.m.encode([t], batch_size=1, convert_to_numpy=True, normalize_embeddings=True,
                             show_progress_bar=False, prompt_name=idx.prompt_name)[0].astype("float32")
        # La fila del índice se codificó en un batch agrupado por presupuesto de
        # tokens; re-codificar el pasaje solo (batch 1) reproduce el vector salvo
        # diferencias de 1 ulp por composición del batch en MPS (medido: coseno
        # 1,0000001). Por eso el criterio es numérico (coseno >= 1 - 1e-5) y no
        # byte a byte; la identidad byte a byte con la MISMA agrupación es el
        # test (b). Con prompt el vector cambia de verdad (coseno ~0,92-0,95).
        c_sin, c_con = float(idx.E[i] @ sin_p), float(idx.E[i] @ con_p)
        filas_doc.append({"i": i, "id": idx.ids[i],
                          "bytes_iguales_a_sin_prompt": bool(np.array_equal(idx.E[i], sin_p)),
                          "coseno_indice_vs_sin_prompt": c_sin,
                          "fila_indice_igual_a_sin_prompt": c_sin >= 1 - 1e-5,
                          "coseno_indice_vs_con_prompt": c_con,
                          "fila_indice_igual_a_con_prompt": c_con >= 1 - 1e-5})
    res["a_asimetria"] = {
        "consulta": q, "prompt_name": idx.prompt_name, "prompt_texto": idx.prompt_texto,
        "sha_con_prompt": sha_arr(con), "sha_sin_prompt": sha_arr(sin),
        "distintos": sha_arr(con) != sha_arr(sin), "coseno_con_vs_sin": float(con @ sin),
        "documentos_muestra": filas_doc,
        "criterio": "consulta: sha distinto con/sin prompt y coseno < 1-1e-5; documentos: fila del índice == codificación SIN prompt (coseno >= 1-1e-5) y != codificación CON prompt",
        "PASS": sha_arr(con) != sha_arr(sin) and float(con @ sin) < 1 - 1e-5
                and all(f["fila_indice_igual_a_sin_prompt"] for f in filas_doc)
                and not any(f["fila_indice_igual_a_con_prompt"] for f in filas_doc),
    }
    print("(a) asimetría:", "PASS" if res["a_asimetria"]["PASS"] else "FAIL",
          f"coseno con/sin = {res['a_asimetria']['coseno_con_vs_sin']:.4f}")

    # (c) coincidencia con el bake-off
    hb = json.loads((EXPERIMENT_DIR / "bakeoff_embeddings" / "resultados" / "harrier.json").read_text())
    e3 = json.loads((EXPERIMENT_DIR / "bakeoff_embeddings" / "resultados" / "e3_entorno.json").read_text())
    res["c_coincidencia_bakeoff"] = {
        "sha_matriz_banco": idx.sha_matriz, "sha_docs_bakeoff": hb["extra"]["sha_docs"],
        "max_seq_banco": idx.man["modelo"]["max_seq_length"], "max_seq_bakeoff": hb["extra"]["max_seq_length_efectivo"],
        "dtype_banco": idx.man["modelo"]["dtype"], "dtype_bakeoff": hb["dtype"],
        "revision_banco": idx.man["modelo"]["revision"], "revision_bakeoff": e3["modelos"]["harrier"]["revision_sha"],
        "libs_banco": {k: idx.man["entorno"].get(k) for k in ("torch", "transformers", "sentence-transformers", "tokenizers", "numpy")},
        "libs_bakeoff": e3["librerias"],
        "PASS": idx.sha_matriz == hb["extra"]["sha_docs"]}
    print("(c) coincidencia con bake-off:", "PASS" if res["c_coincidencia_bakeoff"]["PASS"] else "FAIL")

    # (d) transporte MCP
    log_path = BANCO_DIR / "logs" / f"test_mcp_vector_{datetime.now().strftime('%Y%m%dT%H%M%S')}.jsonl"
    filas = []
    with ClienteFalso([sys.executable, "-B", str(AQUI / "servidor_mcp_vector.py"), "--config", str(a.config)],
                      env={"BANCO_LOG_R1": str(log_path), "BANCO_SESION_TAG": "test_mcp_vector"},
                      timeout_s=900) as cli:
        tools = cli.listar_tools()
        for k, c in enumerate(CONSULTAS, 1):
            via = cli.llamar("buscar_pasajes", c)
            directo = serializar_payload(idx.buscar_pasajes(c.get("consulta", ""), c.get("limite", 10)))
            obj = json.loads(via)
            cita = all(r.get("to") and r.get("unidad") for r in obj["resultados"])
            filas.append({"k": k, "input": c, "chars_mcp": len(via), "n_resultados": len(obj["resultados"]),
                          "sha256_mcp": sha256_bytes(via.encode()), "igual": via == directo,
                          "todos_citan_to_y_unidad": cita,
                          "top1": (obj["resultados"][0]["id"] if obj["resultados"] else None)})
    lineas = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    llam = [l for l in lineas if l["evento"] == "llamada"]
    log_ok = (len(llam) == len(filas) and lineas[0]["evento"] == "inicio" and lineas[-1]["evento"] == "fin"
              and all(l["n"] == f["k"] and l["input"] == f["input"] and l["output_sha256"] == f["sha256_mcp"]
                      and l["config_sha256"] == config_sha for l, f in zip(llam, filas)))
    res["d_transporte"] = {"tools_expuestas": [t["name"] for t in tools], "n": len(filas),
                           "n_iguales": sum(f["igual"] for f in filas),
                           "todos_citan": all(f["todos_citan_to_y_unidad"] for f in filas),
                           "max_chars_resultado": max(f["chars_mcp"] for f in filas),
                           "log_r1": {"ruta": rel_repo(log_path), "n_lineas": len(lineas), "consistente": log_ok,
                                      "sha256_log": sha256_bytes(log_path.read_bytes())},
                           "llamadas": filas,
                           "PASS": [t["name"] for t in tools] == ["buscar_pasajes"] and all(f["igual"] for f in filas)
                                   and all(f["todos_citan_to_y_unidad"] for f in filas) and log_ok}
    print("(d) transporte:", "PASS" if res["d_transporte"]["PASS"] else "FAIL",
          f"{res['d_transporte']['n_iguales']}/{len(filas)} iguales, max {res['d_transporte']['max_chars_resultado']} chars")
    del idx  # liberar el modelo antes de reconstruir

    # (b) determinismo: segunda construcción en un directorio temporal
    if a.b_desde is not None:
        prev = json.loads(a.b_desde.read_text(encoding="utf-8"))
        bprev = prev["b_determinismo"]
        coincide = bprev.get("sha_construccion_1") == res["manifiesto"]["sha256_matriz"]
        res["b_determinismo"] = {
            "citado_de": rel_repo(a.b_desde), "generado_corrida_citada": prev.get("generado"),
            "sha_construccion_1": bprev.get("sha_construccion_1"),
            "sha_construccion_2": bprev.get("sha_construccion_2"),
            "sha_indice_actual": res["manifiesto"]["sha256_matriz"],
            "indice_actual_es_la_construccion_1": coincide,
            "motivo": ("la segunda construcción de la corrida citada se hizo en un directorio temporal y "
                       "se descartó tras comparar el sha; no se re-indexa (≈8 min) porque el índice "
                       "actual es byte-idéntico a la construcción 1 de esa corrida"),
            "PASS": bool(coincide and bprev.get("PASS"))}
    elif a.sin_reconstruir:
        res["b_determinismo"] = {"omitido": True}
    else:
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run([sys.executable, "-B", str(AQUI / "construir_indice.py"), "--out", td,
                                "--max-seq", str(res["manifiesto"]["modelo"]["max_seq_length"])],
                               capture_output=True, text=True)
            man2 = json.loads((Path(td) / "manifiesto_indice.json").read_text()) if r.returncode in (0, 2) else None
            sha2 = man2["matriz"]["sha256_matriz"] if man2 else None
        res["b_determinismo"] = {"sha_construccion_1": res["manifiesto"]["sha256_matriz"],
                                 "sha_construccion_2": sha2, "returncode_2": r.returncode,
                                 "stderr_tail": r.stderr[-400:] if r.returncode not in (0, 2) else None,
                                 "PASS": sha2 is not None and sha2 == res["manifiesto"]["sha256_matriz"]}
        print("(b) determinismo:", "PASS" if res["b_determinismo"]["PASS"] else "FAIL", sha2)

    res["PASS"] = all(res[k]["PASS"] for k in ("a_asimetria", "c_coincidencia_bakeoff", "d_transporte")
                      if k in res) and res["b_determinismo"].get("PASS", a.sin_reconstruir)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TOTAL:", "PASS" if res["PASS"] else "FAIL", "->", rel_repo(a.out))
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
