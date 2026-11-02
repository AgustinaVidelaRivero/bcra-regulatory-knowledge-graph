"""Límites y residuos que deja S0-5a-bis, caso por caso (U-SEG-OFICIAL; USD 0, solo lectura).

Uso: python -B limites_S0-5a-bis.py --bis <E0 de S0-5a-bis> --lista-v2 <lista v2> --candidatos-r5a2 <lectura de los
       candidatos de R5-a′ de S0-5a (s0_5/censos/lectura_candidatos_r5a2_S0-5a.json)> --continuidad <control de
       continuidad sobre S0-5a-bis> --limites-s05a <limites_S0-5a.py sobre S0-5a-bis> --lista-88 <lista de los 88
       rechazos por columna profunda de la mesa> --out-json <json> --out-md <md>

Cada fila: la unidad, sus páginas, el mecanismo (o «sin leer»), el destino y la fuente. Entran:
- los `limites_que_quedan` de los dos mixtos, tal cual de la lista v2, con su unidad en la salida; y, de la tercera
  nota de decisiones del 09/10/2026 (`be88fdf9`), los dos puntos del Anexo III tragados en `ri2_ae::14.3`, uno por uno,
  con el renglón y el motivo que registra E0 en `rechazos_header`;
- `seggar::5.3.5` (nota de la mesa del 09/10/2026, en `32c71ca`: límite declarado, grupo 2, PENDIENTE de la autora);
- `ri_cc::R5::2.2.1.2`, que no se toca por decisión de la autora (sin adjudicar);
- los candidatos de R5-a′ fuera de ri_oc que quedan declarados (todos menos ri_oc C.11 y ri_rml 1.2.3, que la nota
  descarta), con mi lectura de S0-5a; van al grupo 2 si se confirman;
- los saltos de numeración que quedan después de S0-5a-bis: (ii) y (iii), y (i) con descendientes tragados (fuera de
  la tanda 1: grupo 2; tanda 0: fuera de S0-5), y los (i), como información;
- los del §3 del mandato de S0-5a, con su cifra sobre la salida de S0-5a-bis;
- los 87 rechazos por columna profunda que R5-g no toca (7 documentos fuera de la tanda 1), con la lectura de la mesa
  de su lista, y si siguen en la salida.
Las otras 13 listas que no se tocan quedan como en S0-4b porque lo que sigue al último ítem es del ítem (lectura de la
mesa contra la página): no son residuo de R5-a, y se listan aparte con esa razón.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

TANDA1 = ("ayccef", "expaef", "opefci", "adrei", "ri_ccna", "ri_pgn", "ri_rml", "ri_gerc", "snp_cheq", "ceninf",
          "cirmo3", "snp_tr", "lingeef", "depaho", "cajasc", "manori", "efemin", "nmcief", "ri_dcpc", "ri_oc")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("bis", "lista_v2", "candidatos_r5a2", "continuidad", "limites_s05a", "lista_88", "out_json", "out_md"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    v2 = jl(a.lista_v2)
    cache: dict = {}

    def ids(to: str) -> dict:
        if to not in cache:
            cache[to] = {c["id"]: c for c in jl(a.bis / f"chunks_{to}.json")}
        return cache[to]

    def paginas(uid: str):
        c = ids(uid.split("::")[0])
        us = [c[i] for i in c if i == uid or i.startswith(uid + "::parte")]
        return sorted({p for u in us for p in u["paginas"]}) if us else None

    filas = []
    for x in v2["por_lista"]:
        for lim in x.get("limites_que_quedan", []):
            filas.append({"grupo_de_fila": "mixto de R5-a", "unidad": x["lista"], "paginas": lim["paginas"],
                          "que": lim["que"], "mecanismo": lim["mecanismo"], "destino": lim["destino"],
                          "en_la_salida": {"unidad_existe": paginas(x["lista"]) is not None,
                                           "paginas_de_la_unidad": paginas(x["lista"])},
                          "fuente": "lista v2, limites_que_quedan"})
    e_ae = jl(a.bis / "estructura_ri2_ae.json")
    for num in ("15.", "16."):
        r = next((r for r in e_ae["rechazos_header"] if r["pagina"] == 29 and r["texto"].startswith(num + " ")), None)
        filas.append({"grupo_de_fila": "mixto de R5-a, límite medido de un caso", "unidad": "ri2_ae::14.3",
                      "paginas": [29], "que": f"«{r['texto'] if r else num}»",
                      "mecanismo": (f"punto del Anexo III que E0 no abre: en rechazos_header con el motivo {r['motivo']}"
                                    if r else "sin el rechazo en la salida"),
                      "destino": "grupo 2", "en_la_salida": {"rechazo_registrado": r is not None},
                      "fuente": "tercera nota de decisiones del 09/10/2026 al pie del mandato (be88fdf9)"})
    filas.append({"grupo_de_fila": "R5-a, no se toca", "unidad": "seggar::5.3.5", "paginas": paginas("seggar::5.3.5"),
                  "que": "el texto de «6. Instrumentación.» dentro del último ítem de 5.3",
                  "mecanismo": "encabezado de sección que E0 no abrió", "destino": "grupo 2, PENDIENTE de la autora",
                  "fuente": "nota de la mesa del 09/10/2026 al pie del mandato (32c71ca), decisión 1"})
    filas.append({"grupo_de_fila": "R5-a, no se toca", "unidad": "ri_cc::R5::2.2.1.2",
                  "paginas": paginas("ri_cc::R5::2.2.1.2"),
                  "que": "«Apoderado / tutor / curador o Representante legal» y su párrafo, dentro del último ítem",
                  "mecanismo": "sin leer (dudosa: bloque de datos con título)",
                  "destino": "no se toca por decisión de la autora; sin adjudicar",
                  "fuente": "lista v2, no_se_tocan (decisión 4)"})
    for f in jl(a.candidatos_r5a2)["filas"]:
        if f["item"] in ("ri_oc::C.11", "ri_rml::1.2.3") or not f["sobre_S0-4b"]:
            continue
        filas.append({"grupo_de_fila": "R5-a′, candidato declarado", "unidad": f["item"],
                      "paginas": f["paginas_item"], "que": f"«{f['renglon']}»",
                      "mecanismo": f"{f['lectura']} (mi lectura en S0-5a, sin la página): {f['nota']}",
                      "destino": "grupo 2 si se confirma", "fuente": "nota de la mesa del 09/10/2026, decisión 3"})
    c = jl(a.continuidad)
    for f in c["para_la_autora"]:
        filas.append({"grupo_de_fila": "salto de numeración", "unidad": f.get("unidad") or f"{f['to']} (sin unidad)",
                      "paginas": paginas(f["unidad"]) if f.get("unidad") else None,
                      "que": f"{f['to']} {f.get('subdocumento') or ''} {f['rotulo']} ({f['clase']}, {f['forma']})".replace("  ", " "),
                      "mecanismo": ("remisión (posible_referencia)" if f.get("posible_referencia") else
                                    "punto tragado" if f["clase"] == "ii" else
                                    "el PDF salta, con descendientes tragados" if f["clase"] == "i" else "otra"),
                      "destino": ("tanda 0, fuera de S0-5" if f["to"] in ("ctacte", "lingob", "polcre", "pagjub", "docvig")
                                  else "regla por lista en S0-5" if f["to"] in TANDA1 else "grupo 2"),
                      "fuente": "control de continuidad sobre S0-5a-bis"})
    info_i = [f for f in c["filas"] if f["clase"] == "i" and not f["descendientes_tragados"]]
    for f in info_i:
        filas.append({"grupo_de_fila": "salto de numeración, información", "unidad": f"{f['to']} (sin unidad)",
                      "paginas": None,
                      "que": f"{f['to']} {f.get('subdocumento') or ''} {f['rotulo']} (i, {f['forma']})".replace("  ", " "),
                      "mecanismo": "el PDF salta" + (" (solo fuera del cuerpo)" if f.get("aparece_solo_fuera_del_cuerpo")
                                                    else ""),
                      "destino": "información" + (" (declarado: el PDF salta 3.3.6 y 3.3.6.1)"
                                                  if f["to"] == "snp_cheq" and f["rotulo"].startswith("3.3.6") else ""),
                      "fuente": "control de continuidad sobre S0-5a-bis"})
    l5 = jl(a.limites_s05a)
    for uid in ("ri_iepsp::S0", "ri_ieccm::S0", "ri_icpipsp::A1C3::S2", "ri_secoexpo::S17", "ri_mmsef::2.2::intro"):
        v = l5[uid]
        filas.append({"grupo_de_fila": "§3 del mandato de S0-5a", "unidad": uid, "paginas": v.get("paginas"),
                      "que": {"ri_iepsp::S0": "tercer renglón del recuadro como texto del preámbulo",
                              "ri_ieccm::S0": "tercer renglón del recuadro como texto del preámbulo",
                              "ri_icpipsp::A1C3::S2": "encabezado de columna repetido",
                              "ri_secoexpo::S17": "la numeración vuelve a empezar en el bloque A.2",
                              "ri_mmsef::2.2::intro": "una sola unidad; no es error de corte"}[uid],
                      "mecanismo": "limpieza" if uid in ("ri_iepsp::S0", "ri_ieccm::S0", "ri_icpipsp::A1C3::S2")
                      else "numeración que vuelve a empezar" if uid == "ri_secoexpo::S17" else "ninguno",
                      "destino": "no cambia" if uid == "ri_mmsef::2.2::intro" else
                      "grupo 2; si sale en S1-ter, cuenta como error" if uid == "ri_secoexpo::S17" else "grupo 2",
                      "caracteres": v.get("caracteres") or v.get("caracteres_de_la_unidad"),
                      "fuente": "mandato de S0-5a, §3"})
    for f in jl(a.lista_88)["filas"]:
        if f["to"] == "ri_oc":
            continue
        e = jl(a.bis / f"estructura_{f['to']}.json")
        sigue = any(r["pagina"] == f["pagina"] and r["texto"] == f["texto"] and r["motivo"] == f["motivo"]
                    for r in e["rechazos_header"])
        filas.append({"grupo_de_fila": "rechazo por columna profunda", "unidad": f"{f['to']} (renglón rechazado)",
                      "paginas": [f["pagina"]], "que": f"«{f['texto'][:70]}»",
                      "mecanismo": f"{f['motivo']}; lectura de la mesa: {f.get('lectura_mesa', 'sin leer')}",
                      "destino": "como en S0-4b (caso negativo de R5-g); fuera de la tanda 1",
                      "sigue_en_la_salida": sigue, "fuente": "lista de los 88 de la mesa"})
    nst = [{"lista": x["lista"], "paginas": x["paginas"], "clase_mesa": x["clase_mesa"]}
           for x in v2["no_se_tocan"] if x["lista"] not in ("seggar::5.3.5", "ri_cc::R5::2.2.1.2")]
    res = {"filas": len(filas), "por_grupo": dict(collections.Counter(f["grupo_de_fila"] for f in filas)),
           "por_destino": dict(collections.Counter(f["destino"] for f in filas)),
           "limites": filas,
           "no_se_tocan_sin_residuo": {"razon": "lo que sigue al último ítem es del ítem (lectura de la mesa contra la "
                                                "página, clase «no es cierre»): la unidad queda como en S0-4b",
                                       "listas": nst},
           "tanda0_fuera_de_S0-5a-bis": l5.get("tanda0_fuera_de_S0-5a")}
    a.out_json.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = ["# Límites y residuos que deja S0-5a-bis, caso por caso", "",
          "Generado por `s0_5/bis/scripts/limites_S0-5a-bis.py`.", "",
          f"Resumen: {json.dumps({k: res[k] for k in ('filas', 'por_grupo', 'por_destino')}, ensure_ascii=False)}", "",
          "| grupo | unidad | pp. | qué | mecanismo | destino |", "|---|---|---|---|---|---|"]
    for f in filas:
        md.append(f"| {f['grupo_de_fila']} | `{f['unidad']}` | {','.join(map(str, f['paginas'] or []))} | {f['que']} | "
                  f"{f['mecanismo']} | {f['destino']} |")
    md += ["", "## Las listas que no se tocan sin residuo de R5-a", "", res["no_se_tocan_sin_residuo"]["razon"] + ":", ""]
    md += [f"- `{x['lista']}` (pp. {','.join(map(str, x['paginas']))})" for x in nst]
    t0 = res["tanda0_fuera_de_S0-5a-bis"]
    md += ["", f"## La tanda 0, fuera por lista", "",
           f"Sin la exclusión, las reglas crearían {t0['creadas']}, quitarían {t0['quitadas']} y cambiarían "
           f"{t0['cambiadas']} unidades en {len(t0['tos'])} TOs: {', '.join(t0['tos']) or 'ninguno'}."]
    a.out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("filas", "por_grupo", "por_destino")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
