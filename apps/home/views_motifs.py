import os
import re
import pyhmmer

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render

from .models import *
from .utils import get_menu, get_children, notEmpty
from .plots import build_domain_plot_from_PyHammer

from apps.templates.menus.query_sequences import get_keys_recursively
from apps.templates.menus.query_sequences import menu as menu_public
from utils.motifPredictor.predictor import *


def motifScan(sequence, proteinlayout="", domain="", domaingroup="", domainsubgroup="", evalcutoff=1e-10, menu=None):
    if menu is None:
        menu = menu_public

    hits_d = {}

    count_gt = sequence.count(">")
    count_nl = sequence.count("\n")
    if count_gt >= 1:
        hits_d['error'] = 'Fasta format is not valid for this search. Please remove the header of the sequence.'
        return hits_d
    elif count_nl >= 1:
        hits_d['error'] = 'Sequence format is nos valid. Please provide only one sequence and check that there is no new line character and the end of the sequence.'
        return hits_d

    alphabet = pyhmmer.easel.Alphabet.amino()
    seq1 = pyhmmer.easel.TextSequence(name=b"Query sequence", sequence=sequence).digitize(alphabet)

    if proteinlayout.upper() == "ALL":
        hmms = pyhmmer.plan7.HMMFile("./utils/hmmModels/MOTIFS.hmmDb")
    else:
        if domainsubgroup:
            hmms = [domainsubgroup.replace("-", "")]
        elif domaingroup:
            hmms = get_keys_recursively(menu[proteinlayout][domain][domaingroup]) + [domaingroup]
        elif domain:
            hmms = get_keys_recursively(menu[proteinlayout][domain]) + [domain]
        elif proteinlayout:
            hmms = get_keys_recursively(menu[proteinlayout]) + [proteinlayout]
        else:
            hmms = get_keys_recursively(menu)

        hmmList = [hmm for folder in os.listdir('utils/hmmModels/') if os.path.isdir('utils/hmmModels/%s' % (folder)) for hmm in os.listdir('utils/hmmModels/%s' % (folder)) if hmm.replace(".hmm", "") in hmms]

        if not hmmList:
            hits_d['error'] = 'No HMM model found for this motif.'
            return hits_d

        hmms = []
        for hmmModel in hmmList:
            folder = [f for f in os.listdir('utils/hmmModels/') if os.path.isdir('utils/hmmModels/%s' % f) and hmmModel in os.listdir('utils/hmmModels/%s' % f)][0]
            with pyhmmer.plan7.HMMFile('utils/hmmModels/%s/%s' % (folder, hmmModel)) as hmm_file:
                hmm = hmm_file.read()
                hmms.append(hmm)

    optimized_block = pyhmmer.plan7.OptimizedProfileBlock(alphabet=alphabet)
    for h in hmms:
        optimized_block.append(h.to_profile().to_optimized())

    pipeline = pyhmmer.plan7.Pipeline(pyhmmer.easel.Alphabet.amino())
    hits = pipeline.scan_seq(seq1, optimized_block)

    for h in hits:
        if not any([d for d in h.domains if d.pvalue < evalcutoff]):
            continue
        h_name = h.name.decode('UTF-8')
        hits_d[h_name] = {}
        hits_d[h_name]['sequence'] = sequence
        hits_d[h_name]['plot'] = build_domain_plot_from_PyHammer(len(sequence), h, evalcutoff)
        hits_d[h_name]['split_sequence'] = [letter for letter in sequence]
        hits_d[h_name]['domainname'] = Domaingroups.objects.get(domaingroupname=h_name).domain.domainname
        hits_d[h_name]['domains'] = []
        for d in h.domains:
            if d.pvalue > evalcutoff:
                continue
            split_alignment = str(d.alignment).split("\n")
            motifname = split_alignment[0].split()[0] if split_alignment[0].split()[-1] not in ["RF", "SC"] else split_alignment[1].split()[0]
            dgs = Domaingroups.objects.filter(domaingroupname=motifname)
            for dg in dgs:
                domain_obj = Domains.objects.get(domain_id=dg.domain_id).domainname
                if dg.domaingroupparent_id == None:
                    dg_parent = motifname
                elif ";" in dg.domaingroupparent_id:
                    dg_parent = "/".join([x.domaingroupname for x in Domaingroups.objects.filter(domaingroup_id__in=dg.domaingroupparent_id.split(";"))])
                else:
                    dg_parent = Domaingroups.objects.get(domaingroup_id=dg.domaingroupparent_id).domaingroupname

                match = re.search(re.escape(d.alignment.target_sequence.strip().replace("-", "").upper()), sequence)
                x = {'evalue': format(d.pvalue, '.1E'),
                     'pvalue': d.pvalue,
                     'aln_from': match.start() + 1,
                     'aln_to': match.end(),
                     'length': match.end() - (match.start() + 1) + 1,
                     'alignment': d.alignment,
                     'dg': dg.domaingroupname,
                     'dg_parent': dg_parent,
                     'domain': domain_obj,
                     }
                hits_d[h_name]['domains'].append(x)

        hits_d[h_name]["domains"] = sorted(hits_d[h_name]["domains"], key=lambda d: d['pvalue'])

    return hits_d


def QueryMotifsView(request):
    segment = request.path.split('/')[-1]
    context = {"segment": segment,
               "proteinLayoutsList": sorted([pfam for pfam in get_menu(request)]),
               "domainList": [],
               }

    if request.method == "POST":
        context['protseq'] = dict(request.POST)['protseq']
        context['proteinlayout'] = dict(request.POST)['proteinlayout'] if 'proteinlayout' in request.POST else ['']
        context['domain'] = dict(request.POST)['domain'] if 'domain' in request.POST else ['']
        context['domaingroup'] = dict(request.POST)['domaingroup'] if 'domaingroup' in request.POST else ['']
        context['domainsubgroup'] = dict(request.POST)['domainsubgroup'] if 'domainsubgroup' in request.POST else ['']
        context['evalcutoff'] = [request.POST.get('evalcutoff')] if request.POST.get('evalcutoff') else ['10']

        if not context['protseq'][0]:
            context['error'] = 'Please provide a protein sequence to analyze.'
            return render(request, 'home/query-motifs.html', context)
        elif len(context['protseq'][0]) > 2000:
            context['error'] = 'Sequence is too long [max length = 2000 aa].'
            return render(request, 'home/query-motifs.html', context)
        else:
            request.session['context'] = context
            return HttpResponseRedirect(reverse('query-motifs-results'), context)

    return render(request, 'home/query-motifs.html', context)


def QueryMotifsResultsView(request):
    if 'context' in request.session:
        context = request.session['context']
        del request.session['context']
    elif request.method == "POST":
        context = dict(request.POST)
    else:
        context = dict(request.GET)

    segment = request.path.split('/')[-1]
    context["segment"] = segment

    context["proteinLayoutsList"] = sorted([pfam for pfam in get_menu(request)])
    context["domainList"] = []
    context["domaingroupList"] = []
    context["domainsubgroupList"] = []

    context['proteinlayout'] = context['proteinlayout'] if 'proteinlayout' in context else ['']
    context['domain'] = context['domain'] if 'domain' in context else ['']
    context['domaingroup'] = context['domaingroup'] if 'domaingroup' in context else ['']
    context['domainsubgroup'] = context['domainsubgroup'] if 'domainsubgroup' in context else ['']

    if context['domain'][0] != "all":
        domain = Domains.objects.filter(domainname=context['domain'][0])
        context["domaingroupList"] = sorted([x.domaingroupname for x in Domaingroups.objects.filter(domain_id__in=domain.values('domain_id')) if x.analysislevel == 2]) if domain else []

    if 'domaingroup' in context and notEmpty(context, 'domaingroup'):
        domaingroup = Domaingroups.objects.filter(domaingroupname=context['domaingroup'][0])[0]
        context["domainsubgroupList"] = get_children(Domaingroups, Domaingroups.objects.filter(domaingroupname=domaingroup.domaingroupname), "domaingroup_id", "domaingroupparent_id", children=[])
        context["domainsubgroupList"] = ["-" * (int(x.analysislevel) - 2) + x.domaingroupname for x in context["domainsubgroupList"] if x.analysislevel > 2 and (any(x.motifs_set.all()) or any(x.verifymotifs_set.all()))]

    context["hits_d"] = {}
    if notEmpty(context, 'protseq'):
        if len(context['protseq'][0]) > 2000:
            context['error_seq'] = 'Sequence is too long [max length = 2000 aa].'
        elif len(context['protseq'][0]) == 0:
            context['error_seq'] = 'Please provide a protein sequence to analyze.'
        else:
            context["hits_d"] = motifScan(context["protseq"][0],
                                          proteinlayout=context['proteinlayout'][0],
                                          domain=context['domain'][0],
                                          domaingroup=context['domaingroup'][0],
                                          domainsubgroup=context['domainsubgroup'][0].replace("-", ""),
                                          evalcutoff=float('1e-' + context['evalcutoff'][0] if 'evalcutoff' in context else '1e-10'),
                                          menu=get_menu(request))
    else:
        context['error_seq'] = ''

    if not context['hits_d']:
        if not 'domain' in context:
            context['domain'] = ['%EmptyMotifname%']
        hmmToScan = context['domainsubgroup'][0] if context['domainsubgroup'][0] else context['domaingroup'][0] if context['domaingroup'][0] else context['domain'][0]
        context['error_hits'] = "HMMER could not find any match for motif %s in the query sequence." % (hmmToScan)
    elif 'error' in context['hits_d']:
        context['error_hits'] = context['hits_d']['error']
        context['hits_d'] = {}

    if context['domain'][0] == "SNARE":
        context["predictedSNARE"] = predictFromSeqPyHmmer(context['protseq'][0])

    if request.method == "POST":
        context['error_seq'] = ''
        try:
            if len(context['protseq'][0]) > 2000:
                context['error_seq'] = 'Sequence is too long [max length = 2000 aa].'
            elif len(context['protseq'][0]) == 0:
                context['error_seq'] = 'Please provide a protein sequence to analyze.'
        except (IndexError, TypeError):
            context['error_seq'] = 'Please provide a protein sequence to analyze.'

    return render(request, 'home/query-motifs-results.html', context)
