"""U-SEG-OFICIAL, S1-bis-b: prueba de `cifras_lectura_S1bis.py` y `lista_para_la_autora_S1bis.py` con datos sintéticos
(USD 0). No usa la muestra real: arma una muestra y unas planillas con ids inventados, de la misma forma.

Uso: python -B prueba_cifras_S1bis.py

Casos: el primer grupo con 0, 3 y 4 errores de corte (la nota de `2faff14`: con 90, pasa con 3, 0,907, y no con 4, 0,891),
una dudosa contada de las dos maneras, un error de limpieza, un límite declarado sintético en la muestra, `ri2_ae` sin contar
como error, el censo del 1.16 y la lista para la autora (20 correctas y 5 del 1.16, reproducibles).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cifras_lectura_S1bis as C  # noqa: E402
import lista_para_la_autora_S1bis as L  # noqa: E402

PESOS = {"vigente": 8034 / 9446, "marcadores": 190 / 9446, "sin_raiz": 1222 / 9446}
N = {"vigente": 40, "marcadores": 10, "sin_raiz": 40}


def muestra_sintetica() -> dict:
    est = {e: {"peso": PESOS[e], "leidas": n,
               "muestra": [{"id": f"tx{e}::{i}", "to": f"tx{e}", "grupo": f"G1-{e}"} for i in range(n)]}
           for e, n in N.items()}
    est["sin_raiz"]["muestra"][0]["id"] = "ri2_ae::3.3"
    est["sin_raiz"]["muestra"][1]["id"] = "nmaeef::2.9"
    return {"primer_grupo": {"estratos": est},
            "ri_spi": {"muestra": [{"id": f"ri_spi::X.{i}", "to": "ri_spi", "grupo": "ri_spi"} for i in range(10)]},
            "tercer_grupo": {"juicios": 11}, "censo_1_16_tanda1": {"candidatos": 35}}


def planillas(m: dict, errores: int, dudosa: bool = False):
    filas, k = [], 0
    for e, g in m["primer_grupo"]["estratos"].items():
        for u in g["muestra"]:
            k += 1
            filas.append({"fila": str(k), "grupo": u["grupo"], "id": u["id"], "to": u["id"].split("::")[0], "paginas": "1",
                          "marca": "correcta", "clase": "", "subclase": "", "subclase_adicional": "", "limpieza": "",
                          "nota": ""})
    for i in range(errores):
        filas[i].update(marca="error", clase="corte", subclase="trae_texto_de_otro_punto")
    if dudosa:
        filas[10]["marca"] = "dudosa"
    filas[20]["limpieza"] = "restos_pie"
    for u in m["ri_spi"]["muestra"]:
        k += 1
        filas.append({"fila": str(k), "grupo": "ri_spi", "id": u["id"], "to": "ri_spi", "paginas": "1", "marca": "correcta",
                      "clase": "", "subclase": "", "subclase_adicional": "", "limpieza": "", "nota": ""})
    for j in range(11):
        k += 1
        filas.append({"fila": str(k), "grupo": "G3-juicio", "id": "(juicio del documento)", "to": f"ns{j}", "paginas": "1",
                      "marca": "correcta" if j != 9 else "limite_declarado", "clase": "", "subclase": "",
                      "subclase_adicional": "", "limpieza": "", "nota": ""})
    p116 = [{"fila": str(i + 1), "grupo": "C116-tanda1", "id": f"c116::{i}", "to": "c116", "paginas": "1",
             "marca": "error" if i < 7 else "correcta", "clase": "corte" if i < 7 else "",
             "subclase": "trae_texto_de_otro_punto" if i < 7 else "", "subclase_adicional": "", "limpieza": "",
             "nota": ""} for i in range(35)]
    return filas, p116


def main() -> None:
    m = muestra_sintetica()
    casos = {}
    for errores in (0, 3, 4):
        f, p116 = planillas(m, errores)
        r = C.calcular(m, f, p116, {"tx_vigente::0"}, set())
        casos[errores] = r["cifra_del_piso"]["dudosas_como_correctas"]
        assert r["planillas_validas"]
    assert casos[0]["llega_al_piso"] and casos[3]["llega_al_piso"] and not casos[4]["llega_al_piso"]
    assert round(casos[3]["wilson95"][0], 4) == 0.9065 and round(casos[4]["wilson95"][0], 4) == 0.8912
    f, p116 = planillas(m, 3, dudosa=True)
    r = C.calcular(m, f, p116, set(), set())
    assert r["cifra_del_piso"]["dudosas_como_correctas"]["errores_de_corte"] == 3
    assert r["cifra_del_piso"]["dudosas_como_error"]["errores_de_corte"] == 4
    assert r["limpieza_por_grupo"]["primer_grupo"] == 1
    # el error 0 y el 1 caen en el sin_raiz sintético: ri2_ae::3.3 (conocido) y nmaeef::2.9 (límite de corte)
    f, p116 = planillas(m, 0)
    f[50].update(marca="error", clase="corte", subclase="termina_fuera")   # ri2_ae::3.3
    f[51].update(marca="error", clase="corte", subclase="falta_texto_propio")  # nmaeef::2.9
    r = C.calcular(m, f, p116, set(), set())
    assert {x["id"] for x in r["limites_declarados_en_la_muestra"]} == {"ri2_ae::3.3", "nmaeef::2.9"}
    assert r["cifra_del_piso"]["dudosas_como_correctas"]["errores_de_corte"] == 2
    assert r["cifra_del_piso_sin_contar_ri2_ae_como_error"]["dudosas_como_correctas"]["errores_de_corte"] == 1
    assert r["censo_1_16_tanda1"]["con_error_de_corte"] == 7
    malo = [dict(x) for x in f]
    malo[0]["marca"] = "erro"
    assert not C.calcular(m, malo, p116, set(), set())["planillas_validas"]
    l1, l2 = L.lista(m, f, p116), L.lista(m, f, p116)
    assert l1 == l2 and len(l1["correctas_sorteadas"]["ids"]) == 20
    assert len(l1["censo_1_16"]["correctos_sorteados"]["ids"]) == 5 and len(l1["censo_1_16"]["marcados_y_dudosos"]) == 7
    print("prueba de cifras y lista: OK;", {k: round(v["wilson95"][0], 4) for k, v in casos.items()},
          "corpus con 3 errores:", round(C.calcular(m, *planillas(m, 3), set(), set())["cifra_del_corpus"]["n_efectivo"], 3))


if __name__ == "__main__":
    main()
