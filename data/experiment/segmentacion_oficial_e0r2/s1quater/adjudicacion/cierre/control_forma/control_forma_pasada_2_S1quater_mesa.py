"""U-SEG-OFICIAL, S1-quater: control de forma de las planillas selladas de la pasada 2, antes de `armar` (mesa, 15/10/2026; USD 0).

Es el paso 9 del paso a paso de la pasada 2 (hoja de ruta de la mesa, §99, `pasos_pasada_2_para_la_autora_mesa.md`): «Yo controlo la
forma de las planillas». Sale de `adjudicacion_S1ter_cierre_mesa/control_forma/control_forma_pasada_2_S1ter_mesa.py` (11/10/2026), con
un control más: las columnas `lectora_…` son de solo lectura (paso 4 del paso a paso), así que tienen que ser, renglón por renglón, las
de la selección que instaló `instalar_pasada_2_S1quater.py`.

Uso: python3 -I -B control_forma_pasada_2_S1quater_mesa.py --pasada-2-1 <tsv> --sha-pasada-2-1 <sha del sello>
       --pasada-2-2 <tsv> --sha-pasada-2-2 <sha del sello> --seleccion-1 <tsv de `seleccionar`> --sha-seleccion-1 <sha>
       --seleccion-2 <tsv> --sha-seleccion-2 <sha>

Lee cada planilla por renglones y tabulaciones, sin el módulo csv. Por etapa:
1. sin retorno de carro y con salto final; el encabezado es el de la selección (columnas de `pasada_2_S1quater.P2`), y cada renglón
   tiene sus columnas;
2. no hay comillas dobles en las columnas de la autora, de `marca` a `nota`;
3. la columna `ficha` es la de la selección: las mismas fichas, en el mismo orden;
4. las columnas `lectora_…` son las de la selección, renglón por renglón;
5. los valores de `marca`, `la_que_sigue` y `herencia` son de los permitidos, y la etapa 1 no lleva unidad que sigue ni herencia (las
   mismas reglas que `validar_adj` de `pasada_2_S1quater.py`, que `armar` vuelve a aplicar).
No imprime valores de las planillas: solo «ok» o «MAL» por control, con el número de renglón si falla. No escribe nada. Sale con 1 si
algo falla.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
LEC = ("marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
P2 = ADJ + tuple(f"lectora_{c}" for c in LEC)
DE_LA_AUTORA = ADJ[1:]
MARCAS = ("correcta", "error", "dudosa")


def renglones(p: Path, sh: str, que: str) -> list[list[str]]:
    datos = p.read_bytes()
    if hashlib.sha256(datos).hexdigest() != sh:
        sys.exit(f"FRENO: {que} no da su sha256")
    texto = datos.decode("utf-8")
    if "\r" in texto or not texto.endswith("\n"):
        sys.exit(f"FRENO: {que}: fin de renglón inesperado")
    return [r.split("\t") for r in texto[:-1].split("\n")]


def controlar(p2: list[list[str]], sel: list[list[str]], etapa: int) -> list[tuple[bool, str]]:
    cab, filas = p2[0], p2[1:]
    n = len(P2)
    malas_cols = [k for k, f in enumerate(filas, 2) if len(f) != n]
    buenas = [(k, dict(zip(P2, f))) for k, f in enumerate(filas, 2) if len(f) == n]   # por posición: si el encabezado cambia, falla el control 1
    con_comillas = [k for k, f in buenas if any('"' in f[c] for c in DE_LA_AUTORA)]
    sel_por_ficha = {f[0]: dict(zip(P2, f)) for f in sel[1:]}
    lectora_cambiada = [k for k, f in buenas
                        if f["ficha"] in sel_por_ficha and any(f[f"lectora_{c}"] != sel_por_ficha[f["ficha"]][f"lectora_{c}"] for c in LEC)]
    valores = [k for k, f in buenas if f["marca"] not in MARCAS or any(f[c] not in ("", "error") for c in ("la_que_sigue", "herencia"))
               or (etapa == 1 and any(f[c] for c in ("la_que_sigue", "clase_que_sigue", "subclase_que_sigue", "herencia")))]
    ids_p2 = [f[0] for f in filas]
    ids_sel = [f[0] for f in sel[1:]]
    return [
        (tuple(cab) == P2 and tuple(sel[0]) == P2 and not malas_cols,
         f"etapa {etapa}: el encabezado es el de la selección y cada renglón tiene sus {n} columnas"
         + (f" (renglones con otra cantidad: {malas_cols})" if malas_cols else "")),
        (not con_comillas, f"etapa {etapa}: sin comillas dobles en las columnas de la autora, de marca a nota"
         + (f" (renglones: {con_comillas})" if con_comillas else "")),
        (ids_p2 == ids_sel, f"etapa {etapa}: la columna ficha es la de la selección, en su orden"),
        (not lectora_cambiada and len(buenas) == len(filas),
         f"etapa {etapa}: las columnas lectora_… son las de la selección, renglón por renglón"
         + (f" (renglones: {lectora_cambiada})" if lectora_cambiada else "")),
        (not valores, f"etapa {etapa}: marca, la_que_sigue y herencia con valores permitidos"
         + (f" (renglones: {valores})" if valores else "")),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("pasada_2_1", "sha_pasada_2_1", "pasada_2_2", "sha_pasada_2_2", "seleccion_1", "sha_seleccion_1", "seleccion_2",
              "sha_seleccion_2"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    res = []
    for e in (1, 2):
        p2 = renglones(Path(getattr(a, f"pasada_2_{e}")), getattr(a, f"sha_pasada_2_{e}"), f"la pasada 2 de la etapa {e}")
        sel = renglones(Path(getattr(a, f"seleccion_{e}")), getattr(a, f"sha_seleccion_{e}"), f"la selección de la etapa {e}")
        res += controlar(p2, sel, e)
    for b, q in res:
        print(("ok   " if b else "MAL  ") + q)
    sys.exit(0 if all(b for b, _ in res) else 1)


if __name__ == "__main__":
    main()
