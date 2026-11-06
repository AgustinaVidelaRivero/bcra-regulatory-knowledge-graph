# El corpus

`textos_ordenados.csv` trae los 157 Textos Ordenados del corpus: 103 de normativa general y 54 de régimen informativo. Cada uno con su
enlace al sitio del BCRA,
su sha256 y la columna `destino`, que dice si está en el grafo evaluado (128), si queda para el grafo corregido (25) o si queda fuera del
recurso (4). Los 5 del conjunto
de desarrollo se descargaron el 7 y el 10 de mayo de 2026 y van con el sha256 de esa versión; los otros 152, el 13 de agosto de 2026.

El sha256 es el de la versión con que se trabajó, y el enlace da la versión vigente. El 2 de octubre de 2026, 23 de los 157 ya eran
distintos en el sitio, 17 de ellos del
grafo evaluado: los marca la última columna.

`manifiesto_corpus.csv` trae otra cosa: los 133 archivos que nombra la procedencia del grafo. Trae 129 PDF porque a los 128 del grafo
evaluado suma `rdbcra.pdf`, uno de los
25 del grafo corregido, que aparece en la procedencia de un solo nodo, sin aristas, que sale del catálogo de sujetos. Los otros 4 son JSON
de origen.
