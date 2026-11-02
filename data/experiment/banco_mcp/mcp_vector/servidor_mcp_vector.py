#!/usr/bin/env python3
"""servidor_mcp_vector.py — Servidor MCP (stdio) del brazo de fragmentos del banco
(U-A2.0-banco, pieza ii; A2.1, tramo 1). Tool ÚNICA:

    buscar_pasajes(consulta, limite) -> {consulta, total_pasajes, resultados: [
        {rank, id, to, unidad, archivo, titulo, tipo, paginas, score, texto}]}

(en el modo híbrido, `buscar_pasajes(consulta, limite, to, punto)`; con algún
filtro, la salida suma `filtros`, `n_pasajes_filtrados` y, si no queda ningún
pasaje, `aviso`; sin filtros, la misma forma que en los otros dos modos)

sobre los pasajes de E0 (propio + herencia) del índice que declara la config.
Cada pasaje devuelto cita el TO (`to`, `archivo`) y el punto (`unidad`).

Dos medidas de afinidad, por la clave `afinidad` de la config (A2.1: el
sistema por fragmentos es uno solo, con dos configuraciones que difieren solo
en la medida de afinidad):

  · `denso` (default; la de U-A2.0-banco): embeddings de
    `microsoft/harrier-oss-v1-0.6b` construidos por `construir_indice.py`
    (laudo A2.0b). Reglas selladas (docs/decision_modelo_embeddings.md §7-§8):
    la consulta se codifica CON el prompt preconfigurado `web_search_query`
    del propio repo del modelo; los documentos se codificaron SIN prompt
    (asimetría de los autores; test de asimetría en test_mcp_vector.py);
    similitud coseno (embeddings L2-normalizados por el módulo 2_Normalize
    del modelo ⇒ producto interno), `float32`, `max_seq_length` del manifiesto;
  · `bm25`: BM25 con el analizador `spanish` de Lucene (bm25_fragmentos.py),
    sobre los mismos pasajes. En este modo el proceso no importa numpy,
    torch, sentence-transformers ni el driver del grafo, y no carga el modelo.

Una tercera, `hibrida` (U-NAV-DISENO, N5-F: la forma de fragmentos de la
familia 1, medida en F1, §6 bis): el ranking BM25 y el denso de los mismos
pasajes, cada uno con su índice y sus verificaciones, fusionados con RRF
(k = 60, cada ranking entero), con dos entradas opcionales más en la tool,
solo en este modo: `to` (los pasajes de un TO) y `punto` (los de un punto y
sus subpuntos). Los filtros se aplican a cada ranking antes de fusionar.

En las tres, ranking determinístico con el desempate del bake-off
(e3_medicion.py): score desc, luego id asc. `limite` se acota a
[1, limite_max] con la misma expresión que `GraphIndex._limite` (default 10 si
no es entero, acotado también por limite_max). `limite_max` sale de la config:
50 si no lo declara (U-A2.0-banco); 5 en las configuraciones de A2.1 (D-D,
top-k = 5) y en las de F1.

`desde` (U-NAV-DESDE, la misma semántica que en `buscar_puntos` del brazo del
grafo), en los tres modos, solo en las configuraciones que declaran
`parametro_desde: true`: los resultados del ranking desde esa posición, con el
mismo `limite`, y el `rank` de cada uno es su lugar en el ranking. Un entero de
0 o más (lo que no es entero, o es negativo, vale 0, sin error). Con `desde` > 0
la salida suma `desde` y, si pasa el largo del ranking, `aviso`. Con `desde=0`
(o sin pasarlo) la salida es la de antes, byte a byte. Las configuraciones que
no lo declaran (las de A2.1 y A2.2) exponen la tool de antes y no lo leen.

Al arrancar verifica los sha del índice contra su manifiesto y contra la
config (en modo denso, además, el manifiesto contra el sha_docs del bake-off
cuando el índice es el de la E0 vieja; en modo BM25, re-deriva el índice desde
los pasajes con el analizador del proceso y exige el mismo sha; en modo
híbrido, las dos cosas, y que los dos índices sirvan el mismo `pasajes.json`):
si difieren, no expone nada.

R1: log íntegro por llamada (comun_banco.LogR1), mismo formato que mcp_kg.
Serialización de la respuesta: `json.dumps(obj, ensure_ascii=False)` — la misma
del harness y del otro brazo, para que el adaptador trate ambos igual.

Uso:
    python3 -B servidor_mcp_vector.py --config config_mcp_vector.json
"""
from __future__ import annotations

import argparse
import asyncio
import heapq
import json
import sys
import time
import unicodedata
from fractions import Fraction
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
if str(BANCO_DIR) not in sys.path:
    sys.path.insert(0, str(BANCO_DIR))
from comun_banco import (LogR1, cargar_config, rel_repo, serializar_payload,  # noqa: E402
                         sha256_bytes, sha256_file, versiones_entorno)

VERSION_SERVIDOR = "1.0"
NOMBRE_SERVIDOR = "mcp_vector"
CONFIG_DEFAULT = AQUI / "config_mcp_vector.json"
LIMITE_MAX_DEFAULT = 50
# Tope en caracteres del resultado de cada tool en Claude Code (D-6). Sin
# `_meta["anthropic/maxResultSizeChars"]`, el CLI sellado (2.1.241) guarda en
# disco todo resultado de más de 50.000 caracteres; con la anotación, el umbral
# es el valor anotado (hasta 500.000) y el CLI no le aplica a la tool el tope en
# tokens (MAX_MCP_OUTPUT_TOKENS). Mismo valor en todas las tools de los dos
# servidores del banco.
TOPE_CARACTERES_RESULTADO = 200000

TOOL_BUSCAR_PASAJES = {
    "name": "buscar_pasajes",
    "description": ("Búsqueda semántica (embeddings) de pasajes del texto de las normas. "
                    "Devuelve los pasajes más similares a la consulta, cada uno con su "
                    "TO (norma), punto (unidad) y el texto completo del pasaje. Es el "
                    "punto de entrada habitual."),
    "input_schema": {
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Consulta en lenguaje natural."},
            "limite": {"type": "integer", "description": "Máximo de resultados (def. 10)."},
        },
        "required": ["consulta"],
    },
}
# Lo único que cambia en la definición de la tool según la config (A2.1): el
# nombre de la medida de afinidad y, con limite_max < 10, el default y el tope.
DESCRIPCION_BM25 = ("Búsqueda léxica (BM25) de pasajes del texto de las normas. "
                    "Devuelve los pasajes más similares a la consulta, cada uno con su "
                    "TO (norma), punto (unidad) y el texto completo del pasaje. Es el "
                    "punto de entrada habitual.")
# Modo híbrido (N5-F): la misma tool, con el nombre de la medida y los dos filtros opcionales.
DESCRIPCION_HIBRIDA = ("Búsqueda híbrida (léxica BM25 y semántica por embeddings, fusionadas por "
                       "rango) de pasajes del texto de las normas. Devuelve los pasajes más similares "
                       "a la consulta, cada uno con su TO (norma), punto (unidad) y el texto completo "
                       "del pasaje. Se puede acotar a un TO (`to`) y a un punto con sus subpuntos "
                       "(`punto`). Es el punto de entrada habitual.")
PROPIEDADES_FILTROS = {
    "to": {"type": "string",
           "description": "Opcional: solo pasajes de este TO (el valor del campo `to` de los resultados, p. ej. `cap`)."},
    "punto": {"type": "string",
              "description": ("Opcional: solo pasajes de este punto y sus subpuntos (prefijo del campo `unidad`, "
                              "p. ej. `6.5`).")},
}
# Fusión del modo híbrido, fija antes de medir (mandato U-NAV-DISENO, decisión 7 y §6 bis; propuesta del
# diseño de la familia 1): RRF con k = 60 sobre cada ranking entero (profundidad None), después de los
# filtros. La config las declara y el servidor aborta si no coinciden con estas.
RRF_K = 60
PROFUNDIDAD_RRF = None
# U-NAV-DESDE: `desde` en la tool, solo con `parametro_desde: true` en la config. La descripción lo explica con el
# mismo texto que la de buscar_puntos, en el brazo del grafo.
TEXTO_DESDE = ("desde: posición del ranking desde la que se listan los resultados (0 = los primeros). "
               "Sirve para ver los que no entraron.")
PROPIEDAD_DESDE = {"desde": {"type": "integer", "description": "Posición desde la que se lista (def. 0)."}}


def definicion_tool(afinidad: str = "denso", limite_max: int = LIMITE_MAX_DEFAULT, desde: bool = False) -> dict:
    """La de U-A2.0-banco tal cual con (denso, 50); para A2.1, la misma con el nombre de la
    medida de afinidad y el tope de `limite` a la vista; en el modo híbrido, además, `to` y `punto`;
    con `desde` (U-NAV-DESDE), además, `desde` en el esquema y su explicación en la descripción."""
    t = json.loads(json.dumps(TOOL_BUSCAR_PASAJES))
    if afinidad == "bm25":
        t["description"] = DESCRIPCION_BM25
    if afinidad == "hibrida":
        t["description"] = DESCRIPCION_HIBRIDA
        t["input_schema"]["properties"].update(json.loads(json.dumps(PROPIEDADES_FILTROS)))
    if desde:
        t["description"] += " " + TEXTO_DESDE
        t["input_schema"]["properties"].update(json.loads(json.dumps(PROPIEDAD_DESDE)))
    if limite_max < 10:
        t["input_schema"]["properties"]["limite"]["description"] = (
            f"Máximo de resultados (def. {limite_max}, máx. {limite_max}).")
    return t


def _limite(limite, limite_max: int = LIMITE_MAX_DEFAULT) -> int:
    # Misma expresión que GraphIndex.buscar_nodos / Neo4jIndex._limite, con el tope de la config.
    try:
        return max(1, min(int(limite), limite_max))
    except (TypeError, ValueError):
        return min(10, limite_max)


def _desde(desde) -> int:
    """U-NAV-DESDE: un entero de 0 o más, como el `desde` del brazo del grafo: lo que no es entero vale 0, un
    negativo vale 0 y el máximo es 10 ** 9. Sin error, como `limite`, que vale su default."""
    try:
        return max(0, min(int(desde), 10 ** 9))
    except (TypeError, ValueError):
        return 0


def _encabezado(consulta, total_pasajes: int, desde: int) -> dict:
    """El comienzo de la salida: con `desde` = 0, el de antes ({consulta, total_pasajes}); con `desde` > 0, suma `desde`."""
    obj = {"consulta": consulta, "total_pasajes": total_pasajes}
    if desde:
        obj["desde"] = desde
    return obj


def _pagina(obj: dict, resultados: list, desde: int, n_ranking: int) -> dict:
    """Cierra la salida con los resultados de la página. Con `desde` > 0 y la página vacía (`desde` pasa el largo
    del ranking), suma `aviso` con ese largo, salvo que ya haya otro aviso (el de los filtros de la híbrida).
    `n_ranking` solo se usa con la página vacía: entonces la búsqueda ya trajo el ranking entero."""
    if desde and not resultados and "aviso" not in obj:
        obj["aviso"] = f"no hay más resultados: el ranking tiene {n_ranking} pasajes (desde={desde})"
    obj["resultados"] = resultados
    return obj


def _fila(r: int, p: dict, s: float) -> dict:
    return {"rank": r, "id": p["id"], "to": p["to"], "unidad": p["unidad"],
            "archivo": p["archivo"], "titulo": p["titulo"], "tipo": p["tipo"],
            "paginas": p["paginas"], "score": round(s, 6), "texto": p["texto"]}


class IndiceVectorial:
    def __init__(self, config: dict):
        import numpy as np
        self.dir = (AQUI / config["indice_dir"]).resolve()
        self.man = json.loads((self.dir / "manifiesto_indice.json").read_text(encoding="utf-8"))
        self.E = np.load(self.dir / "embeddings_docs.npy")
        self.pasajes = json.loads((self.dir / "pasajes.json").read_text(encoding="utf-8"))
        self.ids = [p["id"] for p in self.pasajes]
        self.limite_max = int(config.get("limite_max", LIMITE_MAX_DEFAULT))
        # sellos
        import hashlib
        sha_m = hashlib.sha256(self.E.astype("float32").tobytes(order="C")).hexdigest()
        if sha_m != self.man["matriz"]["sha256_matriz"]:
            raise SystemExit(f"ABORTO: sha de la matriz {sha_m} != manifiesto {self.man['matriz']['sha256_matriz']}")
        if sha_m != config["sha256_matriz_esperado"]:
            raise SystemExit(f"ABORTO: sha de la matriz {sha_m} != esperado por config {config['sha256_matriz_esperado']}")
        if self.E.shape[0] != len(self.pasajes):
            raise SystemExit("ABORTO: matriz y pasajes no coinciden en cantidad")
        self.sha_matriz = sha_m
        mcfg = self.man["modelo"]
        self.prompt_name = mcfg["prompt_consultas"]
        self.prompt_texto = mcfg["prompt_consultas_texto"]   # sellado en el manifiesto; se re-verifica al cargar
        self._device = config.get("device", "mps")
        self._m = None
        if config.get("carga_modelo", "perezosa") == "inmediata":
            self._cargar_modelo()

    def _cargar_modelo(self):
        """Carga PEREZOSA (decisión medida): el modelo tarda ~70 s en cargar y
        Claude Code 2.1.196 no espera a un servidor `pending` antes del primer
        turno (la espera está documentada a partir de v2.1.221). Con la carga en
        la primera llamada, `initialize` y `tools/list` responden al instante y
        el servidor figura `connected` con su tool desde el `system/init`. La
        primera `buscar_pasajes` paga la carga; el `timeout` por servidor del
        JSON de MCP cubre esa latencia."""
        if self._m is not None:
            return self._m
        mcfg = self.man["modelo"]
        import torch
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(mcfg["repo"], revision=mcfg["revision"], device=self._device,
                                trust_remote_code=False, model_kwargs={"dtype": torch.float32})
        m.max_seq_length = mcfg["max_seq_length"]
        if self.prompt_name not in (m.prompts or {}) or m.prompts[self.prompt_name] != self.prompt_texto:
            raise SystemExit(f"ABORTO: el prompt {self.prompt_name!r} del modelo no coincide con el manifiesto")
        self._m = m
        return m

    @property
    def m(self):
        return self._cargar_modelo()

    def embed_consulta(self, consulta: str, con_prompt: bool = True):
        kw = {"prompt_name": self.prompt_name} if con_prompt else {}
        return self.m.encode([consulta], batch_size=1, convert_to_numpy=True,
                             normalize_embeddings=True, show_progress_bar=False, **kw)[0].astype("float32")

    def buscar_pasajes(self, consulta: str, limite: int = 10, desde: int = 0) -> dict:
        import numpy as np
        limite, desde = _limite(limite, self.limite_max), _desde(desde)
        obj = _encabezado(consulta, len(self.ids), desde)
        if not isinstance(consulta, str) or not consulta.strip():
            return _pagina(obj, [], desde, 0)
        q = self.embed_consulta(consulta, con_prompt=True)
        S = self.E @ q
        idx = np.argsort(-S, kind="stable")[:(desde + limite) * 3]
        orden = sorted(((int(i), float(S[i])) for i in idx), key=lambda kv: (-kv[1], self.ids[kv[0]]))
        top = orden[desde:desde + limite]
        res = [_fila(r, self.pasajes[i], s) for r, (i, s) in enumerate(top, desde + 1)]
        return _pagina(obj, res, desde, len(self.ids))


class IndiceBM25:
    """Modo BM25 (A2.1): sin numpy, sin modelo. El índice persistido se verifica
    por sha contra el manifiesto y la config, y se re-deriva desde los pasajes
    con el analizador de este proceso: si el analizador cambió, aborta."""

    def __init__(self, config: dict):
        import bm25_fragmentos as BM
        self.BM = BM
        self.dir = (AQUI / config["indice_dir"]).resolve()
        self.man = json.loads((self.dir / "manifiesto_indice.json").read_text(encoding="utf-8"))
        sha_p = sha256_file(self.dir / "pasajes.json")
        if sha_p != self.man["corpus"]["sha256_pasajes_json"]:
            raise SystemExit(f"ABORTO: sha de pasajes.json {sha_p} != manifiesto {self.man['corpus']['sha256_pasajes_json']}")
        self.pasajes = json.loads((self.dir / "pasajes.json").read_text(encoding="utf-8"))
        self.ids = [p["id"] for p in self.pasajes]
        crudo = (self.dir / "indice_bm25.json").read_bytes()
        sha_i = sha256_bytes(crudo)
        if sha_i != self.man["bm25"]["sha256_indice"]:
            raise SystemExit(f"ABORTO: sha del índice BM25 {sha_i} != manifiesto {self.man['bm25']['sha256_indice']}")
        if sha_i != config["sha256_indice_esperado"]:
            raise SystemExit(f"ABORTO: sha del índice BM25 {sha_i} != esperado por config {config['sha256_indice_esperado']}")
        indice = json.loads(crudo.decode("utf-8"))
        if BM.sha256_indice(BM.construir(self.pasajes)) != sha_i or indice["ids"] != self.ids:
            raise SystemExit("ABORTO: el analizador de este proceso no reproduce el índice BM25 persistido")
        self.sha_indice = sha_i
        self.limite_max = int(config.get("limite_max", LIMITE_MAX_DEFAULT))
        self.buscador = BM.Buscador(indice)

    def buscar_pasajes(self, consulta: str, limite: int = 10, desde: int = 0) -> dict:
        limite, desde = _limite(limite, self.limite_max), _desde(desde)
        obj = _encabezado(consulta, len(self.ids), desde)
        if not isinstance(consulta, str) or not consulta.strip():
            return _pagina(obj, [], desde, 0)
        top = self.buscador.buscar(consulta, desde + limite)
        res = [_fila(r, self.pasajes[i], s) for r, (i, s) in enumerate(top[desde:], desde + 1)]
        return _pagina(obj, res, desde, len(top))


def fusion_rrf(rankings: list[list[int]], ids: list[str], k: int = RRF_K, profundidad: int | None = PROFUNDIDAD_RRF,
               limite: int | None = None) -> list[tuple[int, Fraction]]:
    """RRF (Cormack, Clarke y Büttcher, SIGIR 2009): puntaje(d) = Σ 1 / (k + rango_i(d)), con el rango
    desde 1, sobre los rankings en los que d está entre los `profundidad` primeros (None: el ranking
    entero). La suma es exacta (fracciones), así dos puntajes iguales empatan siempre y el desempate
    (score desc, id asc) no depende del redondeo. Con `limite`, los `limite` primeros (heapq.nsmallest
    con la misma clave equivale a sorted(...)[:limite])."""
    acum: dict[int, Fraction] = {}
    for r in rankings:
        for pos, i in enumerate(r if profundidad is None else r[:profundidad], 1):
            acum[i] = acum.get(i, 0) + Fraction(1, k + pos)
    clave = lambda kv: (-kv[1], ids[kv[0]])
    if limite is None:
        return sorted(acum.items(), key=clave)
    return heapq.nsmallest(limite, acum.items(), key=clave)


def _filtro(x, punto: bool = False) -> str | None:
    """Normaliza una entrada de filtro: None o vacía -> sin filtro; si no, el texto sin espacios en los
    bordes (y, en `punto`, sin el punto final de «6.5.»)."""
    if x is None:
        return None
    s = str(x).strip()
    if punto:
        s = s.rstrip(".").strip()
    return s or None


def coincide_punto(unidad: str, punto: str) -> bool:
    """`unidad` es `punto` o uno de sus subpuntos: igual, o empieza con `punto` seguido de «.» o de «::».
    Sin distinguir mayúsculas. Así «1.1» incluye «1.1.2» pero no «1.10»."""
    u, p = unidad.casefold(), punto.casefold()
    return u == p or u.startswith(p + ".") or u.startswith(p + "::")


class IndiceHibrido:
    """Modo híbrido (N5-F): los mismos pasajes con su índice BM25 y su matriz densa, cada uno verificado
    como en su modo propio (IndiceBM25 e IndiceVectorial, sin cambios), y la fusión RRF de sus dos
    rankings. El modelo se carga en la primera llamada, como en el modo denso."""

    def __init__(self, config: dict):
        if config.get("rrf_k") != RRF_K or config.get("profundidad_rrf", "sin declarar") != PROFUNDIDAD_RRF:
            raise SystemExit(f"ABORTO: la config declara rrf_k={config.get('rrf_k')!r} y profundidad_rrf="
                             f"{config.get('profundidad_rrf', 'sin declarar')!r}; el servidor fija {RRF_K} y "
                             f"{PROFUNDIDAD_RRF!r}")
        self.limite_max = int(config.get("limite_max", LIMITE_MAX_DEFAULT))
        self.bm25 = IndiceBM25({"indice_dir": config["indice_dir_bm25"],
                                "sha256_indice_esperado": config["sha256_indice_esperado"],
                                "limite_max": self.limite_max})
        self.denso = IndiceVectorial({"indice_dir": config["indice_dir_denso"],
                                      "sha256_matriz_esperado": config["sha256_matriz_esperado"],
                                      "limite_max": self.limite_max, "device": config.get("device", "mps"),
                                      "carga_modelo": config.get("carga_modelo", "perezosa")})
        self.sha_pasajes = sha256_file(self.bm25.dir / "pasajes.json")
        if self.sha_pasajes != sha256_file(self.denso.dir / "pasajes.json") or self.bm25.ids != self.denso.ids:
            raise SystemExit("ABORTO: el índice BM25 y el denso no sirven los mismos pasajes")
        e0_b, e0_d = self.bm25.man.get("manifiesto_e0") or {}, self.denso.man.get("manifiesto_e0") or {}
        if (e0_b.get("id"), e0_b.get("sha256")) != (e0_d.get("id"), e0_d.get("sha256")):
            raise SystemExit("ABORTO: el índice BM25 y el denso vienen de manifiestos de E0 distintos")
        self.man = {"manifiesto_e0": e0_b}
        self.pasajes, self.ids = self.bm25.pasajes, self.bm25.ids
        self.tos = sorted({p["to"] for p in self.pasajes})

    def ranking_bm25(self, consulta: str) -> list[int]:
        """El ranking BM25 entero (los pasajes con puntaje > 0), con la clave de Buscador.buscar."""
        s = self.bm25.buscador.puntajes(self.bm25.BM.analizar(consulta))
        return [i for i, _ in sorted(s.items(), key=lambda kv: (-kv[1], self.ids[kv[0]]))]

    def ranking_denso(self, consulta: str) -> list[int]:
        """El ranking denso entero, con la clave de IndiceVectorial.buscar_pasajes."""
        S = (self.denso.E @ self.denso.embed_consulta(consulta, con_prompt=True)).tolist()
        return sorted(range(len(S)), key=lambda i: (-S[i], self.ids[i]))

    def permitidos(self, to: str | None, punto: str | None) -> set[int] | None:
        if to is None and punto is None:
            return None
        return {i for i, p in enumerate(self.pasajes)
                if (to is None or p["to"].casefold() == to.casefold())
                and (punto is None or coincide_punto(p["unidad"], punto))}

    def buscar_pasajes(self, consulta: str, limite: int = 10, to=None, punto=None, desde: int = 0) -> dict:
        limite, desde = _limite(limite, self.limite_max), _desde(desde)
        to, punto = _filtro(to), _filtro(punto, punto=True)
        obj = _encabezado(consulta, len(self.ids), desde)
        perm = self.permitidos(to, punto)
        if perm is not None:
            obj["filtros"] = {k: v for k, v in (("to", to), ("punto", punto)) if v is not None}
            obj["n_pasajes_filtrados"] = len(perm)
            if not perm:
                if to is not None and to.casefold() not in {t.casefold() for t in self.tos}:
                    obj["aviso"] = f"ningún pasaje es del TO {to!r}; los TOs del índice: {', '.join(self.tos)}"
                else:
                    obj["aviso"] = (f"ningún pasaje{f' del TO {to!r}' if to else ''} tiene el punto {punto!r} "
                                    "ni subpuntos suyos")
        if not isinstance(consulta, str) or not consulta.strip() or perm == set():
            return _pagina(obj, [], desde, 0)
        rk = [self.ranking_bm25(consulta), self.ranking_denso(consulta)]
        if perm is not None:
            rk = [[i for i in r if i in perm] for r in rk]
        top = fusion_rrf(rk, self.ids, limite=desde + limite)
        res = [_fila(r, self.pasajes[i], float(s)) for r, (i, s) in enumerate(top[desde:], desde + 1)]
        return _pagina(obj, res, desde, len(top))


def construir_indice_de(config: dict):
    afinidad = config.get("afinidad", "denso")
    if afinidad == "denso":
        return IndiceVectorial(config)
    if afinidad == "bm25":
        return IndiceBM25(config)
    if afinidad == "hibrida":
        return IndiceHibrido(config)
    raise SystemExit(f"ABORTO: afinidad desconocida en la config: {afinidad!r}")


def construir_servidor(config_path: Path):
    import mcp.types as types
    from mcp.server.lowlevel import Server

    config, config_sha = cargar_config(config_path)
    afinidad = config.get("afinidad", "denso")
    con_desde = config.get("parametro_desde", False)
    if not isinstance(con_desde, bool):
        raise SystemExit(f"ABORTO: parametro_desde tiene que ser true o false en la config: {con_desde!r}")
    idx = construir_indice_de(config)
    if afinidad == "denso":
        fuente = {"backend": "vectorial_local", "indice_dir": rel_repo(idx.dir),
                  "sha256_matriz": idx.sha_matriz,
                  "sha256_manifiesto": sha256_file(idx.dir / "manifiesto_indice.json"),
                  "sha256_pasajes_json": sha256_file(idx.dir / "pasajes.json"),
                  "n_pasajes": len(idx.ids), "modelo": idx.man["modelo"],
                  "sha_docs_bakeoff": idx.man["matriz"].get("sha_docs_bakeoff"),
                  "coincide_con_bakeoff": idx.man["matriz"].get("coincide_con_bakeoff"),
                  "prompt_consultas_texto": idx.prompt_texto}
        libs = ["mcp", "torch", "transformers", "sentence-transformers", "tokenizers", "numpy"]
    elif afinidad == "hibrida":
        b, d = idx.bm25, idx.denso
        fuente = {"backend": "hibrido_local", "afinidad": "hibrida",
                  "fusion": {"metodo": "rrf", "k": RRF_K, "profundidad": PROFUNDIDAD_RRF,
                             "desempate": "score desc, id asc", "filtros": sorted(PROPIEDADES_FILTROS)},
                  "bm25": {"indice_dir": rel_repo(b.dir), "sha256_indice_bm25": b.sha_indice,
                           "sha256_manifiesto": sha256_file(b.dir / "manifiesto_indice.json"),
                           "analizador": b.BM.ANALIZADOR, "lucene_version": b.BM.LUCENE_VERSION,
                           "sha256_stop": b.BM.SHA256_STOP, "unicodedata": unicodedata.unidata_version,
                           "k1": b.BM.K1, "b": b.BM.B, "sha256_modulo_bm25": sha256_file(AQUI / "bm25_fragmentos.py")},
                  "denso": {"indice_dir": rel_repo(d.dir), "sha256_matriz": d.sha_matriz,
                            "sha256_manifiesto": sha256_file(d.dir / "manifiesto_indice.json"),
                            "modelo": d.man["modelo"], "prompt_consultas_texto": d.prompt_texto},
                  "sha256_pasajes_json": idx.sha_pasajes, "n_pasajes": len(idx.ids)}
        libs = ["mcp", "torch", "transformers", "sentence-transformers", "tokenizers", "numpy"]
    else:
        fuente = {"backend": "bm25_local", "afinidad": "bm25", "indice_dir": rel_repo(idx.dir),
                  "sha256_indice_bm25": idx.sha_indice,
                  "sha256_manifiesto": sha256_file(idx.dir / "manifiesto_indice.json"),
                  "sha256_pasajes_json": sha256_file(idx.dir / "pasajes.json"),
                  "n_pasajes": len(idx.ids), "analizador": idx.BM.ANALIZADOR,
                  "lucene_version": idx.BM.LUCENE_VERSION, "sha256_stop": idx.BM.SHA256_STOP,
                  "unicodedata": unicodedata.unidata_version,
                  "k1": idx.BM.K1, "b": idx.BM.B,
                  "sha256_modulo_bm25": sha256_file(AQUI / "bm25_fragmentos.py")}
        libs = ["mcp"]
    if "manifiesto_e0" in idx.man:
        fuente["manifiesto_e0"] = idx.man["manifiesto_e0"]
    fuente["limite_max"] = idx.limite_max
    if con_desde:
        fuente["parametro_desde"] = True
    log = LogR1(NOMBRE_SERVIDOR, VERSION_SERVIDOR, config, config_sha, fuente,
                versiones_entorno(libs) | {"config_path": rel_repo(config_path)})
    server = Server(NOMBRE_SERVIDOR, version=VERSION_SERVIDOR)
    tool = definicion_tool(afinidad, idx.limite_max, desde=con_desde)

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [types.Tool(name=tool["name"], description=tool["description"], inputSchema=tool["input_schema"],
                           _meta={"anthropic/maxResultSizeChars": TOPE_CARACTERES_RESULTADO})]

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict):
        t0 = time.perf_counter()
        n, call_id = log.nuevo_call_id()
        try:
            rpc_id = server.request_context.request_id
        except LookupError:
            rpc_id = None
        args = arguments or {}
        desde = {"desde": args.get("desde", 0)} if con_desde else {}   # sin parametro_desde, no se lee
        try:
            if name == "buscar_pasajes" and afinidad == "hibrida":
                obj = idx.buscar_pasajes(args.get("consulta", ""), args.get("limite", 10),
                                         to=args.get("to"), punto=args.get("punto"), **desde)
            elif name == "buscar_pasajes":
                obj = idx.buscar_pasajes(args.get("consulta", ""), args.get("limite", 10), **desde)
            else:
                obj = {"error": f"tool desconocida: {name}"}
            out = serializar_payload(obj)
        except Exception as e:
            log.llamada(n, call_id, rpc_id, name, args, None, t0, error=f"{type(e).__name__}: {e}")
            raise
        log.llamada(n, call_id, rpc_id, name, args, out, t0)
        return [types.TextContent(type="text", text=out)]

    return server, log, idx


def _fin_ante_senal(log):
    """C2 (laudo fase B): Claude Code termina el proceso del servidor al cerrar la
    sesión (SIGTERM tras cerrar stdin). Sin esto el `finally` no corre y el log
    R1 queda sin línea `fin` (medido en la corrida 1: 6/6 sesiones del vectorial)."""
    import os
    import signal

    def _handler(signum, frame):
        try:
            log.fin()
        finally:
            os._exit(0)
    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)


async def servir(config_path: Path) -> None:
    from mcp.server.stdio import stdio_server
    server, log, _ = construir_servidor(config_path)
    _fin_ante_senal(log)
    try:
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())
    finally:
        if not log.cerrado:
            log.fin()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    a = ap.parse_args()
    asyncio.run(servir(a.config.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
