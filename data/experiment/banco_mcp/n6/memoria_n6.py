#!/usr/bin/env python3
"""memoria_n6.py — N6 de U-NAV-DISENO: la memoria del servidor del grafo con el modelo del denso cargado (decisión de la
autora del 27/10/2026: «El servidor del grafo lanza el codificador de consultas del denso al arrancar, y nadie probó su
arranque con el modelo listo»). USD 0, sin modelo de lenguaje.

Arranca el servidor nuevo (servidor_mcp_kg_nav_cand.py) con la config de T y BANCO_VENV_VECTOR, por stdio
(banco_mcp/cliente_falso.py), le hace una consulta de prueba a buscar_puntos que no sale de ninguna pregunta (CONSULTA), así el
codificador queda cargado, y sigue un rato con el modelo listo (dos consultas más). Desde este mismo proceso, cada 5 s, toma:
  · la memoria del árbol de procesos del servidor: los descendientes de este proceso (el servidor del grafo y su codificador de
    consultas), por `ps -axo pid=,ppid=,rss=`, sin leer líneas de comandos: la residente (RSS) y la huella física
    (`footprint -p`, phys_footprint, que cuenta también lo comprimido; con la máquina paginando, la RSS se queda corta). El
    pico es el de la huella;
  · la memoria de la máquina por `vm_stat` (páginas libres, activas, inactivas, fijas y las del compresor) y el swap por
    `sysctl vm.swapusage`.
La única espera con plazo es la del hilo de muestreo entre muestras (threading.Event.wait con 5 s, que corta al cerrar);
el hilo principal espera la señal de cada muestra nueva, sin plazo. No hay sleep.
Con el pico, propone la P de N6 con la regla de la autora para B6.3: el pico de P sesiones más lo fijo, 14,5 GB como mucho,
y sin que crezca el swap. Lo fijo es la memoria en uso de la máquina antes de arrancar el servidor (la línea de base). La P la
decide la autora. Escribe un JSON con las muestras y la propuesta.
Uso: NEO4J_URI=bolt://127.0.0.1:57687 BANCO_VENV_VECTOR=<venv> python -B n6/memoria_n6.py --salida <json>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
MCP_KG = BANCO_DIR / "mcp_kg"
for _p in (str(BANCO_DIR), str(MCP_KG)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from cliente_falso import ClienteFalso  # noqa: E402

NEO4J_URI_N6 = "bolt://127.0.0.1:57687"
CONFIG_T = AQUI / "config_mcp_kg_n6_T.json"
CONSULTA = "consulta de prueba del codificador"          # no sale de ninguna pregunta
INTERVALO_S = 5.0
MUESTRAS_CON_EL_MODELO_LISTO = 12                         # 60 s con el modelo cargado, después de la primera consulta
LIMITE_GB = 14.5
GB = 1e9


def tabla_rss() -> dict[int, tuple[int, int]]:
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,rss="], capture_output=True, text=True, check=True).stdout
    t = {}
    for linea in out.split("\n"):
        p = linea.split()
        if len(p) == 3 and all(x.isdigit() for x in p):
            t[int(p[0])] = (int(p[1]), int(p[2]) * 1024)
    return t


def arbol(raiz: int, t: dict) -> set[int]:
    hijos: dict[int, list[int]] = {}
    for q, (pp, _) in t.items():
        hijos.setdefault(pp, []).append(q)
    out, pila = set(), [raiz]
    while pila:
        for h in hijos.get(pila.pop(), []):
            if h not in out:
                out.add(h)
                pila.append(h)
    return out


UNIDAD = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


def huella(pids: set[int]) -> int:
    """La suma de la huella física (phys_footprint, que cuenta lo comprimido) de los procesos, por `footprint -p`."""
    total = 0
    for p in sorted(pids):             # uno por proceso: con varios -p, footprint suma además una línea con el total
        out = subprocess.run(["footprint", "-p", str(p)], capture_output=True, text=True).stdout
        m = re.search(r"Footprint: ([\d.]+) (B|KB|MB|GB)", out)
        total += int(float(m.group(1)) * UNIDAD[m.group(2)]) if m else 0
    return total


def desglose(pids: set[int]) -> list[dict]:
    """Por proceso del árbol, las categorías de `footprint -p` con más memoria sucia (sus 6 primeras): solo la categoría y los
    tamaños, sin rutas ni nombres de archivos."""
    out = []
    for p in sorted(pids):
        txt = subprocess.run(["footprint", "-p", str(p)], capture_output=True, text=True).stdout
        tot = re.search(r"Footprint: ([\d.]+) (B|KB|MB|GB)", txt)
        filas = []
        for m in re.finditer(r"^\s*([\d.]+) (B|KB|MB|GB)\s+([\d.]+) (B|KB|MB|GB)\s+([\d.]+) (B|KB|MB|GB)\s+(\d+)\s+(\S.*)$",
                             txt, re.M):
            cat = m.group(8).strip()
            if cat.startswith("/") or "TOTAL" in cat:
                continue
            filas.append({"categoria": cat[:40], "sucia_gb": round(float(m.group(1)) * UNIDAD[m.group(2)] / GB, 3),
                          "limpia_gb": round(float(m.group(3)) * UNIDAD[m.group(4)] / GB, 3)})
        filas.sort(key=lambda f: -f["sucia_gb"])
        out.append({"huella_gb": round(float(tot.group(1)) * UNIDAD[tot.group(2)] / GB, 3) if tot else None,
                    "categorias": filas[:6]})
    return out


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


class Muestreo:
    def __init__(self):
        self.muestras: list[dict] = []
        self.fin = threading.Event()
        self.nueva = threading.Event()             # la señal de cada muestra nueva, para el hilo principal
        self.etapa = "arranque"
        self.desglose = None
        self.yo = os.getpid()

    def tomar(self) -> None:
        t = tabla_rss()
        pids = arbol(self.yo, t)
        rss = sum(t[p][1] for p in pids if p in t)
        hf = huella(pids)
        if self.etapa == "modelo listo" and self.desglose is None:
            self.desglose = desglose(pids)
        self.muestras.append({"t": round(time.time() - self.t0, 1), "etapa": self.etapa, "procesos_del_arbol": len(pids),
                              "rss_arbol_gb": round(rss / GB, 3), "huella_arbol_gb": round(hf / GB, 3),
                              **memoria_maquina()})
        self.nueva.set()

    def correr(self) -> None:
        self.t0 = time.time()
        self.tomar()
        while not self.fin.wait(INTERVALO_S):
            self.tomar()
        self.tomar()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args(argv)
    if os.environ.get("NEO4J_URI") != NEO4J_URI_N6:
        raise SystemExit(f"FRENO: NEO4J_URI no es la del Neo4j propio de N6 ({NEO4J_URI_N6})")
    if not os.environ.get("BANCO_VENV_VECTOR"):
        raise SystemExit("FRENO: falta BANCO_VENV_VECTOR (el codificador de consultas)")
    base = memoria_maquina()
    m = Muestreo()
    hilo = threading.Thread(target=m.correr, daemon=True)
    env = {k: v for k, v in os.environ.items() if k in ("NEO4J_URI", "BANCO_VENV_VECTOR", "PATH", "HOME", "TMPDIR")}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "BANCO_LOG_R1": os.devnull, "BANCO_SESION_TAG": "memoria_n6",
                "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    cmd = [sys.executable, "-B", str(MCP_KG / "servidor_mcp_kg_nav_cand.py"), "--config", str(CONFIG_T)]
    tiempos = {}
    hilo.start()
    t0 = time.time()
    with ClienteFalso(cmd=cmd, env=env, cwd=BANCO_DIR.parents[2]) as cli:
        tiempos["servidor_listo_s"] = round(time.time() - t0, 1)
        m.etapa = "primera consulta (carga del modelo)"
        r1 = cli.llamar("buscar_puntos", {"consulta": CONSULTA, "limite": 3})
        tiempos["primera_consulta_s"] = round(time.time() - t0, 1)
        m.etapa = "modelo listo"
        n0 = len(m.muestras)
        k = 0
        while len(m.muestras) < n0 + MUESTRAS_CON_EL_MODELO_LISTO:
            if k < 2:
                cli.llamar("buscar_puntos", {"consulta": CONSULTA, "limite": 3, "desde": k + 1})
                k += 1
            else:
                m.nueva.wait()                       # espera la muestra siguiente del hilo de muestreo (sin plazo)
                m.nueva.clear()
        primera_ok = r1.startswith("buscar_puntos «") and "fusión RRF" in r1
    m.etapa = "servidor cerrado"
    m.fin.set()
    hilo.join()
    pico = max(m.muestras, key=lambda x: x["huella_arbol_gb"])
    pico_rss = max(x["rss_arbol_gb"] for x in m.muestras)
    swap_max = max(x["swap_usado_gb"] for x in m.muestras)
    fijo = base["en_uso_gb"]
    pico_s = pico["huella_arbol_gb"]
    p_max = int((LIMITE_GB - fijo) // pico_s) if pico_s > 0 and fijo < LIMITE_GB else 0
    out = {"que": "memoria del servidor del grafo de N6 (config T) con el codificador de consultas cargado",
           "config": "n6/config_mcp_kg_n6_T.json", "consulta_de_prueba": CONSULTA, "intervalo_s": INTERVALO_S,
           "primera_consulta_con_la_fusion": primera_ok, "tiempos": tiempos, "linea_de_base": base,
           "muestras": m.muestras, "pico_arbol_del_servidor": pico, "desglose_con_el_modelo_listo": m.desglose,
           "al_cerrar_el_servidor": {"baja_en_uso_gb": round(m.muestras[-2]["en_uso_gb"] - m.muestras[-1]["en_uso_gb"], 3),
                                     "sube_libre_gb": round(m.muestras[-1]["libre_gb"] - m.muestras[-2]["libre_gb"], 3)},
           "swap": {"al_empezar_gb": base["swap_usado_gb"], "maximo_gb": swap_max,
                    "crecio_gb": round(swap_max - base["swap_usado_gb"], 3)},
           "propuesta_P": {"regla": "pico de P sesiones + lo fijo <= 14,5 GB, y sin que crezca el swap (la de la autora para B6.3)",
                           "lo_fijo_gb": fijo, "pico_por_sesion_gb_servidor": pico_s, "pico_rss_gb_servidor": pico_rss,
                           "P_max_con_el_servidor_solo": p_max,
                           "nota": "el pico por sesión es el del árbol del servidor (el servidor y su codificador); el CLI de cada "
                                   "sesión y su Node no se midieron (NO VERIFICADO). Lo fijo es la memoria en uso de la máquina "
                                   "antes de arrancar el servidor, con lo que estaba abierto en ese momento."},
           "hora": datetime.now().astimezone().isoformat(timespec="seconds")}
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("tiempos", "linea_de_base", "pico_arbol_del_servidor", "swap", "propuesta_P",
                                         "primera_consulta_con_la_fusion")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
