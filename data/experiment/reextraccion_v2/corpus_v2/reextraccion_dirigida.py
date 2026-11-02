"""
reextraccion_dirigida.py — LAUDO post-corrida: re-extracción dirigida de las
6 unidades rechazadas en E1 durante la corrida del corpus, previa al
re-ensamblado final.

Mandato:
  - cap::3.1.14.1 / cap::4.2.1.2 / cap::4.3.3.1 (max_tokens_hit): mismo
    request canónico con techo de salida 16.384 (no invalida el prefijo).
  - cla::9.2 / ext::4.7.1 / ext::8.5.20.3 (entities_o_relations_invalidos):
    reintento MARCADO — bloque post-breakpoint anexado al mensaje (request
    distinto del fallido; prefijo intacto).
  - Tope duro de esta mini-corrida: USD 0,50.
  - Lo que pasa validación entra por el circuito normal (E3 + ratchet,
    política A+B); lo que falla de nuevo queda en cola con su expediente.

Persistencia: append a los jsonl de la corrida (last-wins ya implementado);
el ledger suma la fase "reextraccion_dirigida". Después de esto corre
cerrar_e2 de cap/cla/ext y el re-ensamblado (ensamblar_corpus.py).

Uso:  .venv/bin/python3 reextraccion_dirigida.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import runner_corpus as rc                    # noqa: E402
from runner_corpus import (                   # noqa: E402
    MODEL_E1, MODEL_E3, P_E1, P_E3, MAX_TOKENS_REINTENTO,
    DB_REINTENTOS_E1, EVAL_DIR, Estado, append_jsonl, cargar_jsonl_last_wins,
    compactar_e1, cerrar_e2,
)
import comun_e1                               # noqa: E402
import prompt_e1                              # noqa: E402
import cliente_e1                             # noqa: E402
import validador_e1                           # noqa: E402
import comun_e3                               # noqa: E402
import cliente_e3                             # noqa: E402
import ratchet_e3                             # noqa: E402

TOPE_USD = 0.50
SALIDA = AQUI / "salida"

CASOS = {
    "cap::3.1.14.1": "max_tokens_16384",
    "cap::4.2.1.2": "max_tokens_16384",
    "cap::4.3.3.1": "max_tokens_16384",
    "cla::9.2": "reintento_marcado",
    "ext::4.7.1": "reintento_marcado",
    "ext::8.5.20.3": "reintento_marcado",
}

MARCA_REINTENTO = (
    "\n\n# REINTENTO DE EXTRACCIÓN DIRIGIDO (post-corrida, intento 1)\n"
    "La salida anterior de este chunk no cumplió el contrato de la "
    "herramienta (entities/relations inválidos a nivel chunk). Re-extraé el "
    "chunk COMPLETO cumpliendo estrictamente el schema de la herramienta: "
    "cada entidad con local_id/type/label/punto válidos, cada relación con "
    "predicado y extremos válidos, y todo `punto` dentro de los admitidos."
)


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(EVAL_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("ANTHROPIC_API_KEY ausente")
        return 1

    estado = Estado(SALIDA)
    assert "reextraccion_dirigida" not in estado.d["fases_cerradas"], \
        "la re-extracción dirigida ya corrió (fase cerrada en el ledger)"

    por_to: dict[str, list[str]] = {}
    for cid in CASOS:
        por_to.setdefault(cid.split("::")[0], []).append(cid)

    cli_e1 = cliente_e1.ClienteE1Real(**P_E1, tope_usd=TOPE_USD,
                                      run_label="reextraccion_dirigida_e1")
    cli_e3 = cliente_e3.ClienteE3Real(**P_E3, tope_usd=TOPE_USD,
                                      run_label="reextraccion_dirigida_e3")
    cli_re = cliente_e1.ClienteE1Real(**P_E1, tope_usd=TOPE_USD,
                                      run_label="reextraccion_dirigida_reint",
                                      db_path=DB_REINTENTOS_E1)

    def gasto() -> float:
        return cli_e1.gasto_usd + cli_e3.gasto_usd + cli_re.gasto_usd

    desenlaces: dict[str, dict] = {}
    t0 = time.time()
    for to, cids in por_to.items():
        chunks = {c["id"]: c for c in
                  comun_e1.cargar_chunks((to,), e0_dir=comun_e1.E0_SALIDA_ENM01)}
        unidades_corpus = {c["unidad"] for c in chunks.values()}
        tdir = SALIDA / to
        registro = ratchet_e3.RegistroE3(tdir)
        for cid in cids:
            if gasto() > TOPE_USD:
                print(f"FRENO por tope antes de {cid}: USD {gasto():.4f}")
                break
            chunk = chunks[cid]
            modo = CASOS[cid]
            if modo == "max_tokens_16384":
                kwargs = prompt_e1.build_request_kwargs(
                    chunk, model=MODEL_E1, max_tokens=MAX_TOKENS_REINTENTO)
            else:
                kwargs = prompt_e1.build_request_kwargs(chunk, model=MODEL_E1)
                kwargs["messages"] = [{
                    "role": "user",
                    "content": kwargs["messages"][0]["content"] + MARCA_REINTENTO}]
            try:
                resp = cli_e1.create(doc=chunk["archivo"], **kwargs)
            except cliente_e1.TopeExcedido as e:
                print(f"FRENO por tope en {cid}: {e}")
                break
            u = resp.usage
            usage = {"input_tokens": getattr(u, "input_tokens", 0) or 0,
                     "output_tokens": getattr(u, "output_tokens", 0) or 0,
                     "cache_write_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
                     "cache_read_tokens": getattr(u, "cache_read_input_tokens", 0) or 0}
            stop = getattr(resp, "stop_reason", None)
            tool_input = next((b.input for b in resp.content
                               if getattr(b, "type", None) == "tool_use"), None)
            err = None
            if tool_input is None:
                err = f"no_tool_use stop_reason={stop}"
            elif stop == "max_tokens":
                err = "max_tokens_hit"
            val = (validador_e1.validar_salida(tool_input, chunk).as_dict()
                   if tool_input is not None else None)
            rechazo_chunk = bool(val and any(
                r["nivel"] == "chunk" for r in val["rechazos"]))

            append_jsonl(tdir / "extracciones_e1.jsonl", {
                "chunk_id": cid, "unidad": chunk["unidad"],
                "tipo_unidad": chunk["tipo"], "titulo": chunk["titulo"],
                "stop_reason": stop,
                "error": err or ("reextraccion_dirigida_invalida"
                                 if rechazo_chunk else None),
                "reextraccion_dirigida": modo,
                "usage": usage, "tool_input_crudo": tool_input,
                "validacion": val})

            if err or val is None or rechazo_chunk:
                motivo = err or "; ".join(r["motivo"] for r in val["rechazos"]
                                          if r["nivel"] == "chunk")
                registro.cola_humana(cid, "cola_humana_reextraccion_dirigida",
                                     {"faltantes": [], "incoherencias":
                                      [f"re-extracción dirigida falló: {motivo}"]})
                append_jsonl(tdir / "finales.jsonl", {
                    "chunk_id": cid, "tipo_unidad": chunk["tipo"],
                    "estado": "cola_humana_reextraccion_dirigida",
                    "n_reintentos": 0, "residuales": [],
                    "validacion_final": None})
                desenlaces[cid] = {"modo": modo, "resultado": "cola_humana",
                                   "motivo": motivo}
                print(f"[{cid}] FALLÓ de nuevo ({motivo}) → cola humana")
                continue

            # circuito normal: E3 + ratchet con política A+B
            exp = ratchet_e3.ciclo_ratchet(
                chunk, val, cliente_verificador=cli_e3, cliente_extractor=cli_re,
                model_e3=MODEL_E3, model_e1=MODEL_E1, registro=registro,
                max_tokens_reintento=MAX_TOKENS_REINTENTO,
                unidades_corpus=unidades_corpus)
            append_jsonl(tdir / "finales.jsonl", {
                "chunk_id": cid, "tipo_unidad": chunk["tipo"],
                "estado": exp["estado"], "n_reintentos": len(exp["reintentos"]),
                "residuales": exp["residuales"],
                "validacion_final": exp["validacion_final"]})
            desenlaces[cid] = {
                "modo": modo, "resultado": exp["estado"],
                "n_reintentos": len(exp["reintentos"]),
                "residuales": len(exp["residuales"]),
                "entidades": len(val["entidades"]),
                "relaciones": len(val["relaciones"])}
            print(f"[{cid}] validación OK ({len(val['entidades'])} ent / "
                  f"{len(val['relaciones'])} rel) → E3: {exp['estado']} "
                  f"| gasto USD {gasto():.4f}")

    resumen = {"casos": desenlaces, "gasto_usd": round(gasto(), 4),
               "tope_usd": TOPE_USD,
               "clientes": {"e1": cli_e1.resumen(), "e3": cli_e3.resumen(),
                            "reintentos": cli_re.resumen()},
               "wall_min": round((time.time() - t0) / 60, 1)}
    (SALIDA / "reextraccion_dirigida.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    cli_e1.close(); cli_e3.close(); cli_re.close()

    estado.d["fases_cerradas"]["reextraccion_dirigida"] = {
        "gasto_usd": round(gasto(), 6), "resumen": {
            "n": len(desenlaces),
            "desenlaces": {k: v["resultado"] for k, v in desenlaces.items()}}}
    estado.persistir()

    # E2 de los TOs afectados (fan-in estricto) — el re-ensamblado global es
    # ensamblar_corpus.py, corrido aparte
    for to in por_to:
        compactar_e1(to, SALIDA)
        cerrar_e2(to, SALIDA)

    print(json.dumps(resumen["casos"], ensure_ascii=False, indent=1))
    print(f"gasto total: USD {resumen['gasto_usd']} (tope {TOPE_USD})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
