"""
Retry batch de las URLs que persistent-failed durante B.4/B.5.
Usa timeout=30s (vs 15s normal) y reintentos limitados.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import download_bcra as dm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"


def collect_persistent_fails(log_path: Path) -> tuple[list[str], list[str]]:
    """Devuelve (urls_A, urls_tachado) deduplicados."""
    urls_A: set[str] = set()
    urls_tn: set[str] = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if "[persistent-fail]" not in line:
            continue
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        url = parts[2].strip()
        if "/comytexord/A" in url:
            urls_A.add(url)
        elif "/texord/texcomp/A" in url:
            urls_tn.add(url)
    return sorted(urls_A), sorted(urls_tn)


def main() -> int:
    ws = dm.Workspace()
    # Bump timeout temporalmente
    original_timeout = dm.HTTP_TIMEOUT
    dm.HTTP_TIMEOUT = 30
    client = dm.RateLimitedClient(ws.log)

    urls_A, urls_tn = collect_persistent_fails(RAW / "log.txt")
    ws.log(f"=== RETRY START — A={len(urls_A)} tachado={len(urls_tn)} timeout=30s ===")

    rescued = {"A_ok": 0, "A_irrelevant": 0, "A_still_fail": 0,
               "tn_ok": 0, "tn_still_fail": 0}

    # 1) Reintentar Comunicaciones A
    for url in urls_A:
        m = re.search(r"/(A\d+)\.pdf", url)
        if not m:
            continue
        numero = m.group(1)
        n_int = numero[1:]
        out = RAW / f"02_comunicaciones_A/{numero}.pdf"
        # Si ya se rescató antes (otra corrida), skip-existing actúa
        status, rec = dm.download_and_save(
            client, ws, url, out,
            categoria="comunicacion_A",
            numero=numero,
            require_keyword_filter=True,
            fallback_tachado_for_A=n_int,
            name_with_slug_prefix=numero,
        )
        ws.log(f"[RETRY-A] {numero} status={status}")
        if status == "ok":
            rescued["A_ok"] += 1
        elif status == "irrelevant":
            rescued["A_irrelevant"] += 1
        elif not status.startswith("skip"):
            rescued["A_still_fail"] += 1

    # 2) Reintentar tachado/negrita
    for url in urls_tn:
        m = re.search(r"/(A\d+n-(?:ec|opc))\.pdf", url)
        if not m:
            continue
        numero = m.group(1)
        out = RAW / f"06_tachado_negrita/{numero}.pdf"
        status, _ = dm.download_and_save(
            client, ws, url, out,
            categoria="tachado_negrita",
            numero=numero,
        )
        ws.log(f"[RETRY-TN] {numero} status={status}")
        if status == "ok":
            rescued["tn_ok"] += 1
        elif not status.startswith("skip"):
            rescued["tn_still_fail"] += 1

    dm.HTTP_TIMEOUT = original_timeout
    ws.log(f"=== RETRY END — {rescued} ===")
    print(f"\nResultado retry batch: {rescued}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
