# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
import time, datetime
import subprocess
import mimetypes
import pyhmmer
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import pandas as pd
from random import randrange
from dna_features_viewer import GraphicFeature, GraphicRecord
from time import gmtime, strftime
from collections import OrderedDict
from operator import getitem
from Bio.Blast.Applications import NcbiblastpCommandline

from django import template
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.views import generic
from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib import messages
from django.utils.timezone import now

from .forms import *
from .models import *
from utils.ncbi_taxonomy import TaxonomyUpdater
from utils.ncbi_taxonomy import TreeUpdater

from django import template

register = template.Library()


### FUNCTIONS ###
def get_childs(model, parent, parent_id, child_parent_id, childs=[], search_type='iexact'):
    variable_column = child_parent_id
    filter = variable_column + '__' + search_type
    cs = model.objects.none()
    for p in parent:
        if getattr(p, parent_id) == 4 and isinstance(p, Domaingroups):
            cs = cs.union(model.objects.filter( **{ variable_column+"__icontains" : ";4" }))
        else:
            cs = cs.union(model.objects.filter( **{ filter: getattr(p, parent_id) }))
    for c in cs:
        childs.append(c)
        if model.objects.filter( **{ filter: getattr(c, parent_id) }):
            get_childs(model, model.objects.filter(pk=c.pk), parent_id, child_parent_id, childs=childs)
    return(childs)


def get_childs_raw(model, modelname, parent, query_id, parent_id, child_parent_id):
    variable_column = child_parent_id
    filter = variable_column + '__iexact'

    if len(model.objects.filter( **{ filter: getattr(parent, parent_id) } ) ) == 0:
        childs = [model.objects.get( **{ parent_id: getattr(parent, parent_id) })]
    else:
        childs = []
        query= "select  *\
                from    (select * from model\
                         order by parent_id, child_id) model,\
                        (select @pv := 'parent_query_id') initialisation\
                where   any_in_set(parent_id, @pv) > 0\
                and     @pv := concat(@pv, ',', child_id)\
                order by parent_id;".replace("model", modelname).replace("parent_id", child_parent_id).replace("child_id", parent_id).replace("parent_query_id", str(getattr(parent, query_id)))
        for entity in model.objects.raw(query):
            childs.append(entity)

    return childs


# def get_parents(model, instance, instance_id, instance_parent_id, parents=[]):
#     if getattr(instance, instance_id) != getattr(instance, instance_parent_id): # if instance is not root...
#         parent = model.objects.get( **{ instance_id: getattr(instance, instance_parent_id) } )
#         parents.append( [getattr(instance, 'taxonomyrank'), getattr(instance, 'scientificname'), getattr(instance, instance_id)] )
#         get_parents(model, parent, instance_id, instance_parent_id, parents=parents)
#     else:
#         parents.append( [getattr(instance, 'taxonomyrank'), getattr(instance, 'scientificname'), getattr(instance, instance_id)] )
#         return parents
#     return parents


def get_sequences(query, verify=False):

    # Filter by Domaingroup
    # Gets all domaingroups (and their children) matching query 'domaingroup(s)'
    if 'domaingroup' in query and notEmpty(query, 'domaingroup'):
        domaingroup_list = [x.replace("-","") for x in query['domaingroup']]
        domaingroups_parents = Domaingroups.objects.filter(domaingroupname__in = domaingroup_list)
        domaingroups_children  = get_childs(Domaingroups, domaingroups_parents, "domaingroup_id", "domaingroupparent_id", childs=[])
        children_ids = [x.domaingroup_id for x in domaingroups_children] + [x.domaingroup_id for x in domaingroups_parents]
        domaingroups = Domaingroups.objects.filter(domaingroup_id__in = children_ids)
    elif 'domaingroup_rank' in query and notEmpty(query, 'domaingroup_rank'):
        domaingrouprank = Domaingroups.objects.filter(domaingroupname = query['domaingroup_rank'][0].replace("-",""))
        domaingrouprank_children = get_childs(Domaingroups, domaingrouprank, "domaingroup_id", "domaingroupparent_id", childs=[])
        # domaingrouprank_childs = get_childs_raw(Domaingroups, "domaingroups", domaingrouprank, "domaingroup_id", "domaingroup_id", "domaingroupparent_id")
        children_ids = [x.domaingroup_id for x in domaingrouprank_children] + [x.domaingroup_id for x in domaingrouprank]
        domaingroups = Domaingroups.objects.filter(domaingroup_id__in = children_ids)
    elif 'domainname' in query and notEmpty(query, 'domainname'):
        domainname = query['domainname'][0]
        domain = Domains.objects.get(domainname = domainname)
        domaingroups = Domaingroups.objects.filter(domain_id = domain.domain_id)
    else:
        if verify:
            context = {'error': "At least 'Domain name', 'Domain group' or 'Subgroup' fields are required"}
            return context
        else:
            domaingroups = Domaingroups.objects.all()

    # Filter sequences using domaingroups obtained in previous step
    motifs = Motifs.objects.filter(domaingroup_id__in = domaingroups.values('domaingroup_id'))
    seqs = Sequences.objects.filter(sequence_id__in = motifs.values('sequence_id'))

    if verify and query['onlyverified'][0] == 'false':
        # Adds sequences with Verifymotifs matching query 'domaingroups'
        verifymotifs = Verifymotifs.objects.filter(domaingroup_id__in = domaingroups.values('domaingroup_id'))
        verifyseqs = Sequences.objects.filter(sequence_id__in = verifymotifs.values('sequence_id'))
        seqs = seqs | verifyseqs # OR operator for querysets

    if 'sequencestatus' in query and notEmpty(query, 'sequencestatus'):
        status = ['live' if query['sequencestatus'][0] == '1' else query['sequencestatus'][0]][0]
        seqs = seqs.filter(sequencestatus = status)

    if 'private' in query and notEmpty(query, 'private'):
        seqs = seqs.filter(private = query['private'][0])

    # Filter seqs if shortname/foreignAnnotation or taxonomy is provided
    if 'shortname' in query and notEmpty(query, 'shortname'):
        seqs = seqs.filter(sequenceshortname__icontains = query['shortname'][0])

    if 'foreignannotation' in query and notEmpty(query, 'foreignannotation'):
        pattern = re.compile("^gi\|([0-9]+)$")
        if not pattern.match(query['foreignannotation'][0]):
            context = {'error': 'Foreign Annotation format is not correct. Plase use NCBI format.'}
            return context
        seqs = seqs.filter(foreignannotation = query['foreignannotation'][0])

    if ('taxonomy_rank' in query and notEmpty(query, 'taxonomy_rank')) or ('taxonomy' in query and not notEmpty(query, 'taxonomy_rank')):
        if ('taxonomy' in query and notEmpty(query, 'taxonomy')):
            taxonomy = Taxonomies.objects.filter(scientificname__in = query['taxonomy'])
            taxonomy_childs = []
            taxonomy_childs_ = []
            for taxa in taxonomy:
                taxonomy_ = Taxonomies.objects.filter(taxonomy_id = taxa.taxonomy_id)
                taxonomy_childs_ = get_childs(Taxonomies, taxonomy_, "taxonomy_id", "taxonomyparent_id", childs=[])
                # taxonomy_childs_ = get_childs_raw(Taxonomies, "taxonomies", taxonomy_, "taxonomy_id", "taxonomy_id", "taxonomyparent_id")
                taxonomy_childs += taxonomy_childs_
            taxonomy_childs_ids = [x.taxonomy_id for x in taxonomy_childs] + [x.taxonomy_id for x in taxonomy]
            seqs = seqs.filter(taxonomy_id__in = taxonomy_childs_ids)
        else:
            if verify:
                pass
            else:
                context = {'error': 'At least one %s must be selected.' % (query['taxonomy_rank'][0])}
                return context

    return seqs

def notEmpty(query, element):
    try:
        if query[element] in [[''], '', None]:
            return False
        else:
            return True
    except:
        return False
#################

# Home
def index(request):
    context = {'segment': 'index'}

    html_template = loader.get_template('home/home.html')
    #html_template = loader.get_template('home/index.html')

    return HttpResponse(html_template.render(context, request))


# Pages deprecated - template examples
def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:

        load_template = request.path.split('/')[-1]
        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template

        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))


# Query Home
def QueryView(request):
    segment = request.path.split('/')[-1]
    context = {"segment": segment}

    return render(request, 'home/query.html', context)


# Query form
def load_taxonomy_rank(request):
    rank = request.GET.get('taxonomy_rank')
    taxonomy_list = sorted(list(set( [ x.scientificname for x in Taxonomies.objects.filter(taxonomyrank=rank)] )))
    return render(request, 'home/query-sequences-family-taxonomyRank.html', {'taxonomy_list': taxonomy_list})


def load_domaingroups_rank1(request):
    domainname = request.GET.get('domainname')
    domaingroup_rank = request.GET.get('domaingroup_rank')
    if domainname == '':
        domainGroupNames = sorted([ x.domaingroupname for x in Domaingroups.objects.filter(analysislevel = 2) ])
    else:
        domain = Domains.objects.filter(domainname = domainname)
        domainGroupNames = [ x.domaingroupname for x in Domaingroups.objects.filter(domain_id__in = domain.values('domain_id')) if x.analysislevel == 2 ]
    return render(request, 'home/query-sequences-family-domaingroupsRank1.html', {'domaingroups_rank_list': domainGroupNames, 'domaingroup_rank': domaingroup_rank})


def load_sequenceshortnames(request):
    domainname = request.GET.get('domainname')
    domainID = Domains.objects.get(domainname = domainname).domain_id
    domaingroups = Domaingroups.objects.filter(domain_id = domainID)
    motifs = Motifs.objects.filter(domaingroup_id__in = domaingroups.values('domaingroup_id'))
    shortnames = sorted(list( set([ x.sequenceshortname.split("_")[0] for x in Sequences.objects.filter(sequence_id__in = motifs.values('sequence_id')) if x.sequenceshortname.split("_")[0] != "" ]) ))
    return render(request, 'home/query-sequences-family-sequenceshortnames.html', {'shortnames': shortnames})


def load_domaingroups_rank2(request):

    def get_names_list(parent_id):
        # for domaingroup in Domaingroups.objects.filter(domaingroupparent_id=parent_id):
        for domaingroup in Domaingroups.objects.all():
            domaingroupparent_id = domaingroup.domaingroupparent_id
            if domaingroupparent_id == None: continue

            if ";" in domaingroupparent_id:
                domaingroupparent_id = [ int(x) for x in domaingroupparent_id.split(";") ]
            else:
                domaingroupparent_id = [ int(domaingroupparent_id) ]

            if int(parent_id) in domaingroupparent_id:
                name_list = "-" * (int(domaingroup.analysislevel)-2) + domaingroup.domaingroupname
                if domaingroup.analysislevel > 2:
                    childs_list.append(name_list)
                if Domaingroups.objects.filter(domaingroupparent_id=domaingroup.domaingroup_id):
                    get_names_list(domaingroup.domaingroup_id)

        return childs_list

    childs_list = []
    domainname = request.GET.get('domainname')
    rank = request.GET.get('domaingroup_rank')
    if not rank and not domainname:
        childs_list = []#[ "-" * (int(x.analysislevel)-2) + x.domaingroupname for x in Domaingroups.objects.filter(analysislevel__gt = 2) ]
    else:
        if rank:
            parent_id = Domaingroups.objects.filter(domaingroupname=rank)[0].domaingroup_id
            childs_list = get_names_list(parent_id)
        else:
            domain = Domains.objects.filter(domainname = domainname)
            childs_list = [ "-" * (int(x.analysislevel)-2) + x.domaingroupname for x in Domaingroups.objects.filter(domain_id__in = domain.values('domain_id')) if x.analysislevel > 2 ]

    return render(request, 'home/query-sequences-family-domaingroupsRank2.html', {'domaingroups_rank_list': childs_list})


def load_queryverifysequences(request):
    sequences = get_sequences(dict(request.POST), verify = True)
    if 'error' in sequences:
        context = {'sequences': '',
                   'error': sequences['error']}
    else:
        context = {'sequences': sequences}

    if len(context['sequences']) > 0:
        speciesname = {}
        motifs = {}

        for seq in context['sequences']:
            speciesname[seq.sequence_id] = [x.scientificname for x in Taxonomies.objects.filter(taxonomy_id = seq.taxonomy_id)][0]
            motifs[seq.sequence_id] = ", ".join( set([x.motifname for x in Motifs.objects.filter(sequence_id=seq.sequence_id)]) )

        context['speciesname'] = speciesname
        context['motifs'] = motifs

    context['log'] = len(context['sequences'])
    return render(request, 'home/query-verify-update-sequences.html', context)


def QuerySequences(request):
    segment = request.path.split('/')[-1]
    form = FamilyForm

    ## GET QUERIES ##
    domains = Domains.objects.all()
    domainsList = sorted(list( set([ x.domainname for x in domains ]) ))

    SNAREdomainID = Domains.objects.get(domainname = "SNARE").domain_id
    SNAREdomaingroups = Domaingroups.objects.filter(domain_id = SNAREdomainID)
    SNAREdomaingroupnames = [x.domaingroupname for x in SNAREdomaingroups if x.analysislevel == 2 ]

    SNAREmotifs = Motifs.objects.filter(domaingroup_id__in = SNAREdomaingroups.values('domaingroup_id'))
    shortnames = sorted(list( set([ x.sequenceshortname.split("_")[0] for x in Sequences.objects.filter(sequence_id__in = SNAREmotifs.values('sequence_id')) if x.sequenceshortname.split("_")[0] != "" ]) ))

    taxonomy_ranks = ['superkingdom', 'kingdom', 'superphylum', 'phylum', 'subphylum', 'superclass', 'class', 'subclass', 'superorder', 'order', 'suborder', 'infraorder', 'superfamily', 'family', 'genus', 'subgenus', 'species subgroup', 'species', 'subspecies', 'strain']

    ## CONTEXT ##
    context = {'segment': segment,
               'domainsList': domainsList,
               'domainGroupNames': SNAREdomaingroupnames,
               'shortnames': shortnames,
               'taxonomy_ranks': taxonomy_ranks,
               'domaingroup_rank': SNAREdomaingroupnames,
               'form': form,
               'error': [request.session['error'] if 'error' in request.session else ''][0]}

    if request.method == "GET":
        form = FamilyForm(request.GET)
        if form.is_valid():

            # If error on query request or query is empty
            if context['error']:
                request.session['error'] = ''
                return render(request, 'home/query-sequences.html', context)
            # If no field is specified
            elif sum([ 0 if x in ["", []] else 1 for x in list(form.cleaned_data.values()) ]) == 0:
                if form.cleaned_data["domainname"] != None:
                    context['error'] = ''
                else:
                    context['error'] = 'At least one field is required to make a query'
                    return render(request, 'home/query-sequences.html', context)
            # If at least 1 field is provided
            else:
                return render(request, 'home/query-sequences-results.html', context=form.cleaned_data)

        else:
            context['form'] = form
            return render(request, 'home/query-sequences.html', context)

    return render(request, 'home/query-sequences.html', context)


# Query results
def QuerySequencesResults(request):
    segment = request.path.split("?")[0].split('/')[-1]
    context = dict(request.GET)
    sequences = get_sequences(context)

    if len(sequences) == 0 or 'error' in sequences:
        if 'error' in sequences:
            request.session['error'] = sequences['error']
            return redirect('query-sequences')
        else:
            request.session['error'] = 'This query returns 0 sequences. Please select different options.'
            return redirect('query-sequences')

    speciesname = {}
    for seq in sequences:
        speciesname[seq.sequence_id] = [x.scientificname for x in Taxonomies.objects.filter(taxonomy_id = seq.taxonomy_id)][0]

    context["sequences"] = sequences
    context["speciesname"] = speciesname
    context["segment"] = segment
    context["is_staff"] = request.user.is_staff
    hmmMoldes = []
    for d in os.listdir('utils/hmmModels/'):
        if not os.path.isdir('utils/hmmModels/%s'%(d)): continue
        for f in os.listdir('utils/hmmModels/%s'%(d)):
            hmmMoldes.append(f.split('.hmm')[0])

    context["hmmModels"] = hmmMoldes
    return render(request, 'home/query-sequences-results.html', context)


def QuerySequencesFastaFormat(request):
    if request.method == 'POST':
        boxes = request.POST.getlist('checkbox')

    try:
        sequences = Sequences.objects.filter(pk__in=boxes)
    except Sequences.DoesNotExist:
        raise Http404("Sequences does not exist")

    if 'fasta' in request.POST:
        return render(request, 'home/query-sequences-fasta.html', {'sequences': sequences})
    elif 'multialignment' in request.POST:
        if len(sequences) < 2:
            return render(request, 'home/query-sequences-multialignment.html', {'names': []})
        # Do HMMalignment with sequences
        # 1.Get hmm file
        for d in os.listdir('utils/hmmModels/'):
            if not os.path.isdir('utils/hmmModels/%s'%(d)): continue
            for f in os.listdir('utils/hmmModels/%s'%(d)):
                if request.POST['hmmModel'][0] in f:
                    with pyhmmer.plan7.HMMFile("./utils/hmmModels/%s/%s"%(d,f)) as hmm_file:
                        hmm = hmm_file.read()
        # 2.Convert sequences into iterable of digitalsequences
        alphabet = pyhmmer.easel.Alphabet.amino()
        background = pyhmmer.plan7.Background(alphabet)
        digitalsequences = [pyhmmer.easel.TextSequence(name=bytes(seq.sequenceshortname, 'utf-8'), sequence=seq.sequence).digitize(alphabet) for seq in sequences]
        # 3.MSA
        MSA = pyhmmer.hmmer.hmmalign(hmm, digitalsequences, digitize=False)
        names = [ name.decode("utf-8") for name in MSA.names ]
        zippedLists = {}
        for i in range(len(names)):
            alignment = [*MSA.alignment[i]] # splits alignment into list for each character in the alignment
            upperList = []
            for n in alignment:
                upperList.append([ 1 if n.isupper() else 0 ][0])
            zippedLists[names[i]] = zip(alignment, upperList)
        return render(request, 'home/query-sequences-multialignment.html', {'names': names, 'zippedLists': zippedLists})
    else:
        return render(request, 'home/query-sequences-fasta.html', {'sequences': sequences})


# Query details
def getMotifPlot_fromMotif(start, end, length, label):
    import io
    import urllib, base64

    buf = io.BytesIO()
    fig, ax = plt.subplots(nrows=1, figsize=(20, 1.5), sharex=True)
    features = [ GraphicFeature(start=start, end=end, label=label, color="#ffcccc"), ]

    record = GraphicRecord(sequence_length=length, features=features)
    record.plot(ax=ax)
    fig.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = urllib.parse.quote(string)
    return uri


def QuerySequencesDetails(request, sequence_id):
    segment = request.path.split('/')[-4]
    context = {"segment": segment}

    try:
        context['sequence'] = Sequences.objects.get(pk=sequence_id)
    except Sequences.DoesNotExist:
        context['log'] = 'Seqence ID %s not found in TRACEY'%(sequence_id)
        return render(request, 'home/query-sequences-details.html', context)
        # raise Http404("Sequence ID does not exist")

    context["speciesname"] = [x.scientificname for x in Taxonomies.objects.filter(taxonomy_id = context['sequence'].taxonomy_id)][0]

    motifs  = Motifs.objects.filter(sequence_id = context['sequence'].sequence_id)

    context["motifs"]  = {}
    for m in motifs:
        context["motifs"][m] = {}
        d = Domaingroups.objects.get(domaingroup_id = m.domaingroup_id)

        if d.domaingroupparent_id == None:
            context["motifs"][m]["domaingroupparent"] = m.motifname
        elif ";" in d.domaingroupparent_id:
            p_id = d.domaingroupparent_id.split(";")
            context["motifs"][m]["domaingroupparent"] = Domaingroups.objects.get(domaingroup_id = p_id[0]).domaingroupname +"/"+ Domaingroups.objects.get(domaingroup_id = p_id[1]).domaingroupname
        else:
            context["motifs"][m]["domaingroupparent"] = Domaingroups.objects.get(domaingroup_id = d.domaingroupparent_id).domaingroupname
        context["motifs"][m]["domaingroup"] = d.domaingroupname
        context["motifs"][m]["ascii"] = m.asciioutput

        data = ET.fromstring(context["motifs"][m]["ascii"])
        for x in data:
            context["motifs"][m][x.tag] = x.text
        context["motifs"][m]["eValueFloat"] = float(context["motifs"][m]["eValue"])
        context["motifs"][m]["length"] = m.stopposition - m.startposition + 1
        context["motifs"][m]["plot"] = getMotifPlot_fromMotif(m.startposition, m.stopposition, len(context['sequence'].sequence), context["motifs"][m]["domaingroupparent"])

    context["motifs"] = OrderedDict(sorted(context["motifs"].items(), key = lambda x: getitem(x[1], 'eValue')))
    return render(request, 'home/query-sequences-details.html', context)


def DetailsSequencesFastaFormat(request, sequence_id):
    try:
        sequence = Sequences.objects.get(pk=sequence_id)
    except Sequences.DoesNotExist:
        raise Http404("Sequence does not exist")

    return render(request, 'home/details-sequences-fasta.html', {'sequence': sequence})


# Motifs
def QueryMotifsView(request):
    segment = request.path.split('/')[-1]
    context = {"segment": segment,
               "motifs": sorted(list( set([ x.domainname for x in Domains.objects.all() ]) ))
              }

    if request.method == "POST":
        context['protseq'] = dict(request.POST)['protseq']
        context['motifname'] = dict(request.POST)['motifname']

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


def getMotifPlot_fromPyhammer(hit, sequence):
    import io
    import urllib, base64

    buf = io.BytesIO()
    fig, ax = plt.subplots(nrows=1, figsize=(15, 2), sharex=True)
    features = [
                GraphicFeature(start=d.alignment.target_from-1, end=d.alignment.target_to, label=str(d.alignment).split("\n")[1].split()[0]+" (%s)"%(format(d.pvalue, '.1E')))
                for d in hit.domains
            ]
    record = GraphicRecord(sequence_length=len(sequence), features=features)
    record.plot(ax=ax)
    fig.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = urllib.parse.quote(string)
    return uri


def motifScan(sequence, motifname):

    hits_d = {}

    #Check sequence format
    count_gt = sequence.count(">")
    count_nl = sequence.count("\n")
    if count_gt >= 1:
        hits_d['error'] = 'Fasta format is not valid for this search. Please remove the header of the sequence.'
        return hits_d
    elif count_nl >= 1:
        hits_d['error'] = 'Sequence format is nos valid. Please provide only one sequence and check that there is no new line character and the end of the sequence.'
        return hits_d

    alphabet = pyhmmer.easel.Alphabet.amino()
    background = pyhmmer.plan7.Background(alphabet)
    seq1 = pyhmmer.easel.TextSequence(name=b"Query sequence", sequence=sequence).digitize(alphabet)

    M = motifname[0].upper()
    if M == "ALL":
        hmms = pyhmmer.plan7.HMMFile("./utils/hmmModels/MOTIFS.hmmDb")
    else:
        hmms = []
        for f in os.listdir('utils/hmmModels/%s'%(M)):
            with pyhmmer.plan7.HMMFile('utils/hmmModels/%s/%s'%(M, f)) as hmm_file:
                hmm = hmm_file.read()
                hmms.append(hmm)

    pipeline = pyhmmer.plan7.Pipeline(pyhmmer.easel.Alphabet.amino())
    hits = pipeline.scan_seq(seq1, hmms)

    for h in hits:
        h_name = h.name.decode('UTF-8')
        hits_d[h_name] = {}
        hits_d[h_name]['plot'] = plot = getMotifPlot_fromPyhammer(h, sequence)
        hits_d[h_name]['domains'] = []
        for d in h.domains:
            motifname = str(d.alignment).split("\n")[1].split()[0]
            dgs = Domaingroups.objects.filter(domaingroupname = motifname)
            for dg in dgs:
                domain = Domains.objects.get(domain_id = dg.domain_id).domainname
                if dg.domaingroupparent_id == None:
                    dg_parent = motifname
                elif ";" in dg.domaingroupparent_id:
                    dg_parent = "/".join([ x.domaingroupname for x in Domaingroups.objects.filter(domaingroup_id__in = dg.domaingroupparent_id.split(";")) ])
                else:
                    dg_parent = Domaingroups.objects.get(domaingroup_id = dg.domaingroupparent_id).domaingroupname
                x = {'evalue': format(d.pvalue, '.1E'),
                     'pvalue': d.pvalue,
                     'env_from': d.env_from,
                     'env_to': d.env_to,
                     'length': d.env_to - d.env_from,
                     'alignment': d.alignment,
                     'dg': dg.domaingroupname,
                     'dg_parent': dg_parent,
                     'domain': domain,
                    }
                hits_d[h_name]['domains'].append(x)

        hits_d[h_name]["domains"] = sorted(hits_d[h_name]["domains"], key=lambda d: d['pvalue'])

    return hits_d


def QueryMotifsResultsView(request):

    if 'context' in request.session:
        context = request.session['context']
        # context['motifname'] = dict(request.POST)['motifname']
        del request.session['context']
    elif request.method == "POST":
    # if request.method == "POST":
        context = dict(request.POST)
    else:
        context = dict(request.GET)

    segment = request.path.split('/')[-1]
    context["segment"] = segment
    context["motifs"] = sorted(list(set([ x.motifname for x in Motifs.objects.all() ])))
    context["hits_d"] = {}

    if notEmpty(context, 'protseq'):
        if len(context['protseq'][0]) > 2000:
            context['error_seq'] = 'Sequence is too long [max length = 2000 aa].'
        elif len(context['protseq'][0]) == 0:
            context['error_seq'] = 'Please provide a protein sequence to analyze.'
        else:
            context["hits_d"] = motifScan(context["protseq"][0], context['motifname'])
    else:
        context['error_seq'] = ''

    if not context['hits_d']:
        if not 'motifname' in context:
            context['motifname'] = ['%EmptyMotifname%']
        context['error_hits'] = "HMMER couldn't find any match for motif %s in the query sequence."%(context['motifname'][0])
    elif 'error' in context['hits_d']:
        context['error_hits'] = context['hits_d']['error']
        context['hits_d'] = {}
        # return HttpResponseRedirect(reverse('query-motifs-results'), context)

    if request.method == "POST":
        context['error_seq'] = ''
        # context['protseq'] = [request.POST['protseq']]
        # context['motifname'] = [request.POST['motifname']]
        # context['csrfmiddlewaretoken'] = request.POST['csrfmiddlewaretoken']
        # request.session['context'] = context
        try:
            if len(context['protseq'][0]) > 2000:
                context['error_seq'] = 'Sequence is too long [max length = 2000 aa].'
            elif len(context['protseq'][0]) == 0:
                context['error_seq'] = 'Please provide a protein sequence to analyze.'
        except:
            context['error_seq'] = 'Please provide a protein sequence to analyze.'



    return render(request, 'home/query-motifs-results.html', context)


# Insert
def is_staff(self):
    if str(self.user_type) == 'Staff':
        return True
    else:
        return False

rec_login_required = user_passes_test(lambda u: True if u.is_staff else False, login_url="/noPermits.html")
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
                    gaps.append("%s:%s"%(gapInitialPosition, count))
                count = 0
                gapInitialPosition = 0
        if count > 0:
            gaps.append("%s:%s"%(gapInitialPosition, count))
        return ", ".join(gaps)

    for motif in hits:
        motifInfo = hits[motif]
        for d in motifInfo['domains']:
            vm = Verifymotifs(sequence_id = sequence_id,
                             motifname = motif,
                             startposition = d['env_from']+1,
                             stopposition = d['env_to']-1,
                             verifymotifcomments = '',
                             domaingroup_id = Domaingroups.objects.get(domaingroupname = d['dg']).domaingroup_id,
                             gaps = countGaps(d['alignment'].target_sequence),
                             active = 0,
                             method = Methods.objects.get(domaingroup_id = Domaingroups.objects.get(domaingroupname = d['dg']).domaingroup_id), #Review this field
                             verifymotifrank = 1000000,
                             asciioutput = '<asciiOutput>\r\t<consensus>%s</consensus>\r\t<similarity>%s\t</similarity>\r\t<motif>%s</motif>\r\t<eValue>%s</eValue>\r\t<bitscore>321</bitscore>\r</asciiOutput>'%(d['alignment'].hmm_sequence, d['alignment'].identity_sequence, d['alignment'].target_sequence, d['evalue']),
                             binaryoutput = '')
            vm.save()


def common_name(list, sn):
    arr = {}
    for name in list:
        l = len(name)
        for i in range(l):
            for j in range(l+1):
                if j <= i: continue
                subname = name[i:j].replace("_", "")
                if len(subname) < 3 or subname == "ref": continue
                if not subname in arr:
                    arr[subname] = 1
                else:
                    arr[subname] += 1

    sorted_arr = sorted(arr.items(), key=lambda x:-x[1])
    top = [ x[0] for x in sorted_arr if x[1]/len(list)>=0.5 ]
    common_names = []
    for i in range(len(top)):
        unique = True
        for j in range(len(top)):
            if i == j: continue
            if top[i] in top[j]: unique = False
        if unique and top[i] not in common_names: common_names.append(sn+"_"+top[i])
    return common_names


def suggested_names(shortname, sequence):
    blastp_path = 'utils/ncbi-blast-2.13.0+/bin/blastp'
    file_path = 'utils/ncbi-blast-2.13.0+/query_vm.fasta'
    sn = shortname.split("_")[0]
    with open(file_path, 'w') as fasta_file:
        fasta_file.write( '>'+shortname+'\n'+sequence )
    blastp_cline = NcbiblastpCommandline(cmd = blastp_path, query = file_path, db = "utils/ncbi-blast-2.13.0+/traceyBLASTdb/traceyp", outfmt = 6)
    stdout, stderr = blastp_cline()
    shortnames = [ y[1].split("|")[0][y[1].find('_')+1:] for y in [ x.split("\t") for x in stdout.split("\n") if len(x) > 1 ] if float(y[2]) > 95]
    suggestedNames = common_name(shortnames, sn)
    return suggestedNames


def TreesView(request):
    segment = request.path.split('/')[-1]
    taxonomies = ['superkingdom', 'kingdom', 'superphylum', 'phylum', 'subphylum', 'superclass', 'class', 'subclass', 'superorder', 'order', 'suborder', 'infraorder', 'superfamily', 'family', 'genus', 'subgenus']
    context = {'segment': segment,
               'taxonomies': taxonomies}

    return render(request, 'home/trees.html', context)


def plotTrees(request):
    # Clean old tree files/plots
    filePath = 'apps/static/assets/img/tmpTrees/'
    fileslist = os.listdir(filePath)
    current_time = time.time()
    minutes = 5
    for fileName in fileslist:
        file_time = os.stat(filePath+fileName).st_mtime
        if(current_time - file_time > minutes*60):
            os.remove(filePath+fileName)

    # Start new plot
    data = dict(request.GET)
    colname = data['taxonomy_rank'][0]
    values = data['taxonomy_rank_2']
    df = pd.read_csv('utils/phylogeneticTrees/taxonomies.csv', index_col=0)

    # Get TRACEY Taxonomy_ids to be ploted and transform to NCBI ids
    if values:
        taxonomy_ids = df[df[colname].isin(values)].index.values
    else:
        taxonomy_ids = df[df[colname] != "-"].index.values

    active_ids = [ str(x.ncbi_taxonomy_id) for x in Taxonomies.objects.filter(taxonomy_id__in=taxonomy_ids) ]
    clean_ids = 1
    while clean_ids:
        bashCommand = ['/home/cpulidoq/.cargo/bin/fastax', 'tree', '-n', '-f', '"(%taxid)"'] + active_ids
        runout = subprocess.run(bashCommand, capture_output=True)
        if runout.stderr==b'':
            tree = str(runout.stdout.decode("utf-8")).strip().replace('"', "")
            clean_ids = 0
        else:
            wrong_id = re.search(r"(\b\d+)", str(runout.stderr)).group(1)
            active_ids.remove(wrong_id)

    # Find all NCBI_IDs in the newick tree
    matches = re.finditer('\d+', tree)
    ranges = [ [match.start(), match.end()] for match in matches]
    ranges.sort(key=lambda k: (k[0], -k[1]), reverse=True)

    # Replace found NCBI_IDs with its scientific_name
    c=0
    for r in ranges:
        c += 1
        start = r[0]
        end = r[1]
        tax_id = tree[start:end]
        try:
            t = Taxonomies.objects.get(ncbi_taxonomy_id=tax_id)
            tax_name = t.scientificname + "|" + df.loc[t.taxonomy_id][colname]
        except:
            tax_name = 'unknown'
        tree = tree[:start] + tax_name + tree[end:]

    # Get username
    try:
        user = AuthUser.objects.get(pk=request.session['_auth_user_id']).username
    except:
        user = 'guest'+str(randrange(100))

    # Delete files
    # list_of_files = os.listdir('')

    # Save newick tree (this file will be deleted within R script)
    treeFileName = '%s.newick'%(user)
    with open('apps/static/assets/img/tmpTrees/'+treeFileName, 'w') as fo:
        fo.write(str(tree))

    # Plotting Tree with R script
    bashCommand = ['Rscript', 'utils/phylogeneticTrees/plotTree.R', treeFileName, colname] + values
    subprocess.run(bashCommand)

    return render(request, 'home/treeplot.html', {'treeplot': treeFileName+'.png'})


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
            form.cleaned_data['changelog'] = strftime("%d.%m.%Y|%H:%M:%S|", gmtime())+user.username+' - insertSequence;'
            try:
                new_form = form.save(commit=False)
                new_form.changelog = form.cleaned_data['changelog']
                new_form.save()
                hits = motifScan(form.cleaned_data['sequence'], ["ALL"])
                saveVerifyMotifs(new_form.pk, hits)
                return HttpResponseRedirect(reverse('query-verify', args=(new_form.pk,)))
            except:
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


#Verify
@login_required(login_url="/noPermits.html")
@staff_login_required
def QueryVerifyMenuView(request):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    taxonomy_ranks = ['superkingdom', 'kingdom', 'superphylum', 'phylum', 'subphylum', 'superclass', 'class', 'subclass', 'superorder', 'order', 'suborder', 'infraorder', 'superfamily', 'family', 'genus', 'subgenus', 'species subgroup', 'species', 'subspecies', 'strain']

    context = {'segment': request.path.split('/')[-1],
               'sequences': Sequences.objects.none(),
               'speciesname': {},
               'MotifForm': MotifForm(initial={'status': 'live'}),
               'taxonomy_ranks': taxonomy_ranks
               }

    context['log'] = len(context['sequences'])
    return render(request, 'home/query-verify-menu.html', context)


@login_required(login_url="/noPermits.html")
def QueryVerifyBlastView(request, db, query_id):
    if db[-1] == 'm':
        query = Verifymotifs.objects.get(pk=int(query_id))
        query_sequence = query.sequence.sequence[query.startposition-1:query.stopposition]
        shortname = "_".join([ query.sequence.sequenceshortname, query.motifname ])
    elif db[-1] == 's':
        query = Sequences.objects.get(pk=int(query_id))
        query_sequence = query.sequence
        shortname = query.sequenceshortname
    context = {'db': db[:-1],
               'query_id': query_id,
               'name': shortname,
               'motif_length': len(query_sequence),
               'blast_error': '',
               'blast_result': '',
               'header': ['query acc.ver', 'subject acc.ver', '% identity', 'alignment length', 'mismatches', 'gap opens', 'q. start', 'q. end', 's. start', 's. end', 'evalue', 'bit score']}
    context['fasta_sequence'] = '>'+context['name']+"\n%s"%(query_sequence)

    file_path = 'utils/ncbi-blast-2.13.0+/query_vm.fasta'
    if context['db'] == 'TRACEY':

        blastp_path = 'utils/ncbi-blast-2.13.0+/bin/blastp'
        with open(file_path, 'w') as fasta_file:
            fasta_file.write( context['fasta_sequence'] )

        blastp_cline = NcbiblastpCommandline(cmd = blastp_path, query = file_path, db = "utils/ncbi-blast-2.13.0+/traceyBLASTdb/traceyp", outfmt = 6)
        stdout, stderr = blastp_cline()

        if stderr:
            context['blast_error'] = stderr
        else:
            context['blast_result'] = [x.split("\t") for x in [line for line in stdout.split("\n") ]]

    elif context['db'] == 'NCBI':

        ncbi_url = 'https://blast.ncbi.nlm.nih.gov/Blast.cgi?PROGRAM=blastp&PAGE_TYPE=BlastSearch&LINK_LOC=blasthome&QUERY=%s'%(context['fasta_sequence'])
        return HttpResponseRedirect(ncbi_url)
        # return redirect('http://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=put&DATABASE=nr&PROGRAM=blastp&QUERY=GTDHTERRGRIYIQAHIDRDVLIVLVRDAKNLVPMDPNGLSDPYVKLKLIPDPKSESKQKTKTIKCSLNPEWNETFRFQLKESDKDRRLSVEIWDWDLTSRNDFMGSLSFGISELQKASVDGWFKLLSQEEGEYFNVPVP')
        # from Bio.Blast.NCBIWWW import qblast
                # Protein databases
                # - env_nr
                # - nr
                # - pataa
                # - pdbaa
                # - refseq_protein
                # - swissprot
        # context['result'] = qblast('blastp', 'nr', file_path, url_base='https://blast.ncbi.nlm.nih.gov/Blast.cgi', format_type='Tabular')  #https://ncbi.github.io/blast-cloud/dev/api.html

    else:
        context['blast_error'] = 'An error ocurred while choosing database..'

    return render(request, 'home/query-verify-blast.html', context)


@login_required(login_url="/noPermits.html")
@staff_login_required
def QueryVerifyView(request, sequence_id):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    segment = request.path.split('/')[-2]
    context = {'segment': segment}

    try:
        seq = Sequences.objects.get(pk=sequence_id)
        context["sequence"] = seq
    except:
        seq = Sequences()
        form = InsertSequence(instance=seq, )
        context['log'] = 'Seqence ID %s not found in TRACEY'%(sequence_id)
        context['form'] = form
        return render(request, 'home/query-verify.html', context)

    if 'deleteSequence' in request.POST:
        # TODO: Rise a warning before accepting deletion
        seq.delete()
        return render(request, 'home/query-verify-menu.html')

    if seq.gene.ncbigene_id == '-1':
        ncbigene_id = 'not_specified:-1:%s'%(seq.gene.gene_id)
    else:
        ncbigene_id = seq.gene.ncbigene_id

    # Retrive verifyMotifs
    motifs = Motifs.objects.filter(sequence_id = sequence_id)
    verifymotifs = Verifymotifs.objects.filter(sequence_id = sequence_id)
    context["motifs"]  = {}
    context["verifymotifs"]  = {}

    suggestedNames = suggested_names(seq.sequenceshortname, seq.sequence)
    context['suggestedNames'] = ",    ".join(suggestedNames)

    for type, motifs in zip(['motifs', 'verifymotifs'], [motifs, verifymotifs]):
        for m in motifs:
            context[type][m] = {}
            if type == "motifs":
                context[type][m]['motif_id'] = m.motif_id
            else:
                context[type][m]['verifymotif_id'] = m.verifymotif_id
            d = Domaingroups.objects.get(domaingroup_id = m.domaingroup_id)

            if d.domaingroupparent_id == None:
                context[type][m]["domaingroupparent"] = m.motifname
            elif ";" in d.domaingroupparent_id:
                p_id = d.domaingroupparent_id.split(";")
                context[type][m]["domaingroupparent"] = Domaingroups.objects.get(domaingroup_id = p_id[0]).domaingroupname +"/"+ Domaingroups.objects.get(domaingroup_id = p_id[1]).domaingroupname
            else:
                context[type][m]["domaingroupparent"] = Domaingroups.objects.get(domaingroup_id = d.domaingroupparent_id).domaingroupname
            context[type][m]["domaingroup"] = d.domaingroupname
            context[type][m]["ascii"] = m.asciioutput
            context[type][m]["length"] = m.stopposition - m.startposition + 1

            data = ET.fromstring(context[type][m]["ascii"])
            for x in data:
                context[type][m][x.tag] = x.text
            context[type][m]["eValueFloat"] = float(context[type][m]["eValue"])
            context[type][m]["plot"] = getMotifPlot_fromMotif(m.startposition, m.stopposition, len(seq.sequence), context[type][m]["domaingroupparent"])

    if request.method == 'POST':
        form = InsertSequence(request.POST, instance=seq, initial={'gene': ncbigene_id, })

        # remember old state
        _mutable = form.data._mutable
        # set to mutable
        form.data._mutable = True
        # сhange the values you want
        if form.data['newChangelog']:
            form.data['newChangelog'] = " %s %s - %s;"%(strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, form.data['newChangelog'])

        #Verify motifs if not verified yet
        for vm_id in request.POST.getlist('verifymotif_id'):

            requestValue, vm_id = vm_id.split(":")
            vm = Verifymotifs.objects.get(verifymotif_id=vm_id)

            if requestValue == 'delete':
                # Delete VerifyMotif
                vm.delete()
                form.data['newChangelog'] += " %s %s - VerifyMotif deleted: '%s';"%(strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, vm.motifname)
                continue

            # Create motif from vm
            m = Motifs(sequence = seq,
                       motifname = vm.motifname,
                       startposition = vm.startposition,
                       stopposition = vm.stopposition,
                       motifcomments = vm.verifymotifcomments,
                       domaingroup = vm.domaingroup,
                       # motif_id = models.AutoField(primary_key=True),
                       gaps = vm.gaps,
                       active = 1,
                       method = vm.method,
                       motifrank = vm.verifymotifrank,
                       asciioutput = vm.asciioutput,
                       binaryoutput = vm.binaryoutput)

            if int(requestValue) == int(vm.active):

                continue

            elif requestValue == "0" or requestValue == "-1":

                # Delete Motif if already exists
                if vm.active == 1:
                    for activeMotif in Motifs.objects.filter( sequence_id = vm.sequence_id ):
                        if activeMotif.sequence_id == vm.sequence_id and activeMotif.asciioutput == vm.asciioutput:
                            activeMotif.delete()

                vm.active = int(requestValue)
                vm.save()
                form.data['newChangelog'] += " %s %s - VerifyMotif deactivated: '%s';"%(strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, vm.motifname)

            elif requestValue == '1':

                # Save active Motif if does not exist
                activeMotifs = Motifs.objects.filter( sequence_id = vm.sequence_id )
                if vm in activeMotifs:
                    continue
                else:
                    m.save()
                    form.data['newChangelog'] += " %s %s - Verified motif: '%s';"%(strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, m.motifname)
                vm.active = 1
                vm.save()

        for m_id in request.POST.getlist('motif_id'):
            requestValue, m_id = m_id.split(":")
            motif = Motifs.objects.get(motif_id=m_id)

            if requestValue == 'delete':
                # Delete VerifyMotif
                linked_vm = ''
                for vm in Verifymotifs.objects.filter( sequence_id = motif.sequence_id ):
                    if motif.sequence_id == vm.sequence_id and motif.asciioutput == vm.asciioutput:
                        linked_vm = vm
                # If linked_vm set 'active' to 0 else create new linked_vm
                if linked_vm:
                    linked_vm.active = 0
                else:
                    linked_vm = Verifymotifs( sequence  = motif.sequence,
                                              motifname = motif.motifname,
                                              startposition = motif.startposition,
                                              stopposition = motif.stopposition,
                                              verifymotifcomments = motif.motifcomments,
                                              domaingroup = motif.domaingroup,
                                              gaps = motif.gaps,
                                              active = 0,
                                              method = motif.method,
                                              verifymotifrank = motif.motifrank,
                                              asciioutput = motif.asciioutput,
                                              binaryoutput = motif.binaryoutput
                                              )
                linked_vm.save()
                motif.delete()
                form.data['newChangelog'] += " %s %s - Motif deleted: '%s';"%(strftime("%d.%m.%Y|%H:%M:%S|", gmtime()), user.username, vm.motifname)
                continue
            elif int(requestValue) == int(motif.active):
                continue
            else:
                motif.active = int(requestValue)
                motif.save()

        # set mutable flag back
        form.data._mutable = _mutable

        if form.is_valid():
            context['form'] = form
            try:
                form.save()
                context['message'] = 'Sequence updated successfully'
                return HttpResponseRedirect(reverse('query-verify', args=(seq.pk,)))
            except:
                context['message'] = 'Sequence could not be updated'
        else:
            context['form'] = form
    else:
        context['form'] = InsertSequence(instance=seq, initial={'gene': ncbigene_id, })

    return render(request, 'home/query-verify.html', context)


# TRACEY Features
@login_required(login_url="/noPermits.html")
@staff_login_required
def features(request):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    if request.user.is_authenticated:
        user.last_login = now()
        user.save()

    taxonomy_file = 'utils/ncbi_taxonomy/taxdmp/TaxonomyUpdate.report.txt'
    tree_file = 'utils/ncbi_taxonomy/TRACEY_phylogeneticTree.newick'
    if os.path.isfile(taxonomy_file):
        last_taxonomy_update = open(taxonomy_file, 'r').readlines()[0].split("(Date: ")[1].split(" ")[0][:-1]
        last_taxonomy_update = ['Today' if last_taxonomy_update == str(datetime.datetime.now().date()) else last_taxonomy_update][0]
    else:
        last_taxonomy_update = 'Last update not found'
    if os.path.isfile(tree_file):
        if open(tree_file, 'r').readlines()[0] == "In progress":
            last_tree_update = "In progress"
        else:
            last_tree_update = str(datetime.datetime.fromtimestamp(os.stat(tree_file).st_mtime)).split(" ")[0]
            last_tree_update = ['Today' if last_tree_update == str(datetime.datetime.now().date()) else last_tree_update][0]
    else:
        last_tree_update = 'Last update not found'
    segment = request.path.split('/')[-1]
    context = {"segment": segment,
               # "users": AuthUser.objects.all(),
               "last_taxonomy_update": last_taxonomy_update,
               "last_tree_update": last_tree_update,
               }
    return render(request, 'home/features.html', context)


@login_required(login_url="/noPermits.html")
@staff_login_required
def update_taxonomy(request):
    if dict(request.GET)['taxonomy_last_update'] == ['Last update on: Today']:
        return HttpResponse('Taxonomy already up to date.')
    else:
        outcome = TaxonomyUpdater.update_tracey_taxonomies()
        return HttpResponse(outcome)


@login_required(login_url="/noPermits.html")
@staff_login_required
def update_tree(request):
    if dict(request.GET)['tree_last_update'] == ['Last update on: Today']:
        return HttpResponse('Tree already up to date.')
    else:
        outcome = TreeUpdater.update_tracey_tree()
        return HttpResponse(outcome)


@login_required(login_url="/noPermits.html")
@staff_login_required
def read_update_taxonomy_results(request):
    f = open('utils/ncbi_taxonomy/taxdmp/TaxonomyUpdate.report.txt', 'r')
    file_content = f.read()
    f.close()
    return HttpResponse(file_content, content_type="text/plain")


@login_required(login_url="/noPermits.html")
@staff_login_required
def download_file(request, filename=''):
    if filename != '':
        # Define Django project base directory
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Define the full file path
        if 'Tree' in filename:
            filepath = 'utils/ncbi_taxonomy/' + filename
        else:
            filepath = BASE_DIR + ''
        # Open the file for reading content
        try:
            path = open(filepath, 'rb')
        except FileNotFoundError:
            return HttpResponse('<br>File not found')
        # Set the mime type
        mime_type, _ = mimetypes.guess_type(filepath)
        # Set the return value of the HttpResponse
        response = HttpResponse(path, content_type=mime_type)
        # Set the HTTP header for sending to browser
        response['Content-Disposition'] = "attachment; filename=%s" % filename
        # Return the response value
        return response
    else:
        # Load the template
        return HttpResponse()
