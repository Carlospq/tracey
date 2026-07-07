import os
import re
import json
import subprocess
import datetime
import mimetypes

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.timezone import now

from .models import *
from .views_verify import staff_login_required
from apps.templates.menus.query_sequences_full import menu, get_keys_recursively
from utils.traceySequenceUploader.uploadSequences import DONE_MARKER


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
               "domains": [d.domainname for d in Domains.objects.all()],
               "hmm_catalog": get_hmm_catalog(),
               "hmm_families": list(menu.keys()),
               "hmm_domains": json.dumps({f: list(menu[f].keys()) for f in menu}),
               "all_hmm_keys": json.dumps(get_keys_recursively(menu)),
               }

    return render(request, 'home/features.html', context)


def get_hmm_catalog():
    base = os.path.join(str(settings.BASE_DIR), 'utils', 'hmmModels')
    try:
        db_files = sorted(
            f for f in os.listdir(base)
            if os.path.isfile(os.path.join(base, f))
        )
        families = {}
        for entry in sorted(os.scandir(base), key=lambda e: e.name):
            if entry.is_dir():
                files = sorted(f.name for f in os.scandir(entry.path) if f.name.endswith('.hmm'))
                if files:
                    families[entry.name] = files
        return {'db_files': db_files, 'families': families}
    except (FileNotFoundError, PermissionError):
        return {'db_files': [], 'families': {}}


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
    VALID_SHORT_NAMES = {'All', 'HoSa', 'MuMu', 'RaNo', 'DaRe', 'SaCe'}

    domain = request.GET.get('domain', '')
    shortName = request.GET.get('shortName', 'All')

    if shortName not in VALID_SHORT_NAMES:
        if not Taxonomies.objects.filter(taxonomyshortname=shortName).exists():
            return HttpResponse('Invalid shortName parameter.', status=400)
    if not Domains.objects.filter(domainname=domain).exists() and domain != '':
        return HttpResponse('Invalid domain parameter.', status=400)

    cmd = ['python3', 'manage.py', 'UpdateTraceySequences', '--force', '--domain', domain]
    if shortName != 'All':
        cmd.extend(['--species', shortName])
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return HttpResponse('Process started.')


@login_required(login_url="/noPermits.html")
@staff_login_required
def rescan_motifs(request):
    hmm          = request.GET.get('hmm', '').strip()
    family       = request.GET.get('family', '').strip()
    species      = request.GET.get('species', '').strip()
    evalue       = request.GET.get('evalue', '1e-10').strip()
    motif_filter = request.GET.get('motifFilter', '').strip()
    only_active  = request.GET.get('onlyActive', '') == 'true'
    dry_run      = request.GET.get('dryRun', '') == 'true'

    if not hmm and not family:
        return HttpResponse('Specify an HMM key or a family.', status=400)

    all_keys = set(get_keys_recursively(menu))
    if hmm and hmm not in all_keys:
        return HttpResponse('Invalid HMM key.', status=400)
    if family and family not in menu:
        return HttpResponse('Invalid family.', status=400)

    try:
        float(evalue)
    except ValueError:
        return HttpResponse('Invalid e-value.', status=400)

    if species and not Taxonomies.objects.filter(
            Q(taxonomyshortname=species) | Q(scientificname=species)).exists():
        return HttpResponse('Species not found in TRACEY.', status=400)

    if motif_filter and not Domains.objects.filter(domainname=motif_filter).exists():
        return HttpResponse('Invalid motif-filter domain.', status=400)

    cmd = ['python3', 'manage.py', 'ReScanMotifs']
    if hmm:
        cmd.extend(['--hmm', hmm])
    else:
        cmd.extend(['--family', family])
    if species:
        cmd.extend(['--species', species])
    cmd.extend(['--evalue', evalue])
    if motif_filter:
        cmd.extend(['--motif-filter', motif_filter])
    if only_active:
        cmd.append('--onlyActive')
    if dry_run:
        cmd.append('--dry-run')

    if dry_run:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + (('\n--- stderr ---\n' + result.stderr) if result.stderr.strip() else '')
        return HttpResponse(output or '(no output)', content_type='text/plain')

    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return HttpResponse('Re-scan started.')


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


@login_required(login_url="/noPermits.html")
@staff_login_required
def download_hmm_zip(request):
    import io
    import zipfile

    selection = request.GET.get('selection', '')
    base_dir = os.path.realpath(os.path.join(str(settings.BASE_DIR), 'utils', 'hmmModels'))
    buffer = io.BytesIO()

    if selection == 'TRACEY_db':
        zip_name = 'TRACEY_HMM_database.zip'
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(base_dir)):
                fpath = os.path.join(base_dir, f)
                if os.path.isfile(fpath):
                    zf.write(fpath, f)
    else:
        if not selection:
            return HttpResponse(status=400)
        family_dir = os.path.realpath(os.path.join(base_dir, selection))
        if not family_dir.startswith(base_dir + os.sep):
            return HttpResponse(status=403)
        if not os.path.isdir(family_dir):
            return HttpResponse(status=404)
        zip_name = f'TRACEY_HMM_{selection}.zip'
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(family_dir)):
                if f.endswith('.hmm'):
                    zf.write(os.path.join(family_dir, f), f)

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_name}"'
    return response


UPLOAD_DIR = os.path.join('utils', 'traceySequenceUploader')
UPLOAD_INCOMING_DIR = os.path.join(UPLOAD_DIR, 'incoming')


@login_required(login_url="/noPermits.html")
@staff_login_required
def upload_sequences(request):

    if request.method != 'POST':
        return HttpResponse(status=405)
    if 'sequences_file' not in request.FILES:
        return HttpResponse('No file received.', status=400)

    try:
        evalue = float(request.POST.get('evalue', '1e-1'))
    except ValueError:
        evalue = 1e-1

    os.makedirs(UPLOAD_INCOMING_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    fasta_path = os.path.join(UPLOAD_INCOMING_DIR, f'upload.{stamp}.fasta')
    log_name = f'upload.{stamp}.log'
    log_path = os.path.join(UPLOAD_DIR, log_name)

    uploaded_file = request.FILES['sequences_file']
    with open(fasta_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    cmd = ['python3', 'manage.py', 'UploadSequences', fasta_path,
           '--evalue', str(evalue), '--username', request.user.username, '--log-file', log_path]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return JsonResponse({'log_file': log_name})


@login_required(login_url="/noPermits.html")
@staff_login_required
def read_upload_sequences_results(request):
    log_file = request.GET.get('log_file', '')
    if not re.match(r'^[\w\-\.]+$', log_file) or log_file.startswith('.'):
        return HttpResponse(status=400)

    log_path = os.path.join(UPLOAD_DIR, log_file)
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return JsonResponse({'done': False})

    if DONE_MARKER not in content:
        return JsonResponse({'done': False})

    html = content.split(DONE_MARKER)[0]
    return JsonResponse({'done': True, 'html': html})
