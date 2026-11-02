"""S0-2 de U-SEG-OFICIAL, decisión 8: censo de las páginas que cambian de rol con la ampliación de la regla 3 (página
de cuerpo que es entera una lista de la regla 8), sobre los 152 TOs (PDFs de escalado_prep) y los diez de la tanda 0.
Corre la escalera de e0-r2 del prototipo con interruptores (`proto9`) dos veces por TO: sin la ampliación (`r3i`
apagada, el estado de S0-1 bis) y con ella, y compara los roles de página. Por cada página con una lista de la regla
8 y por cada página que cambia de rol, da el rol antes y después, el modo de lectura y los renglones de contenido.
Controla ceninf p. 1 (la página anterior a una de índice nueva no se vuelve portada). Solo lectura.

Uso: python -B censo_rol_indice.py <raíz de la copia con proto9> <salida.json> [--workers N]"""
import json
import sys
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
RAIZ = Path(sys.argv[1])


def uno(args):
    to, pdf = args
    sys.path.insert(0, str(RAIZ / "data/experiment/reextraccion_v2/e0_chunking"))
    import correr_e0 as CE
    import e0_lib as E0
    paginas = E0.extraer_lineas(pdf)
    todas = CE.REGLAS_S0_E0_R2
    out = {}
    for nombre, reglas in (("antes", todas - {"r3i"}), ("despues", todas | {"r3i"})):
        CE.REGLAS_S0_E0_R2 = reglas
        roles0 = E0.clasificar_paginas(paginas, continuacion_con_titulo=True)
        res, roles, _rep, modo, _m = CE.escalera_e0_r2(to, f"{to}.pdf", paginas, roles0)
        out[nombre] = {"roles": roles, "modo": modo, "lineas_contenido": res.lineas_contenido}
    CE.REGLAS_S0_E0_R2 = todas
    renglones = []
    roles_a = out["antes"]["roles"]
    E0.lineas_de_listas_r8(paginas, roles_a, renglones=renglones)
    paginas_lista = sorted({p for r in renglones for p, _t in r})
    rep = E0.titulos_mayusculas_repetidos(paginas, roles_a)
    filas = []
    for p in sorted(set(paginas_lista) | {i + 1 for i, (a, b) in enumerate(zip(roles_a, out["despues"]["roles"]))
                                            if a != b}):
        cont, _d, _s = E0.separar_encabezado_pie(paginas[p - 1], mayusculas_repetidas=rep, pie_desde_version=True,
                                                 seccion_variante=True)
        filas.append({"pagina": p, "con_lista_r8": p in paginas_lista, "rol_antes": roles_a[p - 1],
                      "rol_despues": out["despues"]["roles"][p - 1], "renglones_de_contenido": len(cont)})
    return to, {"modo_antes": out["antes"]["modo"], "modo_despues": out["despues"]["modo"],
                "lineas_contenido": [out["antes"]["lineas_contenido"], out["despues"]["lineas_contenido"]],
                "roles_iguales_fuera_de_la_lista": all(a == b for i, (a, b) in enumerate(
                    zip(roles_a, out["despues"]["roles"])) if i + 1 not in paginas_lista),
                "paginas": filas,
                "pagina_1": [roles_a[0], out["despues"]["roles"][0]]}


def main():
    sal = Path(sys.argv[2])
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    c = json.loads((RAIZ / "data/experiment/segmentacion_84/b584_particion/conteos_b584.json").read_text())
    pdfs = RAIZ / "data/experiment/escalado_prep/pdfs"
    trabajos = [(t, pdfs / f"{t}.pdf") for t in sorted(t for t, v in c.items() if isinstance(v, dict))]
    man = json.loads((RAIZ / "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos.json").read_text())
    trabajos += [(t["id"], RAIZ / t["pdf"]) for t in man["tos"]]
    with ProcessPoolExecutor(w) as ex:
        res = list(ex.map(uno, trabajos))
    por_to = OrderedDict((t, r) for t, r in res if r["paginas"])
    cambian = [(t, f["pagina"], f["rol_antes"], f["rol_despues"]) for t, r in por_to.items() for f in r["paginas"]
               if f["rol_antes"] != f["rol_despues"]]
    out = OrderedDict([
        ("tos_revisados", len(trabajos)),
        ("paginas_que_cambian_de_rol", [{"to": t, "pagina": p, "antes": a, "despues": d} for t, p, a, d in cambian]),
        ("renglones_que_pasan_al_rol", {t: r["lineas_contenido"][0] - r["lineas_contenido"][1] for t, r in por_to.items()
                                        if r["lineas_contenido"][0] != r["lineas_contenido"][1]}),
        ("paginas_con_lista_que_no_cambian", [{"to": t, "pagina": f["pagina"], "rol": f["rol_antes"]}
                                              for t, r in por_to.items() for f in r["paginas"]
                                              if f["con_lista_r8"] and f["rol_antes"] == f["rol_despues"]]),
        ("tos_con_otro_rol_cambiado", [t for t, r in res if not r["roles_iguales_fuera_de_la_lista"]]),
        ("tos_con_otro_modo", [t for t, r in res if r["modo_antes"] != r["modo_despues"]]),
        ("ceninf_pagina_1", dict(res)["ceninf"]["pagina_1"]),
        ("por_to", por_to)])
    sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "por_to"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
