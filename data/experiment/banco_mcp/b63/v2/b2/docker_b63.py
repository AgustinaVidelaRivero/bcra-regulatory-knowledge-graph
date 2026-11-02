#!/usr/bin/env python3
"""docker_b63.py — El control de Docker de B6.3 (etapa b1; decisión de la autora del 27/10/2026, 11:31:49: «La VM de Docker topeada
en 2,5 GB para N6 y para B6.3, como estaba previsto. Incluí en los comandos cuándo se topea y cómo se controla.»).

Antes de lanzar y antes de cada bloque, sin listar nada de Docker (solo lo de su VM y de ese contenedor):
  · la memoria de la VM: `docker info --format '{{.MemTotal}}'`, hasta 2.684.354.560 bytes (2,5 GiB);
  · la salud del contenedor del Neo4j de B6.3: `docker inspect -f '{{.State.Health.Status}}' neo4j-bcra-kg-indices-eval`, que tiene que
    dar `healthy`;
  · la memoria de ese contenedor: `docker stats --no-stream --format '{{.MemUsage}}' neo4j-bcra-kg-indices-eval`, que se registra.
Con la VM por encima del tope o el contenedor que no está sano, frena (código 14 del runner) sin lanzar. Con la memoria de la máquina
(memoria_b63) el registro suma la memoria en uso y el swap. `docker` es el del PATH: el selftest pone uno falso.
"""
from __future__ import annotations

import subprocess

TOPE_VM_BYTES = 2_684_354_560
CONTENEDOR = "neo4j-bcra-kg-indices-eval"


def _docker(*args: str) -> tuple[int, str]:
    r = subprocess.run(["docker", *args], capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip()


def control(medir_maquina=None) -> dict:
    rc_vm, vm = _docker("info", "--format", "{{.MemTotal}}")
    rc_h, salud = _docker("inspect", "-f", "{{.State.Health.Status}}", CONTENEDOR)
    rc_s, uso = _docker("stats", "--no-stream", "--format", "{{.MemUsage}}", CONTENEDOR)
    vm_bytes = int(vm) if rc_vm == 0 and vm.isdigit() else None
    out = {"evento": "control de Docker", "vm_mem_total_bytes": vm_bytes, "tope_vm_bytes": TOPE_VM_BYTES,
           "contenedor": CONTENEDOR, "salud": salud if rc_h == 0 else None, "memoria_del_contenedor": uso if rc_s == 0 else None}
    if medir_maquina is not None:
        m = medir_maquina()
        out |= {"maquina_en_uso_gb": m["en_uso_gb"], "maquina_swap_usado_gb": m["swap_usado_gb"]}
    problemas = []
    if vm_bytes is None:
        problemas.append("no se pudo leer la memoria de la VM de Docker")
    elif vm_bytes > TOPE_VM_BYTES:
        problemas.append(f"la VM de Docker tiene {vm_bytes} bytes, más que el tope de {TOPE_VM_BYTES} (2,5 GiB)")
    if out["salud"] != "healthy":
        problemas.append(f"el contenedor {CONTENEDOR} no está sano ({out['salud']!r})")
    out["ok"] = not problemas
    out["motivo"] = "; ".join(problemas) or None
    return out
