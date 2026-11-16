# Weekly Fondos Balanz — instrucciones para Claude

Este repo publica el tablero Weekly Fondos en https://weekly-fondos-dashboard.vercel.app/.
Vercel redeploya solo con cada push a `main`. El sitio es estático: lo único que
cambia cada semana es `index.html`.

## Cuando te piden "actualizá el weekly fondos"

El colaborador ya cargó los inputs en los Excel y corrió la macro
`Weekly_Master.xlsm` (botón "Actualizar y generar reporte" de la hoja Panel).
La macro deja el archivo `index.html` en la carpeta de OneDrive
`FCI - Matias\Weekly Fondos`. Tu trabajo empieza ahí.

1. **Conseguí el `index.html` nuevo.**
   - Si el colaborador lo adjuntó al chat, usá ese archivo.
   - Si la carpeta `Weekly Fondos` está conectada a la sesión, tomalo de ahí.
   - Si no tenés ninguna de las dos, pedile que adjunte el `index.html` de esa
     carpeta. No lo busques en otro lado ni uses versiones con fecha en el nombre.
   - Copialo siempre byte a byte. Nunca lo reescribas ni lo reconstruyas a mano.

2. **Traé lo último del repo:** `git pull origin main`.

3. **Validá e instalá:**

   ```
   python3 scripts/validar_index.py <ruta_del_index_nuevo> --instalar
   ```

   - Salida 0: sin observaciones.
   - Salida 1: hay advertencias. Mostráselas al colaborador tal cual, en
     castellano simple, y preguntale si publica igual o corrige y vuelve a
     correr la macro. No publiques sin su respuesta.
   - Salida 2: hay errores. No publiques. Explicale qué falló.
   - Salida 3: es idéntico a lo publicado. Avisale que no hay nada nuevo;
     lo más probable es que falte correr la macro.

4. **Publicá** (solo con salida 0, o salida 1 confirmada por el colaborador):

   ```
   git add index.html
   git commit -m "Actualizar Weekly Fondos al cierre DD/MM/AAAA"
   git push origin main
   ```

   Usá la fecha de cierre que informa el validador. Se publica directo a
   `main`; no abras ramas ni pull requests para la actualización semanal.

5. **Verificá la página.** Esperá el deploy (suele tardar menos de un minuto) y
   confirmá que https://weekly-fondos-dashboard.vercel.app/ contiene
   `const REPORT_DATE = "DD/MM/AAAA"` con la fecha nueva. Si a los 5 minutos
   sigue la fecha vieja, avisale al colaborador en vez de reintentar.

6. **Cerrá con un resumen corto:** fecha de cierre, patrimonio total, y las
   advertencias que quedaron publicadas, si hubo.

## Qué no hacer

- No edites los datos dentro de `index.html` para "corregir" una advertencia.
  Los datos se corrigen en los Excel y se vuelve a correr la macro.
- No abras ni modifiques los Excel de origen (`Tabla weekly Fondos.xlsx`,
  `Comments - Daily.xlsx`, `Weekly_Master.xlsm`). Tienen autoguardado.
- No toques `WEEKLY/`, `factsheets.json` ni `scripts/index-factsheets.mjs` en
  una actualización semanal.

## Cómo está armado

| Archivo | Rol |
|---|---|
| `index.html` | Tablero completo en un solo archivo: template + Chart.js + datos de la semana. Lo genera la macro. |
| `WEEKLY/` | PDF de factsheets, `AAAAMMDD.NombreFondo.esp.pdf`. Se actualizan una vez por mes. |
| `factsheets.json` | Índice del factsheet más reciente por fondo. Lo regenera solo un GitHub Action cuando cambia `WEEKLY/`. |
| `scripts/validar_index.py` | Validación previa a publicar. |
| `scripts/index-factsheets.mjs` | Generador de `factsheets.json`. |
| `.vercelignore` | Evita que estos archivos internos se sirvan en la página pública. |

El código del tablero no se edita en este repo: sale de `template.html`, que
vive en la carpeta de OneDrive junto a la macro. Un cambio de diseño o de
lógica se hace ahí y llega al repo con la siguiente corrida. Si el validador
avisa que "el código del tablero cambió", confirmá con el colaborador que
alguien modificó `template.html` a propósito.

## Actualización mensual de factsheets

Subir los PDF nuevos a `WEEKLY/` con el nombre `AAAAMMDD.NombreFondo.esp.pdf`
y hacer push. El índice se regenera solo; no edites `factsheets.json` a mano.
