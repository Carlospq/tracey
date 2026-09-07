# TRACEY (traceyDB) — Architecture & Maintenance Manual

This document explain the project's architecture, the main views, the admin panel (`features.html`), and the
frontend structure, so that anyone picking up the project can maintain it without having to reread
the whole codebase from scratch.

## Running the dev server

```bash
/path/to/env/with/django/bin/python manage.py runserver localhost:8000
```

## Table of contents

1. [General architecture](#1-general-architecture)
2. [Reference of the main views (`query-*`)](#2-reference-of-the-main-views-query-)
3. [`features.html` — admin panel](#3-featureshtml--admin-panel)
4. [Frontend: templates, JS, includes and menus](#4-frontend-templates-js-includes-and-menus)
5. [Maintenance commands (`manage.py`)](#5-maintenance-commands-managepy)
6. [Access control (staff permissions)](#6-access-control-staff-permissions)
7. [Adding a new HMM model and generating its Domaingroups](#7-adding-a-new-hmm-model-and-generating-its-domaingroups)
8. [Notes and gotchas for the next developer](#8-notes-and-gotchas-for-the-next-developer)
9. [Note on this document and exporting to PDF](#9-note-on-this-document-and-exporting-to-pdf)

---

## 1. General architecture

### 1.1 Repository layout

```
core/               Django project (settings.py, urls.py, wsgi.py, asgi.py)
apps/               only app registered in INSTALLED_APPS ("apps.config.AppsConfig")
├── home/           the "real" app: views, forms, models, plots, utils
├── authentication/ login/register/logout
├── management/commands/   custom manage.py commands (see section 5)
├── templates/      layouts, includes, menus, home/ pages (see section 4)
└── static/         CSS/SCSS, JS, images (see section 4)
utils/              bioinformatics scripts (HMM, BLAST, NCBI taxonomy, phylogenetic trees)
                    NOT a Django app, these are scripts invoked by the management commands
docs/               this manual
```

Prior diagrams (not duplicated here, useful as visual reference): `traceyStructure.pdf/pptx`,
`tracey_all_models.pdf`, `tracey_main_models.pdf`, `tracey_other_models.pdf`,
`DomaingroupsStructure.pdf/pptx`, `tree.pdf` (all at the repo root).

### 1.2 The `INSTALLED_APPS` quirk

In `core/settings.py`, `INSTALLED_APPS` only registers `'apps.config.AppsConfig'` — it does **not**
register `apps.home` or `apps.authentication` as separate apps. Since Django's app registry assigns
models by module-path prefix matching, models defined in `apps/home/models.py` end up under the
`apps` app-label. That's why `apps/admin.py` registers the admin by iterating
`apps.get_app_config('apps')` instead of `apps.get_app_config('home')`. The `HomeConfig` class in
`apps/home/apps.py` exists but, since it's not in `INSTALLED_APPS`, is effectively dead code.

### 1.3 Database

The backend is MySQL (`core/settings.py`, `ENGINE: django.db.backends.mysql`), pointing at a
**pre-existing** schema. All models in `apps/home/models.py` have `managed = False`. This means:

- Schema changes are **not** done with `makemigrations`/`migrate`. The MySQL database has to be
  modified directly (or via the `.sql` dumps in `utils/`), and the change then reflected by hand in
  `models.py`.
- `apps/migrations/` only has `0001_initial.py` — there is no real migration history to maintain.

**Backups:** the server keeps up to 30 daily backups of the database (one per day; once the cap
is reached, the oldest backup is deleted as each new one is created). To work on a local copy,
download the most recent backup from the server and restore it into a local MySQL instance:

1. Copy the latest backup file from the server (SCP/SSH):
   ```bash
   scp <user>@<server>:/path/to/backups/<latest-backup>.sql ./utils/
   ```
2. Create a local database and import the dump:
   ```bash
   mysql -u <local_user> -p -e "CREATE DATABASE tracey_local CHARACTER SET utf8mb4"
   mysql -u <local_user> -p tracey_local < utils/<latest-backup>.sql
   ```
3. Point `.env` (repo root) at the local database — `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
   `DB_HOST=localhost`, `DB_PORT` (see `core/settings.py`, `DATABASES`).
4. Run the dev server as usual (see the top of this document) — Django will connect to the local
   copy instead of the server's database.

Downloaded dump files should **not** be committed — `.gitignore` already excludes
`utils/*.backup.sql` and `utils/tracey_20180606_0400.dump2`.

### 1.4 Routing (`core/urls.py` → `apps/home/urls.py`)

`core/urls.py` includes, in order: `admin/`, `apps.authentication.urls`
(login/register/logout), `captcha/`, `robots.txt`, `sitemap.xml`, and **last** `apps.home.urls`.
A comment in the file itself warns that `apps.home.urls` must stay last, because it ends with a
catch-all:

```python
re_path(r'^.*\.*', views.pages, name='pages')
```

The `pages()` view (in `apps/home/views_query.py`) takes the last URL segment and loads
`home/<segment>.html` directly as a template — that's how standalone pages like `/contact.html`
work without an explicit route. `updates.html` is gated behind login via the `_PAGES_REQUIRES_LOGIN`
set.

### 1.5 The "grouped views" pattern

Views are split across several modules inside `apps/home/`, grouped by functional family, and
`views.py` acts as a **single aggregator**: it does explicit named imports from each module and
re-exports them. `urls.py` only does `from apps.home import views` and calls `views.<Name>` — it
never imports a sub-module directly.

| Module | View family |
|---|---|
| `apps/home/views_query.py` | `query-sequences`, `query-sequences-results`, FASTA/multialignment export, 3D viewer, `query-sequence-details`, ajax endpoints for autocomplete and cascading dropdowns |
| `apps/home/views_motifs.py` | `query-motifs`, `query-motifs-results`, and the `motifScan` helper (shared HMM-scanning engine) |
| `apps/home/views_verify.py` | `query-insert`, `query-verify` (curation menu and view), `query-verify-blast` |
| `apps/home/views_trees.py` | Phylogenetic tree view (`trees`) |
| `apps/home/views_admin.py` | `features.html` and all its actions (see section 3) |

If a new view is added, it must be added both in its corresponding `views_*.py` module and in the
explicit import list in `apps/home/views.py` so it's exposed to `urls.py`.

### 1.6 The `segment` convention (menu highlighting)

Each view manually computes a `segment` context variable (typically
`request.path.split('/')[-1]` or a variant) and passes it to the template. `includes/sidebar.html`
uses that variable in conditionals such as `{% if 'query' in segment %}` to highlight the active
menu item.

**There is no central context processor for this** — it's a pattern copy-pasted view by view. If a
new view is added and `segment` is forgotten, the sidebar highlighting simply won't work for that
page (a silent failure, no error).

### 1.7 Key models

All in `apps/home/models.py`, `managed = False` (see the model PDFs at the repo root for the full
schema):

| Model | Purpose |
|---|---|
| `Sequences` | Central entity: a protein/gene sequence (annotation, status, taxonomy, associated gene) |
| `Motifs` | **Verified/active** HMM motif hits on a sequence |
| `Verifymotifs` | Mirror of `Motifs` for hits **pending verification** (the `query-verify` workflow) |
| `Domaingroups` | Functional/structural domain groups, with a parent hierarchy (`domaingroupparent_id`, can have several parents separated by `;`) |
| `Domains` | Top-level protein domain (SNARE, Habc, Longin, LGL, …) |
| `Taxonomies` | Node in TRACEY's own taxonomy tree (scientific name, rank, parent) |
| `Methods` | How a motif/verifymotif was generated (`type = 'hmm'` or `'manual'`) |

---

## 2. Reference of the main views (`query-*`)

### `QuerySequences` / `QuerySequencesResults`
*File: `apps/home/views_query.py`. URLs: `query-sequences`, `query-sequences-results`.*

- `QuerySequences` renders the search form (`home/query-sequences.html`). Key context:
  `domainsList`, `proteinLayoutsList` (from `get_menu(request)`, distinguishes staff vs public
  menu), `shortnames` (cached 24h), `taxonomy_ranks`, `form` (`FamilyForm`), `is_staff`, `error`
  (session message if the previous search returned 0 results).
- `QuerySequencesResults` runs the actual search by delegating to `get_sequences()`
  (`apps/home/utils.py`), which combines non-motif filters (aliases, status, species, taxonomy
  subtree via BFS) with motif filters (domain/domaingroup/proteinlayout), and splits results into
  verified (`Motifs`) vs unverified (`Verifymotifs`). Hard cap of 4000 rows. Key context:
  `sequences`, `speciesname`, `motifnames`, `hmmModels` (list of available `.hmm` files for
  generating an MSA).

### `QuerySequencesFastaFormat`
*URL: `query-sequences-fasta` (POST).*

Export endpoint with 4 modes depending on which POST field is present: TSV table download, plain
per-sequence FASTA, per-motif FASTA (extracted from the XML in `asciioutput`), or HMM
multialignment (via `pyhmmer.hmmalign`) to view/download.

### `QuerySequences3dViewer`
*URL: `query-sequences-3dViewer/<sequence_id>`.*

Renders the 3D viewer (3Dmol.js) for a sequence. Key context: `sequence`, `fetch3d` (AlphaFold
URL), `motif_coords` (real coordinates of each domaingroup, recomputed against the full sequence).
Uses `user_can_access_sequence()` (`apps/home/utils.py`) to verify that all of the sequence's
domaingroups are within the menu allowed for the caller (staff vs public); raises `Http404`
otherwise.

### `QuerySequencesDetails` (`query-sequence-details`)
*URL: `query-sequences/<sequence_id>/details/`.*

Sequence detail page. Key context: `sequence`, `speciesname`, `wiki_image`, `pdb`/`pdb_name`
(parsed out of `foreignannotation`), `fetch3d`, `layout` (SVG plot via `build_domain_plot()`), and
`motifs` — a dict per active `Motifs` entry with its domaingroup-parent chain, fields parsed out of
the `asciioutput` XML (consensus, similarity, e-value), and an individual plot per motif. Same
access check as the 3D viewer.

### `DetailsSequencesFastaFormat`
*URL: `details/fastaFormat/<sequence_id>/`.* Simple FASTA download of a sequence, with the same
access control.

### `QueryMotifsView` / `QueryMotifsResultsView`
*File: `apps/home/views_motifs.py`. URLs: `query-motifs`, `query-motifs-results`.*

Form to scan a hand-pasted sequence against TRACEY's HMMs (no need for the sequence to already
exist in the database). `QueryMotifsView` validates the input (non-empty, ≤2000 aa) and redirects
to `QueryMotifsResultsView`, which calls the `motifScan()` helper.

**`motifScan()`** (same file) is the HMM-scanning engine also reused by `QueryInsertView` and
`QueryVerifyView`: it validates the input isn't FASTA-formatted, runs `pyhmmer` against the
relevant subset of `.hmm` files (or the full `MOTIFS.hmmDb` if `proteinlayout == "ALL"`), filters by
`evalcutoff`, resolves domaingroup/domain names and real alignment coordinates, and returns
`hits_d` (a hits dict sorted by ascending p-value).

### `QueryInsertView` (`query-insert`)
*File: `apps/home/views_verify.py`. Staff-only (`@login_required` + `@staff_login_required`).*

Form to insert a new sequence (`InsertSequence` ModelForm). On save, it creates the `Sequences`
row, immediately runs `motifScan(..., ["ALL"])`, persists the hits as `Verifymotifs` via
`saveVerifyMotifs()`, and redirects to `query-verify` for that sequence. If saving or scanning
fails, it rolls back by deleting the newly created `Genes` row.

### `QueryVerifyMenuView` / `QueryVerifyView` (`query-verify`)
*File: `apps/home/views_verify.py`. Staff-only.*

- `QueryVerifyMenuView` (`query-verify`, no id) is the listing/menu page for sequences pending
  curation; the actual table is loaded via ajax through `load_queryverifysequences`
  (`apps/home/views_query.py`, partial template `home/query-verify-update-sequences.html`).
- `QueryVerifyView` (`query-verify/<sequence_id>`) is the curation workbench view, the most
  complex view in the project. From the same form you can: verify/promote a `Verifymotifs` to
  `Motifs` (or the reverse, "unverify"), delete motifs or the whole sequence, re-scan
  (`motifScan` + `saveVerifyMotifs`), or add a manual motif (`add_manual_motif`, creates a
  `Methods` row with `type='manual'`). Each action appends an audit line to the sequence's
  `changelog` field.

### `QueryVerifyBlastView` (`query-verify-blast`)
*URL: `query-verify/traceyBLAST/<db>/<query_id>`.*

Compares a sequence/motif/verifymotif against one of TRACEY's local BLAST databases (or redirects
to public NCBI BLAST if `db` indicates so), using the local `blastp` binary at
`utils/ncbi-blast-2.13.0+/bin/blastp`, and renders the result as a colored alignment viewer.

### Supporting ajax endpoints

A set of small GET views in `views_query.py` (`load_taxonomy_rank`, `load_species`,
`load_domains`, `load_domaingroups_rank1/2`, `load_sequenceshortnames`,
`load_taxonomy_by_shortname`, `suggest_aliases`, `updateSequenceStatus`) and in `views_verify.py`
(`suggestNames`, `autocompleteModel`) feed the cascading dropdowns and autocomplete of the
search/insert/verify forms. They're not detailed one by one here — they all follow the same
pattern: receive a parameter from the level above and return partial HTML or JSON with the options
for the next level.

---

## 3. `features.html` — admin panel

*Template: `apps/templates/home/features.html`. View: `features()` in
`apps/home/views_admin.py`. Staff-only.*

This is TRACEY's data-maintenance panel: eight cards, each with its own form + ajax call + inline
script at the bottom of the file.

| Feature | What it does | Ajax endpoint | Script/command behind it |
|---|---|---|---|
| **Update Taxonomies** | Refreshes the taxonomy table against current NCBI data; creates new taxa if needed. Takes ~10 min. | `ajax_update_taxonomy` → `views.update_taxonomy` | `utils/ncbi_taxonomy/TaxonomyUpdater.py`, same engine as `manage.py UpdateTraceyTaxonomies` |
| **Update TRACEY Sequences** | Re-syncs "live" sequences that have an NCBI ID against current data (sequences without an NCBI ID are left untouched). Filterable by species/family. Can take hours. | `ajax_update_sequences` → `views.update_sequences` | `utils/traceySequenceUpdater/traceySequencesUpdater.py`, same engine as `manage.py UpdateTraceySequences` |
| **Re-scan Motifs** | Re-runs the HMM scan over existing sequences to refresh `Motifs`/`Verifymotifs`. Filters: species, family/domain/specific HMM, e-value threshold, "only active", **dry-run** mode (opens the result in a new tab without persisting). | `ajax_rescan_motifs` → `views.rescan_motifs` | `utils/motifPredictor/reScanMotifs.py`, same engine as `manage.py ReScanMotifs` |
| **Upload new sequences** | Uploads a FASTA of new sequences; TRACEY analyzes them against the HMMs and auto-assigns the best-hit motif. | `ajax_upload_sequences` → `views.upload_sequences` | Required FASTA header format documented in `home/help_doc_upload_sequences.html` |
| **HMM Models (download)** | Downloads TRACEY's HMM profiles (one family or the full database) for external use with `hmmsearch`/`hmmscan`. | `download_hmm_zip` (direct navigation, not ajax) | Catalogs `.hmm` files in `utils/hmmModels/` via `get_hmm_catalog()` |
| **Build Phylogenetic Tree** | Rebuilds the tree of life for all taxonomies currently in TRACEY, following current NCBI phylogeny. Provides download links for the tree in Newick and PDF form. | `ajax_update_tree` → `views.update_tree` | `utils/ncbi_taxonomy/TreeUpdater.py`, same engine as `manage.py UpdateTraceyTree` |
| **Update Domaingroups** | Syncs newly added `.hmm` files under `utils/hmmModels/<FAMILY>/` into the system: adds missing entries to the staff family menu, creates the matching `Domaingroups` rows, and rebuilds `MOTIFS.hmmDb`. Detached run; a report opens in a new tab when done. Help: `home/help_doc_update_domaingroups.html`. | `ajax_update_domaingroups` → `views.update_domaingroups` (+ `ajax_update_domaingroups_results` polled for the report) | `utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py`, same engine as `manage.py UpdateDomainGroups` |
| **Upload HMM Model** | Uploads a new HMMER3 `.hmm` profile into a chosen protein family (the `DOMAIN_CONFIG` families). Validates it (HMMER3 header, `LENG` line, `NAME` line = file name, single profile, ≤5 MB, name unique across families), saves it to `utils/hmmModels/<FAMILY>/`, then chains **Update Domaingroups** so the profile is wired into the menu + `Domaingroups` + `MOTIFS.hmmDb`. "Replace existing profile" allows overwrite. Help: `home/help_doc_upload_hmm_model.html`. | `ajax_upload_hmm` → `views.upload_hmm_model` (report polled via `ajax_update_domaingroups_results`) | saves the file, then `manage.py UpdateDomainGroups` |

Common pattern across most cards: a CSRF token in each form, a spinner + status message, and a
shared flag (`reloadOnAjaxStop`) that reloads the page once any of these long ajax calls finishes,
to refresh the "last updated" timestamps. **Upload new sequences** and **Update Domaingroups**
instead POST and then poll a `*_results` endpoint until the per-run log file ends with a
`DONE_MARKER`, and open the finished HTML report in a new tab (no page reload — their "last run"
line refreshes on the next visit).

---

## 4. Frontend: templates, JS, includes and menus

### 4.1 Template tree (`apps/templates/`)

```
layouts/
  base.html              main layout (sidebar + content + footer)
  sequenceForm.html       large insert/verify-sequence form (an include, not a base)
includes/
  sidebar.html           navigation menu (hardcoded, see 4.3)
  footer.html            page footer (partner logos)
  scripts.html           common JS bundle (Popper, Bootstrap, Chartist, SweetAlert2, moment.js, volt.js, …)
  settings-box.html      Volt theme widget (commented out in base.html, unused)
accounts/                login.html, register.html
home/                    ~30 page templates + partials/_motif_card.html
menus/                   NOT HTML templates — Python modules (see 4.3)
```

`layouts/base.html` defines the blocks `title`, `og_title`, `og_description`, `stylesheets`,
`content`, `javascripts`. Most templates in `home/` and `accounts/` extend it directly (a single
level of inheritance, no deeper chains).

Some templates in `home/` are **not full pages**: they're HTML fragments returned directly by ajax
views (e.g. `query-sequences-fasta.html`, `query-verify-update-sequences.html`, dropdown option
lists). Others are standalone HTML documents opened in a new tab (`query-sequences-3dViewer.html`,
`query-verify-blast.html`, each with its own `<!DOCTYPE html>`).

`home/partials/_motif_card.html` is reused twice in `layouts/sequenceForm.html`: once for
`verifymotifs` (with a Verify/Delete option) and once for `motifs` (with an Unverify/Delete
option).

### 4.2 Main JS files (`apps/static/assets/js/`)

| File | Role |
|---|---|
| `volt.js` | JS for the Volt theme (Bootstrap 5): SweetAlert2, settings panel, general theme chrome |
| `sequenceForm-dropdowns.js` | Cascading dropdowns proteinlayout → domain → domaingroup → domainsubgroup on the insert/verify form (and its "manual" variant) |
| `sequenceForm-utils.js` | `suggestNames()` (ajax to `ajax_suggestNames`) and `searchOpen()` (taxonomy autocomplete via `/search.json`) |
| `ngl-viewer.js` | 3D viewer based on **NGL.js**, used on the insert/verify sequence form (colors by domain, highlights residues) |
| `django-htmx.js` | Debug helper for `django_htmx`: when `DEBUG=True`, replaces HTMX error responses with Django's debug error page |
| `jquery-4.0.0.min.js` | jQuery, loaded per-page (not globally from `base.html`) wherever AJAX/DOM manipulation is needed |

**Important:** the standalone detail/3D-viewer pages (`query-sequences-3dViewer.html`,
`query-sequences-details.html`) instead use **3Dmol.js via CDN**
(`https://3Dmol.org/build/3Dmol-min.js`). In other words, TRACEY has **two different 3D viewers**
depending on the page: NGL.js (local) in the insert/verify workflow, and 3Dmol.js (CDN) on the
public query pages. If you touch 3D-visualization functionality, check both.

### 4.3 How TRACEY builds its menus

There are two distinct concepts both loosely called "menu" — worth not confusing:

1. **Navigation menu (sidebar)** — `includes/sidebar.html`. This is **hardcoded** HTML, not
   generated from the database or from a Python data structure. Active-item highlighting is done
   with Django conditionals (`{% if 'query' in segment %}`) over the `segment` variable each view
   computes by hand (see 1.6). The only real context processor in play is
   `apps/context_processors.py:cfg_assets_root`, which just injects `ASSETS_ROOT` for static-asset
   paths.
2. **"Menu" of protein families** — `apps/templates/menus/query_sequences.py` and
   `query_sequences_full.py`. Despite living under `templates/` and having a `.py` extension,
   **these are not Django templates**: they're Python modules holding a nested dict
   (`menu = {...}`) describing the protein-family → domain → domaingroup hierarchy (SNARE, Ras,
   AAA, …), plus helper functions (`get_keys_recursively()`, `get_dict()`). Views import them to
   populate the cascading dropdowns on Query/Insert/Verify/Features. Unrelated to UI navigation.

### 4.4 CSS / SCSS

Base theme "Volt" (Bootstrap 5, AppSeed/Themesberg), compiled from SCSS
(`apps/static/assets/scss/`) to CSS (`apps/static/assets/css/volt.css`). Project-specific
customization in `scss/custom/_variables.scss` and `css/sequenceForm.css` (styles for the
insert/verify form). The CSS specific to `features.html` (loaders, `.feature-card` grid) is inline
in the template itself rather than in a separate file.

---

## 5. Maintenance commands (`manage.py`)

Defined in `apps/management/commands/`. Each one (except `plotTaxonomy`) has an equivalent feature
in `features.html` (section 3) that triggers the same logic from the UI — `UpdateDomainGroups` is
reused by two of them (*Update Domaingroups* and *Upload HMM Model*):

| Command | What it does |
|---|---|
| `UpdateTraceySequences` | Refreshes "live" sequences that have an NCBI ID. Flags: `--continue`, `--force`, `--onlyActive`, `--species`, `--traceyIds`, `--domain` |
| `UpdateTraceyTaxonomies` | Refreshes taxonomies from NCBI. Flag `--taxa` (default `superkingdom`) |
| `UpdateTraceyTree` | Rebuilds the phylogenetic tree |
| `ReScanMotifs` | Re-scans HMMs over existing sequences. Requires `--hmm` or `--family` |
| `UpdateDomainGroups` | Syncs new `.hmm` files under `utils/hmmModels/` into the system (see below). Optional `--log-file` (used by the *Update Domaingroups* feature to write its report). |
| `plotTaxonomy` | Diagnostic command: draws the taxonomy tree/network for a given scientific name (not part of the data pipeline) |

`UpdateDomainGroups` (core logic in `utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py`,
`update_domaingroups_with_hmms()`) syncs new HMM files under `utils/hmmModels/` into the rest of
the system: adds any missing entries to the staff `query_sequences_full.py` menu, creates the
corresponding `Domaingroups` rows in the database, and rebuilds `utils/hmmModels/MOTIFS.hmmDb`
(concatenates every `.hmm` file and re-indexes with `hmmpress -f`, via `rebuildMotifsHmmDb.py`) so
`motifScan(proteinlayout="ALL")` picks up the new profiles. It does **not** touch the public
`query_sequences.py` menu — that still has to be edited by hand (see 7). The equivalent
*Update Domaingroups* card in `features.html` runs the same command.

```
python manage.py UpdateDomainGroups
```

---

## 6. Access control (staff permissions)

The database-management sections — `features.html`, `query-insert`, `query-verify` (and its
BLAST sub-view) — are gated behind `@login_required` + `@staff_login_required`
(`apps/home/views_verify.py`, `apps/home/views_admin.py`), which check
`request.user.is_staff`. A plain registered user has **no** access to these sections; only
users flagged as staff do.

To grant access to a user who has already registered:

1. Go to `tracey.unil.ch/admin` (Django admin) and log in with a superuser/staff account.
2. Open the **Users** section and select the target user.
3. Check "Staff status" (and any relevant permissions/groups) and save.

**Careful not to confuse two different models both called "User":** the one you edit here is
Django's standard `auth.User` model (the one `/admin` manages). There's also a legacy `User`
table in `apps/home/models.py` (`managed = False`), which is a pre-Django authentication table
unrelated to the current access control — that's not the one to touch to grant permissions.

## 7. Adding a new HMM model and generating its Domaingroups

A new HMM profile has to keep three things in sync: the `.hmm` file under
`utils/hmmModels/<FAMILY>/`, its `Domaingroups` row in the database, and the **staff** domain menu
(`apps/templates/menus/query_sequences_full.py`) that drives the cascading dropdowns on
Query/Insert/Verify/Features. Two staff-only cards in `features.html` cover this (section 3):

- **Upload HMM Model** — upload one `.hmm` into a chosen family; it is validated, filed, and the
  sync below runs automatically.
- **Update Domaingroups** — run the sync on its own, after `.hmm` files reached
  `utils/hmmModels/` by other means (a manual copy, a bulk `scp`, a new family folder).

Both use the engine
`utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py:update_domaingroups_with_hmms()`, also
runnable directly as `python manage.py UpdateDomainGroups` (section 5).

### 7.1 Naming rules

The file's basename (without `.hmm`) becomes **both** the `Domaingroups.domaingroupname` and the
staff menu key, and it must equal the profile's `NAME` field (line 2 of the `.hmm`) — motif
scanning resolves a hit to its domaingroup by that `NAME` (`motifScan()`,
`apps/home/views_motifs.py`), so a mismatch means the hits are silently dropped.

- A case-insensitive match against an existing menu key, or a per-family alias in `DOMAIN_CONFIG`
  (e.g. `SNAP` maps `aSnap`/`cSnap` → `aSNAP`/`cSNAP`) → treated as already present, nothing added.
- Listed in `HMM_BLACKLIST` → skipped entirely (general HMMs superseded by named variants, e.g.
  the SM `Vps33`/`Vps45` base profiles).
- Dot notation infers menu hierarchy: `Longin.V` nests under an existing `Longin` key, otherwise
  it is added at the top of the family subtree.
- The name must be unique across all family folders.

`DOMAIN_CONFIG` (top of `updateDomainGroupsWithHMMs.py`) maps each family **folder** →
`(domain_name_in_DB, menu_path[, aliases])`. Families it currently knows: `SNARE`, `HABC`,
`LONGIN`, `LGL`, `C2`, `AAA.AAA`, `AAA.ND`, `RAS`, `ARF`, `MUN.D1`/`MUN.D2`,
`NSR.CD`/`NSR.MD`/`NSR.ND`, `PROPPIN`, `RHOMBOID`, `RINT`, `SM.D1`/`SM.D2A`/`SM.D2B`/`SM.D3`,
`SNAP`, `ZW10`. Folders with no `DOMAIN_CONFIG` entry (`ROD`, `SEC39`) are only picked up for the
`MOTIFS.hmmDb` rebuild — no menu entry, no `Domaingroups` row — until an entry is added.

### 7.2 Option A — the *Upload HMM Model* card (one profile)

Pick the family, choose/drop the `.hmm`, submit. `upload_hmm_model()`
(`apps/home/views_admin.py`) rejects the upload unless: it is a HMMER3 profile with a `LENG` line,
a single profile, ≤ 5 MB, filename `^[A-Za-z0-9][\w.\-]*\.hmm$`, `NAME` == filename, the family is
in `DOMAIN_CONFIG`, and the name is not already used in another family (tick *Replace existing
profile* to overwrite one in the **selected** family). It then saves the file into
`utils/hmmModels/<FAMILY>/` and runs the sync detached; the report opens in a new tab.

### 7.3 Option B — copy files + *Update Domaingroups* (bulk / new family)

For several profiles at once, or a brand-new family:

1. If the family folder is new, add a `DOMAIN_CONFIG` entry
   (`folder → (domain_name_in_DB, menu_path_list)`).
2. Copy the `.hmm` file(s) into `utils/hmmModels/<FAMILY>/` (names per 7.1).
3. Run `python manage.py UpdateDomainGroups`, or click **Update Domaingroups** in `features.html`
   (staff only; detached, report opens in a new tab).

### 7.4 What the sync does

1. **Menu sync** — `sync_menu_with_hmms()` adds any not-yet-represented `.hmm` (per 7.1) to the
   **staff** menu `apps/templates/menus/query_sequences_full.py`, rewriting that file in place
   (see 4.3).
2. **Database** — `updateDomainGroups()` walks the updated menu and creates a `Domaingroups` row
   for every key that lacks one, linked to its parent `Domains`/`Domaingroups`, with
   `domaingrouplength` read from the `.hmm` `LENG` field.
3. **`MOTIFS.hmmDb` rebuild** — `rebuild_motifs_hmmdb()` (`rebuildMotifsHmmDb.py`) concatenates
   every `.hmm` under `utils/hmmModels/` into `utils/hmmModels/MOTIFS.hmmDb` and re-indexes it
   with `hmmpress -f` (needs `hmmpress` on `PATH`), so `motifScan(proteinlayout="ALL")` sees the
   new profile, not just family-scoped scans.

### 7.5 What's still manual

- **Public menu** — `apps/templates/menus/query_sequences.py` (non-staff) is **not** touched. Add
  the new domaingroup there by hand if non-staff users should see it (see 4.3 and 6).
- **Commit** — the new `.hmm` file(s) and the rewritten `query_sequences_full.py` are both tracked;
  commit them so the change survives the next deployment.
- **New families** — need the `DOMAIN_CONFIG` code change (7.1) before either option can wire them
  into the menu and the database.

---

## 8. Notes and gotchas for the next developer

- **Database schema changes are NOT done with `makemigrations`/`migrate`** — all models are
  `managed = False` over a pre-existing MySQL database (see 1.3).
- `HomeConfig` (`apps/home/apps.py`) is not in `INSTALLED_APPS` — appears to be dead code.
- TRACEY has **two different 3D viewers** (NGL.js vs 3Dmol.js via CDN) depending on the page — see
  4.2.
- Menu highlighting depends on every new view manually defining `segment` — there's no automatic
  mechanism for this (see 1.6).

---

## 9. Note on this document and exporting to PDF

This manual is deliberately kept in Markdown: it's versioned alongside the code, editable without
special tooling, and renders directly on GitHub/GitLab/VSCode. If a PDF version is ever needed, it
can be generated with:

```bash
pandoc docs/MANUAL_en.md -o manual.pdf
```
