"""U-INDICES-EVAL: registro EN MEMORIA de la vista runtime del grafo evaluado de B6.3 (pre-registro firmado en adf20f3b,
H-1), el acumulado de las tandas 0, 1 y final sin la cola humana, con la re-aplicación única, con el patrón de
data/experiment/banco_mcp/mcp_kg/registro_vista_acumulado.py, sin editarlo: agrega la clave a la tabla TANDA0 en
memoria y vuelve a llamar a su registro (idempotente). Lo importa data/experiment/neo4j/grafos.py
(cargar_vista_runtime) por los campos requiere_registro_dir y requiere_registro_modulo de la entrada
KG_Acumulado_Tandas0y1yFinal_r2b_sincola. La vista es la de comun_tanda0.cargar_runtime_gen3; el kg.json no se toca.

El kg.json del grafo evaluado no está en el repo: se restaura del kg.json.gz sellado (kg.json.gz.sello.json, fde70c67),
y su sha256 es el que controla el cargador. r2b no se evalúa con EV2: esta vista sirve a la carga en Neo4j, a su
verificación y a las herramientas de navegación (mcp_kg/familias_nav.py).
"""
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[2]                    # data/experiment
CODE_T0 = EXP / "tanda0" / "code"
if str(CODE_T0) not in sys.path:
    sys.path.insert(0, str(CODE_T0))

import comun_tanda0 as T0   # noqa: E402  (registra la tanda 0 al importarse)

EVALUADO = {
    "acumulado_tandas0y1yfinal_r2b_sincola": {
        "path": EXP / "reaplicacion_unica" / "acumulado" / "ens_128_r2b_sincola" / "r2" / "kg.json",
        "sha256": "576c97256185a0d5741cb2c35a2a85e91412f3e1119ad7a85d960b7d60c35ad3",
        "label": "r2b_acumulado_tandas0y1yfinal_sincola_mem",
    },
}


def registrar_evaluado() -> None:
    T0.TANDA0.update(EVALUADO)
    T0.registrar_tanda0()


registrar_evaluado()
