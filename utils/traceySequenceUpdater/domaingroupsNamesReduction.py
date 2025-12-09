# Run code when run as script
# python manage.py shell < utils/traceySequenceUpdater/domaingroupsNamesReduction.py

#! Script adapted only for SNARE and Habc domaingroups

if __name__ == "django.core.management.commands.shell":

	from apps.home.models import *

	# Remove old domaingroups that don't have an hmm associated to them
	domaingroupsNames = {'Qa.I': ['Syx18', 'Ufe1'],
						 'Qa.II': ['Syx5', 'Sed5', 'Syp3-plants'],
						 'Qa.III.a': ['Syx16', 'Tlg2', 'Syp4-plants'],
						 'Qa.III.b': ['Syx7', 'Syx13', 'Pep12', 'Syp2-plants', 'Syx17', 'Syx20'],
						 'Qa.IV': ['Syx1', 'Sso', 'Syp1-plants', 'Proto'],
						 'Qb.I': ['Sec20'],
						 'Qb.II': ['Bos1', 'Gos1', 'Membrin', 'Gos28'],
						 'Qb.III.b': ['Vti1'],
						 'Qb.III.d': ['Npsn'],
						 'Qc.I': ['Use1'],
						 'Qc.II': ['Bet1', 'Sft1', 'Gs15'],
						 'Qc.III.b': ['Syx6', 'Tlg1', 'Syp5'],
						 'Qc.III.c': ['Vam7', 'Syx8', 'Syp7', 'Syp6', 'Syx6-like'],
						 'R.I': ['Sec22', 'Sec22like'],
						 'R.II': ['Ykt6'],
						 'R.III': ['Vamp7', 'Nyv1', 'Endobrevin', 'Vamp4'],
						 'R.IV': ['Syb', 'Snc', 'Myobrevin'],
						 'R.Reg': ['Tomosyn', 'Amisyn'],
						 'SNAP.b': ['SNAP25.b', 'SNAP29.b', 'SNAP-plant.b', 'SNAP47.b', 'Sec9.b'],
						 'SNAP.c': ['SNAP25.c', 'SNAP29.c', 'SNAP-plants.c', 'SNAP47.c', 'Sec9.c']
						 }

	# new_fullsequence_domaingroups = {'SNAREa.I': ['SNAREa.I.Syx18', 'SNAREa.I.Ufe1'],
	# 								 'SNAREa.II': ['SNAREa.II.Sed5', 'SNAREa.II.Syx5'],
	# 								 'SNAREa.III': ['SNAREa.III.a', 'SNAREa.III.b'],
	# 								 'SNAREa.IV': ['SNAREa.IV.Sso', 'SNAREa.IV.Syx'],
	# 								 'SNAREb.I': [],
	# 								 'SNAREb.II': ['SNAREb.II.Bos1', 'SNAREb.II.Gos1', 'SNAREb.II.Membrin'],
	# 								 'SNAREb.III': ['SNAREb.III.b', 'SNAREb.III.d'],
	# 								 'SNAREc.I': [],
	# 								 'SNAREc.III': ['SNAREc.III.b', 'SNAREc.III.c']}

	for dgKeyName in domaingroupsNames:
		dgKey = Domaingroups.objects.get(domaingroupname=dgKeyName)
		for dgName in domaingroupsNames[dgKeyName]:
			dg = Domaingroups.objects.get(domaingroupname=dgName)
			for m in dg.motifs_set.all():
				m.domaingroup = dgKey
				m.domaingroup_id = dgKey.domaingroup_id
				m.save()


	# Add new domaingroups matching SNARE/Habc HMMs
	hmmPath = "utils/hmmModels"
	HabcHMMs = [f.replace('.hmm', '') for f in os.listdir(os.path.join(hmmPath, 'HABC')) if f.endswith('.hmm')]
	snareHMMs = [f.replace('.hmm', '') for f in os.listdir(os.path.join(hmmPath, 'SNARE')) if f.endswith('.hmm')]
	allHMMs = HabcHMMs + snareHMMs
	new_domaingroups = {'Habc': {}, 'SNARE': {}}


	# - Generate Dictionary with new domaingroups // dict{domaingroup_parent: [domaingroup_children], ...}
	for hmm in allHMMs:
		domain = "Habc" if hmm.startswith('H') else "SNARE"
		if hmm.count(".") == 0:
			continue
		else:
			dg_parent = ".".join(hmm.split(".")[:-1])
			if not dg_parent in new_domaingroups[domain]:
				new_domaingroups[domain][dg_parent] = []
			new_domaingroups[domain][dg_parent].append(hmm)

	# Recursive function to generate nested dictionary from domaingroup list
	def generate_dictionary(dg_list, dictionary=None, level=None):

		level = level if level is not None else 0
		dictionary = dictionary if dictionary is not None else {}

		dg_names = [dg_name for dg_name in dg_list if dg_name.count(".") == level]
		for dg_name in dg_names:
			dictionary[dg_name] = {}
			sub_dg_list = [sub_dg_name for sub_dg_name in dg_list if sub_dg_name.startswith(dg_name + ".")]
			if len(sub_dg_list) > 0:
				dictionary[dg_name] = generate_dictionary(sub_dg_list, dictionary=dictionary[dg_name], level=level + 1)

		return dictionary


	habc_dg_dictionary = generate_dictionary([hmm for hmm in allHMMs if hmm.startswith('H')])
	snare_dg_dictionary = generate_dictionary([hmm for hmm in allHMMs if not hmm.startswith('H')])

	# For Habc / SNARE domaingroups - Add new domaingroups to TRACEY
	def generate_domaingroup(dict_obj, dg_parent_name, level=None):

		level = level if level is not None else 1
		domain = Domains.objects.get(domainname='Habc' if dg_parent_name.startswith('H') else 'SNARE')

		for dg_name in dict_obj:
			dg_parent = Domaingroups.objects.get(domaingroupname=dg_parent_name)

			# Create domaingroup if it doesn't exist
			if not any(Domaingroups.objects.filter(domaingroupname=dg_name)):
				print('Creating domaingroup:', dg_name)
				hmmFilePath = 'utils/hmmModels/%s/%s.hmm' % (domain.domainname.upper(), dg_name)

				with open(hmmFilePath, 'r') as hmm_file:
					dg_len = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])

				dg = Domaingroups(domaingroupname=dg_name,
								  domaingrouplength=dg_len,
								  domain=domain,
								  domaingroupparent_id=dg_parent.domaingroup_id,
								  analysislevel=level,
								  softcutoff=1.0,
								  strictcutoff=1.0)
				dg.save()
			# Recursive call for child domaingroups
			generate_domaingroup(dict_obj[dg_name], dg_name, level=level + 1)

	# Generate Habc domaingroups
	generate_domaingroup(habc_dg_dictionary, "Habc")
	# Generate SNARE domaingroups
	generate_domaingroup(snare_dg_dictionary, "SNARE")




	# For fullsequence HabcSNARE domaingroups
	# d = Domains.objects.get(domainname="SNARE")
	# dgSNARE = Domaingroups.objects.get(domaingroupname="SNARE")
	# for dgKeyName in new_fullsequence_domaingroups:
	#
	# 	if not any(Domaingroups.objects.filter(domaingroupname=dgKeyName)):
	# 		with open('utils/hmmModels/SNARE/%s' % (dgKeyName + ".hmm"), 'r') as hmm_file:
	# 			dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])
	# 		dgKey = Domaingroups(domaingroupname=dgKeyName,
	# 							 domaingrouplength=dgLen,
	# 							 domain=d,
	# 							 domaingroupparent_id=135,
	# 							 analysislevel=3,
	# 							 softcutoff=1.0,
	# 							 strictcutoff=1.0)
	# 		dgKey.save()
	# 	else:
	# 		dgKey = Domaingroups.objects.get(domaingroupname=dgKeyName)
	#
	# 	for dgName in new_fullsequence_domaingroups[dgKeyName]:
	# 		if not any(Domaingroups.objects.filter(domaingroupname=dgName)):
	# 			with open('utils/hmmModels/SNARE/%s' % (dgName + ".hmm"), 'r') as hmm_file:
	# 				dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])
	# 			dg = Domaingroups(domaingroupname=dgName,
	# 							  domaingrouplength=dgLen,
	# 							  domain=d,
	# 							  domaingroupparent_id=dgKey.domaingroup_id,
	# 							  analysislevel=5,
	# 							  softcutoff=1.0,
	# 							  strictcutoff=1.0)
	# 			dg.save()