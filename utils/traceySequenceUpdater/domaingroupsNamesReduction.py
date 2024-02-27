# Run code when run as script
# python manage.py shell < utils\traceySequenceUpdater\domaingroupsNamesReduction.py

if __name__ == "django.core.management.commands.shell":

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

