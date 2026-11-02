#!/usr/bin/env python3
"""lanzar_agente_b63.py (b64/v1, B6.4) — El lanzador de una sesión de B6.4: el de B6.3 de HEAD (b63/v2/b2/lanzar_agente_b63.py), con
su mismo nombre (comun_b63.LANZADOR_SESION lo nombra), y con lo que cambia de su cadena:
  · la carpeta: b64/v1 está un nivel más arriba que b63/v2/b2, así que la del banco sale de AQUI.parents[1];
  · `archivos_del_lanzador`, la cadena que va a la meta de cada sesión: el runner, lo común y el juez de esta carpeta, y la ventana, la
    memoria, Docker y el Neo4j de b63/v2/b2, de donde los importa el runner de B6.4;
  · `UNIDAD`, la de B6.4.
La sesión, la configuración de la entrada sellada (B63_CONFIG_AGENTES y B63_CONFIG_AGENTES_SHA256, que pone el runner), la meta
completa y la meta sin texto, tal cual.

Lo de B6.3, tal cual: lanzar_agente_b63.py (v2/b2, etapa b2; el de la b1 bis, con la cadena de esta carpeta) — Lanza UNA sesión `claude -p` de B6.3 en uno de sus tres brazos, con la interfaz de
agentes/lanzar_agente.py, así que la corre el lanzador del lote (agentes/lanzar_lote_paralelo_r5.py, por la ventana del runner de esta
carpeta, con --lanzador b63/v2/b2/lanzar_agente_b63.py). Es b63/v2/lanzar_agente_b63.py (etapa b1) con lo de la etapa b1 bis
(decisiones de la autora del 27/10/2026, 21:52:30):
  · el stream va en la meta, con su ruta (la de rel_repo, como el log R1) y su sha256 (decisión 2): `stream`;
  · la meta completa trae texto (la respuesta y el input de cada llamada), así que no se commitea: queda fuera del repo, junto al
    stream (en modo real, la carpeta de la sesión tiene que estar fuera del repo y de git; si no, frena sin lanzar). Al lado va la meta
    sin texto, `meta_sin_texto_<id>.json`, que es la que se commitea (decisión 3), con una lista cerrada de campos:
      - tal cual, los de la meta del lanzador sellado (agentes/lanzar_agente.py, `armar_meta`, y `duracion_s`): CAMPOS_TAL_CUAL;
      - tal cual, los que suman el lanzador de N6 y el de B6.3 y no traen texto: CAMPOS_DEL_LANZADOR (`hb2`, del de N6, sus conteos;
        `unidad_del_lanzador_importado`; `banco_venv_vector`, la ruta del venv y la versión de su Python; `control_disco`, sus marcas,
        los nombres de los archivos de tool_results/ y los largos; `valor_remoto_por_tool`, los nombres de tool con sus números);
      - cambian: `mapa_R7`, cada llamada sin su `input` y con el sha256 de su JSON canónico; `final_json_R4`, si está, el sha256 de
        su JSON canónico y la cuenta de sus citas; `permission_denials`, por su cuenta;
      - se suman el stream y la meta completa, cada uno con su ruta y su sha256.
    El JSON canónico: json.dumps con sort_keys, ensure_ascii=False y separadores sin espacios, en UTF-8.
Lo demás, como en la etapa b1: la sesión es la de paralelo/lanzar_agente_n6_prueba.py, `lanzar`, importada sin editarla, con la
configuración de agentes de la entrada sellada (B63_CONFIG_AGENTES y B63_CONFIG_AGENTES_SHA256, que pone el runner, y que no pasan a
la sesión); y, después de que la sesión terminó, `control_disco` y `valor_remoto_por_tool` (los de A2.1, importados sin editar), la
cadena del lanzador con el sha256 de cada archivo, BANCO_VENV_VECTOR y la unidad.

Uso (lo arma el lanzador del lote):
  lanzar_agente_b63.py --brazo <brazo> --id X --pregunta "..." --out <dir> --modo init|real --sesiones <raíz>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b64/v1
BANCO_DIR = AQUI.parents[1]                                 # b64/v1: un nivel más arriba que b63/v2/b2
B63_B2 = BANCO_DIR / "b63" / "v2" / "b2"                    # lo del runner de B6.4 que no cambia
for _p in (str(BANCO_DIR), str(BANCO_DIR / "agentes"), str(BANCO_DIR / "paralelo"), str(BANCO_DIR / "a2_1"), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_agente as LA                                  # noqa: E402  (sellado: solo import)
import lanzar_agente_n6_prueba as N6P                       # noqa: E402  (solo import)
import correr_a2_1 as CR                                    # noqa: E402  (A2.1: solo import, control_disco y valor_remoto_por_tool)
from comun_banco import rel_repo, sha256_file               # noqa: E402

UNIDAD = "B6.4 (b64/v1/lanzar_agente_b63.py sobre paralelo/lanzar_agente_n6_prueba.py)"
CAMPOS_TAL_CUAL = ("pregunta_id", "brazo", "modo", "contrato", "unidad", "generado", "sesion", "modelos_R8", "credenciales",
                   "servidores_mcp", "sha_fuentes", "harness_R10", "inventario_tools_R6", "corte_R5", "completitud_R3", "tokens_R9",
                   "log_r1", "duracion_s")
CAMPOS_DEL_LANZADOR = ("hb2", "unidad_del_lanzador_importado", "banco_venv_vector", "control_disco", "valor_remoto_por_tool")
CAMPOS_QUE_CAMBIAN = ("mapa_R7", "final_json_R4", "permission_denials")
CAMPOS_QUE_SE_SUMAN = ("stream", "meta_completa")
CLAVES_SIN_TEXTO = CAMPOS_TAL_CUAL + CAMPOS_DEL_LANZADOR + CAMPOS_QUE_CAMBIAN + CAMPOS_QUE_SE_SUMAN


def archivos_del_lanzador() -> list[dict]:
    """La cadena que lanza una sesión de B6.4, del runner a la sesión, con la ruta y el sha256 de cada archivo."""
    return LA.archivos_lanzador(AQUI / "correr_b63.py", AQUI / "comun_b63.py", AQUI / "juez_b63.py", B63_B2 / "ventana_b63.py",
                                B63_B2 / "memoria_b63.py", B63_B2 / "docker_b63.py", B63_B2 / "control_neo4j_b63.py",
                                BANCO_DIR / "agentes" / "lanzar_lote_paralelo_r5.py", BANCO_DIR / "agentes" / "lanzar_lote_paralelo.py",
                                BANCO_DIR / "paralelo" / "guardas_lote_r5.py", BANCO_DIR / "paralelo" / "guardas_lote.py",
                                Path(__file__), N6P.__file__, LA.__file__)


def config_de_la_entrada() -> Path:
    r, s = os.environ.get("B63_CONFIG_AGENTES"), os.environ.get("B63_CONFIG_AGENTES_SHA256")
    if not r or not s:
        raise SystemExit("ABORTO: faltan B63_CONFIG_AGENTES y B63_CONFIG_AGENTES_SHA256 (los pone el runner de B6.3)")
    p = Path(r)
    if not p.is_file() or sha256_file(p) != s:
        raise SystemExit("ABORTO: la configuración de agentes de B6.3 no existe o no da su sha256")
    return p


def venv_vector() -> dict:
    v = os.environ.get("BANCO_VENV_VECTOR", "")
    py = Path(v) / "bin" / "python"
    import subprocess
    r = subprocess.run([str(py), "--version"], capture_output=True, text=True) if py.is_file() else None
    return {"ruta": v.replace(str(Path.home()), "$HOME"), "python_declarado": os.environ.get("B63_VENV_PYTHON"),
            "python_observado": ((r.stdout or r.stderr).strip().split()[-1] if r is not None and r.returncode == 0 else None)}


def canonico(o) -> bytes:
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_canonico(o) -> str:
    return hashlib.sha256(canonico(o)).hexdigest()


def archivo(p: Path) -> dict:
    """La ruta (rel_repo: relativa al repo, o con la carpeta personal como «~/») y el sha256 de un archivo, como el log R1."""
    return {"existe": True, "ruta": rel_repo(p), "sha256": sha256_file(p)} if p.is_file() else {"existe": False, "ruta": rel_repo(p)}


def meta_sin_texto(m: dict, ruta_completa: Path) -> dict:
    """La meta sin texto: la lista cerrada de campos (CLAVES_SIN_TEXTO), sin el texto de ninguna pregunta, criterio ni respuesta, ni el
    input de ninguna llamada."""
    out = {k: m.get(k) for k in CAMPOS_TAL_CUAL + CAMPOS_DEL_LANZADOR}
    out["mapa_R7"] = [{"n": x.get("n"), "tool_use_id": x.get("tool_use_id"), "tool": x.get("tool"), "call_id_log": x.get("call_id_log"),
                       "coincide_tool_input": x.get("coincide_tool_input"), "input_sha256": sha256_canonico(x.get("input"))}
                      for x in m.get("mapa_R7") or []]
    fj = m.get("final_json_R4")
    out["final_json_R4"] = None if fj is None else {
        "sha256": sha256_canonico(fj), "n_citas": len(fj["citas"]) if isinstance(fj, dict) and isinstance(fj.get("citas"), list) else None}
    pd = m.get("permission_denials")
    out["permission_denials"] = len(pd) if isinstance(pd, list) else None
    out["stream"] = m.get("stream")
    out["meta_completa"] = archivo(ruta_completa)
    assert tuple(out) == CLAVES_SIN_TEXTO
    return out


def completar(out: Path, pid: str, sesiones: Path) -> None:
    lanzador = archivos_del_lanzador()
    cp, mp = out / f"comando_{pid}.json", out / f"meta_{pid}.json"
    sid = json.loads(cp.read_text(encoding="utf-8")).get("session_id") if cp.is_file() else None
    if cp.is_file():
        c = json.loads(cp.read_text(encoding="utf-8"))
        c["lanzador"] = lanzador
        cp.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if mp.is_file():
        m = json.loads(mp.read_text(encoding="utf-8"))
        m["unidad_del_lanzador_importado"] = m.get("unidad")
        m["unidad"] = UNIDAD
        m["harness_R10"]["lanzador"] = lanzador
        m["banco_venv_vector"] = venv_vector()
        m["control_disco"] = CR.control_disco(out, pid)
        m["valor_remoto_por_tool"] = (CR.valor_remoto_por_tool(Path(sesiones).resolve() / "config" / sid) if sid
                                      else {"clave": CR.CLAVE_REMOTA, "archivo": "sin session_id"})
        m["stream"] = archivo(out / f"stream_{pid}.jsonl")
        mp.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sin = meta_sin_texto(m, mp)
        (out / f"meta_sin_texto_{pid}.json").write_text(json.dumps(sin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brazo", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--pregunta", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--modo", choices=["real", "init"], default="init")
    ap.add_argument("--via", choices=["api", "bedrock"], default="api")
    ap.add_argument("--sesiones", type=Path, required=True)
    ap.add_argument("--timeout-s", type=float, default=1800.0)
    a = ap.parse_args()
    if a.modo == "real" and (a.out.resolve().is_relative_to(LA.REPO_DIR) or LA.dentro_de_git(a.out.resolve()) is not None):
        raise SystemExit("ABORTO: en modo real la carpeta de la sesión va fuera del repo y de git (la meta completa y el stream traen "
                         "texto; decisión 3)")
    cfg = config_de_la_entrada()
    try:
        meta = N6P.lanzar(a.brazo, a.id, a.pregunta, a.out, a.modo, a.via, None, a.timeout_s, a.sesiones, cfg)
    finally:
        completar(a.out, a.id, a.sesiones)
    print(json.dumps({"brazo": a.brazo, "modo": a.modo, "completa": meta["completitud_R3"]["completa"],
                      "duracion_s": meta["duracion_s"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
