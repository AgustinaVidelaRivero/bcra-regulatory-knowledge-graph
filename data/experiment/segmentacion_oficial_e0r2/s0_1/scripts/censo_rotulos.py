"""U-SEG-OFICIAL, S0-1, regla 2 — censo de rótulos de punto aceptados por e0-r2 que pueden no serlo, sobre los 152 TOs
(USD 0, sin API). Solo lectura.

Clases de candidato (cada punto aceptado puede caer en más de una):
  remision    el resto del rótulo empieza en minúscula con la forma de una remisión envuelta: «y N.», «a N.»,
              «al N.», «de las normas», «de la Sección», «del presente», «de este», «inclusive»…
  minuscula   el resto empieza en minúscula (todos, para leer: ext tiene rótulos reales en minúscula)
  miles       el número tiene un componente de tres dígitos o más (21.526: número de ley)
  fila_tabla  la línea del rótulo tiene dos o más fronteras de columna (ngaps ≥ 2)
  raiz_sin_punto  en el modo sin raíz, el rótulo abre una raíz implícita sin punto final («10.1 Producción…»)
Uso: python -B censo_rotulos.py <raíz de la copia> <caché de líneas> <salida.json>
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_s01 as C  # noqa: E402

RE_REMISION = re.compile(r"^(y|e|o|u|a|al|hasta|inclusive|de\s+(las?|los)\s+normas|de\s+la\s+(presente|secci)|"
                         r"del?\s+(presente|este|esta|anexo|cap[ií]tulo|punto|art[ií]culo|texto)|de\s+(esta|este)\b|"
                         r"de\s+las?\s+(Secci|secci)|y\s+\d|a\s+\d|en\s+(el|la)\s+(punto|secci))", re.I)


def main() -> None:
    raiz, cache, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    CE, E0 = C.cargar_codigo(raiz)
    filas = []
    for to in C.tos_particion(raiz):
        paginas = C.paginas_de(cache, to, E0)
        res, roles, modo, _ = C.parsear(CE, E0, to, paginas)
        for n in C.nodos(res):
            if n.tipo != "punto" or n.linea_label is None:
                continue
            l = n.linea_label
            tok = l.texto.split()[0]
            resto = l.texto[len(tok):].strip()
            clases = []
            if resto[:1].islower():
                clases.append("minuscula")
                if RE_REMISION.match(resto):
                    clases.append("remision")
            if any(len(x) >= 3 for x in n.numero.split(".")):
                clases.append("miles")
            if l.ngaps >= 2:
                clases.append("fila_tabla")
            if modo == "sin_raiz" and n.padre is not None and n.padre.tipo == "seccion" and n.padre.sintetica \
                    and n.padre.linea_label is None and not tok.endswith("."):
                clases.append("raiz_sin_punto")
            if clases:
                filas.append(OrderedDict([("to", to), ("modo", modo), ("numero", n.numero), ("pagina", l.pagina),
                                          ("x0", l.x0), ("ngaps", l.ngaps), ("hijos", len(n.hijos)),
                                          ("clases", clases), ("linea", l.texto[:140])]))
    por_clase = Counter(c for f in filas for c in f["clases"])
    out = OrderedDict([("resumen", OrderedDict([
        ("candidatos", len(filas)), ("por_clase", dict(sorted(por_clase.items()))),
        ("tos_por_clase", {k: sorted({f["to"] for f in filas if k in f["clases"]}) for k in sorted(por_clase)})])),
        ("filas", filas)])
    sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["resumen"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
