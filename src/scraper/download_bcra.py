"""
Descargador del corpus regulatorio del BCRA. Para el proyecto final de Ingeniería en IA,
UdeSA.

Modular. Cada paso del plan B.1..B.9 es un subcomando:

    python src/scraper/download_bcra.py B1   # TOs actuales
    python src/scraper/download_bcra.py B2   # marco legal
    python src/scraper/download_bcra.py B3   # TOs históricos
    python src/scraper/download_bcra.py B4   # Comunicaciones A
    python src/scraper/download_bcra.py B5   # tachado/negrita
    python src/scraper/download_bcra.py B6   # Comunicaciones B
    python src/scraper/download_bcra.py B7   # Comunicaciones C
    python src/scraper/download_bcra.py B8   # Comunicaciones P
    python src/scraper/download_bcra.py B9   # complementarios

Por defecto descarga la regulación BCRA completa (scope ampliado de la PPF).
Para restringir B4/B6/B7/B8 a temática MULC (scope previo del proyecto):

    python src/scraper/download_bcra.py B4 --mulc-only

El flag activa el filtro KEYWORDS_MULC sobre las Comunicaciones A/B/C/P y el
fallback de tachado/negrita (solo para A). No afecta a B1/B2/B3/B5/B9.

Reglas:
- Rate limit 2 req/s por dominio (sleep 0.5s).
- argentina.gob.ar: 10s/req (robots.txt Crawl-delay).
- Reintento 1 vez ante 503/timeout (esperar 10s).
- Si 5+ 503 consecutivos: pausa 60s y baja a 1 req/s.
- Validación PDF: %PDF + size > 1KB.
- Manifiesto + log + checkpoint en data/raw/.
- Idempotente: skipea archivos ya descargados.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

USER_AGENT = (
    "Mozilla/5.0 (compatible; AcademicResearchBot/1.0; "
    "PPF Tesis IA UdeSA)"
)
HEADERS = {"User-Agent": USER_AGENT, "Connection": "close"}

# Rate limit por host (segundos entre requests).
DEFAULT_DELAY = 0.5
HOST_DELAY = {
    "www.argentina.gob.ar": 10.0,
}

MIN_PDF_BYTES = 1024
MAX_CORPUS_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB
HTTP_TIMEOUT = 15  # segundos por request (bajado de 60 para evitar bloqueos)
RETRY_SLEEP = 5    # pausa antes del único retry permitido
MAX_ATTEMPTS = 2   # 1 retry máximo (1 intento original + 1 retry)

# Flag global: si True, las Comunicaciones A/B/C/P se filtran por keywords MULC
# y se aplica el fallback de tachado/negrita. Se setea desde main() según
# --mulc-only. Default False (scope BCRA completo).
MULC_ONLY = False

KEYWORDS_MULC = [
    "exterior y cambios",
    "mercado de cambios",
    "mercado libre de cambios",
    "mulc",
    "regimen cambiario",
    "operaciones cambiarias",
    "operadores de cambio",
    "casa de cambio",
    "casas de cambio",
    "ingreso de divisas",
    "egreso de divisas",
    "regimen penal cambiario",
    "decreto 260/02",
    "decreto 260/2002",
    "decreto 609/19",
    "decreto 609/2019",
    "sepaimpo",
    "secoexpo",
    "rioc",
    "posicion general de cambios",
    "boleto de cambio",
    "bopreal",
]
# Keywords compuestas (ambas partes deben aparecer).
KEYWORDS_MULC_COMPOUND = [
    ("exportaciones de bienes", "liquidacion"),
    ("importaciones de bienes", "pago"),
]

MANIFIESTO_HEADERS = [
    "categoria", "archivo_local", "url_origen", "numero",
    "fecha_descarga", "fecha_documento", "tamano_bytes", "num_paginas",
    "titulo_extraido", "relevancia_mulc", "keywords_encontradas",
    "tiene_version_tachado_negrita",
]
DESCARTADOS_HEADERS = [
    "categoria", "url_origen", "numero",
    "fecha_descarga", "tamano_bytes", "razon_descarte",
]


# -- utils ----------------------------------------------------------------

def normalize_text(s: str) -> str:
    """lowercase + sin acentos para keyword match."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def slugify(s: str, maxlen: int = 30) -> str:
    s = normalize_text(s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:maxlen]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -- HTTP client ----------------------------------------------------------

class RateLimitedClient:
    """Cliente HTTP con rate limit GLOBAL compartido entre threads.

    El lock se mantiene durante el sleep del rate limit, así dos workers
    se serializan en la cola pero comparten un único stream de requests
    al host (no es 2 req/s por worker, es 2 req/s totales).
    """

    def __init__(self, log_fn: Callable[[str], None]):
        self.session = self._make_session()
        self._last_request_at: dict[str, float] = {}
        self._consecutive_503: dict[str, int] = {}
        self._slow_mode_hosts: set[str] = set()
        self._rate_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        # estadísticas para reporte final
        self.total_requests = 0
        self.total_request_time = 0.0
        self.total_request_errors = 0
        self.persistent_failures: list[str] = []
        # Recycling: cada N attempts (exitosos o no) creamos una Session nueva.
        # Defensa en profundidad contra (a) keep-alive zombie con CDN BCRA,
        # (b) TIME_WAIT exhaustion del SO con Connection: close en runs largos.
        # Ver memoria project_bug_workers_deadlock.md.
        self._recycle_threshold = 200
        self._attempts_since_recycle = 0
        self.session_recycle_count = 0
        self.log = log_fn

    @staticmethod
    def _make_session() -> requests.Session:
        s = requests.Session()
        s.headers.update(HEADERS)
        return s

    def _maybe_recycle_session(self) -> None:
        """Si pasamos el threshold, creamos Session nueva. Asignación atómica;
        la session vieja queda viva mientras workers en flight la usen
        (cada uno toma snapshot local en `get()`); el GC la libera después."""
        with self._stats_lock:
            self._attempts_since_recycle += 1
            if self._attempts_since_recycle < self._recycle_threshold:
                return
            self._attempts_since_recycle = 0
            self.session_recycle_count += 1
            recycle_n = self.session_recycle_count
            total = self.total_requests
        self.session = self._make_session()
        self.log(f"[recycle-session] #{recycle_n} (total_requests={total})")

    def _acquire_slot(self, host: str) -> None:
        """Adquiere el siguiente slot del token bucket compartido.

        Mantiene el lock durante el sleep para serializar la salida y respetar
        2 req/s GLOBAL. Después del sleep, registra `last_request_at` así el
        próximo thread ve la marca actualizada.
        """
        with self._rate_lock:
            base_delay = HOST_DELAY.get(host, DEFAULT_DELAY)
            if host in self._slow_mode_hosts:
                base_delay = max(base_delay, 1.0)
            last = self._last_request_at.get(host, 0.0)
            elapsed = time.time() - last
            wait = base_delay - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_request_at[host] = time.time()

    def get(self, url: str, timeout: int = HTTP_TIMEOUT) -> requests.Response | None:
        host = urlparse(url).netloc
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._acquire_slot(host)
            t0 = time.time()
            local_session = self.session  # snapshot estable: protege contra reciclaje concurrente
            try:
                resp = local_session.get(url, timeout=timeout, allow_redirects=True)
            except requests.exceptions.RequestException as e:
                # Catch-all amplio: cubre Timeout, ConnectionError, ChunkedEncodingError,
                # SSLError y cualquier futura subclase de RequestException. El comportamiento
                # downstream (log [net-err], retry, [persistent-fail]) es el adecuado para
                # todas estas. Decisión documentada en bug #3 de project_bug_workers_deadlock.
                dt = time.time() - t0
                with self._stats_lock:
                    self.total_request_errors += 1
                self._maybe_recycle_session()  # cada attempt consume un puerto efímero
                self.log(f"[net-err] {url} attempt={attempt}/{MAX_ATTEMPTS} dt={dt:.1f}s {type(e).__name__}: {str(e)[:120]}")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_SLEEP)
                    continue
                with self._stats_lock:
                    self.persistent_failures.append(url)
                self.log(f"[persistent-fail] {url}")
                return None

            dt = time.time() - t0
            with self._stats_lock:
                self.total_requests += 1
                self.total_request_time += dt
            self._maybe_recycle_session()

            if resp.status_code == 503:
                with self._rate_lock:
                    self._consecutive_503[host] = self._consecutive_503.get(host, 0) + 1
                    n_503 = self._consecutive_503[host]
                self.log(f"[503] {url} attempt={attempt} consec={n_503}")
                if n_503 >= 5 and host not in self._slow_mode_hosts:
                    self.log(f"[slow-mode] {host}: pausa 60s + 1 req/s")
                    self._slow_mode_hosts.add(host)
                    time.sleep(60)
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_SLEEP)
                    continue
                with self._stats_lock:
                    self.persistent_failures.append(url)
                return None

            with self._rate_lock:
                self._consecutive_503[host] = 0
            return resp
        return None

    def avg_latency(self) -> float:
        with self._stats_lock:
            if self.total_requests == 0:
                return 0.0
            return self.total_request_time / self.total_requests


# -- PDF utils ------------------------------------------------------------

def is_valid_pdf(content: bytes) -> bool:
    return len(content) >= MIN_PDF_BYTES and content[:4] == b"%PDF"


def extract_pdf_text(content: bytes, max_pages: int | None = None) -> tuple[str, int]:
    """Extrae texto del PDF. Devuelve (texto, num_paginas).
    Si max_pages está dado, solo extrae las primeras N páginas (truncado tipo
    'primer 30%' aproximado).
    """
    try:
        reader = PdfReader(io.BytesIO(content))
        n = len(reader.pages)
        limit = n if max_pages is None else min(max_pages, n)
        chunks = []
        for i in range(limit):
            try:
                chunks.append(reader.pages[i].extract_text() or "")
            except Exception:  # noqa: BLE001
                continue
        return "\n".join(chunks), n
    except Exception:  # noqa: BLE001
        return "", 0


def first_30pct_pages(num_pages: int) -> int:
    return max(1, int(num_pages * 0.3 + 0.999))


def keywords_in(text: str) -> list[str]:
    """Devuelve la lista de keywords MULC presentes en text (normalizado)."""
    nt = normalize_text(text)
    found = []
    for kw in KEYWORDS_MULC:
        if kw in nt:
            found.append(kw)
    for a, b in KEYWORDS_MULC_COMPOUND:
        if a in nt and b in nt:
            found.append(f"{a} + {b}")
    return found


# -- Manifiesto / log / checkpoint ---------------------------------------

class Workspace:
    def __init__(self) -> None:
        self.manifiesto_path = RAW_DIR / "manifiesto.csv"
        self.descartados_path = RAW_DIR / "manifiesto_descartados.csv"
        self.log_path = RAW_DIR / "log.txt"
        self.checkpoint_path = RAW_DIR / "checkpoint.json"
        self._ensure_csv(self.manifiesto_path, MANIFIESTO_HEADERS)
        self._ensure_csv(self.descartados_path, DESCARTADOS_HEADERS)
        self._csv_lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._cache_urls_lock = threading.Lock()
        self._manifiesto_urls_cache: set[str] | None = None
        self._descartados_urls_cache: set[str] | None = None

    @staticmethod
    def _ensure_csv(path: Path, headers: list[str]) -> None:
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(headers)

    def log(self, msg: str) -> None:
        line = f"{now_iso()} {msg}\n"
        with self._log_lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line)
            sys.stdout.write(line)
            sys.stdout.flush()

    def add_manifiesto_row(self, row: dict) -> None:
        with self._csv_lock:
            with self.manifiesto_path.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=MANIFIESTO_HEADERS)
                w.writerow({k: row.get(k, "") for k in MANIFIESTO_HEADERS})
            with self._cache_urls_lock:
                if self._manifiesto_urls_cache is not None:
                    self._manifiesto_urls_cache.add(row.get("url_origen", ""))

    def add_descartado_row(self, row: dict) -> None:
        with self._csv_lock:
            with self.descartados_path.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=DESCARTADOS_HEADERS)
                w.writerow({k: row.get(k, "") for k in DESCARTADOS_HEADERS})
            with self._cache_urls_lock:
                if self._descartados_urls_cache is not None:
                    self._descartados_urls_cache.add(row.get("url_origen", ""))

    def manifiesto_urls(self) -> set[str]:
        """Cached para evitar leer el CSV en cada chequeo de skip-existing."""
        with self._cache_urls_lock:
            if self._manifiesto_urls_cache is not None:
                return self._manifiesto_urls_cache
        if not self.manifiesto_path.exists():
            urls: set[str] = set()
        else:
            urls = set()
            with self.manifiesto_path.open("r", encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    urls.add(row.get("url_origen", ""))
        with self._cache_urls_lock:
            self._manifiesto_urls_cache = urls
            return self._manifiesto_urls_cache

    def descartados_urls(self) -> set[str]:
        with self._cache_urls_lock:
            if self._descartados_urls_cache is not None:
                return self._descartados_urls_cache
        if not self.descartados_path.exists():
            urls: set[str] = set()
        else:
            urls = set()
            with self.descartados_path.open("r", encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    urls.add(row.get("url_origen", ""))
        with self._cache_urls_lock:
            self._descartados_urls_cache = urls
            return self._descartados_urls_cache

    def total_corpus_bytes(self) -> int:
        total = 0
        for p in RAW_DIR.rglob("*.pdf"):
            total += p.stat().st_size
        return total

    def save_checkpoint(self, step: str, state: dict) -> None:
        ck: dict = {}
        if self.checkpoint_path.exists():
            try:
                ck = json.loads(self.checkpoint_path.read_text())
            except Exception:  # noqa: BLE001
                ck = {}
        ck[step] = {"updated_at": now_iso(), **state}
        self.checkpoint_path.write_text(json.dumps(ck, indent=2, ensure_ascii=False))

    def load_checkpoint(self, step: str) -> dict:
        if not self.checkpoint_path.exists():
            return {}
        try:
            ck = json.loads(self.checkpoint_path.read_text())
            return ck.get(step, {})
        except Exception:  # noqa: BLE001
            return {}


# -- Helpers de download --------------------------------------------------

def title_from_pdf_text(text: str, max_chars: int = 200) -> str:
    """Heurística para extraer el primer párrafo significativo."""
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 15 and not line.isdigit():
            return line[:max_chars]
    return text.strip()[:max_chars] if text else ""


def fecha_from_pdf_text(text: str) -> str:
    """Busca una fecha plausible en el texto. Devuelve YYYY-MM-DD si encuentra."""
    # patrón: dd/mm/yyyy
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if m:
        d, mo, y = m.groups()
        try:
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        except ValueError:
            pass
    # patrón: dd de <mes> de yyyy
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
        "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
        "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    nt = normalize_text(text)
    m2 = re.search(r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})\b", nt)
    if m2:
        d, mo_name, y = m2.groups()
        if mo_name in meses:
            try:
                return f"{int(y):04d}-{meses[mo_name]:02d}-{int(d):02d}"
            except ValueError:
                pass
    return ""


def has_tachado_negrita(client: RateLimitedClient, num_A: str) -> tuple[bool, bool]:
    """Devuelve (existe_ec, existe_opc) probando con HEAD-equivalente (GET corto).
    num_A es el número sin la letra (ej: '8307').
    """
    found_ec = False
    found_opc = False
    for sufijo, flag_attr in (("ec", "ec"), ("opc", "opc")):
        url = f"https://www.bcra.gob.ar/archivos/Pdfs/texord/texcomp/A{num_A}n-{sufijo}.pdf"
        resp = client.get(url)
        if resp is not None and resp.status_code == 200 and resp.content[:4] == b"%PDF":
            if sufijo == "ec":
                found_ec = True
            else:
                found_opc = True
    return found_ec, found_opc


def download_and_save(
    client: RateLimitedClient,
    ws: Workspace,
    url: str,
    out_path: Path,
    categoria: str,
    numero: str = "",
    require_keyword_filter: bool = False,
    extra_record: dict | None = None,
    fallback_tachado_for_A: str | None = None,
    name_with_slug_prefix: str | None = None,
) -> tuple[str, dict]:
    """
    Devuelve (status, record) donde status ∈
      'ok', 'skip-existing', 'skip-already-manifest', '404', 'invalid-pdf',
      'irrelevant', 'net-fail'.

    fallback_tachado_for_A: si está definido (número A sin letra), cuando no se
    encuentren keywords se probará la existencia de versión tachado/negrita y, si
    existe, se considerará relevante (criterio alternativo).
    """
    if out_path.exists() and out_path.stat().st_size >= MIN_PDF_BYTES:
        return "skip-existing", {}
    if url in ws.manifiesto_urls() or url in ws.descartados_urls():
        return "skip-already-manifest", {}

    resp = client.get(url)
    if resp is None:
        ws.log(f"[net-fail] {url}")
        return "net-fail", {}
    if resp.status_code == 404:
        return "404", {}
    if resp.status_code != 200:
        ws.log(f"[http-{resp.status_code}] {url}")
        return f"http-{resp.status_code}", {}

    content = resp.content
    if not is_valid_pdf(content):
        ws.log(f"[invalid-pdf] {url} bytes={len(content)}")
        return "invalid-pdf", {}

    text_full, num_pages = extract_pdf_text(content)
    text_first30 = ""
    keywords_found: list[str] = []
    if require_keyword_filter:
        first30_pages = first_30pct_pages(num_pages)
        text_first30, _ = extract_pdf_text(content, max_pages=first30_pages)
        keywords_found = keywords_in(text_first30)

    titulo = title_from_pdf_text(text_full[:5000])
    fecha_doc = fecha_from_pdf_text(text_full[:5000])

    record = {
        "categoria": categoria,
        "url_origen": url,
        "numero": numero,
        "fecha_descarga": now_iso(),
        "fecha_documento": fecha_doc,
        "tamano_bytes": len(content),
        "num_paginas": num_pages,
        "titulo_extraido": titulo,
        "relevancia_mulc": "true" if (not require_keyword_filter or keywords_found) else "false",
        "keywords_encontradas": "; ".join(keywords_found),
        "tiene_version_tachado_negrita": "",
    }
    if extra_record:
        record.update(extra_record)

    if require_keyword_filter and not keywords_found:
        # Criterio alternativo: existencia de versión tachado/negrita (solo para A)
        has_ec = has_opc = False
        if fallback_tachado_for_A is not None:
            has_ec, has_opc = has_tachado_negrita(client, fallback_tachado_for_A)
        if has_ec or has_opc:
            ws.log(f"[fallback-tachado] A{fallback_tachado_for_A} relevante via tachado (ec={has_ec}, opc={has_opc})")
            record["relevancia_mulc"] = "true"
            record["tiene_version_tachado_negrita"] = "true"
            record["keywords_encontradas"] = "tachado_negrita_existe"
            # fall-through: se guarda
        else:
            ws.add_descartado_row({
                "categoria": categoria,
                "url_origen": url,
                "numero": numero,
                "fecha_descarga": now_iso(),
                "tamano_bytes": len(content),
                "razon_descarte": "sin keywords MULC en primer 30% y sin tachado/negrita",
            })
            return "irrelevant", record

    # Si se pidió, renombrar con slug del título antes de guardar
    final_path = out_path
    if name_with_slug_prefix:
        slug = slugify(titulo)
        if slug:
            final_path = out_path.with_name(f"{name_with_slug_prefix}_{slug}.pdf")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if not final_path.exists():
        final_path.write_bytes(content)
    record["archivo_local"] = str(final_path.relative_to(PROJECT_ROOT))
    ws.add_manifiesto_row(record)
    return "ok", record


def check_corpus_size(ws: Workspace) -> None:
    total = ws.total_corpus_bytes()
    if total > MAX_CORPUS_BYTES:
        ws.log(f"[FATAL] corpus={total} bytes supera 5 GB. Pausa.")
        raise SystemExit(2)


# -- Pasos B1..B9 ---------------------------------------------------------

def step_B1(client: RateLimitedClient, ws: Workspace) -> dict:
    """Descarga los Textos Ordenados vigentes del BCRA.

    Listado oficial: 158 entradas del índice del BCRA (104 Normativa General
    + 54 Régimen Informativo). Dedup por URL: 157 únicos (t-optico.pdf
    aparece 2 veces). Snapshot del 2026-05-15.

    Fuente: https://www.bcra.gob.ar/ordenamiento-y-resumenes/ (la página
    renderiza la lista vía JavaScript, no es accesible por HTTP plano;
    ver caveat 3 en project_corpus_caveats.md).

    Idempotencia y re-ejecución periódica:
    - Si un PDF ya está en disco con el mismo path destino, `download_and_save`
      retorna `skip-existing` instantáneo (no toca red, no toca manifiesto).
    - Re-correr `python src/scraper/download_bcra.py B1` baja solo los TOs nuevos
      (los que el BCRA agregó al índice) o los que cambiaron de URL.
    - Para detectar TOs que CAMBIARON contenido (mismo path pero PDF actualizado):
      esto NO está cubierto por skip-existing. Para captura de cambios
      periódica, hay que (a) borrar manualmente los archivos de TOs a re-bajar,
      o (b) extender el script con verificación de hash/Last-Modified.
    - Para automatizar la corrida periódica (mensual, semanal): ver README,
      sección "Cómo correr el scraper periódicamente" (a documentar).

    Etiquetas en comentarios:
    - [E] = matched existente en disco (snapshot sesión 1); idempotencia salta.
    - [N] = nuevo en este snapshot del índice oficial.

    Huérfanos conocidos en disco (sesión 1, NO en el índice oficial):
      t-fdrc.pdf, t-ri-coc.pdf, RI-planNIIF.pdf, t-ri-pl.pdf
    Se conservan en disco por trazabilidad; pueden ser obsoletos o renombrados.
    """
    ws.log("=== B.1 START — Textos Ordenados actuales ===")
    base = RAW_DIR / "01_textos_ordenados/actuales"
    items = [
        # === NORMATIVA GENERAL ===
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-adfsp.pdf',  # [N] Adelantos del Banco Central a las entidades financieras
         base / 'TO_adelantos_del_banco_central_a_las_entidades_financieras_con__actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-actgar.pdf',  # [N] Afectación de activos en garantía
         base / 'TO_afectacion_de_activos_en_garantia_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-adrei.pdf',  # [N] Agregación de datos sobre riesgos y elaboración de informes
         base / 'TO_agregacion_de_datos_sobre_riesgos_y_elaboracion_de_informes_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-seggar.pdf',  # [E] Aplicación del sistema de seguro de garantía de depósitos
         base / 'TO_seguro_garantia_depositos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-afiltr.pdf',  # [E] Asistencia financiera por iliquidez transitoria
         base / 'TO_asistencia_iliquidez_transitoria_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-asomut.pdf',  # [N] Asociaciones mutuales Reglamentación de actividad financiera
         base / 'TO_asociaciones_mutuales_reglamentacion_de_su_actividad_financi_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-autenf.pdf',  # [E] Autoridades de entidades financieras
         base / 'TO_autoridades_entidades_financieras_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ayccef.pdf',  # [N] Autorización y composición del capital de entidades financieras
         base / 'TO_autorizacion_y_composicion_del_capital_de_entidades_financie_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-cajasc.pdf',  # [N] Cajas de Crédito Cooperativas
         base / 'TO_cajas_de_credito_cooperativas_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-capmin.pdf',  # [E] Capitales mínimos de las entidades financieras
         base / 'TO_capitales_minimos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-inspag.pdf',  # [N] Características de los instrumentos de pago
         base / 'TO_caracteristicas_de_los_instrumentos_de_pago_que_emiten_las_e_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-cateloc.pdf',  # [N] Categorización de localidades para entidades financieras
         base / 'TO_categorizacion_de_localidades_para_entidades_financieras_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-cryl.pdf',  # [N] Central de registro y liquidación de instrumentos de deuda
         base / 'TO_central_de_registro_y_liquidacion_de_instrumentos_de_deuda_p_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ceninf.pdf',  # [E] Centrales de información
         base / 'TO_centrales_informacion_crediticia_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-cedin.pdf',  # [N] Certificados de depósitos para la inversión
         base / 'TO_certificados_de_depositos_para_la_inversion_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-cescar.PDF',  # [E] Cesión de cartera de créditos
         base / 'TO_cesion_cartera_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-cirmo3.pdf',  # [N] Circulación monetaria
         base / 'TO_circulacion_monetaria_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-cladeu.pdf',  # [E] Clasificación de deudores
         base / 'TO_clasificacion_deudores_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-coltit.pdf',  # [N] Colocación de títulos valores de deuda y obtención de líneas
         base / 'TO_colocacion_de_titulos_valores_de_deuda_y_obtencion_de_lineas_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-icmecma.pdf',  # [N] Comunicación por medios electrónicos para el medio ambiente
         base / 'TO_comunicacion_por_medios_electronicos_para_el_cuidado_del_med_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-convca.pdf',  # [N] Conversión cambiaria
         base / 'TO_conversion_cambiaria_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ctavis.pdf',  # [N] Cuentas a la vista cajas de crédito cooperativas
         base / 'TO_cuentas_a_la_vista_abiertas_en_las_cajas_de_credito_cooperat_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ccbcra.pdf',  # [N] Cuentas corrientes y otras cuentas a la vista
         base / 'TO_cuentas_corrientes_y_otras_cuentas_a_la_vista_de_las_entidad_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ctacor.pdf',  # [N] Cuentas de corresponsalía
         base / 'TO_cuentas_de_corresponsalia_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-depaho.pdf',  # [E] Depósitos de ahorro, cuenta sueldo y especiales
         base / 'TO_depositos_ahorro_cuenta_sueldo_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-depinv.pdf',  # [E] Depósitos e inversiones a plazo
         base / 'TO_depositos_inversiones_plazo_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-micemp.pdf',  # [N] Determinación de la condición de micro pequeña mediana empresa
         base / 'TO_determinacion_de_la_condicion_de_micro_pequena_o_mediana_emp_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-dmrd.pdf',  # [N] Disciplina de Mercado Requisitos mínimos de divulgación
         base / 'TO_disciplina_de_mercado_requisitos_minimos_de_divulgacion_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-jAFIP.pdf',  # [N] Disposiciones judiciales originadas en juicios entablados por ARCA
         base / 'TO_disposiciones_judiciales_originadas_en_juicios_entablados_po_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-disres.pdf',  # [E] Distribución de resultados
         base / 'TO_distribucion_resultados_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-docvig.pdf',  # [E] Documentos de identificación en vigencia
         base / 'TO_documentos_identificacion_vigencia_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-efemin.pdf',  # [E] Efectivo mínimo
         base / 'TO_efectivo_minimo_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-evacre.pdf',  # [E] Evaluaciones crediticias
         base / 'TO_evaluaciones_crediticias_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-expaef.pdf',  # [E] Expansión de entidades financieras
         base / 'TO_expansion_entidades_financieras_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-excbio.pdf',  # [E] Exterior y cambios
         base / 'TO_exterior_cambios_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-fclef.pdf',  # [E] Fideicomisos financieros comprendidos en la LEF
         base / 'TO_fideicomisos_financieros_lef_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-finsec.pdf',  # [E] Financiamiento al sector público no financiero
         base / 'TO_financiamiento_sector_publico_no_financiero_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-fabcra.pdf',  # [N] Firmas Autorizadas ante el BCRA
         base / 'TO_firmas_autorizadas_ante_el_bcra_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-fgarcp.pdf',  # [E] Fondos de garantía de carácter público
         base / 'TO_fondos_garantia_caracter_publico_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-garant.pdf',  # [E] Garantías
         base / 'TO_garantias_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-garopt.pdf',  # [N] Garantías por intermediación en operaciones entre terceros
         base / 'TO_garantias_por_intermediacion_en_operaciones_entre_terceros_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-gescre.pdf',  # [E] Gestión crediticia
         base / 'TO_gestion_crediticia_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-graloc.pdf',  # [N] Gestión de riesgos asociados a liquidación de operaciones de cambio
         base / 'TO_gestion_de_riesgos_asociados_a_la_liquidacion_de_operaciones_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-gracre.pdf',  # [E] Graduación del crédito
         base / 'TO_graduacion_credito_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-gerc.pdf',  # [E] Grandes exposiciones al riesgo de crédito
         base / 'TO_grandes_exposiciones_riesgo_credito_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-horari.pdf',  # [N] Horario de las entidades financieras
         base / 'TO_horario_de_las_entidades_financieras_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-incuca.pdf',  # [N] Incumplimientos de capitales mínimos y relaciones técnicas
         base / 'TO_incumplimientos_de_capitales_minimos_y_relaciones_tecnicas_c_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-consyr.pdf',  # [N] Instrumentación, conservación y reproducción de documentos
         base / 'TO_instrumentacion_conservacion_y_reproduccion_de_documentos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-fimipyme.pdf',  # [N] Línea de financiamiento para la inversión productiva MiPyME
         base / 'TO_linea_de_financiamiento_para_la_inversion_productiva_de_mipy_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-lingob.pdf',  # [E] Lineamientos para el gobierno societario en entidades financieras
         base / 'TO_lineamientos_gobierno_societario_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-lingeef.pdf',  # [E] Lineamientos para la gestión de riesgos en EF
         base / 'TO_lineamientos_gestion_riesgos_ef_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-rrci.pdf',  # [N] Lineamientos para la respuesta y recuperación ante ciberincidentes
         base / 'TO_lineamientos_para_la_respuesta_y_recuperacion_ante_ciberinci_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-manori.pdf',  # [N] Manuales de originación y administración de préstamos
         base / 'TO_manuales_de_originacion_y_administracion_de_prestamos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-seguef.pdf',  # [N] Medidas mínimas de seguridad en entidades financieras
         base / 'TO_medidas_minimas_de_seguridad_en_entidades_financieras_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI2-AE.pdf',  # [N] Normas mínimas auditorías externas casas y agencias de cambio
         base / 'TO_normas_minimas_sobre_auditorias_externas_para_casas_y_agenci_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-nmaeef.pdf',  # [N] Normas mínimas auditorías externas para entidades financieras
         base / 'TO_normas_minimas_sobre_auditorias_externas_para_entidades_fina_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI2-CI.pdf',  # [N] Normas mínimas controles internos casas y agencias de cambio
         base / 'TO_normas_minimas_sobre_controles_internos_para_casas_y_agencia_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-nmcief.pdf',  # [N] Normas mínimas controles internos para entidades financieras
         base / 'TO_normas_minimas_sobre_controles_internos_para_entidades_finan_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-opefci.pdf',  # [N] Operaciones al contado a liquidar y a término pases cauciones
         base / 'TO_operaciones_al_contado_a_liquidar_y_a_termino_pases_caucione_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-opecam.pdf',  # [E] Operadores de cambio
         base / 'TO_operadores_cambio_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ordcom.pdf',  # [E] Ordenamiento, emisión y divulgación de Comunicaciones
         base / 'TO_ordenamiento_emision_comunicaciones_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-osapsa.pdf',  # [N] Otros servicios y actividades prestados por sujetos alcanzados
         base / 'TO_otros_servicios_y_actividades_prestados_por_sujetos_alcanzad_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-pagjub.pdf',  # [N] Pago de beneficios de la seguridad social por cuenta de ANSES
         base / 'TO_pago_de_beneficios_de_la_seguridad_social_por_cuenta_de_la_a_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-retype.pdf',  # [N] Pago de retiros y pensiones militares
         base / 'TO_pago_de_retiros_y_pensiones_militares_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-pfmipyme.pdf',  # [N] Plataformas para el financiamiento MiPyME
         base / 'TO_plataformas_para_el_financiamiento_mipyme_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-polcre.pdf',  # [E] Política de crédito
         base / 'TO_politica_credito_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-pognme.pdf',  # [N] Posición global neta de moneda extranjera
         base / 'TO_posicion_global_neta_de_moneda_extranjera_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-optico.pdf',  # [E] Presentación de informaciones al BCRA
         base / 'TO_presentacion_informaciones_soportes_opticos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-lavdin.pdf',  # [E] Prevención del lavado de activos del financiamiento del terrorismo
         base / 'TO_prevencion_lavado_dinero_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-prevmi.pdf',  # [E] Previsiones mínimas por riesgo de incobrabilidad
         base / 'TO_previsiones_minimas_incobrabilidad_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-pimf.pdf',  # [N] Principios para las infraestructuras del mercado financiero
         base / 'TO_principios_para_las_infraestructuras_del_mercado_financiero_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-pusf.pdf',  # [E] Protección de los usuarios de servicios financieros
         base / 'TO_proteccion_usuarios_servicios_financieros_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-pscpp.pdf',  # [N] Proveedores de servicios de créditos entre particulares por plataformas
         base / 'TO_proveedores_de_servicios_de_creditos_entre_particulares_a_tr_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-psp.pdf',  # [N] Proveedores de servicios de pago
         base / 'TO_proveedores_de_servicios_de_pago_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-apnf.pdf',  # [E] Proveedores no financieros de crédito
         base / 'TO_asistencia_proveedores_no_financieros_credito_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-raapal.pdf',  # [N] Ratio de apalancamiento
         base / 'TO_ratio_de_apalancamiento_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ratio.pdf',  # [N] Ratio de cobertura de liquidez
         base / 'TO_ratio_de_cobertura_de_liquidez_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ratiofn.pdf',  # [N] Ratio de fondeo neto estable
         base / 'TO_ratio_de_fondeo_neto_estable_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-rdbcra.pdf',  # [N] Régimen disciplinario a cargo del BCRA
         base / 'TO_regimen_disciplinario_a_cargo_del_banco_central_de_la_republ_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-regpri.pdf',  # [N] Régimen para facilitar privatización de Bancos Provinciales y Municipales
         base / 'TO_regimen_para_facilitar_la_privatizacion_de_bancos_provincial_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ctacte.pdf',  # [N] Reglamentación de la cuenta corriente bancaria
         base / 'TO_reglamentacion_de_la_cuenta_corriente_bancaria_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-relact.pdf',  # [N] Relación para los activos inmovilizados y otros conceptos
         base / 'TO_relacion_para_los_activos_inmovilizados_y_otros_conceptos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-repefe.pdf',  # [N] Representantes de entidades financieras del exterior no autorizadas
         base / 'TO_representantes_de_entidades_financieras_del_exterior_no_auto_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-rmrtsd.pdf',  # [E] Requisitos mínimos gestión y control riesgos de tecnología y seguridad
         base / 'TO_requisitos_minimos_riesgos_tecnologia_seguridad_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-rmgcti.pdf',  # [N] Requisitos mínimos gestión y control riesgos tecnología seguridad EF
         base / 'TO_requisitos_minimos_para_la_gestion_y_control_de_los_riesgos__actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-reqcac.pdf',  # [N] Requisitos Operativos Mínimos Tecnología Sistemas Casas y Agencias
         base / 'TO_requisitos_operativos_minimos_de_tecnologia_y_sistemas_de_in_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-secfin.pdf',  # [N] Secreto financiero
         base / 'TO_secreto_financiero_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-servco.pdf',  # [N] Servicios complementarios de la actividad financiera
         base / 'TO_servicios_complementarios_de_la_actividad_financiera_y_activ_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-atm.pdf',  # [N] Sistema Nacional de Pagos Cajeros automáticos
         base / 'TO_sistema_nacional_de_pagos_cajeros_automaticos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-cec.pdf',  # [N] Sistema Nacional de Pagos Cámaras electrónicas de compensación
         base / 'TO_sistema_nacional_de_pagos_camaras_electronicas_de_compensaci_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-cheq.pdf',  # [N] Sistema Nacional de Pagos Cheques y otros instrumentos compensables
         base / 'TO_sistema_nacional_de_pagos_cheques_y_otros_instrumentos_compe_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-debin.pdf',  # [N] Sistema Nacional de Pagos Débito Inmediato
         base / 'TO_sistema_nacional_de_pagos_debito_inmediato_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-dd.pdf',  # [N] Sistema Nacional de Pagos Débitos Directos
         base / 'TO_sistema_nacional_de_pagos_debitos_directos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-mep.pdf',  # [N] Sistema Nacional de Pagos MEP
         base / 'TO_sistema_nacional_de_pagos_medio_electronico_de_pagos_mep_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-spd.pdf',  # [E] Sistema Nacional de Pagos Servicios de pago
         base / 'TO_sistema_nacional_pagos_servicios_pago_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-tr-nc.pdf',  # [N] Sistema Nacional de Pagos Transferencias Normas complementarias
         base / 'TO_sistema_nacional_de_pagos_transferencias_normas_complementar_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-SNP-tr.pdf',  # [N] Sistema Nacional de Pagos Transferencias
         base / 'TO_sistema_nacional_de_pagos_transferencias_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-socgar.pdf',  # [N] Sociedades de garantía recíproca inscriptas en el Banco Central
         base / 'TO_sociedades_de_garantia_reciproca_inscriptas_en_el_banco_cent_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-supcon.pdf',  # [N] Supervisión consolidada
         base / 'TO_supervision_consolidada_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-tasint.pdf',  # [E] Tasas de interés en las operaciones de crédito
         base / 'TO_tasas_interes_operaciones_credito_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-traval.pdf',  # [N] Transportadoras de valores
         base / 'TO_transportadoras_de_valores_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-venliq.pdf',  # [N] Ventanilla de liquidez del BCRA
         base / 'TO_ventanilla_de_liquidez_del_bcra_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-verac.pdf',  # [N] Veracidad de las registraciones contables
         base / 'TO_veracidad_de_las_registraciones_contables_actual.pdf'),
        # === RÉGIMEN INFORMATIVO ===
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI2-CS.pdf',  # [N] RI Casas y Agencias de Cambio Contable Anual
         base / 'TO_ri_casas_y_agencias_de_cambio_contable_anual_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI2-PM.pdf',  # [N] RI Casas y Agencias de Cambio Plan y Manual de Cuentas
         base / 'TO_ri_casas_y_agencias_de_cambio_plan_y_manual_de_cuentas_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/RI-DCPC.pdf',  # [N] RI Disposiciones complementarias al plan de cuentas
         base / 'TO_ri_disposiciones_complementarias_al_plan_de_cuentas_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/RI-NIIF.pdf',  # [E] RI Estados financieros para publicación trimestral anual (NIIF)
         base / 'TO_regimen_informativo_niif_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-FCEM.pdf',  # [N] RI Facturas de Crédito Electrónicas MiPyME
         base / 'TO_ri_facturas_de_credito_electronicas_mipyme_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-ICPIPSP.pdf',  # [N] RI Informe Contadores Públicos Independientes sobre cumplimiento
         base / 'TO_ri_informe_de_contadores_publicos_independientes_sobre_cumpl_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-IESINAP.pdf',  # [N] RI Informe especial cumplimiento Proveedores no financieros
         base / 'TO_ri_informe_especial_de_cumplimiento_requerido_por_las_normas_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-IECCM.pdf',  # [N] RI Informe Especial Capitales Mínimos
         base / 'TO_ri_informe_especial_respecto_del_cumplimiento_de_capitales_m_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-IEPSP.pdf',  # [N] RI Informe especial cumplimiento Proveedores no financieros
         base / 'TO_ri_informe_especial_sobre_el_cumplimiento_de_las_normas_prov_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/manual.pdf',  # [N] RI Manual de Cuentas vigente al 31-12-17
         base / 'TO_ri_manual_de_cuentas_vigente_al_31_12_17_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/plandecuentas.pdf',  # [N] RI Plan de cuentas
         base / 'TO_ri_plan_de_cuentas_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ri-pnp.pdf',  # [N] RI Plan de negocios y proyecciones
         base / 'TO_ri_plan_de_negocios_y_proyecciones_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-PFMIPYME.pdf',  # [N] RI Plataformas para el Financiamiento MiPyME
         base / 'TO_ri_plataformas_para_el_financiamiento_mipyme_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-LAFT.pdf',  # [N] RI Prevención del Lavado de Activos Financiamiento del Terrorismo
         base / 'TO_ri_prevencion_del_lavado_de_activos_del_financiamiento_del_t_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-PSCPP.pdf',  # [N] RI Proveedores de servicios de créditos entre particulares
         base / 'TO_ri_proveedores_de_servicios_de_creditos_entre_particulares_a_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-PSPAPT.pdf',  # [N] RI Proveedores de Servicios de Pago Adquirentes pagos con tarjeta
         base / 'TO_ri_proveedores_de_servicios_de_pago_adquirentes_de_pagos_con_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-PSPII.pdf',  # [N] RI Proveedores de Servicios de Pago Información Contable
         base / 'TO_ri_proveedores_de_servicios_de_pago_informacion_contable_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-PSPRCA.pdf',  # [N] RI Proveedores de Servicios de Pago Redes de Cajeros Automáticos
         base / 'TO_ri_proveedores_de_servicios_de_pago_redes_de_cajeros_automat_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-PSP.pdf',  # [N] RI Proveedores de servicios de pago que ofrecen cuentas de pago
         base / 'TO_ri_proveedores_de_servicios_de_pago_que_ofrecen_cuentas_de_p_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-ACSF.pdf',  # [N] RI Cont Mensual Agencias complementarias de servicios financieros
         base / 'TO_ri_cont_mensual_agencias_complementarias_de_servicios_financ_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-AO.pdf',  # [N] RI Cont Mensual Anticipo de Operaciones
         base / 'TO_ri_cont_mensual_anticipo_de_operaciones_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RIbspc.pdf',  # [N] RI Cont Mensual Balance de Saldos
         base / 'TO_ri_cont_mensual_balance_de_saldos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-BDP.pdf',  # [N] RI Cont Mensual Base de Datos Padrón
         base / 'TO_ri_cont_mensual_base_de_datos_padron_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-CHR.pdf',  # [N] RI Cont Mensual Cheques Rechazados
         base / 'TO_ri_cont_mensual_cheques_rechazados_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-DSF.pdf',  # [N] RI Cont Mensual Deudores del Sistema Financiero
         base / 'TO_ri_cont_mensual_deudores_del_sistema_financiero_y_composicio_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-RML.pdf',  # [N] RI Cont Mensual Efectivo mínimo y aplicación de recursos
         base / 'TO_ri_cont_mensual_efectivo_minimo_y_aplicacion_de_recursos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-Con.pdf',  # [N] RI Cont Mensual Estado de Consolidación de Entidades Locales
         base / 'TO_ri_cont_mensual_estado_de_consolidacion_de_entidades_locales_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-ESD.PDF',  # [N] RI Cont Mensual Estado de Situación de Deudores Consolidado
         base / 'TO_ri_cont_mensual_estado_de_situacion_de_deudores_consolidado_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-CM.pdf',  # [E] RI Cont Mensual Exigencia e integración de capitales mínimos
         base / 'TO_regimen_informativo_contable_mensual_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-TAR.pdf',  # [E] RI Cont Mensual Financiamiento con tarjetas de crédito
         base / 'TO_regimen_informativo_tarjetas_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-GERC.pdf',  # [N] RI Cont Mensual Grandes exposiciones al riesgo de crédito
         base / 'TO_ri_cont_mensual_grandes_exposiciones_al_riesgo_de_credito_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-II-31-12-19.pdf',  # [N] RI Cont Mensual Información Institucional EF y Cambiarias
         base / 'TO_ri_cont_mensual_informacion_institucional_de_entidades_finan_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-ITME.pdf',  # [N] RI Cont Mensual Información sobre tenencias en moneda extranjera
         base / 'TO_ri_cont_mensual_informacion_sobre_tenencias_en_moneda_extran_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-MSRL.pdf',  # [N] RI Cont Mensual Medición y Seguimiento del Riesgo de Liquidez
         base / 'TO_ri_cont_mensual_medicion_y_seguimiento_del_riesgo_de_liquide_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-MMSEF.pdf',  # [N] RI Cont Mensual Medidas mínimas de seguridad en EF
         base / 'TO_ri_cont_mensual_medidas_minimas_de_seguridad_en_entidades_fi_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-nge.pdf',  # [N] RI Cont Mensual Normas generales
         base / 'TO_ri_cont_mensual_normas_generales_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-OT.pdf',  # [N] RI Cont Mensual Operaciones a Término
         base / 'TO_ri_cont_mensual_operaciones_a_termino_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-OC.pdf',  # [N] RI Cont Mensual Operaciones de Cambio
         base / 'TO_ri_cont_mensual_operaciones_de_cambio_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-Rem.pdf',  # [N] RI Cont Mensual Pago de Remuneraciones en Cuenta Bancaria
         base / 'TO_ri_cont_mensual_pago_de_remuneraciones_mediante_acreditacion_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-PGN.pdf',  # [N] RI Cont Mensual Posición Global Neta en Moneda Extranjera
         base / 'TO_ri_cont_mensual_posicion_global_neta_en_moneda_extranjera_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-RCL.pdf',  # [N] RI Cont Mensual Ratio de Cobertura de Liquidez
         base / 'TO_ri_cont_mensual_ratio_de_cobertura_de_liquidez_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-CR.pdf',  # [N] RI Cont Mensual Reclamos
         base / 'TO_ri_cont_mensual_reclamos_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-AI.pdf',  # [N] RI Cont Mensual Relación para activos inmovilizados
         base / 'TO_ri_cont_mensual_relacion_para_los_activos_inmovilizados_y_ot_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-SAOFE.pdf',  # [N] RI Cont Mensual Seguimiento anticipos y otras financiaciones exportaciones
         base / 'TO_ri_cont_mensual_seguimiento_de_anticipos_y_otras_financiacio_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-SECOEXPO.pdf',  # [N] RI Cont Mensual Seguimiento negociaciones de divisas exportaciones
         base / 'TO_ri_cont_mensual_seguimiento_de_las_negociaciones_de_divisas__actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI–SPI.pdf',  # [N] RI Cont Mensual Seguimiento de Pagos de Importaciones
         base / 'TO_ri_cont_mensual_seguimiento_de_pagos_de_importaciones_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-TVF.pdf',  # [N] RI Cont Mensual Títulos Valores
         base / 'TO_ri_cont_mensual_titulos_valores_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-Transpa.pdf',  # [E] RI Cont Mensual Transparencia
         base / 'TO_regimen_informativo_transparencia_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-SEF.pdf',  # [N] RI Cont Mensual Unidades de servicios de las EF
         base / 'TO_ri_cont_mensual_unidades_de_servicios_de_las_entidades_finan_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-TII.pdf',  # [N] RI Cont Mensual Transferencias Inmediatas Intraentidades
         base / 'TO_ri_cont_mensual_transferencias_inmediatas_intraentidades_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-ri-cc.pdf',  # [N] RI para Cajas de Crédito contable
         base / 'TO_ri_para_cajas_de_credito_contable_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-CcNA.pdf',  # [N] RI para Cajas de Crédito Normas de Auditoría
         base / 'TO_ri_para_cajas_de_credito_normas_de_auditoria_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-CCPNP.pdf',  # [N] RI para Cajas de Crédito Plan de Negocios y Proyecciones
         base / 'TO_ri_para_cajas_de_credito_plan_de_negocios_y_proyecciones_actual.pdf'),
        ('https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-RI-TSA.pdf',  # [N] RI para supervisión
         base / 'TO_ri_para_supervision_actual.pdf'),
    ]
    counts = {"ok": 0, "skip": 0, "fail": 0}
    for url, out in items:
        status, _ = download_and_save(
            client, ws, url, out, categoria="TO_actual",
        )
        ws.log(f"[B1] {status} {url} -> {out.name}")
        if status == "ok":
            counts["ok"] += 1
        elif status.startswith("skip"):
            counts["skip"] += 1
        else:
            counts["fail"] += 1
    ws.save_checkpoint("B1", {"counts": counts})
    ws.log(f"=== B.1 END counts={counts} ===")
    return counts


def step_B2(client: RateLimitedClient, ws: Workspace) -> dict:
    ws.log("=== B.2 START — Marco legal ===")
    counts = {"ok": 0, "skip": 0, "fail": 0}

    # a) Carta Orgánica (PDF directo)
    url = "https://www.bcra.gob.ar/Pdfs/MarcoLegal/CartaOrganica.pdf"
    out = RAW_DIR / "00_marco_legal/Ley_24144_Carta_Organica_BCRA.pdf"
    status, _ = download_and_save(client, ws, url, out, categoria="marco_legal", numero="Ley_24144")
    ws.log(f"[B2-a] {status} {url}")
    counts["ok" if status == "ok" else ("skip" if status.startswith("skip") else "fail")] += 1

    # b/c/d) HTML → guardar HTML (no convertimos a PDF; lo dejo como .html con
    # nota en log: la conversión HTML→PDF requiere wkhtmltopdf u otro engine
    # opcional. Lo guardamos como .pdf si el endpoint sirve PDF, si no .html.)
    html_targets = [
        ("https://servicios.infoleg.gob.ar/infolegInternet/anexos/15000-19999/16641/texact.htm",
         RAW_DIR / "00_marco_legal/Ley_19359_Regimen_Penal_Cambiario.html",
         "Ley_19359"),
        ("https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=72104",
         RAW_DIR / "00_marco_legal/Decreto_260_2002.html",
         "Decreto_260_2002"),
        ("https://www.argentina.gob.ar/normativa/nacional/decreto-609-2019-327251/texto",
         RAW_DIR / "00_marco_legal/Decreto_609_2019.html",
         "Decreto_609_2019"),
        ("https://servicios.infoleg.gob.ar/infolegInternet/anexos/15000-19999/16071/texact.htm",
         RAW_DIR / "00_marco_legal/Ley_21526_LEF.html",
         "Ley_21526"),
    ]
    for url, out, num in html_targets:
        if out.exists() and out.stat().st_size > 1024:
            ws.log(f"[B2] skip-existing {url}")
            counts["skip"] += 1
            continue
        if url in ws.manifiesto_urls():
            counts["skip"] += 1
            continue
        resp = client.get(url)
        if resp is None or resp.status_code != 200:
            ws.log(f"[B2-fail] {url} status={getattr(resp, 'status_code', 'net-fail')}")
            counts["fail"] += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(resp.content)
        # extraer texto plano del html (heurística simple) para titulo
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.content, "html.parser")
            titulo = (soup.title.text.strip() if soup.title else "")[:200]
            txt = soup.get_text(" ", strip=True)
            fecha_doc = fecha_from_pdf_text(txt[:5000])
        except Exception:  # noqa: BLE001
            titulo = ""
            fecha_doc = ""
        record = {
            "categoria": "marco_legal",
            "archivo_local": str(out.relative_to(PROJECT_ROOT)),
            "url_origen": url,
            "numero": num,
            "fecha_descarga": now_iso(),
            "fecha_documento": fecha_doc,
            "tamano_bytes": len(resp.content),
            "num_paginas": "",
            "titulo_extraido": titulo,
            "relevancia_mulc": "true",
            "keywords_encontradas": "",
            "tiene_version_tachado_negrita": "",
        }
        ws.add_manifiesto_row(record)
        ws.log(f"[B2] ok-html {url} -> {out.name}")
        counts["ok"] += 1

    ws.save_checkpoint("B2", {"counts": counts})
    ws.log(f"=== B.2 END counts={counts} ===")
    return counts


def step_B3(client: RateLimitedClient, ws: Workspace) -> dict:
    """TOs históricos: enumerar fechas plausibles y conservar las que devuelven PDF.

    Patrón confirmado: YY-MM-DD (2 dígitos año), path /pdfs/texord/texord_viejos/.
    Las versiones reales salen en días arbitrarios — probamos todos los días del mes.
    """
    ws.log("=== B.3 START — TOs históricos ===")
    counts = {"ok": 0, "skip": 0, "404": 0, "fail": 0}

    # Fechas conocidas (que aparecen en resultados Google)
    known_iso = [
        "2024-06-02", "2025-02-09", "2024-01-25", "2022-05-04",
        "2021-12-15", "2019-01-24", "2021-11-10",
    ]

    # Enumeración: 2017..año_actual, todos los dias del mes
    today = datetime.now(timezone.utc).date()
    enum_dates = []
    for year in range(2017, today.year + 1):
        for month in range(1, 13):
            for d in range(1, 32):
                try:
                    dt = datetime(year, month, d).date()
                except ValueError:
                    continue
                if dt > today:
                    continue
                iso = dt.isoformat()
                if iso not in known_iso:
                    enum_dates.append(iso)

    all_iso = known_iso + enum_dates
    ws.log(f"[B3] candidatos: {len(all_iso)} fechas x 2 TOs = {len(all_iso)*2} URLs")

    # 2 TOs: el path /pdfs/texord/texord_viejos/ funciona (sin "archivos")
    patrones = [
        ("https://www.bcra.gob.ar/pdfs/texord/texord_viejos/v-excbio_{yy}.pdf",
         "exterior_cambios", "TO_historico_excbio"),
        ("https://www.bcra.gob.ar/pdfs/texord/texord_viejos/v-opecam_{yy}.pdf",
         "operadores_cambio", "TO_historico_opecam"),
    ]
    encontradas: list[dict] = []

    cnt = 0
    for url_pat, label, categoria in patrones:
        for iso in all_iso:
            # ISO YYYY-MM-DD -> YY-MM-DD para la URL
            yyyy, mm, dd = iso.split("-")
            yy = yyyy[-2:]
            url = url_pat.format(yy=f"{yy}-{mm}-{dd}")
            if "exterior" in label:
                out = RAW_DIR / f"01_textos_ordenados/historicos/TO_exterior_cambios_{iso}.pdf"
            else:
                out = RAW_DIR / f"01_textos_ordenados/historicos/TO_operadores_cambio_{iso}.pdf"
            status, rec = download_and_save(
                client, ws, url, out, categoria=categoria, numero=iso,
            )
            cnt += 1
            if status == "ok":
                counts["ok"] += 1
                encontradas.append({"label": label, "fecha": iso, "url": url})
                ws.log(f"[B3] HIT {label} {iso}")
            elif status.startswith("skip"):
                counts["skip"] += 1
            elif status == "404":
                counts["404"] += 1
            else:
                counts["fail"] += 1
            if cnt % 100 == 0:
                ws.save_checkpoint("B3", {"counts": counts, "last_url": url})
                ws.log(f"[B3] checkpoint cnt={cnt} counts={counts}")

    ws.save_checkpoint("B3", {"counts": counts, "encontradas": encontradas})
    ws.log(f"=== B.3 END counts={counts} encontradas={len(encontradas)} ===")
    return counts


def step_B_letra(
    client: RateLimitedClient,
    ws: Workspace,
    letra: str,
    rango: tuple[int, int],
    out_subdir: str,
    require_filter: bool = True,
    workers: int = 1,
) -> dict:
    """Descarga genérica de Comunicaciones letra A/B/C/P en un rango.

    Si workers > 1, usa ThreadPoolExecutor. El rate limit es global compartido
    (RateLimitedClient maneja el lock internamente).
    """
    ws.log(f"=== B-{letra} START rango={rango} filter={require_filter} workers={workers} ===")
    counts = {"ok": 0, "skip": 0, "404": 0, "irrelevant": 0, "fail": 0}
    counts_lock = threading.Lock()
    cnt_holder = [0]
    t_start = time.time()

    def process_one(n: int) -> str:
        url = f"https://www.bcra.gob.ar/archivos/Pdfs/comytexord/{letra}{n}.pdf"
        tmp_out = RAW_DIR / out_subdir / f"{letra}{n}.pdf"
        status, _ = download_and_save(
            client, ws, url, tmp_out,
            categoria=f"comunicacion_{letra}",
            numero=f"{letra}{n}",
            require_keyword_filter=require_filter,
            fallback_tachado_for_A=str(n) if letra == "A" else None,
            name_with_slug_prefix=f"{letra}{n}",
        )
        with counts_lock:
            if status == "ok":
                counts["ok"] += 1
            elif status.startswith("skip"):
                counts["skip"] += 1
            elif status == "404":
                counts["404"] += 1
            elif status == "irrelevant":
                counts["irrelevant"] += 1
            else:
                counts["fail"] += 1
            cnt_holder[0] += 1
            cnt = cnt_holder[0]
            if cnt % 100 == 0:
                elapsed = time.time() - t_start
                rate = cnt / elapsed if elapsed > 0 else 0
                ws.save_checkpoint(f"B-{letra}", {"counts": counts.copy(), "last_n_processed": n})
                ws.log(f"[B-{letra}] checkpoint cnt={cnt} counts={counts} elapsed={elapsed:.0f}s rate={rate:.2f}/s")
                check_corpus_size(ws)
        return status

    last_processed_n = ws.load_checkpoint(f"B-{letra}").get("last_n_processed", rango[0] - 1)
    # Idempotencia: confiamos en skip-existing/skip-already-manifest dentro de
    # download_and_save; igual barremos todo el rango.
    numeros = list(range(rango[0], rango[1] + 1))

    if workers <= 1:
        for n in numeros:
            process_one(n)
    else:
        with ThreadPoolExecutor(max_workers=workers) as exe:
            futures = [exe.submit(process_one, n) for n in numeros]
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as e:  # noqa: BLE001
                    ws.log(f"[worker-exception] {type(e).__name__}: {e}")

    elapsed_total = time.time() - t_start
    avg_latency = client.avg_latency()
    ws.save_checkpoint(f"B-{letra}", {
        "counts": counts, "last_n_processed": rango[1],
        "elapsed_seconds": elapsed_total,
        "client_avg_latency_seconds": avg_latency,
        "client_total_requests": client.total_requests,
        "client_total_errors": client.total_request_errors,
        "persistent_failures_count": len(client.persistent_failures),
    })
    ws.log(
        f"=== B-{letra} END counts={counts} elapsed={elapsed_total:.0f}s "
        f"avg_latency={avg_latency:.2f}s n_reqs={client.total_requests} "
        f"errs={client.total_request_errors} persistent_fails={len(client.persistent_failures)} ==="
    )
    return counts


def step_B5(client: RateLimitedClient, ws: Workspace, workers: int = 2) -> dict:
    """Tachado/negrita: para cada A relevante en el manifiesto, intentar -ec y -opc."""
    ws.log(f"=== B.5 START — tachado/negrita workers={workers} ===")
    t_start = time.time()
    counts = {"ok": 0, "skip": 0, "404": 0, "fail": 0}
    counts_lock = threading.Lock()

    relevantes_A: list[str] = []
    with (RAW_DIR / "manifiesto.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("categoria") == "comunicacion_A" and row.get("relevancia_mulc") == "true":
                num = row.get("numero", "").lstrip("A")
                if num.isdigit():
                    relevantes_A.append(num)
    ws.log(f"[B5] candidatos A relevantes: {len(relevantes_A)}")

    def process_one(num: str, sufijo: str) -> str:
        url = f"https://www.bcra.gob.ar/archivos/Pdfs/texord/texcomp/A{num}n-{sufijo}.pdf"
        out = RAW_DIR / f"06_tachado_negrita/A{num}n-{sufijo}.pdf"
        status, _ = download_and_save(
            client, ws, url, out,
            categoria="tachado_negrita",
            numero=f"A{num}n-{sufijo}",
        )
        with counts_lock:
            if status == "ok":
                counts["ok"] += 1
            elif status.startswith("skip"):
                counts["skip"] += 1
            elif status == "404":
                counts["404"] += 1
            else:
                counts["fail"] += 1
        return status

    tasks = [(num, suf) for num in relevantes_A for suf in ("ec", "opc")]
    if workers <= 1:
        for num, suf in tasks:
            process_one(num, suf)
    else:
        with ThreadPoolExecutor(max_workers=workers) as exe:
            futs = [exe.submit(process_one, n, s) for n, s in tasks]
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as e:  # noqa: BLE001
                    ws.log(f"[B5 worker-exception] {type(e).__name__}: {e}")

    elapsed = time.time() - t_start
    ws.save_checkpoint("B5", {"counts": counts, "elapsed_seconds": elapsed})
    ws.log(f"=== B.5 END counts={counts} elapsed={elapsed:.0f}s ===")
    return counts


def step_B9(client: RateLimitedClient, ws: Workspace) -> dict:
    ws.log("=== B.9 START — complementarios ===")
    counts = {"ok": 0, "skip": 0, "fail": 0, "crawled": 0}
    # a)
    url = "https://www.bcra.gob.ar/archivos/Pdfs/SistemasFinancierosYdePagos/marco%20normativo.pdf"
    out = RAW_DIR / "07_documentos_complementarios/marco_normativo_resumen.pdf"
    status, _ = download_and_save(client, ws, url, out, categoria="complementario", numero="marco_normativo")
    counts["ok" if status == "ok" else ("skip" if status.startswith("skip") else "fail")] += 1

    # b/c) crawl ligero: extraer todos los PDFs linkeados en bcra.gob.ar
    from bs4 import BeautifulSoup
    pages = [
        "https://www.bcra.gob.ar/normativa-de-exterior-y-cambios/",
        "https://www.bcra.gob.ar/SistemasFinancierosYdePagos/Regulaciones_exterior_y_cambios.asp",
    ]
    pdf_urls: set[str] = set()
    for page_url in pages:
        resp = client.get(page_url)
        if resp is None or resp.status_code != 200:
            ws.log(f"[B9-crawl-fail] {page_url}")
            continue
        soup = BeautifulSoup(resp.content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.lower().endswith(".pdf"):
                continue
            if href.startswith("/"):
                href = "https://www.bcra.gob.ar" + href
            if "bcra.gob.ar" in href:
                pdf_urls.add(href)
    ws.log(f"[B9-crawl] PDFs descubiertos en páginas: {len(pdf_urls)}")
    existing_urls = ws.manifiesto_urls()
    nuevos = [u for u in pdf_urls if u not in existing_urls]
    ws.log(f"[B9-crawl] PDFs nuevos a descargar: {len(nuevos)}")
    for url in nuevos:
        name = url.rsplit("/", 1)[-1].split("?")[0]
        out = RAW_DIR / "07_documentos_complementarios" / name
        status, _ = download_and_save(client, ws, url, out, categoria="complementario")
        counts["crawled"] += 1
        if status == "ok":
            counts["ok"] += 1
        elif status.startswith("skip"):
            counts["skip"] += 1
        else:
            counts["fail"] += 1
    ws.save_checkpoint("B9", {"counts": counts})
    ws.log(f"=== B.9 END counts={counts} ===")
    return counts


# -- main -----------------------------------------------------------------

STEPS: dict[str, Callable[[RateLimitedClient, Workspace], dict]] = {
    "B1": step_B1,
    "B2": step_B2,
    "B3": step_B3,
    "B4": lambda c, w: step_B_letra(c, w, "A", (6770, 8500), "02_comunicaciones_A", MULC_ONLY, workers=2),
    "B5": lambda c, w: step_B5(c, w, workers=2),
    "B6": lambda c, w: step_B_letra(c, w, "B", (11870, 13200), "03_comunicaciones_B", MULC_ONLY, workers=2),
    "B7": lambda c, w: step_B_letra(c, w, "C", (90000, 100000), "04_comunicaciones_C", MULC_ONLY, workers=2),
    "B8": lambda c, w: step_B_letra(c, w, "P", (50000, 55000), "05_comunicaciones_P", MULC_ONLY, workers=2),
    "B9": step_B9,
}


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    mulc_only = False
    if "--mulc-only" in args:
        mulc_only = True
        args.remove("--mulc-only")
    if not args or args[0] not in STEPS:
        print(f"uso: python {argv[0]} <{ '|'.join(STEPS) }> [--mulc-only]")
        return 1
    step_name = args[0]
    global MULC_ONLY
    MULC_ONLY = mulc_only
    ws = Workspace()
    client = RateLimitedClient(ws.log)
    ws.log(f"### run step={step_name} mulc_only={mulc_only} ###")
    counts = STEPS[step_name](client, ws)
    print(f"\nFINAL counts step={step_name}: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
