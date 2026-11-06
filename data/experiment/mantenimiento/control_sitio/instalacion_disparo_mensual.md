# Disparo mensual del control del sitio: instrucciones de instalación

U-MANT, etapa M3. Decisión de la autora del 02/10/2026: el control corre
**mensual, solo sobre el índice**, con aviso si pasan 45 días sin una corrida
exitosa. Este documento dice cómo instalarlo. **No está instalado.** Lo
instala la autora, si decide hacerlo, con los comandos de abajo.

## Qué corre

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/control_sitio/correr_control_sitio.py --modo indice --autorizado-red
```

- **Un pedido al sitio:** el índice, con hasta 3 intentos si falla, un
  pedido cada 0,5 s, 60 s de timeout y un User-Agent propio sin datos
  personales.
- **Controla S1 a S4** contra `linea_base.json` (`supuestos_sitio.md`). S5 a
  S7 no se controlan en este modo: se controlan cuando se baja el PDF, con
  `--modo indice-y-pdfs`, como en la corrida de M3.
- **Escribe en `control_sitio/corridas/<fecha>/`:** `indice_crudo.json`,
  `resultado_control.json`, `resumen_corrida.json`, `bitacora.txt` y, si
  corresponde, `aviso.md`, `corrida_fallida.md` o `aviso_latido.md`.
- **Latido:** cada corrida en la que el índice respondió escribe su fecha en
  `control_sitio/corridas/ultima_ok.txt`.
- **Códigos de salida:**
  - 0 sin aviso;
  - 1 aviso;
  - 2 error de uso, la carpeta de esa fecha ya existe o los parámetros del
    código no son los de la línea de base;
  - 3 el índice no respondió.
- **El latido avisa cuando una corrida falla.** Si una corrida no puede
  preguntar al sitio y la última exitosa tiene más de 45 días, o no hay
  ninguna, escribe `aviso_latido.md`. Si el disparo deja de correr del todo,
  ninguna corrida avisa; para verlo, sin red:

  ```bash
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/control_sitio/correr_control_sitio.py --estado
  ```

  Informa la fecha de la última corrida exitosa y sale con 1 si pasaron más de
  45 días.

## Instalación con launchd (macOS), sin instalar todavía

1. Crear `~/Library/LaunchAgents/ar.udesa.bcra-kg.control-sitio.plist` con el
   contenido de abajo. `RUTA_DEL_REPO` es la ruta absoluta del repo; tiene
   espacios, y el plist la pasa entera como un solo argumento.

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
     <key>Label</key><string>ar.udesa.bcra-kg.control-sitio</string>
     <key>ProgramArguments</key>
     <array>
       <string>/bin/zsh</string>
       <string>-c</string>
       <string>cd "RUTA_DEL_REPO" &amp;&amp; PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/control_sitio/correr_control_sitio.py --modo indice --autorizado-red; c=$?; if [ $c -ne 0 ]; then osascript -e "display notification \"código $c: ver control_sitio/corridas\" with title \"Control del sitio del BCRA\""; fi; exit $c</string>
     </array>
     <key>StartCalendarInterval</key>
     <dict><key>Day</key><integer>1</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
     <key>StandardOutPath</key><string>/tmp/control_sitio_bcra.log</string>
     <key>StandardErrorPath</key><string>/tmp/control_sitio_bcra.log</string>
   </dict>
   </plist>
   ```

2. Cargarlo:

   ```bash
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ar.udesa.bcra-kg.control-sitio.plist
   ```

3. Probarlo una vez sin esperar al día 1. Ojo: esto hace un pedido real al
   sitio.

   ```bash
   launchctl kickstart gui/$(id -u)/ar.udesa.bcra-kg.control-sitio
   ```

4. Desinstalarlo:

   ```bash
   launchctl bootout gui/$(id -u)/ar.udesa.bcra-kg.control-sitio
   ```

## Qué tener en cuenta

- **Si la máquina no está disponible el día 1:** si está dormida, launchd
  corre la tarea al despertar; si está apagada, esa corrida se pierde y el
  latido la hace visible después. Ese comportamiento de launchd es NO
  VERIFICADO en esta máquina.
- **El aviso:** llega como notificación del sistema cuando el código no es 0,
  y queda en la carpeta de la corrida. Lo ve la autora, en esa máquina.
- **Las corridas no se commitean solas:** versionarlas es decisión de la
  autora. Los PDFs no se versionan (`.gitignore:35`).
- **Dos corridas el mismo día no se pisan:** la segunda frena con código 2.
