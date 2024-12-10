### README
# Only works for SNARE proteins
#
# This script predicts the SNARE group that a sequences belongs to using linear regression models (lm) based on SNARE HMM motifs
#
# MAIN FUNCTION: predictMotifs(sequences, bothDomains=False, probCutOff=60, onlyPrint=False)
#
# INPUTS:
# 	- sequences: string
# 		- either a single protein sequence or
# 		- path to a fasta file with multiple protein sequences
# 	- bothDomains: bool[=False]
# 		- if False, only motif sequence is expected and Habc and SNARE models will be used
# 		- if True, full length protein sequence is expected and HabcSNARE models will be used
# 	- probCutOff: int[=60]
# 		- probability cut off to consider a prediction as valid
#		- if prediction probability is below probCutOff, a secondary "suggested" prediction will be given along with the primary prediction
# 	- onlyPrint: bool[=False]
# 		- if True, only prints the prediction results into the console
#		- if False, returns the prediction results as a dictionary
# OUTPUTS:
# 	- results: dict
# 		- keys: sequence names
# 		- values: dict
# 			- keys: prediction level (group/subgroups) or prediction probability
# 			- values: prediction (group name for prediction level, probability (in % from 0 to 100) for prediction probability)
#
# Different lm are used to do the predictions:
#
#	model name				|	used motifs	|	possible predictions	| number of variables
#
#	> models that expect only domain sequence
#
#	lm_general.sav			|	Habc, SNARE	|	Habc, SNARE, NotSNARE	| 55
#	lm_Hacb_main.sav		|	Habc, SNARE	|	main Habc groups		| 55
#	lm_Habc_sub.sav			|	Habc, SNARE	|	Habc subgroups			| 55
#	lm_SNARE_main.sav		|	Habc, SNARE	|	main SNARE groups		| 55
#	lm_SNARE_sub.sav		|	Habc, SNARE	|	SNARE subgroups			| 55
#
#	> models that expect full length protein sequence
#
#	lm_generalHabcSNARE.sav	|	Habc+SNARE	|	SNARE, NotSNARE			| 24
#	lm_HabcSNARE_main.sav	|	Habc+SNARE	|	main HabcSNARE groups	| 24
#	lm_HabcSNARE_sub.sav	|	Habc+SNARE	|	HabcSNARE subgroups		| 24
#
#########################################################################################

### IMPORTS
import os, subprocess
import pyhmmer
import tempfile
import pickle
import numpy as np
# from sklearn.linear_model import LogisticRegression

# list of motif names used for the different lm
from utils.motifPredictor.motifNames import *

### FUNCTIONS
# Stores hmmsearch results for each motif into a dictionary
def retriveEvalues(domtbloutFile, all_motifs):
	results = {}
	with open(domtbloutFile, 'r') as f:
		for line in f:
			if line.startswith("#"): continue
			line = line.strip().split()
			seq_name = line[0]
			hmm_name = line[3]
			evalue = np.log(float(line[12]))
			if hmm_name not in all_motifs: continue
			if seq_name not in results:
				results[seq_name] = {}
				for m in all_motifs:
					results[seq_name][m] = np.log(10e10)
			if evalue < results[seq_name][hmm_name]:
				results[seq_name][hmm_name] = evalue
	return results

# Search sequences againts HMM database
def motifSearch(input_file="", sequence="", bothDomains=False, hmmDB="utils/motifPredictor/HmmDb/hmmDb.hmm", tmp_file="utils/motifPredictor/temp_domtblout.txt"):

	# Retrieve valid motifnames according to lmModel that is going to be used
	if bothDomains:
		all_motifs = HabcSNAREMotifsNames
	else:
		all_motifs = motifsNames

	# Scan the sequence for hits
	if sequence:
		# If sequence is provided
		# Prepare HMM models
		hmms = pyhmmer.plan7.HMMFile(hmmDB)

		# Convert hmms to optimized profiles -> optimizad block
		alphabet = pyhmmer.easel.Alphabet.amino()
		optimized_block = pyhmmer.plan7.OptimizedProfileBlock(alphabet=alphabet)

		for h in hmms:
			optimized_block.append(h.to_profile().to_optimized())

		pipeline = pyhmmer.plan7.Pipeline(pyhmmer.easel.Alphabet.amino())
		digitalsequence = pyhmmer.easel.TextSequence(name=bytes("Query_sequence", 'utf-8'), sequence=sequence).digitize(alphabet)
		hits = pipeline.scan_seq(digitalsequence, optimized_block)

		# Store results in dictionary
		results = {'inputSequence': {}}

		# Initialize results dictionary
		for m in all_motifs:
			results['inputSequence'][m] = np.log(10e10)

		for hit in hits:
			for d in hit.domains:
				hit_name = hit.name.decode('utf-8')
				if hit_name in all_motifs:
					if d.pvalue < results['inputSequence'][hit_name]:
						results['inputSequence'][hit_name] = d.pvalue
	else:
		# If file is provided
		tmp_file_domtblout = "./utils/motifPredictor/domtblout_tmpfile.txt"
		cmd = "hmmsearch --domtblout %s --cpu 4 %s %s" % (tmp_file_domtblout, hmmDB, input_file)
		out, error = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		if error:
			return error
		else:
			results = retriveEvalues(tmp_file_domtblout, all_motifs)
			os.remove(tmp_file_domtblout)

	# if no results
	if not results:
		return {}
	else:
		evals = {}
		for idx in results:
			evals[idx] = [results[idx][m] for m in all_motifs]
		return evals

# Predicts the domain of a sequence
def domainPredict(evals, probCutOff = 60, SNARE=False, bypass=''):

	# Generates dictionary with probabilities for each prediction
	def probsToDict(model, evals):
		groups = model.classes_
		probs = model.predict_proba([evals])[0]
		probsDict = {}
		for i in range(len(groups)):
			probsDict[groups[i]] = probs[i]*100
		return probsDict

	# Returns n best predictions
	def nBest(model, evals, n):
		probsDict = probsToDict(model, evals)
		nProb = sorted(model.predict_proba([evals])[0])[-n]*100
		nGroup = [x for x in probsDict if probsDict[x] == nProb][0]
		return [nGroup, round(nProb, 2)]

	# Motif names
	submotifsTree = subTree

	#### Defined models
	modelPath = 'utils/motifPredictor/'

	# Load models
	if SNARE:
		general_main_model = pickle.load(open(modelPath + 'lm_generalHabcSNARE.sav', 'rb'))
		full_main_model = pickle.load(open(modelPath + 'lm_HabcSNARE_main.sav', 'rb'))
		full_sub_model = pickle.load(open(modelPath + 'lm_HabcSNARE_sub.sav', 'rb'))
		models = {"SNARE": {"main": full_main_model,
							"sub": full_sub_model}
				  }
	else:
		general_main_model = pickle.load(open(modelPath+'lm_general.sav', 'rb'))
		Habc_main_model = pickle.load(open(modelPath + 'lm_Habc_main.sav', 'rb'))
		Habc_sub_model = pickle.load(open(modelPath + 'lm_Habc_sub.sav', 'rb'))
		SNARE_main_model = pickle.load(open(modelPath + 'lm_SNARE_main.sav', 'rb'))
		SNARE_sub_model = pickle.load(open(modelPath + 'lm_SNARE_sub.sav', 'rb'))
		models = {"Habc": {"main": Habc_main_model,
						   "sub": Habc_sub_model},
				  "SNARE": {"main": SNARE_main_model,
							"sub": SNARE_sub_model}
				  }

	# Initialize variables for predictions and probabilities
	domain = ''
	domain_prob = 0
	group = ''
	group_prob = 0
	sug_group = ''
	sug_group_prob = 0
	subgroup = ''
	subgroup_prob = 0
	sug_subgroup = ''
	sug_subgroup_prob = 0
	alt_domain = ''
	alt_domain_prob = 0
	p1_alt_group = ''
	p1_alt_group_prob = 0
	p2_alt_group = ''
	p2_alt_group_prob = 0
	p1_alt_subgroup = ''
	p1_alt_subgroup_prob = 0
	p2_alt_subgroup = ''
	p2_alt_subgroup_prob = 0

	### Prediction ###
	if bypass:
		domain, domain_prob = bypass, 100
	else:
		domain, domain_prob = nBest(general_main_model, evals, 1)
	# Predict group and subgroup
	if domain != 'notSNARE':
		group_model = models[domain]["main"]
		group, group_prob = nBest(group_model, evals, 1)
		if group_prob < probCutOff:
			sug_group, sug_group_prob = nBest(group_model, evals, 2)
		# Predict subgroup if group has any subgroups
		if submotifsTree[group]:
			subgroup_model = models[domain]["sub"]
			subgroup, subgroup_prob = nBest(subgroup_model, evals, 1)
			# If pred subgroup not in group search for best hit in group-subgroups
			if not subgroup in submotifsTree[group] or subgroup_prob < probCutOff:
				n = 2
				probsDict = probsToDict(subgroup_model, evals)
				while not sug_subgroup in submotifsTree[group]:
					try:
						sug_subgroup, sug_subgroup_prob = nBest(subgroup_model, evals, n)
						n += 1
					except IndexError:
						sug_subgroup, sug_subgroup_prob = '', 0
						break
	# main_prediction = [domain, group, subgroup, sug_subgroup]
	# main_probs = [domain_prob, group_prob, subgroup_prob, sug_subgroup_prob]

	if domain_prob < probCutOff:
		# Alternative domain prediction
		alt_domain, alt_domain_prob = nBest(general_main_model, evals, 2)
		# Alternative group prediction
		if alt_domain != 'notSNARE':
			alt_group_model = models[alt_domain]["main"]
			alt_subgroup_model = models[alt_domain]["sub"]
			p1_alt_group, p1_alt_group_prob = nBest(alt_group_model, evals, 1)
			# Alternative subgroup prediction
			# Path 1: alt_group_pro > probCutOff
			if submotifsTree[p1_alt_group]:
				p1_alt_subgroup, p1_alt_subgroup_prob = nBest(alt_subgroup_model, evals, 1)
				# If pred subgroup not in group search for best hit in group-subgroups
				if not p1_alt_subgroup in submotifsTree[p1_alt_group]:
					p1_alt_subgroup, p1_alt_subgroup_prob, n = '', 0, 2
					probsDict = probsToDict(alt_subgroup_model, evals)
					while not p1_alt_subgroup in submotifsTree[p1_alt_group]:
						try:
							p1_alt_subgroup, p1_alt_subgroup_prob = nBest(alt_subgroup_model, evals, n)
							n += 1
						except IndexError:
							p1_alt_subgroup, p1_alt_subgroup_prob = '', 0
							break
			# Path 2: alt_group_pro < probCutOff
			if p1_alt_group_prob < probCutOff:
				p2_alt_group, p2_alt_group_prob = nBest(alt_group_model, evals, 2)
				if submotifsTree[p2_alt_group]:
					p2_alt_subgroup, p2_alt_subgroup_prob = nBest(alt_subgroup_model, evals, 1)
					# If pred subgroup not in group search for best hit in group-subgroups
					if not p2_alt_subgroup in submotifsTree[p2_alt_group]:
						p2_alt_subgroup, p2_alt_subgroup_prob, n = '', 0, 2
						probsDict = probsToDict(alt_subgroup_model, evals)
						while not p2_alt_subgroup in submotifsTree[p2_alt_group]:
							try:
								p2_alt_subgroup, p2_alt_subgroup_prob = nBest(alt_subgroup_model, evals, n)
								n += 1
							except IndexError:
								p2_alt_subgroup, p2_alt_subgroup_prob = '', 0
								break
	### Return
	return {'domain': domain,
			'domain_prob': domain_prob,
			'group': group,
			'group_prob': group_prob,
			'sug_group': sug_group,
			'sug_group_prob': sug_group_prob,
			'subgroup': subgroup,
			'subgroup_prob': subgroup_prob,
			'sug_subgroup': sug_subgroup,
			'sug_subgroup_prob': sug_subgroup_prob,
			'alt_domain': alt_domain,
			'alt_domain_prob': alt_domain_prob,
			'p1_alt_group': p1_alt_group,
			'p1_alt_group_prob': p1_alt_group_prob,
			'p2_alt_group': p2_alt_group,
			'p2_alt_group_prob': p2_alt_group_prob,
			'p1_alt_subgroup': p1_alt_subgroup,
			'p1_alt_subgroup_prob': p1_alt_subgroup_prob,
			'p2_alt_subgroup': p2_alt_subgroup,
			'p2_alt_subgroup_prob': p2_alt_subgroup_prob}

# Prints formatted results into console
def formatPrediction(results):
	def color(eval):
		if eval >= 90:
			col = '\033[92m'  # green
		elif eval >= 70:
			col = '\033[32m'  # okGreen
		elif eval >= 50:
			col = '\033[33m'  # yellow
		elif eval >= 30:
			col = '\033[35m'  # magenta
		elif eval >= 10:
			col = '\033[31m'  # warning
		else:
			col = '\033[30m'  # black
		ENDC = '\033[0m'
		return "%s%.2f%s" % (col, eval, ENDC)

	printOut = '## Domain prediction || Values between parenthesis are predicted probabilities for each model; If probability is below treshold an alternative prediction is also given\n\n'
	printOut += '# Prediction\n\tDomain: %s (%s)\n\t' % (results['domain'], color(results['domain_prob']))

	if results["sug_group"]:
		printOut += 'Group: %s (%s) [Suggested: %s (%s)]\n\tSubgroup: %s (%s)' % (
		results['group'], color(results['group_prob']), results['sug_group'], color(results['sug_group_prob']),
		results['subgroup'], color(results['subgroup_prob']))
	else:
		printOut += 'Group: %s (%s)\n\tSubgroup: %s (%s)' % (
		results['group'], color(results['group_prob']), results['subgroup'], color(results['subgroup_prob']))

	if results["sug_subgroup"]:
		printOut += ' [Suggested: %s (%s)]\n\n' % (results['sug_subgroup'], color(results['sug_subgroup_prob']))
	else:
		printOut += '\n\n'

	if results['alt_domain'] or results['p1_alt_group']:
		printOut += '# Alternative prediction with group prob > treshold\n\tDomain: %s (%s)\n\tGroup: %s (%s)\n\tSubgroup: %s (%s)\n\n' % (
		results['alt_domain'], color(results['alt_domain_prob']),
		results['p1_alt_group'], color(results['p1_alt_group_prob']),
		results['p1_alt_subgroup'], color(results['p1_alt_subgroup_prob']))
	if results['p2_alt_group']:
		printOut += '# Alternative prediction with group prob < treshold\n\tDomain: %s (%s)\n\tGroup: %s (%s)\n\tSubgroup: %s (%s)\n\n' % (
		results['alt_domain'], color(results['alt_domain_prob']),
		results['p2_alt_group'], color(results['p2_alt_group_prob']),
		results['p2_alt_subgroup'], color(results['p2_alt_subgroup_prob']))
	return printOut

# Prediction and formatting of results combined
def snareMotifPrediction(evals, probCutOff = 60, SNARE=False, bypass=''):
	print(formatPrediction(domainPredict(evals, probCutOff = probCutOff, SNARE=SNARE, bypass=bypass)))

# Prediction from sequence string or path to fasta file
def predictMotifs(sequence, bothDomains=False, probCutOff = 60, bypass='', onlyPrint=False):

	# Write sequence to temporary file
	with tempfile.NamedTemporaryFile(mode='w', dir='utils/motifPredictor', delete=False) as tempseqfile:
		sequenceTemporaryFile = tempseqfile.name
		line = '>' + 'inputSequence' + '\n' + sequence + '\n'
		tempseqfile.write(line)
	tempseqfile.close()

	# Search hmmDb against sequence
	evals = motifSearch(input_file=sequenceTemporaryFile, sequence=sequence, bothDomains=bothDomains)
	if not evals:
		return {}
	else:
		evals = evals['inputSequence']

	# Remove temp file
	os.remove(sequenceTemporaryFile)

	if onlyPrint:
		snareMotifPrediction(evals, SNARE=bothDomains, probCutOff=probCutOff, bypass=bypass)
	else:
		return domainPredict(evals, probCutOff=probCutOff, SNARE=bothDomains, bypass=bypass)


# Test
if __name__ == '__main__':
	# HoSa_Syx16 - Qa.III.a SNARE
	sequence = 'MATRRLTDAFLLLRNNSIQNRQLLAEQVSSHITSSPLHSRSIAAELDELADDRMALVSGISLDPEAAIGVTKRPPPKWVDGVDEIQYDVGRIKQKMKELASLHDKHLNRPTLDDSSEEEHAIEITTQEITQLFHRCQRAVQALPSRARACSEQEGRLLGNVVASLAQALQELSTSFRHAQSGYLKRMKNREERSQHFFDTSVPLMDDGDDNTLYHRGFTEDQLVLVEQNTLMVEEREREIRQIVQSISDLNEIFRDLGAMIVEQGTVLDRIDYNVEQSCIKTEDGLKQLHKAEQYQKKNRKMLVILILFVIIIVLIVVLVGVKSR'
	predictMotifs(sequence, bothDomains=True, probCutOff=60, onlyPrint=True)
