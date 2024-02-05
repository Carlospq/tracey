##############################################################################################################################
#### IMPORTS ####
import os, sys
import subprocess
import xmltodict
from apps.home.models import *
from datetime import date

# Log file: will include all sequences that failed to be uupdated and need a manual check
today = date.today()
logFile = open("./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log"%today.strftime("%Y.%m.%d"), "a")
if os.path.isfile("./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log"%today.strftime("%Y.%m.%d")):
	sys.exit("ERROR: Log file already exists. Exiting...")
##############################################################################################################################
#### FUNCTIONS ####
def get_ncbi_ids(seq):
	fids = seq.foreignannotation.split("|")
	ncbiDictionary = {}
	if len(fids) == 1:
		ncbiDictionary["ncbi_id"] = fids[0].split()[0]
	else:
		for i in range(len(fids)):
			if len(fids[i]) < 4 and fids[i]:
				ncbiDictionary[fids[i]] = fids[i + 1]
	return ncbiDictionary


def esummary(idx, db="protein"):
	# Fetch data from NCBI using esummary
	# db: database to fetch data from
	# id: sequence id
	# Returns: xml data
	# Example: esummary("protein", "NP_001191")
	cmd = "esummary -db %s -id %s"%(db, idx)
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	if b'ERROR' in output.upper() or b'Otherdb' in output:
		if b'Invalid db name specified' in output:
			output, error = "", "Invalid db name specified"
		elif b'gi is not found' in output:
			output, error = "", "gi is not found"
		elif b'Otherdb' in output:
			warning = xmltodict.parse(output)['DocumentSummarySet']['Warning']
			output, error = "", "ID %s not found in db '%s', but found in db '%s' with id %s" % (idx, db, warning['Otherdb']['@db'], warning['Otherdb']['@uid'])
		else:
			output, error = "", "Invalid ID format"
	else:
		output = xmltodict.parse(output)['DocumentSummarySet']['DocumentSummary']
	return [output, error]

def efetch(idx, db="sequences"):
	cmd = 'efetch -db %s -id %s -format gb -mode xml' % (db, idx)
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	output = xmltodict.parse(output)['GBSet']['GBSeq']
	return [output, error]
##############################################################################################################################
#### CODE ####

## NOTE: So far this script is adapted only for SNARE sequences

# All sequences with SNARE/Habc motifs
snareMotifsIds = set([m.sequence_id for m in Motifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])
snareVerifymotifsIds = set([m.sequence_id for m in Verifymotifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])

snareSeqs = Sequences.objects.filter(sequence_id__in=list(snareMotifsIds | snareVerifymotifsIds))

######### UPDATE NCBI SEQUENCES #########
# This first section collects all the sequences from the database that are sourced from NCBI
# Then fetch data from the required database from NCBI and compares it with the sequence data
# If needed, sequence will be updated with the new information

snareSeqsNCBI = snareSeqs.filter(sourcedatabase__in = ['NCBI_est', 'NCBI_nr', 'NCBI_refseq'])	#83304 sequences

for seq in snareSeqsNCBI:
	# If not foreignannotation: write sequence ID into log file and continue
	if seq.foreignannotation == "none":
		logFile.write("ERROR with seq ID %s: Foreignannotation missing\n"%(seq.sequence_id))
		continue

	# possibles IDs sources: ['gi', 'gb', 'emb', 'ref', 'dbj', 'pir', 'prf', 'sp', 'pdb', 'tpe', 'none', 'tpg']
	ncbi_ids = get_ncbi_ids(seq)
	idx = [ncbi_ids["gi"] if "gi" in ncbi_ids else [ncbi_ids[x] for x in ncbi_ids][0]][0]

	# Get summary data for idx
	summary_output, summary_error = esummary(idx)
	if summary_error:
		# Print error and write sequence ID into log file
		print(summary_error)

	# If "Status" in summary_output (means sequence is deleted/supressed/replaced/...)
	if "Status" in summary_output:
		if summary_output["Status"] == "replaced":
			print("Id=%s, %s" % (idx, summary_output["Status"]))
			# Check if replaced_by is in TRACEY; otherwise create a new sequence entry with data from replaced_by

			# Check for replaced_by in TRACEY
			# CODE ...

			# Fetch data for replaced_by Id
			replaced_by = summary_output["ReplacedBy"]
			fetch_output, fetch_error = efetch(replaced_by)
			break
		else:
			# If sequence is deleted/supressed/... Update TRACEY sequence and write to log file
			print("Id=%s, %s" % (idx, summary_output["Status"]))
	else:
		# If no change needed write to log file
		print("Id=%s, No status" % (idx))

logFile.close()

