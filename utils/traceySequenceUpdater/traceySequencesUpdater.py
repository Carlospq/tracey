##############################################################################################################################
#### IMPORTS ####
import os, sys
import subprocess
import xmltodict
import re
import pyhmmer

from datetime import date
from collections import Counter
from Bio import Align

from apps.home.models import *
from django.db.models import Q

today = date.today()
##############################################################################################################################
#### FUNCTIONS ####
def writeLog(logFile, traceyID, ncbiID, shortname, newshortname, comment):
	logFile.write("%s\t%s\t%s\t%s\t%s\n" % (traceyID, ncbiID, shortname, newshortname, comment))

def get_ncbi_id(seq):
	# possibles IDs sources: ['gi', 'gb', 'emb', 'ref', 'dbj', 'pir', 'prf', 'sp', 'pdb', 'tpe', 'none', 'tpg']
	fids = seq.foreignannotation.split("|")
	if len(fids) == 1:
		idx = fids[0].split()[0]
		if ";" in idx:
			ncbiIdx = None
		else:
			ncbiIdx = idx
	else:
		ncbiDictionary = {}
		for i in range(len(fids)):
			if fids[i] in ncbiDictionary: continue
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
	# idx: NCBI sequence id
	# Returns: xml data
	# Example: esummary("NP_004594.1", db="protein")
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
	# Fetch data from NCBI using efetch
	# db: database to fetch data from
	# idx: NCBI sequence id
	# Returns: xml data
	# Example: efetch("NP_004594.1", db="sequences")
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

def alignSimilarSequences(sequence, threshold=0.65):
	similarSequences = []
	testSequences = []

	# Use domaingroups instead?
	motifs = [m.motifname for m in sequence.motifs_set.all()]
	for seq in Sequences.objects.filter(taxonomy=sequence.taxonomy):
		for m in seq.motifs_set.all():
			if m.motifname in motifs:
				if not seq in testSequences:
					testSequences.append(seq)

	aligner = Align.PairwiseAligner()
	aligner.gap_score = -1
	aligner.open_gap_score = -0.5
	aligner.extend_gap_score = -0.1
	aligner.target_end_gap_score = 0.0
	aligner.query_end_gap_score = 0.0
	for seq in testSequences:
		alignments = aligner.align(sequence.sequence, seq.sequence)
		if alignments[0].score/len(sequence.sequence) >= threshold:
			if not seq in similarSequences:
				similarSequences.append(seq)

	return similarSequences

def getSimilarSequences(sequence, summary_output, sequencesAnalysed):
	# Returns all sequences with similar protein sequence belonging to the same taxonomy
	status = ['live' if not 'Status' in summary_output else summary_output['Status']][0]
	identicalSequences = {sequence.sequence_id: {'sequence': sequence,
												 'status': status,
												 'main': True,
												 'summary_output': summary_output}
						  }
	errorSequences = {}

	for seq in alignSimilarSequences(sequence, threshold=0.65):
		# Check if sequence is already in identicalSequences
		if seq.sequence_id in sequencesAnalysed: continue
		if seq.sequence_id != sequence.sequence_id:
			ncbi_id = get_ncbi_id(seq)
			if not ncbi_id:
				errorSequences[seq.sequence_id] = {'sequence': seq,
												   'status': 'NotUpdated',
												   'ncbi_id': '',
												   'main': False,
												   'error': 'Identical sequence to tracey ID %s but no ncbi_id found; Not updated' % sequence.sequence_id}
				continue
			new_summary_output, summary_error = esummary(ncbi_id)
			status = ['live' if not 'Status' in new_summary_output else new_summary_output['Status']][0]
			if summary_error:
				errorSequences[seq.sequence_id] = {'sequence': seq,
												   'status': status,
												   'ncbi_id': ncbi_id,
												   'main': False,
												   'error': summary_error}
				continue
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
	mainSequences = {}
	secondarySequence = {}

	# Choose main reference sequences
	# Priority: RefSeq > SwissProt > INSD > PDB > PIR > PRF
	# Then: Choose main reference sequence with highest isoform number (isoform 1 or isoform A)
	# If no main reference sequence, choose live sequence with highest isoform number
	for source in dbSoruces:
		if nSourceDb[source] == 0: continue
		if nSourceDb[source] == 1:
			idx = [idx for idx in identicalSequences if identicalSequences[idx]['summary_output']['SourceDb'] == source][0]
			mainSequences[idx] = identicalSequences[idx]
		if nSourceDb[source] > 1:
			sourceIdxs = [idx for idx in identicalSequences if identicalSequences[idx]['summary_output']['SourceDb'] == source]
			taxIdxs = [identicalSequences[idx]['sequence'].taxonomy.taxonomystatus for idx in identicalSequences if identicalSequences[idx]['summary_output']['SourceDb'] == source]
			mainRefCount = Counter(taxIdxs)['main reference']

			if mainRefCount == 0:
				try:
					mainIdx = [x for x in sourceIdxs if identicalSequences[x]['main'] and identicalSequences[x]['Status'] == 'live'][0]
					secondarySequence = {mainIdx: identicalSequences[mainIdx]}
				except:
					pass
			elif mainRefCount >= 1:
				for idx in sourceIdxs:
					if identicalSequences[idx]['sequence'].taxonomy.taxonomystatus == 'main reference' and identicalSequences[idx]['status'] == 'live':
						# Check if sequence is isoform > 1
						description = getDescription(identicalSequences[idx])
						match = re.search('isoform[-\s]([\d]*[a-zA-Z]*[\d]*)', description, re.IGNORECASE)
						if match:
							try:
								iso = str([x for x in match.groups() if x][0])
							except:
								iso = "z"
							if (iso.isnumeric() and iso > "1") or (not iso.isnumeric() and iso.lower() > "a") or (not iso.isnumeric() and len(iso)>1 and iso.lower() >"1a") or (not iso.isnumeric() and len(iso)>1 and iso.lower() > "a1"):
								secondarySequence = {idx: identicalSequences[idx]}
							else:
								# Get isoform info from identical sequences
								isoforms = {}
								for idx2 in sourceIdxs:
									title = identicalSequences[idx2]['summary_output']['Title']
									description = [title if 'isoform' in title else getDescription(identicalSequences[idx2])][0]
									match = re.search('isoform[-\s]([\d]*[a-zA-Z]*[\d]*)', description, re.IGNORECASE)
									if match:
										iso = str([x for x in match.groups() if x][0])
									else:
										iso = "z"
									isoforms[idx2] = iso
								# Check if identical live sequence exists
								identicalSeq = [x for x in identicalSequences if identicalSequences[x]['status'] == 'live'
																			 and identicalSequences[x]['sequence'].sequence == identicalSequences[idx]['sequence'].sequence
							 												 and identicalSequences[x]['summary_output']['SourceDb'] == source
																			 and isoforms[x] < isoforms[idx]
																			 and idx != x]
								if identicalSeq:
									secondarySequence = {idx: identicalSequences[idx]}
								else:
									mainSequences[idx] = identicalSequences[idx]
						else:
							mainSequences[idx] = identicalSequences[idx]
					else:
						secondarySequence = {idx: identicalSequences[idx]}

		# If exact same proteiin sequences in mainsequences: choose first sequence
		if len(mainSequences) > len(Counter([mainSequences[idx]['sequence'].sequence for idx in mainSequences])):
			uniqueSequences = []
			removeIdxs = []
			for idx in mainSequences:
				if mainSequences[idx]['sequence'].sequence in uniqueSequences:
					removeIdxs.append(idx)
				else:
					uniqueSequences.append(mainSequences[idx]['sequence'].sequence)
			for idx in removeIdxs:
				del mainSequences[idx]

		if mainSequences:
			return mainSequences
		elif secondarySequence:
			return secondarySequence
	# Return initial sequence if not main in identicalSequences
	mainSequences = [{idx: identicalSequences[idx] for idx in identicalSequences if identicalSequences[idx]['main']}][0]
	return mainSequences

def countLive(identicalSequences):
	return sum([1 for seqId in identicalSequences if identicalSequences[seqId]['status'] == 'live'])

def regexProteinName(protname):
	# Search for key patterns in protein names and info.
	patterns = {'ykt': 'ykt([0-9]*)',
				'sft1': 'sft1',
				'gos': 'Golgi SNA.* .*?(R[0-9]*)|gos(R[0-9]*)',
				'GS15': 'GS15|BET1L|bet1-like',
				'use': 'use(1)|use-(1)',
				'bet': 'bet(1)|bet-(1)',
				'tom': 'tomosyn',
				'vti': 'vti(\d*[a-z]*)|vesicle transport through interaction with t-SNAREs.*?(\d[A-Z]*)',
				'snap': 'snap.*?([0-9]*)|synaptosom[a-z]*-associated protein ([0-9]*)|sec9',
				'membrin': 'membrin\W?([0-9]*)|memb([0-9]+)|Golgi SNAP receptor',
				'endobrevin': 'endobrevin',
				'syxbp': 'syntaxin\s*-?\s*binding protein ([0-9]*)|stxbp.*?([0-9]*[l]?)',
				'syb': 'syb[^l]\D*?(\d*)|synaptobrevin[^-like]\s*(\d+)|synaptobrevin[-\s](\d+)',
				'syx': 'syntaxin[\s]*\D*([\dA-Z]*)|syn[^aptobrevin]([0-9A-Z]*)|stx([0-9A-Z]*)',
				'sec': 'sec[\s]*(\d*)?',
				'vamp': 'v\D*a\D*m\D*p\D*(\d*)?',
				'lamin': 'lamin\s'
				}
	# Check for isoform number
	match = re.search('isoform[-\s]([\da-zA-Z]*)', protname, re.IGNORECASE)
	if match:
		iso = '-'+[x for x in match.groups() if x][0]
	else:
		iso = ''
	for prot in patterns:
		match = re.search(patterns[prot], protname, re.IGNORECASE)
		if match:
			try:
				num = [x for x in match.groups() if x][0]
				if num:
					return prot+num+iso
				else:
					return prot+iso
			except IndexError:
				return prot+iso
	return ''

def getDescription(identicalSequence):
	# Returns a description of the sequence [protein name, sequence product, protein synonyms, ...] based on the information from NCBI
	name = identicalSequence['summary_output']['Title']
	accession = identicalSequence['summary_output']['AccessionVersion']
	try:
		efetch_out, efetch_err = efetch(accession)
		GBQ = [x for x in efetch_out['GBSeq_feature-table']['GBFeature'] if x['GBFeature_key'] in ['Protein', 'CDS']]
		GBQ = [x['GBFeature_quals']['GBQualifier'] for x in GBQ]
		for qualifier in GBQ:
			for desc in [x['GBQualifier_value'] for x in qualifier if
						 x['GBQualifier_name'] in ['product', 'name', 'note', 'gene', 'gene_synonym']]:
				name += ' ' + desc
		return name
	except:
		return name

def predictShortname(identicalSequence):
	shortname = identicalSequence['sequence'].taxonomy.taxonomyshortname.split("_")[0]
	name = identicalSequence['summary_output']['Title']
	accession = identicalSequence['summary_output']['AccessionVersion']

	try:
		efetch_out, efetch_err = efetch(accession)
		GBQ = [x for x in efetch_out['GBSeq_feature-table']['GBFeature'] if x['GBFeature_key'] in ['Protein', 'CDS']]
		GBQ = [x['GBFeature_quals']['GBQualifier'] for x in GBQ]
		for qualifier in GBQ:
			for desc in [x['GBQualifier_value'] for x in qualifier if x['GBQualifier_name'] in ['product', 'name', 'note', 'gene', 'gene_synonym']]:
				name += ' '+desc
	except:
		pass

	# search for protein names regexs
	protName = regexProteinName(name)
	if protName:
		shortname += "_" + protName
	else:
		shortname = identicalSequence['sequence'].sequenceshortname
	return shortname

def predictShortnameByTraceyId(traceySeqId):
	seq = Sequences.objects.get(sequence_id=traceySeqId)
	shortname = seq.taxonomy.taxonomyshortname.split("_")[0]
	ncbiId = get_ncbi_id(seq)
	efetch_out, efetch_err = efetch(ncbiId)

	name = ''
	try:
		GBQ = [x for x in efetch_out['GBSeq_feature-table']['GBFeature'] if x['GBFeature_key'] in ['Protein', 'CDS']]
		GBQ = [x['GBFeature_quals']['GBQualifier'] for x in GBQ]
		for qualifier in GBQ:
			for desc in [x['GBQualifier_value'] for x in qualifier if x['GBQualifier_name'] in ['product', 'name', 'note', 'gene', 'gene_synonym']]:
				name += " "+desc
	except:
		pass

	# search for protein names regexs
	name += seq.sequenceshortname
	protName = regexProteinName(name)
	if 'similar to' in name or 'homolog' in name:
		protName += '-like'
	if protName:
		shortname += "_"+protName
	else:
		shortname = seq.sequenceshortname
	return shortname


def newEntryForReplacedBy(replaced_by, seqId, updateLog={}):
	if any(Sequences.objects.filter(foreignannotation__icontains=replaced_by)):
		updateLog[seqId]['comment'] += ' - NCBI ID %s already exists in TRACEY' % replaced_by
		return "", ""

	fetch_output, fetch_error = efetch(replaced_by)
	esummary_output, esummary_error = esummary(replaced_by)

	newEntrySequence = ''
	if fetch_error:
		updateLog[seqId]['comment'] += 'Error fetching NCBI ID %s; ' % (replaced_by)
	elif "Status" in esummary_output and not "replaced" in esummary_output["Status"]:
		updateLog[seqId]['comment'] += 'NCBI ID %s is %s - Sequence not created ' % (replaced_by, esummary_output["Status"])
	elif "Status" in esummary_output and "replaced" in esummary_output["Status"]:
		updateLog[seqId]['comment'] += ' - NCBI ID %s is replaced by %s' % (replaced_by, esummary_output["ReplacedBy"])
		newEntryForReplacedBy(esummary_output["ReplacedBy"], seqId, updateLog=updateLog)
	else:
		# Fetch data from ncbi for replaced_by and create new sequence entry in TRACEY
		newEntrySequence = newSequenceEntryFromEfetch(esummary_output, fetch_output)
		# Use TRACEY ID of newly created sequence entry
		# updateLog[seqId + 99999999] = {'accessionVersion': fetch_output['GBSeq_accession-version'],
		# 							   'comment': 'New sequence entry created replacing TRACEY ID %s' % seqId,
		# 							   'newshortname': newEntrySequence.sequenceshortname}
	return [newEntrySequence, esummary_output]


def analyzeSequence(newSeq):

	# Scan sequence for all motifs in TRACEY
	with pyhmmer.plan7.HMMFile("./utils/hmmModels/MOTIFS.hmmDb") as hmm_file:
		alphabet = pyhmmer.easel.Alphabet.amino()
		proteins = [pyhmmer.easel.TextSequence(name=b"Query sequence", sequence=newSeq.sequence).digitize(alphabet)]
		all_hits = pyhmmer.hmmer.hmmscan(proteins, hmm_file, E=1e-5)

	hits_d = {}
	for hits in all_hits:
		for h in hits:
			print(h.name.decode())
			h_name = h.name.decode()
			for d in h.domains:
				print(h_name, format(d.pvalue, '.1E'))
				if h_name in hits_d and d.pvalue > hits_d[h_name]['pvalue']:
					continue
				dg_name = str(d.alignment).split("\n")[1].split()[0]
				dg = Domaingroups.objects.get(domaingroupname=dg_name)
				motif = Domains.objects.get(domain_id=dg.domain_id).domainname
				hits_d[h_name] = {'evalue': format(d.pvalue, '.1E'),
								  'pvalue': d.pvalue,
								  'env_from': d.env_from,
								  'env_to': d.env_to,
								  'length': d.env_to - d.env_from,
								  'alignment': d.alignment,
								  'dg': dg,
								  'motif': motif,
								  }
	# Save motifs to database
	for hit in hits_d:
		motif = Motifs()
		motif.sequence = newSeq
		motif.motifname = hits_d[hit]['motif']
		motif.startposition = hits_d[hit]['env_from']
		motif.endposition = hits_d[hit]['env_to']
		motif.domaingroup = hits_d[hit]['dg']
		motif.gaps = 0 # Need to implement gap counting
		motif.evalue = hits_d[hit]['evalue']
		motif.alignment = hits_d[hit]['alignment']
		# motif.save()

	return hits_d


def newSequenceEntryFromEfetch(esummary_out, efetch_out):
	# Create new sequence entry in TRACEY
	# Returns: new sequence entry
	newSeq = Sequences()
	newSeq.sequence = efetch_out['GBSeq_sequence'].upper()
	newSeq.sequencetype = 'protein'
	newSeq.sequencestatus = 'live'
	newSeq.changelog = 'New sequence entry created by SequenceUpdater - %s' % today.strftime("%Y.%m.%d")
	newSeq.taxonomy = Taxonomies.objects.get(ncbi_taxonomy_id=esummary_out['TaxId'])
	newSeq.sequenceshortname = predictShortname({'sequence': newSeq, 'summary_output': esummary_out})
	newSeq.private = False
	newSeq.foreignannotation = "".join([esummary_out['Extra'], esummary_out['Title']])
	newSeq.sourcedatabase = esummary_out['SourceDb']
	newSeq.dbxref = esummary_out['AccessionVersion']
	newSeq.aliases = "; ".join([d['GBQualifier_value']
									for l in [x["GBFeature_quals"]['GBQualifier']
									for x in efetch_out['GBSeq_feature-table']['GBFeature']]
									for d in l
									if "gene" in d['GBQualifier_name']])
	try:
		ncbigene_id =  [d['GBQualifier_value']
								for l in [x["GBFeature_quals"]['GBQualifier']
								for x in efetch_out['GBSeq_feature-table']['GBFeature']]
								for d in l
								if d['GBQualifier_name']=="db_xref" and "GeneID" in d['GBQualifier_value']][0].replace("GeneID:", "")
	except:
		ncbigene_id = '-1'

	if ncbigene_id in Genes.objects.values_list('ncbigene_id', flat=True):
		newGene = Genes.objects.filter(ncbigene_id=ncbigene_id)[0]
	else:
		newGene = Genes(ncbigene_id=ncbigene_id)
		# newGene.save()

	newSeq.gene = newGene
	# newSeq.save()

	# Analyze sequence for new motifs
	# analyzeSequence(newSeq)

	return newSeq


def sequenceUpdate(sequence, summary_output, sequencesAnalysed):

	# Initialize updateLog to keep track of all updates
	updateLog = {}

	# Check if similar sequence exist in TRACEY and collect NCBI data for them
	identicalSequences, errorSequences = getSimilarSequences(sequence, summary_output, sequencesAnalysed)
	# If error while fetching identical sequences write to log file and continue
	if errorSequences:
		for errorSeqId in errorSequences:
			updateLog[errorSeqId] = {'accessionVersion': errorSequences[errorSeqId]['ncbi_id'],
									 'comment': errorSequences[errorSeqId]['error'],
									 'newshortname': Sequences.objects.get(sequence_id=errorSeqId).sequenceshortname
									 }

	# Add new ReplacedBy sequences to identicalSequences
	newReplacedSequences = {}
	for identicalSeqId in identicalSequences:

		identicalSeq = identicalSequences[identicalSeqId]
		seq = identicalSeq['sequence']
		identicalSeqSummaryOutput = identicalSeq['summary_output']

		if "Status" in identicalSeqSummaryOutput and identicalSeqSummaryOutput["Status"] == "replaced":
			replaced_by = identicalSeqSummaryOutput["ReplacedBy"]
			accessionVersion = identicalSeqSummaryOutput['AccessionVersion']

			comment = ''
			if seq.dbxref != accessionVersion:
				comment += 'dbxref updated to %s; ' % accessionVersion
			comment += 'Sequence replaced by NCBI ID %s; ' % (replaced_by)

			if seq.sequencestatus not in ['replaced', 'replaced NCBI']:
				comment += 'Sequencestatus changed from %s to replaced NCBI; ' % (seq.sequencestatus)
				# sequence.sequencestatus = 'replaced NCBI'

			newShortname = predictShortname(identicalSeq)
			updateLog[identicalSeqId] = {'accessionVersion': accessionVersion,
										 'comment': comment,
										 'newshortname': newShortname}

			newSeq, newEsummary_output = newEntryForReplacedBy(replaced_by, identicalSeqId, updateLog=updateLog)
			if not newSeq: continue
			newReplacedSequences[newSeq.sequence_id] = {'sequence': newSeq,
														'status': newSeq.sequencestatus,
														'main': True,
														'summary_output': newEsummary_output}

	for replacedId in newReplacedSequences:
		identicalSequences[replacedId] = newReplacedSequences[replacedId]

	# Select main sequence in case of multiple identical sequences (if no identical then mainSequence = sequence)
	# NOTE: main sequences will become the only active sequences in TRACEY
	mainSequences = selectMainFromIdenticalSequences(identicalSequences)
	# Update all sequences in identicalSequences: mainSequences becomes "live", the rest become "ignore"
	for identicalSeqId in identicalSequences:

		identicalSeq = identicalSequences[identicalSeqId]
		identicalSeqSummaryOutput = identicalSeq['summary_output']
		seq = identicalSeq['sequence']

		accessionVersion = identicalSeqSummaryOutput['AccessionVersion']
		comment = ''
		newShortname = predictShortname(identicalSeq)
		# Update dbxref: gi to accession version
		if seq.dbxref != accessionVersion:
			#sequence.dbxref = accessionVersion
			comment += 'dbxref updated to %s; ' % accessionVersion


		if "lamin" in newShortname:
			comment += 'Sequence is a LAMIN; Sequence status changed from %s to dead' % seq.sequencestatus
			# sequence.sequencestatus = 'dead'
		elif "Status" in identicalSeqSummaryOutput:
			# If "Status" in summary_output (meaning sequence is deleted/suppressed/replaced/...)
			# Status == replaced: update status if needed and check if replaced_by is in TRACEY
			if identicalSeqSummaryOutput["Status"] == "replaced":
				continue

			# Else If sequence is deleted/suppressed/dead, Update TRACEY sequence and write to log file
			else:
				# Update sequence.sequencestatus if needed
				if seq.sequencestatus == identicalSeqSummaryOutput["Status"]:
					comment += "No changes needed. Sequencestatus already %s" % identicalSeqSummaryOutput["Status"]
				else:
					comment += "Sequencestatus changed from %s to %s" % (seq.sequencestatus, identicalSeqSummaryOutput["Status"])

		# If not "Status" in summary_output (meaning sequence is active in NCBI)
		else:
			# Update sequenceshortname if necessary
			#if "OLD" in seq.sequenceshortname.upper() or not seq.sequenceshortname:
			#	newShortname = predictShortname(identicalSequences[identicalSeqId])

			if identicalSeqId in mainSequences:

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
			elif "-like" in newShortname:
				comment += "Sequence is a homolog, sequencestatus updated from live to ignore"
				#seq.sequencestatus = 'ignore'
			else:
				if seq.sequencestatus == 'live':
					comment += "Sequencestatus updated from live to ignore"
					# seq.sequencestatus = 'ignore'
				else:
					comment += "No changes needed. Sequence status already ignore"
			updateLog[identicalSeqId] = {
				'accessionVersion': identicalSequences[identicalSeqId]['summary_output']['AccessionVersion'],
				'comment': comment,
				'newshortname': newShortname
			}

		if identicalSeqId not in updateLog:
			updateLog[identicalSeqId] = {'accessionVersion': accessionVersion,
										 'comment': comment,
										 'newshortname': newShortname}

	return updateLog

#### MAIN FUNCTION ####
def updateSequences(sequencesAnalysed, species="", traceyIds=[], onlyActive=False):
	#### NOTE: So far this script is adapted only for SNARE sequences

	######### UPDATE SEQUENCES WITH NCBI SOURCE #########
	# This first section collects all the sequences from the database that are sourced from NCBI
	# Then fetch data from the required database from NCBI and compares it with the sequence data in tracey
	# If needed, sequence will be updated with the new information

	# Collect all sequences in tracey with SNARE/Habc motifs
	snareMotifsIds = set([m.sequence_id for m in Motifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])
	snareVerifymotifsIds = set([m.sequence_id for m in Verifymotifs.objects.filter(motifname__in=["SNARE", "Snare", "Habc"])])

	snareSeqs = Sequences.objects.filter(sequence_id__in=list(snareMotifsIds | snareVerifymotifsIds))
	snareSeqs = snareSeqs.exclude(sequence_id__in=sequencesAnalysed)

	if species:
		try:
			taxonomy = Taxonomies.objects.get(Q(taxonomyshortname=species) | Q(scientificname=species))
			snareSeqs = snareSeqs.filter(taxonomy=taxonomy)
		except Taxonomies.DoesNotExist:
			sys.exit("Species not found in database. Please confirm that the given species name is correct.")

	if traceyIds:
		snareSeqs = snareSeqs.filter(sequence_id__in=traceyIds)

	snareSeqsNCBI = snareSeqs.filter(sourcedatabase__in=['NCBI_est', 'NCBI_nr', 'NCBI_refseq'])  # 83304 sequences
	if onlyActive:
		snareSeqsNCBI = [s for s in snareSeqsNCBI if any(m.motifname == "SNARE" for m in s.motifs_set.all())]
		snareSeqsNCBI = [s for s in snareSeqsNCBI if s.sequencestatus == 'live']

	print("Sequences to analyze: %d" % len(snareSeqsNCBI))

	for sequence in snareSeqsNCBI:

		logFile = open("./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % today.strftime("%Y.%m.%d"), "a")

		# Skip sequence if already updated
		if sequence.sequence_id in sequencesAnalysed:
			continue

		# If summary_error from NCBI: write sequence ID and error into log file and continue
		if sequence.foreignannotation == "none":
			comment = "ERROR with sequence tracey_id %s: Foreignannotation missing\n" % (sequence.sequence_id)
			writeLog(logFile, sequence.sequence_id, '', sequence.sequenceshortname, '', comment)
			continue

		ncbi_id = get_ncbi_id(sequence)
		if not ncbi_id:
			comment = "ERROR with sequence tracey_id %s: No NCBI ID found\n" % (sequence.sequence_id)
			writeLog(logFile, sequence.sequence_id, '', sequence.sequenceshortname, '', comment)
			continue

		# Get summary data for idx
		summary_output, summary_error = esummary(ncbi_id)

		# If summary_error from NCBI: write sequence ID and error into log file and continue
		if summary_error:
			writeLog(logFile, sequence.sequence_id, ncbi_id, sequence.sequenceshortname, '', comment)
			continue

		# Update sequence if needed and print log into logFile
		updateLog = sequenceUpdate(sequence, summary_output, sequencesAnalysed)
		print(updateLog)
		logFile.write("Similarity block:\n")
		for updateId in updateLog:
			if not updateId in sequencesAnalysed:
				sequencesAnalysed.append(updateId)
			try:
				shortname = Sequences.objects.get(sequence_id=updateId)
			except:
				shortname = 'empty'
			writeLog(logFile, updateId, updateLog[updateId]['accessionVersion'], shortname,
					 updateLog[updateId]['newshortname'], updateLog[updateId]['comment'])

		logFile.close()

	logFile = open("./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % today.strftime("%Y.%m.%d"), "a")
	logFile.write("Update completed")
	logFile.close()


# Run code when run as script
if __name__ == "django.core.management.commands.shell":
	sequencesAnalysed = []
	updateSequences(sequencesAnalysed)




# sequence = Sequences.objects.get(pk=26)
# ncbi_id = get_ncbi_id(sequence)
# summary_output, summary_error = esummary(ncbi_id)
#
# identicalSequences, errorSequences = getSimilarSequences(sequence, summary_output)
# for identicalSeqId in identicalSequences:
# 	pass
# identicalSeq = identicalSequences[identicalSeqId]
# predictShortname(identicalSeq)
# identicalSequence = identicalSeq
# name = identicalSequence['summary_output']['Title']
# accession = identicalSequence['summary_output']['AccessionVersion']
# efetch_out, efetch_err = efetch(accession)
# GBQ = [x for x in efetch_out['GBSeq_feature-table']['GBFeature'] if x['GBFeature_key'] in ['Protein', 'CDS']]
# GBQ = [x['GBFeature_quals']['GBQualifier'] for x in GBQ]
# for qualifier in GBQ:
# 	for desc in [x['GBQualifier_value'] for x in qualifier if x['GBQualifier_name'] in ['product', 'name', 'note', 'gene', 'gene_synonym']]:
# 		name += ' '+desc
# protname = name
# match = re.search('isoform[-\s]([\d]*[a-zA-Z]*[\d]*)', protname, re.IGNORECASE)
# if match:
# 	iso = '-' + [x for x in match.groups() if x][0]
# else:
# 	iso = ''
# for prot in patterns:
# 	match = re.search(patterns[prot], protname, re.IGNORECASE)
# 	if match:
# 		print(match)
# print(iso)
# match
# regexProteinName(protname)
#
#
# # updateLog = sequenceUpdate(sequence, summary_output)
# # for updateId in updateLog:
# # 	try:
# # 		shortname = Sequences.objects.get(sequence_id=updateId)
# # 	except:
# # 		shortname = 'empty'
# # 	print(updateId, updateLog[updateId]['accessionVersion'], shortname, updateLog[updateId]['newshortname'], updateLog[updateId]['comment'])
#
#
# patterns = {'ykt': 'ykt([0-9]*)',
# 				'sft1': 'sft1',
# 				'gos': 'Golgi SNA.* .*?(R[0-9]*)|gos(R[0-9]*)',
# 				'GS15': 'GS15|BET1L|bet1-like',
# 				'use': 'use(1)|use-(1)',
# 				'bet': 'bet(1)|bet-(1)',
# 				'tom': 'tomosyn',
# 				'vti': 'vti(\d*[a-z]*)|vesicle transport through interaction with t-SNAREs.*(\d[A-Z]*)',
# 				'snap': 'snap.*?([0-9]*)|synaptosom[a-z*]-associated protein ([0-9]*)|sec9',
# 				'membrin': 'membrin\W?([0-9]*)|memb([0-9]+)|Golgi SNAP receptor',
# 				'endobrevin': 'endobrevin',
# 				'syxbp': 'syntaxin\s*-?\s*binding protein ([0-9]*)|stxbp.*?([0-9]*[l]?)',
# 				'syb': 'syb[^l]\D*?(\d*)|synaptobrevin[^-like]\s*(\d+)|synaptobrevin[-\s](\d+)',
# 				'syx': 'syntaxin[\s]*\D*(\d*[A-Z]*)|syn([0-9]*[A-Z]*)|stx([0-9]*[A-Z]*)',
# 				'sec': 'sec[^retion].*?([0-9]*)?',
# 				'vamp': 'v\D*a\D*m\D*p\D*(\d*)?',
# 				}
# for prot in patterns:
# 	match = re.search(patterns[prot], protname, re.IGNORECASE)
# 	if match:
# 		print(match)


