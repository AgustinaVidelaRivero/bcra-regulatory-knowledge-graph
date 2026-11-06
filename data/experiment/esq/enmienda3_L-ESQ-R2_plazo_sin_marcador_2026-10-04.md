# Enmienda 3 a L-ESQ-R2 — el plazo sin marcador de comparación queda `no_determinada`

**FIRMADA por la autora** el 04/10/2026 · Redactada: 2026-10-04.

Enmienda con fecha a L-ESQ-R2 (`data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`, FIRMADA en `4ef7650`;
sha256 del texto firmado `66c4a1b9…`). L-ESQ-R2 no se edita: esta enmienda vive al lado y se lee junto con
ella, con sus notas posteriores a la firma y con la enmienda 2 (`5f9a731`). Por la regla k de CLAUDE.md §4,
toda cita de L-ESQ-R2 es del texto firmado
(`git show 4ef7650:data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`), con su línea.

---

## 0. Qué enmienda y por qué

**Lo que dice L-ESQ-R2.** §1.3, punto 3, regla «Sin marcador» (`:296-297`): «en un plazo, máximo inclusivo
con la marca `comparacion_asumida`; en cualquier otra cuantía, `no_determinada`». La repiten el §1.4 (`:350`)
y la lista de casos del §1.5 (`:390`). El §1.5 manda contar aparte los elementos con `comparacion_asumida` y
con `no_determinada` (`:397`).

**Lo que hace el código.** `data/experiment/pyd_r2/code/reglas_comparacion.py:443-447`: una cuantía de clase
plazo sin marcador recibe `maximo_inclusivo`, la regla `sin_marcador_plazo` y la marca `comparacion_asumida`.

**Lo que se midió.**

- En KG-Tanda0-Diez-r2a (`99fe2bfa…`), 176 de los 842 elementos de umbral llevan `comparacion_asumida`. En
  KG-Tanda0-Desarrollo-r2a (`93a7af72…`), 157 de 758. Comando, con `ens_diez_r2a` o `ens_desarrollo_r2a`
  como argumento; imprime el total, los que llevan la marca y los `no_determinada`:

  ```
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -c "import json,sys;kg=json.load(open('data/experiment/reextraccion_v2/corpus_tanda0/'+sys.argv[1]+'/r2/kg.json'));u=[x for n in kg['nodes'] for x in (n['properties'].get('umbrales') or [])];print(len(u),sum(bool(x.get('comparacion_asumida')) for x in u),sum(x.get('comparacion')=='no_determinada' for x in u))" ens_diez_r2a
  ```

- La revisión independiente (U-REVISION-LIBRE, hallazgo 1.8; `reports/u_revision_libre/freno_b1.md:18` y
  `reporte.md:80`, `54f57cd`) clasificó los 176 por patrón: 63 no son un máximo y 16 sí. Los 97 restantes
  quedaron sin clasificar (176 menos 63 y 16). En su lectura de 12 sorteados con semilla 99, 2 son un máximo
  (`freno_a.md:20`). Estas cifras son de esa unidad, NO VERIFICADAS: no las recomputé, y el script de los
  patrones no está versionado.
- Mi lectura, aproximada y con otra regla: las palabras que anteceden a la cuantía en el texto propio de la
  unidad (`data/experiment/esq/code/lectura_plazos_sin_marcador_enmienda3.py`). De los 176, 28 tienen un
  antecedente que no es un máximo («últimos», «transcurrido», «períodos de»), 40 un antecedente compatible
  con un máximo, 89 quedan sin clasificar y en 19 el tramo no está en el texto propio de la unidad. Entre
  los 40 hay máximos falsos: «luego del plazo de…» (`ext::14.1.1`, tres elementos) y ventanas hacia atrás
  («emitidos en los 30 días…», `ctacte::6.2.5`). No reproduce las cifras de la revisión independiente;
  coincide en el sentido.
- Dos casos, verificables en el grafo y en la E0. En `ext::14.1.1`, «luego del plazo de 2 (dos) años» queda
  como `maximo_inclusivo`: el texto dice lo que pasa después del plazo, no fija un tope. En `polcre::7.1.2`,
  «durante los últimos 90 días corridos» es una ventana hacia atrás, y también queda como máximo.
- Los marcadores de un plazo máximo ya tienen regla: «hasta» y «dentro de» dan máximo inclusivo
  (`reglas_comparacion.py:297-298`). Lo que llega a la regla «Sin marcador» es el resto.

**Por qué.** Un máximo asumido que resulta falso es un error con forma de dato: el elemento afirma
`maximo_inclusivo` donde la norma no fija un tope. `no_determinada` no afirma nada, y el tramo literal, el
valor y la unidad quedan en el elemento.

## 1. Qué decide

1. Un plazo sin marcador de comparación queda con `comparacion: no_determinada`, como cualquier otra cuantía
   sin marcador. No se asume un máximo.
2. La regla «Sin marcador» del §1.3 (`:296-297`) se lee así: «Sin marcador: `no_determinada`, en toda
   cuantía». Lo mismo vale para el §1.4 (`:350`).
3. La marca `comparacion_asumida` deja de producirse. El campo sigue en el modelo del elemento de umbral
   (`data/experiment/pyd_r2/code/modelos_r2.py`, campo `comparacion_asumida`), para que los grafos r2a sellados
   sigan validando.
4. En el §1.5, el caso «un plazo, con `comparacion_asumida`» (`:390`) pasa a ser «un plazo sin marcador, con
   `no_determinada`». El conteo aparte del `:397` sigue: el de `comparacion_asumida` da 0 desde r2b.
5. El plazo sin marcador conserva su nombre de regla propio, `sin_marcador_plazo`, para contarlo aparte de las
   demás cuantías sin marcador, que llevan la regla `sin_marcador`.
6. Rige desde r2b. Los grafos r2a sellados no se tocan.

## 2. Efectos declarados

- Con KG-Tanda0-Diez-r2a como referencia, 176 elementos pasan de `maximo_inclusivo` a `no_determinada`: los
  `no_determinada` pasan de 129 a 305, sobre 842. Con KG-Tanda0-Desarrollo-r2a, 157 elementos: de 125 a 282,
  sobre 758.
- Lo que se pierde: los plazos sin marcador que sí son un máximo quedan `no_determinada`. Por el patrón de
  la revisión son 16 de los 176.
- Cómo se recupera: una forma que sea un máximo se agrega como marcador en el código, con su calibración, y
  se re-aplica sobre lo extraído. No pide cambiar el prefijo de E1.
- E1 no emite `comparacion`: la fija el código. El prefijo, el tool schema y el esquema no cambian.

## 3. Implementación

Entra como punto (m) de C2 de U-R2-CODIGO-2
(`docs/mandatos/UR2CODIGO2_correcciones_previas_a_reext.md`):

- `pyd_r2/code/reglas_comparacion.py:443-447` y su docstring (`:44-45`): el plazo sin marcador recibe
  `no_determinada`, con la regla `sin_marcador_plazo` y sin la marca;
- `pyd_r2/code/selftest_pyd_r2.py`: los cuatro casos que hoy esperan la marca en un plazo sin marcador
  (`grep -n comparacion_asumida`; en `54f57cd`, `:458`, `:477-479`, `:555-556` y `:708`) pasan a esperar
  `no_determinada`;
- control: la lista de cada elemento que cambia en los dos grafos r2a (176 y 157); ningún elemento con
  marcador cambia; los cuatro casos de control del §1.5 (`:391-395`) dan lo mismo que hoy.

## 4. Qué no cambia

- El texto de L-ESQ-R2, sus notas y la enmienda 2.
- Las demás reglas de comparación y su precedencia.
- El modelo del elemento de umbral y su validador (`modelos_r2.py`: la marca solo vale en un plazo con
  `maximo_inclusivo`).
- Los grafos sellados.

## 5. Decisión de la autora al firmar

1. El plazo sin marcador conserva un nombre de regla propio, `sin_marcador_plazo` (§1, punto 5).
2. Las cifras de la revisión independiente (63, 16 y 97) quedan citadas como de esa unidad, no verificadas,
   junto con la lectura del §0.

## Firma

FIRMADA por la autora el 04/10/2026. Rige desde esta firma.

## Notas posteriores a la firma

El texto firmado termina en la línea anterior a este título y no cambia.

- **04/10/2026 — son nueve las expectativas del selftest que cambian, no cuatro (consecuencia de esta
  enmienda; FRENO C2 de U-R2-CODIGO-2, `data/experiment/r2_codigo2/freno_c2.md`).** El §3 nombra «los cuatro
  casos» de `pyd_r2/code/selftest_pyd_r2.py` que esperan la marca en un plazo sin marcador. Las expectativas
  que codifican la regla anterior son nueve:
  - las cuatro de la marca `comparacion_asumida`, que nombra el §3;
  - cinco filas que esperan `maximo_inclusivo` con la regla `sin_marcador_plazo` para un plazo sin marcador
    («el menor entre 1 año y el plazo residual», «la Superintendencia podrá fijar un plazo de 30 días», «en
    un plazo de 30 días», «la supervisión dispondrá de 30 días» y «cinco días hábiles» de la fila r1).
  Las nueve pasan a esperar `no_determinada`, sin la marca. Es la misma regla del §1, punto 1: no hay
  decisión nueva. Comando, sobre el código de C2 (sin commit al 04/10/2026):
  `git diff -U0 HEAD -- data/experiment/pyd_r2/code/selftest_pyd_r2.py | grep -E "sin_marcador_plazo|asumida"`.
  Con ese código, `selftest_pyd_r2` da 378 de 378, corrido sobre una copia en la revisión del freno.
