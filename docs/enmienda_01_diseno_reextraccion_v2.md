# Enmienda 01 al diseño de la re-extracción v2 (issue #9)

**Bloques estructurales como unidades de extracción de primera clase.**

Este documento enmienda `docs/diseno_reextraccion_v2.md` sin editarlo: el
diseño original queda intacto y esta desviación se documenta como enmienda
separada, nunca como ajuste silencioso — el mismo régimen de válvula que rige
el resto del proyecto (`docs/diseno_ev2.md` §"Después del sellado";
precedente `docs/protocolo_u6.md` §8). Donde esta enmienda calla, rige el
diseño original. Todo número lleva la ruta o el comando que lo reproduce,
corrido desde la raíz del repo.

---

## 1. Motivo: la calibración E0→E3 sobre pro midió un defecto arquitectural

La calibración del pipeline sobre el TO de Protección de Usuarios (88 chunks,
87 unidades verificadas por E3 tras el rechazo de `pro::3.1.1.2` en el fan-in
de E2) produjo tres mediciones que, juntas, no admiten lectura de defecto de
prompt.

**(a) 62,1 % de las unidades con faltantes en la verificación base.** El
veredicto base de E3 (intento 0, antes de todo reintento) marcó faltantes en
54 de 87 unidades — 62,1 % — con 117 faltantes en total, y el tipo dominante
es `otro` (58 de 117):

```bash
python3 -c "
import json
d=json.load(open('data/experiment/reextraccion_v2/e3_verificador/salida/faseB_pro/resumen_faseB_e3.json'))
vb=d['veredicto_base']
print(vb['con_faltantes'], '/', d['n_unidades_procesadas'], '=', round(vb['con_faltantes']/d['n_unidades_procesadas'],4))
print(vb['faltantes_total'], vb['faltantes_por_tipo'])"
```

Ese tipo dominante no es ruido disperso: está concentrado en contenido
normativo de los bloques heredados que llegó sin elemento portador en la
extracción. Anclando la cita textual de cada faltante contra el texto propio
del chunk y contra sus bloques de herencia (con la normalización del
precedente C7: des-guionado + sin espacios + casefold + sin acentos), **60 de
los 117 faltantes base verifican SOLO en bloques heredados** (51,3 %),
repartidos en 27 unidades; del tipo `otro`, 38 de 58 (65,5 %) son de esa
familia. Por tipo de bloque E0: intro 40, cierre 13, chapeau de sección 5,
encabezado 1.

```bash
python3 -c "
import json,unicodedata
def n(s):
    s=s.replace('-\n','')
    s=''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c)!='Mn')
    return ''.join(s.lower().split())
ch={c['id']:c for c in json.load(open('data/experiment/reextraccion_v2/e0_chunking/salida/chunks_pro.json'))}
vs=[json.loads(l) for l in open('data/experiment/reextraccion_v2/e3_verificador/salida/faseB_pro/veredictos.jsonl')]
tot=her=otro_her=0; unidades=set()
for r in vs:
    if r['fase']!='verificacion' or r['intento']!=0: continue
    c=ch[r['chunk_id']]; H=n('\n'.join(b['texto'] for b in c['herencia'])); P=n(c['texto'])
    for f in r['faltantes']:
        q=n(f['cita_textual_del_fuente']); tot+=1
        if q and q in H and q not in P:
            her+=1; otro_her+=(f['tipo']=='otro'); unidades.add(r['chunk_id'])
print(f'{her}/{tot} solo-herencia, {otro_her} del tipo otro, {len(unidades)} unidades')"
```

**(b) Cola del ratchet: 29,9 % REAL tras corregir la capa de citas.** La
corrida sellada de fase B dejó 27 unidades en cola humana (23 `cola_humana` +
4 `cola_humana_veredicto_inutilizable`;
`data/experiment/reextraccion_v2/e3_verificador/salida/faseB_pro/resumen_faseB_e3.json
→ estados`). La re-medición con la capa de citas corregida — que NO altera la
corrida sellada — convirtió exactamente 1 de las 27; la cola real es de 26
unidades sobre 87: **29,9 %**
(`data/experiment/reextraccion_v2/e3_verificador/salida/remedicion_citas/resumen_remedicion.json
→ tasa_cola_real_sobre_87: 0.2989`, con los 26 ids en `cola_real_chunk_ids`).

**(c) El experimento natural de la re-medición: el feedback completo no
convierte.** La re-medición es un experimento natural sobre el modo de falla:
en 25 de las 27 unidades, corregir la capa de citas no alteró el insumo del
reintento — 21 reintentos de E1 fueron byte-idénticos a los de la corrida
sellada (hits de la caché local: `cliente_e1_reintentos.cache_stats.hits: 21`
de 23 llamadas) y 4 veredictos siguieron inutilizables (sin cita verificable,
sin reintento posible; `estados_remedicion`) — es decir, en esas 25 el
feedback entregado ya estaba completo en la corrida sellada, y la
re-extracción igual no incorporó el contenido heredado señalado. Solo 2
unidades recibieron feedback distinto (los 2 misses de caché; el gasto del
log se mueve únicamente en `[3/27] pro::2.3.1.1` y `[9/27] pro::2.3.6.2`,
`salida/remedicion_citas/runner_log.txt`), y solo una de ellas convirtió
(`pro::2.3.6.2`, único `aceptado_tras_reintento`).

```bash
python3 -c "
import json
d=json.load(open('data/experiment/reextraccion_v2/e3_verificador/salida/remedicion_citas/resumen_remedicion.json'))
print(d['estados_remedicion'], d['cliente_e1_reintentos']['cache_stats']['hits'], '/', d['cliente_e1_reintentos']['cache_stats']['accesses'])
rows=[json.loads(l) for l in open('data/experiment/reextraccion_v2/e3_verificador/salida/remedicion_citas/desenlaces.jsonl')]
print(len(rows),'unidades;', sum(1 for r in rows if r['n_reintentos']==0),'sin reintento (inutilizable)')"
```

**Conclusión.** E1 sí usa la herencia como contexto de anclaje cuando decide
hacerlo — el chunker E0 hace viajar los bloques (caso ext 7.6: el encabezado
sin numerar de 1.144 chars en la herencia de los 8 chunks 7.6.x,
`data/experiment/reextraccion_v2/e0_chunking/INFORME_E0.md` §6.b), y en la
calibración de E1 sobre pro los chunks `pro::2.7.1`/`pro::2.7.2` anclaron
elementos al punto `2.7` con rol `herencia_encabezado`
(`data/experiment/reextraccion_v2/e1_extractor/salida/faseB_pro/extracciones.jsonl`).
Pero no extrae sistemáticamente el contenido normativo DESDE la herencia — ni
siquiera con feedback explícito, completo y con cita verificada que le señala
exactamente qué falta. Un defecto que sobrevive al feedback correcto no es un
defecto de prompt: es la arquitectura la que le pide a N extractores hijos
hacerse cargo, cada uno de paso, de un texto que no es el suyo. La respuesta
es cambiar de quién es la responsabilidad, no insistir con más ciclos.

---

## 2. La enmienda: los bloques estructurales son unidades de extracción

Los bloques estructurales que E0 hoy emite solo como herencia — chapeau de
sección, encabezado con contenido normativo, intro, intersticial, cierre
(tipos reales de la salida de E0: `chapeau_seccion`, `encabezado`, `intro`,
`intersticial`, `cierre`) — pasan a ser **unidades de extracción de primera
clase**, con estos cinco cambios:

**(a) E0 los emite como mini-chunks propios.** Cada bloque estructural que
cumple el criterio de materialización (abajo) se emite UNA vez como
mini-chunk, con:

- **id determinístico** en el namespace de chunks, función de la unidad de
  origen y el rol documental del bloque (p. ej.
  `<to>::<unidad_origen>::<rol>[::<n>]`, con `n` para tramos múltiples del
  mismo rol) — nunca del orden de emisión;
- **sha256 propio** del texto del bloque;
- **provenance de su unidad de origen**: el punto o sección al que el bloque
  pertenece (`unidad_origen`, que E0 ya registra por bloque) — NO los hijos
  que lo heredan.

**Criterio de materialización (explícito y determinístico):** un bloque
estructural se materializa como mini-chunk si y solo si contiene texto además
de su línea de título — operativamente: tras descontar la línea de label
(numeración + título, que el parser de E0 §2.4 ya identifica), el texto
restante normalizado no es vacío. Los encabezados puros — solo título, sin
contenido normativo, como «Sección 1. Disposiciones generales.» — NO se
materializan: no hay nada que extraer de ellos, y materializarlos fabricaría
unidades vacías que el censo de E2 contaría como ausencias falsas. Un
`encabezado` con prosa normativa (ext 7.6, 1.144 chars) sí se materializa: el
criterio es de contenido, no de tipo de bloque. Escala estimada con este
criterio (heurística de una línea de título; el número exacto lo fija la
implementación de E0): 284 mini-chunks sobre 810 bloques únicos en los 5 TOs
(pro: 13).

```bash
python3 -c "
import json,hashlib
tot=cont=0; pro=0
for to in ['cap','cla','ext','pro','ric']:
    vistos=set()
    for c in json.load(open(f'data/experiment/reextraccion_v2/e0_chunking/salida/chunks_{to}.json')):
        for b in c['herencia']:
            k=(b['unidad_origen'],b['tipo'],hashlib.sha256(b['texto'].encode()).hexdigest())
            if k in vistos: continue
            vistos.add(k); tot+=1
            ls=[l for l in b['texto'].strip().split('\n') if l.strip()]
            if not (len(ls)==1 and len(ls[0])<=140):
                cont+=1; pro+=(to=='pro')
print(cont,'/',tot,'; pro:',pro)"
```

**(b) E1 extrae cada mini-chunk UNA sola vez, con el mismo contrato.** El
mini-chunk entra al fan-out de E1 como cualquier chunk: mismo prefijo, mismo
contrato de salida (`extraer_kg_e1`), mismo validador; sus elementos llevan
`punto` = su unidad de origen. Los chunks hijos siguen recibiendo los bloques
estructurales como contexto — el anclaje que ya funciona no se toca — pero
con instrucción explícita de NO extraer contenido de ellos: **el contexto
ancla, la unidad extrae**. La división de responsabilidad puede además
endurecerse determinísticamente en el validador (restringiendo los "puntos
admitidos" del hijo); si se adopta, se declara en la unidad de
implementación.

**(c) E2 ensambla igual.** Los ids de E2 ya son función del contenido y la
provenance, y los elementos de los mini-chunks llegan con provenance de la
unidad de origen — el anclaje correcto por construcción, sin lógica nueva de
ensamblado. El mapa de E0 (y con él la guarda de fan-in y el censo
estructural) pasa a incluir los mini-chunks como unidades esperadas.

**(d) E3 verifica cada unidad contra su propio texto.** El blanco de
completitud de un chunk hijo pasa a ser su texto propio; el del mini-chunk,
el texto del bloque. Los faltantes de la familia medida en §1.a desaparecen
del veredicto de los hijos porque la herencia dejó de ser responsabilidad de
los hijos: si el contenido de un chapeau falta, el veredicto cae sobre el
mini-chunk del chapeau — una unidad, un responsable, un reintento.

**(e) El tope del ratchet queda en 1.** `TOPE_REINTENTOS = 1`, como en la
calibración (`data/experiment/reextraccion_v2/e3_verificador/INFORME_E3_FASEA.md`
§4). Esto cierra la pregunta abierta §7.a del diseño original por la vía de
la evidencia de §1.c: pagar reintentos adicionales contra un modo de falla
que el feedback completo no corrige es gasto sin mecanismo.

---

## 3. Efectos esperados (predicciones refutables)

La mini-recalibración de §5 mide estas predicciones; las declaro antes de
correr nada:

1. **La familia de faltantes en heredados desaparece por construcción.** Los
   60/117 faltantes base que verifican solo en herencia (§1.a) no pueden
   reaparecer en el veredicto de los hijos: el fuente del hijo ya no los
   contiene como blanco. Si reaparecen como faltantes de los mini-chunks, el
   defecto era del extractor y no de la arquitectura — eso refutaría la
   enmienda y quedaría medido.
2. **La cola del ratchet baja sustancialmente.** Predicción pre-declarada de
   mesa: **< 10 %** (contra el 29,9 % medido en §1.b).
3. **El costo por TO baja o queda neutro.** Cada bloque estructural se
   extrae 1 vez en lugar de intentarse N veces vía los reintentos de sus
   hijos, a cambio de más llamadas chicas (los ~13 mini-chunks de pro contra
   los 50 reintentos de E1 que la corrida sellada pagó;
   `resumen_faseB_e3.json → cliente_e1_reintentos.llamadas: 50`). El costo
   real lo mide la mini-recalibración.
4. **La provenance del contenido estructural queda anclada a su unidad
   real.** Hoy ese anclaje depende de que algún hijo decida extraer y anclar
   bien (§1, conclusión); con la enmienda es correcto por construcción.
   Esto corrige de paso el anclaje impreciso del contenido estructural —
   contenido de un bloque atribuido al hijo que lo heredó en lugar de a su
   unidad de origen.

---

## 4. Alternativas descartadas

- **Subir el tope del ratchet a 2 reintentos.** El experimento natural de
  §1.c muestra que el feedback completo, correcto y con cita verificada no
  convierte (21 reintentos byte-idénticos, cero conversiones; las 2 únicas
  conversiones de toda la fase B + re-medición fueron 27+1 sobre 54 unidades
  con faltantes). Pagar otro ciclo del mismo mecanismo contra un modo de
  falla sistemático es la definición de gasto sin hipótesis.
- **Asumir la cola humana.** 29,9 % del corpus son ≈ 441 chunks
  (`python3 -c "print(round(0.2989*1477))"`, sobre los 1.477 chunks de E0;
  `data/experiment/reextraccion_v2/e0_chunking/INFORME_E0.md` §3):
  exactamente el refinamiento manual que este pipeline existe para eliminar
  (`docs/diseno_reextraccion_v2.md` §1.a — la corrección manual no escala).

---

## 5. Alcance y secuencia

**Qué modifica la enmienda:**

- **E0**: emisión de mini-chunks con el criterio de materialización de §2.a;
  el mapa estructural y `conteos.json` los incluyen. El chunking de los
  puntos terminales no cambia; la herencia sigue viajando como contexto.
- **E1**: instrucción nueva sobre el contexto heredado (§2.b). El cambio de
  prompt **rota el namespace de caché** por el candado de diseño (el hash del
  prefijo integra el namespace,
  `e1_extraccion|cv=e1-extractor-v1-p<hash_prefijo>|think=0`;
  `docs/decisiones_caching_extraccion.md`): las extracciones de la
  mini-recalibración se pagan completas, y lo declaro acá — no es un hit
  perdido, es el candado operando como se diseñó.
- **E2/E3**: sin cambio de código sustantivo. E2 ensambla el mapa ampliado
  con la misma lógica; en E3 cambia el armado del fuente del hijo (texto
  propio como blanco), no el contrato ni el prompt del verificador.

**Secuencia:** el corpus queda **gateado por una mini-recalibración sobre
pro** con la arquitectura enmendada — mismo TO, mismo circuito E0→E3, tope
declarado ex ante (principio 2.f del diseño). Sus números — cola nueva contra
la predicción de §3.2, costo real contra §3.3, y el destino de la familia
§3.1 — alimentan la autorización de la corrida del corpus. Sin esa
mini-recalibración aprobada, esta enmienda no habilita ninguna corrida.
