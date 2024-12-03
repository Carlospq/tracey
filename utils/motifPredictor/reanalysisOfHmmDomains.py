# Reanalyse SNARE and Habc domains with new HMM models

# Importing necessary libraries
import os, subprocess
import pyhmmer

import xml.etree.ElementTree as ET
from utils.motifPredictor.predictor import *

# Ignore UserWarnings from sklearn for importing models from a diferent version than current python package
import warnings
from sklearn.exceptions import *
warnings.filterwarnings("ignore", category=UserWarning)

# Global variables
cwd_path = os.getcwd()+"/utils/motifPredictor/"
all_motifs = ['Ha.I', 'Ha.II', 'Ha.III', 'Ha.IV', 'Hb.I', 'Hb.II', 'Hb.III', 'Hc.I', 'Hc.III',
			  'Ha.I.Syx18', 'Ha.I.Ufe1', 'Ha.III.a', 'Ha.III.b', 'Ha.IV.Sso', 'Ha.IV.Syx',
			  'Hb.II.Bos1', 'Hb.II.Gos1', 'Hb.II.Membrin', 'Hb.III.b', 'Hb.III.d',
			  'Hc.III.b', 'Hc.III.c',
			  'Qa.I', 'Qa.II', 'Qa.III', 'Qa.IV', 'Qb.I', 'Qb.II', 'Qb.III', 'Qc.I', 'Qc.II', 'Qc.III', 'R.I',
			  'R.II', 'R.III', 'R.IV', 'R.Reg', 'SNAP',
			  'Qa.I.Syx18', 'Qa.I.Ufe1', 'Qa.II.Sed5', 'Qa.II.Syx5', 'Qa.III.a', 'Qa.III.b',
			  'Qa.IV.Sso', 'Qa.IV.Syx', 'Qb.II.Bos1', 'Qb.II.Gos1', 'Qb.II.Membrin',
			  'Qb.III.b', 'Qb.III.d', 'Qc.III.b', 'Qc.III.c', 'SNAPb', 'SNAPc'
			  ]
motif_tree = {'Ha.I': ['Ha.I.Syx18', 'Ha.I.Ufe1'],
			  'Ha.II': '',
			  'Ha.III': ['Ha.III.a', 'Ha.III.b'],
			  'Ha.IV': ['Ha.IV.Sso', 'Ha.IV.Syx'],
			  'Hb.I': '',
			  'Hb.II': ['Hb.II.Bos1', 'Hb.II.Gos1', 'Hb.II.Membrin'],
			  'Hb.III': ['Hb.III.b', 'Hb.III.d'],
			  'Hc.I': '',
			  'Hc.III': ['Hc.III.b', 'Hc.III.c'],
			  'Qa.I': ['Qa.I.Syx18', 'Qa.I.Ufe1'],
			  'Qa.II': ['Qa.II.Sed5', 'Qa.II.Syx5'],
			  'Qa.III': ['Qa.III.a', 'Qa.III.b'],
			  'Qa.IV': ['Qa.IV.Sso', 'Qa.IV.Syx'],
			  'Qb.I': '',
			  'Qb.II': ['Qb.II.Bos1', 'Qb.II.Gos1', 'Qb.II.Membrin'],
			  'Qb.III': ['Qb.III.b', 'Qb.III.d'],
			  'Qc.I': '',
			  'Qc.II': '',
			  'Qc.III': ['Qc.III.b', 'Qc.III.c'],
			  'R.I': '',
			  'R.II': '',
			  'R.III': '',
			  'R.IV': '',
			  'R.Reg': '',
			  'SNAP': ['SNAPb', 'SNAPc'],
			  'SNAREa.I': ['SNAREa.I.Syx18', 'SNAREa.I.Ufe1', 'SNAREa.II.Sed5', 'SNAREa.II.Syx5', 'SNAREa.III.a', 'SNAREa.III.b', 'SNAREa.IV.Sso', 'SNAREa.IV.Syx'],
			  'SNAREa.II': ['SNAREa.II.Sed5', 'SNAREa.II.Syx5', 'SNAREa.III.a', 'SNAREa.III.b'],
			  'SNAREa.III': ['SNAREa.III.a', 'SNAREa.III.b'],
			  'SNAREa.IV': ['SNAREa.IV.Sso', 'SNAREa.IV.Syx'],
			  'SNAREb.I': ['SNAREb.II.Bos1', 'SNAREb.II.Gos1', 'SNAREb.II.Membrin', 'SNAREb.III.b', 'SNAREb.III.d'],
			  'SNAREb.II': ['SNAREb.II.Bos1', 'SNAREb.II.Gos1', 'SNAREb.II.Membrin', 'SNAREb.III.b', 'SNAREb.III.d'],
			  'SNAREb.III': ['SNAREb.III.b', 'SNAREb.III.d'],
			  'SNAREc.I': ['SNAREc.III.b', 'SNAREc.III.c'],
			  'SNAREc.III': ['SNAREc.III.b', 'SNAREc.III.c']
			  }

# Functions
def retriveEvalues(domtbloutFile, all_motifs):
	results = {}
	with open(domtbloutFile, 'r') as f:
		for line in f:
			if line.startswith("#"): continue
			line = line.strip().split()
			seq_name = line[0]
			hmm_name = line[3]
			# evalue = np.log(float(line[12]))
			evalue = float(line[12])
			if hmm_name not in all_motifs: continue
			if seq_name not in results:
				results[seq_name] = {}
				for m in all_motifs:
					results[seq_name][m] = np.log(10e10)
			if evalue < results[seq_name][hmm_name]:
				results[seq_name][hmm_name] = evalue
	return results

# Collect SNARE sequences from the database
domain_names = ['SNARE', 'Habc']
ds = Domains.objects.filter(domainname__in=domain_names)
dgs = Domaingroups.objects.filter(domain__in=ds)
ms = Motifs.objects.filter(domaingroup__in=dgs)
sequences_ids = set([m.sequence_id for m in ms])
# sequences = Sequences.objects.filter(sequence_id__in=sequences_ids, sequencestatus="live")

# Create a fasta file with the sequences
fasta_file = f'{cwd_path}SNARE_Habc.fasta'
# with open(fasta_file, 'w') as f:
# 	for s in sequences:
# 		sequence_header = f'>{s.sequenceshortname}|{";".join([m.domaingroup.domaingroupname for m in s.motifs_set.all()])}\n'
# 		f.write(sequence_header + s.sequence.replace("-","").replace("+","") + '\n')

# Run the HMM models
hmm_db = f'{cwd_path}HmmDb/hmmDb.hmm'
output_file = f'{cwd_path}SNARE_Habc.domtblout'
cmd = f'hmmsearch --domtblout {output_file} {hmm_db} {fasta_file}'
# out, error = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

# Retrieve the e-values
results = retriveEvalues(output_file, all_motifs)

# Compare results with current motifs information (update when new result is better)
for seq_id in results:

	seq_name = seq_id.split("|")[0]
	seq_motifs = seq_id.split("|")[1].split(";")
	sequence = Sequences.objects.filter(sequenceshortname=seq_name, sequencestatus="live")

	if len(sequence) == 0:
		print("Sequence not found")
		continue
	elif len(sequence) == 1:
		sequence = sequence[0]
	else:
		print("Multiple sequences found", seq_name)
		continue

	for m in seq_motifs:

		current_motif = [motif for motif in sequence.motifs_set.all() if motif.domaingroup.domaingroupname == m][0]
		current_domain = current_motif.domaingroup.domain.domainname
		current_motif_data = {}
		for x in ET.fromstring(current_motif.asciioutput):
			current_motif_data[x.tag] = x.text
		current_motif_data['startposition'] = current_motif.startposition
		current_motif_data['stopposition'] = current_motif.stopposition

		prediction = predictMotifs(current_motif_data['motif'].strip().replace("-",""), probCutOff=90)
		if not prediction['group'] == m:
			print("Group", m, prediction['group'], prediction['subgroup'])
			break
		if not m in prediction['subgroup']:
			print("Subgroup", m, prediction['group'], prediction['subgroup'])
			break

		# Check if there is submotif with better score than motif
		if m in motif_tree:
			for submotif in motif_tree[m]:
				if results[seq_id][submotif] < results[seq_id][m]:
					m2 = submotif
					break
				else:
					m2 = m

		# Create new motif if new result is better and set old motif as not verify
		if results[seq_id][m2] < float(current_motif_data['eValue']):

			# TODO: Check if old prediction is group/subgroup. If new is subgroups and old is group, replace with new

			# Align sequence with HMM motif
			alphabet = pyhmmer.easel.Alphabet.amino()
			seq1 = pyhmmer.easel.TextSequence(name=b"Query sequence", sequence=sequence.sequence).digitize(alphabet)

			with pyhmmer.plan7.HMMFile('utils/hmmModels/%s/%s.hmm'%(current_domain.upper(), m2)) as hmm_file:
				hmm = hmm_file.read()
			optimized_block = pyhmmer.plan7.OptimizedProfileBlock(alphabet=alphabet)
			optimized_block.append(hmm.to_profile().to_optimized())
			pipeline = pyhmmer.plan7.Pipeline(pyhmmer.easel.Alphabet.amino())
			hits = pipeline.scan_seq(seq1, optimized_block)

			for h in hits:
				for d in h.domains:

					# Parse alignment
					split_alignment = [x.strip() for x in str(d.alignment).strip().split("\n")]
					consensus = split_alignment[0].split()[-2]
					similarity = split_alignment[1].split()[0]
					motif = split_alignment[2].split()[-2]
					pvalue = "{:.3g}".format(d.pvalue)

					asciioutput = f'<asciiOutput><bitscore>{round(d.score,2)}</bitscore><eValue>{pvalue}</eValue><consensus>{consensus}</consensus><similarity>{similarity}</similarity><motif>{motif}</motif></asciiOutput>'

					# Create new method if it does not exist
					try:
						method = Methods.objects.get(domaingroup_id = Domaingroups.objects.get(domaingroupname=m2).domaingroup_id)
					except:
						method = Methods(domaingroup_id = Domaingroups.objects.get(domaingroupname=m2).domaingroup_id,
										 input ='',
										 type = 'hmm',
										 parameter = '')
						method.save()

					# Create new motif
					new_motif = Motifs(sequence = sequence,
									   motifname = h.name.decode(encoding="utf-8"),
									   startposition = d.env_from,
									   stopposition = d.env_to,
									   motifcomments = 'Motif reanalysed with new SNARE HMM model',
									   domaingroup = Domaingroups.objects.get(domaingroupname=m2),
									   gaps = motif.count("-"),
									   active = 1,
									   method = method,
									   motifrank = 1000000,
									   asciioutput = asciioutput,
									   binaryoutput = b''
									   )
					new_motif.save()

					# Mark old motif as not active
					current_motif.active = 0
					current_motif.save()

					# TODO: convert old motif into verifymotif

					break
				break

	sequence.save()
	break