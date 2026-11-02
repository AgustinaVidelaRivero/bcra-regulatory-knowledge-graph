#!/usr/bin/env python3
"""selftest_entorno_limpio.py — El entorno de la sesión de `env_sesion` (registro de decisiones, §83, §84 y §88) y
la preparación de cada sesión del banco (§84 y §85):
arranca vacío y del padre pasan solo las de la lista cerrada. Sin CLI y sin modelo (costo USD 0; no
escribe archivos).

Con un entorno de juguete sucio (las variables de una sesión de escritorio de Claude Code y otras de la
máquina, con valores falsos; las básicas del sistema, estén o no en la lista; las de AWS; una clave
falsa y MAX_MCP_OUTPUT_TOKENS), llama a `lanzar_agente.env_sesion` en los dos brazos (`vector` y `kg`) y
los dos modos (`init` y `real`), por la vía `api`, y controla que:
  1. el entorno final trae solo la lista decidida (PERMITIDAS: PATH, HOME y NEO4J_URI, con la carpeta personal
     de juguete), la clave, MAX_MCP_OUTPUT_TOKENS y lo del lanzador (BANCO_*, MCP_TIMEOUT,
     DISABLE_AUTOUPDATER=1 y, en init, la URL al puerto cerrado), con sus valores;
  2. ningún valor del padre que no pasó está en el entorno final;
  3. los nombres y los valores son iguales en los dos brazos, salvo BANCO_VENV_VECTOR, que va solo en
     el vector;
  4. el registro: `entorno_de_la_sesion` trae cada variable de la sesión con su valor, la carpeta
     personal como $HOME (HOME misma, como $HOME) y la clave como presencia; `entorno_no_heredadas`, los
     nombres del padre que no pasaron (HOME no está); y en ningún lado la clave, su largo, la carpeta
     personal ni un valor que no pasó.
Además: NEO4J_URI pasa con su valor y NEO4J_USER y NEO4J_PASSWORD no, en los dos brazos y los dos modos;
sin clave en el padre, init pone la inválida y real frena; la vía bedrock deja pasar las de AWS
(y la clave no), con CLAUDE_CODE_USE_BEDROCK=1 y las credenciales por presencia; A2.1
(`a2_1/lanzar_agente_a2_1.env_sesion`) da lo mismo que el brazo vector; `os.environ` no cambia; y, como
control, los chequeos marcan el entorno de juguete sin filtrar.

Las ramas C (etapa c), en carpetas temporales que se borran solas: la carpeta de configuración es nueva, vacía,
está bajo la raíz y no en el repo, y es distinta en cada sesión; CLAUDE_CONFIG_DIR está en el entorno y en el
registro, y la del padre no pasa; el cwd es el mismo en los dos brazos, está fuera de git y no nombra el brazo; el
lanzador frena con un cwd dentro del repo, dentro de un repo de git de juguete, no vacío y con una carpeta de
configuración que ya existe; la copia lee de la carpeta de configuración (y no de la configuración del asistente de la carpeta personal), con una transcripción
y un resultado guardado de juguete; y `lanzador` trae la ruta y el sha256 de los archivos cargados (uno en el
banco, dos en A2.1).

Uso:
  .venv/bin/python -B selftest_entorno_limpio.py
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
for _p in (str(BANCO_DIR), str(AQUI), str(BANCO_DIR / "a2_1")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_agente as LA                                               # noqa: E402
import lanzar_agente_a2_1 as L21                                         # noqa: E402

CLAVE = "ANTHROPIC_API_KEY"
CASA = "/hogar/juguete"
# La lista decidida (registro de decisiones, §84 y §88); el selftest la fija, no la lee del lanzador.
PERMITIDAS = ("PATH", "HOME", "NEO4J_URI")
# Las básicas del sistema candidatas y NEO4J_URI, con valores de juguete; pasan solo las de PERMITIDAS.
BASICAS = {"PATH": f"{CASA}/.local/bin:/usr/bin:/bin", "HOME": CASA, "TMPDIR": f"{CASA}/tmp-juguete/",
           "USER": "usuario-juguete", "LOGNAME": "logname-juguete", "SHELL": "/bin/shell-juguete",
           "LANG": "lang-juguete", "LC_CTYPE": "lc-juguete", "NEO4J_URI": "bolt://neo4j-juguete.invalid:37687"}
# Las otras NEO4J_* que lee conexion.py (valores de juguete): no pasan.
NEO4J_OTRAS = {"NEO4J_USER": "usuario-neo4j-juguete", "NEO4J_PASSWORD": "contrasena-neo4j-juguete"}
# Variables de una sesión de escritorio de Claude Code y otras de la máquina (valores falsos): no pasan.
SUCIAS = {
    "ANTHROPIC_BASE_URL": "http://sucio.invalid:1", "CLAUDECODE": "uno-sucio", "CLAUDE_EFFORT": "esfuerzo-sucio",
    "CLAUDE_CODE_SIMPLE": "simple-sucio", "CLAUDE_AGENT_SDK_MCP_NO_PREFIX": "prefijo-sucio",
    "MCP_CONNECTION_NONBLOCKING": "nonblocking-sucio", "CLAUDE_CODE_USE_BEDROCK": "bedrock-sucio",
    "CLAUDE_CODE_USE_VERTEX": "vertex-sucio", "CLAUDE_CODE_USE_FOUNDRY": "foundry-sucio",
    "CLAUDE_CONFIG_DIR": "/sucio/config", "CLAUDE_CODE_OAUTH_TOKEN": "token-oauth-sucio",
    "CLAUDE_CODE_MESSAGING_TOKEN": "token-mensajeria-sucio", "CLAUDE_CODE_ENTRYPOINT": "entrada-sucia",
    "MCP_TIMEOUT": "timeout-sucio", "MCP_SERVER_CONNECTION_BATCH_SIZE": "lote-sucio",
    "ANTHROPIC_AUTH_TOKEN": "auth-sucio", "ANTHROPIC_MODEL": "modelo-sucio",
    "API_TIMEOUT_MS": "espera-sucia", "AI_AGENT": "agente-sucio", "USE_STAGING_OAUTH": "staging-sucio",
    "USE_LOCAL_OAUTH": "local-sucio", "NODE_USE_SYSTEM_CA": "ca-sucio", "BAGGAGE": "baggage-sucio",
    "DISABLE_MICROCOMPACT": "microcompact-sucio", "DISABLE_AUTOUPDATER": "autoupdater-sucio",
    "CONDA_PREFIX": "/sucio/conda", "PYTHONPATH": "/sucio/pythonpath", "SSH_AUTH_SOCK": "/sucio/ssh",
    "BANCO_REPO": "/sucio/repo", "BANCO_LOG_R1": "/sucio/log", "BANCO_SESION_TAG": "tag-sucio",
}
AWS = {"AWS_REGION": "us-juguete-1", "AWS_PROFILE": "perfil-juguete", "AWS_ACCESS_KEY_ID": "AKIA-juguete",
       "AWS_SECRET_ACCESS_KEY": "secreto-aws-juguete", "AWS_SESSION_TOKEN": "token-aws-juguete"}
VENV_DEL_PADRE = "/juguete/venv_vector"
MAX_TOKENS = "70000"
CLAVE_FALSA = "sk-ant-falsa-del-selftest-" + "x" * 27
URL_INIT = "http://127.0.0.1:9"
CLAVE_INVALIDA = "sk-ant-invalido-modo-init"
LOG_R1 = AQUI / "no_se_escribe" / "log_r1_SELF-ENTORNO.jsonl"
TAG = "SELF-ENTORNO"


def permitidas() -> dict:
    return {k: v for k, v in BASICAS.items() if k in PERMITIDAS}


def correr(padre: dict, cfg: dict, brazo: str, modo: str, via: str = "api", fn=None) -> tuple[dict, dict, bool]:
    """(env final, env declarado, os.environ intacto) de env_sesion con `padre` como entorno."""
    fn = fn or LA.env_sesion
    with mock.patch.dict(os.environ, padre, clear=True), mock.patch.object(LA, "VENV_VECTOR_DEFAULT", "/sin/uso"):
        env, decl = fn(cfg, brazo, via, LOG_R1, TAG, modo)
        intacto = dict(os.environ) == padre
    return env, decl, intacto


def no_pasan(padre: dict, pasan: set) -> dict:
    return {k: v for k, v in padre.items() if k not in pasan}


def registro_ok(decl: dict, env: dict, padre: dict, pasaron: set, secretos: list[str], propias=frozenset()) -> bool:
    """El registro de una sesión: la sesión entera con sus valores, las no heredadas y nada que no deba ir.
    `propias`: las del lanzador que toman su valor del padre (BANCO_VENV_VECTOR en el brazo vector)."""
    ses = decl.get("entorno_de_la_sesion")
    if not isinstance(ses, dict):
        return False
    credenciales = getattr(LA, "CREDENCIALES_DEL_ENTORNO", (CLAVE,))
    esperado = {k: (("presente: sí" if env.get(k) else "presente: no") if k in credenciales
                    else env[k].replace(CASA, "$HOME")) for k in sorted(set(env) | {CLAVE})}
    texto = json.dumps(decl, ensure_ascii=False)
    return (ses == esperado and list(ses) == sorted(ses)
            and decl.get("entorno_no_heredadas") == sorted(set(padre) - pasaron)
            and not any(s in texto for s in secretos) and str(len(CLAVE_FALSA)) not in texto
            and CASA not in texto and not any(v in texto for v in no_pasan(padre, pasaron | propias).values())
            and ("HOME" not in PERMITIDAS
                 or (ses.get("HOME") == "$HOME" and "HOME" not in (decl.get("entorno_no_heredadas") or []))))


BRAZOS_EN_NOMBRES = ("kg", "vector", "fragmentos", "bm25", "denso")


def frena(f, *args) -> str | None:
    """El mensaje con que frena `f(*args)`, o None si no frena."""
    try:
        f(*args)
    except SystemExit as e:
        return str(e)
    return None


def ramas_c(rama, padre: dict, cfg: dict) -> None:
    """Las ramas de la etapa c. Cada una que no puede correr (p. ej. con un lanzador sin las piezas) da FAIL."""
    def probar(nombre: str, prueba) -> None:
        try:
            ok, detalle = prueba()
        except Exception as e:  # noqa: BLE001  (un lanzador sin las piezas de la etapa c falla, no se cae)
            ok, detalle = False, f"{type(e).__name__}: {e}"
        rama(nombre, ok, detalle)

    with tempfile.TemporaryDirectory() as td:
        raiz = Path(td).resolve() / "banco_sesiones"

        def c1():
            c_a, cwd_a = LA.preparar_sesion(raiz, None, "sesion-a")
            c_b, cwd_b = LA.preparar_sesion(raiz, None, "sesion-b")
            ok = (c_a != c_b and c_a.parent == c_b.parent == raiz / "config" and c_a.is_dir() and c_b.is_dir()
                  and not any(c_a.iterdir()) and not any(c_b.iterdir())
                  and not c_a.is_relative_to(LA.REPO_DIR) and not c_b.is_relative_to(LA.REPO_DIR))
            return ok, f"{c_a.relative_to(raiz)} y {c_b.relative_to(raiz)}"
        probar("C1 la carpeta de configuración: nueva, vacía, bajo la raíz, fuera del repo, una por sesión", c1)

        config_juguete = Path(CASA) / "banco_sesiones" / "config" / "sesion-juguete"
        for brazo in ("vector", "kg"):
            def c2(brazo=brazo):
                env, decl, _ = correr_con(padre, cfg, brazo, "init", config_juguete)
                ses = decl.get("entorno_de_la_sesion") or {}
                ok = (env.get("CLAUDE_CONFIG_DIR") == str(config_juguete)
                      and ses.get("CLAUDE_CONFIG_DIR") == "$HOME/banco_sesiones/config/sesion-juguete"
                      and SUCIAS["CLAUDE_CONFIG_DIR"] not in env.values() and CASA not in json.dumps(decl))
                return ok, f"registrado: {ses.get('CLAUDE_CONFIG_DIR')}"
            probar(f"C2 {brazo}: CLAUDE_CONFIG_DIR en el entorno y en el registro, y la del padre no pasa", c2)

        def c3():
            _, cwd_v = LA.preparar_sesion(raiz, None, "sesion-vector")
            _, cwd_k = LA.preparar_sesion(raiz, None, "sesion-kg")
            defecto = Path(LA.BANCO_SESIONES) / "cwd"
            ok = (cwd_v == cwd_k == raiz / "cwd" and LA.dentro_de_git(cwd_v) is None
                  and not any(b in parte.lower() for parte in defecto.parts for b in BRAZOS_EN_NOMBRES)
                  and inspect.signature(L21.lanzar).parameters["sesiones"].default == LA.BANCO_SESIONES)
            return ok, f"cwd por defecto: {str(defecto).replace(str(Path.home()), '$HOME')}"
        probar("C3 el cwd: el mismo en los dos brazos, fuera de git, sin el nombre del brazo", c3)

        dentro = LA.REPO_DIR / "data"
        antes = sorted(x.name for x in dentro.iterdir())
        probar("C4 frena con un cwd dentro del repo",
               lambda: (("dentro del repo" in (frena(LA.preparar_sesion, raiz, dentro, "sesion-repo") or ""))
                        and sorted(x.name for x in dentro.iterdir()) == antes
                        and not (raiz / "config" / "sesion-repo").exists(), "data/ del repo"))
        git = Path(td).resolve() / "repo_de_juguete"
        (git / ".git").mkdir(parents=True)
        probar("C4 frena con un cwd dentro de un repo de git de juguete",
               lambda: (("repo de git" in (frena(LA.preparar_sesion, raiz, git / "cwd", "sesion-git") or ""))
                        and not (git / "cwd").exists(), "repo_de_juguete/cwd"))
        lleno = Path(td).resolve() / "cwd_no_vacio"
        lleno.mkdir()
        (lleno / "algo.txt").write_text("x", encoding="utf-8")
        probar("C4 frena con un cwd no vacío",
               lambda: ("no vacío" in (frena(LA.preparar_sesion, raiz, lleno, "sesion-lleno") or ""),
                        "cwd_no_vacio/algo.txt"))
        probar("C4 frena con una carpeta de configuración que ya existe",
               lambda: ("ya existe" in (frena(LA.preparar_sesion, raiz, None, "sesion-a") or ""),
                        "config/sesion-a, otra vez"))

        def c5():
            casa = Path(td).resolve() / "casa"
            config, cwd = LA.preparar_sesion(raiz, None, "sesion-copia")
            base = config / "projects" / LA.slug_proyecto(cwd)
            (base / "sesion-copia" / "tool-results").mkdir(parents=True)
            (base / "sesion-copia.jsonl").write_text('{"de": "la carpeta de configuración"}\n', encoding="utf-8")
            (base / "sesion-copia" / "tool-results" / "r.txt").write_text("resultado de juguete", encoding="utf-8")
            señuelo = casa / ".claude" / "projects" / LA.slug_proyecto(cwd)
            señuelo.mkdir(parents=True)
            (señuelo / "sesion-copia.jsonl").write_text('{"de": "la carpeta personal"}\n', encoding="utf-8")
            out = Path(td).resolve() / "out"
            out.mkdir()
            with mock.patch.dict(os.environ, {"HOME": str(casa)}):
                copia, reg = LA.copiar_sesion(config, cwd, "sesion-copia", out, "PID", True)
                _, reg_init = LA.copiar_sesion(config, cwd, "sesion-copia", out / "no", "PID", False)
            ok = (copia == out / "sesion_PID.jsonl"
                  and copia.read_text(encoding="utf-8") == '{"de": "la carpeta de configuración"}\n'
                  and (out / "tool_results_PID" / "r.txt").read_text(encoding="utf-8") == "resultado de juguete"
                  and reg["copia_transcripcion"] == "sí" and reg["copia_resultados_en_disco"] == "sí"
                  and reg_init["copia_transcripcion"] == "no" and reg_init["copia_resultados_en_disco"] == "no"
                  and not (out / "no").exists())
            return ok, f"{ {k: v for k, v in reg.items() if k != 'carpeta_configuracion'} }"
        probar("C5 la copia lee de la carpeta de configuración, no de la configuración del asistente de la carpeta personal", c5)

    def sha(p) -> str:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    def c6_banco():
        x = LA.archivos_lanzador(LA.__file__)
        ok = (x == [{"ruta": "data/experiment/banco_mcp/agentes/lanzar_agente.py", "sha256": sha(LA.__file__)}]
              and "archivos_lanzador(__file__)" in inspect.getsource(LA.main))
        return ok, f"{[e['ruta'] for e in x]}"
    probar("C6 lanzador, en el banco: un archivo, con su ruta y su sha256", c6_banco)

    def c6_a21():
        x = LA.archivos_lanzador(LA.__file__, L21.__file__)
        ok = (x == [{"ruta": "data/experiment/banco_mcp/agentes/lanzar_agente.py", "sha256": sha(LA.__file__)},
                    {"ruta": "data/experiment/banco_mcp/a2_1/lanzar_agente_a2_1.py", "sha256": sha(L21.__file__)}]
              and "LA.archivos_lanzador(LA.__file__, __file__)" in inspect.getsource(L21.lanzar))
        return ok, f"{[e['ruta'] for e in x]}"
    probar("C6 lanzador, en A2.1: dos archivos, con su ruta y su sha256", c6_a21)


def correr_con(padre: dict, cfg: dict, brazo: str, modo: str, config_cli: Path) -> tuple[dict, dict, bool]:
    """Como `correr`, con la carpeta de configuración de la sesión."""
    with mock.patch.dict(os.environ, padre, clear=True), mock.patch.object(LA, "VENV_VECTOR_DEFAULT", "/sin/uso"):
        env, decl = LA.env_sesion(cfg, brazo, "api", LOG_R1, TAG, modo, config_cli)
        intacto = dict(os.environ) == padre
    return env, decl, intacto


def main() -> int:
    cfg = LA.cargar(LA.CONFIG_AGENTES)
    timeout = cfg["env_por_sesion"]["MCP_TIMEOUT"].split()[0]
    padre = BASICAS | SUCIAS | AWS | NEO4J_OTRAS | {"BANCO_VENV_VECTOR": VENV_DEL_PADRE,
                                                    "MAX_MCP_OUTPUT_TOKENS": MAX_TOKENS, CLAVE: CLAVE_FALSA}
    ramas: list[tuple[str, bool, str]] = []

    def rama(nombre: str, ok: bool, detalle: str = "") -> None:
        ramas.append((nombre, bool(ok), detalle))

    finales = {}
    for modo in ("init", "real"):
        for brazo in ("vector", "kg"):
            env, decl, intacto = correr(padre, cfg, brazo, modo)
            finales[(brazo, modo)] = (env, decl)
            et = f"{brazo}/{modo}"
            pasaron = set(permitidas()) | {"MAX_MCP_OUTPUT_TOKENS", CLAVE}
            esperado = permitidas() | {"MAX_MCP_OUTPUT_TOKENS": MAX_TOKENS, CLAVE: CLAVE_FALSA,
                                       "BANCO_REPO": str(LA.REPO_DIR), "BANCO_LOG_R1": str(LOG_R1),
                                       "BANCO_SESION_TAG": TAG, "MCP_TIMEOUT": timeout, "DISABLE_AUTOUPDATER": "1"}
            if brazo == "vector":
                esperado["BANCO_VENV_VECTOR"] = VENV_DEL_PADRE
            if modo == "init":
                esperado["ANTHROPIC_BASE_URL"] = URL_INIT
            # 1. solo la lista, la clave, MAX_MCP_OUTPUT_TOKENS y lo del lanzador, con sus valores
            rama(f"1 {et}: solo la lista, la clave, MAX_MCP_OUTPUT_TOKENS y lo del lanzador", env == esperado,
                 f"{sorted(env)}")
            # 2. ningún valor de lo que no pasó (BANCO_VENV_VECTOR es del lanzador y toma el valor del padre)
            propias = {"BANCO_VENV_VECTOR"} if brazo == "vector" else set()
            fuera = no_pasan(padre, pasaron | propias)
            rama(f"2 {et}: ningún valor de lo que no pasó", not any(v in env.values() for v in fuera.values()),
                 f"{len(fuera)} del padre no pasaron")
            # 4. el registro
            rama(f"4 {et}: registro con la sesión y las no heredadas, sin clave ni carpeta personal",
                 registro_ok(decl, env, padre, pasaron, [CLAVE_FALSA], propias),
                 f"{len(decl.get('entorno_de_la_sesion') or {})} en la sesión, "
                 f"{len(decl.get('entorno_no_heredadas') or [])} no heredadas")
            rama(f"* {et}: os.environ intacto", intacto)
        # 3. mismos nombres y valores en los dos brazos, salvo BANCO_VENV_VECTOR
        (ev, dv), (ek, dk) = finales[("vector", modo)], finales[("kg", modo)]
        sv = dict(dv.get("entorno_de_la_sesion") or {})
        sk = dict(dk.get("entorno_de_la_sesion") or {})
        rama(f"3 {modo}: mismos nombres y valores en los dos brazos, salvo BANCO_VENV_VECTOR",
             {k: v for k, v in ev.items() if k != "BANCO_VENV_VECTOR"} == ek and "BANCO_VENV_VECTOR" in ev
             and "BANCO_VENV_VECTOR" not in ek
             and {k: v for k, v in dv.items() if k not in ("BANCO_VENV_VECTOR", "entorno_de_la_sesion")}
             == {k: v for k, v in dk.items() if k != "entorno_de_la_sesion"}
             and bool(sv) and {k: v for k, v in sv.items() if k != "BANCO_VENV_VECTOR"} == sk,
             f"{len(ev)} y {len(ek)} variables")

    # NEO4J_URI pasa con su valor; NEO4J_USER y NEO4J_PASSWORD no, ni en el entorno ni en el registro
    rama("* NEO4J_URI pasa con su valor y las otras NEO4J_* no, en los dos brazos y los dos modos",
         all(e.get("NEO4J_URI") == BASICAS["NEO4J_URI"] and not any(k in e for k in NEO4J_OTRAS)
             and (d.get("entorno_de_la_sesion") or {}).get("NEO4J_URI") == BASICAS["NEO4J_URI"]
             and set(NEO4J_OTRAS) <= set(d.get("entorno_no_heredadas") or [])
             and not any(v in json.dumps(d, ensure_ascii=False) for v in NEO4J_OTRAS.values())
             for e, d in finales.values()), f"{len(finales)} sesiones")

    # sin clave en el padre: init pone la inválida; real frena
    sin_clave = {k: v for k, v in padre.items() if k != CLAVE}
    env, decl, _ = correr(sin_clave, cfg, "kg", "init")
    rama("* init sin clave en el padre: la inválida, registrada como presencia",
         env.get(CLAVE) == CLAVE_INVALIDA and env.get("ANTHROPIC_BASE_URL") == URL_INIT
         and (decl.get("entorno_de_la_sesion") or {}).get(CLAVE) == "presente: sí"
         and CLAVE_INVALIDA not in json.dumps(decl) and CLAVE not in (decl.get("entorno_no_heredadas") or [CLAVE]))
    try:
        correr(sin_clave, cfg, "kg", "real")
        frena = False
    except SystemExit:
        frena = True
    rama("* real sin clave en el padre: frena", frena)

    # vía bedrock: pasan las de AWS y la clave no; las credenciales, por presencia
    secretos_aws = [CLAVE_FALSA, AWS["AWS_ACCESS_KEY_ID"], AWS["AWS_SECRET_ACCESS_KEY"], AWS["AWS_SESSION_TOKEN"]]
    for modo in ("init", "real"):
        env, decl, _ = correr(padre, cfg, "kg", modo, via="bedrock")
        pasaron = set(permitidas()) | {"MAX_MCP_OUTPUT_TOKENS"} | set(AWS)
        clave_ok = env.get(CLAVE) == CLAVE_INVALIDA if modo == "init" else CLAVE not in env
        ses = decl.get("entorno_de_la_sesion") or {}
        rama(f"* bedrock/{modo}: pasan las de AWS y la clave no, con CLAUDE_CODE_USE_BEDROCK=1",
             all(env.get(k) == v for k, v in AWS.items()) and env.get("CLAUDE_CODE_USE_BEDROCK") == "1"
             and clave_ok and not any(v in env.values() for v in no_pasan(padre, pasaron).values())
             and ses.get("AWS_SECRET_ACCESS_KEY") == "presente: sí" and ses.get("AWS_REGION") == AWS["AWS_REGION"]
             and ses.get(CLAVE) == ("presente: sí" if modo == "init" else "presente: no")
             and registro_ok(decl, env, padre, pasaron, secretos_aws))

    # A2.1 usa la misma función: el brazo de fragmentos da lo mismo que el brazo vector
    cfg21 = L21.cargar_cfg()
    for modo in ("init", "real"):
        e21, d21, _ = correr(padre, cfg21, "fragmentos_bm25", modo, fn=L21.env_sesion)
        ev, dv = finales[("vector", modo)]
        rama(f"* A2.1 fragmentos_bm25/{modo}: lo mismo que el brazo vector",
             e21 == ev and "entorno_de_la_sesion" in d21
             and d21.get("entorno_de_la_sesion") == dv.get("entorno_de_la_sesion")
             and d21.get("entorno_no_heredadas") == dv.get("entorno_no_heredadas"))

    # control: los chequeos 1, 2 y 4 marcan el entorno de juguete sin filtrar, registrado tal cual
    pasaron = set(permitidas()) | {"MAX_MCP_OUTPUT_TOKENS", CLAVE}
    fuera = no_pasan(padre, pasaron)
    crudo = {"entorno_de_la_sesion": dict(sorted(padre.items())), "entorno_no_heredadas": []}
    rama("* control: los chequeos marcan el entorno sin filtrar",
         padre != finales[("kg", "real")][0] and any(v in padre.values() for v in fuera.values())
         and not registro_ok(crudo, padre, padre, pasaron, [CLAVE_FALSA]),
         f"{len(fuera)} variables que no pasan")

    ramas_c(rama, padre, cfg)

    for nombre, ok, detalle in ramas:
        print(f"{'PASS' if ok else 'FAIL'}  {nombre}" + (f"  [{detalle}]" if detalle else ""))
    n_ok = sum(ok for _, ok, _ in ramas)
    print(f"lista decidida: {list(PERMITIDAS)} | lista del lanzador: {list(getattr(LA, 'ENTORNO_PERMITIDAS', ()))}")
    print(f"TOTAL: {'PASS' if n_ok == len(ramas) else 'FAIL'} ({n_ok} de {len(ramas)} ramas)")
    return 0 if n_ok == len(ramas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
