"""
acuerdo_juez_cob_t.py — U-COB-T, vueltas b y c, punto 8: el acuerdo del juez de presencia con la lectura de la autora sobre
las 100 primeras (nota v3, punto 9). Solo corre si están selladas la hoja de presencia de la autora (vuelta c: la segunda nota
la separa de la de importancia) y las salidas del juez. USD 0, sin API.
Imprime solo cuentas.

  - el veredicto de la autora, con la regla del 5.6 (cob_v.presencia_regla, sin adjudicación); el del juez, el modal de sus tres
    repeticiones (cob_v.agregar_modal), cada una con la misma regla;
  - una fila acuerda si el modal del juez es el de la autora; las que el juez manda a adjudicación o deja sin consenso cuentan
    como desacuerdo;
  - el acuerdo sobre las 100; el kappa de Cohen sobre las tres clases, en las filas en las que deciden los dos; la distribución
    de las repeticiones (unanimidad, 2 a 1, mayoría con una repetición sin salida, sin consenso); y si escala: 84 de 100 o más.
  python3 -I -B acuerdo_juez_cob_t.py [--lectura L] [--corridas C] [--salidas S]
  python3 -I -B acuerdo_juez_cob_t.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_cob_t as T  # noqa: E402
import comun_600_cob_t as M  # noqa: E402
import sellar_hojas_600_cob_t as SH  # noqa: E402

CLASES = ("presente", "parcial", "ausente")
UMBRAL = 84
VEREDICTOS = "veredictos_juez_presencia_cob_t.json"
SALIDA = "acuerdo_juez_cob_t.json"


def kappa(pares: list[tuple[str, str]]) -> float | None:
    """Kappa de Cohen sobre las tres clases: (po − pe) / (1 − pe)."""
    n = len(pares)
    if not n:
        return None
    po = sum(a == b for a, b in pares) / n
    ca, cb = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    pe = sum(ca[c] * cb[c] for c in CLASES) / (n * n)
    return None if pe == 1 else (po - pe) / (1 - pe)


def acuerdo(autora: dict, juez: dict, primeras: list[str]) -> dict:
    """autora: ref -> veredicto; juez: ref -> {veredicto_final, distribucion}. Sobre las refs de las 100 primeras."""
    acuerdan, pares, dist = 0, [], Counter()
    for r in primeras:
        j = juez[r]
        dist[j["distribucion"]] += 1
        if j["veredicto_final"] in CLASES:
            pares.append((autora[r], j["veredicto_final"]))
            acuerdan += autora[r] == j["veredicto_final"]
    n = len(primeras)
    k = kappa(pares)
    return {"n": n, "acuerdan": acuerdan, "desacuerdan": n - acuerdan,
            "juez_a_adjudicacion": sum(juez[r]["veredicto_final"] == "adjudicacion" for r in primeras),
            "juez_sin_consenso": sum(juez[r]["veredicto_final"] == "sin_consenso" for r in primeras),
            "deciden_los_dos": len(pares), "kappa": k, "distribucion_de_las_repeticiones": dict(dist),
            "escala": acuerdan >= UMBRAL, "umbral": f"{UMBRAL} de 100"}


def calcular(lectura: Path, corridas: Path, dir_acta: Path | None, consola=print) -> dict:
    esp, limpias, s_hoja = SH.leer_sellada(lectura, "presencia", dir_acta)
    vp = Path(corridas) / "juez_presencia" / VEREDICTOS
    s_juez = M.verificar_sello(vp)
    juez = json.loads(vp.read_text(encoding="utf-8"))
    por_ref = {r: x["ref"] for x in esp["renglones"] for r in x["refs"]}
    fila = {f["ref"]: f for f in limpias}
    primeras = juez["primeras"]
    autora = {r: fila[por_ref[r]]["veredicto"] for r in primeras}
    out = acuerdo(autora, juez["por_ref"], primeras) | {"hora": T.hora(), "hoja_sha256": s_hoja, "juez_sha256": s_juez}
    s = T.escribir_json(Path(lectura) / SALIDA, out)
    consola(f"acuerdo: {out['acuerdan']} de {out['n']} (adjudicación {out['juez_a_adjudicacion']}, sin consenso "
            f"{out['juez_sin_consenso']}); kappa {out['kappa']:.4f} sobre {out['deciden_los_dos']}; repeticiones "
            f"{out['distribucion_de_las_repeticiones']}; escala {out['escala']}; {SALIDA}: {s}")
    return out


def selftest() -> bool:
    res = {}
    # a mano: 10 filas en que deciden los dos: (P,P)x4 (A,A)x2 (Pa,Pa)x1 (P,A) (A,P) (Pa,A): po = 0,7; la autora P 5, A 3,
    # Pa 2; el juez P 5, A 4, Pa 1; pe = 0,25 + 0,12 + 0,02 = 0,39; kappa = 0,31 / 0,61 = 0,508197
    pares = ([("presente", "presente")] * 4 + [("ausente", "ausente")] * 2 + [("parcial", "parcial")]
             + [("presente", "ausente"), ("ausente", "presente"), ("parcial", "ausente")])
    res["kappa_a_mano_0_508197"] = round(kappa(pares), 6) == 0.508197
    res["kappa_perfecto_1"] = kappa([("presente", "presente"), ("ausente", "ausente")]) == 1.0
    refs = [f"S{i:03d}" for i in range(1, 13)]
    autora = dict(zip(refs, [a for a, _ in pares] + ["presente", "ausente"]))
    juez = {r: {"veredicto_final": b, "distribucion": "unanimidad"} for r, (_, b) in zip(refs, pares)}
    juez["S011"] = {"veredicto_final": "adjudicacion", "distribucion": "2_a_1"}
    juez["S012"] = {"veredicto_final": "sin_consenso", "distribucion": "sin_consenso"}
    a = acuerdo(autora, juez, refs)
    res["acuerdo_7_de_12_con_adjudicacion_y_sin_consenso_en_desacuerdo"] = (
        (a["acuerdan"], a["n"], a["deciden_los_dos"], a["juez_a_adjudicacion"], a["juez_sin_consenso"])
        == (7, 12, 10, 1, 1) and round(a["kappa"], 6) == 0.508197
        and a["distribucion_de_las_repeticiones"] == {"unanimidad": 10, "2_a_1": 1, "sin_consenso": 1})
    cien = [f"S{i:03d}" for i in range(1, 101)]
    au = {r: "presente" if i % 2 else "ausente" for i, r in enumerate(cien)}
    for n_ok, escala in ((84, True), (83, False)):
        ju = {r: {"veredicto_final": au[r] if i < n_ok else ("ausente" if au[r] == "presente" else "presente"),
                  "distribucion": "unanimidad"} for i, r in enumerate(cien)}
        res[f"{n_ok}_de_100_escala_{escala}"] = acuerdo(au, ju, cien)["escala"] is escala
    ok = all(res.values())
    for k, v in res.items():
        print(f"  {k}: {v}")
    print("selftest del acuerdo:", "OK" if ok else "MAL", f"({sum(res.values())} de {len(res)})")
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lectura", type=Path, default=T.LECTURA)
    ap.add_argument("--corridas", type=Path, default=T.CORRIDAS)
    ap.add_argument("--salidas", type=Path, default=T.SALIDAS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if selftest() else 2
    calcular(a.lectura, a.corridas, a.salidas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
