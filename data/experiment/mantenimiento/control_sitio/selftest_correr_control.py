"""
selftest_correr_control.py — U-MANT, etapa M3: prueba sin red del runner
correr_control_sitio.py, con un cliente simulado que responde desde archivos
locales (el índice y los PDFs de la corrida del job del 2026-09-07).

Casos:
  T1  el índice no responde, sin latido previo   → 3, corrida_fallida.md y aviso_latido.md, 0 PDFs
  T2  el índice no responde, latido de 10 días    → 3, sin aviso_latido.md
  T3  el índice no responde, latido de 50 días    → 3, con aviso_latido.md
  T4  modo índice, índice igual a la línea de base → 0, sin aviso, latido actualizado
  T5  modo índice y PDFs: 304 en todos salvo snp_psp (200, PDF sin su página 1),
      cladeu (200, mismos bytes de la corrida del 07/09) y ri_cc (error)
                                                   → 1, aviso solo S5; 157 pedidos de PDF
                                                     condicionales; snp_psp clasificado F18a + F05
  T6  modo índice y PDFs, índice que no es JSON    → 1, aviso solo S1, 0 PDFs pedidos
Escribe solo bajo --trabajo, que tiene que estar fuera del repo.

Uso, desde la raíz del repo:
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
    data/experiment/mantenimiento/control_sitio/selftest_correr_control.py \\
    --trabajo <dir fuera del repo> --out <json>
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import correr_control_sitio as R  # noqa: E402
import selftest_control_sitio as S  # noqa: E402

FECHA = "2026-10-02"


class ClienteSimulado:
    """Responde desde archivos locales; registra cada pedido y sus cabeceras."""

    def __init__(self, log, plan_indice: str, plan_pdfs: dict, trabajo: Path):
        self.log = log
        self.plan_indice = plan_indice
        self.plan_pdfs = plan_pdfs
        self.trabajo = trabajo
        self.pedidos: list[dict] = []
        self.intentos_http = 0

    def traer(self, url: str, condicionales: dict | None = None) -> dict:
        self.intentos_http += 1
        self.pedidos.append({"url": url, "condicionales": sorted(condicionales or {})})
        if url == R.URL_INDICE:
            if self.plan_indice == "error":
                return {"estado": "error", "error": "URLError: simulado", "intentos": R.INTENTOS}
            datos = (b"<html>no es json</html>" if self.plan_indice == "no_json"
                     else (R.C.CORRIDA_BASE / "indice_crudo.json").read_bytes())
            return {"estado": "ok", "http": 200, "datos": datos, "intentos": 1, "cabeceras": {}}
        ident = R.C.L.id_corto(url.rsplit("/", 1)[1])
        accion = self.plan_pdfs.get(ident, "304")
        if accion == "304":
            return {"estado": "no_modificado", "http": 304, "datos": b"", "intentos": 1, "cabeceras": {}}
        if accion == "error":
            return {"estado": "error", "error": "HTTPError 503", "intentos": R.INTENTOS}
        datos = Path(accion).read_bytes()
        return {"estado": "ok", "http": 200, "datos": datos, "intentos": 1,
                "cabeceras": {"etag": None, "last_modified": None}}


def caso(nombre: str, trabajo: Path, modo: str, plan_indice: str, plan_pdfs: dict,
         latido_dias: int | None) -> tuple[int, Path, ClienteSimulado]:
    base = trabajo / f"base_{nombre}"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    if latido_dias is not None:
        (base / "ultima_ok.txt").write_text(
            (date.fromisoformat(FECHA) - timedelta(days=latido_dias)).isoformat() + "\n", encoding="utf-8")
    hechos = {}

    def fabrica(log):
        hechos["c"] = ClienteSimulado(log, plan_indice, plan_pdfs, trabajo)
        return hechos["c"]
    codigo = R.correr(modo, FECHA, base, fabrica)
    return codigo, base, hechos["c"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    trabajo = a.trabajo.resolve()
    if str(trabajo).startswith(str(R.C.REPO.resolve())):
        print("FRENO: --trabajo tiene que estar fuera del repo.", file=sys.stderr)
        return 2
    trabajo.mkdir(parents=True, exist_ok=True)
    resultados = []

    def registrar(nombre, ok, **datos):
        resultados.append({"caso": nombre, "ok": bool(ok)} | datos)

    for nombre, latido, espera_latido in (("T1", None, True), ("T2", 10, False), ("T3", 50, True)):
        codigo, base, cli = caso(nombre, trabajo, "indice-y-pdfs", "error", {}, latido)
        d = base / FECHA
        registrar(nombre, codigo == 3 and (d / "corrida_fallida.md").exists()
                  and (d / "aviso_latido.md").exists() == espera_latido and len(cli.pedidos) == 1
                  and not (d / "pdfs").exists(),
                  codigo=codigo, pedidos=len(cli.pedidos),
                  aviso_latido=(d / "aviso_latido.md").exists())

    codigo, base, cli = caso("T4", trabajo, "indice", "ok", {}, 50)
    d = base / FECHA
    registrar("T4", codigo == 0 and not (d / "aviso.md").exists() and len(cli.pedidos) == 1
              and R.leer_latido(base) == FECHA,
              codigo=codigo, pedidos=len(cli.pedidos), latido=R.leer_latido(base))

    sin_portada = trabajo / "snp_psp_sin_portada.pdf"
    S.quitar_portada(R.C.CORRIDA_BASE / "pdfs" / "snp_psp.pdf", sin_portada)
    plan = {"snp_psp": str(sin_portada), "cladeu": str(R.C.CORRIDA_BASE / "pdfs" / "cladeu.pdf"),
            "ri_cc": "error"}
    codigo, base, cli = caso("T5", trabajo, "indice-y-pdfs", "ok", plan, None)
    d = base / FECHA
    res = json.loads((d / "resultado_control.json").read_text(encoding="utf-8"))
    ped = json.loads((d / "pedidos.json").read_text(encoding="utf-8"))
    cls = json.loads((d / "clasificacion_cambios.json").read_text(encoding="utf-8"))
    rotos = sorted(r["supuesto"] for r in res["rotos"])
    condicionales_ok = all(p["condicionales"] == ["If-Modified-Since", "If-None-Match"]
                           for p in cli.pedidos[1:])
    estados = {}
    for p in ped.values():
        estados[p["estado"]] = estados.get(p["estado"], 0) + 1
    snp = cls["desde_el_corpus_congelado"].get("snp_psp", {})
    registrar("T5", codigo == 1 and rotos == ["S5"] and len(cli.pedidos) == 158 and condicionales_ok
              and estados == {"descargado": 2, "error": 1, "no_modificado": 154}
              and ped["cladeu"]["igual_a_2026_09_07"] is True
              and cls["cambiaron_desde_la_corrida_del_2026_09_07"] == ["snp_psp"]
              and snp.get("fila_m1") == "F18a + F05",
              codigo=codigo, rotos=rotos, pedidos=len(cli.pedidos), estados=estados,
              condicionales_en_todos_los_pdfs=condicionales_ok,
              clasificacion_snp_psp={k: snp.get(k) for k in ("fila_m1", "clase", "paginas_anterior",
                                                             "paginas_actual", "paginas_viejas_tocadas",
                                                             "paginas_de_unidades_tocadas")},
              clasificados_desde_congelado={k: v["fila_m1"] for k, v in
                                            sorted(cls["desde_el_corpus_congelado"].items())})

    codigo, base, cli = caso("T6", trabajo, "indice-y-pdfs", "no_json", {}, None)
    d = base / FECHA
    res = json.loads((d / "resultado_control.json").read_text(encoding="utf-8"))
    rotos = sorted(r["supuesto"] for r in res["rotos"])
    en_aviso = sorted(set(re.findall(r"^## (S\d)", (d / "aviso.md").read_text(encoding="utf-8"), re.M)))
    registrar("T6", codigo == 1 and rotos == ["S1"] and en_aviso == ["S1"] and len(cli.pedidos) == 1,
              codigo=codigo, rotos=rotos, pedidos=len(cli.pedidos))

    out = {"selftest": "U-MANT M3 — runner del control del sitio, sin red",
           "casos": resultados, "casos_ok": sum(1 for r in resultados if r["ok"]),
           "casos_total": len(resultados)}
    out["veredicto"] = "OK" if out["casos_ok"] == out["casos_total"] else "FRENO"
    texto = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if a.out:
        a.out.write_text(texto, encoding="utf-8")
    for r in resultados:
        print(r["caso"], "OK" if r["ok"] else "MAL", {k: v for k, v in r.items()
                                                    if k in ("codigo", "rotos", "pedidos", "estados")})
    print("VEREDICTO:", out["veredicto"])
    return 0 if out["veredicto"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
