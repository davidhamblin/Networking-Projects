from gurobipy import *

m = Model('NodeLink2-4')

nodes = ['1', '2', '3', '4']

demands, dAmount = multidict({
  ('1', '2'):   15,
  ('1', '3'):   20,
  ('2', '3'):   10 })
demands = tuplelist(demands)

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

# Capacity variables per link
capacity = {}
for i, j in links:
    capacity[i, j] = m.addVar(lb=0)

flow = {}
for i,j in links:
    for d in demands:
        flow[i,j,d] = m.addVar(obj=cost[i,j],
                               name='flow_%s_%s_%s' % (i, j, d))

m.update()

# Flow balance at source nodes
for i in nodes:
    for d in demands:
        if i == d[0]:
            m.addConstr(
                quicksum(flow[i,j,d] for i,j in links.select(i,'*')) -
                quicksum(flow[k,i,d] for k,i in links.select('*',i))
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
for i,j in links:
    m.addConstr(quicksum(flow[i,j,d] for d in demands) <= capacity[i,j],
                'cap_%s_%s' % (i, j))

m.update()

totalCost = quicksum(capacity[i, j]*cost[i, j] for i, j in links)
m.setObjective(totalCost, GRB.MINIMIZE)
m.update()

m.optimize()

if m.status == GRB.Status.OPTIMAL:
    print()
    solutionCap = m.getAttr('x', capacity)
    for i, j in links:
        print('Optimal capacity on link %s: cap: %s' % ((i, j), solutionCap[i, j]))
    print()
    solutionFlow = m.getAttr('x', flow)
    for d in demands:
        print('\nOptimal flows for demand %s -> %s (%s):' % (d[0], d[1], dAmount[d]))
        for i,j in links:
            if solutionFlow[i,j,d] > 0:
                print('Link %s -> %s: %g' % (i, j, solutionFlow[i,j,d]))
