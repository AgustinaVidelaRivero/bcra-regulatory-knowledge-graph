"""U-SEG-OFICIAL, S1-quater: instala el material de la pasada 2 de la adjudicación en la carpeta de la autora (mesa, 14/10/2026; USD 0).

Lo corre la autora con un comando que le prepara la mesa, que no escribe en su carpeta (decisión de la autora del §91). La selección
la hizo la mesa con `pasada_2_S1quater.py seleccionar`, sellado en el 59, y la regla a–d; este script no elige nada: arma el material
de las fichas seleccionadas y copia la planilla de la selección tal cual.

Entradas, todas controladas antes de escribir nada:
- la pasada 1 de la autora, por etapa:
  - `manifest.txt`, con el sha256 que registró la mesa al armar la pasada 1 (`orden_pasada_1_S1quater.json`); de ese manifest se
    controlan el archivo de fichas y las imágenes;
  - la planilla, contra el sha256 de su sello (el manifest trae la planilla vacía del armado);
- la selección: `adjudicacion_pasada_2_etapa_N.tsv`, con su sha256.

Controles:
- la selección tiene el encabezado de la pasada 2 (`pasada_2_S1quater.P2`) y la forma que controla `leer_autora`;
- sus fichas están en la pasada 1, en el mismo orden relativo, y no se repiten;
- sus columnas de la adjudicación son, valor por valor, las de la fila de la pasada 1;
- cada ficha cumple al menos una condición de la regla a–d (`pasada_2_S1quater.condiciones`);
- cada ficha tiene su bloque en el archivo de fichas de la pasada 1 y al menos una imagen en su manifest.

Escribe, por etapa, en `<out>/etapa_N/`. `<out>` no puede existir: escribe en `<out>.parcial` y lo renombra solo si todo dio; si no,
lo borra.
- `fichas_pasada_2_etapa_N.md`: por ficha, en el orden de la planilla, el bloque de la pasada 1 tal cual, por qué está en la pasada 2,
  la fila de la pasada 1 y la fila de la lectora, campo por campo;
- las imágenes de esas fichas, copiadas de la pasada 1;
- `adjudicacion_pasada_2_etapa_N.tsv`: la selección, byte a byte. Es lo único que la autora escribe;
- `LEEME.md` y `manifest.txt`, legible por `shasum -a 256 -c`.
Todo queda de solo lectura salvo la planilla. Imprime solo el sha256 del `manifest.txt` de cada etapa.

Uso: python3 -I -B instalar_pasada_2_S1quater.py --pasada-1 <carpeta pasada_1> --sha-manifest-1 <sha> --sha-manifest-2 <sha>
       --sha-planilla-1 <sha del sello> --sha-planilla-2 <sha del sello> --seleccion <carpeta> --sha-seleccion-1 <sha>
       --sha-seleccion-2 <sha> --out <carpeta pasada_2 nueva>
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pasada_2_S1quater as P2S            # noqa: E402  (sellado en el 59)
from preparar_pasada_1_S1quater import bloques  # noqa: E402  (sellado en el 59)

CONDICION = {"a": "tu marca de la pasada 1 y la de la lectora no coinciden",
             "b": "las dos marcaron error, pero una lo clasificó como de corte y la otra como de limpieza",
             "c": "la lectora dejó una nota",
             "d": "marcaste la_que_sigue o herencia como error (etapa 2)"}
LEEME = """# Adjudicación de la lectura de segmentación: etapa_{n}, pasada 2

Están las fichas de tu pasada 1 que cumplen al menos una condición de la regla a–d (`pasada_2_S1quater.py`, sellado en el 59):
- a. tu marca de la pasada 1 y la de la lectora no coinciden;
- b. las dos marcaron `error`, pero una lo clasificó como de corte y la otra como de limpieza;
- c. la lectora dejó una nota, aunque la marca coincida;
- d. en la etapa 2, marcaste `la_que_sigue` o `herencia` como `error`.

En `fichas_pasada_2_etapa_{n}.md`, cada ficha trae su bloque de la pasada 1, por qué está acá, tu fila de la pasada 1 y la de la
lectora. Sus imágenes están en esta carpeta.

**Dónde marcás:** `adjudicacion_pasada_2_etapa_{n}.tsv`. Trae tu fila de la pasada 1 en las columnas de la adjudicación (de `marca` a
`nota`) y, al final, las de la lectora (de `lectora_marca` a `lectora_nota`), solo para leer.
- Corregí, si hace falta, solo las columnas de `marca` a `nota`, con los mismos valores de la pasada 1 (LEEME de la pasada 1).
- No cambies la columna `ficha`, el orden de las filas, el encabezado ni las columnas de la lectora.
- Separador: tabulación. En ninguna celda va una tabulación, un salto de renglón ni comillas dobles.
- Rige el mismo criterio que en la pasada 1.
- Sin ningún modelo, ni para leer las fichas ni para escribir la planilla (decisión del 14/10/2026).

**Sello**, cuando termines la etapa:
`shasum -a 256 adjudicacion_pasada_2_etapa_{n}.tsv > sello_adjudicacion_pasada_2_etapa_{n}.txt` y
`date '+%Y-%m-%d %H:%M:%S %z' >> sello_adjudicacion_pasada_2_etapa_{n}.txt`. Después, `chmod a-w adjudicacion_pasada_2_etapa_{n}.tsv`.
"""


class Freno(Exception):
    pass


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def leer_manifest(d: Path, sh: str, n: int) -> dict[str, str]:
    m = d / "manifest.txt"
    if not m.is_file() or sha(m) != sh:
        raise Freno(f"el manifest.txt de la etapa {n} de la pasada 1 no da el sha256 del registro de la mesa")
    out = {}
    for renglon in m.read_text(encoding="utf-8").splitlines():
        h, nombre = renglon.split("  ", 1)
        out[nombre] = h
    return out


def preparar_etapa(a, n: int) -> dict:
    d = Path(a.pasada_1) / f"etapa_{n}"
    man = leer_manifest(d, getattr(a, f"sha_manifest_{n}"), n)
    fichas_md = f"fichas_pasada_1_etapa_{n}.md"
    planilla = f"adjudicacion_pasada_1_etapa_{n}.tsv"
    if fichas_md not in man or planilla not in man:
        raise Freno(f"el manifest de la etapa {n} no lista el archivo de fichas o la planilla")
    if sha(d / fichas_md) != man[fichas_md]:
        raise Freno(f"el archivo de fichas de la etapa {n} no da el sha256 de su manifest")
    p1 = P2S.leer_autora(d / planilla, getattr(a, f"sha_planilla_{n}"), P2S.ADJ, f"la pasada 1 de la etapa {n}")
    sel_p = Path(a.seleccion) / f"adjudicacion_pasada_2_etapa_{n}.tsv"
    if not sel_p.is_file():
        raise Freno(f"falta la selección de la etapa {n}")
    sel = P2S.leer_autora(sel_p, getattr(a, f"sha_seleccion_{n}"), P2S.P2, f"la selección de la etapa {n}")
    orden = [f["ficha"] for f in p1]
    de_p1 = {f["ficha"]: f for f in p1}
    ids = [f["ficha"] for f in sel]
    if any(i not in de_p1 for i in ids) or ids != [i for i in orden if i in set(ids)]:
        raise Freno(f"la selección de la etapa {n} no trae fichas de la pasada 1 en su orden")
    bl = bloques((d / fichas_md).read_text(encoding="utf-8"))
    imagenes = {}
    for f in sel:
        i = f["ficha"]
        if any(f[c] != de_p1[i][c] for c in P2S.ADJ):
            raise Freno(f"en la selección de la etapa {n}, una fila no es la de la pasada 1 ({i})")
        lec = {c: f[f"lectora_{c}"] for c in P2S.LEC}
        if not P2S.condiciones(de_p1[i], lec, n):
            raise Freno(f"en la selección de la etapa {n}, una ficha no cumple ninguna condición de la regla a–d ({i})")
        if i not in bl:
            raise Freno(f"la ficha {i} no tiene su bloque en el archivo de fichas de la etapa {n}")
        imgs = sorted(x for x in man if x.startswith(f"{i}_p") and x.endswith(".png"))
        if not imgs:
            raise Freno(f"la ficha {i} no tiene imágenes en el manifest de la etapa {n}")
        for x in imgs:
            if not (d / x).is_file() or sha(d / x) != man[x]:
                raise Freno(f"una imagen de la etapa {n} no da el sha256 de su manifest ({x})")
        imagenes[i] = imgs
    return {"d": d, "sel": sel, "sel_p": sel_p, "de_p1": de_p1, "bl": bl, "imagenes": imagenes}


def valor(v: str) -> str:
    return v if v else "(vacía)"


def escribir_etapa(n: int, e: dict, dest: Path) -> str:
    dest.mkdir(parents=True)
    partes = [f"# Adjudicación de la lectura de segmentación: etapa_{n}, pasada 2\n\nLas fichas de la pasada 2, en el orden de la "
              f"planilla. Cada una, con su bloque de la pasada 1 tal cual.\n\n"]
    for f in e["sel"]:
        i = f["ficha"]
        b = e["bl"][i]
        partes.append(b if b.endswith("\n") else b + "\n")
        lec = {c: f[f"lectora_{c}"] for c in P2S.LEC}
        partes.append("\n### Por qué está en la pasada 2\n\n")
        partes += [f"- {c}: {CONDICION[c]}\n" for c in P2S.condiciones(e["de_p1"][i], lec, n)]
        partes.append("\n### Tu pasada 1\n\n")
        partes += [f"- {c}: {valor(e['de_p1'][i][c])}\n" for c in P2S.ADJ[1:]]
        partes.append("\n### La lectora\n\n")
        partes += [f"- {c}: {valor(lec[c])}\n" for c in P2S.LEC]
        partes.append("\n---\n\n")
        for x in e["imagenes"][i]:
            shutil.copy2(e["d"] / x, dest / x)
    fichas = dest / f"fichas_pasada_2_etapa_{n}.md"
    fichas.write_text("".join(partes), encoding="utf-8")
    planilla = dest / f"adjudicacion_pasada_2_etapa_{n}.tsv"
    shutil.copyfile(e["sel_p"], planilla)
    (dest / "LEEME.md").write_text(LEEME.format(n=n), encoding="utf-8")
    nombres = sorted(p.name for p in dest.iterdir())
    (dest / "manifest.txt").write_text("".join(f"{sha(dest / x)}  {x}\n" for x in nombres), encoding="utf-8")
    # controles de lo escrito
    if planilla.read_bytes() != e["sel_p"].read_bytes():
        raise Freno(f"la planilla de la etapa {n} no quedó igual a la selección")
    for x in nombres:
        if x.endswith(".png") and sha(dest / x) != sha(e["d"] / x):
            raise Freno(f"una imagen de la etapa {n} no quedó igual a la de la pasada 1")
    for p in dest.iterdir():
        p.chmod(0o644 if p.name == planilla.name else 0o444)
    return sha(dest / "manifest.txt")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("pasada_1", "sha_manifest_1", "sha_manifest_2", "sha_planilla_1", "sha_planilla_2", "seleccion", "sha_seleccion_1",
              "sha_seleccion_2", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    fin = Path(a.out)
    parcial = fin.with_name(fin.name + ".parcial")
    try:
        if fin.exists() or parcial.exists():
            raise Freno("la carpeta de la pasada 2 (o su .parcial) ya existe")
        etapas = {n: preparar_etapa(a, n) for n in (1, 2)}   # todo se controla antes de escribir nada
        parcial.mkdir(parents=True)
        mans = {n: escribir_etapa(n, etapas[n], parcial / f"etapa_{n}") for n in (1, 2)}
    except (Freno, SystemExit) as ex:
        if parcial.exists():
            for p in parcial.rglob("*"):
                p.chmod(0o755 if p.is_dir() else 0o644)
            shutil.rmtree(parcial)
        raise SystemExit(f"FRENO: {ex}" if isinstance(ex, Freno) else ex.code)
    parcial.rename(fin)
    for n in (1, 2):
        print(f"etapa_{n}: manifest.txt {mans[n]}")


if __name__ == "__main__":
    main()
