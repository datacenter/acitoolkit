#!/usr/bin/env python
import acitoolkit
import inspect
from graphviz import Digraph


def build_graph_from_parent(root_parent_name):
    def clean_name(name):
        graphviz_illegal_node_names = ['Node']
        if name in graphviz_illegal_node_names:
            name += '_'
        return name

    def get_child_edges(edges, parent_name):
        resp = []
        for edge in edges:
            (edge_parent_name, child_class_name) = edge
            if edge_parent_name == parent_name:
                resp.append(edge)
                child_edges = get_child_edges(edges, child_class_name)
                # Combine child_edges and resp with some list/set magic to take only the unique edges
                resp = list(set(resp) - set(child_edges)) + child_edges
        return resp

    nodes = []
    edges = []

    graph = Digraph(name='ACI Toolkit Class Hierarchy', comment='ACI Toolkit Class Hierarchy', format='pdf')
    graph.node_attr.update(color='lightblue2', style='filled')
    graph.edge_attr.update(arrowhead='none')

    for name, obj in inspect.getmembers(acitoolkit):
        if inspect.ismodule(obj):
            for class_name, class_obj in inspect.getmembers(obj):
                class_name = clean_name(class_name)
                if inspect.isclass(class_obj):
                    get_parent_class = getattr(class_obj, "_get_parent_class", None)
                    if callable(get_parent_class):
                        try:
                            parent_class = class_obj._get_parent_class()
                            if class_name not in nodes:
                                nodes.append(class_name)
                            if isinstance(parent_class, list):
                                for parent in parent_class:
                                    parent_name = clean_name(parent.__name__)
                                    if (parent_name, class_name) not in edges:
                                        edges.append((parent_name, class_name))
                            elif parent_class is not None:
                                parent_name = clean_name(parent_class.__name__)
                                if (parent_name, class_name) not in edges:
                                    edges.append((parent_name, class_name))
                        except NotImplementedError:
                            pass

    subgraph_nodes = []

    # Get the edges starting from the root_parent_name as the parent node
    subgraph_edges = get_child_edges(edges, root_parent_name)

    # Derive the nodes from the edges
    for subgraph_edge in subgraph_edges:
        (parent_name, class_name) = subgraph_edge
        if parent_name not in subgraph_nodes:
            subgraph_nodes.append(parent_name)
        if class_name not in subgraph_nodes:
            subgraph_nodes.append(class_name)

    # Fill in the graph
    for subgraph_node in subgraph_nodes:
        graph.node(subgraph_node, subgraph_node)
    for subgraph_edge in subgraph_edges:
        (parent_name, class_name) = subgraph_edge
        graph.edge(parent_name, class_name)

    graph.render('acitoolkit-hierarchy.%s.tmp.gv' % root_parent_name)

    output_file = open('acitoolkit-hierarchy.%s.gv' % root_parent_name, 'w')
    output_file.write('.. graphviz::\n\n')
    with open('acitoolkit-hierarchy.%s.tmp.gv' % root_parent_name, 'r') as input_file:
        for line in input_file:
            output_file.write('    ' + line)
    output_file.close()


def build_graphs():
    build_graph_from_parent('Fabric')
    build_graph_from_parent('PhysicalModel')
    build_graph_from_parent('LogicalModel')


if __name__ == '__main__':
    try:
        build_graphs()
    except KeyboardInterrupt:
        pass
