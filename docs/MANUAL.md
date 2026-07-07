# Manual de arquitectura y mantenimiento de TRACEY (traceyDB)

Este documento complementa a `CLAUDE.md` (que solo explica cómo levantar el servidor de
desarrollo). Aquí se explica la arquitectura del proyecto, las vistas principales, el panel de
administración (`features.html`) y la estructura del frontend, para que cualquier persona que
retome el proyecto pueda mantenerlo sin tener que releer todo el código desde cero.

> Para cómo correr el servidor de desarrollo (intérprete de WSL/Anaconda, comando de
> `manage.py runserver`), ver `CLAUDE.md` en la raíz del repo — no se repite aquí.

## Índice

1. [Arquitectura general](#1-arquitectura-general)
2. [Referencia de vistas principales (`query-*`)](#2-referencia-de-vistas-principales-query-)
3. [`features.html` — panel de administración](#3-featureshtml--panel-de-administración)
4. [Frontend: templates, JS, includes y menús](#4-frontend-templates-js-includes-y-menús)
5. [Comandos de mantenimiento (`manage.py`)](#5-comandos-de-mantenimiento-managepy)
6. [Control de acceso (permisos de staff)](#6-control-de-acceso-permisos-de-staff)
7. [Añadir un nuevo modelo HMM](#7-añadir-un-nuevo-modelo-hmm)
8. [Notas y gotchas para el próximo desarrollador](#8-notas-y-gotchas-para-el-próximo-desarrollador)
9. [Nota sobre este documento y exportar a PDF](#9-nota-sobre-este-documento-y-exportar-a-pdf)

---

## 1. Arquitectura general

### 1.1 Layout del repositorio

```
core/               proyecto Django (settings.py, urls.py, wsgi.py, asgi.py)
apps/               única app registrada en INSTALLED_APPS ("apps.config.AppsConfig")
├── home/           la app "real": vistas, forms, modelos, plots, utils
├── authentication/ login/register/logout
├── management/commands/   comandos custom de manage.py (ver sección 5)
├── templates/      layouts, includes, menús, páginas home/ (ver sección 4)
└── static/         CSS/SCSS, JS, imágenes (ver sección 4)
utils/              scripts de bioinformática (HMM, BLAST, taxonomía NCBI, árboles filogenéticos)
                    NO es una app Django, son scripts invocados por los management commands
docs/               este manual
```

Diagramas previos (no duplicados aquí, útiles como referencia visual): `traceyStructure.pdf/pptx`,
`tracey_all_models.pdf`, `tracey_main_models.pdf`, `tracey_other_models.pdf`,
`DomaingroupsStructure.pdf/pptx`, `tree.pdf` (todos en la raíz del repo).

### 1.2 Quirk de `INSTALLED_APPS`

En `core/settings.py`, `INSTALLED_APPS` solo registra `'apps.config.AppsConfig'` — **no** registra
`apps.home` ni `apps.authentication` como apps separadas. Como el registro de apps de Django asigna
los modelos por coincidencia de prefijo de módulo, los modelos definidos en `apps/home/models.py`
terminan bajo el app-label `apps`. Por eso `apps/admin.py` registra el admin iterando
`apps.get_app_config('apps')` en vez de `apps.get_app_config('home')`. La clase `HomeConfig` en
`apps/home/apps.py` existe pero, al no estar en `INSTALLED_APPS`, es efectivamente código muerto.

### 1.3 Base de datos

El backend es MySQL (`core/settings.py`, `ENGINE: django.db.backends.mysql`), apuntando a un
esquema **preexistente**. Todos los modelos en `apps/home/models.py` tienen `managed = False`.
Esto implica:

- Los cambios de esquema **no se hacen con `makemigrations`/`migrate`**. Hay que modificar la base
  MySQL directamente (o vía los dumps `.sql` en `utils/`) y luego reflejar el cambio a mano en
  `models.py`.
- `apps/migrations/` solo tiene `0001_initial.py` — no hay historial real de migraciones que
  mantener.

### 1.4 Enrutamiento (`core/urls.py` → `apps/home/urls.py`)

`core/urls.py` incluye, en orden: `admin/`, `apps.authentication.urls` (login/register/logout),
`captcha/`, `robots.txt`, `sitemap.xml`, y **al final** `apps.home.urls`. El comentario en el propio
archivo advierte que `apps.home.urls` debe quedar último, porque termina en un catch-all:

```python
re_path(r'^.*\.*', views.pages, name='pages')
```

La vista `pages()` (en `apps/home/views_query.py`) toma el último segmento de la URL y carga
`home/<segmento>.html` directamente como template — así es como funcionan páginas sueltas como
`/contact.html` sin necesidad de una ruta explícita. `updates.html` está protegida detrás de login
mediante el set `_PAGES_REQUIRES_LOGIN`.

### 1.5 Patrón de vistas "por grupo"

Las vistas están repartidas en varios módulos dentro de `apps/home/`, agrupadas por familia
funcional, y `views.py` actúa como **agregador único**: hace imports explícitos con nombre desde
cada módulo y los re-exporta. `urls.py` solo hace `from apps.home import views` y llama
`views.<Nombre>` — nunca importa un submódulo directamente.

| Módulo | Familia de vistas |
|---|---|
| `apps/home/views_query.py` | `query-sequences`, `query-sequences-results`, exportación FASTA/multialineamiento, visor 3D, `query-sequence-details`, endpoints ajax de autocompletado y dropdowns en cascada |
| `apps/home/views_motifs.py` | `query-motifs`, `query-motifs-results`, y el helper `motifScan` (motor de escaneo HMM compartido) |
| `apps/home/views_verify.py` | `query-insert`, `query-verify` (menú y vista de curación), `query-verify-blast` |
| `apps/home/views_trees.py` | Vista de árboles filogenéticos (`trees`) |
| `apps/home/views_admin.py` | `features.html` y todas sus acciones (ver sección 3) |

Si se agrega una vista nueva, debe añadirse tanto en su módulo `views_*.py` correspondiente como en
el import explícito de `apps/home/views.py` para que quede expuesta a `urls.py`.

### 1.6 Convención `segment` (resaltado de menú)

Cada vista calcula a mano una variable de contexto `segment` (típicamente
`request.path.split('/')[-1]` o una variante) y la pasa al template. `includes/sidebar.html` usa
esa variable en condicionales `{% if 'query' in segment %}` para resaltar el ítem de menú activo.

**No hay un context processor central para esto** — es un patrón copiado vista por vista. Si se
agrega una vista nueva y se olvida definir `segment`, el resaltado del menú lateral simplemente no
funcionará para esa página (falla silenciosa, sin error).

### 1.7 Modelos clave

Todos en `apps/home/models.py`, `managed = False` (ver PDFs de modelos en la raíz para el esquema
completo):

| Modelo | Propósito |
|---|---|
| `Sequences` | Entidad central: una secuencia de proteína/gen (anotación, estado, taxonomía, gen asociado) |
| `Motifs` | Hits de motivos HMM **verificados/activos** sobre una secuencia |
| `Verifymotifs` | Espejo de `Motifs` para hits **pendientes de verificar** (flujo de `query-verify`) |
| `Domaingroups` | Grupos de dominios funcionales/estructurales, con jerarquía de padres (`domaingroupparent_id`, puede tener varios separados por `;`) |
| `Domains` | Dominio de proteína de más alto nivel (SNARE, Habc, Longin, LGL, …) |
| `Taxonomies` | Nodo del árbol taxonómico propio de TRACEY (nombre científico, rango, padre) |
| `Methods` | Cómo se generó un motivo/verifymotivo (`type = 'hmm'` o `'manual'`) |

---

## 2. Referencia de vistas principales (`query-*`)

### `QuerySequences` / `QuerySequencesResults`
*Archivo: `apps/home/views_query.py`. URLs: `query-sequences`, `query-sequences-results`.*

- `QuerySequences` renderiza el formulario de búsqueda (`home/query-sequences.html`). Contexto
  clave: `domainsList`, `proteinLayoutsList` (desde `get_menu(request)`, distingue menú staff vs
  público), `shortnames` (cacheado 24h), `taxonomy_ranks`, `form` (`FamilyForm`), `is_staff`,
  `error` (mensaje de sesión si la búsqueda anterior dio 0 resultados).
- `QuerySequencesResults` ejecuta la búsqueda real delegando en `get_sequences()`
  (`apps/home/utils.py`), que combina filtros no relacionados a motivos (alias, estado, especie,
  subárbol de taxonomía vía BFS) con filtros de motivos (dominio/domaingroup/proteinlayout) y separa
  resultados verificados (`Motifs`) de no verificados (`Verifymotifs`). Límite duro de 4000 filas.
  Contexto clave: `sequences`, `speciesname`, `motifnames`, `hmmModels` (lista de `.hmm` disponibles
  para generar MSA).

### `QuerySequencesFastaFormat`
*URL: `query-sequences-fasta` (POST).*

Endpoint de exportación con 4 modos según el campo de POST presente: descarga de tabla TSV, FASTA
plano por secuencia, FASTA por motivo (extraído del XML en `asciioutput`), o multialineamiento HMM
(vía `pyhmmer.hmmalign`) para ver/descargar.

### `QuerySequences3dViewer`
*URL: `query-sequences-3dViewer/<sequence_id>`.*

Renderiza el visor 3D (3Dmol.js) para una secuencia. Contexto clave: `sequence`, `fetch3d` (URL de
AlphaFold), `motif_coords` (coordenadas reales de cada domaingroup, recalculadas contra la secuencia
completa). Usa `user_can_access_sequence()` (`apps/home/utils.py`) para verificar que todos los
domaingroups de la secuencia estén dentro del menú permitido al usuario (staff vs público);
lanza `Http404` si no.

### `QuerySequencesDetails` (`query-sequence-details`)
*URL: `query-sequences/<sequence_id>/details/`.*

Página de detalle de una secuencia. Contexto clave: `sequence`, `speciesname`, `wiki_image`,
`pdb`/`pdb_name` (parseado de `foreignannotation`), `fetch3d`, `layout` (plot SVG vía
`build_domain_plot()`), y `motifs` — diccionario por cada `Motifs` activo con su cadena de
domaingroup-padre, campos parseados del XML de `asciioutput` (consensus, similarity, e-value) y un
plot individual por motivo. Misma verificación de acceso que el visor 3D.

### `DetailsSequencesFastaFormat`
*URL: `details/fastaFormat/<sequence_id>/`.* Descarga FASTA simple de una secuencia, con el mismo
control de acceso.

### `QueryMotifsView` / `QueryMotifsResultsView`
*Archivo: `apps/home/views_motifs.py`. URLs: `query-motifs`, `query-motifs-results`.*

Formulario para escanear una secuencia pegada a mano contra los HMMs de TRACEY (sin necesidad de
que la secuencia ya exista en la base). `QueryMotifsView` valida la entrada (no vacía, ≤2000 aa) y
redirige a `QueryMotifsResultsView`, que llama al helper `motifScan()`.

**`motifScan()`** (mismo archivo) es el motor de escaneo HMM reutilizado también por
`QueryInsertView` y `QueryVerifyView`: valida que la entrada no sea FASTA, corre `pyhmmer` contra el
subconjunto de `.hmm` relevante (o `MOTIFS.hmmDb` completo si `proteinlayout == "ALL"`), filtra por
`evalcutoff`, resuelve nombres de domaingroup/dominio y coordenadas reales de alineamiento, y
devuelve `hits_d` (dict de hits ordenado por p-value ascendente).

### `QueryInsertView` (`query-insert`)
*Archivo: `apps/home/views_verify.py`. Solo staff (`@login_required` + `@staff_login_required`).*

Formulario para insertar una secuencia nueva (`InsertSequence` ModelForm). Al guardar, crea el
`Sequences`, corre `motifScan(..., ["ALL"])` inmediatamente, persiste los hits como
`Verifymotifs` vía `saveVerifyMotifs()`, y redirige a `query-verify` para esa secuencia. Si falla el
guardado o el escaneo, revierte borrando el `Genes` recién creado.

### `QueryVerifyMenuView` / `QueryVerifyView` (`query-verify`)
*Archivo: `apps/home/views_verify.py`. Solo staff.*

- `QueryVerifyMenuView` (`query-verify`, sin id) es la página de listado/menú de secuencias
  pendientes de curar; la tabla real se carga por ajax vía `load_queryverifysequences`
  (`apps/home/views_query.py`, template parcial `home/query-verify-update-sequences.html`).
- `QueryVerifyView` (`query-verify/<sequence_id>`) es la vista de trabajo de curación, la más
  compleja del proyecto. Desde el mismo formulario se puede: verificar/promover un `Verifymotifs` a
  `Motifs` (o al revés, "unverify"), borrar motivos o toda la secuencia, re-escanear
  (`motifScan` + `saveVerifyMotifs`), o añadir un motivo manual (`add_manual_motif`, crea un
  `Methods` con `type='manual'`). Cada acción agrega una línea de auditoría al campo `changelog` de
  la secuencia.

### `QueryVerifyBlastView` (`query-verify-blast`)
*URL: `query-verify/traceyBLAST/<db>/<query_id>`.*

Compara una secuencia/motivo/verifymotivo contra una de las bases BLAST locales de TRACEY (o
redirige al BLAST público de NCBI si `db` lo indica), usando el binario local en
`utils/ncbi-blast-2.13.0+/bin/blastp`, y renderiza el resultado como un visor de alineamiento con
colores.

### Endpoints ajax de soporte

Un conjunto de vistas GET pequeñas en `views_query.py` (`load_taxonomy_rank`, `load_species`,
`load_domains`, `load_domaingroups_rank1/2`, `load_sequenceshortnames`,
`load_taxonomy_by_shortname`, `suggest_aliases`, `updateSequenceStatus`) y en `views_verify.py`
(`suggestNames`, `autocompleteModel`) alimentan los dropdowns en cascada y el autocompletado de los
formularios de búsqueda/inserción/verificación. No se detallan uno a uno aquí — todos siguen el
mismo patrón: reciben un parámetro del nivel superior y devuelven HTML parcial o JSON con las
opciones del siguiente nivel.

---

## 3. `features.html` — panel de administración

*Template: `apps/templates/home/features.html`. Vista: `features()` en
`apps/home/views_admin.py`. Solo staff.*

Es el panel de mantenimiento de datos de TRACEY: seis tarjetas, cada una con su propio formulario +
llamada ajax + script inline al final del archivo.

| Feature | Qué hace | Endpoint ajax | Script/comando detrás |
|---|---|---|---|
| **Update Taxonomies** | Refresca la tabla de taxonomías contra NCBI actual; crea taxones nuevos si hace falta. Tarda ~10 min. | `ajax_update_taxonomy` → `views.update_taxonomy` | `utils/ncbi_taxonomy/TaxonomyUpdater.py`, mismo motor que `manage.py UpdateTraceyTaxonomies` |
| **Update TRACEY Sequences** | Resincroniza secuencias "live" que tengan ID de NCBI contra los datos actuales (las que no tienen ID de NCBI no se tocan). Filtrable por especie/familia. Puede tardar horas. | `ajax_update_sequences` → `views.update_sequences` | `utils/traceySequenceUpdater/traceySequencesUpdater.py`, mismo motor que `manage.py UpdateTraceySequences` |
| **Re-scan Motifs** | Re-corre el escaneo HMM sobre secuencias existentes para refrescar `Motifs`/`Verifymotifs`. Filtros: especie, familia/dominio/HMM específico, umbral de e-value, "solo activas", modo **dry-run** (abre resultado en pestaña nueva sin persistir). | `ajax_rescan_motifs` → `views.rescan_motifs` | `utils/motifPredictor/reScanMotifs.py`, mismo motor que `manage.py ReScanMotifs` |
| **Upload new sequences** | Sube un FASTA de secuencias nuevas; TRACEY las analiza contra los HMMs y asigna el mejor motivo automáticamente. | `ajax_upload_sequences` → `views.upload_sequences` | Formato de encabezado FASTA requerido documentado en `home/help_doc_upload_sequences.html` |
| **HMM Models (download)** | Descarga los perfiles HMM de TRACEY (una familia o la base completa) para usar externamente con `hmmsearch`/`hmmscan`. | `download_hmm_zip` (navegación directa, no ajax) | Cataloga `.hmm` en `utils/hmmModels/` vía `get_hmm_catalog()` |
| **Build Phylogenetic Tree** | Reconstruye el árbol de la vida para todas las taxonomías presentes en TRACEY, siguiendo la filogenia NCBI actual. Da enlaces de descarga del árbol en Newick y PDF. | `ajax_update_tree` → `views.update_tree` | `utils/ncbi_taxonomy/TreeUpdater.py`, mismo motor que `manage.py UpdateTraceyTree` |

Patrón común a las seis: token CSRF en cada formulario, spinner + mensaje de estado, y un flag
compartido (`reloadOnAjaxStop`) que recarga la página cuando termina cualquiera de estas llamadas
largas, para refrescar los timestamps de "última actualización".

---

## 4. Frontend: templates, JS, includes y menús

### 4.1 Árbol de templates (`apps/templates/`)

```
layouts/
  base.html              layout principal (sidebar + contenido + footer)
  base-fullscreen.html   variante sin sidebar (parece SIN USO actualmente, ver sección 8)
  sequenceForm.html       formulario grande de insertar/verificar secuencia (es un include, no un base)
includes/
  sidebar.html           menú de navegación (hardcodeado, ver 4.3)
  footer.html            pie de página (logos de socios)
  scripts.html           bundle de JS común (Popper, Bootstrap, Chartist, SweetAlert2, moment.js, volt.js, …)
  settings-box.html      widget de tema de Volt (comentado en base.html, sin uso)
accounts/                login.html, register.html
home/                    ~30 templates de página + partials/_motif_card.html
menus/                   NO son templates HTML — módulos Python (ver 4.3)
```

`layouts/base.html` define los bloques `title`, `og_title`, `og_description`, `stylesheets`,
`content`, `javascripts`. La mayoría de templates de `home/` y `accounts/` lo extienden
directamente (una sola capa de herencia, sin cadenas más profundas).

Algunos templates de `home/` **no son páginas completas**: son fragmentos HTML devueltos
directamente por vistas ajax (p. ej. `query-sequences-fasta.html`,
`query-verify-update-sequences.html`, dropdowns de opciones). Otros son documentos HTML
independientes que se abren en pestaña nueva (`query-sequences-3dViewer.html`,
`query-verify-blast.html`, cada uno con su propio `<!DOCTYPE html>`).

`home/partials/_motif_card.html` se reutiliza dos veces en `layouts/sequenceForm.html`: una para
`verifymotifs` (con opción Verificar/Borrar) y otra para `motifs` (con opción Anular
verificación/Borrar).

### 4.2 JS principales (`apps/static/assets/js/`)

| Archivo | Rol |
|---|---|
| `volt.js` | JS del tema Volt (Bootstrap 5): SweetAlert2, panel de settings, chrome general del tema |
| `sequenceForm-dropdowns.js` | Cascada de dropdowns proteinlayout → domain → domaingroup → domainsubgroup en el formulario de insertar/verificar (y su variante "manual") |
| `sequenceForm-utils.js` | `suggestNames()` (ajax a `ajax_suggestNames`) y `searchOpen()` (autocompletado de taxonomía vía `/search.json`) |
| `ngl-viewer.js` | Visor 3D basado en **NGL.js**, usado en el formulario de insertar/verificar secuencia (colorea por dominio, resalta residuos) |
| `django-htmx.js` | Helper de debug de `django_htmx`: en `DEBUG=True`, reemplaza respuestas de error HTMX por la página de debug de Django |
| `jquery-4.0.0.min.js` | jQuery, cargado por página (no globalmente desde `base.html`) donde haga falta AJAX/manipulación de DOM |

**Importante:** las páginas de detalle/visor 3D independiente (`query-sequences-3dViewer.html`,
`query-sequences-details.html`) usan en cambio **3Dmol.js por CDN**
(`https://3Dmol.org/build/3Dmol-min.js`). Es decir, TRACEY tiene **dos visores 3D distintos** según
la página: NGL.js (local) en el flujo de insertar/verificar, y 3Dmol.js (CDN) en las páginas de
consulta pública. Si se toca la funcionalidad de visualización 3D, hay que revisar ambos.

### 4.3 Cómo TRACEY arma los menús

Hay dos conceptos distintos que se llaman "menu" y conviene no confundir:

1. **Menú de navegación (sidebar)** — `includes/sidebar.html`. Es HTML **hardcodeado**, no se
   genera desde la base de datos ni desde una estructura Python. El resaltado del ítem activo se
   hace con condicionales Django (`{% if 'query' in segment %}`) sobre la variable `segment` que
   cada vista calcula a mano (ver 1.6). El único context processor real en juego es
   `apps/context_processors.py:cfg_assets_root`, que solo inyecta `ASSETS_ROOT` para las rutas de
   estáticos.
2. **"Menú" de familias de proteínas** — `apps/templates/menus/query_sequences.py` y
   `query_sequences_full.py`. A pesar de vivir bajo `templates/` y tener extensión `.py`, **no son
   templates de Django**: son módulos Python con un diccionario anidado (`menu = {...}`) que
   describe la jerarquía familia de proteína → dominio → domaingroup (SNARE, Ras, AAA, …), más
   funciones helper (`get_keys_recursively()`, `get_dict()`). Las vistas los importan para poblar
   los dropdowns en cascada de Query/Insert/Verify/Features. No tiene relación con la navegación de
   la UI.

### 4.4 CSS / SCSS

Tema base "Volt" (Bootstrap 5, AppSeed/Themesberg), compilado de SCSS (`apps/static/assets/scss/`)
a CSS (`apps/static/assets/css/volt.css`). Personalización propia del proyecto en
`scss/custom/_variables.scss` y `css/sequenceForm.css` (estilos del formulario de
insertar/verificar). El CSS específico de `features.html` (loaders, grid de `.feature-card`) está
inline en el propio template en vez de en un archivo separado.

---

## 5. Comandos de mantenimiento (`manage.py`)

Definidos en `apps/management/commands/`. Cada uno tiene una feature equivalente en
`features.html` (sección 3) que dispara la misma lógica desde la UI:

| Comando | Qué hace |
|---|---|
| `UpdateTraceySequences` | Refresca secuencias "live" con ID de NCBI. Flags: `--continue`, `--force`, `--onlyActive`, `--species`, `--traceyIds`, `--domain` |
| `UpdateTraceyTaxonomies` | Refresca taxonomías desde NCBI. Flag `--taxa` (default `superkingdom`) |
| `UpdateTraceyTree` | Reconstruye el árbol filogenético |
| `ReScanMotifs` | Re-escanea HMMs sobre secuencias existentes. Requiere `--hmm` o `--family` |
| `plotTaxonomy` | Comando de diagnóstico: dibuja el árbol/red de taxonomía para un nombre científico dado (no forma parte del pipeline de datos) |

---

## 6. Control de acceso (permisos de staff)

Las secciones de manejo de la base de datos — `features.html`, `query-insert`, `query-verify`
(y su sub-vista de BLAST) — están protegidas con `@login_required` + `@staff_login_required`
(`apps/home/views_verify.py`, `apps/home/views_admin.py`), que comprueban
`request.user.is_staff`. Un usuario registrado normal **no** tiene acceso a estas secciones;
solo lo tienen los usuarios marcados como staff.

Para dar acceso a un usuario que ya se ha registrado:

1. Entrar a `tracey.unil.ch/admin` (admin de Django) con una cuenta de superusuario/staff.
2. Abrir la sección **Users**, seleccionar el usuario en cuestión.
3. Marcar "Staff status" (y cualquier permiso/grupo relevante) y guardar.

**Cuidado con no confundir dos modelos distintos llamados "User":** el que se edita aquí es el
modelo estándar `auth.User` de Django (el que gestiona `/admin`). Existe además una tabla `User`
legada en `apps/home/models.py` (`managed = False`), que es una tabla de autenticación previa a
Django y no tiene relación con el control de acceso actual — no es la que hay que tocar para dar
permisos.

## 7. Añadir un nuevo modelo HMM

Para añadir un nuevo perfil HMM a TRACEY:

1. Incluir el archivo `.hmm` en `utils/hmmModels/`, dentro de la carpeta de la familia de
   proteína correspondiente (por ejemplo `RAS`, `C2`, `HABC`, `LONGIN`, `ARF`, `PROPPIN`,
   `RHOMBOID`, `MUN.D1`/`MUN.D2`, `NSR.CD`/`NSR.MD`/`NSR.ND`, `AAA.AAA`/`AAA.ND`), o crear una
   carpeta nueva si el HMM pertenece a una familia que todavía no existe.
2. Generar en la base de datos el `Domaingroups` correspondiente a ese HMM (enlazado a su
   `Domains` padre) — el escaneo de motivos (`motifScan()`, `apps/home/views_motifs.py`)
   resuelve cada hit de HMM contra un registro de `Domaingroups`, así que un `.hmm` sin su
   `Domaingroups` correspondiente no se podrá clasificar/mostrar correctamente.
3. Añadir manualmente el nuevo dominio/domaingroup al menú de dominios —
   `apps/templates/menus/query_sequences.py` y `query_sequences_full.py` (ver 4.3) — para que
   aparezca en los dropdowns en cascada de Query/Insert/Verify/Features. Este paso es manual: no
   hay sincronización automática entre la tabla `Domaingroups` y estos diccionarios de menú.

---

## 8. Notas y gotchas para el próximo desarrollador

- **Los cambios de esquema de base de datos NO se hacen con `makemigrations`/`migrate`** — todos
  los modelos son `managed = False` sobre un MySQL preexistente (ver 1.3).
- `HomeConfig` (`apps/home/apps.py`) no está en `INSTALLED_APPS` — parece código muerto.
- `layouts/base-fullscreen.html` no es extendido por ningún template actual — verificar si sigue
  haciendo falta antes de tocarlo o borrarlo.
- `jquery-3.3.1.min.js` y el script `paginatedTable.js` no parecen referenciados activamente
  (el único `<script>` que usa `paginatedTable.js` está comentado en
  `query-sequences-results.html`) — confirmar antes de asumir que están en uso.
- Los modelos `PollsChoice`/`PollsQuestion` en `models.py` son sobrantes del tutorial/boilerplate
  de Django/AppSeed, no parecen tener relación con TRACEY.
- Hay dos dumps completos de MySQL dentro de `utils/` (`tracey_20180606_0400.dump2`,
  `tracey_20251208.backup.sql`, ~1.6-1.7 GB cada uno) versionados en el repo — vale la pena
  sacarlos del control de versiones (o usar Git LFS) salvo que exista una razón deliberada para
  mantenerlos ahí.
- TRACEY tiene **dos visores 3D distintos** (NGL.js vs 3Dmol.js por CDN) según la página — ver 4.2.
- El resaltado de menú depende de que cada vista nueva defina `segment` a mano — no hay
  mecanismo automático (ver 1.6).

---

## 9. Nota sobre este documento y exportar a PDF

Este manual se mantiene en Markdown a propósito: se versiona junto al código, se puede editar sin
herramientas especiales, y se renderiza directamente en GitHub/GitLab/VSCode. Si en algún momento
se necesita una versión en PDF, se puede generar con:

```bash
pandoc docs/MANUAL.md -o manual.pdf
```

El WSL de este entorno ya tiene `pandoc` instalado, pero **no** un motor de renderizado a PDF
(`pdflatex`/`xelatex`, `wkhtmltopdf` o `weasyprint`) — habría que instalar uno de esos antes de que
el comando anterior funcione.
