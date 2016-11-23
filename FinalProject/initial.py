from gurobipy import *
import networkx as nx
import matplotlib .pyplot as plt
from geopy.distance import vincenty
import random

"""

For all virtual networks, for all nodes within the virtual network:
Place hv at n, calculate distance[n -> c] + distance[n -> v]
(shortest path from hypervisor to controller + hypervisor to all other nodes, for all nodes)
Find the smallest max

Task for Thursday 17th:
Brute force above method

"""

G = nx.read_gml('AttModified.gml')

m = Model('HypervisorModel')

"""
Add lengths/latencies to links, use longitude/latitude
Virtual node at 23, 13, 18, 7, 4, 6
Controller at 17

Find HV that gives min max latency (distance between nodes)
"""

"""
do 200 times:
do for 140 networks, then optimize (find min max latency):
vnet generation:
- randomly pick vnode number 2...10                 -> rand range 2...10
- randomly pick locations for vnodes: uniform       -> take above, randomly pick from node list and remove to exclude duplicates
- randomly pick controller location                 -> random number within the node list
"""

# Add the length of each edge with the Vincenty function in GeoPy
for i,j in G.edges():
    i_coord = (G.node[i]['Latitude'], G.node[i]['Longitude'])
    j_coord = (G.node[j]['Latitude'], G.node[j]['Longitude'])
    G.edge[i][j]['length'] = vincenty(i_coord, j_coord).miles

print("Edge measurements are reported in miles.\n")

for x in range(0, 200):
    for y in range(0, 140):
        pass

virtual_nodes = {'ORLD': G.node['ORLD'], 'DLLS': G.node['DLLS'], 'WASH': G.node['WASH'], 'LA03': G.node['LA03']}
virtual_nodes_2 = {'PHLA': G.node['PHLA'], 'HSTN': G.node['HSTN'], 'DNVR': G.node['DNVR'], 'RLGH': G.node['RLGH']}
virtual_nodes_3 = {'SNAN': G.node['SNAN'], 'CHCG': G.node['CHCG'], 'NY54': G.node['NY54']}

controller_node = 'PHNX'
controller_node_2 = 'KSCY'
controller_node_3 = 'STLS'

def vnet_generator(G, n):
    vnet = {}
    vnodes = []
    nodes_list = G.nodes()
    random.shuffle(nodes_list)
    for x in range(0, n):
        vnodes.append(nodes_list[x])
    vnet['vnodes'] = vnodes
    vnet['controller'] = G.nodes()[random.randrange(0, len(G.nodes()))]
    return vnet

v_list = []
# for x in range(0, 140):
#     num_nodes = random.randrange(2, 11)
#     v_dict = vnet_generator(G, num_nodes)
#     v_list.append(v_dict)

virtual_networks = []
controllers = []

virtual_networks.append(virtual_nodes)
virtual_networks.append(virtual_nodes_2)
virtual_networks.append(virtual_nodes_3)
controllers.append(controller_node)
controllers.append(controller_node_2)
controllers.append(controller_node_3)

sum_list = {}
# Find all of the shortest paths using Dijkstra's algorithm
# path = nx.all_pairs_dijkstra_path(G, weight='length')

# Find all of the shortest paths using the Floyd-Warshall algorithm
fw_path = nx.floyd_warshall(G, weight='length')

freq_dict = {}

v3_list = []
for i in range(0,3):
    temp_dict = {}
    temp_dict['controller'] = controllers[i]
    temp_dict['vnodes'] = virtual_networks[i]
    v3_list.append(temp_dict)

nodes_cost = {}
controller_count = 0
for vnet in v3_list:
    for name in G.nodes():
        sum = 0
        max_length = 0
        for v in vnet['vnodes']:
            sum = fw_path[name][vnet['controller']] + fw_path[name][v]
            if sum > max_length:
                max_length = sum
        sum_list[name] = max_length
        # print('%s: %s' % (name, max_length))
        if name in nodes_cost:
            if nodes_cost[name] < max_length:
                nodes_cost[name] = max_length
        else:
            nodes_cost[name] = max_length
    controller_count += 1
    min_length = min(sum_list.items(), key=lambda x: x[1])
    if min_length[0] in nodes_cost:
        if nodes_cost[min_length[0]] < min_length[1]:
            nodes_cost[min_length[0]] = min_length[1]
    else:
        nodes_cost[min_length[0]] = min_length[1]
    # print('\nNetwork %s\nMin Max Length is %s: %s' % (controller_count, min_length[0], min_length[1]))
    if min_length[0] in freq_dict:
        freq_dict[min_length[0]] += 1
    else:
        freq_dict[min_length[0]] = 1

# print(sorted(freq_dict.items(), key=operator.itemgetter(1), reverse=True))
sorted_answer = sorted(nodes_cost.items(), key=operator.itemgetter(1), reverse=False)
print('Min Max Latency: %s %s' % (sorted_answer[0][0], sorted_answer[0][1]))
print(sorted_answer)

# # # Below uses the Dijkstra approach # # #
# for name in G.nodes():
#     for n in path[name]:
#         # import pdb
#         # pdb.set_trace()
#         for city in path[name][n]:
#             if name != city and len(path[name][n]) > 1 and (path[name][n][-1] in virtual_nodes or path[name][n][-1] == controller_node):
#                     if city in G[name]:
#                         el = G.edge[name][city]['length']
#                         sum += el
#                     elif name in G[city]:
#                         el = G.edge[city][name]['length']
#                         sum += el
#     sum_list[name] = sum
#     print('%s: %s' % (name, sum))
#     sum = 0
#
# min_length = min(sum_list.items(), key=lambda x: x[1])
# print('\nMin Max Length is %s: %s' % (min_length[0], min_length[1]))


"""
Implement the model in Gurobi

Implement Pairing SDN with Network Virtualization paper.

Constraints:
Hypervisor for nodes Q


Three objective functions:
Minimize maximum latency w
Minimize average latency L_avg
Minimize maximum-average latency w
"""

Q = 1
num_sim = 50
num_vnets = 10

for x in range(0, num_vnets):
    num_nodes = random.randrange(2, 11)
    v_dict = vnet_generator(G, num_nodes)
    v_list.append(v_dict)

# hvselector[mdv]*(latency[controller[m]][v] + latency[v][d]) for v in nodes <= MaxLatency

# Variables
hypervisors = {}
for v in G. nodes():
    hypervisors[v] = m.addVar(name='hypervisors_%s' % v)

demand_vn = {}
for v in G.nodes():
    demand_vn[v] = m.addVar(name='demand_vn_%s_' % v)

# y_m,d,v in paper
y_mdv = {}
for m in v_list:
    for d in vnet['nodes']:
        for v in G.nodes():
            y[m,d,v] = m.addVar(name='y_%s_%s_%s' % (m,d,v))


# x_v in paper
possible_hv = {}
for v in G.nodes():
    possible_hv[v] = m.addVar(vtype=GRB.BINARY, name='possible-hv_%s' % v)

# z_w,v in paper
phys_node_hv = {}
for w in G.nodes():
    for v in G.nodes():
        phys_node_hv[w,v] = m.addVar(vtype=GRB.BINARY, name='phys-node-hv_%s_%s' % (w,v))

# Constraints
# For all nodes, there can be no more than Q hypervisor nodes.
m.addConstr(quicksum(possible_hv[v] for v in G.nodes()) == Q, 'hv_constr')


# totalCost = quicksum((capacity[i, j]*cost[i, j] + install[i, j]*install_cost[i, j]) for i, j in links)

min_max_lat = 0
m.setObjective(min_max_lat, GRB.MINIMIZE)
m.update()

# m.optimize()

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