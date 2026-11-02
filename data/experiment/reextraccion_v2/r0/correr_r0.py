"""
correr_r0.py — R0: E3-01 de la tanda 0 dentro del re-sellado único (enmienda 7 al protocolo entre tandas, firmada en
4a33ce92; nota al pie del 09/10/2026 en 0c516af9: R0 corre solo E3-01, con tope de USD 1,50).

Las 20 unidades de ítems de lista de la lista sellada de O3 (cc6b0cd6…) pasan por el E3 corregido con el ratchet de
siempre: el E1 del intento 0 está en la caché y E3 es el de O3. Con el veredicto de cada verificación, la unidad se
acepta con el intento 0, reintenta con E1 y E3 nuevos o vuelve a la cola; cada una recibe un registro final nuevo
(enmienda 5, §1.3).

El código es el del pipeline; nada se copia:
  - importa runner_corpus (que agrega e1, e3, e2 y e0 al sys.path), lo configura con el manifiesto de la tanda 0 r2b
    y activa el camino del perfil r2 como main() (PERFIL_R2 = perfil_forma_r2(PERFIL));
  - arma una carpeta de trabajo (--trabajo) con el registro de E1 del intento 0 de las 20 (la última línea de cada una
    en extracciones_e1.jsonl de la tanda 0, byte a byte; es la del compactado) y corre sobre ella
    runner_corpus.fase_e3 de cada TO, en el orden del manifiesto: fase_e3 procesa justo esas unidades (pares_de las
    toma del E1 de la carpeta), con las unidades del corpus de la E0 entera del TO para la guardia B, el techo del
    reintento de techo_reintento_ratchet, ratchet_e3.ciclo_ratchet y los registros de siempre;
  - los clientes son cliente_e3.ClienteE3Real y cliente_e1.ClienteE1Real (este, con la base de reintentos del
    pipeline y el prefijo del perfil), con el tope duro COMPARTIDO de runner_corpus.PresupuestoCompartido (--tope,
    obligatorio, hasta USD 1,50) y una guardia antes de cada llamada: el pedido sin el mensaje es el del prefijo
    sellado en esperados_r0.json, y el mensaje es uno de los esperados (las 20 verificaciones, con el sha256 del
    control de O3; los 3 reintentos de E1, con el armado desde el veredicto de O3) o, en la re-verificación de E3 y en
    el reintento de E1 sin reuso, el de una unidad de las 20 que ya pasó por el paso anterior. Después de cada
    respuesta controla el id del modelo (E1 claude-haiku-4-5-20251001, E3 claude-sonnet-5, los de la tanda 0). Una
    guardia que frena queda frenada: los reintentos de API del runner no vuelven a llamar;
  - el reuso de las 20 verificaciones de O3 (--reuso-o3, pregunta b): «sembrar» copia sus 20 filas a la base de E3 de
    la corrida antes de la primera llamada, y fase_e3 las encuentra como aciertos de la caché local; «leer» las
    devuelve como respuesta desde la base de O3, abierta en modo inmutable, sin escribirlas; «no», sin reuso. Las
    bases de la corrida son las del pipeline salvo que --db-e3 y --db-e1r digan otras; una ruta nueva es una base
    propia de R0, que el sembrado crea con el esquema de llm_cache;
  - --anexar (pregunta c): agrega a la salida de la tanda 0 los renglones nuevos de la carpeta de trabajo (finales,
    veredictos, reintentos_e3, cola_humana y copias_nota_e3 de cada TO), byte a byte, y controla que cada archivo
    quede igual a su versión anterior más esos renglones. Una sola vez por carpeta de trabajo.

Caching (docs/decisiones_caching_extraccion.md): los pedidos los arman prompt_e3 y el perfil r2b, con el system en
bloques y cache_control (D1); el gasto, con la fórmula de caching de los clientes (D2); los clientes loguean el usage
de cada respuesta real en logs/cache_usage.jsonl, y R0 además cada llamada en registro_llamadas_r0.jsonl (D3); en
secuencia, un proceso (D4); el pipeline de evaluación no se toca (D5).

Modos:
  --esperados <json>   escribe los valores esperados (sin red, USD 0)
  --seco               sin red ni clave: los mismos clientes con un transporte simulado en lugar del de la API, sobre
                       bases que no son las del pipeline (--db-e3, --db-e1r); --escenario elige las respuestas
  --correr             con API; solo con el «seguí» de la autora; --tope obligatorio
  --anexar             sin red: agrega los renglones de --trabajo a --salida-t0

Uso (siempre con PYTHONDONTWRITEBYTECODE=1 y .venv/bin/python -B):
  correr_r0.py --correr --tope 1.50 --reuso-o3 sembrar
  correr_r0.py --anexar
  correr_r0.py --seco --escenario base --reuso-o3 sembrar --trabajo <dir> --db-e3 <copia> --db-e1r <copia> --tope 1.50
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent                    # reextraccion_v2/r0
REX = AQUI.parent
REPO = REX.parents[2]
if str(REX / "corpus_v2") not in sys.path:
    sys.path.insert(0, str(REX / "corpus_v2"))
import runner_corpus as RC          # noqa: E402  (agrega e1, e3, e2, e0 y reextraccion_v2 al sys.path)
import manifiesto_corpus            # noqa: E402
import comun_e3                     # noqa: E402
import cliente_e1                   # noqa: E402
import cliente_e3                   # noqa: E402
import prompt_e3                    # noqa: E402
import ratchet_e3                   # noqa: E402
import llm_cache as lc              # noqa: E402

LISTA = REPO / "data/experiment/e3_listas/o3/lista_unidades_afectadas_tanda0.json"
LISTA_SHA256 = "cc6b0cd6c56831c486d60bf7da64712cea391a1eb2948eef822448567df9bab6"
RUNNER_SHA256 = "a287c7479939bab8667131c1c9a59cadd61f129a8bb9e0eeed8c2e1567c082a6"
CLIENTE_E3_SHA256 = "e7b4b164f0062f2d501e854d6e7582e6d35d69ee7f87d13abe86b6b9c673ec10"
O3A = REPO / "data/experiment/e3_listas/o3/a"
DB_O3 = REPO / "data/experiment/e3_listas/cache/e3_listas_o3.db"
DB_O3_SHA256 = "ab5321543ad306396014ed0bbe3d555a0df0b2c23f0e3bc71ec839ab0975ea3f"   # commit 6dde4b9b (O3)
MANIFIESTO = REX / "manifiestos/tanda0_10tos_r2b.json"
SALIDA_T0 = REX / "corpus_tanda0/salida_r2b"
TRABAJO = AQUI / "corrida"
ESPERADOS = AQUI / "esperados_r0.json"
TOPE_MAXIMO = 1.50                  # enmienda 7, decisión 1 al firmar
NS_E1 = "e1_extraccion|cv=e1-extractor-v1-p322c5a23e9b7|think=0"
NS_E3 = "e3_verificacion|cv=e3-verificador-v1-p21a836c7de6d|think=0"
MODELO_RESPUESTA = {"e3": "claude-sonnet-5", "e1r": "claude-haiku-4-5-20251001"}   # reext_t0/freno_t2.md:8
ARCHIVOS_ANEXO = ("finales.jsonl", "veredictos.jsonl", RC.REINTENTOS_E3, "cola_humana.jsonl",
                  "copias_nota_e3.jsonl")
REGISTRO_LLAMADAS = "registro_llamadas_r0.jsonl"
PRESUPUESTO = "presupuesto_r0.json"
RESUMEN = "resumen_r0.json"
ANEXO = "anexo_r0.json"


class FrenoR0(RuntimeError):
    pass


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_s(s: str) -> str:
    return sha_b(s.encode("utf-8"))


def ahora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def rel(p: Path) -> str:
    """La ruta relativa al repo; fuera del repo, con la carpeta personal como <home> (los registros no llevan rutas
    de la sesión)."""
    p = Path(p).resolve()
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return str(p).replace(str(Path.home()), "<home>")


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def abrir_ro(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{urllib.parse.quote(str(Path(db).resolve()))}?mode=ro&immutable=1", uri=True)


def sha_sin_mensaje(kwargs: dict) -> str:
    """sha256 del pedido canónico sin `messages`: modelo, techo, system, tools, tool_choice y temperatura."""
    return sha_s(lc.canonical_request({k: v for k, v in kwargs.items() if k != "messages"}))


def append_linea(path: Path, reg: dict) -> None:
    RC.append_jsonl(path, reg)


# ----------------------------- contexto y controles previos (sin red) ------ #
def cargar_contexto(salida_t0: Path) -> dict:
    """Configura el runner como main() y carga las 20 unidades: chunk, registro de E1 del intento 0 (con su línea
    cruda), unidades del corpus por TO y la verificación de O3."""
    if sha_b(LISTA.read_bytes()) != LISTA_SHA256:
        raise FrenoR0("la lista sellada de O3 no tiene el sha256 cc6b0cd6…")
    for mod, esperado in ((RC, RUNNER_SHA256), (cliente_e3, CLIENTE_E3_SHA256)):
        if sha_b(Path(mod.__file__).read_bytes()) != esperado:
            raise FrenoR0(f"{Path(mod.__file__).name} no tiene el sha256 de la fase 1 ({esperado[:12]}…)")
    RC.configurar(manifiesto_corpus.cargar(MANIFIESTO))
    RC.PERFIL_R2 = RC.perfil_forma_r2(RC.PERFIL)          # como main() del runner
    unidades = [u["chunk_id"] for u in json.loads(LISTA.read_text(encoding="utf-8"))["unidades"]]
    if len(unidades) != 20 or len(set(unidades)) != 20:
        raise FrenoR0("la lista no tiene 20 unidades distintas")
    ns_e1 = cliente_e1.namespace_e1(prefijo_hash=RC.PERFIL.prefijo_hash_para_namespace)
    ns_e3 = cliente_e3.namespace_e3()
    if (ns_e1, ns_e3) != (NS_E1, NS_E3):
        raise FrenoR0(f"namespaces {ns_e1} / {ns_e3} distintos de los de la tanda 0")
    ctx = {"salida_t0": salida_t0, "unidades": set(unidades), "por_to": {}, "chunks": {}, "regs": {},
           "lineas": {}, "unidades_corpus": {}, "ns_e1": ns_e1, "ns_e3": ns_e3}
    for to in RC.TOS_ORDEN:
        suyas = {u for u in unidades if u.split("::")[0] == to}
        if not suyas:
            continue
        tdir = salida_t0 / to
        chunks = RC.chunks_con_partes(RC.chunks_sin_ids_repetidos(
            comun_e3.cargar_chunks((to,), e0_dir=RC.E0_DIR), to), tdir)
        ctx["unidades_corpus"][to] = {c["unidad"] for c in chunks}
        ctx["por_to"][to] = [c["id"] for c in chunks if c["id"] in suyas]
        for c in chunks:
            if c["id"] in suyas:
                ctx["chunks"][c["id"]] = c
        with (tdir / "extracciones_e1.jsonl").open(encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    cid = json.loads(linea)["chunk_id"]
                    if cid in suyas:
                        ctx["lineas"][cid] = linea if linea.endswith("\n") else linea + "\n"
        for cid in suyas:
            ctx["regs"][cid] = json.loads(ctx["lineas"][cid])
    if set(ctx["chunks"]) != ctx["unidades"] or set(ctx["regs"]) != ctx["unidades"]:
        raise FrenoR0("faltan unidades de la lista en la E0 o en el E1 de la tanda 0")
    ctx["o3"] = {r["chunk_id"]: r for r in jl(O3A / "respuestas_e3_o3.jsonl")}
    ctx["control_o3"] = {r["chunk_id"]: r["sha_msg"] for r in
                         json.loads((O3A / "control_mensajes_o2.json").read_text(encoding="utf-8"))}
    return ctx


def calcular_esperados(ctx: dict) -> dict:
    """Valores esperados, sin red: el mensaje y la clave de E3 de cada verificación; con el veredicto de O3, la decisión
    del ratchet y, para las que reintentan, el mensaje y la clave del reintento de E1; los prefijos sin mensaje."""
    perfil = RC.PERFIL
    out = {"lista_sha256": LISTA_SHA256, "namespace_e1": ctx["ns_e1"], "namespace_e3": ctx["ns_e3"],
           "modelo_e1": RC.MODEL_E1, "modelo_e3": RC.MODEL_E3, "verificacion": {}, "reintento_e1_con_o3": {},
           "decision_con_o3": {}}
    pref_e3, pref_e1r = set(), set()
    for to, cids in ctx["por_to"].items():
        for cid in cids:
            c, reg = ctx["chunks"][cid], ctx["regs"][cid]
            kw = prompt_e3.build_request_kwargs(c, reg["validacion"], model=RC.MODEL_E3)
            pref_e3.add(sha_sin_mensaje(kw))
            out["verificacion"][cid] = {"sha_mensaje": sha_s(kw["messages"][0]["content"]),
                                        "clave": lc.compute_key(ctx["ns_e3"], lc.canonical_request(kw))}
            ev = ratchet_e3.evaluar_veredicto(ctx["o3"][cid]["tool_input"], c, ctx["unidades_corpus"][to],
                                              reg["validacion"])
            d = ("completo_ok_directo" if ev["es_completo_ok"] else "aceptado_con_residuales" if ev["aceptable"]
                 else "cola_humana_veredicto_inutilizable" if not ev["bloqueantes_utilizables"] else "reintenta")
            out["decision_con_o3"][cid] = d
            kwr = ratchet_e3.build_reextraccion_kwargs(
                c, ev["bloqueantes_utilizables"], model=RC.MODEL_E1, intento=1,
                max_tokens_reintento=RC.techo_reintento_ratchet(reg), perfil=perfil)
            pref_e1r.add(sha_sin_mensaje(kwr))
            if d == "reintenta":
                out["reintento_e1_con_o3"][cid] = {"sha_mensaje": sha_s(kwr["messages"][0]["content"]),
                                                   "clave": lc.compute_key(ctx["ns_e1"], lc.canonical_request(kwr)),
                                                   "max_tokens": kwr["max_tokens"]}
    if len(pref_e3) != 1 or len(pref_e1r) != 1:
        raise FrenoR0("el pedido sin mensaje no es uno solo entre las 20 unidades")
    out["prefijo_e3_sin_mensaje_sha256"] = pref_e3.pop()
    out["prefijo_e1r_sin_mensaje_sha256"] = pref_e1r.pop()
    out["reparto_con_o3"] = dict(Counter("acepta" if d.startswith(("completo", "aceptado")) else
                                         "cola" if d.startswith("cola") else d
                                         for d in out["decision_con_o3"].values()))
    return out


def controles_previos(ctx: dict, esperados_path: Path) -> dict:
    """Antes de toda llamada: el registro de E1 de cada unidad es el del compactado y E3 lo acepta; el E1 del intento 0
    está en la caché de E1 del pipeline con la respuesta guardada; el mensaje de E3 es el del control de O3; los
    esperados recomputados son los sellados en la fase 1."""
    res = {"hora": ahora(), "unidades": len(ctx["unidades"])}
    con = abrir_ro(cliente_e1.DB_PATH)
    e1_ok, comp_ok, msg_ok = [], [], []
    try:
        for to, cids in ctx["por_to"].items():
            compact = comun_e3.cargar_extracciones(ctx["salida_t0"] / to / "extracciones_e1_compact.jsonl")
            for cid in cids:
                c, reg = ctx["chunks"][cid], ctx["regs"][cid]
                if compact.get(cid) == reg and comun_e3.chunk_aceptado(reg):
                    comp_ok.append(cid)
                kw1 = RC.PERFIL.build_request_kwargs(c, model=RC.MODEL_E1)
                fila = con.execute("select model, raw_json from cache where key = ?",
                                   (lc.compute_key(ctx["ns_e1"], lc.canonical_request(kw1)),)).fetchone()
                if fila is not None and fila[0] == MODELO_RESPUESTA["e1r"]:
                    ti = next((b.get("input") for b in json.loads(fila[1]).get("content") or []
                               if isinstance(b, dict) and b.get("type") == "tool_use"), None)
                    if ti == reg.get("tool_input_crudo"):
                        e1_ok.append(cid)
                msg = prompt_e3.build_user_message(c, reg["validacion"])
                if sha_s(msg) == ctx["control_o3"][cid]:
                    msg_ok.append(cid)
    finally:
        con.close()
    res.update({"e1_registro_igual_al_compactado_y_aceptado": len(comp_ok),
                "e1_intento0_acierta_la_cache": len(e1_ok), "mensaje_e3_igual_al_control_de_o3": len(msg_ok)})
    esp = calcular_esperados(ctx)
    sellados = json.loads(esperados_path.read_text(encoding="utf-8"))
    res["esperados_sha256"] = sha_b(esperados_path.read_bytes())
    res["esperados_iguales_a_los_sellados"] = esp == sellados
    if not (len(comp_ok) == len(e1_ok) == len(msg_ok) == 20 and res["esperados_iguales_a_los_sellados"]):
        raise FrenoR0(f"controles previos: {json.dumps(res, ensure_ascii=False)}")
    if esp["reparto_con_o3"] != {"acepta": 16, "reintenta": 3, "cola": 1}:
        raise FrenoR0(f"el reparto con el veredicto de O3 no es el de la enmienda 7, §1.2: {esp['reparto_con_o3']}")
    return res


# ----------------------------- guardia de cada llamada --------------------- #
class Guardia:
    """Control antes de cada llamada (pedido sin mensaje y mensaje) y después de cada respuesta (id del modelo). Una
    guardia que frena queda frenada: toda llamada posterior frena antes de la caché y de la red."""

    def __init__(self, ctx: dict, esp: dict, reuso: str, trabajo: Path):
        self.reuso, self.path = reuso, trabajo / REGISTRO_LLAMADAS
        self.pref = {"e3": esp["prefijo_e3_sin_mensaje_sha256"], "e1r": esp["prefijo_e1r_sin_mensaje_sha256"]}
        self.verif = {v["sha_mensaje"]: cid for cid, v in esp["verificacion"].items()}
        self.reint = {v["sha_mensaje"]: cid for cid, v in esp["reintento_e1_con_o3"].items()}
        self.linea_unidad = {f"Unidad bajo verificación: {c['unidad']} — {c['titulo']}": cid
                             for cid, c in ctx["chunks"].items()}
        if len(self.linea_unidad) != 20:
            raise FrenoR0("dos unidades de la lista con la misma línea de unidad en el mensaje de E3")
        self.base_e1 = {cid: RC.PERFIL.build_request_kwargs(c, model=RC.MODEL_E1)["messages"][0]["content"]
                        + "\n\n" + ratchet_e3.MARCA_REINTENTO for cid, c in ctx["chunks"].items()}
        self.pasos: dict[str, list[str]] = defaultdict(list)
        self.frenada: str | None = None
        self.ultimo: dict | None = None
        self.n = 0

    def _frenar(self, motivo: str):
        self.frenada = motivo
        raise FrenoR0(motivo)

    def antes(self, tipo: str, kwargs: dict) -> dict:
        if self.frenada:
            raise FrenoR0(f"guardia frenada: {self.frenada}")
        if sha_sin_mensaje(kwargs) != self.pref[tipo]:
            self._frenar(f"{tipo}: el pedido sin el mensaje no es el del prefijo sellado")
        if len(kwargs.get("messages") or []) != 1:
            self._frenar(f"{tipo}: el pedido no tiene un solo mensaje")
        msg = kwargs["messages"][0]["content"]
        sm = sha_s(msg)
        if tipo == "e3":
            if sm in self.verif:
                cid, paso = self.verif[sm], "verificacion"
            else:
                cid = next((self.linea_unidad[x] for x in msg.splitlines() if x in self.linea_unidad), None)
                if cid is None or "reintento" not in self.pasos[cid]:
                    self._frenar(f"e3: mensaje inesperado (sha {sm[:12]}…), no es una verificación de las 20 ni la "
                                 f"re-verificación de una unidad que reintentó")
                paso = "re_verificacion"
        else:
            if self.reuso != "no":
                if sm not in self.reint:
                    self._frenar(f"e1r: el mensaje del reintento (sha {sm[:12]}…) no es el armado con el veredicto "
                                 f"de O3")
                cid = self.reint[sm]
            else:
                cid = next((k for k, b in self.base_e1.items() if msg.startswith(b)), None)
                if cid is None:
                    self._frenar(f"e1r: el mensaje del reintento (sha {sm[:12]}…) no es el de una de las 20")
            if "verificacion" not in self.pasos[cid]:
                self._frenar(f"e1r: reintento de {cid} sin su verificación")
            paso = "reintento"
        self.n += 1
        self.ultimo = {"n": self.n, "tipo": tipo, "chunk_id": cid, "paso": paso, "sha_mensaje": sm, "hora": ahora()}
        return self.ultimo

    def despues(self, llamada: dict, resp, hit: bool, usd: float, fuente: str) -> None:
        u = getattr(resp, "usage", None)
        reg = {**llamada, "hit_cache_local": hit, "fuente": fuente, "usd": round(usd, 6),
               "modelo_respuesta": getattr(resp, "model", None), "stop_reason": getattr(resp, "stop_reason", None),
               "usage": {k: getattr(u, k, None) for k in ("input_tokens", "output_tokens",
                                                          "cache_creation_input_tokens", "cache_read_input_tokens")}}
        append_linea(self.path, reg)
        self.pasos[llamada["chunk_id"]].append(llamada["paso"])
        if reg["modelo_respuesta"] != MODELO_RESPUESTA[llamada["tipo"]]:
            self._frenar(f"{llamada['tipo']}: la respuesta trae el modelo {reg['modelo_respuesta']} "
                         f"(esperado {MODELO_RESPUESTA[llamada['tipo']]})")


class ClienteE3R0(cliente_e3.ClienteE3Real):
    """ClienteE3Real con la guardia; con reuso «leer», las verificaciones de O3 salen de su base (inmutable)."""

    def __init__(self, *, guardia: Guardia, db_o3_leer: Path | None = None, **kw):
        super().__init__(**kw)
        self.guardia = guardia
        self.con_o3 = abrir_ro(db_o3_leer) if db_o3_leer is not None else None
        self.leidas_de_o3 = 0

    def create(self, *, doc: str | None = None, **kwargs):
        llamada = self.guardia.antes("e3", kwargs)
        if self.con_o3 is not None:
            key = lc.compute_key(self.cache.namespace, lc.canonical_request(kwargs))
            fila = self.con_o3.execute("select raw_json from cache where key = ?", (key,)).fetchone()
            if fila is not None:
                resp = lc._reconstruct(fila[0])
                self.llamadas += 1
                self.llamadas_hit += 1
                self.leidas_de_o3 += 1
                self.guardia.despues(llamada, resp, True, 0.0, "base_o3")
                return resp
        h0, g0 = self.llamadas_hit, self.gasto_usd
        resp = super().create(doc=doc, **kwargs)
        hit = self.llamadas_hit > h0
        self.guardia.despues(llamada, resp, hit, self.gasto_usd - g0, "cache_local" if hit else "api")
        return resp

    def close(self) -> None:
        if self.con_o3 is not None:
            self.con_o3.close()
        super().close()


class ClienteE1R0(cliente_e1.ClienteE1Real):
    """ClienteE1Real (reintentos del ratchet) con la guardia."""

    def __init__(self, *, guardia: Guardia, **kw):
        super().__init__(**kw)
        self.guardia = guardia

    def create(self, *, doc: str | None = None, **kwargs):
        llamada = self.guardia.antes("e1r", kwargs)
        h0, g0 = self.llamadas_hit, self.gasto_usd
        resp = super().create(doc=doc, **kwargs)
        hit = self.llamadas_hit > h0
        self.guardia.despues(llamada, resp, hit, self.gasto_usd - g0, "cache_local" if hit else "api")
        return resp


# ----------------------------- reuso de O3: sembrar ------------------------ #
COLUMNAS = ("key", "namespace", "domain", "created_at", "model", "input_tokens", "output_tokens",
            "cache_read_tokens", "cache_write_tokens", "stop_reason", "thinking_enabled", "request_json", "raw_json")


def sembrar_o3(db_e3: Path, esp: dict) -> dict:
    """Copia las 20 filas de la base de O3 a la base de E3 de la corrida (INSERT OR IGNORE, columnas tal cual; el
    access_log de O3 no se copia). Controla: las 20 claves de O3 son las 20 claves de verificación esperadas; antes,
    cada una está ausente o presente con la misma fila; después, las 20 presentes e iguales a las de O3, y la base con
    las filas de antes más las insertadas."""
    claves = {v["clave"] for v in esp["verificacion"].values()}
    co = abrir_ro(DB_O3)
    try:
        filas = {r[0]: r for r in co.execute(f"select {', '.join(COLUMNAS)} from cache")}
    finally:
        co.close()
    if set(filas) != claves:
        raise FrenoR0("las claves de la base de O3 no son las 20 claves de verificación esperadas")
    lc._connect(Path(db_e3)).close()        # el esquema de llm_cache, si la base es nueva (base propia de R0)
    con = sqlite3.connect(str(db_e3))
    try:
        con.execute("PRAGMA busy_timeout=5000;")
        antes_n = con.execute("select count(*) from cache").fetchone()[0]
        ya = {}
        for k in claves:
            r = con.execute(f"select {', '.join(COLUMNAS)} from cache where key = ?", (k,)).fetchone()
            if r is not None:
                ya[k] = r
        if any(ya[k] != filas[k] for k in ya):
            raise FrenoR0("una clave de O3 ya está en la base de E3 con otra fila")
        nuevas = [filas[k] for k in sorted(claves - set(ya))]
        con.executemany(f"insert or ignore into cache ({', '.join(COLUMNAS)}) values "
                        f"({', '.join('?' * len(COLUMNAS))})", nuevas)
        con.commit()
        despues_n = con.execute("select count(*) from cache").fetchone()[0]
        iguales = sum(1 for k in claves if con.execute(f"select {', '.join(COLUMNAS)} from cache where key = ?",
                                                       (k,)).fetchone() == filas[k])
    finally:
        con.close()
    res = {"hora": ahora(), "base": rel(db_e3), "filas_antes": antes_n, "ya_presentes": len(ya),
           "insertadas": len(nuevas), "filas_despues": despues_n, "iguales_a_o3": iguales}
    if despues_n != antes_n + len(nuevas) or iguales != 20:
        raise FrenoR0(f"sembrado de O3: {json.dumps(res, ensure_ascii=False)}")
    return res


# ----------------------------- carpeta de trabajo y corrida ---------------- #
def preparar_trabajo(trabajo: Path, ctx: dict) -> None:
    """extracciones_e1.jsonl de cada TO con las líneas del intento 0 de sus unidades, byte a byte, en orden documental.
    Si ya existe (reanudación), tiene que ser igual."""
    if (trabajo / ANEXO).exists():
        raise FrenoR0("esta carpeta de trabajo ya se anexó: no se vuelve a correr sobre ella")
    for to, cids in ctx["por_to"].items():
        tdir = trabajo / to
        tdir.mkdir(parents=True, exist_ok=True)
        txt = "".join(ctx["lineas"][cid] for cid in cids)
        p = tdir / "extracciones_e1.jsonl"
        if p.exists():
            if p.read_text(encoding="utf-8") != txt:
                raise FrenoR0(f"{rel(p)} existe y no es el E1 del intento 0 de las unidades de {to}")
        else:
            p.write_text(txt, encoding="utf-8")


def resumen_corrida(trabajo: Path, ctx: dict) -> dict:
    out = {"por_unidad": {}, "estados": {}, "por_to": {}}
    for to, cids in ctx["por_to"].items():
        fin = trabajo / to / "finales.jsonl"
        lineas = jl(fin) if fin.exists() else []
        cuenta = Counter(r["chunk_id"] for r in lineas)
        for r in lineas:
            out["por_unidad"][r["chunk_id"]] = {"to": to, "estado": r["estado"], "n_reintentos": r["n_reintentos"],
                                                "residuales": len(r.get("residuales") or []),
                                                "con_validacion_final": r.get("validacion_final") is not None}
        out["por_to"][to] = dict(Counter(r["estado"] for r in lineas))
        out.setdefault("lineas_por_unidad_distintas_de_1", {}).update(
            {k: v for k, v in cuenta.items() if v != 1})
        out.setdefault("ajenas_a_la_lista", []).extend(sorted(set(cuenta) - set(cids)))
    out["estados"] = dict(Counter(v["estado"] for v in out["por_unidad"].values()))
    out["unidades_con_registro_final"] = len(out["por_unidad"])
    return out


def correr(a, ctx: dict, previos: dict) -> int:
    esp = json.loads(a.esperados.read_text(encoding="utf-8"))
    trabajo = a.trabajo
    trabajo.mkdir(parents=True, exist_ok=True)
    preparar_trabajo(trabajo, ctx)
    esperas: list[float] = []
    if a.seco:
        # sin red y sin clave: el transporte simulado reemplaza al de la API; los usage van a la carpeta de trabajo y
        # las esperas del reintento de API del runner se registran en lugar de dormir
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:9"
        cliente_e3.CACHE_USAGE_LOG = cliente_e1.CACHE_USAGE_LOG = trabajo / "cache_usage_seco.jsonl"
        RC.time.sleep = esperas.append
        if a.seco_alterar_esperado:
            esp = copy.deepcopy(esp)
            esp["verificacion"][a.seco_alterar_esperado]["sha_mensaje"] = "0" * 64
    else:
        from dotenv import load_dotenv      # noqa: PLC0415 — como runner_corpus.main()
        load_dotenv(RC.EVAL_DIR / ".env")
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            print(f"ANTHROPIC_API_KEY ausente (esperada en {rel(RC.EVAL_DIR / '.env')})")
            return 1
    registro = {"inicio": ahora(), "modo": "seco" if a.seco else "correr", "escenario": a.escenario,
                "tope_usd": a.tope, "reuso_o3": a.reuso_o3, "db_e3": rel(a.db_e3), "db_e1r": rel(a.db_e1r),
                "trabajo": rel(trabajo), "salida_t0": rel(ctx["salida_t0"]),
                "controles_previos": previos}
    if a.reuso_o3 == "sembrar":
        registro["sembrado_o3"] = sembrar_o3(a.db_e3, esp)
    guardian = RC.PresupuestoCompartido(a.tope, trabajo / PRESUPUESTO)
    guardia = Guardia(ctx, esp, a.reuso_o3, trabajo)
    cli_e3 = ClienteE3R0(**RC.P_E3, tope_usd=a.tope, run_label="R0_E3_01_e3", db_path=a.db_e3, guardian=guardian,
                         guardia=guardia, db_o3_leer=DB_O3 if a.reuso_o3 == "leer" else None)
    cli_e1r = ClienteE1R0(**RC.P_E1, tope_usd=a.tope, run_label="R0_E3_01_reintentos_e1", db_path=a.db_e1r,
                          guardian=guardian, prefijo_hash=RC.PERFIL.prefijo_hash_para_namespace,
                          transmision=RC.PERFIL_R2, guardia=guardia)
    transporte = None
    if a.seco:
        import seco_r0                      # noqa: PLC0415 — r0/seco_r0.py, solo en la corrida en seco
        transporte = seco_r0.Transporte(guardia, ctx, a.escenario)
        cli_e3.cache._real = transporte
        cli_e1r._real = transporte
        cli_e1r.cache._real = transporte
    estado = RC.Estado(trabajo)
    codigo, freno = 0, None
    try:
        for to in RC.TOS_ORDEN:
            if to not in ctx["por_to"] or estado.fase_cerrada(f"{to}:e3"):
                continue
            RC.fase_e3(to, cli_e3, cli_e1r, estado, trabajo, None, a.abortar_tras, None)
    except (RC.Freno, cliente_e1.TopeExcedido, cliente_e3.TopeExcedido, FrenoR0) as e:
        freno, codigo = f"{type(e).__name__}: {e}", 3
        print(f"\nFRENO: {freno}", flush=True)
        estado.persistir()
    finally:
        registro.update({"fin": ahora(), "freno": freno, "gasto_compartido_usd": round(guardian.gasto_usd, 6),
                         "cliente_e3": cli_e3.resumen(), "cliente_e1_reintentos": cli_e1r.resumen(),
                         "leidas_de_o3": cli_e3.leidas_de_o3, "llamadas_guardia": guardia.n,
                         "esperas_registradas_s": esperas if a.seco else None,
                         "transporte_simulado": transporte.resumen() if transporte else None,
                         "corrida": resumen_corrida(trabajo, ctx)})
        cli_e3.close()
        cli_e1r.close()
        (trabajo / RESUMEN).write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: registro[k] for k in ("freno", "gasto_compartido_usd", "leidas_de_o3", "llamadas_guardia")}
                     | {"estados": registro["corrida"]["estados"]}, ensure_ascii=False), flush=True)
    return codigo


# ----------------------------- anexo a la salida de la tanda 0 ------------- #
def anexar(a, ctx: dict) -> int:
    trabajo, salida_t0 = a.trabajo, a.salida_t0
    if (trabajo / ANEXO).exists():
        raise FrenoR0("esta carpeta de trabajo ya se anexó")
    est = RC.Estado(trabajo)
    if not all(est.fase_cerrada(f"{to}:e3") for to in ctx["por_to"]):
        raise FrenoR0("la corrida no cerró la fase E3 de todos los TOs")
    r = resumen_corrida(trabajo, ctx)
    if r["unidades_con_registro_final"] != 20 or r["lineas_por_unidad_distintas_de_1"] or r["ajenas_a_la_lista"]:
        raise FrenoR0(f"la carpeta de trabajo no tiene un registro final por unidad de las 20: {r}")
    plan = []
    for to in ctx["por_to"]:
        for nombre in ARCHIVOS_ANEXO:
            src = trabajo / to / nombre
            if not src.exists() or not src.read_bytes():
                continue
            nuevo = src.read_bytes()
            if not nuevo.endswith(b"\n") or any(json.loads(x)["chunk_id"] not in ctx["unidades"]
                                                 for x in nuevo.decode("utf-8").splitlines() if x.strip()):
                raise FrenoR0(f"{rel(src)}: renglones ajenos a las 20 o sin salto final")
            dst = salida_t0 / to / nombre
            antes = dst.read_bytes() if dst.exists() else b""
            if antes and not antes.endswith(b"\n"):
                raise FrenoR0(f"{rel(dst)} no termina en salto de línea")
            plan.append((to, nombre, dst, antes, nuevo))
    registro = {"hora": ahora(), "salida_t0": rel(salida_t0), "trabajo": rel(trabajo), "archivos": []}
    for to, nombre, dst, antes, nuevo in plan:
        tmp = dst.with_suffix(dst.suffix + ".tmp_r0")
        tmp.write_bytes(antes + nuevo)
        os.replace(tmp, dst)
        despues = dst.read_bytes()
        ok = despues == antes + nuevo
        registro["archivos"].append({"to": to, "archivo": nombre, "existia": bool(antes),
                                     "sha256_antes": sha_b(antes) if antes else None, "sha256_despues": sha_b(despues),
                                     "renglones_agregados": nuevo.count(b"\n"), "igual_a_antes_mas_lo_nuevo": ok})
        if not ok:
            raise FrenoR0(f"{rel(dst)}: el archivo no quedó igual a su versión anterior más los renglones nuevos")
    (trabajo / ANEXO).write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"archivos": len(registro["archivos"]),
                      "renglones": sum(x["renglones_agregados"] for x in registro["archivos"])}, ensure_ascii=False))
    return 0


# ----------------------------- main --------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--esperados-salida", type=Path, help="escribe los valores esperados y termina (sin red)")
    g.add_argument("--seco", action="store_true")
    g.add_argument("--correr", action="store_true")
    g.add_argument("--anexar", action="store_true")
    ap.add_argument("--tope", type=float, default=None)
    ap.add_argument("--reuso-o3", choices=("sembrar", "leer", "no"), default=None)
    ap.add_argument("--trabajo", type=Path, default=TRABAJO)
    ap.add_argument("--salida-t0", type=Path, default=SALIDA_T0)
    ap.add_argument("--esperados", type=Path, default=ESPERADOS)
    ap.add_argument("--db-e3", type=Path, default=cliente_e3.DB_PATH)
    ap.add_argument("--db-e1r", type=Path, default=RC.DB_REINTENTOS_E1)
    ap.add_argument("--abortar-tras", type=int, default=None, help="sys.exit(9) tras N unidades (fase_e3)")
    ap.add_argument("--escenario", default=None, help="solo --seco: las respuestas del transporte simulado")
    ap.add_argument("--seco-alterar-esperado", default=None, help="solo --seco: altera el sha esperado de una unidad")
    a = ap.parse_args()
    try:
        ctx = cargar_contexto(a.salida_t0)
        if a.esperados_salida:
            esp = calcular_esperados(ctx)
            a.esperados_salida.write_text(json.dumps(esp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(json.dumps(esp["reparto_con_o3"], ensure_ascii=False))
            return 0
        if a.anexar:
            return anexar(a, ctx)
        if a.tope is None or not 0 < a.tope <= TOPE_MAXIMO:
            print(f"--tope es obligatorio y va de 0 a {TOPE_MAXIMO} (enmienda 7)")
            return 2
        if a.reuso_o3 is None:
            print("--reuso-o3 es obligatorio: sembrar, leer o no (pregunta b, la decide la autora)")
            return 2
        if a.seco:
            if a.escenario is None:
                print("--seco exige --escenario")
                return 2
            reales = {cliente_e3.DB_PATH.resolve(), RC.DB_REINTENTOS_E1.resolve()}
            if a.db_e3.resolve() in reales or a.db_e1r.resolve() in reales:
                print("--seco no escribe en las bases del pipeline: pasá copias en --db-e3 y --db-e1r")
                return 2
        elif a.escenario or a.seco_alterar_esperado:
            print("--escenario y --seco-alterar-esperado son solo de --seco")
            return 2
        if a.reuso_o3 != "no" and sha_b(DB_O3.read_bytes()) != DB_O3_SHA256:
            raise FrenoR0("la base de O3 no tiene el sha256 sellado")
        previos = controles_previos(ctx, a.esperados)
        print(f"R0 | {'seco' if a.seco else 'correr'} | tope USD {a.tope} | reuso de O3: {a.reuso_o3} | "
              f"inicio {ahora()} | controles previos: {json.dumps(previos, ensure_ascii=False)}", flush=True)
        return correr(a, ctx, previos)
    except FrenoR0 as e:
        print(f"\nFRENO: {e}", flush=True)
        return 3


if __name__ == "__main__":
    sys.exit(main())
