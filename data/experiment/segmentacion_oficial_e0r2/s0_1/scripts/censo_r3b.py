"""Regla 3b de S0-1 (solo lectura): páginas de ri_cc y ri_tsa anteriores a su primer índice, que e0-r2 lee como
portada y deja fuera de toda unidad. Por sub-documento («N – TÍTULO» en la zona de título), con páginas, renglones
de contenido (sin encabezado ni pie, criterio de e0-r2), caracteres y renglones de prosa (55 o más caracteres, sin
huecos de columna)."""
import json, re, sys
from collections import OrderedDict
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_s01 as C
raiz, cache, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
CE, E0 = C.cargar_codigo(raiz)
RE_SUB = re.compile(r"^(\d{1,2})\s*[-–]\s+([A-ZÁÉÍÓÚÑ].*)$")
out = OrderedDict()
for to in ("ri_cc", "ri_tsa"):
    ps = C.paginas_de(cache, to, E0)
    res, roles, modo, _ = C.parsear(CE, E0, to, ps)
    primer = roles.index(E0.ROL_INDICE) + 1
    rep = E0.titulos_mayusculas_repetidos(ps, [E0.ROL_CUERPO] * len(ps))
    subs = OrderedDict()
    actual = "caratula"
    for pi in range(1, primer):
        ls = ps[pi - 1]
        for l in ls[:5]:
            m = RE_SUB.match(l.texto.strip())
            if m:
                actual = f"{m.group(1)} – {m.group(2)[:60]}"
                break
        cont, _, _ = E0.separar_encabezado_pie(ls, mayusculas_repetidas=rep, pie_desde_version=True)
        d = subs.setdefault(actual, {"paginas": [], "renglones": 0, "caracteres": 0, "renglones_prosa": 0,
                                     "renglones_con_huecos": 0})
        d["paginas"].append(pi)
        d["renglones"] += len(cont)
        d["caracteres"] += sum(len(l.texto) for l in cont)
        d["renglones_prosa"] += sum(1 for l in cont if l.ngaps == 0 and len(l.texto) >= 55)
        d["renglones_con_huecos"] += sum(1 for l in cont if l.ngaps >= 1)
    for d in subs.values():
        d["rango"] = f"{d['paginas'][0]}-{d['paginas'][-1]}"
        d["n_paginas"] = len(d.pop("paginas"))
    out[to] = OrderedDict([("modo_lectura", modo), ("paginas_del_to", len(ps)), ("primer_indice", primer),
                           ("roles_antes_del_indice", sorted(set(roles[:primer - 1]))),
                           ("paginas_fuera", primer - 1),
                           ("caracteres_fuera", sum(d["caracteres"] for d in subs.values())),
                           ("subdocumentos", subs)])
Path(sal).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for to, v in out.items():
    print(to, v["paginas_fuera"], "páginas,", v["caracteres_fuera"], "caracteres")
    for k, d in v["subdocumentos"].items():
        print("   ", k[:55], d["rango"], d["n_paginas"], "pág", d["caracteres"], "car", d["renglones_prosa"], "prosa", d["renglones_con_huecos"], "huecos")
