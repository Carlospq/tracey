# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import xml.etree.ElementTree as ET
import pyhmmer
from dna_features_viewer import GraphicFeature, GraphicRecord
import matplotlib.pyplot as plt
from time import gmtime, strftime
from collections import OrderedDict
from operator import getitem

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

from django import template

register = template.Library()


### FUNCTIONS ###
def get_childs(model, parent, parent_id, child_parent_id, childs=[], search_type='iexact'):
    variable_column = child_parent_id
    filter = variable_column + '__' + search_type
    cs = model.objects.none()
    for p in parent:
        if getattr(p, parent_id) == 4:
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


def get_sequences(query):
    def notEmpty(element):
        if element in [[''], '']:
            return False
        return True

    # Filter by Domaingroup
    if 'domaingroup_rank' in query and notEmpty(query['domaingroup_rank']):
        if 'domaingroup' in query and notEmpty(query['domaingroup']):
            domaingroup_list = [x.replace("-","") for x in query['domaingroup']]
            domaingroups_parents = Domaingroups.objects.filter(domaingroupname__in = domaingroup_list)
            domaingroups_children  = get_childs(Domaingroups, domaingroups_parents, "domaingroup_id", "domaingroupparent_id", childs=[])
            children_ids = [x.domaingroup_id for x in domaingroups_children] + [x.domaingroup_id for x in domaingroups_parents]
        else:
            # Get all child domain groups of domaingroup_rank
            domaingrouprank = Domaingroups.objects.filter(domaingroupname = query['domaingroup_rank'][0].replace("-",""))
            domaingrouprank_children = get_childs(Domaingroups, domaingrouprank, "domaingroup_id", "domaingroupparent_id", childs=[])
            # domaingrouprank_childs = get_childs_raw(Domaingroups, "domaingroups", domaingrouprank, "domaingroup_id", "domaingroup_id", "domaingroupparent_id")
            children_ids = [x.domaingroup_id for x in domaingrouprank_children] + [x.domaingroup_id for x in domaingrouprank]
        domaingroups = Domaingroups.objects.filter(domaingroup_id__in = children_ids)
    else:
        domainname = query['domainname'][0]
        domain = Domains.objects.get(domainname = domainname)
        domaingroups = Domaingroups.objects.filter(domain_id = domain.domain_id)

    motifs = Motifs.objects.filter(domaingroup_id__in = domaingroups.values('domaingroup_id'))
    seqs = Sequences.objects.filter(sequence_id__in = motifs.values('sequence_id'))

    # Filter seqs if shortname/foreignAnnotation or taxonomy is provided
    if 'shortname' in query and notEmpty(query['shortname']):
        seqs = seqs.filter(sequenceshortname__icontains = query['shortname'][0])

    if 'foreignannotation' in query and notEmpty(query['foreignannotation']):
        pattern = re.compile("^gi\|([0-9]+)$")
        if not pattern.match(query['foreignannotation'][0]):
            context = {'error': 'Foreign Annotation format is not correct. Plase use NCBI format.'}
            return context
        seqs = seqs.filter(foreignannotation = query['foreignannotation'][0])

    if 'taxonomy_rank' in query and notEmpty(query['taxonomy_rank']):
        if 'taxonomy' in query and notEmpty(query['taxonomy']):
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
            context = {'error': 'At least one %s must be selected.' % (query['taxonomy_rank'][0])}
            return context

    return seqs
#################

# Home
@login_required(login_url="/login/")
def index(request):
    context = {'segment': 'index'}

    html_template = loader.get_template('home/home.html')
    #html_template = loader.get_template('home/index.html')

    return HttpResponse(html_template.render(context, request))


# Pages deprecated - template examples
@login_required(login_url="/login/")
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
    if domainname == '':
        domainGroupNames = []
    else:
        domain = Domains.objects.filter(domainname = domainname)
        domainGroupNames = [x.domaingroupname for x in Domaingroups.objects.filter(domain_id__in = domain.values('domain_id')) if x.analysislevel == 2 ]

    return render(request, 'home/query-sequences-family-domaingroupsRank1.html', {'domaingroups_rank_list': domainGroupNames})


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
                childs_list.append(name_list)
                if Domaingroups.objects.filter(domaingroupparent_id=domaingroup.domaingroup_id):
                    get_names_list(domaingroup.domaingroup_id)

        return childs_list

    childs_list = []
    rank = request.GET.get('domaingroup_rank')
    if rank == "":
        childs_list = []
    else:
        parent_id = Domaingroups.objects.filter(domaingroupname=rank)[0].domaingroup_id
        childs_list = get_names_list(parent_id)
    return render(request, 'home/query-sequences-family-domaingroupsRank2.html', {'domaingroups_rank_list': childs_list})


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

    return render(request, 'home/query-sequences-results.html', context)


def QuerySequencesFastaFormat(request):
    if request.method == 'POST':
        boxes = request.POST.getlist('checkbox')
    try:
        sequences = Sequences.objects.filter(pk__in=boxes)
    except Sequences.DoesNotExist:
        raise Http404("Sequences does not exist")

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
               "motifs": sorted(list(set([ x.motifname for x in Motifs.objects.all() ])))
              }

    if request.method == "POST":
        context = dict(request.POST)
        if not context['protseq'][0]:
            context['error'] = 'Please provide a protein sequence to analyze.'
            return render(request, 'home/query-motifs.html', context)

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

    alphabet = pyhmmer.easel.Alphabet.amino()
    background = pyhmmer.plan7.Background(alphabet)
    seq1 = pyhmmer.easel.TextSequence(name=b"Query sequence", sequence=sequence).digitize(alphabet)
    if motifname[0].upper() == "ALL":
        hmmDb = "./utils/hmmModels/MOTIFS.hmmDb"
    else:
        hmmDb = "./utils/hmmModels/%s/%s.hmmDb"%(motifname[0].upper(), motifname[0].upper())
    hmm =  pyhmmer.plan7.HMMFile(hmmDb)

    pipeline = pyhmmer.plan7.Pipeline(hmm.read().alphabet)
    hits = pipeline.scan_seq(seq1, hmm)

    hits_d = {}
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

    segment = request.path.split('/')[-1]
    context = dict(request.POST)
    context["segment"] = segment
    context["hits_d"] = motifScan(context["protseq"][0], context['motifname'])
    context["motifs"] = sorted(list(set([ x.motifname for x in Motifs.objects.all() ])))

    if request.method == "POST":
        # context = dict(request.POST)
        if not context['protseq'][0]:
            context['error_seq'] = 'Please provide a protein sequence to analyze.'
            return render(request, 'home/query-motifs-results.html', context)
        if not context['hits_d']:
            context['error_hits'] = "HMMER couldn't find any match for motif %s in the query sequence."%(context['motifname'][0])
            return render(request, 'home/query-motifs-results.html', context)

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
                             startposition = d['env_from'],
                             stopposition = d['env_to'],
                             verifymotifcomments = '',
                             domaingroup_id = Domaingroups.objects.get(domaingroupname = d['dg']).domaingroup_id,
                             gaps = countGaps(d['alignment'].target_sequence),
                             active = 0,
                             method = Methods.objects.get(domaingroup_id = Domaingroups.objects.get(domaingroupname = d['dg']).domaingroup_id), #Review this field
                             verifymotifrank = 1000000,
                             asciioutput = '<asciiOutput>\r\t<consensus>%s</consensus>\r\t<similarity>%s\t</similarity>\r\t<motif>%s</motif>\r\t<eValue>%s</eValue>\r\t<bitscore>321</bitscore>\r</asciiOutput>'%(d['alignment'].hmm_sequence, d['alignment'].identity_sequence, d['alignment'].target_sequence, d['evalue']),
                             binaryoutput = '')
            vm.save()

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

    context["form"] = InsertSequence()
    return render(request, 'home/query-insert.html', context)


#Verify
@staff_login_required
def QueryVerifyMenuView(request):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    segment = request.path.split('/')[-1]
    context = {'segment': segment,
               'status': ['', 'dead', 'replaced NCBI', 'live', 'ignore', 'unknown', 'crystal structure', 'suppressed', 'replaced'],
              }

    return render(request, 'home/query-verify-menu.html', context)


# Users
@staff_login_required
def users(request):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    if request.user.is_authenticated:
        user.last_login = now()
        user.save()
    segment = request.path.split('/')[-1]
    context = {"segment": segment,
               "users": AuthUser.objects.all()}
    return render(request, 'home/users.html', context)


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

    if seq.gene.ncbigene_id == '-1':
        ncbigene_id = 'not_specified:-1:%s'%(seq.gene.gene_id)
    else:
        ncbigene_id = seq.gene.ncbigene_id

    # Retrive verifyMotifs
    motifs = Motifs.objects.filter(sequence_id = sequence_id)
    verifymotifs = Verifymotifs.objects.filter(sequence_id = sequence_id)
    context["motifs"]  = {}
    context["verifymotifs"]  = {}

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
                for vm in Verifymotifs.objects.filter( sequence_id = motif.sequence_id ):
                    if motif.sequence_id == vm.sequence_id and motif.asciioutput == vm.asciioutput:
                        vm.active = 0
                        vm.save()
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
