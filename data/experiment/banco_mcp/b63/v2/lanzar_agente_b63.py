#!/usr/bin/env python3
"""lanzar_agente_b63.py (v2, etapa b1) — Lanza UNA sesión `claude -p` de B6.3 en uno de sus tres brazos, con la interfaz de
agentes/lanzar_agente.py, así que la corre el lanzador del lote (agentes/lanzar_lote_paralelo_r5.py, por la ventana del runner v2, con
--lanzador b63/v2/lanzar_agente_b63.py). Es b63/lanzar_agente_b63.py (etapa a) con la cadena del lanzador del runner v2 en el comando y
en la meta: el runner, lo común, el juez y la ventana de b63/v2/, el lanzador del lote r5 y su base, y las guardas r5 y su base.

La sesión es la de paralelo/lanzar_agente_n6_prueba.py, `lanzar`, importada sin editarla (y con ella las piezas del lanzador sellado:
construir_prompt, env_sesion para el brazo `vector` en los tres brazos, preparar_sesion, copiar_sesion, armar_meta), con la
configuración de agentes de la entrada sellada en lugar de la de prueba: su ruta y su sha256 llegan en B63_CONFIG_AGENTES y
B63_CONFIG_AGENTES_SHA256, que pone el runner (b63/correr_b63.py); si no están o el archivo no da su sha256, frena sin lanzar.
Esas dos variables no pasan a la sesión: su entorno es el de la lista cerrada de LA.env_sesion.

Lo que agrega, después de que la sesión terminó y sin tocar su línea de comandos ni su entorno (y lo que el lanzador del lote no
trae: el control del disco y la lectura acotada del valor remoto, los de A2.1, `a2_1/correr_a2_1.py`, importados sin editar, como en
A2.2):
  · en la meta, `control_disco` (un resultado de tool que llegó como referencia a un archivo: la marca en la transcripción o
    tool_results_<id>/ con archivos; §5, registro, §72) y `valor_remoto_por_tool` (de `tengu_velvet_ibis`, en el `.claude.json` de
    la carpeta de configuración de la sesión, por código y en memoria: solo si la clave existe y, si existe, los nombres de tool con
    sus números; registro, §97);
  · en el comando y en la meta, la ruta y el sha256 de cada archivo del lanzador que corrió (registro, §84): los de N6, este, el
    runner, lo común de B6.3, el lanzador del lote y sus guardas;
  · en la meta, BANCO_VENV_VECTOR: la ruta (la carpeta personal como $HOME) y la versión de su Python, la que declara la entrada
    (B63_VENV_PYTHON) y la que da su `bin/python --version`;
  · la unidad, B6.3.

Uso (lo arma el lanzador del lote):
  lanzar_agente_b63.py --brazo <brazo> --id X --pregunta "..." --out <dir> --modo init|real --sesiones <raíz>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b63/v2
BANCO_DIR = AQUI.parent.parent
for _p in (str(BANCO_DIR), str(BANCO_DIR / "agentes"), str(BANCO_DIR / "paralelo"), str(BANCO_DIR / "a2_1"), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_agente as LA                                  # noqa: E402  (sellado: solo import)
import lanzar_agente_n6_prueba as N6P                       # noqa: E402  (solo import)
import correr_a2_1 as CR                                    # noqa: E402  (A2.1: solo import, control_disco y valor_remoto_por_tool)
from comun_banco import sha256_file                         # noqa: E402

UNIDAD = "B6.3 (b63/v2/lanzar_agente_b63.py sobre paralelo/lanzar_agente_n6_prueba.py)"


def archivos_del_lanzador() -> list[dict]:
    """La cadena que lanza una sesión de B6.3, del runner a la sesión, con la ruta y el sha256 de cada archivo."""
    return LA.archivos_lanzador(AQUI / "correr_b63.py", AQUI / "comun_b63.py", AQUI / "juez_b63.py", AQUI / "ventana_b63.py",
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
        mp.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
