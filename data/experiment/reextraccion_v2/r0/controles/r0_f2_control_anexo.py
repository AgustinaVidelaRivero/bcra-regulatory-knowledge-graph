"""R0, fase 2: el control del anexo (USD 0, sin red; solo lee).

Contra el sha256 de cada archivo de salida_r2b/ y de la E0 de la tanda 0 tomado antes de la corrida (--antes) y contra
la versión de HEAD de cada archivo (git show, solo lectura):
  - cambian solo los archivos que registra r0/corrida/anexo_r0.json, y cada uno es su versión de HEAD más los
    renglones de r0/corrida/, byte a byte, todos de las 20 unidades de la lista;
  - ningún otro archivo de salida_r2b/ cambia, ninguno se agrega ni se borra;
  - la E0 de la tanda 0 no cambia (57 de 57);
  - en finales.jsonl, la última versión de cada una de las 20 es la de r0/corrida/, y la de las demás unidades no cambia.
Uso (desde la raíz del repo): PYTHONDONTWRITEBYTECODE=1 <python> -B r0_f2_control_anexo.py --antes <json> --salida <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

AQUI = Path(__file__).resolve().parent
R0 = AQUI.parent
REX = R0.parent
REPO = REX.parents[2]
SALIDA = REX / "corpus_tanda0/salida_r2b"
E0 = REX / "e0_chunking/salida_tanda0_r2b"
TRABAJO = R0 / "corrida"
LISTA = REPO / "data/experiment/e3_listas/o3/lista_unidades_afectadas_tanda0.json"


def shas(base: Path) -> dict[str, str]:
    return {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob("*")) if p.is_file()}


def en_head(p: Path) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{p.relative_to(REPO).as_posix()}"],
                          capture_output=True, check=True).stdout


def ultimas(b: bytes) -> dict[str, str]:
    out = {}
    for x in b.decode("utf-8").splitlines():
        if x.strip():
            out[json.loads(x)["chunk_id"]] = x
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    antes = json.loads(a.antes.read_text(encoding="utf-8"))
    veinte = {u["chunk_id"] for u in json.loads(LISTA.read_text(encoding="utf-8"))["unidades"]}
    anexo = json.loads((TRABAJO / "anexo_r0.json").read_text(encoding="utf-8"))
    registrados = {f"{x['to']}/{x['archivo']}" for x in anexo["archivos"]}
    ahora_s, ahora_e0 = shas(SALIDA), shas(E0)
    cambiados = sorted(k for k in ahora_s if antes["salida_r2b"].get(k) != ahora_s[k])
    res = {"cambiados": cambiados, "agregados": sorted(set(ahora_s) - set(antes["salida_r2b"])),
           "borrados": sorted(set(antes["salida_r2b"]) - set(ahora_s)),
           "cambiados_son_los_del_anexo": set(cambiados) == registrados,
           "archivos_sin_cambios": sum(1 for k in ahora_s if antes["salida_r2b"].get(k) == ahora_s[k]),
           "archivos_de_salida_r2b": len(ahora_s),
           "e0_iguales": sum(1 for k in ahora_e0 if antes["e0_salida_tanda0_r2b"].get(k) == ahora_e0[k]),
           "e0_archivos": len(ahora_e0), "por_archivo": {}}
    ok_arch = True
    for k in cambiados:
        p = SALIDA / k
        head, ahora, nuevo = en_head(p), p.read_bytes(), (TRABAJO / k).read_bytes()
        ids = [json.loads(x)["chunk_id"] for x in nuevo.decode("utf-8").splitlines() if x.strip()]
        d = {"sha256_head": hashlib.sha256(head).hexdigest(), "sha256_antes_igual_a_head":
             antes["salida_r2b"][k] == hashlib.sha256(head).hexdigest(),
             "igual_a_head_mas_lo_nuevo": ahora == head + nuevo, "renglones_nuevos": len(ids),
             "renglones_nuevos_de_las_20": sum(1 for i in ids if i in veinte)}
        d["ok"] = d["sha256_antes_igual_a_head"] and d["igual_a_head_mas_lo_nuevo"] and \
            d["renglones_nuevos"] == d["renglones_nuevos_de_las_20"] > 0
        ok_arch &= d["ok"]
        res["por_archivo"][k] = d
    fin_ok = True
    for to in ("ext", "docvig"):
        f = SALIDA / to / "finales.jsonl"
        u_head, u_ahora, u_trab = ultimas(en_head(f)), ultimas(f.read_bytes()), ultimas((TRABAJO / to / "finales.jsonl")
                                                                                      .read_bytes())
        fin_ok &= all(u_ahora[c] == u_trab[c] for c in u_trab) and set(u_trab) <= veinte \
            and all(u_ahora[c] == u_head[c] for c in u_head if c not in veinte) and set(u_ahora) == set(u_head)
    res["finales_ultima_version_ok"] = fin_ok
    res["renglones_nuevos_total"] = sum(d["renglones_nuevos"] for d in res["por_archivo"].values())
    res["ok"] = (res["cambiados_son_los_del_anexo"] and not res["agregados"] and not res["borrados"] and ok_arch
                 and fin_ok and res["e0_iguales"] == res["e0_archivos"] == 57)
    a.salida.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_archivo"}, ensure_ascii=False))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
