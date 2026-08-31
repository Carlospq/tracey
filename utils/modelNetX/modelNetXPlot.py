import networkx as nx
from matplotlib import pyplot as plt

def get_children(model, parent, parent_id, child_parent_id, children=[], search_type='iexact'):
	variable_column = child_parent_id
	filter = variable_column + '__' + search_type
	cs = model.objects.none()
	for p in parent:
		children.append(p) if p not in children and p.analysislevel >= 2 else None
		if getattr(p, parent_id) == 4 and isinstance(p, Domaingroups):
			cs = cs.union(model.objects.filter( **{ variable_column+"__icontains" : ";4" }))
		else:
			cs = cs.union(model.objects.filter( **{ filter: getattr(p, parent_id) }))
	for c in cs:
		children.append(c)
		if model.objects.filter( **{ filter: getattr(c, parent_id) }):
			get_children(model, model.objects.filter(pk=c.pk), parent_id, child_parent_id, children=children)
	return(children)


def modelToGraph(model, instance_name, instance_id, instance_parent_id, queryset=None):
	"""
	Convert a model to a graph.
	:param model: TRACEY model
	:param instance_name: str (field name for instance_name)
	:param instance_id: str (field name for instance_id)
	:param instance_parent_id: str (field name for instance_parent_id)
	:return: networkx.Graph
	"""
	iterator = queryset if queryset else model.objects.all()
	G = nx.DiGraph()
	for instance in iterator:
		G.add_node( getattr(instance, instance_name), label=getattr(instance, instance_id))
		if getattr(instance, instance_parent_id):
			if ";" in getattr(instance, instance_parent_id):
				parent_instances = model.objects.filter(**{instance_id + "__in": getattr(instance, instance_parent_id).split(";")})
				for parent_instance in parent_instances:
					G.add_edge(getattr(instance, instance_name), getattr(parent_instance, instance_name))
			else:
				parent_instance = model.objects.get(**{instance_id: getattr(instance, instance_parent_id)})
				G.add_edge(getattr(instance, instance_name), getattr(parent_instance, instance_name))
	return G


def plotGraph(G, pos=None, plot_size=10, node_size=500, node_color='blue', node_shape='o', alpha=0.5, edge_color='black', with_labels=True):
	"""
	Plot a graph using networkx and matplotlib.
	:param G: networkx.Graph
	:param pos: dict
	:param node_size: int
	:param node_color: str
	:param node_shape: str
	:param alpha: float
	:param edge_color: str
	:param with_labels: bool
	:return: None
	"""
	if pos is None:
		pos = nx.spring_layout(G)
	nx.draw_networkx(G, pos, node_size=node_size, node_color=node_color, node_shape=node_shape, alpha=alpha, edge_color=edge_color, with_labels=with_labels)
	nx.draw_networkx_edges(G, pos, arrows=True)
	plt.rcParams["figure.figsize"] = (plot_size, plot_size)
	plt.show()


def graphToTSV(G, filename):
	"""
	Write a graph to a TSV file.
	:param G: networkx.Graph
	:param filename: str
	:return: None
	"""
	with open(filename, 'w') as f:
		f.write('node1\tnode2\n')
		for edge in G.edges:
			f.write('%s\t%s\n'%(edge[0], edge[1]))


# Example
Qa = Domaingroups.objects.filter(domaingroupname="Qa")
QaDomaingroups = get_children(Domaingroups, Qa, "domaingroup_id", "domaingroupparent_id", children=[], search_type='iexact')
G = modelToGraph(Domaingroups, 'domaingroupname', 'domaingroup_id', 'domaingroupparent_id', queryset=QaDomaingroups)
graphToTSV(G, 'graph.tsv')
plotGraph(G)
