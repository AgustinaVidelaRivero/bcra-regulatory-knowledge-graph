"""
runner_corpus.py — Corrida de UN CORPUS DECLARADO POR MANIFIESTO por el
pipeline E1→E3 con la arquitectura enmendada (enmienda 01) y la política
laudada A+B. Extiende los runners de la mini-recalibración enm01 con:
multi-TO, reanudación idempotente por unidad persistida, checkpoints
intra-TO, tope global duro y freno por proyección.

U-B5.1: los TOs, el orden, la salida de E0, los límites (tope/estimados/
checkpoints/chequeos de hits) y el modo del censo (con o sin oráculo) salen
del manifiesto de corpus (--manifiesto; default: manifiestos/
desarrollo_5tos.json, cuyos valores son EXACTAMENTE los que este módulo
tenía cableados — paridad verificada en selftest_manifiesto.py). Modelos y
precios siguen siendo materia de la autorización de cada corrida (laudo
D-b del freno 1) y quedan como constantes de este módulo.

Autorización vigente (FASE B de la unidad "corrida del corpus completo"):
  - TOPE DURO GLOBAL: USD 48,50 (estimación FASE A: USD 34,59 × 1,4).
  - E1 (extractor + reintentos): claude-haiku-4-5 — 1,00/5,00/1,25/0,10 USD/MTok.
  - E3 (verificador): claude-sonnet-5 — 2,00/10,00/2,50/0,20 USD/MTok.
  - Orden: pro → cla → ric → cap → ext; SECUENCIAL dentro de cada TO (D4).
  - Freno por proyección al cierre de cada TO + checkpoints intra-TO cada
    150 unidades en cap y ext.
  - En pro: la fase E1 y las verificaciones E3 base deben ser ≈100% hits de
    la caché local (mismos requests que enm01). E1 con gasto > 0,01 ⇒ FRENO.
    Los ciclos de reintento pueden pagarse de nuevo (la política A+B cambia
    el feedback respecto de enm01: solo bloqueantes); techo declarado
    USD 1,00 para la fase E3 de pro ⇒ si se supera, FRENO.

Reanudación idempotente:
  - E1: extracciones_e1.jsonl es append-only; al relanzar se saltean las
    unidades con registro persistido sin error (last-wins por chunk_id) y se
    re-llaman SOLO las erradas/faltantes. La caché local (never-pay-twice)
    hace que nada ya pagado se vuelva a pagar.
  - E3: finales.jsonl es append-only; una unidad con expediente persistido
    (cualquier estado terminal) se saltea entera. Si el proceso muere a mitad
    de un ciclo de ratchet, el ciclo se re-corre completo al relanzar y sus
    llamadas ya pagadas son hits de caché; veredictos.jsonl puede quedar con
    filas duplicadas de esa unidad (se dedupea al agregar, declarado).
  - Contabilidad: estado_corpus.json se reescribe (temp+rename) tras cada
    unidad; el gasto de un proceso muerto entre la llamada y la escritura se
    subestima como máximo en 1 unidad (~USD 0,03), declarado.

La cola humana NO ingresa al grafo (validacion_final=None — principio "nunca
ingreso silencioso"): sus unidades quedan contabilizadas como rechazadas en el
fan-in de E2 y diagnosticadas en el censo.

Uso:
  .venv/bin/python3 runner_corpus.py --autorizado-tope 48.50            # corrida real
  .venv/bin/python3 runner_corpus.py --stub --salida <dir> [--limite N] # prueba offline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REX = AQUI.parent
sys.path.insert(0, str(REX / "e1_extractor"))
sys.path.insert(0, str(REX / "e3_verificador"))
sys.path.insert(0, str(REX / "e2_reduce"))
# U-REEXT-T0, T2-bis: correr_e0 (tercer escalón y partición por corte del perfil r2) se importa desde e0_chunking
sys.path.insert(0, str(REX / "e0_chunking"))
sys.path.insert(0, str(REX))

import comun_e1                     # noqa: E402
import prompt_e1                    # noqa: E402
import perfil_e1                    # noqa: E402  (U-CABLE-V3: perfiles E1)
import cliente_e1                   # noqa: E402
import validador_e1                 # noqa: E402
import comun_e3                     # noqa: E402
import prompt_e3                    # noqa: E402
import cliente_e3                   # noqa: E402
import ratchet_e3                   # noqa: E402
import e2_lib                       # noqa: E402
import manifiesto_corpus            # noqa: E402

# --------------------- constantes de autorización por corrida ------------ #
# Techo del reintento del RATCHET E3 (re-extracción con feedback). Se
# MANTIENE en 16.384 (U-B5.3 decisión 3: cambiarlo alteraría los kwargs de
# requests de unidades que no cortan y rompería never-pay-twice). El remedio
# de fondo de los cortes por max_tokens es el reintento por corte de la fase
# E1 con 32.768 (cliente_e1.MAX_TOKENS_REINTENTO_CORTE, U-B5.3 decisión 1).
MAX_TOKENS_REINTENTO = 16384

MODEL_E1 = "claude-haiku-4-5"
P_E1 = dict(precio_in_por_mtok=1.00, precio_out_por_mtok=5.00,
            precio_cache_write_por_mtok=1.25, precio_cache_read_por_mtok=0.10)
MODEL_E3 = "claude-sonnet-5"
P_E3 = dict(precio_in_por_mtok=2.00, precio_out_por_mtok=10.00,
            precio_cache_write_por_mtok=2.50, precio_cache_read_por_mtok=0.20)

EVAL_DIR = comun_e3.REPO / "data" / "experiment" / "evaluacion"
DB_REINTENTOS_E1 = REX / "e3_verificador" / "cache" / "e1_reintentos.db"
# U-R2-CODIGO, R2.b: archivo compañero de finales.jsonl con el crudo de los
# reintentos de E3 (lo escribe fase_e3; lo leen crudos_reintento_e3 y
# r2_codigo/lector_reintentos_e3)
REINTENTOS_E3 = "reintentos_e3.jsonl"

# --------------------- configuración por manifiesto (U-B5.1) ------------- #
MANIFIESTO_DEFAULT = REX / "manifiestos" / "desarrollo_5tos.json"

MAN = None
TOS_ORDEN: tuple[str, ...] = ()
TOPE_GLOBAL_USD: float = 0.0
MARGEN_UNIDAD_USD: float = 0.0      # margen pre-unidad (precedente enm01)
ESTIMADO_USD: dict[str, dict] = {}
ESTIMADO_TOTAL_USD: float = 0.0
CHECKPOINT_CADA: dict[str, int] = {}
CHEQUEOS_HITS: list[dict] = []
E0_DIR: Path = comun_e1.E0_SALIDA_ENM01
CENSO_ORACULO_ARG = None            # None = cargar del e0_dir; o SIN_ORACULO
LIMITACIONES: dict | None = None
PERFIL = None                       # U-CABLE-V3: perfil E1 del manifiesto


def configurar(man) -> None:
    """Fija el estado de módulo desde un manifiesto cargado. Se invoca al
    importar (manifiesto de desarrollo — valores idénticos a los cableados
    históricos) y de nuevo en main() con el --manifiesto de la corrida.
    U-CABLE-V3: acá se construye el PERFIL de extracción declarado por el
    manifiesto — los candados del perfil v3 (sha/hash del sello) corren en
    este punto, antes de toda llamada."""
    global MAN, TOS_ORDEN, TOPE_GLOBAL_USD, MARGEN_UNIDAD_USD, ESTIMADO_USD, \
        ESTIMADO_TOTAL_USD, CHECKPOINT_CADA, CHEQUEOS_HITS, E0_DIR, \
        CENSO_ORACULO_ARG, LIMITACIONES, PERFIL
    MAN = man
    PERFIL = perfil_e1.perfil(man.perfil_e1)
    TOS_ORDEN = tuple(man.orden_corrida)
    lim = man.limites
    TOPE_GLOBAL_USD = lim["tope_global_usd"]
    MARGEN_UNIDAD_USD = lim["margen_unidad_usd"]
    ESTIMADO_USD = lim["estimado_usd"]
    ESTIMADO_TOTAL_USD = round(
        sum(f["e1"] + f["e3"] for f in ESTIMADO_USD.values()), 3)
    CHECKPOINT_CADA = dict(lim["checkpoint_cada"])
    CHEQUEOS_HITS = list(lim["chequeos_hits"])
    E0_DIR = man.e0_salida
    CENSO_ORACULO_ARG = None if man.tiene_oraculo else e2_lib.SIN_ORACULO
    LIMITACIONES = man.limitaciones_e0()


configurar(manifiesto_corpus.cargar(MANIFIESTO_DEFAULT))


class Freno(RuntimeError):
    pass


class IdsRepetidos(RuntimeError):
    """U-R2-CODIGO, R2 (BKL-0037): la E0 trae dos o más chunks con el mismo id
    en un TO. Los registros de E1 y E3 se indexan por chunk_id con last-wins
    (`cargar_jsonl_last_wins`) y la compactación escribe uno por id: con ids
    repetidos se perdería sin aviso una extracción de cada par. El runner se
    detiene antes de llamar a la API."""


def chunks_sin_ids_repetidos(chunks: list[dict], to: str) -> list[dict]:
    """Devuelve los chunks tal cual si sus ids son únicos; si no, frena con
    IdsRepetidos. Con una E0 sin ids repetidos (la de r1 y la de la tanda 0)
    el comportamiento es el de siempre."""
    conteo = Counter(c["id"] for c in chunks)
    repetidos = sorted(k for k, v in conteo.items() if v > 1)
    if repetidos:
        raise IdsRepetidos(
            f"{to}: {len(repetidos)} ids de chunk repetidos en la E0 "
            f"({sum(conteo[k] - 1 for k in repetidos)} chunks de más; p. ej. "
            f"{repetidos[:3]}): el runner se detiene en lugar de pisar "
            f"registros (BKL-0037; e0-r2 los desambigua)")
    return chunks


class PresupuestoCompartido:
    """Guardián de presupuesto COMÚN a todos los clientes LLM de una corrida
    (U-B5.3 decisión 8): hasta esta unidad cada CachingClient cortaba solo por
    su tope propio, y una fase con dos clientes (E3 + reintentos E1, ambos
    construidos con tope_usd = remanente) podía comprometer hasta el doble del
    remanente antes del chequeo pre-unidad. Cada miss se registra acá; el
    chequeo pre-llamada de cada cliente proyecta sobre el gasto COMBINADO y el
    freno es duro (TopeExcedido del cliente que lo detecta, antes de tocar la
    red). Estado persistido con escritura atómica (temp+rename) tras cada
    registro: reconstruir sobre la misma salida reanuda con el gasto previo
    cargado. El tope configurado por la corrida MANDA sobre el del archivo
    (la diferencia se reporta, no se adopta)."""

    def __init__(self, tope_usd: float, path: Path):
        if tope_usd <= 0:
            raise ValueError("tope compartido debe ser positivo")
        self.tope_usd = tope_usd
        self.path = Path(path)
        self.gasto_usd = 0.0
        if self.path.exists():
            d = json.loads(self.path.read_text(encoding="utf-8"))
            self.gasto_usd = float(d["gasto_usd"])
            if d.get("tope_usd") != tope_usd:
                print(f"[presupuesto compartido] tope persistido "
                      f"{d.get('tope_usd')} ≠ configurado {tope_usd}: manda "
                      f"el configurado", flush=True)

    def excedido(self, proyeccion_usd: float) -> bool:
        return self.gasto_usd + proyeccion_usd > self.tope_usd

    def registrar(self, delta_usd: float) -> None:
        self.gasto_usd += delta_usd
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"tope_usd": self.tope_usd,
                                   "gasto_usd": round(self.gasto_usd, 6)},
                                  ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, self.path)


# ----------------------------- stubs offline ----------------------------- #
class _StubUsage:
    input_tokens = 0
    output_tokens = 0
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _StubResp:
    def __init__(self, tool_input, nombre_tool):
        class B:
            type = "tool_use"
        b = B()
        b.name = nombre_tool
        b.input = tool_input
        self.content = [b]
        self.stop_reason = "tool_use"
        self.usage = _StubUsage()


class StubE1Corpus:
    """Stub E1 para el selftest del runner: extracción mínima válida por
    chunk. Interfaz dual: .create(doc=..., **kw) y .messages.create(**kw)."""

    def __init__(self):
        self.messages = self
        self.llamadas = 0
        self.llamadas_hit = 0
        self.gasto_usd = 0.0
        self.chunk_ids_llamados: list[str] = []
        # U-CABLE-V3 (solo diagnóstico de selftest): sha256 del texto del
        # system de cada request recibido. No entra en resumen() ni en ningún
        # artefacto persistido — la huella golden no lo ve.
        self.system_shas: list[str] = []

    def create(self, doc=None, **kwargs):
        self.llamadas += 1
        sysb = kwargs.get("system")
        if isinstance(sysb, list) and sysb and isinstance(sysb[0], dict):
            import hashlib
            self.system_shas.append(
                hashlib.sha256(sysb[0].get("text", "").encode("utf-8")).hexdigest())
        msg = kwargs["messages"][0]["content"]
        # el punto propio viene en el mensaje canónico; lo recuperamos del
        # renglón "Punto del chunk:" (hijo) / "Unidad de origen:" (mini)
        punto = None
        for linea in msg.splitlines():
            if linea.startswith(("Punto del chunk:", "Unidad de origen:")):
                punto = linea.split(":", 1)[1].strip().split(" ", 1)[0]
                break
        tool_input = {
            "entities": [{"local_id": "e1", "type": "Obligacion",
                          "label": f"obligacion stub {punto}",
                          "punto": punto, "properties": {}}],
            "relations": [],
            "omisiones_no_prosa": [],
        }
        self.chunk_ids_llamados.append(punto)
        return _StubResp(tool_input, prompt_e1.NOMBRE_TOOL)

    def resumen(self):
        return {"llamadas": self.llamadas, "hits_cache_local": self.llamadas_hit,
                "gasto_usd_real": 0.0, "stub": True}

    def close(self):
        pass


class StubE3Corpus:
    """Stub E3: siempre completo_ok (el flujo de ratchet con faltantes ya
    está cubierto por selftest_e3; acá se prueba la mecánica del runner)."""

    def __init__(self):
        self.messages = self
        self.llamadas = 0
        self.llamadas_hit = 0
        self.gasto_usd = 0.0

    def create(self, doc=None, **kwargs):
        self.llamadas += 1
        return _StubResp({"veredicto": "completo_ok", "faltantes": []},
                         prompt_e3.NOMBRE_TOOL)

    def resumen(self):
        return {"llamadas": self.llamadas, "stub": True}

    def close(self):
        pass


# ----------------------------- persistencia ------------------------------ #
def cargar_jsonl_last_wins(path: Path) -> dict[str, dict]:
    """chunk_id → último registro persistido (dedup last-wins)."""
    regs: dict[str, dict] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    r = json.loads(linea)
                    regs[r["chunk_id"]] = r
    return regs


def append_jsonl(path: Path, reg: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


class Estado:
    """Ledger global de gasto + fase actual; reescritura atómica por unidad."""

    def __init__(self, salida: Path):
        self.path = salida / "estado_corpus.json"
        if self.path.exists():
            self.d = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.d = {"fases_cerradas": {}, "fase_actual": None,
                      "tope_global_usd": TOPE_GLOBAL_USD,
                      "estimado_total_usd": ESTIMADO_TOTAL_USD}

    def persistir(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, self.path)

    def abrir_fase(self, key: str) -> float:
        """Devuelve el gasto previo de esta fase (de intentos anteriores)."""
        fa = self.d.get("fase_actual")
        previo = 0.0
        if fa and fa["key"] == key:
            previo = fa.get("gasto_previo_usd", 0.0) + fa.get("gasto_proceso_usd", 0.0)
        self.d["fase_actual"] = {"key": key, "gasto_previo_usd": round(previo, 6),
                                 "gasto_proceso_usd": 0.0, "unidades_hechas": 0}
        self.persistir()
        return previo

    def tick(self, gasto_proceso: float, unidades: int) -> None:
        fa = self.d["fase_actual"]
        fa["gasto_proceso_usd"] = round(gasto_proceso, 6)
        fa["unidades_hechas"] = unidades
        self.persistir()

    def cerrar_fase(self, key: str, resumen: dict) -> None:
        fa = self.d["fase_actual"]
        assert fa and fa["key"] == key
        gasto = fa["gasto_previo_usd"] + fa["gasto_proceso_usd"]
        self.d["fases_cerradas"][key] = {"gasto_usd": round(gasto, 6),
                                         "resumen": resumen}
        self.d["fase_actual"] = None
        self.persistir()

    def gasto_global(self) -> float:
        g = sum(f["gasto_usd"] for f in self.d["fases_cerradas"].values())
        fa = self.d.get("fase_actual")
        if fa:
            g += fa["gasto_previo_usd"] + fa["gasto_proceso_usd"]
        return g

    def fase_cerrada(self, key: str) -> bool:
        return key in self.d["fases_cerradas"]

    def reabrir_fase(self, key: str) -> bool:
        """U-REEXT-T0, T2-bis (--reabrir-fase): saca la fase de fases_cerradas y la deja como fase_actual con su gasto
        en gasto_previo_usd; abrir_fase lo conserva y cerrar_fase la vuelve a cerrar con el gasto previo más el nuevo.
        La reapertura queda en `reaperturas`, con el resumen de la fase cerrada. No hace nada si la fase no está
        cerrada (ya reabierta, o en curso tras un corte) o si hay otra fase en curso, cuyo gasto no se pisa."""
        if key not in self.d["fases_cerradas"] or self.d.get("fase_actual") is not None:
            return False
        cerrada = self.d["fases_cerradas"].pop(key)
        self.d["fase_actual"] = {"key": key, "gasto_previo_usd": cerrada["gasto_usd"],
                                 "gasto_proceso_usd": 0.0, "unidades_hechas": 0}
        self.d.setdefault("reaperturas", []).append({"key": key, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                                     "fase_cerrada": cerrada})
        self.persistir()
        return True


# ----------------------------- proyección/freno -------------------------- #
def proyeccion(estado: Estado, fase_key: str | None, frac: float) -> dict:
    """Proyección del total con factor conservador (ratio real/estimado sobre
    lo YA PAGADO, excluyendo pro — cuyos hits distorsionarían a la baja)."""
    real_global = estado.gasto_global()
    est_corrido = est_corrido_pagado = real_pagado = 0.0
    for key, f in estado.d["fases_cerradas"].items():
        to, fase = key.split(":")
        est = ESTIMADO_USD[to][fase]
        est_corrido += est
        if to != "pro":
            est_corrido_pagado += est
            real_pagado += f["gasto_usd"]
    if fase_key:
        to, fase = fase_key.split(":")
        est = ESTIMADO_USD[to][fase] * frac
        est_corrido += est
        fa = estado.d["fase_actual"]
        if to != "pro" and fa:
            est_corrido_pagado += est
            real_pagado += fa["gasto_previo_usd"] + fa["gasto_proceso_usd"]
    ratio = (real_pagado / est_corrido_pagado) if est_corrido_pagado > 0.5 else 1.0
    factor = max(1.0, ratio)
    est_restante = max(0.0, ESTIMADO_TOTAL_USD - est_corrido)
    proy = real_global + factor * est_restante
    return {"gasto_real_global_usd": round(real_global, 4),
            "estimado_corrido_usd": round(est_corrido, 4),
            "ratio_real_vs_estimado_pagado": round(ratio, 4),
            "factor_freno": round(factor, 4),
            "estimado_restante_usd": round(est_restante, 4),
            "proyeccion_total_usd": round(proy, 4),
            "tope_global_usd": TOPE_GLOBAL_USD}


def checkpoint(salida: Path, estado: Estado, to: str, fase: str,
               n: int, total: int, etiqueta: str) -> dict:
    p = proyeccion(estado, f"{to}:{fase}", n / total if total else 1.0)
    reg = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "to": to, "fase": fase, "unidades": f"{n}/{total}",
           "etiqueta": etiqueta, **p}
    cdir = salida / "checkpoints"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / f"checkpoint_{to}_{fase}_{etiqueta}.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "ultimo_checkpoint.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"CHECKPOINT [{to}:{fase} {n}/{total}] gasto=USD "
          f"{p['gasto_real_global_usd']:.2f} proyección=USD "
          f"{p['proyeccion_total_usd']:.2f} (tope {TOPE_GLOBAL_USD})", flush=True)
    if p["proyeccion_total_usd"] > TOPE_GLOBAL_USD:
        raise Freno(f"proyección USD {p['proyeccion_total_usd']:.2f} supera el "
                    f"tope global USD {TOPE_GLOBAL_USD:.2f} en {to}:{fase} {n}/{total}")
    return reg


# ----------------------------- fase E1 ----------------------------------- #
# Error REINTENTABLE dentro del pase (U-B5.3 decisión 5): el marcador que el
# runner pre-B5.3 dejaba al cortar sin reintentar. El código nuevo reintenta
# en el acto y nunca lo escribe; puede aparecer en jsonl de corridas viejas
# reanudadas (esas unidades se re-llaman al reanudar: no están en hechas_ok).
ERROR_REINTENTABLE = "max_tokens_hit"


def reintentables_pendientes(regs: dict[str, dict]) -> list[str]:
    """chunk_ids con error reintentable en el último registro persistido: un
    pase NO se declara terminado con estos pendientes (decisión 5)."""
    return sorted(cid for cid, r in regs.items()
                  if r.get("error") == ERROR_REINTENTABLE)


# U-R2-CODIGO, R4.b (BKL-0030, solo con --perfil-r2): las unidades cuya
# extracción corta por max_tokens también en el reintento se parten con la
# mecánica de sub-chunking de E0 (correr_e0.particionar_por_corte) y se
# registran acá; en las fases siguientes las partes reemplazan a la unidad.
ARCHIVO_PARTICIONES_CORTE = "particiones_por_corte.json"
ERROR_PARTICIONADA = "particionada_por_corte"
# U-R2-CODIGO-2, C2, punto b: con el perfil r2, una salida con tool_use que validador_e1 rechaza entera por su
# forma recibe UN reintento con el mismo request en su propio namespace (cliente_e1.SUFIJO_REINTENTO_FORMA); si
# vuelve mal formada, la unidad queda con este error y va a la lista declarada (errores_definitivos y
# reintentos_forma del resumen de E1). Sin reparación determinística. Con el perfil r2b (U-PROMPT-R2, P5), el
# request del reintento cambia en la temperatura (kwargs_reintento_forma).
MOTIVOS_FORMA_E1 = ("salida_no_parseable", "salida_no_dict", "entities_o_relations_invalidos")
ERROR_FORMA_TRAS_REINTENTO = "salida_mal_formada_tras_reintento"
# U-PROMPT-R2, P3c-2 (decisión 6 de la autora sobre el FRENO P3c-1; solo con el perfil r2): tercer escalón del
# reintento por corte (cliente_e1.crear_con_reintento_corte, con techo cliente_e1.MAX_TOKENS_ESCALON_3_R2, por
# transmisión). Se dispara solo si el reintento corta y la unidad no se puede partir, o si la unidad es una parte. La
# unidad lleva la marca `escalon_3` en su registro de E1 y va al resumen de E1; U-REEXT-T0 las lee todas.
ERROR_TRAS_ESCALON_3 = "max_tokens_hit_tras_escalon_3"


def corresponde_escalon_3(c: dict) -> bool:
    """Tercer escalón: la unidad es una parte, o particionar_por_corte no la parte."""
    if "sub_chunk" in c:
        return True
    import correr_e0    # noqa: PLC0415 — e0_chunking, solo con el perfil r2
    return correr_e0.particionar_por_corte(c)[0] is None


def techo_reintento_ratchet(reg_e1: dict | None) -> int:
    """El techo del reintento del ratchet de E3 de una unidad: el de siempre o, si su E1 usó el tercer escalón (solo
    con el perfil r2), el del escalón, por el mismo cliente con transmisión."""
    if PERFIL_R2 and (reg_e1 or {}).get("escalon_3"):
        return cliente_e1.MAX_TOKENS_ESCALON_3_R2
    return MAX_TOKENS_REINTENTO


def kwargs_reintento_forma(kwargs: dict, perfil) -> dict:
    """El pedido del reintento por salida mal formada (punto b): el que produjo la salida, con su techo. Con un perfil
    de forma r2 (r2b; U-PROMPT-R2, P5), con la temperatura del reintento (prompt_r2b.kwargs_reintento_forma_r2b),
    para obtener una respuesta distinta; con los perfiles existentes, el mismo pedido, tal cual."""
    if not perfil_forma_r2(perfil):
        return kwargs
    import prompt_r2b    # noqa: PLC0415 — e1_extractor, solo con el perfil r2b
    return prompt_r2b.kwargs_reintento_forma_r2b(kwargs)


def motivo_forma_e1(val: dict | None) -> str | None:
    """Motivo de forma con que validador_e1 rechazó el chunk entero, o None."""
    return next((r["motivo"] for r in (val or {}).get("rechazos", [])
                 if r.get("nivel") == "chunk" and r.get("motivo") in MOTIVOS_FORMA_E1), None)


def _usage_e1(resp) -> dict:
    u = resp.usage
    return {"input_tokens": getattr(u, "input_tokens", 0) or 0,
            "output_tokens": getattr(u, "output_tokens", 0) or 0,
            "cache_write_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
            "cache_read_tokens": getattr(u, "cache_read_input_tokens", 0) or 0}


def salida_reintento_forma(resp, c: dict) -> tuple:
    """usage, stop_reason, tool input y validación de la respuesta de un reintento por forma."""
    tool_input = next((b.input for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    val = (validador_e1.validar_salida(tool_input, c, esquema=PERFIL.esquema).as_dict()
           if tool_input is not None else None)
    return _usage_e1(resp), getattr(resp, "stop_reason", None), tool_input, val


def mal_formada_tras_reintento(stop, tool_input, val: dict | None) -> bool:
    """La respuesta de un reintento por forma que deja la unidad con ERROR_FORMA_TRAS_REINTENTO."""
    return stop == "max_tokens" or tool_input is None or motivo_forma_e1(val) is not None


# U-REEXT-T0, T2-ter (decisión 2 de la autora sobre el FRENO T2-bis): la única excepción a «sin reparación
# determinística» de C2. Con el perfil r2b y agotados los reintentos por forma, una salida con `entities` lista y sin la
# clave `relations` sigue con `relations = []` si así validador_e1 la acepta; la unidad queda marcada (reparacion_forma)
# y va a E3, que reclama las relaciones que falten. Cualquier otra salida mal formada sigue el camino de siempre.
MOTIVO_REPARACION_FORMA = "relations_ausente"


def reparar_relations_ausente(stop, tool_input, c: dict) -> tuple | None:
    """(salida con relations = [], su validación) si la salida es la única forma reparable y así no tiene rechazos de
    chunk; si no, None."""
    if stop == "max_tokens" or not isinstance(tool_input, dict) or "relations" in tool_input \
            or not isinstance(tool_input.get("entities"), list):
        return None
    reparada = {**tool_input, "relations": []}
    val = validador_e1.validar_salida(reparada, c, esquema=PERFIL.esquema).as_dict()
    if any(r.get("nivel") == "chunk" for r in val.get("rechazos", [])):
        return None
    return reparada, val


def partes_por_corte(tdir: Path) -> dict[str, dict]:
    """id de la unidad partida → {partes, informe}, de particiones_por_corte.json
    (vacío si el archivo no existe: corrida sin particiones)."""
    p = Path(tdir) / ARCHIVO_PARTICIONES_CORTE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def chunks_con_partes(chunks: list[dict], tdir: Path) -> list[dict]:
    """La lista de chunks con cada unidad partida por corte reemplazada por sus
    partes, en el mismo lugar del orden documental. Sin particiones, la misma
    lista."""
    partes = partes_por_corte(tdir)
    if not partes:
        return chunks
    out = []
    for c in chunks:
        out.extend(partes[c["id"]]["partes"] if c["id"] in partes else [c])
    return out


def guardar_particion(tdir: Path, unidad: dict, partes: list[dict], informe: dict) -> None:
    todas = partes_por_corte(tdir)
    todas[unidad["id"]] = {"partes": partes, "informe": informe}
    (Path(tdir) / ARCHIVO_PARTICIONES_CORTE).write_text(
        json.dumps(todas, ensure_ascii=False, indent=1), encoding="utf-8")


def llamar_con_reintentos_api(fn, descripcion: str, max_intentos: int = 3):
    """Reintento ante errores transitorios de API (la corrida es desatendida).
    TopeExcedido NO se reintenta: es freno."""
    esperas = (20, 60, 180)
    ultimo = None
    for i in range(max_intentos):
        try:
            return fn(), None
        except (cliente_e1.TopeExcedido, cliente_e3.TopeExcedido):
            raise
        except Exception as e:  # noqa: BLE001 — transitorios de red/API
            ultimo = f"{type(e).__name__}: {e}"
            print(f"  error API en {descripcion} (intento {i+1}/{max_intentos}): "
                  f"{ultimo}", flush=True)
            if i < max_intentos - 1:
                time.sleep(esperas[i])
    return None, ultimo


def fase_e1(to: str, cliente, estado: Estado, salida: Path,
            limite: int | None, abortar_tras: int | None,
            checkpoint_cada: int | None) -> None:
    key = f"{to}:e1"
    tdir = salida / to
    tdir.mkdir(parents=True, exist_ok=True)
    jsonl = tdir / "extracciones_e1.jsonl"

    chunks = chunks_sin_ids_repetidos(comun_e1.cargar_chunks((to,), e0_dir=E0_DIR), to)
    if PERFIL_R2:
        chunks = chunks_con_partes(chunks, tdir)
    if limite:
        chunks = chunks[:limite]
    previos = cargar_jsonl_last_wins(jsonl)
    hechas_ok = {cid for cid, r in previos.items() if r.get("error") is None}
    pendientes = [c for c in chunks if c["id"] not in hechas_ok]
    # techo del reintento por corte: el del perfil r2 solo con --perfil-r2
    techo_corte = (cliente_e1.MAX_TOKENS_REINTENTO_CORTE_R2 if PERFIL_R2
                   else cliente_e1.MAX_TOKENS_REINTENTO_CORTE)
    print(f"[{key}] unidades={len(chunks)} ya_persistidas_ok={len(hechas_ok)} "
          f"pendientes={len(pendientes)}", flush=True)

    gasto_previo = estado.abrir_fase(key)
    errores_consecutivos = 0
    procesadas = len(hechas_ok)
    hechas_este_proceso = 0
    cola = list(pendientes)
    i_cola = 0
    while i_cola < len(cola):
        c = cola[i_cola]
        i_cola += 1
        if estado.gasto_global() + MARGEN_UNIDAD_USD > TOPE_GLOBAL_USD:
            raise Freno(f"tope global antes de {c['id']}: gasto USD "
                        f"{estado.gasto_global():.4f} + margen {MARGEN_UNIDAD_USD}")
        kwargs = PERFIL.build_request_kwargs(c, model=MODEL_E1)
        # U-B5.3 decisión 1: ante corte por max_tokens, UNA re-llamada en el
        # mismo pase con 32k (16k en el perfil r2, R4.b). El camino sin corte
        # pasa kwargs tal cual.
        escalon3 = False
        if PERFIL_R2:
            # P3c-2: con el perfil r2, el tercer escalón (los intentos cortados vuelven en orden)
            par, err = llamar_con_reintentos_api(
                lambda: cliente_e1.crear_con_reintento_corte(
                    cliente, kwargs, doc=c["archivo"], max_tokens_reintento=techo_corte,
                    escalon_3=lambda: corresponde_escalon_3(c)), c["id"])
            resp, cortados = par if par is not None else (None, ())
            cortado = cortados[0] if cortados else None
            escalon3 = len(cortados) == 2
        else:
            par, err = llamar_con_reintentos_api(
                lambda: cliente_e1.crear_con_reintento_corte(
                    cliente, kwargs, doc=c["archivo"], max_tokens_reintento=techo_corte), c["id"])
            resp, cortado = par if par is not None else (None, None)
        if resp is not None:
            usage = _usage_e1(resp)
            stop = getattr(resp, "stop_reason", None)
            tool_input = next((b.input for b in resp.content
                               if getattr(b, "type", None) == "tool_use"), None)
            if stop == "max_tokens":
                # el reintento también cortó: error DEFINITIVO contabilizado
                # (decisión 5) — nunca queda como reintentable pendiente.
                err = ERROR_TRAS_ESCALON_3 if escalon3 else "max_tokens_hit_tras_reintento"
            elif tool_input is None:
                err = f"no_tool_use stop_reason={stop}"
        else:
            usage, stop, tool_input = {"input_tokens": 0, "output_tokens": 0,
                                       "cache_write_tokens": 0,
                                       "cache_read_tokens": 0}, None, None
        val = (validador_e1.validar_salida(tool_input, c,
                                           esquema=PERFIL.esquema).as_dict()
               if tool_input is not None else None)
        reintento_forma = reparacion_forma = None
        if PERFIL_R2 and err is None and motivo_forma_e1(val) is not None:
            # punto b: el request que produjo la salida mal formada (con el techo de corte si lo hubo), tal cual; con el
            # perfil r2b (U-PROMPT-R2, P5), con la temperatura del reintento
            kwargs_forma = kwargs_reintento_forma(
                dict(kwargs, max_tokens=cliente_e1.MAX_TOKENS_ESCALON_3_R2) if escalon3
                else dict(kwargs, max_tokens=techo_corte) if cortado is not None else kwargs, PERFIL)
            reintento_forma = {"namespace": cliente_e1.namespace_e1(
                                   prefijo_hash=PERFIL.prefijo_hash_para_namespace,
                                   sufijo=cliente_e1.SUFIJO_REINTENTO_FORMA),
                               "motivo": motivo_forma_e1(val), "intento_1": cliente_e1.resumen_intento(resp)}
            resp_f, err_f = llamar_con_reintentos_api(
                lambda: cliente_e1.crear_reintento_forma(cliente, kwargs_forma, doc=c["archivo"]), c["id"])
            if resp_f is None:
                err = err_f
            else:
                usage, stop, tool_input, val = salida_reintento_forma(resp_f, c)
                if mal_formada_tras_reintento(stop, tool_input, val) and perfil_forma_r2(PERFIL):
                    # U-REEXT-T0, T2-bis: UN segundo reintento, el mismo pedido (con la temperatura del reintento) en
                    # el namespace -rforma2; el registro guarda la salida del primero en reintento_2.intento_2
                    reintento_forma["reintento_2"] = {
                        "namespace": cliente_e1.namespace_e1(prefijo_hash=PERFIL.prefijo_hash_para_namespace,
                                                             sufijo=cliente_e1.SUFIJO_REINTENTO_FORMA_2),
                        "motivo": motivo_forma_e1(val), "intento_2": cliente_e1.resumen_intento(resp_f)}
                    resp_f2, err_f2 = llamar_con_reintentos_api(
                        lambda: cliente_e1.crear_reintento_forma(cliente, kwargs_forma, doc=c["archivo"],
                                                                 sufijo=cliente_e1.SUFIJO_REINTENTO_FORMA_2), c["id"])
                    if resp_f2 is None:
                        err = err_f2
                    else:
                        usage, stop, tool_input, val = salida_reintento_forma(resp_f2, c)
                if err is None and mal_formada_tras_reintento(stop, tool_input, val):
                    reparada = reparar_relations_ausente(stop, tool_input, c) if perfil_forma_r2(PERFIL) else None
                    if reparada is None:
                        err = ERROR_FORMA_TRAS_REINTENTO
                    else:
                        # T2-ter: el registro guarda la salida reparada (la entrada de E2 r2 vuelve a validar el
                        # crudo); la del modelo queda en la caché
                        tool_input, val = reparada
                        reparacion_forma = {"motivo": MOTIVO_REPARACION_FORMA,
                                            "intento": cliente_e1.SUFIJO_REINTENTO_FORMA_2
                                            if "reintento_2" in reintento_forma else cliente_e1.SUFIJO_REINTENTO_FORMA}
        reg = {
            "chunk_id": c["id"], "unidad": c["unidad"], "tipo_unidad": c["tipo"],
            "titulo": c["titulo"], "stop_reason": stop, "error": err,
            "usage": usage, "tool_input_crudo": tool_input, "validacion": val}
        if reintento_forma is not None:
            reg["reintento_forma"] = reintento_forma
        if reparacion_forma is not None:
            reg["reparacion_forma"] = reparacion_forma
        if cortado is not None:
            # decisión 2: AMBOS intentos persistidos íntegros — el crudo
            # completo del intento 1 ya está en la db (write-through); acá
            # queda su proyección jsonl junto al intento efectivo.
            reg["reintento_corte"] = {
                "max_tokens_reintento": techo_corte,
                "intento_1": cliente_e1.resumen_intento(cortado)}
        if escalon3:
            # P3c-2: el tercer escalón, con el intento cortado del reintento; la marca la lee U-REEXT-T0 (T4)
            reg["escalon_3"] = {"max_tokens": cliente_e1.MAX_TOKENS_ESCALON_3_R2,
                                "intento_2": cliente_e1.resumen_intento(cortados[1])}
        partes = None
        if PERFIL_R2 and err == "max_tokens_hit_tras_reintento" and "sub_chunk" not in c:
            # R4.b: la unidad se parte (sin cortar bloques de tabla) y las
            # partes se extraen a continuación, en este mismo pase
            import correr_e0    # noqa: PLC0415 — e0_chunking, solo con --perfil-r2
            partes, informe = correr_e0.particionar_por_corte(c)
            reg["particion_por_corte"] = informe
            if partes:
                err = reg["error"] = ERROR_PARTICIONADA
                guardar_particion(tdir, c, partes, informe)
                cola[i_cola:i_cola] = partes
        append_jsonl(jsonl, reg)
        procesadas += 1
        hechas_este_proceso += 1
        estado.tick(cliente.gasto_usd, procesadas)
        errores_consecutivos = 0 if err in (None, ERROR_PARTICIONADA) else errores_consecutivos + 1
        if errores_consecutivos > 5:
            raise Freno(f"{key}: más de 5 errores de API consecutivos "
                        f"(último: {err}) — problema sistémico, se frena")
        if procesadas % 25 == 0 or err or cortado is not None or reintento_forma is not None:
            print(f"[{key} {procesadas}/{len(chunks)}] {c['id']:<28s} "
                  f"gasto_fase=USD {gasto_previo + cliente.gasto_usd:.4f}"
                  + (" REINTENTO_CORTE" if cortado is not None else "")
                  + (" ESCALON_3" if escalon3 else "")
                  + (" REINTENTO_FORMA" if reintento_forma is not None else "")
                  + (f" ERROR {err}" if err else ""), flush=True)
        if checkpoint_cada and procesadas % checkpoint_cada == 0:
            checkpoint(salida, estado, to, "e1", procesadas, len(chunks),
                       f"u{procesadas}")
        if abortar_tras and hechas_este_proceso >= abortar_tras:
            print(f"[{key}] ABORT SIMULADO tras {hechas_este_proceso} unidades "
                  f"de este proceso", flush=True)
            sys.exit(9)

    # Cierre del pase (U-B5.3 decisión 5): sin reintentables pendientes; los
    # errores definitivos quedan contabilizados en el resumen (nunca en
    # silencio). Las claves nuevas del resumen solo aparecen si hubo casos:
    # una corrida sin cortes produce un resumen byte-idéntico al histórico.
    if PERFIL_R2:
        chunks = chunks_con_partes(chunks, tdir)
    ids_corrida = {c["id"] for c in chunks}
    finales_e1 = {cid: r for cid, r in cargar_jsonl_last_wins(jsonl).items()
                  if cid in ids_corrida}
    pendientes_corte = reintentables_pendientes(finales_e1)
    if pendientes_corte:
        raise Freno(f"{key}: {len(pendientes_corte)} unidades con corte por "
                    f"max_tokens sin reintentar ({pendientes_corte[:5]}) — un "
                    f"pase no cierra con reintentables pendientes; relanzar "
                    f"reanuda y las reintenta")
    definitivos = [{"chunk_id": cid, "error": r["error"]}
                   for cid, r in sorted(finales_e1.items()) if r.get("error")]
    reintentos_corte = sum(1 for r in finales_e1.values() if "reintento_corte" in r)
    resumen = {"n_unidades": len(chunks),
               "cliente": cliente.resumen(),
               "gasto_fase_usd": round(gasto_previo + cliente.gasto_usd, 4)}
    if PERFIL.esquema is not None and PERFIL.esquema.obligacion_tipo_enum is not None:
        # U-CABLE-V3 resolución 2 (vigilancia (5) del laudo de congelado):
        # suma visible de las normalizaciones de Obligacion.properties.tipo.
        # SOLO en modo v3 — el resumen dev queda byte-idéntico.
        n_norm = n_ret = 0
        for r in finales_e1.values():
            m = ((r.get("validacion") or {}).get("metricas") or {})
            n_norm += m.get("tipo_obligacion_normalizados", 0)
            n_ret += m.get("tipo_obligacion_requisito_de_estructura", 0)
        resumen["tipo_obligacion_normalizados"] = n_norm
        resumen["tipo_obligacion_requisito_de_estructura"] = n_ret
    if reintentos_corte:
        resumen["reintentos_corte"] = reintentos_corte
    con_forma = sorted(cid for cid, r in finales_e1.items() if "reintento_forma" in r)
    if con_forma:
        resumen["reintentos_forma"] = {
            "unidades": con_forma,
            "agotados": sorted(cid for cid in con_forma if finales_e1[cid].get("error") == ERROR_FORMA_TRAS_REINTENTO)}
        con_segundo = sorted(cid for cid in con_forma if "reintento_2" in finales_e1[cid]["reintento_forma"])
        if con_segundo:
            resumen["reintentos_forma"]["con_segundo_reintento"] = con_segundo
    reparadas = sorted(cid for cid, r in finales_e1.items() if "reparacion_forma" in r)
    if reparadas:
        # T2-ter: las unidades reparadas, contadas aparte de los reintentos por forma
        resumen["reparadas_forma"] = {"motivo": MOTIVO_REPARACION_FORMA, "unidades": reparadas}
    con_escalon3 = sorted(cid for cid, r in finales_e1.items() if r.get("escalon_3")) if PERFIL_R2 else []
    if con_escalon3:
        resumen["escalon_3"] = {
            "max_tokens": cliente_e1.MAX_TOKENS_ESCALON_3_R2, "unidades": con_escalon3,
            "cortan_tambien": sorted(cid for cid in con_escalon3 if finales_e1[cid].get("error") == ERROR_TRAS_ESCALON_3)}
    particionadas = partes_por_corte(tdir) if PERFIL_R2 else {}
    if particionadas:
        resumen["particionadas_por_corte"] = {k: [x["id"] for x in v["partes"]]
                                              for k, v in sorted(particionadas.items())}
    if definitivos:
        resumen["errores_definitivos"] = definitivos
        print(f"[{key}] {len(definitivos)} errores definitivos "
              f"contabilizados en resumen_e1.json", flush=True)
    (tdir / "resumen_e1.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    estado.cerrar_fase(key, {"gasto_usd": resumen["gasto_fase_usd"],
                             "n": len(chunks)})
    checkpoint(salida, estado, to, "e1", len(chunks), len(chunks), "cierre")


# ----------------------------- fase E3 ----------------------------------- #
def compactar_e1(to: str, salida: Path) -> Path:
    """extracciones_e1.jsonl (append-only, posibles duplicados por reanudación)
    → compactado determinístico en orden documental, last-wins."""
    tdir = salida / to
    regs = cargar_jsonl_last_wins(tdir / "extracciones_e1.jsonl")
    chunks = chunks_sin_ids_repetidos(comun_e1.cargar_chunks((to,), e0_dir=E0_DIR), to)
    if PERFIL_R2:
        chunks = chunks_con_partes(chunks, tdir)
    out = tdir / "extracciones_e1_compact.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for c in chunks:
            if c["id"] in regs:
                f.write(json.dumps(regs[c["id"]], ensure_ascii=False) + "\n")
    return out


def fase_e3(to: str, cli_e3, cli_e1r, estado: Estado, salida: Path,
            limite: int | None, abortar_tras: int | None,
            checkpoint_cada: int | None) -> None:
    key = f"{to}:e3"
    tdir = salida / to
    finales = tdir / "finales.jsonl"

    chunks = chunks_sin_ids_repetidos(comun_e3.cargar_chunks((to,), e0_dir=E0_DIR), to)
    if PERFIL_R2:
        chunks = chunks_con_partes(chunks, tdir)
    if limite:
        chunks = chunks[:limite]
    unidades_corpus = {c["unidad"] for c in chunks}
    compact = compactar_e1(to, salida)
    regs = comun_e3.cargar_extracciones(compact)
    pares = comun_e3.pares_de(chunks, regs)

    previos = cargar_jsonl_last_wins(finales)
    pendientes = [(c, v) for c, v in pares if c["id"] not in previos]
    print(f"[{key}] aceptadas_e1={len(pares)} ya_persistidas={len(previos)} "
          f"pendientes={len(pendientes)}", flush=True)

    gasto_previo = estado.abrir_fase(key)
    registro = ratchet_e3.RegistroE3(tdir)
    procesadas = len(previos)
    hechas_este_proceso = 0
    for c, val in pendientes:
        gasto_fase = gasto_previo + cli_e3.gasto_usd + cli_e1r.gasto_usd
        if estado.gasto_global() + MARGEN_UNIDAD_USD > TOPE_GLOBAL_USD:
            raise Freno(f"tope global antes de {c['id']}: gasto USD "
                        f"{estado.gasto_global():.4f} + margen {MARGEN_UNIDAD_USD}")
        exp, err = llamar_con_reintentos_api(
            lambda: ratchet_e3.ciclo_ratchet(
                c, val, cliente_verificador=cli_e3, cliente_extractor=cli_e1r,
                model_e3=MODEL_E3, model_e1=MODEL_E1, registro=registro,
                max_tokens_reintento=techo_reintento_ratchet(regs.get(c["id"])),
                unidades_corpus=unidades_corpus, perfil=PERFIL),
            c["id"])
        if exp is None:
            raise Freno(f"{key}: ciclo de ratchet de {c['id']} falló tras "
                        f"reintentos de API ({err}) — se frena para no dejar "
                        f"huecos silenciosos; relanzar reanuda acá")
        # U-R2-CODIGO, R2.b: crudo de cada reintento del ratchet en el archivo
        # compañero de finales.jsonl, ANTES de la línea de finales (una unidad
        # en finales tiene su crudo persistido; una reanudación puede repetir
        # registros: se leen last-wins por (chunk_id, intento)). Sin reintentos
        # el archivo no se crea, así que una corrida sin reintentos deja los
        # mismos archivos que antes.
        for reex in exp["reintentos"]:
            append_jsonl(tdir / REINTENTOS_E3, {
                "chunk_id": c["id"], "intento": reex["intento"],
                "tool_input": reex["tool_input"], "error": reex["error"]})
        append_jsonl(finales, {
            "chunk_id": c["id"], "tipo_unidad": c["tipo"],
            "estado": exp["estado"], "n_reintentos": len(exp["reintentos"]),
            "residuales": exp["residuales"],
            "validacion_final": exp["validacion_final"]})
        procesadas += 1
        hechas_este_proceso += 1
        estado.tick(cli_e3.gasto_usd + cli_e1r.gasto_usd, procesadas)
        if procesadas % 25 == 0:
            print(f"[{key} {procesadas}/{len(pares)}] {c['id']:<28s} "
                  f"{exp['estado']:<28s} gasto_fase=USD "
                  f"{gasto_previo + cli_e3.gasto_usd + cli_e1r.gasto_usd:.4f}",
                  flush=True)
        if checkpoint_cada and procesadas % checkpoint_cada == 0:
            checkpoint(salida, estado, to, "e3", procesadas, len(pares),
                       f"u{procesadas}")
        if abortar_tras and hechas_este_proceso >= abortar_tras:
            print(f"[{key}] ABORT SIMULADO tras {hechas_este_proceso} unidades "
                  f"de este proceso", flush=True)
            sys.exit(9)

    todos = cargar_jsonl_last_wins(finales)
    estados = Counter(r["estado"] for r in todos.values())
    resumen = {"n_unidades_e3": len(pares),
               "estados": dict(estados),
               "cliente_e3": cli_e3.resumen(),
               "cliente_e1_reintentos": cli_e1r.resumen(),
               "gasto_fase_usd": round(gasto_previo + cli_e3.gasto_usd
                                       + cli_e1r.gasto_usd, 4)}
    if perfil_forma_r2(PERFIL):
        # Enmienda a LAUDO B, condición de la autora: cada unidad eximida por la ampliación, para leerla.
        exen = exenciones_ampliacion(tdir)
        resumen["exenciones_ampliacion_laudo_b"] = exen
        resumen["unidades_eximidas_ampliacion"] = sorted({x["chunk_id"] for x in exen})
    (tdir / "resumen_e3.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    estado.cerrar_fase(key, {"gasto_usd": resumen["gasto_fase_usd"],
                             "n": len(pares), "estados": dict(estados)})
    checkpoint(salida, estado, to, "e3", len(pares), len(pares), "cierre")


# ----------------------------- E2 por TO --------------------------------- #
def cerrar_e2(to: str, salida: Path, limite: int | None = None) -> dict:
    """Construye el jsonl FINAL del TO (post-E3: aceptadas con su validación
    final; cola humana y rechazos E1 como registros rechazados contabilizados)
    y corre reducir(): fan-in + ensamblado + censo contra el mapa enm01."""
    tdir = salida / to
    regs_e1 = cargar_jsonl_last_wins(tdir / "extracciones_e1_compact.jsonl")
    finales = cargar_jsonl_last_wins(tdir / "finales.jsonl")
    chunks = chunks_sin_ids_repetidos(comun_e1.cargar_chunks((to,), e0_dir=E0_DIR), to)
    if limite:
        chunks = chunks[:limite]
    # U-REEXT-T0, T2-bis (corrección autorizada por la autora fuera de los puntos a-c): el fan-in de este E2 espera las
    # unidades de la E0, y el compactado lleva las partes de una unidad partida por corte (perfil r2), no la unidad.
    # La unidad va con su último registro de E1 (error particionada_por_corte), como rechazada en E1, y se declara
    # aparte en el reporte, reemplazada por sus partes, que entran al E2 r2. Sin particiones, nada cambia.
    partidas = partes_por_corte(tdir) if PERFIL_R2 else {}
    if partidas:
        regs_todos = cargar_jsonl_last_wins(tdir / "extracciones_e1.jsonl")
        regs_e1 = {**regs_e1, **{cid: regs_todos[cid] for cid in partidas if cid in regs_todos}}

    path_final = tdir / f"extracciones_finales_{to}.jsonl"
    with path_final.open("w", encoding="utf-8") as f:
        for c in chunks:
            cid = c["id"]
            if cid in finales and finales[cid]["validacion_final"] is not None:
                f.write(json.dumps({
                    "chunk_id": cid, "error": None,
                    "estado_e3": finales[cid]["estado"],
                    "validacion": finales[cid]["validacion_final"]},
                    ensure_ascii=False) + "\n")
            elif cid in finales:  # cola humana: NO ingresa al grafo
                f.write(json.dumps({
                    "chunk_id": cid, "error": f"cola_humana:{finales[cid]['estado']}",
                    "estado_e3": finales[cid]["estado"], "validacion": None},
                    ensure_ascii=False) + "\n")
            elif cid in regs_e1:  # rechazado en E1 (nunca llegó a E3)
                f.write(json.dumps(regs_e1[cid], ensure_ascii=False) + "\n")
    # con --limite (solo pruebas) el fan-in es parcial por construcción; la
    # corrida real va SIN flag: un ausente inesperado aborta como debe.
    res = e2_lib.reducir(to, path_final, permitir_parcial=bool(limite),
                         censo_oraculo=CENSO_ORACULO_ARG, e0_dir=E0_DIR,
                         limitaciones=LIMITACIONES, esquema=PERFIL.esquema,
                         labels_catalogo=PERFIL.labels_catalogo)
    if partidas:
        res["reporte"]["particionadas_por_corte"] = {
            cid: {"reemplazada_por": [p["id"] for p in v["partes"]],
                  "en_este_fan_in": "rechazada en E1 con el error particionada_por_corte; sus partes entran al E2 r2"}
            for cid, v in sorted(partidas.items())}
    (tdir / f"grafo_{to}.json").write_text(res["grafo_json"], encoding="utf-8")
    (tdir / f"reporte_e2_{to}.json").write_text(
        json.dumps(res["reporte"], ensure_ascii=False, indent=1), encoding="utf-8")
    (tdir / f"censo_{to}.json").write_text(
        json.dumps(res["censo"], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{to}:e2] nodos={res['reporte']['nodes_total']} "
          f"aristas={res['reporte']['edges_total']} "
          f"sha256={res['reporte']['sha256_grafo'][:12]}", flush=True)
    return res["reporte"]


# ----------------------------- perfil r2 --------------------------------- #
# U-R2-CODIGO, R3.a: con --perfil-r2, además del E2 del perfil de E1 (sin
# cambios), el runner arma la entrada de E2 del perfil r2: el crudo del intento
# que E3 aceptó (primer intento o reintento), validado con el validador, la
# política y el catálogo r2 (pyd_r2), con los sujetos resueltos por relación y
# el registro de no mapeados (r1_e4), y el E2 del perfil r2 (e2_lib). E1 y E3
# no cambian: sus prompts sellados leen la validación del perfil de E1. Los
# archivos del perfil r2 llevan nombre propio; los del perfil de E1 quedan
# byte a byte iguales.
PERFIL_R2 = False
# Forma del crudo de E1 según el perfil que lo produjo (validador_r2.validar):
# los perfiles existentes emiten la forma v3 (sujeto_propuesto, omisiones_no_prosa).
FORMA_CRUDO_POR_PERFIL = {"produccion_dev": "v3", "v3_b54": "v3", "r2b": "r2"}


def perfil_forma_r2(perfil) -> bool:
    """U-PROMPT-R2 (decisión 1 del mandato): el perfil cuya salida tiene la forma «r2» (r2b) activa el camino del
    perfil r2 que antes pedía --perfil-r2 (techo de corte de r2, partición R4.b y E2 r2). Los perfiles existentes
    siguen con el camino por defecto, y --perfil-r2 sigue valiendo para ellos."""
    return perfil.esquema is not None and getattr(perfil.esquema, "forma_salida", "v3") == "r2"


def exenciones_ampliacion(tdir: Path) -> list[dict]:
    """Enmienda a LAUDO B (§2, punto 6): los faltantes eximidos por la ampliación, es decir los
    estructural_no_bloqueante de tipo distinto de enumeracion_incompleta, con su unidad, su fase, su cita y su
    tipo, desde veredictos.jsonl (en orden de registro)."""
    p = Path(tdir) / "veredictos.jsonl"
    out: list[dict] = []
    if p.exists():
        for linea in p.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            v = json.loads(linea)
            for f in v.get("faltantes") or []:
                if f.get("estructural_no_bloqueante") and f.get("tipo") != "enumeracion_incompleta":
                    out.append({"chunk_id": v["chunk_id"], "fase": v["fase"], "intento": v["intento"],
                                "tipo": f.get("tipo"), "cita": f.get("cita_textual_del_fuente")})
    return out


def leer_reintentos_companero(tdir: Path) -> dict[tuple[str, int], dict]:
    """(chunk_id, intento) → registro de reintentos_e3.jsonl (last-wins)."""
    out: dict[tuple[str, int], dict] = {}
    p = Path(tdir) / REINTENTOS_E3
    if p.exists():
        for linea in p.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                r = json.loads(linea)
                out[(r["chunk_id"], r["intento"])] = r
    return out


def claves_reintentos_cache(tdir: Path, chunks: list[dict], perfil, solo: set | None = None) -> list[dict]:
    """Corridas anteriores al archivo compañero: por cada unidad con reintento
    en finales.jsonl, la clave de caché del request del reintento,
    reconstruido con el código del pipeline (veredicto de la verificación →
    evaluar_veredicto → build_reextraccion_kwargs con el perfil, el modelo y
    el techo de la corrida; un reintento por unidad). `solo`: limita a esos
    chunk_id."""
    ns = cliente_e1.namespace_e1(prefijo_hash=perfil.prefijo_hash_para_namespace)
    por_id = {c["id"]: c for c in chunks}
    unidades = {c["unidad"] for c in chunks}
    finales = cargar_jsonl_last_wins(Path(tdir) / "finales.jsonl")
    verif: dict[str, dict] = {}
    with (Path(tdir) / "veredictos.jsonl").open(encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                r = json.loads(linea)
                if r["fase"] == "verificacion":
                    verif[r["chunk_id"]] = r
    # validación de la verificación (la de E1 que vio E3): rige la ampliación de LAUDO B en la forma r2
    regs_e1 = cargar_jsonl_last_wins(Path(tdir) / "extracciones_e1_compact.jsonl")
    out = []
    for cid, fin in finales.items():
        if not fin.get("n_reintentos") or (solo is not None and cid not in solo):
            continue
        ev = ratchet_e3.evaluar_veredicto(verif[cid]["tool_input"], por_id[cid], unidades,
                                          (regs_e1.get(cid) or {}).get("validacion"))
        kw = ratchet_e3.build_reextraccion_kwargs(
            por_id[cid], ev["bloqueantes_utilizables"], model=MODEL_E1, intento=1,
            max_tokens_reintento=techo_reintento_ratchet(regs_e1.get(cid)),
            perfil=None if perfil.nombre == "produccion_dev" else perfil)
        out.append({"chunk_id": cid, "intento": 1, "namespace": ns,
                    "clave": cliente_e1.lc.compute_key(ns, cliente_e1.lc.canonical_request(kw))})
    return out


def crudos_reintento_e3(tdir: Path, chunks: list[dict], perfil) -> dict[tuple[str, int], dict]:
    """(chunk_id, intento) → {tool_input, error, fuente}: del archivo compañero
    si existe la fila; si no, de e1_reintentos.db por la clave reconstruida,
    con la db abierta en modo inmutable."""
    import sqlite3          # noqa: PLC0415
    import urllib.parse     # noqa: PLC0415
    out = {k: {"tool_input": r["tool_input"], "error": r["error"], "fuente": "companero"}
           for k, r in leer_reintentos_companero(tdir).items()}
    finales = cargar_jsonl_last_wins(Path(tdir) / "finales.jsonl")
    sin_companero = {cid for cid, f in finales.items()
                     if f.get("n_reintentos") and (cid, f["n_reintentos"]) not in out}
    faltan = claves_reintentos_cache(tdir, chunks, perfil, solo=sin_companero) if sin_companero else []
    if faltan:
        con = sqlite3.connect(f"file:{urllib.parse.quote(str(DB_REINTENTOS_E1.resolve()))}?mode=ro&immutable=1",
                              uri=True)
        try:
            for r in faltan:
                fila = con.execute("select raw_json from cache where key = ?", (r["clave"],)).fetchone()
                if fila is None:
                    continue
                msg = json.loads(fila[0])
                tis = [b.get("input") for b in (msg.get("content") or [])
                       if isinstance(b, dict) and b.get("type") == "tool_use"]
                out[(r["chunk_id"], r["intento"])] = {"tool_input": tis[0] if tis else None,
                                                      "error": None if tis else "no_tool_use",
                                                      "fuente": "cache"}
        finally:
            con.close()
    return out


def vistos_por_e3(validacion: dict | None) -> dict | None:
    """U-PROMPT-R2, P3 (nota del 04/10/2026 al mandato, punto b): los índices del crudo que validador_e1 pasó a
    E3, leídos de la validación guardada del intento (forma r2: cada elemento lleva `indice_crudo`). None si la
    validación falta, no es de la forma r2 o le falta algún índice."""
    if not validacion or validacion.get("forma_salida") != "r2":
        return None
    ents, rels = validacion.get("entidades") or [], validacion.get("relaciones") or []
    if any(not isinstance(x.get("indice_crudo"), int) for x in ents + rels):
        return None
    vistos = {"entidades": sorted(x["indice_crudo"] for x in ents),
              "relaciones": sorted(x["indice_crudo"] for x in rels)}
    copias = (validacion.get("marcas_e3") or {}).get("copia_nota_e3")
    if copias:
        # U-PROMPT-R2, P3b-2: la marca de la copia de la nota de E3 (ratchet_e3) llega al nodo por validador_r2.
        vistos["marcas"] = {"copia_nota_e3": copias}
    # U-R2-CODIGO-2, C2, punto t: las marcas de la lectura del veredicto como texto y del reintento con menos
    # elementos llegan a la validación y al conteo de E2 (stats["p3b"]).
    otras = {k: v for k, v in (validacion.get("marcas_e3") or {}).items()
             if k in ("lectura_veredicto_e3", "reintento_con_menos_elementos") and v}
    if otras:
        vistos.setdefault("marcas", {}).update(otras)
    return vistos


def entrada_r2(to: str, tdir: Path, chunks: list[dict], perfil, validar) -> list[dict]:
    """Registros de la entrada de E2 del perfil r2, uno por chunk, en el orden
    de E0. Crudo del intento que E3 aceptó: el primero si no hubo reintento,
    el del reintento si lo hubo. Cola humana: el crudo del primer intento,
    como la cadena r1 (r1_cola_flaggeada), con `cola_humana`. Rechazados en E1
    (nunca llegaron a E3): quedan rechazados. `validar(tool_input, chunk)` es
    el validador r2 con su política.
    Con un perfil de forma r2 (U-PROMPT-R2, P3), el validador recibe además lo
    que vio E3 de ese intento (`vistos_e3`, de la validación guardada: la
    final o, en la cola humana, la del primer intento) y solo eso entra; sin
    esos índices, la unidad queda sin validación, con su error."""
    regs_e1 = cargar_jsonl_last_wins(Path(tdir) / "extracciones_e1_compact.jsonl")
    finales = cargar_jsonl_last_wins(Path(tdir) / "finales.jsonl")
    crudos_r = crudos_reintento_e3(tdir, chunks, perfil)
    forma_r2 = perfil_forma_r2(perfil)
    out = []
    for c in chunks:
        cid = c["id"]
        base = {"chunk_id": cid, "to": to, "archivo": c["archivo"],
                "e0_sha256_completo": c.get("sha256_completo")}
        if cid in finales:
            fin = finales[cid]
            n = fin.get("n_reintentos") or 0
            cola = fin.get("validacion_final") is None
            if n and not cola:
                cr = crudos_r.get((cid, n))
                if cr is None or cr["tool_input"] is None:
                    out.append({**base, "error": "crudo_del_reintento_no_encontrado", "estado_e3": fin["estado"],
                                "validacion": None, "origen_crudo": f"reintento_{n}"})
                    continue
                ti, origen = cr["tool_input"], f"reintento_{n}:{cr['fuente']}"
            else:
                ti, origen = (regs_e1.get(cid) or {}).get("tool_input_crudo"), "e1"
            if ti is None:
                out.append({**base, "error": "sin_crudo", "estado_e3": fin["estado"], "validacion": None,
                            "origen_crudo": origen})
                continue
            if forma_r2:
                val_e3 = (regs_e1.get(cid) or {}).get("validacion") if cola else fin.get("validacion_final")
                vistos = vistos_por_e3(val_e3)
                if vistos is None:
                    out.append({**base, "error": "validacion_e3_sin_indices_r2", "estado_e3": fin["estado"],
                                "validacion": None, "origen_crudo": origen})
                    continue
                validacion = validar(ti, c, vistos_e3=vistos)
            else:
                validacion = validar(ti, c)
            reg = {**base, "error": None, "estado_e3": fin["estado"], "validacion": validacion,
                   "origen_crudo": origen}
            if cola:
                reg["cola_humana"] = True
            out.append(reg)
        elif cid in regs_e1:
            out.append({**base, "error": regs_e1[cid].get("error") or "rechazado_en_e1", "estado_e3": None,
                        "validacion": None, "origen_crudo": "e1"})
    return out


def conteo_paso_por_e3(regs: list[dict]) -> dict:
    """U-PROMPT-R2, P3 (nota del 04/10/2026, punto c): elementos de extracción que entran sin haber pasado por E3
    (entidades sin paso_por_e3 y relaciones con no_verificada_e3), los excluidos por no haber pasado y las
    unidades sin los índices de E3. Con la forma r2 los que entran sin verificar son 0 por construcción; el
    control de suite que lo exige es de otra unidad.
    Las unidades que E3 no terminó (ratchet agotado y veredicto inutilizable: la cola humana) entran marcadas
    (`cola_humana`, decisión de la autora del 04/10/2026): son la excepción explícita a «cero elementos sin
    verificar» y se cuentan aparte, por estado."""
    val = [r["validacion"] for r in regs if r.get("validacion") and not r.get("cola_humana")]
    cola = [r for r in regs if r.get("validacion") and r.get("cola_humana")]
    no_vistos = Counter("entidad" if x["elemento"].startswith("entities") else "relacion"
                        for v in val + [r["validacion"] for r in cola] for x in v.get("no_vistos_e3", []))
    return {"entidades_sin_verificar": sum(1 for v in val for e in v["entidades"] if e.get("paso_por_e3") is not True),
            "relaciones_sin_verificar": sum(1 for v in val for x in v["relaciones"] if x.get("no_verificada_e3")),
            "cola_humana": {"unidades": len(cola),
                            "por_estado": dict(sorted(Counter(r["estado_e3"] for r in cola).items())),
                            "entidades": sum(len(r["validacion"]["entidades"]) for r in cola),
                            "relaciones": sum(len(r["validacion"]["relaciones"]) for r in cola)},
            "excluidos_entidades": no_vistos.get("entidad", 0), "excluidos_relaciones": no_vistos.get("relacion", 0),
            "unidades_sin_indices_e3": sum(1 for r in regs if r.get("error") == "validacion_e3_sin_indices_r2")}


def validador_perfil_r2(perfil=None):
    """(validar, política) del perfil r2, con los candados de la decisión 10
    del mandato: catálogo r2 por sha256 (modelos_r2) y política con el sha de
    57a8dd2. `perfil`: el de E1 que produjo el crudo (default, el de la
    corrida), que fija la forma del crudo."""
    import r1_e4 as E4      # noqa: PLC0415
    V = E4.modulo_validador_r2()
    pol = V.politica_default()
    if pol.sha256 != E4.POLITICA_R2_SHA256:
        raise Freno(f"política r2 con sha {pol.sha256[:12]}… (esperado {E4.POLITICA_R2_SHA256[:12]}…)")
    forma = FORMA_CRUDO_POR_PERFIL[(perfil or PERFIL).nombre]
    # vistos_e3 (U-PROMPT-R2, P3): lo pasa entrada_r2 solo con la forma r2.
    return (lambda ti, c, **kw: V.validar(ti, c, pol, forma=forma, **kw)), pol


def cerrar_e2_r2(to: str, salida: Path, limite: int | None = None) -> dict:
    """E2 del perfil r2 de un TO (USD 0, sin API): entrada r2, resolución de
    sujetos por relación, registro de no mapeados del TO y E2 r2. Escribe
    extracciones_finales_r2_<to>.jsonl, resolucion_sujetos.jsonl,
    no_mapeados_sujetos.jsonl, grafo_r2_<to>.json y reporte_e2_r2_<to>.json."""
    import r1_e4 as E4      # noqa: PLC0415
    tdir = salida / to
    chunks = chunks_con_partes(chunks_sin_ids_repetidos(comun_e1.cargar_chunks((to,), e0_dir=E0_DIR), to), tdir)
    if limite:
        chunks = chunks[:limite]
    validar, pol = validador_perfil_r2()
    cat = E4.catalogo_r2()
    regs = entrada_r2(to, tdir, chunks, PERFIL, validar)
    versiones = {"catalogo_sha256": cat["catalogo_sha256"], "politica_sha256": pol.sha256,
                 "perfil": "r2", "prefijo_hash": PERFIL.prefijo_hash}
    res = E4.resolver_relaciones_r2(regs, cat["indice"], cat["rol_por_to"], versiones, parte_a=perfil_forma_r2(PERFIL))
    M = E4.modulo_modelos_r2()
    ens = e2_lib.ensamblar_r2(chunks, regs, cat["labels"], M.SUJETOS_R2_SET, M.firma_r2,
                              M.TIPOS_ENTIDAD, M.PREDICADOS, res["registro"], fase="r2b" if perfil_forma_r2(PERFIL) else "r2a")
    grafo = {"nodes": ens["nodes"], "edges": ens["edges"]}
    r_cola = e2_lib.flaggear_cola_r2(grafo, {r["chunk_id"]: r["estado_e3"] for r in regs if r.get("cola_humana")})
    grafo_json = json.dumps(grafo, ensure_ascii=False, indent=2)

    def jl(nombre: str, filas: list[dict]) -> None:
        with (tdir / nombre).open("w", encoding="utf-8") as f:
            for r in filas:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    jl(f"extracciones_finales_r2_{to}.jsonl", regs)
    jl("resolucion_sujetos.jsonl", res["resolucion"])
    jl("no_mapeados_sujetos.jsonl", res["registro"])
    (tdir / f"grafo_r2_{to}.json").write_text(grafo_json, encoding="utf-8")
    reporte = {"to": to, "perfil": "r2", **versiones,
               "nodes_total": len(ens["nodes"]), "edges_total": len(ens["edges"]),
               "nodes_by_type": e2_lib._conteo(ens["nodes"], "type"),
               "edges_by_relation": e2_lib._conteo(ens["edges"], "relation"),
               "stats": ens["stats"], "rechazos_e2": ens["rechazos_e2"],
               "conflictos_properties": ens["conflictos_properties"],
               "resolucion_sujetos": res["resumen"], "cola_flaggeada": r_cola,
               "origen_crudo": dict(Counter(r["origen_crudo"].split(":")[0] for r in regs)),
               "sha256_grafo": hashlib_sha256(grafo_json)}
    if perfil_forma_r2(PERFIL):
        # U-PROMPT-R2, P3: el registro de omisiones (L-ESQ-R2 §5.4; lo lee LN-7) y el conteo de elementos de
        # extracción sin verificar por E3, que con la forma r2 es 0 por construcción (nota del 04/10/2026).
        jl("omisiones.jsonl", [{"chunk_id": r["chunk_id"], "to": to, **o} for r in regs
                               for o in (r.get("validacion") or {}).get("omisiones", [])])
        reporte["paso_por_e3"] = conteo_paso_por_e3(regs)
    (tdir / f"reporte_e2_r2_{to}.json").write_text(json.dumps(reporte, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    print(f"[{to}:e2-r2] nodos={reporte['nodes_total']} aristas={reporte['edges_total']} "
          f"sha256={reporte['sha256_grafo'][:12]}", flush=True)
    return reporte


def hashlib_sha256(s: str) -> str:
    import hashlib          # noqa: PLC0415
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ----------------------------- chequeo de hits --------------------------- #
def chequear_hits(to: str, chk: dict, estado: Estado, stub: bool) -> None:
    """Chequeo de hits declarado en el manifiesto (limites.chequeos_hits):
    umbrales de gasto por fase para un TO cuyas llamadas deberían ser hits de
    la caché local (precedente: pro en la corrida del corpus de desarrollo)."""
    if stub:
        return
    e1_max, e3_max = chk["e1_max_usd"], chk["e3_max_usd"]
    g_e1 = estado.d["fases_cerradas"][f"{to}:e1"]["gasto_usd"]
    g_e3 = estado.d["fases_cerradas"][f"{to}:e3"]["gasto_usd"]
    if g_e1 > e1_max:
        raise Freno(f"{to}:e1 gastó USD {g_e1:.4f} > {e1_max} — se "
                    f"esperaban ≈100% hits locales; algo cambió")
    if g_e3 > e3_max:
        raise Freno(f"{to}:e3 gastó USD {g_e3:.4f} > {e3_max} — más "
                    f"que el techo esperado de los ciclos de reintento nuevos "
                    f"bajo la política A+B; algo cambió")
    print(f"[{to}] chequeo de hits OK: e1=USD {g_e1:.4f} (≤{e1_max}) "
          f"e3=USD {g_e3:.4f} (≤{e3_max})", flush=True)


# ----------------------------- main -------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stub", action="store_true", help="clientes stub, offline")
    ap.add_argument("--autorizado-tope", type=float, default=None,
                    help="eco de la autorización; debe igualar el "
                         "tope_global_usd del manifiesto para corrida real")
    ap.add_argument("--salida", type=Path, default=AQUI / "salida")
    ap.add_argument("--tos", type=str, default=None,
                    help="subconjunto de TOs (default: todos, en el orden "
                         "del manifiesto)")
    ap.add_argument("--limite", type=int, default=None,
                    help="solo primeras N unidades por TO (pruebas)")
    ap.add_argument("--abortar-tras", type=int, default=None,
                    help="sys.exit(9) tras N unidades por fase (prueba de reanudación)")
    ap.add_argument("--checkpoint-cada", type=int, default=None,
                    help="override del intervalo de checkpoint intra-TO")
    ap.add_argument("--manifiesto", type=Path, default=MANIFIESTO_DEFAULT,
                    help="manifiesto de corpus (U-B5.1); default: el de "
                         "desarrollo (5 TOs)")
    ap.add_argument("--perfil-r2", action="store_true",
                    help="U-R2-CODIGO R3.a: también el E2 del perfil r2 (archivos *_r2_*, "
                         "resolucion_sujetos.jsonl y no_mapeados_sujetos.jsonl por TO)")
    ap.add_argument("--reabrir-fase", type=str, default=None,
                    help="U-REEXT-T0, T2-bis: fases cerradas que se reabren antes de su salteo, separadas por coma "
                         "(p. ej. cap:e1,cap:e3); conservan su gasto como gasto previo y la corrida las vuelve a cerrar")
    args = ap.parse_args()
    global PERFIL_R2

    if args.manifiesto != MANIFIESTO_DEFAULT:
        configurar(manifiesto_corpus.cargar(args.manifiesto))
    PERFIL_R2 = args.perfil_r2 or perfil_forma_r2(PERFIL)

    tos = ([t.strip() for t in args.tos.split(",") if t.strip()]
           if args.tos else list(TOS_ORDEN))
    assert all(t in TOS_ORDEN for t in tos), tos
    reabrir = {k.strip() for k in (args.reabrir_fase or "").split(",") if k.strip()}
    assert all(k.split(":")[0] in tos and k.split(":")[-1] in ("e1", "e3") for k in reabrir), reabrir

    if not args.stub:
        if args.autorizado_tope != TOPE_GLOBAL_USD:
            print(f"corrida real exige --autorizado-tope {TOPE_GLOBAL_USD} "
                  f"(eco de la autorización, igual al tope_global_usd del "
                  f"manifiesto)")
            return 2
        from dotenv import load_dotenv
        load_dotenv(EVAL_DIR / ".env")
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            print(f"ANTHROPIC_API_KEY ausente (esperada en {EVAL_DIR / '.env'})")
            return 1

    args.salida.mkdir(parents=True, exist_ok=True)
    estado = Estado(args.salida)
    # U-B5.3 decisión 8: tope COMPARTIDO entre todos los clientes de la
    # corrida (E1, E3 y reintentos E1), con estado persistido para reanudar.
    # El tope es el global del manifiesto; en stub no hay clientes reales.
    guardian = None
    if not args.stub:
        guardian = PresupuestoCompartido(
            TOPE_GLOBAL_USD, args.salida / "presupuesto_compartido.json")
    t0 = time.time()
    print(f"corrida corpus_v2 | manifiesto={MAN.nombre} | stub={args.stub} "
          f"| tope global=USD {TOPE_GLOBAL_USD} | estimado=USD "
          f"{ESTIMADO_TOTAL_USD} | orden={tos} "
          f"| perfil E1 {PERFIL.nombre} "
          f"| prefijos: E1 {PERFIL.prefijo_hash} E3 {prompt_e3.PREFIJO_HASH}",
          flush=True)

    try:
        for to in tos:
            ck = args.checkpoint_cada or CHECKPOINT_CADA.get(to)
            # ------- fase E1 -------
            if f"{to}:e1" in reabrir and estado.reabrir_fase(f"{to}:e1"):
                print(f"[{to}:e1] reabierta (--reabrir-fase), gasto previo USD "
                      f"{estado.d['fase_actual']['gasto_previo_usd']:.6f}", flush=True)
            if estado.fase_cerrada(f"{to}:e1"):
                print(f"[{to}:e1] ya cerrada — se saltea", flush=True)
            else:
                if args.stub:
                    cli = StubE1Corpus()
                else:
                    restante = TOPE_GLOBAL_USD - estado.gasto_global()
                    cli = cliente_e1.ClienteE1Real(
                        **P_E1, tope_usd=round(restante, 4),
                        run_label=f"corpus_{to}_e1", guardian=guardian,
                        prefijo_hash=PERFIL.prefijo_hash_para_namespace,
                        transmision=PERFIL_R2)
                try:
                    fase_e1(to, cli, estado, args.salida, args.limite,
                            args.abortar_tras, ck)
                finally:
                    cli.close()
            # ------- fase E3 (incluye reintentos E1) -------
            if f"{to}:e3" in reabrir and estado.reabrir_fase(f"{to}:e3"):
                print(f"[{to}:e3] reabierta (--reabrir-fase), gasto previo USD "
                      f"{estado.d['fase_actual']['gasto_previo_usd']:.6f}", flush=True)
            if estado.fase_cerrada(f"{to}:e3"):
                print(f"[{to}:e3] ya cerrada — se saltea", flush=True)
            else:
                if args.stub:
                    c3, c1 = StubE3Corpus(), StubE1Corpus()
                else:
                    restante = TOPE_GLOBAL_USD - estado.gasto_global()
                    c3 = cliente_e3.ClienteE3Real(
                        **P_E3, tope_usd=round(restante, 4),
                        run_label=f"corpus_{to}_e3", guardian=guardian)
                    c1 = cliente_e1.ClienteE1Real(
                        **P_E1, tope_usd=round(restante, 4),
                        run_label=f"corpus_{to}_reintentos_e1",
                        db_path=DB_REINTENTOS_E1, guardian=guardian,
                        prefijo_hash=PERFIL.prefijo_hash_para_namespace,
                        transmision=PERFIL_R2)
                try:
                    fase_e3(to, c3, c1, estado, args.salida, args.limite,
                            args.abortar_tras, ck)
                finally:
                    c3.close()
                    c1.close()
            # ------- E2 del TO (offline) + chequeos -------
            cerrar_e2(to, args.salida, args.limite)
            if PERFIL_R2:
                cerrar_e2_r2(to, args.salida, args.limite)
            for chk in CHEQUEOS_HITS:
                if chk["to"] == to:
                    chequear_hits(to, chk, estado, args.stub)
    except (Freno, cliente_e1.TopeExcedido, cliente_e3.TopeExcedido) as e:
        # el tope compartido (decisión 8) frena duro con TopeExcedido desde
        # cualquier cliente; se trata como Freno: estado persistido, salida 3.
        print(f"\nFRENO: {e}", flush=True)
        estado.persistir()
        return 3
    except IdsRepetidos as e:
        # BKL-0037: error explícito, salida 4, antes de llamar a la API
        print(f"\nERROR: {e}", flush=True)
        estado.persistir()
        return 4

    print(f"\ncorrida completa: gasto global=USD {estado.gasto_global():.4f} "
          f"| wall={round((time.time()-t0)/60, 1)} min", flush=True)
    print("siguiente paso: ensamblar_corpus.py (kg.json global + tests de "
          "respuesta conocida)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
