# Fe de erratas del laudo de esquema congelado — «20 TOs vírgenes» del §7

**FIRMADO por la autora — Agustina Videla Rivero, 08/09/2026.** Corrección
por declaración del laudo firmado
`data/experiment/esq/laudo_esquema_congelado.md` (FIRMADO 03/09/2026,
sellado en `2593d4d`), §7, líneas 169–170. El laudo **no se edita**: esta fe
de erratas lo corrige al lado.

**Contradicción de ruta, declarada.** El mandato original de esta unidad
ubicó el laudo en `docs/laudo_esquema_congelado.md`; esa ruta no existe. El
laudo vive en `data/experiment/esq/laudo_esquema_congelado.md`
(`git log -1 --format=%h 2593d4d`; sha256 actual
`64c5da88bbc4d5698025d722b69253d3a97ce2a510e2f07b9de457184f7a23bf`). Por la
convención del repo —la fe de erratas queda junto al artefacto que corrige,
como quedó la de los desvíos de lectura de ESQ-2 en
`data/experiment/esq/cobertura/`— esta fe de erratas vive en
`data/experiment/esq/`, al lado del laudo.

## 1. El pasaje, verbatim

`data/experiment/esq/laudo_esquema_congelado.md`, §7, líneas 169–173:

> Rige la opción (ii) del laudo ESQ-3a §8: la tanda 1 de B6 (**20 TOs
> vírgenes**) es el test de generalización; si revela una clase nueva de falla
> DE ESQUEMA (no de pipeline), se admite UN ciclo de corrección con laudo
> propio, re-extracción de la tanda 1 incluida, SIEMPRE ANTES de sellar el
> pre-registro de B6.3 […]

Su fuente, `data/experiment/esq/laudo_ESQ-3a_retoques.md` (FIRMADO
02/09/2026, sellado en `0a76549`), §7, mitigación 5, líneas 275–277, es más
explícita:

> 5. La ventana de la tanda 1 de B6 (§8) opera como test de generalización
>    sobre **material virgen: 20 TOs nunca vistos**, con salida de corrección
>    declarada.

La palabra sostiene el argumento de generalización de los dos laudos: el §7
de ESQ-3a declara el riesgo de que «el esquema retocado queda informado por
15 documentos de 157 […] y nunca fue probado sobre material que no lo
informó», y la mitigación 5 es la que promete ese material.

## 2. Qué se verificó, y contra qué

**(a) Los 20 de la tanda 1 no están enumerados.** `docs/plan_tesis.md:638`
define B6.1 como «Tanda 1: 20 TOs digeribles (normativa general
prioritaria)» y la línea 641 define B6.2 como «resto de digeribles (48)».
20 + 48 = 68, que es el veredicto de digeribilidad del inventario
(`data/experiment/escalado_prep/reporte_generalizacion.md` §1: «Veredicto
**digerible**: 68», commit `111ed19`). El ítem B6.1 sigue sin tildar y no
hay artefacto que liste los 20: **el conjunto concreto todavía no existe**.
Lo que sí existe es el conjunto del que saldrá.

**(b) Los 68 digeribles fueron leídos y adjudicados con cita verbatim en
U-B5.4 fase 1.** Artefacto: `data/experiment/esq_v3_miembros/tabla_to_rol_post_f1.md`
(reconstruido sin editar el generador y sellado en `b01eb18`); laudo que lo
cita como «la guarda del mapeo»: `docs/laudo_B5.4_fase1_catalogo.md` (FIRMADO
05/09/2026, sellado en `dea56ba`). Fuente de los pasajes declarada en la
propia tabla: `data/experiment/escalado_prep/e0_dry/<to>/chunks_<to>.json`.

Recuento sobre la tabla: **68 filas**, de las cuales **66 con pasaje de
alcance citado verbatim** y **2 huecos** (`docvig`, `fimipyme`) cuya ausencia
se estableció leyendo el índice del documento y se registró como hueco en vez
de inventarse. Reparto: 35 con alcance = clase(s) exacta(s) del catálogo,
31 con id de rol propio, 2 huecos — recuento de la fase 1, movido después por
el mini-laudo del freno 2 a **30 rol / 36 clase / 2 huecos = 68**
(`data/experiment/b54_catalogo_v3/catalogo_sujetos_v3.md`).

```bash
python3 -c "
import re
f=[l for l in open('data/experiment/esq_v3_miembros/tabla_to_rol_post_f1.md') if re.match(r'^\|\s*\d+\s*\|',l)]
c=[[x.strip() for x in l.strip().strip('|').split('|')] for l in f]
print(len(c), sum(1 for r in c if r[6].strip('«» ')!='—'), [r[1] for r in c if r[6].strip('«» ')=='—'])
"
```

Salida: `68 66 ['docvig', 'fimipyme']`.

**(c) Esa lectura no fue un censo: PRODUJO el recurso.** De ella salen los 30
ids `Sujeto_rol_alcance_<to>` y los 36 mapeos directos a clase, es decir
`ROL_POR_TO_V3` (71 entradas = 5 de desarrollo + 30 rol + 36 clase;
`catalogo_sujetos_v3.md`). Cada uno de los 68 documentos tiene en el catálogo
una entrada escrita **leyendo su propio pasaje de alcance**, y ese catálogo es
el que la extracción de la tanda 1 va a usar (perfil declarado `perfil_e1:
"v3_b54"`, U-ESQ-V3, `b01eb18`).

**(d) Los diez de ESQ-2 están dentro de los 68.** Los diez documentos quemados
por ESQ-2 (`data/experiment/esq/documentos_excluidos_esq.json`) —`actgar`,
`adrei`, `ayccef`, `cryl`, `ctacor`, `expaef`, `lavdin`, `opefci`, `prevmi`,
`traval`— figuran los diez en las 68 filas de la tabla. Los 5 de desarrollo
(`cap`, `cla`, `ext`, `pro`, `ric`) **no** están: el subset de desarrollo es
ajeno a la partición de 152.

```bash
python3 -c "
import re,json
f=[l for l in open('data/experiment/esq_v3_miembros/tabla_to_rol_post_f1.md') if re.match(r'^\|\s*\d+\s*\|',l)]
tos={[x.strip() for x in l.strip().strip('|').split('|')][1] for l in f}
q={d['id'] for d in json.load(open('data/experiment/esq/documentos_excluidos_esq.json'))['documentos']}
print(len(tos), len(q & tos), sorted(q - tos))
"
```

Salida: `68 10 []`.

**(e) Cronología.** El gate se firmó el **03/09**; la lectura de alcance de
los 68 es del **05/09** (`dea56ba`). El pasaje **no era falso cuando se
firmó**: quedó **superado** por trabajo posterior del propio proyecto. Lo
único anterior al 03/09 sobre esos documentos es la corrida E0 en seco y el
censo de menciones del `escalado_prep` (13/08, `111ed19`, determinístico y
USD 0), que `docs/diseno_UCABLEV3.md:288` clasifica como «censo/inventario
históricos, solo informan» y que no alimentó ni el esquema ni el catálogo.

## 3. El corte: vírgenes ¿respecto de qué?

El laudo usa «vírgenes» sin decir de qué. El proyecto tiene **dos recursos
distintos** que la tanda 1 pone a prueba a la vez, y el adjetivo se comporta
distinto en cada uno.

| dimensión | ¿vírgenes los 20? | evidencia |
|---|---|---|
| **ESQUEMA** (tipos, predicados, enum de `Obligacion.tipo`) | **Depende de la elección de los 20, y es alcanzable**: el esquema quedó informado por 15 documentos (5 de desarrollo + 10 de ESQ-2). Los 5 de desarrollo no están en los 68; los 10 de ESQ-2 sí. Quedan **58 digeribles** que ningún documento informó, más que suficientes para armar una tanda 1 de 20. Si los 20 se eligen entre esos 58, el adjetivo es cierto en esta dimensión. Si no se declara la exclusión, no lo es. | ESQ-3a §7 (`0a76549`) para los 15; `documentos_excluidos_esq.json`; tabla F1 |
| **CATÁLOGO DE SUJETOS v3** | **NO, y no hay elección que lo arregle**: los 68 digeribles —los 20 de la tanda 1 entre ellos, sean cuáles sean— tienen cada uno su pasaje de alcance leído y su entrada escrita a partir de esa lectura. No queda material digerible virgen para el catálogo. | tabla F1 (68/68); `catalogo_sujetos_v3.md` (`ROL_POR_TO_V3`, 71 entradas) |

En una línea: **la tanda 1 puede ser test de generalización del esquema, si
los 20 se eligen fuera de los diez de ESQ-2; no puede ser test de
generalización del catálogo de sujetos, se elija como se elija.**

## 4. Qué se sostiene igual

1. **La ventana de corrección del §7 y su política.** Un ciclo único con
   laudo propio antes de sellar el pre-registro de B6.3, y la muerte de la
   ventana con ese sello: no dependen de que el material sea virgen, sino de
   la secuencia. Sin cambio.
2. **Los nueve ítems de vigilancia pre-declarados.** Se miden igual. Más aún:
   los ítems (7), (8) y (9) —roles de alcance en `ejecuta` sin apoyo textual,
   tasa de `sujeto_propuesto`, emisiones de `entidad_originante_de_transferencia`
   fuera de dominio— son ítems **del catálogo**, agregados por el laudo de
   cierre de U-B5.4, y su valor está justamente en medir un recurso ajustado
   a estos documentos. No se debilitan: se re-rotulan.
3. **El principio de gobierno del §1** y todo lo que el laudo decide sobre
   retoques, retiros y residuos. Nada de eso pasa por la palabra «vírgenes».
4. **El riesgo declarado del §7 de ESQ-3a** («informado por 15 documentos de
   157 […] nunca fue probado sobre material que no lo informó») sigue en pie
   tal cual, y esta fe de erratas lo **agrava**: la mitigación 5 cubría menos
   de lo que su redacción promete.

## 5. Qué hay que reformular

**(i) El §7 del laudo de esquema congelado, líneas 169–170.** «20 TOs
vírgenes» pasa a decir de qué son vírgenes y de qué no. Redacción propuesta:

> Rige la opción (ii) del laudo ESQ-3a §8: la tanda 1 de B6 (20 TOs
> digeribles) es el test de generalización **del esquema**, y lo es a
> condición de que los 20 se elijan entre los 58 digeribles que no son
> ninguno de los diez de ESQ-2 — condición que el mandato de B6.1 declara y
> verifica. **No es test de generalización del catálogo de sujetos**: los 68
> digeribles tienen su pasaje de alcance leído y su entrada de catálogo
> escrita a partir de esa lectura (U-B5.4 fase 1), de modo que los ítems de
> vigilancia (7)–(9) miden el catálogo sobre material que lo informó.

**(ii) El §7 de ESQ-3a, mitigación 5.** «material virgen: 20 TOs nunca
vistos» pasa a «20 TOs que no informaron el esquema»; el «nunca vistos» es
insostenible desde el 05/09 en la dimensión del catálogo.

**(iii) Una condición nueva y verificable para el mandato de B6.1**: la
elección de los 20 excluye explícitamente a los diez de
`documentos_excluidos_esq.json`, y el mandato deja el aserto que lo comprueba.
Sin esa condición escrita, el adjetivo no se sostiene en ninguna de las dos
dimensiones.

**(iv) Toda prosa que herede el argumento.** `docs/plan_tesis.md:1080-1082`
repite «test de generalización sobre material virgen» en el punto de agenda de
mentores. Corresponde el mismo corte. La respuesta registrada del 04/09 (no
se ordenó test adicional; la validación externa es la lectura del capítulo) no
cambia por esto, pero el argumento con el que se acompañó sí: era más fuerte
de lo que el material permite.

## 6. Nota de alcance

Esta fe de erratas trata **una sola** de las dos vías por las que el laudo
argumenta generalización. La otra —la «regresión fresca» de ESQ-3b v2, que el
laudo invoca como «material fresco»— tiene su propia limitación, registrada
como entrada nueva en `data/experiment/esq/laudo_ESQ-3a_retoques.md` §7: es
fresca a nivel unidad y no a nivel documento. Las dos vías comparten el mismo
defecto de fondo: material descrito como ajeno que, mirado con el corte
correcto, no lo es del todo.

## Firma

**FIRMADO por la autora — Agustina Videla Rivero, 08/09/2026.**
