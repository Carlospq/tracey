#############################################
# Plot taxonomy tree/network for the specified Taxa
#############################################
import sys
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from apps.home.models import *

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

#############################################

class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument('scientificname')

	def plot_component(self, g, scientificname): #dictionary = {"hg38": "lightgreen", "mm39": "lightblue", "danrer11": "yellow"}):
		#org_color = dictionary
		fig,ax = plt.subplots(figsize=(8,8))
		nodes = g.nodes()
		edges = g.edges()
		edges_set = set(edges)
		bidirectional = [True if (v[1],v[0]) in edges_set else False for v in edges]
		edge_color = ['red' if x else 'gray' for x in bidirectional]
		# node_color = [org_color[x[0]] for x in nodes]
		node_color = ["lightblue" if x[1]==scientificname else "lightgreen" for x in nodes ]
		labels = {x:"_".join([x[1], str(x[3]), str(x[4])]) for x in nodes} ############### cambiar x[1] por tu_dictionary[x[1]]!
		pos=nx.spring_layout(g)
		nx.draw_networkx_nodes(g,pos,nodelist=nodes,node_color=node_color)
		nx.draw_networkx_edges(g,pos,edgelist=edges,edge_color=edge_color)
		nx.draw_networkx_labels(g,pos,labels,font_weight='bold')
		#plt.legend(handles=[mpatches.Patch(color=v, label=k) for k,v in org_color.items()],
		#		   bbox_to_anchor=(1, 1))
		plt.tight_layout()
		plt.axis('off')
		plt.margins(x=0.3, y=0.3)
		plt.title('Node name: scientificname_#sequences_#children')
		# plt.show()
		plt.savefig("graph.pdf")

	def add_taxonomies(self, taxonomy, ALL_NODES, EDGES, depth=0, depth_down=0):
		depth += 1
		if depth > 3 or depth_down > 1:
			return
		if taxonomy.taxonomyparent_id == 1:
			return

		_sequences = len(taxonomy.sequences_set.all())
		_children = len(Taxonomies.objects.filter(taxonomyparent_id=taxonomy.taxonomy_id))
		tax_node = (taxonomy.taxonomy_id, taxonomy.scientificname, taxonomy.taxonomyparent_id, _sequences, _children)
		if tax_node in ALL_NODES:
			return ALL_NODES, EDGES
		ALL_NODES.append(tax_node)

		parent_taxonomy = Taxonomies.objects.get(taxonomy_id=taxonomy.taxonomyparent_id)
		_parent_sequences = len(parent_taxonomy.sequences_set.all())
		_parent_children = len(Taxonomies.objects.filter(taxonomyparent_id=parent_taxonomy.taxonomy_id))
		parent_node = (parent_taxonomy.taxonomy_id, parent_taxonomy.scientificname, parent_taxonomy.taxonomyparent_id, _parent_sequences, _parent_children)

		edge = (tax_node, parent_node)
		if not edge in EDGES:
			EDGES.append(edge)

		self.add_taxonomies(parent_taxonomy, ALL_NODES, EDGES, depth=depth, depth_down=depth_down)
		if len(Taxonomies.objects.filter(taxonomyparent_id=taxonomy.taxonomy_id)) > 1:
			depth_down += 1
			for t in Taxonomies.objects.filter(taxonomyparent_id=taxonomy.taxonomy_id):
				self.add_taxonomies(t, ALL_NODES, EDGES, depth=1, depth_down=depth_down)
			depth_down = 0
		return ALL_NODES, EDGES

	def handle(self, *args, **options):
		### Generate clusters
		ALL_NODES = []
		EDGES = []

		taxonomies = Taxonomies.objects.filter(scientificname=options['scientificname'])
		for t in taxonomies:
			ALL_NODES, EDGES = self.add_taxonomies(t, ALL_NODES, EDGES, depth=0)

		G = nx.DiGraph()
		G.add_nodes_from(ALL_NODES)
		G.add_edges_from(EDGES, length = 10)
		G_undirected = G.to_undirected()

		components = sorted(list(G_undirected.subgraph(c) for c in nx.connected_components(G_undirected)),key=lambda x:-len(x))
		Gplot = G.subgraph(components[0])

		self.plot_component(Gplot, options['scientificname'])

