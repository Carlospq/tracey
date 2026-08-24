# Run code when run as script
# python manage.py shell < utils/traceySequenceUpdater/updateDomainGroupsWithHMMs.py

if __name__ == "django.core.management.commands.shell":

	import os
	import pprint
	import importlib
	import sys

	from apps.home.models import *
	from apps.templates.menus.query_sequences_full import menu, get_keys_recursively
	from utils.traceySequenceUpdater.rebuildMotifsHmmDb import rebuild_motifs_hmmdb

	# Maps each HMM folder → (domain_name_in_DB, menu_path_list[, name_aliases_dict])
	# name_aliases: HMM basename → menu key it corresponds to (avoids adding duplicates
	# when the file name and the menu key differ in capitalisation).
	DOMAIN_CONFIG = {
		'SNARE':    ('SNARE',    ['SNARE', 'SNARE']),
		'HABC':     ('Habc',     ['SNARE', 'Habc']),
		'LONGIN':   ('Longin',   ['SNARE', 'Longin']),
		'LGL':      ('LGL',      ['SNARE', 'LGL']),
		'C2':       ('C2',       ['C2']),
		'AAA.AAA':  ('AAA',      ['AAA']),
		'AAA.ND':   ('AAA.ND',   ['AAA']),
		'RAS':      ('Ras',      ['Ras superfamily']),
		'ARF':      ('Arf',      ['Ras superfamily']),
		'MUN.D1':   ('MUN.D1',   ['MUN']),
		'MUN.D2':   ('MUN.D2',   ['MUN']),
		'NSR.CD':   ('NSR.CD',   ['NSR']),
		'NSR.MD':   ('NSR.MD',   ['NSR']),
		'NSR.ND':   ('NSR.ND',   ['NSR']),
		'PROPPIN':  ('Proppin',  ['Proppin']),
		'RHOMBOID': ('Rhomboid', ['Rhomboid']),
		'RINT':     ('Rint',     ['Rint']),
		'SM.D1':    ('SM.D1',    ['SM']),
		'SM.D2A':   ('SM.D2A',   ['SM']),
		'SM.D2B':   ('SM.D2B',   ['SM']),
		'SM.D3':    ('SM.D3',    ['SM']),
		'SNAP':     ('SNAP',     ['SNAP'],  {'aSnap': 'aSNAP', 'cSnap': 'cSNAP'}),
		'ZW10':     ('Zw10',     ['Zw10']),
		# ROD and SEC39 folders exist but have no menu entry yet — add manually when needed
	}

	# HMM basenames that should never be added to the menu automatically.
	# Use this for files whose naming does not match the menu convention (e.g. a
	# general HMM where the menu already has more specific named variants).
	HMM_BLACKLIST = {
		# SM: general Vps33/Vps45 HMMs — menu already uses Vps33a/Vps33b variants
		'Vps33.d1',
		'vps33.d2a',
		'vps33.d2b',
		'vps33.d3',
		'vps45.d2a',
		'vps45.d2b',
		'vps45.d3',
	}

	# ── helpers ──────────────────────────────────────────────────────────────────

	def get_nested(d, path):
		for key in path:
			d = d[key]
		return d

	def find_subtree_for_key(d, target):
		"""Returns the dict that directly contains 'target' as a key, or None."""
		if target in d:
			return d
		for v in d.values():
			if isinstance(v, dict):
				result = find_subtree_for_key(v, target)
				if result is not None:
					return result
		return None

	def add_with_dot_hierarchy(subtree, key_name):
		"""
		Adds key_name as a leaf {} to subtree.
		Infers parent from dot notation: 'Longin.V' → parent key 'Longin'.
		Falls back to top of subtree if no parent found.
		"""
		parts = key_name.rsplit('.', 1)
		if len(parts) == 2:
			parent_name = parts[0]
			parent_dict = find_subtree_for_key(subtree, parent_name)
			if parent_dict is not None:
				parent_dict[parent_name][key_name] = {}
				return
		subtree[key_name] = {}

	def sync_menu_with_hmms():
		"""
		Scans utils/hmmModels/ and adds to menu any HMM files not already present.
		Respects HMM_BLACKLIST and per-folder name aliases in DOMAIN_CONFIG.
		Returns True if the menu was modified.
		"""
		all_menu_keys = set(get_keys_recursively(menu))
		all_menu_keys_lower = {k.lower() for k in all_menu_keys}
		changed = False
		for folder, config in DOMAIN_CONFIG.items():
			domain_name, menu_path = config[0], config[1]
			aliases = config[2] if len(config) > 2 else {}
			folder_path = os.path.join('utils/hmmModels', folder)
			if not os.path.isdir(folder_path):
				continue
			hmm_names = {f[:-4] for f in os.listdir(folder_path) if f.endswith('.hmm')}
			to_add = []
			for hmm in sorted(hmm_names):
				if hmm in HMM_BLACKLIST:
					continue
				# Apply alias: check whether the canonical menu key already exists (case-insensitive)
				check_key = aliases.get(hmm, hmm)
				if check_key.lower() not in all_menu_keys_lower:
					to_add.append(hmm)
			if to_add:
				subtree = get_nested(menu, menu_path)
				for key in to_add:
					add_with_dot_hierarchy(subtree, key)
					print(f'  [+] {key}  →  menu{menu_path}')
					all_menu_keys.add(key)
					all_menu_keys_lower.add(key.lower())
				changed = True
		return changed

	def write_menu_to_file(menu_dict):
		"""
		Rewrites only the menu dict in query_sequences_full.py, preserving
		the helper functions that follow it.
		"""
		filepath = 'apps/templates/menus/query_sequences_full.py'
		with open(filepath, 'r') as f:
			content = f.read()
		helper_start = content.index('\ndef get_keys_recursively')
		helpers_block = content[helper_start:]
		formatted = pprint.pformat(menu_dict, indent=1, width=120, sort_dicts=False)
		with open(filepath, 'w') as f:
			f.write('menu = ' + formatted + '\n' + helpers_block)

	# ── core function ─────────────────────────────────────────────────────────────

	def updateDomainGroups(domaingroups_dict, domain, dgparent, alignmentlength=0, domaingrouplength=0):

		if not domaingroups_dict: return

		# Domain
		try:
			domain = Domains.objects.get(domainname=domain)
		except Domains.DoesNotExist:
			domain = Domains(domainname=domain, alignmentlength=alignmentlength, alignment='')
			domain.save()

		# Parent domaingroup
		try:
			dgparent = Domaingroups.objects.get(domaingroupname=dgparent, domain_id=domain.domain_id)
		except Domaingroups.DoesNotExist:
			dgparent = Domaingroups(domaingroupname=dgparent, domain_id=domain.domain_id,
									domaingrouplength=domaingrouplength, analysislevel=1,
									softcutoff=1.0, strictcutoff=1.0, mappingstring='')
			dgparent.save()

		# Add domaingroups for each HMM in the dict
		for dgKeyName in domaingroups_dict:

			if not Domaingroups.objects.filter(domaingroupname__iexact=dgKeyName):

				folder_name = domain.domainname.upper()
				try:
					with open('utils/hmmModels/%s/%s' % (folder_name, dgKeyName + '.hmm'), 'r') as hmm_file:
						dgLen = int([l.strip().split()[1] for l in hmm_file.readlines() if l.startswith('LENG')][0])
				except FileNotFoundError:
					dgLen = 0  # intermediate hierarchy node — no dedicated HMM file

				dg = Domaingroups(domaingroupname=dgKeyName,
								  domaingrouplength=dgLen,
								  domain=domain,
								  domaingroupparent_id=dgparent.domaingroup_id,
								  analysislevel=5,
								  softcutoff=1.0,
								  strictcutoff=1.0,
								  mappingstring='')
				dg.save()

			if domaingroups_dict[dgKeyName]:
				updateDomainGroups(domaingroups_dict[dgKeyName], domain.domainname, dgKeyName)

	# ── main ──────────────────────────────────────────────────────────────────────

	print('=== Sync HMMs → menu ===')
	changed = sync_menu_with_hmms()
	if changed:
		write_menu_to_file(menu)
		print('query_sequences_full.py updated.')
		importlib.reload(sys.modules['apps.templates.menus.query_sequences_full'])
		from apps.templates.menus.query_sequences_full import menu
	else:
		print('No new HMMs found.')

	print('=== Update DB domaingroups ===')
	for folder, config in DOMAIN_CONFIG.items():
		domain_name, menu_path = config[0], config[1]
		try:
			subtree = get_nested(menu, menu_path)
		except KeyError:
			print(f'  [!] menu path {menu_path} not found, skipping {folder}')
			continue
		print(f'  Processing {domain_name} ...')
		updateDomainGroups(subtree, domain=domain_name, dgparent=domain_name)

	print('=== Rebuild MOTIFS.hmmDb ===')
	rebuild_motifs_hmmdb()
