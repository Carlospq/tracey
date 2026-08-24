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

This is TRACEY's data-maintenance panel: six cards, each with its own form + ajax call + inline
script at the bottom of the file.

| Feature | What it does | Ajax endpoint | Script/command behind it |
|---|---|---|---|
| **Update Taxonomies** | Refreshes the taxonomy table against current NCBI data; creates new taxa if needed. Takes ~10 min. | `ajax_update_taxonomy` → `views.update_taxonomy` | `utils/ncbi_taxonomy/TaxonomyUpdater.py`, same engine as `manage.py UpdateTraceyTaxonomies` |
| **Update TRACEY Sequences** | Re-syncs "live" sequences that have an NCBI ID against current data (sequences without an NCBI ID are left untouched). Filterable by species/family. Can take hours. | `ajax_update_sequences` → `views.update_sequences` | `utils/traceySequenceUpdater/traceySequencesUpdater.py`, same engine as `manage.py UpdateTraceySequences` |
| **Re-scan Motifs** | Re-runs the HMM scan over existing sequences to refresh `Motifs`/`Verifymotifs`. Filters: species, family/domain/specific HMM, e-value threshold, "only active", **dry-run** mode (opens the result in a new tab without persisting). | `ajax_rescan_motifs` → `views.rescan_motifs` | `utils/motifPredictor/reScanMotifs.py`, same engine as `manage.py ReScanMotifs` |
| **Upload new sequences** | Uploads a FASTA of new sequences; TRACEY analyzes them against the HMMs and auto-assigns the best-hit motif. | `ajax_upload_sequences` → `views.upload_sequences` | Required FASTA header format documented in `home/help_doc_upload_sequences.html` |
| **HMM Models (download)** | Downloads TRACEY's HMM profiles (one family or the full database) for external use with `hmmsearch`/`hmmscan`. | `download_hmm_zip` (direct navigation, not ajax) | Catalogs `.hmm` files in `utils/hmmModels/` via `get_hmm_catalog()` |
| **Build Phylogenetic Tree** | Rebuilds the tree of life for all taxonomies currently in TRACEY, following current NCBI phylogeny. Provides download links for the tree in Newick and PDF form. | `ajax_update_tree` → `views.update_tree` | `utils/ncbi_taxonomy/TreeUpdater.py`, same engine as `manage.py UpdateTraceyTree` |

Common pattern across all six: a CSRF token in each form, a spinner + status message, and a shared
flag (`reloadOnAjaxStop`) that reloads the page once any of these long ajax calls finishes, to
refresh the "last updated" timestamps.

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

Defined in `apps/management/commands/`. Each one has an equivalent feature in `features.html`
(section 3) that triggers the same logic from the UI:

| Command | What it does |
|---|---|
| `UpdateTraceySequences` | Refreshes "live" sequences that have an NCBI ID. Flags: `--continue`, `--force`, `--onlyActive`, `--species`, `--traceyIds`, `--domain` |
| `UpdateTraceyTaxonomies` | Refreshes taxonomies from NCBI. Flag `--taxa` (default `superkingdom`) |
| `UpdateTraceyTree` | Rebuilds the phylogenetic tree |
| `ReScanMotifs` | Re-scans HMMs over existing sequences. Requires `--hmm` or `--family` |
| `plotTaxonomy` | Diagnostic command: draws the taxonomy tree/network for a given scientific name (not part of the data pipeline) |

Additionally, `utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py` is a standalone
maintenance script — not a `manage.py` command — run via:

```
python manage.py shell < utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py
```

It syncs new HMM files under `utils/hmmModels/` into the rest of the system: adds any missing
entries to the `query_sequences_full.py` menu, creates the corresponding `Domaingroups` rows in
the database, and rebuilds `utils/hmmModels/MOTIFS.hmmDb` (concatenates every `.hmm` file and
re-indexes with `hmmpress -f`, via `rebuildMotifsHmmDb.py`) so `motifScan(proteinlayout="ALL")`
picks up the new profiles. It does **not** touch the public `query_sequences.py` menu — that
still has to be edited by hand (see 7).

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

Adding a new HMM profile touches three things that all have to stay in sync: the `.hmm` file
itself, the `Domaingroups` row in the database, and the domain menu dicts that drive the
cascading dropdowns on Query/Insert/Verify/Features. Most of this is automated by
`utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py` (see 5) — this section explains what
it does step by step so a new HMM can be added correctly.

### 7.1 Drop the `.hmm` file in the right place

Add the file to `utils/hmmModels/<FOLDER>/`, where `<FOLDER>` is the family folder already
mapped in `DOMAIN_CONFIG` at the top of `updateDomainGroupsWithHMMs.py` — e.g. `SNARE`, `HABC`,
`LONGIN`, `LGL`, `C2`, `AAA.AAA`, `AAA.ND`, `RAS`, `ARF`, `MUN.D1`/`MUN.D2`,
`NSR.CD`/`NSR.MD`/`NSR.ND`, `PROPPIN`, `RHOMBOID`, `RINT`, `SM.D1`/`SM.D2A`/`SM.D2B`/`SM.D3`,
`SNAP`, `ZW10`. If the HMM belongs to a brand-new family with no existing folder, create the
folder and add a new entry to `DOMAIN_CONFIG` (`folder → (domain_name_in_DB, menu_path_list)`)
before running the script — otherwise it will be skipped.

The file's basename (without `.hmm`) becomes both the `Domaingroups.domaingroupname` and the
menu key, so naming matters:

- If the name matches (case-insensitive) a menu key that already exists, or a per-folder alias
  defined in `DOMAIN_CONFIG` (e.g. `SNAP` maps `aSnap`/`cSnap` → `aSNAP`/`cSNAP`), it's treated
  as already present and nothing new is added.
- If the name is listed in `HMM_BLACKLIST`, it's skipped entirely — use this for general HMMs
  that shouldn't get their own menu entry (e.g. the SM `Vps33`/`Vps45` base HMMs, superseded by
  the `Vps33a`/`Vps33b` variants already in the menu).
- Dot notation infers hierarchy: `Longin.V` is nested as a child of `Longin` in the menu if a
  `Longin` key already exists there; otherwise it's added at the top of the family subtree.

### 7.2 Run the sync script

```
python manage.py shell < utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py
```

This does everything else automatically:

1. **Menu sync** — `sync_menu_with_hmms()` scans `utils/hmmModels/` and adds any `.hmm` not
   already represented (per the rules in 7.1) to the **staff** menu,
   `apps/templates/menus/query_sequences_full.py` (see 4.3).
2. **Database** — `updateDomainGroups()` walks the (updated) menu and, for every key without a
   matching `Domaingroups` row, creates one linked to its parent `Domains`/`Domaingroups`,
   reading `domaingrouplength` from the `LENG` field of the corresponding `.hmm` file. Motif
   scanning (`motifScan()`, `apps/home/views_motifs.py`) resolves each HMM hit against a
   `Domaingroups` record, so a `.hmm` with no matching row can't be classified/displayed
   correctly.
3. **`MOTIFS.hmmDb` rebuild** — `rebuild_motifs_hmmdb()` (`rebuildMotifsHmmDb.py`) concatenates
   every `.hmm` under `utils/hmmModels/` into `utils/hmmModels/MOTIFS.hmmDb` and re-indexes it
   with `hmmpress -f`, so the new profile is picked up by `motifScan(proteinlayout="ALL")`
   scans, not just family-scoped ones.

### 7.3 What's still manual

`apps/templates/menus/query_sequences.py` — the **public** (non-staff) menu — is **not** touched
by the script. If the new domaingroup should be visible to non-staff users, add it there by hand
(see 4.3, and 6 for the staff/public distinction).

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
