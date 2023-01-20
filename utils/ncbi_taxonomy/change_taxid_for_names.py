import sys, re
from apps.home.models import *

def get_parents(ncbi_taxonomy_id, tree=[]):
    t = Taxonomies.objects.filter(ncbi_taxonomy_id=ncbi_taxonomy_id)[0]
    tree.append([t.taxonomyrank, t.scientificname])
    if t.scientificname != 'root':
        t_parent = Taxonomies.objects.get(taxonomy_id=t.taxonomyparent_id)
        get_parents(t_parent.ncbi_taxonomy_id, tree)
    return tree



f_tree = 'utils/ncbi_taxonomy/TRACEY_taxid.newick'
f_names = 'utils/ncbi_taxonomy/TRACEY_active_NCBItaxonomyIDs_and_names.txt'
taxa = 'kingdom'

# Read tree file newick ( it is all in 1 line)
with open(f_tree, 'r') as fh:
    for line in fh:
        tree_line = line

# Generate dictionary with NCBI_tax_id (key) - scientific_name (value)
id_name = {}
with open(f_names, 'r') as fh:
    for line in fh:
        tax_id, tax_name = line.strip().split("\t")
        tax_phylo = get_parents(int(tax_id), tree=[])
        tax_group = 'outer'
        for x,y in zip([x[0]for x in tax_phylo], [x[1]for x in tax_phylo]):
            if x == taxa:
                tax_group = y
        # id_name[tax_id] = tax_name+"|"+tax_group
        id_name[tax_id] = tax_id+"|"+tax_group


# Find all NCBI_IDs in the newick tree
matches = re.finditer('\d+', tree_line)
ranges = [ [match.start(), match.end()] for match in matches]
ranges.sort(key=lambda k: (k[0], -k[1]), reverse=True)

# Replace found NCBI_IDs with its scientific_name
c=0
for r in ranges:
    c += 1
    start = r[0]
    end = r[1]
    tax_id = tree_line[start:end]
    try:
        tax_name = id_name[tax_id]
    except:
        tax_name = tax_id+"|outer"

    tree_line = tree_line[:start] + tax_name + tree_line[end:]

print(tree_line)
