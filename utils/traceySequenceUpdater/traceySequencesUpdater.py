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
	logFile.close()

##############################################################################################################################
#### CODE ####

# Run code when run as script
if __name__ == "django.core.management.commands.shell":

	## NOTE: So far this script is adapted only for SNARE sequences

	# Make update stop if logfile date is to recent [??]

	######### UPDATE SEQUENCES WITH NCBI SOURCE #########
	# This first section collects all the sequences from the database that are sourced from NCBI
	# Then fetch data from the required database from NCBI and compares it with the sequence data in tracey
	# If needed, sequence will be updated with the new information

	# Collect all sequences in tracey with SNARE/Habc motifs
	snareMotifsIds = set([m.sequence_id for m in Motifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])
	snareVerifymotifsIds = set([m.sequence_id for m in Verifymotifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])

	snareSeqs = Sequences.objects.filter(sequence_id__in=list(snareMotifsIds | snareVerifymotifsIds))

	# Check log files for last updates on each sequence [??]
	sequencesAnalysed = []

	snareSeqsNCBI = snareSeqs.filter(sourcedatabase__in=['NCBI_est', 'NCBI_nr', 'NCBI_refseq'])  # 83304 sequences
	for sequence in snareSeqsNCBI:

		# Skip sequence if already updated
		if sequence.sequence_id in sequencesAnalysed:
			continue

		logFile = open("./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % today.strftime("%Y.%m.%d"), "a")
		# If summary_error from NCBI: write sequence ID and error into log file and continue
		if sequence.foreignannotation == "none":
			comment = "ERROR with sequence tracey_id %s: Foreignannotation missing\n"%(sequence.sequence_id)
			writeLog(logFile, sequence.sequence_id, '', comment)
			continue

		ncbi_id = get_ncbi_id(sequence)
		if not ncbi_id:
			comment = "ERROR with sequence tracey_id %s: No NCBI ID found\n"%(sequence.sequence_id)
			writeLog(logFile, sequence.sequence_id, '', comment)
			continue

		# Get summary data for idx
		summary_output, summary_error = esummary(ncbi_id)

		# If summary_error from NCBI: write sequence ID and error into log file and continue
		if summary_error:
			writeLog(logFile, sequence.sequence_id, ncbi_id, summary_error)
			continue

		# Update sequence if needed and print log into logFile
		updateLog = sequenceUpdate(sequence, summary_output)
		for updateId in updateLog:
			sequencesAnalysed.append(updateId)
			writeLog(logFile, updateId, updateLog[updateId]['accessionVersion'], updateLog[updateId]['comment'])

		logFile.close()





