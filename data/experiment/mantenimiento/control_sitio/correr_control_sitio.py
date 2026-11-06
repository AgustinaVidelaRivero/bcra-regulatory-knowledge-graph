"""
correr_control_sitio.py — U-MANT, etapa M3: corrida del control de los
supuestos del sitio del BCRA contra el sitio, y runner del disparo periódico.

Dos modos:
  indice          un pedido: el índice. Controla S1 a S4. Es el modo del
                  disparo mensual (decisión de la autora del 02/10/2026).
  indice-y-pdfs   el índice y, si responde, los PDFs que publica, con pedidos
                  condicionales (If-None-Match con el ETag e If-Modified-Since
                  con el Last-Modified de la corrida del job del 2026-09-07).
                  Controla S1 a S7 y clasifica cada TO que cambió con la tabla
                  de M1 (tabla_reprocesamiento.md). Es el modo de la corrida de M3.

Cortesía (job_actualizacion/diseno_job_actualizacion.md, §6; mismos valores
que correr_job.py:47-54): un pedido cada 0,5 s, uno por vez; 60 s de timeout;
3 intentos por pedido con esperas de 2 y 4 s; modo lento ante 5 respuestas 503
seguidas; User-Agent propio sin datos personales. Si el índice no responde, la
corrida se aborta antes de pedir un solo PDF.

Escribe solo en <base>/<fecha>/ (por defecto control_sitio/corridas/<fecha>/)
y en <base>/ultima_ok.txt. No actualiza inventarios, manifiestos ni PDFs
congelados (mandato U-MANT, decisiones 2 y 3). Los PDFs que vuelven con 200 se
guardan en <base>/<fecha>/pdfs/ (data/experiment/**/*.pdf ya está en
.gitignore:35).

Latido: cada corrida en la que el sitio respondió el índice escribe su fecha en
<base>/ultima_ok.txt. Una corrida que no puede preguntar escribe
corrida_fallida.md y, si la última corrida exitosa tiene más de 45 días (o no
hay ninguna registrada), además aviso_latido.md.

Códigos de salida: 0 sin aviso; 1 aviso (aviso.md o aviso_latido.md); 2 error
de uso, directorio ya existente o parámetros distintos de los de la línea de
base; 3 el índice no respondió.

Uso, desde la raíz del repo (la red solo con --autorizado-red):
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
    data/experiment/mantenimiento/control_sitio/correr_control_sitio.py \\
    --modo indice --autorizado-red
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import control_sitio as C  # noqa: E402

URL_INDICE = "https://www.bcra.gob.ar/api/endpoints/ordenamiento-y-resumenes.php?lang=es"
USER_AGENT = ("AcademicResearchBot/1.0 (control de supuestos del sitio de un corpus "
              "regulatorio; investigacion academica)")
RITMO = 0.5
TIMEOUT = 60
INTENTOS = 3
ESPERA = 2.0
UMBRAL_503 = 5
PAUSA_503 = 60.0
RITMO_LENTO = 1.0
MIN_PDF_BYTES = 1024
DIAS_LATIDO = 45
BASE_CORRIDAS = AQUI / "corridas"
OBSERVACIONES_PREVIAS = C.CORRIDA_BASE / "observaciones.json"
TANDA0_NUEVOS = ("ctacte", "docvig", "lingob", "pagjub", "polcre")


class Cliente:
    """Cliente cortés con pedidos condicionales. Un 304 no es error ni se
    reintenta."""

    def __init__(self, log):
        self.log = log
        self.ultimo = 0.0
        self.ritmo = RITMO
        self.consecutivos_503 = 0
        self.intentos_http = 0

    def _turno(self) -> None:
        falta = self.ritmo - (time.time() - self.ultimo)
        if falta > 0:
            time.sleep(falta)
        self.ultimo = time.time()

    @staticmethod
    def _normalizar(url: str) -> str:
        p = urllib.parse.urlsplit(url)
        return urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%"),
                                        p.query, p.fragment))

    def traer(self, url: str, condicionales: dict | None = None) -> dict:
        ultimo_error = ""
        cab = {"User-Agent": USER_AGENT} | (condicionales or {})
        for intento in range(1, INTENTOS + 1):
            self._turno()
            self.intentos_http += 1
            try:
                req = urllib.request.Request(self._normalizar(url), headers=cab)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    datos = resp.read()
                    self.consecutivos_503 = 0
                    return {"estado": "ok", "http": resp.status, "datos": datos, "intentos": intento,
                            "cabeceras": {"etag": resp.headers.get("ETag"),
                                          "last_modified": resp.headers.get("Last-Modified"),
                                          "content_type": resp.headers.get("Content-Type"),
                                          "content_length": resp.headers.get("Content-Length")}}
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    self.consecutivos_503 = 0
                    return {"estado": "no_modificado", "http": 304, "datos": b"", "intentos": intento,
                            "cabeceras": {"etag": e.headers.get("ETag"),
                                          "last_modified": e.headers.get("Last-Modified")}}
                ultimo_error = f"HTTPError {e.code}"
                if e.code == 503:
                    self.consecutivos_503 += 1
                    if self.consecutivos_503 >= UMBRAL_503 and self.ritmo < RITMO_LENTO:
                        self.log(f"[modo-lento] {UMBRAL_503} respuestas 503 seguidas")
                        self.ritmo = RITMO_LENTO
                        time.sleep(PAUSA_503)
            except Exception as e:  # noqa: BLE001 — se registra textual
                ultimo_error = f"{type(e).__name__}: {e}"
            self.log(f"[reintento] {url} intento={intento}/{INTENTOS} {ultimo_error}")
            if intento < INTENTOS:
                time.sleep(ESPERA * intento)
        return {"estado": "error", "error": ultimo_error, "intentos": INTENTOS}


# ------------------------------------------------------------------------- #
# Latido                                                                     #
# ------------------------------------------------------------------------- #

def leer_latido(base: Path) -> str | None:
    p = base / "ultima_ok.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else None


def aviso_latido(base: Path, destino: Path, fecha: str) -> bool:
    ultima = leer_latido(base)
    dias = (date.fromisoformat(fecha) - date.fromisoformat(ultima)).days if ultima else None
    if ultima is None or dias > DIAS_LATIDO:
        (destino / "aviso_latido.md").write_text(
            "# AVISO — control del sitio sin corrida exitosa\n\n"
            f"Última corrida en la que el sitio respondió el índice: {ultima or 'ninguna registrada'}"
            + (f" (hace {dias} días; el umbral es {DIAS_LATIDO})" if dias is not None else "") + ".\n"
            "Mientras el control no corra, un cambio de los supuestos del sitio no se detecta.\n",
            encoding="utf-8")
        return True
    return False


# ------------------------------------------------------------------------- #
# Clasificación de los TOs que cambiaron (tabla de M1)                        #
# ------------------------------------------------------------------------- #

E0_TANDA0 = C.REPO / "data" / "experiment" / "reextraccion_v2" / "e0_chunking" / "salida_tanda0"
PARTICION = C.REPO / "data" / "experiment" / "segmentacion_84" / "b584_particion"


def paginas_de_unidades(ident: str, base_job: dict) -> tuple[set[int] | None, str]:
    """Páginas del PDF congelado que usan las unidades de E0 guardadas (texto
    propio y herencia): la E0 de la tanda 0 para sus diez TOs y la partición
    del corpus escalado para el resto. Es la definición operativa de «páginas
    que E0 convierte en unidades» de la fila F18a de la tabla de M1."""
    interno = base_job[ident]["id_interno"]
    if base_job[ident]["grupo"] == "desarrollo_5" or interno in TANDA0_NUEVOS:
        p = E0_TANDA0 / f"chunks_{interno}.json"
    else:
        p = PARTICION / interno / f"chunks_{interno}.json"
    if not p.exists():
        return None, str(p.relative_to(C.REPO))
    pags: set[int] = set()
    for c in json.loads(p.read_text(encoding="utf-8")):
        pags.update(c.get("paginas", []))
        for h in c.get("herencia", []):
            pags.update(h.get("paginas", []))
    return pags, str(p.relative_to(C.REPO))


def clasificar(viejo: Path, nuevo: Path, unidades: set[int] | None, fuente: str) -> dict:
    """Clase de la tabla de M1 según en qué páginas del PDF congelado cae el
    cambio. Diff por página con la misma normalización y el mismo alineamiento
    que job_actualizacion/code/adjudicar_deltas.py:43-79: con igual cantidad de
    páginas, una a una; con distinta, SequenceMatcher sobre la secuencia de
    páginas. Una página vieja reemplazada o eliminada cuenta en su número
    viejo; una página insertada cuenta como de cuerpo si una de sus vecinas
    viejas lo es. F18b si alguna página tocada es de unidades; F18a si
    ninguna; más F05 si cambió la cantidad de páginas."""
    import difflib
    if str(C.JOB_CODE) not in sys.path:
        sys.path.insert(0, str(C.JOB_CODE))
    import adjudicar_deltas as AD  # noqa: PLC0415 — solo lectura (job cerrado)
    _, tv = C.L.texto_paginas(viejo, None)
    _, tn = C.L.texto_paginas(nuevo, None)
    pv = [AD.normalizar(tv[i]) for i in sorted(tv)]
    pn = [AD.normalizar(tn[i]) for i in sorted(tn)]
    tocadas, insertadas_junto_a = set(), set()
    if len(pv) == len(pn):
        tocadas = {i + 1 for i, (a, b) in enumerate(zip(pv, pn)) if a != b}
        alineacion = "una_a_una"
    else:
        alineacion = "por_secuencia"
        for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(None, pv, pn, autojunk=False).get_opcodes():
            if tag in ("replace", "delete"):
                tocadas.update(range(i1 + 1, i2 + 1))
            elif tag == "insert":
                insertadas_junto_a.update(p for p in (i1, i1 + 1) if 1 <= p <= len(pv))
    out = {"fuente_paginas_de_unidades": fuente, "alineacion": alineacion,
           "paginas_anterior": len(pv), "paginas_actual": len(pn),
           "paginas_viejas_tocadas": sorted(tocadas),
           "vecinas_de_insercion": sorted(insertadas_junto_a)}
    if not tocadas and not insertadas_junto_a:
        out["fila_m1"], out["clase"] = "sin cambio de texto", "nada"
        out["lectura"] = "el sha cambió pero ninguna página cambia su texto extraído"
        return out
    if not unidades:
        out["fila_m1"], out["clase"] = "no clasificable", "sin unidades de E0 guardadas para este TO"
        return out
    cuerpo = sorted((tocadas | insertadas_junto_a) & unidades)
    out["paginas_de_unidades_tocadas"] = cuerpo
    if cuerpo:
        out["fila_m1"], out["clase"] = "F18b", "E1 y E3 de las afectadas"
        out["lectura"] = ("el cambio cae en páginas que usan unidades de E0: re-extraen las unidades "
                          "cuyo request cambie (filas F01 a F04 y F19); cuántas, solo con E0 y la clave "
                          "(U-SUBGRAFO)")
    else:
        out["fila_m1"], out["clase"] = "F18a", "nada"
        out["lectura"] = ("el cambio cae solo en páginas que ninguna unidad de E0 usa: nada, si E0 "
                          "sobre el PDF nuevo devuelve las mismas unidades (NO VERIFICADO sin correr E0)")
    if len(pv) != len(pn):
        out["fila_m1"] += " + F05"
        out["lectura"] += "; cambió la cantidad de páginas: las páginas de las unidades se corren (F05)"
    return out


def clasificar_todos(destino: Path, pedidos: dict, base_job: dict, obs_prev: dict) -> dict:
    """Cada TO cuyo PDF de hoy difiere del congelado se clasifica contra el
    PDF congelado, sobre el que se construyó la E0 guardada. Los que además
    cambiaron desde la corrida del 2026-09-07 se listan aparte."""
    res = {"desde_el_corpus_congelado": {}, "cambiaron_desde_la_corrida_del_2026_09_07": []}
    for ident, p in sorted(pedidos.items()):
        if ident not in base_job or obs_prev.get(ident) is None:
            continue
        if p["estado"] == "descargado":
            actual, sha_actual = destino / "pdfs" / f"{ident}.pdf", p["sha256"]
        elif p["estado"] == "no_modificado":
            actual, sha_actual = C.CORRIDA_BASE / "pdfs" / f"{ident}.pdf", obs_prev[ident]["sha256"]
        else:
            continue
        if sha_actual != obs_prev[ident]["sha256"]:
            res["cambiaron_desde_la_corrida_del_2026_09_07"].append(ident)
        if sha_actual != base_job[ident]["sha256"]:
            unidades, fuente = paginas_de_unidades(ident, base_job)
            res["desde_el_corpus_congelado"][ident] = {
                "id_interno": base_job[ident]["id_interno"], "grupo": base_job[ident]["grupo"],
                "en_la_tanda0": base_job[ident]["grupo"] == "desarrollo_5"
                or base_job[ident]["id_interno"] in TANDA0_NUEVOS,
                "estado_pedido": p["estado"], "sha256_congelado": base_job[ident]["sha256"],
                "sha256_actual": sha_actual,
            } | clasificar(Path(base_job[ident]["pdf"]), actual, unidades, fuente)
    return res


# ------------------------------------------------------------------------- #
# Corrida                                                                    #
# ------------------------------------------------------------------------- #

def correr(modo: str, fecha: str, base: Path, cliente_factory) -> int:
    destino = base / fecha
    if destino.exists():
        print(f"FRENO: {destino} ya existe; una corrida no sobrescribe a otra.", file=sys.stderr)
        return 2
    lb = json.loads(C.LINEA_BASE_DEFAULT.read_text(encoding="utf-8"))
    if C.parametros_distintos(lb):
        print("FRENO: parámetros del código distintos de los de la línea de base.", file=sys.stderr)
        return 2
    destino.mkdir(parents=True)
    bitacora = []

    def log(m: str) -> None:
        bitacora.append(m)
        print(m, flush=True)

    cliente = cliente_factory(log)
    t0 = time.time()
    r = cliente.traer(URL_INDICE)
    resumen = {"fecha": fecha, "modo": modo, "url_indice": URL_INDICE, "user_agent": USER_AGENT,
               "cortesia": {"ritmo_s": RITMO, "timeout_s": TIMEOUT, "intentos_por_pedido": INTENTOS,
                            "espera_s": ESPERA, "concurrencia": 1}}
    if r["estado"] != "ok":
        (destino / "corrida_fallida.md").write_text(
            f"# Corrida del {fecha}: el índice no respondió\n\nError: {r['error']}\n"
            "Se aborta antes de pedir un solo PDF: sin índice no se distingue «el sitio cambió» "
            "de «no pude preguntar».\n", encoding="utf-8")
        latido = aviso_latido(base, destino, fecha)
        resumen |= {"indice": {"estado": "error", "error": r["error"], "intentos": r["intentos"]},
                    "pedidos_logicos": 1, "intentos_http": cliente.intentos_http,
                    "aviso_latido": latido, "codigo_salida": 3}
        (destino / "resumen_corrida.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1,
                                                                 sort_keys=True) + "\n", encoding="utf-8")
        return 3
    indice = destino / "indice_crudo.json"
    indice.write_bytes(r["datos"])
    resumen["indice"] = {"estado": "ok", "http": r["http"], "bytes": len(r["datos"]),
                         "sha256": C.hashlib.sha256(r["datos"]).hexdigest(), "intentos": r["intentos"]}
    (base / "ultima_ok.txt").write_text(fecha + "\n", encoding="utf-8")
    pedidos: dict = {}
    pdfs_dir = None
    if modo == "indice-y-pdfs":
        try:
            filas, _dup = C.L.leer_indice(indice)
        except Exception as exc:  # noqa: BLE001 — S1 roto: no se piden PDFs
            filas = []
            log(f"[indice] no se pudo leer como índice ({type(exc).__name__}); no se piden PDFs")
        obs_prev = json.loads(OBSERVACIONES_PREVIAS.read_text(encoding="utf-8"))
        pdfs_dir = destino / "pdfs"
        pdfs_dir.mkdir()
        for n, f in enumerate(filas, 1):
            prev = (obs_prev.get(f["id"]) or {}).get("cabeceras") or {}
            cond = {}
            if prev.get("etag"):
                cond["If-None-Match"] = prev["etag"]
            if prev.get("last_modified"):
                cond["If-Modified-Since"] = prev["last_modified"]
            rp = cliente.traer(f["url"], cond)
            reg = {"id": f["id"], "url": f["url"], "condicionales_enviados": sorted(cond),
                   "intentos": rp["intentos"], "http": rp.get("http")}
            if rp["estado"] == "no_modificado":
                reg["estado"] = "no_modificado"
            elif rp["estado"] == "error":
                reg |= {"estado": "error", "error": rp["error"]}
            elif not (rp["datos"][:4] == b"%PDF" and len(rp["datos"]) > MIN_PDF_BYTES):
                reg |= {"estado": "contenido_no_pdf", "bytes": len(rp["datos"])}
            else:
                (pdfs_dir / f"{f['id']}.pdf").write_bytes(rp["datos"])
                reg |= {"estado": "descargado", "bytes": len(rp["datos"]),
                        "sha256": C.hashlib.sha256(rp["datos"]).hexdigest(),
                        "cabeceras": rp["cabeceras"],
                        "igual_a_2026_09_07": (C.hashlib.sha256(rp["datos"]).hexdigest()
                                               == (obs_prev.get(f["id"]) or {}).get("sha256"))}
            pedidos[f["id"]] = reg
            if n % 25 == 0 or reg["estado"] not in ("no_modificado", "descargado"):
                log(f"[{n:3d}/{len(filas)}] {f['id']:24s} {reg['estado']} {reg.get('http')}")
        (destino / "pedidos.json").write_text(json.dumps(pedidos, ensure_ascii=False, indent=1,
                                                         sort_keys=True) + "\n", encoding="utf-8")
    codigo = C.controlar(indice, pdfs_dir, destino, C.LINEA_BASE_DEFAULT)
    if modo == "indice-y-pdfs" and pedidos:
        base_job = C.L.linea_base()
        obs_prev = json.loads(OBSERVACIONES_PREVIAS.read_text(encoding="utf-8"))
        cls = clasificar_todos(destino, pedidos, base_job, obs_prev)
        (destino / "clasificacion_cambios.json").write_text(json.dumps(
            cls, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        resumen["tos_que_cambiaron"] = {k: sorted(v) for k, v in cls.items()}
        resumen["clases_desde_el_corpus_congelado"] = {
            k: v["fila_m1"] for k, v in sorted(cls["desde_el_corpus_congelado"].items())}
    from collections import Counter
    resumen |= {
        "pedidos_logicos": 1 + len(pedidos), "intentos_http": cliente.intentos_http,
        "pedidos_por_estado": dict(sorted(Counter(p["estado"] for p in pedidos.values()).items())),
        "pedidos_por_http": dict(sorted(Counter(str(p.get("http")) for p in pedidos.values()).items())),
        "bytes_descargados_pdfs": sum(p.get("bytes", 0) for p in pedidos.values()
                                      if p["estado"] == "descargado"),
        "segundos_de_pared": round(time.time() - t0, 1),
        "codigo_control": codigo, "codigo_salida": codigo,
    }
    (destino / "resumen_corrida.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1,
                                                             sort_keys=True) + "\n", encoding="utf-8")
    (destino / "bitacora.txt").write_text("\n".join(bitacora) + "\n", encoding="utf-8")
    return codigo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=("indice", "indice-y-pdfs"))
    ap.add_argument("--fecha", default=date.today().isoformat())
    ap.add_argument("--base", type=Path, default=BASE_CORRIDAS)
    ap.add_argument("--autorizado-red", action="store_true",
                    help="sin esta marca el runner no sale a la red")
    ap.add_argument("--estado", action="store_true",
                    help="sin red: informa la última corrida exitosa; código 1 si pasaron más de 45 días")
    a = ap.parse_args()
    if a.estado:
        ultima = leer_latido(a.base)
        dias = (date.fromisoformat(a.fecha) - date.fromisoformat(ultima)).days if ultima else None
        print(f"última corrida exitosa: {ultima or 'ninguna'}"
              + (f" (hace {dias} días; umbral {DIAS_LATIDO})" if dias is not None else ""))
        return 1 if ultima is None or dias > DIAS_LATIDO else 0
    if not a.modo:
        ap.error("--modo es obligatorio (o --estado)")
    if not a.autorizado_red:
        print("FRENO: falta --autorizado-red; el runner no sale a la red sin esa marca.", file=sys.stderr)
        return 2
    a.base.mkdir(parents=True, exist_ok=True)
    return correr(a.modo, a.fecha, a.base, Cliente)


if __name__ == "__main__":
    sys.exit(main())
