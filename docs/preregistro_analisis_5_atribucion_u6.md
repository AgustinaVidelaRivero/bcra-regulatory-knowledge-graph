# Pre-registro — Análisis de los 5 casos con atribución de fuente (U6)

Mini pre-registro del análisis descriptivo de los 5 casos de U6 con síntoma
que atribuye la fuente del contenido erróneo (cierre del issue #1). El commit
de este archivo sella mi adjudicación causal humana y mi predicción ANTES de
cualquier corrida del verificador sobre estos casos.

## 1. Objeto

Los 5 casos U6-001, U6-003, U6-010, U6-011 y U6-019 quedaron fuera del piloto
sin-gold (`docs/preregistro_piloto_singold_u6.md`, commit 3e507c1) porque su
síntoma atribuye la fuente del contenido erróneo en términos normativos: en
ellos no es separable si el verificador halla la familia causal solo o si el
síntoma la insinúa. Este análisis corre el verificador sobre esos 5 casos con
la MISMA mecánica del piloto — verificador v5.7 congelado, N=1 por caso,
`sintoma_humano` prependido fuera del módulo sellado, condición `n_seen = 0`,
ciego a mi adjudicación — y mide el acuerdo con las mismas métricas de acuerdo
de capa y de causa fina definidas en el §3 del pre-registro del piloto
(3e507c1), con la lectura estricta de primarias múltiples laudada como oficial
en `docs/resultado_piloto_singold_u6.md` §1.

Los 5 casos son exactamente la cohorte
`cohorte_sintoma = "sintoma_con_atribucion_de_fuente"` de la planilla sellada.
Reproducción del conteo:

```
python3 -c "
import json
rows=[json.loads(l) for l in open('data/experiment/exploracion/adjudicacion/u6_adjudicacion_humana.jsonl') if l.strip()]
print(sorted(r['qid'] for r in rows if r.get('cohorte_sintoma')=='sintoma_con_atribucion_de_fuente'))"
```

## 2. Adjudicación causal humana

Mi adjudicación causal, sellada por este commit, previa a toda exposición del
verificador a estos casos:

| qid | causa primaria | causa secundaria |
|---|---|---|
| U6-001 | completitud_kg | alucinacion_agente |
| U6-003 | navegación | completitud_kg |
| U6-010 | contenido_kg | alucinacion_agente |
| U6-011 | contenido_kg | aplicacion_erronea |
| U6-019 | completitud_kg | contenido_kg |

## 3. Predicción pre-registrada

Espero que el acuerdo de capa sea mayor que el del piloto (4/13 ≈ 31%),
porque el síntoma más informativo orienta la investigación del verificador
hacia la familia causal correcta.

Operacionalización honesta para n=5:

- **≥ 3/5 de acuerdo de capa** → señal compatible con la predicción.
- **≤ 2/5 de acuerdo de capa** → sin señal.

NINGÚN resultado con n=5 valida ni invalida nada: este análisis es descriptivo
y su valor es direccional. La rama laudada del piloto (Motor 3 no validado,
adjudicación manual permanente) no se modifica por este análisis bajo ningún
resultado.

Limitación declarada: el diseño no puede separar "el verificador halló la
familia causal solo" de "el síntoma la insinuó" — esa inseparabilidad fue el
motivo de la exclusión original de estos 5 casos y sigue vigente. Lo que este
análisis SÍ mide es si el acuerdo cambia cuando el síntoma es más informativo,
comparando la cohorte con atribución de fuente contra la cohorte síntoma-puro
del piloto.

## 4. Mecánica y costo

- Mecánica idéntica a la del piloto (§5 del pre-registro 3e507c1 y enmienda 01
  en commit e55388c): verificador v5.7 sin modificación alguna, síntoma
  verbatim de la planilla prependido fuera del módulo sellado, N=1, sin acceso
  a mi veredicto ni a la tabla del §2 ni a mis notas. No requiere corrida
  nueva de agente: los 5 casos ya tienen traza.
- Label nuevo `analisis_5_atribucion`, con db propia bajo
  `data/experiment/evaluacion/posthoc_run/` — separada de la db del piloto
  (`singold_piloto_u6`).
- Costo: antes de gastar, la unidad de ejecución debe producir una estimación
  de tokens y costo. Referencia de estimación: ~5/13 del costo del piloto
  (USD 18,28 por 13 casos, `docs/resultado_piloto_singold_u6.md` §6), es
  decir ≈ USD 7. Como referencia de tope rige el remanente del tope laudado
  de la sesión previa (6M entrada / 200K salida, consumidos 3.111.580 y
  108.814 respectivamente). Si la estimación excede lo razonable, la decisión
  de alcance vuelve a mí antes de gastar.
- La corrida es una unidad separada, posterior al commit de este documento.

## 5. Cierre

El commit de este documento sella mi adjudicación causal humana y mi
predicción ANTES de la corrida. Cualquier desviación posterior se documenta
como enmienda separada; este archivo no se edita.
