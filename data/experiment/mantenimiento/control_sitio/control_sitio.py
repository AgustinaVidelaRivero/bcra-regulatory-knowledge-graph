"""
control_sitio.py — U-MANT, etapa M2 (b y c): control de los supuestos del
sitio del BCRA contra una línea de base, con aviso.

El job de actualización (data/experiment/job_actualizacion/) y E0 descansan en
supuestos sobre lo que publica el sitio: la forma del endpoint del índice, las
cuatro claves de cada entrada, cuántas entradas hay, el patrón de URL de los
PDFs y que las regex de portada, de pie y de marcadores de página sigan
acertando sobre los PDFs. Este script mide esos supuestos y los compara contra
`linea_base.json`. Si alguno se rompe, escribe `aviso.md` al frente de la
corrida y sale con código 1.

NO toca la red: recibe un índice ya descargado y un directorio de PDFs. La
corrida contra el sitio (M3) descarga aparte y llama a este control.

NO escribe fuera de --salida (y de --linea-base al construirla). Lee en solo
lectura el job (`lib_job.py`, importado), E0 (`e0_lib.py`, importado), el
índice congelado y los PDFs.

Supuestos (declaración completa en supuestos_sitio.md):
  S1  forma de la respuesta del endpoint del índice
  S2  las cuatro claves de cada entrada (titulo, titulo_truncado, archivo, url)
  S3  cantidad de entradas y de TOs únicos (158 y 157)
  S4  patrón de URL de los PDFs
  S5  acierto de la regex de portada de lib_job (RE_PORTADA)
  S6  acierto de la regex de pie de lib_job (RE_PIE)
  S7  acierto de los marcadores de página de E0 (RE_PIE de e0_lib)
Si S1 se rompe, S2 a S4 no se miden (no hay entradas que medir) y se informan
como «no medido».

Uso, desde la raíz del repo:
  construir la línea de base (sin red):
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
      data/experiment/mantenimiento/control_sitio/control_sitio.py \\
      --construir-linea-base data/experiment/mantenimiento/control_sitio/linea_base.json
  controlar un índice y, si se pasan, sus PDFs:
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
      data/experiment/mantenimiento/control_sitio/control_sitio.py \\
      --indice <indice_crudo.json> [--pdfs <dir con <id>.pdf>] --salida <dir> \\
      [--remedir-todo]

Códigos de salida: 0 sin supuestos rotos; 1 algún supuesto roto (aviso.md
escrito); 2 error de uso o de insumos.

Medición por sha: un PDF cuyo sha256 es el de la línea de base reutiliza la
medición de la línea de base (la medición es función de los bytes del PDF).
--remedir-todo la recalcula igual.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                    # control_sitio/
REPO = AQUI.parents[3]
JOB_CODE = REPO / "data" / "experiment" / "job_actualizacion" / "code"
E0_CODE = REPO / "data" / "experiment" / "reextraccion_v2" / "e0_chunking"
CORRIDA_BASE = REPO / "data" / "experiment" / "job_actualizacion" / "corridas" / "2026-09-07"
INDICE_CONGELADO = REPO / "data" / "experiment" / "escalado_prep" / "indice_oficial_raw.json"
LINEA_BASE_DEFAULT = AQUI / "linea_base.json"

for _p in (JOB_CODE, E0_CODE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import lib_job as L      # noqa: E402 — solo lectura (unidad cerrada)
import e0_lib as E0      # noqa: E402 — solo lectura

CLAVES_ENTRADA = ("archivo", "titulo", "titulo_truncado", "url")
LISTAS = tuple(c for _, c in L.CATEGORIAS)               # textos_ordenados, regimenes_informativos
RE_URL = re.compile(r"^https://www\.bcra\.gob\.ar/archivos/Pdfs/Texord/(?P<archivo>[^/]+)$")
RE_EXT = re.compile(r"\.pdf$", re.IGNORECASE)
UMBRAL_S7 = 0.5     # aviso si la fracción de páginas con marcador cae por debajo
                    # de la mitad de la de la línea de base

NOMBRES = {
    "S1": "forma de la respuesta del endpoint del índice",
    "S2": "cuatro claves de cada entrada del índice",
    "S3": "cantidad de entradas y de TOs únicos del índice",
    "S4": "patrón de URL de los PDFs",
    "S5": "acierto de la regex de portada de lib_job (RE_PORTADA)",
    "S6": "acierto de la regex de pie de lib_job (RE_PIE)",
    "S7": "acierto de los marcadores de página de E0 (RE_PIE de e0_lib)",
}

# Qué depende de cada supuesto (tabla de M1:
# data/experiment/mantenimiento/tabla_reprocesamiento.md, y el job).
DEPENDENCIAS = {
    "S1": "job de actualización: correr_job.py aborta sin las dos listas (:169-174) y no "
          "puede distinguir bajas de fallas; sin índice no hay detección de TOs nuevos ni "
          "modificados (tabla de M1, filas F17, F18a y F18b).",
    "S2": "lib_job.leer_indice usa titulo, archivo y url de cada entrada (:92-110); el id "
          "del TO sale de `archivo` (id_corto); la tabla de deltas y el inventario quedan "
          "sin identidad (filas F17 y F18 de la tabla de M1).",
    "S3": "alcance del job (157 TOs): altas y bajas del índice; un TO nuevo es la fila F17 "
          "de la tabla de M1 y uno que desaparece sale del ensamblado.",
    "S4": "descarga de los PDFs del job (correr_job.py:200-205) y regla de identidad por "
          "nombre de archivo; con otro patrón, el job puede no encontrar ni identificar los PDFs.",
    "S5": "procedencia por documento (lib_job.procedencia, portada); fuente 1 del "
          "procedimiento de empalme (procedimiento_empalme.md).",
    "S6": "procedencia por página (pie): el mapeo fino delta → páginas → unidades del "
          "diseño del job (§5.b) y la atribución de cada página a su Comunicación.",
    "S7": "E0 (e0_lib.separar_encabezado_pie, :534-536): un pie que E0 no reconoce entra "
          "al texto de las unidades de esa página; cambian las claves de E1 y E3 de esas "
          "unidades (tabla de M1, filas F01 y F18b) y el grafo hereda texto de pie.",
}


# ------------------------------------------------------------------------- #
# Utilidades                                                                 #
# ------------------------------------------------------------------------- #

def sha256_archivo(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel(p: Path) -> str:
    p = Path(p).resolve()
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


# ------------------------------------------------------------------------- #
# Medición del índice (S1 a S4)                                              #
# ------------------------------------------------------------------------- #

def medir_indice(datos: bytes) -> dict:
    """Mide S1 a S4 sobre los bytes crudos del índice."""
    out: dict = {"sha256": hashlib.sha256(datos).hexdigest(), "bytes": len(datos)}
    try:
        crudo = json.loads(datos.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — se informa textual
        out["S1"] = {"json": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
        return out
    if not isinstance(crudo, dict):
        out["S1"] = {"json": True, "tipo": type(crudo).__name__}
        return out
    out["S1"] = {
        "json": True, "tipo": "dict",
        "claves_nivel_superior": sorted(crudo),
        "success": crudo.get("success"),
        "listas": {c: isinstance(crudo.get(c), list) for c in LISTAS},
    }
    if not all(out["S1"]["listas"].values()):
        return out
    entradas = [(c, it) for c in LISTAS for it in crudo[c]]
    # S2: claves de cada entrada
    distintas = []
    for c, it in entradas:
        claves = sorted(it) if isinstance(it, dict) else None
        if claves != list(CLAVES_ENTRADA):
            distintas.append({"lista": c, "archivo": it.get("archivo") if isinstance(it, dict) else None,
                              "claves": claves})
    out["S2"] = {"entradas": len(entradas),
                 "con_las_cuatro_claves": len(entradas) - len(distintas),
                 "distintas": distintas}
    # S3: cantidades e identidad (misma regla que lib_job.leer_indice: dedup por URL)
    vistas, ids, dup = set(), set(), []
    for c, it in entradas:
        if not isinstance(it, dict):
            continue
        url = it.get("url")
        if url in vistas:
            dup.append(url)
            continue
        vistas.add(url)
        if isinstance(it.get("archivo"), str):
            ids.add(L.id_corto(it["archivo"]))
    out["S3"] = {"por_lista": {c: len(crudo[c]) for c in LISTAS},
                 "entradas": len(entradas), "urls_unicas": len(vistas),
                 "duplicadas": sorted(d for d in dup if isinstance(d, str)),
                 "ids": sorted(ids)}
    # S4: patrón de URL
    fuera = []
    for c, it in entradas:
        url = it.get("url") if isinstance(it, dict) else None
        m = RE_URL.match(url) if isinstance(url, str) else None
        ok = bool(m) and m.group("archivo") == it.get("archivo") and bool(RE_EXT.search(url))
        if not ok:
            fuera.append({"lista": c, "archivo": it.get("archivo") if isinstance(it, dict) else None,
                          "url": url})
    out["S4"] = {"patron": RE_URL.pattern, "entradas": len(entradas),
                 "con_el_patron": len(entradas) - len(fuera), "fuera_del_patron": fuera}
    return out


# ------------------------------------------------------------------------- #
# Medición de un PDF (S5 a S7)                                               #
# ------------------------------------------------------------------------- #

def _lineas_e0(page) -> list[str]:
    """Réplica de la agrupación de e0_lib.extraer_lineas (:300-334) para UNA
    página: palabras agrupadas por `top` con la tolerancia E0.TOL_TOP, ordenadas
    por x0 y unidas por espacio. El selftest la compara con extraer_lineas."""
    grupos: list[tuple[float, list[dict]]] = []
    for w in page.extract_words():
        for t, ws in grupos:
            if abs(t - w["top"]) <= E0.TOL_TOP:
                ws.append(w)
                break
        else:
            grupos.append((w["top"], [w]))
    return [" ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"]))
            for _, ws in sorted(grupos, key=lambda g: g[0])]


def marcador_e0(lineas: list[str]) -> bool:
    """True si E0 descartaría al menos la última línea como pie
    (e0_lib.separar_encabezado_pie, :534-536)."""
    return bool(lineas) and any(p.match(lineas[-1].strip()) for p in E0.RE_PIE)


def medir_pdf(pdf: Path) -> dict:
    """S5 y S6 con lib_job.procedencia (mismas páginas de sondeo y mismas
    regex que el job); S7 con los marcadores de E0 sobre esas mismas páginas."""
    import pdfplumber
    out: dict = {"sha256": sha256_archivo(pdf)}
    try:
        with pdfplumber.open(str(pdf)) as doc:
            total = len(doc.pages)
            idxs = L.paginas_de_sondeo(total)
            por_pagina = {}
            for i in idxs:
                lineas = _lineas_e0(doc.pages[i])
                if lineas:
                    por_pagina[str(i + 1)] = marcador_e0(lineas)
    except Exception as exc:  # noqa: BLE001
        out["lectura"] = f"fallida: {type(exc).__name__}: {str(exc)[:200]}"
        return out
    proc = L.procedencia(pdf)
    out["lectura"] = "ok"
    out["paginas"] = total
    out["paginas_sondeo"] = [i + 1 for i in idxs]
    out["S5_portada"] = proc.get("portada_comunicacion") is not None
    out["portada_comunicacion"] = proc.get("portada_comunicacion")
    out["S6_pie"] = bool(proc.get("pie_por_pagina"))
    out["pie_paginas"] = sorted(int(p) for p in (proc.get("pie_por_pagina") or {}))
    out["limite_declarado"] = proc.get("limite_declarado")
    out["S7_paginas_con_texto"] = len(por_pagina)
    out["S7_paginas_con_marcador"] = sum(1 for v in por_pagina.values() if v)
    return out


def _fraccion(m: dict) -> float | None:
    n = m.get("S7_paginas_con_texto") or 0
    return (m.get("S7_paginas_con_marcador", 0) / n) if n else None


# ------------------------------------------------------------------------- #
# Línea de base                                                              #
# ------------------------------------------------------------------------- #

def construir_linea_base(destino: Path) -> dict:
    ind_corrida = CORRIDA_BASE / "indice_crudo.json"
    med_cong = medir_indice(INDICE_CONGELADO.read_bytes())
    med_corr = medir_indice(ind_corrida.read_bytes())
    base_job = L.linea_base()                         # 157 TOs, PDFs congelados, solo lectura
    obs = json.loads((CORRIDA_BASE / "observaciones.json").read_text(encoding="utf-8"))
    por_to: dict = {}
    for ident in sorted(base_job):
        pdf_cong = Path(base_job[ident]["pdf"])
        m_cong = medir_pdf(pdf_cong)
        pdf_corr = CORRIDA_BASE / "pdfs" / f"{ident}.pdf"
        reg = {"pdf_congelado": rel(pdf_cong), "pdf_corrida": rel(pdf_corr),
               "id_interno": base_job[ident]["id_interno"]}
        if obs.get(ident, {}).get("sha256") == m_cong["sha256"]:
            reg["medicion"] = m_cong
            reg["corrida_igual_a_congelado"] = True
        else:
            m_corr = medir_pdf(pdf_corr)
            reg["medicion"] = m_corr
            reg["medicion_congelado"] = m_cong
            reg["corrida_igual_a_congelado"] = False
        if reg["medicion"]["sha256"] != obs[ident]["sha256"]:
            raise RuntimeError(f"{ident}: el PDF de la corrida no tiene el sha de observaciones.json")
        por_to[ident] = reg

    def _cuenta(campo):
        return sum(1 for r in por_to.values() if r["medicion"].get(campo))

    supuestos = {
        "S1": {k: med_corr["S1"][k] for k in ("claves_nivel_superior", "success", "listas")},
        "S2": {"claves": list(CLAVES_ENTRADA), "entradas": med_corr["S2"]["entradas"],
               "con_las_cuatro_claves": med_corr["S2"]["con_las_cuatro_claves"]},
        "S3": {k: med_corr["S3"][k] for k in ("por_lista", "entradas", "urls_unicas", "duplicadas", "ids")},
        "S4": {"patron": RE_URL.pattern, "entradas": med_corr["S4"]["entradas"],
               "con_el_patron": med_corr["S4"]["con_el_patron"]},
        "S5": {"tos_con_acierto": _cuenta("S5_portada"), "tos": len(por_to),
               "sin_acierto": sorted(i for i, r in por_to.items() if not r["medicion"].get("S5_portada"))},
        "S6": {"tos_con_acierto": _cuenta("S6_pie"), "tos": len(por_to),
               "sin_acierto": sorted(i for i, r in por_to.items() if not r["medicion"].get("S6_pie"))},
        "S7": {"tos_con_algun_marcador": sum(1 for r in por_to.values()
                                             if r["medicion"].get("S7_paginas_con_marcador")),
               "tos": len(por_to),
               "paginas_sondeadas_con_texto": sum(r["medicion"].get("S7_paginas_con_texto", 0)
                                                  for r in por_to.values()),
               "paginas_con_marcador": sum(r["medicion"].get("S7_paginas_con_marcador", 0)
                                           for r in por_to.values()),
               "sin_marcador": sorted(i for i, r in por_to.items()
                                      if not r["medicion"].get("S7_paginas_con_marcador"))},
    }
    diferencias_congelado = {
        i: {k: [r["medicion_congelado"].get(k), r["medicion"].get(k)]
            for k in ("S5_portada", "S6_pie", "S7_paginas_con_marcador", "S7_paginas_con_texto",
                      "portada_comunicacion")
            if r["medicion_congelado"].get(k) != r["medicion"].get(k)}
        for i, r in por_to.items() if not r["corrida_igual_a_congelado"]}
    lb = {
        "unidad": "U-MANT M2 — línea de base del control del sitio",
        "fuentes": {
            "indice_congelado": {"ruta": rel(INDICE_CONGELADO), "sha256": med_cong["sha256"]},
            "indice_corrida_2026_09_07": {"ruta": rel(ind_corrida), "sha256": med_corr["sha256"]},
            "indices_byte_identicos": med_cong["sha256"] == med_corr["sha256"],
            "pdfs_congelados": "escalado_prep/pdfs/<id>.pdf (152) y data/experiment/subset/ (5), "
                               "vía lib_job.linea_base()",
            "pdfs_corrida": rel(CORRIDA_BASE / "pdfs"),
            "referencia_del_control": "índice y PDFs de la corrida del 2026-09-07 (último "
                                      "estado observado del sitio)",
        },
        "parametros": {
            "claves_entrada": list(CLAVES_ENTRADA), "listas": list(LISTAS),
            "re_url": RE_URL.pattern, "re_ext": RE_EXT.pattern,
            "re_portada_lib_job": L.RE_PORTADA.pattern, "re_pie_lib_job": L.RE_PIE.pattern,
            "re_pie_e0": [p.pattern for p in E0.RE_PIE], "tol_top_e0": E0.TOL_TOP,
            "paginas_cabecera": L.PAGS_CABECERA, "paginas_muestra": L.PAGS_MUESTRA,
            "umbral_s7": UMBRAL_S7,
        },
        "supuestos": supuestos,
        "corrida_vs_congelado": {
            "tos_con_pdf_distinto": sorted(diferencias_congelado),
            "diferencias_de_medicion": {i: d for i, d in diferencias_congelado.items() if d},
        },
        "por_to": por_to,
    }
    destino.write_text(json.dumps(lb, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
    return lb


# ------------------------------------------------------------------------- #
# Control                                                                    #
# ------------------------------------------------------------------------- #

def comparar_indice(med: dict, sup: dict) -> tuple[dict, list[dict]]:
    """Estado por supuesto (S1 a S4) y lista de rotos."""
    estado, rotos = {}, []

    def roto(sid, base, obs, detalle=None):
        estado[sid] = "roto"
        rotos.append({"supuesto": sid, "nombre": NOMBRES[sid], "linea_base": base,
                      "observado": obs, "detalle": detalle})

    s1 = med.get("S1", {})
    b1 = sup["S1"]
    obs1 = {k: s1.get(k) for k in ("json", "tipo", "claves_nivel_superior", "success", "listas", "error")
            if k in s1}
    if (not s1.get("json") or s1.get("tipo") != "dict"
            or s1.get("claves_nivel_superior") != b1["claves_nivel_superior"]
            or s1.get("success") != b1["success"] or s1.get("listas") != b1["listas"]):
        roto("S1", b1, obs1)
    else:
        estado["S1"] = "ok"
    if "S2" not in med:
        for sid in ("S2", "S3", "S4"):
            estado[sid] = "no medido (S1 roto)"
        return estado, rotos
    s2 = med["S2"]
    if s2["distintas"]:
        roto("S2", {"entradas_con_las_cuatro_claves": sup["S2"]["con_las_cuatro_claves"],
                    "claves": sup["S2"]["claves"]},
             {"entradas": s2["entradas"], "con_las_cuatro_claves": s2["con_las_cuatro_claves"]},
             s2["distintas"][:20])
    else:
        estado["S2"] = "ok"
    s3, b3 = med["S3"], sup["S3"]
    if any(s3[k] != b3[k] for k in ("por_lista", "entradas", "urls_unicas", "duplicadas", "ids")):
        roto("S3", {k: b3[k] for k in ("por_lista", "entradas", "urls_unicas", "duplicadas")}
             | {"ids": len(b3["ids"])},
             {k: s3[k] for k in ("por_lista", "entradas", "urls_unicas", "duplicadas")}
             | {"ids": len(s3["ids"])},
             {"ids_nuevos": sorted(set(s3["ids"]) - set(b3["ids"])),
              "ids_ausentes": sorted(set(b3["ids"]) - set(s3["ids"]))})
    else:
        estado["S3"] = "ok"
    s4 = med["S4"]
    if s4["fuera_del_patron"]:
        roto("S4", {"con_el_patron": sup["S4"]["con_el_patron"], "patron": sup["S4"]["patron"]},
             {"entradas": s4["entradas"], "con_el_patron": s4["con_el_patron"]},
             s4["fuera_del_patron"][:20])
    else:
        estado["S4"] = "ok"
    return estado, rotos


def comparar_pdfs(mediciones: dict, base: dict) -> tuple[dict, list[dict], dict]:
    estado, rotos, info = {}, [], {"tos_sin_linea_base": [], "lecturas_fallidas": []}
    fallos = {"S5": [], "S6": [], "S7": []}
    for ident, m in sorted(mediciones.items()):
        b = base["por_to"].get(ident)
        if b is None:
            info["tos_sin_linea_base"].append(ident)
            continue
        bm = b["medicion"]
        if m.get("lectura") != "ok":
            info["lecturas_fallidas"].append(ident)
            for sid in fallos:
                fallos[sid].append({"to": ident, "linea_base": "legible", "observado": m.get("lectura")})
            continue
        if bm.get("S5_portada") and not m.get("S5_portada"):
            fallos["S5"].append({"to": ident, "linea_base": bm.get("portada_comunicacion"),
                                 "observado": m.get("portada_comunicacion"),
                                 "limite_declarado": m.get("limite_declarado")})
        if bm.get("S6_pie") and not m.get("S6_pie"):
            fallos["S6"].append({"to": ident, "linea_base": bm.get("pie_paginas"),
                                 "observado": m.get("pie_paginas")})
        fb, fm = _fraccion(bm), _fraccion(m)
        if bm.get("S7_paginas_con_marcador") and (fm is None or fm < UMBRAL_S7 * fb):
            fallos["S7"].append({
                "to": ident,
                "linea_base": f"{bm['S7_paginas_con_marcador']} de {bm['S7_paginas_con_texto']}",
                "observado": f"{m.get('S7_paginas_con_marcador', 0)} de {m.get('S7_paginas_con_texto', 0)}"})
    total = {"S5": base["supuestos"]["S5"], "S6": base["supuestos"]["S6"], "S7": base["supuestos"]["S7"]}
    for sid, fs in fallos.items():
        if not mediciones:
            estado[sid] = "no medido (sin PDFs)"
        elif fs:
            estado[sid] = "roto"
            resumen_base = ({"tos_con_acierto": total[sid]["tos_con_acierto"], "tos": total[sid]["tos"]}
                            if sid != "S7" else
                            {"tos_con_algun_marcador": total[sid]["tos_con_algun_marcador"],
                             "tos": total[sid]["tos"], "umbral": f"fracción < {UMBRAL_S7} × la de la línea de base"})
            rotos.append({"supuesto": sid, "nombre": NOMBRES[sid], "linea_base": resumen_base,
                          "observado": {"tos_medidos": len(mediciones), "tos_que_fallan": len(fs)},
                          "detalle": fs})
        else:
            estado[sid] = "ok"
    return estado, rotos, info


def escribir_aviso(destino: Path, rotos: list[dict], contexto: dict) -> None:
    lineas = ["# AVISO — control de los supuestos del sitio del BCRA", "",
              f"Índice: `{contexto['indice']}` (sha256 `{contexto['sha256_indice']}`).",
              f"PDFs: {contexto['pdfs']}.", "",
              f"Supuestos rotos: {len(rotos)} ({', '.join(r['supuesto'] for r in rotos)}).",
              "El control no actualiza nada: compara y avisa (mandato U-MANT, decisiones 2 y 3).", ""]
    for r in rotos:
        lineas += [f"## {r['supuesto']} — {r['nombre']}", "",
                   f"- Valor de la línea de base: `{json.dumps(r['linea_base'], ensure_ascii=False)}`",
                   f"- Valor observado: `{json.dumps(r['observado'], ensure_ascii=False)}`",
                   f"- Qué depende de este supuesto: {DEPENDENCIAS[r['supuesto']]}"]
        if r.get("detalle"):
            det = r["detalle"][:20] if isinstance(r["detalle"], list) else r["detalle"]
            lineas.append(f"- Detalle (listas: hasta 20 elementos): `{json.dumps(det, ensure_ascii=False)}`")
        lineas.append("")
    destino.write_text("\n".join(lineas), encoding="utf-8")


def parametros_distintos(base: dict) -> dict:
    """Regex y tolerancias del código importado contra las de la línea de
    base. E0 y el job pueden editarse en otras unidades: si cambian, medir con
    ellos compararía peras con manzanas."""
    actuales = {"re_portada_lib_job": L.RE_PORTADA.pattern, "re_pie_lib_job": L.RE_PIE.pattern,
                "re_pie_e0": [p.pattern for p in E0.RE_PIE], "tol_top_e0": E0.TOL_TOP,
                "paginas_cabecera": L.PAGS_CABECERA, "paginas_muestra": L.PAGS_MUESTRA}
    return {k: {"linea_base": base["parametros"].get(k), "codigo": v}
            for k, v in actuales.items() if base["parametros"].get(k) != v}


def controlar(indice: Path, pdfs: Path | None, salida: Path, linea_base: Path,
              remedir_todo: bool = False) -> int:
    base = json.loads(linea_base.read_text(encoding="utf-8"))
    distintos = parametros_distintos(base)
    if distintos:
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "resultado_control.json").write_text(json.dumps(
            {"veredicto": "FRENO_PARAMETROS", "parametros_distintos": distintos},
            ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("FRENO: las regex o tolerancias del código no son las de la línea de base: "
              + json.dumps(distintos, ensure_ascii=False), file=sys.stderr)
        return 2
    datos = indice.read_bytes()
    med = medir_indice(datos)
    estado, rotos = comparar_indice(med, base["supuestos"])
    mediciones: dict = {}
    reutilizadas = 0
    if pdfs is not None:
        for pdf in sorted(Path(pdfs).glob("*.pdf")):
            ident = pdf.stem
            b = base["por_to"].get(ident)
            sha = sha256_archivo(pdf)
            if b is not None and not remedir_todo and sha == b["medicion"]["sha256"]:
                mediciones[ident] = b["medicion"]
                reutilizadas += 1
            else:
                mediciones[ident] = medir_pdf(pdf)
    e2, r2, info = comparar_pdfs(mediciones, base)
    estado |= e2
    rotos += r2
    salida.mkdir(parents=True, exist_ok=True)
    resultado = {
        "indice": rel(indice), "sha256_indice": med["sha256"],
        "pdfs": rel(pdfs) if pdfs is not None else None,
        "linea_base": rel(linea_base),
        "pdfs_medidos": len(mediciones), "mediciones_reutilizadas_por_sha": reutilizadas,
        "pdfs_ausentes_del_directorio": (sorted(set(base["por_to"]) - set(mediciones))
                                         if pdfs is not None else None),
        "estado_por_supuesto": dict(sorted(estado.items())),
        "rotos": rotos, "info": info,
        "veredicto": "AVISO" if rotos else "OK",
    }
    (salida / "resultado_control.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    aviso = salida / "aviso.md"
    if rotos:
        escribir_aviso(aviso, rotos, {"indice": rel(indice), "sha256_indice": med["sha256"],
                                      "pdfs": f"`{rel(pdfs)}`" if pdfs is not None else "no controlados"})
    return 1 if rotos else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--construir-linea-base", type=Path, default=None)
    ap.add_argument("--indice", type=Path)
    ap.add_argument("--pdfs", type=Path, default=None)
    ap.add_argument("--salida", type=Path)
    ap.add_argument("--linea-base", type=Path, default=LINEA_BASE_DEFAULT)
    ap.add_argument("--remedir-todo", action="store_true")
    a = ap.parse_args()
    if a.construir_linea_base:
        lb = construir_linea_base(a.construir_linea_base)
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("ids", "sin_acierto", "sin_marcador")}
                          for k, v in lb["supuestos"].items()}, ensure_ascii=False))
        return 0
    if not a.indice or not a.salida:
        ap.error("--indice y --salida son obligatorios (o --construir-linea-base)")
    if (a.salida / "aviso.md").exists() or (a.salida / "resultado_control.json").exists():
        print(f"FRENO: {a.salida} ya tiene una corrida del control; no se sobrescribe.", file=sys.stderr)
        return 2
    if not a.indice.exists() or not a.linea_base.exists() or (a.pdfs is not None and not a.pdfs.is_dir()):
        print("FRENO: falta el índice, la línea de base o el directorio de PDFs.", file=sys.stderr)
        return 2
    codigo = controlar(a.indice, a.pdfs, a.salida, a.linea_base, a.remedir_todo)
    if codigo == 2:
        return 2
    res = json.loads((a.salida / "resultado_control.json").read_text(encoding="utf-8"))
    print("veredicto:", res["veredicto"], "|", json.dumps(res["estado_por_supuesto"], ensure_ascii=False))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
