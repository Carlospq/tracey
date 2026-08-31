# import Bio, Bio.PDB
# from Bio.SeqUtils import seq1
# from Bio.PDB.alphafold_db import *
from Bio.PDB import alphafold_db

from utils.ncbi_taxonomy.TaxonomyUpdater import *
from utils.traceySequenceUpdater.traceySequencesUpdater import *

ncbi = read_ncbi_files('utils/ncbi_taxonomy/taxdmp/')

# Run code when run as script
if __name__ == "django.core.management.commands.shell":

	alpha_file = 'path/to/file'
	alpha_data = [line.strip().split('\t') for line in open(alpha_file, 'r')]

	for protein in alpha_data:

		alpha_id = protein[0] #AF-A0A0L7KTD5-F1-v4 or AF-Q16623-F1 (human syx18)
		uniprot_id = protein[1] #A0A0L7KTD5 or Q16623
		#ncbi_id = protein[2]

		# structure = [structure for structure in get_structural_models_for(uniprot_id)][0]
		# chains_sequences = {chain.id: seq1(''.join(residue.resname for residue in chain)) for chain in structure.get_chains()}

		# Get metadata from alphafold_db - assuming it only has one prediction
		# pred = [x for x in alphafold_db.get_predictions('A0A0L7KTD5')][0]
		metadata = dict([x for x in alphafold_db.get_predictions(uniprot_id)][0].items())

		organism_taxid = metadata['taxId']
		prot_desc = metadata['uniprotDescription']
		gene = metadata['gene']
		dbxref = metadata['uniprotAccession']
		sourcedatabase = 'Uniprot'
		sequence = metadata['uniprotSequence']

		# Extract metadata from PDB
		# metadata = structure.__dict__
		# organism_scientific = metadata['header']['source']['1']['organism_scientific']
		# organism_taxid = metadata['header']['source']['1']['organism_taxid']

		# Generate taxonomy if not in tracey
		taxonomy = create_ncbi_taxonomy(organism_taxid, ncbi, report_file='')

		# Get sequence - assuming it only has one chain
		# chain = [chain for chain in structure.get_chains()][0]
		# chain_sequence = ''.join(residue.resname for residue in chain)


		# Transform uniprot ID to ncbi ID with Unipressed
		from unipressed import IdMappingClient

		request = IdMappingClient.submit(source="UniProtKB_AC-ID",
										 dest="RefSeq_Protein",
										 ids={dbxref})
		while True:
			if request.get_status() == "RUNNING":
				continue
			elif request.get_status() == "FINISHED":
				ncbi_ids = list(request.each_result())
				break
			# elif request.get_status().startswith("Unknown response returned by UniProt"):
			else:
				print(request.get_status())
				ncbi_ids = []
				break

		if not ncbi_ids:
			continue
		else:
			for ncbi_id in [x['to'] for x in ncbi_ids]:
				print(ncbi_id)
				if not any(Sequences.objects.filter( Q(foreignannotation__icontains=ncbi_id) | Q(dbxref=ncbi_id)) ):
					print("Adding sequence to database")
					esummary_output, esummary_error = esummary(ncbi_id)
					efetch_output, efetch_error = efetch(ncbi_id)
					newSequenceEntryFromEfetch(esummary_output, efetch_output, seqId=None, updateLog=None)




