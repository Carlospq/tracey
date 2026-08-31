##############################################################################################################################
#### IMPORTS ####
import os, re, sys, django
import subprocess
import xmltodict
import pyhmmer

from collections import Counter

from datetime import date, datetime
from collections import Counter
from Bio import Align

from apps.home.models import *
from django.db.models import Q

today = date.today()

##############################################################################################################################
#### FUNCTIONS ####
def get_parents_stats(model, instance, instance_id, instance_parent_id, parents=[], lists=True):
	if getattr(instance, instance_id) != getattr(instance, instance_parent_id) and getattr(instance, instance_parent_id) != -1: # if instance is not root...
		if lists:
			parents.append( [getattr(instance, 'taxonomyrank'), getattr(instance, 'scientificname'), getattr(instance, instance_id)] )
		else:
			parents.append( getattr(instance, 'scientificname') )
		try:
			parent = model.objects.get(**{instance_id: getattr(instance, instance_parent_id)})
			get_parents_stats(model, parent, instance_id, instance_parent_id, parents=parents)
		except model.DoesNotExist:
			pass
	else:
		if lists:
			parents.append( [getattr(instance, 'taxonomyrank'), getattr(instance, 'scientificname'), getattr(instance, instance_id)] )
		else:
			parents.append( getattr(instance, 'scientificname') )
		return parents
	return parents

def tax_to_dict(taxonomy):
	taxData_ = get_parents_stats(Taxonomies, taxonomy, 'taxonomy_id', 'taxonomyparent_id', [], lists=True)
	taxData = {x[0]: x[1] for x in taxData_ if x[0] in ["superkingdom", "kingdom", "phylum", "species"]}
	taxData = {(key):(taxData[key] if key in taxData else 'Unknown') for key in ["superkingdom", "kingdom", "phylum", "species", "sequences"]}
	# taxData["sequences"] = len([seq for seq in taxonomy.sequences_set.all() if seq.sequencestatus == 'live' and any([m for m in seq.motifs_set.all()])])
	return taxData

##############################################################################################################################

#### TAXONOMY STATS
def get_taxonomy_stats(file='utils/stats/taxonomyData.tsv'):
	"""
	Get statistics about the taxonomy.
	# Taxonomiranks: 'no rank', 'superkingdom', 'kingdom', 'superphylum', 'phylum', 'subphylum', 'superclass', 'class', 'subclass', 'superorder', 'order', 'suborder', 'infraorder', 'superfamily', 'family', 'genus', 'subgenus', 'species', 'subspecies', 'strain', 'varietas', 'species subgroup', 'forma', 'tribe'
	"""
	counters = Counter([x.taxonomyrank for x in Taxonomies.objects.all()])
	kingdoms = list(set([x.scientificname for x in Taxonomies.objects.filter(taxonomyrank="kingdom")]))
	phylums = list(set([x.scientificname for x in Taxonomies.objects.filter(taxonomyrank="phylum")]))
	print(f'{counters["species"]} species split in {len(kingdoms)} kingdoms, {len(phylums)} phylums')

	# datasources = ['Silkworm Genome Database: SilkDB', 'Social Amoebas Comparative Genome Browser', 'Assembled by hand', 'Ensemble', 'G. tigrina Transcriptome', 'hand', 'DOE Joint Genome Institute', 'OIST Molecular Genetics Unit',
	# 			   'Genoscope: Centre National de Sequencage', 'Japanese Lamprey Genome Project', 'Oxytricha Genome Database', 'NCBI_refseq', 'Eukaryotic Pathogens Database Resources', 'Cryptosporidium Genomics Resource', 'The Pleurobrachia Genome',
	# 			   'Hypsibius dujardini genome project', 'nematodes.org', 'Broad Institute', 'Schmidtea mediterranea Genome Database', 'Sanger Institute', 'unknown', 'NCBI_nr', 'Galdieria sulphuraria Genome Project (Michigan State University)',
	# 			   'Symbiodinium kawagutii', 'Private communication', 'OIST Marine Genomics Unit', 'Shanghai Center fo Bioinformation Thecnology', 'Reef Genomics', 'Choano transcriptomes', 'Fungal Genomics Project', 'Cyanophora Genomics Project',
	# 			   'Mnemiopsis Genome Project', 'Comparative genomics platform for basal metazoa', 'TrEMBL', 'Metazome', 'MacGenome', 'NCBI_est', 'J. Craig Venter Institute', 'Chinese Lancelet Genome Sequencing project', 'EchinoBase',
	# 			   'Cyanidioschyzon merolae Genome Project', 'Protist Est Program']

	with open(file, 'w') as fo:
		fo.write("\t".join(['superkingdom', 'kingdom', 'phylum', 'species', 'sequences', 'active_sequences', 'active_motif', 'active_nomotif', 'inactive_motif', 'inactive_nomotif']) + "\n")

	# Write stats to file
	with open(file, 'a') as fo:
		for tax in Taxonomies.objects.filter():
			if not any(tax.sequences_set.all()): continue # Next if no sequences for this taxonomy
			taxDict = {}
			taxDict = tax_to_dict(tax)
			sequences = len(tax.sequences_set.all())
			active_sequences = len(tax.sequences_set.filter(sequencestatus='live'))
			active_motif = len([seq for seq in tax.sequences_set.filter(sequencestatus='live') if seq.motifs_set.all()])
			active_nomotif = active_sequences - active_motif
			inactive_motif = len([seq for seq in tax.sequences_set.exclude(sequencestatus='live') if seq.motifs_set.all()])
			inactive_nomotif = sequences - active_sequences - inactive_motif
			# db_counts = [str(len(tax.sequences_set.filter(sourcedatabase=db))) for db in datasources]
			fo.write("\t".join([taxDict['superkingdom'], taxDict['kingdom'], taxDict['phylum'], taxDict['species'],
								str(sequences), str(active_sequences),
								str(active_motif), str(active_nomotif),
								str(inactive_motif), str(inactive_nomotif)]) + "\n")


######
get_taxonomy_stats()


try:
	with open("utils/stats/sequencesData.tsv", 'r') as fi:
		lines = fi.readlines()
		shortnames = [line.split("\t")[0] for line in lines[1:]]
except FileNotFoundError:
	shortnames = []

with open("utils/stats/sequencesData.tsv", 'w') as fo:
	fo.write("\t".join(['shortname', 'superkingdom', 'kingdom', 'phylum', 'species', 'motifs', 'active_motifs', 'source_db', 'sequence_status']) + "\n")
	for sequence in Sequences.objects.all():
		if sequence.sequenceshortname in shortnames: continue
		shortname = sequence.sequenceshortname
		taxonomy = sequence.taxonomy
		source_db = sequence.sourcedatabase
		taxDict = tax_to_dict(taxonomy)
		motifs = len(sequence.motifs_set.all())
		active_motifs = len([m for m in sequence.motifs_set.all() if m.active])
		fo.write("\t".join([shortname, taxDict['superkingdom'], taxDict['kingdom'], taxDict['phylum'], taxDict['species'], str(motifs), str(active_motifs), source_db, sequence.sequencestatus]) + "\n")

with open("utils/stats/motifsData.tsv", 'w') as fo:
	fo.write("\t".join(['superkingdom', 'kingdom', 'phylum', 'species', 'motifName', 'motifActive', 'sequenceActive']) + "\n")
	for motif in Motifs.objects.all():
		taxonomy = motif.sequence.taxonomy
		taxDict = tax_to_dict(taxonomy)
		sequencestatus = str(1) if motif.sequence.sequencestatus == 'live' else str(0)
		fo.write("\t".join([taxDict['superkingdom'], taxDict['kingdom'], taxDict['phylum'], taxDict['species'], motif.motifname, str(motif.active), sequencestatus]) + "\n")




# get sequences status
# echo "select * from sequences" | mysql tracey -B -utracey -ptracey > utils/stats/sequences_query.tsv
# echo "select * from motifs" | mysql tracey -B -utracey -ptracey > utils/stats/motifs_query.tsv

# tr -d $'\r' < utils/stats/sequences_query.tsv | sed 's/\\n//g' > utils/stats/sequences_query_copy.tsv; mv utils/stats/sequences_query_copy.tsv utils/stats/sequences_query.tsv
# tr -d $'\r' < utils/stats/motifs_query.tsv | sed 's/\\n//g' > utils/stats/motifs_query_copy.tsv; mv utils/stats/motifs_query_copy.tsv utils/stats/motifs_query.tsv

# sed -i 's/<.*<eValue>\(.*\)<\/eValue.*>/\1/g' utils/stats/motifs_query.tsv
# sed -i 's/\\n//g' utils/stats/motifs_query.tsv































