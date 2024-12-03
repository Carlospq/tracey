# Run code when run as script
# python manage.py shell < utils/traceySequenceUpdater/domaingroupsNamesReduction.py

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

	for dgKeyName in domaingroupsNames:
		dgKey = Domaingroups.objects.get(domaingroupname=dgKeyName)
		for dgName in domaingroupsNames[dgKeyName]:
			dg = Domaingroups.objects.get(domaingroupname=dgName)
			for m in dg.motifs_set.all():
				m.domaingroup = dgKey
				m.domaingroup_id = dgKey.domaingroup_id
				m.save()


	# Add new domaingroups matching new SNARE HMMs
	new_domaingroups = {'Habc': {'Ha.I': ['Ha.I.Syx18', 'Ha.I.Ufe1'],
								 'Ha.II': [],
								 'Ha.III': ['Ha.III.a', 'Ha.III.b'],
								 'Ha.IV': ['Ha.IV.Sso', 'Ha.IV.Syx'],
								 'Hb.I': [],
								 'Hb.II': ['Hb.II.Bos1', 'Hb.II.Gos1', 'Hb.II.Membrin'],
								 'Hb.III': ['Hb.III.b', 'Hb.III.d'],
								 'Hc.I': [],
								 'Hc.III': ['Hc.III.b', 'Hc.III.c']},
						'SNARE': {'Qa.I': ['Qa.I.Syx18', 'Qa.I.Ufe1'],
								  'Qa.II': ['Qa.II.Sed5', 'Qa.II.Syx5'],
								  'Qa.III': ['Qa.III.a', 'Qa.III.b'],
								  'Qa.IV': ['Qa.IV.Sso', 'Qa.IV.Syx'],
								  'Qb.I': [],
								  'Qb.II': ['Qb.II.Bos1', 'Qb.II.Gos1', 'Qb.II.Membrin'],
								  'Qb.III': ['Qb.III.b', 'Qb.III.d'],
								  'Qc.I': [],
								  'Qc.II': [],
								  'Qc.III': ['Qc.III.b', 'Qc.III.c'],
								  'R.I': [],
								  'R.II': [],
								  'R.III': [],
								  'R.IV': [],
								  'R.Reg': [],
								  'SNAP': ['SNAPb', 'SNAPc']}
						}
	new_fullsequence_domaingroups = {'SNAREa.I': ['SNAREa.I.Syx18', 'SNAREa.I.Ufe1'],
									 'SNAREa.II': ['SNAREa.II.Sed5', 'SNAREa.II.Syx5'],
									 'SNAREa.III': ['SNAREa.III.a', 'SNAREa.III.b'],
									 'SNAREa.IV': ['SNAREa.IV.Sso', 'SNAREa.IV.Syx'],
									 'SNAREb.I': [],
									 'SNAREb.II': ['SNAREb.II.Bos1', 'SNAREb.II.Gos1', 'SNAREb.II.Membrin'],
									 'SNAREb.III': ['SNAREb.III.b', 'SNAREb.III.d'],
									 'SNAREc.I': [],
									 'SNAREc.III': ['SNAREc.III.b', 'SNAREc.III.c']}


	# For Habc / SNARE domaingroups
	for dKeyName in new_domaingroups:
		d = Domains.objects.get(domainname=dKeyName)
		for dgKeyName in new_domaingroups[dKeyName]:
			if dgKeyName == 'SNAP':
				dgKey = Domaingroups.objects.get(pk=4)
			else:
				dgKey = Domaingroups.objects.get(domaingroupname=dgKeyName)
			for dgName in new_domaingroups[dKeyName][dgKeyName]:
				if not any(Domaingroups.objects.filter(domaingroupname=dgName)):
					with open('utils/hmmModels/SNARE/%s' % (dgName + ".hmm"), 'r') as hmm_file:
						dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])
					dg = Domaingroups(domaingroupname=dgName,
									  domaingrouplength=dgLen,
									  domain=d,
									  domaingroupparent_id=dgKey.domaingroup_id,
									  analysislevel=5,
									  softcutoff=1.0,
									  strictcutoff=1.0)
					dg.save()

	# For fullsequence HabcSNARE domaingroups
	d = Domains.objects.get(domainname="SNARE")
	dgSNARE = Domaingroups.objects.get(domaingroupname="SNARE")
	for dgKeyName in new_fullsequence_domaingroups:

		if not any(Domaingroups.objects.filter(domaingroupname=dgKeyName)):
			with open('utils/hmmModels/SNARE/%s' % (dgKeyName + ".hmm"), 'r') as hmm_file:
				dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])
			dgKey = Domaingroups(domaingroupname=dgKeyName,
								 domaingrouplength=dgLen,
								 domain=d,
								 domaingroupparent_id=135,
								 analysislevel=3,
								 softcutoff=1.0,
								 strictcutoff=1.0)
			dgKey.save()
		else:
			dgKey = Domaingroups.objects.get(domaingroupname=dgKeyName)

		for dgName in new_fullsequence_domaingroups[dgKeyName]:
			if not any(Domaingroups.objects.filter(domaingroupname=dgName)):
				with open('utils/hmmModels/SNARE/%s' % (dgName + ".hmm"), 'r') as hmm_file:
					dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])
				dg = Domaingroups(domaingroupname=dgName,
								  domaingrouplength=dgLen,
								  domain=d,
								  domaingroupparent_id=dgKey.domaingroup_id,
								  analysislevel=5,
								  softcutoff=1.0,
								  strictcutoff=1.0)
				dg.save()