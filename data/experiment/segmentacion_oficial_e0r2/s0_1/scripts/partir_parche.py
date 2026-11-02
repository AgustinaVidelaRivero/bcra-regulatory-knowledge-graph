"""Parche del prototipo de S0-1 contra el código del repo, partido por regla (USD 0). No aplica nada al repo.

Uso: python -B partir_parche.py <dir base: e0_chunking del repo copiado> <dir prototipo: e0_chunking> <salida>

Escribe en <salida>: el parche completo y un parche por regla (trozos del diff unificado clasificados por las marcas
de cada regla; un trozo con marcas de más de una regla va al parche común, que se aplica primero). Verifica que
aplicar el común y después los de cada regla, en orden, sobre una copia de la base reproduce el prototipo byte a
byte (aplicador propio: cada trozo se ubica por su contexto exacto, sin desplazamientos ni coincidencias difusas).
"""
import difflib
import json
import re
import sys
from pathlib import Path

ARCHIVOS = ("e0_lib.py", "correr_e0.py")
MARCAS = {
    "r1": ["seccion_variante", "RE_SECCION_VARIANTE_R2", "_match_seccion_r2", "Regla 1:"],
    "r2": ["rotulos_r2", "REMISION_ENVUELTA", "motivo_2", "MIN_FILAS_CODIGO", "codigos_pagina", "Regla 2:"],
    "r3": ["continuacion_con_titulo", "regla 3 de S0"],
    "r4": ["marcador_letra", "APARTADO", "ROTULO_LETRA", "MIN_APARTADOS", "regla 4 de S0", "Regla 4:"],
    "r5": ["COLA_TITULO_ESTRICTA_R5", "cola_estricta_si_prosa", "_estricta", "estado_cola", "regla 5 de S0"],
    "r6": ["renglones", "partir_por_renglones", "PARTIR_TABLAS", "rol_bloque", "RE_FIN_ORACION", "_piezas_renglones",
           "regla 6", "r6 =", "r6 and", "if r6"],
    "r7": ["reabrir", "reapertura", "camino_para_reabrir", "_ultima_pos", "punto 7 de S0"],
    "r1r7t": ["fundir_tabla", "r1r7t"],
}
ORDEN = ["comun", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r1r7t"]


def trozos(a: list[str], b: list[str]):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for grupo in sm.get_grouped_opcodes(3):
        i1, i2 = grupo[0][1], grupo[-1][2]
        j1, j2 = grupo[0][3], grupo[-1][4]
        yield (i1, i2, j1, j2, a[i1:i2], b[j1:j2])


def clasificar(texto: str) -> str:
    rs = [r for r, ms in MARCAS.items() if any(m in texto for m in ms)]
    return rs[0] if len(rs) == 1 else "comun"


def main():
    base, proto, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    sal.mkdir(parents=True, exist_ok=True)
    por_regla = {r: [] for r in ORDEN}
    indice = []
    completo = []
    for nombre in ARCHIVOS:
        a = (base / nombre).read_text(encoding="utf-8").splitlines(keepends=True)
        b = (proto / nombre).read_text(encoding="utf-8").splitlines(keepends=True)
        completo.extend(difflib.unified_diff(a, b, f"a/{nombre}", f"b/{nombre}"))
        for (i1, i2, j1, j2, va, vb) in trozos(a, b):
            nuevo = "".join(x for x in vb if x not in va) + "".join(x for x in va if x not in vb)
            r = clasificar(nuevo)
            por_regla[r].append((nombre, i1, va, vb))
            indice.append({"archivo": nombre, "lineas_base": f"{i1 + 1}-{i2}", "parche": r,
                           "reglas_en_el_trozo": [x for x, ms in MARCAS.items() if any(m in nuevo for m in ms)]})
    (sal / "parche_completo_S0-1_prototipo.diff").write_text("".join(completo), encoding="utf-8")
    for r in ORDEN:
        if not por_regla[r]:
            continue
        out = []
        for nombre, i1, va, vb in por_regla[r]:
            out.extend(difflib.unified_diff(va, vb, f"a/{nombre}", f"b/{nombre}", n=len(va) + len(vb)))
        (sal / f"parche_{ORDEN.index(r):02d}_{r}_S0-1_prototipo.diff").write_text("".join(out), encoding="utf-8")
    # verificación: aplicar, en orden, cada trozo (reemplazo del bloque viejo exacto por el nuevo)
    for nombre in ARCHIVOS:
        texto = (base / nombre).read_text(encoding="utf-8")
        for r in ORDEN:
            for n, i1, va, vb in por_regla[r]:
                if n != nombre:
                    continue
                viejo, nuevo = "".join(va), "".join(vb)
                if viejo:
                    assert texto.count(viejo) == 1, (nombre, r, i1)
                    texto = texto.replace(viejo, nuevo)
                else:
                    raise SystemExit(f"trozo sin contexto en {nombre}:{i1}")
        igual = texto == (proto / nombre).read_text(encoding="utf-8")
        print(nombre, "reproduce el prototipo:", igual)
        assert igual
    (sal / "indice_trozos_S0-1.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1) + "\n",
                                                 encoding="utf-8")
    print({r: len(v) for r, v in por_regla.items()})


if __name__ == "__main__":
    main()
