"""
run_posthoc.py — Runner de la corrida NUEVA instrumentada (Fase 2.3+).

Corrida independiente de instrumentación (decisión 1 firmada): NO re-selecciona el
ganador (eso lo fija el dataset congelado), su propósito es generar trazas RICAS para
análisis cualitativo. Mismo eval_set_v1 (23 preguntas) y mismo juez v2.1.1 para que
sea comparable con lo congelado.

NO toca run_frozen.py / harness.py / judge.py (congelados). Todo vive acá y en
llm_cache.py. Reusa GraphAgent y judge.judge_trace tal cual.

Cómo prende thinking sin tocar el harness congelado
---------------------------------------------------
GraphAgent.ask y judge._call HARDCODEAN los kwargs del create (sin `thinking`,
temperature=0/JUDGE_TEMPERATURE, max_tokens fijo). Para no modificarlos, se intercala
un ParamOverrideClient POR ENCIMA de la caché que reescribe los kwargs en vuelo:

    GraphAgent ─▶ ParamOverrideClient ─▶ CachingClient ─▶ (cliente real con retries)

El override ocurre ANTES de la caché, así la key refleja el request REAL (con thinking).
El namespace además lleva think=0/1 (cinturón y tiradores: nunca se cruzan cachés ON/OFF).

  - thinking OFF (control comparable al frozen): override = identidad. El request es
    byte-idéntico al del frozen; la única diferencia es la instrumentación.
  - thinking ON (exploración del razonamiento): se agrega thinking={enabled,budget},
    se QUITA temperature (la API de thinking clásico no admite temperature custom en
    Haiku 4.5 — A CONFIRMAR con --preflight, ver abajo) y se sube max_tokens a
    base+budget (garantiza budget < max_tokens y conserva el espacio de la respuesta).

Modos
-----
  --selftest         Prueba OFFLINE del cableado + determinismo de replay multi-turno
                     con un cliente FALSO (sin API, sin gastar). Corre el loop REAL del
                     agente sobre un grafo real. Es lo que se puede mostrar corriendo.
  --preflight        [requiere API] 1 pregunta, 1 rep. Confirma temperature+thinking y
                     VERIFICA que los 4 campos de tokens se pueblan (item 1 de la autora).
  --verify-replay    [requiere API] 1 pregunta dos veces; confirma 100% de hits en TODOS
                     los turnos del 2do pase (item 4 — replay multi-turno no re-paga).
  (default)          [requiere API] corrida completa del eval_set sobre el/los grafo(s).

Flag --thinking prende/apaga thinking_enabled. Plan: primero --thinking ausente
(OFF, control), después --thinking (ON, cualitativo).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loader import load_graph, EVAL_DIR, RUN_KEYS
from harness import GraphAgent
import judge
import llm_cache as lc

# --------------------------------------------------------------------------- #
# Config                                                                       #
# --------------------------------------------------------------------------- #
POSTHOC_DIR = EVAL_DIR / "posthoc_run"
DB_PATH = EVAL_DIR / "cache" / "calls.db"
EVAL_SET = EVAL_DIR / "queries" / "eval_set_v1.json"
DEV_POOL = EVAL_DIR / "queries" / "dev_pool.json"

# Presupuestos de thinking (tunables; su efecto real se valida con --preflight).
AGENT_THINK_BUDGET = 4000      # < max_tokens efectivo (base 2048 + 4000 = 6048)
JUDGE_THINK_BUDGET = 6000

# Precios (USD/MTok) — idénticos a los del frozen para comparabilidad de costos.
HAIKU_IN, HAIKU_OUT = 1.00, 5.00
SONNET_IN, SONNET_OUT = 3.00, 15.00


def _judge_cost(usage: dict) -> float:
    return round(usage.get("in", 0) * SONNET_IN / 1e6
                 + usage.get("out", 0) * SONNET_OUT / 1e6, 6)


# --------------------------------------------------------------------------- #
# ParamOverrideClient — inyecta thinking/temperature/max_tokens SIN tocar el   #
# harness/juez congelados. Va POR ENCIMA de la caché.                          #
# --------------------------------------------------------------------------- #
def identity_transform(kwargs: dict) -> dict:
    return kwargs


def make_thinking_transform(budget: int):
    """Transform para thinking ON: agrega thinking, quita temperature, sube max_tokens
    a base+budget (garantiza budget < max_tokens y conserva el espacio de la respuesta).
    Se aplica por-llamada, así respeta el max_tokens propio de cada paso del juez."""
    def _t(kwargs: dict) -> dict:
        kw = dict(kwargs)
        kw.pop("temperature", None)   # thinking clásico (Haiku 4.5) no admite temp custom
        kw["thinking"] = {"type": "enabled", "budget_tokens": budget}
        base = int(kw.get("max_tokens", 1024) or 1024)
        kw["max_tokens"] = base + budget
        return kw
    return _t


class ParamOverrideClient:
    """Wrapper drop-in que reescribe los kwargs del create antes de pasarlos hacia
    adentro (a la caché). `transform(kwargs) -> kwargs`."""

    def __init__(self, inner, transform=identity_transform):
        self._inner = inner
        self._transform = transform
        self.messages = _OverrideMessages(self)


class _OverrideMessages:
    def __init__(self, owner):
        self._o = owner

    def create(self, **kwargs):
        return self._o._inner.messages.create(**self._o._transform(kwargs))


# --------------------------------------------------------------------------- #
# Construcción de la cadena de clientes                                        #
# --------------------------------------------------------------------------- #
def build_clients(real_client, kg, *, thinking: bool, db_path: Path, run_label: str):
    """Devuelve (agent_client, judge_client, agent_cache, judge_cache).
    agent_client/judge_client son los ParamOverride que ven harness y juez.
    agent_cache/judge_cache son los CachingClient (para stats + leer access_log)."""
    cv = lc.code_version()

    # kg.path robusto (punto 2 de la autora): fallar ruidosamente si falta.
    kg_path = getattr(kg, "path", None)
    if not kg_path or not Path(kg_path).exists():
        raise RuntimeError(
            f"KnowledgeGraph sin .path válido (run={getattr(kg,'run_key','?')}). "
            "El graph_fingerprint se degradaría a solo LOADER_VERSION y perdería la "
            "protección contra hits stale por cambio de kg.json. Abortando.")
    gfp = lc.graph_fingerprint(kg)

    agent_cache = lc.CachingClient(
        real_client, domain="agent", db_path=db_path,
        namespace=lc.make_namespace("agent", code_ver=cv, graph_fp=gfp, thinking=thinking),
        thinking_enabled=thinking, run_label=run_label)
    judge_cache = lc.CachingClient(
        real_client, domain="judge", db_path=db_path,
        namespace=lc.make_namespace("judge", code_ver=cv, thinking=thinking),
        thinking_enabled=thinking, run_label=run_label)

    if thinking:
        agent_xf = make_thinking_transform(AGENT_THINK_BUDGET)
        judge_xf = make_thinking_transform(JUDGE_THINK_BUDGET)
    else:
        agent_xf = judge_xf = identity_transform

    agent_client = ParamOverrideClient(agent_cache, agent_xf)
    judge_client = ParamOverrideClient(judge_cache, judge_xf)
    return agent_client, judge_client, agent_cache, judge_cache


# --------------------------------------------------------------------------- #
# Lectura de los crudos por-turno desde la caché (vía access_log)              #
# Permite trazas self-contained y nothing-dropped SIN tocar llm_cache.         #
# --------------------------------------------------------------------------- #
def _max_access_rowid(cache) -> int:
    r = cache._conn.execute("SELECT COALESCE(MAX(rowid),0) AS m FROM access_log").fetchone()
    return r["m"]


def _turns_since(cache, start_rowid: int, domain: str):
    """Crudos de las llamadas de `domain` posteriores a start_rowid, en orden.
    Devuelve (n_hits, n_total, turns) donde cada turn = {hit, raw(model_dump)}."""
    rows = cache._conn.execute(
        "SELECT key, hit FROM access_log WHERE rowid > ? AND domain = ? ORDER BY rowid",
        (start_rowid, domain)).fetchall()
    turns, n_hits = [], 0
    for r in rows:
        n_hits += int(r["hit"])
        c = cache._conn.execute("SELECT raw_json FROM cache WHERE key = ?",
                                (r["key"],)).fetchone()
        turns.append({"hit": bool(r["hit"]),
                      "raw": json.loads(c["raw_json"]) if c else None})
    return n_hits, len(rows), turns


# --------------------------------------------------------------------------- #
# Una repetición: agente + juez, con captura completa                          #
# --------------------------------------------------------------------------- #
def run_rep(agent, judge_client, agent_cache, judge_cache, q, run_key, rep_k,
            thinking: bool, capture_raw=True) -> dict:
    qid = q["id"]
    a0 = _max_access_rowid(agent_cache)
    tr = agent.ask(qid, q.get("pregunta", ""))
    _, _, agent_turns = _turns_since(agent_cache, a0, "agent") if capture_raw else (0, 0, [])

    failed = (not tr.parse_ok) or tr.truncated_max_tokens or (tr.error is not None)
    judge_out, judge_turns = None, []
    if not failed:
        j0 = _max_access_rowid(judge_cache)
        judge_out = judge.judge_trace(judge_client, q, vars(tr))
        if capture_raw:
            _, _, judge_turns = _turns_since(judge_cache, j0, "judge")

    return {
        "rep": rep_k + 1,
        "qid": qid, "run": run_key, "categoria": q.get("categoria"),
        "thinking_enabled": thinking,
        "failed_trace": failed,
        # Resumen del QuestionTrace (igual que el loop manual: steps, api_calls,
        # final_raw, seen_provenances, tokens por rep, etc.).
        "trace": vars(tr),
        # Crudo íntegro por turno del AGENTE (content[] incl. thinking blocks, usage,
        # stop_reason) — recuperado de la caché. Nothing-dropped.
        "raw_turns_agent": agent_turns,
        # Juez 2 pasos COMPLETO: step1 + step2 + verdict (lo que el frozen descartaba).
        "judge": judge_out,
        "raw_turns_judge": judge_turns,
        "harness_cost": tr.cost_usd,
        "judge_cost": _judge_cost(judge_out["usage"]) if judge_out else 0.0,
    }


# --------------------------------------------------------------------------- #
# Corrida de un grafo                                                          #
# --------------------------------------------------------------------------- #
def run_graph(real_client, run_key, questions, *, reps, thinking, db_path, label):
    kg = load_graph(run_key)
    agent_client, judge_client, agent_cache, judge_cache = build_clients(
        real_client, kg, thinking=thinking, db_path=db_path, run_label=label)
    agent = GraphAgent(kg, client=agent_client, cache_conversation=True)

    outdir = POSTHOC_DIR / "traces" / label / run_key
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"== posthoc {run_key} | thinking={'ON' if thinking else 'OFF'} | "
          f"{len(questions)} preguntas × {reps} reps ==", flush=True)

    all_reps = []
    for q in questions:
        reps_q = []
        for k in range(reps):
            r = run_rep(agent, judge_client, agent_cache, judge_cache,
                        q, run_key, k, thinking)
            reps_q.append(r)
            v = (r["judge"] or {}).get("verdict") if r["judge"] else None
            print(f"  [{q['id']} rep{k+1}] failed={r['failed_trace']} "
                  f"tools={r['trace']['tool_calls_used']} "
                  f"corr={(v or {}).get('correctitud')} "
                  f"costo=${r['harness_cost']+r['judge_cost']:.5f}", flush=True)
        json.dump(reps_q, open(outdir / f"{q['id']}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        all_reps.extend(reps_q)

    summary = {
        "run_key": run_key, "label": label, "thinking_enabled": thinking,
        "timestamp": datetime.now().isoformat(),
        "n_preguntas": len(questions), "reps_por_pregunta": reps,
        "n_reps_total": len(all_reps),
        "n_failed": sum(1 for r in all_reps if r["failed_trace"]),
        "costo_usd": round(sum(r["harness_cost"] + r["judge_cost"] for r in all_reps), 6),
        "agent_cache_stats": agent_cache.stats(),
        "judge_cache_stats": judge_cache.stats(),
        "code_version": lc.code_version(),
        "graph_fingerprint": lc.graph_fingerprint(kg),
    }
    POSTHOC_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(POSTHOC_DIR / f"summary_{label}_{run_key}.json", "w",
                            encoding="utf-8"), ensure_ascii=False, indent=2)
    agent_cache.close()
    judge_cache.close()
    print(f"  -> trazas en {outdir}  | costo grafo ${summary['costo_usd']:.5f} "
          f"| hit_rate agente {summary['agent_cache_stats']['hit_rate']}", flush=True)
    return summary


def _load_questions(path: Path) -> list:
    data = json.load(open(path, encoding="utf-8"))
    return data["preguntas"] if isinstance(data, dict) else data


# --------------------------------------------------------------------------- #
# Modos que requieren API                                                      #
# --------------------------------------------------------------------------- #
def _real_client(max_retries=3):
    from dotenv import load_dotenv
    import os
    load_dotenv(EVAL_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise SystemExit(f"ERROR: ANTHROPIC_API_KEY no seteada en {EVAL_DIR/'.env'}")
    import anthropic
    # Se usa el retry NATIVO del SDK (429/5xx con backoff). Se evita importar
    # run_frozen.RetryingClient porque su import aplica un monkeypatch global a
    # judge._call. CachingClient compone igual con RetryingClient si se quisiera.
    return anthropic.Anthropic(max_retries=max_retries)


def preflight(run_key, thinking, db_path, label):
    """[API] item 1: 1 pregunta 1 rep; confirma temperature+thinking y que los 4
    campos de tokens se pueblan con valores reales (no quedan en 0).

    CRITERIOS DE ÉXITO de una corrida SANA:
      - stop_reason final == 'end_turn'  (la respuesta JSON terminó completa).
        Si sale 'max_tokens', el JSON final se CORTÓ: hay que subir el presupuesto
        de thinking / max_tokens (AGENT_THINK_BUDGET y/o el base de max_tokens).
        ('tool_use' nunca debería ser el stop_reason FINAL: el loop solo termina
        cuando el modelo deja de pedir tools.)
      - input_tokens > 0 y output_tokens > 0 en el agregado de turnos.
      - cache_read/cache_write pueden ser 0 legítimamente (prefijo < 4096 tok, mín
        de Haiku) — se reporta, no se exige.
      - con thinking ON: al menos un thinking block en el content."""
    real = _real_client()
    kg = load_graph(run_key)
    agent_client, judge_client, agent_cache, judge_cache = build_clients(
        real, kg, thinking=thinking, db_path=db_path, run_label=label + "_preflight")
    agent = GraphAgent(kg, client=agent_client, cache_conversation=True)
    q = _load_questions(EVAL_SET)[0]
    print(f"== PREFLIGHT {run_key} thinking={'ON' if thinking else 'OFF'} :: {q['id']} ==")
    a0 = _max_access_rowid(agent_cache)
    tr = agent.ask(q["id"], q["pregunta"])
    _, _, turns = _turns_since(agent_cache, a0, "agent")

    print(f"\nstop_reason final: {tr.final_stop_reason} | parse_ok={tr.parse_ok} | "
          f"tools={tr.tool_calls_used} | error={tr.error}")
    print("\nDesglose de tokens por turno (item 1 — deben poblarse, no quedar en 0):")
    agg = {"in": 0, "out": 0, "cr": 0, "cw": 0}
    for i, t in enumerate(turns, 1):
        u = (t["raw"] or {}).get("usage", {}) or {}
        ci, co = u.get("input_tokens", 0), u.get("output_tokens", 0)
        cr, cw = u.get("cache_read_input_tokens", 0), u.get("cache_creation_input_tokens", 0)
        has_think = any(b.get("type") == "thinking" for b in (t["raw"] or {}).get("content", []))
        print(f"  turno {i}: in={ci} out={co} cache_read={cr} cache_write={cw} "
              f"| thinking_block={'sí' if has_think else 'no'}")
        agg["in"] += ci; agg["out"] += co; agg["cr"] += cr; agg["cw"] += cw
    print(f"  TOTAL: in={agg['in']} out={agg['out']} cache_read={agg['cr']} "
          f"cache_write={agg['cw']}")
    ok_io = agg["in"] > 0 and agg["out"] > 0
    ok_cache = (agg["cr"] + agg["cw"]) > 0
    cache_note = (">0" if ok_cache else
                  "=0 (puede ser legítimo: prefijo < 4096 tok mín de Haiku; "
                  "ver harness.py:404)")
    # CRITERIO DE STOP_REASON: sano == end_turn; max_tokens == JSON cortado.
    ok_stop = (tr.final_stop_reason == "end_turn") and not tr.truncated_max_tokens
    print(f"\n[{'PASS' if ok_stop else 'FAIL'}] stop_reason final == 'end_turn' "
          f"(obtenido: {tr.final_stop_reason})")
    if tr.truncated_max_tokens or tr.final_stop_reason == "max_tokens":
        print("  ⚠ stop_reason=max_tokens → el JSON final se CORTÓ. Subí "
              "AGENT_THINK_BUDGET y/o el base de max_tokens y reintentá el preflight.")
    print(f"[{'PASS' if ok_io else 'FAIL'}] input/output tokens > 0")
    print(f"[{'INFO' if ok_cache else 'WARN'}] cache_read+cache_write {cache_note}")
    ok = ok_io and ok_stop
    if thinking:
        any_think = any(any(b.get("type") == "thinking"
                            for b in (t["raw"] or {}).get("content", [])) for t in turns)
        print(f"[{'PASS' if any_think else 'FAIL'}] thinking ON produjo thinking blocks")
        print("  -> CONFIRMAR a mano que temperature+thinking no dio 400 (si llegó acá, ok).")
        ok = ok and any_think
    agent_cache.close(); judge_cache.close()
    return ok


def verify_replay(run_key, thinking, db_path, label):
    """[API] item 4: corre la MISMA pregunta dos veces; el 2do pase debe dar 100% de
    hits en TODOS los turnos (replay multi-turno no re-paga).

    CRITERIO DE ÉXITO: pase 1 con 0 hits, pase 2 con hits == nº de turnos (100%),
    mismo nº de turnos en ambos pases. Eso prueba que la serialización de los
    ContentBlocks del historial es estable turno a turno.

    RESPETA EL FLAG THINKING: corre con `thinking` tal cual se lo pasa (NO hardcodeado
    en OFF). Con `--thinking`, el pase 1 genera thinking blocks con `signature` reales
    y el 2do pase debe cachearlos idénticos — exactamente lo que el selftest OFFLINE
    NO pudo probar (su Message falso no traía signatures reales). Corré este modo en
    AMBOS estados: una vez sin --thinking (control) y otra con --thinking (firma real)."""
    import tempfile
    real = _real_client()
    kg = load_graph(run_key)
    q = _load_questions(EVAL_SET)[0]
    print(f"== VERIFY-REPLAY {run_key} thinking={'ON' if thinking else 'OFF'} :: {q['id']} ==")

    # Caché TEMPORAL AISLADA: este modo necesita arrancar de caché VACÍA para que el
    # assert "pase 1 = 0 hits" sea válido. Usar la calls.db de producción rompe el
    # test si esa pregunta ya fue cacheada (p. ej. por un --preflight previo) y además
    # ensucia producción. El tempdir se borra al salir; producción no se toca.
    # (Ignora deliberadamente db_path; el namespace/serialización son los mismos.)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "replay_cache.db"
        agent_client, _, agent_cache, judge_cache = build_clients(
            real, kg, thinking=thinking, db_path=tmp_db, run_label=label + "_replay")
        agent = GraphAgent(kg, client=agent_client, cache_conversation=True)

        a0 = _max_access_rowid(agent_cache)
        agent.ask(q["id"], q["pregunta"])                   # PASE 1 (misses, paga real)
        h1, n1, _ = _turns_since(agent_cache, a0, "agent")
        a1 = _max_access_rowid(agent_cache)
        agent.ask(q["id"], q["pregunta"])                   # PASE 2 (debe ser todo hits)
        h2, n2, _ = _turns_since(agent_cache, a1, "agent")
        agent_cache.close(); judge_cache.close()

    print(f"  pase 1: {n1} turnos, {h1} hits (esperado 0 hits)")
    print(f"  pase 2: {n2} turnos, {h2} hits (esperado {n2} = 100%)")
    ok = (n1 == n2 and n2 > 0 and h2 == n2 and h1 == 0)
    print(f"\n[{'PASS' if ok else 'FAIL'}] replay multi-turno: 2do pase 100% hits en "
          f"todos los turnos (serialización de ContentBlocks estable turno a turno"
          + (", incl. thinking blocks con signature real" if thinking else "") + ")")
    return ok


# --------------------------------------------------------------------------- #
# Selftest OFFLINE (sin API) — cablea el runner REAL con un cliente falso       #
# --------------------------------------------------------------------------- #
def _selftest():
    import tempfile
    from anthropic.types import Message

    _checks = []
    def check(name, cond): _checks.append((name, bool(cond)))

    # --- 1) unit: el transform de thinking inyecta bien ---
    xf = make_thinking_transform(4000)
    out = xf({"model": "m", "max_tokens": 2048, "temperature": 0, "system": "s",
              "messages": [], "tools": []})
    check("thinking transform: agrega thinking enabled+budget",
          out.get("thinking") == {"type": "enabled", "budget_tokens": 4000})
    check("thinking transform: QUITA temperature", "temperature" not in out)
    check("thinking transform: max_tokens = base+budget (budget<max)",
          out["max_tokens"] == 2048 + 4000)
    check("identity transform: passthrough exacto (control OFF)",
          identity_transform({"a": 1}) == {"a": 1})

    # --- 2) cableado + replay multi-turno con el loop REAL del agente y cliente falso ---
    kg = load_graph("run_3")

    # cliente falso que devuelve 2 turnos scripteados: turno1 tool_use, turno2 final JSON.
    TURN1 = {
        "id": "msg_t1", "type": "message", "role": "assistant",
        "model": "claude-haiku-4-5-20251001",
        "content": [
            {"type": "text", "text": "Busco en el grafo."},
            {"type": "tool_use", "id": "toolu_a", "name": "buscar_nodos",
             "input": {"consulta": "encaje", "limite": 5}},
        ],
        "stop_reason": "tool_use", "stop_sequence": None,
        "usage": {"input_tokens": 1433, "output_tokens": 40,
                  "cache_read_input_tokens": 0, "cache_creation_input_tokens": 1200},
    }
    TURN2 = {
        "id": "msg_t2", "type": "message", "role": "assistant",
        "model": "claude-haiku-4-5-20251001",
        "content": [{"type": "text",
                     "text": '{"respuesta":"prueba","citas":[],"respondible":true}'}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 1600, "output_tokens": 60,
                  "cache_read_input_tokens": 1433, "cache_creation_input_tokens": 0},
    }

    class FakeMessages:
        def __init__(self): self.calls = 0; self.script = [TURN1, TURN2]
        def create(self, **kwargs):
            i = self.calls; self.calls += 1
            if i >= len(self.script):
                raise AssertionError(f"llamada inesperada al cliente real (#{i+1}); "
                                     "un turno cacheó mal → replay NO determinista")
            return Message.model_validate(self.script[i])

    class FakeClient:
        def __init__(self, m): self.messages = m

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "calls.db"
        fake = FakeMessages()
        agent_cache = lc.CachingClient(
            FakeClient(fake), domain="agent", db_path=db,
            namespace=lc.make_namespace("agent", code_ver="cv", graph_fp="gfp",
                                        thinking=False),
            thinking_enabled=False, run_label="selftest")
        agent_client = ParamOverrideClient(agent_cache, identity_transform)
        agent = GraphAgent(kg, client=agent_client, cache_conversation=True)

        # PASE 1 — misses, ejercita el loop real (2 turnos)
        a0 = _max_access_rowid(agent_cache)
        tr1 = agent.ask("ST", "¿qué es el encaje?")
        h1, n1, turns1 = _turns_since(agent_cache, a0, "agent")
        check("pase 1: el loop real hizo >=2 turnos", n1 >= 2)
        check("pase 1: todos misses (0 hits)", h1 == 0)
        check("pase 1: el cliente real se llamó una vez por turno", fake.calls == n1)
        check("pase 1: respuesta final parseada", tr1.parse_ok and tr1.final_json is not None)

        calls_after_p1 = fake.calls
        # PASE 2 — misma pregunta: debe ser TODO hits y NO llamar al cliente real
        a1 = _max_access_rowid(agent_cache)
        tr2 = agent.ask("ST", "¿qué es el encaje?")
        h2, n2, turns2 = _turns_since(agent_cache, a1, "agent")
        check("pase 2: mismo nº de turnos que el pase 1", n2 == n1)
        check("REPLAY MULTI-TURNO: 2do pase 100% hits en TODOS los turnos", h2 == n2 and n2 > 0)
        check("pase 2: NO se volvió a llamar al cliente real (no re-paga)",
              fake.calls == calls_after_p1)
        check("pase 2: misma respuesta final reconstruida",
              tr2.final_json == tr1.final_json)

        # --- 3) crudos por-turno recuperados (nothing-dropped) + tokens no-cero ---
        check("crudos por-turno recuperados de la caché", all(t["raw"] for t in turns1))
        u_turn2 = turns1[-1]["raw"]["usage"]
        check("desglose de tokens del último turno poblado (cache_read no-cero)",
              u_turn2["cache_read_input_tokens"] == 1433 and u_turn2["input_tokens"] == 1600)
        agent_cache.close()

    print("\n=== run_posthoc --selftest (OFFLINE, sin API) ===\n")
    passed = sum(ok for _, ok in _checks)
    for name, ok in _checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n  {passed}/{len(_checks)} checks OK")
    print("  RESULTADO:", "PASS ✅" if passed == len(_checks) else "FAIL ❌")
    return 0 if passed == len(_checks) else 1


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Runner post-hoc instrumentado (Fase 2.3+).")
    ap.add_argument("--run", default="run_3", help="run_1..run_5 o 'all' (def run_3)")
    ap.add_argument("--reps", type=int, default=3, help="repeticiones por pregunta")
    ap.add_argument("--thinking", action="store_true", help="prende thinking_enabled (def OFF)")
    ap.add_argument("--queries", default=str(EVAL_SET))
    ap.add_argument("--label", default=None, help="etiqueta de corrida (def on/off)")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--selftest", action="store_true", help="prueba OFFLINE (sin API)")
    ap.add_argument("--preflight", action="store_true", help="[API] item 1: tokens reales")
    ap.add_argument("--verify-replay", action="store_true",
                    help="[API] item 4: replay multi-turno 100%% hits")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    label = args.label or ("on" if args.thinking else "off")
    db_path = Path(args.db)

    if args.preflight:
        return 0 if preflight(args.run, args.thinking, db_path, label) else 1
    if args.verify_replay:
        return 0 if verify_replay(args.run, args.thinking, db_path, label) else 1

    # corrida completa (requiere API)
    real = _real_client()
    runs = RUN_KEYS if args.run == "all" else [args.run]
    questions = _load_questions(Path(args.queries))
    for rk in runs:
        run_graph(real, rk, questions, reps=args.reps, thinking=args.thinking,
                  db_path=db_path, label=label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
