# Scoping de ESQ-1 — cómo correr el test ciego de generalización sin comprar un cero falso

Unidad **U-ESQ-0**. Diagnóstico puro: **USD 0**, cero llamadas a API, cero
implementación, cero cambios de comportamiento. Ningún archivo de extracción
fue tocado. Este documento entrega evidencia y una recomendación; **la decisión
del modo es de la autora**.

Anclas verificadas contra el árbol de trabajo en `HEAD = f986e42`. Todo número
de este documento lleva el archivo:línea o el comando que lo reproduce.

---

## 0. Resumen ejecutivo

1. El esquema está cerrado en **cuatro** capas, no tres. La capa que el mandato
   atribuía solo a los sujetos —el enum duro del tool schema— **enumera también
   los tipos de entidad y los predicados** (§1).
2. El "cero por construcción" es empíricamente **casi** cierto, no
   absolutamente: sobre 8.162 entidades crudas hubo **0** tipos fuera de
   esquema, y sobre 11.827 relaciones crudas hubo **2** predicados fuera de
   enum (0,017 %), ambos variantes léxicas de predicados existentes (§3).
3. **El canal de rechazos es mudo para el propósito de ESQ-1** y el modo (iii)
   queda descartado — a costo cero, antes de gastar un dólar (§3).
4. Pero el corpus ya contiene un **control interno decisivo**: el esquema tiene
   exactamente **un** canal abierto (`sujeto_propuesto`, texto libre) y ese
   canal **disparó 56 veces sobre 39 sujetos distintos**. Los canales cerrados
   dispararon ~0. La diferencia no es que el corpus no tenga contenido fuera de
   esquema: es que los canales cerrados no pueden reportarlo (§3.3).
5. **La premisa de costo del mandato no se sostiene.** Abrir el esquema **no
   invalida nada**: el namespace de la caché local ya incluye el hash del
   prefijo (`cliente_e1.py:56-64`), y la base de datos **hoy ya contiene dos
   namespaces conviviendo intactos**. El costo de "romper el prefijo" es **una
   escritura de caché ≈ USD 0,0125** (§2.5, §5).
6. ESQ-1 sale por **USD 5,91** (banda 5,53–6,66) en el modo recomendado, no por
   USD 15–20. La referencia del plan **no se sostiene como estimación**; sirve
   como tope holgado (§5).
7. **El atajo del rol de alcance absorbe el 83,2 % de las relaciones de sujeto**
   del conjunto de desarrollo (2.914 de 3.504), y **no existe para los 20
   documentos de ESQ** (`ROL_POR_TO` sólo cubre los 5 PDFs del subset). El
   canal de sujetos queda confundido; los canales de tipos y de predicados —la
   medición primaria— **no** (§4.8).
8. **Recomendación de modo: (i), un pase con canal abierto**, precedido de un
   **control de instrumento de USD 0,32** sobre unidades ya pagadas (§6, §8).
9. **Recomendación de lectura: absoluta**, con el canal de sujetos en cuarentena
   y un **brazo pareado de USD 0,16** como su única referencia. Parametrizar los
   roles a mano sería circular: obliga a decidir contenido de esquema antes del
   test que debe informarlo (§7).
10. Paquete: **esperado USD 6,38, tope propuesto USD 9,00** (§5.4). El **único
    factor no medido** de todo el presupuesto es el recargo de salida del modo
    abierto (+10 %, supuesto): la sensibilidad va de USD 5,97 a 7,20 y **no
    cambia la recomendación en ninguna celda** (§5.2.1).
11. Las bandas de lectura se sellan junto con una **regla de normalización** y un
    **orden de ejecución a ciegas**, porque un umbral sellado con procedimiento
    de medición discrecional no es un pre-registro (§7.5).

---

## 1. Mapa de las capas de cierre del esquema

El mandato pedía confirmar o corregir tres capas. **Corrección: son cuatro**, y
la segunda es más amplia de lo que el mandato suponía.

### Capa A — Redacción del prompt (persuasiva, no vinculante)

| Punto | Ancla | Texto |
|---|---|---|
| Declaración general | `prompt_e1.py:54` | «Trabajás con un schema CERRADO y RÍGIDO […] NO inventes tipos. NO inventes predicados. NO inventes sujetos.» |
| Tipos | `prompt_e1.py:56` | «# TIPOS DE ENTIDAD VÁLIDOS (exactamente 6, ningún otro)» |
| Predicados | `prompt_e1.py:78` | «# PREDICADOS VÁLIDOS (exactamente 12, ningún otro)» |
| Sujetos | `prompt_e1.py:97-99` | «SUJETOS: CATÁLOGO CERRADO […] se ELIGE del catálogo de abajo — NO se crea» |
| Regla dura | `prompt_e1.py:134` | «NO inventes tipos ni predicados fuera de las listas. […] Es preferible no extraer algo a forzarlo en una caja equivocada.» |
| Ejemplos negativos | `prompt_e1.py:167-174` | seis ejemplos ❌ de tipos/predicados inventados |

### Capa B — Enum duro en el tool schema (restricción a nivel de API)

**Ésta es la corrección principal al mandato.** El mandato citaba
`prompt_e1.py:21` (que es la *docstring* del módulo, no el enum) y decía que
los sujetos van por enum duro. En realidad el tool schema lleva **cuatro**
restricciones estructurales, y **tres** de ellas son enums:

| Campo | Ancla | Restricción |
|---|---|---|
| `entities[].type` | `prompt_e1.py:219` | `{"type": "string", "enum": list(ENTITY_TYPES)}` — **los tipos también van por enum** |
| `relations[].predicate` | `prompt_e1.py:239` | `{"type": "string", "enum": list(PREDICATES)}` — **los predicados también van por enum** |
| `relations[].sujeto_id` | `prompt_e1.py:241-244` | `enum: list(SUJETOS_CATALOGO)` (70 entradas, catálogo v2.0) |
| `relations[].sujeto_propuesto_padre_sugerido` | `prompt_e1.py:250-253` | `enum: list(SUJETOS_CATALOGO)` |
| `entities[]` | `prompt_e1.py:229` | `"additionalProperties": False` |
| `relations[]` | `prompt_e1.py:258` | `"additionalProperties": False` |
| raíz | `prompt_e1.py:267` | `"additionalProperties": False` |

Fuente única de los tres catálogos: `data/experiment/grafo_v2/code/schema.py:24`
(`ENTITY_TYPES`, 6 entradas), `:41` (`PREDICATES`, 12 entradas), `:94`
(`SUJETOS_CATALOGO`, 70 entradas), importados en `prompt_e1.py:31-38`.

Reproducción:
```bash
python3 -c "import sys; sys.path.insert(0,'data/experiment/grafo_v2/code'); import schema; print(len(schema.ENTITY_TYPES), len(schema.PREDICATES), len(schema.SUJETOS_CATALOGO), schema.CATALOGO_VERSION)"
```
→ `6 12 70 2.0`

**`additionalProperties: False` es una quinta cerradura de hecho**: aunque se
relajaran los enums, el modelo no podría agregar un campo nuevo (p. ej.
`tipo_propuesto`) sin que el schema lo declare. Cualquier modo abierto tiene
que **agregar el campo explícitamente**; no alcanza con quitar el enum.

### Capa C — Validador determinístico (rechaza y registra)

| Motivo | Ancla | Qué mata |
|---|---|---|
| `type_invalido` | `validador_e1.py:140-141` | `etype not in ENTITY_TYPES` |
| `predicado_invalido` | `validador_e1.py:188-189` | `pred not in PREDICATES` |
| `sujeto_id_fuera_de_catalogo` | `validador_e1.py:221-223` | `sujeto_id not in SUJETOS_CATALOGO_SET` |
| `firma_invalida` | `validador_e1.py:244-246`, `:264-267` | firma dominio→rango contra `schema.py:167` (`DOMAIN_RANGE`), vía `schema.py:303` (`is_valid_triple`) |

El rechazo **conserva el elemento crudo íntegro**: `validador_e1.py:64-68`
(`_rechazo(...)` guarda `elemento`) y `:141` guarda el nombre del tipo
propuesto en `detalle` (`f"{ref}: '{etype}'"`). **Sí conserva el nombre.**

### Capa D — Matriz dominio/rango (la que más presión recibe)

`schema.py:167-181` fija `DOMAIN_RANGE`. Ésta no cierra el *inventario* de
tipos sino las *combinaciones* permitidas, y es la capa contra la que el modelo
efectivamente empuja (§3.2).

### Lo que NO está cerrado

`relations[].sujeto_propuesto` (`prompt_e1.py:246-249`) es **texto libre sin
enum**: el único canal abierto del contrato. Su existencia es la prueba de
concepto del modo (i) (§3.3).

---

## 2. Modos viables para ESQ-1

Antes de nada, las **cinco decisiones vinculantes** de
`docs/decisiones_caching_extraccion.md` y cómo aplican:

- **D1** (`decisiones_caching_extraccion.md:13-30`) — prefijo estático cacheado,
  nada variable por chunk antes del breakpoint. **Todos los modos la respetan**:
  el cambio de esquema va dentro del prefijo estable (`prompt_e1.py:272-282`),
  no en el mensaje de usuario. Ningún modo vuelve el `system` a string plano.
- **D2** (`:32-42`) — el costo se calcula con la fórmula de caching. Toda cifra
  de §5 usa `in×P_in + out×P_out + cw×1,25 + cr×0,10`, nunca input+output a
  secas.
- **D3** (`:44-56`) — todo call site nuevo loguea usage con `component`
  distinguible. Cualquier modo de ESQ-1 debe loguear con un component propio
  (p. ej. `esq1_e1_abierto`), no reusar `reextraccion_v2_e1`
  (`cliente_e1.py:157`), para que el gasto de ESQ sea auditable por separado.
- **D4** (`:58-67`) — corridas con prefijo idéntico van **secuenciales**. Afecta
  sobre todo al modo (ii): sus dos pases tienen prefijos **distintos**, así que
  podrían solaparse, pero el modo recomendado es secuencial de todos modos.
  La cuestión abierta *warm-then-parallel* sigue **sin laudo**: no se implementa.
- **D5** (`:69-76`) — evaluación excluida del caching. **No aplica**: ESQ-1 es
  extracción, no evaluación. Ningún modo toca el cuarteto sellado.

### 2.5 La pregunta que decide el costo: ¿se puede aislar la caché?

**Sí, en los tres modos, y no hace falta hacer nada especial para lograrlo: ya
está construido.**

`cliente_e1.py:56-64`:
```python
def namespace_e1() -> str:
    return lc.make_namespace(
        DOMAIN,
        code_ver=f"{CODE_VER}-p{prompt_e1.PREFIJO_HASH}",
        thinking=False,
    )
```
`PREFIJO_HASH` (`prompt_e1.py:287-291`) es el sha256 de `{system, tools}`
serializado canónicamente. La key de caché es
`sha256(namespace + "\n" + request canónico)` (`llm_cache.py:120-127`), y el
namespace se guarda como columna indexada (`llm_cache.py:135`, `:148`).

Consecuencia: **cambiar el prompt o el tool schema cambia el namespace, lo que
PARTICIONA la caché — no la invalida.** Las filas viejas siguen ahí, íntegras y
legibles; simplemente no las alcanza la corrida nueva.

Esto **no es teoría: ya pasó**, y está en disco.

```bash
python3 -c "
import sqlite3
c=sqlite3.connect('data/experiment/reextraccion_v2/e1_extractor/cache/e1_extraccion.db')
for ns,n in c.execute('select namespace, count(*) from cache group by namespace'): print(n, ns)"
```
```
1769 e1_extraccion|cv=e1-extractor-v1-p4793d6152608|think=0
  88 e1_extraccion|cv=e1-extractor-v1-p4dd055a4c5e8|think=0
```

**Dos prefijos distintos conviviendo en la misma base, ambos intactos.** El de
88 filas es la calibración de fase B sobre `pro`; el de 1.769 es la corrida del
corpus. La primera no fue destruida por la segunda.

Aislamiento adicional disponible sin tocar código sellado: `cliente_e1.py:121`
expone `db_path` como parámetro con default, así que ESQ-1 puede además escribir
en **su propio archivo** `.db` (p. ej. `data/experiment/esq/cache/esq1.db`),
dejando la base de producción sin una sola escritura.

#### Y la caché de Anthropic tampoco se invalida

El caché de prefijo de la API es **efímero y de contenido**: un prefijo distinto
es una entrada distinta. Medición sobre la corrida del corpus:

```bash
python3 - <<'PY'
import json, glob, collections
agg=collections.Counter(); n=0; nw=0
for p in glob.glob('data/experiment/reextraccion_v2/corpus_v2/salida/*/extracciones_e1.jsonl'):
    for line in open(p):
        u=(json.loads(line).get('usage') or {})
        if not u: continue
        n+=1
        if u.get('cache_write_tokens',0)>0: nw+=1
        for k in ('input_tokens','output_tokens','cache_write_tokens','cache_read_tokens'): agg[k]+=u.get(k,0)
print(n,'unidades |',nw,'pagaron cache write |',agg['cache_write_tokens'],'tok escritos')
PY
```
```
1769 unidades | 4 pagaron cache write | 39932 tok escritos
```

Sobre **1.769 unidades, el prefijo se escribió 4 veces**: 39.932 / 4 = **9.983
tokens por escritura**, es decir el prefijo completo. O sea que el caché efímero
**ya expiró y se re-pagó tres veces dentro de la propia corrida de producción**.
No existe un "prefijo de producción" persistente que ESQ-1 pueda destruir: el
costo de estrenar un prefijo nuevo es una escritura, **9.983 × 1,25/1e6 = USD
0,0125**, y el corpus entero pagó por ese concepto **USD 0,0499**.

#### El argumento que cierra la cuestión

Aunque el aislamiento no existiera, la premisa igual caería: **ESQ-3 va a
retocar el esquema por diseño** (`docs/plan_tesis.md:336-340`, «decide los
últimos retoques […] emite el laudo de esquema congelado»). El escalado corre
bajo el prefijo que ESQ-3 congele, que por definición **no** es el prefijo
vigente. La caché del prefijo actual no tiene consumidor futuro haga ESQ-1 lo
que haga.

### 2.1 Modo (i) — Un pase con canal abierto  ★ recomendado

Esquema como guía, con una vía explícita para reportar lo que no entra.

**Diseño**: no quitar los enums (perder el enum degrada la extracción y
contamina el conteo con ruido de nomenclatura: el modelo escribiría `aplicaA`
en vez de `aplica_a` y eso se contaría como "tipo nuevo", que es exactamente el
falso positivo espejo del falso cero). En su lugar, **agregar un canal paralelo**,
calcado del patrón `sujeto_propuesto` que ya funciona:

- `entities[].tipo_propuesto` (string libre) + `entities[].type` pasa a
  opcional; mutuamente excluyentes, igual que `sujeto_id`/`sujeto_propuesto`
  (`validador_e1.py:216-220`).
- `relations[].predicado_propuesto` (string libre), mutuamente excluyente con
  `predicate`.
- Una sección nueva en el prefijo que **pida explícitamente** usar esos campos
  cuando el contenido no entre, con la misma redacción que ya probó funcionar:
  «ante la duda, proponé» (`prompt_e1.py:110`).
- `additionalProperties: False` (`:229`, `:258`) obliga a declarar los campos:
  no alcanza con relajar los enums.

**Archivos a tocar**: `prompt_e1.py` (prefijo + tool schema) y `validador_e1.py`
(aceptar y contar los dos campos nuevos). **Ninguno de los dos está en zona
sellada** — el cluster congelado es el del verificador y el cuarteto de
evaluación (`CLAUDE.md` §3); `reextraccion_v2/` no figura en esa lista, pero el
mandato de U-ESQ-0 lo declaró intocable para **esta** unidad. Modo limpio y
recomendado: **no editarlos en su lugar**, sino crear
`data/experiment/esq/prompt_esq1.py` y `validador_esq1.py` que importen los
originales y extiendan el schema, dejando producción byte-intacta.

**¿Rota el prefijo cacheado?** Sí, por construcción — y eso es **deseable**:
`PREFIJO_HASH` cambia, el namespace cambia, la corrida queda **automáticamente
aislada**. Costo de la rotación: **USD 0,0125** (una escritura de prefijo).

**¿Namespace aislado?** **Sí, automático** (`cliente_e1.py:56-64` +
`prompt_e1.py:287-291`), y opcionalmente `.db` propia (`cliente_e1.py:121`).

### 2.2 Modo (ii) — Dos pases (cerrado + descubrimiento)

Pase A idéntico al vigente; pase B con un prompt de descubrimiento que recibe el
mismo chunk **y el esquema**, y pregunta qué contenido normativo del texto no
tiene lugar en los 6 tipos / 12 predicados.

**Ventaja real**: el pase A produce extracción **utilizable** (mismo prefijo que
producción → sus filas de caché sirven al escalado si el esquema no cambiara), y
el pase B no puede degradar la extracción porque no la produce. Además el pase B
puede razonar en prosa, que es más rico que un campo `tipo_propuesto`.

**Desventaja**: cuesta ~1,6× y **el pase B se solapa fuertemente con ESQ-2**,
que ya es análisis cualitativo documento por documento y cuesta USD 0 de
extracción (`plan_tesis.md:329-335`). Pagar un pase LLM de descubrimiento sobre
los documentos de ESQ-1 duplica, con menos profundidad, el trabajo que ESQ-2
hace gratis sobre otros diez.

**Archivos a tocar**: los del modo (i), más un `prompt_esq1_descubrimiento.py`
con su propio tool schema y su propio cliente.

**¿Rota el prefijo?** El pase A **no** (prefijo idéntico → mismo namespace →
sus filas incluso se acumulan con las de producción, sin conflicto: son chunks
nuevos, keys nuevas). El pase B estrena su propio prefijo → su propio namespace.
**Dos namespaces, cero invalidación.**

**¿Namespace aislado?** **Sí**: el pase B automáticamente; el pase A comparte
namespace con producción, lo cual es **inocuo** (sólo agrega filas) y hasta
útil. Si se quisiera aislamiento total del pase A, basta pasarle `db_path`
propio (`cliente_e1.py:121`).

### 2.3 Modo (iii) — Explotar el canal de rechazos en modo cerrado

Correr tal cual está y contar los rechazos `type_invalido` /
`predicado_invalido`.

**Veredicto: DESCARTADO**, y la evidencia para descartarlo **ya está paga** (§3).

**Archivos a tocar**: ninguno. **¿Rota el prefijo?** No. **¿Namespace aislado?**
Comparte el de producción, lo cual es inocuo. **Costo de la corrida**: el mismo
que el modo (i) menos el delta de output. **Señal obtenida: ~cero.**

Aclaración importante: el canal de rechazos **se cosecha gratis en cualquier
modo** —el validador corre igual—, así que su registro debe conservarse siempre.
Lo que se descarta es usarlo como **instrumento principal**.

### 2.4 Modo (iv) — Extracción libre sin esquema *(agregado; evaluado y descartado)*

Correr un prompt de extracción de KG sin esquema alguno y comparar el inventario
de tipos emergentes contra los 6+12 vigentes.

Mide algo distinto y más débil: la nomenclatura espontánea de un LLM, no la
cobertura del esquema sobre el corpus. Produciría decenas de "tipos nuevos" que
son sinónimos de los existentes (`Norma`, `Deber`, `Prohibición`…), inflando el
conteo de deriva con ruido puro y volviendo la lectura de ESQ-3 imposible.
**Descartado por ininterpretable**, no por costo.

---

## 3. ¿Hay señal en el canal de rechazos, a costo cero?

**Sí están persistidos. Sí conservan el nombre. Y la respuesta es que el canal
está MUDO para lo que ESQ-1 necesita.**

### 3.1 Dónde están

`data/experiment/reextraccion_v2/corpus_v2/salida/{cap,cla,ext,pro,ric}/extracciones_e1.jsonl`
— una línea por unidad, con las claves `tool_input_crudo` (**la salida cruda del
modelo, antes del validador**) y `validacion` (con `rechazos`). 1.769 líneas,
~23 MB. Es más de lo que el mandato esperaba: **está el crudo íntegro**, así que
cualquier recuento futuro es re-computable a USD 0.

### 3.2 El conteo

```bash
python3 - <<'PY'
import json, glob, collections
tot=collections.Counter(); n=0
for p in glob.glob('data/experiment/reextraccion_v2/corpus_v2/salida/*/extracciones_e1.jsonl'):
    for line in open(p):
        d=json.loads(line); n+=1
        for r in d.get('validacion',{}).get('rechazos',[]): tot[r['motivo']]+=1
print(n,'unidades'); [print(f'{c:6d}  {m}') for m,c in tot.most_common()]
PY
```
```
1769 unidades
   304  firma_invalida
    10  ref_colgante
     7  entities_o_relations_invalidos
     2  extremo_chunk_ausente
     2  predicado_invalido
     1  punto_fuera_de_admitidos
```

Y sobre el **crudo** (lo que el modelo intentó emitir, antes de cualquier filtro):

| | emitido | fuera de esquema | tasa de fuga |
|---|--:|--:|--:|
| Entidades | 8.162 | **0** | **0,000 %** |
| Relaciones | 11.827 | **2** | **0,017 %** |

Los dos predicados fugados son `'exceptua_restriccion'` (`cap::3.1.6`) y
`'aplicaA'` (`ext::4.4.4`). **Ninguno es semánticamente nuevo**: el primero es un
nombre alternativo de `exceptua`, el segundo es `aplica_a` en camelCase.

**Matiz que corrige levemente al mandato**: el enum del tool schema **no es una
garantía absoluta** —2 elementos se colaron sobre ~20.000—, pero la tasa de fuga
es tan baja, y su contenido tan trivialmente léxico, que a efectos prácticos
*"cero por construcción"* se sostiene. El hallazgo de mesa era correcto.

**Lo que el canal sí mide (y vale la pena llevar a ESQ-3 gratis)**: los 304
`firma_invalida` no son ruido, son **presión estructurada sobre la matriz
dominio/rango**:

| firma que el modelo quiso emitir | veces |
|---|--:|
| `Operacion --aplica_a--> Sujeto` | 142 |
| `Excepcion --aplica_a--> Sujeto` | 54 |
| `Excepcion --exceptua_obligacion--> Restriccion` | 17 |
| `Excepcion --exceptua--> Operacion` | 16 |
| `Restriccion --condiciona--> Operacion` | 9 |
| resto (≈20 firmas más) | 66 |

196 de 304 (64 %) son el mismo pedido: **ampliar el dominio de `aplica_a` de
`{Restriccion, Obligacion}` a `{…, Operacion, Excepcion}`** (`schema.py:170`).
Eso es un hallazgo de esquema, obtenido a USD 0, listo para ESQ-3.

### 3.3 El control interno que decide el diseño

El esquema tiene **exactamente un canal abierto**: `sujeto_propuesto`
(`prompt_e1.py:246-249`, sin enum). Su uso medido:

| canal | forma | disparos |
|---|---|--:|
| `entities[].type` | enum cerrado | **0** de 8.162 |
| `relations[].predicate` | enum cerrado | **2** de 11.827 |
| `relations[].sujeto_id` | enum cerrado | 3.449 usos válidos |
| **`relations[].sujeto_propuesto`** | **texto libre** | **56 usos, 39 distintos, en 29 unidades** |

Muestra: `'Entidades financieras del grupo 1'` (×7), `'Banco de Pagos
Internacionales'`, `'Fondo Monetario Internacional'`, `'Banco Central Europeo'`,
`'Compañía de seguros de crédito a la exportación'`, `'Agentes regulados por la
CNV'`, `'Personas jurídicas que tengan a su cargo la provisión de medicamentos a
pacientes'`.

**Éste es el argumento central del documento.** Sobre el mismo corpus, con el
mismo modelo, en la misma corrida: los canales cerrados reportaron ~0 y el canal
abierto reportó 56. La conclusión no es "el corpus entra en el esquema"; es **"el
instrumento sólo reporta por donde tiene salida"**. Y demuestra que el patrón
del modo (i) —campo libre + instrucción de proponer ante la duda— **ya está
validado empíricamente en este pipeline**, con este prompt y este modelo. No es
un diseño especulativo: es la generalización de un mecanismo que funciona.

**Conclusión de §3**: modo (iii) descartado como instrumento principal (mudo);
su cosecha se conserva igual porque es gratis; y el modo (i) queda respaldado
por evidencia interna en vez de por analogía.

---

## 4. Selección de los 10 + 10 documentos

### 4.1 Contradicción con el plan, reportada

`plan_tesis.md:310-312` dice: «correr el extractor […] sobre **10 documentos
nuevos** del corpus (`data/raw`, selección por semilla declarada y registrada,
disjunta del subset)». **Mandan los archivos** (CLAUDE.md §4.d), y los archivos
dicen otra cosa:

1. **`data/raw` no es el universo operable.** Tiene 3.171 PDFs, de los cuales
   186 son textos ordenados (161 `actuales`, 25 `historicos`), con nombres
   descriptivos (`TO_afectacion_de_activos_en_garantia_actual.pdf`) que **no
   cruzan** contra el inventario. El universo con manifiesto, hashes, inventario
   de unidades y **chunks de E0 ya calculados** es
   `data/experiment/escalado_prep/` (152 TOs, `pdfs/`, `manifest_pdfs.sha256`,
   `inventario_unidades.csv`, `e0_dry/`). **La selección se hace ahí.**
2. **Una selección uniforme sobre `data/raw` produciría un test vacío.** De los
   152 TOs, **62 producen cero unidades de extracción** porque E0 no engancha su
   estructura (`resumen_escalado.md:67-69`). Sortear 10 al azar sobre el universo
   entero daría ~4 documentos con cero chunks: cero llamadas, cero señal, y un
   "cero tipos nuevos" que sería nulo por una razón **distinta** de la que el
   plan quiere descartar.

### 4.2 Universo elegible

**Los 68 TOs con veredicto `digerible`** de `inventario_unidades.csv` — los
únicos sobre los que el extractor puede correr de verdad.

- Disjunción del subset: **verificada**. Los 5 TOs del subset (`pro`, `cla`,
  `ric`, `cap`, `ext`) **no aparecen** en el inventario de 152.
  ```bash
  python3 -c "import csv; ids={r['id'] for r in csv.DictReader(open('data/experiment/escalado_prep/inventario_unidades.csv'))}; print(sorted(ids & {'pro','cla','ric','cap','ext'}))"
  ```
  → `[]`
- Los 68 digeribles: 12 a 613 unidades (mediana 60), 6.340 unidades en total.
- **Limitación estructural que hay que declarar en el reporte de ESQ-1**: los 68
  digeribles son **todos** de categoría `normativa_general`. De los 53 TOs de
  `regimen_informativo`, **cero** son digeribles y sólo 5 producen alguna unidad
  (105 en total). **ESQ-1 no puede testear la generalización del esquema a la
  familia de régimen informativo** — que es justamente donde más se espera que
  falte (formularios, partidas, códigos, plazos de presentación). Esto **no se
  arregla con la selección**: se arregla con las reglas de parseo de E0 (B5.6) o
  se declara como límite de alcance. Es insumo directo de ESQ-3 y de D5/B5.5.

### 4.3 Regla de selección, con semilla declarada

**Semilla: `20260827`.** Algoritmo (determinístico, reproducible, sin estado):

1. Universo = los 68 con `veredicto == "digerible"`, ordenados por `id`
   ascendente (orden canónico, independiente del orden del CSV).
2. Estratificar en 4 cuartiles por `unidades_extraccion` (17 cada uno),
   desempatando por `id`.
3. De cada cuartil, `random.Random(20260827).sample(cuartil_ordenado_por_id, 5)`
   → 20 documentos, con un único objeto `Random` consumido en orden de cuartil.
4. Asignación alternada dentro de cada cuartil: el elemento `j` del cuartil `qi`
   va a ESQ-1 si `(j + qi) % 2 == 0`, si no a ESQ-2. Da 10 y 10, balanceados por
   estrato.

**Por qué estratificado y no uniforme simple.** Con n=10 sobre una población que
va de 12 a 613 unidades, el sorteo uniforme es una lotería de costo y de
cobertura: la misma semilla, uniforme, deja ESQ-1 con 557 unidades (USD 3,93 en
modo cerrado, 4,32 en el modo (i) recomendado — §5.5) y ESQ-2 con 1.498, y puede
fácilmente dar un ESQ-1 de puros documentos chicos —
un test ciego que sólo mira documentos de 20 páginas dice poco sobre la
generalización. El estratificado **garantiza que el test vea documentos grandes
y chicos** y vuelve el costo predecible antes de autorizarlo. Es una decisión de
diseño explícita, no un ajuste post-hoc: se declara acá, antes de correr nada.

El sorteo uniforme con la misma semilla queda registrado en §4.6 como contraste,
para que la decisión sea de la autora.

### 4.4 ESQ-1 — los 10 documentos (762 unidades, 254 páginas)

| id | unidades | pág. | pág. cuerpo | USD E1 (cerrado) | sha256 (16) | título |
|---|--:|--:|--:|--:|---|---|
| `ayccef` | 196 | 47 | 33 | 1,384 | `aa5e3e43a920c904` | Autorización y composición del capital de entidades financieras |
| `expaef` | 165 | 37 | 24 | 1,165 | `9cb78ac9e1c73b21` | Expansión de entidades financieras |
| `opefci` | 77 | 33 | 18 | 0,544 | `1012372fc30d37a9` | Operaciones al contado a liquidar y a término, pases, cauciones, otros derivados y con FCI |
| `adrei` | 70 | 19 | 15 | 0,494 | `44a2eea2e1d374d6` | Agregación de datos sobre riesgos y elaboración de informes |
| `cryl` | 64 | 31 | 24 | 0,452 | `5885e8e62278af86` | Central de registro y liquidación de instrumentos de deuda pública (CRyL) |
| `actgar` | 60 | 18 | 9 | 0,424 | `146631df4b04e084` | Afectación de activos en garantía |
| `prevmi` | 52 | 25 | 15 | 0,367 | `9c47e28525186a7f` | Previsiones mínimas por riesgo de incobrabilidad |
| `lavdin` | 29 | 19 | 19 | 0,205 | `4d88491ec342b513` | Prevención del lavado de activos y del financiamiento del terrorismo |
| `traval` | 28 | 15 | 15 | 0,198 | `6156c3b3a1b44074` | Transportadoras de valores |
| `ctacor` | 21 | 10 | 10 | 0,148 | `1ee99b4bd37ac482` | Cuentas de corresponsalía |
| **total** | **762** | **254** | | **5,38** | | |

### 4.5 ESQ-2 — los otros 10 (1.065 unidades, 301 páginas)

USD 0 de extracción (análisis cualitativo, `plan_tesis.md:329`); las unidades se
listan sólo para dimensionar el trabajo de lectura.

| id | unidades | pág. | sha256 (16) | título |
|---|--:|--:|---|---|
| `ctacte` | 388 | 86 | `06969a2cafb898a7` | Reglamentación de la cuenta corriente bancaria |
| `depinv` | 202 | 53 | `8a85401c3ca9285b` | Depósitos e inversiones a plazo |
| `lingob` | 139 | 24 | `e3c7d7b3e689e8e9` | Lineamientos para el gobierno societario en entidades financieras |
| `rrci` | 77 | 20 | `14d5138378f10cb7` | Lineamientos para la respuesta y recuperación ante ciberincidentes |
| `polcre` | 61 | 32 | `7b94ea5d8d5f99ba` | Política de crédito |
| `gescre` | 59 | 35 | `4998cebcfc397857` | Gestión crediticia |
| `pagjub` | 52 | 16 | `908445f273415d29` | Pago de beneficios de la seguridad social por cuenta de ANSES |
| `retype` | 40 | 13 | `4aed2d774c5952a5` | Pago de retiros y pensiones militares |
| `docvig` | 31 | 14 | `d2d8a0d39d69be8f` | Documentos de identificación en vigencia |
| `snp_atm` | 16 | 8 | `7b346c404ec0fac8` | Sistema Nacional de Pagos - Cajeros automáticos |
| **total** | **1.065** | **301** | | |

**Disjunción ESQ-1 ∩ ESQ-2 = ∅** (verificado). **Disjunción con el subset**:
por §4.2, el universo entero ya es disjunto.

Los 20 IDs, con su sha256 completo, van al archivo de exclusión
`data/experiment/esq/documentos_excluidos_esq.json` **cuando ESQ-1/ESQ-2 se
ejecuten** (`plan_tesis.md:326-328`, `:333-335`). **Esta unidad no lo escribe.**

### 4.6 Contraste: sorteo uniforme, misma semilla

| | unidades | páginas | USD E1 | ids |
|---|--:|--:|--:|---|
| ESQ-1 | 557 | 189 | 3,93 | actgar, adrei, docvig, fclef, fgarcp, gracre, icmecma, pimf, retype, traval |
| ESQ-2 | 1.498 | 400 | 10,58 | afiltr, convca, ctacte, ctavis, depaho, incuca, pagjub, rmrtsd, snp_cec, snp_psp |

### 4.7 Insumos que ya existen (no hay que pagarlos)

- **PDFs**: `data/experiment/escalado_prep/pdfs/<id>.pdf`, con hash en
  `manifest_pdfs.sha256`.
- **Chunks de E0: YA CALCULADOS.** `escalado_prep/e0_dry/<id>/chunks_<id>.json`
  existe para los 20 documentos, con **el mismo formato** que la salida de
  producción (`archivo, chars_completo, chars_propio, flags, herencia, id,
  paginas, sha256_completo, sha256_propio, texto, tipo, titulo, to, unidad`, más
  `rol_bloque` en los mini-chunks). Los conteos coinciden exactamente con
  `inventario_unidades.csv` (196, 165, 77, 70, 64, 60, 52, 29, 28, 21 = 762).
  **E0 no hay que correrlo: USD 0 y cero trabajo.**
  Única diferencia operativa: `e0_dry` anida por TO
  (`<id>/chunks_<id>.json`) mientras producción es plano
  (`chunks_<to>.json`). `comun_e1.cargar_chunks` recibe `e0_dir` como parámetro
  (`comun_e1.py:40`), así que basta un cargador propio en el runner de ESQ —
  **sin tocar `comun_e1.py`**.

### 4.8 El confusor del rol de alcance — medido

`prompt_e1.py:320-328` inyecta el bloque «Alcance de este TO» sólo si
`ROL_POR_TO.get(chunk['archivo'])` devuelve algo, y `ROL_POR_TO`
(`schema.py:106-114`, alimentado por `esquema_v2_clases.json` → `roles`, 5
entradas) **sólo cubre los 5 PDFs del subset**:

```bash
python3 -c "import sys; sys.path.insert(0,'data/experiment/grafo_v2/code'); import schema; print(list(schema.ROL_POR_TO.keys()))"
```
→ los 5 `TO_*_actual.pdf` del subset.

Para los 20 documentos de ESQ el bloque **queda ausente**. En la primera versión
de este documento eso se anotó como un confusor menor. **Medido, no es menor.**

```bash
python3 - <<'PY'
import json, glob, os
ROL={'cap':'Sujeto_rol_alcance_capmin','ext':'Sujeto_rol_entidad_autorizada_exterior',
     'cla':'Sujeto_rol_obligado_a_clasificar_clasificacion','ric':'Sujeto_rol_entidad_comprendida_reginf',
     'pro':'Sujeto_rol_sujeto_obligado_proteccion'}
for p in sorted(glob.glob('data/experiment/reextraccion_v2/corpus_v2/salida/*/extracciones_e1.jsonl')):
    to=os.path.basename(os.path.dirname(p)); ns=nr=npr=0
    for line in open(p):
        for r in ((json.loads(line).get('tool_input_crudo') or {}).get('relations') or []):
            if isinstance(r,dict) and r.get('predicate') in ('aplica_a','ejecuta'):
                ns+=1
                if r.get('sujeto_id')==ROL[to]: nr+=1
                if r.get('sujeto_propuesto'): npr+=1
    print(f'{to}: rel_sujeto={ns} usa_rol={nr} ({100*nr/ns:.1f}%) sujeto_propuesto={npr} ({100*npr/ns:.2f}%)')
PY
```
```
cap: rel_sujeto=1156 usa_rol=1010 (87.4%) sujeto_propuesto=30 (2.60%)
cla: rel_sujeto=287  usa_rol=262  (91.3%) sujeto_propuesto=0  (0.00%)
ext: rel_sujeto=1510 usa_rol=1157 (76.6%) sujeto_propuesto=22 (1.46%)
pro: rel_sujeto=295  usa_rol=236  (80.0%) sujeto_propuesto=0  (0.00%)
ric: rel_sujeto=256  usa_rol=249  (97.3%) sujeto_propuesto=3  (1.17%)
TOTAL: rel_sujeto=3504 usa_rol=2914 (83,2%) sujeto_propuesto=55 (1,57%)
```
**El 83,2 % de todas las relaciones de sujeto del conjunto de desarrollo pasó
por el atajo del rol** (2.914 de 3.504; 1.321 de 1.769 unidades lo usaron al
menos una vez). No es un detalle de borde: es el camino dominante.

Matiz que corrige a la primera versión: los 5 `rol_id` **sí están** en
`SUJETOS_CATALOGO`, o sea que aparecen en el enum del tool schema
(`prompt_e1.py:243-244`) y en el catálogo del prefijo (`prompt_e1.py:114`)
corran o no con el bloque. Pero cada uno está nombrado por su TO
(`Sujeto_rol_alcance_capmin`, `Sujeto_rol_entidad_comprendida_reginf`, …) y
ninguno corresponde a un TO nuevo. Lo que el bloque aporta no es *visibilidad*
del rol sino **la asignación TO→rol**; sin él, para los 20 documentos la
respuesta correcta del modelo es que ninguno de los 5 roles aplica.

**Alcance del confusor** — importa acotarlo bien:

- **Afecta** al canal de sujetos (`sujeto_id` / `sujeto_propuesto` de
  `aplica_a`/`ejecuta`). Ahí el 83,2 % del tráfico pierde su destino por
  defecto y tiene que reubicarse: clase concreta del catálogo,
  `sujeto_propuesto`, u omisión.
- **No afecta** a los canales de tipos de entidad ni de predicados. El bloque
  de rol no menciona ni condiciona `type` ni `predicate`. **La medición
  primaria de ESQ-1 queda limpia.**
- **Efecto de segundo orden, NO VERIFICADO**: sin sujeto disponible el modelo
  podría reestructurar la relación (menos `aplica_a`, más `regula`), corriendo
  la distribución de predicados. Es una hipótesis, no una medición; el brazo D
  de §6.5 la mide.

Consecuencia para la lectura, tratada en **§7**: la tasa de desarrollo de
`sujeto_propuesto` (1,57 %) **no es un baseline comparable** con lo que salga de
ESQ-1, porque se midió con el atajo presente.

**No afecta al caching**: el bloque va en el mensaje de usuario, después del
breakpoint (D1, `decisiones_caching_extraccion.md:13-19`).

---

## 5. Estimación de costo por modo

> **Fe de erratas de la primera versión de este documento.** La revisión de mesa
> encontró que `762 × 0,007744` da 5,9009 y no 5,94. Tenía razón, y la causa era
> un **doble conteo**: la tarifa 0,007744 ya incluía el `cache_write`
> amortizado (0,000028/u, medido sobre el corpus), y §5.3 **volvía a sumar** las
> escrituras de prefijo como línea aparte. Además el control de instrumento se
> presupuestó con ~30 unidades cuando §6 especifica 20+10+10 = **40**. Esta
> sección se rehízo separando la **tarifa marginal** (sin `cache_write`) de las
> **escrituras de prefijo**, que ahora aparecen **exactamente una vez**. Cifras
> corregidas: corrida del modo (i) **USD 5,91** (era 5,94); control **USD 0,32**
> (era 0,25); banda del modo (i) **5,53–6,66** (era «5,5–7,0»); contraste
> uniforme **USD 4,32** (era 4,35). El modo (iii) (5,49) y el modo (ii) (8,49)
> sobreviven sin cambio, pero su descomposición publicada era la incorrecta y
> también se rehízo.

### 5.1 Tarifa y su ancla

`corpus_v2/runner_corpus.py:76-78`:
```python
MODEL_E1 = "claude-haiku-4-5"
P_E1 = dict(precio_in_por_mtok=1.00, precio_out_por_mtok=5.00,
            precio_cache_write_por_mtok=1.25, precio_cache_read_por_mtok=0.10)
```
Misma tarifa en `e1_extractor/runner_faseB_e1.py:40-41`.

### 5.2 Los factores, medidos sobre el `usage` persistido

Comando único que produce todos los factores de §5.3:

```bash
python3 - <<'PY'
import json, glob, collections
agg=collections.Counter(); n=0; nw=0
for p in glob.glob('data/experiment/reextraccion_v2/corpus_v2/salida/*/extracciones_e1.jsonl'):
    for line in open(p):
        u=(json.loads(line).get('usage') or {})
        if not u: continue
        n+=1
        if u.get('cache_write_tokens',0)>0: nw+=1
        for k in ('input_tokens','output_tokens','cache_write_tokens','cache_read_tokens'): agg[k]+=u.get(k,0)
print('unidades', n, '| escrituras de prefijo', nw)
for k in agg: print(f'  {k}: total {agg[k]}  ->  {agg[k]/n:.2f} /unidad')
print('prefijo =', agg['cache_write_tokens']//nw, 'tok/escritura')
PY
```
```
unidades 1769 | escrituras de prefijo 4
  input_tokens: total 2128412  ->  1203.17 /unidad
  output_tokens: total 1761060  ->  995.51 /unidad
  cache_write_tokens: total 39932  ->  22.57 /unidad
  cache_read_tokens: total 17619995  ->  9960.43 /unidad
prefijo = 9983 tok/escritura
```

De acá salen **los cinco factores** que usa todo §5.3:

| factor | valor | origen |
|---|--:|---|
| `t_in` — input variable por unidad | **1.203,17** tok | 2.128.412 / 1.769 |
| `t_out` — output por unidad | **995,51** tok | 1.761.060 / 1.769 |
| `t_cr` — prefijo leído por unidad | **9.960,43** tok | 17.619.995 / 1.769 |
| `PREF` — prefijo, tamaño | **9.983** tok | 39.932 / 4 escrituras |
| escrituras esperadas en 762 u | **2** (cota 3) | 4 × 762 / 1.769 = 1,72 |

**Tarifa marginal por unidad** (sin `cache_write`, que pasa a línea propia):

```
r_marg = 1203,17 × 1,00/1e6  +  995,51 × 5,00/1e6  +  9960,43 × 0,10/1e6
       = 0,00120317          +  0,00497756         +  0,00099604
       = USD 0,00717677 / unidad
```

**Costo de una escritura de prefijo**: `9.983 × 1,25/1e6 = USD 0,012479`.

*Cruce de consistencia*: incluyendo el `cache_write` amortizado (22,57 tok/u),
la tarifa histórica da `0,007205 USD/u`, y `0,007205 × 1.769 = USD 12,7456`,
que es exactamente el costo D2 de la corrida. Los dos caminos cierran; §5.3 usa
el marginal **para no contar las escrituras dos veces** — que es el error que
esta revisión corrige.

Fórmula D2 (`decisiones_caching_extraccion.md:32-42`) en todos los casos.
Rango por TO: 0,005277 (`ext`) a 0,008798 (`ric`) USD/unidad histórico.
**El 69 % del costo es output** (0,004978 / 0,007205) — de ahí que abrir el
canal, que sólo agrega salida, tenga un delta acotado.

#### 5.2.1 El recargo del modo abierto — **SUPUESTO, no medición**

El modo (i) y el control se presupuestan a `0,00771679 USD/u`; el modo (iii) y el
pase A del modo (ii), a la tarifa marginal medida `0,00717677`. La diferencia es
`0,00054002`, y **es el único factor de todo §5 que no está medido**. Su
derivación, que en la revisión 2 no estaba a la vista:

```
r_open − r_marg  =  Δoutput  +  Δprefijo

Δoutput   = t_out × 10 %  × 5,00/1e6 = 995,51 × 0,10 = 99,5512 tok × 5,00/1e6
          = USD 0,0004977558 / u
Δprefijo  = (PREF_OPEN − t_cr) × 0,10/1e6 = (10.383 − 9.960,43) = 422,5732 tok × 0,10/1e6
          = USD 0,0000422573 / u
                                                        ─────────────────
suma                                                    USD 0,0005400131 / u
```
Cierra exacto contra `r_open − r_marg`, y equivale a
`0,0005400131 ÷ (5,00/1e6) = 108,00` tokens de salida por unidad.

**Descarte de transposición de dígitos** (`0,00717677` vs `0,00771679`): la
diferencia **factoriza exactamente** en dos cantidades derivadas de factores
declarados — 99,55 tokens de output y 422,57 tokens de prefijo. Una transposición
de dígitos no factorizaría así. Ambos números son los que entran en la cuenta:
`762 × 0,00771679 + 2 × 0,012979 = 5,9061` (§5.3) y
`762 × 0,00717677 + 2 × 0,012479 = 5,4937`.

*Detalle de precisión, declarado*: el supuesto «+400 tok» es sobre `PREF = 9.983`,
mientras `r_marg` usa el promedio **medido** de lectura `t_cr = 9.960,43` (menor
que `PREF` porque 4 de las 1.769 llamadas pagaron *write* en vez de *read*). Por
eso el Δ de prefijo es 422,57 y no 400. El desfase vale `USD 0,0000000023/u`
— despreciable, pero se declara en vez de disimularse.

**Los dos supuestos, y por qué aplican al modo (i) y al control pero no al (iii)**

| supuesto | valor | estado | por qué |
|---|--:|---|---|
| output +10 % | +99,55 tok/u | **SUPUESTO** | el canal abierto sólo puede **agregar** salida: emite elementos que el modo cerrado hoy no emite. Cuánto agrega **no es medible ex ante** — es, literalmente, lo que ESQ-1 va a averiguar. |
| prefijo +400 tok | 9.983 → 10.383 | **SUPUESTO** | una sección nueva en el prefijo (~2 párrafos) más dos campos en el tool schema con su `description`. |

El **modo (iii) no lleva recargo por construcción**: corre el prompt y el tool
schema **sin un byte de diferencia**, sobre documentos distintos. Su tarifa es la
medida, y la única incertidumbre que le queda es la variación entre documentos.
El **control (§6.1-6.3) y el brazo D (§6.5) sí lo llevan** porque corren
exactamente el mismo modo abierto que ESQ-1 — sería incoherente presupuestarlos a
otra tarifa.

**Ancla del supuesto de output**: no hay medición posible del canal abierto, pero
sí hay una referencia de escala. La variación de output por unidad **entre TOs
del propio corpus** ya es mucho mayor que el recargo supuesto:

```bash
python3 - <<'PY'
import json, glob, os
for p in sorted(glob.glob('data/experiment/reextraccion_v2/corpus_v2/salida/*/extracciones_e1.jsonl')):
    to=os.path.basename(os.path.dirname(p)); o=n=0
    for line in open(p):
        u=(json.loads(line).get('usage') or {})
        if u: o+=u.get('output_tokens',0); n+=1
    print(f'{to}: out/u={o/n:7.1f}  ({100*(o/n)/995.5116-100:+.1f}% vs la media)')
PY
```
```
cap: out/u = 1267.0  (+27.3% vs la media)
cla: out/u = 1010.8  ( +1.5% vs la media)
ext: out/u =  830.7  (-16.6% vs la media)
pro: out/u = 1064.8  ( +7.0% vs la media)
ric: out/u = 1295.2  (+30.1% vs la media)
```
La sola elección de documentos mueve el output entre **−16,6 % y +30,1 %**. El
recargo supuesto (+10 %) queda **dentro** de una banda de incertidumbre que el
presupuesto ya acepta por otra vía. No lo vuelve medido; lo vuelve **de segundo
orden**.

**Sensibilidad — modo (i), 762 unidades** (la pregunta de la mesa: ¿y si el
recargo fuera el doble, o cero?):

| output supuesto | prefijo +0 | prefijo +400 | prefijo +800 |
|---|--:|--:|--:|
| **+0 %** (recargo cero) | USD 5,49 | USD 5,53 | USD 5,56 |
| +5 % | 5,68 | 5,72 | 5,75 |
| **+10 %** (base publicada) | 5,87 | **5,91** | 5,94 |
| **+20 %** (recargo doble) | 6,25 | **6,29** | 6,32 |
| +30 % | 6,63 | 6,66 | 6,70 |

**Sensibilidad del paquete completo** (control 40 u + brazo D 20 u + ESQ-1 762 u,
prefijo +400):

| output supuesto | paquete | vs. tope USD 9,00 |
|---|--:|---|
| +0 % | USD 5,97 | margen 51 % |
| +10 % (base) | USD 6,38 | margen 41 % |
| +20 % (doble) | USD 6,79 | margen 33 % |
| +30 % | USD 7,20 | margen 25 % |

**Conclusión sobre el supuesto**: el rango completo de la grilla va de USD 5,49 a
6,70 para la corrida y de 5,97 a 7,20 para el paquete. **La decisión no depende
del supuesto**: ni en el peor caso de la grilla el modo (i) se acerca al modo (ii)
(8,49) ni al tope (9,00), y el orden de preferencia entre modos no cambia en
ninguna celda. El supuesto mueve la cifra publicada, no la recomendación. Aun
así queda marcado como supuesto, y el **primer dato real** que lo va a corregir
es el propio control de §6 — 40 unidades corridas en modo abierto, antes de ESQ-1,
que devuelven el recargo **medido** y permiten re-presupuestar la corrida grande
antes de lanzarla.


### 5.3 Las cuentas, con todos los factores a la vista

Base: **762 unidades** — la suma de la columna `unidades_extraccion` de los 10
documentos de §4.4 (196+165+77+70+64+60+52+29+28+21 = 762), verificable con:
```bash
python3 -c "
import csv
sel={'ayccef','expaef','opefci','adrei','cryl','actgar','prevmi','lavdin','traval','ctacor'}
r=[x for x in csv.DictReader(open('data/experiment/escalado_prep/inventario_unidades.csv')) if x['id'] in sel]
print(len(r), sum(int(x['unidades_extraccion']) for x in r))"
```
→ `10 762`

**Modo (iii) — cerrado, sin cambios** *(línea de base)*
```
tarifa marginal   r_marg                                = 0,00717677 USD/u
corrida           762 × 0,00717677                      = USD 5,4687
escrituras        2 × 9.983 × 1,25/1e6 = 2 × 0,012479    = USD 0,0250
invalidación      ninguna (prefijo idéntico)            = USD 0,0000
                                                          ─────────
                                                          USD 5,4937  →  5,49
```

**Modo (i) — un pase con canal abierto**  ★
```
supuestos declarados: prefijo +400 tok (sección nueva + 2 campos) → 10.383 tok
                      output +10 % (los elementos fuera de esquema que se agregan)
                      input variable SIN cambio (el chunk es el mismo)

tarifa   r_open = 1203,17 × 1,00/1e6 + 1095,06 × 5,00/1e6 + 10383 × 0,10/1e6
                = 0,00120317         + 0,00547531         + 0,00103830
                = USD 0,00771679 / unidad

corrida           762 × 0,00771679                      = USD 5,8802
escrituras        2 × 10.383 × 1,25/1e6 = 2 × 0,012979   = USD 0,0260
invalidación      NINGUNA (namespace nuevo, §2.5)       = USD 0,0000
                                                          ─────────
                                                          USD 5,9061  →  5,91

banda (única variable movida: el supuesto de output)
   output +0 %  → r = 0,00721903 → 762×r + 0,0260        = USD 5,5269
   output +30 % → r = 0,00871210 → 762×r + 0,0260        = USD 6,6647
                                                          → USD 5,53–6,66
```

**Modo (ii) — dos pases**
```
pase A (cerrado, prefijo idéntico al vigente)
   corrida        762 × 0,00717677                       = USD 5,4687
   escrituras     2 × 0,012479                           = USD 0,0250
                                                           USD 5,4937

pase B (descubrimiento; supuestos: prefijo 7.000 tok, output 400 tok)
   tarifa  r_b = 1203,17×1,00/1e6 + 400×5,00/1e6 + 7000×0,10/1e6
               = 0,00120317       + 0,00200000   + 0,00070000
               = USD 0,00390317 / unidad
   corrida        762 × 0,00390317                       = USD 2,9742
   escrituras     2 × 7.000 × 1,25/1e6 = 2 × 0,00875     = USD 0,0175
                                                           USD 2,9917

MODO (ii) TOTAL = 5,4937 + 2,9917                        = USD 8,4854  →  8,49

banda (única variable movida: output del pase B)
   300 tok → USD 8,1044      800 tok → USD 10,0094       → USD 8,10–10,01
```

**Control de instrumento (§6) — 40 unidades, no 30**
```
§6.1 control positivo A   20 unidades
§6.2 control positivo B   10 unidades
§6.3 control negativo C   10 unidades
                          ──
                          40 unidades

corrida           40 × 0,00771679                        = USD 0,3087
escritura         1 × 10.383 × 1,25/1e6                  = USD 0,0130
                                                          ─────────
                                                          USD 0,3217  →  0,32
```

**Brazo D (§6.5) — 20 unidades con el rol suprimido**
```
mismo prefijo que el control (el rol vive en el mensaje de usuario, no en el
prefijo) → NO paga escritura nueva; el mensaje cambia → son misses, se pagan.

corrida           20 × 0,00771679                        = USD 0,1543  →  0,16
```

### 5.4 Paquete recomendado, con tope

```
control de instrumento §6.1-6.3   40 u                     USD 0,3217
brazo D §6.5                      20 u                     USD 0,1543
ESQ-1 modo (i)                   762 u                     USD 5,9061
                                                           ─────────
esperado                                                   USD 6,3821
margen 41 % (banda alta de output + reintentos por cola)   USD 2,6179
TOPE A AUTORIZAR                                           USD 9,00
```

Cota superior si todo sale por la banda alta: `6,6647 + 0,3217 + 0,1543 = USD
7,14`, holgadamente bajo el tope. `ClienteE1Real` frena solo al tope
(`cliente_e1.py:167-171`, `TopeExcedido`), así que el tope declarado es un freno
real, no una intención.

### 5.5 ¿Se sostiene la referencia de USD 15–20 del plan?

**No como estimación; sí como tope holgado.**

| modo | costo | vs. USD 15–20 |
|---|--:|---|
| (iii) cerrado | 5,49 | 2,73–3,64× por debajo |
| **(i) abierto** ★ | **5,91** (banda 5,53–6,66) | **2,54–3,39× por debajo** |
| (ii) dos pases | 8,49 (banda 8,10–10,01) | 1,77–2,36× por debajo |
| (i) con selección uniforme (§4.6, 557 u) | 4,32 | 3,47–4,63× por debajo |

Ningún modo, con ninguna de las dos reglas de selección, se acerca a USD 15.
Para llegar a 15 habría que elegir a propósito los 10 documentos más grandes
(`lingeef` + `depaho` + `ctacte` + … ≈ 2.900 unidades ≈ USD 22). La cifra del
plan (`plan_tesis.md:309`, anotada como «a estimar antes de autorizar») cumplió
su función de reserva; **la estimación con páginas reales y factores medidos la
baja a ~USD 6**.

---

## 6. Documento de control: cómo se prueba que el modo elegido reporta de verdad

Sin esto, el criterio de lectura del plan (`plan_tesis.md:322-325`) no se puede
cumplir: **un cero no sería interpretable**. El control debe correrse **antes**
de ESQ-1 y su resultado debe quedar sellado antes de mirar el de ESQ-1.

### 6.1 Control positivo A — unidades ya pagadas con contenido fuera de esquema *documentado por el propio modelo* (20 unidades)

El extractor tiene un campo donde **declara por escrito lo que dejó afuera**:
`omisiones_no_prosa` (`prompt_e1.py:162`, `:260-264`). Medición:

```bash
python3 - <<'PY'
import json, glob, os, collections
n=0; por=collections.Counter()
for p in glob.glob('data/experiment/reextraccion_v2/corpus_v2/salida/*/extracciones_e1.jsonl'):
    to=os.path.basename(os.path.dirname(p))
    for line in open(p):
        if (json.loads(line).get('validacion') or {}).get('omisiones_no_prosa'):
            n+=1; por[to]+=1
print(n, dict(por))
PY
```
```
74 {'cap': 33, 'cla': 1, 'ext': 3, 'ric': 37}
```

**74 unidades donde sabemos de antemano, por escrito, que hay contenido que no
se extrajo.** Y lo que hay es homogéneo y nombrable:

- `cap::2.1` — «Tabla de factor k por calificación SEFYC (filas: calificaciones
  1-5, columna valor k…)»
- `cap::2.12.2.8` — «Tabla de ponderadores de riesgo por banda de calificación
  crediticia (AAA/AA- a Inferior a B-/No calificado)…»
- `cap::2.12.3.2` — «Tabla de ponderadores de riesgo con encabezados de
  calificación…»

Una **tabla de ponderadores de riesgo por banda de calificación** no es una
`Restriccion`, ni una `Obligacion`, ni una `Excepcion`, ni una `Operacion`, ni
una `Comunicacion`, ni un `TextoOrdenado`. Es una **tabla de parámetros
regulatorios**, y el esquema v2 **no tiene dónde ponerla**. Sabemos de antemano
que ahí hay algo fuera de esquema, y sabemos **qué**.

**Protocolo**: **20** de las 74, estratificadas por TO (10 `cap`, 8 `ric`,
2 `ext`/`cla`), corridas en el modo elegido.
**Criterio de aprobación, a sellar antes de correr**: al menos **10 de 20**
emiten algún `tipo_propuesto` / `predicado_propuesto`. Por debajo, **el
instrumento está mudo y ESQ-1 no se corre**: se rediseña el modo primero.

### 6.2 Control positivo B — presión conocida sobre la matriz dominio/rango (10 unidades)

164 unidades intentaron `Operacion --aplica_a--> Sujeto` o
`Excepcion --aplica_a--> Sujeto` (§3.2). Tomar **10** de ellas.
**Criterio, a sellar**: **≥7 de 10** vuelven a reportar esa relación (por el
canal abierto, o como `firma_invalida` registrada). Por debajo, el modo abierto
está *tapando* señal que el modo cerrado ya capturaba — resultado que también
hay que conocer antes de gastar.

### 6.3 Control negativo C — que el instrumento no invente (10 unidades)

**10** unidades sin rechazos, sin `sujeto_propuesto` y sin `omisiones_no_prosa`
(extracción limpia en modo cerrado).
**Criterio, a sellar**: **≤1 de 10** emite un tipo propuesto, y si lo emite tiene
que ser inspeccionable a mano y defendible. Un modo abierto que propone tipos en
todas partes convierte a ESQ-1 en un generador de ruido, y su conteo de deriva
sería tan inútil como el cero del modo cerrado. **Sin este control, un número
alto sería tan ininterpretable como un cero.**

### 6.4 Por qué el control se hace sobre los 5 TOs y no sobre documentos nuevos

Los 5 TOs son **conjunto de desarrollo** (`plan_tesis.md`, principio 10) y su
extracción cerrada está **persistida íntegra**, así que cada corrida de control
es un **diff contra una referencia conocida**. Y no consume documentos nuevos:
**no engrosa el archivo de exclusión** ni le quita material a B6.3.

Que el esquema se haya diseñado mirando esos TOs **no invalida el control**: no
se está midiendo generalización acá, se está midiendo si el canal transmite.

### 6.5 Brazo D — condición pareada para el canal de sujetos (20 unidades)

Nace del confusor de §4.8 y lo vuelve medible en vez de conjetural.

**Protocolo**: **20** de las unidades ya corridas en §6.1-6.3, re-corridas en el
mismo modo abierto pero **con el bloque de rol suprimido**, replicando la
condición en que van a correr los 20 documentos de ESQ.

**Qué mide** (dos cosas, ambas contra la salida cerrada persistida de las mismas
unidades, así que el diff es exacto):
1. **Efecto de primer orden**: cuánto se mueve `sujeto_propuesto` al quitar el
   atajo que hoy absorbe el 83,2 % del tráfico de sujetos. Es la única
   referencia pareada legítima contra la cual leer el canal de sujetos de ESQ-1.
2. **Efecto de segundo orden** (hoy NO VERIFICADO, §4.8): si la distribución de
   predicados se corre —menos `aplica_a`, más `regula`— al no haber sujeto
   disponible. Se lee comparando la distribución de predicados del brazo D
   contra la de esas mismas unidades en la corrida original.

**Implementación**: el bloque de rol se arma en `build_user_message`
(`prompt_e1.py:320-328`), o sea **en el mensaje de usuario**. Suprimirlo requiere
una variante de esa función en el módulo propio de ESQ (§8), **sin tocar
`prompt_e1.py`**, y **no rota el prefijo**:
mismo `PREFIJO_HASH`, mismo namespace, sin escritura nueva (D1).

**Costo**: USD 0,16 (§5.3).

**Criterio, a sellar**: el brazo D no tiene umbral de aprobación/rechazo — **es
instrumento de medición, no de decisión**. Su resultado se sella antes de correr
ESQ-1 y se publica junto con él.

---

## 7. Lectura de ESQ-1: ¿baseline pareado o lectura absoluta?

El problema, planteado por la revisión de mesa: la tasa de `sujeto_propuesto` del
conjunto de desarrollo (1,57 % de las relaciones de sujeto, §4.8) se midió **con
el atajo del rol presente**, y los 20 documentos de ESQ van a correr **sin él**.
Comparar una contra otra es comparar dos condiciones distintas. Hay que
resolverlo **antes** de correr.

### 7.1 Opción (a) — Parametrizar el rol para los 20 documentos

**Qué habría que tocar.** `ROL_POR_TO` se arma en `schema.py:106-114` desde
`esquema_v2_clases.json` → clave `roles` (5 entradas hoy). Cada entrada tiene
`id`, `label`, `nivel`, `to`, `miembros` (ids de clases del catálogo) y
`provenance` con `source_doc` y `location` (p. ej. `"Punto 1.1.2"`). Agregar 20
entradas es editar ese JSON.

**¿Rota el prefijo cacheado?** **No, si no se toca `version`.** `_sujetos_prompt()`
(`schema.py:117-161`) construye el catálogo del prefijo a partir de
`_CATALOGO["clases"]` **solamente** (`schema.py:120`), y el prefijo interpola
`CATALOGO_VERSION` (`prompt_e1.py:54`) y `SUJETOS_PROMPT` (`prompt_e1.py:114`),
no los roles. Los roles entran únicamente por el mensaje de usuario
(`prompt_e1.py:320`), después del breakpoint. **Pero**: agregar 20 entradas a un
catálogo versionado y **no** bumpear `version` es exactamente la clase de cambio
silencioso que la Decisión 1 previene (`decisiones_caching_extraccion.md:27-30`);
y si se bumpea, el prefijo **sí** rota (línea 54). El costo de esa rotación es
igualmente trivial (§2.5), así que esto **no es un argumento de costo** —es un
argumento de higiene de versionado.

**Costo en dinero**: **USD 0** de API.

**Costo en trabajo**: definir, para cada uno de los 20 TOs, quién es el
colectivo destinatario y con qué miembros del catálogo se compone, **con
provenance a un punto concreto del documento** (el formato lo exige: las 5
entradas existentes la traen). Son 20 lecturas dirigidas de scope. No es
trabajo mecánico.

**A quién pertenece este trabajo.** A **B5.1**, que lo nombra literalmente:

> `plan_tesis.md:353` — «B5.1 (I, $0) A1: parametrizar runner/E2/ensamblado por
> manifiesto (hoy cableado a 5 TOs; `censo_oraculo[to]` → KeyError;
> `LIMITACIONES_E0` hardcodeado; **`ROL_POR_TO` con 5 keys**); modo E2 sin
> oráculo.»

Y B5 arranca **después** de ESQ-3: `plan_tesis.md:366` — «Condición de arranque:
**ESQ-3 laudado (esquema congelado)**». Hacer (a) ahora **invierte la ruta
crítica declarada** (`plan_tesis.md:563`: `ESQ-1 → ESQ-2 → ESQ-3 → B5`).

**Riesgo nuevo — y es el que decide.** Definir el rol de un TO es decidir, a
mano y **antes del test**, qué sujeto del catálogo es el destinatario colectivo
de ese TO. Para un TO cuyo colectivo **no está en el catálogo**, hay dos salidas
y las dos contaminan:

- **Forzar la entrada más parecida.** Es exactamente lo que el prompt prohíbe
  (`prompt_e1.py:105-108`: «NUNCA una más específica ni una más general»;
  `:110`: «NO fuerces el id más parecido: ante la duda, proponé»), y **suprime
  la señal que ESQ-1 existe para detectar**: el modelo usaría el rol impuesto en
  vez de proponer el sujeto ausente.
- **Crear una entrada nueva de catálogo.** Es **retocar el esquema antes del
  test que debe informar el retoque** — la competencia de ESQ-3
  (`plan_tesis.md:336-340`).

Y el caso no es hipotético: `resumen_escalado.md` §5.1 ya identificó **3 TOs
cuyo título nombra un sujeto ausente del catálogo**, uno de ellos `osapsa`
(«Otros servicios y actividades prestados por sujetos alcanzados», núcleo
detectado «sujetos alcanzados»).

**Veredicto de (a): circular.** Exige tomar a mano, antes de ESQ-1, decisiones
de contenido de la misma naturaleza que ESQ-3 debe tomar después de leerlo.

### 7.2 Opción (b) — Declarar que no hay baseline y leer en absoluto

**Qué se pierde, exactamente.** Una sola cosa: la frase «la tasa de elementos
fuera de esquema en documentos nuevos es N veces la del conjunto de desarrollo».
Ese enunciado comparativo no va a poder hacerse **para el canal de sujetos**.

**Qué NO se pierde** — y es casi todo:

1. **La medición primaria queda intacta.** El bloque de rol no menciona ni
   condiciona `type` ni `predicate` (`prompt_e1.py:320-328`). Los canales de
   tipos de entidad y de predicados —el objeto declarado de ESQ-1: «contar
   cuántas entidades y relaciones nuevas aparecen que el esquema no contempla»,
   `plan_tesis.md:312-314`— **no están confundidos**. El confusor está contenido
   en **uno de los tres canales**.
2. **La salida que el plan pide no requiere baseline.** `plan_tesis.md:315-316`
   pide «tabla de tipos fuera de esquema por documento + **tasa de cobertura
   observada**». Es una tasa **intra-corrida** (elementos fuera de esquema sobre
   elementos emitidos en *esos* documentos), no una comparación contra
   desarrollo.
3. **El criterio de lectura del plan sigue siendo verificable, íntegro.**
   `plan_tesis.md:322-325` dice que un cero no se interpreta como buena
   generalización «hasta haber verificado que el modo de extracción permitía
   reportarlos». Esa verificación es la del **instrumento**, y la hace el control
   de §6.1-6.3 —sobre material de desarrollo, en el mismo modo abierto—
   **independientemente** de la cuestión del baseline. El criterio del plan **no
   depende** de tener una tasa de referencia.
4. **El canal de sujetos no queda a ciegas**: el brazo D (§6.5) le da una
   referencia **pareada** por USD 0,16, sin tocar el catálogo ni invertir la ruta
   crítica.

### 7.3 Recomendación única: **(b), lectura absoluta, con el canal de sujetos en cuarentena y el brazo D como su única referencia**

Fundamento, en una línea: **(a) paga con contaminación del test un baseline que
sólo hace falta para uno de los tres canales, y que el brazo D consigue por USD
0,16 sin tocar nada.** (a) además invierte la ruta crítica y hace trabajo de
B5.1 antes de que su prerrequisito (ESQ-3) exista.

Regla de cuarentena, a aplicar en el reporte de ESQ-1:

- `sujeto_propuesto` de ESQ-1 se reporta en **absoluto** (conteo, distintos,
  en cuántos de los 10 documentos aparece). **Nunca** como tasa contra el 1,57 %
  de desarrollo.
- La **única** comparación admisible del canal de sujetos es contra el brazo D.
- Un sujeto fuera de catálogo es un **hallazgo de catálogo** (clase candidata —
  lo que `resumen_escalado.md` §5 ya anticipa), **no** un hallazgo de tipo de
  entidad: **no cuenta** para los umbrales de §7.4.
- El reporte declara el confusor y su magnitud medida (83,2 %).

### 7.4 Criterios de lectura propuestos para sellar antes de correr

Propuestas para que la autora selle, no decisiones tomadas. Van al pre-registro
de ESQ-1 junto con los umbrales del control (§6.1-6.3).

**Definiciones** (hay que fijarlas antes, porque cada una admite más de una
lectura):

- `T_fam`, `P_fam` — número de **familias semánticas distintas** de tipos y de
  predicados propuestos, **después de normalizar a mano las variantes léxicas**.
  La normalización manual **no es opcional**: el precedente `'aplicaA'` /
  `'exceptua_restriccion'` (§3.2) prueba que sin ella se cuentan como
  «tipos nuevos» cosas que son el mismo predicado escrito distinto. Quién
  normaliza y con qué regla se declara en el pre-registro.
- `spread(f)` — en cuántos de los 10 documentos aparece la familia `f`. Separa
  la idiosincrasia de un documento del hueco sistemático.
- `vol` — elementos propuestos / elementos emitidos totales, en la corrida.
- Los sujetos fuera de catálogo **no entran** en `T_fam` ni en `P_fam` (§7.3).

**Bandas propuestas:**

| banda | condición | lectura |
|---|---|---|
| **NULO del instrumento** | el control §6.1-6.3 **no** pasó en cualquiera de sus tres brazos, **o** no se corrió | **Ningún** resultado de ESQ-1 es admisible — ni el cero ni el distinto de cero. Se rediseña el modo y se vuelve a §6. Implementa `plan_tesis.md:322-325`. |
| **A — el esquema generaliza** | control pasado **y** `T_fam + P_fam ≤ 2` **y** `max spread ≤ 2/10` **y** `vol < 1 %` | ESQ-3 puede congelar el esquema sin agregar tipos. Las 1-2 familias sueltas se documentan como conocidas y no atendidas. |
| **B — el esquema tiene huecos** | control pasado **y** ( alguna familia con `spread ≥ 3/10` **o** `T_fam + P_fam ≥ 3` **o** `vol ≥ 3 %` ) | ESQ-3 se pronuncia **familia por familia** (agregar / renombrar / fusionar / rechazar), cada una con su justificación y su evidencia textual. |
| **C — zona gris** | control pasado y todo lo demás | Sin regla automática: lectura cualitativa obligatoria en ESQ-3, cruzada con ESQ-2. |

`spread ≥ 3/10` es el corte que hace el trabajo pesado: una familia que aparece
en 3 documentos independientes es un hueco del esquema; la que aparece en 1 es,
hasta prueba en contrario, una particularidad de ese documento.

**Canal de sujetos, reporte separado y sin banda**: conteo absoluto, distintos,
`spread`, y comparación **sólo** contra el brazo D. Alimenta al catálogo y a
B5.1, no al laudo de tipos de ESQ-3.

**Advertencia sobre las bandas**: los cortes (2 familias, 3/10, 1 %, 3 %) son
propuestas **sin precedente medido** en este repo — no hay una corrida previa de
esquema abierto de la cual derivarlos. Se ofrecen como valores de arranque
defendibles, y su virtud principal es estar **sellados antes** de ver el
resultado, no ser óptimos. Se marcan como **no calibrados**.

**El umbral no alcanza sin la regla de medición.** Sellar los cortes deja abierta
la discreción de *cómo* se cuenta: la normalización manual que `T_fam`/`P_fam`
exigen puede mover el conteo a través del corte sin tocar el umbral. Esa puerta
la cierra **§7.5**, que se sella en el mismo acto que estas bandas.


### 7.5 Regla de normalización — a sellar ANTES de correr

**El problema.** §7.4 cuenta familias «tras normalización manual de variantes
léxicas». Con el umbral sellado pero el **procedimiento de medición**
discrecional, quien normalice después de ver los resultados puede mover el conteo
de un lado al otro del corte sin tocar el umbral. Es la puerta de atrás clásica
del pre-registro. Se cierra **antes**, con una regla y con un orden de ejecución
que niega la información necesaria para explotarla.

**Quién la ejecuta**: la autora. Es adjudicación, no trabajo de instancia. Está
redactada para que la ejecute ella, y su producto (§7.5.c) es lo que se sella.

#### 7.5.a Criterio operativo: variante léxica vs familia nueva

Se aplican a cada cadena propuesta, **en este orden**; la primera que dispara
decide y las siguientes no se evalúan.

**V1 — Identidad tras normalización de forma.** Transformación mecánica, sin
discreción: separar camelCase con `_`, quitar diacríticos, minúsculas, colapsar
toda corrida de caracteres no alfanuméricos en `_`, podar `_` de los extremos. Si
el resultado **es igual** a la forma normalizada de un elemento vigente
(`ENTITY_TYPES`, `schema.py:24`; `PREDICATES`, `schema.py:41`) → **VARIANTE** de
ese elemento.

**V2 — Núcleo existente + calificador redundante.** La cadena normalizada es
`<E>_<cal>` o `<cal>_<E>` con `E` un predicado vigente, y `cal` nombra un tipo que
**ya está** en el dominio o el rango de `E` según `DOMAIN_RANGE`
(`schema.py:167-181`). Como el calificador no agrega nada que la firma no declare
ya, es el mismo predicado con su firma escrita en el nombre → **VARIANTE** de `E`.
Si `cal` nombra un tipo que **no** está en la firma de `E`, V2 **no dispara**: eso
es un pedido de ampliar la firma, y es hallazgo, no variante.

**V3 — Rechazo pre-declarado.** La cadena figura en la lista cerrada de nombres
que el prompt **ya nombra y rechaza explícitamente**:

| cadena | ancla |
|---|---|
| `Artículo`, `Punto`, `Sección`, `Capítulo`, `Inciso` | `prompt_e1.py:128` (regla 1) y `:167` |
| `regulado_por`, `contiene`, `se_aplica_si` | `prompt_e1.py:168` |
| `EntidadFinanciera`, `Sujeto` | `prompt_e1.py:171` |

→ **`RECHAZO_PREDECLARADO`**: se registra y se reporta aparte, y **no cuenta** en
`T_fam` ni `P_fam`. Fundamento: el esquema ya nombró ese concepto y lo rechazó
con su razón; que reaparezca dice algo sobre **seguimiento de instrucciones**, no
sobre cobertura del esquema. La lista es **cerrada y anterior** —está en un
archivo commiteado— así que no admite ampliación después de ver resultados.

**Por defecto — FAMILIA NUEVA.** Si no dispara V1, V2 ni V3, la cadena es familia
nueva. **El default está puesto en la dirección incómoda a propósito**: sube
`T_fam`/`P_fam`, o sea empuja hacia la banda B («el esquema tiene huecos»). La
regla **no puede fabricar** un veredicto de «generaliza».

**V4 — Fusión entre familias nuevas: sólo mecánica.** Dos familias nuevas se
funden **únicamente** si V1 dispara entre ellas. **Está prohibido fusionar dos
familias nuevas por sinonimia semántica durante el conteo**, aunque sea evidente
que nombran lo mismo: esa fusión baja `T_fam` y es exactamente la dirección que
abre la puerta de atrás. La agrupación semántica **sí** se propone —anotada, sin
efecto sobre el conteo— y la lee ESQ-3 en su lectura cualitativa. La banda se
computa sobre el conteo **sin fusión semántica**.

#### 7.5.a.bis Los dos casos reales del repo, resueltos

Son los únicos dos predicados fuera de enum de toda la corrida del corpus (§3.2).

| cadena | `N(x)` | regla | veredicto | por qué |
|---|---|---|---|---|
| `aplicaA` (`ext::4.4.4`) | `aplica_a` | **V1** | **VARIANTE de `aplica_a`** | camelCase → `aplica_a`, que está en `PREDICATES` (`schema.py:45`). Mecánico, sin juicio. |
| `exceptua_restriccion` (`cap::3.1.6`) | `exceptua_restriccion` | **V2** | **VARIANTE de `exceptua`** | núcleo `exceptua` (`schema.py:47`); calificador `restriccion`; `DOMAIN_RANGE["exceptua"] = ({"Excepcion"}, {"Restriccion"})` (`schema.py:173`) — el calificador nombra el rango que la firma ya declara. No agrega semántica. |

**Contraste que prueba que la regla discrimina** (no colapsa todo a «variante»):
un hipotético `exceptua_operacion` **no** sería variante. `Operacion` no está ni
en el dominio ni en el rango de `exceptua` (`schema.py:173`), así que V2 no cierra
y la cadena cae al default → **FAMILIA NUEVA**. Eso es correcto: sería el modelo
pidiendo que las excepciones puedan exceptuar operaciones, que es precisamente el
tipo de hallazgo que ESQ-1 debe capturar. Verificación de las cuatro cadenas:

```
aplicaA               -> V1  VARIANTE de aplica_a
exceptua_restriccion  -> V2  VARIANTE de exceptua        (cal 'restriccion' ∈ firma)
exceptua_operacion    -> --  FAMILIA NUEVA               (cal 'operacion' ∉ firma)
regulado_por          -> V3  RECHAZO_PREDECLARADO        (prompt_e1.py:168)
```

#### 7.5.b Orden de ejecución — el blindaje

El blindaje no es voluntad, es **negación de información**: se normaliza sin ver
todavía el efecto sobre las bandas.

| paso | qué | quién |
|---|---|---|
| **0** | Sellar, fechadas y hasheadas: las bandas de §7.4, esta regla, y los resultados del control §6.1-6.3 y del brazo D §6.5. | autora |
| **1** | Correr ESQ-1. Un script extrae **sólo el conjunto de cadenas propuestas distintas**, ordenado alfabéticamente y **deduplicado**: sin frecuencias, sin documento de origen, sin `spread`, sin volumen, sin porcentajes. Salida determinística y re-derivable por un tercero desde la corrida. | script |
| **2** | Aplicar V1→V2→V3→default→V4 a esa lista pelada, produciendo el mapeo cadena → familia y el registro de §7.5.c. | **autora** |
| **3** | **Sellar el mapeo** (escribirlo, hashearlo, fecharlo) **antes de generar un solo conteo**. | autora |
| **4** | Recién ahí computar `T_fam`, `P_fam`, `spread`, `vol` y leer las bandas de §7.4. | script |

Lo que hace el trabajo es el **paso 1**: sin frecuencias ni `spread`, en el paso 2
es imposible saber qué decisión de fusión mueve el resultado a través del corte.

*Límite declarado*: el blindaje no es hermético —la autora conoce el corpus y
podría intuir qué cadena es frecuente—. Lo que elimina es la lectura **directa**
del efecto de cada decisión sobre la banda, que es el mecanismo por el que la
puerta de atrás opera en la práctica. Se declara como mitigación, no como
garantía.

#### 7.5.c Registro auditable

Una fila por **cadena distinta**, en
`data/experiment/esq/normalizacion_esq1.json`, sellado en el paso 3:

| campo | contenido |
|---|---|
| `cadena_propuesta` | verbatim, tal como la emitió el modelo |
| `forma_normalizada` | salida de la transformación de V1 |
| `regla_aplicada` | `V1` / `V2` / `V3` / `DEFAULT` / `V4` / `EXCEPCION_ADJUDICADA` / `NO_COMPUTABLE` |
| `familia_asignada` | id del elemento vigente, o `NUEVA::<slug>`, o `RECHAZO_PREDECLARADO` |
| `justificacion` | una línea. **Obligatoria con cita** para V2 (la entrada de `DOMAIN_RANGE` y su línea de `schema.py`) y para toda `EXCEPCION_ADJUDICADA` |
| `agrupacion_semantica_sugerida` | opcional, **sin efecto sobre el conteo**; insumo cualitativo de ESQ-3 |
| `fecha`, `adjudica` | fecha y `autora` |

Con eso, un tercero puede recorrer el registro fila por fila, re-aplicar V1-V3
mecánicamente y verificar cada desvío.

#### 7.5.d Lo que la regla no resuelve

Tres salidas, todas registradas, ninguna silenciosa:

1. **Cadena que ninguna regla alcanza** → **FAMILIA NUEVA** por default (§7.5.a).
   Es el caso normal, no una excepción: el default existe para eso, y empuja
   hacia la banda incómoda.

2. **La regla dispara pero la autora juzga que da el resultado equivocado** (V2
   cierra sobre algo que ella lee como genuinamente nuevo, o V1 acierta por
   coincidencia) → **`EXCEPCION_ADJUDICADA`**. Puede apartarse de la regla, con
   dos condiciones que hacen que el desvío cueste lo que tiene que costar:
   - queda registrada con su justificación en la misma fila;
   - **la banda se computa dos veces**, con la regla tal como está escrita y con
     la excepción aplicada. **Si las dos lecturas caen en bandas distintas, la
     banda no se resuelve automáticamente: pasa a lectura cualitativa en ESQ-3**,
     que debe pronunciarse sobre la excepción con la evidencia textual a la
     vista. Una excepción nunca puede **mover** el veredicto por su cuenta: sólo
     puede **escalarlo** a lectura humana.
   La misma regla de doble cómputo se aplica a V3: el reporte publica `T_fam`
   con y sin los `RECHAZO_PREDECLARADO` plegados, y si difieren de banda, se
   escala igual.

3. **Cadena que no es un tipo ni un predicado** (fragmento de oración, cadena
   vacía, ruido) → **`NO_COMPUTABLE`**: se registra, se excluye de `T_fam`/`P_fam`
   y **se reporta su conteo por separado**. No es un descarte cosmético: un
   `NO_COMPUTABLE` alto es en sí mismo un hallazgo **sobre el instrumento** —el
   canal abierto está produciendo ruido—, que es justo lo que el control negativo
   §6.3 mide. Umbral propuesto, a sellar: si `NO_COMPUTABLE` supera el **20 %**
   de las cadenas distintas, el resultado de ESQ-1 se lee como **NULO del
   instrumento** (§7.4), igual que si el control hubiera fallado.

**Estado de esta regla**: propuesta, **no calibrada** —no hay corrida previa de
esquema abierto en este repo contra la cual haberla probado; lo único contra lo
que está probada son los dos casos reales de §7.5.a.bis y el contraste
`exceptua_operacion`—. Su virtud es ser **anterior y auditable**, no ser óptima.

---

## 8. Recomendación de modo

### Modo (i) — un pase con canal abierto, precedido del control de §6

**Por qué**

1. **Es el único modo con evidencia interna a favor.** El patrón —campo de texto
   libre, mutuamente excluyente con el enum, más la instrucción «ante la duda,
   proponé»— **ya está en producción y ya funciona**: `sujeto_propuesto` disparó
   56 veces sobre 39 sujetos distintos mientras los canales cerrados disparaban 0
   y 2 (§3.3). No hay que apostar a que el diseño funcione: hay que replicarlo.
2. **Mantiene los enums, así que no compra ruido.** Quitar el enum haría que
   `aplicaA` se contara como tipo nuevo. El canal paralelo separa limpiamente
   «esto no entra en ninguna caja» de «esto entra pero lo escribí distinto».
3. **Es barato y el aislamiento es automático.** USD 5,91 esperado; el namespace
   se particiona solo por `PREFIJO_HASH` (§2.5). **Costo de invalidación: cero**,
   verificado contra dos namespaces conviviendo hoy en la base.
4. **Cosecha el modo (iii) gratis de todos modos**: el validador corre igual, así
   que ESQ-1 entrega *además* la tabla de `firma_invalida` sobre documentos
   nuevos, comparable contra la del corpus (§3.2).
5. **Produce extracción reutilizable**: la salida del canal cerrado es válida y
   sirve como insumo del escalado si ESQ-3 no la invalida.

**Riesgo y su mitigación**: el canal abierto podría inflar el conteo con
propuestas espurias. Lo cubre el control negativo (§6.3), que es **parte de la
recomendación**, no un extra.

### Las alternativas, y qué se pierde

| modo | costo | recomendación |
|---|--:|---|
| **(i) canal abierto** | **5,91** | ★ **recomendado** |
| (ii) dos pases | 8,49 | Defendible. +44 % de costo, y el pase de descubrimiento **duplica a ESQ-2**, que hace lo mismo con más profundidad y a USD 0 sobre otros 10 documentos. Elegirlo sólo si se quiere que **los mismos** documentos tengan lectura cuantitativa y cualitativa. |
| (iii) canal de rechazos | 5,49 | **Descartado.** Mudo, probado a costo cero (§3). Su cosecha se conserva igual en cualquier modo. |
| (iv) extracción libre | ~6 | **Descartado.** Ininterpretable: mide nomenclatura espontánea, no cobertura. |
| **no correr el control** | −0,32 | **Descartado.** Sin él, `plan_tesis.md:322-325` no se puede cumplir y ESQ-1 no es leíble en ninguno de sus resultados posibles. |

### Paquete a autorizar

```
tope USD 9,00   (esperado 6,38 = control 0,32 + brazo D 0,16 + corrida 5,91)
orden: control §6.1-6.3 → brazo D §6.5 → sellar ambos → ESQ-1 → ESQ-2 → ESQ-3
```

---

## 9. Decisiones que quedan para la autora

Ninguna de éstas la toma esta unidad.

1. **El modo.** Recomendado (i); (ii) es defendible al costo de +44 % y de
   solaparse con ESQ-2.
2. **Baseline pareado (a) vs lectura absoluta (b)** (§7). Recomendado (b) + brazo
   D. Elegir (a) implica hacer trabajo de B5.1 antes de su prerrequisito y
   tomar 20 decisiones de contenido que pueden suprimir la señal del test.
3. **La regla de selección**: estratificada por cuartiles (§4.3-4.5,
   recomendada) o uniforme simple (§4.6). Ambas con semilla `20260827`.
4. **La semilla misma**: `20260827` es propuesta, no laudada.
5. **El tope**: USD 9,00 propuesto (esperado 6,38; cota alta 7,14).
6. **Dónde vive el código de ESQ-1**: módulos nuevos bajo `data/experiment/esq/`
   que extienden los originales (recomendado, deja producción byte-intacta) o
   edición in situ de `prompt_e1.py`/`validador_e1.py`.
7. **Los umbrales del control** (§6.1: 10/20; §6.2: ≥7/10; §6.3: ≤1/10), **las
   bandas de lectura** (§7.4: 2 familias, spread 3/10, vol 1 %/3 %) y **la regla
   de normalización con su orden de ejecución** (§7.5, incluido el corte de
   `NO_COMPUTABLE` en 20 %). Todos son propuestas **no calibradas** y se sellan
   **en un mismo acto, antes** de correr. Sellar las bandas sin la regla deja el
   pre-registro abierto por el lado de la medición.
7bis. **Si acepta el recargo supuesto de +10 % de salida** (§5.2.1) o prefiere
   presupuestar por la banda alta. Alternativa disponible sin costo: el control
   de §6 devuelve el recargo **medido** sobre 40 unidades **antes** de lanzar la
   corrida grande, así que la cifra puede re-computarse con dato real en vez de
   supuesto.
8. **Qué hacer con el límite de `regimen_informativo`** (§4.2): ESQ-1 no puede
   testear esa familia con E0 como está. Se declara como límite de alcance de
   ESQ-1, o se prioriza B5.6 antes de ESQ-3. Afecta a D5/B5.5.
9. **Si los 304 `firma_invalida` del corpus (§3.2) entran a ESQ-3** como insumo
   propio. Están medidos y disponibles a USD 0.

---

## 10. Lo que esta unidad NO hizo

No tocó el prompt, ni el tool schema, ni el validador, ni ningún archivo de
extracción. No corrió extracción. No eligió el modo. No escribió
`documentos_excluidos_esq.json` (es de ESQ-1/ESQ-2 al ejecutarse). No commiteó.
Gasto de API: **USD 0**, cero llamadas.

Única escritura en el repo: **este archivo**.
