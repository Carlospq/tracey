import os
import hashlib
import uuid
import json
import urllib.request
import urllib.error
import urllib.parse
import pandas as pd
from Bio.Phylo.PhyloXML import Taxonomy

from django.core.cache import cache

from .models import *
from utils.ncbi_taxonomy.reducedTRACEYtaxonomies import *
from apps.templates.menus.query_sequences import menu as menu_public, get_keys_recursively, get_keys_level_recursively, get_dict
from apps.templates.menus.query_sequences_full import menu as menu_full


_taxonomy_df = None


def get_taxonomy_df():
	global _taxonomy_df
	if _taxonomy_df is None:
		_taxonomy_df = pd.read_csv('utils/phylogeneticTrees/taxonomies.csv', index_col=0)
	return _taxonomy_df


def get_alphafold_url(sequence):
	seq_md5 = md5_from_seq(sequence)
	cache_key = f'alphafold_{seq_md5}'
	result = cache.get(cache_key)
	if result is None:
		try:
			fetch3d = urllib.request.urlopen(
				f'https://alphafold.ebi.ac.uk/api/sequence/summary?id={seq_md5}&type=md5',
				timeout=10
			).read().decode('utf8')
			result = json.loads(fetch3d)['structures'][0]['summary']['model_url']
		except (urllib.error.HTTPError, urllib.error.URLError, KeyError, IndexError):
			result = False
		cache.set(cache_key, result, timeout=86400)
	return result


def get_wikipedia_image(scientific_name):
	if not scientific_name:
		return None

	def retrieve_wiki_img(key):
		try:
			name_encoded = urllib.parse.quote(key.replace(' ', '_'))
			url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{name_encoded}'
			req = urllib.request.Request(url, headers={'User-Agent': 'traceyDB/1.0 (carlospq88@gmail.com)'})
			data = urllib.request.urlopen(req, timeout=10).read().decode('utf8')
			parsed = json.loads(data)
			image_url = parsed.get('thumbnail', {}).get('source')
			page_url = parsed.get('content_urls', {}).get('desktop', {}).get('page')
			result = {'image_url': image_url, 'page_url': page_url} if image_url else False
			return result
		except Exception:
			return False

	# Try species name
	species_cache_key = f'wikipedia_img_{scientific_name.replace(" ", "_")}'
	result = cache.get(species_cache_key)
	if result is None:
		result = retrieve_wiki_img(scientific_name)
		cache.set(species_cache_key, result, timeout=86400)

	# Try parent taxonomy name as fallback
	if result is False:
		taxonomy = Taxonomies.objects.filter(scientificname=scientific_name).first()
		if taxonomy and taxonomy.taxonomyparent_id:
			parent = Taxonomies.objects.filter(taxonomy_id=taxonomy.taxonomyparent_id).first()
			if parent and parent.scientificname:
				parent_cache_key = f'wikipedia_img_{parent.scientificname.replace(" ", "_")}'
				result = cache.get(parent_cache_key)
				if result is None:
					result = retrieve_wiki_img(parent.scientificname)
					cache.set(parent_cache_key, result, timeout=86400)

	return result


def get_menu(request):
	return menu_full if request.user.is_staff else menu_public


def user_can_access_sequence(request, sequence):
	allowed_dg = set(get_keys_recursively(get_menu(request)))
	seq_dg_names = set(sequence.motifs_set.values_list('domaingroup__domaingroupname', flat=True))
	return seq_dg_names.issubset(allowed_dg)


def get_children(model, parent, parent_id, child_parent_id, children=None, search_type='iexact'):
	if children is None:
		children = []
	variable_column = child_parent_id
	filter = variable_column + '__' + search_type
	cs = model.objects.none()
	for p in parent:
		children.append(p) if p not in children and p.analysislevel >= 2 else None
		if getattr(p, parent_id) == 1018 and isinstance(p, Domaingroups):
			cs = cs.union(model.objects.filter(**{variable_column + "__icontains": ";4"}))
		else:
			cs = cs.union(model.objects.filter(**{filter: getattr(p, parent_id)}))
	for c in cs:
		children.append(c)
		if model.objects.filter(**{filter: getattr(c, parent_id)}):
			get_children(model, model.objects.filter(pk=c.pk), parent_id, child_parent_id, children=children)
	return children


def _apply_non_motif_filters(seqs, query):
	if 'aliases' in query and notEmpty(query, 'aliases'):
		seqs = seqs.filter(aliases__icontains=query['aliases'][0])
	if 'sequencestatus' in query and notEmpty(query, 'sequencestatus'):
		status = ['live' if query['sequencestatus'][0] == '1' else query['sequencestatus'][0]][0]
		seqs = seqs.filter(sequencestatus=status)
	if 'private' in query and notEmpty(query, 'private'):
		seqs = seqs.filter(private=query['private'][0])
	if 'shortname' in query and notEmpty(query, 'shortname'):
		taxonomies = [t for t in Taxonomies.objects.filter(taxonomyshortname__istartswith=query['shortname'][0])
					  if t.taxonomyshortname.lower() == query['shortname'][0].lower() or
					  t.taxonomyshortname.lower().startswith(query['shortname'][0].lower() + "_") or
					  t.taxonomyshortname.lower().startswith(query['shortname'][0].lower() + ".")]
		seqs = seqs.filter(taxonomy__in=taxonomies)
	if 'shortnamesearch' in query and notEmpty(query, 'shortnamesearch'):
		taxonomies = [t for t in Taxonomies.objects.filter(taxonomyshortname__icontains=query['shortnamesearch'][0])]
		seqs = seqs.filter(taxonomy__in=taxonomies)
	if 'taxonomy_ids' in query and notEmpty(query, 'taxonomy_ids'):
		ids = [int(x) for x in query['taxonomy_ids'] if x]
		all_tax_ids = set(ids)
		frontier = list(ids)
		while frontier:
			children = list(Taxonomies.objects.filter(taxonomyparent_id__in=frontier).values_list('taxonomy_id', flat=True))
			new_ids = [c for c in children if c not in all_tax_ids]
			all_tax_ids.update(new_ids)
			frontier = new_ids
		seqs = seqs.filter(taxonomy_id__in=all_tax_ids)
	if 'foreignannotation' in query and notEmpty(query, 'foreignannotation'):
		seqs = seqs.filter(foreignannotation__icontains=query['foreignannotation'][0])
	if 'species_list' in query:
		taxonomies_ids = [x.taxonomy_id for x in Taxonomies.objects.filter(scientificname__in=query['species_list'])]
		seqs = seqs.filter(taxonomy_id__in=taxonomies_ids)
	if 'taxonomy' in query and notEmpty(query, 'taxonomy'):
		query['taxonomy'] = list(filter(None, query['taxonomy']))
		taxonomy_name = [query['taxonomy'][-1]]
		df = get_taxonomy_df()
		reducedTaxonomyIDs = reducedTRACEYtaxonomies_ncbiIDs[taxonomy_name[0]]
		taxonomy_names = [x.scientificname for x in Taxonomies.objects.filter(ncbi_taxonomy_id__in=reducedTaxonomyIDs)]
		ncbi_taxonomy_ids = []
		for t in taxonomy_names:
			arr = list(df[(df.eq(t).any(axis=1))].index.values)
			ncbi_taxonomy_ids = ncbi_taxonomy_ids + arr
		taxonomy_ids = [x.taxonomy_id for x in Taxonomies.objects.filter(ncbi_taxonomy_id__in=ncbi_taxonomy_ids)]
		seqs = seqs.filter(taxonomy_id__in=taxonomy_ids)
	return seqs


def get_sequences(query, verify=False, menu=None, include_taxonomy_no_motifs=False):
	if menu is None:
		menu = menu_public

	if 'domainname' not in query and 'proteinlayout' not in query:
		return {'error': "At least one of 'Domain name' or 'Protein Layout' fields are required"}

	if 'domaingroup' in query and notEmpty(query, 'domaingroup'):
		domaingroup_list = [x.replace("-", "") for x in query['domaingroup']]
		domaingroups_parents = Domaingroups.objects.filter(domaingroupname__in=domaingroup_list)
		domaingroups_children = get_children(Domaingroups, domaingroups_parents, "domaingroup_id", "domaingroupparent_id", children=[])
		children_ids = [x.domaingroup_id for x in domaingroups_children] + [x.domaingroup_id for x in domaingroups_parents]
		domaingroups = Domaingroups.objects.filter(domaingroup_id__in=children_ids)

	elif 'domaingroup_rank' in query and notEmpty(query, 'domaingroup_rank'):
		dg_list = get_keys_recursively(menu[query['proteinlayout'][0]][query['domainname'][0]][query['domaingroup_rank'][0]]) + query['domaingroup_rank']
		domaingroups = Domaingroups.objects.filter(domaingroupname__in=dg_list)

	elif ('proteinlayout' in query and notEmpty(query, 'proteinlayout')) or ('domainname' in query and notEmpty(query, 'domainname')):
		if 'domainname' in query and notEmpty(query, 'domainname'):
			dg_list = get_keys_recursively(menu[query['proteinlayout'][0]][query['domainname'][0]]) + query['domainname']
			domaingroups = Domaingroups.objects.filter(domaingroupname__in=dg_list)
		elif 'proteinlayout' in query and notEmpty(query, 'proteinlayout'):
			dg_list = get_keys_recursively(menu[query['proteinlayout'][0]]) + query['proteinlayout']
			domaingroups = Domaingroups.objects.filter(domaingroupname__in=dg_list)

		if query['proteinlayout'][0] == "C2" or query['domainname'][0] == "C2 classical":
			domaingroups = domaingroups.union(Domaingroups.objects.filter(domaingroupname="C2"))

	else:
		domaingroups = Domaingroups.objects.all()

	motifs = Motifs.objects.filter(domaingroup_id__in=domaingroups.values('domaingroup_id'))
	seqs = Sequences.objects.filter(sequence_id__in=motifs.values('sequence_id'))

	if verify:
		verifymotifs = Verifymotifs.objects.filter(domaingroup_id__in=domaingroups.values('domaingroup_id'))
		verifyseqs = Sequences.objects.filter(sequence_id__in=verifymotifs.values('sequence_id'))
		if query['unverified'][0] == query['verified'][0]:
			seqs = seqs | verifyseqs
		if query['unverified'][0] == 'true' and query['verified'][0] == 'false':
			seqs = verifyseqs

	seqs = _apply_non_motif_filters(seqs, query)

	if include_taxonomy_no_motifs:
		taxonomy_filter_keys = ['taxonomy_ids', 'species_list', 'taxonomy', 'shortname', 'shortnamesearch']
		if any(notEmpty(query, k) for k in taxonomy_filter_keys):
			extra_seqs = _apply_non_motif_filters(Sequences.objects.all(), query)
			seqs = seqs | extra_seqs

	if len(seqs) > 4000 and not verify:
		return {'error': 'This query returned too many sequences (>4000). Please refine your search.'}
	return seqs.order_by('sequenceshortname')


def notEmpty(query, element):
	try:
		if query[element] in [[''], '', None]:
			return False
		else:
			return True
	except (KeyError, TypeError):
		return False


def md5(fname):
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


def md5_from_seq(sequence):
	path = 'utils/tmp_files/seq_md5_%s.txt' % uuid.uuid4().hex
	with open(path, 'w') as f:
		f.write(sequence)
	try:
		return md5(path)
	finally:
		os.remove(path)



def get_kingdom_stats():
	from django.db.models import Count
	# 1. Cargar árbol taxonómico en memoria (1 query)
	all_taxonomies = Taxonomies.objects.values(
		'taxonomy_id', 'taxonomyparent_id', 'taxonomyrank', 'scientificname'
	)
	children_map = {}
	taxonomy_info = {}
	for t in all_taxonomies:
		children_map.setdefault(t['taxonomyparent_id'], []).append(t['taxonomy_id'])
		taxonomy_info[t['taxonomy_id']] = t
	kingdoms = [t for t in taxonomy_info.values() if t['taxonomyrank'] == 'kingdom']
	# 2. Contar secuencias live con SNARE o HABC agrupadas por taxonomy_id (1 query)
	seq_counts = (
		Sequences.objects
		.filter(sequencestatus='live', motifs__motifname__in=['SNARE', 'HABC'])
		.values('taxonomy_id')
		.annotate(seq_count=Count('sequence_id', distinct=True))
	)
	seq_count_map = {row['taxonomy_id']: row['seq_count'] for row in seq_counts}
	# 3. BFS en memoria para cada reino; acumular todos los taxonomy_ids cubiertos
	result = []
	covered_tax_ids = set()
	for kingdom in kingdoms:
		all_ids = {kingdom['taxonomy_id']}
		frontier = [kingdom['taxonomy_id']]
		while frontier:
			next_frontier = []
			for tid in frontier:
				for child_id in children_map.get(tid, []):
					if child_id not in all_ids:
						all_ids.add(child_id)
						next_frontier.append(child_id)
			frontier = next_frontier
		covered_tax_ids.update(all_ids)
		total_seqs = sum(seq_count_map.get(tid, 0) for tid in all_ids)
		species_count = sum(1 for tid in all_ids if tid in seq_count_map)
		result.append({
			'kingdom': kingdom['scientificname'],
			'sequences': total_seqs,
			'species': species_count,
		})
	# 4. Secuencias sin reino asignado (SAR y otros grupos sin rank "kingdom")
	uncovered_tax_ids = set(seq_count_map.keys()) - covered_tax_ids
	result.append({
		'kingdom': 'No kingdom assigned',
		'sequences': sum(seq_count_map.get(tid, 0) for tid in uncovered_tax_ids),
		'species': len(uncovered_tax_ids),
	})
	return sorted(result, key=lambda x: x['sequences'], reverse=True)


def get_annotation_stats():
	from django.db.models import Count
	# 1. Dominios anotados por tipo (filas en Motifs, no secuencias)
	domain_counts = (
		Motifs.objects
		.filter(sequence__sequencestatus='live', motifname__in=['SNARE', 'HABC'])
		.values('motifname')
		.annotate(count=Count('motif_id'))
	)
	domains = {row['motifname']: row['count'] for row in domain_counts}
	# 2. Familias taxonómicas: subir el árbol hasta rank='family' para cada taxonomy_id
	all_tax_ids = list(
		Sequences.objects
		.filter(sequencestatus='live', motifs__motifname__in=['SNARE', 'HABC'])
		.values_list('taxonomy_id', flat=True)
		.distinct()
	)
	all_taxonomies = Taxonomies.objects.values('taxonomy_id', 'taxonomyparent_id', 'taxonomyrank', 'scientificname')
	parent_map = {}
	taxonomy_info = {}
	for t in all_taxonomies:
		parent_map[t['taxonomy_id']] = t['taxonomyparent_id']
		taxonomy_info[t['taxonomy_id']] = t
	def find_family(taxonomy_id):
		visited = set()
		current = taxonomy_id
		while current and current not in visited:
			visited.add(current)
			info = taxonomy_info.get(current)
			if info is None:
				break
			if info['taxonomyrank'] == 'family':
				return info['scientificname']
			current = parent_map.get(current)
		return None
	families = {find_family(tid) for tid in all_tax_ids if tid is not None}
	families.discard(None)
	return {
		'snare_domains': domains.get('SNARE', 0),
		'habc_domains': domains.get('Habc', 0),
		'total_domains': sum(domains.values()),
		'taxonomic_families': len(families),
	}


def diagnose_unclassified():
	"""Lista los taxones sin phylum, mostrando su linaje de ranks para identificar dónde clasificarlos."""
	from django.db.models import Count
	all_taxonomies = Taxonomies.objects.values(
		'taxonomy_id', 'taxonomyparent_id', 'taxonomyrank', 'scientificname'
	)
	parent_map = {}
	taxonomy_info = {}
	children_map = {}
	for t in all_taxonomies:
		parent_map[t['taxonomy_id']] = t['taxonomyparent_id']
		taxonomy_info[t['taxonomy_id']] = t
		children_map.setdefault(t['taxonomyparent_id'], []).append(t['taxonomy_id'])
	covered_tax_ids = set()
	for t in taxonomy_info.values():
		if t['taxonomyrank'] == 'kingdom':
			frontier = [t['taxonomy_id']]
			covered_tax_ids.add(t['taxonomy_id'])
			while frontier:
				next_frontier = []
				for tid in frontier:
					for child_id in children_map.get(tid, []):
						if child_id not in covered_tax_ids:
							covered_tax_ids.add(child_id)
							next_frontier.append(child_id)
				frontier = next_frontier
	seq_counts = (
		Sequences.objects
		.filter(sequencestatus='live', motifs__motifname__in=['SNARE', 'HABC'])
		.values('taxonomy_id')
		.annotate(seq_count=Count('sequence_id', distinct=True))
	)
	seq_count_map = {row['taxonomy_id']: row['seq_count'] for row in seq_counts}
	uncovered_tax_ids = set(seq_count_map.keys()) - covered_tax_ids
	def get_lineage(taxonomy_id):
		lineage = []
		visited = set()
		current = taxonomy_id
		while current and current not in visited:
			visited.add(current)
			info = taxonomy_info.get(current)
			if info is None:
				break
			lineage.append(f"{info['taxonomyrank']}:{info['scientificname']}")
			if info['taxonomyrank'] in ('superkingdom', 'kingdom'):
				break
			current = parent_map.get(current)
		return ' > '.join(reversed(lineage))
	unclassified = []
	for tid in uncovered_tax_ids:
		visited = set()
		current = tid
		has_phylum = False
		while current and current not in visited:
			visited.add(current)
			info = taxonomy_info.get(current)
			if info is None:
				break
			if info['taxonomyrank'] == 'phylum':
				has_phylum = True
				break
			current = parent_map.get(current)
		if not has_phylum:
			unclassified.append({
				'name': taxonomy_info[tid]['scientificname'],
				'rank': taxonomy_info[tid]['taxonomyrank'],
				'sequences': seq_count_map[tid],
				'lineage': get_lineage(tid),
			})
	unclassified.sort(key=lambda x: x['sequences'], reverse=True)
	for u in unclassified:
		print(f"[{u['sequences']:>4} seqs] {u['name']:35} ({u['rank']:15})  {u['lineage']}")
	print(f"\nTotal: {len(unclassified)} taxones / {sum(u['sequences'] for u in unclassified)} seqs")


def diagnose_kingdom_stats():
	from django.db.models import Count
	base_filter = {'motifs__motifname__in': ['SNARE', 'HABC']}
	# A. Total con filtro live (el que usa get_kingdom_stats)
	total_live = Sequences.objects.filter(sequencestatus='live', **base_filter).distinct().count()
	species_live = Sequences.objects.filter(sequencestatus='live', **base_filter).values('taxonomy_id').distinct().count()
	# B. Total sin filtro de status (para comparar con la cifra del manuscrito)
	total_all = Sequences.objects.filter(**base_filter).distinct().count()
	species_all = Sequences.objects.filter(**base_filter).values('taxonomy_id').distinct().count()
	# C. Secuencias con taxonomy_id NULL
	null_live = Sequences.objects.filter(sequencestatus='live', taxonomy_id__isnull=True, **base_filter).distinct().count()
	# D. Suma real del seq_count_map (lo que distribuye get_kingdom_stats entre kingdoms)
	seq_count_map_total = sum(
		row['seq_count'] for row in
		Sequences.objects.filter(sequencestatus='live', **base_filter)
		.values('taxonomy_id')
		.annotate(seq_count=Count('sequence_id', distinct=True))
	)
	# E. Secuencias en Verifymotifs con SNARE o HABC (no incluidas en get_kingdom_stats)
	verify_live = Sequences.objects.filter(
		sequencestatus='live',
		verifymotifs__motifname__in=['SNARE', 'HABC']
	).distinct().count()
	# F. Desglose por sequencestatus (para identificar qué status suman 18.811)
	status_breakdown = (
		Sequences.objects.filter(**base_filter)
		.values('sequencestatus')
		.annotate(
			seq_count=Count('sequence_id', distinct=True),
			species_count=Count('taxonomy_id', distinct=True),
		)
		.order_by('-seq_count')
	)
	print("=== Diagnóstico get_kingdom_stats ===")
	print(f"[A] Live + SNARE/HABC:               {total_live:>6} seqs  / {species_live:>5} species")
	print(f"[B] Todos status + SNARE/HABC:        {total_all:>6} seqs  / {species_all:>5} species")
	print(f"[C] Live + taxonomy NULL:              {null_live:>6} seqs")
	print(f"[D] Suma seq_count_map (distribuido):  {seq_count_map_total:>6} seqs")
	print(f"[E] Live en Verifymotifs SNARE/HABC:   {verify_live:>6} seqs")
	print(f"    Diff A-D (no distribuidas):         {total_live - seq_count_map_total:>6} seqs")
	print(f"    Diff manuscrito-A (18811-A):         {18811 - total_live:>6} seqs")
	print()
	print("[F] Desglose por sequencestatus:")
	running = 0
	for row in status_breakdown:
		running += row['seq_count']
		print(f"    {str(row['sequencestatus']):20}  {row['seq_count']:>6} seqs / {row['species_count']:>5} species  (acum: {running})")


def get_no_kingdom_by_phylum():
	from django.db.models import Count
	# 1. Cargar árbol taxonómico en memoria
	all_taxonomies = Taxonomies.objects.values(
		'taxonomy_id', 'taxonomyparent_id', 'taxonomyrank', 'scientificname'
	)
	children_map = {}
	parent_map = {}
	taxonomy_info = {}
	for t in all_taxonomies:
		children_map.setdefault(t['taxonomyparent_id'], []).append(t['taxonomy_id'])
		parent_map[t['taxonomy_id']] = t['taxonomyparent_id']
		taxonomy_info[t['taxonomy_id']] = t
	# 2. BFS hacia abajo desde cada reino para obtener covered_tax_ids
	covered_tax_ids = set()
	for t in taxonomy_info.values():
		if t['taxonomyrank'] == 'kingdom':
			frontier = [t['taxonomy_id']]
			covered_tax_ids.add(t['taxonomy_id'])
			while frontier:
				next_frontier = []
				for tid in frontier:
					for child_id in children_map.get(tid, []):
						if child_id not in covered_tax_ids:
							covered_tax_ids.add(child_id)
							next_frontier.append(child_id)
				frontier = next_frontier
	# 3. Conteo de secuencias live SNARE/HABC por taxonomy_id
	seq_counts = (
		Sequences.objects
		.filter(sequencestatus='live', motifs__motifname__in=['SNARE', 'HABC'])
		.values('taxonomy_id')
		.annotate(seq_count=Count('sequence_id', distinct=True))
	)
	seq_count_map = {row['taxonomy_id']: row['seq_count'] for row in seq_counts}
	# 4. Taxones sin reino que tienen secuencias
	uncovered_tax_ids = set(seq_count_map.keys()) - covered_tax_ids
	# 5. Para cada taxón, subir el árbol buscando phylum; si no hay, usar class como fallback
	def find_ancestor_rank(taxonomy_id, ranks):
		visited = set()
		current = taxonomy_id
		while current and current not in visited:
			visited.add(current)
			info = taxonomy_info.get(current)
			if info is None:
				break
			if info['taxonomyrank'] in ranks:
				return info['scientificname']
			current = parent_map.get(current)
		return 'Unclassified'
	# 6. Agrupar por phylum (con fallback a class)
	phylum_seqs = {}
	phylum_species = {}
	for tid in uncovered_tax_ids:
		phylum = find_ancestor_rank(tid, ['phylum', 'class'])
		phylum_seqs[phylum] = phylum_seqs.get(phylum, 0) + seq_count_map.get(tid, 0)
		phylum_species[phylum] = phylum_species.get(phylum, 0) + 1
	result = [
		{'phylum': p, 'sequences': phylum_seqs[p], 'species': phylum_species[p]}
		for p in phylum_seqs
	]
	return sorted(result, key=lambda x: x['sequences'], reverse=True)

