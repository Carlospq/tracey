### README
# Only works for SNARE proteins
#
# This script predicts the SNARE group that a sequences belongs to using Logistic Regression models (lm) based on SNARE HMM motifs
#
# MAIN FUNCTION: motifPrediction(input, hmm_file["utils/motifPredictor/HmmDb/SNAREDb.hmm"], probCutOff[60], tree[SNARETree]):
#
# INPUTS:
# 	- input: [string]
# 		- either a protein sequence or
# 		- path to a fasta file with multiple protein sequences
#	- hmm_file: [string] [=utils/motifPredictor/HmmDb/SNAREDb.hmm]
#		- path to the hmm database file
# 	- probCutOff: [int=60]
# 		- probability cut off to consider a prediction as valid
#		- if prediction probability is below probCutOff, a secondary "suggested" prediction will be given along with the primary prediction
# 	- tree: [dict=SNARETree]
# 		- Dictionary with the SNARE motifs tree
#		- By default the SNARETree from motifNames.py is used
# OUTPUTS:
# 	- results: [dict]
# 		- keys: sequence names
# 		- values: dict
# 			- keys: prediction level (group/subgroups) or prediction probability
# 			- values: prediction (group name for prediction level, probability (in % from 0 to 100) for prediction probability)
#
# Different lm are used to do the predictions:
#
#	model name					|	used motifs	|	possible predictions			| number of variables
#
#	> models
#
#	lm_SNARE_mainMotifs.sav		|	SNARE		|	SNARE							| 83
#	lm_SNARE_groupMotifs.sav	|	SNARE		|	main SNARE groups				| 83
#	lm_SNARE_subMotifs.sav		|	SNARE		|	SNARE subgroups					| 83 # Bad performance; model not used
#	lm_SNARE_#MOTIF.sav			|	SNARE		|	SNARE subgroup only for #MOTIF	| 83
#	lm_SNARE_#MOTIF_#RANK.sav	|	SNARE		|	SNARE subgroups if #RANK		| 83
#
#########################################################################################

### IMPORTS
import os
import pyhmmer
import tempfile
import pickle
import numpy as np

# Import motifs trees to generate motifs lists used for the different lm
from utils.motifPredictor.motifNames import *

#### FUNCTIONS
def searchHMMs(input_sequences, hmmDB="utils/motifPredictor/HmmDb/SNAREDb.hmm", tree=SNARETree):

	# Prepare HMM models
	hmms = pyhmmer.plan7.HMMFile(hmmDB)

	# Convert hmms to optimized profiles -> optimizad block
	alphabet = pyhmmer.easel.Alphabet.amino()
	pipeline = pyhmmer.plan7.Pipeline(pyhmmer.easel.Alphabet.amino())
	optimized_block = pyhmmer.plan7.OptimizedProfileBlock(alphabet=alphabet)
	for h in hmms:
		optimized_block.append(h.to_profile().to_optimized())

	# Get all domains in lists
	domainSNARE = nestedDictValues(tree)[0]
	groupSNARE = nestedDictValues(tree)[1]
	subgroupSNARE = [hmm for rank in nestedDictValues(tree) for hmm in nestedDictValues(tree)[rank] if rank >= 2]
	all_motifs = domainSNARE + groupSNARE + subgroupSNARE

	# Search sequences against hmm DB and store results in dictionary
	results = {}
	# If input is a file
	if os.path.isfile(input_sequences):

		with pyhmmer.easel.SequenceFile(input_sequences, digital=True) as seq_file:
			for digitalsequence in seq_file.read_block():
				hits = pipeline.scan_seq(digitalsequence, optimized_block)

				# Initialize results dictionary for each sequence
				results[hits.query_name] = {}
				for m in all_motifs:
					results[hits.query_name][m] = np.log(10e10)

				for hit in hits:
					for d in hit.domains:
						hit_name = hit.name.decode('utf-8')
						if hit_name in all_motifs:
							if d.pvalue < results[hits.query_name][hit_name]:
								results[hits.query_name][hit_name] = d.pvalue

	# If input is a sequence
	else:

		digitalsequence = pyhmmer.easel.TextSequence(name=bytes("Query_sequence", 'utf-8'), sequence=input_sequences).digitize(alphabet)
		hits = pipeline.scan_seq(digitalsequence, optimized_block)

		results[hits.query_name] = {}
		for m in all_motifs:
			results[hits.query_name][m] = np.log(10e10)

		for hit in hits:
			for d in hit.domains:
				hit_name = hit.name.decode('utf-8')
				if hit_name in all_motifs:
					if d.pvalue < results[hits.query_name][hit_name]:
						results[hits.query_name][hit_name] = d.pvalue

	# Return results
	evals = {}
	for idx in results:
		evals[idx] = [results[idx][m] for m in all_motifs]
	return evals


#### Parse domtblout file to retrive evalues for each motif
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


#### Function to get all keys in a nested dictionary
def nestedDictValues(d, values=None, rank=0):
	if values is None:
		values = {}
	if not rank in values:
		values[rank] = []
	for k in d:
		if type(d[k]) is dict:
			values = nestedDictValues(d[k], values, rank + 1 if rank < 3 else rank)
		if not k in values[rank]:
			values[rank].append(k)
	return values


#### Function to predict domain and subdomain of a given sequence given the evalues obtained with hmmsearch
def motifPredictionFromEvals(evals, tree, probCutOff=60, domainfamily="SNARE"):

	def predictGroups(evals, tree, groupName="", probCutOff=probCutOff, results=None, iteration=None,
					  domainfamily="SNARE"):

		def probsToDict(model, evals):
			groups = model.classes_
			probs = model.predict_proba([evals])[0]
			probsDict = {}
			for i in range(len(groups)):
				probsDict[groups[i]] = probs[i] * 100
			return probsDict

		def nBest(model, evals, n):
			probsDict = probsToDict(model, evals)
			nProb = sorted(model.predict_proba([evals])[0])[-n] * 100
			nGroup = [x for x in probsDict if probsDict[x] == nProb][0]
			return [nGroup, nProb]

		lm_path = "utils/motifPredictor/lm_models/"
		labels = ["group", "subgroup", "subgroup_rank0", "subgroup_rank1", "subgroup_rank2"]
		if not results:
			results = {"domain": domainfamily}
			iteration = 0

		if iteration == 0:
			modelName = lm_path + "lm_%s_mainMotifs.sav" % (domainfamily)
		elif iteration == 1:
			modelName = lm_path + "lm_%s_%s.sav" % (domainfamily, results["group"])
		else:
			modelName = lm_path + "lm_%s_%s_rank%s.sav" % (domainfamily, results["subgroup"], str(iteration - 2))

		model = pickle.load(open(modelName, 'rb'))
		pred_group, pred_group_prob = nBest(model, evals, 1)
		results[labels[iteration]] = pred_group
		results[labels[iteration] + "_prob"] = pred_group_prob
		if pred_group_prob < probCutOff:
			sug_pred_group, sug_pred_group_prob = nBest(model, evals, 2)
			results["sug_" + labels[iteration]] = sug_pred_group
			results["sug_" + labels[iteration] + "_prob"] = sug_pred_group_prob

		if pred_group in tree and tree[pred_group]:
			predictGroups(evals, tree[pred_group], pred_group, probCutOff=probCutOff, results=results,
						  iteration=iteration + 1, domainfamily=domainfamily)

		return results

	# Prediction
	results = predictGroups(evals, tree)
	return results


#### Formatting for printing results
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
	printOut += '# Prediction\n\tDomain: %s \n\t' % (results['domain'])  # , color(results['domain_prob']))

	if "sug_group" in results and results["sug_group"]:
		printOut += 'Group: %s (%s) [Suggested: %s (%s)]\n\tSubgroup: %s (%s)\n\t' % (
		results['group'], color(results['group_prob']), results['sug_group'], color(results['sug_group_prob']),
		results['subgroup'], color(results['subgroup_prob']))
	else:
		printOut += 'Group: %s (%s)\n\tSubgroup: %s (%s)\n\t' % (
		results['group'], color(results['group_prob']), results['subgroup'], color(results['subgroup_prob']))
		for x in results:
			if "rank" in x and not "prob" in x:
				printOut += '%s: %s (%s)\n\t' % (x, results[x], color(results[x + "_prob"]))

	if "sug_subgroup" in results and results["sug_subgroup"]:
		printOut += ' [Suggested: %s (%s)]\n\n' % (results['sug_subgroup'], color(results['sug_subgroup_prob']))
	else:
		printOut += '\n\n'

	return printOut


#### Prediction and formatting of results combined
def formatMotifPrediction(evals, tree, probCutOff=60, domainfamily="SNARE"):
	print(formatPrediction(motifPredictionFromEvals(evals, tree, probCutOff=probCutOff, domainfamily=domainfamily)))


#### PREDICTION FUNCTION
def motifPrediction(input, hmm_file="utils/motifPredictor/HmmDb/SNAREDb.hmm", probCutOff=60, tree=SNARETree):

	# Search HMMs
	evals = searchHMMs(input, hmm_file, tree)

	# Make predictions
	predictions = {}
	for seqId in evals:
		predictions[seqId.decode(encoding="utf-8")] = motifPredictionFromEvals(evals[seqId], tree, probCutOff=probCutOff)

	return predictions


# Test
if __name__ == '__main__':

	### Get all domains in lists
	domainSNARE = nestedDictValues(SNARETree)[0]
	groupSNARE = nestedDictValues(SNARETree)[1]
	subgroupSNARE = [hmm for rank in nestedDictValues(SNARETree) for hmm in nestedDictValues(SNARETree)[rank] if rank >= 2]
	allSNARE = domainSNARE + groupSNARE + subgroupSNARE

	fastaFile = "test.fasta"
	hmmDB = "hmms/SNAREDb.hmm"
	domain = "SNARE"

	results = motifPrediction(fastaFile)

	for seqId in results:
		print(formatPrediction(results[seqId]))
