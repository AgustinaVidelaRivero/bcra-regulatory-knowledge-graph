# Corrida del job de actualización — 2026-09-07

Primera corrida del job. Todo lo de abajo sale de `tabla_deltas.json` y
`mapeo_grafo.json`, en este mismo directorio; este reporte solo los redacta.
La línea base sellada no fue tocada: el job la lee y compara.

---

## 1. `delta_conjunto_desarrollo` — los 5 TOs sobre los que se construyó el método

**3 de 5 cambiaron.** Es hallazgo mayor y va con su
sha anterior y el actual. **No invalida nada**: el trabajo está anclado por
sha, que es precisamente la defensa que el informe ya declara — el grafo se
construyó sobre los PDFs cuyo sha está en el manifiesto, y esos siguen
siendo los mismos archivos en disco. Lo que cambia es qué publica hoy la
fuente.

| TO | id en el grafo | clase | sha anterior → actual | páginas | procedencia anterior → actual |
|---|---|---|---|---|---|
| `capmin` | `cap` | contenido_modificado | `f6ab71be` → **`462a6c93`** | 204 → **206** | portada A 8418, t.o. al 09/04/26 → **portada A 8463, t.o. al 31/07/26** |
| `cladeu` | `cla` | contenido_modificado | `6e7f528d` → **`9717cc82`** | 60 | portada A 8378, t.o. al 19/12/2025 → **portada A 8443, t.o. al 29/05/26** |
| `excbio` | `ext` | sin_cambio | `baea7264` = `baea7264` | 201 | portada A 8307, t.o. al 25/08/2025 |
| `pusf` | `pro` | sin_cambio | `48564cc7` = `48564cc7` | 40 | portada A 8433, t.o. al 06/05/26 |
| `ri_cm` | `ric` | contenido_modificado | `754c888a` → **`1f3c5d3a`** | 59 | pie A 7149, A 7946, A 8156 → **pie A 7149, A 7946, A 8449** |

### `capmin` — mapeo delta → grafo

- **Páginas con texto modificado: 46** de 206 — 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 125, 126, 127, 128, 129, 130, 131, 132, 133 …
- **TO entero:** 2164 nodos / 5461 aristas.
- **Restringido a las páginas modificadas:** **598 nodos / 1394 aristas**, sobre 128 chunks. Ese es el conjunto a revisar.
- **4 de esos nodos están anclados en más de un TO** (`Sujeto_banco`, `Sujeto_banco_comercial`, `Sujeto_entidad_financiera`, `Sujeto_sefyc`): se marcan para **revisar**, nunca para reemplazar por TO.

### `cladeu` — mapeo delta → grafo

- **Páginas con texto modificado: 5** de 60 — 1, 10, 44, 50, 57
- **TO entero:** 510 nodos / 1075 aristas.
- **Restringido a las páginas modificadas:** **18 nodos / 25 aristas**, sobre 6 chunks. Ese es el conjunto a revisar.
- **1 de esos nodo está anclado en más de un TO** (`Sujeto_sefyc`): se marcan para **revisar**, nunca para reemplazar por TO.

### `ri_cm` — mapeo delta → grafo

- **Páginas con texto modificado: 14** de 59 — 4, 7, 8, 10, 11, 12, 13, 15, 16, 18, 23, 24, 27, 37
- **TO entero:** 388 nodos / 955 aristas.
- **Restringido a las páginas modificadas:** **123 nodos / 329 aristas**, sobre 32 chunks. Ese es el conjunto a revisar.
- **1 de esos nodo está anclado en más de un TO** (`Sujeto_banco_comercial`): se marcan para **revisar**, nunca para reemplazar por TO.

---

## 2. `delta_inicial_vs_descarga_original` — desglosado por corpus

Las ventanas son **distintas por corpus** y se reportan por separado: un
agregado único escondería de qué lado viene el material.

| corpus | adquisición | ventana | fuente de la fecha |
|---|---|---|---|
| Conjunto de desarrollo (5) | 2026-05-07/2026-05-10 | ~4 meses | campo fecha_descarga de data/raw/manifiesto.csv (categoría TO_actual) |
| Inventario de escalado (152) | 2026-08-13 | ~3,5 semanas | commit de alta 111ed19 de data/experiment/escalado_prep/descarga_log.json |

| corpus | TOs | sin cambio | contenido modificado | nuevo en índice | desaparecido | no verificable |
|---|---:|---:|---:|---:|---:|---:|
| Conjunto de desarrollo (5) | 5 | 2 | 3 | 0 | 0 | 0 |
| Inventario de escalado (152) | 152 | 144 | 8 | 0 | 0 | 0 |
| **Total** | 157 | 146 | 11 | 0 | 0 | 0 |

- **contenido_modificado** (11): `capmin`, `cladeu`, `ctacte`, `finsec`, `optico`, `ri_cm`, `ri_oc`, `ri_secoexpo`, `ri_tii`, `seggar`, `tasint`

### El índice de hoy

158 entradas → **157 URLs únicas** (1 duplicada descartada), con la misma regla de
deduplicación del inventario sellado.

### Qué anuncia el documento y qué cambió de verdad

De los 11 con contenido modificado, **6 movieron
su procedencia declarada** y **5 no la movieron**: mismo número de
comunicación y misma fecha de texto ordenado, pero distinto sha256.

| TO | páginas modificadas | muestra del cambio |
|---|---:|---|
| `ctacte` | 1 de 86 (pág. 85) | aparece «, “C” 102261 (02/09/26)»; aparece «, “C” 102264 (03/09/26)» |
| `finsec` | 1 de 62 (pág. 62) | aparece «. “A” 8470: Financiamiento al sector público no financiero. Títulos Públicos de la provinc» |
| `ri_secoexpo` | 1 de 21 (pág. 19) | «Informar vacío Fecha de » → «»; aparece «Informar vacío » |
| `seggar` | 1 de 26 (pág. 20) | aparece «/26), “B” 13211 (12/08/26), “B” 13217 (20/08» |
| `tasint` | 1 de 29 (pág. 23) | aparece «/26), “B” 13209 (03/08»; «p, “B” 11971 (13/03/20), “B” 11986 (14/04/20)» → «, “B” 11971 (13/03/20), “B” 11986 (14/04/20),» |

**Consecuencia de método:** un cambio de sha con procedencia quieta es un cambio
que el documento **no anuncia**. Confirma la decisión de diseño de §3: la señal
de cambio tiene que ser el sha del contenido — ni la cabecera HTTP, ni siquiera
lo que el documento declara de sí mismo.

### Qué es y qué no es el diff por página

El diff fino compara **texto extraído**, página contra página. Es un
**localizador**, no un comparador semántico: dice dónde mirar, no qué cambió.
En páginas muy tabulares, el orden en que se extrae el texto puede variar entre
dos generaciones del mismo PDF, de modo que una página puede aparecer como
modificada por reordenamiento de extracción y no por cambio de contenido. El
cambio de sha del documento sí es real en todos los casos; la atribución página
por página es una pista a verificar, y así se declara.

---

## 3. Lectura para la exigencia 6 (validación contra material posterior)

Las fechas de referencia son las **reales**, ancladas en artefactos
(`docs/fe_erratas_fecha_corpus_congelado.md`): **2026-05-07/10** para los 5
del conjunto de desarrollo y **2026-08-13** para los 152. No «marzo».

**Hay material posterior al corte, y está del lado útil.** Los 3 TOs modificados
del conjunto de desarrollo son exactamente los documentos que el
grafo vigente cubre, así que el delta es directamente accionable: se sabe qué
nodos y aristas provienen del texto que cambió, y sobre qué páginas.

Ese material es el candidato concreto para la exigencia 6: contenido
regulatorio incorporado **después** de la construcción del grafo, con el que
se puede probar si el recurso responde bien a normativa que no vio.

Del lado de los 152, 8 TOs con contenido modificado en una ventana de
~3,5 semanas. Un delta chico de ese lado es el resultado **esperable**, no un
fracaso del instrumento: la ventana es corta por construcción. Y aunque
apareciera material, el grafo vigente no cubre esos documentos, así que el
mapeo se declara `fuera_de_alcance` en lugar de fingir alcance.

---

## 4. Cortesía con la fuente y retención

- **Pedidos registrados en la bitácora: 160** = 3 al índice + 157 a PDFs, sobre 157 documentos distintos.
- Más 1 pedido en vuelo al interrumpir, sin línea propia en la bitácora: **161 pedidos reales** al sitio.
- Reintentos por error de red: **1**. Activaciones del modo lento por 503: **0**.
- Ritmo: 1 pedido cada 0,5 s, uno por vez, sin concurrencia.
- Cierre del último segmento: `=== corrida 2026-09-07 — fin === descargados=157 fallidos=0 pedidos=106 pared=215s`

**El runner arrancó 3 veces y los números de arriba suman los
tres segmentos, no el último.** El primero fue `--solo-indice`,
verificación del endpoint antes de bajar nada. El segundo se interrumpió
a propósito y el tercero lo reanudó con `--reanudar`, que saltea lo ya
bajado: por eso el tercero reporta 106 pedidos y no 158. El único
documento pedido dos veces es el que estaba descargándose cuando se
cortó — no tenía observación escrita, así que la reanudación lo volvió a
pedir. Es el caso para el que la idempotencia existe.

La bitácora cruda (`corrida.log`) **no se versiona**: el `.gitignore`
raíz del repositorio excluye `*.log` y esta unidad no lo edita. Sus
estadísticas quedan persistidas en `verificacion_corrida.json`, que sí
se versiona, y de ahí las lee este reporte.

**Retención declarada** (§2.a.5 del diseño): se conservan permanentemente los
artefactos JSON/Markdown de la corrida; los PDFs de esta corrida quedan como
línea base de la siguiente; los PDFs de los TOs con contenido modificado se
conservan de forma permanente, porque son la única copia de una versión que la
fuente ya no sirve. **El job nunca borra**: la purga es manual y explícita.

---

## 5. Qué NO hizo el job

- **No tocó el inventario sellado** ni el manifiesto de desarrollo: los leyó.
- **No tocó el grafo.** Produjo el conjunto de partes afectadas y se detuvo.
  Aplicar la actualización es una release con laudo propio.
- **No instaló nada**: ni cron, ni demonio, ni monitoreo, ni alertas.

