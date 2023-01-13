### IS RECOMENDED TO UPDATE TRACEY TAXONOMY (TaxonomyUpdater.py) BEFORE GENERATING TREE TO GET A FULL UPDATED TREE

# Get ncbi taxonomy ids from TRACEY (CODE for "python manager.py shell")
from apps.home.models import *
with open('TRACEY_NCBItaxonomyIDs.txt', 'w') as of:
     for t in Taxonomies.objects.all():
         of.write(str(t.ncbi_taxonomy_id)+"\n")

# Check for NCBI taxonomiees status and filter
> upload previous generated file into: https://www.ncbi.nlm.nih.gov/Taxonomy/TaxIdentifier/tax_identifier.cgi
> parse downloaded file ('tax_report.txt')
awk -F"|" '$1==1{print $2, $4}' tax_report.txt > TRACEY_active_NCBItaxonomyIDs_and_names.txt

# Clean names of forbiden characters for newick format ( "(", ")", ":", ";", ... )
sed -i 's/://g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/-/_/g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i "s/'//g" TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/*//g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/+//g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/#//g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/(/[/g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\.//g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/=//g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/)/]/g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\///g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/;//g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\t \t/:/g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\t//g' TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/:/\t/g' TRACEY_active_NCBItaxonomyIDs_and_names.txt

# Get active NCBI ids
awk '{print $1}' TRACEY_active_NCBItaxonomyIDs_and_names.txt > TRACEY_active_NCBItaxonomyIDs.txt
tr '\n' ' ' < TRACEY_active_NCBItaxonomyIDs.txt > tmp.txt; mv tmp.txt  TRACEY_active_NCBItaxonomyIDs.txt

# build newick tree with taxids
> You might need to add path to fastax executable
PATH=$PATH:/home/cpulidoq/.cargo/bin/
fastax tree -n -f "(%taxid)" [copy-paste all taxonomy ids in TRACEY_active_NCBItaxonomyIDs.txt from previous step] > TRACEY_taxid.newick

# SED taxids for curated scientific names
python change_taxid_for_names.py TRACEY_taxid.newick TRACEY_active_NCBItaxonomyIDs_and_names.txt > TRACEY_names.newick

# Delete intermediate files (optional)
rm tax_report.txt TRACEY_active_NCBItaxonomyIDs_and_names.txt TRACEY_active_NCBItaxonomyIDs.txt TRACEY_taxid.newick





# OLD code to replace NCBI ids #
# cp TRACEY_taxid.newick TRACEY_names.newick
# while IFS= read -r line; do v1=$(echo $line | awk '{print $1}'); v2=$(echo $line | awk '{$1=""; print $0}'); echo $v1, $v2; sed -i 's/\b'"$v1"'\b/'"$v2"'/g' TRACEY_names.newick; done < TRACEY_active_NCBItaxonomyIDs_and_names.txt >> error.txt 2>>error.txt

