# Fe de erratas del pre-registro ESQ-2 — regla de ranking de la muestra dirigida (§3)

**FIRMADO por la autora — 01/09/2026** — corrección por declaración del pre-registro sellado en
`2240c9c` (`data/experiment/esq/prerregistro_esq2.md`). El pre-registro no se
edita: esta fe de erratas lo corrige ANTES de toda lectura, con la evidencia,
la causa y la regla corregida declaradas.

## 1. Evidencia (verificada por mesa contra disco)

La regla sellada del §3 («ranking determinístico round-robin por disparador y
orden por `chunk_id`») produjo una muestra dirigida degenerada: **36 de las 37
fichas dirigidas caen en actgar** (la restante en adrei). Verificado por la
mesa por recomputo independiente sobre
`data/experiment/esq/cobertura/orden/seleccion_muestra_esq2.json`.

## 2. Causa

El orden por `chunk_id` se coló como criterio de selección: los `chunk_id`
empiezan con el id del TO, actgar es el primer TO en orden alfabético, y sus
candidatos encabezan las cuatro listas de disparadores (29 en d1, 15 en d2,
16 en d3, 10 en d4 = 70 candidatos para 37 cupos, según
`orden/disparadores_esq2.json`). El round-robin por disparador, al tomar
siempre la cabeza de cada lista, consume actgar casi en exclusiva. El
ejecutor implementó la regla sellada literalmente y reportó la degeneración
sin apartarse; el defecto es de la regla, no de la ejecución.

## 3. Qué desarmaba la concentración

1. **La dispersión de TOs del criterio de ESQ-3**: el criterio sellado (§6)
   cuenta «≥3 TOs distintos» sobre ambas muestras; con 36/37 en un solo TO,
   la dirigida casi no puede aportar dispersión de TOs a ninguna familia.
2. **El cegado de origen**: con 39 fichas de actgar sobre 75, de las cuales
   36 son dirigidas, leer una ficha de actgar implica ~92 % de probabilidad
   de que sea dirigida — el origen de muestra queda estadísticamente
   inferible aunque la ficha no lo declare, derrotando el criterio «fichas
   sin marca de origen» del mandato.

## 4. Regla corregida (reemplaza el pasaje del §3 «Si los candidatos exceden 37: …»)

> Si los candidatos exceden 37: ranking determinístico **round-robin anidado
> por disparador × TO** — se recorren los disparadores en el orden declarado
> (d1→d4) y, dentro del turno de cada disparador, los TOs en ciclo por orden
> alfabético de id; en cada par (disparador, TO) se toma el candidato
> pendiente de menor `chunk_id` como desempate; los pares agotados se
> saltean. El resto del §3 queda sin cambio: exclusión de unidades ya
> seleccionadas, reasignación del déficit a la azarosa declarada en el
> reporte, y cuarentena D5.

## 5. Declaración explícita de la ventana

Al momento de esta corrección: **cero fichas leídas, cero fichas
adjudicadas** (verificado por mesa: 75/75 fichas con todas las marcas en
null en `cobertura/fichas/worksheet_fichas_esq2.json`). La **muestra azarosa
queda intacta**: sale de un sorteo independiente (semilla 20260901,
estratificación por TO) y no depende del ranking de la dirigida; no se
regenera. Solo se regeneran la selección dirigida y el worksheet de fichas,
a costo USD 0 (las 762 extracciones ya están persistidas). La dirigida no
genera los números que generalizan (Wilson corre solo sobre la azarosa), por
lo que esta corrección no puede sesgar ningún resultado: es la última
ventana en la que el cambio es inocuo, y se cierra con la primera ficha
leída.

## Firma

Firmado por la autora, 01/09/2026. La regla corregida del §4 es vinculante
para la regeneración de la muestra dirigida y el worksheet de fichas de
U-ESQ-2; el sha del commit de esta fe de erratas es el sello que el mandato
de regeneración referencia.
