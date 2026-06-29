import os
import re
import pyhmmer
import xml.etree.ElementTree as ET
import django_tables2 as tables

from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, redirect
from django.core.cache import cache
from django_tables2.config import RequestConfig
from django_tables2.export.export import TableExport

from .models import *
from .forms import *
from .utils import get_taxonomy_df, get_sequences, get_menu, notEmpty, get_wikipedia_image, user_can_access_sequence
from .plots import build_domain_plot, get_pdb_data, get_alphafold_url

from utils.ncbi_taxonomy.reducedTRACEYtaxonomies import *
from apps.templates.menus.query_sequences import get_keys_level_recursively, get_keys_recursively


def index(request):
    context = {'segment': 'index'}
    html_template = loader.get_template('home/home.html')
    return HttpResponse(html_template.render(context, request))


_PAGES_REQUIRES_LOGIN = {'updates.html'}


def pages(request):
    context = {}
    try:
        load_template = request.path.split('/')[-1]
        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template
        if load_template in _PAGES_REQUIRES_LOGIN and not request.user.is_authenticated:
            return HttpResponseRedirect('/noPermits.html?next=' + request.path)
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:
        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))
    except Exception:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))


def QueryView(request):
    segment = request.path.split('/')[-1]
    context = {"segment": segment}
    return render(request, 'home/query.html', context)


def load_taxonomy_rank(request):
    def getInnerDict(taxa, reducedTaxonomies=reducedTRACEYtaxonomies):
        if taxa in reducedTaxonomies:
            return reducedTaxonomies[taxa]
        else:
            for t in reducedTaxonomies:
                innerDict = getInnerDict(taxa, reducedTaxonomies[t])
                if innerDict:
                    return innerDict

    rank = request.GET.get('taxonomy_rank')
    if request.GET.get('reduced') == 'true':
        taxonomy_list = getInnerDict(rank)
    else:
        cache_key = f'taxonomy_rank_{rank}'
        taxonomy_list = cache.get(cache_key)
        if taxonomy_list is None:
            taxonomy_list = sorted(list(set([x.scientificname for x in Taxonomies.objects.filter(taxonomyrank=rank)])))
            cache.set(cache_key, taxonomy_list, timeout=21600)
    return render(request, 'home/query-sequences-family-taxonomyRank.html', {'taxonomy_list': taxonomy_list})


def load_species(request):
    df = get_taxonomy_df()
    ranks = [x for x in request.GET.getlist('taxonomy_list[]') if x != ''][-1]
    reducedTaxonomyID = reducedTRACEYtaxonomies_ncbiIDs[ranks]
    values = [x.scientificname for x in Taxonomies.objects.filter(ncbi_taxonomy_id__in=reducedTaxonomyID)]
    taxonomy_ids = []
    for v in values:
        arr = list(df[(df.eq(v).any(axis=1)) & (df['species'] != "-")].index.values)
        taxonomy_ids = taxonomy_ids + arr
    species_list = sorted(list(set([x.scientificname for x in Taxonomies.objects.filter(ncbi_taxonomy_id__in=taxonomy_ids)])))
    return render(request, 'home/query-sequences-family-species.html', {'species_list': species_list})


def proteinlayoutToDomaingroups(proteinLayoutname):
    proteinlayout = Proteinlayouts.objects.get(proteinlayoutname=proteinLayoutname)
    proteinlayoutgroups = proteinlayout.proteinlayoutgroups_set.all()
    p2d = P2Dmapping.objects.filter(proteinlayoutgroup__in=proteinlayoutgroups)
    domaingroups = Domaingroups.objects.filter(domaingroup_id__in=p2d.values('domaingroup_id'))
    return domaingroups


def proteinlayoutToDomains(proteinLayoutname):
    domaingroups = proteinlayoutToDomaingroups(proteinLayoutname)
    domains = Domains.objects.filter(domain_id__in=domaingroups.values('domain_id'))
    return domains


def load_domains(request):
    if request.GET.get('proteinlayout'):
        if request.GET.get('proteinlayout').upper() == "ALL":
            domains = ['']
        else:
            domains = [d for d in get_menu(request)[request.GET.get('proteinlayout')]]
    else:
        domains = [x.domainname for x in Domains.objects.all()]
    return render(request, 'home/query-sequences-family-domains.html', {'domains': domains})


def load_domaingroups_rank1(request):
    proteinlayout = request.GET.get('proteinlayout')
    domainname = request.GET.get('domainname')
    if proteinlayout and domainname:
        domaingroups_rank_list = [dg_name for dg_name in get_menu(request)[proteinlayout][domainname]]
    elif domainname:
        domaingroups_rank_list = [dg_name for dg_name in get_menu(request)[proteinlayout][domainname]]
    else:
        domaingroups_rank_list = []
    return render(request, 'home/query-sequences-family-domaingroupsRank1.html', {'domaingroups_rank_list': domaingroups_rank_list})


def load_sequenceshortnames(request):
    shortnames = cache.get('taxonomy_species_shortnames')
    if shortnames is None:
        shortnames = sorted(list(set([t.taxonomyshortname for t in Taxonomies.objects.filter(taxonomyrank='species')])))
        cache.set('taxonomy_species_shortnames', shortnames, timeout=21600)
    return render(request, 'home/query-sequences-family-sequenceshortnames.html', {'shortnames': shortnames})


def load_taxonomy_by_shortname(request):
    q = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'shortname')

    from django.db.models import Count, Q

    if search_type == 'scientific':
        if len(q) < 3:
            return JsonResponse({'taxa': []})
        matched_ids = set(
            Taxonomies.objects.filter(scientificname__istartswith=q)
            .values_list('taxonomy_id', flat=True)
        )
    else:
        if len(q) < 2:
            return JsonResponse({'taxa': []})
        matched_ids = set(
            Taxonomies.objects.filter(
                taxonomyshortname__istartswith=q
            ).values_list('taxonomy_id', flat=True)
        )

    # Traverse parent-child tree to include all descendants
    all_ids = set(matched_ids)
    frontier = list(matched_ids)
    while frontier:
        children_ids = list(
            Taxonomies.objects.filter(taxonomyparent_id__in=frontier)
            .values_list('taxonomy_id', flat=True)
        )
        new_ids = [cid for cid in children_ids if cid not in all_ids]
        all_ids.update(new_ids)
        frontier = new_ids

    # Build sequence filter: restrict to current protein layout / domain if provided
    proteinlayout = request.GET.get('proteinlayout', '').strip()
    domainname = request.GET.get('domainname', '').strip()
    seq_filter = Q(sequencestatus='live')
    if proteinlayout:
        try:
            menu = get_menu(request)
            if domainname and proteinlayout in menu and domainname in menu.get(proteinlayout, {}):
                dg_list = get_keys_recursively(menu[proteinlayout][domainname]) + [domainname]
            elif proteinlayout in menu:
                dg_list = get_keys_recursively(menu[proteinlayout]) + [proteinlayout]
            else:
                dg_list = []
            if dg_list:
                dg_ids = Domaingroups.objects.filter(domaingroupname__in=dg_list).values_list('domaingroup_id', flat=True)
                motif_seq_ids = Motifs.objects.filter(domaingroup_id__in=dg_ids).values_list('sequence_id', flat=True)
                seq_filter &= Q(sequence_id__in=motif_seq_ids)
        except (KeyError, Exception):
            pass

    # Direct sequence counts per taxonomy
    direct_counts_qs = (
        Sequences.objects
        .filter(seq_filter, taxonomy_id__in=all_ids)
        .values('taxonomy_id')
        .annotate(cnt=Count('sequence_id'))
    )
    direct_counts = {row['taxonomy_id']: row['cnt'] for row in direct_counts_qs}

    # Fetch taxa with parent info for bottom-up accumulation
    taxa_list = list(
        Taxonomies.objects
        .filter(taxonomy_id__in=all_ids)
        .only('taxonomy_id', 'taxonomyrank', 'scientificname', 'taxonomyshortname', 'taxonomyparent_id')
        .order_by('taxonomyrank', 'scientificname')
    )
    taxa_parent = {t.taxonomy_id: t.taxonomyparent_id for t in taxa_list}

    # Propagate counts from leaves up to ancestors (topological BFS)
    from collections import deque
    acc_counts = {tid: direct_counts.get(tid, 0) for tid in all_ids}
    children_of = {tid: [] for tid in all_ids}
    for tid in all_ids:
        pid = taxa_parent.get(tid)
        if pid in all_ids:
            children_of[pid].append(tid)
    remaining_children = {tid: len(children_of[tid]) for tid in all_ids}
    queue = deque(tid for tid in all_ids if remaining_children[tid] == 0)
    while queue:
        tid = queue.popleft()
        pid = taxa_parent.get(tid)
        if pid in all_ids:
            acc_counts[pid] += acc_counts[tid]
            remaining_children[pid] -= 1
            if remaining_children[pid] == 0:
                queue.append(pid)

    # Build response — skip taxa with 0 sequences in the current layout/domain
    taxa_data = [
        {
            'taxonomy_id': t.taxonomy_id,
            'scientificname': t.scientificname or '',
            'taxonomyrank': t.taxonomyrank or '',
            'shortname': t.taxonomyshortname,
            'seq_count': acc_counts.get(t.taxonomy_id, 0),
        }
        for t in taxa_list
        if acc_counts.get(t.taxonomy_id, 0) > 0
    ]

    return JsonResponse({'taxa': taxa_data})


def load_domaingroups_rank2(request):
    if not request.GET.get('domaingroup_rank'):
        children_list = []
    else:
        proteinlayout = request.GET.get('proteinlayout')
        domainname = request.GET.get('domainname')
        domaingroup_rank = request.GET.get('domaingroup_rank')
        children_list = get_keys_level_recursively(get_menu(request)[proteinlayout][domainname][domaingroup_rank])
    return render(request, 'home/query-sequences-family-domaingroupsRank2.html', {'domaingroups_rank_list': children_list})


def load_queryverifysequences(request):
    sequences = get_sequences(dict(request.POST), verify=True, menu=get_menu(request))
    if 'error' in sequences:
        context = {'sequences': '',
                   'error': sequences['error']}
    else:
        context = {'sequences': sequences}
        context['status_values'] = ['crystal structure', 'dead', 'ignore', 'live', 'replaced', 'replaced NCBI', 'suppressed', 'unknown']

    if len(context['sequences']) > 0:
        seqs = context['sequences']
        sequence_ids = seqs.values_list('sequence_id', flat=True)

        taxonomy_ids = seqs.values_list('taxonomy_id', flat=True)
        taxonomy_names = {t.taxonomy_id: t.scientificname for t in Taxonomies.objects.filter(taxonomy_id__in=taxonomy_ids)}
        speciesname = {seq.sequence_id: taxonomy_names.get(seq.taxonomy_id, '') for seq in seqs}

        motif_map = {}
        for m in Motifs.objects.filter(sequence_id__in=sequence_ids).values('sequence_id', 'motifname'):
            motif_map.setdefault(m['sequence_id'], set()).add(m['motifname'])
        for m in Verifymotifs.objects.filter(sequence_id__in=sequence_ids).values('sequence_id', 'motifname'):
            motif_map.setdefault(m['sequence_id'], set()).add(m['motifname'])
        motifs = {sid: ", ".join(names) for sid, names in motif_map.items()}

        context['speciesname'] = speciesname
        context['motifs'] = motifs

    context['log'] = len(context['sequences'])
    return render(request, 'home/query-verify-update-sequences.html', context)


def updateSequenceStatus(request):
    data = dict(request.POST)
    seq = Sequences.objects.get(sequence_id=data['seqID'][0])
    seq.sequencestatus = data['status'][0]
    seq.save()
    return HttpResponse('')


def QuerySequences(request):
    segment = request.path.split('/')[-1]
    form = FamilyForm

    proteinLayoutsList = sorted([pfam for pfam in get_menu(request)])

    domains_map = {name: did for name, did in Domains.objects.filter(
        domainname__in=["SNARE", "Habc", "Longin", "LGL"]
    ).values_list("domainname", "domain_id")}
    domainsList = sorted(domains_map.keys())
    SNAREdomainID = domains_map["SNARE"]

    SNAREdomaingroups = Domaingroups.objects.filter(domain_id=SNAREdomainID)
    SNAREdomaingroupnames = []
    SNAREmotifs = Motifs.objects.filter(domaingroup_id__in=SNAREdomaingroups.values('domaingroup_id'))

    shortnames = cache.get('querysequences_snare_shortnames')
    if shortnames is None:
        raw_names = Sequences.objects.filter(
            sequence_id__in=SNAREmotifs.values('sequence_id')
        ).values_list('sequenceshortname', flat=True)
        shortnames = sorted({
            prefix
            for name in raw_names
            if (prefix := name.split("_")[0]) != ""
        })
        cache.set('querysequences_snare_shortnames', shortnames, timeout=86400)

    taxonomy_ranks = [x for x in reducedTRACEYtaxonomies]

    context = {'segment': segment,
               'domainsList': domainsList,
               'domainGroupNames': SNAREdomaingroupnames,
               'proteinLayoutsList': proteinLayoutsList,
               'shortnames': shortnames,
               'taxonomy_ranks': taxonomy_ranks,
               'domaingroup_rank': SNAREdomaingroupnames,
               'form': form,
               'is_staff': request.user.is_staff,
               'error': [request.session['error'] if 'error' in request.session else ''][0]}

    if request.method == "GET":
        form = FamilyForm(request.GET)
        if form.is_valid():
            if context['error']:
                context['error'] = request.session['error']
                request.session['error'] = ''
                return render(request, 'home/query-sequences.html', context)
            elif sum([0 if x in ["", []] else 1 for x in list(form.cleaned_data.values())]) == 0:
                if form.cleaned_data["domainname"] != None:
                    context['error'] = ''
                else:
                    context['error'] = 'At least one field is required to make a query'
                    return render(request, 'home/query-sequences.html', context)
            else:
                return render(request, 'home/query-sequences-results.html', context=form.cleaned_data)
        else:
            context['form'] = form
            return render(request, 'home/query-sequences.html', context)

    return render(request, 'home/query-sequences.html', context)


def QuerySequencesResults(request):
    segment = request.path.split("?")[0].split('/')[-1]
    context = dict(request.GET)
    sequences = get_sequences(context, menu=get_menu(request))

    if len(sequences) == 0 or 'error' in sequences:
        if 'error' in sequences:
            request.session['error'] = sequences['error']
            return redirect('query-sequences')
        else:
            request.session['error'] = 'This query returns 0 sequences. Please select different options.'
            return redirect('query-sequences')

    taxonomy_ids = sequences.values_list('taxonomy_id', flat=True)
    speciesname = {t.taxonomy_id: t.scientificname for t in Taxonomies.objects.filter(taxonomy_id__in=taxonomy_ids)}
    speciesname = {seq.sequence_id: speciesname.get(seq.taxonomy_id, '') for seq in sequences}

    sequence_ids = sequences.values_list('sequence_id', flat=True)
    all_motifs = Motifs.objects.filter(sequence_id__in=sequence_ids).values('sequence_id', 'domaingroup_id')
    domaingroup_ids = set(m['domaingroup_id'] for m in all_motifs)
    domaingroup_names = {d.domaingroup_id: d.domaingroupname for d in Domaingroups.objects.filter(domaingroup_id__in=domaingroup_ids)}
    motifnames = {}
    for m in all_motifs:
        motifnames.setdefault(m['sequence_id'], set()).add(domaingroup_names.get(m['domaingroup_id'], ''))
    motifnames = {sid: ", ".join(sorted(names)) for sid, names in motifnames.items()}
    motifnames = {seq.sequence_id: motifnames.get(seq.sequence_id, '') for seq in sequences}

    context["sequences"] = sequences
    context["speciesname"] = speciesname
    context["motifnames"] = motifnames
    context["segment"] = segment
    context["is_staff"] = request.user.is_staff

    hmmMoldes = []
    for d in os.listdir('utils/hmmModels/'):
        if not os.path.isdir('utils/hmmModels/%s' % (d)):
            continue
        for f in os.listdir('utils/hmmModels/%s' % (d)):
            hmmMoldes.append(f.split('.hmm')[0])
    hmmMoldes.sort()
    context["hmmModels"] = hmmMoldes

    return render(request, 'home/query-sequences-results.html', context)


class SequencesResultsTable(tables.Table):
    name = tables.Column()
    speciesshortname = tables.Column()
    scientificname = tables.Column()
    motifs = tables.Column()
    sourcedatabase = tables.Column()
    foreignannotation = tables.Column()
    sequence = tables.Column()


def QuerySequencesFastaFormat(request):
    if request.method == 'POST':
        boxes = request.POST.getlist('checkbox')

    try:
        sequences = Sequences.objects.filter(pk__in=boxes)
    except Sequences.DoesNotExist:
        raise Http404("Sequences does not exist")

    if 'download_table' in request.POST:
        data = [{'name': x.sequenceshortname,
                 'speciesshortname': x.taxonomy.taxonomyshortname,
                 'scientificname': x.taxonomy.scientificname,
                 'motifs': ", ".join([m.motifname for m in x.motifs_set.all()]),
                 'sourcedatabase': x.sourcedatabase,
                 'foreignannotation': x.foreignannotation,
                 'sequence': x.sequence} for x in sequences]
        table = SequencesResultsTable(data)
        RequestConfig(request).configure(table)
        export_format = 'tsv'
        if TableExport.is_valid_format(export_format):
            exporter = TableExport(export_format, table)
            return exporter.response(f"sequencesResult.{export_format}")

    if 'fasta_seq' in request.POST or 'fasta_motif' in request.POST:
        if 'fasta_seq' in request.POST:
            return render(request, 'home/query-sequences-fasta.html', {'sequences': sequences})
        elif 'fasta_motif' in request.POST:
            motifs_seqs = {}
            for seq in sequences:
                for m in seq.motifs_set.all():
                    mdata = {}
                    for x in ET.fromstring(m.asciioutput):
                        mdata[x.tag] = x.text
                    s = mdata['motif'].upper().replace("-", "").strip()
                    name = seq.sequenceshortname + "|" + "_".join([m.domaingroup.domain.domainname, m.domaingroup.domaingroupname])
                    motifs_seqs[name] = s
            return render(request, 'home/query-sequences-fasta.html', {'motifs_seqs': motifs_seqs})

    elif 'multialignment' in request.POST or 'download_multialignment' in request.POST:
        if len(sequences) < 2:
            return render(request, 'home/query-sequences-multialignment.html', {'names': []})
        hmmModel = request.POST.get('hmmModel', '')
        for d in os.listdir('utils/hmmModels/'):
            if not os.path.isdir('utils/hmmModels/%s' % (d)):
                continue
            for f in os.listdir('utils/hmmModels/%s' % (d)):
                if hmmModel and hmmModel[0] in f:
                    with pyhmmer.plan7.HMMFile("./utils/hmmModels/%s/%s" % (d, f)) as hmm_file:
                        hmm = hmm_file.read()
        alphabet = pyhmmer.easel.Alphabet.amino()
        background = pyhmmer.plan7.Background(alphabet)
        digitalsequences = [pyhmmer.easel.TextSequence(name=bytes(seq.sequenceshortname, 'utf-8'), sequence=seq.sequence).digitize(alphabet) for seq in sequences]
        MSA = pyhmmer.hmmer.hmmalign(hmm, digitalsequences, digitize=False)
        names = [name.decode("utf-8") for name in MSA.names]
        alignedsequences = {}
        for i in range(len(names)):
            alignedsequences[names[i]] = MSA.alignment[i]
        if 'download_multialignment' in request.POST:
            file_data = ""
            for al in alignedsequences:
                file_data += ">" + al + "\n" + alignedsequences[al] + "\n"
            response = HttpResponse(file_data, content_type='application/text charset=utf-8')
            safe_name = re.sub(r'[^\w\-]', '', hmmModel)
            response['Content-Disposition'] = 'attachment; filename="%s_MSA.fasta"' % safe_name
            return response
        zippedLists = {}
        for i in range(len(names)):
            alignment = [*MSA.alignment[i]]
            upperList = []
            for n in alignment:
                upperList.append([1 if n.isupper() else 0][0])
            zippedLists[names[i]] = zip(alignment, upperList)
        return render(request, 'home/query-sequences-multialignment.html', {'names': names, 'zippedLists': zippedLists, 'alignedsequences': alignedsequences})
    else:
        return render(request, 'home/query-sequences-fasta.html', {'sequences': sequences})


def QuerySequences3dViewer(request, sequence_id):
    context = {'is_staff': request.user.is_staff}
    try:
        context['sequence'] = Sequences.objects.get(pk=sequence_id)
    except Sequences.DoesNotExist:
        context['log'] = 'Seqence ID %s not found in TRACEY' % (sequence_id)
        return render(request, 'home/query-sequences-details.html', context)

    if not user_can_access_sequence(request, context['sequence']):
        raise Http404

    context["fetch3d"] = get_alphafold_url(context['sequence'].sequence)

    motifs = context['sequence'].motifs_set.all()
    motif_coords = {}
    for m in motifs:
        motif_coords[m.domaingroup.domaingroupname] = {"start": m.get_real_startposition(),
                                                       "end": m.get_real_stopposition(),
                                                       "domain": m.domaingroup.domain.domainname}
    context["motif_coords"] = motif_coords

    return render(request, 'home/query-sequences-3dViewer.html', context)


def QuerySequencesDetails(request, sequence_id):
    segment = request.path.split('/')[-4]
    context = {"segment": segment,
               'is_staff': request.user.is_staff}

    try:
        context['sequence'] = Sequences.objects.get(pk=sequence_id)
    except Sequences.DoesNotExist:
        context['log'] = 'Seqence ID %s not found in TRACEY' % (sequence_id)
        return render(request, 'home/query-sequences-details.html', context)

    if not user_can_access_sequence(request, context['sequence']):
        raise Http404

    context["speciesname"] = [x.scientificname for x in Taxonomies.objects.filter(taxonomy_id=context['sequence'].taxonomy_id)][0]
    context["wiki_image"] = get_wikipedia_image(context["speciesname"])
    if 'pdb' in context['sequence'].foreignannotation:
        m = re.search(r'pdb\|([A-Z0-9]+)\|([A-z0-9\s]+)', context['sequence'].foreignannotation)
        context["pdb"] = m.group(1)
        context["pdb_name"] = m.group(2)

    context["fetch3d"] = get_alphafold_url(context['sequence'].sequence)
    if context["fetch3d"]:
        motifs = context['sequence'].motifs_set.all()
        motif_coords = {}
        for m in motifs:
            motif_coords[m.domaingroup.domaingroupname] = {"start": m.get_real_startposition(),
                                                           "end": m.get_real_stopposition(),
                                                           "domain": m.domaingroup.domain.domainname}
        context["motif_coords"] = motif_coords

    context["layout"] = build_domain_plot(len(context['sequence'].sequence), context['sequence'].motifs_set.all())
    motifs = Motifs.objects.filter(sequence_id=context['sequence'].sequence_id).order_by('startposition')

    context["motifs"] = {}
    for m in motifs:
        context["motifs"][m] = {}
        d = Domaingroups.objects.get(domaingroup_id=m.domaingroup_id)

        if d.domaingroupparent_id == None:
            context["motifs"][m]["domaingroupparent"] = m.motifname
        elif ";" in d.domaingroupparent_id:
            p_id = d.domaingroupparent_id.split(";")
            context["motifs"][m]["domaingroupparent"] = Domaingroups.objects.get(domaingroup_id=p_id[0]).domaingroupname + "/" + Domaingroups.objects.get(domaingroup_id=p_id[1]).domaingroupname
        else:
            context["motifs"][m]["domaingroupparent"] = Domaingroups.objects.get(domaingroup_id=d.domaingroupparent_id).domaingroupname
        context["motifs"][m]["domaingroup"] = d.domaingroupname
        context["motifs"][m]["ascii"] = m.asciioutput

        data = ET.fromstring(context["motifs"][m]["ascii"])
        for x in data:
            context["motifs"][m][x.tag] = x.text
        context["motifs"][m]["eValueFloat"] = float(context["motifs"][m]["eValue"])
        context["motifs"][m]["plot"] = build_domain_plot(len(context['sequence'].sequence), [m], eval=context["motifs"][m]["eValueFloat"])

    return render(request, 'home/query-sequences-details.html', context)


def DetailsSequencesFastaFormat(request, sequence_id):
    try:
        sequence = Sequences.objects.get(pk=sequence_id)
    except Sequences.DoesNotExist:
        raise Http404("Sequence does not exist")

    if not user_can_access_sequence(request, sequence):
        raise Http404

    return render(request, 'home/details-sequences-fasta.html', {'sequence': sequence})


def suggest_aliases(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 3:
        return JsonResponse([], safe=False)
    suggestions = (
        Sequences.objects
        .filter(aliases__icontains=q)
        .exclude(aliases__isnull=True).exclude(aliases='')
        .values_list('aliases', flat=True)
        .distinct()[:15]
    )
    return JsonResponse(list(suggestions), safe=False)
