"""
selftest_corpus.py — Prueba OFFLINE del runner de corpus (segundo acto de la
FASE B, previo a toda llamada paga): corrida en stub sobre 8 unidades de pro
con TRES muertes simuladas (dos en E1, una en E3) y relanzamientos que deben
re-servir lo persistido SIN duplicar ni saltear, más checkpoints y cierre E2
parcial. Cero llamadas a API (clientes stub del runner).

Uso:  .venv/bin/python3 selftest_corpus.py   → imprime N/N y evidencia
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "e1_extractor"))
import comun_e1  # noqa: E402

PY = sys.executable
SALIDA = AQUI / "salida_selftest"

OKS: list[str] = []
FAILS: list[str] = []


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    (OKS if cond else FAILS).append(nombre)
    print(f"  [{'ok' if cond else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""))


def correr(*extra: str) -> subprocess.CompletedProcess:
    cmd = [PY, str(AQUI / "runner_corpus.py"), "--stub", "--tos", "pro",
           "--limite", "8", "--checkpoint-cada", "2",
           "--salida", str(SALIDA), *extra]
    return subprocess.run(cmd, capture_output=True, text=True)


def jsonl_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [json.loads(l)["chunk_id"] for l in path.open(encoding="utf-8")
            if l.strip()]


def main() -> int:
    if SALIDA.exists():
        shutil.rmtree(SALIDA)

    chunks = comun_e1.cargar_chunks(("pro",), e0_dir=comun_e1.E0_SALIDA_ENM01)
    esperados = [c["id"] for c in chunks[:8]]
    tdir = SALIDA / "pro"
    e1_jsonl = tdir / "extracciones_e1.jsonl"
    fin_jsonl = tdir / "finales.jsonl"

    print("— Corrida A: muere en E1 tras 3 unidades —")
    a = correr("--abortar-tras", "3")
    check("A exit 9 (muerte simulada)", a.returncode == 9)
    ids_a = jsonl_ids(e1_jsonl)
    check("A persistió exactamente 3 unidades E1", ids_a == esperados[:3],
          f"{len(ids_a)} regs")

    print("— Corrida B: relanza, muere en E1 tras 3 más (6 acumuladas) —")
    b = correr("--abortar-tras", "3")
    check("B reanuda sin duplicar: ya_persistidas_ok=3 pendientes=5",
          "ya_persistidas_ok=3 pendientes=5" in b.stdout)
    check("B exit 9", b.returncode == 9)
    ids_b = jsonl_ids(e1_jsonl)
    check("B jsonl = 6 unidades, sin duplicados ni salteos",
          ids_b == esperados[:6], f"{len(ids_b)} regs")

    print("— Corrida C: cierra E1, muere en E3 tras 4 —")
    c = correr("--abortar-tras", "4")
    check("C reanuda E1: ya_persistidas_ok=6 pendientes=2",
          "ya_persistidas_ok=6 pendientes=2" in c.stdout)
    check("C cerró E1 (checkpoint de cierre)",
          (SALIDA / "checkpoints" / "checkpoint_pro_e1_cierre.json").exists())
    check("C exit 9 (muerte en E3)", c.returncode == 9)
    ids_c1 = jsonl_ids(e1_jsonl)
    check("C E1 completo = 8 unidades exactas (una sola llamada por unidad)",
          ids_c1 == esperados, f"{len(ids_c1)} regs")
    ids_c3 = jsonl_ids(fin_jsonl)
    check("C persistió 4 expedientes E3", ids_c3 == esperados[:4],
          f"{len(ids_c3)} regs")

    print("— Corrida D: relanza, completa E3 + E2 —")
    d = correr()
    check("D saltea E1 cerrada", "[pro:e1] ya cerrada" in d.stdout)
    check("D reanuda E3: ya_persistidas=4 pendientes=4",
          "ya_persistidas=4 pendientes=4" in d.stdout)
    check("D exit 0", d.returncode == 0, d.stderr[-300:] if d.returncode else "")
    ids_d = jsonl_ids(fin_jsonl)
    check("D finales = 8 unidades exactas, orden documental, sin dup/salteo",
          ids_d == esperados, f"{len(ids_d)} regs")
    estados = [json.loads(l)["estado"] for l in fin_jsonl.open(encoding="utf-8")]
    check("D 8/8 completo_ok_directo (stub)", estados == ["completo_ok_directo"] * 8)

    estado = json.loads((SALIDA / "estado_corpus.json").read_text(encoding="utf-8"))
    check("ledger: pro:e1 y pro:e3 cerradas con gasto 0.0",
          set(estado["fases_cerradas"]) == {"pro:e1", "pro:e3"} and
          all(f["gasto_usd"] == 0.0 for f in estado["fases_cerradas"].values()))

    ck = json.loads((SALIDA / "ultimo_checkpoint.json").read_text(encoding="utf-8"))
    check("checkpoint con proyección bajo el tope",
          ck["proyeccion_total_usd"] <= ck["tope_global_usd"],
          f"proy={ck['proyeccion_total_usd']}")
    check("checkpoints intra-fase escritos (cada 2)",
          (SALIDA / "checkpoints" / "checkpoint_pro_e1_u2.json").exists() and
          (SALIDA / "checkpoints" / "checkpoint_pro_e3_u6.json").exists())

    rep = json.loads((tdir / "reporte_e2_pro.json").read_text(encoding="utf-8"))
    check("E2 parcial (limite) ensambló 8 nodos de las 8 unidades",
          rep["parcial"] is True and rep["nodes_total"] == 8,
          f"nodes={rep['nodes_total']}")

    print("— Corrida E: re-lanzamiento sobre corrida completa = no-op —")
    e = correr()
    check("E no-op idempotente: ambas fases salteadas, exit 0",
          e.returncode == 0 and "[pro:e1] ya cerrada" in e.stdout
          and "[pro:e3] ya cerrada" in e.stdout)
    check("E no re-escribió nada: jsonl sigue en 8+8",
          jsonl_ids(e1_jsonl) == esperados and jsonl_ids(fin_jsonl) == esperados)

    print(f"\nSELFTEST CORPUS: {len(OKS)}/{len(OKS) + len(FAILS)} PASS")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
