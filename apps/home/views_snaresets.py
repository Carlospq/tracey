import csv
import io

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from .models import Domaingroups, Motifs, Taxonomies
from .utils import get_sequences, get_menu, notEmpty

from utils.ncbi_taxonomy.reducedTRACEYtaxonomies import reducedTRACEYtaxonomies


# Column order follows TRACEY_Human_master_enriched.tsv
SNARE_SET_COLUMNS = [
    'Name', 'Speciesshortname', 'Scientificname', 'ncbi_taxid', 'Protein_display_name',
    'snare_group', 'snare_subclass', 'class_I_IV', 'RefSeq_accession', 'Motifs',
    'Sourcedatabase', 'Sequencestatus', 'Foreignannotation', 'Sequence', 'full_length_aa',
    'SNARE_domain_start', 'SNARE_domain_end', 'SNARE_domain_sequence', 'SNARE_domain_length',
    'Habc_domain_start', 'Habc_domain_end', 'Habc_domain_sequence',
    'Longin_domain_start', 'Longin_domain_end', 'Longin_domain_sequence',
    'other_domain_annotations', 'domain_annotation_status', 'classification_note',
]

SNARE_SET_DEFAULT_COLUMNS = [
    'Name', 'Protein_display_name', 'Scientificname', 'snare_group', 'snare_subclass',
    'class_I_IV', 'RefSeq_accession', 'Motifs', 'full_length_aa', 'domain_annotation_status',
]

_COORD_DOMAINS = ('SNARE', 'Habc', 'Longin')
_ORGANISM_FIELDS = ('taxonomy_ids', 'species_list', 'shortname', 'sciname', 'taxonomy')


def _snare_domaingroup_paths():
    """Map each SNARE domaingroup_id to its path of names from the root, following domainGroupParent_id,
    e.g. Syx13 -> ['SNARE', 'Qa', 'Qa.III', 'Qa.III.b', 'Syx7', 'Syx13']."""
    nodes = {}
    for dg_id, name, parent in Domaingroups.objects.filter(domain__domainname='SNARE').values_list(
            'domaingroup_id', 'domaingroupname', 'domaingroupparent_id'):
        parent = str(parent or '').strip()
        nodes[dg_id] = (name, int(parent) if parent.isdigit() else None)

    paths = {}
    for dg_id in nodes:
        path, current, seen = [], dg_id, set()
        while current in nodes and current not in seen:
            seen.add(current)
            name, current = nodes[current]
            path.append(name)
        paths[dg_id] = path[::-1]
    return paths


def _snare_classification(paths):
    """(group, subclass, class) from the SNARE hierarchy: group and subclass are the 2nd and 3rd levels
    of the path (e.g. 'Qa' / 'Qa.III'); class is the subclass name without the group prefix ('III')."""
    groups, subclasses, classes = [], [], []
    for path in paths:
        if len(path) > 1 and path[1] not in groups:
            groups.append(path[1])
        if len(path) > 2 and path[2] not in subclasses:
            subclasses.append(path[2])
            prefix = path[1] + '.'
            if path[2].startswith(prefix) and path[2][len(prefix):] not in classes:
                classes.append(path[2][len(prefix):])
    return ', '.join(groups), ', '.join(subclasses), ', '.join(classes)


def _motif_coords(motif):
    try:
        return motif.get_real_startposition(), motif.get_real_stopposition()
    except Exception:
        return None, None


def _join(values):
    return '; '.join(str(v) for v in values)


def build_snare_set_rows(sequences):
    taxonomies = {t.taxonomy_id: t for t in Taxonomies.objects.filter(
        taxonomy_id__in=sequences.values('taxonomy_id'))}

    motifs_by_seq = {}
    for m in (Motifs.objects.filter(sequence_id__in=sequences.values('sequence_id'))
              .select_related('domaingroup__domain', 'sequence').order_by('startposition')):
        motifs_by_seq.setdefault(m.sequence_id, []).append(m)

    dg_paths = _snare_domaingroup_paths()

    rows = []
    for seq in sequences:
        tax = taxonomies.get(seq.taxonomy_id)
        motifs = motifs_by_seq.get(seq.sequence_id, [])

        coords = {d: [] for d in _COORD_DOMAINS}
        other_domains, snare_paths, missing_coords = [], [], False
        for m in motifs:
            domainname = m.domaingroup.domain.domainname
            if domainname == 'SNARE':
                snare_paths.append(dg_paths.get(m.domaingroup_id, []))
            if domainname in coords:
                start, end = _motif_coords(m)
                if start is None:
                    missing_coords = True
                else:
                    coords[domainname].append((start, end, seq.sequence[start - 1:end]))
            else:
                other_domains.append(domainname)

        group, subclass, class_ = _snare_classification(snare_paths)

        row = {
            'sequence_id': seq.sequence_id,
            'Name': seq.sequenceshortname,
            'Speciesshortname': tax.taxonomyshortname if tax else '',
            'Scientificname': (tax.scientificname or '') if tax else '',
            'ncbi_taxid': tax.ncbi_taxonomy_id if tax else '',
            'Protein_display_name': seq.aliases or '',
            'snare_group': group,
            'snare_subclass': subclass,
            'class_I_IV': class_,
            'RefSeq_accession': seq.dbxref or '',
            'Motifs': ', '.join(m.domaingroup.domain.domainname for m in motifs),
            'Sourcedatabase': seq.sourcedatabase,
            'Sequencestatus': seq.sequencestatus or '',
            'Foreignannotation': seq.foreignannotation,
            'Sequence': seq.sequence,
            'full_length_aa': len(seq.sequence),
            'other_domain_annotations': ', '.join(other_domains),
            'domain_annotation_status': 'missing coordinates' if missing_coords else ('complete' if motifs else 'no motifs'),
            'classification_note': '' if subclass else 'No SNARE subclass assigned',
        }
        for d in _COORD_DOMAINS:
            row[f'{d}_domain_start'] = _join(c[0] for c in coords[d])
            row[f'{d}_domain_end'] = _join(c[1] for c in coords[d])
            row[f'{d}_domain_sequence'] = _join(c[2] for c in coords[d])
        row['SNARE_domain_length'] = _join(c[1] - c[0] + 1 for c in coords['SNARE'])
        rows.append(row)
    return rows


def SnareSets(request):
    context = {'segment': request.path.split('/')[-1],
               'domaingroup_rank': [],
               'taxonomy_ranks': list(reducedTRACEYtaxonomies),
               'is_staff': request.user.is_staff,
               'previous_query': {}}
    return render(request, 'home/snare-sets.html', context)


def SnareSetsTable(request):
    query = dict(request.GET)
    query['domainname'] = ['SNARE']
    query['proteinlayout'] = ['SNARE']
    export_tsv = query.pop('format', [''])[0] == 'tsv'

    if not any(f in query and notEmpty(query, f) for f in _ORGANISM_FIELDS):
        return JsonResponse({'error': 'Select at least one organism (taxonomy, species, shortname or scientific name).'})

    sequences = get_sequences(query, menu=get_menu(request))
    if 'error' in sequences:
        return JsonResponse({'error': sequences['error']})
    if not sequences:
        return JsonResponse({'error': 'This query returns 0 sequences. Please select different options.'})

    rows = build_snare_set_rows(sequences)

    if export_tsv:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=SNARE_SET_COLUMNS, delimiter='\t',
                                extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        response = HttpResponse(buffer.getvalue(), content_type='text/tab-separated-values')
        response['Content-Disposition'] = 'attachment; filename="TRACEY_snare_sets.tsv"'
        return response

    return JsonResponse({'columns': SNARE_SET_COLUMNS,
                         'default_columns': SNARE_SET_DEFAULT_COLUMNS,
                         'rows': rows})
