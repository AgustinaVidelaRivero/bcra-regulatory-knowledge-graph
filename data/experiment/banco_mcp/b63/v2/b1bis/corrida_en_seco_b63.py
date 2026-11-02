#!/usr/bin/env python3
"""corrida_en_seco_b63.py (v2/b1bis, etapa b1 bis) — La corrida en seco del runner de B6.3 de esta carpeta, a USD 0 y sin ningún dato
real: preguntas, configuraciones y servidores de juguete (b63/seco/ y b63/v2/b1bis/seco/), una entrada sellada de juguete, el CLI falso
de la b1 bis (las formas reales del error, con la del 401), el juez de EV2 sobre un transporte simulado (el juez falso) y los dobles de
memoria, Docker y Neo4j.

Su guarda, antes de todo: la de otro paso pago con el patrón de la b1 bis (correr_b63.PATRON_B1, el real: es el único `pgrep` con el
patrón real de esta corrida). Si ve un paso pago, no corre nada más: escribe el resultado con lo que vio y sale con el 7.

Importa el runner (correr_b63.py, de su misma carpeta: ningún arreglo del sys.path por fuera, el mismo camino de imports que la corrida
real) y llama a sus funciones, en modo real, con el CLI falso primero en el PATH y una clave de relleno: cada lote recorre el camino
real (la ventana, el lanzador del lote, el lanzador de la sesión de la b1 bis, el de N6, `claude`, el servidor MCP de juguete de la
sesión, la meta completa y la meta sin texto) y ninguna petición sale a la API. Las guardas de otro paso pago y de la extracción buscan
un token propio (correr_b63.fijar_patron_de_prueba), y cada línea de comandos que lanzan las guardas, el lote y los controles queda
anotada.

Las ramas:
  S1  la ventana con P = 1: el orden firmado y cada reintento enseguida de su falla (una falla de infraestructura, la forma real del
      429, que termina al segundo intento); el juez de a tres en cada respuesta, una base y un namespace por repetición;
  S2  la ventana con P = 2: nunca más de 2 a la vez, y el reintento al frente de las pendientes;
  S3  los reintentos: la forma real del 500 en los tres intentos, falla_infra_sin_terminar y ningún cuarto;
  S4  la opción (d): tres formas desconocidas, el 12, con 3 sesiones lanzadas;
  S5  la clave inválida con P = 1: la forma real del 401 frena el lote a la primera con el 16, sin lanzar otra; la sesión no cuenta ni
      va al juez; retomar con la clave buena la corre y no repite ninguna terminada;
  S6  la clave inválida con P = 2, inválida desde la primera sesión: las dos que el lote lanza a la vez dan el 401; la segunda termina
      después del freno y queda registrada; al retomar se corren las dos, una vez, y ninguna terminada se repite;
  S7  los cortes, por --max-turns (en el brazo kg de SEC06) y por el presupuesto (en el bm25 de SEC07; cada plan de corte de la etapa
      a se aplica a un brazo): cortada y sin juez; los otros 4 brazos, completos y juzgados;
  S8  la guarda del gasto del agente y el juez juntos: frena con el 2 antes del freno;
  S9  los ganchos: la memoria (13), Docker (14) y el Neo4j (15) frenan sin lanzar;
  S10 retomar sin repetir: la corrida de S1, otra vez, no lanza nada;
  S11 la meta sin texto y el stream en la meta, en cada sesión de S1: las claves de la lista cerrada, el sha256 de la meta completa y
      el del stream;
  S12 el comando con env -i (comando_b63.zsh correr): con LANG=es_AR.UTF-8 en el entorno padre, el runner, lanzado por el comando, pasa
      sus controles (--solo-controles, en modo init, con el patrón de prueba); lanzado sin el comando, frena con el 10. Son los dos
      únicos procesos de esta corrida con un guion del patrón (correr_b63.py), después de la guarda;
  S13 ninguna otra línea de comandos con un guion del patrón, y ningún `pgrep` con el patrón real después de la guarda.
El resultado (--resultado), solo cuentas, sha256 y banderas; imprime una línea por rama.

Uso, desde la raíz de una copia del repo (frena si encuentra .git ahí):
  <python del .venv del repo> -B data/experiment/banco_mcp/b63/v2/b1bis/corrida_en_seco_b63.py --tmp <dir> --resultado <json>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import correr_b63 as R                                       # noqa: E402  (el runner de la b1 bis, de esta misma carpeta)
from seco import herramientas_b1bis as H                     # noqa: E402
import lanzar_agente_b63 as LZ                               # noqa: E402  (las listas de campos de la meta sin texto)

K, JB, LOTE, G, LA = R.K, R.JB, R.LOTE, R.G, R.LA
J = sys.modules["juez"]
TOKEN = "prueba_b1bis_seco_zq7xk2m4"                          # un token propio: no nombra ningún paso pago
LINEAS: list[list[str]] = []
PREGUNTAS = AQUI / "seco" / "preguntas_seco_b1bis.json"
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


def correr_ramas(TMP: Path) -> None:
    falso = TMP / "bin"
    falso.mkdir(parents=True, exist_ok=True)
    (falso / "claude").write_text(f'#!/bin/sh\nexec "{sys.executable}" -B "{AQUI / "seco" / "claude_falso_b63.py"}" "$@"\n',
                                  encoding="utf-8")
    (falso / "claude").chmod(0o755)
    path0 = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{falso}:{path0}"
    os.environ["NEO4J_URI"] = "bolt://127.0.0.1:47687"
    os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_DE_RELLENO
    R.fijar_patron_de_prueba(TOKEN)

    def corrida(nombre: str, ids: list[str], P: int = 1, freno: float = 40.0, tope: float = 50.0, pedidos: list | None = None,
                **kw) -> R.CorridaB63:
        ent, s = H.entrada_v2(TMP, nombre, ids, preguntas=PREGUNTAS, P=P, freno=freno, tope=tope)
        e = K.cargar_entrada(ent, s)
        preg = K.cargar_preguntas(e)
        R.preparar_entorno(e)
        base = TMP / nombre
        return R.CorridaB63(e, preg, modo="real", out=base / "out", sesiones=base / "ses", juez_dir=base / "juez", lotes=base / "lotes",
                            client_factory=H.juez_simulado(base / "juez" / "cache", pedidos if pedidos is not None else []),
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

    pedidos_s1: list = []
    s1 = corrida("s1_p1", ["SEC01", "SEC02", "SEC03"], pedidos=pedidos_s1)

    @rama("S1", "la ventana con P = 1, un reintento enseguida de su falla, y el juez de a tres")
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
        ok = (cod == 0 and ids == esperado and set(finales(s1).values()) == {"completa"} and len(JB.leer_tabla(s1.juez_dir)["filas"]) == 9
              and len(juez) == 9 and all(e["repeticiones_lanzadas_a_la_vez"] == [1, 2, 3] for e in juez) and sin_cruces
              and len(pedidos_s1) == 27)
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
        return (cod == 0 and maximo == 2 and frente and n_ins == 3 and set(finales(c).values()) == {"completa"}), \
            {"codigo": cod, "maximo_a_la_vez": maximo, "reintentos_insertados": n_ins, "cada_reintento_al_frente": frente}

    @rama("S3", "los reintentos: la forma real del 500 en los tres intentos")
    def _():
        c = corrida("s3_infra3", ["SEC04"])
        cod = c.correr()
        st = c.estado["bloques"]["SEC04-r1"]
        return (cod == 0 and set(v["clasificacion"] for v in st["final"].values()) == {"falla_infra_sin_terminar"}
                and set(st["intentos_por_brazo"].values()) == {3} and len(lanzados(c)) == 9), \
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
              and cod2 == 0 and set(malas) <= set(p2) and not set(p2) & contadas and len(p1) + len(p2) == 9 + len(malas) and n_final == 9
              and set(finales(r).values()) == {"completa"} and len(JB.leer_tabla(r.juez_dir)["filas"]) == 9)
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
                and sorted(fin.values()).count("completa") == 4 and len(juzgadas) == 4), \
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
                  and all("input" not in x for x in sn["mapa_R7"]))
            n += 1
            if not ok:
                malas.append(s["id"])
        return n == 12 and not malas, {"sesiones": n, "con_algo_que_no_da": len(malas)}

    @rama("S12", "el comando con env -i: el runner por el comando con LANG=es_AR.UTF-8 pasa sus controles; sin el comando, frena con el 10")
    def _():
        ent, s = H.entrada_v2(TMP, "s12_comando", ["SEC01"], preguntas=PREGUNTAS)
        padre = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "LANG": "es_AR.UTF-8", "VARIABLE_DE_LA_TERMINAL_B1BIS": "x",
                 "ANTHROPIC_API_KEY": H.CLAVE_DE_RELLENO, "B63_PYTHON": sys.executable}   # B63_PYTHON: la copia no trae el .venv
        resto = ["--modo", "init", "--solo-controles", "--patron-de-prueba", TOKEN, "--out", str(TMP / "s12_comando" / "out"),
                 "--sesiones", str(TMP / "s12_comando" / "ses"), "--juez-dir", str(TMP / "s12_comando" / "juez")]
        argv = ["zsh", str(AQUI / "comando_b63.zsh"), "correr", str(ent), s] + resto
        LINEAS.append(argv)
        a = subprocess.run(argv, env=padre, capture_output=True, text=True)
        nombres = next((l.split("env -i con ", 1)[1] for l in a.stdout.splitlines() if l.startswith("comando_b63: env -i con ")), None)
        directo = [sys.executable, "-B", str(AQUI / "correr_b63.py"), "--entrada", str(ent), "--sha256-entrada", s] + resto
        LINEAS.append(directo)
        b = subprocess.run(directo, env=padre | {"NEO4J_URI": "bolt://127.0.0.1:47687"}, capture_output=True, text=True)
        controles_ok = a.returncode == 0 and '"controles": "OK"' in a.stdout
        frena_10 = b.returncode == K.PRECONDICION and "la medición de memoria no anda" in b.stdout
        return (controles_ok and nombres == "PATH, HOME, NEO4J_URI, ANTHROPIC_API_KEY" and frena_10), \
            {"por_el_comando": {"rc": a.returncode, "controles_OK": controles_ok, "variables": nombres},
             "sin_el_comando": {"rc": b.returncode, "frena_por_la_medicion_de_memoria": frena_10}}

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
    hallados = G.otro_paso_pago(raiz_lote=os.getpid(), patron=R.PATRON_B1)   # la guarda: el patrón real de la b1 bis
    guarda = {"patron": "correr_b63.PATRON_B1 (b1 bis)", "hallados": [{"script": h["script"]} for h in hallados]}
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
    print(f"corrida en seco B6.3-b1 bis: {n} de {len(RES)} en PASS", flush=True)
    a.resultado.write_text(json.dumps({"guarda": guarda, "corrio": True, "ramas": RES, "pass": n, "total": len(RES)}, ensure_ascii=False,
                                      indent=1) + "\n", encoding="utf-8")
    return 0 if n == len(RES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
