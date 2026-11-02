"""U-NAV-DISENO, N5 (mandato firmado en c2ddf5f7, §4, N5): registro EN MEMORIA de la vista runtime del acumulado de
las tandas 0 y 1 sin la cola humana, el grafo de N6 (decisión 5), con el patrón de
data/experiment/tanda1/t3/registro_vista_r2b_tanda1.py y de data/experiment/tanda0/code/comun_tanda0.py, sin editarlos:
agrega la clave a la tabla TANDA0 en memoria y vuelve a llamar a su registro (idempotente). Lo importa
data/experiment/neo4j/grafos.py (cargar_vista_runtime) por los campos requiere_registro_dir y requiere_registro_modulo de
la entrada KG_Acumulado_Tandas0y1_r2b_sincola. La vista es la de comun_tanda0.cargar_runtime_gen3; el kg.json no se toca.

El kg.json del acumulado no está en el repo: se restaura del kg.json.gz sellado (kg.json.gz.sello.json, e2615b36), y su
sha256 es el que controla el cargador. r2b no se evalúa con EV2: esta vista sirve a la carga en Neo4j, a su
verificación y a las herramientas de navegación (mcp_kg/familias_nav.py).
"""
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[2]                    # data/experiment
CODE_T0 = EXP / "tanda0" / "code"
if str(CODE_T0) not in sys.path:
    sys.path.insert(0, str(CODE_T0))

import comun_tanda0 as T0   # noqa: E402  (registra la tanda 0 al importarse)

ACUMULADO = {
    "acumulado_tandas0y1_r2b_sincola": {
        "path": EXP / "tanda1" / "t3" / "acumulado" / "ens_treinta_r2b_sincola" / "r2" / "kg.json",
        "sha256": "0435d41f9c7b45ea10cc87e8121fcfb8b3d2b089af837fff377a3460ced9636c",
        "label": "r2b_acumulado_tandas0y1_sincola_mem",
    },
}


def registrar_acumulado() -> None:
    T0.TANDA0.update(ACUMULADO)
    T0.registrar_tanda0()


registrar_acumulado()
