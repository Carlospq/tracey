import sys, re

f_tree = sys.argv[1]
f_names = sys.argv[2]

# Read tree file newick ( it is all in 1 line)
with open(f_tree, 'r') as fh:
    for line in fh:
        tree_line = line

# Generate dictionary with NCBI_tax_id (key) - scientific_name (value)
id_name = {}
with open(f_names, 'r') as fh:
    for line in fh:
        tax_id, tax_name = line.strip().split("\t")
        id_name[tax_id] = tax_name

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
        tax_name = tax_id

    tree_line = tree_line[:start] + tax_name + tree_line[end:]

print(tree_line)
