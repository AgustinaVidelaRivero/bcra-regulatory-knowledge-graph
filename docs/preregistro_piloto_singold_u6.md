# Pre-registro — Piloto de doble adjudicación sin-gold (U6)

Documento de pre-registro del piloto de doble adjudicación sin-gold (issue #1).
El commit de este archivo sella mi adjudicación causal humana y el diseño del
piloto ANTES de cualquier corrida del verificador sobre estos casos.

## 1. Objeto

Quiero validar si el diagnóstico automático (verificador v5.7, congelado;
Motor 3) coincide con mi adjudicación causal humana en casos reales de intake
sin gold. Uso los 13 casos síntoma-puro de U6, sellados en el commit b337152
(planilla `data/experiment/exploracion/adjudicacion/u6_adjudicacion_humana.jsonl`,
campo `cohorte_sintoma = "sintoma_puro"`). Los 5 casos con atribución de
fuente (U6-001, U6-003, U6-010, U6-011, U6-019) quedan fuera del conteo y se
analizan aparte: en ellos no es separable si el verificador halló la familia
causal solo o si el síntoma la insinuó.

Reproducción del conteo:

```
python3 -c "
import json
rows=[json.loads(l) for l in open('data/experiment/exploracion/adjudicacion/u6_adjudicacion_humana.jsonl') if l.strip()]
print(sorted(r['qid'] for r in rows if r.get('cohorte_sintoma')=='sintoma_puro'))"
```

## 2. Adjudicación causal humana

Mi adjudicación causal, sellada por este commit, previa a toda exposición del
verificador a estos casos:

| qid | causa primaria | causa secundaria |
|---|---|---|
| U6-005 | completitud_kg | alcanzabilidad_kg |
| U6-007 | completitud_kg | alucinacion_agente |
| U6-008 | alcanzabilidad_kg | — |
| U6-009 | estructural_kg | alcanzabilidad_kg |
| U6-012 | estructural_kg | navegación |
| U6-014 | contenido_kg | provenance_imprecisa |
| U6-015 | completitud_kg | — |
| U6-016 | completitud_kg | alucinacion_agente |
| U6-018 | contenido_kg | alucinacion_agente |
| U6-020 | contenido_kg | navegación |
| U6-022 | contenido_kg | alucinacion_agente |
| U6-024 | completitud_kg | alucinacion_agente |
| U6-025 | completitud_kg | alucinacion_agente |

Nota al pie: dos filas (U6-008 y U6-016) fueron adjudicadas tras desempates
determinísticos de solo-lectura sobre `kg.json` que refutaron las hipótesis
pre-registradas originales (sobre-fusión y parse-incorrecto respectivamente);
el resto confirma los pre-diagnósticos sellados en
`data/experiment/exploracion/adjudicacion/notas_adjudicacion_u6.md`.

## 3. Métrica de acuerdo

Mido el acuerdo en dos niveles:

- **Acuerdo de CAPA:** el verificador señala el mismo lado del deslinde que mi
  causa primaria. Capa KG = {`contenido_kg`, `completitud_kg`,
  `alcanzabilidad_kg`, `estructural_kg`, `provenance_imprecisa`}; capa
  agente = {`navegación`, `alucinacion_agente`, `aplicacion_erronea`}.
  `sin_defecto` y `frontera_no_determinada` cuentan como desacuerdo de capa
  salvo coincidencia exacta con mi adjudicación.
- **Acuerdo de CAUSA FINA:** la causa primaria del verificador pertenece al
  conjunto {primaria humana, secundaria humana} de la fila correspondiente de
  la tabla del punto 2.

## 4. Umbral pre-registrado y ramas

- **Capa ≥ 11/13 Y causa ≥ 9/13** → Motor 3 validado pleno para diagnóstico
  con laudo.
- **Capa ≥ 11/13 y causa < 9/13** → Motor 3 validado solo como clasificador
  de capa; la causa fina sigue requiriendo laudo manual.
- **Capa < 11/13** → Motor 3 no validado; adjudicación manual permanente y
  régimen sin-gold declarado no validado en este ciclo.

## 5. Mecánica

- Verificador v5.7 sin ninguna modificación (cluster congelado, hashes
  sellados en `posthoc_run/dev_set/extraccion_h2h_ciclo2.md` §Sello).
- `sintoma_humano` (el comentario verbatim de la planilla
  `u6_adjudicacion_humana.jsonl`) se prepende FUERA del módulo sellado,
  siguiendo el patrón del gate U5.
- El verificador ve síntoma + traza del caso; NUNCA ve mi veredicto, las
  causas de la tabla del punto 2 ni mis notas de revisión.
- N=1 por caso.
- Los 13 casos corren en una sola sesión API junto con la medición N=3 de
  RT-C6-1 (issue #2).

## 6. Costo

Antes de la corrida, la unidad de ejecución debe producir una estimación de
tokens y costo contra el tope de la corrida. Si la estimación excede lo
razonable, la decisión de alcance vuelve a mí antes de gastar.

## 7. Cierre

El commit de este documento sella mi adjudicación humana y el diseño del
piloto ANTES de cualquier corrida. Cualquier desviación posterior se
documenta como enmienda separada; este archivo no se edita.
