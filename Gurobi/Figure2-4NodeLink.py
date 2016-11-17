#       2
#       |\
#       4 \
#     /   \\
#    /     \\
#   1-------3
#
#   Demands:
#   <1,2> = 15
#   <1,3> = 20
#   <2,3> = 10
#
#   Capacity:
#
#
from gurobipy import *

# Model data

nodes = ['1', '2', '3', '4']
numNodes = 4
numLinks = 5
link_size = range(numLinks)

numDemands = 3
demands = range(numDemands)
demandVolume = [15, 20, 10]

capCost = [2, 1, 1, 3, 1]

links, cost = multidict({
    ('1', '3'): 1,
    ('3', '1'): 1,
    ('1', '4'): 3,
    ('4', '1'): 3,
    ('3', '4'): 1,
    ('4', '3'): 1,
    ('4', '2'): 1,
    ('2', '4'): 1,
    ('2', '3'): 2,
    ('3', '2'): 2
})
links = tuplelist(links)

demands, dAmount = multidict({
    ('1', '2'): 15,
    ('1', '3'): 20,
    ('2', '3'): 10})
demands = tuplelist(demands)

# each tuple in tuplelist is of format: (demand, (list of path links))
# Note: if there is only one link in a path, there still needs to be a comma, otherwise error
links = tuplelist([(0,(1,3)), (1,(4,)), (1,(2,3)), (2,(0,)), (2,(1,2))])

# Create optimization model
m = Model('CapacityModel')
l = Model('ExpandedNodeLink')

# flow = {}
# for i, j in links:
#     flow[i, j] = m.addVar(lb=0)

capacity = {}
for i,j in links:
    capacity[i,j] = l.addVar(lb=0)

# Create variables and make them part of the objective function
flow = {}
for i, j in links:
    for d in demands:
        flow[i, j, d] = m.addVar(ub=capacity[i, j], obj=cost[i, j],
                                 name='flow_%s_%s_%s' % (i, j, d))

m.update()

# Demand-Flow Constraints
#print("\nDEMAND-FLOW CONSTRAINTS")
for d in demands:
    #print("Demand constraints: %s %s" % (d, demandVolume[d]))
    # print(links.select((i,j),'*'))
    m.addConstr(quicksum(flow[i, j] for i, j in links.select(d,'*'))
                == demandVolume[d])
m.update()

# Link Capacity Constraints
#print("\nLINK-CAPACITY CONSTRAINTS")
for e in link_size:
    expr = LinExpr(0)
    #print("Link %s" % e)
    for i, j in links:
        if e in i[0]:
            #print p, "added"
            expr += flow[i, j]
    m.addConstr(expr <= capacity[e])
m.update

#
# CONSTRAINTS
#
# Flow balance at source nodes
for i in nodes:
    for d in demands:
        if i == d[0]:
            m.addConstr(
                quicksum(flow[i, j, d] for i, j in links.select(i, '*')) -
                quicksum(flow[k, i, d] for k, i in links.select('*', i))
                == dAmount[d], 'node_%s_%s' % (i, d))

# Flow balance at destination nodes
for i in nodes:
    for d in demands:
        if i == d[1]:
            m.addConstr(
                quicksum(flow[i, j, d] for i, j in links.select(i, '*')) -
                quicksum(flow[k, i, d] for k, i in links.select('*', i))
                == -dAmount[d], 'node_%s_%s' % (i, d))

# Flow balance at interior nodes
for i in nodes:
    for d in demands:
        if i != d[0] and i != d[1]:
            m.addConstr(
                quicksum(flow[i, j, d] for i, j in links.select(i, '*')) -
                quicksum(flow[k, i, d] for k, i in links.select('*', i))
                == 0, 'node_%s_%s' % (i, d))


# Capacity constraints
for i, j in links:
    m.addConstr(quicksum(flow[i, j, d] for d in demands) <= capacity[i, j],
                'cap_%s_%s' % (i, j))

m.update()
l.update()

# OBJECTIVE FUNCTION
# minimize total cost
totalCost = quicksum(cap[e]*capCost[e] for e in links)
l.setObjective(totalCost, GRB.MINIMIZE)
l.update()

# Compute optimal solution
m.optimize()

if m.status == GRB.Status.OPTIMAL:
    solutionCap = m.getAttr('x', cap)
    for e in links:
        print('Optimal capacity on link %s: cap: %s' % (e, solutionCap[e]))



m.optimize()
# Print solution
if m.status == GRB.Status.OPTIMAL:
    solution = m.getAttr('x', flow)
    for d in demands:
        print('\nOptimal flows for demand %s -> %s (%s):' % (d[0], d[1], dAmount[d]))
        for i, j in links:
            if solution[i, j, d] > 0:
                print('Link %s -> %s: %g' % (i, j, solution[i, j, d]))
