"""Runner del job de actualización: trae el índice y los PDFs, y observa.

Ejecuta los pasos 2 y 4 del mecanismo (§2.a.3 del diseno). NO adjudica: la
clasificación de deltas y el mapeo al grafo son del adjudicador, que corre sin
red sobre lo que este script persiste. La separación es deliberada: una corrida
se puede re-adjudicar sin volver a molestar al sitio.

SOLO LECTURA sobre la línea base sellada. Escribe únicamente en
../corridas/<fecha>/.

Uso (desde cualquier cwd):
  python3 data/experiment/job_actualizacion/code/correr_job.py [--solo-indice]
                                                              [--reanudar]
                                                              [--fecha AAAA-MM-DD]

Salidas:
  ../corridas/<fecha>/indice_crudo.json    respuesta cruda del endpoint
  ../corridas/<fecha>/observaciones.json   una entrada por TO
  ../corridas/<fecha>/pdfs/<id>.pdf        los PDFs (no versionados)
  ../corridas/<fecha>/corrida.log          bitácora de la corrida
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_job as L                                              # noqa: E402

# El endpoint que alimenta la lista de https://www.bcra.gob.ar/ordenamiento-y-resumenes/
# (la página la monta por JS). Documentado en escalado_prep/code/construir_inventario.py:
# es la misma fuente cuya respuesta quedó congelada como indice_oficial_raw.json.
URL_INDICE = "https://www.bcra.gob.ar/api/endpoints/ordenamiento-y-resumenes.php?lang=es"

# Identificación descriptiva y sin datos personales.
USER_AGENT = ("AcademicResearchBot/1.0 (job de actualizacion de corpus "
              "regulatorio; investigacion academica)")

RITMO = 0.5          # s entre pedidos (2 req/s), un pedido por vez
TIMEOUT = 60         # s
INTENTOS = 3
ESPERA = 2.0         # s, creciente: 2 / 4 / 6
UMBRAL_503 = 5       # 503 consecutivos que disparan el modo lento
PAUSA_503 = 60.0     # s
RITMO_LENTO = 1.0    # s
MIN_PDF_BYTES = 1024


class Cliente:
    """Cliente cortés: ritmo global, reintentos acotados y modo lento ante 503.

    Los parámetros salen del scraper ya calibrado contra este mismo host
    (src/scraper/download_bcra.py) y de escalado_prep/code/descargar_pdfs.py.
    """

    def __init__(self, log):
        self.log = log
        self.ultimo = 0.0
        self.ritmo = RITMO
        self.consecutivos_503 = 0
        self.pedidos = 0
        self.segundos = 0.0

    def _esperar_turno(self) -> None:
        falta = self.ritmo - (time.time() - self.ultimo)
        if falta > 0:
            time.sleep(falta)
        self.ultimo = time.time()

    @staticmethod
    def _normalizar(url: str) -> str:
        """Percent-encoding del path: el índice publica al menos un archivo con
        guion largo (t-RI–SPI.pdf, U+2013) que urllib no puede poner en la línea
        de request. Precedente: escalado_prep/code/descargar_pdfs.py."""
        p = urllib.parse.urlsplit(url)
        return urllib.parse.urlunsplit(
            (p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%"),
             p.query, p.fragment))

    def traer(self, url: str) -> dict:
        ultimo_error = ""
        for intento in range(1, INTENTOS + 1):
            self._esperar_turno()
            t0 = time.time()
            try:
                req = urllib.request.Request(self._normalizar(url),
                                             headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    datos = resp.read()
                    cabeceras = {
                        "content_type": resp.headers.get("Content-Type"),
                        "content_length": resp.headers.get("Content-Length"),
                        "last_modified": resp.headers.get("Last-Modified"),
                        "etag": resp.headers.get("ETag"),
                    }
                    http = resp.status
                self.pedidos += 1
                self.segundos += time.time() - t0
                self.consecutivos_503 = 0
                return {"estado": "ok", "http": http, "datos": datos,
                        "cabeceras": cabeceras, "intentos": intento}
            except urllib.error.HTTPError as e:
                ultimo_error = f"HTTPError {e.code}"
                if e.code == 503:
                    self.consecutivos_503 += 1
                    if self.consecutivos_503 >= UMBRAL_503 and self.ritmo < RITMO_LENTO:
                        self.log(f"[modo-lento] {UMBRAL_503} respuestas 503 seguidas: "
                                 f"pausa {PAUSA_503:.0f}s y ritmo a 1 req/s")
                        self.ritmo = RITMO_LENTO
                        time.sleep(PAUSA_503)
            except Exception as e:                # noqa: BLE001 — se reporta textual
                ultimo_error = f"{type(e).__name__}: {e}"
            self.log(f"[reintento] {url} intento={intento}/{INTENTOS} {ultimo_error}")
            if intento < INTENTOS:
                time.sleep(ESPERA * intento)
        return {"estado": "error", "error": ultimo_error, "intentos": INTENTOS}


def es_pdf(datos: bytes) -> bool:
    return datos[:4] == b"%PDF" and len(datos) > MIN_PDF_BYTES


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fecha", default=date.today().isoformat())
    ap.add_argument("--solo-indice", action="store_true")
    ap.add_argument("--reanudar", action="store_true")
    args = ap.parse_args(argv)

    destino = L.CORRIDAS / args.fecha
    if destino.exists() and not args.reanudar:
        print(f"FRENO: {destino} ya existe. Una corrida no sobrescribe a otra.\n"
              f"Usá --reanudar para continuar una corrida interrumpida, o "
              f"--fecha para otra fecha.", file=sys.stderr)
        return 2
    (destino / "pdfs").mkdir(parents=True, exist_ok=True)

    bitacora = (destino / "corrida.log").open("a", encoding="utf-8")

    def log(msg: str) -> None:
        linea = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}"
        print(linea, flush=True)
        bitacora.write(linea + "\n")
        bitacora.flush()

    cliente = Cliente(log)
    t_inicio = time.time()
    log(f"=== corrida {args.fecha} — inicio ===")

    # --- paso 2: el índice ------------------------------------------------
    log(f"[indice] {URL_INDICE}")
    r = cliente.traer(URL_INDICE)
    if r["estado"] != "ok":
        log(f"[ABORTA] el endpoint del indice no respondio: {r['error']}")
        log("Sin indice no se puede distinguir 'desaparecio' de 'no pude preguntar': "
            "la corrida se aborta antes de bajar un solo PDF.")
        return 3
    try:
        crudo = json.loads(r["datos"].decode("utf-8"))
    except Exception as e:                        # noqa: BLE001
        log(f"[ABORTA] el indice no es JSON parseable: {type(e).__name__}: {e}")
        return 3
    faltan = [c for _, c in L.CATEGORIAS if c not in crudo]
    if faltan:
        log(f"[ABORTA] el indice no trae las listas esperadas: faltan {faltan}. "
            f"Claves recibidas: {sorted(crudo)}. No se adivina el formato nuevo.")
        return 3
    (destino / "indice_crudo.json").write_bytes(r["datos"])
    log(f"[indice] OK — {sum(len(crudo[c]) for _, c in L.CATEGORIAS)} entradas, "
        f"{len(r['datos'])} bytes")

    filas, duplicadas = L.leer_indice(destino / "indice_crudo.json")
    log(f"[indice] {len(filas)} URLs unicas, {len(duplicadas)} duplicadas descartadas")
    if args.solo_indice:
        log("[--solo-indice] no se bajan PDFs.")
        return 0

    # --- paso 3: objetivo = lo que publica el índice UNION lo que hay en la base
    base = L.linea_base()
    del_indice = {f["id"]: f for f in filas}
    objetivo = sorted(set(del_indice) | set(base))
    log(f"[objetivo] {len(objetivo)} TOs = {len(del_indice)} del indice UNION "
        f"{len(base)} de la linea base")

    # --- paso 4: los PDFs -------------------------------------------------
    obs_path = destino / "observaciones.json"
    obs = json.loads(obs_path.read_text(encoding="utf-8")) if obs_path.exists() else {}
    a_pedir = [i for i in objetivo if i in del_indice]
    log(f"[pdfs] {len(a_pedir)} a pedir "
        f"({len(objetivo) - len(a_pedir)} sin URL en el indice de hoy)")

    for n, ident in enumerate(a_pedir, 1):
        pdf = destino / "pdfs" / f"{ident}.pdf"
        if args.reanudar and pdf.exists() and pdf.stat().st_size > 0 and ident in obs:
            continue
        entrada = del_indice[ident]
        r = cliente.traer(entrada["url"])
        registro = {"id": ident, "url": entrada["url"],
                    "titulo_indice": entrada["titulo"],
                    "archivo_indice": entrada["archivo"],
                    "categoria": entrada["categoria"],
                    "intentos": r["intentos"]}
        if r["estado"] != "ok":
            registro |= {"estado": "error_de_descarga", "error": r["error"]}
        elif not es_pdf(r["datos"]):
            registro |= {"estado": "contenido_no_pdf", "http": r["http"],
                         "bytes": len(r["datos"]),
                         "cabeceras": r["cabeceras"],
                         "error": f"no empieza con %PDF o pesa <= {MIN_PDF_BYTES} bytes"}
        else:
            pdf.write_bytes(r["datos"])
            registro |= {"estado": "descargado", "http": r["http"],
                         "bytes": len(r["datos"]),
                         "sha256": L.sha256_bytes(r["datos"]),
                         "cabeceras": r["cabeceras"]}
            try:
                total, _ = L.texto_paginas(pdf, [])
                registro["paginas"] = total
            except Exception as e:                # noqa: BLE001
                registro["paginas"] = None
                registro["error_paginas"] = f"{type(e).__name__}: {e}"
            registro["procedencia"] = L.procedencia(pdf)
        obs[ident] = registro
        obs_path.write_text(json.dumps(obs, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        log(f"[{n:3d}/{len(a_pedir)}] {ident:28s} {registro['estado']:18s} "
            f"{registro.get('bytes', registro.get('error', ''))}")

    ok = sum(1 for v in obs.values() if v["estado"] == "descargado")
    log(f"=== corrida {args.fecha} — fin === descargados={ok} "
        f"fallidos={len(obs) - ok} pedidos={cliente.pedidos} "
        f"pared={time.time() - t_inicio:.0f}s")
    bitacora.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
