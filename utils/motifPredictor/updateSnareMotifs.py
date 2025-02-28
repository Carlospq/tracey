import os, pyhmmer
from apps.templates.menus.query_sequences import *
import subprocess

def countGaps(alignment):
	gaps = []
	count = 0
	gapInitialPosition = 0
	for i in range(len(alignment)):
		if alignment[i] == "-":
			if gapInitialPosition == 0:
				gapInitialPosition = i
			count += 1
		else:
			if count > 0:
				gaps.append("%s:%s" % (gapInitialPosition, count))
			count = 0
			gapInitialPosition = 0
	if count > 0:
		gaps.append("%s:%s" % (gapInitialPosition, count))
	return ", ".join(gaps)

########################################################################################################################################################
seq_ids = Motifs.objects.filter(domaingroup__domain__domainname='SNARE').values('sequence_id')
seqs = Sequences.objects.filter(sequence_id__in=seq_ids, sequencestatus="live")
analyzed_sequences = []
# sp = "MuMu"
# seqs = Sequences.objects.filter(taxonomy__taxonomyshortname=sp)

n=1
for sequence in seqs:

	print(n, sequence)
	n += 1

	if sequence in analyzed_sequences: continue

	for m in sequence.motifs_set.all():
		if not m.domaingroup.domain.domainname in ["SNARE", "Habc"]: continue

		hmmpath = 'utils/hmmModels/%s/' % m.domaingroup.domain.domainname.upper()

		# - collect hmm names from menu
		hmms = [m.domaingroup.domaingroupname]
		split_name = m.domaingroup.domaingroupname.split(".")
		d = menu['SNARE'][m.domaingroup.domain.domainname]
		for i in range(len(split_name)):
			try:
				d = d[".".join(split_name[:i+1])]
			except:
				pass
		if d:
			hmms += get_keys_recursively(d)

		print(m.domaingroup.domaingroupname, hmms)

		# - prepare DB for specific HMMs
		tmpHMMdb = "utils/motifPredictor/tmpHMMdb.hmmDb"
		with open(tmpHMMdb, "w") as f:
			for hmm in hmms:
				try:
					f.write(open(hmmpath + hmm + ".hmm").read())
				except FileNotFoundError:
					pass
		cmd = "hmmpress -f %s" % tmpHMMdb
		subprocess.call(cmd, shell=True, stdout=open(os.devnull, 'wb'))

		# Scan sequence for all motifs in TRACEY
		with pyhmmer.plan7.HMMFile(tmpHMMdb) as hmm_file:
			alphabet = pyhmmer.easel.Alphabet.amino()
			proteins = [pyhmmer.easel.TextSequence(name=b"Query sequence", sequence=sequence.sequence.strip()).digitize(alphabet)]
			all_hits = pyhmmer.hmmer.hmmscan(proteins, hmm_file, E=1e-0, F1=1, F2=1, F3=1)

		hits_d = {}
		for hits in all_hits:
			pass
			for h in hits:

				h_name = h.name.decode()

				for d in h.domains:

					# Continue if a best hit for same dg is already in hits_d
					if h_name in hits_d and d.pvalue > hits_d[h_name]['pvalue']: continue

					if "RF\n" in str(d.alignment):
						dg_name = str(d.alignment).split("RF\n")[1].split()[0]
					else:
						dg_name = str(d.alignment).split("\n")[0].split()[0]

					dg = [d for d in Domaingroups.objects.filter(domaingroupname=dg_name)][0]

					# Continue if dg does not belong to SNARE
					# if not dg.domain.domainname == "SNARE": continue

					motif = Domains.objects.get(domain_id=dg.domain_id).domainname
					hits_d[h_name] = {'evalue': format(d.pvalue, '.1E'),
									  'pvalue': d.pvalue,
									  'env_from': d.env_from,
									  'env_to': d.env_to,
									  'length': d.env_to - d.env_from,
									  'alignment': d.alignment,
									  'dg': dg,
									  'motif': motif}

		# Get best hit
		best_hit = sorted(hits_d.items(), key=lambda x: x[1]['pvalue'])[0][1]
		if best_hit['dg'] == m.domaingroup: continue

		try:
			method = Methods.objects.get(domaingroup_id=Domaingroups.objects.get(domaingroupname=best_hit['dg']).domaingroup_id)
		except:
			method = Methods(domaingroup_id=Domaingroups.objects.get(domaingroupname=best_hit['dg']).domaingroup_id, input='', type='hmm', parameter='')
		method.save()
		asciioutput = '<asciiOutput>\r\t<consensus>%s</consensus>\r\t<similarity>%s\t</similarity>\r\t<motif>%s</motif>\r\t<eValue>%s</eValue>\r\t<bitscore>321</bitscore>\r</asciiOutput>' % (
			best_hit['alignment'].hmm_sequence, best_hit['alignment'].identity_sequence,
			best_hit['alignment'].target_sequence, best_hit['evalue'])

		new_snare_motif = Motifs(sequence = sequence,
								 motifname = best_hit['motif'],
								 startposition = best_hit['env_from'],
								 stopposition = best_hit['env_to'],
								 motifcomments = '',
								 domaingroup = best_hit['dg'],
								 gaps = countGaps(best_hit['alignment'].target_sequence),
								 active = 1,
								 method = method,
								 motifrank = 1000000,
								 asciioutput = asciioutput,
								 binaryoutput = '')
		new_verifymotif = Verifymotifs(sequence=m.sequence,
									   motifname=m.motifname,
									   startposition=m.startposition,
									   stopposition=m.stopposition,
									   verifymotifcomments=m.motifcomments,
									   domaingroup=m.domaingroup,
									   gaps=m.gaps,
									   active=0,
									   method=m.method,
									   verifymotifrank=m.motifrank,
									   asciioutput=m.asciioutput,
									   binaryoutput=m.binaryoutput)
		new_verifymotif.save()
		new_snare_motif.save()
		m.delete()

		analyzed_sequences.append(sequence)