import requests, io, subprocess, sys, re
from bs4 import BeautifulSoup

from apps.home.models import *
taxa = 'superkingdom'
##########################################################################################
def get_parents(ncbi_taxonomy_id, tree=[]):
    t = Taxonomies.objects.filter(ncbi_taxonomy_id=ncbi_taxonomy_id)[0]
    tree.append([t.taxonomyrank, t.scientificname])
    if t.scientificname != 'root':
        t_parent = Taxonomies.objects.get(taxonomy_id=t.taxonomyparent_id)
        get_parents(t_parent.ncbi_taxonomy_id, tree)
    return tree
##########################################################################################

def update_tracey_tree(taxa = taxa):
    with open('utils/ncbi_taxonomy/TRACEY_phylogeneticTree.newick', 'w') as f:
        f.write("In progress")

    print("Getting TRACEY taxonomies...")
    # Get Taxonomy_ids from TRACEY
    taxonomy_string = ''
    for t in Taxonomies.objects.all():
        taxonomy_string = taxonomy_string+str(t.ncbi_taxonomy_id)+"\n"
    f = io.StringIO(taxonomy_string)

    print("Comparing TRACEY ids with NCBI ids...")
    # file_ob = {'fl': open('utils/ncbi_taxonomy/TRACEY_NCBItaxonomyIDs.txt', 'rb')}
    # Create an inMemory file with TRACEY ids and send request to NCBI to obtain status of IDs
    file_ob = {'fl': f}
    data = {'button': 'Show on screen'} #'Save in file'
    try:
        response = requests.post('https://www.ncbi.nlm.nih.gov/Taxonomy/TaxIdentifier/tax_identifier.cgi', files=file_ob, data=data, timeout=60)
    except requests.exceptions.ReadTimeout:
        return "No response from NCBI server. Try again."
    if not response.content:
        return "Bad response from NCBI server. Try again."
    soup = BeautifulSoup(response.content, 'html.parser')

    # Clean scientific names of species obtained from NCBI
    print("cleanning scientific names...")
    replacement = [":", "-", "'", "*", "+", "#", "(", ")", ".", ",", "=", "/", ";", "\t"]
    h2 = soup.find_all('h2')
    tax_ids = {}
    for tag_ in h2:
        trTags = tag_.find_all("tr")
        if not trTags: continue
        for tag in trTags:
            tdTags = tag.find_all("td")
            if len(tdTags) < 3: continue
            if tdTags[1].text == "taxid": continue
            tdTag_id = [tdTags[1].text if tdTags[0].text == '1' else tdTags[2].text][0]
            new_tag = tdTags[3].text
            for r in replacement:
                new_tag = new_tag.replace(r, "")

            tax_phylo = get_parents(int(tdTag_id), tree=[])
            tax_group = 'Unclassified'
            for x,y in zip([x[0]for x in tax_phylo], [x[1]for x in tax_phylo]):
                if x == taxa:
                    tax_group = y
            if tax_group == 'Unclassified': continue
            tax_ids[tdTag_id] = new_tag+"|"+tax_group

    active_ids = list(tax_ids.keys())

    print('Generating tree...')
    # Generate tree from active TRACEY ids
    bashCommand = ['/home/cpulidoq/.cargo/bin/fastax', 'tree', '-n', '-f', '"(%taxid)"'] + active_ids
    runout = subprocess.run(bashCommand, capture_output=True)
    while runout.stderr:
        stderr = runout.stderr.decode("utf-8").replace('fastax: No such ID: ', "").strip()
        for idx in stderr.split():
            active_ids.remove(idx)
        bashCommand = ['/home/cpulidoq/.cargo/bin/fastax', 'tree', '-n', '-f', '"(%taxid)"'] + active_ids
        runout = subprocess.run(bashCommand, capture_output=True)
    tree = str(runout.stdout.decode("utf-8")).strip()

    # Find all NCBI_IDs in the newick tree
    matches = re.finditer('\d+', tree)
    ranges = [ [match.start(), match.end()] for match in matches]
    ranges.sort(key=lambda k: (k[0], -k[1]), reverse=True)

    # Replace found NCBI_IDs with its scientific_name
    c=0
    for r in ranges:
        c += 1
        start = r[0]
        end = r[1]
        tax_id = tree[start:end]
        try:
            tax_name = tax_ids[tax_id]
        except:
            tax_name = tax_id+"|outer"

        tree = tree[:start] + tax_name + tree[end:]

    with open('utils/ncbi_taxonomy/TRACEY_phylogeneticTree.newick', 'w') as fo:
        fo.write(str(tree))

    # Plotting Tree with R script
    print('Plotting Tree...')
    bashCommand = ['Rscript', 'utils/ncbi_taxonomy/plotPhyloTree.R']
    subprocess.run(bashCommand)

    return "\nUpdate completed."

if __name__ == "django.core.management.commands.shell":
    print("Updating TRACEY tree...")
    outcome = update_tracey_tree()
    print(outcome)
