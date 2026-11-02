#!/usr/bin/env python3
"""correr_b63.py (v2, etapa b1) — El runner de B6.3 (pre-registro FIRMADO, `adf20f3b`, §5, §6 y §7.1). Es b63/correr_b63.py (etapa a),
con su mismo nombre en esta carpeta nueva para que el patrón `correr_b63\\.py` de toda guarda lo siga viendo, y con lo de la etapa b1:

  · el lanzador del lote r5 (agentes/lanzar_lote_paralelo_r5.py y paralelo/guardas_lote_r5.py, importados sin editar;
    NOTA_lanzar_lote_paralelo_r5.md, decisiones de la autora del 26/10/2026, 22:45:52): R5 de la entrada sellada, uno de los dos del
    pre-registro, y el Namespace con la entrada y su sha256;
  · la ventana corrida (decisión del 26/10/2026, 21:58:48: «La ventana corrida: P sesiones a la vez en el orden firmado, y cada
    reintento en el primer lugar libre.»): un lote por pasada, `ventana_b63.LoteVentana`, con todas las sesiones que faltan en el orden
    del §6; los reintentos de una falla de infraestructura los inserta al frente de las pendientes;
  · la opción (d) (la misma decisión: «la sesión queda incompleta, no cuenta como correcta en el análisis principal, sale del de
    sensibilidad y se declara, y el lote frena cuando junta 3 formas desconocidas»): una sesión que termina con una forma de error que
    no es de corte ni una de las formas de infraestructura medidas (formas_reales_b63.json) es `desconocida`; con la tercera, el lote
    frena con el 12;
  · el `pip freeze --all` del venv del banco, el Neo4j de B6.3 (NEO4J_URI y la huella de contenido), la P (1 o 2) y el pico de una
    sesión, en la entrada sellada (comun_b63.cargar_entrada, v2);
  · la guarda de otro paso pago con el patrón de guardas_lote_r5 más `lanzar_lote_paralelo_r5\\.py` y `correr_n6\\.py`, que vale
    también dentro del lote (su guarda lee el patrón del módulo);
  · antes de lanzar y antes de cada bloque, en modo real: la guarda de memoria (memoria_b63; código 13), el control de Docker
    (docker_b63; código 14), y las de otro paso pago (7) y de una extracción (9); antes de lanzar, el Neo4j de B6.3
    (control_neo4j_b63; código 15);
  · la guarda del gasto del agente y el juez juntos, antes de lanzar cada sesión (el gancho de la ventana: espera si corre alguna);
  · el juez de B6.3 con las tres repeticiones de cada respuesta a la vez (juez_b63.TresJueces).
Lo demás, como en la etapa a: los controles previos, la clasificación, el control del disco (11), D-10 antes de cada juicio, el estado
para retomar, `lote_init` y `leer_testigo`. Imprime solo cuentas.

Salidas (--out; por defecto b63/resultados/<modo>/): orden_b63.json, estado_b63.json, fechas_b63.json, resumen_b63.json y, por pasada,
pasada<n>/ con el registro del lote y las carpetas de sus sesiones; el juez, en --juez-dir (por defecto b63/juez/).
Uso: correr_b63.py --entrada <json> --sha256-entrada <hex> --modo real|init [--solo-orden | --solo-controles]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from argparse import Namespace
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b63/v2
BANCO_DIR = AQUI.parent.parent
for _p in (str(AQUI), str(BANCO_DIR), str(BANCO_DIR / "agentes"), str(BANCO_DIR / "paralelo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import comun_b63 as K                        # noqa: E402  (v2)
import juez_b63 as JB                        # noqa: E402  (v2)
import ventana_b63 as V                      # noqa: E402
import memoria_b63 as MEM                    # noqa: E402
import docker_b63 as DK                      # noqa: E402
import control_neo4j_b63 as N4               # noqa: E402

LOTE = V.LOTE                                # agentes/lanzar_lote_paralelo_r5.py (solo import)
G = LOTE.G                                   # paralelo/guardas_lote_r5.py (solo import): el BASE.G del lote
LA = LOTE.LA
PATRON_REAL = G.PATRON_PAGO_REAL             # el de guardas_lote_r5: el del renglón 16, correr_prueba_T_v2 y correr_b63
SUFIJO_B1 = r"|lanzar_lote_paralelo_r5\.py|correr_n6\.py"
PATRON_B1 = PATRON_REAL + SUFIJO_B1          # el que usan las guardas del runner y del lote mientras corre B6.3
EXTRACCION_REAL = G.PATRON_EXTRACCION
PREGUNTA_INIT = "Pregunta de prueba de B6.3 en modo init: sin modelo."
FORMAS = AQUI / "formas_reales_b63.json"
_PRUEBA = {"token": None}


# --------------------------------------------------------------------------------------------------------------------- #
# Las guardas propias                                                                                                   #
# --------------------------------------------------------------------------------------------------------------------- #
def control_patron() -> dict:
    """El patrón real de guardas_lote_r5 trae el del renglón 16 de a2_2/guardas_a2_2.zsh, correr_prueba_T_v2.py y correr_b63.py
    (NOTA_lanzar_lote_paralelo_r5.md, §2.5), y el de la etapa b1 suma los dos nombres nuevos."""
    linea = (BANCO_DIR / "a2_2" / "guardas_a2_2.zsh").read_text(encoding="utf-8").splitlines()[15]
    pat = linea.split("=", 1)[1].strip().strip("'") if linea.startswith("PATRON=") else None
    piezas = PATRON_B1.split("|")
    r16 = pat is not None and all(x in piezas for x in pat.split("|"))
    t, b63 = r"correr_prueba_T_v2\.py" in piezas, r"correr_b63\.py" in piezas
    nuevos = r"lanzar_lote_paralelo_r5\.py" in piezas and r"correr_n6\.py" in piezas
    if not (r16 and t and b63 and nuevos):
        K.frena("el patrón de otro paso pago no trae el renglón 16, correr_prueba_T_v2.py, correr_b63.py o los dos nombres de b1")
    return {"trae_el_renglon_16": r16, "trae_correr_prueba_T_v2": t, "trae_correr_b63": b63,
            "trae_lanzar_lote_paralelo_r5_y_correr_n6": nuevos,
            "patron_real_igual_al_renglon_16_mas_T_y_b63": PATRON_REAL == f"{pat}|correr_prueba_T_v2\\.py|correr_b63\\.py",
            "patron_b1_igual_al_real_mas_los_dos": PATRON_B1 == PATRON_REAL + SUFIJO_B1}


def fijar_patron() -> dict:
    """El patrón de la etapa b1 en guardas_lote_r5 (el módulo que usa el lote), salvo que ya haya uno de prueba."""
    if _PRUEBA["token"] is None:
        G.PATRON_PAGO = PATRON_B1
    return {"patron": G.PATRON_PAGO, "de_prueba": _PRUEBA["token"] is not None}


def fijar_patron_de_prueba(token: str) -> dict:
    """Solo para una prueba: las guardas de otro paso pago y de la extracción buscan un token propio, con la forma del patrón real
    (`<token>\\.py|<token>_b63\\.py`, la de lanzar_lote_paralelo_r5.patron_de_prueba), así ningún `pgrep` de la prueba lleva en su línea
    de comandos un nombre de un paso pago (registro, §122). Frena si el `claude` del PATH no es un CLI falso o si el token nombra un paso
    pago, con el patrón de la etapa b1."""
    v = LOTE.cli_del_path()["version"] or ""
    if "falso" not in v:
        K.frena("el patrón de prueba solo corre con un CLI falso en el PATH")
    if not re.fullmatch(r"[a-z][a-z0-9_]{11,}", token) or re.search(r"lanzar|correr|juez", token) \
            or any(re.search(PATRON_B1, token + s) for s in (".py", "_b63.py")):
        K.frena("el token de prueba no es un token propio (nombra un paso pago o no tiene la forma)")
    _PRUEBA["token"] = token
    G.PATRON_PAGO = LOTE.patron_de_prueba(token)
    G.PATRON_EXTRACCION = r"(^|/)python[0-9.]*\s+(-\S+\s+)*\S*?(" + re.escape(token) + r"_extraccion)\.py(\s|$)"
    return {"patron_de_prueba": G.PATRON_PAGO}


def guarda_otro_paso_pago(cuando: str) -> dict:
    h = G.otro_paso_pago(raiz_lote=os.getpid())
    return {"hora": LOTE.ahora()[1], "evento": "guarda de otro paso pago", "cuando": cuando, "patron": G.PATRON_PAGO, "hallados": h}


def guarda_extraccion(cuando: str) -> dict:
    return {"hora": LOTE.ahora()[1], "evento": "guarda de la extracción", "cuando": cuando, "hallados": G.extraccion_corriendo()}


# --------------------------------------------------------------------------------------------------------------------- #
# La clasificación de una sesión (por código: subtype e is_error del result, los error_status de system/api_retry, y la meta)
# --------------------------------------------------------------------------------------------------------------------- #
def formas_de_infraestructura(ruta: Path = FORMAS) -> list[dict]:
    """Las formas reales de una falla de infraestructura, medidas a USD 0 (formas_error_b63.py; formas_reales_b63.json)."""
    return [f for f in json.loads(Path(ruta).read_text(encoding="utf-8"))["formas"] if f["clase"] == "falla_infra"]


def forma_del_stream(stream: Path) -> dict:
    """Del stream, solo: si hay `result`, su subtype y su is_error, y los error_status de los system/api_retry. Ningún texto."""
    r, status = None, set()
    if stream.is_file():
        for linea in stream.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"result"' not in linea and '"api_retry"' not in linea:
                continue
            try:
                d = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if d.get("type") == "result":
                r = {"subtype": d.get("subtype"), "is_error": bool(d.get("is_error"))}
            elif d.get("type") == "system" and d.get("subtype") == "api_retry":
                status.add(str(d.get("error_status")))
    return {"hay_result": r is not None, "subtype": (r or {}).get("subtype"), "is_error": (r or {}).get("is_error"),
            "api_retry_error_status": sorted(status)}


def coincide(f: dict, conocida: dict) -> bool:
    return (f["hay_result"] == conocida["hay_result"] and f["subtype"] == conocida["subtype"] and f["is_error"] == conocida["is_error"]
            and f["api_retry_error_status"] == conocida["api_retry_error_status"])


def clasificar(s: dict, out_lote: Path, modo: str, timeout_s: float, infra: list[dict]) -> tuple[str, dict | None]:
    """(clase, forma): completa, cortada, falla_infra (una de las formas medidas), desconocida (un error que no es de corte ni de las
    medidas: la opción (d)), incompleta_otra (sin error: un result sin is_error con R3 incompleto, o el plazo del lanzador), no_lanzada o
    init."""
    if s.get("estado") in ("no lanzada", "pendiente"):
        return "no_lanzada", None
    if modo == "init":
        return "init", None
    d = out_lote / s["id"]
    mp = d / f"meta_{s['id']}.json"
    f = forma_del_stream(d / f"stream_{s['id']}.jsonl")
    if not mp.is_file():
        return ("falla_infra" if any(coincide(f, c) for c in infra) else "desconocida"), f
    meta = json.loads(mp.read_text(encoding="utf-8"))
    if meta["completitud_R3"]["completa"]:
        return "completa", f
    if f["hay_result"] and f["subtype"] in K.CORTES:
        return "cortada", f
    if not f["hay_result"] and (meta.get("duracion_s") or 0) >= timeout_s - 1:
        return "incompleta_otra", f
    if any(coincide(f, c) for c in infra):
        return "falla_infra", f
    if f["hay_result"] and not f["is_error"]:
        return "incompleta_otra", f
    return "desconocida", f


def respuesta_de(out_lote: Path, sid: str) -> str | None:
    m = json.loads((out_lote / sid / f"meta_{sid}.json").read_text(encoding="utf-8"))
    r = (m.get("final_json_R4") or {}).get("respuesta")
    return r if isinstance(r, str) and r.strip() else None


# --------------------------------------------------------------------------------------------------------------------- #
# La corrida                                                                                                            #
# --------------------------------------------------------------------------------------------------------------------- #
class CorridaB63:
    def __init__(self, e: dict, preguntas: dict, *, modo: str, via: str = "api", out: Path, sesiones: Path, juez_dir: Path,
                 lotes: Path | None = None, timeout_s: float = 1800.0, client_factory=None, python_juez: str | None = None,
                 medir_memoria=None, control_docker=None, control_neo4j=None, formas: Path = FORMAS):
        self.e, self.preguntas, self.modo, self.via = e, preguntas, modo, via
        self.out, self.sesiones, self.juez_dir = Path(out).resolve(), Path(sesiones).resolve(), Path(juez_dir).resolve()
        self.cache_dir = self.juez_dir / "cache"
        self.lotes = Path(lotes).resolve() if lotes else self.sesiones / "lotes"
        self.timeout_s, self.python_juez = timeout_s, python_juez
        self.client_factory = client_factory or JB.factory_real(self.cache_dir)
        self.jueces = None
        self.medir_memoria = medir_memoria or MEM.memoria_maquina
        self.control_docker = control_docker or DK.control
        self.control_neo4j = control_neo4j or (lambda: N4.estado(e["neo4j"]["huella_contenido"], e["neo4j"]["uri"]))
        self.infra = formas_de_infraestructura(formas)
        self.brazos = sorted(e["brazos"])
        self.P, self.pico = e["P"], float(e["pico_sesion_gb"])
        self.tope, self.freno = float(e["tope_usd"]), float(e["freno_usd"])
        self.orden = K.orden_bloques(e["preguntas"]["ids_en_orden"], e["k"], self.brazos)
        self.por_bloque = {b["bloque"]: b for b in self.orden}
        self.estado_path = self.out / "estado_b63.json"
        self.estado = self.cargar_estado()
        self._ultimo_bloque = None
        self._previo = 0.0

    # --- el estado, para retomar ------------------------------------------------------------------------------------ #
    def cargar_estado(self) -> dict:
        if self.estado_path.is_file():
            st = json.loads(self.estado_path.read_text(encoding="utf-8"))
            if st["entrada_sha256_sin_tope"] != self.e["_sha256_sin_tope"] or st["modo"] != self.modo:
                K.frena("estado_b63.json es de otra entrada (fuera del tope y el freno) o de otro modo: no se retoma")
            if st["entradas"][-1]["sha256"] != self.e["_sha256"]:
                st["entradas"].append({"sha256": self.e["_sha256"], "tope_usd": self.tope, "freno_usd": self.freno,
                                       "desde": LOTE.ahora()[1]})
            return st
        return {"que": "el estado del runner de B6.3 (sin ningún texto)", "version": "v2 (etapa b1)",
                "entrada_sha256_sin_tope": self.e["_sha256_sin_tope"],
                "entradas": [{"sha256": self.e["_sha256"], "tope_usd": self.tope, "freno_usd": self.freno, "desde": LOTE.ahora()[1]}],
                "modo": self.modo, "P": self.P, "bloques": {}, "sesiones": [], "eventos": [], "pasadas": 0, "desconocidas": [],
                "acumulado_agente_guarda_usd": 0.0, "acumulado_agente_R9_usd": 0.0, "codigo": 0, "freno": None}

    def guardar(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        self.estado["actualizado"] = LOTE.ahora()[1]
        self.estado["gasto_juez"] = JB.gasto(self.cache_dir)
        for p, obj in ((self.estado_path, self.estado), (self.out / "fechas_b63.json", K.cuenta_fechas(self.estado["sesiones"])),
                       (self.out / "resumen_b63.json", self.resumen())):
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            tmp.replace(p)

    def evento(self, ev: dict) -> None:
        self.estado["eventos"].append(ev)

    def frenar(self, codigo: int, motivo: str) -> int:
        if not self.estado["codigo"]:
            self.estado["codigo"], self.estado["freno"] = codigo, motivo
        self.evento({"hora": LOTE.ahora()[1], "evento": "freno", "codigo": codigo, "motivo": motivo})
        self.guardar()
        return codigo

    def gastado(self, lote=None) -> float:
        g = self.estado["acumulado_agente_guarda_usd"] + (lote.acumulado_guarda if lote is not None else 0.0)
        return round(g + JB.gasto(self.cache_dir)["usd"], 6)

    def escribir_orden(self) -> Path:
        p = self.out / "orden_b63.json"
        obj = {"semilla": K.SEMILLA_ORDEN, "regla": "por pregunta (en el orden de las olas aprobadas) y por repetición; en cada bloque, "
                                                     "random.Random(f'{semilla}:{id}:{r}').shuffle sobre los brazos ordenados (§6, D-4)",
               "k": self.e["k"], "brazos": self.brazos, "ids_en_orden": self.e["preguntas"]["ids_en_orden"], "bloques": self.orden}
        nuevo = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
        self.out.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.read_text(encoding="utf-8") != nuevo:
            K.frena("orden_b63.json ya existe y difiere del recomputado")
        p.write_text(nuevo, encoding="utf-8")
        return p

    # --- lo que falta correr, en el orden del §6 -------------------------------------------------------------------- #
    def falta(self, b: dict, x: str) -> int | None:
        """El intento que le toca al brazo x del bloque b, o None si ya tiene su clasificación final."""
        st = self.estado["bloques"].get(b["bloque"], {})
        f = (st.get("final") or {}).get(x)
        n = (st.get("intentos_por_brazo") or {}).get(x, 0)
        if f is None or f["clasificacion"] == "no_lanzada":
            return n + 1 if f is None or n else 1
        if f["clasificacion"] == "falla_infra" and n < K.INTENTOS_MAX:
            return n + 1
        return None

    def sesion(self, b: dict, x: str, intento: int) -> dict:
        return {"id": K.id_sesion(b["qid"], b["r"], x, intento), "brazo": x, "bloque": b["bloque"],
                "pregunta": PREGUNTA_INIT if self.modo == "init" else self.preguntas[b["qid"]]["pregunta"],
                "qid": b["qid"], "r": b["r"], "intento": intento}

    def pendientes(self) -> list[dict]:
        out = []
        for b in self.orden:
            for x in b["brazos"]:
                n = self.falta(b, x)
                if n is not None:
                    out.append(self.sesion(b, x, n))
        return out

    # --- los ganchos de la ventana ---------------------------------------------------------------------------------- #
    def antes_de_lanzar(self, L, s: dict, corriendo: int):
        g = self.gastado(L)
        si = g + L.presupuesto * (corriendo + 1)
        if si > self.freno or si > self.tope:
            return ("esperar", f"la guarda del gasto del agente y el juez juntos: {g:.4f} + {L.presupuesto} × {corriendo + 1} pasa el "
                               f"freno {self.freno} o el tope {self.tope}")
        if self.modo == "real" and s["bloque"] != self._ultimo_bloque:
            for ev, cod in ((MEM.guarda(self.P, self.pico, self.medir_memoria), K.MEMORIA),
                            (self.control_docker(self.medir_memoria), K.DOCKER)):
                self.evento({"hora": LOTE.ahora()[1], "antes_del_bloque": s["bloque"], **ev})
                if not ev["ok"]:
                    return (cod, f"{ev['evento']} antes del bloque {s['bloque']}: {ev['motivo']}")
            for ev in (guarda_otro_paso_pago(f"antes del bloque {s['bloque']}"), guarda_extraccion(f"antes del bloque {s['bloque']}")):
                self.evento(ev)
                if ev["hallados"]:
                    cod = G.CODIGO_PAGO if ev["evento"] == "guarda de otro paso pago" else G.CODIGO_EXTRACCION
                    return (cod, f"{ev['evento']} antes del bloque {s['bloque']}: {ev['hallados']}")
        self._ultimo_bloque = s["bloque"]
        return None

    def al_terminar(self, L, s: dict) -> dict:
        info = self._info[s["id"]]
        b = self.por_bloque[info["bloque"]]
        st = self.estado["bloques"].setdefault(b["bloque"], {"final": {}, "intentos_por_brazo": {}, "juez_pendiente": []})
        c, forma = clasificar(s, L.out, self.modo, self.timeout_s, self.infra)
        mp = L.out / s["id"] / f"meta_{s['id']}.json"
        m = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
        cd, vr = m.get("control_disco") or {}, m.get("valor_remoto_por_tool") or {}
        if c != "no_lanzada":
            st["intentos_por_brazo"][s["brazo"]] = info["intento"]
        self.estado["sesiones"].append({
            "id": s["id"], "qid": b["qid"], "r": b["r"], "brazo": s["brazo"], "bloque": b["bloque"], "intento": info["intento"],
            "pasada": self.estado["pasadas"], "posicion_en_el_lote": s["posicion"], "estado_del_lote": s["estado"],
            "fecha": s.get("fecha"), "inicio": s.get("inicio"), "fin": s.get("fin"), "clasificacion": c, "forma": forma,
            "completa_R3": s.get("completa_R3"), "costo_R9_usd": s.get("costo_R9_usd"),
            "costo_para_la_guarda_usd": s.get("costo_para_la_guarda_usd"), "reintentos_api": s.get("reintentos_api"),
            "errores_429": s.get("errores_429"), "version_cli_init": s.get("version_cli_init"), "salida": s.get("salida"),
            "n_llamadas_log_r1": s.get("n_llamadas_log_r1"), "control_disco_frena": cd.get("FRENA"),
            "largo_mayor_utf16": cd.get("largo_mayor_utf16"),
            "valor_remoto": {k: vr.get(k) for k in ("archivo", "existe", "tools_del_banco_con_numero") if k in vr}})
        final = c
        out: dict = {}
        if c == "falla_infra":
            if info["intento"] < K.INTENTOS_MAX:
                nueva = self.sesion(b, s["brazo"], info["intento"] + 1) | {"tras": s["id"]}
                self._info[nueva["id"]] = nueva
                out["insertar"] = [nueva]
            else:
                final = "falla_infra_sin_terminar"
        st["final"][s["brazo"]] = {"clasificacion": final, "id": s["id"], "intento": info["intento"],
                                   "salida": str((L.out / s["id"]).relative_to(self.out))}
        if cd.get("FRENA"):
            out["frenar"] = (K.DISCO, f"un resultado de tool llegó como referencia a un archivo en {s['id']} (control del disco)")
            return out
        if c == "desconocida":
            self.estado["desconocidas"].append({"id": s["id"], "brazo": s["brazo"], "forma": forma})
            if len(self.estado["desconocidas"]) >= 3:
                out["frenar"] = (K.DESCONOCIDAS, f"tres formas desconocidas (la opción (d)): {[x['id'] for x in self.estado['desconocidas']]}")
                return out
        if c == "completa" and self.modo == "real":
            st["juez_pendiente"].append(s["brazo"])
            r = self.juzgar(b, s["brazo"], L)
            if r:
                out["frenar"] = r
        self.guardar()
        return out

    # --- D-10 y el juez de una respuesta --------------------------------------------------------------------------- #
    def juzgar(self, b: dict, x: str, L=None):
        st = self.estado["bloques"][b["bloque"]]
        f = st["final"][x]
        resp = respuesta_de(self.out / f["salida"].rsplit("/", 1)[0], f["id"])
        if resp is None:
            f["clasificacion"] = "incompleta_otra"
            st["juez_pendiente"].remove(x)
            return None
        caso = JB.caso_ciego(b["qid"], x, b["r"], resp, self.preguntas)
        fugas = JB.verificar_pedido(caso, self.brazos)
        if fugas:
            return (K.PRECONDICION, f"fuga en el pedido del juez (no se llamó): {sorted(set(fugas))}")
        tabla = JB.leer_tabla(self.juez_dir)
        fila = tabla["filas"].get(caso["id_opaco"])
        if fila is None or not fila.get("d10"):       # D-10, antes de juzgarla
            tabla["filas"][caso["id_opaco"]] = {"qid": b["qid"], "brazo": x, "r": b["r"], "id_sesion": f["id"], "intento": f["intento"],
                                                 "sha256_respuesta": JB.sha256_texto(resp), "n_criterios": len(caso["criterios"]),
                                                 "d10": JB.contar_d10(resp, JB.marcas_d10(self.e, x))}
            JB.escribir_tabla(self.juez_dir, tabla)
            (self.juez_dir / "d10_b63.json").write_text(json.dumps(JB.resumen_d10(tabla, self.e), ensure_ascii=False, indent=1) + "\n",
                                                        encoding="utf-8")
        if self.jueces is None:
            self.jueces = JB.TresJueces(self.client_factory, self.juez_dir, self.cache_dir)
        agente = self.estado["acumulado_agente_guarda_usd"] + (L.acumulado_guarda if L is not None else 0.0)
        try:
            r = self.jueces.juzgar(caso, agente, self.freno, self.tope)
        except JB.FrenoJuez as ex:
            return (2, f"el juez, en el bloque {b['bloque']}: {ex}")
        except RuntimeError as ex:
            return (K.PRECONDICION, f"el juez, en el bloque {b['bloque']}: {ex}")
        self.evento({"hora": LOTE.ahora()[1], "evento": "juez", "bloque": b["bloque"], "llamadas": r["llamadas"],
                     "errores": r["errores"], "repeticiones_lanzadas_a_la_vez": r.get("lanzadas")})
        st["juez_pendiente"].remove(x)
        return None

    # --- una pasada y todo ------------------------------------------------------------------------------------------ #
    def pasada(self, ses: list[dict]) -> tuple[int, str | None]:
        self.estado["pasadas"] += 1
        n = self.estado["pasadas"]
        self.lotes.mkdir(parents=True, exist_ok=True)
        lote = self.lotes / f"lote_pasada{n}.json"
        if lote.exists():
            K.frena(f"el lote {lote.name} ya existe: una pasada a medio correr no se retoma sola")
        lote.write_text(json.dumps({"sesiones": [{k: s[k] for k in ("id", "brazo", "bloque", "pregunta")} for s in ses]},
                                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        self._info = {s["id"]: s for s in ses}
        g = self.gastado()
        a = Namespace(lote=lote, out=self.out / f"pasada{n}", sesiones=self.sesiones, paralelo=self.P, modo=self.modo, via=self.via,
                      tope=round(max(0.0, self.tope - g), 6), freno=round(max(0.0, self.freno - g), 6), presupuesto_sesion=None,
                      lanzador=K.LANZADOR_SESION, timeout_s=self.timeout_s, config_agentes=K.rel_banco(self.e["_rutas"]["config_agentes"]),
                      entrada=self.e["_ruta"], sha256_entrada=self.e["_sha256"])
        self.evento({"hora": LOTE.ahora()[1], "evento": "pasada", "n": n, "sesiones": len(ses), "gastado_antes": g,
                     "freno_del_lote": a.freno, "tope_del_lote": a.tope, "P": self.P})
        try:
            L = V.LoteVentana(a, antes_de_lanzar=self.antes_de_lanzar, al_terminar=self.al_terminar)
            codigo = L.correr()
            motivo = L.motivo_freno
        except SystemExit as ex:                      # el lote inválido (código 3)
            return LOTE.LOTE_INVALIDO, str(ex)
        reg = json.loads((a.out / "registro_lote.json").read_text(encoding="utf-8"))
        self.estado["acumulado_agente_guarda_usd"] = round(self.estado["acumulado_agente_guarda_usd"] + reg["acumulado_de_la_guarda_usd"], 6)
        self.estado["acumulado_agente_R9_usd"] = round(self.estado["acumulado_agente_R9_usd"] + reg["acumulado_R9_usd"], 6)
        for s in L.sesiones:                          # las que el lote no llegó a lanzar
            if s["estado"] == "no lanzada" and s["id"] in self._info:
                info = self._info[s["id"]]
                st = self.estado["bloques"].setdefault(info["bloque"], {"final": {}, "intentos_por_brazo": {}, "juez_pendiente": []})
                st["final"].setdefault(info["brazo"], {"clasificacion": "no_lanzada", "id": s["id"], "intento": info["intento"],
                                                       "salida": None})
        return codigo, motivo

    def correr(self) -> int:
        self.escribir_orden()
        self.estado["codigo"], self.estado["freno"] = 0, None
        if self.modo == "real":
            n = self.control_neo4j()
            self.evento({"hora": LOTE.ahora()[1], "evento": "control del Neo4j de B6.3", **n})
            if not n["ok"]:
                return self.frenar(K.NEO4J, f"el Neo4j de B6.3: {n['motivo']}")
            for ev in (guarda_otro_paso_pago("antes de la primera sesión"), guarda_extraccion("antes de la primera sesión")):
                self.evento(ev)
                if ev["hallados"]:
                    cod = G.CODIGO_PAGO if ev["evento"] == "guarda de otro paso pago" else G.CODIGO_EXTRACCION
                    for x in ev["hallados"]:
                        print(f"FRENO: {ev['evento']}: pid {x['pid']} ({x['script']})", flush=True)
                    return self.frenar(cod, f"{ev['evento']} antes de la primera sesión: {ev['hallados']}")
            for b in self.orden:                       # lo que quedó sin juzgar (un corte del juez)
                for x in list((self.estado["bloques"].get(b["bloque"]) or {}).get("juez_pendiente") or []):
                    r = self.juzgar(b, x)
                    if r:
                        return self.frenar(*r)
        try:
            while True:
                ses = self.pendientes()
                if not ses:
                    break
                codigo, motivo = self.pasada(ses)
                if codigo:
                    return self.frenar(codigo, f"la pasada {self.estado['pasadas']}: {motivo}")
            if self.modo == "real":
                tabla = JB.leer_tabla(self.juez_dir)
                casos = {i: f["n_criterios"] for i, f in tabla["filas"].items()}
                if casos:
                    (self.juez_dir / "agregados_b63_ciego.json").write_text(
                        json.dumps(JB.agregar(self.juez_dir, casos), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            self.guardar()
            return 0
        finally:
            if self.jueces is not None:
                self.jueces.cerrar()
                self.jueces = None

    def resumen(self) -> dict:
        por = {x: {} for x in self.brazos}
        infra = {x: 0 for x in self.brazos}
        for st in self.estado["bloques"].values():
            for x, f in st["final"].items():
                por[x][f["clasificacion"]] = por[x].get(f["clasificacion"], 0) + 1
        for s in self.estado["sesiones"]:
            if s["clasificacion"] == "falla_infra":
                infra[s["brazo"]] += 1
        tabla = JB.leer_tabla(self.juez_dir)
        h = JB.hechas(self.juez_dir)
        return {"que": "el resumen del runner de B6.3 (v2): solo cuentas, por brazo", "modo": self.modo, "P": self.P,
                "bloques": len(self.orden), "pasadas": self.estado["pasadas"], "final_por_brazo": por,
                "sesiones_con_falla_de_infraestructura_por_brazo": infra, "desconocidas": len(self.estado["desconocidas"]),
                "sesiones_lanzadas": sum(1 for s in self.estado["sesiones"] if s["clasificacion"] != "no_lanzada"),
                "respuestas_en_la_tabla_del_juez": len(tabla["filas"]),
                "repeticiones_del_juez_escritas": {rep: len(v) for rep, v in h.items()},
                "acumulado_agente_guarda_usd": self.estado["acumulado_agente_guarda_usd"],
                "acumulado_agente_R9_usd": self.estado["acumulado_agente_R9_usd"], "gasto_juez_usd": JB.gasto(self.cache_dir)["usd"],
                "codigo": self.estado["codigo"], "freno": self.estado["freno"]}


# --------------------------------------------------------------------------------------------------------------------- #
# Lo que prepara la corrida y lo que llama la etapa b                                                                   #
# --------------------------------------------------------------------------------------------------------------------- #
def preparar_entorno(e: dict) -> dict:
    """BANCO_VENV_VECTOR, de la entrada (nunca de la terminal), y la configuración de agentes para el lanzador de cada sesión."""
    v = str(e["_rutas"]["banco_venv_vector"])
    previa = os.environ.get("BANCO_VENV_VECTOR")
    os.environ["BANCO_VENV_VECTOR"] = v
    os.environ["B63_CONFIG_AGENTES"] = str(e["_rutas"]["config_agentes"])
    os.environ["B63_CONFIG_AGENTES_SHA256"] = e["config_agentes"]["sha256"]
    os.environ["B63_VENV_PYTHON"] = e["banco_venv_vector"]["python"]
    return {"banco_venv_vector": v.replace(str(Path.home()), "$HOME"), "python": e["banco_venv_vector"]["python"],
            "en_la_terminal_habia": previa is not None, "igual_al_de_la_terminal": previa == v if previa is not None else None}


def controles(entrada: Path, sha: str, modo: str, python_juez: str | None = None) -> tuple[dict, dict, dict]:
    """Todos los controles previos, sin lanzar nada: (entrada, preguntas, registro de los controles)."""
    e = K.cargar_entrada(entrada, sha)
    preguntas = K.cargar_preguntas(e)
    if os.environ.get("NEO4J_URI") != e["neo4j"]["uri"]:
        K.frena(f"NEO4J_URI del entorno no es el de la entrada ({e['neo4j']['uri']}): el servidor del grafo tiene que apuntar ahí",
                K.NEO4J)
    reg = {"entrada_sha256": e["_sha256"], "patron": control_patron(), "patron_fijado": fijar_patron(),
           "juez": JB.controlar_instrumento(e), "entorno": preparar_entorno(e), "n_preguntas": len(preguntas), "k": e["k"],
           "brazos": sorted(e["brazos"]), "P": e["P"], "pico_sesion_gb": e["pico_sesion_gb"], "neo4j_uri": e["neo4j"]["uri"]}
    if modo == "real":
        reg["sdk"] = JB.control_sdk(python_juez)     # el primer control del paso pago del juez (§7.1)
    return e, preguntas, reg


def lote_init(e: dict, out: Path, sesiones: Path, lotes: Path | None = None, n: int = 1, config_agentes: dict | None = None) -> dict:
    """El lote de referencia en modo init, por el camino del runner (CorridaB63.pasada, la ventana): n tandas de una sesión por brazo,
    con ids B63-I<t>-r1-<brazo> y la pregunta de prueba PREGUNTA_INIT. config_agentes ({ruta, sha256}, dentro del banco) cambia la
    configuración de agentes, con sus brazos (el testigo arma sus sesiones con la de prueba de N6)."""
    if config_agentes is not None:
        p = K.sello(config_agentes, "config_agentes del lote init")
        cfg = json.loads(p.read_text(encoding="utf-8"))
        if not p.resolve().is_relative_to(K.BANCO_DIR.resolve()) or not cfg.get("claude_code_version_sellada"):
            K.frena("config_agentes del lote init: fuera del banco o sin claude_code_version_sellada")
        e = e | {"config_agentes": config_agentes, "_rutas": {**e["_rutas"], "config_agentes": p}, "_cfg": cfg,
                 "brazos": {b: {"rol": None} for b in cfg["brazos"]}}
    preparar_entorno(e)
    ids = [f"I{t}" for t in range(1, n + 1)]
    c = CorridaB63(e | {"preguntas": {**e["preguntas"], "ids_en_orden": ids}, "k": 1}, {}, modo="init", out=out, sesiones=sesiones,
                   juez_dir=Path(out) / "sin_juez", lotes=lotes)
    codigo, motivo = c.pasada(c.pendientes())
    c.guardar()
    return {"codigo": codigo, "motivo": motivo, "salida": str(c.out / f"pasada{c.estado['pasadas']}"),
            "ids": [s["id"] for s in c.estado["sesiones"]]}


FECHA_EN_EL_TESTIGO = re.compile(r"^(?P<id>.+), pedido (?P<n>\d+) \((?P<tipo>[^)]*)\), `(?P<campo>[^`]+)`: la fecha del día "
                                 r"\((?P<k>\d+) apariciones\)$")


def leer_testigo(res: dict) -> dict:
    """El resultado del testigo (aislamiento/testigo_aislamiento.py, fase_testigo), leído para B6.3 sin cambiar el testigo: sus
    renglones de FRENO por la fecha del día en un pedido son lo que la decisión de la autora del 26/10/2026 declara («El agente recibe
    la fecha del día en su pedido: la pone el CLI.»), y se cuentan por campo y por tipo de pedido; cualquier otro renglón de FRENO
    sigue siendo un FRENO. El PASS de B6.3 es el del testigo sin los renglones de la fecha."""
    fechas, otros = [], []
    for l in res.get("FRENO") or []:
        m = FECHA_EN_EL_TESTIGO.match(l)
        (fechas if m else otros).append(m.groupdict() if m else l)
    ps = res.get("por_sesion") or {}
    resto = (all(r.get("tools_PASS") and (r.get("comparacion_con_init") or {}).get("PASS") and r.get("cwd_vacio") for r in ps.values())
             and bool(ps) and (res.get("testigos_despues") or {}).get("iguales") and (res.get("testigos_despues") or {}).get("plantados_borrados")
             and (res.get("cwd_al_final") or {}).get("vacio") and res.get("ningun_pedido_al_modelo_sale_de_la_maquina"))
    por = {}
    for f in fechas:
        k = f"{f['tipo']}|{f['campo']}"
        por[k] = por.get(k, 0) + 1
    return {"renglones_de_la_fecha": len(fechas), "sesiones_con_la_fecha": len({f["id"] for f in fechas}),
            "fecha_por_tipo_y_campo": dict(sorted(por.items())), "otros_FRENO": otros,
            "PASS_de_B63": bool(resto) and not otros, "PASS_del_testigo_tal_cual": bool(res.get("PASS"))}


def juez_prohibido(rep: int, label: str):
    """La fábrica del juez con el patrón de prueba: en una prueba no hay juez real (ningún pedido a la API)."""
    K.frena("con el patrón de prueba no hay juez real: la prueba no tiene que llegar a juzgar")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, required=True)
    ap.add_argument("--sha256-entrada", required=True)
    ap.add_argument("--modo", choices=["real", "init"], required=True)
    ap.add_argument("--via", choices=["api", "bedrock"], default="api")
    ap.add_argument("--out", type=Path, default=None, help="por defecto b63/resultados/<modo>/")
    ap.add_argument("--sesiones", type=Path, default=K.SESIONES)
    ap.add_argument("--juez-dir", type=Path, default=K.JUEZ_DIR)
    ap.add_argument("--lotes", type=Path, default=None, help="los lotes del lanzador del lote (fuera del repo); por defecto <sesiones>/lotes")
    ap.add_argument("--timeout-s", type=float, default=1800.0)
    ap.add_argument("--solo-orden", action="store_true")
    ap.add_argument("--solo-controles", action="store_true")
    ap.add_argument("--patron-de-prueba", default=None, help="solo con un CLI falso: el token de las guardas (corrida en seco)")
    a = ap.parse_args(argv)
    try:
        if a.patron_de_prueba:
            fijar_patron_de_prueba(a.patron_de_prueba)
        e, preguntas, reg = controles(a.entrada, a.sha256_entrada, a.modo)
        out = a.out or (K.RESULTADOS / a.modo)
        c = CorridaB63(e, preguntas, modo=a.modo, via=a.via, out=out, sesiones=a.sesiones, juez_dir=a.juez_dir, lotes=a.lotes,
                       timeout_s=a.timeout_s, client_factory=juez_prohibido if a.patron_de_prueba else None)
        c.evento({"hora": LOTE.ahora()[1], "evento": "controles", **{k: v for k, v in reg.items() if k != "juez"}})
        if a.solo_orden or a.solo_controles:
            c.escribir_orden()
            print(json.dumps({"controles": "OK", "bloques": len(c.orden), "preguntas": len(preguntas), "k": e["k"]}), flush=True)
            return 0
        codigo = c.correr()
    except K.FrenoB63 as ex:
        print(f"FRENO DE PRECONDICIÓN ({ex.codigo}): {ex}", flush=True)
        return ex.codigo
    r = c.resumen()
    print(json.dumps({k: r[k] for k in ("modo", "P", "bloques", "pasadas", "final_por_brazo", "desconocidas", "sesiones_lanzadas",
                                        "codigo", "freno")}, ensure_ascii=False), flush=True)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
