#!/usr/bin/python

##############################################
# CPSC611_2.2.4_SimpleNodeLink.py
# Author: Anton Riedl
##############################################
# Simple dimensioning problem with Multicommodity Flows
# in Link-Path Formulation
# according to Pioro/Medhi, Routing, Flow, Capacity Design in ...
# Example 2.4.11


from gurobipy import *

# Model data

numNodes = 4

numLinks = 5
links = range(numLinks)

numDemands = 3
demands = range(numDemands)
demandVolume = [15, 20, 10]

#numPaths = 5
# each tuple in tuplelist is of format: (demand, (list of path links))
# Note: if there is only one link in a path, there still needs to be a comma, otherwise error
paths = tuplelist([(0,(1,3)), (1,(4,)), (1,(2,3)), (2,(0,)), (2,(1,2))])


capCost = [2, 1, 1, 3, 1]


# Create optimization model
m = Model('SimpleDimensioningLinkPath')


# Create variables

# DECISION VARIABLES
# Flow Variable per demand path
flow = {}
for p in paths:
    flow[p] = m.addVar(lb=0)

m.update()


# Capacity variables per link
cap = {}
for e in links:
    cap[e] = m.addVar(lb=0)

m.update()
    
#
# CONSTRAINTS
#

# Demand-Flow Constraints
#print("\nDEMAND-FLOW CONSTRAINTS")
for d in demands:
    #print("Demand constraints: %s %s" % (d, demandVolume[d]))
    #print(paths.select(d,'*'))
    m.addConstr(quicksum(flow[p] for p in paths.select(d,'*'))
                == demandVolume[d])
m.update()

# Link Capacity Constraints
#print("\nLINK-CAPACITY CONSTRAINTS")
for e in links:
    expr = LinExpr(0)
    #print("Link %s" % e)
    for p in paths:
        if e in p[1]:
            #print p, "added"
            expr += flow[p]
    m.addConstr(expr <= cap[e])
m.update

expr = LinExpr(0)

# OBJECTIVE FUNCTION
# minimize total cost
totalCost = quicksum(cap[e]*capCost[e] for e in links)
m.setObjective(totalCost, GRB.MINIMIZE)
m.update()



# Compute optimal solution
m.optimize()

# Print solution
print("\nSOLUTION")
if m.status == GRB.Status.OPTIMAL:
    solutionFlow = m.getAttr('x', flow)
    solutionCap = m.getAttr('x', cap)
    for p in paths: # range(numPaths):
        print('Optimal flow for demand %s on path %s: %s' % (p[0],p[1], solutionFlow[p]))
    for e in links: #range(numLinks):
        print('Optimal capacity on link %s: cap: %s cost: %s' % (e, solutionCap[e], solutionCap[e]*capCost[e]))
