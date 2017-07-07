#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyomo.core.base import ConcreteModel
from pyomo.environ import *

# Creation of a Concrete Model
model = ConcreteModel()

## Define sets ##
#  Sets
#       i   Sources   / 0, 1, 2, 3, 4 /
#       j   Destinations    / 0, 1, 2, 3, 4 /
#       d   Days    / 0, 1 /
#       t   Times    / 0, 1, 2, 3, 4 /;

model.t = Set(initialize=range(0, 96), doc='Times')
model.d = Set(initialize=range(0, 2), doc='Days')
model.i = Set(initialize=range(0, 5), doc='Sources')
model.j = SetOf(model.i)

## Define parameters ##
#   Parameters
#       T(i)  Time spent at activity i
#         /    0     0
#              1     3
#              2     4
#              3     3
#              4     2  /
#       W(i)  Weights for activity i
#         /    0     4
#              1     2
#              2     2
#              3     5
#              4     7  /
#       R(d)  Time spent at activity i
#         /    0     6
#              1     8  /;

time_values = [0, 3, 4, 3, 2]
Ti = {}
for i in range(0, len(time_values)):
    Ti[i] = time_values[i]

weight_values = [4, 2, 2, 5, 7]
Wi = {}
for i in range(0, len(weight_values)):
    Wi[i] = weight_values[i]

day_slots = [6, 8]
Rd = {}
for i in range(0, len(day_slots)):
    Rd[i] = day_slots[i]

model.Ti = Param(model.i, initialize=Ti, doc='Average Times')
model.Wi = Param(model.i, initialize=Wi, doc='Weight Scores')
model.Rd = Param(model.d, initialize=Rd, doc='Day Slots')

# Comments Here
Cij = {
    (0, 0): 0,
    (0, 1): 2,
    (0, 2): 1,
    (0, 3): 1,
    (0, 4): 3,
    (1, 0): 2,
    (1, 1): 0,
    (1, 2): 1,
    (1, 3): 2,
    (1, 4): 3,
    (2, 0): 1,
    (2, 1): 1,
    (2, 2): 0,
    (2, 3): 3,
    (2, 4): 2,
    (3, 0): 1,
    (3, 1): 1,
    (3, 2): 3,
    (3, 3): 0,
    (3, 4): 2,
    (4, 0): 3,
    (4, 1): 3,
    (4, 2): 2,
    (4, 3): 2,
    (4, 4): 0
}
model.Cij = Param(model.i, model.j, initialize=Cij, doc='Cost of Trip')

Adt = {}
for j in len(day_slots):
    for i in range(0, 96):
        if 32 <= i <= 32 + day_slots[j]:
            Adt[(j, i)] = 1
        else:
            Adt[(j, i)] = 0
model.Adt = Param(model.d, model.t, initialize=Adt, doc='Availability')

Oidt = {}
for i in range(0, 5):
    for d in range(0, 2):
        for t in range(0, 32):
            if 32 <= t <= 40:
                Oidt[(i, d, t)] = 1
            else:
                Oidt[(i, d, t)] = 0

model.Oidt = Param(model.i, model.d, model.t, doc='Business Hours')

#  Parameter c(i,j)  transport cost in thousands of dollars per case ;
#            c(i,j) = f * d(i,j) / 1000 ;
def c_init(model, i, j):
    return model.f * model.d[i, j] / 1000


model.c = Param(model.i, model.j, initialize=c_init, doc='Transport cost in thousands of dollar per case')

## Define variables ##
#  Variables
#       x(i,j)  shipment quantities in cases
#       z       total transportation costs in thousands of dollars ;
#  Positive Variable x ;
model.x = Var(model.i, model.j, bounds=(0.0, None), doc='Shipment quantities in case')


## Define contrains ##
# supply(i)   observe supply limit at plant i
# supply(i) .. sum (j, x(i,j)) =l= a(i)
def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.a[i]


model.supply = Constraint(model.i, rule=supply_rule, doc='Observe supply limit at plant i')


# demand(j)   satisfy demand at market j ;
# demand(j) .. sum(i, x(i,j)) =g= b(j);
def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.i) >= model.b[j]


model.demand = Constraint(model.j, rule=demand_rule, doc='Satisfy demand at market j')


## Define Objective and solve ##
#  cost        define objective function
#  cost ..        z  =e=  sum((i,j), c(i,j)*x(i,j)) ;
#  Model transport /all/ ;
#  Solve transport using lp minimizing z ;
def objective_rule(model):
    return sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)


model.objective = Objective(rule=objective_rule, sense=minimize, doc='Define objective function')


## Display of the output ##
# Display x.l, x.m ;
def pyomo_postprocess(options=None, instance=None, results=None):
    model.x.display()


# This is an optional code path that allows the script to be run outside of
# pyomo command-line.  For example:  python transport.py
if __name__ == '__main__':
    # This emulates what the pyomo command-line tools does
    from pyomo.opt import SolverFactory
    import pyomo.environ

    opt = SolverFactory("glpk")
    results = opt.solve(model)
    # sends results to stdout
    results.write()
    print("\nDisplaying Solution\n" + '-' * 60)
    pyomo_postprocess(None, model, results)
