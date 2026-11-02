#!/usr/bin/env python3
"""adaptador_cc.py — Adaptador sesión de Claude Code -> traza del formato del repo.

U-A2.0-gate, entregable 4. Costo USD 0.

Precedente y mismo patrón: `scripts/adaptador_sesiones.py` (adaptador jsonl de
la app -> traza del verificador). Acá el origen es otro: el jsonl de sesión de
Claude Code (`<configuración del asistente>/projects/<proyecto>/<session_id>.jsonl`).

Contrato que debe satisfacer (entregable 1, `inventario_campos.md`): producir un
payload con la forma que consume `atribucion_fallas.atribuir_payload`:

    {"meta": {...},
     "trace": {"steps": [{n, tool, input, output_truncado, output_chars}],
               "final_json": ..., "tool_calls_used": int, "hit_tool_limit": bool},
     "steps_full": [{n, tool, input, output, output_chars}]}

Dos subcomandos:

  extraer   sesión completa -> rebanada CRUDA verbatim + manifiesto + copia de
            los outputs derramados a disco (`persistedOutputPath`). La rebanada
            es autosuficiente: `adaptar` no vuelve a tocar la sesión original.
  adaptar   rebanada -> una traza por caso declarado en `casos_gate.json`.

Principios duros (heredados del inventario §3):
  · Ningún step se descarta en silencio. Todo comando candidato que no parsee a
    UNA invocación limpia va a `rechazos` con su motivo y el conteo se reporta.
    Motivo: `alcanzabilidad` se afirma por NEGACIÓN — un step perdido convierte
    cualquier clase en `alcanzabilidad` sin que nada lo delate.
  · El output se recupera del transporte, nunca se re-ejecuta acá. Si no se
    puede recuperar íntegro, `output_truncado`/`output_chars` quedan en null y
    el caso se marca `output_no_recuperado`.
  · Un caso con corte de sesión (tool_use sin su tool_result) se marca
    `corte_sesion: true` y `atribuible: false`: la traza está incompleta y
    atribuirla daría una clase plausible y falsa.

Uso:
  adaptador_cc.py extraer --sesion <ruta.jsonl> [--out sesiones/]
  adaptador_cc.py adaptar [--rebanada sesiones/rebanada_cruda.jsonl] [--out corrida/trazas]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import sys
from datetime import datetime
from pathlib import Path

GATE_DIR = Path(__file__).resolve().parents[1]
CASOS_PATH = GATE_DIR / "casos_gate.json"
SESIONES_DIR = GATE_DIR / "sesiones"
TRAZAS_DIR = GATE_DIR / "corrida" / "trazas"
REBANADA = SESIONES_DIR / "rebanada_cruda.jsonl"
MANIFIESTO = SESIONES_DIR / "manifiesto_captura.json"
TOOL_RESULTS_DIR = SESIONES_DIR / "tool_results"

MARCA = "tools_juguete.py"
TOOLS_VALIDAS = ("buscar_nodos", "ver_nodo", "ver_vecinos")
# Espejo exacto del truncado del harness (harness.TRUNC_TOOL_OUTPUT).
TRUNC = 1200
SHELL_PROHIBIDO = re.compile(r"[|;><]|&&")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


SLUG_PROYECTO = str(Path.cwd()).replace("/", "-").replace(" ", "-")


def enmascarar(texto: str) -> str:
    """Colapsa el home y el slug de proyecto de Claude Code en los artefactos
    persistidos: ninguna ruta absoluta de la maquina queda escrita. El slug se
    deriva del cwd (`pwd | tr '/ ' '--'`), asi que no se pierde informacion."""
    if not texto:
        return texto
    return texto.replace(SLUG_PROYECTO, "<slug-del-proyecto>").replace(str(Path.home()), "~")


def ruta_portable(p: Path | str) -> str:
    """Ruta con el home colapsado a `~` y el slug enmascarado."""
    p = Path(p)
    try:
        base = str(Path("~") / p.relative_to(Path.home()))
    except ValueError:
        base = str(p)
    return enmascarar(base)


def _truncar(s: str) -> str:
    """Formato exacto de `harness._truncate`."""
    return s if len(s) <= TRUNC else s[:TRUNC] + f"… [+{len(s)-TRUNC} chars]"


def cargar_casos(path: Path | None = None) -> dict:
    d = json.loads((path or CASOS_PATH).read_text(encoding="utf-8"))
    return {c["caso_id"]: c for c in d["casos"]}


# --------------------------------------------------------------------------- #
# Parseo del comando (transporte Bash)                                         #
# --------------------------------------------------------------------------- #
def parsear_comando(cmd: str) -> dict:
    """`cmd` -> {'contrato','caso','tool','input'} o levanta ValueError.

    Estricto a propósito: una sola invocación por comando, sin pipes ni
    encadenamientos. El `cd` inicial se acepta porque es el patrón con que
    Claude Code fija el directorio de trabajo.
    """
    resto = cmd.strip()
    if resto.count(MARCA) != 1:
        raise ValueError(f"el comando no contiene exactamente una invocación de {MARCA} "
                         f"(cuenta: {resto.count(MARCA)})")
    # separar un prefijo `cd <dir> &&`
    prefijo = ""
    m = re.match(r"^\s*cd\s+(?:\"[^\"]*\"|'[^']*'|\S+)\s*&&\s*", resto)
    if m:
        prefijo, resto = m.group(0), resto[m.end():]
    if SHELL_PROHIBIDO.search(resto):
        raise ValueError("el comando encadena o redirige después de la invocación "
                         "(pipe / ';' / '>' / '&&'): no es una tool call limpia")
    argv = shlex.split(resto)
    i = next(k for k, t in enumerate(argv) if t.endswith(MARCA))
    argv = argv[i + 1:]

    contrato, caso, tool, opts = "v1", None, None, {}
    k = 0
    while k < len(argv):
        t = argv[k]
        if t == "--contrato":
            contrato = argv[k + 1]; k += 2
        elif t == "--caso":
            caso = argv[k + 1]; k += 2
        elif t == "--grafo":
            opts["_grafo"] = argv[k + 1]; k += 2
        elif t.startswith("--"):
            clave = t[2:].replace("-", "_")
            if k + 1 >= len(argv) or argv[k + 1].startswith("--"):
                raise ValueError(f"opción sin valor: {t}")
            opts[clave] = argv[k + 1]; k += 2
        elif tool is None:
            tool = t; k += 1
        else:
            raise ValueError(f"token posicional inesperado: {t!r}")
    if tool not in TOOLS_VALIDAS:
        raise ValueError(f"tool desconocida: {tool!r}")
    if caso is None:
        raise ValueError("invocación sin --caso: no se puede agrupar en una sesión")
    if contrato not in ("v1", "v2"):
        raise ValueError(f"contrato desconocido: {contrato!r}")

    # tipado del input al shape que consume el replay
    inp: dict = {}
    if tool == "buscar_nodos":
        inp["consulta"] = opts["consulta"]
        if "limite" in opts:
            inp["limite"] = int(opts["limite"])
    elif tool == "ver_nodo":
        inp["id"] = opts["id"]
    else:
        inp["id"] = opts["id"]
        if contrato == "v1":
            if "direccion" in opts:
                inp["direccion"] = opts["direccion"]
        else:
            if "relacion" in opts:
                inp["relacion"] = opts["relacion"]
            if "pagina" in opts:
                inp["pagina"] = int(opts["pagina"])
            if "por_pagina" in opts:
                inp["por_pagina"] = int(opts["por_pagina"])
    return {"contrato": contrato, "caso": caso, "tool": tool, "input": inp,
            "prefijo_cd": bool(prefijo)}


# --------------------------------------------------------------------------- #
# Lectura de la sesión                                                         #
# --------------------------------------------------------------------------- #
def _bloques_tool_use(d: dict) -> list[dict]:
    if d.get("type") != "assistant":
        return []
    return [c for c in (d.get("message") or {}).get("content", []) or []
            if isinstance(c, dict) and c.get("type") == "tool_use"]


def _bloques_tool_result(d: dict) -> list[dict]:
    if d.get("type") != "user":
        return []
    return [c for c in (d.get("message") or {}).get("content", []) or []
            if isinstance(c, dict) and c.get("type") == "tool_result"]


def leer_sesion(path: Path) -> list[dict]:
    """[{'nro','cruda','json'}] en orden de archivo."""
    out = []
    for nro, cruda in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not cruda.strip():
            continue
        try:
            out.append({"nro": nro, "cruda": cruda, "json": json.loads(cruda)})
        except json.JSONDecodeError:
            out.append({"nro": nro, "cruda": cruda, "json": None})
    return out


def candidatos(lineas: list[dict]) -> tuple[list[dict], list[dict]]:
    """(aceptados, rechazados). Un candidato es un tool_use cuyo comando
    menciona la marca de las tools de juguete."""
    aceptados, rechazados = [], []
    for L in lineas:
        d = L["json"]
        if d is None:
            continue
        for c in _bloques_tool_use(d):
            inp = c.get("input") or {}
            cmd = inp.get("command") if c.get("name") == "Bash" else None
            es_mcp = str(c.get("name", "")).startswith("mcp__") and \
                MARCA.split(".")[0] in str(c.get("name", ""))
            if cmd is None and not es_mcp:
                continue
            if cmd is not None and MARCA not in cmd:
                continue
            reg = {"tool_use_id": c["id"], "linea_tool_use": L["nro"],
                   "uuid": d.get("uuid"), "timestamp": d.get("timestamp"),
                   "transporte": "bash" if cmd is not None else "mcp",
                   "comando": cmd}
            try:
                if cmd is not None:
                    reg.update(parsear_comando(cmd))
                else:   # transporte MCP: el input ya viene estructurado
                    reg.update({"contrato": inp.get("contrato", "v1"),
                                "caso": inp.get("caso"),
                                "tool": str(c["name"]).rsplit("__", 1)[-1],
                                "input": {k: v for k, v in inp.items()
                                          if k not in ("caso", "contrato")}})
                    if reg["caso"] is None:
                        raise ValueError("invocación MCP sin `caso`")
                aceptados.append(reg)
            except (ValueError, KeyError, IndexError, StopIteration) as e:
                reg["motivo_rechazo"] = f"{type(e).__name__}: {e}"
                rechazados.append(reg)
    return aceptados, rechazados


def indice_resultados(lineas: list[dict]) -> dict:
    """tool_use_id -> {'linea','toolUseResult','bloque'}"""
    idx = {}
    for L in lineas:
        d = L["json"]
        if d is None:
            continue
        for c in _bloques_tool_result(d):
            idx[c.get("tool_use_id")] = {"linea": L["nro"], "toolUseResult": d.get("toolUseResult"),
                                         "bloque": c}
    return idx


# --------------------------------------------------------------------------- #
# Recuperación del output                                                      #
# --------------------------------------------------------------------------- #
def recuperar_output(res: dict, dir_derrames: Path | None) -> dict:
    """Devuelve {'obj','texto','fuente','ok','motivo'} desde un tool_result.

    Orden de preferencia: archivo de derrame (`persistedOutputPath`, el output
    ÍNTEGRO que Claude Code escribe a disco cuando pasa el cap) > `stdout` >
    payload MCP. El derrame es la única vía por la que un output mayor al cap
    del transporte sobrevive.
    """
    tur = res["toolUseResult"]
    texto, fuente = None, None
    if isinstance(tur, dict):
        p = tur.get("persistedOutputPath")
        if p:
            cand = []
            if dir_derrames is not None:
                cand.append(dir_derrames / Path(p).name)
            cand.append(Path(p))
            for c in cand:
                if c.exists():
                    texto, fuente = c.read_text(encoding="utf-8"), f"derrame:{c.name}"
                    break
            if texto is None:
                return {"obj": None, "texto": None, "fuente": "derrame_ausente", "ok": False,
                        "motivo": f"persistedOutputPath no disponible: {ruta_portable(p)}"}
        else:
            if tur.get("stderr"):
                return {"obj": None, "texto": None, "fuente": "stderr", "ok": False,
                        "motivo": f"la tool escribió en stderr: {tur['stderr'][:200]!r}"}
            texto, fuente = tur.get("stdout") or "", "stdout"
    elif isinstance(tur, list):
        partes = [b.get("text", "") for b in tur if isinstance(b, dict) and b.get("type") == "text"]
        texto, fuente = "".join(partes), "mcp_text"
    else:
        return {"obj": None, "texto": None, "fuente": type(tur).__name__, "ok": False,
                "motivo": "toolUseResult de forma no soportada"}

    crudo = texto.rstrip("\n")
    try:
        obj = json.loads(crudo)
    except json.JSONDecodeError as e:
        return {"obj": None, "texto": crudo, "fuente": fuente, "ok": False,
                "motivo": f"output no parseable (truncado por el transporte): {e}"}
    return {"obj": obj, "texto": crudo, "fuente": fuente, "ok": True, "motivo": None}


# --------------------------------------------------------------------------- #
# extraer                                                                      #
# --------------------------------------------------------------------------- #
def extraer(sesion: Path, out_dir: Path, hasta_linea: int | None = None,
            casos_path: Path | None = None) -> dict:
    casos = cargar_casos(casos_path)
    lineas = leer_sesion(sesion)
    if hasta_linea is not None:
        # Ventana de captura: el jsonl de sesion sigue creciendo mientras la
        # sesion corre, asi que la rebanada se acota al segmento en que corrieron
        # las tools de juguete. Sin esto `extraer` no es re-ejecutable.
        lineas = [L for L in lineas if L["nro"] <= hasta_linea]
    acept, rech = candidatos(lineas)
    idx = indice_resultados(lineas)

    # cortes declarados: {caso: n_step} (1-based sobre los steps del caso)
    cortes = {c: v["corte_en_step"] for c, v in casos.items() if v.get("corte_en_step")}
    orden: dict[str, int] = {}
    lineas_tool_use, lineas_result, omitidas_por_corte = set(), set(), []
    for a in acept:
        orden[a["caso"]] = orden.get(a["caso"], 0) + 1
        a["n"] = orden[a["caso"]]
        lineas_tool_use.add(a["linea_tool_use"])
        r = idx.get(a["tool_use_id"])
        if r is None:
            continue
        if cortes.get(a["caso"]) == a["n"]:
            omitidas_por_corte.append({"caso": a["caso"], "n": a["n"], "linea": r["linea"]})
            continue
        lineas_result.add(r["linea"])
    for r in rech:
        lineas_tool_use.add(r["linea_tool_use"])
        rr = idx.get(r["tool_use_id"])
        if rr:
            lineas_result.add(rr["linea"])

    conservar = lineas_tool_use | lineas_result
    out_dir.mkdir(parents=True, exist_ok=True)
    # los derrames se copian JUNTO a la rebanada que los referencia, para que
    # cada captura sea autosuficiente y las fases no se pisen entre si
    derrames_dir = out_dir / "tool_results"
    derrames_dir.mkdir(parents=True, exist_ok=True)
    seleccion = [L for L in lineas if L["nro"] in conservar]
    (out_dir / "rebanada_cruda.jsonl").write_text(
        "".join(L["cruda"] + "\n" for L in seleccion), encoding="utf-8")

    # copiar los outputs derramados a disco (para que la rebanada sea autosuficiente)
    derrames = []
    for L in seleccion:
        tur = (L["json"] or {}).get("toolUseResult")
        if isinstance(tur, dict) and tur.get("persistedOutputPath"):
            src = Path(tur["persistedOutputPath"])
            if src.exists():
                dst = derrames_dir / src.name
                shutil.copyfile(src, dst)
                derrames.append({"origen": ruta_portable(src), "copia": str(dst.resolve().relative_to(GATE_DIR)),
                                 "bytes": dst.stat().st_size,
                                 "sha256": sha256_bytes(dst.read_bytes()),
                                 "persistedOutputSize": tur.get("persistedOutputSize")})

    man = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "unidad": "U-A2.0-gate",
        "sesion_origen": ruta_portable(sesion),
        "sesion_origen_sha256_al_capturar": sha256_bytes(sesion.read_bytes()),
        "nota_sesion_origen": ("El jsonl de sesion vive fuera del repo y sigue creciendo mientras "
                               "la sesion corre: su sha256 es el del momento de la captura y NO es "
                               "reproducible despues. Lo reproducible es la rebanada, acotada por "
                               "`ventana_de_captura_hasta_linea`. El slug del proyecto se deriva "
                               "del cwd con `pwd | tr '/ ' '--'`."),
        "nota_confidencialidad": ("En los campos generados por el adaptador las rutas absolutas "
                                  "van enmascaradas. `rebanada_cruda.jsonl` NO se enmascara: es "
                                  "la evidencia cruda y cualquier edicion la invalidaria (su "
                                  "sha256 dejaria de corresponder a lineas verbatim de la "
                                  "sesion). Contiene rutas de la maquina, ningun dato de "
                                  "terceros."),
        "ventana_de_captura_hasta_linea": hasta_linea,
        "n_lineas_sesion": len(lineas),
        "n_lineas_rebanada": len(seleccion),
        "lineas_conservadas": sorted(conservar),
        "n_candidatos_aceptados": len(acept),
        "n_candidatos_rechazados": len(rech),
        "rechazos": [{k: v for k, v in r.items() if k != "comando"} |
                     {"comando": enmascarar((r.get("comando") or "")[:300])} for r in rech],
        "corte_materializado": omitidas_por_corte,
        "nota_corte": ("El corte de sesion se materializa NO conservando la linea de tool_result "
                       "del step declarado: es exactamente el estado en disco de una sesion "
                       "interrumpida entre el tool_use y su resultado. Las lineas conservadas son "
                       "verbatim, byte a byte."),
        "derrames_copiados": derrames,
        "rebanada_sha256": sha256_bytes((out_dir / "rebanada_cruda.jsonl").read_bytes()),
    }
    (out_dir / "manifiesto_captura.json").write_text(
        json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"rebanada: {len(seleccion)} lineas de {len(lineas)} | aceptados {len(acept)} | "
          f"rechazados {len(rech)} | derrames {len(derrames)} | cortes {len(omitidas_por_corte)}")
    for r in rech:
        print(f"  RECHAZO linea {r['linea_tool_use']}: {r['motivo_rechazo']}")
    return man


# --------------------------------------------------------------------------- #
# adaptar                                                                      #
# --------------------------------------------------------------------------- #
def adaptar(rebanada: Path, out_dir: Path, casos_path: Path | None = None) -> dict:
    casos = cargar_casos(casos_path)
    lineas = leer_sesion(rebanada)
    acept, rech = candidatos(lineas)
    idx = indice_resultados(lineas)

    por_caso: dict[str, list] = {}
    for a in acept:
        por_caso.setdefault(a["caso"], []).append(a)

    grafo_sha = sha256_bytes((GATE_DIR / "grafo_juguete.json").read_bytes())
    out_dir.mkdir(parents=True, exist_ok=True)
    resumen = []
    for caso_id, decl in casos.items():
        steps, full, incidencias = [], [], []
        # `n` es una convencion de esta unidad (Claude Code no numera tool calls
        # por dominio): se persiste el mapa n -> tool_use_id / linea de la
        # rebanada para que la renumeracion sea auditable, no una afirmacion.
        mapa_steps = []
        corte = False
        n = 0
        for a in sorted(por_caso.get(caso_id, []), key=lambda x: x["linea_tool_use"]):
            r = idx.get(a["tool_use_id"])
            if r is None:
                corte = True
                incidencias.append({"tool_use_id": a["tool_use_id"], "tool": a["tool"],
                                    "input": a["input"], "motivo": "tool_use sin tool_result "
                                    "(corte de sesion)"})
                continue
            rec = recuperar_output(r, rebanada.parent / "tool_results")
            n += 1
            mapa_steps.append({"n": n, "tool_use_id": a["tool_use_id"],
                               "linea_tool_use": a["linea_tool_use"],
                               "linea_tool_result": r["linea"],
                               "uuid_asistente": a.get("uuid"),
                               "timestamp": a.get("timestamp"),
                               "transporte": a["transporte"]})
            if rec["ok"]:
                # serialización canónica del harness: es contra ESTA cadena que
                # el replay estándar compara. Se verifica que coincida byte a
                # byte con lo que devolvió la sesión (`igual_a_la_sesion`).
                s = json.dumps(rec["obj"], ensure_ascii=False)
                steps.append({"n": n, "tool": a["tool"], "input": a["input"],
                              "output_truncado": _truncar(s), "output_chars": len(s)})
                full.append({"n": n, "tool": a["tool"], "input": a["input"],
                             "output": rec["obj"], "output_chars": len(s)})
                incidencias.append({"n": n, "fuente_output": rec["fuente"],
                                    "igual_a_la_sesion": s == rec["texto"],
                                    "chars": len(s)})
            else:
                steps.append({"n": n, "tool": a["tool"], "input": a["input"],
                              "output_truncado": None, "output_chars": None})
                incidencias.append({"n": n, "fuente_output": rec["fuente"],
                                    "output_no_recuperado": True, "motivo": rec["motivo"]})

        payload = {
            "meta": {
                "unidad": "U-A2.0-gate", "caso_id": caso_id, "origen": "claude_code_session",
                "contrato_tools": decl.get("contrato", "v1"),
                "grafo": "data/experiment/banco_mcp/gate/grafo_juguete.json",
                "grafo_sha256": grafo_sha,
                "adaptador": "data/experiment/banco_mcp/gate/code/adaptador_cc.py",
                "rebanada": str(rebanada.relative_to(GATE_DIR)) if rebanada.is_relative_to(GATE_DIR) else str(rebanada),
                "anclas_gold": decl["anclas"], "veredicto_declarado": decl["veredicto"],
                "clase_esperada": decl["clase_esperada"],
                "generado": datetime.now().isoformat(timespec="seconds"),
            },
            "trace": {
                "question": None,
                "steps": steps,
                # No hay JSON final: Claude Code no impone el contrato de salida
                # del harness. Declarado como hueco en inventario_campos.md §7.
                "final_json": None,
                "tool_calls_used": len(steps),
                "hit_tool_limit": False,
            },
            "steps_full": full,
            "gate": {
                "corte_sesion": corte,
                "atribuible": (not corte) and all(s["output_chars"] is not None for s in steps),
                "n_steps_adaptados": len(steps),
                "mapa_steps": mapa_steps,
                "incidencias": incidencias,
            },
        }
        (out_dir / f"{caso_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        resumen.append({"caso_id": caso_id, "n_steps": len(steps), "corte_sesion": corte,
                        "atribuible": payload["gate"]["atribuible"],
                        "contrato": decl.get("contrato", "v1")})
        print(f"{caso_id}: {len(steps)} steps | corte={corte} | "
              f"atribuible={payload['gate']['atribuible']}")

    huerfanos = sorted(set(por_caso) - set(casos))
    if huerfanos:
        raise SystemExit(f"steps de casos NO declarados en casos_gate.json: {huerfanos}. FRENAR.")
    res = {"generado": datetime.now().isoformat(timespec="seconds"),
           "n_casos": len(resumen), "n_rechazos_en_rebanada": len(rech),
           "rechazos": [r.get("motivo_rechazo") for r in rech], "casos": resumen}
    (out_dir.parent / "resumen_adaptacion.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extraer"); p.add_argument("--sesion", type=Path, required=True)
    p.add_argument("--out", type=Path, default=SESIONES_DIR)
    p.add_argument("--hasta-linea", dest="hasta_linea", type=int, default=None,
                   help="ventana de captura: ignora las lineas posteriores de la sesion")
    p.add_argument("--casos", type=Path, default=None)
    p = sub.add_parser("adaptar"); p.add_argument("--rebanada", type=Path, default=REBANADA)
    p.add_argument("--out", type=Path, default=TRAZAS_DIR)
    p.add_argument("--casos", type=Path, default=None)
    a = ap.parse_args()
    if a.cmd == "extraer":
        extraer(a.sesion, a.out, a.hasta_linea, a.casos); return 0
    adaptar(a.rebanada, a.out, a.casos); return 0


if __name__ == "__main__":
    raise SystemExit(main())
