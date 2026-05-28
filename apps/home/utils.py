import os
import hashlib
import json
import urllib.request
import urllib.error
import pandas as pd

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


def get_menu(request):
	return menu_full if request.user.is_staff else menu_public


def get_children(model, parent, parent_id, child_parent_id, children=None, search_type='iexact'):
	if children is None:
		children = []
	variable_column = child_parent_id
	filter = variable_column + '__' + search_type
	cs = model.objects.none()
	for p in parent:
		children.append(p) if p not in children and p.analysislevel >= 2 else None
		if getattr(p, parent_id) == 4 and isinstance(p, Domaingroups):
			cs = cs.union(model.objects.filter(**{variable_column + "__icontains": ";4"}))
		else:
			cs = cs.union(model.objects.filter(**{filter: getattr(p, parent_id)}))
	for c in cs:
		children.append(c)
		if model.objects.filter(**{filter: getattr(c, parent_id)}):
			get_children(model, model.objects.filter(pk=c.pk), parent_id, child_parent_id, children=children)
	return children


def get_sequences(query, verify=False, menu=None):
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
	with open('utils/tmp_files/seq_md5.txt', 'w') as temp_file:
		temp_file.write(sequence)
	seq_md5 = md5(temp_file.name)
	os.remove(temp_file.name)
	return seq_md5
