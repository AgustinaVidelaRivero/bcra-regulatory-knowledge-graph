"""U-SEG-OFICIAL, S1-ter-b: control a ciegas de la carpeta de la lectora (USD 0).

Uso: python -B control_ciego_fichas_S1ter.py <carpeta de la lectora> <manifiesto de S1-ter> <orden de lectura sellado>

Fuera de los bloques de texto de la norma (y de los textos heredados, entre comillas latinas), cuenta los renglones con
vocabulario de población, regla, tanda o límite declarado, y los que nombran un TO; en todo el archivo, «::» y los ids
de unidad del orden sellado; en la carpeta, los archivos que no son ficha, imagen ni manifest, y las imágenes con otro
nombre que `<id opaco>_p<N>.png`.
"""
import json, re, sys
from pathlib import Path
L = Path(sys.argv[1]); tos = [t["id"] for t in json.load(open(sys.argv[2]))["tos"]]
o = json.load(open(sys.argv[3]))
PAL = re.compile(r"poblaci|estrato|regla|tanda|l[ií]mite|cierre|R5|semilla|regresi|candidat|\bcaso|1\.16|S1-ter|S0-5|mixto|"
                 r"declarad|vigente|marcadores|sin_raiz|ri_|::", re.I)
RE_IMG = re.compile(r"E[12]-\d{3}_p\d+\.png")
print("# control a ciegas de la carpeta de la lectora")
for etapa in ("etapa_1", "etapa_2"):
    d = L / etapa
    t = (d / f"fichas_{etapa}.md").read_text(encoding="utf-8")
    fuera, dentro = [], False
    for ln in t.split("\n"):
        if ln.startswith("```"):
            dentro = not dentro
            continue
        if not dentro:
            fuera.append(re.sub(r"«.*»", "«…»", ln))
    hits = [ln for ln in fuera if PAL.search(ln)]
    tohits = [ln for ln in fuera for to in tos if re.search(r"\b" + re.escape(to) + r"\b", ln)]
    ids = [f["id"] for f in o[etapa]["fichas"]]
    idhits = [i for i in ids if i in t]
    n_fichas = sum(1 for ln in t.split("\n") if ln.startswith("## "))
    otros = [p.name for p in d.iterdir() if not (p.name.startswith("fichas_") or p.suffix == ".png" or p.name == "manifest.txt")]
    malos = [p.name for p in d.glob("*.png") if not RE_IMG.fullmatch(p.name)]
    print(f"{etapa}: {n_fichas} fichas; renglones fuera del texto de la norma: {len(fuera)}; con vocabulario de población, "
          f"regla, tanda o límite: {len(hits)}; con un id de TO: {len(tohits)}; «::» en todo el archivo: {t.count('::')}; "
          f"ids de unidad que aparecen: {len(idhits)}")
    print(f"{etapa}: archivos: {len(list(d.iterdir()))}; que no son ficha, imagen ni manifest: {otros}; imágenes con otro "
          f"nombre que <id opaco>_p<N>.png: {malos}")
    for h in (hits + tohits)[:5]:
        print("   ", h)
