#!/usr/bin/env python3
"""memoria_b63.py — La memoria de la máquina para B6.3 (etapa b1; decisiones de la autora del 27/10/2026, 11:31:49 y 11:35:20: «Que
el comando de N6 mida lo fijo después del reinicio y antes de lanzar. Con esa cifra decidimos P para las sesiones que cargan el
codificador: 1, o 2 si lo fijo queda en 5,4 GB o menos con tu cuenta. Lo mismo para B6.3 en el testigo.»).

  · `memoria_maquina`: la de data/experiment/banco_mcp/n6/memoria_n6.py (en HEAD, del commit de N6), copiada tal cual (vm_stat,
    `sysctl vm.swapusage` y `hw.memsize`): lo fijo es su `en_uso_gb` (las páginas activas, las fijas y las del compresor). El selftest
    controla que dé lo mismo que la de N6 sobre un `vm_stat` falso;
  · `regla_P(fijo, pico)`: la de la decisión 10, P = 2 si lo fijo más dos veces el pico de una sesión de B6.3 (su CLI, su Node y su
    servidor) queda en 14,5 GB o menos; si no, P = 1 (y 0 si ni una entra);
  · `guarda(P, pico, medir)`: antes de lanzar y antes de cada bloque, lo fijo de ese momento más P picos, hasta 14,5 GB. Si no entra,
    frena (código 13 del runner) y no cambia la P sola. Con sesiones corriendo, su memoria ya está en lo fijo: la guarda cuenta de más,
    del lado seguro.
"""
from __future__ import annotations

import re
import subprocess

LIMITE_GB = 14.5
GB = 1e9


def memoria_maquina() -> dict:
    vm = subprocess.run(["vm_stat"], capture_output=True, text=True, check=True).stdout
    pag = int(re.search(r"page size of (\d+) bytes", vm).group(1))
    v = {m.group(1).strip(): int(m.group(2)) for m in re.finditer(r"^(.+?):\s+(\d+)\.", vm, re.M)}
    sw = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, check=True).stdout
    usado = float(re.search(r"used = ([\d.]+)M", sw).group(1)) * 1024 * 1024
    total = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True).stdout)
    libres = v.get("Pages free", 0) + v.get("Pages speculative", 0)
    en_uso = (v.get("Pages active", 0) + v.get("Pages wired down", 0)
              + v.get("Pages occupied by compressor", 0)) * pag
    return {"total_gb": round(total / GB, 3), "libre_gb": round(libres * pag / GB, 3),
            "inactiva_gb": round(v.get("Pages inactive", 0) * pag / GB, 3), "en_uso_gb": round(en_uso / GB, 3),
            "compresor_gb": round(v.get("Pages occupied by compressor", 0) * pag / GB, 3), "swap_usado_gb": round(usado / GB, 3)}


def regla_P(fijo_gb: float, pico_gb: float, limite_gb: float = LIMITE_GB) -> int:
    if fijo_gb + 2 * pico_gb <= limite_gb:
        return 2
    return 1 if fijo_gb + pico_gb <= limite_gb else 0


def guarda(P: int, pico_gb: float, medir=memoria_maquina, limite_gb: float = LIMITE_GB) -> dict:
    m = medir()
    total = round(m["en_uso_gb"] + P * pico_gb, 3)
    ok = total <= limite_gb
    return {"evento": "guarda de memoria", "P": P, "pico_sesion_gb": pico_gb, "fijo_gb": m["en_uso_gb"], "fijo_mas_P_picos_gb": total,
            "limite_gb": limite_gb, "swap_usado_gb": m["swap_usado_gb"], "P_que_entra": regla_P(m["en_uso_gb"], pico_gb, limite_gb),
            "ok": ok, "motivo": None if ok else (f"lo fijo ({m['en_uso_gb']} GB) más {P} picos de {pico_gb} GB da {total} GB, más de "
                                                  f"{limite_gb}: no lanza (la P no cambia sola)")}
