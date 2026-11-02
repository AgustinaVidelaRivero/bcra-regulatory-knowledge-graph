"""U-SEG-OFICIAL, S1-ter-b2: controles de las fichas con el número (USD 0).

Uso: python -B controles_fichas_numero_S1ter.py --antes <carpeta como la dejó S1-ter-b> --despues <carpeta nueva>
       --orden <tramo_b/orden_lectura_S1ter.json> --registro <tramo_b2/fichas_numero_registro_S1ter.json> --e0 <s1ter/e0>

Puntos 4 a 6 de las decisiones de la autora sobre el FRENO S1-ter-b:
- sin los renglones `- número que le asignó la segmentación: …`, cada archivo de fichas nuevo es, byte a byte, el de antes
  (el que listan los `manifest.txt` `b3606f03…` y `6692fbea…`);
- archivos de cada etapa: nuevos, cambiados y quitados contra el `manifest.txt` de antes (en la etapa 2, los únicos nuevos son
  las 8 imágenes; las 171 de antes, iguales);
- los conteos: 90 renglones (78 con número y 12 sin número) y 101 (96 y 5);
- en la etapa 1, la ficha que es una parte partida por tamaño y las introducciones y cierres muestran el número de su punto;
  en la etapa 2, la ficha cuya unidad está partida muestra el número del punto partido. Salida sin ids de unidad.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

RENGLON = "- número que le asignó la segmentación: "
RX = re.compile(r"(?:[A-Z]\.)?\d+(?:\.\d+)*|[A-Z](?:\.\d+)+")
ESPERADO = {"etapa_1": (90, 78, 12), "etapa_2": (101, 96, 5)}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest(d: Path) -> dict[str, str]:
    out = {}
    for l in (d / "manifest.txt").read_text(encoding="utf-8").splitlines()[2:]:
        if l.strip():
            s, _, resto = l.split("  ", 2)
            out[resto.split(" — ", 1)[0]] = s
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("antes", "despues", "orden", "registro", "e0"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    orden = json.loads(a.orden.read_text(encoding="utf-8"))
    reg = json.loads(a.registro.read_text(encoding="utf-8"))
    ok = True
    print("# controles de las fichas con el número (S1-ter-b2)")
    for etapa in ("etapa_1", "etapa_2"):
        ma, md = manifest(a.antes / etapa), manifest(a.despues / etapa)
        f_antes = a.antes / etapa / f"fichas_{etapa}.md"
        f_nuevo = a.despues / etapa / f"fichas_{etapa}.md"
        assert sha(f_antes) == ma[f"fichas_{etapa}.md"], "el archivo de antes no es el del manifest.txt sellado"
        nuevo = f_nuevo.read_text(encoding="utf-8").split("\n")
        quitado = "\n".join(x for x in nuevo if not x.startswith(RENGLON)).encode("utf-8")
        igual = quitado == f_antes.read_bytes()
        renglones = [x[len(RENGLON):] for x in nuevo if x.startswith(RENGLON)]
        n, con, sin = len(renglones), sum(1 for x in renglones if x != "sin número"), renglones.count("sin número")
        # el renglón nuevo es el primero después de cada encabezado
        primero = all(nuevo[i + 2].startswith(RENGLON) for i, x in enumerate(nuevo) if x.startswith("## E"))
        nuevos = sorted(set(md) - set(ma))
        cambiados = sorted(x for x in set(ma) & set(md) if ma[x] != md[x])
        quitados = sorted(set(ma) - set(md))
        imagenes_iguales = sum(1 for x in ma if x.endswith(".png") and md.get(x) == ma[x])
        imagenes_antes = sum(1 for x in ma if x.endswith(".png"))
        print(f"{etapa}: sin los renglones nuevos, el archivo de fichas es byte a byte el de antes: {'sí' if igual else 'NO'}")
        print(f"{etapa}: renglones nuevos {n} (con número {con}, sin número {sin}); esperado {ESPERADO[etapa]}; "
              f"el renglón es el primero después de cada encabezado: {'sí' if primero else 'NO'}")
        print(f"{etapa}: archivos nuevos {len(nuevos)} {nuevos}; cambiados {cambiados}; quitados {quitados}; imágenes de "
              f"antes iguales {imagenes_iguales} de {imagenes_antes}")
        ok &= igual and primero and (n, con, sin) == ESPERADO[etapa] and not quitados and cambiados == [f"fichas_{etapa}.md"]
        ok &= imagenes_iguales == imagenes_antes
    # casos del punto 4
    num1, num2 = reg["etapas"]["etapa_1"]["numero_por_ficha"], reg["etapas"]["etapa_2"]["numero_por_ficha"]

    def punto(uid: str) -> str | None:
        base = re.sub(r"::(parte\d+|intro|cierre)$", "", uid)
        seg = [s for s in base.split("::")[1:] if RX.fullmatch(s)]
        return seg[-1] if seg else None
    partes1 = [f for f in orden["etapa_1"]["fichas"] if re.search(r"::parte\d+$", f["id"])]
    ic1 = [f for f in orden["etapa_1"]["fichas"] if re.search(r"::(intro|cierre)$", f["id"])]
    partes2 = [f for f in orden["etapa_2"]["fichas"] if re.search(r"::parte\d+$", f["unidades_calificadas"][0])]
    bien = lambda fs, num, key: sum(1 for f in fs if punto(key(f)) is not None and num[f["id_opaco"]] == punto(key(f)))
    b1p, b1i = bien(partes1, num1, lambda f: f["id"]), bien(ic1, num1, lambda f: f["id"])
    b2p = bien(partes2, num2, lambda f: f["unidades_calificadas"][0])
    print(f"etapa_1: fichas que son una parte partida por tamaño {len(partes1)}, con el número de su punto {b1p}")
    print(f"etapa_1: introducciones o cierres {len(ic1)}, con el número de su punto {b1i}")
    print(f"etapa_2: fichas cuya unidad está partida por tamaño {len(partes2)}, con el número del punto partido {b2p}")
    ok &= (len(partes1), b1p, len(ic1), b1i, len(partes2), b2p) == (1, 1, 8, 8, 1, 1)
    sigue = reg["etapas"]["etapa_2"]
    print(f"etapa_2: páginas de la unidad que sigue con su imagen: {sigue['con_imagen']} de {sigue['paginas_de_la_unidad_que_sigue']}")
    ok &= sigue["con_imagen"] == sigue["paginas_de_la_unidad_que_sigue"] == 104
    print("TODO BIEN" if ok else "HAY DIFERENCIAS")


if __name__ == "__main__":
    main()
