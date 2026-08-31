from .models import *
from .forms import *
from . import views
from . import urls

import xml.etree.ElementTree as ET
from django.test.utils import setup_test_environment
from django.test import Client
from django.urls import reverse, path

# setup_test_environment()

## TEST QUERY SEQUENCES
def test_response(urlname, html_response, context={}, args=[]):
    # context in form of dict: {k: v, }
    # args in form of list: [####, ]
    client = Client()
    response = client.get(reverse(urlname, args=args), context)
    status_code = response.status_code
    if status_code == html_response:
        print("Correct response for '%s'"%(urlname))
    else:
        print("#ERROR: expected %s for '%s' - got %s"%(str(html_response), urlname, str(status_code)))


def test_response_ajax(urlname, context={}, expected_length=0):
    # context in form of dict: {k: v, }
    client = Client()
    content = client.get(reverse(urlname), context).content.decode("utf-8")
    root = ET.fromstring("<root>" + content + "</root>")
    n = 0
    for child in root: n+=1
    if n == 0 and expected_length != 0:
        print("#ERROR: ajax returned element of length 0 in %s for %s"%(urlname, context))
    else:
        print("Correct response for '%s' - %s"%(urlname, context))


# Test Home
test_response('home', 302)

# Test query
test_response('query', 200)

# Test query sequences
segment = 'query-sequences'
domains = Domains.objects.all()
domainsList = sorted(list( set([ x.domainname for x in domains ]) ))

SNAREdomainID = Domains.objects.get(domainname = "SNARE").domain_id
SNAREdomaingroups = Domaingroups.objects.filter(domain_id = SNAREdomainID)
SNAREdomaingroupnames = [x.domaingroupname for x in SNAREdomaingroups if x.analysislevel == 2 ]

SNAREmotifs = Motifs.objects.filter(domaingroup_id__in = SNAREdomaingroups.values('domaingroup_id'))
shortnames = sorted(list( set([ x.sequenceshortname.split("_")[0] for x in Sequences.objects.filter(sequence_id__in = SNAREmotifs.values('sequence_id')) if x.sequenceshortname.split("_")[0] != "" ]) ))
taxonomy_ranks = ['superkingdom', 'kingdom', 'superphylum', 'phylum', 'subphylum', 'superclass', 'class', 'subclass', 'superorder', 'order', 'suborder', 'infraorder', 'superfamily', 'family', 'genus', 'subgenus', 'species subgroup', 'species', 'subspecies', 'strain']

form = FamilyForm

query_sequences_context = {'segment': segment,
           'domainsList': domainsList,
           'domainGroupNames': SNAREdomaingroupnames,
           'shortnames': shortnames,
           'taxonomy_ranks': taxonomy_ranks,
           'domaingroup_rank': SNAREdomaingroupnames,
           'form': form,
           'error': ''}

test_response('query-sequences', 200, context=query_sequences_context)

# Test query sequences ajax's
def get_names_list(parent_id):
    # for domaingroup in Domaingroups.objects.filter(domaingroupparent_id=parent_id):
    childs_list = []
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

for taxa in taxonomy_ranks:
    test_response_ajax('ajax_load_taxonomy_rank', context={'taxonomy_rank': taxa})

for domain in domainsList:
    test_response_ajax('ajax_load_domaingroups_rank1', context={'domainname': domain})
    test_response_ajax('ajax_load_sequenceshortnames', context={'domainname': domain})

for domaingroup in [domaingroup for domaingroup in Domaingroups.objects.all() if domaingroup.analysislevel == 2]:
    expected_length = 1
    if len(get_names_list(domaingroup.domaingroup_id)) == 0:
        expected_length = 0
    test_response_ajax('ajax_load_domaingroups_rank2', context={'domaingroup_rank': domaingroup.domaingroupname}, expected_length=expected_length)
