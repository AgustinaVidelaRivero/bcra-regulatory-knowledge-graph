#!/usr/bin/env python3
"""selftest_comandos_b64.py — La prueba de los comandos de la corrección del H-6 (B6.4), con datos de juguete. USD 0, sin la API, sin
ningún dato real: arma en --trabajo (que no puede existir) un HOME de juguete con lo que leen los comandos y los corre ahí, con `env -i` y
HOME apuntando a él, así que no pueden leer ni escribir nada fuera de él:
  - el repo: un clon de HEAD por rutas explícitas (lo que importa el runner de H-4: b63/v2/b2, agentes/ y paralelo/, sin ningún
    *_SOLO_MESA* ni NO_ABRIR_*, más comun_banco, el juez de EV2 y llm_cache), con el runner de H-4 (runner_b64/para_el_repo/, cada
    archivo con el sha256 de runner_b64/lista_H34.txt) en data/experiment/banco_mcp/b64/v1/, una entrada de juguete en
    data/experiment/banco_mcp/b64/entrada_B64.json y el .venv del repo, enlazado;
  - fuera_del_repo/: banco_b64/ de juguete, con la forma de la salida del runner de H-4 (resultados/real/ y juez/), y una lista y un
    sello de juguete en analisis_b64_corr/.

Las ramas:
  - el del manifiesto (corrida_manifiesto_fuera_B64.zsh): sin llenar, frena con 22 sin escribir; lleno (una copia que difiere solo en el
    renglón del sha256 de la entrada), escribe su JSON con la forma del runner (rutas «banco_b64/…», tamaño y sha256 de cada archivo de
    las dos carpetas), su consola y su código de salida, y analizar_b63.Banco lo acepta; otra vez, frena con 23 porque ya existe, sin
    pisarlo; con una lista que no es la del sello, frena con 20 sin escribir;
  - los de H-6: MANIFIESTO, D10 y FECHAS llenos, con las rutas del runner de H-4; los demás PENDIENTE siguen así; corridos en el HOME de
    juguete, cada uno frena con 22 en el primero que falta, sin escribir nada; todos controlan la lista contra el sello de la corrección;
  - ningún comando lleva rm ni sleep.
Imprime solo el nombre de cada control con PASS o FAIL y el sha256 del informe (sin rutas, para que dos corridas den lo mismo).

  B64_CODIGO_B63=<b63/analisis/codigo de una copia de HEAD> python3 -I -B selftest_comandos_b64.py --comandos <comandos/> --repo <el repo>
      --runner <runner_b64/> --trabajo <carpeta nueva> --informe <json nuevo>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import analizar_b64 as B  # noqa: E402  (solo import: analizar_b63.Banco)

A = B.A
RUNNER = "data/experiment/banco_mcp/b64/v1"
CARPETAS_DEL_RUNNER = re.compile(r"^data/experiment/banco_mcp/(b63/v2/b2|agentes|paralelo)/[^/]+\.(py|json)$")
SUELTOS = ("data/experiment/banco_mcp/comun_banco.py", "data/experiment/ev2_juez/juez.py", "data/experiment/ev2_juez/mapping.py",
           "data/experiment/ev2_juez/prompt_juez_v1.md", "data/experiment/evaluacion/llm_cache.py")
DE_H6 = {"corrida_analisis_B64.zsh": ("ESPERADO", ["ESPERADO", "SHA_ESPERADO", "ENTRADA", "CLASES", "LUGARES", "EXPERTOS"]),
         "corrida_exactitud_de_cita_B64.zsh": ("ESPERADO", ["ESPERADO", "SHA_ESPERADO", "ENTRADA", "E0", "ARMADO_E0"]),
         "corrida_lectura_tolerante_B64.zsh": ("ENTRADA", ["ENTRADA", "SHA_ENTRADA"]),
         "corrida_armado_adjudicacion_B64.zsh": ("ENTRADA", ["ENTRADA", "SHA_ENTRADA"])}
MANIFIESTO_CMD = "corrida_manifiesto_fuera_B64.zsh"
LLENOS = {"corrida_analisis_B64.zsh": {"MANIFIESTO": "$F/banco_b64/manifiesto_fuera_B64.json", "D10": "$F/banco_b64/juez/d10_b63.json",
                                       "FECHAS": "$F/banco_b64/resultados/real/fechas_b63.json"},
          "corrida_exactitud_de_cita_B64.zsh": {"MANIFIESTO": "$F/banco_b64/manifiesto_fuera_B64.json"},
          MANIFIESTO_CMD: {"MANIFIESTO": "$F/banco_b64/manifiesto_fuera_B64.json", "OUT": "$F/banco_b64/resultados/real",
                           "JUEZ": "$F/banco_b64/juez", "ENTRADA": "data/experiment/banco_mcp/b64/entrada_B64.json"}}


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def escribir(p: Path, contenido) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    b = contenido if isinstance(contenido, (bytes, str)) else json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    b = b.encode("utf-8") if isinstance(b, str) else b
    p.write_bytes(b)
    return sha_b(b)


def foto(*raices: Path) -> dict:
    """{ruta: sha256} de los archivos bajo las raíces (sin seguir enlaces): para ver que un comando no escribió nada."""
    out = {}
    for r in raices:
        for d, subs, ns in os.walk(r, followlinks=False):
            for n in ns:
                p = Path(d) / n
                out[str(p)] = "enlace" if p.is_symlink() else sha_b(p.read_bytes())
    return out


def asignaciones(texto: str) -> dict:
    """Las asignaciones VAR="valor" de un comando, al principio de un renglón o después de «;»."""
    return dict(re.findall(r'(?:^|;\s*)([A-Z_0-9]+)="([^"]*)"', texto, flags=re.M))


def casa(H: Path, repo: Path, runner: Path, lista_runner: dict, lista_buena: bool = True) -> dict:
    """Un HOME de juguete: el repo (clon de HEAD por rutas explícitas, el runner de H-4, la entrada de juguete y el .venv enlazado) y
    fuera_del_repo/ (banco_b64/ de juguete y la lista y el sello de juguete de la corrección)."""
    R = H / "bcra-regulatory-kg"
    F = H / "fuera_del_repo"
    R.mkdir(parents=True)
    ls = subprocess.run(["git", "-C", str(repo), "--no-optional-locks", "ls-tree", "-r", "--name-only", "HEAD",
                         "data/experiment/banco_mcp/b63/v2/b2", "data/experiment/banco_mcp/agentes", "data/experiment/banco_mcp/paralelo"],
                        capture_output=True, text=True, check=True).stdout.splitlines()
    rutas = [p for p in ls if CARPETAS_DEL_RUNNER.match(p) and not A.veda(Path(p).name)] + list(SUELTOS)
    arch = subprocess.run(["git", "-C", str(repo), "--no-optional-locks", "archive", "HEAD", *rutas], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(R)], input=arch, check=True)
    for rel, s in lista_runner.items():
        destino = R / RUNNER / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(runner / "para_el_repo" / RUNNER / rel, destino)
        if sha_b(destino.read_bytes()) != s:
            raise SystemExit("ABORTO: un archivo del runner de H-4 no da el sha256 de su lista")
    (R / ".venv").symlink_to(repo / ".venv")
    sha_entrada = escribir(R / "data" / "experiment" / "banco_mcp" / "b64" / "entrada_B64.json", {"que": "la entrada de juguete"})
    BB = F / "banco_b64"
    sid = "B63-JUG-X01-r1-kg"
    escribir(BB / "resultados" / "real" / "estado_b63.json", {"que": "estado de juguete", "bloques": {}})
    escribir(BB / "resultados" / "real" / "fechas_b63.json", {"por_brazo_y_fecha": {}})
    escribir(BB / "resultados" / "real" / "pasada1" / sid / f"meta_{sid}.json", {"brazo": "kg"})
    escribir(BB / "resultados" / "real" / "pasada1" / sid / f"log_r1_{sid}.jsonl", '{"evento": "inicio"}\n')
    for n in ("veredictos_r1.jsonl", "errores_r1.jsonl"):
        escribir(BB / "juez" / n, "")
    escribir(BB / "juez" / "d10_b63.json", {"por_brazo": {}})
    escribir(BB / "juez" / "agregados_b63_ciego.json", {"agregados": []})
    lista = escribir(F / "analisis_b64_corr" / "lista_H6_corr.txt", "lista de juguete\n")
    escribir(F / "analisis_b64_corr" / "sello_H6_corr.txt", f"sha256: {lista if lista_buena else '0' * 64}\n")
    return {"H": H, "R": R, "F": F, "sha_entrada": sha_entrada, "clon": len(rutas)}


def zsh(cmd: Path, H: Path, *args) -> tuple[int, str]:
    r = subprocess.run(["/bin/zsh", "-f", str(cmd), *map(str, args)], env={"HOME": str(H), "PATH": "/usr/bin:/bin", "BCRA_KG_FUERA_DEL_REPO": str(H / "fuera_del_repo")}, cwd=str(H),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    for a in ("comandos", "repo", "runner", "trabajo", "informe"):
        ap.add_argument("--" + a, type=Path, required=True)
    a = ap.parse_args(argv)
    if a.trabajo.exists() or a.informe.exists():
        raise SystemExit("--trabajo y --informe no pueden existir")
    T = a.trabajo.resolve()
    T.mkdir(parents=True)
    CM = a.comandos.resolve()
    lr = [l.split() for l in (a.runner / "lista_H34.txt").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    lista_runner = {p.split(f"para_el_repo/{RUNNER}/", 1)[1]: s for s, _, p in lr if p.startswith(f"para_el_repo/{RUNNER}/")}
    R: dict = {}
    salidas: dict = {}

    def control(nombre, cond):
        R[nombre] = "PASS" if cond else "FAIL"

    # --- El comando del manifiesto ------------------------------------------------------------------------------------ #
    c1 = casa(T / "casa", a.repo.resolve(), a.runner.resolve(), lista_runner)
    H, F = c1["H"], c1["F"]
    MAN = F / "banco_b64" / "manifiesto_fuera_B64.json"
    original = (CM / MANIFIESTO_CMD).read_text(encoding="utf-8")
    lleno = original.replace('SHA_ENTRADA="PENDIENTE"', f'SHA_ENTRADA="{c1["sha_entrada"]}"', 1)
    distintos = [(x, y) for x, y in zip(original.split("\n"), lleno.split("\n")) if x != y]
    escribir(T / "lleno" / MANIFIESTO_CMD, lleno)
    antes = foto(H)
    rc0, s0 = zsh(CM / MANIFIESTO_CMD, H)
    control("manifiesto_sin_llenar_frena_con_22_sin_escribir", rc0 == 22 and s0 == "falta llenar SHA_ENTRADA" and foto(H) == antes)
    rc1, s1 = zsh(T / "lleno" / MANIFIESTO_CMD, H)
    m = json.loads(MAN.read_text(encoding="utf-8")) if MAN.is_file() else {}
    BB = F / "banco_b64"
    de_banco = sorted(str(p.relative_to(F)) for c in ("resultados/real", "juez") for p in (BB / c).rglob("*") if p.is_file())
    sm = sha_b(MAN.read_bytes()) if MAN.is_file() else None
    control("manifiesto_lleno_escribe_su_json_con_la_forma_del_runner",
            len(distintos) == 1 and distintos[0][0] == 'SHA_ENTRADA="PENDIENTE"        # H-3: su sha256' and rc1 == 0
            and m.get("raiz") == "fuera_del_repo/" and m.get("carpetas") == ["banco_b64/resultados/real", "banco_b64/juez"]
            and sorted(x["ruta"] for x in m.get("archivos", [])) == de_banco and m.get("n_archivos") == len(de_banco)
            and all(x["sha256"] == sha_b((F / x["ruta"]).read_bytes()) and x["bytes"] == (F / x["ruta"]).stat().st_size for x in m["archivos"])
            and m.get("carpetas_por_nombre") == [] and m.get("enlaces") == []
            and (BB / "codigo_de_salida_manifiesto_fuera_B64.txt").read_text(encoding="utf-8") == "0\n"
            and json.loads((BB / "consola_manifiesto_fuera_B64.txt").read_text(encoding="utf-8")) == {"manifiesto_fuera": len(de_banco),
                                                                                                      "carpetas_por_nombre": 0}
            and s1.splitlines()[-1] == f"manifiesto_fuera_B64.json: {sm}")
    try:
        banco = A.Banco(BB, MAN, {"manifiesto_fuera": sm})
        lo_lee = all(banco.leer(F / r) == (F / r).read_bytes() for r in de_banco)
    except (A.Freno, OSError):
        lo_lee = False
    control("el_manifiesto_lo_acepta_analizar_b63_Banco", lo_lee)
    estado = (MAN.read_bytes(), MAN.stat().st_mtime_ns) if MAN.is_file() else None
    antes = foto(H)
    rc2, s2 = zsh(T / "lleno" / MANIFIESTO_CMD, H)
    control("manifiesto_otra_vez_frena_con_23_sin_pisarlo", rc2 == 23 and s2 == "ya existe: manifiesto_fuera_B64.json"
            and (MAN.read_bytes(), MAN.stat().st_mtime_ns) == estado and foto(H) == antes)
    c2 = casa(T / "casa_otra_lista", a.repo.resolve(), a.runner.resolve(), lista_runner, lista_buena=False)
    escribir(T / "lleno_otra_lista" / MANIFIESTO_CMD, original.replace('SHA_ENTRADA="PENDIENTE"', f'SHA_ENTRADA="{c2["sha_entrada"]}"', 1))
    antes = foto(c2["H"])
    rc3, s3 = zsh(T / "lleno_otra_lista" / MANIFIESTO_CMD, c2["H"])
    control("manifiesto_con_una_lista_que_no_es_la_del_sello_frena_con_20_sin_escribir",
            rc3 == 20 and s3 == "la lista no es la del sello de la corrección del H-6" and foto(c2["H"]) == antes)
    salidas["manifiesto"] = {"codigos": [rc0, rc1, rc2, rc3], "consolas": [s0, s1.splitlines()[-1] if s1 else "", s2, s3],
                             "sha256_manifiesto": sm, "archivos_del_banco_de_juguete": len(de_banco), "clon_rutas": c1["clon"]}

    # --- Los comandos de H-6: lo lleno, lo PENDIENTE, y el freno ------------------------------------------------------- #
    textos = {n: (CM / n).read_text(encoding="utf-8") for n in list(DE_H6) + [MANIFIESTO_CMD]}
    asig = {n: asignaciones(t) for n, t in textos.items()}
    runner_txt = (a.runner / "para_el_repo" / RUNNER / "correr_b63.py").read_text(encoding="utf-8")
    control("manifiesto_D10_y_fechas_llenos_con_las_rutas_del_runner_de_H4",
            all(asig[n].get(k) == v for n, d in LLENOS.items() for k, v in d.items())
            and 'self.juez_dir / "d10_b63.json"' in runner_txt and 'self.out / "fechas_b63.json"' in runner_txt
            and "--manifiesto-fuera" in runner_txt)
    pend = {n: sorted(k for k, v in asig[n].items() if v == "PENDIENTE") for n in asig}
    control("los_demas_PENDIENTE_siguen_asi", all(pend[n] == sorted(v[1]) for n, v in DE_H6.items()) and pend[MANIFIESTO_CMD] == ["SHA_ENTRADA"])
    sp = T / "scratchpad_de_juguete"
    sp.mkdir()
    corridas = {}
    for n, (primero, _) in DE_H6.items():
        antes = foto(H, sp)
        corridas[n] = zsh(CM / n, H, sp) + (foto(H, sp) == antes,)
    control("los_de_H6_frenan_con_22_en_el_primero_que_falta_sin_escribir",
            all(corridas[n] == (22, f"falta llenar {DE_H6[n][0]}", True) for n in DE_H6))
    control("todos_controlan_la_lista_contra_el_sello_de_la_correccion",
            all('H6="$F/analisis_b64_corr"' in t and '"$H6/lista_H6_corr.txt"' in t and '"$H6/sello_H6_corr.txt"' in t
                and "analisis_b64/" not in t.replace("analisis_b64_corr/", "") for t in textos.values()))
    todos = {p.name: p.read_text(encoding="utf-8") for p in sorted(CM.glob("*.zsh"))}
    control("ningun_comando_lleva_rm_ni_sleep", not any(re.search(r"(^|[\s;&|(])(rm|sleep)(\s|$)", t, flags=re.M) for t in todos.values()))
    salidas["comandos_de_H6"] = {n: {"codigo": c[0], "consola": c[1], "sin_escribir": c[2]} for n, c in corridas.items()}
    salidas["pendientes"] = pend

    informe = {"que": "la prueba de los comandos de la corrección del H-6 (B6.4), en un HOME de juguete",
               "codigo": {Path(__file__).name: sha_b(Path(__file__).read_bytes())},
               "comandos": {n: sha_b(t.encode("utf-8")) for n, t in todos.items()},
               "runner_de_H4": dict(sorted(lista_runner.items())), "salidas": salidas, "controles": R,
               "da": all(v == "PASS" for v in R.values())}
    a.informe.parent.mkdir(parents=True, exist_ok=True)
    a.informe.write_text(json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in R.items():
        print(f"{v}  {k}")
    print(f"prueba: {'PASS' if informe['da'] else 'FAIL'} ({sum(v == 'PASS' for v in R.values())} de {len(R)}); "
          f"informe sha256 {sha_b(a.informe.read_bytes())}")
    return 0 if informe["da"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
