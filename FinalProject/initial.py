from gurobipy import *
import networkx as nx
import matplotlib .pyplot as plt
from geopy.distance import vincenty

"""
Implement Pairing SDN with Network Virtualization paper.

Constraints:
Hypervisor for nodes Q


Three objective functions:
Minimize maximum latency w
Minimize average latency L_avg
Minimize maximum-average latency w

For all virtual networks, for all nodes within the virtual network:
Place hv at n, calculate distance[n -> c] + distance[n -> v]
(shortest path from hypervisor to controller + hypervisor to all other nodes, for all nodes)
Find the smallest max

Task for Thursday 17th:
Brute force above method

"""

G = nx.read_gml('AttModified.gml')

m = Model('HypervisorModel')

Q = 1

"""
Add lengths/latencies to links, use longitude/latitude
Virtual node at 23, 13, 18, 7, 4, 6
Controller at 17

Find HV that gives min max latency (distance between nodes)
"""

possible_nodes = {'LA03': G.node['LA03'], 'CHCG': G.node['CHCG'], 'WASH': G.node['WASH'], 'CLEV': G.node['CLEV'], 'RLGH': G.node['RLGH'], 'DLLS': G.node['DLLS']}
controller_node = G.node['SNFN']
sum = 0

# Add the length of each edge with the Vincenty function in GeoPy
for i,j in G.edges():
    i_coord = (G.node[i]['Latitude'], G.node[i]['Longitude'])
    j_coord = (G.node[j]['Latitude'], G.node[j]['Longitude'])
    G.edge[i][j]['length'] = vincenty(i_coord, j_coord).miles
print("Edge measurements are reported in miles.\n")

sum_list = {}
# Find all of the shortest paths using Dijkstra's algorithm
path = nx.all_pairs_dijkstra_path(G, weight='length')

for name in G.nodes(): # <- For running all nodes as virtual nodes.
# for name, v in possible_nodes.items():
    for n in path[name]:
        for city in path[name][n]:
            if name != city:
                if city in G[name]:
                    el = G.edge[name][city]['length']
                    sum += el
                elif name in G[city]:
                    el = G.edge[city][name]['length']
                    sum += el
    sum_list[name] = sum
    print('%s: %s' % (name, sum))
    sum = 0

min_length = min(sum_list.items(), key=lambda x: x[1])
print('\nMin Max Length is %s: %s' % (min_length[0], min_length[1]))

pos = {}
for v in nx.nodes(G):
    pos[v] = [G.node[v]['Longitude'], G.node[v]['Latitude']]

nx.draw(G, pos)

nx.draw_networkx_nodes(G, pos, node_size=800, node_shape='s')
nx.draw_networkx_labels(G,pos,font_size=10,font_family='sans-serif',font_color='w')

plt.show()


def remove_attributes_ATT(G):
    for i,j in G.edges():
        del G.edge[i][j]['LinkLabel']

    for v in G.nodes():
        del G.node[v]['type']
        del G.node[v]['Country']
        del G.node[v]['Internal']

    nx.write_gml(G, 'AttModified.gml')

# remove_attributes_ATT(G)