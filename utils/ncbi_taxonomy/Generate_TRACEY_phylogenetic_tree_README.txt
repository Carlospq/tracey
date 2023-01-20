### IS RECOMENDED TO UPDATE TRACEY TAXONOMY (TaxonomyUpdater.py) BEFORE GENERATING TREE TO GET A FULL UPDATED TREE
### fastax is needed to build the tree. Download and prepare files as describerd here: https://github.com/Picani/fastax

# Simplify path for commands
tpath='utils/ncbi_taxonomy'

# Get ncbi taxonomy ids from TRACEY (CODE for "python manager.py shell")
# from apps.home.models import *
# with open('TRACEY_NCBItaxonomyIDs.txt', 'w') as of:
#      for t in Taxonomies.objects.all():
#          of.write(str(t.ncbi_taxonomy_id)+"\n")
python manage.py shell < $tpath/GetTaxonomyNames.py

# Check for NCBI taxonomiees status and filter
> upload previous generated file into: https://www.ncbi.nlm.nih.gov/Taxonomy/TaxIdentifier/tax_identifier.cgi
> download file and save it in utils/ncbi_taxonomy/
> parse downloaded file ('tax_report.txt')
# with taxname
awk -F"|" '$1==1{print $2, $4}' $tpath/tax_report.txt > $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt

# Clean names of forbiden characters for newick format ( "(", ")", ":", ";", ... )
sed -i 's/://g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/-/_/g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i "s/'//g" $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/*//g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/+//g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/#//g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/(/[/g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\.//g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/=//g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/)/]/g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\///g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/;//g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\t \t/:/g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/\t//g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt
sed -i 's/:/\t/g' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt

# Get active NCBI ids
awk '{print $1}' $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt > $tpath/TRACEY_active_NCBItaxonomyIDs.txt
tr '\n' ' ' < $tpath/TRACEY_active_NCBItaxonomyIDs.txt > $tpath/tmp.txt; mv $tpath/tmp.txt  $tpath/TRACEY_active_NCBItaxonomyIDs.txt

# build newick tree with taxids
> You might need to add path to fastax executable
PATH=$PATH:/home/cpulidoq/.cargo/bin/
fastax tree -n -f "(%taxid)" [copy-paste all taxonomy ids in TRACEY_active_NCBItaxonomyIDs.txt from previous step] > $tpath/TRACEY_taxid.newick

# SED taxids for curated scientific names
python manage.py shell < $tpath/change_taxid_for_names.py > $tpath/TRACEY_names.newick

# Delete intermediate files (optional)
rm $tpath/tax_report.txt $tpath/TRACEY_active_NCBItaxonomyIDs_and_names.txt $tpath/TRACEY_active_NCBItaxonomyIDs.txt $tpath/TRACEY_taxid.newick $tpath/TRACEY_NCBItaxonomyIDs.txt