"""
grafos.py — Registro de los grafos que el backend Neo4j carga y sirve (U-A1.1).

Nomenclatura canónica: docs/nomenclatura_grafos.md. Cada entrada fija el path
sellado, el sha256 esperado (verificado ANTES de cualquier carga), los conteos
sellados, el label Neo4j que separa el grafo dentro de la única db de
Community (:KG_Refinado / :KG_Reextraido), el nombre de su índice full-text y
la vista RUNTIME con la que el harness lo ve.

Vista runtime (decisión): se reutiliza `cargar_runtime` de
data/experiment/ev2_corrida/code/comun_ev2.py (solo IMPORT), porque es la
vista exacta que vio el agente en EV2 — el mapa causal de U-A0 (clases
alcanzabilidad / vista_no_consultada) se midió sobre esas vistas:
  - KG-Refinado  -> loader.load_graph_from_path(path, adapter_key=None)
                    (idéntico a lo que ya hacía cargar_kg.py en c26cb9b).
  - KG-Reextraído-> provenance PRIMARIA {to, archivo, punto} mapeada en memoria
                    a {source_doc, location} con las dataclasses y el merge del
                    loader congelado (sin ese mapeo el adaptador nulo dejaría
                    al grafo sin provenances y el agente no podría citar).
El kg.json no se toca en ningún caso.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

NEO4J_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = NEO4J_DIR.parent
REPO_DIR = EXPERIMENT_DIR.parents[1]
EVAL_DIR = EXPERIMENT_DIR / "evaluacion"
EV2_CODE_DIR = EXPERIMENT_DIR / "ev2_corrida" / "code"
for _p in (str(EVAL_DIR), str(EV2_CODE_DIR), str(NEO4J_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

GRAFOS = {
    "KG_Refinado": {
        "nombre_canonico": "KG-Refinado",
        "label": "KG_Refinado",
        "path": EXPERIMENT_DIR / "grafo_v2" / "reensamblado_v3" / "kg.json",
        "sha256": "26fac8b49f6c08c1aa364b47273d36958d831f240d4e6b4ee7700b6a0bff3571",
        "commit_sellado": "05984e1",
        "n_nodos": 4469,
        "n_aristas": 8073,
        "ev2_key": "v3",
        "vista_runtime": "comun_ev2.cargar_runtime('v3') = loader.load_graph_from_path(path, adapter_key=None)",
        "indice_fulltext": "nodos_fulltext_kg_refinado",
    },
    "KG_Reextraido": {
        "nombre_canonico": "KG-Reextraído",
        "label": "KG_Reextraido",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_v2" / "salida" / "kg.json",
        "sha256": "8e2eadee57b48e00ccb51ade9a953ba1469001fe089c45d97c4307ccf2725581",
        "commit_sellado": "5273c0c",
        "n_nodos": 6178,
        "n_aristas": 11415,
        "ev2_key": "v2",
        "vista_runtime": "comun_ev2.cargar_runtime('v2') (provenance primaria mapeada a {source_doc, location}; dataclasses + merge del loader congelado)",
        "indice_fulltext": "nodos_fulltext_kg_reextraido",
    },
    "KG_Reextraido_r1": {
        "nombre_canonico": "KG-Reextraído-r1",
        "label": "KG_Reextraido_r1",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_v2" / "salida_r1" / "kg.json",
        "sha256": "0226e9477baee02d772bbfecee78a49441b189d0e0512ca5e22956dfb084196a",
        "commit_sellado": "185e042",
        "commit_medicion_ev2": "774acac",
        "laudo_promocion": "docs/laudo_promocion_r1_vigente.md",
        "n_nodos": 6529,
        "n_aristas": 17772,
        "ev2_key": "r1",
        # r1 no está en el dict GRAFOS de comun_ev2 (módulo sellado): su vista
        # runtime se sirve por el registro en memoria de ev2_r1/code/comun_r1
        # (reemplaza el despachador al importarse, sin editar módulos sellados;
        # misma vista que vio el agente en la medición 774acac).
        "requiere_registro_dir": EXPERIMENT_DIR / "ev2_r1" / "code",
        "vista_runtime": "comun_ev2.cargar_runtime('r1') tras importar comun_r1 (registro en memoria, U-B1.8)",
        "indice_fulltext": "nodos_fulltext_kg_reextraido_r1",
    },
    # Tanda 0 (B6.0 fase 2a, U-TANDA0-2A E3.c): grafos r1 re-ensamblados con el
    # esquema congelado y perfil v3_b54. Su vista runtime la registra en memoria
    # data/experiment/tanda0/code/comun_tanda0.py, que cargar_vista_runtime importa
    # por el campo requiere_registro_modulo (opción B, autorizada por la autora el
    # 28/09/2026).
    "KG_Tanda0_Desarrollo_r1": {
        "nombre_canonico": "KG-Tanda0-Desarrollo-r1",
        "label": "KG_Tanda0_Desarrollo_r1",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_desarrollo" / "r1" / "kg.json",
        "sha256": "eab2fdd01dec4dad026d596a793919e666920fab127d7efb14b5b00857ae64ef",
        "commit_sellado": "1b8916c",
        "n_nodos": 6378,
        "n_aristas": 15007,
        "ev2_key": "tanda0_ens_desarrollo",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda0" / "code",
        "requiere_registro_modulo": "comun_tanda0",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_desarrollo') tras importar tanda0/code/comun_tanda0 (registro en memoria, patrón comun_r1)",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_desarrollo_r1",
    },
    "KG_Tanda0_Diez_r1": {
        "nombre_canonico": "KG-Tanda0-Diez-r1",
        "label": "KG_Tanda0_Diez_r1",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_diez" / "r1" / "kg.json",
        "sha256": "dd42d6d9c0c8379da90ec4ed4e4659157a960a0d1ceaf8af5a008bdd9cad9010",
        "commit_sellado": "1b8916c",
        "n_nodos": 8256,
        "n_aristas": 18932,
        "ev2_key": "tanda0_ens_diez",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda0" / "code",
        "requiere_registro_modulo": "comun_tanda0",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_diez') tras importar tanda0/code/comun_tanda0 (registro en memoria, patrón comun_r1)",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_diez_r1",
    },
    # Tanda 0, perfil r2b (U-REEXT-T0; T3, punto 4, reemplazadas en T3-bis, punto 5): ensamblados r2b de la
    # re-extracción de la tanda 0, re-ensamblados en T3-bis. Su vista runtime la registra en memoria
    # data/experiment/reext_t0/t3bis/registro_vista_r2b.py (patrón comun_tanda0, sin editarlo).
    # commit_sellado: "PENDIENTE" hasta que la autora selle los grafos (no None: Neo4j no guarda propiedades nulas y
    # cargar_kg.verificar_carga lee la clave de KG_Meta).
    "KG_Tanda0_Desarrollo_r2b": {
        "nombre_canonico": "KG-Tanda0-Desarrollo-r2b",
        "label": "KG_Tanda0_Desarrollo_r2b",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_desarrollo_r2b" / "r2" / "kg.json",
        "sha256": "6e7560433148cfe0c476cdd61199c32278187c4196d6f90dc0a38976a6d8e9a2",
        "commit_sellado": "bbc38dc",
        "n_nodos": 6990,
        "n_aristas": 23445,
        "ev2_key": "tanda0_ens_desarrollo_r2b",
        "requiere_registro_dir": EXPERIMENT_DIR / "reext_t0" / "t3bis",
        "requiere_registro_modulo": "registro_vista_r2b",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_desarrollo_r2b') tras importar reext_t0/t3bis/registro_vista_r2b (registro en memoria, patrón comun_tanda0); r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_desarrollo_r2b",
    },
    "KG_Tanda0_Diez_r2b": {
        "nombre_canonico": "KG-Tanda0-Diez-r2b",
        "label": "KG_Tanda0_Diez_r2b",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_diez_r2b" / "r2" / "kg.json",
        "sha256": "a9631a64b422bdae634fb05135373c6f04c6272cdf7acd43a1be9f5b6c1f5f57",
        "commit_sellado": "bbc38dc",
        "n_nodos": 8816,
        "n_aristas": 27632,
        "ev2_key": "tanda0_ens_diez_r2b",
        "requiere_registro_dir": EXPERIMENT_DIR / "reext_t0" / "t3bis",
        "requiere_registro_modulo": "registro_vista_r2b",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_diez_r2b') tras importar reext_t0/t3bis/registro_vista_r2b (registro en memoria, patrón comun_tanda0); r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_diez_r2b",
    },
    # Tanda 0, grafo evaluado sin la cola humana (U-SINCOLA-T0, SC2, punto 2; ensamblados en SC1-bis, 01046b6): los
    # r2b re-ensamblados sin las 74 unidades de la cola humana (59 en desarrollo) con ensamblar_tanda0.py --sin-cola
    # (enmienda 1, 1f7c159). Su vista runtime la registra en memoria data/experiment/sincola_t0/
    # registro_vista_r2b_sincola.py (patrón de reext_t0/t3bis/registro_vista_r2b.py), que declara además el desglose de
    # las citas irresolubles por «punto sin nodos». commit_sellado: "PENDIENTE" hasta que la autora selle los grafos en
    # su commit siguiente (como en c9540c0).
    "KG_Tanda0_Desarrollo_r2b_sincola": {
        "nombre_canonico": "KG-Tanda0-Desarrollo-r2b-sincola",
        "label": "KG_Tanda0_Desarrollo_r2b_sincola",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_desarrollo_r2b_sincola" / "r2" / "kg.json",
        "sha256": "2922b72dca2c2bcb204a04f53fc89f265ac2c57e83e6aaab2ce1af8b82d413e4",
        "commit_sellado": "dde9f44",
        "n_nodos": 6723,
        "n_aristas": 22084,
        "ev2_key": "tanda0_ens_desarrollo_r2b_sincola",
        "requiere_registro_dir": EXPERIMENT_DIR / "sincola_t0",
        "requiere_registro_modulo": "registro_vista_r2b_sincola",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_desarrollo_r2b_sincola') tras importar sincola_t0/registro_vista_r2b_sincola (registro en memoria, patrón comun_tanda0); grafo evaluado de la tanda 0 sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_desarrollo_r2b_sincola",
    },
    "KG_Tanda0_Diez_r2b_sincola": {
        "nombre_canonico": "KG-Tanda0-Diez-r2b-sincola",
        "label": "KG_Tanda0_Diez_r2b_sincola",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_diez_r2b_sincola" / "r2" / "kg.json",
        "sha256": "e22fae1afc3cf37fbe5b49ee0b220d51d0ec5febc13abeb6ebf7b74226da34fb",
        "commit_sellado": "dde9f44",
        "n_nodos": 8503,
        "n_aristas": 26129,
        "ev2_key": "tanda0_ens_diez_r2b_sincola",
        "requiere_registro_dir": EXPERIMENT_DIR / "sincola_t0",
        "requiere_registro_modulo": "registro_vista_r2b_sincola",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_diez_r2b_sincola') tras importar sincola_t0/registro_vista_r2b_sincola (registro en memoria, patrón comun_tanda0); grafo evaluado de la tanda 0 sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_diez_r2b_sincola",
    },
    # Tanda 0, re-sellado único de los cuatro r2b (mandato firmado el 15/10/2026, 67fe5b14; decisión 1 de su §8: los
    # nombres de U-SINCOLA-T0 con el sufijo _rs1): las versiones posteriores de los cuatro grafos de arriba, que
    # siguen sellados, ensambladas con el código de U-OMISIONES-COD (ded41d50) sobre las salidas de E1 y E3 de la
    # tanda 0 tal como las deja R0 (1d690df3 y 2d0f5277). Su vista runtime la registra en memoria
    # data/experiment/resellado_t0/registro_vista_r2b_rs1.py (patrón de sincola_t0/registro_vista_r2b_sincola.py).
    # commit_sellado: "PENDIENTE" hasta el segundo commit del sello de la autora (como en c9540c0 y 235a295).
    "KG_Tanda0_Desarrollo_r2b_rs1": {
        "nombre_canonico": "KG-Tanda0-Desarrollo-r2b-rs1",
        "label": "KG_Tanda0_Desarrollo_r2b_rs1",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_desarrollo_r2b_rs1" / "r2" / "kg.json",
        "sha256": "acb26dca0885e9ea83ab02637f15c1dac57885f0cf017c5fb16173ac7dfcac31",
        "commit_sellado": "4fe6ece",
        "n_nodos": 6962,
        "n_aristas": 23311,
        "ev2_key": "tanda0_ens_desarrollo_r2b_rs1",
        "requiere_registro_dir": EXPERIMENT_DIR / "resellado_t0",
        "requiere_registro_modulo": "registro_vista_r2b_rs1",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_desarrollo_r2b_rs1') tras importar resellado_t0/registro_vista_r2b_rs1 (registro en memoria, patrón comun_tanda0); re-sellado único de la tanda 0; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_desarrollo_r2b_rs1",
    },
    "KG_Tanda0_Diez_r2b_rs1": {
        "nombre_canonico": "KG-Tanda0-Diez-r2b-rs1",
        "label": "KG_Tanda0_Diez_r2b_rs1",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_diez_r2b_rs1" / "r2" / "kg.json",
        "sha256": "fda6c07dbb95602f5992f7e1ad9bf148ff1c2a72b9f69ff2ebbce891c15740ea",
        "commit_sellado": "4fe6ece",
        "n_nodos": 8788,
        "n_aristas": 27430,
        "ev2_key": "tanda0_ens_diez_r2b_rs1",
        "requiere_registro_dir": EXPERIMENT_DIR / "resellado_t0",
        "requiere_registro_modulo": "registro_vista_r2b_rs1",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_diez_r2b_rs1') tras importar resellado_t0/registro_vista_r2b_rs1 (registro en memoria, patrón comun_tanda0); re-sellado único de la tanda 0; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_diez_r2b_rs1",
    },
    "KG_Tanda0_Desarrollo_r2b_sincola_rs1": {
        "nombre_canonico": "KG-Tanda0-Desarrollo-r2b-sincola-rs1",
        "label": "KG_Tanda0_Desarrollo_r2b_sincola_rs1",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_desarrollo_r2b_sincola_rs1" / "r2" / "kg.json",
        "sha256": "66e745f57397ab754cde09eb641e9f0d9ef6259ea7e6445d086ecbf1c36dcc6c",
        "commit_sellado": "4fe6ece",
        "n_nodos": 6711,
        "n_aristas": 21996,
        "ev2_key": "tanda0_ens_desarrollo_r2b_sincola_rs1",
        "requiere_registro_dir": EXPERIMENT_DIR / "resellado_t0",
        "requiere_registro_modulo": "registro_vista_r2b_rs1",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_desarrollo_r2b_sincola_rs1') tras importar resellado_t0/registro_vista_r2b_rs1 (registro en memoria, patrón comun_tanda0); re-sellado único de la tanda 0; grafo evaluado de la tanda 0 sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_desarrollo_r2b_sincola_rs1",
    },
    "KG_Tanda0_Diez_r2b_sincola_rs1": {
        "nombre_canonico": "KG-Tanda0-Diez-r2b-sincola-rs1",
        "label": "KG_Tanda0_Diez_r2b_sincola_rs1",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda0" / "ens_diez_r2b_sincola_rs1" / "r2" / "kg.json",
        "sha256": "61dd1b69ba03e40499845c40a6a8bec4c22d892ebe95823c7d5a569110f08738",
        "commit_sellado": "4fe6ece",
        "n_nodos": 8491,
        "n_aristas": 25976,
        "ev2_key": "tanda0_ens_diez_r2b_sincola_rs1",
        "requiere_registro_dir": EXPERIMENT_DIR / "resellado_t0",
        "requiere_registro_modulo": "registro_vista_r2b_rs1",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda0_ens_diez_r2b_sincola_rs1') tras importar resellado_t0/registro_vista_r2b_rs1 (registro en memoria, patrón comun_tanda0); re-sellado único de la tanda 0; grafo evaluado de la tanda 0 sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda0_diez_r2b_sincola_rs1",
    },
    # Tanda 1 de B6.1 (pre-registro firmado en 95b18217, §5.1; T3): los dos grafos de la tanda sola, completo y sin la
    # cola humana, ensamblados con ensamblar_tanda0.py (cadena r2, --e0-r2) sobre las salidas de E1 y E3 de la tanda 1.
    # Su vista runtime la registra en memoria data/experiment/tanda1/t3/registro_vista_r2b_tanda1.py (patrón de
    # resellado_t0/registro_vista_r2b_rs1.py). commit_sellado: "PENDIENTE" hasta el sello de la autora.
    "KG_Tanda1_Veinte_r2b": {
        "nombre_canonico": "KG-Tanda1-Veinte-r2b",
        "label": "KG_Tanda1_Veinte_r2b",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda1" / "ens_veinte_r2b" / "r2" / "kg.json",
        "sha256": "22e83a62cb88e5bbe31b64a0f2322194bc2ffd2622ea7adc2c07310d8a02c7c7",
        "commit_sellado": "eb0711a",
        "n_nodos": 12731,
        "n_aristas": 31478,
        "ev2_key": "tanda1_ens_veinte_r2b",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda1" / "t3",
        "requiere_registro_modulo": "registro_vista_r2b_tanda1",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda1_ens_veinte_r2b') tras importar tanda1/t3/registro_vista_r2b_tanda1 (registro en memoria, patrón comun_tanda0); tanda 1 de B6.1; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda1_veinte_r2b",
    },
    "KG_Tanda1_Veinte_r2b_sincola": {
        "nombre_canonico": "KG-Tanda1-Veinte-r2b-sincola",
        "label": "KG_Tanda1_Veinte_r2b_sincola",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda1" / "ens_veinte_r2b_sincola" / "r2" / "kg.json",
        "sha256": "384a6d5bc139cd7b74d86840c68e7034b7a9bcb4bc26da7c61567f3f053e624e",
        "commit_sellado": "eb0711a",
        "n_nodos": 12452,
        "n_aristas": 28320,
        "ev2_key": "tanda1_ens_veinte_r2b_sincola",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda1" / "t3",
        "requiere_registro_modulo": "registro_vista_r2b_tanda1",
        "vista_runtime": "comun_ev2.cargar_runtime('tanda1_ens_veinte_r2b_sincola') tras importar tanda1/t3/registro_vista_r2b_tanda1 (registro en memoria, patrón comun_tanda0); tanda 1 de B6.1; grafo evaluado de la tanda 1 sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tanda1_veinte_r2b_sincola",
    },
    # Tanda final de B6.1 (pre-registro firmado en 4de7f2a7, §7; T3): los dos grafos de la tanda sola, completo y sin la
    # cola humana, ensamblados con ensamblar_tanda0.py (cadena r2, --e0-r2) sobre las salidas de E1 y E3 de la tanda final.
    # Su vista runtime la registra en memoria data/experiment/tanda_final/t3/registro_vista_r2b_tanda_final.py (patrón de
    # tanda1/t3/registro_vista_r2b_tanda1.py). commit_sellado: "PENDIENTE" hasta el sello de la autora.
    "KG_TandaFinal_r2b": {
        "nombre_canonico": "KG-TandaFinal-r2b",
        "label": "KG_TandaFinal_r2b",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda_final" / "ens_98_r2b" / "r2" / "kg.json",
        "sha256": "db2df7b7e707ef191d1df6fdb3638fd920cf4486afce13a7e889b9755155bc97",
        "commit_sellado": "71cb930",
        "n_nodos": 17025,
        "n_aristas": 46273,
        "ev2_key": "tandafinal_ens_98_r2b",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda_final" / "t3",
        "requiere_registro_modulo": "registro_vista_r2b_tanda_final",
        "vista_runtime": "comun_ev2.cargar_runtime('tandafinal_ens_98_r2b') tras importar tanda_final/t3/registro_vista_r2b_tanda_final (registro en memoria, patrón comun_tanda0); tanda final de B6.1; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tandafinal_r2b",
    },
    "KG_TandaFinal_r2b_sincola": {
        "nombre_canonico": "KG-TandaFinal-r2b-sincola",
        "label": "KG_TandaFinal_r2b_sincola",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda_final" / "ens_98_r2b_sincola" / "r2" / "kg.json",
        "sha256": "c050f3c90ce5d32be759d2e5d05bbe2e131d9abf7811de097c97f4a1fe410cf7",
        "commit_sellado": "71cb930",
        "n_nodos": 16598,
        "n_aristas": 43392,
        "ev2_key": "tandafinal_ens_98_r2b_sincola",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda_final" / "t3",
        "requiere_registro_modulo": "registro_vista_r2b_tanda_final",
        "vista_runtime": "comun_ev2.cargar_runtime('tandafinal_ens_98_r2b_sincola') tras importar tanda_final/t3/registro_vista_r2b_tanda_final (registro en memoria, patrón comun_tanda0); tanda final de B6.1; grafo de la tanda final sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tandafinal_r2b_sincola",
    },
    # El tramo 1 de la tanda final de B6.1, sellado como respaldo (enmienda 9 al protocolo entre tandas, §1, punto 1; T5): sus
    # dos grafos, completo y sin la cola humana, ensamblados en T3 con ensamblar_tanda0.py (cadena r2, --e0-r2) y los manifiestos
    # de la raya. Su vista runtime la registra en memoria data/experiment/tanda_final/t5/registro_vista_r2b_tramo1.py (patrón de
    # tanda_final/t3/registro_vista_r2b_tanda_final.py). commit_sellado: "PENDIENTE" hasta el commit siguiente al sello.
    "KG_TandaFinal_Tramo1_r2b": {
        "nombre_canonico": "KG-TandaFinal-Tramo1-r2b",
        "label": "KG_TandaFinal_Tramo1_r2b",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda_final" / "ens_tramo1_r2b" / "r2" / "kg.json",
        "sha256": "f064d4e00b41246525d3c30a88f33b3ba9672c5e02cc10a36a4fa18dc88b940c",
        "commit_sellado": "aeaf0ec",
        "n_nodos": 2372,
        "n_aristas": 4066,
        "ev2_key": "tandafinal_ens_tramo1_r2b",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda_final" / "t5",
        "requiere_registro_modulo": "registro_vista_r2b_tramo1",
        "vista_runtime": "comun_ev2.cargar_runtime('tandafinal_ens_tramo1_r2b') tras importar tanda_final/t5/registro_vista_r2b_tramo1 (registro en memoria, patrón comun_tanda0); tramo 1 de la tanda final de B6.1, sellado como respaldo (enmienda 9); r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tandafinal_tramo1_r2b",
    },
    "KG_TandaFinal_Tramo1_r2b_sincola": {
        "nombre_canonico": "KG-TandaFinal-Tramo1-r2b-sincola",
        "label": "KG_TandaFinal_Tramo1_r2b_sincola",
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_tanda_final" / "ens_tramo1_r2b_sincola" / "r2" / "kg.json",
        "sha256": "bbda74cda7e071e27782b41b06d7557e2c153e8afff7ea3f6540bdd520c3615f",
        "commit_sellado": "aeaf0ec",
        "n_nodos": 2207,
        "n_aristas": 3822,
        "ev2_key": "tandafinal_ens_tramo1_r2b_sincola",
        "requiere_registro_dir": EXPERIMENT_DIR / "tanda_final" / "t5",
        "requiere_registro_modulo": "registro_vista_r2b_tramo1",
        "vista_runtime": "comun_ev2.cargar_runtime('tandafinal_ens_tramo1_r2b_sincola') tras importar tanda_final/t5/registro_vista_r2b_tramo1 (registro en memoria, patrón comun_tanda0); tramo 1 de la tanda final de B6.1, sellado como respaldo (enmienda 9); grafo del tramo 1 sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_tandafinal_tramo1_r2b_sincola",
    },
    # Acumulado de las tandas 0 y 1 sin la cola humana (U-NAV-DISENO, N5; mandato firmado en c2ddf5f7, decisión 5: el
    # grafo de N6). Lo armó T3 de la tanda 1 (tanda1/t3/acumulado/ens_treinta_r2b_sincola); su kg.json no está en el
    # repo: se restaura del kg.json.gz, sellado en e2615b36 (kg.json.gz.sello.json, que fija el sha256 del kg.json). Su
    # vista runtime la registra en memoria data/experiment/banco_mcp/mcp_kg/registro_vista_acumulado.py (patrón de
    # tanda1/t3/registro_vista_r2b_tanda1.py). Antes de N5 se cargaba con un envoltorio en memoria.
    "KG_Acumulado_Tandas0y1_r2b_sincola": {
        "nombre_canonico": "KG-Acumulado-Tandas0y1-r2b-sincola",
        "label": "KG_Acumulado_Tandas0y1_r2b_sincola",
        "path": EXPERIMENT_DIR / "tanda1" / "t3" / "acumulado" / "ens_treinta_r2b_sincola" / "r2" / "kg.json",
        "sha256": "0435d41f9c7b45ea10cc87e8121fcfb8b3d2b089af837fff377a3460ced9636c",
        "commit_sellado": "e2615b36",
        "n_nodos": 20833,
        "n_aristas": 55358,
        "ev2_key": "acumulado_tandas0y1_r2b_sincola",
        "requiere_registro_dir": EXPERIMENT_DIR / "banco_mcp" / "mcp_kg",
        "requiere_registro_modulo": "registro_vista_acumulado",
        "vista_runtime": "comun_ev2.cargar_runtime('acumulado_tandas0y1_r2b_sincola') tras importar banco_mcp/mcp_kg/registro_vista_acumulado (registro en memoria, patrón comun_tanda0); grafo de N6 de U-NAV-DISENO (decisión 5): acumulado de las tandas 0 y 1 sin la cola humana; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_acumulado_tandas0y1_r2b_sincola",
    },
    # El grafo evaluado de B6.3 (pre-registro firmado en adf20f3b, H-1): el acumulado de las tandas 0, 1 y final sin la
    # cola humana, con la re-aplicación única (U-REAPL, paso 5; reaplicacion_unica/acumulado/ens_128_r2b_sincola). Su
    # kg.json no está en el repo: se restaura del kg.json.gz, sellado en fde70c67 (sello_grafo_evaluado.json y
    # kg.json.gz.sello.json, que fijan el sha256 del kg.json). Su vista runtime la registra en memoria
    # data/experiment/banco_mcp/mcp_kg/registro_vista_evaluado.py (patrón de registro_vista_acumulado.py).
    "KG_Acumulado_Tandas0y1yFinal_r2b_sincola": {
        "nombre_canonico": "KG-Acumulado-Tandas0y1yFinal-r2b-sincola",
        "label": "KG_Acumulado_Tandas0y1yFinal_r2b_sincola",
        "path": EXPERIMENT_DIR / "reaplicacion_unica" / "acumulado" / "ens_128_r2b_sincola" / "r2" / "kg.json",
        "sha256": "576c97256185a0d5741cb2c35a2a85e91412f3e1119ad7a85d960b7d60c35ad3",
        "commit_sellado": "fde70c67",
        "n_nodos": 37168,
        "n_aristas": 128552,
        "ev2_key": "acumulado_tandas0y1yfinal_r2b_sincola",
        "requiere_registro_dir": EXPERIMENT_DIR / "banco_mcp" / "mcp_kg",
        "requiere_registro_modulo": "registro_vista_evaluado",
        "vista_runtime": "comun_ev2.cargar_runtime('acumulado_tandas0y1yfinal_r2b_sincola') tras importar banco_mcp/mcp_kg/registro_vista_evaluado (registro en memoria, patrón comun_tanda0); el grafo evaluado de B6.3 (H-1): acumulado de las tandas 0, 1 y final sin la cola humana, con la re-aplicación única; r2b no se evalúa con EV2",
        "indice_fulltext": "nodos_fulltext_kg_acumulado_tandas0y1yfinal_r2b_sincola",
    },
}
CLAVES = list(GRAFOS.keys())
GRAFO_DEFAULT = "KG_Refinado"   # el grafo vigente (docs/tablero.md); compatibilidad con c26cb9b


def sha256_de(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def verificar_sha(clave: str) -> str:
    """Aborta si el kg.json no coincide con el sha sellado. Devuelve el sha."""
    g = GRAFOS[clave]
    h = sha256_de(g["path"])
    if h != g["sha256"]:
        raise SystemExit(
            f"ABORTO: sha256 de {g['path']} = {h}\n"
            f"        esperado ({clave}) = {g['sha256']}\n"
            "El grafo insumo no coincide con el sellado; no se carga nada."
        )
    return h


def cargar_vista_runtime(clave: str):
    """KnowledgeGraph con la vista runtime EV2 del grafo (import de comun_ev2).
    Si la entrada declara `requiere_registro_dir`, se importa antes el módulo
    que registra su vista en memoria (r1: comun_r1, precedente U-B1.8)."""
    reg = GRAFOS[clave].get("requiere_registro_dir")
    if reg is not None:
        if str(reg) not in sys.path:
            sys.path.insert(0, str(reg))
        import importlib  # noqa: E402
        # default comun_r1: comportamiento idéntico para las entradas existentes
        importlib.import_module(GRAFOS[clave].get("requiere_registro_modulo", "comun_r1"))
    from comun_ev2 import cargar_runtime  # noqa: E402  (solo import)
    return cargar_runtime(GRAFOS[clave]["ev2_key"])


def rel_repo(path: Path) -> str:
    return str(Path(path).resolve().relative_to(REPO_DIR))
