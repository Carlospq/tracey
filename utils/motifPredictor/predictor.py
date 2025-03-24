### README
# This script predicts the groups that a sequences belongs to using regression models
#
#
# INPUT: string
# 	- either a single protein sequence or
# 	- path to a fasta file with multiple protein sequences

import os, sys
import subprocess, tempfile
import pickle
import numpy as np

# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# from scripts.motifNames import *
from utils.motifPredictor.motifNames import *

#### hmmsearch on fasta file to obtain evalues for each motif
def searchHMMs(sequences_file, hmm_file, domtbloutPath):
	# Search sequences against hmm DB and store results in domtblout files
	cmd = "hmmsearch --domtblout %s --cpu 4 %s %s" % (domtbloutPath, hmm_file, sequences_file)
	out, error = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
	if error:
		print(error)


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
def domainPredict(evals, tree, probCutOff=60, domainfamily="SNARE"):
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

		labels = ["group", "subgroup", "subgroup_rank0", "subgroup_rank1", "subgroup_rank2"]
		if not results:
			results = {"domain": domainfamily}
			iteration = 0

		if iteration == 0:
			modelName = "./utils/motifPredictor/lm_models/lm_%s_mainMotifs.sav" % (domainfamily)
		elif iteration == 1:
			modelName = "./utils/motifPredictor/lm_models/lm_%s_%s.sav" % (domainfamily, results["group"])
		else:
			modelName = "./utils/motifPredictor/lm_models/lm_%s_%s_rank%s.sav" % (domainfamily, results["subgroup"], str(iteration - 2))

		model = pickle.load(open(modelName, 'rb'))
		pred_group, pred_group_prob = nBest(model, evals, 1)
		results[labels[iteration]] = pred_group
		results[labels[iteration] + "_prob"] = pred_group_prob
		if pred_group_prob < probCutOff:
			sug_pred_group, sug_pred_group_prob = nBest(model, evals, 2)
			results["sug_" + labels[iteration]] = sug_pred_group
			results["sug_" + labels[iteration] + "_prob"] = sug_pred_group_prob

		# if pred_group in tree:
		try:
			predictGroups(evals, tree[pred_group], pred_group, probCutOff=probCutOff, results=results,
						  iteration=iteration + 1, domainfamily=domainfamily)
		except:
			results = results

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
def snareMotifPrediction(evals, tree, probCutOff=60, domainfamily="SNARE"):
	print(formatPrediction(domainPredict(evals, tree, probCutOff=probCutOff, domainfamily=domainfamily)))


#### Write sequence into fasta file
def seqToFasta(seq, fastaFile, header="seq"):
	with open(fastaFile, 'w') as f:
		f.write(">%s\n%s\n" % (header, seq))


#### Prediction from fasta file
def predictFromFasta(fastaFile, hmmDB, SNARETree, probCutOff=80, domainfamily="SNARE", print_results=False):

	### Get all domains in lists
	domainSNARE = nestedDictValues(SNARETree)[0]
	groupSNARE = nestedDictValues(SNARETree)[1]
	subgroupSNARE = [hmm for rank in nestedDictValues(SNARETree) for hmm in nestedDictValues(SNARETree)[rank] if rank >= 2]
	allSNARE = domainSNARE + groupSNARE + subgroupSNARE

	new_file, domtblout = tempfile.mkstemp(dir="./utils/motifPredictor/tmp")
	searchHMMs(fastaFile, hmmDB, domtblout)
	evals = retriveEvalues(domtblout, allSNARE)
	os.remove(domtblout)

	results = {}
	for seqId in evals:
		seqEvals = [evals[seqId][x] for x in evals[seqId]]
		results[seqId] = domainPredict(seqEvals, SNARETree, probCutOff=probCutOff, domainfamily=domainfamily)
		print(evals)
		if print_results:
			print(formatPrediction(results))

	return results


#### Prediction from protein sequence
def predictFromSeq(sequence, SNARETree=SNARETree, hmmDB=None, seqName="Query_sequence", probCutOff=80, domainfamily="SNARE", print_results=False):

	if hmmDB == None:
		hmmDB = "./utils/motifPredictor/HmmDb/SNAREDb.hmm"

	new_file, tmpFasta = tempfile.mkstemp(dir="./utils/motifPredictor/tmp")
	seqToFasta(sequence, tmpFasta, header=seqName)

	results = predictFromFasta(tmpFasta, hmmDB, SNARETree, probCutOff=probCutOff, domainfamily=domainfamily, print_results=print_results)
	os.remove(tmpFasta)
	return results


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

	if not os.path.exists("utils/motifPredictor/tmp"):
		os.makedirs("tmp")

	new_file, domtblout = tempfile.mkstemp(dir="./utils/motifPredictor/tmp")
	searchHMMs(fastaFile, hmmDB, domtblout)
	evals = retriveEvalues(domtblout, allSNARE)
	os.remove(domtblout)

	for seqId in evals:
		seqEvals = [evals[seqId][x] for x in evals[seqId]]
		results = domainPredict(seqEvals, SNARETree, probCutOff = 60, domainfamily=domain)
		print(formatPrediction(results))








# domains = ["Qa", "Qb", "Qc", "R", "SNAPbc"]
# domains = Domaingroups.objects.filter(domain__domainname="SNARE", analysislevel=2)
# for domain in domains:
#
# 	print(domain)
#
# 	# collect motifs
# 	dg = Domaingroups.objects.get(domaingroupname=domain)
# 	children = getChildren(Domaingroups, [dg], "domaingroup_id", "domaingroupparent_id", childs=[], search_type='iexact')
# 	motifs = [m for dg in children for m in dg.motifs_set.all() if m.sequence.sequencestatus == "live"]
#
# 	# print motif sequence to fasta
# 	fasta = 'utils/motifPredictor/%s.fasta' % domain
# 	with open(fasta, 'w') as f:
# 		for motif in motifs:
# 			header = "%s/%s-%s" % (motif.sequence.sequenceshortname, motif.startposition, motif.stopposition)
# 			f.write(">%s\n%s\n" % (header, motif.sequence.sequence[motif.get_real_startposition()-1:motif.get_real_stopposition()]))



























