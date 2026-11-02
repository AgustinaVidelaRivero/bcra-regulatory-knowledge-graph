"""Regla 6 (c) de S0-1: las 14 unidades de la clase A del mandato, una por una, en la salida con el prototipo: si la
unidad sigue igual, cambia, o la partió E0, y cómo la parte la partición por corte de E1 con la regla 6 (código de
una copia con el prototipo; correr con S0_REGLAS que incluya r6). Solo lectura.

Uso: S0_REGLAS=r6 python -B clase_a_una_por_una.py <dir base> <dir final> <raíz del prototipo> <salida.json>"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
base_d, fin_d, proto, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(proto / "data/experiment/reextraccion_v2/e0_chunking"))
import correr_e0 as CE  # noqa: E402
A = ["cateloc::S2", "snp_mep::S7", "manori::S2", "ri_laft::3.7", "manori::S4", "ri_niif::3.2", "seggar::8.2",
     "ri_oc::3.51", "ri_spi::S0", "ri_psp::SIII", "ri_iepsp::S4", "nmcief::S3::chapeau_seccion", "ri_tsa::3.2", "dmrd::S0"]
out = []
for i in A:
    to = i.split("::")[0]
    fin = {c["id"]: c for c in json.loads((fin_d / f"chunks_{to}.json").read_text(encoding="utf-8"))}
    base = {c["id"]: c for c in json.loads((base_d / f"chunks_{to}.json").read_text(encoding="utf-8"))}
    b = base[i]
    fila = {"id": i, "chars_base": b["chars_propio"]}
    if i in fin:
        c = fin[i]
        partes, info = CE.particionar_por_corte(c)
        fila.update({"en_la_final": "igual" if c == b else "cambia", "chars_final": c["chars_propio"],
                     "e1_particion_r6": [p["chars_propio"] for p in partes] if partes else None,
                     "familia": info.get("familia_items"), "motivo": info.get("motivo")})
    else:
        partes = [c for cid, c in fin.items() if cid.startswith(i + "::parte")]
        fila.update({"en_la_final": "partida_en_E0" if partes else "no_existe",
                     "partes_E0": [c["chars_propio"] for c in partes]})
    out.append(fila)
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for f in out:
    print(f)
