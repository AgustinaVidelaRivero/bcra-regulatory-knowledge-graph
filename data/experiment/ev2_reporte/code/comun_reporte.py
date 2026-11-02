"""
comun_reporte.py — Infraestructura común de la unidad U-A0 (reporte consolidado
de EV2 + atribución determinística de fallas). Todo OFFLINE (USD 0): ningún
módulo de esta unidad llama a la API.

Provee rutas a los INSUMOS commiteados (solo lectura), sha256 esperados de
los que otras unidades ya sellaron, y cargadores. Nada de lo que está bajo
`ev2_corrida/`, `ev2_fidelidad_eval/`, `ev2_encadenamiento/`,
`ev2_adjudicacion/`, `ev2_juez/`, `exploracion/` ni del cuarteto de
`evaluacion/` se edita: se importa o se lee.

Nomenclatura canónica (docs/nomenclatura_grafos.md): las claves internas de
los archivos EV2 son `v2` / `v3` / `run_3`; en toda salida legible se agrega
el nombre canónico KG-Reextraído / KG-Refinado / KG-Base.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

UNIDAD_DIR = Path(__file__).resolve().parents[1]         # data/experiment/ev2_reporte
EXPERIMENT_DIR = UNIDAD_DIR.parent                        # data/experiment
REPO_DIR = EXPERIMENT_DIR.parents[1]

CORRIDA_DIR = EXPERIMENT_DIR / "ev2_corrida"
FIDELIDAD_DIR = EXPERIMENT_DIR / "ev2_fidelidad_eval"
ENC_DIR = EXPERIMENT_DIR / "ev2_encadenamiento"
ADJ_DIR = EXPERIMENT_DIR / "ev2_adjudicacion"
JUEZ_DIR = EXPERIMENT_DIR / "ev2_juez"
EVAL_DIR = EXPERIMENT_DIR / "evaluacion"
GOLD_FIDELIDAD = EXPERIMENT_DIR / "exploracion" / "ev2_fidelidad" / "preguntas_ev2_fidelidad.json"

SALIDA_DIR = UNIDAD_DIR / "salida"

# Los módulos de la corrida se importan por sys.path (mismo patrón que
# ev2_corrida/navegabilidad/replay_navegabilidad_ev2.py).
for _p in (str(CORRIDA_DIR / "code"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --------------------------------------------------------------------------- #
# Nomenclatura canónica                                                        #
# --------------------------------------------------------------------------- #
CANONICO = {
    "run_3": {"nombre": "KG-Base", "sha_corto": "12c226e2", "label": "ev2_base_run3"},
    "v3": {"nombre": "KG-Refinado", "sha_corto": "26fac8b4", "label": "ev2_base_v3"},
    "v2": {"nombre": "KG-Reextraído", "sha_corto": "8e2eadee", "label": "ev2_base_v2"},
}
ORDEN_GRAFOS = ["run_3", "v3", "v2"]      # orden de presentación: base, refinado, reextraído
LABEL2GRAFO = {v["label"]: k for k, v in CANONICO.items()}
VEREDICTOS = ["correcto", "parcial", "incorrecto", "requiere_adjudicacion"]


def nombre(grafo: str, con_sha: bool = False) -> str:
    c = CANONICO[grafo]
    return f"{c['nombre']} (`{c['sha_corto']}`)" if con_sha else c["nombre"]


# --------------------------------------------------------------------------- #
# Insumos (solo lectura) y sellos                                              #
# --------------------------------------------------------------------------- #
INSUMOS = {
    # cruce definitivo (64de678)
    "cruce_definitivo": ADJ_DIR / "adjudicacion_SOLO_MESA" / "cruce_definitivo_por_grafo_SOLO_MESA.json",
    "veredictos_definitivos": ADJ_DIR / "adjudicacion" / "veredictos_definitivos_ciego.json",
    "reporte_muestra": ADJ_DIR / "adjudicacion" / "reporte_muestra_simetrica.json",
    "poblacion_adj": ADJ_DIR / "adjudicacion_SOLO_MESA" / "poblacion_adjudicacion_SOLO_MESA.json",
    "tabla_fichas": ADJ_DIR / "adjudicacion_SOLO_MESA" / "tabla_fichas_SOLO_MESA.json",
    # corrida base de fidelidad (b624865)
    "agregados_base": FIDELIDAD_DIR / "out" / "veredictos_agregados_ciego.json",
    "tabla_base": FIDELIDAD_DIR / "desanonimizacion" / "tabla_id_opaco.json",
    "resumen_fidelidad": FIDELIDAD_DIR / "out" / "resumen_corrida.json",
    # encadenamiento §7 (9044a04)
    "finales_enc": ENC_DIR / "reporte" / "veredictos_finales_ciego.json",
    "agregados_enc": ENC_DIR / "juez_out" / "veredictos_agregados_ciego.json",
    "tabla_enc": ENC_DIR / "desanonimizacion_SOLO_MESA" / "tabla_id_opaco_encadenamiento_SOLO_MESA.json",
    "resumen_agente_enc": ENC_DIR / "reporte" / "resumen_agente.json",
    "resumen_juez_enc": ENC_DIR / "juez_out" / "resumen_corrida_juez.json",
    # navegabilidad y censo (5b02d22 / bb89a8e)
    "agregados_nav": CORRIDA_DIR / "navegabilidad" / "agregados_navegabilidad.json",
    "censo_resumen": CORRIDA_DIR / "censo" / "censo_resumen.json",
    "ausencias_diagnostico": CORRIDA_DIR / "censo" / "ausencias_diagnostico.json",
    # corrida del agente (bb89a8e): resúmenes por grafo
    "resumen_agente_v2": CORRIDA_DIR / "trazas" / "ev2_base_v2" / "resumen_ev2_base_v2.json",
    "resumen_agente_v3": CORRIDA_DIR / "trazas" / "ev2_base_v3" / "resumen_ev2_base_v3.json",
    "resumen_agente_run3": CORRIDA_DIR / "trazas" / "ev2_base_run3" / "resumen_ev2_base_run3.json",
    # juez: calibración (1a0ac5c)
    "juez_resumen_b2": JUEZ_DIR / "out" / "resumen_corrida.json",
    "juez_resumen_app": JUEZ_DIR / "out_app" / "resumen_corrida.json",
    "juez_resumen_app_v11": JUEZ_DIR / "out_app_v11" / "resumen_corrida.json",
    "juez_acuerdo_app": JUEZ_DIR / "out_app" / "acuerdo_juez_humana.json",
    "prompt_juez_v1": JUEZ_DIR / "prompt_juez_v1.md",
    # gold sellado (9c44516)
    "gold_fidelidad": GOLD_FIDELIDAD,
}

# sha256 que otras unidades ya sellaron en sus salidas (se re-verifican acá)
SHA_ESPERADOS = {
    "agregados_base": "9f1046c61372db44407d94cf3676d1a93db47f09f7c881e367517f8e01e8828c",
    "tabla_base": "e219b2fb38eabc561f7118005c10408ce305a2ccc623e8d9915d9cda8cab6137",
    "finales_enc": "0c82e47aff46c48dabeba3fe0dab163a93c2f842e9c908a1ca1af816e394b81c",
    "agregados_enc": "e7c8b5e139bd5242187043d9a32322c94a4a8ec1fe48194621e86538ca6ba823",
    "tabla_enc": "629c4fb882ee8492a0e4c75bf1bdbb0feee4a9a9b3937ca0fc3fc447a31667b5",
    "gold_fidelidad": "1d58733699c325c90510e1ead5f18eac6c3cd970ee3b0ab7ff141da539162b40",
    "prompt_juez_v1": "fd446f8e61f46033d7de9b862121c698b2c52dcc2696b7f10993f44e509f5455",
}

CUARTETO = {
    "loader.py": "5aba8b7a0aa46e8d5c4c83b33884b8cae7d0a099884a7d3bc935de4d3097af8b",
    "harness.py": "fd267e833866f86850e43130e627b08d78e05523b97484696de0ab0c8c9fba9e",
    "judge.py": "7169145aaeb3f2d90a7e3873964378aa6520c5688fed136cf5a79ea63b589eaa",
    "llm_cache.py": "fc86b0e48df464d01d87aa1d8067168d2d522f66ead53f594092a16484c22752",
}


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_repo(p: Path) -> str:
    return str(Path(p).resolve().relative_to(REPO_DIR))


def cargar(clave: str):
    return json.loads(INSUMOS[clave].read_text(encoding="utf-8"))


def verificar_sellos(verbose: bool = True) -> dict:
    """Verifica los sha256 conocidos de insumos y del cuarteto; aborta si alguno
    no coincide. Devuelve {ruta_relativa: sha256} de TODOS los insumos."""
    out = {}
    for k, p in INSUMOS.items():
        got = sha256_path(p)
        out[rel_repo(p)] = got
        esp = SHA_ESPERADOS.get(k)
        if esp and got != esp:
            raise RuntimeError(f"SHA256 INESPERADO en {p}: {got} != {esp}. FRENAR.")
    for f, esp in CUARTETO.items():
        got = sha256_path(EVAL_DIR / f)
        out[rel_repo(EVAL_DIR / f)] = got
        if got != esp:
            raise RuntimeError(f"CUARTETO ALTERADO: {f} {got} != {esp}. FRENAR.")
    if verbose:
        print(f"sellos verificados: {len(SHA_ESPERADOS)} insumos con sha esperado + cuarteto 4/4")
    return out


def escribir_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
                    encoding="utf-8")
