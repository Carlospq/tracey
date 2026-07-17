#####################################
#
# version: 1.1
# date: 05/12/2022
# updated: 21/03/2023
#
# creator: Carlos Pulido
#
# To run this script type the following command on a terminal at the main projects directory:
# python manage.py shell < utils/ncbi_taxonomy/TaxonomyUpdater.py
#
#####################################
#
# Description: This script downloads and reads most updated NCBI taxonomy files, then compares and updates the actual TRACEY taxonomies
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
from utils.phylogeneticTrees.generateTable import generate_taxonomy_tables
import datetime, os, zipfile, requests, time

try:
    from Bio import Entrez
    Entrez.email = "carlospq88@gmail.com"
    _HAS_ENTREZ = True
except Exception:
    _HAS_ENTREZ = False


def build_ncbi_dict_from_entrez(scientific_name, throttle=0.34):
    if not _HAS_ENTREZ:
        return None
    try:
        handle = Entrez.esearch(db="taxonomy", term=scientific_name)
        search = Entrez.read(handle); handle.close()
        if throttle:
            time.sleep(throttle)
        ids = search.get("IdList", [])
        if not ids:
            return None
        tax_id = ids[0]
        handle = Entrez.efetch(db="taxonomy", id=tax_id, retmode="xml")
        records = Entrez.read(handle); handle.close()
        if throttle:
            time.sleep(throttle)
        if not records:
            return None
        t = records[0]
        if str(t.get('ScientificName', '')).lower() != scientific_name.strip().lower():
            return None
        chain = [{'id': str(n['TaxId']), 'name': str(n['ScientificName']),
                  'rank': str(n.get('Rank', 'no rank'))} for n in t.get('LineageEx', [])]
        chain.append({'id': str(t['TaxId']), 'name': str(t['ScientificName']),
                      'rank': str(t.get('Rank', 'no rank'))})
        ncbi = {'dict_nodes': {}, 'dict_names': {},
                'dict_delnodes': {}, 'dict_merged': {}, 'dict_division': {}}
        for i, node in enumerate(chain):
            parent_id = chain[i - 1]['id'] if i > 0 else node['id']
            ncbi['dict_nodes'][node['id']] = {
                'tax_id': node['id'], 'parent_tax_id': parent_id, 'rank': node['rank']
            }
            ncbi['dict_names'][node['id']] = {'tax_id': node['id'], 'name_txt': node['name']}
        return str(tax_id), ncbi
    except Exception:
        return None

INFRASPECIFIC_RANKS = {
    'subspecies', 'strain', 'varietas', 'forma', 'forma specialis',
    'serogroup', 'serotype', 'biotype', 'genotype', 'isolate',
    'pathogroup', 'subvariety', 'morph',
}
AMBIGUOUS_RANKS = {'no rank', 'clade'}

def is_species_or_below(ncbi_id, ncbi, _seen=None):
    node = ncbi['dict_nodes'].get(str(ncbi_id))
    if not node:
        return False
    rank = node['rank']
    if rank == 'species' or rank in INFRASPECIFIC_RANKS:
        return True
    if rank not in AMBIGUOUS_RANKS:
        return False
    _seen = _seen or set()
    if str(ncbi_id) in _seen:
        return False
    _seen.add(str(ncbi_id))
    parent_id = node['parent_tax_id']
    if parent_id == str(ncbi_id):
        return False
    return is_species_or_below(parent_id, ncbi, _seen)


def download_ncbi_taxonomy_files(path, url='https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdmp.zip'):
    print('Downloading NCBI taxonomy files...')
    response = requests.get(url)
    open(path+"taxdmp.zip", "wb").write(response.content)
    with zipfile.ZipFile(path+"taxdmp.zip","r") as zip_ref:
        zip_ref.extractall(path)
    os.remove(path+"taxdmp.zip")


def read_ncbi_files(path = 'utils/ncbi_taxonomy/taxdmp/'):
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
        taxonomy = Taxonomies.objects.get(ncbi_taxonomy_id=ncbi_id)
        print('Taxonomy exists. Aborted..')
        return taxonomy
    except:
        pass

    # Create NCBI parent Taxonomy if does not exists in TRACEY
    try:
        taxonomy_parent = Taxonomies.objects.get(ncbi_taxonomy_id=node['parent_tax_id'])
    except:
        taxonomy_parent = create_ncbi_taxonomy(node['parent_tax_id'], ncbi)

    # Check if shortname exists (species-level taxonomies and below only)
    if is_species_or_below(ncbi_id, ncbi):
        _name = [name['name_txt'].split(" ") if len(name['name_txt'].split(" ")) > 1 else ''][0]
        if not _name or len(_name) < 2:
            tax_shortname = ''
        else:
            lengths = [[2,2], [2,3], [3,2], [3,3]]
            for l in lengths:
                tax_shortname = _name[0][:l[0]].title()+_name[1][:l[1]].title()

                if tax_shortname.endswith("."):
                    related_taxonomies = Taxonomies.objects.filter(taxonomyshortname__istartswith=tax_shortname[:-1])
                    get_index = [int(t.taxonomyshortname[-1]) for t in related_taxonomies if "_" in t.taxonomyshortname]
                    if get_index:
                        tax_shortname = tax_shortname[:-1] + "_" + str(max(get_index)+1)
                    else:
                        tax_shortname = tax_shortname[:-1] + "_1"

                if not Taxonomies.objects.filter(taxonomyshortname=tax_shortname):
                    break

            if Taxonomies.objects.filter(taxonomyshortname=tax_shortname):
                tax_shortname = ''
    else:
        tax_shortname = ''
    taxonomy = Taxonomies(scientificname = name['name_txt'],
                          taxonomycomments = 'automatically Added by TaxonomyUpdater',
                          taxonomyparent_id = int(taxonomy_parent.taxonomy_id),
                          analysislevel = '-1',
                          taxonomyrank = node['rank'],
                          taxonomyshortname = tax_shortname,
                          ncbi_taxonomy_id = int(ncbi_id),
                          taxonomystatus = 'main reference')
    taxonomy.save()
    # Write report
    if report_file:
        report_file.write("CREATED Taxonomy (id:%s): %s\n"%(taxonomy.taxonomy_id, taxonomy.scientificname))
    return taxonomy


def merge_ncbi_taxonomy(taxonomy, ncbi, report_file=''):
    # Default values
    time_now = datetime.datetime.now().date()
    # Search for merged taxonomy - create parent taxonomy if does not exists
    ncbi_id = str(taxonomy.ncbi_taxonomy_id)
    ncbi_merged_id = ncbi['dict_merged'][ncbi_id]['new_tax_id']
    taxonomy.taxonomystatus = 'merged by ncbi'
    taxonomy.taxonomycomments = taxonomy.taxonomycomments + '; %s - automatically Updated by TaxonomyUpdater: merged into %s by NCBI' % (str(time_now), ncbi_merged_id)
    taxonomy.save()
    try:
        merged_taxonomy = Taxonomies.objects.get(ncbi_taxonomy_id=ncbi_merged_id)
    except:
        merged_taxonomy = create_ncbi_taxonomy(ncbi_merged_id, ncbi)
    # Update reportFile
    if report_file:
        with open(report_file, 'a') as rf:
            rf.write("MERGED Taxonomy (id:%s): %s - merged into %s (id:%s) by NCBI\n" % (taxonomy.taxonomy_id, taxonomy.scientificname, merged_taxonomy.scientificname, merged_taxonomy.taxonomy_id))
    # Make sequences from old taxonomies to point to new taxonomy
    for seq in taxonomy.sequences_set.all():
        seq.taxonomy_id = merged_taxonomy.taxonomy_id
        seq.taxonomy = merged_taxonomy
        seq.save()
        if report_file:
            with open(report_file, 'a') as rf:
                rf.write("\t- SEQUENCE %s (id:%s): now linked to taxonomy %s (id:%s)\n" % (seq.sequenceshortname, seq.sequence_id, merged_taxonomy.scientificname, merged_taxonomy.taxonomy_id))
    return


def delete_ncbi_taxonomy(taxonomy, report_file=''):
    # Default values
    time_now = datetime.datetime.now().date()
    # Delete taxonomy
    taxonomy.taxonomystatus = 'deleted by ncbi'
    taxonomy.taxonomycomments = taxonomy.taxonomycomments + '; %s - automatically Updated by TaxonomyUpdater: deleted from NCBI' % (str(time_now))
    taxonomy.save()
    # Update reportFile
    if report_file:
        with open(report_file, 'a') as rf:
            rf.write("DELETED Taxonomy (id:%s): %s - deleted from NCBI\n" % (taxonomy.taxonomy_id, taxonomy.scientificname))
        # Sequences are reported in 'report_file'
        for seq in taxonomy.sequences_set.all():
            # Flag them as "dead" (????)
            with open(report_file, 'a') as rf:
                rf.write("\t- %s (id:%s): sequence's taxonomy (%s; id:%s) has been deleted from NCBI\n" % (seq.sequenceshortname, seq.sequence_id, taxonomy.scientificname, taxonomy.taxonomy_id))


def update_ncbi_taxonomy(taxonomy, ncbi, report_file=''):
    time_now = datetime.datetime.now().date()
    ncbi_id = taxonomy.ncbi_taxonomy_id
    ncbi_parent_id = ncbi['dict_nodes'][str(ncbi_id)]['parent_tax_id']

    # Check if parent taxonomy exists and create it if doesn't exists
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
        taxonomy.save()
        if report_file:
            with open(report_file, 'a') as rf:
                rf.write("UPDATED Taxonomy (id:%s): %s\n updated fields - %s\n"%(taxonomy.taxonomy_id, taxonomy.scientificname, ", ".join(updated_fields)))

    return taxonomy


def update_tracey_taxonomies(path = 'utils/ncbi_taxonomy/taxdmp/', report_file_name='TaxonomyUpdate.report.txt'):
    time_now = datetime.datetime.now().date()
    # Check date of last update in report_file_name
    if not os.path.isdir(path):
        os.mkdir(path)
    if report_file_name in os.listdir(path):
        try:
            fheader = open(path+report_file_name, 'r').readlines()[0]
        except:
            fheader = ''
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

    ## Tag duplications in database
    # taxonomystatus: 'merged by ncbi', 'additional', 'unknown', 'main reference', 'secondary reference', 'duplication', 'additionnal', 'deleted from ncbi'
    print("Removing duplications in database")
    from collections import Counter
    counts = Counter([x.ncbi_taxonomy_id for x in Taxonomies.objects.all()])
    duplicated_ncbi_ids = [x for x in counts if counts[x] > 1]
    for ncbi_id in duplicated_ncbi_ids:
        # 32644 is the NCBI ID for "unclassified sequences" - skip it
        if ncbi_id == 32644:
            continue
        # Set first entry as MAIN
        main_entry = Taxonomies.objects.filter(ncbi_taxonomy_id=ncbi_id).order_by('taxonomy_id')[0]
        # Set any sequence in the rest of duplication to point to the main entry
        for entry in Taxonomies.objects.filter(ncbi_taxonomy_id=ncbi_id).exclude(taxonomy_id=main_entry.taxonomy_id):
            for g in Genomesource.objects.filter(taxonomy=entry):
                g.taxonomy = main_entry
                g.taxonomy_id = main_entry.taxonomy_id
                g.save()
            for seq in Sequences.objects.filter(taxonomy_id=entry.taxonomy_id):
                seq.taxonomy_id = main_entry.taxonomy_id
                seq.taxonomy = main_entry
                seq.save()
            entry.delete()


    ## Merge Taxonomies that have been merged by NCBI
    print("Merging Taxonomies that have been merged by NCBI")
    for ncbi_id in ncbi['dict_merged']:
        try: # Check if taxonomy exists in TRACEY and merge it
            taxonomy = Taxonomies.objects.get(ncbi_taxonomy_id=ncbi_id)
            merge_ncbi_taxonomy(taxonomy, ncbi, report_file=path+report_file_name)
        except:
            continue

    ## Delete Taxonomies that have been deleted by NCBI
    print("Deleting Taxonomies that have been deleted by NCBI")
    for taxonomy in Taxonomies.objects.all():
        if str(taxonomy.ncbi_taxonomy_id) in ncbi['dict_delnodes']:
            delete_ncbi_taxonomy(taxonomy, report_file=path+report_file_name)

    ## Update Taxonomies that have been updated by NCBI
    print("Updating Taxonomies that have been updated by NCBI")
    for taxonomy in Taxonomies.objects.all():
        if str(taxonomy.ncbi_taxonomy_id) in ncbi['dict_nodes']:
            update_ncbi_taxonomy(taxonomy, ncbi, report_file=path+report_file_name)
        else:
            if report_file_name:
                with open(path+report_file_name, 'a') as fh:
                    fh.write("NOT FOUND: %s NCBI ID was not found in TRACEY\n"%(taxonomy.ncbi_taxonomy_id))

    print("Regenerating taxonomy lineage tables")
    generate_taxonomy_tables()

    return "\nUpdate completed."

# Run code when run as script
if __name__ == "django.core.management.commands.shell":
    print("Updating TRACEY taxonomies...")
    outcome = update_tracey_taxonomies()
    print(outcome)
