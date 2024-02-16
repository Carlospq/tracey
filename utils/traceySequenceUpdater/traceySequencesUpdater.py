##############################################################################################################################
#### IMPORTS ####
import os, sys
from utils.modules.traceySequencesUpdater import *
from apps.home.models import *
from datetime import date

# Log file: will include all sequences that failed to be updated and need a manual check
today = date.today()
if os.path.isfile("./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log"%today.strftime("%Y.%m.%d")):
	sys.exit("ERROR: Log file already exists. Exiting...")
else:
	logFile = open("./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % today.strftime("%Y.%m.%d"), "a")
	logFile.write("traceyID\tncbiID\tcomment\n")
##############################################################################################################################
#### CODE ####

# Run code when run as script
if __name__ == "django.core.management.commands.shell":

	## NOTE: So far this script is adapted only for SNARE sequences

	# Collect all sequences in tracey with SNARE/Habc motifs
	snareMotifsIds = set([m.sequence_id for m in Motifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])
	snareVerifymotifsIds = set([m.sequence_id for m in Verifymotifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])

	snareSeqs = Sequences.objects.filter(sequence_id__in=list(snareMotifsIds | snareVerifymotifsIds))

	######### UPDATE SEQUENCES WITH NCBI SOURCE #########
	# This first section collects all the sequences from the database that are sourced from NCBI
	# Then fetch data from the required database from NCBI and compares it with the sequence data in tracey
	# If needed, sequence will be updated with the new information

	snareSeqsNCBI = snareSeqs.filter(sourcedatabase__in = ['NCBI_est', 'NCBI_nr', 'NCBI_refseq'])	#83304 sequences

	for seq in snareSeqsNCBI:
		# If not foreignannotation: write sequence ID into log file and continue
		if seq.foreignannotation == "none":
			logFile.write("%s\t%s\tERROR with seq tracey_id %s: Foreignannotation missing\n"%(seq.sequence_id, '', seq.sequence_id))
			continue

		# possibles IDs sources: ['gi', 'gb', 'emb', 'ref', 'dbj', 'pir', 'prf', 'sp', 'pdb', 'tpe', 'none', 'tpg']
		ncbi_ids = get_ncbi_ids(seq)
		idx = [ncbi_ids["gi"] if "gi" in ncbi_ids else [ncbi_ids[x] for x in ncbi_ids][0]][0]

		# Get summary data for idx
		summary_output, summary_error = esummary(idx)
		if summary_error:
			# Print error and write sequence ID into log file
			logFile.write("%s\t%s\t%s\n" % (seq.sequence_id, idx, summary_error))
			continue

		# If "Status" in summary_output (means sequence is deleted/supressed/replaced/...)
		if "Status" in summary_output:
			if summary_output["Status"] == "replaced":
				replaced_by = summary_output["ReplacedBy"]
				logFile.write('%s\t%s\tSequence replaced by NCBI ID %s\n'%(seq.sequence_id, idx, replaced_by))
				# Check if replaced_by is in TRACEY; otherwise create a new sequence entry with data from replaced_by
				# CODE ...

				# Fetch data for replaced_by Id
				fetch_output, fetch_error = efetch(replaced_by)
			else:
				# If sequence is deleted/supressed/... Update TRACEY sequence and write to log file
				logFile.write('%s\t%s\tsequence_status changed to %s\n'%(seq.sequence_id, idx, summary_output["Status"]))
		else:
			# If no change needed write to log file OK
			logFile.write('%s\t%s\t%s\n'%(seq.sequence_id, idx, "OK"))

	logFile.close()





