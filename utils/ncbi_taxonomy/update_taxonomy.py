#####################################
#
# creator: Carlos Pulido
# date: 05/12/2022
#
# To run this script type the following command on a terminal at the main projects directory:
# python manage.py shell < utils/ncbi_taxonomy/update_taxonomy.py
#
#####################################
#
# Uses NCBI taxonomy files to check and update TRACEY taxonomies
# NCBI taxonomy files can be download from: https://www.ncbi.nlm.nih.gov/guide/taxonomy/ -> Downloads
# Definitions of headers can be found here: https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_readme.txt
#
#####################################

# update_taxonomy.py
# This script reads NCBI taxonomy files and compares with the actual TRACEY taxonomies
# If TRACEY taxonomies are in:
#   - delnodes.dmp: TRACEY taxonomy.taxonomystatus is set to "deleted" and sequences pointing to this taxa are flagged as "dead"
#   - nodes.dmp: It checks if TRACEY taxonomy.taxonomyparent_id matches with NCBI new data.
#                If new data matches with TRACEY data then no modifications are performed.
#                If new data does not match with TRACEY data then TRACEY taxonomy is updated
#   - none of the previous: It search for TRACEY taxonomy.scientificname in names.dmp.
#                If scientific name is found then TRACEY taxonomy.taxonomyparent_id and taxonomy.ncbi_taxonomy_id is updated with the new NCBI data
#                If scientific name is not found ......

#####################################
from apps.home.models import *

import datetime

time_now = datetime.datetime.now()

# Check and Read NCBI files
file_nodes = 'utils/ncbi_taxonomy/taxdmp/nodes.dmp'
file_names = 'utils/ncbi_taxonomy/taxdmp/names.dmp'
file_delnodes = 'utils/ncbi_taxonomy/taxdmp/delnodes.dmp'
file_merged = 'utils/ncbi_taxonomy/taxdmp/merged.dmp'
file_division = 'utils/ncbi_taxonomy/taxdmp/division.dmp'

header_nodes = ['tax_id', 'parent_tax_id', 'rank', 'embl_code', 'division_id', 'inherited_div', 'genetic_code_id', 'inherited_GC', 'mitochondrial_genetic_code_id', 'inherited_MGC', 'GenBank_hidden', 'hidden_subtree_root', 'comments']
header_names = ['tax_id', 'name_txt', 'unique_name', 'name_class']
header_delnodes = []
header_merger = []
header_division = []

dict_nodes = {}
dict_names = {}
dict_delnodes = {}
dict_merger = {}
dict_division = {}

files = [file_nodes, file_names, file_delnodes, file_merged, file_division]
headers = [header_nodes, header_names, header_delnodes, header_merger, header_division]
dictionaries = [dict_nodes, dict_names, dict_delnodes, dict_merger, dict_division]

for file_name, file_header, dictionary in zip(files, headers, dictionaries):
    print('\t- Reading '+file_name)
    with open(file_name) as filehandler:
        for line in filehandler:
            line = line.strip().split("\t|\t")
            field_id = line[0]
            dictionary[field_id] = {}
            for i in range(len(line)):
                dictionary[field_id][file_header[i]] = line[i]

print(nodes["1"])
print(names["1"])
