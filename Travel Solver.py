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
for j in range(0, len(day_slots)):
    for i in range(0, 96):
        if 32 <= i < 32 + day_slots[j]:
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

## Define variables ##
model.Yijdt = Var(model.i, model.j, model.d, model.t, within=Binary, doc='Going to Activity')
model.Sijdt = Var(model.i, model.j, model.d, model.t, within=Binary, doc='Followed by Activity')


## Define contrains ##
def startDay(model, d, t):
    return sum(model.Sijdt[0, j, d, t] for j in model.j) <= model.Adt[d, t]
model.startDay = Constraint(model.d, model.t, rule=startDay, doc='Start Day Rule')


def endDay(model, d, t):
    return sum(model.Sijdt[i, 0, d, t] for i in model.i) <= model.Adt[d, t + model.Cij[i, 0] + model.Ti[i]]
model.endDay = Constraint(model.d, model.t, rule=endDay, doc='End Day Rule')


def startIfOpen(model, i, d, t):
    return sum(model.Sijdt[i, j, d, t] for j in model.j) <= model.Oidt[i, d, t]
model.startIfOpen = Constraint(model.d, model.t, rule=startIfOpen, doc='Start if Open')


def continueIfOpen(model, i, d, t):
    return sum(model.Sijdt[i, j, d, t] for j in model.j) <= model.Oidt[i, d, t]
model.continueIfOpen = Constraint(model.i, model.d, model.t, rule=continueIfOpen, doc='Continue if Open')


def startOnce(model, i):
    return sum(model.Sijdt[i, j, d, t] for j in model.j for d in model.d for t in model.t) <= 1
model.startOnce = Constraint(model.i, rule=startOnce, doc='Start Activity Once')


def startAtHotel(model, d):
    return sum(model.Sijdt[0, j, d, t] for j in model.j for t in model.t) == 1
model.supply = Constraint(model.i, rule=supply_rule, doc='Start at Hotel')


def endAtHotel(model, d):
    return sum(model.Sijdt[i, 0, d, t] for i in model.i for t in model.t) == 1
model.demand = Constraint(model.j, rule=demand_rule, doc='End at Hotel')


def CompAct(model, i, j, d, t):
    return (model.Cij[i, j] + model.Ti[i])*model.Sijdt[i, j, d, t] == sum(model.Yijdt[i, j, d, t] for t in range(t, t + model.Cij[i, j] + model.Ti[i]))
model.CompAct = Constraint(model.i, model.j, model.d, model.t, rule=CompAct, doc='Complete Activity')


def timeAvailable(model, d):
    return sum(model.Cij[i, j]*model.Sijdt[i, j, d, t] for i in model.i for j in model.j for t in model.t)\
           + sum(model.Ti[i]*sum(model.Sijdt[i, j, d, t] for j in model.j for t in model.t) for i in model.i)\
           + sum(model.Cij[i, j]*sum(model.Sijdt[0, j, d, t] for t in model.t) for j in model.j)\
           + sum(model.Cij[i, j]*sum(model.Sijdt[i, 0, d, t] for t in model.t) for i in model.i)\
           <= model.Rd[d]
model.timeAvailable = Constraint(model.d, rule=timeAvailable, doc='Time Available')


def limitActivities(model, d, t):
    return sum(model.Yijdt[i, j, d, t] for i in model.i for j in model.j) <= 1
model.limitActivities = Constraint(model.j, rule=limitActivities, doc='Schedule Activities')

## Define Objective and solve ##
def objectiveRule(model):
    return sum(model.Wi[i]*sum(model.Sijdt[i, j, d, t] for j in model.j for d in model.d for t in model.t) for i in model.i)


model.objectiveRule = Objective(rule=objectiveRule, sense=maximize, doc='Define Objective Function')


## Display of the output ##
# Display x.l, x.m ;
def pyomo_postprocess(options=None, instance=None, results=None):
    model.Yijdt.display()


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
