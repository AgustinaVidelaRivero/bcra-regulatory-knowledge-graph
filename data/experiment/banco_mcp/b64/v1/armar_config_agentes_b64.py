#!/usr/bin/env python3
"""armar_config_agentes_b64.py (b64/v1, B6.4) — La configuración de agentes de B6.4 (config_agentes_b64.json, de esta carpeta), armada
por código y siempre igual desde dos configuraciones de HEAD, controladas por su sha256 antes de escribir nada. USD 0: no llama a ningún
modelo ni levanta nada; solo lee archivos del banco.

Los cuatro brazos (pre-registro de B6.4, `55ee1a5a`, §4), cada campo con su fuente:
  · kg, el brazo del grafo: N7c+, la configuración que adoptó la regla de B2 (H-7 y H-8; nota al pie del pre-registro): el brazo
    `kg_N7c_amp` de n7c/config_agentes_n7c.json, tal cual, con su JSON de MCP, su config del servidor, su bloque y los archivos de su
    servidor. Se controla que difiere del `kg` de B6.3 solo en mcp_config, config_servidor y archivos_servidor, y que su config del
    servidor difiere de la de N7 solo en la versión del servidor (el mismo grafo evaluado, el mismo índice, el mismo denso);
  · kg_n7, el grafo sin corregir (D-10): el brazo `kg` de b63/v2/b2/config_agentes_b63.json, tal cual (el que corrió en B6.3). Se
    controla que es, campo por campo, el `kg_N7` de B2 (n7c/config_agentes_n7c.json);
  · fragmentos_hibrida y fragmentos_denso: los de config_agentes_b63.json, tal cual;
  · lo común (base, versión sellada del CLI, modelo, modo, prompt, corte_R5 y env_por_sesion): lo de config_agentes_b63.json, tal cual.
    Se controla que es lo mismo en n7c/config_agentes_n7c.json.
Cada archivo que nombran los brazos (su JSON de MCP, su config del servidor, su bloque y los archivos de su servidor), la plantilla, la
base y las dos configuraciones fuente se controlan contra su sha256: los de la lista del 241 (n7c/comando_b2_n7c.zsh, renglones 30 a
47, 18 archivos), con el de esa lista, que además se lee del archivo y tiene que ser la de acá; los demás, con el de HEAD
(`80085175`). Frena si alguno no da.
Los roles de los brazos en esta configuración quedan como en sus fuentes («grafo» en kg y en kg_n7); el rol de cada brazo en la
evaluación lo fija la entrada sellada (armar_entrada_B64.py: «grafo» y «grafo_sin_corregir»).

Uso: python3 -I -B armar_config_agentes_b64.py [--verificar] [--controles <json>]
  sin argumentos, escribe config_agentes_b64.json (frena si existe y difiere); con --verificar, la rearma en memoria y la compara;
  con --controles, escribe además cada control de un sha256 (ruta, el esperado, de dónde sale y el que da).
Imprime solo nombres, cuentas y sha256.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b64/v1
BANCO_DIR = AQUI.parents[1]
SALIDA = AQUI / "config_agentes_b64.json"
B63 = "b63/v2/b2/config_agentes_b63.json"
N7C = "n7c/config_agentes_n7c.json"
LISTA_241 = "n7c/comando_b2_n7c.zsh"
RENGLONES_241 = (30, 47)
PREFIJO_REPO = "data/experiment/banco_mcp/"
DE_B63 = ("base", "claude_code_version_sellada", "modelo", "modo_harness", "prompt", "corte_R5", "env_por_sesion")
BRAZOS = (("kg", N7C, "kg_N7c_amp"), ("kg_n7", B63, "kg"), ("fragmentos_hibrida", B63, "fragmentos_hibrida"),
          ("fragmentos_denso", B63, "fragmentos_denso"))
DIFIERE_DE_N7 = {"mcp_config", "config_servidor", "archivos_servidor"}
# La lista del 241 (n7c/comando_b2_n7c.zsh, renglones 30 a 47), relativa al banco.
SHA256_241 = {
    "mcp_kg/familias_nav_rel.py": "1b368333838b3d090b923e7d4b3db31751b7e06946ccc31038b4d41a30f125a7",
    "mcp_kg/servidor_mcp_kg_nav_rel.py": "ab799426a53484a70dd4adc2709acee70c973e6431f32fff3d1f5d69fa944079",
    "mcp_kg/familias_nav_rel_amp.py": "d5e9aff19bd7d26143b0a9b7a7074844d90bac6405a2dd1a30bd119ff46f9022",
    "mcp_kg/servidor_mcp_kg_nav_rel_amp.py": "caf496311442469eafbf54b11320772b1950ff6fadbec6f23a79af23fb4de956",
    "n7c/config_mcp_kg_n7c_evaluado.json": "41b0a6db1950877a23743d100f0ebc3e41e05430c472ad4484f09752e1220d81",
    "n7c/mcp_kg_n7c_evaluado.json": "13a3ae62a542478f2c4bb9261a979de5801ce90fc8fc441b0a695ddd35bb729c",
    "n7c/config_mcp_kg_n7c_amp_evaluado.json": "31b39342c736720e5b002423b66453ff219b40daec8e9b73a461e8f8648ad666",
    "n7c/mcp_kg_n7c_amp_evaluado.json": "ef76623881b82478950319e07d4a790879b89390ce3fb99bc59b6a221d91a109",
    "n7c/config_agentes_n7c.json": "ec1357011f87f4422d17963565de39bd885078dc35133592b39c801f77758fc9",
    "n7c/config_agentes_n7c_humo.json": "3e0b4383a66be2763b773066c6c3604f6090d0f8a401f74ff0b964dad6060994",
    "n7c/correr_n7c.py": "5eec8ab3e3186bd0293d87c5ab42c463e03649be7766c3709e16cd7c27e68455",
    "n7c/lanzar_agente_n7c.py": "3ce01b7388a777ca2eada2972407b9b612108ebbe9b935f4b0aa0e804a07c17b",
    "n7c/entrada_n7c_n3.json": "78568a0215e4eadfc07242f0581b0930bfda39ee408c3e40508d499fea2bed13",
    "n7c/entrada_n7c_humo.json": "3e00a859a558b47a3915f9e75d8334d7e636e2e4f9893cbe4d72fe10e255bfed",
    "n7c/control_servidores_n7c.py": "e5d78a8817b9ca15c9592e301f6a6b053913db14de621177c9de10a2d18e235b",
    "n7c/controlar_humo_n7c.py": "a4892875a9359a09714dad65840e4073c86dd7edc4a65c7534290400a3a57243",
    "n7c/analizar_n7c.py": "93d88a0385d1f16a9fe0dcda694089eb0bf5743696623b26e9f12e7c2128c81b",
    "n7c/lector_anclas_n7c.py": "304eccaa411292ee8d5243ac7c87e83dde760589d1f8bc8bb69a537333e8fe3f",
}
# Los demás, con su sha256 en HEAD (`80085175`), relativos al banco.
SHA256_HEAD = {
    "a2_2/config_agentes_a2_2.json": "fd4ce4e4ce7d4c7cd0550af1ed2ba7d2cbd3d1a2301ee82060ba7d6eba4697c0",
    "agentes/bloque_tools_vector.txt": "d2f853b47caa4cba3bbc6395f1a0546cc562e440b19ea025ed52909943734ba2",
    "b63/v2/b2/config_agentes_b63.json": "eaff32bbad93cb9bc1f9d66ea2c4887cba8268f71007be6bb7158cc97bf0d0c4",
    "mcp_kg/codificador_consultas.py": "5473c49fd4737a4134728f02a86a5a823cd673da035bb3b4a3b4fb94e64ecfb8",
    "mcp_kg/familias_nav.py": "c27bc888224051de2d2959227479e31e5190027078d5fe405ccb1bd5582da22d",
    "mcp_kg/familias_nav_cand.py": "b8a2e828314a54f62928a6351eacedc1cfdd8178f654ba632d6374ac0bb66d0e",
    "mcp_kg/indice_puntos.py": "2474ce5eb43974529d85ca96f3317c81e9565c0af2f6debb95cd383002ce58fe",
    "mcp_kg/servidor_mcp_kg.py": "f8b8de7a587c0f3910b7f1b7e008cdf2030b2e9024850e9815629c03201c29b3",
    "mcp_kg/servidor_mcp_kg_nav.py": "78a2dfaf02c4494232d576a54ec377f58dd01366fbe34fb1681c6272e5b7bb9b",
    "mcp_kg/servidor_mcp_kg_nav_cand.py": "1eaacadb6485c7722b7bacc3e63f68ff34865b870675f9a108e3ac85587ff92a",
    "mcp_vector/bm25_fragmentos.py": "7e26c29c51ae47e394c5bd42424a3319eb45243840846df5f700aebfd82c414d",
    "mcp_vector/config_fragmentos_denso_evaluado_r2b.json": "09b2233d9016dcfb9ad2ca76e8814a0fd73db13dc4f226554de08f486722cfd1",
    "mcp_vector/config_fragmentos_hibrida_evaluado_r2b.json": "a4acb5cff735baf34a849d6dae8327ddfdb209e7647b7ace1454134039949455",
    "mcp_vector/mcp_fragmentos_denso_evaluado.json": "9385cdf2d7d67fb6fd049147b1ff2bf2056d86991e691ca90ed207dc3489540a",
    "mcp_vector/mcp_fragmentos_hibrida_evaluado.json": "7eea9175be78c00c038c3e39a9ee2f77b4fd99fa1df3eb4060faba928a0c331e",
    "mcp_vector/servidor_mcp_vector.py": "cd68f32948bb05fff7357fa6f3f572d3c1db53a5f5ebfbd41c83596e2c081b8b",
    "n7/bloque_tools_fragmentos_n7.txt": "0c42964fbb565ca35b70cae2b7a27ddeb701a2e7f9345871acdf095eeed8b0e6",
    "n7/bloque_tools_kg_n7.txt": "7ced741bffce79c339c741546df10393271e79a40a26341a92c5f47232a1f38c",
    "n7/config_mcp_kg_n7_evaluado.json": "9e9f0ee5b9be4ff41bb2c8cc0c3528892d346197097c6de8b9c5007cb308d8c5",
    "n7/mcp_kg_n7_evaluado.json": "4e3b9ccb062d8eea26049bb8814d62a5807cd683211539394bedb87632c43777",
    "n7/plantilla_prompt_n7.txt": "822aa4e72517bee7a3bd0ed4c80776548622930e54159c16562b874745e771b9",
    "n7c/comando_b2_n7c.zsh": "a600ae5d17df72d16345b8af26f088b9687c81bb07211d0debbc36c62e1a3ef1",
}


class Freno(Exception):
    pass


def sha(rel: str) -> str:
    return hashlib.sha256((BANCO_DIR / rel).read_bytes()).hexdigest()


def leer(rel: str) -> dict:
    return json.loads((BANCO_DIR / rel).read_text(encoding="utf-8"))


def esperado(rel: str) -> tuple[str, str]:
    """(sha256 esperado, de dónde sale) de un archivo del banco: la lista del 241 si está en ella; si no, HEAD."""
    if rel in SHA256_241:
        return SHA256_241[rel], "lista del 241"
    if rel in SHA256_HEAD:
        return SHA256_HEAD[rel], "HEAD 80085175"
    raise Freno(f"{rel}: no tiene un sha256 esperado (ni en la lista del 241 ni en la de HEAD)")


def controlar(rel: str, controles: list) -> str:
    e, fuente = esperado(rel)
    s = sha(rel) if (BANCO_DIR / rel).is_file() else None
    controles.append({"ruta": rel, "sha256_esperado": e, "de": fuente, "sha256": s, "ok": s == e})
    if s != e:
        raise Freno(f"{rel}: da {str(s)[:12]}…, no su sha256 ({fuente}) {e[:12]}…")
    return s


def lista_241_del_archivo(controles: list) -> dict:
    """Los 18 pares de la lista del 241, leídos de n7c/comando_b2_n7c.zsh (renglones 30 a 47), relativos al banco."""
    controlar(LISTA_241, controles)
    renglones = (BANCO_DIR / LISTA_241).read_text(encoding="utf-8").splitlines()[RENGLONES_241[0] - 1:RENGLONES_241[1]]
    out = {}
    for r in renglones:
        s, ruta = r.split()
        if not ruta.startswith(PREFIJO_REPO):
            raise Freno(f"la lista del 241 trae una ruta fuera del banco: renglón {r[:20]}…")
        out[ruta[len(PREFIJO_REPO):]] = s
    return out


def archivos_del_brazo(b: dict) -> list[str]:
    return [b["mcp_config"], b["config_servidor"], b["bloque_tools"], *b["archivos_servidor"]]


def armar() -> tuple[dict, list, dict]:
    controles: list = []
    if lista_241_del_archivo(controles) != SHA256_241:
        raise Freno("la lista del 241 de n7c/comando_b2_n7c.zsh no es la de este armador")
    controlar(B63, controles)
    controlar(N7C, controles)
    b63, n7c = leer(B63), leer(N7C)
    for k in DE_B63:
        if n7c[k] != b63[k]:
            raise Freno(f"lo común de N7c ({k}) no es lo de B6.3")
    brazos = {nuevo: copy.deepcopy((b63 if fuente == B63 else n7c)["brazos"][viejo]) for nuevo, fuente, viejo in BRAZOS}
    kg_n7_igual = brazos["kg_n7"] == n7c["brazos"]["kg_N7"]
    if not kg_n7_igual:
        raise Freno("el brazo kg de B6.3 no es, campo por campo, el kg_N7 de B2")
    difieren = sorted(k for k in set(brazos["kg"]) | set(b63["brazos"]["kg"]) if brazos["kg"].get(k) != b63["brazos"]["kg"].get(k))
    if set(difieren) != DIFIERE_DE_N7:
        raise Freno(f"el brazo de N7c+ difiere del kg de B6.3 en {difieren}, no solo en {sorted(DIFIERE_DE_N7)}")
    mcp = leer(brazos["kg"]["mcp_config"])["mcpServers"]
    if list(mcp) != ["kg"] or not mcp["kg"]["args"][1].endswith("mcp_kg/servidor_mcp_kg_nav_rel_amp.py") \
            or not mcp["kg"]["args"][3].endswith(brazos["kg"]["config_servidor"]) \
            or brazos["kg"]["archivos_servidor"][0] != "mcp_kg/servidor_mcp_kg_nav_rel_amp.py":
        raise Freno("el JSON de MCP de N7c+ no sirve servidor_mcp_kg_nav_rel_amp.py con su config")
    c_amp, c_n7 = leer(brazos["kg"]["config_servidor"]), leer(brazos["kg_n7"]["config_servidor"])
    difiere_cfg = sorted(k for k in set(c_amp) | set(c_n7) if c_amp.get(k) != c_n7.get(k))
    if difiere_cfg != ["version"]:
        raise Freno(f"la config del servidor de N7c+ difiere de la de N7 en {difiere_cfg}, no solo en la versión")
    archivos = sorted({r for b in brazos.values() for r in archivos_del_brazo(b)} | {b63["prompt"]["plantilla"], b63["base"]["ruta"]})
    shas = {r: controlar(r, controles) for r in archivos}
    if shas[b63["prompt"]["plantilla"]] != b63["prompt"]["sha256"] or shas[b63["base"]["ruta"]] != b63["base"]["sha256"]:
        raise Freno("la plantilla o la base no dan el sha256 que declara config_agentes_b63.json")
    for nombre, fuente, viejo in BRAZOS:
        declarados = (b63 if fuente == B63 else n7c)["sha256_de_cada_archivo"]
        for r in archivos_del_brazo(brazos[nombre]):
            if r in declarados and declarados[r] != shas[r]:
                raise Freno(f"{r}: no da el sha256 que declara su configuración fuente")
    cfg = {
        "unidad": "B6.4 — la configuración de agentes de los cuatro brazos de B6.4, armada desde las de B6.3 y de B2 de N7c "
                  "(b64/v1/armar_config_agentes_b64.py)",
        "por_que": ("B6.4 corre el runner de B6.3 con cuatro brazos (pre-registro de B6.4, §4): el del grafo que adoptó la regla de B2 "
                    "(N7c+), el grafo sin corregir (N7, D-10, fuera de Holm), la principal de fragmentos y el denso. Las instrucciones "
                    "del agente, el modelo, el CLI, R5 y los dos de fragmentos son los de B6.3; el brazo del grafo cambia solo en su "
                    "servidor."),
        "base": b63["base"],
        "fuentes": {"config_agentes_b63": {"ruta": B63, "sha256": sha(B63)},
                    "config_agentes_n7c": {"ruta": N7C, "sha256": sha(N7C)},
                    "lista_241": {"ruta": LISTA_241, "sha256": sha(LISTA_241), "renglones": list(RENGLONES_241),
                                  "n_archivos": len(SHA256_241)}},
        "fuentes_de_los_campos": {
            **{k: "config_agentes_b63.json, tal cual (igual en config_agentes_n7c.json)" for k in DE_B63},
            "brazos.kg": "el brazo kg_N7c_amp (N7c+) de config_agentes_n7c.json, tal cual: el del grafo, el que adoptó la regla de B2",
            "brazos.kg_n7": "el brazo kg de config_agentes_b63.json, tal cual: el grafo sin corregir (N7, D-10); igual, campo por campo, "
                            "al kg_N7 de config_agentes_n7c.json",
            "brazos.fragmentos_hibrida": "el de config_agentes_b63.json, tal cual",
            "brazos.fragmentos_denso": "el de config_agentes_b63.json, tal cual",
            "sha256_de_cada_archivo": "los archivos que nombran los brazos, la plantilla y la base, medidos al armar y controlados: "
                                      "los de la lista del 241 con el de esa lista; los demás, con el de HEAD (80085175)"},
        "claude_code_version_sellada": b63["claude_code_version_sellada"], "modelo": b63["modelo"], "modo_harness": b63["modo_harness"],
        "brazos": brazos,
        "prompt": b63["prompt"], "corte_R5": b63["corte_R5"], "env_por_sesion": b63["env_por_sesion"],
        "controles_de_los_brazos": {"kg_n7_igual_al_kg_N7_de_B2": kg_n7_igual,
                                    "kg_difiere_del_kg_de_B63_solo_en": difieren,
                                    "config_servidor_de_kg_difiere_de_la_de_kg_n7_solo_en": difiere_cfg},
        "sha256_de_cada_archivo": {r: shas[r] for r in archivos}}
    resumen = {"controles": f"{sum(c['ok'] for c in controles)} de {len(controles)}",
               "de_la_lista_del_241": sum(1 for c in controles if c["de"] == "lista del 241"),
               "de_HEAD": sum(1 for c in controles if c["de"] == "HEAD 80085175"),
               "kg_n7_igual_al_kg_N7_de_B2": kg_n7_igual, "kg_difiere_del_kg_de_B63_solo_en": difieren}
    return cfg, controles, resumen


def main(argv: list[str]) -> int:
    try:
        cfg, controles, resumen = armar()
    except Freno as ex:
        print(f"FRENO (USD 0): {ex}")
        return 10
    nuevo = json.dumps(cfg, ensure_ascii=False, indent=1) + "\n"
    if "--controles" in argv:
        Path(argv[argv.index("--controles") + 1]).write_text(json.dumps(controles, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if "--verificar" in argv:
        igual = SALIDA.is_file() and SALIDA.read_text(encoding="utf-8") == nuevo
        print(json.dumps(resumen | {"config_agentes_b64_igual_a_la_rearmada": igual}, ensure_ascii=False))
        return 0 if igual else 1
    if SALIDA.exists() and SALIDA.read_text(encoding="utf-8") != nuevo:
        print("FRENO (USD 0): config_agentes_b64.json ya existe y difiere de la rearmada")
        return 10
    SALIDA.write_text(nuevo, encoding="utf-8")
    print(json.dumps(resumen | {"brazos": {b: x["rol"] for b, x in cfg["brazos"].items()},
                                "config_agentes_b64": hashlib.sha256(nuevo.encode("utf-8")).hexdigest()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
