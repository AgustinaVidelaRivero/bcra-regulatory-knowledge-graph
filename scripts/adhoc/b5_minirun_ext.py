"""Mini-run EXTENDIDO de validacion (250 candidatos = 500 attempts).

Objetivo: forzar al menos 2 reciclajes (threshold=200) y validar:
- Throughput estable a lo largo del run (no degradacion post-reciclaje).
- Cero "ConnectionError: Max retries exceeded".
- session_recycle_count >= 2 al final.

Uso: python /tmp/b5_minirun_ext.py
"""
import csv
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "scraper"))
import download_bcra as dm  # noqa: E402

SAMPLE_N = 250


def main() -> int:
    print(f"=== mini-run EXTENDIDO: HEADERS={dm.HEADERS}")
    ws = dm.Workspace()
    client = dm.RateLimitedClient(ws.log)
    print(f"recycle_threshold={client._recycle_threshold}")

    relevantes_A: list[str] = []
    mf = dm.RAW_DIR / "manifiesto.csv"
    with mf.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("categoria") == "comunicacion_A" and row.get("relevancia_mulc") == "true":
                num = row.get("numero", "").lstrip("A")
                if num.isdigit():
                    relevantes_A.append(num)
            if len(relevantes_A) >= SAMPLE_N:
                break
    print(f"=== candidatos: {len(relevantes_A)}")

    tasks = [(num, suf) for num in relevantes_A for suf in ("ec", "opc")]
    print(f"=== tasks totales: {len(tasks)}")
    print()

    t0 = time.time()
    counts: dict[str, int] = {}
    interval_t0 = t0
    interval_count = 0
    interval_data: list[tuple[int, float, float]] = []  # (cnt, elapsed, interval_rate)
    for i, (num, suf) in enumerate(tasks, start=1):
        url = f"https://www.bcra.gob.ar/archivos/Pdfs/texord/texcomp/A{num}n-{suf}.pdf"
        out = dm.RAW_DIR / f"06_tachado_negrita/A{num}n-{suf}.pdf"
        status, _ = dm.download_and_save(
            client, ws, url, out,
            categoria="tachado_negrita",
            numero=f"A{num}n-{suf}",
        )
        counts[status] = counts.get(status, 0) + 1
        interval_count += 1
        # Reporte cada 50 attempts
        if i % 50 == 0 or i == len(tasks):
            now = time.time()
            elapsed = now - t0
            interval_dt = now - interval_t0
            interval_rate = interval_count / interval_dt if interval_dt > 0 else 0
            avg_rate = i / elapsed if elapsed > 0 else 0
            print(
                f"[{i:3d}/{len(tasks)}] elapsed={elapsed:.1f}s "
                f"interval_rate={interval_rate:.2f}/s (last {interval_count} attempts) "
                f"avg_rate={avg_rate:.2f}/s "
                f"recycles={client.session_recycle_count} "
                f"counts={counts} "
                f"errors={client.total_request_errors} "
                f"persistent={len(client.persistent_failures)}"
            )
            interval_data.append((i, elapsed, interval_rate))
            interval_t0 = now
            interval_count = 0
            sys.stdout.flush()

    elapsed = time.time() - t0
    avg_rate = len(tasks) / elapsed
    print()
    print(f"=== MINI-RUN EXTENDIDO END ===")
    print(f"  tasks={len(tasks)}  elapsed={elapsed:.1f}s ({elapsed/60:.1f} min)  avg_rate={avg_rate:.2f}/s  avg={elapsed/len(tasks):.2f}s/req")
    print(f"  counts={counts}")
    print(f"  client.total_requests={client.total_requests}")
    print(f"  client.total_request_errors={client.total_request_errors}")
    print(f"  client.persistent_failures={len(client.persistent_failures)}")
    print(f"  client.session_recycle_count={client.session_recycle_count}")
    if client.persistent_failures:
        print("  persistent-fails:")
        for u in client.persistent_failures[:10]:
            print(f"    {u}")

    # Stability analysis: throughput por intervalo
    print(f"\n=== Throughput por intervalos de 50 attempts ===")
    for (cnt, el, r) in interval_data:
        print(f"  cnt={cnt:3d} elapsed={el:6.1f}s  interval_rate={r:.3f}/s")
    rates = [r for (_, _, r) in interval_data]
    if rates:
        rmin, rmax = min(rates), max(rates)
        ravg = sum(rates) / len(rates)
        print(f"\n  rate min/avg/max: {rmin:.3f} / {ravg:.3f} / {rmax:.3f} (estable si max-min < 30%)")
        if ravg > 0:
            print(f"  variabilidad: {100*(rmax-rmin)/ravg:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
