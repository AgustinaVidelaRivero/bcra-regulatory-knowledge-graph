#!/usr/bin/env python3
"""selftest_servidor_mcp_kg_nav_cand.py — N6 de U-NAV-DISENO: selftest del servidor nuevo del grafo
(servidor_mcp_kg_nav_cand.py), sin modelo de lenguaje (USD 0), con el doble sin Neo4j de selftest_familias_nav.py
(_DriverSinNeo4j, importado sin cambiarlo) y sobre el Neo4j propio de N6 (bolt://127.0.0.1:57687).

Casos:
  S1 (sin Neo4j) las 8 configuraciones de N4, §2: para cada una, la lista de herramientas que arma el servidor con las
     familias de su config es la esperada (ESPERADAS, escrita aparte), en su orden; la de config_agentes_n6.json es la
     misma en el orden del CLI; cada config del servidor es la de config_mcp_kg_nav_acumulado.json de HEAD con solo
     version, familias, firma_tools, configuracion_n6 y nota cambiados; una familia fuera de 1 a 5 aborta;
  S2 (sin Neo4j) despachar_cand le pasa a familias_nav.despachar, tal cual (los mismos objetos), las seis herramientas de
     HEAD, y devuelve lo que esa da; `ver_descendientes` no pasa por ahí. Sobre el índice por punto real y el doble: el
     despacho del servidor nuevo da lo mismo que familias_nav.despachar en buscar_puntos (sin el denso), y lo mismo que
     NavegadorCand.ver_descendientes directo;
  S3 (Neo4j, por stdio con banco_mcp/cliente_falso.py) las 8 configuraciones, una por una: el servidor lista las herramientas
     esperadas, con la definición de harness.TOOLS en las tres de hoy y la de TOOLS_NAV_CAND en las demás, y las tres de hoy
     dan, byte a byte, la cadena del servidor de hoy (servidor_mcp_kg.despachar y serializar_payload);
  S4 (Neo4j, por stdio, la configuración T) `ver_descendientes`: en cada punto con hijos y en los casos de borde (niveles
     1 a 3 y fuera de rango, `desde` del pie y fuera de rango, un punto que no existe, un TO, «::intro»), la salida del
     servidor es, byte a byte, la de familias_nav_cand.despachar_cand sobre un NavegadorCand directo del mismo Neo4j y el
     mismo índice; la salida de la llamada queda en el log R1 de la sesión (`output_str`, la que lee el instrumento de
     citas) con los mismos bytes; ver_punto, ver_remisiones, indice_to y la familia 5, en una muestra, dan lo mismo que
     familias_nav.despachar. buscar_puntos por el servidor usa el denso: lo cubre S2 (el despacho) y la medición de la
     memoria de N6, que hace una consulta de prueba.
Imprime y guarda solo pasa/falla, cuentas y sha256 (el acumulado trae la tanda 1: cegamiento, mandato, §7, regla 5).
Uso (desde la raíz de la copia, con NEO4J_URI y BANCO_VENV_VECTOR):
  .venv/bin/python -B data/experiment/banco_mcp/mcp_kg/selftest_servidor_mcp_kg_nav_cand.py [--sin-neo4j] --salida <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import selftest_familias_nav as STF  # noqa: E402  (el doble sin Neo4j, sin cambios; agrega banco y neo4j al path)
import servidor_mcp_kg_nav_cand as CAND  # noqa: E402
import familias_nav as FN  # noqa: E402
import familias_nav_cand as FNC  # noqa: E402
from comun_banco import serializar_payload  # noqa: E402

BASE = CAND.BASE
N6_DIR = BANCO_DIR / "n6"
CONFIG_AGENTES = N6_DIR / "config_agentes_n6.json"
CONFIG_ACUM = AQUI / "config_mcp_kg_nav_acumulado.json"
NEO4J_URI_N6 = "bolt://127.0.0.1:57687"
TRES = ["buscar_nodos", "ver_nodo", "ver_vecinos"]
F = {1: ["buscar_puntos"], 2: ["ver_punto"], 3: ["ver_remisiones"], 4: ["indice_to"],
     5: ["tipos_de_relacion", "vecinos_por_relacion"]}
# Las listas esperadas, en el orden del servidor (las tres de hoy y TOOLS_NAV_CAND filtrada), escritas aparte (N4, §2).
ESPERADAS = {
    "B": TRES,
    "T": TRES + F[1] + F[2] + F[3] + F[4] + F[5] + ["ver_descendientes"],
    "T-F1": TRES + F[2] + F[3] + F[4] + F[5] + ["ver_descendientes"],
    "T-F2": TRES + F[1] + F[3] + F[4] + F[5],
    "T-F3": TRES + F[1] + F[2] + F[4] + F[5] + ["ver_descendientes"],
    "T-F4": TRES + F[1] + F[2] + F[3] + F[5] + ["ver_descendientes"],
    "T-F5": TRES + F[1] + F[2] + F[3] + F[4] + ["ver_descendientes"],
    "T-F6": TRES + F[1] + F[2] + F[3] + F[4] + F[5] + ["ver_descendientes"],
}
CAMBIAN_EN_LA_CONFIG = {"version", "familias", "firma_tools", "configuracion_n6", "nota"}
SIN_CODIFICADOR = {"T-F1"}       # además, sin el denso (armar_configuraciones_n6.SIN_CODIFICADOR)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Resultado:
    def __init__(self):
        self.casos = []

    def caso(self, nombre: str, ok: bool, detalle: str = "") -> None:
        self.casos.append({"caso": nombre, "ok": bool(ok), "detalle": detalle})
        print(f"{'OK  ' if ok else 'FALLA'} {nombre}" + (f" · {detalle}" if detalle else ""), flush=True)


def configs() -> dict:
    ca = json.loads(CONFIG_AGENTES.read_text(encoding="utf-8"))
    out = {}
    for brazo, b in ca["brazos"].items():
        if b.get("servidor") != "kg":
            continue
        ruta = BANCO_DIR / b["config_servidor"]
        out[b["configuracion_n6"]] = {"brazo": brazo, "agentes": b, "ruta": ruta,
                                      "config": json.loads(ruta.read_text(encoding="utf-8"))}
    return out


# --------------------------------------------------------------------------- #
def s1(R: Resultado, cs: dict) -> None:
    R.caso("S1 las 8 configuraciones del grafo en config_agentes_n6.json", sorted(cs) == sorted(ESPERADAS),
           f"{len(cs)}: {sorted(cs)}")
    acum = json.loads(CONFIG_ACUM.read_text(encoding="utf-8"))
    for cid in sorted(ESPERADAS):
        c = cs[cid]["config"]
        nombres = [t["name"] for t in CAND.tools_de(c["familias"])]
        defs = {t["name"]: t for t in list(BASE.TOOLS) + FNC.TOOLS_NAV_CAND}
        defs_ok = all(t is defs[t["name"]] for t in CAND.tools_de(c["familias"]))
        cli = sorted(f"mcp__kg__{n}" for n in nombres) == cs[cid]["agentes"]["tools_esperadas"]
        cambian = CAMBIAN_EN_LA_CONFIG | ({"denso"} if cid in SIN_CODIFICADOR else set())
        solo = {k for k in set(acum) | set(c) if acum.get(k) != c.get(k)} <= cambian
        denso_ok = ((c.get("denso") or {}).get("requerido") is False) == (cid in SIN_CODIFICADOR)
        R.caso(f"S1 {cid}: la lista del servidor es la esperada ({len(nombres)} herramientas)",
               nombres == ESPERADAS[cid] and defs_ok and cli and solo and denso_ok,
               f"orden del servidor {'=' if nombres == ESPERADAS[cid] else '≠'}; la del CLI {'=' if cli else '≠'}; "
               f"config = la de HEAD salvo {sorted(cambian)}: {solo}; "
               f"{'sin' if cid in SIN_CODIFICADOR else 'con'} el denso: {denso_ok}")
    try:
        CAND.tools_de([1, 6])
        aborta = False
    except SystemExit:
        aborta = True
    R.caso("S1 una familia fuera de 1 a 5 aborta (la validación de HEAD)", aborta)


def s2(R: Resultado, cs: dict) -> None:
    llamados = []
    real = FNC.FN.despachar

    def espia(nav, name, args):
        llamados.append((nav, name, args))
        return f"<espía {name}>"
    nav_falso = object()
    ok = True
    try:
        FNC.FN.despachar = espia
        for name in ("buscar_puntos", "ver_punto", "ver_remisiones", "indice_to", "tipos_de_relacion", "vecinos_por_relacion"):
            args = {"x": name}
            llamados.clear()
            out = FNC.despachar_cand(nav_falso, name, args)
            ok = ok and out == f"<espía {name}>" and len(llamados) == 1 and llamados[0][0] is nav_falso \
                and llamados[0][1] == name and llamados[0][2] is args
        llamados.clear()
        nav_cand_falso = SimpleNamespace(ver_descendientes=lambda p, n, d: f"<vd {p} {n} {d}>")
        vd = FNC.despachar_cand(nav_cand_falso, "ver_descendientes", {"punto": "x::1", "niveles": 3})
        ok_vd = vd == "<vd x::1 3 0>" and not llamados
    finally:
        FNC.FN.despachar = real
    R.caso("S2 despachar_cand le pasa a familias_nav.despachar, tal cual, las seis de HEAD", ok)
    R.caso("S2 ver_descendientes no pasa por familias_nav.despachar y lleva sus valores por defecto", ok_vd)
    c = cs["T"]["config"]
    indice_dir = (AQUI / c["indice_puntos"]).resolve()
    drv = STF._DriverSinNeo4j(indice_dir, c["kg_sha256_esperado"])
    from grafos import GRAFOS  # noqa: E402
    nav = FNC.NavegadorCand(drv, GRAFOS[c["grafo"]]["label"], indice_dir, sha256_manifiesto=c["sha256_manifiesto_indice"],
                            python_vector=None, hubs_esperados=None)
    nombres = {t["name"] for t in CAND.tools_de(c["familias"]) if "familia" in t}
    consultas = [{"consulta": "plazo de conservación de la documentación"}, {"consulta": "requisitos", "to": "cla"},
                 {"consulta": "excepción", "punto": "cla::5.1", "limite": 3}, {"consulta": "monto", "desde": 8}, {}]
    iguales = sum(CAND.despachar(nav, None, nombres, "buscar_puntos", a) == FN.despachar(nav, "buscar_puntos", a)
                  for a in consultas)
    R.caso("S2 sin Neo4j: buscar_puntos por el despacho del servidor nuevo = familias_nav.despachar (sin el denso)",
           iguales == len(consultas), f"{iguales} de {len(consultas)}")
    con_hijos = sorted(k for k, p in nav.puntos.items() if p["tipo"] != "to" and p["hijos"])[:200]
    iguales = sum(CAND.despachar(nav, None, nombres, "ver_descendientes", {"punto": k}) == nav.ver_descendientes(k)
                  for k in con_hijos)
    R.caso("S2 sin Neo4j: ver_descendientes por el despacho del servidor nuevo = NavegadorCand directo",
           iguales == len(con_hijos), f"{iguales} de {len(con_hijos)} puntos con hijos")


# --------------------------------------------------------------------------- #
def env_servidor(log: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k in ("NEO4J_URI", "BANCO_VENV_VECTOR", "PATH", "HOME", "TMPDIR")}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "BANCO_LOG_R1": str(log), "BANCO_SESION_TAG": "selftest_cand",
                "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    return env


def bateria(nav) -> tuple[list, list, list]:
    """(las tres de hoy, ver_descendientes, las otras de la navegación): las llamadas de S3 y S4, sobre el NavegadorCand del
    Neo4j de N6 (la usa también n6/comparar_tf1_sin_codificador.py)."""
    ids = sorted(nav.nodos)[:: max(1, len(nav.nodos) // 6)][:6]
    base = [("buscar_nodos", {"consulta": "plazo"}), ("buscar_nodos", {"consulta": "excepción", "limite": 3}),
            ("ver_nodo", {"id": ids[0]}), ("ver_vecinos", {"id": ids[1]}),
            ("ver_vecinos", {"id": sorted(nav.hubs)[0], "direccion": "entrantes"}), ("ver_nodo", {"id": "x"})]
    muestra = sorted(k for k, p in nav.puntos.items() if p["tipo"] != "to")[::60]
    otras = ([("ver_punto", {"punto": k}) for k in muestra] + [("ver_remisiones", {"punto": k}) for k in muestra[::3]]
             + [("indice_to", {"to": t}) for t in nav.tos] + [("tipos_de_relacion", {"id": i}) for i in ids]
             + [("vecinos_por_relacion", {"id": sorted(nav.hubs)[0], "relacion": "aplica_a",
                                          "direccion": "entrantes", "to": "cla"})])
    return base, [("ver_descendientes", a) for a in casos_ver_descendientes(nav)], otras


def casos_ver_descendientes(nav) -> list[dict]:
    con_hijos = sorted(k for k, p in nav.puntos.items() if p["tipo"] != "to" and p["hijos"])
    casos = [{"punto": k} for k in con_hijos]
    casos += [{"punto": k, "niveles": n} for k in con_hijos[::25] for n in (1, 3, 0, 9, "x")]
    largos = [k for k in con_hijos if "pedí desde=" in nav.ver_descendientes(k, 3)][:40]
    for k in largos:
        out = nav.ver_descendientes(k, 3)
        d = int(out.rsplit("pedí desde=", 1)[1].split(",", 1)[0])
        casos += [{"punto": k, "niveles": 3, "desde": d}, {"punto": k, "niveles": 3, "desde": 10 ** 6},
                  {"punto": k, "niveles": 3, "desde": -4}]
    casos += [{"punto": "no::existe"}, {"punto": "cla"}, {"punto": "cla::5.1.1::intro"}, {"punto": ""}, {},
              {"punto": "Punto 5.1.1", "niveles": 2}, {"punto": con_hijos[0], "niveles": None, "desde": "y"}]
    return casos


def s3_s4(R: Resultado, cs: dict, salida: Path) -> dict:
    from cliente_falso import ClienteFalso  # noqa: E402
    from conexion import abrir_driver  # noqa: E402
    from grafos import GRAFOS  # noqa: E402
    if os.environ.get("NEO4J_URI") != NEO4J_URI_N6:
        raise SystemExit(f"FRENO: NEO4J_URI no es la del Neo4j propio de N6 ({NEO4J_URI_N6})")
    resumen = {}
    index, _ = BASE.abrir_backend(cs["B"]["config"])
    driver = abrir_driver()
    c = cs["T"]["config"]
    nav = FNC.NavegadorCand(driver, GRAFOS[c["grafo"]]["label"], (AQUI / c["indice_puntos"]).resolve(),
                            sha256_manifiesto=c["sha256_manifiesto_indice"], python_vector=None,
                            hubs_esperados=c["hubs_esperados"])
    base_llamadas = bateria(nav)[0] + [("ver_punto", {"punto": "cla::5.1.1"})]
    esperado_base = [serializar_payload(BASE.despachar(index, n, a)) for n, a in base_llamadas]
    defs = {t["name"]: t for t in list(BASE.TOOLS) + FNC.TOOLS_NAV_CAND}
    for cid in sorted(ESPERADAS):
        log = salida / f"log_r1_selftest_cand_{cid}.jsonl"
        t0 = time.time()
        cmd = [sys.executable, "-B", str(AQUI / "servidor_mcp_kg_nav_cand.py"), "--config", str(cs[cid]["ruta"])]
        with ClienteFalso(cmd=cmd, env=env_servidor(log), cwd=AQUI.parents[3]) as cli:
            tools = cli.listar_tools()
            nombres = [t["name"] for t in tools]
            defs_ok = all((t["description"], t["input_schema"]) == (defs[t["name"]]["description"],
                                                                    defs[t["name"]]["input_schema"]) for t in tools)
            llamadas = base_llamadas if cid == "B" else base_llamadas[:-1]
            base_ok = [cli.llamar(n, a) for n, a in llamadas] == esperado_base[:len(llamadas)]
            R.caso(f"S3 {cid} por stdio: lista las {len(ESPERADAS[cid])} esperadas, con su definición",
                   nombres == ESPERADAS[cid] and defs_ok, f"{len(nombres)} herramientas")
            R.caso(f"S3 {cid} por stdio: las tres de hoy, byte a byte iguales al servidor de hoy", base_ok,
                   f"{len(llamadas)} llamadas" + (" (con una de navegación, desconocida para B)" if cid == "B" else ""))
            if cid == "T":
                casos = casos_ver_descendientes(nav)
                n_ok, shas = 0, []
                for a in casos:
                    s_out = cli.llamar("ver_descendientes", a)
                    d_out = FNC.despachar_cand(nav, "ver_descendientes", a)
                    n_ok += s_out == d_out
                    shas.append(sha(s_out))
                R.caso("S4 T: ver_descendientes por el servidor = despachar_cand, byte a byte", n_ok == len(casos),
                       f"{n_ok} de {len(casos)} llamadas; con pie de desde: {sum('pedí desde=' in FNC.despachar_cand(nav, 'ver_descendientes', a) for a in casos)}")
                resumen["sha256_salidas_ver_descendientes"] = sha("\n".join(shas))
                resumen["n_ver_descendientes"] = len(casos)
                otras = bateria(nav)[2]
                n2 = sum(cli.llamar(n, a) == FN.despachar(nav, n, a) for n, a in otras)
                R.caso("S4 T: ver_punto, ver_remisiones, indice_to y la familia 5 por el servidor = familias_nav.despachar",
                       n2 == len(otras), f"{n2} de {len(otras)}")
                resumen["n_otras_familias"] = len(otras)
                n_llamadas_t = len(llamadas) + len(casos) + len(otras)
        lineas = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
        ll = [x for x in lineas if x.get("evento") == "llamada"]
        ini = next((x for x in lineas if x.get("evento") == "inicio"), {})
        R.caso(f"S3 {cid}: el log R1 de la sesión, con inicio, fin y sus llamadas",
               bool(ini) and any(x.get("evento") == "fin" for x in lineas)
               and len(ll) == (n_llamadas_t if cid == "T" else len(llamadas))
               and ini.get("version_servidor") == CAND.VERSION_SERVIDOR,
               f"{len(ll)} llamadas, servidor {ini.get('version_servidor')}, {round(time.time() - t0, 1)} s")
        if cid == "T":
            vd = [x for x in ll if x.get("tool") == "ver_descendientes"]
            casos_vd = casos_ver_descendientes(nav)
            bytes_ok = len(vd) == len(casos_vd) and all(
                x.get("output_str") == FNC.despachar_cand(nav, "ver_descendientes", a) and x.get("output_sha256") == sha(x.get("output_str") or "")
                for x, a in zip(vd, casos_vd))
            R.caso("S4 T: el log R1 guarda la salida de ver_descendientes con los mismos bytes (output_str, la del lector de citas)",
                   bytes_ok, f"{len(vd)} líneas")
        log.unlink()
    driver.close()
    index.driver.close() if hasattr(index, "driver") else None
    return resumen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-neo4j", action="store_true", help="solo S1 y S2")
    ap.add_argument("--salida", type=Path, required=True, help="carpeta del resultado (fuera del repo)")
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)
    R = Resultado()
    t0 = time.time()
    cs = configs()
    s1(R, cs)
    s2(R, cs)
    extra = {} if a.sin_neo4j else s3_s4(R, cs, a.salida)
    fallas = [c["caso"] for c in R.casos if not c["ok"]]
    out = {"selftest": "selftest_servidor_mcp_kg_nav_cand.py", "modo": "sin Neo4j" if a.sin_neo4j else "con Neo4j",
           "casos": R.casos, "n_casos": len(R.casos), "fallas": fallas, **extra, "duracion_s": round(time.time() - t0, 1)}
    (a.salida / ("selftest_servidor_cand_" + ("sin_neo4j" if a.sin_neo4j else "con_neo4j") + ".json")).write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(R.casos) - len(fallas)} de {len(R.casos)} casos OK")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
