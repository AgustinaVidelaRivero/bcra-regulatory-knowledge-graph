import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
raiz = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(raiz / "data/experiment/reextraccion_v2/e0_chunking"))
import e0_lib as E0
cache = {}
for f in sys.argv[2:]:
    for x in json.load(open(f)):
        if x["dtop"] > 16:
            continue
        to = x["to"]
        if to not in cache:
            p = raiz / "data/experiment/escalado_prep/pdfs" / f"{to}.pdf"
            if not p.exists():
                p = next((raiz / "data/experiment/subset").glob(f"*{dict(cap='capitales',cla='clasificacion',ext='exterior',pro='proteccion',ric='regimen')[to]}*"))
            cache[to] = E0.extraer_lineas(p)
        ls = cache[to][x["pagina"] - 1]
        i = next(k for k, l in enumerate(ls) if l.texto[:80] == x["renglon"] and abs(l.x0 - x["x0"]) < 0.2)
        sig = ls[i + 1] if i + 1 < len(ls) else None
        print("%-9s p.%-4d x0=%6.1f sig_x0=%6.1f sig_dtop=%5.1f mismo_x0=%s | %s || %s" % (to, x["pagina"], x["x0"], sig.x0, sig.top - ls[i].top, abs(sig.x0 - x["x0"]) <= 3, x["renglon"][:40], sig.texto[:40]))
