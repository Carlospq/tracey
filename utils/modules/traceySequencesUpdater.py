##############################################################################################################################
#### IMPORTS ####
import subprocess
import xmltodict
import re
from apps.home.models import *
from collections import Counter

##############################################################################################################################
#### FUNCTIONS ####
def writeLog(logFile, traceyID, ncbiID, comment):
	logFile.write("%s\t%s\t%s\n" % (traceyID, ncbiID, comment))


def get_ncbi_id(seq):
	# possibles IDs sources: ['gi', 'gb', 'emb', 'ref', 'dbj', 'pir', 'prf', 'sp', 'pdb', 'tpe', 'none', 'tpg']
	fids = seq.foreignannotation.split("|")
	if len(fids) == 1:
		idx = fids[0].split()[0]
		#ncbiDictionary["ncbi_id"] = fids[0].split()[0]
		if ";" in idx:
			ncbiIdx = None
		else:
			ncbiIdx = idx
	else:
		ncbiDictionary = {}
		for i in range(len(fids)):
			if len(fids[i]) < 4 and fids[i]:
				ncbiDictionary[fids[i]] = fids[i + 1]
		if "gi" in ncbiDictionary:
			ncbiIdx = ncbiDictionary["gi"]
		else:
			ncbiIdx = [ncbiDictionary[x] for x in ncbiDictionary][0]
	return ncbiIdx


def esummary(idx, db="protein"):
	# Fetch data from NCBI using esummary
	# db: database to fetch data from
	# id: sequence id
	# Returns: xml data
	# Example: esummary("protein", "NP_001191")
	if not idx:
		return ['', 'No idx']
	cmd = "esummary -db %s -id %s"%(db, idx)
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	if b'ERROR' in output.upper() or b'Otherdb' in output:
		if b'Invalid db name specified' in output:
			output, error = "", "Invalid db name"
		elif b'gi is not found' in output:
			output, error = "", "gi not found"
		elif b'Invalid uid syntaxin' in output:
			output, error = "", "Invalid uid syntaxin"
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


def getChildren(model, parent, parent_id, child_parent_id, childs=[], search_type='iexact'):
	variable_column = child_parent_id
	filter = variable_column + '__' + search_type
	cs = model.objects.none()
	for p in parent:
		if getattr(p, parent_id) == 4 and isinstance(p, Domaingroups):
			cs = cs.union(model.objects.filter( **{ variable_column+"__icontains" : ";4" }))
		else:
			cs = cs.union(model.objects.filter( **{ filter: getattr(p, parent_id) }))
	for c in cs:
		childs.append(c)
		if model.objects.filter( **{ filter: getattr(c, parent_id) }):
			getChildren(model, model.objects.filter(pk=c.pk), parent_id, child_parent_id, childs=childs)
	return(childs)


def getSpeciesTaxId(seq):
	t = seq.taxonomy
	while t.taxonomyrank != "species":
		t = Taxonomies.objects.get(taxonomy_id=t.taxonomyparent_id)
	children = getChildren(Taxonomies, [t], "taxonomy_id", "taxonomyparent_id", childs=[], search_type='iexact')
	return [t.taxonomy_id]+[t.taxonomy_id for t in children]


def getIdenticalSequences(sequence, summary_output):
	# Returns all sequences with exact same protein sequence belonging to the same taxonomy
	status = ['live' if not 'Status' in summary_output else summary_output['Status']][0]
	identicalSequences = {sequence.sequence_id: {'sequence': sequence,
												 'status': status,
												 'main': True,
												 'summary_output': summary_output}
						  }
	errorSequences = {}
	taxIds = getSpeciesTaxId(sequence)
	for seq in Sequences.objects.filter(sequence=sequence.sequence).filter(taxonomy_id__in=taxIds):
		if seq.sequence_id != sequence.sequence_id:
			ncbi_id = get_ncbi_id(seq)
			if not ncbi_id:
				errorSequences[seq.sequence_id] = {'sequence': seq,
												   'status': status,
												   'ncbi_id': '',
												   'main': False,
												   'error': 'Identical sequence to tracey ID %s but no ncbi_id found; Not updated' % sequence.sequence_id}
				continue
			new_summary_output, summary_error = esummary(ncbi_id)
			if summary_error:
				errorSequences[seq.sequence_id] = {'sequence': seq,
												   'status': status,
												   'ncbi_id': ncbi_id,
												   'main': False,
												   'error': summary_error}
				continue
			status = ['live' if not 'Status' in new_summary_output else new_summary_output['Status']][0]
			if new_summary_output:
				identicalSequences[seq.sequence_id] = {'sequence': seq,
													   'status': status,
													   'main': False,
													   'summary_output': new_summary_output}
	return identicalSequences, errorSequences


def selectMainFromIdenticalSequences(identicalSequences):
	# Check SourceDb. Give priority to refseq, then swiss_prot, then insd (International Nucleotide Sequence Database), then pir (Protein Information Resource), then prf (Protein Research Foundation)
	dbSoruces = ['refseq', 'swiss_prot', 'insd', 'pdb', 'pir', 'prf']
	nSourceDb = Counter([identicalSequences[idx]['summary_output']['SourceDb'] for idx in identicalSequences])
	mainSequence = {}
	secondarySequence = {}
	for source in dbSoruces:
		if nSourceDb[source] == 0: continue
		if nSourceDb[source] == 1:
			idx = [idx for idx in identicalSequences if identicalSequences[idx]['summary_output']['SourceDb'] == source][0]
			mainSequence = {idx: identicalSequences[idx]}
		if nSourceDb[source] > 1:
			# Choose main reference sequence
			# Assumes there is only 1 active identical proteins from same source for the same species/mainstrain
			sourceIdxs = [idx for idx in identicalSequences if identicalSequences[idx]['summary_output']['SourceDb'] == source]
			for idx in sourceIdxs:
				taxStatus = identicalSequences[idx]['sequence'].taxonomy.taxonomystatus
				if taxStatus == 'main reference':
					mainSequence = {idx: identicalSequences[idx]}
				else:
					# Return last sequence if no main reference
					secondarySequence = {idx: identicalSequences[idx]}
		if mainSequence:
			return mainSequence
	# Return initial sequence if not main in identicalSequences
	if not mainSequence:
		if secondarySequence:
			mainSequence = secondarySequence
		else:
			mainSequence = [{idx: identicalSequences[idx] for idx in identicalSequences if identicalSequences[idx]['main']}][0]
	return mainSequence


def countLive(identicalSequences):
	return sum([1 for seqId in identicalSequences if identicalSequences[seqId]['status'] == 'live'])


def regexForeignannotation(foreignannotation):
	# vam/vamp
	patterns = {'ykt': 'ykt[0-9]*',
				'vamp': 'vam.*?\W([0-9A-Z]*)|vesicle-associated membrane protein ([0-9]*)',
				'syx': 'sy.*?x.*?[-0-9A-Z]*',
				}

def sequenceUpdate(sequence, summary_output):

	# Initialize updateLog to keep track of all updates
	updateLog = {}

	# Check if identical sequence exist in TRACEY and collect NCBI data for them
	identicalSequences, errorSequences = getIdenticalSequences(sequence, summary_output)
	# If error while fetching identical sequences write to log file and continue
	if errorSequences:
		for errorSeqId in errorSequences:
			updateLog[errorSeqId] = {'accessionVersion': errorSequences[errorSeqId]['ncbi_id'],
									 'comment': errorSequences[errorSeqId]['error']}

	# Select main sequence in case of multiple identical sequences (if no identical then mainSequence = sequence)
	mainSequence = selectMainFromIdenticalSequences(identicalSequences)

	# Update all sequences in identicalSequences: mainSequence becomes "live", the rest become "ignore"
	for identicalSeqId in identicalSequences:

		identicalSeq = identicalSequences[identicalSeqId]
		identicalSeqSummaryOutput = identicalSeq['summary_output']
		seq = identicalSeq['sequence']

		accessionVersion = identicalSeqSummaryOutput['AccessionVersion']
		comment = ''

		# Update dbxref: gi to accession version
		if seq.dbxref != accessionVersion:
			sequence.dbxref = accessionVersion
			comment += 'dbxref updated to %s; ' % accessionVersion

		# If "Status" in summary_output (meaning sequence is deleted/suppressed/replaced/...)
		if "Status" in identicalSeqSummaryOutput:
			accessionVersion = identicalSeqSummaryOutput['AccessionVersion']
			# Status == replaced: update status if needed and check if replaced_by is in TRACEY
			if identicalSeqSummaryOutput["Status"] == "replaced":
				replaced_by = identicalSeqSummaryOutput["ReplacedBy"]
				comment += 'Sequence replaced by NCBI ID %s; ' % (replaced_by)

				if seq.sequencestatus not in ['replaced', 'replaced NCBI']:
					comment += 'Sequencestatus changed from %s to replaced NCBI; ' % (seq.sequencestatus)
					# sequence.sequencestatus = 'replaced NCBI'

				# if replaced_by not in TRACEY:
				if not any(Sequences.objects.filter(foreignannotation__icontains=replaced_by)):
					fetch_output, fetch_error = efetch(replaced_by)
					if fetch_error:
						comment += 'Error fetching NCBI ID %s; ' % (replaced_by)
					else:
						# Fetch data from ncbi for replaced_by and create new sequence entry in TRACEY
						# newEntrySequence = newSequenceEntryFromEfetch(fetch_output)
						# updateLog[newEntrySequence.sequence_id] = {'accessionVersion': fetch_output['GBSeq_accession-version'],
						updateLog[identicalSeqId+99999999] = {'accessionVersion': fetch_output['GBSeq_accession-version'],
																   'comment': 'New sequence entry created replacing TRACEY ID %s' % seq.sequence_id}

			# Else If sequence is deleted/suppressed/dead, Update TRACEY sequence and write to log file
			else:
				# Update sequence.sequencestatus if needed
				if seq.sequencestatus == identicalSeqSummaryOutput["Status"]:
					comment += "No changes needed. Sequencestatus already %s" % identicalSeqSummaryOutput["Status"]
				else:
					comment += "Sequencestatus changed from %s to %s" % (seq.sequencestatus, identicalSeqSummaryOutput["Status"])

		# If not "Status" in summary_output (meaning sequence is active in NCBI)
		else:
			if identicalSeqId in mainSequence:

				# Check shortname and update if necessary
				if "OLD" in seq.sequenceshortname.upper():
					oldMatch = re.search('\W*?[-|_]*?old', seq.sequenceshortname, re.IGNORECASE).group()
					seq.sequenceshortname.replace(oldMatch, '')
				elif not seq.sequenceshortname:
					# Make shortname from taxonomy shortname and SNARE group
					taxShortName = seq.taxonomy.taxonomyshortname

				if "pdb" in seq.foreignannotation or 'pdb' in identicalSequences[identicalSeqId]['summary_output']['Extra']:
					if not "pdb" in seq.foreignannotation:
						seq.foreignannotation = identicalSequences[identicalSeqId]['summary_output']['Extra'] + "| " + identicalSequences[identicalSeqId]['summary_output']['Title']
					if seq.sequencestatus != 'crystal structure':
						comment += "Sequencestatus updated from %s to Crystal structure" % seq.sequencestatus
					# seq.sequencestatus = 'crystal structure'
				elif seq.sequencestatus != 'live':
					comment += "Sequencestatus changed from %s to live" % seq.sequencestatus
					# seq.sequencestatus = 'live'
				else:
					comment += "No changes needed. Sequence status already live"
			else:
				if seq.sequencestatus == 'live':
					comment += "Sequencestatus updated from live to ignore"
					# seq.sequencestatus = 'ignore'
				else:
					comment += "No changes needed. Sequence status already ignore"
			updateLog[identicalSeqId] = {
				'accessionVersion': identicalSequences[identicalSeqId]['summary_output']['AccessionVersion'],
				'comment': comment
			}

		if identicalSeqId not in updateLog:
			updateLog[identicalSeqId] = {'accessionVersion': accessionVersion,
										 'comment': comment}
	return updateLog


##############################################################################################################################

