from time import gmtime, strftime

from apps.home.models import Genes, Sequences, Taxonomies
from apps.templates.menus.query_sequences_full import menu, get_keys_recursively
from utils.motifPredictor.reScanMotifs import reScanMotifs
from utils.ncbi_taxonomy.TaxonomyUpdater import create_ncbi_taxonomy, read_ncbi_files, build_ncbi_dict_from_entrez

DONE_MARKER = '<!-- UPLOAD_DONE -->'


def upload_sequences_from_file(file_path, evalue, username, log_path):
    """
    Parses a FASTA file, creates Sequences/Genes entries and re-scans motifs.

    Runs as a standalone management command (see apps/management/commands/UploadSequences.py)
    so that the HTTP request that triggers it can return immediately — see
    apps/home/views_admin.py:upload_sequences. Writes the final HTML report to
    log_path, terminated by DONE_MARKER so pollers can detect completion.
    """
    try:
        html = _process(file_path, evalue, username)
    except Exception as e:
        html = (f'<html><body><p class="err">Upload failed — {type(e).__name__}: {e}</p></body></html>')
    _write_log(log_path, html)
    return html


def _process(file_path, evalue, username):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return '<html><body><p class="err">File encoding error. File must be UTF-8.</p></body></html>'

    # Parse FASTA — header fields separated by ||, extras by ;key:value
    parsed = {}
    current_header = None
    parse_errors = []

    # Initialize empty variable for NCBI dictionary (Tier 3 fallback)
    ncbi = None
    entrez_cache = {}

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('>'):
            try:
                raw_header = line[1:]
                fields = raw_header.split('||')
                shortname = fields[0].strip() if len(fields) > 0 else ''
                scientific_name = fields[1].strip() if len(fields) > 1 else ''
                extras = {}
                if len(fields) > 2:
                    for kv in fields[2].split(';'):
                        kv = kv.strip()
                        if ':' in kv:
                            k, v = kv.split(':', 1)
                            extras[k.strip()] = v.strip()
                current_header = raw_header
                parsed[current_header] = {'shortname': shortname, 'scientific_name': scientific_name, 'sequence': '', **extras}
            except Exception:
                parse_errors.append(f'Could not parse header: {line[:80]}')
                current_header = None
        elif current_header:
            parsed[current_header]['sequence'] += line

    # Create entries
    created = []
    created_seqs = []
    errors = list(parse_errors)
    warnings = []
    scan_hits = {}

    for header, data in parsed.items():
        shortname      = data.get('shortname', '').strip()
        scientific_name = data.get('scientific_name', '').strip()
        sequence_str   = data.get('sequence', '').strip()

        if not shortname:
            errors.append(f'Missing shortname in: {header[:60]}')
            continue
        if not scientific_name:
            errors.append(f'{shortname}: missing scientific name')
            continue
        if not sequence_str:
            errors.append(f'{shortname}: empty sequence')
            continue

        taxonomy = Taxonomies.objects.filter(scientificname=scientific_name).first()
        if not taxonomy:
            taxonomy = entrez_cache.get(scientific_name)
        if not taxonomy:
            try:
                built = build_ncbi_dict_from_entrez(scientific_name)
                if built:
                    ncbi_id, ncbi_entrez = built
                    taxonomy = create_ncbi_taxonomy(ncbi_id, ncbi_entrez)
            except Exception:
                taxonomy = None
            if not taxonomy:
                try:
                    if not ncbi:
                        ncbi = read_ncbi_files()
                    ncbi_id = [x for x in ncbi['dict_names']
                               if ncbi['dict_names'][x]['name_txt'] == scientific_name][0]
                    taxonomy = create_ncbi_taxonomy(ncbi_id, ncbi)
                except Exception:
                    taxonomy = None
            entrez_cache[scientific_name] = taxonomy
        if not taxonomy:
            errors.append(f'{shortname}: taxonomy not found for "{scientific_name}"')
            continue

        if Sequences.objects.filter(sequence=sequence_str, taxonomy=taxonomy).exists():
            errors.append(f'{shortname}: sequence already exists for {scientific_name}')
            continue

        if Sequences.objects.filter(sequenceshortname=shortname, taxonomy=taxonomy).exists():
            warnings.append(f'{shortname}: shortname duplicated for {scientific_name}')

        try:
            gene = Genes.objects.create(ncbigene_id='-1')
            seq_obj = Sequences.objects.create(
                sequenceshortname=shortname,
                sequence=sequence_str,
                taxonomy=taxonomy,
                gene=gene,
                foreignannotation=data.get('foreignannotation', ''),
                annotation='',
                sourcedatabase=data.get('sourcedatabase', ''),
                dbxref=data.get('dbxref') or None,
                aliases=data.get('aliases') or None,
                sequencetype='protein',
                sequencestatus='live',
                private=1,
                replacedby=-1,
                changelog=strftime("%d.%m.%Y|%H:%M:%S|", gmtime()) + username + ' - uploadSequences;',
            )
            created.append(shortname)
            created_seqs.append(seq_obj)
        except Exception as e:
            errors.append(f'{shortname}: database error — {e}')
            continue

    if created_seqs:
        try:
            result = reScanMotifs(created_seqs, hmm_keys=get_keys_recursively(menu), evalue=evalue)
            if result:
                scan_hits.update(result)
        except Exception as e:
            warnings.append(f'motif scan error — {type(e).__name__}: {e}')

    lines = ['<html><head><meta charset="utf-8"><style>',
             'body{font-family:monospace;padding:24px;background:#f8f8f8;}',
             'h2{margin-bottom:12px;}',
             '.ok{color:#2a7a2a;} .err{color:#c0392b;} .warn{color:#f39c12;}',
             'ul{margin-top:6px;} li{margin-bottom:4px;}',
             '</style></head><body>',
             f'<h2>Upload results</h2>',
             f'<p class="ok">&#10003; {len(created)} sequence(s) uploaded successfully.</p>']
    if created:
        def _fmt_seq(s):
            hits = scan_hits.get(s, [])
            if hits:
                return f'{s} ({len(hits)} hit{"s" if len(hits) != 1 else ""}: {", ".join(hits)})'
            return s
        lines.append('<ul>' + ''.join(f'<li class="ok">{_fmt_seq(s)}</li>' for s in created) + '</ul>')
    if errors:
        lines.append(f'<p class="err">&#10007; {len(errors)} skipped:</p>')
        lines.append('<ul>' + ''.join(f'<li class="err">{e}</li>' for e in errors) + '</ul>')
    if warnings:
        lines.append(f'<p class="warn">&#10007; {len(warnings)} warning(s):</p>')
        lines.append('<ul>' + ''.join(f'<li class="warn">{e}</li>' for e in warnings) + '</ul>')
    lines.append('</body></html>')

    return '\n'.join(lines)


def _write_log(log_path, html):
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(html)
        f.write('\n' + DONE_MARKER + '\n')
