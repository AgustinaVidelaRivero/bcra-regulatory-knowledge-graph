#!/usr/bin/env python3
"""selftest_gate6.py — selftest del gate 6 de la fase 2 de B6.0 (U-GATE6-INTR-CITA).

Solo biblioteca estándar en este archivo. Invoca los dos scripts extendidos por
subprocess con PYTHONDONTWRITEBYTECODE=1:

  (i)  metricas_intrinsecas.py SIN argumentos (ruta legada) contra la línea de
       base pre-edición de la pieza A, excluyendo `fecha` y `script_sha256`
       (tres casos, uno por grafo). Se ejecuta con .venv/bin/python vía un
       wrapper que redirige OUT_DIR a un directorio temporal (monkeypatch del
       atributo de módulo; el script lo resuelve en tiempo de llamada) y apunta
       KG_V3 a la copia HISTÓRICA de reensamblado_v3/kg.json (commit 7faa03f:
       4.458 nodos / 8.044 aristas, el estado que assemble_v3 reproduce desde el
       caché). Motivo: el kg.json vigente de reensamblado_v3 (4.469 / 8.073 tras
       C1–C7) hace fallar la custodia_v3 y luego la réplica v3 del script sin
       editar, así que la ruta legada no puede completarse sobre el repo actual
       (evidencia: revision_GATE6/baseline_pre_LITERAL_abort.log). Ningún
       control del script se suprime. La línea de base se toma de --baseline;
       sin ese argumento se regenera con la versión pre-edición del script
       (`git show 60bd892:scripts/metricas_intrinsecas.py`) y el mismo wrapper.
  (ii) metricas_intrinsecas.py --gen3 sobre un grafo sintético mínimo de
       generación 3 escrito acá (provenances, rol_documental, rol_fuente
       esqueleto, chunks_emisores), un E0 sintético de dos chunks, un manifiesto
       sintético y un PDF sintético de dos páginas (página 2 con «NORMA DE
       ORIGEN», para que chunk_roles.py clasifique tabla_norma_origen). Verifica
       M4, M8 y M9 a mano (y además M5, M6.grado_max, M7, M10, M1/M2 = 0, M3
       no_computable) y la byte-identidad de dos corridas excluyendo `fecha` y
       `script_sha256`.
  (iii) ucita2_indicadores.py con todos los argumentos de insumos explícitos e
       iguales a los defaults y salidas a un directorio temporal, contra
       reports/ucita2_indicadores.json excluyendo la clave `script`. Se ejecuta
       con `python3` (--python-ucita2): el script original no parsea con el
       Python 3.10 del .venv (f-string con barra invertida en su selftest
       interno) y el reporte sellado se produjo con `python3 -B` (docstring).

Uso (desde la raíz del repo):
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/selftest_gate6.py [--baseline DIR]
      [--python-ucita2 python3] [--solo i,ii,iii]
Salida: una línea PASS/FAIL por caso y el total; código de retorno 1 si hay fallas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
VENV_PY = REPO / ".venv" / "bin" / "python"
SCRIPT_METRICAS = REPO / "scripts" / "metricas_intrinsecas.py"
SCRIPT_UCITA2 = REPO / "scripts" / "ucita2_indicadores.py"
COMMIT_PRE_EDICION = "60bd892"      # último commit anterior a esta unidad
COMMIT_KG_V3_HISTORICO = "7faa03f"  # reensamblado_v3/kg.json = 4.458 / 8.044 (custodia OK)
RUTA_KG_V3 = "data/experiment/grafo_v2/reensamblado_v3/kg.json"
GRAFOS_LEGADOS = ("grafo_v2", "reensamblado_v3", "run_3_ppf_core")
EXCLUIR_METRICAS = ("fecha", "script_sha256")
SELLADO_UCITA2 = REPO / "reports" / "ucita2_indicadores.json"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

WRAPPER_LEGADO = r'''
import sys, types
from pathlib import Path
script, out_dir, kg_v3_hist = (Path(a).resolve() for a in sys.argv[1:4])
fuente = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else script
m = types.ModuleType("metricas_intrinsecas")
m.__file__ = str(script)
sys.argv = [str(script)]
exec(compile(fuente.read_text(encoding="utf-8"), str(script), "exec"), m.__dict__)
_rel_out = m.OUT_DIR.relative_to(m.REPO)
class _PathSalida(type(Path())):
    def relative_to(self, *other):
        return _rel_out / self.name if self.suffix else _rel_out
m.OUT_DIR = _PathSalida(out_dir)
_rel_kg = m.KG_V3.relative_to(m.REPO)
class _PathHistorica(type(Path())):
    def relative_to(self, *other):
        return _rel_kg
m.KG_V3 = _PathHistorica(kg_v3_hist)
sys.exit(m.main())
'''


# --------------------------------------------------------------------------- #
# utilidades                                                                   #
# --------------------------------------------------------------------------- #
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cargar_sin(p: Path, excluir: tuple) -> dict:
    d = json.loads(p.read_text(encoding="utf-8"))
    for k in excluir:
        d.pop(k, None)
    return d


def canon(d) -> str:
    return json.dumps(d, ensure_ascii=False, sort_keys=True, indent=1)


def correr(cmd: list, cwd: Path = REPO, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=ENV, capture_output=True, text=True, timeout=timeout)


def git_show(ref_path: str, destino: Path) -> None:
    r = correr(["git", "show", ref_path])
    if r.returncode != 0:
        raise RuntimeError(f"git show {ref_path} falló: {r.stderr.strip()}")
    destino.write_text(r.stdout, encoding="utf-8")


class Resultados:
    def __init__(self):
        self.casos = []

    def caso(self, nombre: str, ok: bool, detalle: str = "") -> None:
        self.casos.append((nombre, bool(ok), detalle))
        print(f"  [{'PASS' if ok else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""), flush=True)

    @property
    def fallas(self) -> int:
        return sum(1 for _, ok, _ in self.casos if not ok)


# --------------------------------------------------------------------------- #
# (i) ruta legada contra la línea de base pre-edición                           #
# --------------------------------------------------------------------------- #
def correr_legado(tmp: Path, fuente: Path | None, etiqueta: str) -> Path:
    out_dir = tmp / f"legado_{etiqueta}"
    out_dir.mkdir(parents=True, exist_ok=True)
    kg_hist = tmp / "kg_v3_historico_7faa03f.json"
    if not kg_hist.exists():
        git_show(f"{COMMIT_KG_V3_HISTORICO}:{RUTA_KG_V3}", kg_hist)
    wrapper = tmp / "wrapper_legado.py"
    wrapper.write_text(WRAPPER_LEGADO, encoding="utf-8")
    cmd = [str(VENV_PY), str(wrapper), str(SCRIPT_METRICAS), str(out_dir), str(kg_hist)]
    if fuente is not None:
        cmd.append(str(fuente))
    r = correr(cmd)
    (out_dir / "stdout_stderr.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"ruta legada ({etiqueta}) terminó con código {r.returncode}:\n{r.stderr[-2000:]}")
    return out_dir


def caso_i(res: Resultados, tmp: Path, baseline: Path | None) -> None:
    print("(i) ruta legada sin argumentos vs línea de base pre-edición", flush=True)
    if baseline is None:
        fuente_pre = tmp / "metricas_intrinsecas_pre_60bd892.py"
        git_show(f"{COMMIT_PRE_EDICION}:scripts/metricas_intrinsecas.py", fuente_pre)
        print(f"    (sin --baseline: regenerando la línea de base con la fuente {COMMIT_PRE_EDICION}, "
              f"sha256 {sha256_bytes(fuente_pre.read_bytes())[:16]}…)", flush=True)
        baseline = correr_legado(tmp, fuente_pre, "pre")
    post = correr_legado(tmp, None, "post")
    for g in GRAFOS_LEGADOS:
        a, b = baseline / f"{g}.json", post / f"{g}.json"
        if not a.exists() or not b.exists():
            res.caso(f"(i) {g}: JSON pre y post existen", False, f"pre={a.exists()} post={b.exists()}")
            continue
        ca, cb = canon(cargar_sin(a, EXCLUIR_METRICAS)), canon(cargar_sin(b, EXCLUIR_METRICAS))
        res.caso(f"(i) {g}: idéntico pre/post excluyendo fecha y script_sha256", ca == cb,
                 f"sha256 sin exclusiones pre {sha256_bytes(a.read_bytes())[:12]} / post {sha256_bytes(b.read_bytes())[:12]}; "
                 f"canon excl. {sha256_bytes(ca.encode())[:12]} / {sha256_bytes(cb.encode())[:12]}")


# --------------------------------------------------------------------------- #
# (ii) --gen3 sobre un grafo sintético mínimo                                   #
# --------------------------------------------------------------------------- #
def pdf_minimo(paginas_texto: list) -> bytes:
    """PDF de N páginas con texto Helvetica y xref calculado (solo stdlib)."""
    objs = []
    n_pag = len(paginas_texto)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pag))
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pag} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for i, lineas in enumerate(paginas_texto):
        cont_num = 5 + 2 * i
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {cont_num} 0 R >>".encode())
        partes = ["BT /F1 12 Tf 72 720 Td 14 TL"]
        for l in lineas:
            esc = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            partes.append(f"({esc}) Tj T*")
        partes.append("ET")
        stream = "\n".join(partes).encode("latin-1")
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for k, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{k} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def _prov(punto, rol, chunk_id, paginas, ancestros=("S1",), **extra):
    p = {"to": "sin", "archivo": "TO_sintetico_actual.pdf", "punto": punto, "rol_documental": rol,
         "chunk_id": chunk_id, "paginas": list(paginas), "ancestros": list(ancestros)}
    p.update(extra)
    return p


def escribir_sintetico(tmp: Path) -> dict:
    """Grafo sintético de generación 3 + E0 + manifiesto + PDF. Valores a mano:

    Nodos N = 5: A (Obligacion), B (Operacion), C (Sujeto), D (Restriccion), E (Sujeto, esqueleto).
    Aristas: A→B r1 (dos veces: una repetida removida), B→A r2, A→A r3 (self-loop), C→A r4.
      Únicas = 4; repetidas = 1; self-loops = 1.
    M4: grados A=5 (out r1, in r2, self-loop +2, in r4), B=2, C=1, D=0, E=0 → Σ 8 → 8/5 = 1.6.
    M5: componente mayor {A,B,C}: d(A,B)=1, d(A,C)=1, d(B,C)=2 → Σ pares ordenados 8 / 6 = 1.333333.
    M6: grado_max 5; k_top = techo(0.05) = 1 → participación 5/8 = 0.625.
    M8: (4 − 1) / (5·4) = 0.15.
    M9: aislados 2 (D, E); componentes 3 ({A,B,C}, {D}, {E}); fracción 3/5 = 0.6.
    Chunks E0: sin::1.1 (página 1, cuerpo) y sin::1.2 (página 2, «NORMA DE ORIGEN» → tabla_norma_origen).
    M7: nodos cuyo chunk principal es de rol no normativo: C (sin::1.2) → 1/5 = 0.2; E (esqueleto) fuera
        del numerador; A tiene dos provenances del mismo chunk (punto_propio + herencia_encabezado).
    M10: universo = chunks de rol cuerpo = {sin::1.1}; aporta nodos (A, B, D) → 0/1 = 0.0.
    M1/M2: un nodo por tipo salvo Sujeto (C «Banco Central» vs E «Entidad financiera») → 0.
    M3: no_computable (provenances dedup exacto, no menciones)."""
    d = tmp / "gen3_sintetico"
    (d / "e0").mkdir(parents=True, exist_ok=True)
    pdf = d / "TO_sintetico_actual.pdf"
    pdf.write_bytes(pdf_minimo([["Seccion 1. Disposiciones.", "1.1. Primer punto sintetico.", "Texto del cuerpo."],
                                ["NORMA DE ORIGEN", "1.2. Tabla de correspondencias sintetica."]]))
    chunks = [
        {"id": "sin::1.1", "to": "sin", "archivo": "TO_sintetico_actual.pdf", "unidad": "1.1",
         "titulo": "Primer punto sintetico.", "tipo": "punto_terminal", "paginas": [1], "texto": "1.1. …",
         "herencia": [{"tipo": "encabezado", "unidad_origen": "S1", "texto": "Seccion 1.", "paginas": [1]}],
         "flags": {"contenido_tabular": False, "formula": False, "evidencia_tabular": [], "evidencia_formula": []}},
        {"id": "sin::1.2", "to": "sin", "archivo": "TO_sintetico_actual.pdf", "unidad": "1.2",
         "titulo": "Tabla de correspondencias sintetica.", "tipo": "punto_terminal", "paginas": [2], "texto": "1.2. …",
         "herencia": [{"tipo": "encabezado", "unidad_origen": "S1", "texto": "Seccion 1.", "paginas": [1]}],
         "flags": {"contenido_tabular": False, "formula": False, "evidencia_tabular": [], "evidencia_formula": []}},
    ]
    (d / "e0" / "chunks_sin.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    manifiesto = {"version": "1", "nombre": "sintetico_gate6",
                  "tos": [{"id": "sin", "archivo": "TO_sintetico_actual.pdf", "pdf": str(pdf),
                           "sha256_pdf": sha256_bytes(pdf.read_bytes())}],
                  "rutas": {"e0_salida": str(d / "e0")}}
    (d / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=1), encoding="utf-8")
    pA1 = _prov("1.1", "punto_propio", "sin::1.1", [1])
    pA2 = _prov("S1", "herencia_encabezado", "sin::1.1", [1], ancestros=[], chunks_emisores=["sin::1.1"])
    pB = _prov("1.1", "punto_propio", "sin::1.1", [1])
    pC = _prov("1.2", "punto_propio", "sin::1.2", [2])
    pD = _prov("1.1", "punto_propio", "sin::1.1", [1])
    pE = {"to": None, "archivo": None, "punto": None, "rol_documental": "esqueleto", "chunk_id": None,
          "paginas": [], "ancestros": []}
    nodes = [
        {"id": "Obligacion_a", "type": "Obligacion", "label": "Informar mensualmente al BCRA", "properties": {},
         "provenance": pA1, "provenances": [pA1, pA2]},
        {"id": "Operacion_b", "type": "Operacion", "label": "Compra de moneda extranjera", "properties": {},
         "provenance": pB, "provenances": [pB]},
        {"id": "Sujeto_c", "type": "Sujeto", "label": "Banco Central", "properties": {},
         "provenance": pC, "provenances": [pC]},
        {"id": "Restriccion_d", "type": "Restriccion", "label": "Tope del 30 por ciento", "properties": {},
         "provenance": pD, "provenances": [pD]},
        {"id": "Sujeto_e", "type": "Sujeto", "label": "Entidad financiera", "properties": {},
         "provenance": pE, "provenances": [pE], "rol_fuente": "esqueleto"},
    ]
    edges = [
        {"source": "Obligacion_a", "target": "Operacion_b", "relation": "r1", "provenance": pA1, "provenances": [pA1]},
        {"source": "Obligacion_a", "target": "Operacion_b", "relation": "r1", "provenance": pB, "provenances": [pB]},
        {"source": "Operacion_b", "target": "Obligacion_a", "relation": "r2", "provenance": pB, "provenances": [pB]},
        {"source": "Obligacion_a", "target": "Obligacion_a", "relation": "r3", "provenance": pA1, "provenances": [pA1]},
        {"source": "Sujeto_c", "target": "Obligacion_a", "relation": "r4", "provenance": pC, "provenances": [pC]},
    ]
    kg = d / "kg_sintetico.json"
    kg.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"dir": d, "kg": kg, "e0": d / "e0", "manifiesto": d / "manifiesto.json",
            "sha256_kg": sha256_bytes(kg.read_bytes())}


def correr_gen3(s: dict, out_dir: Path, nombre: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(VENV_PY), str(SCRIPT_METRICAS), "--gen3", "--kg", str(s["kg"]), "--nombre", nombre,
           "--e0", str(s["e0"]), "--manifiesto", str(s["manifiesto"]), "--sha256-esperado", s["sha256_kg"],
           "--out-dir", str(out_dir)]
    r = correr(cmd)
    (out_dir / f"{nombre}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"--gen3 sintético terminó con código {r.returncode}:\n{r.stderr[-2000:]}")
    return out_dir / f"{nombre}.json"


def _aprox(a, b, tol=1e-6) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def caso_ii(res: Resultados, tmp: Path) -> None:
    print("(ii) --gen3 sobre el grafo sintético mínimo", flush=True)
    s = escribir_sintetico(tmp)
    j1 = correr_gen3(s, tmp / "gen3_out_1", "sintetico_gate6")
    j2 = correr_gen3(s, tmp / "gen3_out_2", "sintetico_gate6")
    d = json.loads(j1.read_text(encoding="utf-8"))
    m = d["metricas"]
    res.caso("(ii) claves de primer nivel = JSON existentes + adaptador_gen3",
             list(d.keys()) == ["spec", "spec_commit_sellado", "spec_sha256", "script_sha256", "rapidfuzz_version",
                                "umbral_similitud", "fecha", "custodia", "grafo", "kg_path", "nodos_totales",
                                "metricas", "adaptador_gen3"], str(list(d.keys())))
    res.caso("(ii) nodos_totales = 5", d["nodos_totales"] == 5, str(d["nodos_totales"]))
    res.caso("(ii) custodia por sha256 OK", d["custodia"][0]["custodia"] == "OK"
             and d["custodia"][0]["sha256_medido"] == s["sha256_kg"], json.dumps(d["custodia"][0])[:200])
    m4 = m["M4_average_degree"]
    res.caso("(ii) M4 = 1.6 (Σ grados 8 / 5; 4 únicas, 1 repetida, 1 self-loop)",
             _aprox(m4["valor"], 1.6) and m4["numerador"] == 8 and m4["denominador"] == 5
             and m4["notas"]["aristas_unicas"] == 4 and m4["notas"]["aristas_repetidas_removidas"] == 1
             and m4["notas"]["self_loops"] == 1, f"{m4['valor']} = {m4['numerador']}/{m4['denominador']}, notas {m4['notas']}")
    m8 = m["M8_densidad"]
    res.caso("(ii) M8 = 0.15 (3 / 20)", _aprox(m8["valor"], 0.15) and m8["numerador"] == 3 and m8["denominador"] == 20,
             f"{m8['valor']} = {m8['numerador']}/{m8['denominador']}")
    m9 = m["M9_nodos_aislados_y_componentes"]
    res.caso("(ii) M9 = aislados 2, componentes 3, fracción 0.6",
             m9["valor"]["nodos_aislados"] == 2 and m9["valor"]["componentes_conexas"] == 3
             and _aprox(m9["valor"]["fraccion_en_componente_mayor"], 0.6), json.dumps(m9["valor"]))
    m5 = m["M5_avg_shortest_path"]
    res.caso("(ii) M5 = 1.333333 (8 / 6 sobre {A,B,C})", _aprox(m5["valor"], 8 / 6) and m5["numerador"] == 8
             and m5["denominador"] == 6, f"{m5['valor']} = {m5['numerador']}/{m5['denominador']}")
    m6 = m["M6_concentracion_de_grado"]
    res.caso("(ii) M6 grado_max 5, participación top 1 % = 0.625", m6["valor"]["grado_max"] == 5
             and _aprox(m6["valor"]["participacion_top1pct"], 0.625), json.dumps(m6["valor"]))
    res.caso("(ii) M1 = M2 = 0", m["M1_tasa_duplicacion_publicada"]["numerador"] == 0
             and m["M2_tasa_duplicacion_gate"]["numerador"] == 0,
             f"M1 {m['M1_tasa_duplicacion_publicada']['numerador']}, M2 {m['M2_tasa_duplicacion_gate']['numerador']}")
    res.caso("(ii) M3 no_computable", m["M3_tasa_conflacion"].get("status") == "no_computable",
             json.dumps(m["M3_tasa_conflacion"], ensure_ascii=False)[:160])
    m7 = m["M7_tasa_ruido_por_rol"]
    res.caso("(ii) M7 = 0.2 (1 nodo de chunk tabla_norma_origen / 5; esqueleto fuera del numerador)",
             _aprox(m7.get("valor"), 0.2) and m7.get("numerador") == 1 and m7.get("denominador") == 5
             and m7["notas"]["nodos"] == ["Sujeto_c"], json.dumps({k: m7.get(k) for k in ("valor", "numerador", "denominador")}) + f" nodos={m7.get('notas', {}).get('nodos')}")
    m10 = m["M10_chunks_mudos"]
    res.caso("(ii) M10 = 0/1 (universo = chunks de cuerpo = {sin::1.1}; tabla excluida)",
             _aprox(m10.get("valor"), 0.0) and m10.get("numerador") == 0 and m10.get("denominador") == 1,
             json.dumps({k: m10.get(k) for k in ("valor", "numerador", "denominador")}))
    ad = d["adaptador_gen3"]
    res.caso("(ii) adaptador: chunks por rol {cuerpo: 1, tabla_norma_origen: 1}; 0 chunk_ids fuera de E0",
             ad["rol_documental"]["chunks_por_rol"] == {"cuerpo": 1, "tabla_norma_origen": 1}
             and ad["atribucion_nodo_chunk"]["chunk_ids_fuera_de_e0"] == 0,
             json.dumps(ad["rol_documental"]["chunks_por_rol"]) + f"; fuera {ad['atribucion_nodo_chunk']['chunk_ids_fuera_de_e0']}")
    c1, c2 = canon(cargar_sin(j1, EXCLUIR_METRICAS)), canon(cargar_sin(j2, EXCLUIR_METRICAS))
    res.caso("(ii) dos corridas idénticas excluyendo fecha y script_sha256", c1 == c2,
             f"{sha256_bytes(c1.encode())[:12]} / {sha256_bytes(c2.encode())[:12]}")
    res.caso("(ii) dos corridas byte-idénticas (misma fecha y script)", j1.read_bytes() == j2.read_bytes(),
             f"{sha256_bytes(j1.read_bytes())[:12]} / {sha256_bytes(j2.read_bytes())[:12]}")


# --------------------------------------------------------------------------- #
# (iii) ucita2 con argumentos explícitos contra el reporte sellado             #
# --------------------------------------------------------------------------- #
def caso_iii(res: Resultados, tmp: Path, python_ucita2: str) -> None:
    print("(iii) ucita2_indicadores.py con argumentos explícitos = defaults vs reporte sellado", flush=True)
    out = tmp / "ucita2"
    out.mkdir(parents=True, exist_ok=True)
    cmd = [python_ucita2, "-B", str(SCRIPT_UCITA2),
           "--gold", "data/experiment/exploracion/ev2_fidelidad/preguntas_ev2_fidelidad.json",
           "--manifiesto", "data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json",
           "--e0", "data/experiment/reextraccion_v2/e0_chunking/salida_enm01",
           "--trazas", "data/experiment/ev2_r1/trazas",
           "--tandas", "ev2_r1_base", "ev2_r1_enc_r1", "ev2_r1_enc_r2", "ev2_r1_enc_r3",
           "--out-json", str(out / "ucita2_indicadores.json"), "--out-md", str(out / "ucita2_indicadores.md")]
    r = correr(cmd)
    (out / "stdout_stderr.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    res.caso("(iii) corrida termina con código 0", r.returncode == 0, r.stderr[-300:].strip() if r.returncode else "")
    if r.returncode != 0:
        return
    j = out / "ucita2_indicadores.json"
    a, b = canon(cargar_sin(SELLADO_UCITA2, ("script",))), canon(cargar_sin(j, ("script",)))
    res.caso("(iii) JSON idéntico al sellado excluyendo `script`", a == b,
             f"sha256 completo sellado {sha256_bytes(SELLADO_UCITA2.read_bytes())[:12]} / corrida {sha256_bytes(j.read_bytes())[:12]}")
    res.caso("(iii) JSON byte-idéntico al sellado (a9d32d3b…)", SELLADO_UCITA2.read_bytes() == j.read_bytes(),
             sha256_bytes(j.read_bytes()))


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Selftest del gate 6 (intrínsecas gen 3 + indicadores de cita parametrizados).")
    ap.add_argument("--baseline", default=None, help="directorio con la línea de base pre-edición de la pieza A "
                                                     "(grafo_v2.json, reensamblado_v3.json, run_3_ppf_core.json); "
                                                     "sin él se regenera desde git " + COMMIT_PRE_EDICION)
    ap.add_argument("--python-ucita2", default="python3", help="intérprete para ucita2_indicadores.py (default python3)")
    ap.add_argument("--solo", default="i,ii,iii", help="subconjunto de casos, p. ej. ii,iii")
    ap.add_argument("--tmp", default=None, help="directorio temporal a conservar (default: tempfile)")
    args = ap.parse_args()
    if not VENV_PY.exists():
        print(f"ABORTO: no existe {VENV_PY}")
        return 2
    partes = {p.strip() for p in args.solo.split(",")}
    res = Resultados()
    tmp = Path(args.tmp).resolve() if args.tmp else Path(tempfile.mkdtemp(prefix="selftest_gate6_"))
    tmp.mkdir(parents=True, exist_ok=True)
    print(f"SELFTEST GATE6 — repo {REPO} — temporal {tmp}", flush=True)
    try:
        if "i" in partes:
            caso_i(res, tmp, Path(args.baseline).resolve() if args.baseline else None)
        if "ii" in partes:
            caso_ii(res, tmp)
        if "iii" in partes:
            caso_iii(res, tmp, args.python_ucita2)
    except Exception as e:  # noqa: BLE001 — un caso roto es una falla, no un crash silencioso
        res.caso(f"excepción: {type(e).__name__}", False, str(e)[:800])
    print(f"SELFTEST GATE6: {len(res.casos)} casos; fallas = {res.fallas}")
    return 1 if res.fallas else 0


if __name__ == "__main__":
    sys.exit(main())
