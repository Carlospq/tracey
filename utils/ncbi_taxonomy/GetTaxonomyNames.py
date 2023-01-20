from apps.home.models import *
with open('utils/ncbi_taxonomy/TRACEY_NCBItaxonomyIDs.txt', 'w') as of:
     for t in Taxonomies.objects.all():
         of.write(str(t.ncbi_taxonomy_id)+"\n")
