#!/usr/bin/env python3
"""selftest_lanzar_lote_paralelo_r5.py — El selftest de agentes/lanzar_lote_paralelo_r5.py y de paralelo/guardas_lote_r5.py
(U-BANCO-R5-a), a USD 0 y sin lanzar ningún proceso: ni sesiones, ni `claude`, ni `pgrep`, ni `ps`.

Importa el lanzador r5 por su ruta (sin tocar el sys.path por fuera: el módulo agrega las suyas, como en la corrida real) y
controla, sobre las entradas de juguete de --entradas (scripts/armar_juguete_r5.py):
  T1  los dos R5 admitidos son los del pre-registro, en su orden, y el primero es el R5_ESPERADO del lanzador de HEAD;
  T2  la clave de R5 es la de b63/comun_b63.py: el campo «R5» que cargar_entrada exige y lee (por su AST), sin una constante
      con nombre en el módulo;
  T3  admitido(): A y B sí; C, cada R5 a un paso de A o de B, uno con una clave de más o de menos, no;
  T4  r5_de_la_entrada(): A y B dan su R5; otro sha256, una entrada que no existe y una sin R5 frenan (SystemExit con texto);
  T5  el presupuesto por sesión sale del R5 de la entrada (1,80 con A, 3,30 con B, en modo real y la guarda en 0 en init); uno
      explícito igual pasa y uno distinto frena;
  T6  control_aislamiento con el R5 de la entrada: una sesión con el R5 de la entrada pasa, una con el otro R5 admitido frena (R5
      distinto y, con A, presupuesto pasado); BASE.R5_ESPERADO vuelve a su valor, también si el control falla;
  T7  la guarda: BASE.G es guardas_lote_r5; su patrón es el de guardas_lote.py (el renglón 16 de a2_2/guardas_a2_2.zsh más
      correr_prueba_T_v2\\.py) más correr_b63\\.py; con el filtro de BASE, sobre líneas de comandos escritas acá (ningún
      proceso), un Python que corre correr_b63.py cuenta y un `pgrep`, un shell, un `grep`, un editor o un Python que lo nombra
      como argumento no;
  T8  el patrón de prueba tiene la forma del real (`<token>\\.py|<token>_b63\\.py`) y no toca el patrón real;
  T9  main: otro sha256, una entrada que no existe, una sin R5 o un --presupuesto-sesion distinto dan el 3 (LOTE_INVALIDO)
      sin escribir registro; sin --entrada, argparse sale con 2;
  T10 un lote que BASE.Lote.validar rechaza (P = 0): el main de r5 da el 3; el de HEAD, un SystemExit de texto (sale con 1);
  T11 otro_paso_pago sobre una tabla de procesos de juguete (pgrep y ps de juguete, ningún proceso): ve al hermano del patrón y al
      hijo de otro lote; no ve a los ancestros, a los descendientes propios ni a los del lote, ni a un pgrep o un shell que lo
      nombran.
El resultado (solo banderas, cuentas y sha256) va a --resultado.

Uso: selftest_lanzar_lote_paralelo_r5.py --entradas <dir> --tmp <dir> --resultado <json>
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
from argparse import Namespace
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent


def importar(nombre: str, ruta: Path):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = m
    spec.loader.exec_module(m)
    return m


R5L = importar("lanzar_lote_paralelo_r5", AQUI / "lanzar_lote_paralelo_r5.py")
BASE = sys.modules["lanzar_lote_paralelo"]
G = sys.modules["guardas_lote_r5"]
GB = sys.modules["guardas_lote"]

A = {"tope_tool_calls_prompt": 30, "max_turns": 32, "max_budget_usd": 1.8}
B = {"tope_tool_calls_prompt": 45, "max_turns": 47, "max_budget_usd": 3.3}
C = {"tope_tool_calls_prompt": 40, "max_turns": 42, "max_budget_usd": 2.6}


def sha_archivo(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frena(f, *args) -> str | None:
    """El texto del SystemExit con texto que levanta f(*args), o None si no frena así."""
    try:
        f(*args)
    except SystemExit as ex:
        return str(ex) if isinstance(ex.code, str) else None
    return None


def ns(tmp: Path, entrada: Path, sha: str, modo: str = "real", presupuesto=None, config="paralelo/seco_r5/config_agentes_r5_A.json"):
    return Namespace(entrada=entrada, sha256_entrada=sha, lote=tmp / "lote_selftest.json", out=tmp / "out", sesiones=tmp / "sesiones",
                     paralelo=1, modo=modo, via="api", tope=10.0, freno=8.0, presupuesto_sesion=presupuesto,
                     lanzador="paralelo/seco_r5/lanzar_agente_r5_prueba.py", timeout_s=60.0, config_agentes=config)


def t1() -> dict:
    return {"admitidos": list(R5L.R5_ADMITIDOS), "R5_ESPERADO_de_HEAD": BASE.R5_ESPERADO,
            "OK": list(R5L.R5_ADMITIDOS) == [A, B] and R5L.R5_ADMITIDOS[0] == BASE.R5_ESPERADO}


def t2() -> dict:
    src = (BANCO_DIR / "b63" / "comun_b63.py").read_text(encoding="utf-8")
    arbol = ast.parse(src)
    fn = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "cargar_entrada")
    lee = sorted({n.slice.value for n in ast.walk(fn) if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                  and n.value.id == "e" and isinstance(n.slice, ast.Constant) and n.slice.value == "R5"})
    exige = any(isinstance(n, ast.Tuple) and any(isinstance(x, ast.Constant) and x.value == "R5" for x in n.elts) for n in ast.walk(fn))
    constante = [t.id for n in arbol.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and n.value.value == "R5"
                 for t in n.targets if isinstance(t, ast.Name)]
    return {"cargar_entrada_lee": lee, "cargar_entrada_lo_exige_entre_los_campos": exige, "constantes_con_nombre": constante,
            "clave_del_lanzador": R5L.CLAVE_R5, "OK": lee == ["R5"] and exige and R5L.CLAVE_R5 == "R5" and not constante}


def t3() -> dict:
    si = [A, B, dict(reversed(list(A.items()))), {"max_budget_usd": 3.30, "max_turns": 47, "tope_tool_calls_prompt": 45}]
    no = [C, {}, A | {"extra": 1}, {k: v for k, v in B.items() if k != "max_turns"},
          {"tope_tool_calls_prompt": 45, "max_turns": 47, "max_budget_usd": 1.8},
          {"tope_tool_calls_prompt": 30, "max_turns": 32, "max_budget_usd": 3.3},
          {"tope_tool_calls_prompt": 30, "max_turns": 47, "max_budget_usd": 1.8},
          {"tope_tool_calls_prompt": 45, "max_turns": 32, "max_budget_usd": 3.3},
          A | {"max_budget_usd": 1.81}, B | {"max_turns": 48}, A | {"max_turns": "32"}]
    r_si, r_no = [R5L.admitido(x) for x in si], [R5L.admitido(x) for x in no]
    return {"admitidos": r_si, "no_admitidos": r_no, "OK": all(r_si) and not any(r_no)}


def t4(ent: Path) -> dict:
    a, b, s = ent / "entrada_juguete_A.json", ent / "entrada_juguete_B.json", ent / "entrada_juguete_sin_R5.json"
    sa, sb = sha_archivo(a), sha_archivo(b)
    r = {"A": R5L.r5_de_la_entrada(a, sa), "B": R5L.r5_de_la_entrada(b, sb),
         "otro_sha256": frena(R5L.r5_de_la_entrada, a, sb), "no_existe": frena(R5L.r5_de_la_entrada, ent / "no_existe.json", sa),
         "sin_R5": frena(R5L.r5_de_la_entrada, s, sha_archivo(s))}
    r["OK"] = (r["A"] == A and r["B"] == B and all(r[k] and r[k].startswith("LOTE INVÁLIDO") for k in ("otro_sha256", "no_existe", "sin_R5")))
    return r


def t5(ent: Path, tmp: Path) -> dict:
    a, b = ent / "entrada_juguete_A.json", ent / "entrada_juguete_B.json"
    sa, sb = sha_archivo(a), sha_archivo(b)
    la, lb = R5L.Lote(ns(tmp, a, sa)), R5L.Lote(ns(tmp, b, sb, config="paralelo/seco_r5/config_agentes_r5_B.json"))
    li = R5L.Lote(ns(tmp, b, sb, modo="init"))
    lig = R5L.Lote(ns(tmp, b, sb, presupuesto=3.3))
    r = {"A": {"presupuesto_sesion": la.a.presupuesto_sesion, "presupuesto_de_la_guarda": la.presupuesto},
         "B": {"presupuesto_sesion": lb.a.presupuesto_sesion, "presupuesto_de_la_guarda": lb.presupuesto},
         "B_init": {"presupuesto_sesion": li.a.presupuesto_sesion, "presupuesto_de_la_guarda": li.presupuesto},
         "B_explicito_igual": lig.a.presupuesto_sesion,
         "B_explicito_1_8": frena(R5L.Lote, ns(tmp, b, sb, presupuesto=1.8)),
         "A_explicito_3_3": frena(R5L.Lote, ns(tmp, a, sa, presupuesto=3.3))}
    r["OK"] = (r["A"] == {"presupuesto_sesion": 1.8, "presupuesto_de_la_guarda": 1.8}
               and r["B"] == {"presupuesto_sesion": 3.3, "presupuesto_de_la_guarda": 3.3}
               and r["B_init"] == {"presupuesto_sesion": 3.3, "presupuesto_de_la_guarda": 0.0} and r["B_explicito_igual"] == 3.3
               and bool(r["B_explicito_1_8"]) and bool(r["A_explicito_3_3"]))
    return r


def t6(ent: Path, tmp: Path) -> dict:
    a, b = ent / "entrada_juguete_A.json", ent / "entrada_juguete_B.json"
    la, lb = R5L.Lote(ns(tmp, a, sha_archivo(a))), R5L.Lote(ns(tmp, b, sha_archivo(b), config="paralelo/seco_r5/config_agentes_r5_B.json"))
    cfg = R5L.LA.rel_repo(tmp / "config_de_una_sesion")

    def ses(r5):
        return {"id": "T6", "estado": "terminada", "carpeta_configuracion": cfg, "r5": dict(r5)}
    previo = BASE.R5_ESPERADO
    r = {"A_con_A": la.control_aislamiento(ses(A)), "A_con_B": la.control_aislamiento(ses(B)),
         "B_con_B": lb.control_aislamiento(ses(B)), "B_con_A": lb.control_aislamiento(ses(A))}
    r["R5_ESPERADO_igual_despues"] = BASE.R5_ESPERADO == previo == A
    try:
        lb.control_aislamiento({"estado": "terminada", "carpeta_configuracion": cfg, "r5": dict(A)})   # sin id: falla adentro
        r["falla_adentro"] = False
    except KeyError:
        r["falla_adentro"] = True
    r["R5_ESPERADO_igual_despues_de_la_falla"] = BASE.R5_ESPERADO == previo
    r["OK"] = (r["A_con_A"] == [] and r["B_con_B"] == [] and any("distinto de" in x for x in r["A_con_B"])
               and any("pasa el presupuesto" in x for x in r["A_con_B"]) and any("distinto de" in x for x in r["B_con_A"])
               and r["R5_ESPERADO_igual_despues"] and r["falla_adentro"] and r["R5_ESPERADO_igual_despues_de_la_falla"])
    return r


def t7() -> dict:
    linea = (BANCO_DIR / "a2_2" / "guardas_a2_2.zsh").read_text(encoding="utf-8").splitlines()[15]
    r16 = linea.split("=", 1)[1].strip().strip("'") if linea.startswith("PATRON=") else None
    casa = "/home/u/carpeta con espacios/bcra-regulatory-kg"          # una ruta con espacios, como la del repo
    cuentan = [f"python3 {casa}/data/experiment/banco_mcp/b63/correr_b63.py --entrada e.json --modo real",
               f"{casa}/.venv/bin/python -B {casa}/data/experiment/banco_mcp/b63/correr_b63.py --modo real",
               "/usr/bin/python3.12 -u /x/correr_b63.py", f"python3 {casa}/x/correr_juez_v2.py",
               "python3 /x/correr_prueba_T_v2.py"]
    no_cuentan = [r"pgrep -f correr_b63\.py", "/bin/zsh -c pgrep -f correr_b63.py", "grep correr_b63.py notas.txt",
                  "vim b63/correr_b63.py", "python3 /x/otro.py /x/correr_b63.py", "python3 /x/correr_b63_copia.py",
                  "/bin/sh /x/correr_b63.sh", "less /x/correr_b63.py"]

    def cuenta(l):
        s = G.script_python(l)
        return bool(s) and re.search(G.PATRON_PAGO_REAL, GB._nombre(s)) is not None
    r = {"BASE_G_es_guardas_lote_r5": BASE.G is G, "G_archivo": R5L.LA.rel_repo(G.__file__),
         "patron_es_el_de_guardas_lote_mas_correr_b63": G.PATRON_PAGO_REAL == GB.PATRON_PAGO + r"|correr_b63\.py",
         "patron_vigente_es_el_real": G.PATRON_PAGO == G.PATRON_PAGO_REAL,
         "guardas_lote_trae_el_renglon_16_mas_T": r16 is not None and GB.PATRON_PAGO == r16 + r"|correr_prueba_T_v2\.py",
         "mismo_filtro_que_BASE": G.script_python is GB.script_python,
         "cuentan": [cuenta(l) for l in cuentan], "no_cuentan": [cuenta(l) for l in no_cuentan],
         "extraccion_es_la_de_BASE": G.PATRON_EXTRACCION == GB.PATRON_EXTRACCION,
         # Fuera del OK, como observación del filtro de BASE: un `python -c` que nombra el script como argumento cuenta (frena
         # de más, del lado seguro), porque el filtro toma como script todo lo que sigue a las opciones hasta el primer `.py`.
         "observado_python_c_que_lo_nombra_cuenta": cuenta("python3 -c import sys; sys.stdin.read() /x/correr_b63.py")}
    r["OK"] = (r["BASE_G_es_guardas_lote_r5"] and r["patron_es_el_de_guardas_lote_mas_correr_b63"] and r["patron_vigente_es_el_real"]
               and r["guardas_lote_trae_el_renglon_16_mas_T"] and r["mismo_filtro_que_BASE"] and all(r["cuentan"])
               and not any(r["no_cuentan"]) and r["extraccion_es_la_de_BASE"])
    return r


def t8() -> dict:
    tok = "rcinco_prueba_paso"
    p = R5L.patron_de_prueba(tok)
    r = {"patron": p, "forma": p == r"rcinco_prueba_paso\.py|rcinco_prueba_paso_b63\.py",
         "ve_los_dos": all(re.search(p, x) for x in ("rcinco_prueba_paso.py", "rcinco_prueba_paso_b63.py")),
         "no_ve_el_real": not any(re.search(p, x) for x in ("correr_b63.py", "correr_juez_v2.py", "correr_prueba_T_v2.py")),
         "el_real_no_lo_ve": not any(re.search(G.PATRON_PAGO_REAL, x) for x in ("rcinco_prueba_paso.py", "rcinco_prueba_paso_b63.py")),
         "patron_vigente_sin_tocar": G.PATRON_PAGO == G.PATRON_PAGO_REAL}
    r["OK"] = all(v for k, v in r.items() if k != "patron")
    return r


def t9(ent: Path, tmp: Path) -> dict:
    a, s = ent / "entrada_juguete_A.json", ent / "entrada_juguete_sin_R5.json"
    sa = sha_archivo(a)
    base = ["--lote", str(tmp / "lote_selftest.json"), "--out", str(tmp / "out_main"), "--sesiones", str(tmp / "sesiones"),
            "--modo", "real", "--tope", "10", "--freno", "8", "--lanzador", "paralelo/seco_r5/lanzar_agente_r5_prueba.py",
            "--config-agentes", "paralelo/seco_r5/config_agentes_r5_A.json"]
    casos = {"otro_sha256": ["--entrada", str(a), "--sha256-entrada", "0" * 64],
             "no_existe": ["--entrada", str(ent / "no_existe.json"), "--sha256-entrada", sa],
             "sin_R5": ["--entrada", str(s), "--sha256-entrada", sha_archivo(s)],
             "presupuesto_distinto": ["--entrada", str(a), "--sha256-entrada", sa, "--presupuesto-sesion", "3.3"]}
    r = {}
    for k, extra in casos.items():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = R5L.main(extra + base)
        r[k] = {"rc": rc, "dice_lote_invalido": buf.getvalue().startswith("LOTE INVÁLIDO")}
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            R5L.main(base)
        r["sin_entrada"] = None
    except SystemExit as ex:
        r["sin_entrada"] = ex.code
    r["registro_escrito"] = (tmp / "out_main" / "registro_lote.json").exists()
    r["OK"] = (all(r[k] == {"rc": R5L.LOTE_INVALIDO, "dice_lote_invalido": True} for k in casos) and r["sin_entrada"] == 2
               and not r["registro_escrito"] and R5L.LOTE_INVALIDO == 3)
    return r


def t10(ent: Path, tmp: Path) -> dict:
    """Un lote inválido para BASE.Lote.validar (P = 0), antes de lanzar nada: el main de r5 da el 3; el main de HEAD sale con un
    SystemExit de texto (código de salida 1 como proceso, no el 3)."""
    a = ent / "entrada_juguete_A.json"
    base = ["--lote", str(tmp / "lote_selftest.json"), "--out", str(tmp / "out_validar"), "--sesiones", str(tmp / "sesiones"),
            "-P", "0", "--modo", "real", "--tope", "10", "--freno", "8", "--lanzador", "paralelo/seco_r5/lanzar_agente_r5_prueba.py",
            "--config-agentes", "paralelo/seco_r5/config_agentes_r5_A.json"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = R5L.main(["--entrada", str(a), "--sha256-entrada", sha_archivo(a)] + base)
    try:
        BASE.main(base)
        codigo_base = "sin SystemExit"
    except SystemExit as ex:
        codigo_base = "texto" if isinstance(ex.code, str) else ex.code
    r = {"r5_rc": rc, "r5_dice_lote_invalido": "LOTE INVÁLIDO" in buf.getvalue(), "HEAD_SystemExit": codigo_base}
    r["OK"] = rc == R5L.LOTE_INVALIDO and r["r5_dice_lote_invalido"] and codigo_base == "texto"
    return r


def t11() -> dict:
    """guardas_lote_r5.otro_paso_pago sobre una tabla de procesos de juguete, con pgrep y ps de juguete (ningún proceso): deja fuera
    los ancestros y los descendientes propios y los del lote, y lo que no es un Python que corre un script del patrón. Así se
    ejercita la exclusión del código, que el pgrep de macOS ya hace por su cuenta con los ancestros del que lo llama."""
    yo = os.getpid()
    tabla = {yo: (900002, "python3 /x/selftest.py"),
             900002: (900001, "python3 /x/b63/correr_b63.py --entrada e"),          # padre, del patrón
             900001: (1, "python3 /x/correr_juez_v2.py"),                           # abuelo, del patrón
             900003: (yo, "python3 /x/b63/correr_b63.py"),                          # hijo, del patrón
             900004: (1, "python3 /otra/b63/correr_b63.py"),                        # hermano, del patrón: cuenta
             900005: (1, "pgrep -f correr_b63.py"),                                # el pgrep de otra guarda
             900006: (1, "/bin/zsh -c correr_b63.py"),                              # un shell que lo nombra
             900007: (900008, "python3 /y/correr_a2_2.py"),                         # hijo de otro lote, del patrón
             900008: (1, "python3 /y/lote_ajeno.py")}

    def pgrep_de_juguete(patron=None):
        return {p for p, (_, args) in tabla.items() if re.search(patron or G.PATRON_PAGO, args)}
    previos = G.pgrep, G.tabla_procesos
    G.pgrep, G.tabla_procesos = pgrep_de_juguete, (lambda: dict(tabla))
    try:
        sin_lote = G.otro_paso_pago()
        con_raiz_yo = G.otro_paso_pago(raiz_lote=yo)
        con_raiz_ajena = G.otro_paso_pago(raiz_lote=900008)
    finally:
        G.pgrep, G.tabla_procesos = previos
    r = {"pgrep_de_juguete_devuelve": sorted(pgrep_de_juguete(G.PATRON_PAGO_REAL)),
         "sin_raiz": sin_lote, "raiz_propia": con_raiz_yo, "raiz_del_otro_lote": con_raiz_ajena,
         "restaurado": (G.pgrep, G.tabla_procesos) == previos}
    esperado = [{"pid": 900004, "script": "correr_b63.py"}, {"pid": 900007, "script": "correr_a2_2.py"}]
    r["OK"] = (sin_lote == esperado and con_raiz_yo == esperado and con_raiz_ajena == esperado[:1] and r["restaurado"]
               and r["pgrep_de_juguete_devuelve"] == [900001, 900002, 900003, 900004, 900005, 900006, 900007])
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entradas", type=Path, required=True)
    ap.add_argument("--tmp", type=Path, required=True)
    ap.add_argument("--resultado", type=Path, required=True)
    a = ap.parse_args()
    a.tmp.mkdir(parents=True, exist_ok=True)
    (a.tmp / "lote_selftest.json").write_text('{"sesiones": []}\n', encoding="utf-8")
    res = {"unidad": "U-BANCO-R5-a — selftest del lanzador del lote r5 (USD 0, sin procesos)",
           "modulos": {n: {"ruta": R5L.LA.rel_repo(m.__file__), "sha256": sha_archivo(Path(m.__file__))}
                       for n, m in (("lanzar_lote_paralelo_r5", R5L), ("lanzar_lote_paralelo", BASE), ("guardas_lote_r5", G),
                                    ("guardas_lote", GB), ("lanzar_agente", R5L.LA))}}
    for nombre, f in (("T1", t1), ("T2", t2), ("T3", t3), ("T4", lambda: t4(a.entradas)), ("T5", lambda: t5(a.entradas, a.tmp)),
                      ("T6", lambda: t6(a.entradas, a.tmp)), ("T7", t7), ("T8", t8), ("T9", lambda: t9(a.entradas, a.tmp)),
                      ("T10", lambda: t10(a.entradas, a.tmp)), ("T11", t11)):
        try:
            res[nombre] = f()
        except Exception as ex:                       # un control que se rompe es un fallo, con su tipo
            res[nombre] = {"OK": False, "excepcion": type(ex).__name__, "mensaje": str(ex)[:300]}
    ok = {k: v["OK"] for k, v in res.items() if k.startswith("T")}
    res["resumen"] = {"OK": sum(ok.values()), "FALLA": [k for k, v in ok.items() if not v], "total": len(ok)}
    a.resultado.parent.mkdir(parents=True, exist_ok=True)
    a.resultado.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in ok.items():
        print(f"{k}: {'OK' if v else 'FALLA'}")
    print(f"selftest: {res['resumen']['OK']}/{res['resumen']['total']} OK")
    return 0 if not res["resumen"]["FALLA"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
