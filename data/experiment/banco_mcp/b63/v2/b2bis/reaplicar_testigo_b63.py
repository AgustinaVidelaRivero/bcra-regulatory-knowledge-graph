#!/usr/bin/env python3
"""reaplicar_testigo_b63.py (v2/b2bis, etapa b2 bis) — El testigo v2 (aislamiento/testigo_aislamiento_b63_v2.py, con la excepción cerrada
de la decisión de la autora del 28/10/2026, 10:35:10) sobre la captura de la corrida real del testigo de la b2 (el --tmp de
b63/v2/b2/medir_testigo_b63.py), sin ninguna sesión nueva: no lanza ningún CLI ni ningún servidor, y no escribe en la captura.

Lo que hace:
  1. los pedidos: los de la captura privada de la b2, uno por archivo, con la ruta y la clave por presencia que registró la b2 en
     testigo_resultado.json; controla sus bytes y su sha256 contra ese resultado;
  2. los testigos: los mismos de la b2 (los dos del repo, por `git show HEAD`, y el de la cuenta), con su sha256 contra los de la b2;
  3. los tokens de los plantados: de la línea de comandos de cada negativo (testigo_tmp/), con el sha256 de su renglón contra el del
     plantado de la b2;
  4. por sesión, controlar_sesion del testigo v2 sobre su stream, su log_r1, su carpeta de configuración y sus pedidos, con su marcador
     (sesion_<id>.json). Sin las descripciones de las herramientas, que pedirían un servidor, los trechos permitidos van vacíos: como en
     la b2 ninguna sesión excluyó ningún trecho (trechos_excluidos_por_su_configuracion, 0), los efectivos son los mismos, y el control
     del paso 5 lo comprueba. De la b2, tal cual: el rc de cada CLI, la comparación con el init y el cwd vacío; los negativos; las tandas
     y sus otras conexiones; y los controles de los testigos y del cwd después de la corrida;
  5. el control: cada campo que recalcula controlar_sesion da el de la b2, y el FRENO y el PASS tal cual, los de la b2;
  6. el cierre del testigo v2 (cerrar_resultado): FRENO_con_la_excepcion, PASS_de_B63, PASS_del_testigo_tal_cual y excepcion_aplicada;
     y, como control cruzado, leer_testigo de la b2 (b63/v2/b2/correr_b63.py, sin cambiar) sobre el resultado tal cual y sobre el FRENO
     con la excepción.
Escribe un JSON sin texto: cuentas, banderas, sha256 y los renglones de FRENO (ids de sesión y cuentas).

Uso (con env -i, PATH y HOME; sin ninguna clave): <python del .venv> -B data/experiment/banco_mcp/b63/v2/b2bis/reaplicar_testigo_b63.py
  --captura <el --tmp de medir_testigo_b63> --resultado <json fuera del repo>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # data/experiment/banco_mcp/b63/v2/b2bis
BANCO_DIR = AQUI.parents[2]                                 # data/experiment/banco_mcp
for _p in (BANCO_DIR / "aislamiento", BANCO_DIR / "b63" / "v2" / "b2"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import testigo_aislamiento_b63_v2 as T                       # noqa: E402
import correr_b63 as RB2                                    # noqa: E402  (leer_testigo de la b2, sin cambiar)

CONFIG = BANCO_DIR / "b63" / "v2" / "b2" / "config_agentes_b63.json"
SHA_CONFIG = "eaff32bbad93cb9bc1f9d66ea2c4887cba8268f71007be6bb7158cc97bf0d0c4"
DE_LA_B2 = ("rc", "comparacion_con_init", "cwd_vacio")      # lo que la reaplicación toma de la b2, tal cual
NUEVOS = ("log_r1_con_la_excepcion", "excepcion_aplicada", "testigos_que_llegan_con_la_excepcion")


class CapturaGuardada:
    """En lugar de Captura (el servidor de la b2): sus pedidos, desde los archivos de la captura privada y el resultado de la b2."""

    def __init__(self, privado: Path, r2: dict):
        self.pedidos: dict[str, list[dict]] = {}
        self.fallas: list[str] = []
        for sid, r in r2["por_sesion"].items():
            lista = []
            for pe in r["pedidos"]:
                f = privado / sid / f"pedido_{pe['n']}.json"
                b = f.read_bytes() if f.is_file() else b""
                if len(b) != pe["bytes"] or T.sha(b) != pe["sha256"]:
                    self.fallas.append(f"{sid}, pedido {pe['n']}")
                lista.append({"n": pe["n"], "ruta": pe["ruta"], "bytes": len(b), "sha256": T.sha(b), "con_clave": pe["con_clave"],
                              "archivo": f})
            if len(list((privado / sid).glob("pedido_*.json"))) != len(lista):
                self.fallas.append(f"{sid}: otra cantidad de pedidos")
            self.pedidos[sid] = lista


def cargar_testigos() -> tuple[dict, dict]:
    """Los testigos y sus sha256, como los arma fase_testigo de la b2."""
    testigos, sha_t = {}, {}
    for r in T.TESTIGOS_REPO:
        b = subprocess.run(["git", "-C", str(T.REPO_REAL), "--no-optional-locks", "show", f"HEAD:{r}"], capture_output=True,
                           check=True).stdout
        testigos[f"repo:{r}"] = T.trechos(b.decode("utf-8"))
        sha_t[f"repo:{r}"] = {"HEAD": T.sha(b), "archivo": T.sha((T.REPO_REAL / r).read_bytes())}
    if T.CUENTA.is_file():
        b = T.CUENTA.read_bytes()
        testigos["cuenta:.claude/CLAUDE.md"] = T.trechos(b.decode("utf-8", errors="replace"))
        sha_t["cuenta:.claude/CLAUDE.md"] = {"archivo": T.sha(b)}
    return testigos, sha_t


def tokens_de_los_plantados(tmp_testigo: Path, plan: dict, r2: dict) -> tuple[dict, bool]:
    """Los tokens de los plantados, de la línea de comandos de cada negativo; y si cada renglón da el sha256 del plantado de la b2."""
    tokens, ok = {}, True
    for b, plantado in plan["negativos"]:
        argv = json.loads((tmp_testigo / f"linea_de_comandos_NEGATIVO-{b}.json").read_text(encoding="utf-8"))["argv"]
        renglon = argv[argv.index("--append-system-prompt") + 1]
        ok = ok and T.sha((renglon + "\n").encode("utf-8")) == r2["testigos"]["plantados"][plantado]["sha256"]
        tokens[plantado] = renglon.rsplit(": ", 1)[1]
    return tokens, ok


def enmascarar(o, captura: Path):
    """Como el main del testigo de la b2: el --tmp del testigo -> <tmp>, la carpeta personal -> $HOME."""
    return json.loads(json.dumps(o, ensure_ascii=False).replace(str((captura / "testigo_tmp").resolve()), "<tmp>")
                      .replace(str(Path.home()), "$HOME"))


def reaplicar(captura: Path) -> dict:
    captura = Path(captura).resolve()
    if T.sha(CONFIG.read_bytes()) != SHA_CONFIG:
        raise SystemExit("FRENO: la configuración de agentes de B6.3 no da su sha256")
    cfg = T.cargar_configuracion(CONFIG, SHA_CONFIG)
    plan = T.plan_de_la_configuracion(cfg, False)
    r2 = json.loads((captura / "testigo_resultado.json").read_text(encoding="utf-8"))
    control: dict = {}
    control["plan_igual_al_de_la_b2"] = ([b for b, _ in plan["negativos"]] == r2["plan"]["negativos"]
                                         and plan["tandas"] == r2["plan"]["tandas"])
    cap = CapturaGuardada(captura / "testigo_privado_captura", r2)
    control["pedidos_con_sus_bytes_y_su_sha256"] = not cap.fallas
    control["pedidos_que_no_dan"] = cap.fallas
    testigos, sha_t = cargar_testigos()
    control["testigos_iguales_a_los_de_la_b2"] = (sha_t == r2["testigos"]["sha256_antes"]
                                                  and {k: len(v) for k, v in testigos.items()} == r2["testigos"]["trechos"])
    tokens, ok_tok = tokens_de_los_plantados(captura / "testigo_tmp", plan, r2)
    control["tokens_de_los_plantados_con_el_sha256_de_la_b2"] = ok_tok
    por_sesion, distintos = {}, {}
    for sid, rb in r2["por_sesion"].items():
        d = captura / "testigo" / sid
        ses = json.loads((d / f"sesion_{sid}.json").read_text(encoding="utf-8"))
        st = (d / f"stream_{sid}.jsonl").stat()
        s = {"id": sid, "brazo": ses["brazo"], "out": d, "log_r1": d / f"log_r1_{sid}.jsonl", "rc": rb["rc"],
             "config_cli": captura / "testigo_ses" / "config" / ses["session_id"],
             "t0": getattr(st, "st_birthtime", st.st_mtime), "t1": st.st_mtime}
        r = T.controlar_sesion(s, cap, testigos, set(), tokens, ses["marcador"], T.config_de_servidor(cfg, ses["brazo"]))
        r["comparacion_con_init"], r["cwd_vacio"] = rb["comparacion_con_init"], rb["cwd_vacio"]
        m = enmascarar({k: v for k, v in r.items() if k not in NUEVOS}, captura)
        distintos[sid] = sorted(k for k in set(m) | set(rb) if m.get(k) != rb.get(k))
        por_sesion[sid] = r
    control["por_sesion_reproduce_la_b2"] = {sid: not v for sid, v in distintos.items()}
    control["campos_que_no_reproducen"] = {sid: v for sid, v in distintos.items() if v}
    res = {k: r2[k] for k in ("captura", "configuracion", "plan", "testigos", "tandas", "claves_distintas_de_la_invalida",
                              "pedidos_que_no_son_POST", "pedidos_sin_sesion", "testigos_despues", "cwd_al_final")}
    res["por_sesion"], res["negativo"] = por_sesion, r2["negativo"]
    res = T.cerrar_resultado(res, r2["plan"]["en_cada_tanda"], [{"id": i, "brazo": r["brazo"]} for i, r in por_sesion.items()])
    for k in ("FRENO", "PASS", "sha256_por_brazo_y_pedido", "otras_conexiones_de_los_cli_declaradas",
              "ningun_pedido_al_modelo_sale_de_la_maquina"):
        control[f"{k}_tal_cual_igual_al_de_la_b2"] = enmascarar(res[k], captura) == r2[k]
    control["reproduce_la_b2"] = (control["plan_igual_al_de_la_b2"] and control["pedidos_con_sus_bytes_y_su_sha256"]
                                  and control["testigos_iguales_a_los_de_la_b2"]
                                  and control["tokens_de_los_plantados_con_el_sha256_de_la_b2"]
                                  and all(control["por_sesion_reproduce_la_b2"].values())
                                  and all(control[f"{k}_tal_cual_igual_al_de_la_b2"]
                                          for k in ("FRENO", "PASS", "sha256_por_brazo_y_pedido",
                                                    "otras_conexiones_de_los_cli_declaradas",
                                                    "ningun_pedido_al_modelo_sale_de_la_maquina")))
    lt_tal = RB2.leer_testigo(res)
    lt_exc = RB2.leer_testigo(dict(res, FRENO=res["FRENO_con_la_excepcion"]))
    causa = [l for l in res["FRENO"] if l not in res["FRENO_con_la_excepcion"]]
    return {"que": "el testigo v2 sobre la captura de la b2, sin ninguna sesión nueva (USD 0)",
            "control": control,
            "PASS_de_B63": res["PASS_de_B63"], "PASS_del_testigo_tal_cual": res["PASS_del_testigo_tal_cual"],
            "excepcion_aplicada": res["excepcion_aplicada"],
            "por_que_PASS_del_testigo_tal_cual_es_false": {
                "renglones_de_la_fecha": lt_tal["renglones_de_la_fecha"],
                "renglones_que_pasan_por_la_excepcion": causa,
                "otros": [l for l in lt_tal["otros_FRENO"] if l not in causa]},
            "FRENO_tal_cual": {"n": len(res["FRENO"])},
            "FRENO_con_la_excepcion": res["FRENO_con_la_excepcion"],
            "leer_testigo_de_la_b2": {"sobre_el_resultado_tal_cual": lt_tal, "sobre_el_FRENO_con_la_excepcion": lt_exc,
                                      "su_PASS_de_B63_con_la_excepcion_es_el_del_testigo_v2": lt_exc["PASS_de_B63"] == res["PASS_de_B63"]},
            "por_sesion": {i: {"testigos_que_llegan": r["testigos_que_llegan"],
                               "testigos_que_llegan_con_la_excepcion": r["testigos_que_llegan_con_la_excepcion"],
                               "log_r1": r["log_r1"], "log_r1_con_la_excepcion": r["log_r1_con_la_excepcion"]}
                           for i, r in por_sesion.items()}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--captura", type=Path, required=True)
    ap.add_argument("--resultado", type=Path, required=True)
    a = ap.parse_args(argv)
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ABORTO: la reaplicación corre sin ninguna clave en el entorno")
    sal = a.resultado.resolve()
    if sal.is_relative_to(T.REPO_REAL.resolve()) or sal.is_relative_to(BANCO_DIR.parents[2].resolve()):
        raise SystemExit("ABORTO: --resultado dentro del repo")
    out = reaplicar(a.captura)
    sal.parent.mkdir(parents=True, exist_ok=True)
    sal.write_text(json.dumps(out, ensure_ascii=False, indent=1).replace(str(Path(a.captura).resolve()), "<captura>")
                   .replace(str(Path.home()), "$HOME") + "\n", encoding="utf-8")
    print(json.dumps({"reproduce_la_b2": out["control"]["reproduce_la_b2"], "PASS_de_B63": out["PASS_de_B63"],
                      "PASS_del_testigo_tal_cual": out["PASS_del_testigo_tal_cual"],
                      "renglones_que_pasan_por_la_excepcion": out["excepcion_aplicada"]["renglones_del_FRENO_que_pasan"]},
                     ensure_ascii=False), flush=True)
    return 0 if out["control"]["reproduce_la_b2"] else 10


if __name__ == "__main__":
    raise SystemExit(main())
