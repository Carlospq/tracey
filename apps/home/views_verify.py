import re
import xml.etree.ElementTree as ET
from time import gmtime, strftime

from Bio.Blast.Applications import NcbiblastpCommandline

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.shortcuts import render

from .models import *
from .forms import *
from .utils import get_menu
from .plots import build_domain_plot, get_pdb_data
from .views_motifs import motifScan

from utils.ncbi_taxonomy.reducedTRACEYtaxonomies import *


rec_login_required = user_passes_test(lambda u: True if u.is_staff else False, login_url="/noPermits.html")


def is_staff(self):
    if str(self.user_type) == 'Staff':
        return True
    else:
        return False


def staff_login_required(view_func):
    decorated_view_func = login_required(rec_login_required(view_func), login_url='/')
    return decorated_view_func


def saveVerifyMotifs(sequence_id, hits):

    def countGaps(alignment):
        gaps = []
        count = 0
        gapInitialPosition = 0
        for i in range(len(alignment)):
            if alignment[i] == "-":
                if gapInitialPosition == 0:
                    gapInitialPosition = i
                count += 1
            else:
                if count > 0:
                    gaps.append("%s:%s" % (gapInitialPosition, count))
                count = 0
                gapInitialPosition = 0
        if count > 0:
            gaps.append("%s:%s" % (gapInitialPosition, count))
        return ", ".join(gaps)

    for motif in hits:
        motifInfo = hits[motif]
        for d in motifInfo['domains']:
            try:
                method = Methods.objects.get(domaingroup_id=Domaingroups.objects.get(domaingroupname=d['dg']).domaingroup_id)
            except Methods.DoesNotExist:
                method = Methods(domaingroup_id=Domaingroups.objects.get(domaingroupname=d['dg']).domaingroup_id,
                                 input='', type='hmm', parameter='')
                method.save()
            vm = Verifymotifs(sequence_id=sequence_id,
                              motifname=motif,
                              startposition=d['aln_from'],
                              stopposition=d['aln_to'],
                              verifymotifcomments='',
                              domaingroup_id=Domaingroups.objects.get(domaingroupname=d['dg']).domaingroup_id,
                              gaps=countGaps(d['alignment'].target_sequence),
                              active=0,
                              method=method,
                              verifymotifrank=1000000,
                              asciioutput='<asciiOutput>\r\t<consensus>%s</consensus>\r\t<similarity>%s\t</similarity>\r\t<motif>%s</motif>\r\t<eValue>%s</eValue>\r\t<bitscore>321</bitscore>\r</asciiOutput>' % (d['alignment'].hmm_sequence, d['alignment'].identity_sequence, d['alignment'].target_sequence, d['evalue']),
                              binaryoutput='')

            if Verifymotifs.objects.filter(sequence_id=sequence_id, asciioutput=vm.asciioutput).exists() or Motifs.objects.filter(sequence_id=sequence_id, asciioutput=vm.asciioutput).exists():
                continue
            else:
                vm.save()


def common_name(list, sn):
    arr = {}
    for name in list:
        l = len(name)
        for i in range(l):
            for j in range(l + 1):
                if j <= i:
                    continue
                subname = name[i:j].replace("_", "")
                if len(subname) < 3 or subname == "ref":
                    continue
                if not subname in arr:
                    arr[subname] = 1
                else:
                    arr[subname] += 1

    sorted_arr = sorted(arr.items(), key=lambda x: -x[1])
    top = [x[0] for x in sorted_arr if x[1] / len(list) >= 0.5]
    common_names = []
    for i in range(len(top)):
        unique = True
        for j in range(len(top)):
            if i == j:
                continue
            if top[i] in top[j]:
                unique = False
        if unique and top[i] not in common_names:
            common_names.append(sn + "_" + top[i])
    return common_names


def suggested_names(sequence, shortname="Query"):
    blastp_path = 'utils/ncbi-blast-2.13.0+/bin/blastp'
    file_path = 'utils/ncbi-blast-2.13.0+/query_vm.fasta'
    sn = shortname.split("_")[0]
    with open(file_path, 'w') as fasta_file:
        fasta_file.write('>' + shortname + '\n' + sequence)
    blastp_cline = NcbiblastpCommandline(cmd=blastp_path, query=file_path, db="utils/ncbi-blast-2.13.0+/traceyBLASTdb/traceyverify", outfmt=6)
    stdout, stderr = blastp_cline()
    shortnames = [y[1].split("|")[0][y[1].find('_') + 1:] for y in [x.split("\t") for x in stdout.split("\n") if len(x) > 1] if float(y[2]) > 95]
    suggestedNames = common_name(shortnames, sn)
    return suggestedNames


def suggestNames(request):
    suggestedNames = suggested_names(request.POST['sequence'])
    return render(request, 'home/query-verify-suggestedNames.html', {'suggested_names': ", ".join(suggestedNames)})


@login_required(login_url="/noPermits.html")
@staff_login_required
def QueryInsertView(request):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    segment = request.path.split('/')[-1]
    context = {'segment': segment}

    if request.method == 'POST':
        form = InsertSequence(request.POST)

        updated_request = request.POST.copy()
        id_ = dict(request.POST)['gene'][0]
        if id_ == '':
            updated_request.update({'gene': 'create_new:-1'})
        else:
            updated_request.update({'gene': id_})

        form = InsertSequence(updated_request)

        if form.is_valid():
            form.cleaned_data['changelog'] = strftime("%d.%m.%Y|%H:%M:%S|", gmtime()) + user.username + ' - insertSequence;'
            try:
                new_form = form.save(commit=False)
                new_form.changelog = form.cleaned_data['changelog']
                new_form.save()
                hits = motifScan(form.cleaned_data['sequence'], ["ALL"], menu=get_menu(request))
                saveVerifyMotifs(new_form.pk, hits)
                return HttpResponseRedirect(reverse('query-verify', args=(new_form.pk,)))
            except Exception:
                form.cleaned_data['gene'].delete()
                form.cleaned_data['gene'] = ""
                context["form"] = form
                context["error"] = "Error while inserting sequence in TRACEY. Please check your input data."
                return render(request, 'home/query-insert.html', context)
        else:
            context["form"] = form
            return render(request, 'home/query-insert.html', context)

    context["form"] = InsertSequence(initial={'status': 'live'})
    return render(request, 'home/query-insert.html', context)


@login_required(login_url="/noPermits.html")
@staff_login_required
def QueryVerifyMenuView(request):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    shortnames = sorted(list(set([t.taxonomyshortname for t in Taxonomies.objects.filter(analysislevel__gte=4) if t.taxonomyrank == "species" and any(t.sequences_set.all())])))
    taxonomy_ranks = [x for x in reducedTRACEYtaxonomies]
    context = {'segment': request.path.split('/')[-1],
               'sequences': Sequences.objects.none(),
               'speciesname': {},
               'MotifForm': MotifForm(initial={'status': 'live'}),
               'taxonomy_ranks': taxonomy_ranks,
               'shortnames': shortnames,
               }
    context['log'] = len(context['sequences'])
    return render(request, 'home/query-verify-menu.html', context)


def parseNCBIblastpSTDOUT(stdout):

    def count_white_spaces(s):
        spaces = []
        count = 0
        for c in s:
            if c.isspace():
                count += 1
            if not c.isspace() and count > 0:
                spaces.append(count)
                count = 0
        return (spaces)

    lines = stdout.split("\n")
    scores = {}
    alignments = {}
    sequencesIDs = []
    dbBlast_ids = ["Query_1"]
    align_block = 0
    switch = 0
    for line in lines:
        if line.startswith('Query='):
            switch += 1
        if line.startswith('Lambda'):
            break
        if switch == 0 or not line:
            continue
        if switch == 1:
            query_header = line
            switch += 1
            continue
        if switch == 2:
            query_length = line
            switch += 1
            continue
        if switch == 3 and "Bits" in line:
            scores_header = line
            switch += 1
            continue
        if switch == 4:
            values = line.split()
            if len(values) == 3:
                seqID = values[0].split("|")[0]
                sequencesIDs.append(seqID)
                scores[seqID] = {'seqID': values[0], 'bits': values[1], 'e-value': values[2]}
            elif len(values) == 4:
                if values[0] == "Query_1":
                    align_block += 1
                try:
                    if not values[0] in dbBlast_ids:
                        previous_id_index = dbBlast_ids.index(previous_id)
                        dbBlast_ids.insert(previous_id_index + 1, values[0])
                    if values[0] in alignments:
                        alignments[values[0]]['stop'] = values[3]
                        alignments[values[0]]['alignment'] += values[2]
                    else:
                        if values[0] != "Query_1":
                            extra_gaps_start = count_white_spaces(line)[1] - query_gaps[1] + len(str(values[1])) - len(str(alignments['Query_1']['start'])) + 60 * (align_block - 1)
                            alignments[values[0]] = {'seqID': '', 'start': values[1], 'alignment': extra_gaps_start * "-" + values[2], 'stop': values[3], 'e-value': ''}
                        else:
                            query_gaps = count_white_spaces(line)
                            alignments[values[0]] = {'seqID': values[0], 'start': values[1], 'alignment': values[2], 'stop': values[3], 'e-value': '-'}
                    previous_id = values[0]
                except IndexError:
                    continue

    for dbx in dbBlast_ids[1:]:
        idx = dbBlast_ids.index(dbx)
        alignments[dbBlast_ids[idx]]['seqID'] = sequencesIDs[idx - 1]
        alignments[dbBlast_ids[idx]]['e-value'] = scores[sequencesIDs[idx - 1]]['e-value']

    query_alignment = alignments.pop("Query_1")
    for ID in alignments:
        query_length_val = len(query_alignment['alignment'])
        match_length = len(alignments[ID]['alignment'])
        extra_gaps_end = query_length_val - match_length
        alignments[ID]['alignment'] = alignments[ID]['alignment'] + "-" * extra_gaps_end

    return [query_header, query_length, scores_header, scores, query_alignment, alignments]


@login_required(login_url="/noPermits.html")
@staff_login_required
def QueryVerifyBlastView(request, db, query_id):
    alignment_colors = {'A': 'CornflowerBlue', 'I': 'CornflowerBlue', 'L': 'CornflowerBlue', 'M': 'CornflowerBlue', 'F': 'CornflowerBlue', 'W': 'CornflowerBlue', 'V': 'CornflowerBlue', 'C': 'CornflowerBlue',
                        'K': 'red', 'R': 'red',
                        'E': 'magenta', 'D': 'magenta',
                        'N': 'lightgreen', 'Q': 'lightgreen', 'S': 'lightgreen', 'T': 'lightgreen',
                        'G': 'orange',
                        'P': 'yellow',
                        'H': 'cyan', 'Y': 'cyan',
                        '-': 'none', '.': 'none'}
    if db[-1] == 'v':
        query = Verifymotifs.objects.get(pk=int(query_id))
        start = [query.startposition - 1 if query.startposition - 1 > 0 else 0][0]
        query_sequence = query.sequence.sequence[start:query.stopposition]
        shortname = "_".join([query.sequence.sequenceshortname, query.motifname])
    elif db[-1] == 'm':
        query = Motifs.objects.get(pk=int(query_id))
        query_sequence = query.sequence.sequence[query.startposition - 1:query.stopposition]
        shortname = "_".join([query.sequence.sequenceshortname, query.motifname])
    elif db[-1] == 's':
        query = Sequences.objects.get(pk=int(query_id))
        query_sequence = query.sequence
        shortname = query.sequenceshortname

    if db[-2] == 'a':
        db_type = 'all'
        db_path = 'utils/ncbi-blast-2.13.0+/traceyBLASTdb/traceyall'
    elif db[-2] == 'v':
        db_type = 'verify'
        db_path = 'utils/ncbi-blast-2.13.0+/traceyBLASTdb/traceyverify'
    elif db[-2] == 'u':
        db_type = 'unverify'
        db_path = 'utils/ncbi-blast-2.13.0+/traceyBLASTdb/traceyunverify'

    context = {'query_id': query_id,
               'name': shortname,
               'motif_length': len(query_sequence),
               'blast_error': '',
               'blast_result': '',
               'header': ['query acc.ver', 'subject acc.ver', '% identity', 'alignment length', 'mismatches', 'gap opens', 'q. start', 'q. end', 's. start', 's. end', 'evalue', 'bit score']}
    if "NCBI" in db:
        context['db'] = "NCBI"
    else:
        context['db'] = db[:-2] + '_' + db_type
    context['fasta_sequence'] = '>' + context['name'] + "\n%s" % (query_sequence)

    file_path = 'utils/ncbi-blast-2.13.0+/query_vm.fasta'
    if 'TRACEY' in context['db']:
        blastp_path = 'utils/ncbi-blast-2.13.0+/bin/blastp'
        with open(file_path, 'w') as fasta_file:
            fasta_file.write(context['fasta_sequence'])

        blastp_cline = NcbiblastpCommandline(cmd=blastp_path, query=file_path, db=db_path, num_alignments=500, max_hsps=1, outfmt=4)
        stdout, stderr = blastp_cline()

        blastp_cline_pairwise = NcbiblastpCommandline(cmd=blastp_path, query=file_path, db=db_path, num_alignments=500, max_hsps=1, outfmt=0)
        stdout_pairwise, stderr_pairwise = blastp_cline_pairwise()

        context['pairwise'] = stdout_pairwise
        if stderr:
            context['blast_error'] = stderr
        else:
            parsedstdout = parseNCBIblastpSTDOUT(stdout)
            context['query_header'] = parsedstdout[0]
            context['query_length'] = parsedstdout[1]
            context['scores_header'] = parsedstdout[2]
            context['scores'] = parsedstdout[3]
            context['query_alignment'] = parsedstdout[4]
            context['alignments'] = parsedstdout[5]
            context['alignment_colors'] = alignment_colors

    elif context['db'] == 'NCBI':
        ncbi_url = 'https://blast.ncbi.nlm.nih.gov/Blast.cgi?PROGRAM=blastp&PAGE_TYPE=BlastSearch&LINK_LOC=blasthome&QUERY=%s' % (context['fasta_sequence'])
        return HttpResponseRedirect(ncbi_url)
    else:
        context['blast_error'] = 'An error ocurred while choosing database..'

    return render(request, 'home/query-verify-blast.html', context)


@login_required(login_url="/noPermits.html")
@staff_login_required
def QueryVerifyView(request, sequence_id):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    segment = request.path.split('/')[-2]
    context = {'segment': segment}
    context['sequence_id'] = sequence_id
    context['proteinLayoutsList'] = sorted([pfam for pfam in get_menu(request)])

    try:
        seq = Sequences.objects.get(pk=sequence_id)
        context["sequence"] = seq
        context["layout"] = build_domain_plot(len(seq.sequence), seq.motifs_set.all())
    except Sequences.DoesNotExist:
        context['log'] = 'Seqence ID %s not found in TRACEY' % (sequence_id)
        return render(request, 'home/query-verify.html', context)

    if 'deleteSequence' in request.POST:
        seq.delete()
        return render(request, 'home/query-verify-menu.html')

    if seq.gene.ncbigene_id == '-1':
        ncbigene_id = 'not_specified:-1:%s' % (seq.gene.gene_id)
    else:
        ncbigene_id = seq.gene.ncbigene_id

    context['domainsList'] = [d.domainname for d in Domains.objects.all()]

    if request.method == 'POST':
        form = InsertSequence(request.POST, instance=seq, initial={'gene': ncbigene_id, })

        _mutable = form.data._mutable
        form.data._mutable = True
        if form.data['newChangelog']:
            form.data['changelog'] += " %s %s - %s;" % (strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, form.data['newChangelog'])
            form.data['newChangelog'] = ''

        for vm_id in request.POST.getlist('verifymotif_id'):
            requestValue, vm_id = vm_id.split(":")
            vm = Verifymotifs.objects.get(verifymotif_id=vm_id)

            if requestValue == 'delete':
                vm.delete()
                form.data['changelog'] += " %s %s - VerifyMotif deleted: '%s';" % (strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, vm.motifname)
            elif requestValue == 'verify':
                m = Motifs(sequence=seq,
                           motifname=vm.motifname,
                           startposition=vm.startposition,
                           stopposition=vm.stopposition,
                           motifcomments=vm.verifymotifcomments,
                           domaingroup=vm.domaingroup,
                           gaps=vm.gaps,
                           active=1,
                           method=vm.method,
                           motifrank=vm.verifymotifrank,
                           asciioutput=vm.asciioutput,
                           binaryoutput=vm.binaryoutput)
                m.save()
                form.data['changelog'] += " %s %s - Verified motif: '%s';" % (strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, m.motifname)
                vm.delete()

        for m_id in request.POST.getlist('motif_id'):
            requestValue, m_id = m_id.split(":")
            motif = Motifs.objects.filter(motif_id=m_id)[0]

            if requestValue == 'delete':
                motif.delete()
                form.data['changelog'] += " %s %s - Motif deleted: '%s';" % (strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, motif.motifname)
            elif requestValue == 'unverify':
                vm = Verifymotifs(sequence=motif.sequence,
                                  motifname=motif.motifname,
                                  startposition=motif.startposition,
                                  stopposition=motif.stopposition,
                                  verifymotifcomments=motif.motifcomments,
                                  domaingroup=motif.domaingroup,
                                  gaps=motif.gaps,
                                  active=0,
                                  method=motif.method,
                                  verifymotifrank=motif.motifrank,
                                  asciioutput=motif.asciioutput,
                                  binaryoutput=motif.binaryoutput)
                vm.save()
                form.data['changelog'] += " %s %s - Unverified motif: '%s';" % (strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, motif.motifname)
                motif.delete()

        form.data._mutable = _mutable

        if request.POST.get("scan"):
            if not form.data['proteinlayout']:
                context['scanerror'] = 'Protein layout is required to scan sequence for HMM matches'
            elif form.data['sequence'] and form.data['proteinlayout']:
                mutable_ = form.data._mutable
                form.data._mutable = True
                evalcutoff = float('1e-' + request.POST.get('evalcutoff') if request.POST.get('evalcutoff') else '10')
                form.data['domain'] = form.data['domain'] if 'domain' in form.data else ''
                form.data['domaingroup'] = form.data['domaingroup'] if 'domaingroup' in form.data else ''
                form.data['domainsubgroup'] = form.data['domainsubgroup'] if 'domainsubgroup' in form.data else ''
                form.data._mutable = mutable_

                hits_d = motifScan(form.data['sequence'], proteinlayout=form.data['proteinlayout'], domain=form.data['domain'], domaingroup=form.data.get('domaingroups', ''), domainsubgroup=form.data.get('domainsubgroups', ''), evalcutoff=evalcutoff, menu=get_menu(request))
                if 'error' in hits_d:
                    context['scanerror'] = hits_d['error']
                else:
                    saveVerifyMotifs(sequence_id, hits_d)

                context['domain'] = request.POST.get('domain')
                context['domaingroups'] = request.POST.get('domaingroups')
                context['evalcutoff'] = request.POST.get('evalcutoff')

        context['form'] = form
        if form.is_valid():
            if request.htmx or 'scanerror' in context:
                return render(request, 'home/query-verify.html', context)
            try:
                form.save()
            except Exception:
                context['message'] = 'Sequence could not be updated'

    else:
        context['form'] = InsertSequence(instance=seq, initial={'gene': ncbigene_id, 'taxonomy': seq.taxonomy.scientificname})

    motifs = seq.motifs_set.all().order_by('startposition')
    verifymotifs = seq.verifymotifs_set.all().order_by('startposition')
    context["motifs"] = {}
    context["verifymotifs"] = {}

    for type, motifs in zip(['motifs', 'verifymotifs'], [motifs, verifymotifs]):
        for m in motifs:
            context[type][m] = {}
            if type == "motifs":
                context[type][m]['motif_id'] = m.motif_id
            else:
                context[type][m]['verifymotif_id'] = m.verifymotif_id
            d = Domaingroups.objects.get(domaingroup_id=m.domaingroup_id)

            if d.domaingroupparent_id == None:
                context[type][m]["domaingroupparent"] = m.motifname
            elif ";" in d.domaingroupparent_id:
                p_id = d.domaingroupparent_id.split(";")
                context[type][m]["domaingroupparent"] = Domaingroups.objects.get(
                    domaingroup_id=p_id[0]).domaingroupname + "/" + Domaingroups.objects.get(
                    domaingroup_id=p_id[1]).domaingroupname
            else:
                context[type][m]["domaingroupparent"] = Domaingroups.objects.get(
                    domaingroup_id=d.domaingroupparent_id).domaingroupname

            context[type][m]["domaingroup"] = d.domaingroupname
            context[type][m]["ascii"] = m.asciioutput

            data = ET.fromstring(context[type][m]["ascii"])
            for x in data:
                context[type][m][x.tag] = x.text

            data = ET.fromstring(context[type][m]["ascii"])
            for x in data:
                context[type][m][x.tag] = x.text
            context[type][m]["eValueFloat"] = float(context[type][m]["eValue"])
            context[type][m]["plot"] = build_domain_plot(len(seq.sequence), [m])

    context["verifymotifs"] = {k: v for k, v in sorted(context["verifymotifs"].items(), key=lambda x: x[1]['eValueFloat'])}

    data_3d = get_pdb_data(seq.sequence)
    context['pdb_url'] = data_3d['pdb_url'] if data_3d else ''

    motifs = context['sequence'].motifs_set.all()
    motif_coords = {}
    for m in motifs:
        motif_coords[m.domaingroup.domaingroupname] = {"start": m.get_real_startposition(),
                                                       "end": m.get_real_stopposition(),
                                                       "domain": m.domaingroup.domain.domainname}
    context["motif_coords"] = motif_coords

    return render(request, 'home/query-verify.html', context)


def autocompleteModel(request):
    search = request.GET.get('search', '')
    search_qs = Taxonomies.objects.filter(
        scientificname__istartswith=search
    ).filter(taxonomyrank__in=["species", "strain"])
    if len(search) >= 3 or len(search_qs) < 150:
        results = list(search_qs.values_list('scientificname', flat=True))
    else:
        results = []
    return JsonResponse(results, safe=False)
