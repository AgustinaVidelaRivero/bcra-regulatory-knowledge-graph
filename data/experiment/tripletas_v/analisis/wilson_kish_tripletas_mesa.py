"""Mesa, §191 (20/10/2026): el intervalo de la precisión ponderada de tripletas, con Wilson y el n efectivo de Kish (enmienda 3 al
pre-registro de tripletas, §3.6, PARA FIRMAR). USD 0. No lee ningún dato de V ni de T: las pruebas son sintéticas.
- **La estimación puntual no cambia** (`4afbe511:docs/preregistro_evaluacion_tripletas.md:87-89`): p̂_w = Σ_h W_h · p̂_h, con W_h = N_h / N.
- **El intervalo** pasa de Wald (`:89-90`) a Wilson al 95 % (z = 1,959964) con el n efectivo de Kish, como las tasas ponderadas de la tanda 1
  (`95b18217:docs/preregistro_tanda1.md`, §5.4 a [v8b]): n_ef = 1 / Σ_h (W_h² / n_h), y el Wilson de siempre con p̂_w y n_ef.
  - Con una muestra autoponderada (n_h / n = W_h), n_ef = n y p̂_w es la cruda: da el Wilson simple.
- **Los estratos con n_h < 5** se agrupan en «otros» para el intervalo, como el §3.6 los agrupaba para la varianza (`:90-91`): el estrato
  agrupado tiene W = Σ W_h y n = Σ n_h; p̂_w sigue sumando cada estrato.
- **Un estrato sin muestra** (en V, «otros», con cuota 0; nota al pie del 19/10/2026) no entra en n_ef; p̂_w se informa con las dos
  cotas de ese estrato, como dice la nota.
Uso: python3 -I -B wilson_kish_tripletas_mesa.py [--probar]"""
import math
import sys

Z = 1.959964


def wilson(p, n, z=Z):
    if n <= 0:
        raise ValueError("n tiene que ser positivo")
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z / d * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, c - h), min(1.0, c + h)


def ponderada(estratos, minimo=5):
    """estratos: lista de dicts {N_h, n_h, k_h} (k_h correctas de n_h decididas), con n_h ≥ 1. Devuelve p̂_w, n_ef y el intervalo."""
    N = sum(e["N_h"] for e in estratos)
    W = [e["N_h"] / N for e in estratos]
    p = sum(w * e["k_h"] / e["n_h"] for w, e in zip(W, estratos))
    grandes = [(w, e["n_h"]) for w, e in zip(W, estratos) if e["n_h"] >= minimo]
    chicos = [(w, e["n_h"]) for w, e in zip(W, estratos) if e["n_h"] < minimo]
    if chicos:
        grandes.append((sum(w for w, _ in chicos), sum(n for _, n in chicos)))
    n_ef = 1 / sum(w * w / n for w, n in grandes)
    return {"p_w": p, "n_ef": n_ef, "wilson": wilson(p, n_ef)}


def probar():
    ok = []
    # 1. autoponderada: n_h proporcionales a N_h -> n_ef = n y el Wilson simple de la cruda
    e = [{"N_h": 600, "n_h": 60, "k_h": 51}, {"N_h": 300, "n_h": 30, "k_h": 27}, {"N_h": 100, "n_h": 10, "k_h": 8}]
    r = ponderada(e)
    cruda = sum(x["k_h"] for x in e) / sum(x["n_h"] for x in e)
    ok.append(("autoponderada: n_ef = n", abs(r["n_ef"] - 100) < 1e-9))
    ok.append(("autoponderada: p_w = cruda", abs(r["p_w"] - cruda) < 1e-12))
    ok.append(("autoponderada: el Wilson simple", all(abs(a - b) < 1e-12 for a, b in zip(r["wilson"], wilson(cruda, 100)))))
    # 2. un estrato solo: el Wilson simple
    r1 = ponderada([{"N_h": 3967, "n_h": 100, "k_h": 84}])
    ok.append(("un estrato: el Wilson simple", all(abs(a - b) < 1e-12 for a, b in zip(r1["wilson"], wilson(0.84, 100)))))
    # 3. los anclajes del pre-registro (`:285`): 84 de 100 -> 0,7558; 26 de 30 -> 0,7032
    ok.append(("84/100 da 0,7558", round(wilson(0.84, 100)[0], 4) == 0.7558))
    ok.append(("26/30 da 0,7032", round(wilson(26 / 30, 30)[0], 4) == 0.7032))
    # 4. pesos desiguales (un estrato chico en la muestra y grande en el grafo): n_ef < n y el intervalo más ancho
    d = [{"N_h": 800, "n_h": 20, "k_h": 17}, {"N_h": 200, "n_h": 80, "k_h": 72}]
    rd = ponderada(d)
    ok.append(("desiguales: n_ef < n", rd["n_ef"] < 100))
    ok.append(("desiguales: n_ef = 1 / Σ W²/n", abs(rd["n_ef"] - 1 / (0.8 ** 2 / 20 + 0.2 ** 2 / 80)) < 1e-9))
    ok.append(("desiguales: más ancho que el simple con n = 100",
               (rd["wilson"][1] - rd["wilson"][0]) > (wilson(rd["p_w"], 100)[1] - wilson(rd["p_w"], 100)[0])))
    # 5. el intervalo queda dentro de [0, 1] aunque p_w sea 1 (Wald daría ancho 0)
    t = ponderada([{"N_h": 500, "n_h": 50, "k_h": 50}, {"N_h": 500, "n_h": 10, "k_h": 10}])
    ok.append(("p_w = 1: el inferior queda bajo 1", t["wilson"][0] < 1 and t["wilson"][1] == 1.0))
    # 6. los estratos con n_h < 5 se agrupan para n_ef y no para p_w
    g = [{"N_h": 900, "n_h": 90, "k_h": 81}, {"N_h": 60, "n_h": 3, "k_h": 3}, {"N_h": 40, "n_h": 2, "k_h": 1}]
    rg = ponderada(g)
    esp_p = 0.9 * 0.9 + 0.06 * 1.0 + 0.04 * 0.5
    esp_n = 1 / (0.9 ** 2 / 90 + 0.1 ** 2 / 5)
    ok.append(("agrupados: p_w suma cada estrato", abs(rg["p_w"] - esp_p) < 1e-12))
    ok.append(("agrupados: n_ef con «otros» = 0,1 sobre 5", abs(rg["n_ef"] - esp_n) < 1e-9))
    for nombre, b in ok:
        print(("OK   " if b else "MAL  ") + nombre)
    print(f"ejemplo con pesos desiguales: p_w = {rd['p_w']:.4f}, n_ef = {rd['n_ef']:.2f}, Wilson-Kish [{rd['wilson'][0]:.4f}; {rd['wilson'][1]:.4f}], "
          f"Wilson simple con n = 100 [{wilson(rd['p_w'], 100)[0]:.4f}; {wilson(rd['p_w'], 100)[1]:.4f}]")
    print("todo:", "OK" if all(b for _, b in ok) else "MAL")
    return all(b for _, b in ok)


if __name__ == "__main__":
    sys.exit(0 if probar() else 1)
