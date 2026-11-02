"""R0, fase 1: la corrida en seco de correr_r0.py (USD 0, sin red y sin la clave).

Corre sobre una copia del repo sin enlaces (este archivo, dentro de la copia). Cada escenario llama a correr_r0.py
--seco como proceso aparte, con el mismo intérprete y la misma línea de comandos que la corrida real (sin tocar el
sys.path: el script importa runner_corpus como en --correr), sobre copias propias de la base de E3 y de la de
reintentos de E1 de la copia, y controla el resultado esperado de cada rama:
  - base_sembrar: aceptar, reintentar y cola, con el reuso «sembrar» y el anexo a una copia de la salida de la tanda 0
    (y el segundo anexo, rechazado);
  - base_propia_sembrar, base_leer y sin_reuso: el mismo reparto con los otros caminos de la pregunta b (la base propia
    de R0 no existe antes de la corrida: la crea el sembrado con el esquema de llm_cache);
  - tope: frena por el tope compartido a mitad de la corrida y, relanzada con el tope de USD 1,50, termina sin volver a
    pagar lo pagado;
  - reanudacion: corte simulado del runner (--abortar-tras) y relanzamiento;
  - error_transitorio y error_persistente: errores de la API en un reintento de E1 (el runner reintenta dos veces;
    las esperas se registran en lugar de dormir);
  - mal_formada: respuesta sin tool_use en una verificación y en una re-verificación, y entidades que no son lista en
    un reintento de E1;
  - modelo_distinto y mensaje_distinto: las dos guardias de correr_r0 frenan.
Uso: PYTHONDONTWRITEBYTECODE=1 <python> -B r0_f1_corrida_en_seco.py --base <dir fuera de la copia> --salida <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import urllib.parse
from pathlib import Path

AQUI = Path(__file__).resolve().parent
R0 = AQUI.parent
REX = R0.parent
CORRER = R0 / "correr_r0.py"
DB_E3 = REX / "e3_verificador/cache/e3_verificacion.db"
DB_E1R = REX / "e3_verificador/cache/e1_reintentos.db"
SALIDA_T0 = REX / "corpus_tanda0/salida_r2b"
BASE = {"completo_ok_directo": 11, "aceptado_con_residuales": 5, "aceptado_tras_reintento": 2, "cola_humana": 1,
        "cola_humana_veredicto_inutilizable": 1}
MAL = {"completo_ok_directo": 10, "aceptado_con_residuales": 5, "cola_humana": 2,
       "cola_humana_reextraccion_invalida": 1, "cola_humana_veredicto_inutilizable": 2}
ESC = [
    {"nombre": "base_sembrar", "escenario": "base", "reuso": "sembrar", "tope": 1.5, "codigo": 0, "estados": BASE,
     "filas_e3": 23, "filas_e1r": 3, "transporte": 6, "anexar": True},
    {"nombre": "base_propia_sembrar", "escenario": "base", "reuso": "sembrar", "tope": 1.5, "codigo": 0,
     "estados": BASE, "filas_e3": 23, "filas_e1r": 3, "transporte": 6, "bases_nuevas": True},
    {"nombre": "base_leer", "escenario": "base", "reuso": "leer", "tope": 1.5, "codigo": 0, "estados": BASE,
     "filas_e3": 3, "filas_e1r": 3, "transporte": 6, "leidas_o3": 20},
    {"nombre": "sin_reuso", "escenario": "base", "reuso": "no", "tope": 1.5, "codigo": 0, "estados": BASE,
     "filas_e3": 23, "filas_e1r": 3, "transporte": 26},
    {"nombre": "tope", "escenario": "tope", "reuso": "sembrar", "tope": 0.12, "codigo": 3, "freno": "TopeExcedido",
     "luego": {"tope": 1.5, "codigo": 0, "estados": BASE, "filas_e3": 23, "filas_e1r": 3}},
    {"nombre": "reanudacion", "escenario": "base", "reuso": "sembrar", "tope": 1.5, "abortar_tras": 5, "codigo": 9,
     "luego": {"tope": 1.5, "codigo": 0, "estados": BASE, "filas_e3": 23, "filas_e1r": 3}},
    {"nombre": "error_transitorio", "escenario": "error_transitorio", "reuso": "sembrar", "tope": 1.5, "codigo": 0,
     "estados": BASE, "esperas": [20, 60], "filas_e3": 23, "filas_e1r": 3},
    {"nombre": "error_persistente", "escenario": "error_persistente", "reuso": "sembrar", "tope": 1.5, "codigo": 3,
     "freno": "falló tras reintentos de API", "esperas": [20, 60], "filas_e1r": 0},
    {"nombre": "mal_formada", "escenario": "mal_formada", "reuso": "no", "tope": 1.5, "codigo": 0, "estados": MAL},
    {"nombre": "modelo_distinto", "escenario": "modelo_distinto", "reuso": "sembrar", "tope": 1.5, "codigo": 3,
     "freno": "trae el modelo claude-haiku-4-5-20991231", "transporte": 1},
    {"nombre": "mensaje_distinto", "escenario": "mensaje_distinto", "reuso": "sembrar", "tope": 1.5, "codigo": 3,
     "freno": "e3: mensaje inesperado", "transporte": 0, "alterar": "ext::2.6.1.1", "filas_e3": 20, "filas_e1r": 0},
]


def sha_archivo(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def filas(db: Path) -> int:
    con = sqlite3.connect(f"file:{urllib.parse.quote(str(db))}?mode=ro", uri=True)
    try:
        return con.execute("select count(*) from cache").fetchone()[0]
    finally:
        con.close()


def correr(args: list[str], cwd: Path, log: Path) -> int:
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "PYTHONPATH")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-B", str(CORRER), *args], cwd=cwd, env=env, capture_output=True, text=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"$ correr_r0.py {' '.join(args)}\n{p.stdout}{p.stderr}[salida {p.returncode}]\n\n")
    return p.returncode


def controlar(r: dict, esp: dict, d: Path, f0: dict) -> dict:
    """Compara el resumen de una corrida con lo esperado del escenario."""
    ok = {}
    if "estados" in esp:
        c = r["corrida"]
        ok["estados"] = c["estados"] == esp["estados"] and c["unidades_con_registro_final"] == 20 \
            and not c["lineas_por_unidad_distintas_de_1"] and not c["ajenas_a_la_lista"]
    if "freno" in esp:
        ok["freno"] = bool(r.get("freno")) and esp["freno"] in r["freno"]
    else:
        ok["sin_freno"] = r.get("freno") is None
    if "esperas" in esp:
        ok["esperas"] = r["esperas_registradas_s"] == esp["esperas"]
    if "transporte" in esp:
        ok["transporte"] = r["transporte_simulado"]["llamadas_al_transporte"] == esp["transporte"]
    if "leidas_o3" in esp:
        ok["leidas_o3"] = r["leidas_de_o3"] == esp["leidas_o3"]
    if "filas_e3" in esp:
        ok["filas_e3"] = filas(d / "e3.db") - f0["e3"] == esp["filas_e3"]
    if "filas_e1r" in esp:
        ok["filas_e1r"] = filas(d / "e1r.db") - f0["e1r"] == esp["filas_e1r"]
    llam = [json.loads(x) for x in (d / "trabajo" / "registro_llamadas_r0.jsonl").read_text(encoding="utf-8")
            .splitlines()] if (d / "trabajo" / "registro_llamadas_r0.jsonl").exists() else []
    ok["gasto_dentro_del_tope"] = r["gasto_compartido_usd"] <= r["tope_usd"]
    return {"ok": all(ok.values()), "controles": ok, "freno": r.get("freno"),
            "estados": r["corrida"]["estados"], "gasto_compartido_usd": r["gasto_compartido_usd"],
            "transporte": r["transporte_simulado"], "llamadas_registradas": len(llam),
            "modelos": sorted({x["modelo_respuesta"] for x in llam}), "sembrado_o3": r.get("sembrado_o3")}


def anexo(d: Path, log: Path) -> dict:
    """--anexar sobre una copia de la salida de la tanda 0 (ext y docvig): solo cambian los archivos de los renglones
    nuevos, cada uno igual a su versión anterior más los renglones de la carpeta de trabajo; un segundo anexo frena."""
    st = d / "salida_t0"
    for to in ("ext", "docvig"):
        shutil.copytree(SALIDA_T0 / to, st / to)
    antes = {p.relative_to(st).as_posix(): p.read_bytes() for p in sorted(st.rglob("*")) if p.is_file()}
    c1 = correr(["--anexar", "--trabajo", str(d / "trabajo"), "--salida-t0", str(st)], d, log)
    despues = {p.relative_to(st).as_posix(): p.read_bytes() for p in sorted(st.rglob("*")) if p.is_file()}
    cambiados = sorted(k for k in despues if antes.get(k) != despues[k])
    esperado_ok = []
    for k in cambiados:
        to, nombre = k.split("/")
        nuevo = (d / "trabajo" / to / nombre).read_bytes()
        esperado_ok.append(despues[k] == antes.get(k, b"") + nuevo)
    # la última versión de cada unidad de las 20, en finales.jsonl anexado, es la de la carpeta de trabajo
    ult = {}
    for to in ("ext", "docvig"):
        for x in despues[f"{to}/finales.jsonl"].decode("utf-8").splitlines():
            if x.strip():
                ult[json.loads(x)["chunk_id"]] = x
    trab = {}
    for to in ("ext", "docvig"):
        for x in (d / "trabajo" / to / "finales.jsonl").read_text(encoding="utf-8").splitlines():
            trab[json.loads(x)["chunk_id"]] = x
    c2 = correr(["--anexar", "--trabajo", str(d / "trabajo"), "--salida-t0", str(st)], d, log)
    reg = json.loads((d / "trabajo" / "anexo_r0.json").read_text(encoding="utf-8"))
    return {"ok": c1 == 0 and all(esperado_ok) and bool(cambiados) and not (set(antes) - set(despues))
            and all(ult[k] == v for k, v in trab.items()) and c2 == 3,
            "codigo": c1, "archivos_cambiados": cambiados, "cada_uno_igual_a_antes_mas_lo_nuevo": all(esperado_ok),
            "ultima_version_de_las_20_es_la_nueva": all(ult[k] == v for k, v in trab.items()),
            "renglones": {f"{x['to']}/{x['archivo']}": x["renglones_agregados"] for x in reg["archivos"]},
            "segundo_anexo_codigo": c2}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    base = a.base.resolve()
    if base.exists():
        raise SystemExit("--base ya existe: cada corrida en seco empieza de cero")
    base.mkdir(parents=True)
    shas_bases = {"e3": sha_archivo(DB_E3), "e1r": sha_archivo(DB_E1R)}
    res = {"escenarios": {}}
    for e in ESC:
        d = base / e["nombre"]
        d.mkdir()
        if e.get("bases_nuevas"):
            f0 = {"e3": 0, "e1r": 0}            # base propia de R0: no existen, las crea la corrida
        else:
            shutil.copyfile(DB_E3, d / "e3.db")
            shutil.copyfile(DB_E1R, d / "e1r.db")
            f0 = {"e3": filas(d / "e3.db"), "e1r": filas(d / "e1r.db")}
        log = d / "salida.txt"
        comunes = ["--seco", "--escenario", e["escenario"], "--reuso-o3", e["reuso"], "--trabajo", str(d / "trabajo"),
                   "--db-e3", str(d / "e3.db"), "--db-e1r", str(d / "e1r.db")]
        extra = (["--abortar-tras", str(e["abortar_tras"])] if "abortar_tras" in e else []) + (
            ["--seco-alterar-esperado", e["alterar"]] if "alterar" in e else [])
        cod = correr(comunes + ["--tope", str(e["tope"])] + extra, d, log)
        r = json.loads((d / "trabajo" / "resumen_r0.json").read_text(encoding="utf-8"))
        esp = {k: v for k, v in e.items() if k != "luego"}
        out = {"codigo": cod, "codigo_ok": cod == e["codigo"], **controlar(r, esp, d, f0)}
        if "luego" in e:
            l = e["luego"]
            cod2 = correr(comunes + ["--tope", str(l["tope"])], d, log)
            r2 = json.loads((d / "trabajo" / "resumen_r0.json").read_text(encoding="utf-8"))
            out["relanzada"] = {"codigo": cod2, "codigo_ok": cod2 == l["codigo"], **controlar(r2, l, d, f0)}
            out["relanzada"]["transporte_de_la_relanzada"] = r2["transporte_simulado"]["llamadas_al_transporte"]
        if e.get("anexar"):
            out["anexo"] = anexo(d, log)
        out["paso"] = out["codigo_ok"] and out["ok"] and out.get("relanzada", {"codigo_ok": True, "ok": True})[
            "codigo_ok"] and out.get("relanzada", {"ok": True})["ok"] and out.get("anexo", {"ok": True})["ok"]
        res["escenarios"][e["nombre"]] = out
        print(f"{e['nombre']:<20s} {'PASA' if out['paso'] else 'FALLA'}  salida {cod}  estados {out['estados']}"
              + (f"  freno: {out['freno'][:90]}" if out.get("freno") else ""), flush=True)
    res["bases_de_la_copia_sin_cambios"] = shas_bases == {"e3": sha_archivo(DB_E3), "e1r": sha_archivo(DB_E1R)}
    res["pasan"] = sum(1 for x in res["escenarios"].values() if x["paso"])
    res["de"] = len(res["escenarios"])
    a.salida.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"pasan {res['pasan']} de {res['de']}; bases de la copia sin cambios: {res['bases_de_la_copia_sin_cambios']}")
    return 0 if res["pasan"] == res["de"] and res["bases_de_la_copia_sin_cambios"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
