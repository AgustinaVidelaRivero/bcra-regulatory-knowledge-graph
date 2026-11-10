# Reconstruir los índices y arrancar los 4 servidores

Esta guía parte de un clon del repositorio y de los 128 PDF de la versión usada. Rehace la segmentación E0 y los índices, los compara con sus referencias y arranca los 4 servidores: N7, N7c+, la combinada y la densa. No llama a ninguna API y no rehace las matrices densas, que vienen en el repositorio.

**Dónde se probó.** En una Mac con macOS 15.7.1, arm64 y 16 GiB de memoria, sobre el commit `91dbfb9c` más esta carpeta y las matrices densas con su manifiesto. Los nombres de los tar son para esa plataforma.

En la prueba, los comandos se corrieron tal como están acá, desde la raíz de un clon limpio. Hubo 4 excepciones: las descargas, la extracción de los tar y la contraseña de Neo4j venían de una prueba anterior, y el camino Docker no se probó. Lo que imprime cada paso es lo de esa prueba.

**Lo que tarda y ocupa.** Se bajan unos 1,84 GB. Lo que más tarda es bajar el modelo, 18 minutos cuando se probó, y después las 3 corridas de la E0, unos 10 minutos. El resto, salvo las descargas, tarda menos de 1 minuto por paso.

**Si algo no da su sha256, no sigas:** el servidor que lo use no va a arrancar.

## 0. Las carpetas

Todo se corre desde la raíz del clon, en una sola terminal, porque algunos pasos dejan variables para los siguientes.

```bash
H="<carpeta para Python, el JDK y Neo4j, fuera del clon>"
S="<carpeta para lo que generan la E0 y el arranque, fuera del clon>"
```

Los 4 programas de esta carpeta son `colocar_pdfs.py`, `correr_e0_sin_roles.py`, `armar_e0_acumulada.py` y `completar_manifiesto_puntos.py`. Usan solo la biblioteca estándar.

## 1. Los 2 Python

El `.venv` usa Python 3.10.13 y el entorno vectorial, Python 3.12.13. Son los que declaran `requirements.txt:2` y `data/experiment/banco_mcp/requirements_vector.txt:1`.

```bash
mkdir -p "$H/descargas"
curl -fsSL --proto '=https' -o "$H/descargas/cpython-3.10.13+20240224-aarch64-apple-darwin-install_only.tar.gz" "https://github.com/astral-sh/python-build-standalone/releases/download/20240224/cpython-3.10.13%2B20240224-aarch64-apple-darwin-install_only.tar.gz"
curl -fsSL --proto '=https' -o "$H/descargas/cpython-3.12.13+20260807-aarch64-apple-darwin-install_only.tar.gz" "https://github.com/astral-sh/python-build-standalone/releases/download/20260807/cpython-3.12.13%2B20260807-aarch64-apple-darwin-install_only.tar.gz"
```

```bash
shasum -a 256 "$H/descargas/cpython-3.10.13+20240224-aarch64-apple-darwin-install_only.tar.gz" "$H/descargas/cpython-3.12.13+20260807-aarch64-apple-darwin-install_only.tar.gz"
```

Tiene que dar `5fdc0f6a5b5a90fd3c528e8b1da8e3aac931ea8690126c2fdb4254c84a3ff04a` para el de 3.10.13 y `4201588fc5051c2ba988abbe1f033d318965ee378fadf7fb7ef79882ba7be84b` para el de 3.12.13. Son las últimas etiquetas que traen esas versiones, y cada sha256 es el que publica el `SHA256SUMS` de su etiqueta.

```bash
mkdir "$H/python_3_10_13"
tar -xzf "$H/descargas/cpython-3.10.13+20240224-aarch64-apple-darwin-install_only.tar.gz" -C "$H/python_3_10_13"
tar -xzf "$H/descargas/cpython-3.12.13+20260807-aarch64-apple-darwin-install_only.tar.gz" -C "$H"
```

El de 3.10.13 queda en `$H/python_3_10_13/python`, y el de 3.12.13 en `$H/python`.

## 2. Los 2 entornos

El `.venv` va en la raíz del clon, y el entorno vectorial en `venvs/vector`. El `.gitignore` deja afuera las 2 carpetas. El apéndice trae el `pip freeze` de cada entorno en la prueba, porque `requirements.txt` no fija las dependencias de sus dependencias.

```bash
"$H/python_3_10_13/python/bin/python3.10" -m venv .venv
```

```bash
.venv/bin/python -m pip install -r requirements.txt
```

```bash
.venv/bin/python -m pip check
```

```bash
mkdir -p venvs
"$H/python/bin/python3.12" -m venv venvs/vector
```

```bash
venvs/vector/bin/python -m pip install -r data/experiment/banco_mcp/requirements_vector.txt
```

```bash
venvs/vector/bin/python -m pip check
```

Cada `pip check` imprime:

```
No broken requirements found.
```

La variable `BANCO_VENV_VECTOR` nombra el entorno vectorial:

```bash
export BANCO_VENV_VECTOR="$PWD/venvs/vector"
```

## 3. El modelo

```bash
"$BANCO_VENV_VECTOR/bin/python" -c 'from huggingface_hub import snapshot_download; snapshot_download("microsoft/harrier-oss-v1-0.6b", revision="f9b9dc8d367d443f2479d27aa5d8d2850c0774ee")'
```

Son 15 archivos y 1.208.039.868 bytes, y quedan en `HF_HOME`. Los servidores corren después sin red, con `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`, como dicen sus `mcp_*.json`.

## 4. Los 128 PDF

Bajá `textos_ordenados_bcra_128.zip` del registro de Zenodo [10.5281/zenodo.24106654](https://doi.org/10.5281/zenodo.24106654) y dejalo en la raíz del clon. Sus 2 huellas:

```bash
shasum -a 256 textos_ordenados_bcra_128.zip
```

```bash
md5 -q textos_ordenados_bcra_128.zip
```

Tienen que dar `91c79331beda5334dcc4fa878b10efd6bb1684a435568d8435fcabb97309e718` y `0d1ea751f509d6d933caa8f10b8e8349`. En Linux, `md5sum` reemplaza a `md5 -q`.

`colocar_pdfs.py` deja cada PDF en la ruta que nombra su manifiesto de corpus. Lo que abre del ZIP queda en `$S/textos_ordenados_bcra_128/`:

```bash
.venv/bin/python reconstruccion/colocar_pdfs.py textos_ordenados_bcra_128.zip 91c79331beda5334dcc4fa878b10efd6bb1684a435568d8435fcabb97309e718 --tmp "$S"
```

Imprime:

```
zip_sha256_ok=91c79331beda5334dcc4fa878b10efd6bb1684a435568d8435fcabb97309e718
contra_el_csv=128 de 128
copiados=128 ya_estaban=0
en_su_lugar=128 de 128
```

## 5. La E0

La E0 se reconstruye con Python 3.10.13, el de requirements.txt, y con la validación de roles del manifiesto salteada, porque necesita candado_mensaje_r2b.json, que no se publica. Se controla igual: da 640 de 640 contra el armado. Con Python 3.12 da 625 de 640, porque desde esa versión sum() suma los floats con compensación y 15 archivos tablas_ cambian 24 valores de bbox en hasta 0,1.

```bash
M=data/experiment/reextraccion_v2/manifiestos
```

```bash
.venv/bin/python reconstruccion/correr_e0_sin_roles.py "$M/tanda0_10tos_r2b.json" "$S/tanda0"
```

```bash
.venv/bin/python reconstruccion/correr_e0_sin_roles.py "$M/tanda1_20tos_r2b.json" "$S/tanda1"
```

```bash
.venv/bin/python reconstruccion/correr_e0_sin_roles.py "$M/tanda_final_98tos_r2b.json" "$S/tanda_final"
```

Imprimen `archivos_en_la_salida=57`, `archivos_en_la_salida=107` y `archivos_en_la_salida=498`. Tardaron 123, 201 y 289 s.

```bash
.venv/bin/python reconstruccion/armar_e0_acumulada.py "$S/tanda0" "$S/tanda1" "$S/tanda_final"
```

Imprime:

```
armado_valores_hex=626
archivos_leidos_de_las_salidas=662
copiados_y_cotejados=640 de 640
valores_del_armado_sin_archivo=5
pdf_colocados=128
manifiesto_pdf_coinciden=128 de 128
manifiesto_pdf_no_coinciden=0
```

Sale con 0 solo si dan los 640 y los 128. Los 5 valores sin archivo no son archivos de la E0. La E0 queda en `data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b/`, que es la carpeta que nombra el manifiesto del índice de fragmentos.

## 6. El índice de fragmentos

Corre con el entorno vectorial.

```bash
"$BANCO_VENV_VECTOR/bin/python" -B data/experiment/banco_mcp/mcp_vector/construir_indice.py --manifiesto data/experiment/banco_mcp/mcp_vector/manifiestos_e0/e0_evaluado_128tos_r2b.json --afinidad bm25 --out data/experiment/banco_mcp/mcp_vector/indice/e0_evaluado_128tos_bm25
```

Imprime, con otros tiempos:

```
pasajes: 10680 | sha256_corpus OK (7b93dd418042…) | 0.2s
índice BM25 sha=8f57949d931ad74f0d34c169cd53f9392451e1f977a612740e5f01757df55a66 | 10680 docs, vocabulario 25266 | 5.1s
```

El servidor denso usa el mismo `pasajes.json`, que no se rehace con la matriz. Tiene que dar `54ee790d5a0792dbec2f4c54a8633c19012b7f18f0738610954edb7afa78ff75`:

```bash
shasum -a 256 data/experiment/banco_mcp/mcp_vector/indice/e0_evaluado_128tos_bm25/pasajes.json
```

```bash
cp data/experiment/banco_mcp/mcp_vector/indice/e0_evaluado_128tos_bm25/pasajes.json data/experiment/banco_mcp/mcp_vector/indice/e0_evaluado_128tos_denso/
```

## 7. El índice de puntos

Corre con el `.venv`.

El índice de puntos se arma con indice_puntos_union.py en una carpeta sin manifiesto previo. Como la matriz densa no se rehace, completar_manifiesto_puntos.py le agrega al manifiesto el bloque denso del manifiesto de referencia, en el mismo lugar en que lo pone construir_denso_puntos.py, y el manifiesto da el sha256 que comprueban las configuraciones N7 y N7c+.

```bash
gunzip -k data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz
```

```bash
shasum -a 256 data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json
```

Tiene que dar `576c97256185a0d5741cb2c35a2a85e91412f3e1119ad7a85d960b7d60c35ad3`.

```bash
.venv/bin/python data/experiment/banco_mcp/mcp_kg/indice_puntos_union.py --grafo KG_Acumulado_Tandas0y1yFinal_r2b_sincola --e0-dir data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b --salida data/experiment/banco_mcp/mcp_kg/indice_puntos/KG_Acumulado_Tandas0y1yFinal_r2b_sincola
```

Imprime un JSON con `n_puntos` 11814, `n_nodos` 37168, `procedencias_fuera_de_la_e0` 0 y `puntos_fuera_de_la_estructura` 0.

```bash
shasum -a 256 data/experiment/banco_mcp/mcp_kg/indice_puntos/KG_Acumulado_Tandas0y1yFinal_r2b_sincola/manifiesto.json
```

Tiene que dar `eec47db5436dc78e562b11aad0a284f5d14f08ab83568079e2d93d43313ad9dc`.

```bash
.venv/bin/python reconstruccion/completar_manifiesto_puntos.py
```

Imprime:

```
manifiesto_sin_denso_ok=eec47db5436dc78e562b11aad0a284f5d14f08ab83568079e2d93d43313ad9dc
matriz_ok=a5ed3c60035e8355329cc11203b6998dba1ccf5f74a854e759526ded25d5447e
manifiesto_completo_ok=ef036b67032175f32996513a81198f65ed29850bc336ba35ae445f7f20c152d6
```

## 8. Neo4j

Hay 2 caminos. Los 2 usan Neo4j Community 5.26.9 y escuchan solo en `127.0.0.1:7474` y `127.0.0.1:7687`, sin plugins, con 1 GB de heap y 512 MB de caché de páginas. Antes de levantarlo, comprobá que no haya nada en esos puertos. Estos 2 comandos no tienen que imprimir nada:

```bash
lsof -nP -iTCP:7474 -sTCP:LISTEN
```

```bash
lsof -nP -iTCP:7687 -sTCP:LISTEN
```

### Camino 1: el tar de Neo4j y un JDK 21 (probado)

```bash
curl -fsSL --proto '=https' -o "$H/descargas/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.13_9.tar.gz" "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.13_9.tar.gz"
curl -fsSL --proto '=https' -o "$H/descargas/neo4j-community-5.26.9-unix.tar.gz" "https://dist.neo4j.org/neo4j-community-5.26.9-unix.tar.gz"
```

```bash
shasum -a 256 "$H/descargas/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.13_9.tar.gz" "$H/descargas/neo4j-community-5.26.9-unix.tar.gz"
```

Tiene que dar `bf036b35b071bfb2f54f2c0af8ee8d88afa95ee6eb3dce02c0f94cfc2524d04a` para el JDK y `2beb60e00e52562099a82693b8af2e48cdc8c96518d36b13a5816db0370a49ae` para Neo4j.

```bash
tar -xzf "$H/descargas/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.13_9.tar.gz" -C "$H"
tar -xzf "$H/descargas/neo4j-community-5.26.9-unix.tar.gz" -C "$H"
```

```bash
export JAVA_HOME="$H/jdk-21.0.13+9/Contents/Home" NEO4J_HOME="$H/neo4j-community-5.26.9" JAVA_TOOL_OPTIONS="-XX:-UsePerfData"
```

Al final de `$NEO4J_HOME/conf/neo4j.conf` van estos renglones, con la ruta absoluta de la carpeta temporal que elijas:

```
server.default_listen_address=127.0.0.1
server.bolt.listen_address=127.0.0.1:7687
server.http.listen_address=127.0.0.1:7474
server.memory.heap.initial_size=1g
server.memory.heap.max_size=1g
server.memory.pagecache.size=512m
dbms.usage_report.enabled=false
server.jvm.additional=-XX:-UsePerfData
server.jvm.additional="-Djava.io.tmpdir=<ruta absoluta>"
server.jvm.additional="-Djna.tmpdir=<ruta absoluta>"
```

Si la ruta tiene espacios, los 2 renglones de la carpeta temporal de neo4j.conf llevan el argumento entero entre comillas dobles; sin las comillas, Neo4j parte el valor en el espacio y la JVM no arranca.

Hay 2 ajustes que el `docker-compose.yml` no trae:

- `dbms.usage_report.enabled=false`, para que Neo4j no envíe datos de uso a sus servidores.
- `-XX:-UsePerfData`, para que la JVM no escriba sus archivos de rendimiento en la carpeta temporal del sistema. `JAVA_TOOL_OPTIONS` lo aplica también al proceso que lanza `bin/neo4j`.

La contraseña de desarrollo es el valor por defecto de `NEO4J_PASSWORD` en `data/experiment/neo4j/conexion.py:24`. Este comando la pone antes del primer arranque, sin mostrarla:

```bash
"$NEO4J_HOME/bin/neo4j-admin" dbms set-initial-password "$(.venv/bin/python -c 'import sys; sys.path.insert(0, "data/experiment/neo4j"); import conexion; print(conexion.NEO4J_PASSWORD)')"
```

```bash
"$NEO4J_HOME/bin/neo4j" start
```

Este espera a que los 2 puertos escuchen. En la prueba tardaron 6 s:

```bash
until lsof -nP -iTCP:7687 -sTCP:LISTEN > /dev/null && lsof -nP -iTCP:7474 -sTCP:LISTEN > /dev/null; do sleep 2; done
```

### Camino 2: Docker (no probado)

Es la definición de `data/experiment/neo4j/docker-compose.yml`, con la misma contraseña:

```bash
(cd data/experiment/neo4j && docker compose up -d)
```

Los pasos que siguen deberían ser los mismos, pero con este camino no se comprobaron.

## 9. Cargar el grafo

```bash
.venv/bin/python data/experiment/neo4j/cargar_kg.py --grafo KG_Acumulado_Tandas0y1yFinal_r2b_sincola
```

Tardó 40 s. Imprime, entre otras cosas:

```
[KG_Acumulado_Tandas0y1yFinal_r2b_sincola] conteo nodos   Neo4j=37168  esperado=37168 ✓
[KG_Acumulado_Tandas0y1yFinal_r2b_sincola] conteo aristas Neo4j=128552  esperado=128552 ✓
[KG_Acumulado_Tandas0y1yFinal_r2b_sincola] aristas hacia otro grafo: 0 ✓
[KG_Acumulado_Tandas0y1yFinal_r2b_sincola] KG_Meta.kg_sha256=576c97256185a0d5741cb2c35a2a85e91412f3e1119ad7a85d960b7d60c35ad3 ✓
[KG_Acumulado_Tandas0y1yFinal_r2b_sincola] huella contenido neo4j =2645da6d01795d520f3c4ab5e237050c530238061f849cd7d1e0170be9223463 ✓ idéntica
[KG_Acumulado_Tandas0y1yFinal_r2b_sincola] huella props aristas neo4j =e3928cb747a37a5e6eb69502a6e6499e6e5de1199d1116e118b7dff5231807bc ✓ idéntica
```

```bash
.venv/bin/python data/experiment/neo4j/indices.py --grafo KG_Acumulado_Tandas0y1yFinal_r2b_sincola
```

Tardó 1 s. Termina con:

```
RESULTADO KG_Acumulado_Tandas0y1yFinal_r2b_sincola: BKL-0003 N/A | BKL-0003/desc N/A | BKL-0027 OK
```

Los `N/A` son 2 pruebas cuyo nodo no existe en este grafo. El programa también imprime fragmentos del grafo, que esta guía no reproduce.

## 10. Arrancar los servidores

Con Neo4j arriba, de a uno:

```bash
.venv/bin/python ejemplos/arrancar_servidores.py --salida "$S/arranque" --solo n7
```

```bash
.venv/bin/python ejemplos/arrancar_servidores.py --salida "$S/arranque" --solo n7c_mas
```

```bash
.venv/bin/python ejemplos/arrancar_servidores.py --salida "$S/arranque" --solo la_combinada
```

```bash
.venv/bin/python ejemplos/arrancar_servidores.py --salida "$S/arranque" --solo la_densa
```

Cada servidor negocia, lista sus herramientas y termina. N7, por ejemplo, imprime:

```
{"n7": {"mcp_json": "data/experiment/banco_mcp/n7/mcp_kg_n7_evaluado.json", "herramientas": ["buscar_nodos", "buscar_puntos", "indice_to", "tipos_de_relacion", "vecinos_por_relacion", "ver_descendientes", "ver_nodo", "ver_punto", "ver_remisiones", "ver_vecinos"], "arranco": true, "eventos": ["inicio", "fin"]}}
```

| Configuración | Herramientas | Tardó |
|---|---:|---:|
| `n7` | 10 | 3 s |
| `n7c_mas` | 10 | 3 s |
| `la_combinada` | 1, `buscar_pasajes` | 8 s |
| `la_densa` | 1, `buscar_pasajes` | 1 s |

Al arrancar, cada servidor comprueba las huellas de lo que usa. Este paso no llama a ninguna herramienta.

## 11. Bajar Neo4j

```bash
"$NEO4J_HOME/bin/neo4j" stop
```

## Apéndice: las referencias

| Qué | sha256 |
|---|---|
| ZIP de los 128 PDF | `91c79331beda5334dcc4fa878b10efd6bb1684a435568d8435fcabb97309e718` |
| Corpus de la E0 | `7b93dd418042475ce1b7a8707bf14d5e7e50fa7b514f619e16d7609dce36b8f9` |
| `indice_bm25.json` del índice de fragmentos | `8f57949d931ad74f0d34c169cd53f9392451e1f977a612740e5f01757df55a66` |
| `pasajes.json` | `54ee790d5a0792dbec2f4c54a8633c19012b7f18f0738610954edb7afa78ff75` |
| `manifiesto.json` del índice de puntos, sin el bloque denso | `eec47db5436dc78e562b11aad0a284f5d14f08ab83568079e2d93d43313ad9dc` |
| `manifiesto.json` del índice de puntos, completo | `ef036b67032175f32996513a81198f65ed29850bc336ba35ae445f7f20c152d6` |
| Huella del grafo, `kg.json` | `576c97256185a0d5741cb2c35a2a85e91412f3e1119ad7a85d960b7d60c35ad3` |
| Matriz de fragmentos, sus bytes | `0dd40904d5eef51aca0e47e9044240f40bedfa9dc15416128669f655b3030b5d` |

## Apéndice: `pip freeze` de `.venv`, con Python 3.10.13

```
annotated-types==0.8.0
anthropic==0.100.0
anyio==4.16.0
attrs==26.1.0
beautifulsoup4==4.14.3
certifi==2026.10.23
cffi==2.1.1
charset-normalizer==3.5.2
click==8.5.1
cryptography==50.0.2
distro==1.9.0
docstring_parser==0.18.0
exceptiongroup==1.3.1
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
httpx-sse==0.4.3
idna==3.20
jiter==0.18.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
mcp==1.29.0
neo4j==6.2.0
numpy==2.2.6
pdfminer.six==20260107
pdfplumber==0.11.10
pillow==12.3.0
pip==23.0.1
pycparser==3.11
pydantic==2.13.4
pydantic-settings==2.15.0
pydantic_core==2.46.4
PyJWT==2.15.1
pypdf==6.10.2
pypdfium2==5.15.2
python-dotenv==1.2.2
python-multipart==0.0.32
pytz==2026.6
RapidFuzz==3.14.5
referencing==0.37.0
requests==2.33.1
rpds-py==0.30.0
setuptools==65.5.0
sniffio==1.3.1
soupsieve==2.10
sse-starlette==3.5.1
starlette==1.7.0
typing-inspection==0.4.5
typing_extensions==4.16.0
urllib3==2.8.0
uvicorn==0.54.0
```

## Apéndice: `pip freeze` de `venvs/vector`, con Python 3.12.13

```
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.16.0
attrs==26.1.0
certifi==2026.10.23
cffi==2.1.1
click==8.5.1
cloudpickle==3.1.2
cryptography==50.0.2
filelock==4.2.10
fsspec==2026.9.0
h11==0.16.0
hf-xet==1.8.0
httpcore==1.0.9
httpx==0.28.1
httpx-sse==0.4.3
huggingface_hub==1.33.0
idna==3.20
Jinja2==3.1.6
joblib==1.6.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
markdown-it-py==4.2.0
MarkupSafe==3.0.4
mcp==1.29.0
mdurl==0.1.2
mpmath==1.3.0
narwhals==2.28.0
networkx==3.7
numpy==2.5.2
packaging==26.3
pip==25.0.1
pycparser==3.12
pydantic==2.14.3
pydantic-settings==2.16.2
pydantic_core==2.50.4
Pygments==2.21.0
PyJWT==2.15.1
python-dotenv==1.2.4
python-multipart==0.0.33
PyYAML==6.0.3
referencing==0.37.0
regex==2026.11.9
rich==15.0.0
rpds-py==2026.9.1
safetensors==0.8.0
scikit-learn==1.9.1
scipy==1.18.1
sentence-transformers==6.0.0
setuptools==84.2.1
shellingham==1.5.4
sse-starlette==3.7.0
starlette==1.10.0
sympy==1.14.0
threadpoolctl==3.8.0
tokenizers==0.22.2
torch==2.13.0
tqdm==4.70.1
transformers==5.15.1
typer==0.29.0
typing-inspection==0.4.5
typing_extensions==4.16.0
uvicorn==0.54.0
```
