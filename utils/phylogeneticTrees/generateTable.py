#python manage.py shell < utils/phylogeneticTrees/generateTable.py
import pandas as pd
from apps.home.models import *

def get_parents(model, instance, instance_id, instance_parent_id, parents=[]):
    if getattr(instance, instance_id) != getattr(instance, instance_parent_id) and getattr(instance, instance_parent_id) != -1: # if instance is not root...
        parent = model.objects.get( **{ instance_id: getattr(instance, instance_parent_id) } )
        parents.append( [getattr(instance, 'taxonomyrank'), getattr(instance, 'scientificname'), getattr(instance, instance_id)] )
        get_parents(model, parent, instance_id, instance_parent_id, parents=parents)
    else:
        parents.append( [getattr(instance, 'taxonomyrank'), getattr(instance, 'scientificname'), getattr(instance, instance_id)] )
        return parents
    return parents

def generate_taxonomy_tables():
    table_dict = {}
    ranks = ['species group', 'species subgroup', 'cohort', 'family', 'tribe', 'class', 'biotype', 'genotype', 'section', 'order', 'superorder', 'superphylum', 'pathogroup', 'subphylum', 'parvorder', 'subfamily', 'species', 'isolate', 'infraorder', 'subkingdom', 'forma', 'phylum', 'strain', 'superkingdom', 'suborder', 'kingdom', 'infraclass', 'superclass', 'superfamily', 'subtribe', 'subcohort', 'forma specialis', 'serogroup', 'subclass', 'varietas', 'series', 'genus', 'serotype', 'subgenus', 'subspecies']

    for t in Taxonomies.objects.all():
        table_dict[t.ncbi_taxonomy_id] = []
        try:
            parent_taxonomy = Taxonomies.objects.get(taxonomy_id=t.taxonomyparent_id)
            parents = get_parents(Taxonomies, t, 'taxonomy_id', 'taxonomyparent_id', parents=[])
        except:
            parents = []
        table_dict[t.ncbi_taxonomy_id].append(t.taxonomy_id)
        for r in ranks:
            name = '-'
            for x in parents:
                if x[0] == r:
                    name = x[1]
            table_dict[t.ncbi_taxonomy_id].append(name)

    df = pd.DataFrame.from_dict(table_dict, orient='index').reset_index()
    df.columns = ['ncbi_id', 'tracey_id'] + ranks

    # Save taxonomies without tracey_id column
    only_ncbi = df.loc[:, df.columns != 'tracey_id']
    only_ncbi.to_csv('utils/phylogeneticTrees/taxonomies.csv', index=False)

    # Save taxonomies with tracey_id column and ncbi_id column
    df.to_csv('utils/phylogeneticTrees/ncbi_taxonomies.csv', index=False)


# Run code when run as script (python manage.py shell < utils/phylogeneticTrees/generateTable.py)
if __name__ == "django.core.management.commands.shell":
    generate_taxonomy_tables()
