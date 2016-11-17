from gurobipy import *
import matplotlib.pyplot as plt
import networkx as nx

m = Model('Project2Task3-3')

nodes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

# Capacity-dependent cost is 5 MU per 10 Mbps. Links are 1 Gbps.
cap_dep_cost = 5

# Setup cost is 100 MU * cost multiplier
setup_cost = 100

DemandNode, DemandSink = multidict({
    ('A'): 0,
    ('B'): 100,
    ('C'): 100,
    ('D'): 100,
    ('E'): 100,
    ('F'): 100,
    ('G'): 100,
    ('H'): 100
})

links, cost, install_cost = multidict({
    ('A', 'B'): [2*cap_dep_cost, 2*setup_cost],
    ('B', 'A'): [2*cap_dep_cost, 2*setup_cost],
    ('A', 'C'): [2*cap_dep_cost, 2*setup_cost],
    ('C', 'A'): [2*cap_dep_cost, 2*setup_cost],
    ('B', 'D'): [2*cap_dep_cost, 2*setup_cost],
    ('D', 'B'): [2*cap_dep_cost, 2*setup_cost],
    ('D', 'F'): [2*cap_dep_cost, 2*setup_cost],
    ('F', 'D'): [2*cap_dep_cost, 2*setup_cost],
    ('C', 'F'): [3*cap_dep_cost, 3*setup_cost],
    ('F', 'C'): [3*cap_dep_cost, 3*setup_cost],
    ('C', 'E'): [2*cap_dep_cost, 2*setup_cost],
    ('E', 'C'): [2*cap_dep_cost, 2*setup_cost],
    ('E', 'G'): [1*cap_dep_cost, 1*setup_cost],
    ('G', 'E'): [1*cap_dep_cost, 1*setup_cost],
    ('G', 'H'): [2*cap_dep_cost, 2*setup_cost],
    ('H', 'G'): [2*cap_dep_cost, 2*setup_cost],
    ('F', 'H'): [1*cap_dep_cost, 1*setup_cost],
    ('H', 'F'): [1*cap_dep_cost, 1*setup_cost]
})
links = tuplelist(links)

flow = {}
for i,j in links:
    flow[i,j] = m.addVar(name='flow_%s_%s' % (i, j))

capacity = {}
install = {}
for i,j in links:
    capacity[i, j] = m.addVar(name='capacity_%s_%s' % (i, j))
    install[i, j] = m.addVar(vtype=GRB.INTEGER, name='install_%s_%s' % (i, j))

DemandSource = {}
for i in nodes:
    DemandSource[i] = m.addVar(name='demand-source_%s' % i)

server_install = {}
for i in nodes:
    server_install[i] = m.addVar(vtype=GRB.INTEGER, name='server-install_%s' % i)

m.update()

# Flow balance at source, output, and interior nodes
for i in nodes:
    m.addConstr(
        quicksum(flow[i,j] for i,j in links.select(i,'*')) -
        quicksum(flow[k,i] for k,i in links.select('*',i))
        == DemandSource[i] - DemandSink[i], 'node_%s' % (i))

# Capacity constraints
for i,j in links:
    m.addConstr(flow[i,j] <= capacity[i,j],
                'cap_%s_%s' % (i, j))
    m.addConstr(capacity[i,j] <= 2000*install[i,j],
                'install_%s_%s' % (i, j))

for i in nodes:
    m.addConstr(DemandSource[i] <= 2000 * server_install[i],
                'server-install-max_%s' % (i))

m.update()

server_cost = 5000

totalCost = quicksum((capacity[i, j]*cost[i, j] + install[i, j]*install_cost[i, j]) for i, j in links) + quicksum(server_install[i]*server_cost for i in nodes)
m.setObjective(totalCost, GRB.MINIMIZE)
m.update()

m.optimize()

G = nx.DiGraph()

G.add_node('A', x=0, y=0)
G.add_node('B', x=0, y=-10)
G.add_node('C', x=2.5, y=10)
G.add_node('D', x=2.5, y=-20)
G.add_node('E', x=7.5, y=10)
G.add_node('F', x=7.5, y=-20)
G.add_node('G', x=10, y=0)
G.add_node('H', x=10, y=-10)

server_nodes = []

if m.status == GRB.Status.OPTIMAL:
    print()
    solutionCap = m.getAttr('x', capacity)
    for i, j in links:
        print('Optimal capacity on link %s: cap: %s' % ((i, j), solutionCap[i, j]))
    print()
    solutionServer = m.getAttr('x', server_install)
    print(solutionServer)
    for i in nodes:
        if solutionServer[i]:
            print('Server in %s' % i)
            server_nodes.append(i)
    solutionFlow = m.getAttr('x', flow)
    for i,j in links:
        if solutionFlow[i,j] > 0:
            print('Link %s -> %s: %g' % (i, j, solutionFlow[i,j]))
            # Add the solution flow edges to the graph
            G.add_edge(i, j, weight=solutionCap[i, j])

print('\nTotal cost of the network: %s' % m.ObjVal)

# Draw the graph from the optimal flow edges in G
el=[(u,v) for (u,v,d) in G.edges(data=True)]
edge_labels = dict([((u, v,), d['weight'])
                    for u, v, d in G.edges(data=True)])

pos = {}
for v in nx.nodes(G):
    pos[v] = [G.node[v]['x'], G.node[v]['y']]

nx.draw(G, pos, with_labels=True)

# nodes
nx.draw_networkx_nodes(G,pos,node_size=400,node_color='r')
nx.draw_networkx_nodes(G,pos,nodelist=server_nodes,node_size=400,node_color='b')

# labels
nx.draw_networkx_labels(G,pos,font_size=12,font_family='sans-serif',font_color='w')
nx.draw_networkx_edge_labels(G,pos,edge_labels=edge_labels)

plt.figure(1)
plt.axis('off')
plt.savefig("capacity_graph_task33.png") # save as png

plt.show() # display
