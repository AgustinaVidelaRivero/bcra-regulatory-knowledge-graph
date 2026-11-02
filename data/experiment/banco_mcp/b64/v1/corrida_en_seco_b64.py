#!/usr/bin/env python3
"""corrida_en_seco_b64.py (b64/v1, B6.4) — La corrida en seco del runner de B6.4 (H-4; pre-registro FIRMADO, `55ee1a5a`, §4 y §6), a
USD 0 y sin ningún dato real. Es la de B6.3 (b63/v2/b2/corrida_en_seco_b63.py) sobre el runner de esta carpeta, con sus ramas S1 a S15
recorridas con cuatro brazos, y con las de B6.4 (N0 a N9).

Como la de B6.3: importa el runner (correr_b63.py, de su misma carpeta: ningún arreglo del sys.path por fuera, el mismo camino de imports
que la corrida real) y llama a sus funciones, en modo real, con el CLI falso de B6.3 primero en el PATH y una clave de relleno: cada lote
recorre el camino real (la ventana, el lanzador del lote, el lanzador de la sesión de esta carpeta, el de N6, `claude`, el servidor MCP de
juguete de la sesión, la meta completa y la meta sin texto) y ninguna petición sale a la API: el juez es el de EV2 sobre un transporte
simulado. Su guarda, antes de todo, la de otro paso pago con el patrón real (correr_b63.PATRON_B1); después, las guardas buscan un token
propio. Las corridas usan la configuración de juguete de cuatro brazos (seco/config_agentes_b64_juguete.json: kg, kg_n7,
fragmentos_bm25 y fragmentos_denso, con los roles de B6.4) y las preguntas de juguete de B6.3 pasadas al esquema de las aprobadas de
B6.4 (seco/herramientas_b64.py). La entrada de B6.4 con la configuración real de los cuatro brazos (config_agentes_b64.json) la arma
armar_entrada_B64.py sobre 96 preguntas aprobadas DE JUGUETE, y la prueban los controles del runner, el orden, los ids, D-10 y el juez,
sin lanzar ninguna sesión con ella (lanzarla levantaría los servidores reales).

Las ramas de B6.3, con cuatro brazos (S1 a S15; las cuentas, las de cuatro brazos):
  S1  la ventana con P = 1: el orden firmado y cada reintento enseguida de su falla; el juez de a tres en cada respuesta;
  S2  la ventana con P = 2;  S3 los reintentos;  S4 la opción (d);  S5 y S6 la clave inválida con P = 1 y con P = 2, y retomar;
  S7  los cortes;  S8 la guarda del gasto;  S9 los ganchos de memoria, Docker y Neo4j;  S10 retomar sin repetir;
  S11 la meta sin texto y el stream en la meta;  S12 el comando con env -i (comando_b64.zsh);
  S14 el juez fuera del repo;  S15 la salida del juez que no se lee;  S13, al final, ninguna otra línea de comandos con un guion del
      patrón y ningún pgrep con el patrón real después de la guarda.
Las de B6.4:
  N0  el runner de B6.3 de HEAD, sin cambios, no corre los cuatro brazos: su comun_b63 frena en el control de los roles (con los tres de
      B6.3 pasa: el control positivo) y su juez no encuentra el rol del cuarto; el de esta carpeta importa lo común, el juez y el
      lanzador de su carpeta, y la ventana, la memoria, Docker y el Neo4j de b63/v2/b2;
  N1  el orden de cuatro brazos: por pregunta y por repetición, los brazos de cada bloque seguidos y sorteados con la semilla de B6.3
      (D-4), recomputado aparte; las sesiones de cada pregunta, seguidas; con la entrada de B6.4 (288 bloques) y en la ventana;
  N2  un id por brazo: los 1.152 de la entrada de B6.4, distintos (también sin distinguir mayúsculas), con la forma B63-<id>-r<r>-<brazo>
      y admitidos por el lote; el CLI falso lee el brazo de cada uno, también con -i2 y -i3;
  N3  el juez de a tres en cada respuesta de los cuatro brazos: tres por brazo en la tabla, tres repeticiones a la vez en cada una, y los
      agregados;
  N4  la cuenta de D-10 por brazo: los cuatro, sin editar ninguna respuesta; las marcas de kg_n7, las del grafo (sus herramientas y la
      forma de cita, de `marcas_d10` de la entrada), en la de juguete y en la de B6.4; y el control positivo (las respuestas del CLI
      falso no traen marcas): una respuesta con un nodo y una herramienta del grafo da las mismas marcas con las de kg_n7 que con las
      de kg, y una con un pasaje, ninguna de kg_n7 y sí las de fragmentos;
  N5  la cuenta por fecha con cuatro brazos: cada brazo con sus sesiones (también los reintentos), y un bloque de cuatro brazos con dos
      fechas, detectado;
  N6  el freno del gasto en 115 y el tope en 144: la entrada de B6.4 los trae; la guarda de antes de cada sesión, en el borde (con P = 1
      y con P = 2); una corrida que llega al freno de 115 y otra al tope de 144 frenan con el 2 sin pasarlos; el juez, en el borde de 115;
  N7  ninguna salida en el repo: con --out, --juez-dir, --sesiones, --lotes o la carpeta de los originales dentro del repo, el modo real
      frena con el 10 sin escribir nada; también con --solo-controles y --out en el repo (con todo fuera, el control positivo, pasa);
  N8  la entrada de juguete armada con armar_entrada_B64.py, la normal y la del humo: pasan los controles del runner (cargar_entrada,
      cargar_preguntas y `controles`), con lo de B6.3 tal cual; el armador frena con el sha256, el N, un campo y un id repetido, sin
      escribir; y ni su consola ni sus entradas traen el texto de una pregunta, un criterio o una cita;
  N9  el control de la entrada del juez (§5): lo que recibe el juez de una respuesta de kg_n7 se arma igual que el de los otros tres y no
      lleva el nombre de ningún brazo (verificar_pedido, el control que corre el runner antes de cada juicio; el control positivo, con un
      nombre de brazo en un criterio).
El resultado (--resultado), solo cuentas y banderas, sin horas ni rutas; imprime una línea por rama.

Uso, desde la raíz de una copia del repo (frena si encuentra .git ahí):
  <python del .venv del repo> -B data/experiment/banco_mcp/b64/v1/corrida_en_seco_b64.py --tmp <dir> --resultado <json>
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import correr_b63 as R                                       # noqa: E402  (el runner de B6.4, de esta misma carpeta)
from seco import herramientas_b64 as H                       # noqa: E402
import lanzar_agente_b63 as LZ                               # noqa: E402  (las listas de campos de la meta sin texto)
import armar_entrada_B64 as AE                               # noqa: E402  (sus constantes; el armador se corre como lo corre la autora)

K, JB, LOTE, G, LA = R.K, R.JB, R.LOTE, R.G, R.LA
J = sys.modules["juez"]
TOKEN = "prueba_b64_seco_qv8wn3t5"                            # un token propio: no nombra ningún paso pago
LINEAS: list[list[str]] = []
B2_SECO = H.B63 / "v2" / "b2" / "seco"
CLI_FALSO = B2_SECO / "claude_falso_b63.py"
TAG_DEL_CLI_FALSO = r"^B63-(?P<q>.+)-r(?P<r>\d+)-(?P<brazo>.+?)(?:-i(?P<i>\d+))?$"   # el de claude_falso_b63.py (lo controla N2)
BRAZOS_B64 = ("kg", "kg_n7", "fragmentos_hibrida", "fragmentos_denso")
RES: list[dict] = []


class Registrador:
    """En lugar del módulo subprocess de un módulo: anota la línea de comandos de cada run y Popen, y delega."""

    def __getattr__(self, n):
        return getattr(subprocess, n)

    def run(self, argv, *a, **kw):
        LINEAS.append(list(map(str, argv)))
        return subprocess.run(argv, *a, **kw)

    def Popen(self, argv, *a, **kw):                     # noqa: N802
        LINEAS.append(list(map(str, argv)))
        return subprocess.Popen(argv, *a, **kw)


def rama(nombre: str, que: str):
    def deco(f):
        try:
            ok, detalle = f()
        except Exception as ex:                       # noqa: BLE001
            ok, detalle = False, {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
        RES.append({"rama": nombre, "que": que, "PASS": bool(ok), **(detalle or {})})
        return f
    return deco


def por_nombre(n: str) -> bool:
    return "_SOLO_MESA" in n or n.startswith("NO_ABRIR_")


def foto() -> dict:
    """Los archivos de la copia del repo, por su ruta, su tamaño y su fecha (sin leerlos; sin bajar a una carpeta *_SOLO_MESA* o
    NO_ABRIR_*, que entra solo por su nombre)."""
    out = {}
    for d, subs, nombres in os.walk(K.REPO_DIR, followlinks=False):
        out.update({os.path.relpath(os.path.join(d, s), K.REPO_DIR): "carpeta por nombre" for s in subs if por_nombre(s)})
        subs[:] = [s for s in subs if not por_nombre(s) and s != "__pycache__"]
        for n in nombres:
            st = os.lstat(os.path.join(d, n))
            out[os.path.relpath(os.path.join(d, n), K.REPO_DIR)] = (st.st_size, st.st_mtime_ns)
    return out


def cargar_de(ruta: Path, nombre: str):
    """Un módulo de HEAD cargado por su ruta con otro nombre, solo para comparar (N0): no entra en el camino del runner."""
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def correr_ramas(TMP: Path) -> None:
    falso = TMP / "bin"
    falso.mkdir(parents=True, exist_ok=True)
    (falso / "claude").write_text(f'#!/bin/sh\nexec "{sys.executable}" -B "{CLI_FALSO}" "$@"\n', encoding="utf-8")
    (falso / "claude").chmod(0o755)
    path0 = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{falso}:{path0}"
    os.environ["NEO4J_URI"] = "bolt://127.0.0.1:47687"
    os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_DE_RELLENO
    R.fijar_patron_de_prueba(TOKEN)
    preg_seco = H.a_esquema_b64(B2_SECO / "preguntas_seco_b2.json", TMP / "preguntas" / "preguntas_seco_b64.json")
    preg_meta = H.a_esquema_b64(B2_SECO / "preguntas_meta_b63.json", TMP / "preguntas" / "preguntas_meta_b64.json")

    def corrida(nombre: str, ids: list[str], P: int = 1, freno: float = 40.0, tope: float = 50.0, pedidos: list | None = None,
                **kw) -> R.CorridaB63:
        ent, s = H.entrada_b64(TMP, nombre, ids, preguntas=kw.get("preguntas", preg_seco), P=P, freno=freno, tope=tope)
        e = K.cargar_entrada(ent, s)
        preg = K.cargar_preguntas(e)
        R.preparar_entorno(e)
        base = TMP / nombre
        juez_dir = kw.get("juez_dir", base / "juez")
        return R.CorridaB63(e, preg, modo="real", out=kw.get("out", base / "out"), sesiones=kw.get("sesiones", base / "ses"),
                            juez_dir=juez_dir, lotes=kw.get("lotes", base / "lotes"),
                            client_factory=H.juez_simulado(juez_dir / "cache", pedidos if pedidos is not None else []),
                            medir_memoria=kw.get("medir", lambda: {"en_uso_gb": 5.0, "swap_usado_gb": 0.1}),
                            control_docker=kw.get("docker", lambda m=None: {"evento": "control de Docker", "ok": True, "motivo": None}),
                            control_neo4j=kw.get("neo4j", lambda: {"ok": True, "motivo": None}))

    def registro(c: R.CorridaB63, n: int) -> dict:
        return json.loads((c.out / f"pasada{n}" / "registro_lote.json").read_text(encoding="utf-8"))

    def lanzados(c: R.CorridaB63, n: int | None = None) -> list[str]:
        return [e["id"] for k in ([n] if n else range(1, c.estado["pasadas"] + 1)) for e in registro(c, k)["eventos"]
                if e["evento"] == "lanza"]

    def finales(c: R.CorridaB63) -> dict:
        return {f"{b}|{x}": f["clasificacion"] for b, st in c.estado["bloques"].items() for x, f in st["final"].items()}

    # La entrada de B6.4 con la configuración real de los cuatro brazos, armada por armar_entrada_B64.py sobre 96 aprobadas de juguete
    real: dict = {}
    aprob, sha_aprob = H.aprobadas_de_juguete(TMP / "aprobadas" / "preguntas_aprobadas_juguete.json")
    sal_real = TMP / "entrada_real" / "entrada_B64.json"

    def armador(preguntas: Path, sha: str, salida: Path, humo: bool = True) -> subprocess.CompletedProcess:
        argv = [sys.executable, "-B", str(AQUI / "armar_entrada_B64.py"), "--preguntas", str(preguntas), "--sha256-preguntas", sha,
                "--salida", str(salida)] + (["--humo"] if humo else [])
        LINEAS.append(argv)
        return subprocess.run(argv, capture_output=True, text=True)

    real["armado"] = armador(aprob, sha_aprob, sal_real)
    if real["armado"].returncode == 0:
        real["e"] = K.cargar_entrada(sal_real, H.sha(sal_real))
        real["preg"] = K.cargar_preguntas(real["e"])
        real["humo"] = K.cargar_entrada(sal_real.parent / AE.HUMO, H.sha(sal_real.parent / AE.HUMO))

    pedidos_s1: list = []
    s1 = corrida("s1_p1", ["SEC01", "SEC02", "SEC03"], pedidos=pedidos_s1)

    @rama("S1", "la ventana con P = 1, un reintento enseguida de su falla, y el juez de a tres (cuatro brazos)")
    def _():
        cod = s1.correr()
        ids = lanzados(s1)
        esperado = []
        for b in s1.orden:
            for x in b["brazos"]:
                esperado.append(K.id_sesion(b["qid"], 1, x))
                if b["qid"] == "SEC02":
                    esperado.append(K.id_sesion(b["qid"], 1, x, 2))
        juez = [e for e in s1.estado["eventos"] if e.get("evento") == "juez"]
        ns = {}
        for rep in JB.REPS:
            con = sqlite3.connect(str(JB.db_path(rep, s1.cache_dir)))
            ns[rep] = sorted({x[0] for x in con.execute("SELECT namespace FROM cache")})
            con.close()
        sin_cruces = all(ns[rep] == [J.lc.make_namespace(f"juez_ev2_r{rep}", code_ver=J.CODE_VER, thinking=False)] for rep in JB.REPS)
        ok = (cod == 0 and ids == esperado and len(ids) == 16 and set(finales(s1).values()) == {"completa"}
              and len(JB.leer_tabla(s1.juez_dir)["filas"]) == 12 and len(juez) == 12
              and all(e["repeticiones_lanzadas_a_la_vez"] == [1, 2, 3] for e in juez) and sin_cruces and len(pedidos_s1) == 36)
        return ok, {"codigo": cod, "lanzadas": len(ids), "en_el_orden_firmado_con_el_reintento_enseguida": ids == esperado,
                    "finales": sorted(set(finales(s1).values())), "respuestas_juzgadas": len(juez), "pedidos_al_transporte": len(pedidos_s1),
                    "una_base_y_un_namespace_por_repeticion": sin_cruces}

    @rama("S2", "la ventana con P = 2")
    def _():
        c = corrida("s2_p2", ["SEC01", "SEC02", "SEC03"], P=2)
        cod = c.correr()
        ev = registro(c, 1)["eventos"]
        maximo = max(e["corriendo_con_ella"] for e in ev if e["evento"] == "lanza")
        frente = all(next(x for x in ev[i + 1:] if x["evento"] == "lanza")["id"] == e["ids"][0]
                     for i, e in enumerate(ev) if e["evento"] == "inserta")
        n_ins = sum(1 for e in ev if e["evento"] == "inserta")
        return (cod == 0 and maximo == 2 and frente and n_ins == 4 and set(finales(c).values()) == {"completa"}), \
            {"codigo": cod, "maximo_a_la_vez": maximo, "reintentos_insertados": n_ins, "cada_reintento_al_frente": frente}

    @rama("S3", "los reintentos: la forma real del 500 en los tres intentos")
    def _():
        c = corrida("s3_infra3", ["SEC04"])
        cod = c.correr()
        st = c.estado["bloques"]["SEC04-r1"]
        return (cod == 0 and set(v["clasificacion"] for v in st["final"].values()) == {"falla_infra_sin_terminar"}
                and set(st["intentos_por_brazo"].values()) == {3} and len(st["final"]) == 4 and len(lanzados(c)) == 12), \
            {"codigo": cod, "lanzadas": len(lanzados(c)), "intentos_por_brazo": sorted(set(st["intentos_por_brazo"].values()))}

    @rama("S4", "la opción (d): tres formas desconocidas")
    def _():
        c = corrida("s4_opcion_d", ["SEC05", "SEC01"])
        cod = c.correr()
        return (cod == K.DESCONOCIDAS and len(c.estado["desconocidas"]) == 3 and len(lanzados(c)) == 3), \
            {"codigo": cod, "desconocidas": len(c.estado["desconocidas"]), "lanzadas": len(lanzados(c))}

    def clave(nombre: str, P: int, antes_de: int) -> tuple[bool, dict]:
        ids = ["SEC01", "SEC03", "SEC08"]
        c = corrida(nombre, ids, P=P)
        gancho, cuenta = c.antes_de_lanzar, {"n": 0}

        def antes(L, s, corriendo):                    # la clave pasa a la inválida antes de la sesión `antes_de` (solo en la prueba)
            r = gancho(L, s, corriendo)
            if r is None:
                cuenta["n"] += 1
                if cuenta["n"] == antes_de:
                    os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_INVALIDA_DE_RELLENO
            return r
        c.antes_de_lanzar = antes
        cod = c.correr()
        p1 = lanzados(c, 1)
        reg = registro(c, 1)
        ev = reg["eventos"]
        i_freno = next(i for i, e in enumerate(ev) if e["evento"] == "freno")
        tras = [e["id"] for e in ev[i_freno + 1:] if e["evento"] == "termina"]
        lanza_tras = [e["id"] for e in ev[i_freno + 1:] if e["evento"] == "lanza"]
        malas = [x["id"] for x in c.estado["clave_invalida"]]
        contadas = {s["id"] for s in c.estado["sesiones"]}
        juzgadas = {f["id_sesion"] for f in JB.leer_tabla(c.juez_dir)["filas"].values()}
        en_final = {f["id"] for st in c.estado["bloques"].values() for f in st["final"].values()}
        no_cuenta = [s["id"] for s in reg["sesiones"] if s.get("no_cuenta")]
        os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_DE_RELLENO
        r = corrida(nombre, ids, P=P)                  # retomar: el mismo estado, con la clave buena
        cod2 = r.correr()
        p2 = lanzados(r, 2)
        n_final = sum(len(st["final"]) for st in r.estado["bloques"].values())
        esperadas = (4, 1, 0) if P == 1 else (2, 2, 1)         # lanzadas, de la clave inválida, terminadas después del freno
        ok = (cod == K.CLAVE_INVALIDA and (len(p1), len(malas), len(tras)) == esperadas and sorted(malas) == sorted(no_cuenta)
              and not lanza_tras and not set(malas) & (contadas | juzgadas | en_final) and set(tras) <= contadas | set(malas)
              and cod2 == 0 and set(malas) <= set(p2) and not set(p2) & contadas and len(p1) + len(p2) == 12 + len(malas)
              and n_final == 12 and set(finales(r).values()) == {"completa"} and len(JB.leer_tabla(r.juez_dir)["filas"]) == 12)
        return ok, {"codigo": cod, "lanzadas_antes_del_freno": len(p1), "con_la_clave_invalida": len(malas),
                    "terminadas_despues_del_freno": len(tras), "lanzadas_despues_del_freno": len(lanza_tras),
                    "la_de_la_clave_invalida_en_las_cuentas": bool(set(malas) & (contadas | juzgadas | en_final)),
                    "codigo_al_retomar": cod2, "lanzadas_al_retomar": len(p2), "repetidas_al_retomar": len(set(p2) & contadas),
                    "finales": n_final, "respuestas_juzgadas": len(JB.leer_tabla(r.juez_dir)["filas"])}

    @rama("S5", "la clave inválida con P = 1, y retomar con la clave buena")
    def _():
        return clave("s5_clave_p1", 1, 4)

    @rama("S6", "la clave inválida con P = 2, y retomar con la clave buena")
    def _():
        return clave("s6_clave_p2", 2, 1)

    @rama("S7", "los cortes, por --max-turns y por el presupuesto")
    def _():
        c = corrida("s7_cortes", ["SEC06", "SEC07"])
        cod = c.correr()
        fin = finales(c)
        cortadas = sorted(k for k, v in fin.items() if v == "cortada")
        ids_cortadas = {c.estado["bloques"][k.split("|")[0]]["final"][k.split("|")[1]]["id"] for k in cortadas}
        juzgadas = {f["id_sesion"] for f in JB.leer_tabla(c.juez_dir)["filas"].values()}
        return (cod == 0 and cortadas == ["SEC06-r1|kg", "SEC07-r1|fragmentos_bm25"] and not ids_cortadas & juzgadas
                and sorted(fin.values()).count("completa") == 6 and len(juzgadas) == 6), \
            {"codigo": cod, "cortadas": cortadas, "completas": sorted(fin.values()).count("completa"),
             "respuestas_juzgadas": len(juzgadas), "alguna_cortada_juzgada": bool(ids_cortadas & juzgadas)}

    @rama("S8", "la guarda del gasto del agente y el juez juntos")
    def _():
        pedidos: list = []
        c = corrida("s8_gasto", ["SEC01"], freno=1.85, tope=2.0, pedidos=pedidos)
        cod = c.correr()
        return (cod == 2 and len(lanzados(c)) == 2 and len(pedidos) == 6), {"codigo": cod, "lanzadas": len(lanzados(c)),
                                                                          "pedidos_al_transporte": len(pedidos)}

    @rama("S9", "los ganchos: memoria, Docker y Neo4j")
    def _():
        m = corrida("s9_mem", ["SEC01"], medir=lambda: {"en_uso_gb": 13.0, "swap_usado_gb": 0.1})
        d = corrida("s9_docker", ["SEC01"], docker=lambda mm=None: {"evento": "control de Docker", "ok": False, "motivo": "doble"})
        n = corrida("s9_neo4j", ["SEC01"], neo4j=lambda: {"ok": False, "motivo": "doble"})
        cods = (m.correr(), d.correr(), n.correr())
        lz = [len(lanzados(x)) if x.estado["pasadas"] else 0 for x in (m, d, n)]
        return cods == (K.MEMORIA, K.DOCKER, K.NEO4J) and lz == [0, 0, 0], {"codigos": list(cods), "lanzadas": lz}

    @rama("S10", "retomar sin repetir: la corrida de S1, otra vez")
    def _():
        antes = s1.estado["pasadas"]
        c = corrida("s1_p1", ["SEC01", "SEC02", "SEC03"])
        cod = c.correr()
        return cod == 0 and c.estado["pasadas"] == antes, {"codigo": cod, "pasadas_nuevas": c.estado["pasadas"] - antes}

    @rama("S11", "la meta sin texto y el stream en la meta, en cada sesión de S1")
    def _():
        n, malas = 0, []
        for s in s1.estado["sesiones"]:
            d = s1.out / f"pasada{s['pasada']}" / s["id"]
            mc, ms, st = d / f"meta_{s['id']}.json", d / f"meta_sin_texto_{s['id']}.json", d / f"stream_{s['id']}.jsonl"
            m, sn = json.loads(mc.read_text(encoding="utf-8")), json.loads(ms.read_text(encoding="utf-8"))
            ok = (tuple(sn) == LZ.CLAVES_SIN_TEXTO and sn["meta_completa"]["sha256"] == H.sha(mc)
                  and m["stream"]["sha256"] == H.sha(st) and sn["stream"] == m["stream"]
                  and all("input" not in x for x in sn["mapa_R7"]) and sn["unidad"] == LZ.UNIDAD)
            n += 1
            if not ok:
                malas.append(s["id"])
        return n == 16 and not malas, {"sesiones": n, "con_algo_que_no_da": len(malas)}

    @rama("S12", "el comando con env -i: el runner por el comando con LANG=es_AR.UTF-8 pasa sus controles; sin el comando, frena con el 10")
    def _():
        ent, s = H.entrada_b64(TMP, "s12_comando", ["SEC01"], preguntas=preg_seco)
        padre = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "LANG": "es_AR.UTF-8", "VARIABLE_DE_LA_TERMINAL_B64": "x",
                 "ANTHROPIC_API_KEY": H.CLAVE_DE_RELLENO, "B63_PYTHON": sys.executable}   # B63_PYTHON: la copia no trae el .venv
        resto = ["--modo", "init", "--solo-controles", "--patron-de-prueba", TOKEN, "--out", str(TMP / "s12_comando" / "out"),
                 "--sesiones", str(TMP / "s12_comando" / "ses"), "--juez-dir", str(TMP / "s12_comando" / "juez")]
        argv = ["zsh", str(AQUI / "comando_b64.zsh"), "correr", str(ent), s] + resto
        LINEAS.append(argv)
        a = subprocess.run(argv, env=padre, capture_output=True, text=True)
        nombres = next((l.split("env -i con ", 1)[1] for l in a.stdout.splitlines() if l.startswith("comando_b64: env -i con ")), None)
        directo = [sys.executable, "-B", str(AQUI / "correr_b63.py"), "--entrada", str(ent), "--sha256-entrada", s] + resto
        LINEAS.append(directo)
        b = subprocess.run(directo, env=padre | {"NEO4J_URI": "bolt://127.0.0.1:47687"}, capture_output=True, text=True)
        controles_ok = a.returncode == 0 and '"controles": "OK"' in a.stdout
        frena_10 = b.returncode == K.PRECONDICION and "la medición de memoria no anda" in b.stdout
        return (controles_ok and nombres == "PATH, HOME, NEO4J_URI, ANTHROPIC_API_KEY" and frena_10), \
            {"por_el_comando": {"rc": a.returncode, "controles_OK": controles_ok, "variables": nombres},
             "sin_el_comando": {"rc": b.returncode, "frena_por_la_medicion_de_memoria": frena_10}}

    @rama("S14", "el juez fuera del repo: dentro del repo frena con el 10; fuera, la corrida no escribe en el repo y su manifiesto no trae texto")
    def _():
        dentro = K.AQUI / "juez_de_prueba_b64_seco"
        c = corrida("s14_juez_en_el_repo", ["SEC01"], juez_dir=dentro)
        try:
            c.correr()
            cod = 0
        except K.FrenoB63 as ex:
            cod = ex.codigo
        no_escribio = not dentro.exists() and not c.out.exists()
        raiz = TMP / "s14_fuera_del_repo"
        antes = foto()
        f = corrida("s14_juez_fuera", ["MET01"], preguntas=preg_meta, out=raiz / "banco_b64" / "resultados" / "real",
                    juez_dir=raiz / "banco_b64" / "juez")
        codf = f.correr()
        igual = antes == foto()
        m = R.manifiesto_fuera([f.out, f.juez_dir], raiz=raiz)
        texto = json.dumps(m, ensure_ascii=False)
        por_ruta = {x["ruta"]: x for x in m["archivos"]}
        juez = [p for p in f.juez_dir.rglob("*") if p.is_file() and not any("_SOLO_MESA" in q for q in p.relative_to(raiz).parts)]
        sha_bien = all(por_ruta.get(str(p.relative_to(raiz)), {}).get("sha256") == H.sha(p) for p in juez)
        q = json.loads(preg_meta.read_text(encoding="utf-8"))["preguntas"][0]
        metas = sorted(f.out.rglob("meta_*.json"))
        meta = json.loads(metas[0].read_text(encoding="utf-8"))
        fuentes = {"pregunta": q["pregunta"], "criterio": q["criterios"][0]["criterio"], "respuesta": meta["final_json_R4"]["respuesta"]}
        en_m = {k: sum(w in texto for w in H.ventanas(v)) for k, v in fuentes.items()}
        crudo = "".join(p.read_bytes().decode("utf-8", errors="ignore") for p in list(f.juez_dir.rglob("*.db")) + list(f.out.rglob("meta_*.json")))
        en_a = {k: sum(w in crudo for w in H.ventanas(v)) > 0 for k, v in fuentes.items()}
        ok = (cod == K.PRECONDICION and no_escribio and codf == 0 and igual and sha_bien and not any(en_m.values())
              and all(en_a.values()) and len(m["carpetas_por_nombre"]) == 1)
        return ok, {"dentro_del_repo": {"codigo": cod, "no_escribio_nada": no_escribio},
                    "fuera": {"codigo": codf, "el_repo_igual": igual, "archivos_en_el_manifiesto": m["n_archivos"],
                              "archivos_del_juez_con_su_sha256": len(juez) if sha_bien else 0,
                              "carpetas_por_nombre": len(m["carpetas_por_nombre"]), "ventanas_en_el_manifiesto": en_m,
                              "ventanas_en_los_archivos": en_a}}

    @rama("S15", "la salida del juez que no se lee: en errores, sin veredicto ni reintento; en la caché por la clave; la lectura tolerante, un veredicto por criterio")
    def _():
        import lectura_tolerante_juez as LT                  # noqa: PLC0415  (HEAD, sin editar)
        pedidos: list = []
        c = corrida("s15_no_se_lee", ["SEC10"], pedidos=pedidos)
        cod = c.correr()
        tabla = JB.leer_tabla(c.juez_dir)["filas"]
        ids = set(tabla)
        errores = {rep: JB.leer(c.juez_dir / f"errores_r{rep}.jsonl") for rep in JB.REPS}
        veredictos = {rep: JB.leer(c.juez_dir / f"veredictos_r{rep}.jsonl") for rep in JB.REPS}
        registradas = all({x["id_opaco"] for x in errores[rep]} == ids and all(x["rep"] == rep for x in errores[rep]) for rep in JB.REPS)
        sin_veredicto = all(not v for v in veredictos.values())
        n_pedidos = len(pedidos)
        r = corrida("s15_no_se_lee", ["SEC10"], pedidos=pedidos)    # retomar: nada que juzgar otra vez
        cod2 = r.correr()
        leidas = 0
        for i, fila in tabla.items():
            meta = next(c.out.rglob(f"meta_{fila['id_sesion']}.json"))
            resp = R.respuesta_de(meta.parent.parent, fila["id_sesion"])
            caso = JB.caso_ciego(fila["qid"], fila["brazo"], fila["r"], resp, c.preguntas)
            kw = J.construir_kwargs(caso["pregunta"], caso["respuesta"], caso["criterios"])
            for rep in JB.REPS:
                ns = J.lc.make_namespace(f"juez_ev2_r{rep}", code_ver=J.CODE_VER, thinking=False)
                clave_ = J.lc.compute_key(ns, J.lc.canonical_request(kw))
                con = sqlite3.connect(f"file:{JB.db_path(rep, c.cache_dir)}?mode=ro", uri=True)
                try:
                    raw, stop = con.execute("SELECT raw_json, stop_reason FROM cache WHERE key = ?", (clave_,)).fetchone()
                finally:
                    con.close()
                texto = "".join(b["text"] for b in json.loads(raw)["content"] if b.get("type") == "text")
                v = LT.leer(texto, len(caso["criterios"]))
                leidas += int(LT.aplica(texto, stop) and len(v["criterios"]) == len(caso["criterios"]))
        ok = (cod == 0 and len(ids) == 4 and registradas and sin_veredicto and n_pedidos == 12 and cod2 == 0 and len(pedidos) == 12
              and leidas == 12 and all(not JB.leer(c.juez_dir / f"veredictos_r{rep}.jsonl") for rep in JB.REPS))
        return ok, {"codigo": cod, "respuestas": len(ids), "errores_por_repeticion": {rep: len(v) for rep, v in errores.items()},
                    "veredictos_escritos": sum(len(v) for v in veredictos.values()), "pedidos": n_pedidos,
                    "pedidos_al_retomar": len(pedidos) - n_pedidos, "leidas_por_la_clave_con_la_lectura_tolerante": leidas}

    # ------------------------------------------------------------------------------------------------------------------- #
    # Las ramas de B6.4                                                                                                   #
    # ------------------------------------------------------------------------------------------------------------------- #
    @rama("N0", "el runner de B6.3 de HEAD, sin cambios, no corre los cuatro brazos; el de b64/v1 importa lo que cambia de su carpeta y lo demás de b63/v2/b2")
    def _():
        ent4, s4 = H.entrada_b64(TMP, "n0_cuatro", ["SEC01"], preguntas=preg_seco)
        ent3, s3 = H.H2.entrada_v2(TMP, "n0_tres", ["SEC01"], preguntas=B2_SECO / "preguntas_seco_b2.json")
        K_head = cargar_de(H.B63 / "v2" / "b2" / "comun_b63.py", "comun_b63_de_HEAD")
        try:
            K_head.cargar_entrada(ent4, s4)
            cuatro = None
        except Exception as ex:                       # noqa: BLE001  (su FrenoB63, de otro módulo)
            cuatro = {"codigo": getattr(ex, "codigo", None), "roles": "los roles de los brazos son" in str(ex)}
        tres = K_head.cargar_entrada(ent3, s3)["brazos"]
        JB_head = cargar_de(H.B63 / "v2" / "b2" / "juez_b63.py", "juez_b63_de_HEAD")
        e4 = K.cargar_entrada(ent4, s4)
        try:
            JB_head.marcas_d10(e4, "kg_n7")
            juez_head = "encuentra el rol"
        except KeyError:
            juez_head = "KeyError: no encuentra el rol del cuarto brazo"
        b2 = H.B63 / "v2" / "b2"
        origen = {"comun_b63": Path(K.__file__).parent == AQUI, "juez_b63": Path(JB.__file__).parent == AQUI,
                  "lanzar_agente_b63": Path(LZ.__file__).parent == AQUI,
                  **{m.__name__: Path(m.__file__).parent == b2 for m in (R.V, R.MEM, R.DK, R.N4)},
                  "formas_reales_b63.json": R.FORMAS.parent == b2, "lanzador_de_la_sesion": K.LANZADOR_SESION == "b64/v1/lanzar_agente_b63.py"}
        ok = (cuatro == {"codigo": 10, "roles": True} and len(tres) == 3 and juez_head.startswith("KeyError") and all(origen.values()))
        return ok, {"HEAD_con_cuatro_brazos": cuatro, "HEAD_con_los_tres_de_B63": "pasa" if len(tres) == 3 else "no pasa",
                    "juez_de_HEAD_con_el_cuarto": juez_head, "de_donde_importa_el_runner_de_b64": origen}

    @rama("N8", "la entrada de juguete armada con armar_entrada_B64.py, la normal y la del humo: pasan los controles del runner; el armador frena sin escribir; ningún texto en su consola ni en sus entradas")
    def _():
        a = real["armado"]
        e, humo = json.loads(sal_real.read_text(encoding="utf-8")), real["humo"]
        b63 = json.loads((H.B63 / "entrada_B63.json").read_text(encoding="utf-8"))
        aprobadas = json.loads(aprob.read_text(encoding="utf-8"))["preguntas"]
        controles = R.controles(sal_real, H.sha(sal_real), "init")[2]
        controles_humo = R.controles(sal_real.parent / AE.HUMO, H.sha(sal_real.parent / AE.HUMO), "init")[2]
        forma = (list(e)[:-1] == [k for k in b63 if k != "declarado"] and list(e)[-1] == "declarado"
                 and e["preguntas"]["esquema"] == b63["preguntas"]["esquema"] and all(e[c] == b63[c] for c in AE.DE_B63)
                 and e["k"] == 3 and (e["tope_usd"], e["freno_usd"]) == (144.0, 115.0)
                 and {b: x["rol"] for b, x in e["brazos"].items()} == AE.ROLES
                 and e["brazos"]["kg_n7"]["marcas_d10"] == list(JB.CITAS_POR_ROL["grafo"])
                 and e["brazos"]["kg_n7"]["config_servidor"] == b63["brazos"]["kg"]["config_servidor"]
                 and all(e["brazos"][b] == b63["brazos"][b] for b in ("fragmentos_hibrida", "fragmentos_denso")))
        orden = e["preguntas"]["ids_en_orden"] == [q["id"] for q in aprobadas] and e["preguntas"]["ids_en_orden"] != sorted(e["preguntas"]["ids_en_orden"])
        sin_humo = {k: v for k, v in humo.items() if not k.startswith("_")}
        sin_e = {k: v for k, v in e.items() if not k.startswith("_")}
        humo_ok = (humo["preguntas"]["ids_en_orden"] == [aprobadas[0]["id"]] and humo["k"] == 1
                   and {k for k in sin_e if sin_e[k] != sin_humo.get(k)} == {"unidad", "preguntas", "k", "declarado"}
                   and {k: v for k, v in humo["preguntas"].items() if k != "ids_en_orden"}
                   == {k: v for k, v in e["preguntas"].items() if k != "ids_en_orden"} and "humo" in humo["declarado"])
        q0 = aprobadas[0]
        fuentes = [q0["pregunta"], q0["criterios"][0]["criterio"], q0["criterios"][0]["cita_textual"]]
        textos = a.stdout + a.stderr + sal_real.read_text(encoding="utf-8") + (sal_real.parent / AE.HUMO).read_text(encoding="utf-8")
        ventanas = sum(w in textos for t in fuentes for w in H.ventanas(t))
        # los frenos del armador, cada uno sin escribir nada
        frenos = {}
        malas = {"sha256": (aprob, "0" * 64),
                 "95_preguntas": H.aprobadas_de_juguete(TMP / "aprobadas" / "n95.json", mutar=lambda d: d["preguntas"].pop()),
                 "sin_anclas": H.aprobadas_de_juguete(TMP / "aprobadas" / "sin_anclas.json", mutar=lambda d: d["preguntas"][4].pop("anclas")),
                 "criterio_sin_unidad": H.aprobadas_de_juguete(TMP / "aprobadas" / "sin_unidad.json",
                                                               mutar=lambda d: d["preguntas"][7]["criterios"][1].pop("unidad")),
                 "id_repetido": H.aprobadas_de_juguete(TMP / "aprobadas" / "id_repetido.json",
                                                       mutar=lambda d: d["preguntas"][9].update(id=d["preguntas"][3]["id"]))}
        for n, (p, s) in malas.items():
            sal = TMP / "entrada_mala" / n / "entrada_B64.json"
            r = armador(p, s, sal)
            frenos[n] = {"rc": r.returncode, "escribio": sal.parent.exists(),
                         "ventanas_en_su_consola": sum(w in r.stdout + r.stderr for t in fuentes for w in H.ventanas(t))}
        otra_vez = armador(aprob, sha_aprob, sal_real)            # el mismo archivo otra vez: la misma entrada, sin cambiar nada
        frenos_ok = all(v == {"rc": 10, "escribio": False, "ventanas_en_su_consola": 0} for v in frenos.values())
        ok = (a.returncode == 0 and forma and orden and humo_ok and ventanas == 0 and frenos_ok and otra_vez.returncode == 0
              and controles["n_preguntas"] == 96 and controles["brazos"] == sorted(BRAZOS_B64) and controles_humo["n_preguntas"] == 1
              and len(real["preg"]) == 96)
        return ok, {"armado": a.returncode, "la_forma_de_la_de_B63_con_lo_de_B63_tal_cual": forma, "ids_en_el_orden_del_archivo": orden,
                    "controles_del_runner": {"preguntas": controles["n_preguntas"], "k": controles["k"], "brazos": controles["brazos"]},
                    "humo": {"preguntas": controles_humo["n_preguntas"], "k": humo["k"], "la_primera_del_orden": humo_ok},
                    "ventanas_de_texto_en_la_consola_y_las_entradas": ventanas, "frenos_del_armador": frenos,
                    "armado_otra_vez_igual": otra_vez.returncode == 0}

    @rama("N1", "el orden de cuatro brazos: por pregunta y por repetición, los brazos de cada bloque seguidos, con la semilla de B6.3; las sesiones de cada pregunta, seguidas")
    def _():
        e = real["e"]
        c = R.CorridaB63(e, real["preg"], modo="init", out=TMP / "n1_orden" / "out", sesiones=TMP / "n1_orden" / "ses",
                         juez_dir=TMP / "n1_orden" / "juez")
        p = c.escribir_orden()
        o = json.loads(p.read_text(encoding="utf-8"))
        ids = e["preguntas"]["ids_en_orden"]

        def perm(q, r):
            xs = sorted(BRAZOS_B64)
            random.Random(f"B63:orden_corridas:v1:{q}:{r}").shuffle(xs)
            return xs
        recomputado = [{"bloque": f"{q}-r{r}", "qid": q, "r": r, "brazos": perm(q, r)} for q in ids for r in (1, 2, 3)]
        pend = c.pendientes()
        por_q: dict[str, list[int]] = {}
        for i, s in enumerate(pend):
            por_q.setdefault(s["qid"], []).append(i)
        seguidas = all(v == list(range(v[0], v[0] + 12)) for v in por_q.values())
        bloques_seguidos = all([s["brazo"] for s in pend[4 * j:4 * j + 4]] == b["brazos"] and {s["bloque"] for s in pend[4 * j:4 * j + 4]}
                               == {b["bloque"]} for j, b in enumerate(o["bloques"]))
        primero = Counter(b["brazos"][0] for b in o["bloques"])
        ventana = all(sorted(b["brazos"]) == sorted(H.BRAZOS_JUGUETE) for b in s1.orden) and len(s1.orden) == 3
        ok = (o["bloques"] == recomputado and len(o["bloques"]) == 288 and o["semilla"] == "B63:orden_corridas:v1"
              and o["brazos"] == sorted(BRAZOS_B64) and o["ids_en_orden"] == ids and len(pend) == 1152 and seguidas and bloques_seguidos
              and ventana)
        return ok, {"bloques": len(o["bloques"]), "igual_al_recomputado": o["bloques"] == recomputado, "sesiones": len(pend),
                    "las_de_cada_pregunta_seguidas": seguidas, "los_cuatro_de_cada_bloque_seguidos": bloques_seguidos,
                    "permutaciones_distintas": len({tuple(b["brazos"]) for b in o["bloques"]}),
                    "primero_en_el_bloque_por_brazo": dict(sorted(primero.items())), "en_la_ventana_de_S1": ventana}

    @rama("N2", "un id por brazo: los 1.152 de la entrada de B6.4, distintos, con la forma B63-<id>-r<r>-<brazo>, admitidos por el lote y leídos por el CLI falso")
    def _():
        e = real["e"]
        orden = K.orden_bloques(e["preguntas"]["ids_en_orden"], e["k"], sorted(e["brazos"]))
        ses = [(b["qid"], b["r"], x) for b in orden for x in b["brazos"]]
        ids = [K.id_sesion(q, r, x) for q, r, x in ses]
        forma = all(i == f"B63-{q}-r{r}-{x}" for i, (q, r, x) in zip(ids, ses))
        admitidos = all(LOTE.BASE.ID_VALIDO.match(i) and K.ID_VALIDO.match(i) for i in ids)
        tag = re.compile(TAG_DEL_CLI_FALSO)
        el_del_cli = TAG_DEL_CLI_FALSO in CLI_FALSO.read_text(encoding="utf-8")
        leidos = all((m := tag.match(K.id_sesion(q, r, x, i))) and m.group("brazo") == x and m.group("q") == q and int(m.group("r")) == r
                     and int(m.group("i") or 1) == i for q, r, x in ses for i in (1, 2, 3))
        por_bloque = all(len({K.id_sesion(b["qid"], b["r"], x) for x in b["brazos"]}) == 4 for b in orden)
        ok = (len(ids) == 1152 and len(set(ids)) == 1152 and len({i.lower() for i in ids}) == 1152 and forma and admitidos and el_del_cli
              and leidos and por_bloque)
        return ok, {"ids": len(ids), "distintos": len(set(ids)), "distintos_sin_mayusculas": len({i.lower() for i in ids}),
                    "con_la_forma": forma, "admitidos_por_el_lote": admitidos, "un_id_por_brazo_en_cada_bloque": por_bloque,
                    "el_patron_es_el_del_cli_falso": el_del_cli, "el_cli_falso_lee_brazo_pregunta_repeticion_e_intento": leidos}

    @rama("N3", "el juez de a tres en cada respuesta de los cuatro brazos")
    def _():
        filas = JB.leer_tabla(s1.juez_dir)["filas"]
        por_brazo = Counter(f["brazo"] for f in filas.values())
        juez = [e for e in s1.estado["eventos"] if e.get("evento") == "juez"]
        lineas = {rep: len(JB.leer(s1.juez_dir / f"veredictos_r{rep}.jsonl")) for rep in JB.REPS}
        ag = json.loads((s1.juez_dir / "agregados_b63_ciego.json").read_text(encoding="utf-8"))
        ok = (dict(por_brazo) == {b: 3 for b in H.BRAZOS_JUGUETE} and len(juez) == 12
              and all(e["repeticiones_lanzadas_a_la_vez"] == [1, 2, 3] and e["llamadas"] == 3 for e in juez)
              and lineas == {1: 12, 2: 12, 3: 12} and ag["n_agregados"] == 12 and not ag["incompletas"])
        return ok, {"respuestas_por_brazo": dict(sorted(por_brazo.items())), "juicios": len(juez),
                    "veredictos_por_repeticion": lineas, "agregados": ag["n_agregados"], "incompletas": len(ag["incompletas"])}

    @rama("N4", "la cuenta de D-10 por brazo: los cuatro, sin editar ninguna respuesta; las marcas de kg_n7, las del grafo")
    def _():
        d = json.loads((s1.juez_dir / "d10_b63.json").read_text(encoding="utf-8"))
        pb = d["por_brazo"]

        def regex(e, b):
            return sorted(x for _, x in JB.marcas_d10(e, b))
        juguete = regex(s1.e, "kg_n7") == regex(s1.e, "kg")
        e = real["e"]
        de_b64 = regex(e, "kg_n7") == regex(e, "kg") and len(JB.marcas_d10(e, "kg_n7")) == len(JB.marcas_d10(e, "kg")) == 21
        # el control positivo: las respuestas de juguete del CLI falso no traen marcas (0 en los cuatro), así que se cuentan dos con marcas
        grafo, frag = "Según el nodo 4.2 que mostró ver_punto, el plazo es de diez días.", "Según el pasaje 3, el plazo es de diez días."
        cuenta = {(r, b): JB.contar_d10(t, JB.marcas_d10(e, b)) for r, t in (("grafo", grafo), ("fragmentos", frag)) for b in BRAZOS_B64}
        hits = {k: sorted(x for n, x in JB.marcas_d10(e, k[1]) if v["marcas"][n]) for k, v in cuenta.items()}
        positivo = (cuenta[("grafo", "kg_n7")]["con_alguna"] and hits[("grafo", "kg_n7")] == hits[("grafo", "kg")]
                    and not cuenta[("fragmentos", "kg_n7")]["con_alguna"] and cuenta[("fragmentos", "fragmentos_hibrida")]["con_alguna"]
                    and all(v["sha256_antes"] == v["sha256_despues"] for v in cuenta.values()))
        ok = (sorted(pb) == sorted(H.BRAZOS_JUGUETE) and all(v["n_respuestas"] == 3 and v["respuestas_editadas"] == 0 for v in pb.values())
              and pb["kg_n7"]["con_alguna_marca"] == pb["kg"]["con_alguna_marca"] and juguete and de_b64 and positivo
              and "entrada:\\bnodos?\\b" in d["marcas"]["kg_n7"] and "cita:\\bnodos?\\b" in d["marcas"]["kg"])
        return ok, {"por_brazo": {b: {"respuestas": v["n_respuestas"], "con_alguna_marca": v["con_alguna_marca"],
                                      "editadas": v["respuestas_editadas"]} for b, v in sorted(pb.items())},
                    "marcas_de_kg_n7_las_de_kg_en_la_de_juguete": juguete, "marcas_de_kg_n7_las_de_kg_en_la_de_B64": de_b64,
                    "marcas_de_kg_n7_en_la_de_B64": len(JB.marcas_d10(e, "kg_n7")),
                    "control_positivo": {f"{r} con las de {b}": len(h) for (r, b), h in sorted(hits.items())},
                    "control_positivo_PASS": bool(positivo)}

    @rama("N5", "la cuenta por fecha con cuatro brazos: cada brazo con sus sesiones, y un bloque de cuatro brazos con dos fechas, detectado")
    def _():
        f = json.loads((s1.out / "fechas_b63.json").read_text(encoding="utf-8"))
        por = {b: sum(v.values()) for b, v in f["por_brazo_y_fecha"].items()}
        desde_estado = K.cuenta_fechas(s1.estado["sesiones"])
        sint = [{"bloque": "Q1-r1", "brazo": b, "fecha": "2026-10-31" if b != "kg_n7" else "2026-11-01", "intento": 1} for b in BRAZOS_B64]
        sint += [{"bloque": "Q1-r2", "brazo": b, "fecha": "2026-11-01", "intento": 1} for b in BRAZOS_B64]
        cs = K.cuenta_fechas(sint)
        ok = (por == {b: 4 for b in H.BRAZOS_JUGUETE} and f["n_sesiones"] == 16 and f["n_bloques"] == 3 and f == desde_estado
              and cs["n_bloques_con_fechas_distintas"] == 1 and cs["bloques_con_fechas_distintas"][0]["bloque"] == "Q1-r1"
              and sorted(cs["bloques_con_fechas_distintas"][0]["fechas_por_brazo"]) == sorted(BRAZOS_B64)
              and sorted(cs["por_brazo_y_fecha"]) == sorted(BRAZOS_B64) and cs["n_sesiones"] == 8)
        return ok, {"sesiones_por_brazo_en_S1": por, "sesiones": f["n_sesiones"], "bloques": f["n_bloques"],
                    "igual_a_la_recontada_del_estado": f == desde_estado,
                    "sintetica": {"bloques_con_fechas_distintas": cs["n_bloques_con_fechas_distintas"],
                                  "brazos_del_bloque": len(cs["bloques_con_fechas_distintas"][0]["fechas_por_brazo"])}}

    class LoteDoble:
        """Lo que `antes_de_lanzar` lee del lote: lo acumulado de la guarda y el presupuesto de una sesión."""

        def __init__(self):
            self.acumulado_guarda, self.presupuesto = 0.0, 1.8

    @rama("N6", "el freno del gasto en 115 y el tope en 144: en la entrada, en la guarda de cada sesión, en dos corridas y en el juez")
    def _():
        e = real["e"]
        en_la_entrada = (e["tope_usd"], e["freno_usd"]) == (144.0, 115.0)
        mal = frena_(K.cargar_entrada, *H.entrada_b64(TMP, "n6_freno_mayor", ["SEC01"], preguntas=preg_seco, tope=144.0, freno=150.0))

        def borde(freno: float, tope: float, acumulado: float, corriendo: int) -> bool:
            c = corrida(f"n6_borde_{int(freno)}_{int(tope)}", ["SEC01"], freno=freno, tope=tope)
            c.estado["acumulado_agente_guarda_usd"] = acumulado
            s = c.pendientes()[0]
            c._ultimo_bloque = s["bloque"]
            return c.antes_de_lanzar(LoteDoble(), s, corriendo) is None
        guarda = {"115_con_113.2_y_P1": borde(115.0, 144.0, 113.2, 0), "115_con_113.3_y_P1": borde(115.0, 144.0, 113.3, 0),
                  "115_con_111.4_y_P2": borde(115.0, 144.0, 111.4, 1), "115_con_111.5_y_P2": borde(115.0, 144.0, 111.5, 1),
                  "144_con_142.2_y_P1": borde(144.0, 144.0, 142.2, 0), "144_con_142.3_y_P1": borde(144.0, 144.0, 142.3, 0)}
        guarda_ok = guarda == {"115_con_113.2_y_P1": True, "115_con_113.3_y_P1": False, "115_con_111.4_y_P2": True,
                               "115_con_111.5_y_P2": False, "144_con_142.2_y_P1": True, "144_con_142.3_y_P1": False}
        corridas = {}
        for n, freno, tope, acumulado in (("freno_115", 115.0, 144.0, 113.2), ("tope_144", 144.0, 144.0, 142.2)):
            c = corrida(f"n6_{n}", ["SEC01"], freno=freno, tope=tope)
            c.estado["acumulado_agente_guarda_usd"] = acumulado
            cod = c.correr()
            corridas[n] = {"codigo": cod, "lanzadas": len(lanzados(c)), "no_lo_paso": c.gastado() <= freno}
        corridas_ok = all(v == {"codigo": 2, "lanzadas": 1, "no_lo_paso": True} for v in corridas.values())
        d = TMP / "n6_juez"
        preg = {"Q1": {"pregunta": "p", "criterios": [{"criterio": "c1", "cita_textual": "t1"}]}}
        caso = JB.caso_ciego("Q1", "kg_n7", 1, "respuesta", preg)
        tres = JB.TresJueces(lambda rep, label: H.ClienteJuez(), d, d / "cache")
        try:
            try:
                tres.juzgar(caso, 114.97, 115.0, 144.0)      # entran dos de 0,0126 (114,97 + 0,0252 ≤ 115), no la tercera
                corto = False
            except JB.FrenoJuez:
                corto = True
            hechas = JB.hechas(d)
        finally:
            tres.cerrar()
        juez_ok = corto and [caso["id_opaco"] in hechas[rep] for rep in JB.REPS] == [True, True, False]
        ok = en_la_entrada and mal == K.PRECONDICION and guarda_ok and corridas_ok and juez_ok
        return ok, {"entrada_de_B64": {"tope": e["tope_usd"], "freno": e["freno_usd"]}, "freno_mayor_que_el_tope": mal,
                    "guarda_antes_de_cada_sesion_lanza": guarda, "corridas": corridas, "juez_en_el_borde_de_115_corta": juez_ok}

    @rama("N7", "ninguna salida en el repo: con --out, --juez-dir, --sesiones, --lotes o los originales dentro del repo, el modo real frena con el 10 sin escribir nada")
    def _():
        antes = foto()
        obs = {}
        for que in ("out", "juez_dir", "sesiones", "lotes"):
            dentro = K.AQUI / f"salida_de_prueba_{que}"
            c = corrida(f"n7_{que}", ["SEC01"], **{que: dentro})
            cod = frena_(c.correr)
            obs[que] = {"codigo": cod, "escribio": dentro.exists() or c.out.exists()}
        viejo = K.ORIGINALES
        K.ORIGINALES = K.AQUI / "originales_de_prueba"
        try:
            c = corrida("n7_originales", ["SEC01"])
            obs["originales"] = {"codigo": frena_(c.correr), "escribio": K.ORIGINALES.exists() or c.out.exists()}
        finally:
            K.ORIGINALES = viejo
        ent, s = H.entrada_b64(TMP, "n7_solo_controles", ["SEC01"], preguntas=preg_seco)
        solo = {}
        for que, out in (("con_out_en_el_repo", K.AQUI / "salida_de_prueba_solo_controles"), ("con_todo_fuera", TMP / "n7_solo" / "out")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):         # la consola del runner trae rutas: no se imprime
                cod = R.main(["--entrada", str(ent), "--sha256-entrada", s, "--modo", "real", "--solo-controles", "--out", str(out),
                              "--sesiones", str(TMP / "n7_solo" / "ses"), "--juez-dir", str(TMP / "n7_solo" / "juez"),
                              "--patron-de-prueba", TOKEN])
            solo[que] = {"codigo": cod, "orden_escrito": (out / "orden_b63.json").exists(),
                         "por_la_decision_3": "(decisión 3): --out" in buf.getvalue(), "controles_OK": '"controles": "OK"' in buf.getvalue()}
        solo_ok = (solo["con_out_en_el_repo"] == {"codigo": K.PRECONDICION, "orden_escrito": False, "por_la_decision_3": True,
                                                  "controles_OK": False}
                   and solo["con_todo_fuera"] == {"codigo": 0, "orden_escrito": True, "por_la_decision_3": False, "controles_OK": True})
        fuera = not any(p.is_relative_to(K.REPO_DIR.resolve()) for p in (K.RESULTADOS, K.JUEZ_DIR, K.SESIONES, K.ORIGINALES))
        nombres = (K.RESULTADOS.parent.name, K.JUEZ_DIR.parent.name, K.SESIONES.parent.name, K.ORIGINALES.name)
        igual = antes == foto()
        ok = (all(v == {"codigo": K.PRECONDICION, "escribio": False} for v in obs.values()) and solo_ok and igual and fuera
              and nombres == ("banco_b64", "banco_b64", "banco_b64", "banco_mcp_originales_B64"))
        return ok, {"dentro_del_repo": obs, "solo_controles_en_modo_real": solo, "el_repo_igual": igual,
                    "las_por_defecto_fuera_del_repo": fuera, "carpetas_por_defecto": list(nombres)}

    @rama("N9", "el control de la entrada del juez (§5): lo de kg_n7 se arma igual que lo de los otros tres y no lleva el nombre de ningún brazo")
    def _():
        e, preg = real["e"], real["preg"]
        brazos = sorted(e["brazos"])
        q = e["preguntas"]["ids_en_orden"][0]
        resp = "Respuesta de juguete de N9, la misma para los cuatro brazos."
        casos = {b: JB.caso_ciego(q, b, 1, resp, preg) for b in brazos}
        fugas = {b: JB.verificar_pedido(c, brazos) for b, c in casos.items()}
        kws = {b: J.construir_kwargs(c["pregunta"], c["respuesta"], c["criterios"]) for b, c in casos.items()}
        mensajes = {b: J.construir_mensaje_usuario(c["pregunta"], "<respuesta>", c["criterios"]) for b, c in casos.items()}
        iguales = (all(set(c) == {"id_opaco", "pregunta", "respuesta", "criterios"} for c in casos.values())
                   and all({k: v for k, v in c.items() if k != "id_opaco"} == {k: v for k, v in casos["kg"].items() if k != "id_opaco"}
                           for c in casos.values())
                   and all(kw == kws["kg"] for kw in kws.values()))
        sin_nombre = all(not any(b.lower() in m.lower() for b in brazos) and "B63-" not in m and casos[x]["id_opaco"] not in m
                         for x, m in mensajes.items())
        ids_opacos = {b: c["id_opaco"] for b, c in casos.items()}
        opacos_ok = (len(set(ids_opacos.values())) == 4 and all(re.fullmatch(r"B63J-[0-9a-f]{10}", i) for i in ids_opacos.values())
                     and all(b not in i for b, i in ids_opacos.items()))
        positivo = {b: bool(JB.verificar_pedido(JB.caso_ciego(q, b, 1, resp, {q: {"pregunta": preg[q]["pregunta"], "criterios": [
            {"criterio": f"un criterio que nombra {b}", "cita_textual": "t"}]}}), brazos)) for b in ("kg_n7", "kg")}
        ok = all(not v for v in fugas.values()) and iguales and sin_nombre and opacos_ok and all(positivo.values())
        return ok, {"fugas_por_brazo": {b: len(v) for b, v in fugas.items()}, "el_pedido_igual_en_los_cuatro": iguales,
                    "ningun_nombre_de_brazo_ni_id_en_el_mensaje": sin_nombre, "ids_opacos_distintos_sin_el_brazo": opacos_ok,
                    "control_positivo_con_el_nombre_en_un_criterio": positivo}

    @rama("S13", "ninguna otra línea de comandos con un guion del patrón, y ningún pgrep con el patrón real después de la guarda")
    def _():
        con = [l for l in LINEAS if (g := G.script_python(" ".join(l))) and re.search(R.PATRON_B1, g.rsplit("/", 1)[-1])]
        pg = [l for l in LINEAS if l and Path(l[0]).name == "pgrep"]
        runner = [l for l in con if l[2].endswith("/correr_b63.py")]
        guiones = sorted({Path(x).name for l in LINEAS if l and Path(l[0]).name != "pgrep" for x in l if x.endswith(".py")})
        return (con == runner and len(runner) == 1 and pg and all(l[-1] == LOTE.patron_de_prueba(TOKEN) for l in pg)), \
            {"lineas": len(LINEAS), "pgrep_con_el_token": len(pg), "con_un_guion_del_patron": len(con),
             "de_ellas_el_runner_sin_el_comando_de_S12": len(runner), "guiones_lanzados": guiones}

    os.environ["PATH"] = path0


def frena_(f, *a, **kw):
    try:
        f(*a, **kw)
    except K.FrenoB63 as ex:
        return ex.codigo
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp", type=Path, required=True)
    ap.add_argument("--resultado", type=Path, required=True)
    a = ap.parse_args()
    if Path(".git").exists():
        raise SystemExit("ABORTO: la corrida en seco corre en una copia del repo, sin .git")
    tmp = a.tmp.resolve()
    if tmp.is_relative_to(LA.REPO_DIR) or LA.dentro_de_git(tmp) is not None:
        raise SystemExit("ABORTO: --tmp dentro del repo o de git")
    hallados = G.otro_paso_pago(raiz_lote=os.getpid(), patron=R.PATRON_B1)   # la guarda: el patrón real
    guarda = {"patron": "correr_b63.PATRON_B1", "hallados": [{"script": h["script"]} for h in hallados]}
    if hallados:
        a.resultado.write_text(json.dumps({"guarda": guarda, "corrio": False}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"FRENO: la guarda vio otro paso pago ({[h['script'] for h in hallados]}); la corrida en seco no corre", flush=True)
        return G.CODIGO_PAGO
    print("guarda: ningún paso pago corriendo", flush=True)
    for m in (G, LOTE.BASE, K, R.MEM, R.DK, sys.modules["guardas_lote"]):
        m.subprocess = Registrador()
    tmp.mkdir(parents=True, exist_ok=True)
    correr_ramas(tmp)
    for r in RES:
        print(("PASS " if r["PASS"] else "FAIL ") + f"{r['rama']} {r['que']} — "
              + json.dumps({k: v for k, v in r.items() if k not in ("rama", "que", "PASS")}, ensure_ascii=False), flush=True)
    n = sum(r["PASS"] for r in RES)
    print(f"corrida en seco B6.4: {n} de {len(RES)} en PASS", flush=True)
    a.resultado.write_text(json.dumps({"guarda": guarda, "corrio": True, "ramas": RES, "pass": n, "total": len(RES)}, ensure_ascii=False,
                                      indent=1) + "\n", encoding="utf-8")
    return 0 if n == len(RES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
