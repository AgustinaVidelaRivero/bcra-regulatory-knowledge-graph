# Fe de erratas — alcance de la medición de ESQ-1 (crudo vs validado)

**Qué es este documento.** La unidad U-ESQ-1a (instrumento de cadenas distintas,
commit `181e262`) encontró que el pre-registro de ESQ-1
(`data/experiment/esq/prerregistro_esq1.md`, sellado en `38be6e5`) apoya la ubicación
de su medición en una premisa falsa, y que la ubicación elegida introduce un sesgo
direccional. **El pre-registro no se enmienda**: se corrige por declaración, misma
forma que la errata del 8.162 registrada en su §2.

Toda cifra sale de un recomputo contra los cinco jsonl de producción
(`data/experiment/reextraccion_v2/corpus_v2/salida/{cap,cla,ext,pro,ric}/extracciones_e1.jsonl`)
o de una verificación contra el código, con archivo y línea.

---

## (a) Error de hecho: `sujeto_propuesto` sí existe en el crudo

**Lo que dice el pre-registro, §7:** *«por analogía estricta con `sujeto_propuesto`
—que no existe en el crudo y lo agrega el validador al normalizar—»*.

**Lo que dicen los archivos.** `sujeto_propuesto` está declarado en el **tool schema
de `relations`** que se le envía al modelo, de modo que el modelo lo emite
directamente y aparece en `tool_input_crudo`:

- `prompt_e1.py:245-248` — el campo `sujeto_propuesto` es parte del schema de
  `relations`, con su descripción («nombre del sujeto tal como aparece en el texto,
  cuando NO matchea ninguna entrada del catálogo»).
- `prompt_e1.py:110` — la instrucción que le pide al modelo usarlo.
- Registro crudo real (`ext/extracciones_e1.jsonl`):
  `{"predicate": "aplica_a", "source": "e3", "sujeto_propuesto": "Entidades financieras locales", …}`
  dentro de `tool_input_crudo.relations`.

**Lo que el validador sí hace**, y que la frase confundió con «agregar»: (i)
**normaliza** —rellena la clave en las 720 relaciones validadas, incluso cuando viene
vacía, por eso el campo aparece siempre en `validacion.relaciones`— y (ii) **descarta**
las relaciones rechazadas, con la propuesta que transportaban.

---

## (b) Decisión corregida: ESQ-1 mide sobre `tool_input_crudo`

**El número que cuenta para las bandas se computa sobre `tool_input_crudo`, no sobre
`validacion.*`.**

**Fundamento.** Leer del validado descarta propuestas **por motivos ajenos a la
propuesta**. Las dos pérdidas del conjunto de desarrollo, trazadas una por una:

| unidad | cadena perdida | por qué se perdió |
|---|---|---|
| `ext::14.2.1.9` | `agencia de crédito del exterior` | la relación que la transportaba fue rechazada: `firma_invalida` ×3 |
| `ext::4.4.4` | `clientes que no sean personas humanas residentes` | `predicado_invalido` |

En ninguno de los dos casos la propuesta era inválida **como propuesta**: falló el
elemento que la contenía, por la matriz dominio/rango o por el predicado.

**Por qué eso sesga en una dirección.** ESQ-1 corre sobre documentos nuevos, donde el
contenido fuera de esquema es justamente lo que se espera encontrar. Una relación que
expresa algo que el esquema no previó tiene **más** probabilidad de violar también la
matriz dominio/rango, de modo que la pérdida **correlaciona con la señal que ESQ-1
mide**, y no es ruido aleatorio. El sesgo apunta a subcontar novedad, es decir hacia
**banda A — el resultado cómodo**.

Es la misma forma del «cero por construcción» que U-ESQ-0 detectó y que el laudo D1
resolvió: **el instrumento no puede tener un filtro que suprima justo lo que viene a
medir**.

**Se reportan LOS DOS números.** El de crudo es el que se lee contra las bandas; el de
validado se reporta al lado. **La brecha entre ambos es en sí misma un dato**: mide
cuánto de lo que no encaja en el esquema es suprimido por la validación antes de
llegar a cualquier conteo. Sobre desarrollo esa brecha es de 2 disparos y 1 cadena;
sobre documentos nuevos es una cantidad a observar, no a suponer.

**Consecuencia declarada: el crudo no está validado.** Puede traer cadenas
malformadas, truncadas o fuera de tipo. El diseño ya lo absorbe y no hace falta
agregar nada: el **default de la regla de normalización** (§7.5 del scoping, sellado
por D9) manda a **familia nueva** todo lo que ninguna regla alcanza, y lo que no sea
ni tipo ni predicado cae en **`NO_COMPUTABLE`**, con su umbral declarado del 20 %.
Ambos sesgos de la regla apuntan en contra del resultado cómodo, de modo que leer del
crudo no puede fabricar un veredicto de «el esquema generaliza».

**Consecuencia operativa — el instrumento necesita una extensión declarada.** El
instrumento de `181e262` tiene el bloque `validacion` **cableado**: su tabla `CANALES`
mapea cada canal a `(contenedor dentro de validacion, campo)`
(`cadenas_esq.py:86-90`) y la navegación hace `registro.get("validacion")`
(`cadenas_esq.py:129`). *(Nota: U-ESQ-1a-bis movió esas líneas al ejecutar esta
extensión; la cita refiere al estado del archivo en `181e262`.)* Leer del crudo **no es sólo pasarle otra ruta**: requiere
agregar los canales del bloque `tool_input_crudo`. Es una extensión chica y de código
puro, con su selftest, y queda como tarea previa a la corrida de ESQ-1. Mientras no
exista, ningún número de ESQ-1 es computable bajo esta decisión.

---

## (c) Alcance de las cifras que el pre-registro usa sin declarar

El pre-registro cita **54 disparos / 38 cadenas distintas** (fundamento de P2 y de
P5) sin decir sobre qué bloque. La etiqueta correcta:

| cifra | alcance exacto |
|---|---|
| **54 disparos / 38 distintas** | `validacion.relaciones[].sujeto_propuesto`, cinco jsonl de producción |
| **56 disparos / 39 distintas** | `tool_input_crudo.relations[].sujeto_propuesto`, mismos archivos |
| **55** (`scoping_esq1.md:611`) | crudo **restringido** a `predicate ∈ {aplica_a, ejecuta}`; el 56 es el crudo sin restricción de predicado — un disparo cae fuera de esos dos |

Ninguna de las tres está mal: miden cosas distintas. Lo que faltaba era la etiqueta, y
queda fijada acá. Bajo la decisión (b), el número de referencia de ESQ-1 pasa a ser el
de crudo.

---

## Qué NO cambia

- **Las cinco predicciones siguen vigentes tal como están redactadas.** P2 y P5 se
  fundan en el orden de magnitud del canal abierto sobre desarrollo, y ese orden es el
  mismo con cualquiera de las dos cifras (54/38 o 56/39).
- **Los umbrales de las bandas no se tocan** (§7.4, sellados por D9, declarados no
  calibrados).
- **La regla de normalización no se toca** (§7.5, sellada en el mismo acto por D9),
  incluidos su default a familia nueva y el umbral de `NO_COMPUTABLE`.
- **La secuencia de diez pasos y el blindaje de D9 no se tocan**: la lista sigue
  saliendo pelada, la normalización sigue siendo ciega y el mapeo se sigue sellando
  antes de contar. Cambia de qué bloque sale la lista, no cómo se la trata después.
