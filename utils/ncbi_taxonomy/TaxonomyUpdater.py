#####################################
#
# creator: Carlos Pulido
# date: 05/12/2022
#
# To run this script type the following command on a terminal at the main projects directory:
# python manage.py shell < utils/ncbi_taxonomy/TaxonomyUpdater.py
#
#####################################
#
# Uses NCBI taxonomy files to check and update TRACEY taxonomies
# NCBI taxonomy files can be found here: https://www.ncbi.nlm.nih.gov/guide/taxonomy/ -> Downloads
# Definitions of headers can be found here: https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_readme.txt
#
#####################################

# TaxonomyUpdater.py
# This script downloads and reads NCBI taxonomy files and compares with the actual TRACEY taxonomies
# If TRACEY taxonomies are in:
#   - delnodes.dmp: TRACEY taxonomy.taxonomystatus is set to "deleted". Sequences pointing to this taxonomy are reported in 'report_file'
#   - merged.dmp: TRACEY taxonomy is updated and if required new taxonomies are created using NCBI information
#   - nodes.dmp: If NCBI data does not match with TRACEY data then TRACEY taxonomy is updated
#   - none of the previous: reports missing id in 'report_file'

#####################################
from apps.home.models import *
import datetime, os, zipfile, requests

def download_ncbi_taxonomy_files(path, url='https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdmp.zip'):
    print('Downloading NCBI taxonomy files...')
    response = requests.get(url)
    open(path+"taxdmp.zip", "wb").write(response.content)
    with zipfile.ZipFile(path+"taxdmp.zip","r") as zip_ref:
        zip_ref.extractall(path)
    os.remove(path+"taxdmp.zip")


def read_ncbi_files(path):
    # Check and Read NCBI files
    file_nodes = path+'nodes.dmp'
    file_names = path+'names.dmp'
    file_delnodes = path+'delnodes.dmp'
    file_merged = path+'merged.dmp'
    file_division = path+'division.dmp'

    header_nodes = ['tax_id', 'parent_tax_id', 'rank', 'embl_code', 'division_id', 'inherited_div', 'genetic_code_id', 'inherited_GC', 'mitochondrial_genetic_code_id', 'inherited_MGC', 'GenBank_hidden', 'hidden_subtree_root', 'comments']
    header_names = ['tax_id', 'name_txt', 'unique_name', 'name_class']
    header_delnodes = ['tax_id']
    header_merged = ['old_tax_id', 'new_tax_id']
    header_division = ['division_id', 'division cde', 'division name', 'comments']

    files = [file_nodes, file_names, file_delnodes, file_merged, file_division]
    headers = [header_nodes, header_names, header_delnodes, header_merged, header_division]
    dictionaries = ['dict_nodes', 'dict_names', 'dict_delnodes', 'dict_merged', 'dict_division']

    ncbi = {'dict_nodes': {},
            'dict_names': {},
            'dict_delnodes': {},
            'dict_merged': {},
            'dict_division': {}
           }

    # Create dictionaries with ncbi info
    for file_name, file_header, dictionary in zip(files, headers, dictionaries):
        f = file_name.split("/")[-1]
        d = file_name.replace(f, "")
        if not f in os.listdir(d):
            print('\n\n# MISSING %s file in %s. Aborting...'%(f, d))
            break
        print('\t- Reading '+file_name)
        with open(file_name) as filehandler:
            for line in filehandler:
                line = line.strip().replace("\t|", "").split("\t")
                # Skip lines from names.dmp if they are not 'scientific name'
                if 'name_class' in file_header and not 'scientific name' in line: continue
                field_id = line[0]
                ncbi[dictionary][field_id] = {}
                for i in range(len(line)):
                    ncbi[dictionary][field_id][file_header[i]] = line[i]

    return ncbi


def create_ncbi_taxonomy(ncbi_id, ncbi, report_file=''):
    # Check if ID exists in NCBI files
    try:
        node = ncbi['dict_nodes'][str(ncbi_id)]
        name = ncbi['dict_names'][str(ncbi_id)]
    except:
        print('NCBI id %s does not exists.'%(str(ncbi_id)))
    # Check if taxonomy already exists
    try:
        Taxonomies.objects.get(ncbi_taxonomy_id=ncbi_id)
        print('Taxonomy exists. Aborted..')
        return
    except:
        pass
    # Create NCBI parent Taxonomy if does not exists in TRACEY
    try:
        taxonomy_parent = Taxonomies.objects.get(ncbi_taxonomy_id=node['parent_tax_id'])
    except:
        taxonomy_parent = create_ncbi_taxonomy(node['parent_tax_id'], ncbi)
    taxonomy = Taxonomies(scientificname = name['name_txt'],
                          taxonomycomments = 'automatically Added by TaxonomyUpdater',
                          taxonomyparent_id = int(taxonomy_parent.taxonomy_id),
                          analysislevel = '-1',
                          taxonomyrank = node['rank'],
                          taxonomyshortname = [name['name_txt'].split(" ")[0][:2].title()+name['name_txt'].split(" ")[1][:2].title() if len(name['name_txt'].split(" ")) > 1 else ''][0],
                          ncbi_taxonomy_id = int(ncbi_id),
                          taxonomystatus = 'main reference')
    taxonomy.save()
    if report_file:
        report_file.write("CREATED Taxonomy (id:%s): %s\n"%(taxonomy.taxonomy_id, taxonomy.scientificname))
    return taxonomy


def update_taxonomy(taxonomy, ncbi, report_file='', update_type=''):
    time_now = datetime.datetime.now().date()
    tracey_id = taxonomy.taxonomy_id
    ncbi_id = taxonomy.ncbi_taxonomy_id
    #MERGED IDs
    if update_type == "MERGED":
        new_ncbi_id = int(ncbi['dict_merged'][str(ncbi_id)]['new_tax_id'])
        # Create new Taxonomy if does not exists in TRACEY
        try:
            new_merged_taxonomy = Taxonomies.objects.get(ncbi_taxonomy_id=new_ncbi_id)
        except:
            new_merged_taxonomy = create_ncbi_taxonomy(new_ncbi_id, ncbi)
        # Mark old Taxonomy as "merged" in comments (only if last update date is different than todays date)
        if not str(time_now) in taxonomy.taxonomycomments and not 'merged into %s'%(new_merged_taxonomy.taxonomy_id) in taxonomy.taxonomycomments:
            taxonomy.taxonomycomments = taxonomy.taxonomycomments+'; %s - automatically Updated by TaxonomyUpdater: merged into %s by NCBI'%(str(time_now), new_merged_taxonomy.taxonomy_id)
            taxonomy.taxonomystatus = 'merged by ncbi'
            # Move Sequences from old Taxonomy to new Taxonomy
            if report_file:
                report_file.write("%s Taxonomy (id:%s): %s - merged into %s (id:%s) by NCBI\n"%(update_type, tracey_id, taxonomy.scientificname, new_merged_taxonomy.scientificname, new_merged_taxonomy.taxonomy_id))
            for seq in taxonomy.sequences_set.all():
                seq.taxonomy_id = new_merged_taxonomy.taxonomy_id
                seq.save()
                if report_file:
                    report_file.write("\t- SEQUENCE %s (id:%s): now linked to taxonomy %s (id:%s)\n"%(seq.sequenceshortname, seq.sequence_id, new_merged_taxonomy.scientificname, new_merged_taxonomy.taxonomy_id))
    # DELETED IDs
    elif update_type == "DELETED":
        report_file.write("DELETED Taxonomy (%s): %s\n"%(tracey_id, taxonomy.scientificname))
        if not str(time_now) in taxonomy.taxonomycomments and not 'deleted from NCBI' in taxonomy.taxonomycomments:
            taxonomy.taxonomycomments = taxonomy.taxonomycomments+'; %s - automatically Updated by TaxonomyUpdater: deleted from NCBI'%(str(time_now))
            taxonomy.taxonomystatus = 'deleted from ncbi'
            if report_file:
                report_file.write("%s Taxonomy (id:%s): %s - deleted from NCBI\n"%(update_type, tracey_id, taxonomy.scientificname))
                # Sequences are reported in 'report_file'
                for seq in taxonomy.sequences_set.all():
                    # Flag them as "dead" (????)
                    report_file.write("\t- %s (id:%s): sequence's taxonomy (%s; id:%s) has been deleted from NCBI\n"%(seq.sequenceshortname, seq.sequence_id, taxonomy.scientificname, tracey_id))
    # EXISTING IDs: check if update is required
    elif str(ncbi_id) in ncbi['dict_nodes']:
        # Check if parent taxonomy exists and create it if doesn't exists
        ncbi_parent_id = ncbi['dict_nodes'][str(ncbi_id)]['parent_tax_id']
        try:
            taxonomy_parent = Taxonomies.objects.get(ncbi_taxonomy_id=ncbi_parent_id)
        except:
            taxonomy_parent = create_ncbi_taxonomy(ncbi_parent_id, ncbi)
        # Update Taxonomy info (if required)
        updated_fields = []
        for attr, val in zip(['taxonomyparent_id', 'taxonomyrank', 'scientificname'], [int(taxonomy_parent.taxonomy_id), ncbi['dict_nodes'][str(ncbi_id)]['rank'], ncbi['dict_names'][str(ncbi_id)]['name_txt']]):
            if getattr(taxonomy, attr) != val:
                taxonomy.taxonomyparent_id = int(taxonomy_parent.taxonomy_id)
                taxonomy.taxonomyrank = ncbi['dict_nodes'][str(ncbi_id)]['rank']
                taxonomy.scientificname = ncbi['dict_names'][str(ncbi_id)]['name_txt']
                updated_fields.append(attr)
        if updated_fields:
            taxonomy.taxonomycomments = taxonomy.taxonomycomments+'; %s - automatically Updated by TaxonomyUpdater: updated fields = %s'%(str(time_now), ", ".join(updated_fields))
            if report_file:
                report_file.write("UPDATED Taxonomy (id:%s): %s\n updated fields - %s\n"%(taxonomy.taxonomy_id, taxonomy.scientificname, ", ".join(updated_fields)))
    # MISSING IDs
    else:
        if report_file:
            report_file.write("NOT FOUND: %s NCBI ID was not found in ncbi files\n"%(ncbi_id))
        return

    taxonomy.save()
    return taxonomy

def update_tracey_taxonomies(path = 'utils/ncbi_taxonomy/taxdmp/', report_file_name='TaxonomyUpdate.report.txt'):
    time_now = datetime.datetime.now().date()
    # Check date of last update in report_file_name
    if not os.path.isdir(path):
        os.mkdir(path)
    if report_file_name in os.listdir(path):
        fheader = open(path+report_file_name, 'r').readlines()[0]
        if str(time_now) in fheader:
            return '\nALERT: Last update of TRACEY taxonomies in %s is today (%s)'%(report_file_name, str(time_now))
    # Download current NCBI taxonomy files
    download_ncbi_taxonomy_files(path)
    # Start TRACEY taxonomies update
    if report_file_name:
        report_file = open(path+report_file_name, 'w')
        report_file.write("#### REPORT for TaxonomyUpdater (Date: %s)  ####\n"%(str(time_now)))
        report_file.write("#### NOTE: IDs in this report correspond to TRACEY IDs and not to NCBI IDs  ####\n\n")
    ncbi = read_ncbi_files(path)
    # Parse all TAXONOMIES in TRACEY and update them if necesary
    for taxonomy in Taxonomies.objects.all():
        ncbi_id = str(taxonomy.ncbi_taxonomy_id)
        # Check update type for Taxonomy
        if ncbi_id in ncbi['dict_delnodes']:
            update_type = 'DELETED'
        elif ncbi_id in ncbi['dict_merged']:
            update_type = 'MERGED'
        else:
            update_type = ''
        update_taxonomy(taxonomy, ncbi, report_file=report_file, update_type=update_type)

    return "\nUpdate completed."

# Run code when run as script
if __name__ == "django.core.management.commands.shell":
    print("Updating TRACEY taxonomies...")
    outcome = update_tracey_taxonomies()
    print(outcome)
