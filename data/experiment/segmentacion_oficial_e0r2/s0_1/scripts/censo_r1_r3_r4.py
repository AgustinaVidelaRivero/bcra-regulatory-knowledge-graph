"""Censos de solo lectura de S0-1 sobre los 152 TOs (líneas cacheadas, escalera de e0-r2 con el código de la copia).
R1  líneas de la zona de encabezado (5 primeras) de páginas de cuerpo con forma de sección que RE_SECCION no lee.
R3a páginas de índice por continuación (sin marcador) y sus líneas 'Sección N.' con título vacío o en minúscula.
R3b páginas fuera del parseo (portada o índice) con prosa: 3 o más líneas de 55 caracteres o más sin huecos.
R4  líneas 'APARTADO X' (sin guion delante) y rótulos de letra y número ('A.1.') por TO.
"""
import json, re, sys
from collections import Counter, OrderedDict
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_s01 as C
raiz, cache, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
CE, E0 = C.cargar_codigo(raiz)
RE_VAR = re.compile(r"^\W{0,2}Secc?i?[oó]n\s*\d+", re.I)
RE_APARTADO = re.compile(r"^APARTADO\s+[A-Z]\b")
RE_LETRA = re.compile(r"^[A-Z]\.\d+(\.\d+)*\.?\s")
r1, r3a, r3b, r4 = [], [], [], OrderedDict()
for to in C.tos_particion(raiz):
    paginas = C.paginas_de(cache, to, E0)
    roles0 = E0.clasificar_paginas(paginas)
    res, roles, modo, marc = C.parsear(CE, E0, to, paginas)
    for pi, (ls, rol) in enumerate(zip(paginas, roles), 1):
        if rol == E0.ROL_CUERPO:
            for l in ls[:5]:
                t = l.texto.strip()
                if RE_VAR.match(t) and not E0.RE_SECCION.match(t) and not ("B.C.R.A." in t and E0.RE_SECCION_EN_LINEA.search(t)):
                    r1.append({"to": to, "modo": modo, "pagina": pi, "linea": t[:100]})
        # R3a: páginas índice que no tienen marcador (continuación) en los roles iniciales
        if roles0[pi - 1] == E0.ROL_INDICE:
            textos = [l.texto.strip() for l in ls]
            con_marca = any(E0.RE_MARCA_INDICE.match(t) for t in textos) or any(
                E0.RE_MARCA_INDICE_SIN_GUIONES.match(t) for t in textos[:E0.POS_MARCA_INDICE])
            if not con_marca:
                secs = [t for t in textos if E0.RE_SECCION.match(t)]
                malas = [t for t in secs if not E0.RE_SECCION.match(t).group(2).strip()[:1].isupper()]
                r3a.append({"to": to, "modo": modo, "pagina": pi, "rol_final": rol, "n_secc": len(secs),
                            "n_secc_con_titulo": len(secs) - len(malas), "sin_titulo_o_minuscula": malas[:4],
                            "primeras": textos[:4]})
        if rol in (E0.ROL_PORTADA, E0.ROL_INDICE):
            prosa = [l for l in ls if l.ngaps == 0 and len(l.texto) >= 55]
            if len(prosa) >= 3:
                r3b.append({"to": to, "modo": modo, "pagina": pi, "rol": rol, "lineas_prosa": len(prosa),
                            "lineas": len(ls), "primera_prosa": prosa[0].texto[:90]})
    ap = [l.texto[:60] for ls in paginas for l in ls if RE_APARTADO.match(l.texto.strip())]
    le = [l.texto[:40] for ls in paginas for l in ls if RE_LETRA.match(l.texto.strip())]
    if ap or len(le) >= 3:
        r4[to] = {"modo": modo, "apartado": len(ap), "rotulos_letra": len(le), "ej_apartado": ap[:4], "ej_letra": le[:4]}
out = OrderedDict([
    ("r1", {"lineas": len(r1), "por_to": dict(Counter(f["to"] for f in r1)), "filas": r1}),
    ("r3a", {"paginas": len(r3a), "por_to": dict(Counter(f["to"] for f in r3a)), "filas": r3a}),
    ("r3b", {"paginas": len(r3b), "por_to": dict(Counter(f["to"] for f in r3b)),
             "por_to_rol": dict(Counter(f"{f['to']}:{f['rol']}" for f in r3b)), "filas": r3b}),
    ("r4", r4)])
Path(sal).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for k in ("r1", "r3a", "r3b"):
    print(k, json.dumps({kk: v for kk, v in out[k].items() if kk != "filas"}, ensure_ascii=False))
print("r4", json.dumps({t: {k: v for k, v in d.items() if not k.startswith("ej")} for t, d in r4.items()}, ensure_ascii=False))
