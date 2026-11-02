#!/usr/bin/env python3
"""selftest_indice_puntos_union.py — U-INDICES-EVAL, etapa b: el selftest de indice_puntos_union.py (la unión por clave
y el orden sin repetidos). Biblioteca estándar; corre sobre la copia, nunca sobre el repo. Imprime y escribe solo
cuentas, ids y sha256 (ni títulos ni textos).

  C1, sintético: una estructura en memoria con una clave repetida y un ciclo da un solo punto y un hijo cortado,
      contado; y otra con un punto bajo dos padres da el orden de HEAD con el repetido y el nuevo sin él.
  C2, N5 byte a byte con 0 uniones: la E0 de N5 y su kg.json, con la versión nueva, dan documentos.json, puntos.json,
      nodos.json e indice_bm25.json iguales byte a byte a los del respaldo de N5 (verificado antes contra su
      manifest_respaldo.txt); el camino es el de HEAD (0 uniones), y el manifiesto difiere del respaldo solo en el campo
      del código (`version_indice_puntos`; el diff va a la salida).
  C3, los tres TOs del grafo evaluado: 11 claves unidas, 28 apariciones y los 4 hijos cortados esperados, todos de
      ri_transpa (SC→SA, Sbloque2→SA, Sbloque2→SB y Sbloque2→SC).
  C4, el árbol del grafo evaluado: todo punto llega por su padre a su TO, y el subárbol de cada punto termina (las
      listas de hijos no tienen ciclos).
  C5, sin repetidos: en el índice del grafo evaluado, un documento por clave y 0 ids repetidos en los documentos y en el
      BM25 (el denso se controla al construirlo, en el tramo b2), con la cuenta de lo que el orden de HEAD repetía.

Uso (desde la raíz de la copia):
  .venv/bin/python -B data/experiment/banco_mcp/mcp_kg/selftest_indice_puntos_union.py --respaldo-n5 DIR --out DIR
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import indice_puntos_union as U  # noqa: E402
IP = U.IP
BM = IP.BM

N5 = "KG_Acumulado_Tandas0y1_r2b_sincola"
EVALUADO = "KG_Acumulado_Tandas0y1yFinal_r2b_sincola"
E0_EVALUADO = "data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b"
CORTES_ESPERADOS = [["ri_transpa::SC", "ri_transpa::SA"], ["ri_transpa::Sbloque2", "ri_transpa::SA"],
                    ["ri_transpa::Sbloque2", "ri_transpa::SB"], ["ri_transpa::Sbloque2", "ri_transpa::SC"]]


def raiz(to: str) -> dict:
    return {"clave": to, "to": to, "unidad": None, "titulo": to, "tipo": "to", "padre": None, "hijos": [],
            "pagina": None, "paginas": [], "bloques": [], "textos": [], "herencia": [], "intro": False,
            "en_estructura": True, "nodos": []}


def sec(numero: str, hijos: list | None = None) -> dict:
    return {"tipo": "seccion", "numero": numero, "titulo": f"seccion {numero}", "pagina": 1, "hijos": hijos or []}


def c1_sintetico() -> dict:
    # una clave repetida (SA) que cerraría un ciclo: SA > SB > SA
    p, cu = {"sint": raiz("sint")}, {"apariciones_extra": Counter(), "hijos_cortados": []}
    U.unir_estructura("sint", {"secciones": [sec("A", [sec("B", [sec("A")])])]}, p, cu)
    ciclo = {"puntos": sorted(k for k in p if k != "sint"), "claves_unidas": len(cu["apariciones_extra"]),
             "apariciones": sum(1 + v for v in cu["apariciones_extra"].values()), "hijos_cortados": cu["hijos_cortados"],
             "hijos_SA": p["sint::SA"]["hijos"], "hijos_SB": p["sint::SB"]["hijos"]}
    ok1 = (ciclo["puntos"] == ["sint::SA", "sint::SB"] and ciclo["claves_unidas"] == 1 and ciclo["apariciones"] == 2
           and ciclo["hijos_cortados"] == [["sint::SB", "sint::SA"]] and ciclo["hijos_SA"] == ["sint::SB"]
           and ciclo["hijos_SB"] == [])
    # un punto bajo dos padres, sin ciclo: SA > SB y SC > SB
    p2, cu2 = {"sint": raiz("sint")}, {"apariciones_extra": Counter(), "hijos_cortados": []}
    U.unir_estructura("sint", {"secciones": [sec("A", [sec("B")]), sec("C", [sec("B")])]}, p2, cu2)
    dos = {"orden_head": U.ORDEN_CANONICO_HEAD(p2), "orden_nuevo": U.orden_canonico(p2),
           "hijos_cortados": cu2["hijos_cortados"], "padre_SB": p2["sint::SB"]["padre"]}
    ok2 = (dos["orden_head"] == ["sint::SA", "sint::SB", "sint::SC", "sint::SB"]
           and dos["orden_nuevo"] == ["sint::SA", "sint::SB", "sint::SC"] and dos["hijos_cortados"] == []
           and dos["padre_SB"] == "sint::SA")
    return {"ok": ok1 and ok2, "ciclo": ciclo, "dos_padres": dos}


def leer_respaldo(d: Path) -> dict:
    esperado = {}
    for linea in (d / "manifest_respaldo.txt").read_text(encoding="utf-8").splitlines():
        sha, nombre = linea.split(None, 1)
        esperado[nombre.strip()] = sha
    return {n: {"sha256_manifest": s, "sha256_archivo": IP.sha256_file(d / n)} for n, s in esperado.items()}


def c2_n5(respaldo: Path, out: Path) -> dict:
    from grafos import GRAFOS, verificar_sha  # noqa: E402
    resp = leer_respaldo(respaldo)
    respaldo_ok = all(v["sha256_manifest"] == v["sha256_archivo"] for v in resp.values())
    sal = out / "n5_rehecho"
    if sal.exists():
        shutil.rmtree(sal)
    sal.mkdir(parents=True)
    shutil.copy2(respaldo / "manifiesto.json", sal / "manifiesto.json")      # el previo, como en el índice servido
    kg_sha = verificar_sha(N5)
    e0 = IP.REPO_DIR / json.loads((respaldo / "manifiesto.json").read_text(encoding="utf-8"))["e0_dir"]
    man = U.escribir(N5, GRAFOS[N5]["path"], kg_sha, e0, sal)
    cuentas = dict(U.ULTIMAS_CUENTAS)
    archivos = {}
    for n in IP.ARCHIVOS:
        a, b = (sal / n).read_bytes(), (respaldo / n).read_bytes()
        archivos[n] = {"igual_byte_a_byte": a == b, "sha256": hashlib.sha256(a).hexdigest(),
                       "sha256_respaldo": resp[n]["sha256_manifest"]}
    m_resp = json.loads((respaldo / "manifiesto.json").read_text(encoding="utf-8"))
    m_new = json.loads((sal / "manifiesto.json").read_text(encoding="utf-8"))
    claves_distintas = sorted(k for k in set(m_resp) | set(m_new) if m_resp.get(k) != m_new.get(k))
    diff = list(difflib.unified_diff((respaldo / "manifiesto.json").read_text(encoding="utf-8").splitlines(),
                                     (sal / "manifiesto.json").read_text(encoding="utf-8").splitlines(),
                                     "respaldo_N5/manifiesto.json", "n5_rehecho/manifiesto.json", lineterm=""))
    ok = (respaldo_ok and all(v["igual_byte_a_byte"] for v in archivos.values()) and cuentas.get("camino") == "HEAD"
          and cuentas.get("claves_unidas") == 0 and cuentas.get("repetidos_sacados_del_orden") == 0
          and claves_distintas == ["version_indice_puntos"])
    return {"ok": ok, "respaldo_igual_a_su_manifest": respaldo_ok, "respaldo": resp, "archivos": archivos,
            "cuentas": cuentas, "manifiesto_claves_distintas": claves_distintas, "manifiesto_diff": diff,
            "n_puntos": man["n_puntos"]}


def arbol_ok(puntos: dict) -> dict:
    sin_camino = []
    for k, p in puntos.items():
        if p["tipo"] == "to":
            continue
        vistos, x = set(), k
        while puntos[x]["padre"] is not None and x not in vistos:
            vistos.add(x)
            x = puntos[x]["padre"]
        if puntos[x]["tipo"] != "to" or x != p["to"]:
            sin_camino.append(k)
    color, ciclos = {}, []

    def visita(k):                                         # iterativo: DFS con colores sobre las listas de hijos
        pila = [(k, iter(puntos[k]["hijos"]))]
        color[k] = 1
        while pila:
            nodo, it = pila[-1]
            h = next(it, None)
            if h is None:
                color[nodo] = 2
                pila.pop()
            elif color.get(h) == 1:
                ciclos.append([nodo, h])
            elif h not in color:
                color[h] = 1
                pila.append((h, iter(puntos[h]["hijos"])))
    for k in puntos:
        if k not in color:
            visita(k)
    madres = Counter(h for p in puntos.values() for h in p["hijos"])
    return {"sin_camino_a_su_to": sin_camino, "ciclos": ciclos,
            "puntos_en_mas_de_una_lista_de_hijos": sorted(k for k, v in madres.items() if v > 1)}


def c3_c4_c5() -> tuple[dict, dict, dict]:
    from grafos import GRAFOS, verificar_sha  # noqa: E402
    verificar_sha(EVALUADO)
    U.usar_version_nueva()
    d = IP.derivar(GRAFOS[EVALUADO]["path"], IP.REPO_DIR / E0_EVALUADO)
    cu = dict(U.ULTIMAS_CUENTAS)
    tres = {to: cu["por_to"].get(to) for to in ("ri_secoexpo", "ri_transpa", "ri_tsa")}
    cortes = [c for v in cu["por_to"].values() for c in v["hijos_cortados"]]
    c3 = {"ok": (cu["camino"] == "union" and cu["claves_unidas"] == 11 and cu["apariciones"] == 28
                 and cu["hijos_cortados"] == 4 and sorted(cortes) == sorted(CORTES_ESPERADOS)
                 and sorted(cu["por_to"]) == ["ri_secoexpo", "ri_transpa", "ri_tsa"]
                 and [len(tres[t]["claves_unidas"]) for t in ("ri_secoexpo", "ri_transpa", "ri_tsa")] == [3, 4, 4]),
          "claves_unidas": cu["claves_unidas"], "apariciones": cu["apariciones"], "hijos_cortados": cu["hijos_cortados"],
          "por_to": cu["por_to"]}
    ar = arbol_ok(d["puntos"])
    c4 = {"ok": not ar["sin_camino_a_su_to"] and not ar["ciclos"], **ar,
          "n_puntos": sum(1 for p in d["puntos"].values() if p["tipo"] != "to"),
          "n_tos": sum(1 for p in d["puntos"].values() if p["tipo"] == "to")}
    ids_docs = [x["id"] for x in d["documentos"]]
    ids_bm = d["indice_bm25"]["ids"]
    orden_head = U.ORDEN_CANONICO_HEAD(d["puntos"])
    c5 = {"documentos": len(ids_docs), "documentos_distintos": len(set(ids_docs)),
          "ids_bm25": len(ids_bm), "ids_bm25_distintos": len(set(ids_bm)), "bm25_igual_a_documentos": ids_bm == ids_docs,
          "claves_de_punto": c4["n_puntos"], "orden_head": len(orden_head), "orden_head_distintos": len(set(orden_head)),
          "repetidos_sacados_del_orden": cu.get("repetidos_sacados_del_orden"),
          "procedencias_fuera_de_la_e0": d["declarado"]["procedencias_fuera_de_la_e0"],
          "sha256_documentos_json": IP.sha256_bytes(IP.serializar(d["documentos"]))}
    c5["ok"] = (c5["documentos"] == c5["documentos_distintos"] == c5["claves_de_punto"] == c5["ids_bm25_distintos"]
                == c5["ids_bm25"] and c5["bm25_igual_a_documentos"])
    return c3, c4, c5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--respaldo-n5", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    res = {"c1_sintetico": c1_sintetico(), "c2_n5_byte_a_byte": c2_n5(a.respaldo_n5.resolve(), a.out.resolve())}
    res["c3_tres_tos"], res["c4_arbol"], res["c5_sin_repetidos"] = c3_c4_c5()
    res["version"] = U.campo_version()
    res["ok"] = all(v["ok"] for k, v in res.items() if k.startswith("c"))
    (a.out / "selftest_indice_puntos_union.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n",
                                                            encoding="utf-8")
    print(json.dumps({k: (v["ok"] if isinstance(v, dict) and "ok" in v else v) for k, v in res.items()}, ensure_ascii=False))
    print("C2 manifiesto, diff contra el respaldo:")
    print("\n".join(res["c2_n5_byte_a_byte"]["manifiesto_diff"]))
    print("C3:", json.dumps({k: res["c3_tres_tos"][k] for k in ("claves_unidas", "apariciones", "hijos_cortados")}))
    print("C5:", json.dumps({k: v for k, v in res["c5_sin_repetidos"].items() if k != "ok"}))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
