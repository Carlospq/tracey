import os
import re
import subprocess
import datetime
import mimetypes

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.timezone import now

from .models import *
from .views_verify import staff_login_required


@login_required(login_url="/noPermits.html")
@staff_login_required
def features(request):
    user = AuthUser.objects.get(pk=request.session['_auth_user_id'])
    if request.user.is_authenticated:
        user.last_login = now()
        user.save()

    runout = subprocess.run(['ps', 'aux'], capture_output=True)

    taxonomy_file = 'utils/ncbi_taxonomy/taxdmp/TaxonomyUpdate.report.txt'
    tree_file = 'utils/ncbi_taxonomy/TRACEY_phylogeneticTree.newick'
    try:
        sequences_file = [f for f in os.listdir('utils/traceySequenceUpdater/') if f.endswith('.log')][-1]
    except (IndexError, FileNotFoundError):
        sequences_file = ''

    psLine = [x for x in str(runout.stdout.decode("utf-8")).strip().split("\n") if "UpdateTraceyTaxonomies" in x]
    if psLine:
        taxonomyStatus = psLine[0].split()[7]
    else:
        taxonomyStatus = ''
    if "R" in taxonomyStatus or "S" in taxonomyStatus:
        last_taxonomy_update = "Update in progress"
    elif os.path.isfile(taxonomy_file):
        try:
            last_taxonomy_update = open(taxonomy_file, 'r').readlines()[0].split("(Date: ")[1].split(" ")[0][:-1]
            last_taxonomy_update = ['Today' if last_taxonomy_update == str(datetime.datetime.now().date()) else last_taxonomy_update][0]
        except (IndexError, ValueError):
            last_taxonomy_update = 'Last update not found'
    else:
        last_taxonomy_update = 'Last update not found'

    if sequences_file:
        last_sequences_update = "-".join(sequences_file.split(".")[1:-1])
        psLine = [x for x in str(runout.stdout.decode("utf-8")).strip().split("\n") if "UpdateTraceySequences" in x]
        if psLine:
            status = psLine[0].split()[7]
        else:
            status = ''
        if "R" in status or "S" in status:
            last_sequences_update_end = "Update in progress"
        else:
            try:
                last_sequences_update_end = ["" if "Update completed" in open('utils/traceySequenceUpdater/' + sequences_file, 'r').readlines()[-1] else "Update not completed"][0]
            except (IndexError, IOError):
                last_sequences_update_end = "Update not completed"
    else:
        last_sequences_update = 'Last update not found'
        last_sequences_update_end = ''

    if os.path.isfile(tree_file):
        if open(tree_file, 'r').readlines()[0] == "In progress":
            last_tree_update = "Tree in progress"
        else:
            last_tree_update = str(datetime.datetime.fromtimestamp(os.stat(tree_file).st_mtime)).split(" ")[0]
            last_tree_update = ['Today' if last_tree_update == str(datetime.datetime.now().date()) else last_tree_update][0]
    else:
        last_tree_update = 'Last update not found'

    segment = request.path.split('/')[-1]
    context = {"segment": segment,
               "last_taxonomy_update": last_taxonomy_update,
               "last_sequences_update": last_sequences_update,
               "last_sequences_update_end": last_sequences_update_end,
               "last_tree_update": last_tree_update,
               "domains": [d.domainname for d in Domains.objects.all()]
               }

    return render(request, 'home/features.html', context)


@login_required(login_url="/noPermits.html")
@staff_login_required
def update_taxonomy(request):
    if request.GET.get('taxonomy_last_update') == 'Last update on: Today':
        return HttpResponse('Taxonomy already up to date.')
    else:
        cmd = ['python3', 'manage.py', 'UpdateTraceyTaxonomies']
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return HttpResponse('Process started.')


@login_required(login_url="/noPermits.html")
@staff_login_required
def update_sequences(request):
    VALID_CONTINUE_VALS = {'continue', 'force'}
    VALID_SHORT_NAMES = {'All', 'HoSa', 'MuMu', 'RaNo', 'DaRe', 'SaCe'}

    continueVal = request.GET.get('continueVal', '')
    domain = request.GET.get('domain', '')
    onlyActive = request.GET.get('onlyActive', 'false')
    shortName = request.GET.get('shortName', 'All')

    if continueVal not in VALID_CONTINUE_VALS:
        return HttpResponse('Invalid continueVal parameter.', status=400)
    if shortName not in VALID_SHORT_NAMES:
        if not Taxonomies.objects.filter(taxonomyshortname=shortName).exists():
            return HttpResponse('Invalid shortName parameter.', status=400)
    if not Domains.objects.filter(domainname=domain).exists() and domain != '':
        return HttpResponse('Invalid domain parameter.', status=400)

    cmd = ['python3', 'manage.py', 'UpdateTraceySequences',
           '--%s' % continueVal, '--domain', domain]
    if onlyActive == 'true':
        cmd.append('--onlyActive')
    if shortName != 'All':
        cmd.extend(['--species', shortName])
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return HttpResponse('Process started.')


@login_required(login_url="/noPermits.html")
@staff_login_required
def update_tree(request):
    if request.GET.get('tree_last_update') == 'Last update on: Today':
        return HttpResponse('Tree already up to date.')
    else:
        cmd = ['python3', 'manage.py', 'UpdateTraceyTree']
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return HttpResponse('Process started.')


@login_required(login_url="/noPermits.html")
@staff_login_required
def read_update_taxonomy_results(request):
    try:
        with open('utils/ncbi_taxonomy/taxdmp/TaxonomyUpdate.report.txt', 'r') as f:
            file_content = f.read()
    except FileNotFoundError:
        return HttpResponse('Update not started or still running.', content_type="text/plain")
    return HttpResponse(file_content, content_type="text/plain")


@login_required(login_url="/noPermits.html")
@staff_login_required
def read_update_sequences_results(request):
    fileName = [f for f in os.listdir('utils/traceySequenceUpdater/') if f.endswith('.log')][0]
    f = open('utils/traceySequenceUpdater/' + fileName, 'r')
    file_content = f.read()
    f.close()
    return HttpResponse(file_content, content_type="text/plain")


@login_required(login_url="/noPermits.html")
@staff_login_required
def download_file(request, filename=''):
    if not filename:
        return HttpResponse()

    filename = os.path.basename(filename)

    if not re.match(r'^[\w\-\.]+$', filename) or filename.startswith('.'):
        return HttpResponse(status=400)

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if 'Tree' in filename:
        allowed_dir = os.path.realpath(os.path.join(PROJECT_ROOT, 'utils/ncbi_taxonomy'))
    elif 'newick' in filename:
        allowed_dir = os.path.realpath(os.path.join(PROJECT_ROOT, 'apps/static/assets/img/tmpTrees'))
    else:
        return HttpResponse(status=400)

    filepath = os.path.realpath(os.path.join(allowed_dir, filename))

    if not filepath.startswith(allowed_dir + os.sep):
        return HttpResponse(status=403)

    try:
        path = open(filepath, 'rb')
    except FileNotFoundError:
        return HttpResponse('<br>File not found')

    mime_type, _ = mimetypes.guess_type(filepath)
    response = HttpResponse(path, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % filename
    return response
