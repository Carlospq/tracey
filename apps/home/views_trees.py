import os
import re
import time
import subprocess
from random import randrange

from django.shortcuts import render

from .models import *
from .utils import get_taxonomy_df

from utils.ncbi_taxonomy.reducedTRACEYtaxonomies import *


def TreesView(request):
    segment = request.path.split('/')[-1]
    taxonomies = [x for x in reducedTRACEYtaxonomies]
    context = {'segment': segment, 'taxonomies': taxonomies}
    return render(request, 'home/trees.html', context)


def plotTrees(request):
    static1 = 'apps/static/assets/img/tmpTrees/'
    static2 = 'staticfiles/assets/img/tmpTrees/'
    current_time = time.time()
    minutes = 5
    for path in [static1, static2]:
        fileslist = os.listdir(path)
        for fileName in fileslist:
            file_time = os.stat(path + fileName).st_mtime
            if (current_time - file_time > minutes * 60):
                os.remove(path + fileName)

    df = get_taxonomy_df()
    data = dict(request.GET)
    if not data:
        return render(request, 'home/treeplot.html', {'error': 'At least one taxonomy must be selected to plot a tree.'})

    reducedTaxonomyID = reducedTRACEYtaxonomies_ncbiIDs[data['taxonomy'][-1]]
    values = [x.scientificname for x in Taxonomies.objects.filter(ncbi_taxonomy_id__in=reducedTaxonomyID)]
    taxonomy_ids = []
    for v in values:
        arr = list(df[df.eq(v).any(axis=1)].index.values)
        taxonomy_ids = taxonomy_ids + arr

    colname = ''
    for v in values:
        for column in df:
            if v in df[column].values:
                colname = column
                break
    if not colname:
        return render(request, 'home/treeplot.html', {'error': 'This taxonomy can not be plotted. Please select a different one.'})

    if len(taxonomy_ids) > 3500:
        return render(request, 'home/treeplot.html', {'error_length': 'Taxonomies selected exceed the maximun number of branches allowed to plot a tree. Please select a subgroup.'})

    fastax = os.getenv('FASTAX_PATH', 'fastax')
    active_ids = [str(x.ncbi_taxonomy_id) for x in Taxonomies.objects.filter(ncbi_taxonomy_id__in=taxonomy_ids)]
    clean_ids = 1
    while clean_ids:
        bashCommand = [fastax, 'tree', '-n', '-f', '"(%taxid)"'] + active_ids
        runout = subprocess.run(bashCommand, capture_output=True)
        if runout.stderr == b'':
            tree = str(runout.stdout.decode("utf-8")).strip().replace('"', "")
            clean_ids = 0
        else:
            wrong_id = re.search(r"(\b\d+)", str(runout.stderr)).group(1)
            active_ids.remove(wrong_id)

    matches = re.finditer('\d+', tree)
    ranges = [[match.start(), match.end()] for match in matches]
    ranges.sort(key=lambda k: (k[0], -k[1]), reverse=True)

    c = 0
    for r in ranges:
        c += 1
        start = r[0]
        end = r[1]
        tax_id = tree[start:end]
        try:
            t = Taxonomies.objects.get(ncbi_taxonomy_id=tax_id)
            tscientificname = t.scientificname.replace("'", "")
            tax_name = tscientificname + "|" + df.loc[t.ncbi_taxonomy_id][colname]
        except (Taxonomies.DoesNotExist, KeyError):
            tax_name = 'unknown'
        tree = tree[:start] + tax_name + tree[end:]

    try:
        user = AuthUser.objects.get(pk=request.session['_auth_user_id']).username
    except (AuthUser.DoesNotExist, KeyError):
        user = 'guest'

    treeFileName = '%s_%s.newick' % (user, str(randrange(100)))
    with open(static1 + treeFileName, 'w') as fo:
        fo.write(str(tree))

    rscript = os.getenv('RSCRIPT_PATH', 'Rscript')
    bashCommand = [rscript, 'utils/phylogeneticTrees/plotTree.R', treeFileName, colname] + values
    subprocess.run(bashCommand)

    return render(request, 'home/treeplot.html', {'treeplot': treeFileName + '.png', 'treeNewick': treeFileName})
