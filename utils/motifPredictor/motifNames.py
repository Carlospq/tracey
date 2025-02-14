SNARETree = {'Qa': {'Qa.I': {'Qa.I.Syx18': {"Qa.I.Syx18.Metazoa": '',
											"Qa.I.Syx18.SAR": '',
											"Qa.I.Syx18.Viridiplantae": ''},
							 'Qa.I.Ufe1': ''},
					'Qa.II': {'Qa.II.Sed5': '',
							  'Qa.II.Syx5': {'Qa.II.Syx5.Metazoa': '',
											 'Qa.II.Syx5.SAR': '',
											 'Qa.II.Syx5.Viridiplantae': ''}},
					'Qa.III': {'Qa.III.a': '',
							   'Qa.III.b': ''},
					'Qa.IV': {'Qa.IV.Sso': '',
							  'Qa.IV.Syx': ''}},
			 'Qb': {'Qb.I': {'Qb.I.Metazoa': '',
							 'Qb.I.Viridiplantae': '',
							 'Qb.I.Fungi': ''},
					'Qb.II': {'Qb.II.Gos': {'Qb.II.Gos.Gos2': '',
											'Qb.II.Gos.Fungi': '',
											'Qb.II.Gos.Viridiplantae': ''},
							  'Qb.II.MemBos': {'Qb.II.MemBos.Bos1': '',
											   'Qb.II.MemBos.Membrin': ''}},
					'Qb.III': {'Qb.III.b': {'Qb.III.b.Metazoa': '',
											'Qb.III.b.SAR': '',
											'Qb.III.b.Viridiplantae': '',
											'Qb.III.b.Fungi': ''},
							   'Qb.III.d': ''}},
			 'Qc': {'Qc.I': {'Qc.I.Fungi': '',
							 'Qc.I.Metazoa': '',
							 'Qc.I.Viridiplantae': ''},
					'Qc.II': {'Qc.II.Bet1': '',
							  'Qc.II.Sft1': ''},
					'Qc.III': {'Qc.III.b': {'Qc.III.b.Fungi': '',
											'Qc.III.b.Metazoa': '',
											'Qc.III.b.Syp7': ''},
							   'Qc.III.c': {'Qc.III.c.Syp5': '',
											'Qc.III.c.Syx8': '',
											'Qc.III.c.Vam7': ''}}},
			 'R': {'R.I': {'R.I.Fungi': '',
						   'R.I.Metazoa': '',
						   'R.I.Viridiplantae': ''},
				   'R.II': '',
				   'R.III': {'R.III.Nyv1': '',
							 'R.III.Vamp7': '',
							 'R.III.Vamp4': '',
							 'R.III.Endob': ''},
				   'R.IV': {'R.IV.Fungi': '',
							'R.IV.Metazoa': ''},
				   'R.Reg': {'R.Reg.Fungi': '',
							 'R.Reg.Metazoa': '',
							 'R.Reg.Viridiplantae': ''}},
			 'SNAP': {'SNAP.b': {'SNAP.b.Sec9': '',
								 'SNAP.b.SN25': '',
								 'SNAP.b.SN29': ''},
					  'SNAP.c': {'SNAP.c.Sec9': '',
								 'SNAP.c.SN25': '',
								 'SNAP.c.SN29': ''}}
			 }

HabcTree = {'Ha': {'Ha.I': ['Ha.I.Syx18', 'Ha.I.Ufe1'],
				   'Ha.II': '',
				   'Ha.III': ['Ha.III.a', 'Ha.III.b'],
				   'Ha.IV': ['Ha.IV.Sso', 'Ha.IV.Syx']},
			'Hb': {'Hb.I': '',
				   'Hb.II': ['Hb.II.Bos1', 'Hb.II.Gos1', 'Hb.II.Membrin'],
				   'Hb.III': ['Hb.III.b', 'Hb.III.d']},
			'Hc': {'Hc.I': '',
				   'Hc.III': ['Hc.III.b', 'Hc.III.c']},
			'Hr': {'Hr.I': '',
				   'Hr.II': '',
				   'Hr.III': ''}
			}

SNAREp2d = [{'Qa.I.Syx18': 'Ha.I-Syx18'},
			{'Qa.I.Ufe1': 'Ha.I-Ufe1'},
			{'Qa.I.Syx18.Metazoa': 'Ha.I-Syx18'},
			{'Qa.I.Syx18.SAR': 'Ha.I-Syx18'},
			{'Qa.I.Syx18.Viridiplantae': 'Ha.I-Syx18'},

			{'Qa.II.Sed5': 'Ha.II-Sed5'},
			{'Qa.II.Syx5': 'Ha.II-Syx5'},
			{'Qa.II.Syx5.Metazoa': 'Ha.II-Syx5'},
			{'Qa.II.Syx5.SAR': 'Ha.II-Syx5'},
			{'Qa.II.Syx5.Viridiplantae': 'Ha.II-Syx5'},

			{'Qa.IV.Sso': 'Ha.IV-Qa.IV'},
			{'Qa.IV.Syx': 'Ha.IV-Qa.IV'},

			{'Qb.I.Metazoa': 'Hb.I-Qb.I'},
			{'Qb.I.Viridiplantae': 'Hb.I-Qb.I'},
			{'Qb.I.Fungi': 'Hb.I-Qb.I'},

			{'Qb.II.Bos1': 'Hb.II.b-Bos1'},
			{'Qb.II.Gos1': 'Hb.II.a-Gos1'},
			{'Qb.II.Membrin': 'Hb.II.b-Membrin'},
			{'Qb.II.Gos': 'Hb.II.a-Gos1'},
			{'Qb.II.Gos.Gos2': 'Hb.II.a-Gos28'},
			{'Qb.II.Gos.Fungi': 'Hb.II.a-Gos1'},
			{'Qb.II.Gos.Viridiplantae': 'Hb.II.a-Gos1'},
			{'Qb.II.MemBos': 'Hb.II.b-Bos1'},
			{'Qb.II.MemBos.Bos1': 'Hb.II.b-Bos1'},
			{'Qb.II.MemBos.Membrin': 'Hb.II.b-Membrin'},

			{'Qb.III.b.Metazoa': 'Hb.III-Qb.III.b'},
			{'Qb.III.b.SAR': 'Hb.III-Qb.III.b'},
			{'Qb.III.b.Viridiplantae': 'Hb.III-Qb.III.b'},
			{'Qb.III.b.Fungi': 'Hb.III-Qb.III.b'},

			{'Qc.I.Fungi': 'Hc.I-Qc.I'},
			{'Qc.I.Metazoa': 'Hc.I-Qc.I'},
			{'Qc.I.Viridiplantae': 'Hc.I-Use1'},

			{'Qc.II.Bet1': 'Qc.II'},
			{'Qc.II.Sft1': 'Qc.II'},

			{'Qc.III.b.Fungi': 'Hc.III.b-Qc.III.b'},
			{'Qc.III.b.Metazoa': 'Hc.III.b-Qc.III.b'},
			{'Qc.III.b.Syp7': 'Hc.III.b-Qc.III.b'},
			{'Qc.III.c.Syp5': 'Hc.III.c-Qc.III.c'},
			{'Qc.III.c.Syx8': 'Hc.III.c-Qc.III.c'},
			{'Qc.III.c.Vam7': 'Hc.III.c-Qc.III.c'},

			{'R.I.Fungi': 'R.I'},
			{'R.I.Metazoa': 'R.I'},
			{'R.I.Viridiplantae': 'R.I'},
			{'R.III.Nyv1': 'R.III'},
			{'R.III.Vamp7': 'R.III'},
			{'R.III.Vamp4': 'R.III'},
			{'R.III.Endob': 'R.III'},
			{'R.IV.Fungi': 'R.IV'},
			{'R.IV.Metazoa': 'R.IV'},
			{'R.Reg.Fungi': 'LGL-R.reg'},
			{'R.Reg.Metazoa': 'LGL-R.reg'},
			{'R.Reg.Viridiplantae': 'LGL-R.reg'},

			{'SNAPb': 'SNAP.b-SNAP.c'},
			{'SNAPc': 'SNAP.b-SNAP.c'},
			{'SNAP.b.Sec9': 'Sec9.b-Sec9.c'},
			{'SNAP.b.SN25': 'SNAP25.b-SNAP25.c'},
			{'SNAP.b.SN29': 'SNAP29.b-SNAP29.c'},
			{'SNAP.c.Sec9': 'Sec9.b-Sec9.c'},
			{'SNAP.c.SN25': 'SNAP25.b-SNAP25.c'},
			{'SNAP.c.SN29': 'SNAP29.b-SNAP29.c'}
		]

def createDomaingroup(dgName, dgKey, domainfamily, analysislevel):
	print("Creating %s" % (dgName), dgKey)
	d = Domains.objects.get(domainname=domainfamily)
	with open('utils/hmmModels/SNARE/%s' % (dgName + ".hmm"), 'r') as hmm_file:
		dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])
	dg = Domaingroups(domaingroupname=dgName,
					  domaingrouplength=dgLen,
					  domain=d,
					  domaingroupparent_id=dgKey.domaingroup_id,
					  analysislevel=analysislevel,
					  softcutoff=1.0,
					  strictcutoff=1.0)
	dg.save()
	return dg

def defineNewDomaingroups(tree, domainfamily="SNARE", parent=None, analysislevel=2):

	for dgKeyName in tree:
		if not any(Domaingroups.objects.filter(domaingroupname=dgKeyName)):
			dgParent = createDomaingroup(dgKeyName, parent, domainfamily, analysislevel)
		else:
			dgParent = Domaingroups.objects.get(domaingroupname=dgKeyName)

		if tree[dgKeyName]:
			defineNewDomaingroups(tree[dgKeyName], domainfamily, parent=dgParent, analysislevel=analysislevel+1)


if __name__ == "__main__":
	# Create new Domaingroups
	defineNewDomaingroups(SNARETree)
	# defineNewDomaingroups(HabcTree, domainfamily="Habc")

	# Create new entries for P2dmapping
	for p2d in SNAREp2d:
		dg = Domaingroups.objects.get(domaingroupname=list(p2d.keys())[0])
		plg = Proteinlayoutgroups.objects.get(proteinlayoutgroupname=list(p2d.values())[0])
		if not any(P2Dmapping.objects.filter(domaingroup=dg)):
			p2d = P2Dmapping(domaingroup=dg, proteinlayoutgroup=plg, position=1)
			p2d.save()
		print(dg, plg)
