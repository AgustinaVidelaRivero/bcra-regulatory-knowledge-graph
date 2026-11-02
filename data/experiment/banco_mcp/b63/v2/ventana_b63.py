#!/usr/bin/env python3
"""ventana_b63.py — La ventana corrida del runner de B6.3 (etapa b1; decisión de la autora del 26/10/2026, 21:58:48: «La ventana
corrida: P sesiones a la vez en el orden firmado, y cada reintento en el primer lugar libre.»).

`LoteVentana` es el lote de agentes/lanzar_lote_paralelo_r5.py (importado sin editarlo: R5 de la entrada sellada, la guarda de
guardas_lote_r5) con su `correr`: el de agentes/lanzar_lote_paralelo.py (`Lote.correr`, `:409-489` en HEAD) tal cual, con dos ganchos
que pone el runner y una cosa más:
  · `antes_de_lanzar(lote, s, corriendo)`, antes de lanzar cada sesión y después de la guarda de la versión del CLI: None, sigue;
    ("esperar", motivo), no la lanza todavía y espera a que termine una de las que corren (si no corre ninguna, frena con el 2);
    (código, motivo), frena. Ahí van la guarda del gasto del agente y el juez juntos, y las de memoria, Docker y otro paso pago;
  · `al_terminar(lote, s)`, después de los controles de la sesión que terminó: {"insertar": [sesiones], "frenar": (código, motivo)}.
    Las sesiones que inserta (los reintentos de una falla de infraestructura) van al frente de las pendientes: las lanza en el primer
    lugar libre, antes de seguir con la lista;
  · cada sesión insertada pasa por los mismos controles que las de la lista (`validar`: id admitido y único, también sin distinguir
    mayúsculas, y su carpeta de salida nueva) y lleva su propia tanda (la guarda de otro paso pago del lote corre antes de cada tanda).
Con un R5 que no es uno de los admitidos, `correr` es el del lanzador r5: frena con el 5 sin lanzar ninguna sesión.
La espera es la del proceso padre sobre sus hijos (os.wait): sin sleep ni esperas programadas.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent.parent
for _p in (str(BANCO_DIR), str(BANCO_DIR / "agentes"), str(BANCO_DIR / "paralelo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_lote_paralelo_r5 as LOTE           # noqa: E402  (HEAD: solo import)

BASE = LOTE.BASE
G = LOTE.G
ahora = LOTE.ahora


class LoteVentana(LOTE.Lote):
    def __init__(self, a, antes_de_lanzar=None, al_terminar=None):
        super().__init__(a)
        self.antes_de_lanzar = antes_de_lanzar
        self.al_terminar = al_terminar
        self.insertadas: list[str] = []

    def insertar(self, nuevas: list[dict], pendientes: list[int], preguntas: dict) -> bool:
        """Las sesiones nuevas, al frente de las pendientes, en su orden, con una tanda nueva. False si alguna no pasa los controles
        de `validar` (entonces frena con el 3)."""
        vistos = {s["id"].lower() for s in self.sesiones}
        tanda = max((s["tanda"] for s in self.sesiones), default=0) + 1
        idx = []
        for n in nuevas:
            o = (self.out / n["id"]).resolve()
            if not BASE.ID_VALIDO.match(n["id"]) or n["id"].lower() in vistos or o.exists() or not n.get("brazo") or not n.get("pregunta"):
                self.frenar(BASE.LOTE_INVALIDO, f"un reintento no pasa los controles del lote: {n.get('id')!r}")
                return False
            vistos.add(n["id"].lower())
            self.sesiones.append({"posicion": len(self.sesiones) + 1, "id": n["id"], "brazo": n["brazo"],
                                  "bloque": n.get("bloque") or n["id"], "tanda": tanda, "estado": "pendiente",
                                  "insertada_tras": n.get("tras")})
            preguntas[n["id"]] = n["pregunta"]
            idx.append(len(self.sesiones) - 1)
            self.insertadas.append(n["id"])
        pendientes[:0] = idx
        self.eventos.append({"hora": ahora()[1], "evento": "inserta", "ids": [n["id"] for n in nuevas], "tanda": tanda,
                             "al_frente_de_las_pendientes": True})
        return True

    # El `correr` de BASE (agentes/lanzar_lote_paralelo.py:409-489), con los dos ganchos (marcados «ventana»).
    def correr(self) -> int:
        if not self.r5_admitido:
            return LOTE.Lote.correr(self)
        a, P = self.a, self.a.paralelo
        _, self.inicio = ahora()
        ses = self.validar()
        self.sesiones = [{"posicion": k + 1, "id": s["id"], "brazo": s["brazo"], "bloque": s.get("bloque") or s["id"],
                          "tanda": k // P + 1, "estado": "pendiente"} for k, s in enumerate(ses)]
        preguntas = {s["id"]: s["pregunta"] for s in ses}
        pendientes = list(range(len(ses)))
        corriendo: dict[int, tuple[int, subprocess.Popen]] = {}
        libres = set(range(1, P + 1))
        guardadas, controladas = set(), set()
        self.escribir_registro()
        try:
            self.control_cli("al empezar el lote")
            while True:
                while pendientes and len(corriendo) < P and not self.codigo:
                    k = pendientes[0]
                    s = self.sesiones[k]
                    if not self.control_cli(f"antes de {s['id']}"):
                        break
                    if a.modo == "real" and s["tanda"] not in guardadas:
                        h = G.otro_paso_pago(raiz_lote=os.getpid())
                        self.eventos.append({"hora": ahora()[1], "evento": "guarda de otro paso pago",
                                             "antes_de_la_tanda": s["tanda"], "hallados": h})
                        guardadas.add(s["tanda"])
                        if h:
                            for x in h:
                                print(f"FRENO: otro paso pago corriendo: pid {x['pid']} ({x['script']})", flush=True)
                            self.frenar(BASE.OTRO_PASO_PAGO, f"otro paso pago corriendo antes de la tanda {s['tanda']}: {h}")
                            break
                    if self.antes_de_lanzar is not None:                                   # ventana
                        r = self.antes_de_lanzar(self, s, len(corriendo))
                        if r is not None:
                            self.eventos.append({"hora": ahora()[1], "evento": "gancho antes de lanzar", "antes_de": s["id"],
                                                 "corriendo": len(corriendo), "decision": r[0], "motivo": r[1]})
                            if r[0] == "esperar":
                                if corriendo:
                                    break
                                self.frenar(BASE.FRENO_GASTO, f"{r[1]} (sin ninguna sesión corriendo)")
                                break
                            self.frenar(r[0], r[1])
                            break
                    si = self.acumulado_guarda + self.presupuesto * (len(corriendo) + 1)
                    if si > a.freno or si > a.tope:
                        ev = {"hora": ahora()[1], "evento": "guarda del gasto", "antes_de": s["id"],
                              "acumulado": round(self.acumulado_guarda, 6), "corriendo": len(corriendo),
                              "presupuesto": self.presupuesto, "con_la_nueva": round(si, 6), "freno": a.freno, "tope": a.tope}
                        if corriendo:
                            self.eventos.append(ev | {"decision": "espera a que termine una"})
                            break
                        self.eventos.append(ev | {"decision": "frena"})
                        self.frenar(BASE.FRENO_GASTO, f"acumulado {self.acumulado_guarda:.4f} + {self.presupuesto} > freno {a.freno} "
                                                      f"(tope {a.tope}) antes de {s['id']}")
                        break
                    pendientes.pop(0)
                    w = min(libres)
                    libres.discard(w)
                    p = self.lanzar(s, preguntas[s["id"]], w)
                    corriendo[p.pid] = (k, p)
                    self.eventos.append({"hora": s["inicio"], "evento": "lanza", "id": s["id"], "worker": w,
                                         "acumulado": round(self.acumulado_guarda, 6), "corriendo_con_ella": len(corriendo)})
                    self.escribir_registro()
                if not corriendo:
                    break
                pid, status = os.wait()                  # la espera del padre sobre sus hijos
                if pid not in corriendo:
                    continue
                k, p = corriendo.pop(pid)
                p.returncode = os.waitstatus_to_exitcode(status)
                s = self.sesiones[k]
                self.cerrar_sesion(s, status)
                libres.add(s["worker"])
                self.eventos.append({"hora": s["fin"], "evento": "termina", "id": s["id"], "rc": s["rc_lanzador"],
                                     "costo_R9_usd": s["costo_R9_usd"], "costo_para_la_guarda_usd": s["costo_para_la_guarda_usd"],
                                     "acumulado": round(self.acumulado_guarda, 6)})
                prob = self.control_aislamiento(s)
                if prob:
                    self.frenar(BASE.AISLAMIENTO, "; ".join(prob))
                self.control_cli(f"al terminar {s['id']}", s)
                if self.al_terminar is not None and not self.codigo:                       # ventana
                    r = self.al_terminar(self, s) or {}
                    if r.get("insertar"):
                        self.insertar(r["insertar"], pendientes, preguntas)
                    if r.get("frenar"):
                        self.frenar(*r["frenar"])
                t = s["tanda"]
                if t not in controladas and all(x.get("t_fin") is not None for x in self.sesiones if x["tanda"] == t):
                    controladas.add(t)
                    self.control_cwd(f"después de la tanda {t}")
                    self.control_cli(f"después de la tanda {t}")
                self.escribir_registro()
            for x in self.sesiones:
                if x["estado"] == "pendiente":
                    x["estado"] = "no lanzada"
            self.control_cwd("al final del lote")
        finally:
            _, self.fin = ahora()
            self.escribir_registro()
        return self.codigo
