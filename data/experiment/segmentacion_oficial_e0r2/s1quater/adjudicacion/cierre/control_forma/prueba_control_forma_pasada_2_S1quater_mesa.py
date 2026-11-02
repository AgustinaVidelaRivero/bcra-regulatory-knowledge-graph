"""Prueba del control de forma de la pasada 2 de S1-quater, con datos sintéticos (mesa, 15/10/2026; USD 0). No usa nada de la lectura
ni de la adjudicación: fichas inventadas (F01…), marcas inventadas.

Uso: python3 -I -B prueba_control_forma_pasada_2_S1quater_mesa.py --control <control_forma_pasada_2_S1quater_mesa.py> --trabajo <carpeta nueva>
Caso bueno: la autora cambia solo columnas de marca a nota → todo ok y sale con 0. Casos en contra: cada uno tiene que dar MAL en el
control que corresponde (o FRENO) y salir con 1.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
LEC = ("marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
P2 = ADJ + tuple(f"lectora_{c}" for c in LEC)


def fila(ficha: str, marca: str, lec_marca: str, lec_nota: str = "") -> list[str]:
    d = dict.fromkeys(P2, "")
    d.update(ficha=ficha, marca=marca, lectora_marca=lec_marca, lectora_nota=lec_nota)
    if marca == "error":
        d.update(clase="corte", subclase="termina_fuera")
    if lec_marca == "error":
        d.update(lectora_clase="corte", lectora_subclase="empieza_fuera")
    return [d[c] for c in P2]


def texto(filas: list[list[str]], cab: tuple = P2, fin: str = "\n") -> str:
    return fin.join("\t".join(f) for f in [list(cab)] + filas) + fin


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    a = ap.parse_args()
    if a.trabajo.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    a.trabajo.mkdir(parents=True)
    sel = {1: [fila("F01", "correcta", "error"), fila("F02", "error", "correcta", "nota sintética")],
           2: [fila("F11", "correcta", "dudosa"), fila("F12", "error", "error"), fila("F13", "correcta", "correcta", "otra")]}
    for e in (1, 2):
        (a.trabajo / f"sel_{e}.tsv").write_text(texto(sel[e]), encoding="utf-8")

    def bueno(e: int) -> list[list[str]]:
        fs = [list(f) for f in sel[e]]
        fs[0][1] = "error"; fs[0][2] = "corte"; fs[0][3] = "empieza_fuera"; fs[0][10] = "nota de la autora"
        if e == 2:
            fs[1][9] = "error"
        return fs

    def mut(e: int, f) -> dict:
        return {e: f(bueno(e))}

    def lec_cambiada(fs):
        fs[1][P2.index("lectora_marca")] = "dudosa"; return texto(fs)

    def orden(fs):
        fs[0], fs[1] = fs[1], fs[0]; return texto(fs)

    def comillas(fs):
        fs[0][10] = 'con "comillas"'; return texto(fs)

    def columna_de_mas(fs):
        fs[1] = fs[1] + ["x"]; return texto(fs)

    def marca_rara(fs):
        fs[1][1] = "quizas"; return texto(fs)

    def herencia_e1(fs):
        fs[1][9] = "error"; return texto(fs)

    def encabezado(fs):
        return texto(fs, cab=P2[:-1] + ("lectora_otra",))

    casos = [
        ("bueno: solo cambian columnas de la autora", {}, 0, None),
        ("en contra: una columna lectora_ cambiada (etapa 2)", {2: lec_cambiada(bueno(2))}, 1, "MAL  etapa 2: las columnas lectora_"),
        ("en contra: dos fichas en otro orden (etapa 1)", {1: orden(bueno(1))}, 1, "MAL  etapa 1: la columna ficha"),
        ("en contra: comillas dobles en la nota (etapa 1)", {1: comillas(bueno(1))}, 1, "MAL  etapa 1: sin comillas"),
        ("en contra: un renglón con una columna de más (etapa 2)", {2: columna_de_mas(bueno(2))}, 1, "MAL  etapa 2: el encabezado"),
        ("en contra: una marca no permitida (etapa 2)", {2: marca_rara(bueno(2))}, 1, "MAL  etapa 2: marca, la_que_sigue"),
        ("en contra: herencia en la etapa 1", {1: herencia_e1(bueno(1))}, 1, "MAL  etapa 1: marca, la_que_sigue"),
        ("en contra: otro encabezado (etapa 1)", {1: encabezado(bueno(1))}, 1, "MAL  etapa 1: el encabezado"),
        ("en contra: fin de renglón con retorno de carro (etapa 2)", {2: texto(bueno(2), fin="\r\n")}, 1, "FRENO: la pasada 2 de la etapa 2: fin"),
        ("en contra: sha256 que no es el del sello (etapa 1)", {"sha_mal": 1}, 1, "FRENO: la pasada 2 de la etapa 1 no da su sha256"),
    ]
    ok_total = 0
    for k, (nombre, cambios, rc_esperado, aguja) in enumerate(casos):
        d = a.trabajo / f"caso_{k:02d}"
        d.mkdir()
        args = []
        for e in (1, 2):
            t = cambios.get(e, texto(bueno(e)))
            p = d / f"p2_{e}.tsv"
            p.write_bytes(t.encode("utf-8"))
            sh = hashlib.sha256(p.read_bytes()).hexdigest()
            if cambios.get("sha_mal") == e:
                sh = "0" * 64
            s = a.trabajo / f"sel_{e}.tsv"
            args += [f"--pasada-2-{e}", str(p), f"--sha-pasada-2-{e}", sh,
                     f"--seleccion-{e}", str(s), f"--sha-seleccion-{e}", hashlib.sha256(s.read_bytes()).hexdigest()]
        r = subprocess.run([sys.executable, "-I", "-B", str(a.control)] + args, capture_output=True, text=True)
        salida = r.stdout + r.stderr
        bien = r.returncode == rc_esperado and (aguja is None and "MAL" not in salida or aguja is not None and aguja in salida)
        ok_total += bien
        print(("ok   " if bien else "MAL  ") + nombre)
    print(f"{ok_total} de {len(casos)}")
    sys.exit(0 if ok_total == len(casos) else 1)


if __name__ == "__main__":
    main()
