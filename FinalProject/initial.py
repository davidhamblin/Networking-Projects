from gurobipy import *
import networkx as nx
import matplotlib.pyplot as plt
from geopy.distance import vincenty
import random


G = nx.read_gml('AttModified.gml')

# Add the length of each edge with the Vincenty function in GeoPy
for i,j in G.edges():
    i_coord = (G.node[i]['Latitude'], G.node[i]['Longitude'])
    j_coord = (G.node[j]['Latitude'], G.node[j]['Longitude'])
    G.edge[i][j]['length'] = vincenty(i_coord, j_coord).miles

# Find all of the shortest paths using the Floyd-Warshall algorithm
fw_path = nx.floyd_warshall(G, weight='length')

# print("Edge measurements are reported in miles.\n")

# Example virtual network for task 2
virtual_nodes = {'ORLD': G.node['ORLD'], 'DLLS': G.node['DLLS'], 'WASH': G.node['WASH'], 'LA03': G.node['LA03']}
virtual_nodes_2 = {'PHLA': G.node['PHLA'], 'HSTN': G.node['HSTN'], 'DNVR': G.node['DNVR'], 'RLGH': G.node['RLGH']}
virtual_nodes_3 = {'SNAN': G.node['SNAN'], 'CHCG': G.node['CHCG'], 'NY54': G.node['NY54']}

controller_node = 'PHNX'
controller_node_2 = 'KSCY'
controller_node_3 = 'STLS'

# Given the substrate graph G and number of virtual nodes n, outputs a
# virtual network with a randomly chosen controller and virtual nodes
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

virtual_networks = []
controllers = []

virtual_networks.append(virtual_nodes)
virtual_networks.append(virtual_nodes_2)
virtual_networks.append(virtual_nodes_3)
controllers.append(controller_node)
controllers.append(controller_node_2)
controllers.append(controller_node_3)

sum_list = {}
freq_dict = {}

v3_list = []
for i in range(0,3):
    temp_dict = {}
    temp_dict['controller'] = controllers[i]
    temp_dict['vnodes'] = virtual_networks[i]
    v3_list.append(temp_dict)

"""
Implement Pairing SDN with Network Virtualization paper in Gurobi
"""

Q = 1
num_sim = 1
num_vnets = 10
sim_max = {}
sim_avg = {}
sim_avg_max = {}
sim_max_avg = {}

print('\nTotal number of trials: %s' % num_sim)
print('Total number of virtual networks: %s' % num_vnets)

# Trying out a Chinese network GML
# G = nx.read_gml('Cernet.gml')
#
# # Add the length of each edge with the Vincenty function in GeoPy
# for i,j in G.edges():
#     i_coord = (G.node[i]['Latitude'], G.node[i]['Longitude'])
#     j_coord = (G.node[j]['Latitude'], G.node[j]['Longitude'])
#     G.edge[i][j]['length'] = vincenty(i_coord, j_coord).miles
#
# fw_path = nx.floyd_warshall(G, weight='length')

for sim in range(0, num_sim):
    mod = Model('HypervisorModel')

    # Shut Gurobi up
    mod.setParam('OutputFlag', False)

    v_list = []
    for x in range(0, num_vnets):
        num_nodes = random.randrange(2, 11)
        v_dict = vnet_generator(G, num_nodes)
        v_list.append(v_dict)

    # Switch for finding results of the example network for task 2.
    # v_list = v3_list

    ### Variables
    # y_m,d,v in paper
    y_mdv = {}
    for m in range(0, len(v_list)):
        for d in v_list[m]['vnodes']:
            for v in G.nodes():
                y_mdv[m,d,v] = mod.addVar(name='y_%s_%s_%s' % (m,d,v))

    # x_v in paper
    possible_hv = {}
    for v in G.nodes():
        possible_hv[v] = mod.addVar(vtype=GRB.BINARY, name='possible-hv_%s' % v)

    # z_w,v in paper
    phys_node_hv = {}
    for w in G.nodes():
        for v in G.nodes():
            phys_node_hv[w,v] = mod.addVar(vtype=GRB.BINARY, name='phys-node-hv_%s_%s' % (w,v))

    ### Constraints
    # For all nodes, there can be no more than Q hypervisor nodes.
    mod.addConstr(quicksum(possible_hv[v] for v in G.nodes()) == Q, 'hv_constr')

    # Path selection constraint, for each demand of all vnets, exactly one path has to be selected.
    for m in range(0, len(v_list)):
        for d in v_list[m]['vnodes']:
            mod.addConstr(quicksum(y_mdv[m,d,v] for v in G.nodes()) == 1, 'path_constr')

    # Hypervisor node v chosen in case a path including the hypervisor is selected.
    for v in G.nodes():
        temp_val = LinExpr(0)
        for m in range(0, len(v_list)):
            for d in v_list[m]['vnodes']:
                temp_val += LinExpr(y_mdv[m,d,v])
        sum = 0
        for m in range(0, len(v_list)):
            sum += len(v_list[m]['vnodes'])
        mod.addConstr(temp_val <= sum * possible_hv[v])

    # Physical node assignment, physical SDN node is controlled by only one hypervisor.
    for m in range(0, len(v_list)):
        for d in v_list[m]['vnodes']:
            for v in G.nodes():
                mod.addConstr(y_mdv[m,d,v] <= quicksum(phys_node_hv[w,v] for w in G.nodes()))

    # Each physical SDN node is controlled by a single hypervisor instance.
    for v in G.nodes():
        mod.addConstr(quicksum(phys_node_hv[w,v] for w in G.nodes()) <= 1)

    # Objective functions
    w = mod.addVar(name='max-latency')

    w_m = {}
    for m in range(0, len(v_list)):
        w_m[m] = mod.addVar(name='avg-max-latency_%s' % m)

    w_two = mod.addVar(name='max-avg-latency')

    # Constraint for maximum latency
    for m in range(0, len(v_list)):
        for d in v_list[m]['vnodes']:
            mod.addConstr(quicksum(y_mdv[m,d,v]*(fw_path[v][v_list[m]['controller']] + fw_path[v][d]) for v in G.nodes()) <= w,
                          'max-latency-constr_%s_%s' %(m,d))

    # L_avg for average latency
    sum = 0
    for m in range(0, len(v_list)):
        sum += len(v_list[m]['vnodes'])

    y_tot = LinExpr(0)
    for m in range(0, len(v_list)):
        for d in v_list[m]['vnodes']:
            for v in G.nodes():
                y_tot += y_mdv[m,d,v] * (fw_path[v][v_list[m]['controller']] + fw_path[v][d])
    L_avg = (1/sum) * y_tot

    # Can also accomplish with quicksum chaining
    # L_avg = (1/sum) * quicksum(quicksum(quicksum(y_mdv[m,d,v] * (fw_path[v][v_list[m]['controller']] + fw_path[v][d]) for v in G.nodes()) for d in v_list[m]['vnodes']) for m in range(0, len(v_list)))

    # Constraint for average-maximum latency
    for m in range(0, len(v_list)):
        for d in v_list[m]['vnodes']:
            mod.addConstr(quicksum(y_mdv[m,d,v]*(fw_path[v][v_list[m]['controller']] + fw_path[v][d]) for v in G.nodes()) <= w_m[m],
                          'avg-max-latency-constr_%s_%s' %(m,d))

    w_m_objective = 1/len(v_list) * quicksum(w_m[m] for m in range(0, len(v_list)))

    # Constraint for maximum-average latency
    for m in range(0, len(v_list)):
        mod.addConstr(quicksum(quicksum(y_mdv[m,d,v]*(fw_path[v][v_list[m]['controller']] + fw_path[v][d]) for v in G.nodes()) for d in v_list[m]['vnodes'])/len(v_list[m]['vnodes']) <= w_two,
                      'max-avg-latency-constr_%s_%s' %(m,d))

    mod.setObjective(w, GRB.MINIMIZE)
    mod.update()

    mod.optimize()

    min_max_result = ''
    for key, value in mod.getAttr('x', possible_hv).items():
        if value == 1:
            min_max_result = 'Gurobi Best HV for Max Latency: %s, %s' % (key, mod.ObjVal)

    # Brute force method for max latency
    nodes_cost = {}
    controller_count = 0
    for vnet in v_list:
        for name in G.nodes():
            sum = 0
            max_length = 0
            for v in vnet['vnodes']:
                sum = fw_path[name][vnet['controller']] + fw_path[name][v]
                if sum > max_length:
                    max_length = sum
            sum_list[name] = max_length
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
        if min_length[0] in freq_dict:
            freq_dict[min_length[0]] += 1
        else:
            freq_dict[min_length[0]] = 1
    max_sorted_answer = sorted(nodes_cost.items(), key=operator.itemgetter(1), reverse=False)

    mod.setObjective(L_avg, GRB.MINIMIZE)
    mod.update()

    mod.optimize()

    avg_result = ''
    for key, value in mod.getAttr('x', possible_hv).items():
        if value == 1:
            avg_result = 'Gurobi Best HV for Average Latency: %s, %s' % (key, mod.ObjVal)

    # Brute force method for average latency
    # This method is different from the others, because the dang thing wouldn't work correctly with the other outline
    lowest_avg = 10000000000
    lowest_hv = ''
    for name in G.nodes():
        sum = 0
        vnet_length = 0
        for vnet in v_list:
            for v in vnet['vnodes']:
                sum += fw_path[name][vnet['controller']] + fw_path[name][v]
            vnet_length += len(vnet['vnodes'])
        sum /= vnet_length
        if sum < lowest_avg:
            lowest_hv = name
            lowest_avg = sum

    mod.setObjective(w_m_objective, GRB.MINIMIZE)
    mod.update()

    mod.optimize()

    avg_max_result = ''
    for key, value in mod.getAttr('x', possible_hv).items():
        if value == 1:
            avg_max_result = 'Gurobi Best HV for Average-Maximum Latency: %s, %s' % (key, mod.ObjVal)

    # Brute force method for average-max latency
    nodes_cost = {}
    controller_count = 0
    for vnet in v_list:
        for name in G.nodes():
            sum = 0
            max_length = 0
            for v in vnet['vnodes']:
                sum = fw_path[name][vnet['controller']] + fw_path[name][v]
                if sum > max_length:
                    max_length = sum
            sum_list[name] = max_length
            if name in nodes_cost:
                nodes_cost[name] += max_length
            else:
                nodes_cost[name] = max_length
        controller_count += 1
        if controller_count > len(v_list)-1:
            for k,v in nodes_cost.items():
                nodes_cost[k] = v/len(v_list)
            min_length = min(sum_list.items(), key=lambda x: x[1])
            if min_length[0] in nodes_cost:
                if nodes_cost[min_length[0]] < min_length[1]:
                    nodes_cost[min_length[0]] = min_length[1]
            else:
                nodes_cost[min_length[0]] = min_length[1]
            if min_length[0] in freq_dict:
                freq_dict[min_length[0]] += 1
            else:
                freq_dict[min_length[0]] = 1
    avg_max_sorted_answer = sorted(nodes_cost.items(), key=operator.itemgetter(1), reverse=False)

    mod.setObjective(w_two, GRB.MINIMIZE)
    mod.update()

    mod.optimize()

    max_avg_result = ''
    for key, value in mod.getAttr('x', possible_hv).items():
        if value == 1:
            max_avg_result = 'Gurobi Best HV for Maximum-Average Latency: %s, %s' % (key, mod.ObjVal)

    # Brute force method for max-average latency
    nodes_cost = {}
    controller_count = 0
    for vnet in v_list:
        for name in G.nodes():
            sum = 0
            for v in vnet['vnodes']:
                sum += fw_path[name][vnet['controller']] + fw_path[name][v]
            sum /= len(vnet['vnodes'])
            sum_list[name] = sum
            if name in nodes_cost:
                if nodes_cost[name] < sum:
                    nodes_cost[name] = sum
            else:
                nodes_cost[name] = sum
        controller_count += 1
        min_length = min(sum_list.items(), key=lambda x: x[1])
        if min_length[0] in nodes_cost:
            if nodes_cost[min_length[0]] < min_length[1]:
                nodes_cost[min_length[0]] = min_length[1]
        else:
            nodes_cost[min_length[0]] = min_length[1]
        if min_length[0] in freq_dict:
            freq_dict[min_length[0]] += 1
        else:
            freq_dict[min_length[0]] = 1
    max_avg_sorted_answer = sorted(nodes_cost.items(), key=operator.itemgetter(1), reverse=False)

    print('\nTrial %s' % sim)
    print(min_max_result)
    print(avg_result)
    print(avg_max_result)
    print(max_avg_result)
    print('\nBrute Force Best HV for Max Latency: %s, %s' % (max_sorted_answer[0][0], max_sorted_answer[0][1]))
    print('Brute Force Best HV for Average Latency: %s, %s' % (lowest_hv, lowest_avg))
    print('Brute Force Best HV for Average-Maximum Latency: %s, %s' % (avg_max_sorted_answer[0][0], avg_max_sorted_answer[0][1]))
    print('Brute Force Best HV for Maximum-Average Latency: %s, %s' % (max_avg_sorted_answer[0][0], max_avg_sorted_answer[0][1]))

    if max_sorted_answer[0][0] in sim_max:
        sim_max[max_sorted_answer[0][0]] += 1
    else:
        sim_max[max_sorted_answer[0][0]] = 1

    if lowest_hv in sim_avg:
        sim_avg[lowest_hv] += 1
    else:
        sim_avg[lowest_hv] = 1

    if avg_max_sorted_answer[0][0] in sim_avg_max:
        sim_avg_max[avg_max_sorted_answer[0][0]] += 1
    else:
        sim_avg_max[avg_max_sorted_answer[0][0]] = 1

    if max_avg_sorted_answer[0][0] in sim_max_avg:
        sim_max_avg[max_avg_sorted_answer[0][0]] += 1
    else:
        sim_max_avg[max_avg_sorted_answer[0][0]] = 1

print('\nMax Latency Overall: %s' % sim_max)
print('Average Latency Overall: %s' % sim_avg)
print('Average-Max Latency Overall: %s' % sim_avg_max)
print('Max-Average Latency Overall: %s' % sim_max_avg)

pos = {}
for v in nx.nodes(G):
    pos[v] = [G.node[v]['Longitude'], G.node[v]['Latitude']]

nx.draw(G, pos)

nx.draw_networkx_nodes(G, pos, node_size=800, node_shape='s')
nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif', font_color='w')

# plt.figure(1)
# plt.axis('off')
# plt.savefig("att.png") # save as png
# plt.show()

# Function for removing unnecessary information from the GML for ATT's network, and writing a modified GML.
def remove_attributes_ATT(G):
    for i,j in G.edges():
        del G.edge[i][j]['LinkLabel']

    for v in G.nodes():
        del G.node[v]['type']
        del G.node[v]['Country']
        del G.node[v]['Internal']

    nx.write_gml(G, 'AttModified.gml')

# remove_attributes_ATT(G)