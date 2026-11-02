"""Las listas que cambia R5-a en los 152, con mi lectura (U-SEG-OFICIAL, S0-5a; USD 0, solo lectura de las salidas).

Uso: python -B lectura_r5a_S0-5a.py --antes <E0 de S0-4b> --despues <E0 de S0-5a> --planilla-116 <planilla del 1.16
       de S1-bis> --out-json <json> --out-md <md>

Por lista (el último ítem de una lista del detector corregido en la que R5-a movió al menos un párrafo, según los
eventos `cierre_al_margen_r5a` de `estructura_<to>.json`): la tanda de su TO, si es uno de los 9 casos del mecanismo 1
o de los 35 leídos en S1-bis, las columnas de los rótulos y del texto y su diferencia (la sangría), los párrafos y
renglones movidos, el primer renglón de cada uno, lo que queda al final del ítem, el cierre del padre (nuevo o que ya
existía) y cuántas unidades lo heredan.

La lectura (`LECTURA`) es mía, a la vista del texto de la salida y de las columnas, sin abrir la página del PDF, y no
está adjudicada: «cierre», el párrafo tiene la forma de un cierre del padre (prosa al margen que vale para la lista o
para el padre); «no es cierre», es cuerpo del ítem, un formulario o un modelo de nota, un bloque con título propio o un
anexo; «dudosa», no lo puedo decir sin la página. Los 9 casos del mecanismo 1 vienen leídos por la mesa (S1-bis).
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

TANDA1 = ("ayccef", "expaef", "opefci", "adrei", "ri_ccna", "ri_pgn", "ri_rml", "ri_gerc", "snp_cheq", "ceninf",
          "cirmo3", "snp_tr", "lingeef", "depaho", "cajasc", "manori", "efemin", "nmcief", "ri_dcpc", "ri_oc")
CASOS = ("adfsp::1.1.10", "cajasc::11.4.4", "cajasc::4.2.2.3", "depaho::3.11.5.5", "manori::1.4.1.3",
         "manori::3.4.1.3", "ri_oc::B.1.28", "ri_oc::B.2.4", "ri_oc::B.3.4")
C, N, D = "cierre", "no es cierre", "dudosa"
LECTURA = {
    "adfsp::1.2.2.2": (C, "«Para ambos destinos (puntos 1.2.2.1. y 1.2.2.2.)…»: vale para los dos ítems"),
    "adfsp::2.6.3.2": (C, "requisitos de la documentación de 2.6.3 (contratos, certificación notarial)"),
    "apnf::1.3.1.2": (C, "«La inscripción en el registro correspondiente no dará derecho…»: vale para 1.3.1"),
    "apnf::1.3.2.5": (N, "campos de un formulario («FÓRMULA I/II»): 24 párrafos de uno o dos renglones"),
    "cedin::7.1.3.2": (D, "«La documentación deberá incluir… la refacción, ampliación o mejora»: puede ser del ítem"),
    "cirmo3::1.2.11.3": (N, "cuerpo del ítem «1.2.11.3. Impresiones.»: el ítem queda con su título solo"),
    "cirmo3::1.2.23.3": (N, "cuerpo del ítem «1.2.23.3. Impresiones.»: el ítem queda con su título solo"),
    "consyr::3.4.4": (C, "«No será de aplicación lo previsto en el presente punto…»: vale para 3.4"),
    "cryl::4.2.2": (C, "horarios de IDP e IRM y disponibilidad de los pagos: vale para 4.2"),
    "cryl::12.2": (N, "modelo de nota (destinatario, cuerpo, saludo, firmas)"),
    "ctacor::1.3.2": (C, "«Sin perjuicio de lo expuesto anteriormente…»: vale para 1.3"),
    "ctavis::8.2.1.4": (C, "mecanismos de cierre de la cuenta: vale para 8.2.1"),
    "depinv::1.7.2.2": (C, "«Las entidades deberán tener implementado mecanismos de seguridad…»: vale para 1.7.2"),
    "depinv::1.9.2": (C, "publicación de la UVA y la UVI, importe a percibir, moneda: vale para 1.9"),
    "efemin::2.3.2": (C, "«No se exigirá integración mínima diaria para los depósitos en títulos…»: vale para 2.3"),
    "evacre::2.1.2": (D, "«Se considerará la última calificación informada.»: habla de la calificación de 2.1.2"),
    "fimipyme::4.3.3": (C, "«…de los puntos 4.3.2. y 4.3.3.»: vale para los dos ítems"),
    "fimipyme::5.1.2": (C, "TNA de los créditos con reintegros: vale para las tasas de 5.1"),
    "finsec::5.1.2": (C, "«…según lo previsto en los puntos anteriores»: vale para 5.1"),
    "finsec::5.2.5": (C, "«…según las situaciones previstas»: vale para 5.2"),
    "garant::1.2.8.2": (C, "remite al «anteúltimo párrafo del punto 1.2.9»: vale para 1.2.8"),
    "garant::1.2.9.4": (C, "son los párrafos finales de 1.2.9 a los que remite 1.2.8.2"),
    "gerc::2.4.3": (N, "título del ítem partido («…de la» / «SEFyC.») y una tabla: el ítem queda con medio título"),
    "gescre::1.2.8.2": (N, "modelo de declaración jurada"),
    "gracre::6.7.2": (C, "excesos admitidos y facilidades adicionales: vale para 6.7"),
    "inspag::3.3.2": (N, "modelo de nota (cuerpo, saludo, firma)"),
    "manori::1.1.6.5": (C, "«…sólo serán de aplicación obligatoria las pautas previstas en el punto 1.1.6.4.»"),
    "manori::3.5.2": (N, "formulario («PLANILLA DE APROBACIÓN Y ANÁLISIS»): rótulos de casilleros"),
    "manual::2.3.2": (D, "fórmulas del cálculo exponencial y su explicación: pueden ser del ítem"),
    "ratio::5.2.1.5": (C, "«Sin perjuicio de los supuestos de renovación previstos precedentemente…»"),
    "ri2_ae::3.3": (N, "cuerpo de la sección 5, que E0 no abrió: el ítem termina en «5.1. Inscripción.»"),
    "ri2_ae::14.3": (N, "cuerpo del ítem (informes del auditor, 298 renglones de las pp. 28-43), con puntos tragados"),
    "ri2_pm::1.6": (D, "el párrafo «Las casas de cambio…» de S1-bis (ri2_pm quedó fuera de esa lectura)"),
    "ri_cc::R5::2.2.1.2": (D, "«Apoderado / tutor / curador o Representante legal»: un bloque de datos con título"),
    "ri_ot::13.4": (N, "bloque con título propio («Criterios de consistencia»), como el de ri_oc"),
    "ri_pnp::5.7": (N, "otra parte del documento («II – INSTRUCCIONES GENERALES»)"),
    "ri_rml::1.4.2": (D, "las columnas están a 14 pt; «Para el punto 1.4.2. el traslado…» es del ítem"),
    "ri_spi::C.1.3": (N, "los anexos I y II"),
    "seggar::5.3.5": (C, "leyenda de la garantía en los documentos y la publicidad: vale para 5.3"),
    "seguef::2.1.6.2": (C, "«…los sistemas preventivos mencionados en el punto 2.1.6.»"),
    "seguef::2.9.2": (C, "«Se recomienda adoptar el sistema de energía supletoria…»: vale para 2.9"),
    "snp_cec::9.1.3.3": (C, "«…los horarios establecidos en los incisos 9.1.3.1. a 9.1.3.2.»"),
    "snp_mep::3.1.1.2": (C, "«En este ambiente…»: el ambiente es 3.1.1"),
    "snp_mep::3.1.2.2": (C, "«En este ambiente…»: el ambiente es 3.1.2"),
    "snp_mep::4.6.2": (C, "«Además, se proporciona información adicional sobre:»: vale para 4.6"),
    "snp_psp::1.3.2.2": (C, "«Asimismo, se tendrá en consideración…»: vale para 1.3.2"),
    "snp_tr_nc::5.2.3.2": (C, "«El BCRA ejercerá sus funciones de vigilancia monitoreando estos precios…»"),
    "tasint::3.3.2": (C, "«En las expresiones anteriores se entiende»: las definiciones valen para las fórmulas de 3.3"),
}


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def unidad(ch: dict, uid: str):
    if uid in ch:
        return ch[uid]
    ps = sorted((i for i in ch if i.startswith(uid + "::parte")), key=lambda i: int(i.rsplit("parte", 1)[1]))
    if not ps:
        return None
    return {"texto": "\n".join(ch[i]["texto"] for i in ps),
            "paginas": sorted({p for i in ps for p in ch[i]["paginas"]}), "ids": ps}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("antes", "despues", "planilla_116", "out_json", "out_md"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    leidos = {r["id"]: r["marca"] for r in csv.DictReader(open(a.planilla_116, encoding="utf-8"), delimiter="\t")}
    listas: dict = collections.OrderedDict()
    for p in sorted(a.despues.glob("estructura_*.json")):
        e = jl(p)
        for x in e["avisos"]:
            if x["tipo"] == "cierre_al_margen_r5a":
                listas.setdefault((e["to"], x.get("prefijo") or "", x["item"]), []).append(x)
    filas = []
    for (to, pref, item), evs in listas.items():
        A = {c["id"]: c for c in jl(a.antes / f"chunks_{to}.json")}
        B = {c["id"]: c for c in jl(a.despues / f"chunks_{to}.json")}
        base = f"{to}::{pref}::" if pref else f"{to}::"
        iid = base + item
        padre = item.rsplit(".", 1)[0]
        etiqueta_padre = padre if "." in padre else "S" + padre
        cid = base + etiqueta_padre + "::cierre"
        origen = f"{pref}::{padre}" if pref else padre
        origen_s = f"{pref}::{etiqueta_padre}" if pref else etiqueta_padre
        an, de = unidad(A, iid), unidad(B, iid)
        herederos = sorted(i for i, c in B.items() if any(t["tipo"] == "cierre" and t["unidad_origen"] in (origen, origen_s)
                                                          for t in c["herencia"]))
        rot, txt = evs[0]["columna_rotulos"], evs[0]["columna_texto"]
        lec = ("caso", "uno de los 9 casos del mecanismo 1 (S1-bis)") if iid in CASOS else LECTURA.get(iid, (None, None))
        filas.append({"lista": iid, "to": to, "tanda1": to in TANDA1, "caso_del_mandato": iid in CASOS,
                      "leida_en_S1-bis": leidos.get(iid), "paginas": de["paginas"],
                      "columna_rotulos": rot, "columna_texto": txt,
                      "sangria": round(txt - rot, 1) if txt is not None else None,
                      "parrafos_movidos": len(evs), "renglones_movidos": sum(x["renglones"] for x in evs),
                      "primeros_renglones": [x["texto"][:90] for x in evs],
                      "renglones_del_item": [len(an["texto"].split("\n")), len(de["texto"].split("\n"))],
                      "queda_al_final_del_item": de["texto"].split("\n")[-1][:90],
                      "cierre": cid, "cierre_nuevo": unidad(A, cid) is None, "unidades_que_heredan_el_cierre": len(herederos),
                      "lectura": lec[0], "nota": lec[1]})
    faltan = [f["lista"] for f in filas if f["lectura"] is None]
    if faltan:
        raise SystemExit(f"listas sin lectura: {faltan}")
    resumen = {"listas": len(filas), "tos": len({f["to"] for f in filas}),
               "parrafos": sum(f["parrafos_movidos"] for f in filas),
               "renglones": sum(f["renglones_movidos"] for f in filas),
               "por_lectura": dict(collections.Counter(f["lectura"] for f in filas)),
               "tanda1_fuera_de_los_casos": dict(collections.Counter(f["lectura"] for f in filas
                                                                     if f["tanda1"] and not f["caso_del_mandato"])),
               "cierres_nuevos": sum(f["cierre_nuevo"] for f in filas)}
    a.out_json.write_text(json.dumps({"resumen": resumen, "filas": filas}, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    md = ["# R5-a en los 152: las listas que cambia, con mi lectura (S0-5a)", "",
          "Generado por `s0_5/scripts/lectura_r5a_S0-5a.py` sobre la salida de S0-4b (antes) y la de S0-5a (después). "
          "La lectura es mía, a la vista del texto de la salida y de las columnas, sin abrir la página, y no está "
          "adjudicada. Sangría: columna del texto menos columna de los rótulos, en pt.", "",
          f"Resumen: {json.dumps(resumen, ensure_ascii=False)}", "",
          "| lista | tanda 1 | pp. | rótulos / texto (sangría) | párrafos / renglones | heredan | lectura | nota |",
          "|---|---|---|---|---|---|---|---|"]
    for f in filas:
        md.append(f"| `{f['lista']}` | {'sí' if f['tanda1'] else ''} | {','.join(map(str, f['paginas']))} | "
                  f"{f['columna_rotulos']} / {f['columna_texto']} ({f['sangria']}) | {f['parrafos_movidos']} / "
                  f"{f['renglones_movidos']} | {f['unidades_que_heredan_el_cierre']} | {f['lectura']} | {f['nota']} |")
    a.out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
