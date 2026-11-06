# Enmienda 4 a L-ESQ-R2 — con la forma r2, el tipo de la Comunicación sale del tramo verificado

**FIRMADA por la autora** el 04/10/2026 · Redactada: 2026-10-04.

Enmienda con fecha a L-ESQ-R2 (`data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`, FIRMADA en `4ef7650`;
sha256 del texto firmado `66c4a1b9…`). L-ESQ-R2 no se edita: esta enmienda vive al lado y se lee junto con
ella, con sus notas posteriores a la firma y con las enmiendas 2 (`5f9a731`) y 3 (`8d01b04`). Por la regla k de
CLAUDE.md §4, toda cita de L-ESQ-R2 es del texto firmado
(`git show 4ef7650:data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`), con su línea.

---

## 0. Qué enmienda y por qué

**Lo que dice L-ESQ-R2.** §2.3 (`:488-489`): `Comunicacion.tipo` «se deriva en código del `codigo` cuando tiene
forma de Comunicación». §2.4 (`:505`): «Comunicacion.tipo se deriva del `codigo`». La política por campo lo
repite en su paso `derivar_de_codigo_o_label` (`data/experiment/pyd_r2/politica_campos_r2.json:78`), y el
mandato de U-PROMPT-R2 lo extiende al número (decisión 16, `b901f6d`).

**Lo que se encontró.** El `codigo` y la etiqueta los escribe el modelo. En KG-Tanda0-Diez-r2a, el nodo de
código `A-39` es el artículo 39 de la Ley 21.526 (`ctacte::12.10.2`) y quedó con tipo «A» (hallazgo 1.12 de la
revisión independiente, `reports/u_revision_libre/`, `54f57cd`).

**Lo que hace el código desde P3b-2 de U-PROMPT-R2** (`c8c3970`; `data/experiment/pyd_r2/code/validador_r2.py`,
`derivar_comunicacion_tramo`). Con la forma de salida «r2», la derivación lee el tramo de evidencia de la
entidad, verificado contra el texto de la unidad.

## 1. Qué decide

1. **El tipo.** Con la forma r2, `Comunicacion.tipo` se deriva en código del tramo verificado, no del `codigo`
   ni de la etiqueta que escribe el modelo:
   - si el tramo nombra una Comunicación, el tipo es su letra, también cuando la nombra en una enumeración;
   - si nombra una norma externa, por el léxico de la política, el tipo es «externa»;
   - si no, el tipo no se deriva y se cuenta.
2. **El número.** Con la forma r2, `numero` se toma del `codigo`, como hasta ahora, y se controla contra los
   números que nombra el tramo verificado. El resultado se cuenta: coincide, no coincide o sin número para
   controlar. Una diferencia se cuenta y no se corrige. El número no se deriva del tramo porque un tramo puede
   nombrar varias Comunicaciones.
3. **Los perfiles existentes.** Con la forma «v3», la regla del §2.3 y del §2.4 sigue igual, y los grafos
   sellados no cambian.
4. **Referencia de implementación.** La nota a la política por campo
   (`data/experiment/pyd_r2/politica_campos_r2_notas.md`, `226ef7b`). El JSON de la política no cambia, para no
   mover su sha256.

## 2. Efecto medido

Sobre los 22 nodos Comunicacion de KG-Tanda0-Diez-r2a, con el texto de la unidad en lugar del tramo, que el
crudo de r2a no trae (`data/experiment/prompt_r2/p3b/diseno_p3b.md`, §6; `023f9a0`):

| Hoy | Con la regla | Nodos |
|---|---|--:|
| A | A | 11 |
| A | externa (`A-39`) | 1 |
| sin derivación | externa | 3 |
| sin derivación | sin sustento: no son normas | 7 |

El efecto sobre el crudo de r2b lo miden P4 de U-PROMPT-R2 y U-REEXT-T0.

## 3. Qué no cambia

- El texto de L-ESQ-R2, sus notas y las enmiendas 2 y 3.
- La lista de valores de `Comunicacion.tipo`, con «externa».
- El prefijo de E1 y su tool schema: E1 sigue pidiendo solo el `codigo`.
- Los grafos sellados y los perfiles existentes.

## Firma

FIRMADA por la autora el 04/10/2026. Rige desde esta firma.
