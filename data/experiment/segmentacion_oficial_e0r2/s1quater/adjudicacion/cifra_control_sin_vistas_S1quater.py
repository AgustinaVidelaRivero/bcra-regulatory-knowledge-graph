"""U-SEG-OFICIAL, S1-quater: la cifra de control, sin las fichas de la etapa 1 cuyo texto vio un modelo (mesa, 14/10/2026; USD 0).

PROPUESTA de la mesa, sellada antes de que empiece la pasada 2. Decisión de la autora del 14/10/2026 (recibida a las 15:11:28 y sellada
a las 15:12:18, `decisiones_autora_antes_de_la_pasada_2_S1quater.md`): «la cifra que decide es la de las 90 fichas; se informa además,
como control declarado, la cifra sin las 26 fichas de la etapa 1 cuyo texto vio el modelo».

- **Qué fichas salen:** las de `etapa_1.fichas` de `fichas_vistas_por_el_modelo_S1quater.json`, controlado por su sha256. Las midió la
  mesa en la sesión c0a11ec7 (hoja de ruta de la mesa, §98 y §99).
- **Qué calcula:** lo mismo que la cifra del piso de `cifras_lectura_S1quater.py` (sellado en el 59), sobre las fichas de la etapa 1 que
  quedan: el límite inferior de Wilson al 95 % de las unidades sin error de corte, sin ponderar, con las dudosas como correctas y como
  error. Usa las funciones del script sellado (`leer`, `calcular`, `piso`), sin copiarlas.
- **Antes de calcular,** corre `calcular` del script sellado sobre las 90 con las mismas entradas: la cifra de control exige las mismas
  validaciones (fichas del orden, estratos, poblaciones, planillas válidas). Frena si alguna no da.
- **Qué informa:** las leídas que quedan, por estrato; la cifra con los dos modos de las dudosas; y que no decide (decide la de las
  90, que da `cifras_lectura_S1quater.py`). No aplica el umbral de 0,90 como decisión: lo informa como referencia.
- **Qué no hace:** no repondera ni da la cifra del corpus. La cifra de control es la del piso, que es la que decide.

Uso: python3 -I -B cifra_control_sin_vistas_S1quater.py (los argumentos de cifras_lectura_S1quater.py) --excluir <json>
       --sha-excluir <sha256>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cifras_lectura_S1quater as C   # noqa: E402  (sellado en el 59)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("orden", "sha_orden", "poblaciones", "sha_poblaciones", "limites", "sha_limites", "planilla_1", "planilla_2", "excluir",
              "sha_excluir", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    out = Path(a.out)
    try:
        if out.exists():
            raise C.Freno("la salida ya existe")
        crudo = {}
        for k in ("orden", "poblaciones", "limites", "excluir"):
            crudo[k] = Path(getattr(a, k)).read_bytes()
            if hashlib.sha256(crudo[k]).hexdigest() != getattr(a, f"sha_{k}"):
                raise C.Freno(f"{k}: no da su sha256 sellado")
        orden, pob = json.loads(crudo["orden"]), json.loads(crudo["poblaciones"])
        limites = json.loads(crudo["limites"])["cortes"]["limites_declarados"]["unidades"]
        p1, p2 = C.leer(Path(a.planilla_1)), C.leer(Path(a.planilla_2))
        base = C.calcular(orden, pob, limites, p1, p2)
        if not base["planillas_validas"]:
            raise C.Freno("las planillas no son válidas (las mismas validaciones que la cifra que decide)")
        excl = json.loads(crudo["excluir"])["etapa_1"]["fichas"]
        f1 = {x["id_opaco"]: x for x in orden["etapa_1"]["fichas"]}
        if len(excl) != len(set(excl)) or not set(excl) <= set(f1):
            raise C.Freno("las fichas a excluir no son fichas distintas de la etapa 1 del orden sellado")
        quedan = [f for f in p1 if f["ficha"] not in set(excl)]
        if len(quedan) != len(p1) - len(excl):
            raise C.Freno("no salieron exactamente las fichas a excluir")
        res = {"control_declarado": True,
               "no_decide": "la cifra que decide es la de las 90 fichas (cifras_lectura_S1quater.py, etapa_1.cifra_del_piso)",
               "excluidas": {"cuantas": len(excl), "fuente_sha256": a.sha_excluir,
                             "por_estrato": dict(sorted(Counter(f1[i]["estrato"] for i in excl).items()))},
               "leidas_que_quedan": {"cuantas": len(quedan),
                                     "por_estrato": dict(sorted(Counter(f1[f["ficha"]]["estrato"] for f in quedan).items()))},
               "cifra_de_control": C.piso(quedan),
               "nota": "llega_al_piso se informa como referencia del umbral de 0,90; no decide"}
    except C.Freno as ex:
        raise SystemExit(f"FRENO: {ex}")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"control_declarado": True, "escrito": out.name}, ensure_ascii=False))


if __name__ == "__main__":
    main()
