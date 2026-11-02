"""U-SEG-OFICIAL, S1-ter-b2: el número que E0 le asignó a la unidad en las fichas de las dos etapas, las imágenes que
faltan de la unidad que sigue (etapa 2) y el `manifest.txt` de cada etapa (USD 0). No marca.

Uso: python -B fichas_numero_S1ter.py --orden <tramo_b/orden_lectura_S1ter.json> --sha-orden <sha256 sellado>
       --e0 <s1ter/e0> --pdfs <escalado_prep/pdfs> --carpeta <copia de la carpeta de la lectora, en el scratchpad>
       --registro <json>

Decisiones de la autora sobre el FRENO S1-ter-b (punto 2 a 6). Parte de la carpeta tal como la dejó S1-ter-b: controla
que el `manifest.txt` de cada etapa dé `b3606f03…` (etapa 1) y `6692fbea…` (etapa 2) y que sus archivos le den igual.
- Cada ficha lleva un renglón nuevo, el primero después de su encabezado: `- número que le asignó la segmentación: <n>`
  o `- número que le asignó la segmentación: sin número`. Nada más cambia en el texto.
- El número sale del campo `unidad` del chunk de E0 de la unidad que se califica (etapa 1: la de la ficha; etapa 2: la
  primera de `unidades_calificadas`): el último segmento de `unidad`, separado por «::», que cumpla
  `re.fullmatch(r"(?:[A-Z]\\.)?\\d+(?:\\.\\d+)*|[A-Z](?:\\.\\d+)+", segmento)`; si ninguno la cumple, «sin número».
- Etapa 2: cada página de la unidad que sigue tiene su imagen (`<id opaco>_p<N>.png`), con el comando de las demás
  (`pdftoppm -r 110 -png -f p -l p -singlefile`); se agregan solo las que faltan.
- El `manifest.txt` de cada etapa se rehace con el formato de `fichas_S1ter.py`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

RX_NUMERO = re.compile(r"(?:[A-Z]\.)?\d+(?:\.\d+)*|[A-Z](?:\.\d+)+")
RE_PARTE = re.compile(r"^(.*)::parte(\d+)$")
RENGLON = "- número que le asignó la segmentación: "
MANIFEST_ANTES = {"etapa_1": "b3606f0365f4a5595efc0d59f471024270d8d21d83a150d0e1d971c20d0249fa",
                  "etapa_2": "6692fbeab5078e14c6d30760f58faeddfcd30cce94294559f5e893425f3e8c78"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def numero(unidad: str) -> str:
    seg = [s for s in unidad.split("::") if RX_NUMERO.fullmatch(s)]
    return seg[-1] if seg else "sin número"


def verificar_manifest(d: Path) -> dict[str, str]:
    filas = [l for l in (d / "manifest.txt").read_text(encoding="utf-8").splitlines()[2:] if l.strip()]
    lista = {}
    for l in filas:
        s, nb, resto = l.split("  ", 2)
        n = resto.split(" — ", 1)[0]
        assert (d / n).is_file() and sha(d / n) == s and (d / n).stat().st_size == int(nb), f"{d.name}/{n} distinto"
        lista[n] = s
    return lista


def escribir_manifest(d: Path, n_fichas: int, etapa: int) -> None:
    archivos = sorted(p for p in d.iterdir() if p.is_file() and p.name not in ("manifest.txt", ".DS_Store"))
    lineas = [f"Carpeta de la lectora, etapa {etapa}: {len(archivos)} archivos (más este manifest)",
              "sha256  bytes  archivo — descripción"]
    for p in archivos:
        desc = (f"las {n_fichas} fichas de la etapa {etapa}" if p.suffix == ".md" else
                f"imagen de la página {p.stem.split('_p')[1]} del PDF, ficha {p.stem.split('_p')[0]}")
        lineas.append(f"{sha(p)}  {p.stat().st_size}  {p.name} — {desc}")
    (d / "manifest.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("orden", "sha_orden", "e0", "pdfs", "carpeta", "registro"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    raw = Path(a.orden).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.sha_orden, "el orden no da su sha256 sellado"
    orden = json.loads(raw)
    e0, pdfs, carpeta = Path(a.e0), Path(a.pdfs), Path(a.carpeta)
    cache: dict[str, list] = {}

    def chunks(to: str) -> list:
        if to not in cache:
            cache[to] = json.loads((e0 / f"chunks_{to}.json").read_text(encoding="utf-8"))
        return cache[to]

    def por_id(uid: str) -> dict:
        return next(c for c in chunks(uid.split("::")[0]) if c["id"] == uid)

    def siguiente(uid: str) -> dict | None:
        L = chunks(uid.split("::")[0])
        ids = [c["id"] for c in L]
        partes = [i for i in ids if i == uid or (RE_PARTE.match(i) and RE_PARTE.match(i).group(1) == uid)]
        k = max(ids.index(i) for i in partes)
        return L[k + 1] if k + 1 < len(L) else None

    registro: dict = {"regla_del_numero": RX_NUMERO.pattern, "renglon": RENGLON, "etapas": {}}
    for etapa in (1, 2):
        nombre = f"etapa_{etapa}"
        d = carpeta / nombre
        assert sha(d / "manifest.txt") == MANIFEST_ANTES[nombre], f"{nombre}: el manifest.txt de partida no es el sellado"
        antes = verificar_manifest(d)
        fichas = orden[nombre]["fichas"]
        num = {}
        for f in fichas:
            uid = f["id"] if etapa == 1 else f["unidades_calificadas"][0]
            num[f["id_opaco"]] = numero(por_id(uid)["unidad"])
        fp = d / f"fichas_{nombre}.md"
        lineas = fp.read_text(encoding="utf-8").split("\n")
        out, k = [], 0
        while k < len(lineas):
            ln = lineas[k]
            out.append(ln)
            if ln.startswith("## E"):
                op = ln[3:].strip()
                assert lineas[k + 1] == "" and lineas[k + 2].startswith("- "), f"{op}: forma inesperada"
                out += ["", RENGLON + num[op]]
                k += 2
                continue
            k += 1
        assert sum(1 for x in out if x.startswith(RENGLON)) == len(fichas)
        fp.write_text("\n".join(out), encoding="utf-8")
        agregadas, paginas_sigue, con_imagen = [], 0, 0
        if etapa == 2:
            for f in fichas:
                sig = siguiente(f["id"])
                if sig is None:
                    continue
                to = f["id"].split("::")[0]
                for p in sig["paginas"]:
                    paginas_sigue += 1
                    img = d / f"{f['id_opaco']}_p{p}.png"
                    if not img.exists():
                        subprocess.run(["pdftoppm", "-r", "110", "-png", "-f", str(p), "-l", str(p), "-singlefile",
                                        str(pdfs / f"{to}.pdf"), str(img.with_suffix(""))], check=True,
                                       capture_output=True)
                        agregadas.append(img.name)
                    con_imagen += img.exists()
        escribir_manifest(d, len(fichas), etapa)
        despues = verificar_manifest(d)
        registro["etapas"][nombre] = {
            "fichas": len(fichas),
            "con_numero": sum(1 for v in num.values() if v != "sin número"),
            "sin_numero": sum(1 for v in num.values() if v == "sin número"),
            "imagenes_agregadas": sorted(agregadas),
            "paginas_de_la_unidad_que_sigue": paginas_sigue if etapa == 2 else None,
            "con_imagen": con_imagen if etapa == 2 else None,
            "archivos_antes": len(antes), "archivos_despues": len(despues),
            "nuevos": sorted(set(despues) - set(antes)),
            "cambiados": sorted(n for n in set(antes) & set(despues) if antes[n] != despues[n]),
            "quitados": sorted(set(antes) - set(despues)),
            "manifest_antes": MANIFEST_ANTES[nombre], "manifest_despues": sha(d / "manifest.txt"),
            "numero_por_ficha": num}
    Path(a.registro).write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {kk: (vv if kk != "numero_por_ficha" else len(vv)) for kk, vv in v.items()}
                      for k, v in registro["etapas"].items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
