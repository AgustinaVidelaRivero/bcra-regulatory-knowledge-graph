"""R0, fase 1 (USD 0, sin API): el reparto de las 20 unidades de E3-01 y la pregunta (a), la clave de E3.

Para cada unidad de la lista sellada de O3 (sha256 cc6b0cd6…), con el código del pipeline (runner_corpus y lo que
importa, con el manifiesto de la tanda 0 r2b y el camino del perfil r2 que el runner activa en main()):
  - su TO, su registro de E1 (último de extracciones_e1.jsonl, igual al compactado), su estado en la tanda 0;
  - la clave de E1 del intento 0, buscada en la base de E1 del pipeline, y su respuesta contra el crudo guardado;
  - la verificación de O3 (respuestas_e3_o3.jsonl) evaluada con ratchet_e3.evaluar_veredicto y la decisión que toma
    ratchet_e3.ciclo_ratchet con ese veredicto (aceptar, reintentar o cola), contra la evaluación guardada de O3;
  - (a) la clave de E3 que arma el runner (cliente_e3.namespace_e3 + prompt_e3.build_request_kwargs + llm_cache), contra
    la fila de la base de O3 que tiene ese mensaje: clave, namespace y pedido canónico byte a byte;
  - para las que reintentan, la clave del reintento de E1 que arma el ratchet con ese veredicto (y si está en la base
    de reintentos del pipeline) y el sha256 de su mensaje.
Solo lee: las bases se abren en modo inmutable. Escribe un JSON en --salida (fuera de la copia).

Uso: PYTHONDONTWRITEBYTECODE=1 <python> -B r0_f1_reparto_y_claves.py --salida <archivo.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REX = AQUI.parents[1]                                  # reextraccion_v2/
REPO = REX.parents[2]
sys.path.insert(0, str(REX / "corpus_v2"))
import runner_corpus as RC                             # noqa: E402  (agrega e1, e3, e2, e0 y reextraccion_v2 al sys.path)
import manifiesto_corpus                               # noqa: E402
import comun_e3                                        # noqa: E402
import cliente_e1                                      # noqa: E402
import cliente_e3                                      # noqa: E402
import prompt_e3                                       # noqa: E402
import ratchet_e3                                      # noqa: E402
import llm_cache as lc                                 # noqa: E402

LISTA = REPO / "data/experiment/e3_listas/o3/lista_unidades_afectadas_tanda0.json"
LISTA_SHA256 = "cc6b0cd6c56831c486d60bf7da64712cea391a1eb2948eef822448567df9bab6"
O3A = REPO / "data/experiment/e3_listas/o3/a"
DB_O3 = REPO / "data/experiment/e3_listas/cache/e3_listas_o3.db"
MANIFIESTO = REX / "manifiestos/tanda0_10tos_r2b.json"
SALIDA_R2B = REX / "corpus_tanda0/salida_r2b"
# enmienda 7, §1.2 (firma en 4a33ce92)
ENM7 = {"aceptar": {"ext::2.6.1.1", "ext::3.5.6.1", "ext::3.6.1.1", "ext::3.6.4.2", "ext::3.13.1.10"},  # las 5 de la cola
        "reintentar": {"ext::3.6.4.1", "ext::3.16.2.1", "ext::3.18.1.1"},
        "cola": {"docvig::3.3.2"}}


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def abrir_ro(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{urllib.parse.quote(str(db.resolve()))}?mode=ro&immutable=1", uri=True)


def decision(ev: dict) -> str:
    """La rama de ratchet_e3.ciclo_ratchet después de la verificación inicial."""
    if ev["es_completo_ok"]:
        return "aceptar:completo_ok_directo"
    if ev["aceptable"]:
        return "aceptar:aceptado_con_residuales"
    if not ev["bloqueantes_utilizables"]:
        return "cola:cola_humana_veredicto_inutilizable"
    return "reintentar"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    if hashlib.sha256(LISTA.read_bytes()).hexdigest() != LISTA_SHA256:
        raise SystemExit("la lista sellada no tiene el sha256 cc6b0cd6…")
    RC.configurar(manifiesto_corpus.cargar(MANIFIESTO))
    RC.PERFIL_R2 = RC.perfil_forma_r2(RC.PERFIL)        # como main() del runner, sin --perfil-r2
    perfil = RC.PERFIL
    unidades = [u["chunk_id"] for u in json.loads(LISTA.read_text(encoding="utf-8"))["unidades"]]
    assert len(unidades) == len(set(unidades)) == 20

    ns_e1 = cliente_e1.namespace_e1(prefijo_hash=perfil.prefijo_hash_para_namespace)
    ns_e3 = cliente_e3.namespace_e3()
    resp_o3 = {r["chunk_id"]: r for r in jl(O3A / "respuestas_e3_o3.jsonl")}
    ev_o3 = {r["chunk_id"]: r["evaluacion"] for r in jl(O3A / "evaluacion_e3_o3.jsonl")}
    ctl_o2 = {r["chunk_id"]: r for r in json.loads((O3A / "control_mensajes_o2.json").read_text(encoding="utf-8"))}

    # la base de O3: cada fila por el sha256 de su mensaje
    con_o3 = abrir_ro(DB_O3)
    filas_o3 = {}
    for key, ns, model, req, raw in con_o3.execute("select key, namespace, model, request_json, raw_json from cache"):
        msg = json.loads(req)["messages"][0]["content"]
        filas_o3[sha(msg)] = {"key": key, "namespace": ns, "model": model, "request_json": req,
                              "clave_recomputada_de_la_fila": lc.compute_key(ns, req), "raw": json.loads(raw)}
    con_o3.close()
    con_e1 = abrir_ro(cliente_e1.DB_PATH)
    con_e1r = abrir_ro(RC.DB_REINTENTOS_E1)
    con_e3 = abrir_ro(cliente_e3.DB_PATH)

    filas, cache_to = [], {}
    for cid in unidades:
        to = cid.split("::")[0]
        if to not in cache_to:
            tdir = SALIDA_R2B / to
            chunks = RC.chunks_con_partes(RC.chunks_sin_ids_repetidos(
                comun_e3.cargar_chunks((to,), e0_dir=RC.E0_DIR), to), tdir)
            cache_to[to] = {"chunks": {c["id"]: c for c in chunks}, "unidades": {c["unidad"] for c in chunks},
                            "e1": RC.cargar_jsonl_last_wins(tdir / "extracciones_e1.jsonl"),
                            "compact": comun_e3.cargar_extracciones(tdir / "extracciones_e1_compact.jsonl"),
                            "finales": RC.cargar_jsonl_last_wins(tdir / "finales.jsonl"),
                            "particiones": bool(RC.partes_por_corte(tdir))}
        T = cache_to[to]
        c, reg = T["chunks"][cid], T["e1"][cid]
        val = reg["validacion"]
        fila = {"chunk_id": cid, "to": to, "es_item": bool(comun_e3.indices_bloque_lista(c)),
                "forma_r2": val.get("forma_salida") == "r2",
                "e1_registro_igual_al_compactado": T["compact"].get(cid) == reg,
                "e1_aceptado_para_e3": comun_e3.chunk_aceptado(reg),
                "e1_marcas": sorted(k for k in ("reintento_corte", "reintento_forma", "reparacion_forma", "escalon_3",
                                                "particion_por_corte") if k in reg),
                "tanda0": {k: T["finales"][cid].get(k) for k in ("estado", "n_reintentos")}}
        # E1 del intento 0 en la caché del pipeline
        kw1 = perfil.build_request_kwargs(c, model=RC.MODEL_E1)
        k1 = lc.compute_key(ns_e1, lc.canonical_request(kw1))
        r1 = con_e1.execute("select model, raw_json from cache where key = ?", (k1,)).fetchone()
        ti = None
        if r1 is not None:
            ti = next((b.get("input") for b in json.loads(r1[1]).get("content") or []
                       if isinstance(b, dict) and b.get("type") == "tool_use"), None)
        fila["e1_intento0"] = {"clave": k1, "en_la_base": r1 is not None, "modelo_respuesta": r1[0] if r1 else None,
                               "respuesta_igual_al_crudo_guardado": ti == reg.get("tool_input_crudo")}
        # (a) la clave de E3 del runner y la fila de O3
        kw3 = prompt_e3.build_request_kwargs(c, val, model=RC.MODEL_E3)
        msg3 = kw3["messages"][0]["content"]
        can3 = lc.canonical_request(kw3)
        k3 = lc.compute_key(ns_e3, can3)
        f3 = filas_o3.get(sha(msg3))
        fila["e3"] = {"sha_mensaje_runner": sha(msg3),
                      "sha_mensaje_igual_al_control_de_o3": sha(msg3) == ctl_o2[cid]["sha_msg"],
                      "clave_runner": k3, "fila_de_o3_con_ese_mensaje": f3 is not None,
                      "clave_o3": f3["key"] if f3 else None,
                      "clave_igual": bool(f3) and f3["key"] == k3,
                      "namespace_igual": bool(f3) and f3["namespace"] == ns_e3,
                      "pedido_canonico_igual_byte_a_byte": bool(f3) and f3["request_json"] == can3,
                      "clave_de_la_fila_recomputada_igual": bool(f3) and f3["clave_recomputada_de_la_fila"] == f3["key"],
                      "modelo_respuesta_o3": f3["model"] if f3 else None,
                      "respuesta_de_la_base_igual_a_respuestas_e3_o3": bool(f3) and next(
                          (b.get("input") for b in f3["raw"]["content"] if b.get("type") == "tool_use"), None)
                      == resp_o3[cid]["tool_input"],
                      "clave_runner_en_la_base_del_pipeline": con_e3.execute(
                          "select 1 from cache where key = ?", (k3,)).fetchone() is not None}
        # el veredicto de O3 y la decisión del ratchet
        ev = ratchet_e3.evaluar_veredicto(resp_o3[cid]["tool_input"], c, T["unidades"], val)
        d = decision(ev)
        fila["o3"] = {"veredicto": (resp_o3[cid]["tool_input"] or {}).get("veredicto"),
                      "faltantes": len(ev["faltantes"]), "bloqueantes": len(ev["faltantes_bloqueantes"]),
                      "bloqueantes_utilizables": len(ev["bloqueantes_utilizables"]),
                      "residuales": len(ev["residuales"]), "incoherencias": ev["incoherencias"],
                      "evaluacion_igual_a_la_guardada_de_o3": json.dumps(ev, sort_keys=True, ensure_ascii=False)
                      == json.dumps(ev_o3[cid], sort_keys=True, ensure_ascii=False),
                      "decision": d}
        if d == "reintentar":
            kwr = ratchet_e3.build_reextraccion_kwargs(
                c, ev["bloqueantes_utilizables"], model=RC.MODEL_E1, intento=1,
                max_tokens_reintento=RC.techo_reintento_ratchet(reg), perfil=perfil)
            kr = lc.compute_key(ns_e1, lc.canonical_request(kwr))
            fila["reintento_e1"] = {"max_tokens": kwr["max_tokens"], "temperature": kwr.get("temperature"),
                                    "sha_mensaje": sha(kwr["messages"][0]["content"]), "clave": kr,
                                    "en_la_base_de_reintentos": con_e1r.execute(
                                        "select 1 from cache where key = ?", (kr,)).fetchone() is not None,
                                    "feedback": [{k: f.get(k) for k in ("tipo", "severidad", "cita_textual_del_fuente")}
                                                 for f in ev["bloqueantes_utilizables"]]}
        filas.append(fila)
    for con in (con_e1, con_e1r, con_e3):
        con.close()

    rama = Counter(f["o3"]["decision"].split(":")[0] for f in filas)
    por = {r: sorted(f["chunk_id"] for f in filas if f["o3"]["decision"].startswith(r))
           for r in ("aceptar", "reintentar", "cola")}
    t0 = Counter((f["tanda0"]["estado"], bool(f["tanda0"]["n_reintentos"])) for f in filas)
    acept = [f for f in filas if f["o3"]["decision"].startswith("aceptar")]
    res = {
        "codigo": {"namespace_e1": ns_e1, "namespace_e3": ns_e3, "prefijo_e3": prompt_e3.PREFIJO_HASH,
                   "perfil": perfil.nombre, "perfil_r2": RC.PERFIL_R2, "model_e1": RC.MODEL_E1,
                   "model_e3": RC.MODEL_E3, "e0": str(RC.E0_DIR.relative_to(REPO)),
                   "particiones_por_corte_en_ext_o_docvig": any(T["particiones"] for T in cache_to.values())},
        "reparto": {"por_rama": dict(rama), "unidades": por,
                    "aceptadas_por_estado": dict(Counter(f["o3"]["decision"] for f in acept)),
                    "aceptadas_que_reintentaron_en_tanda0_y_su_final_era_el_reintento": sum(
                        1 for f in acept if f["tanda0"]["estado"] == "aceptado_tras_reintento"),
                    "aceptadas_que_estaban_en_la_cola": sorted(f["chunk_id"] for f in acept
                                                               if f["tanda0"]["estado"].startswith("cola_humana")),
                    "estado_tanda0": {f"{e}|reintento={r}": n for (e, r), n in sorted(t0.items())},
                    "igual_a_enmienda7_1_2": (rama == Counter({"aceptar": 16, "reintentar": 3, "cola": 1})
                                              and set(por["reintentar"]) == ENM7["reintentar"]
                                              and set(por["cola"]) == ENM7["cola"]
                                              and ENM7["aceptar"] <= set(por["aceptar"]))},
        "clave_e3": {k: sum(1 for f in filas if f["e3"][k]) for k in (
            "sha_mensaje_igual_al_control_de_o3", "fila_de_o3_con_ese_mensaje", "clave_igual", "namespace_igual",
            "pedido_canonico_igual_byte_a_byte", "clave_de_la_fila_recomputada_igual",
            "respuesta_de_la_base_igual_a_respuestas_e3_o3", "clave_runner_en_la_base_del_pipeline")},
        "filas_en_la_base_de_o3": len(filas_o3),
        "modelos_en_la_base_de_o3": dict(Counter(f["model"] for f in filas_o3.values())),
        "e1_intento0": {k: sum(1 for f in filas if f["e1_intento0"][k]) for k in (
            "en_la_base", "respuesta_igual_al_crudo_guardado")} | {
            "modelos": dict(Counter(f["e1_intento0"]["modelo_respuesta"] for f in filas)),
            "registro_igual_al_compactado": sum(1 for f in filas if f["e1_registro_igual_al_compactado"]),
            "con_marcas": {f["chunk_id"]: f["e1_marcas"] for f in filas if f["e1_marcas"]}},
        "evaluacion_o3_reproducida": sum(1 for f in filas if f["o3"]["evaluacion_igual_a_la_guardada_de_o3"]),
        "unidades": filas,
    }
    a.salida.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("reparto", "clave_e3", "filas_en_la_base_de_o3", "modelos_en_la_base_de_o3",
                                          "e1_intento0", "evaluacion_o3_reproducida")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
