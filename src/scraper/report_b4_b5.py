"""
Genera reporte completo B.4 + B.5 desde manifiesto + log + descartados.

Uso:
    python src/scraper/report_b4_b5.py
"""
from __future__ import annotations

import csv
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"


def main() -> None:
    mf = RAW / "manifiesto.csv"
    desc = RAW / "manifiesto_descartados.csv"
    log = RAW / "log.txt"

    a_rows: list[dict] = []
    tn_rows: list[dict] = []
    with mf.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("categoria") == "comunicacion_A":
                a_rows.append(row)
            elif row.get("categoria") == "tachado_negrita":
                tn_rows.append(row)

    descartados: list[dict] = []
    with desc.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("categoria") == "comunicacion_A":
                descartados.append(row)

    log_text = log.read_text(encoding="utf-8") if log.exists() else ""

    # Persistent fails (URLs)
    persistent_fail_urls = sorted(
        set(
            line.split(" ", 2)[2].strip()
            for line in log_text.splitlines()
            if "[persistent-fail]" in line and "/comytexord/A" in line
        )
    )
    # también algunos pueden ser de tachado (A{n}n-ec.pdf / A{n}n-opc.pdf)
    persistent_fail_tachado = sorted(
        set(
            line.split(" ", 2)[2].strip()
            for line in log_text.splitlines()
            if "[persistent-fail]" in line and "/texord/texcomp/A" in line
        )
    )

    # Fallback tachado activations
    fallback_lines = [
        line for line in log_text.splitlines()
        if "[fallback-tachado]" in line and "relevante via tachado" in line
    ]

    # Latency desde checkpoints (B-A END trae avg_latency)
    latency_match = re.search(r"B-A END counts=\S+ elapsed=([\d.]+)s avg_latency=([\d.]+)s n_reqs=(\d+) errs=(\d+) persistent_fails=(\d+)", log_text)
    elapsed_b4 = avg_latency_b4 = n_reqs_b4 = errs_b4 = pf_b4 = None
    if latency_match:
        elapsed_b4 = float(latency_match.group(1))
        avg_latency_b4 = float(latency_match.group(2))
        n_reqs_b4 = int(latency_match.group(3))
        errs_b4 = int(latency_match.group(4))
        pf_b4 = int(latency_match.group(5))

    # B.5 elapsed
    b5_match = re.search(r"B\.5 END counts=(\S+) elapsed=([\d.]+)s", log_text)
    elapsed_b5 = b5_counts_str = None
    if b5_match:
        b5_counts_str = b5_match.group(1)
        elapsed_b5 = float(b5_match.group(2))

    # Top keywords
    kw_counter = Counter()
    for r in a_rows:
        kws = r.get("keywords_encontradas", "")
        for kw in kws.split(";"):
            kw = kw.strip()
            if kw and kw != "tachado_negrita_existe":
                kw_counter[kw] += 1

    # Relevance por bloque de 200 (basado en numero A)
    blocks: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: {"ok": 0, "irr": 0})
    for r in a_rows:
        m = re.match(r"A(\d+)", r.get("numero", ""))
        if not m:
            continue
        n = int(m.group(1))
        block_start = (n // 200) * 200
        blocks[(block_start, block_start + 199)]["ok"] += 1
    for r in descartados:
        m = re.match(r"A(\d+)", r.get("numero", ""))
        if not m:
            continue
        n = int(m.group(1))
        block_start = (n // 200) * 200
        blocks[(block_start, block_start + 199)]["irr"] += 1

    # Tachado/negrita por A
    tn_for_A: dict[str, list[str]] = defaultdict(list)
    for r in tn_rows:
        num = r.get("numero", "")
        m = re.match(r"A(\d+)n-(ec|opc)", num)
        if m:
            tn_for_A[m.group(1)].append(m.group(2))

    # Fechas extremas
    a_dates = sorted(((r.get("fecha_documento", ""), r.get("numero", "")) for r in a_rows if r.get("fecha_documento")), key=lambda x: x[0])
    earliest = a_dates[0] if a_dates else ("?", "?")
    latest = a_dates[-1] if a_dates else ("?", "?")

    # Tamaños en disco
    def du(path: Path) -> int:
        if not path.exists():
            return 0
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())

    sz_a = du(RAW / "02_comunicaciones_A")
    sz_tn = du(RAW / "06_tachado_negrita")
    sz_total = du(RAW)

    # Salida
    print("=" * 70)
    print("REPORTE B.4 + B.5 — corpus de Comunicaciones A MULC")
    print("=" * 70)
    print()
    print("## 1. Counts finales")
    print(f"  - Comunicaciones A relevantes guardadas: {len(a_rows)}")
    print(f"  - Comunicaciones A descartadas:           {len(descartados)}")
    print(f"  - Versiones tachado/negrita guardadas:    {len(tn_rows)}")
    print(f"  - Persistent-fails (Comunicación A):      {len(persistent_fail_urls)}")
    print(f"  - Persistent-fails (tachado/negrita):     {len(persistent_fail_tachado)}")
    total_proc = len(a_rows) + len(descartados)
    if total_proc:
        rel_rate = 100 * len(a_rows) / total_proc
        print(f"  - Tasa de relevancia global:              {rel_rate:.1f}%")
    print()

    print("## 2. Tasa de relevancia por bloques de 200")
    for k in sorted(blocks.keys()):
        d = blocks[k]
        total = d["ok"] + d["irr"]
        rate = 100 * d["ok"] / total if total else 0
        print(f"  A{k[0]:5d}–A{k[1]:5d}: ok={d['ok']:3d}  irr={d['irr']:3d}  rate={rate:5.1f}%")
    print()

    print("## 3. Top 10 keywords MULC más frecuentes")
    for kw, c in kw_counter.most_common(10):
        print(f"  {c:4d}  {kw}")
    print()

    print("## 4. Activaciones del fallback tachado/negrita")
    print(f"  Total activaciones: {len(fallback_lines)}")
    if fallback_lines:
        print("  Casos:")
        for line in fallback_lines[:20]:
            m = re.search(r"\[fallback-tachado\] (A\d+) relevante via tachado.*$", line)
            if m:
                print(f"    {m.group(1)}")
        if len(fallback_lines) > 20:
            print(f"    ... ({len(fallback_lines)-20} más)")
    else:
        print("  Ninguna. Todas las A relevantes tenían keywords MULC en el primer 30%.")
        print("  → El criterio fallback es redundante en este rango.")
    print()

    print("## 5. Latencia y tiempos")
    print(f"  - B.4 elapsed: {elapsed_b4}s {'(' + str(round(elapsed_b4/60,1)) + ' min)' if elapsed_b4 else ''}")
    print(f"  - B.4 avg latency por request: {avg_latency_b4}s")
    print(f"  - B.4 total requests: {n_reqs_b4}")
    print(f"  - B.4 net errors:     {errs_b4}")
    print(f"  - B.5 elapsed: {elapsed_b5}s {'(' + str(round(elapsed_b5/60,1)) + ' min)' if elapsed_b5 else ''}")
    print(f"  - B.5 counts: {b5_counts_str}")
    print()

    print("## 6. Persistent fails")
    if persistent_fail_urls:
        print("  Comunicaciones A:")
        for u in persistent_fail_urls:
            print(f"    {u}")
    if persistent_fail_tachado:
        print("  Tachado/negrita:")
        for u in persistent_fail_tachado:
            print(f"    {u}")
    if not (persistent_fail_urls or persistent_fail_tachado):
        print("  Ninguno.")
    print()

    print("## 7. Tamaño en disco")
    def fmt(b: int) -> str:
        return f"{b/1024/1024:.1f} MB"
    print(f"  - 02_comunicaciones_A:  {fmt(sz_a)}")
    print(f"  - 06_tachado_negrita:   {fmt(sz_tn)}")
    print(f"  - data/raw total:       {fmt(sz_total)}")
    print()

    # Rango temporal
    print("## 8. Rango temporal de A relevantes")
    print(f"  Más antigua:  {earliest[1]} fecha={earliest[0]}")
    print(f"  Más reciente: {latest[1]} fecha={latest[0]}")
    print()


if __name__ == "__main__":
    main()
