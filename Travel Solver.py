#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyomo.core.base import ConcreteModel
from pyomo.environ import *
import math

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
model.i = Set(initialize=range(0, 10), doc='Sources')
model.j = SetOf(model.i)

## Define parameters ##
#   Parameters
#       T(i)  Time spent at activity i
#         /    0     0
#              1     1
#              2     1
#              3     1
#              4     1  /
#       W(i)  Weights for activity i
#         /    0     4
#              1     2
#              2     2
#              3     5
#              4     7  /
#       R(d)  Time spent at activity i
#         /    0     6
#              1     8  /;

time_values = [0, 12, 14, 11, 14, 12, 18, 10, 17, 12]
Ti = {}
for i in range(0, len(time_values)):
    Ti[i] = time_values[i]

weight_values = [0, 2, 2, 5, 9, 3, 5, 2, 6, 16]
Wi = {}
for i in range(0, len(weight_values)):
    Wi[i] = weight_values[i]

day_slots = [32, 34]
Rd = {}
for i in range(0, len(day_slots)):
    Rd[i] = day_slots[i]

model.Ti = Param(model.i, initialize=Ti, doc='Average Times')
model.Wi = Param(model.i, initialize=Wi, doc='Weight Scores')
model.Rd = Param(model.d, initialize=Rd, doc='Day Slots')

# Comments Here
Cij = {}
for g in range (0, 10):
    for h in range (0, 10):
        if g == h:
            Cij[(g, h)] = 0
        else:
            Cij[(g, h)] = 2
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
for i in range(0, 10):
    for d in range(0, 2):
        for t in range(0, 96):
            if i == 0:
                Oidt[(i, d, t)] = 1
                continue
            if 32 <= t <= 64:
                Oidt[(i, d, t)] = 1
            else:
                Oidt[(i, d, t)] = 0

model.Oidt = Param(model.i, model.d, model.t, initialize=Oidt, doc='Business Hours')

## Define variables ##
model.Yijdt = Var(model.i, model.j, model.d, model.t, within=Binary, doc='Going to Activity')
model.Sijdt = Var(model.i, model.j, model.d, model.t, within=Binary, doc='Followed by Activity')


## Define constraints ##
def Availability(model, i, j, d, t):
    tmax = 95 if t + model.Cij[i, j] + model.Ti[i] >= 95 else t + model.Cij[i, j] + model.Ti[i]
    return model.Sijdt[i, j, d, t] <= model.Adt[d, tmax]
model.Availability = Constraint(model.i, model.j, model.d, model.t, rule=Availability, doc='Availability')


def GroupAvailability(model, i, j, d, t):
    return model.Sijdt[i, j, d, t] <= model.Adt[d, t]
model.GroupAvailability = Constraint(model.i, model.j, model.d, model.t, rule=GroupAvailability, doc='Group Availability')


def IsOpen(model,i, j, d, t):
    tmax = 95 if t + model.Cij[i, j] + model.Ti[i] >= 95 else t + model.Cij[i, j] + model.Ti[i]
    return model.Sijdt[i, j, d, t] <= model.Oidt[j, d, tmax]
model.IsOpen = Constraint(model.i, model.j, model.d, model.t, rule=IsOpen, doc='Is Open')


def BusinessAvailability(model, i, j, d, t):
    return model.Sijdt[i, j, d, t] <= model.Oidt[i, d, t]
model.BusinessAvailability = Constraint(model.i, model.j, model.d, model.t, rule=BusinessAvailability, doc='Business Availability')


def startOnce(model, i):
    if i == 0:
        return Constraint.Skip
    else:
        return sum(model.Sijdt[i, j, d, t] for j in model.j for d in model.d for t in model.t) <= 1
model.startOnce = Constraint(model.i, rule=startOnce, doc='Start Activity Once')

def endtOnce(model, j):
    if j == 0:
        return Constraint.Skip
    else:
        return sum(model.Sijdt[i, j, d, t] for i in model.i for d in model.d for t in model.t) <= 1
model.endtOnce = Constraint(model.j, rule=endtOnce, doc='End Activity Once')


def startAtHotel(model, d):
    return sum(model.Sijdt[0, j, d, t] for j in model.j for t in model.t) == 1
model.startAtHotel = Constraint(model.d, rule=startAtHotel, doc='Start at Hotel')


def endAtHotel(model, d):
    return sum(model.Sijdt[i, 0, d, t] for i in model.i for t in model.t) == 1
model.endAtHotel = Constraint(model.d, rule=endAtHotel, doc='End at Hotel')


def circularRule(model, d, t):
    return sum(model.Sijdt[i, i, d, t] for i in model.i) == 0
model.circularRule = Constraint(model.d, model.t, rule=circularRule, doc='No Circles')


def CompAct(model, i, j, d, t):
    if t + model.Cij[i, j] + model.Ti[i] + 1 >= 96:
        tmax = 96
        return sum(model.Yijdt[i, j, d, g] for g in range(t, tmax)) >= model.Sijdt[i, j, d, t]*(model.Cij[i, j] + model.Ti[i])
    if t + model.Cij[i, j] + model.Ti[i] == t:
        return Constraint.Skip
    else:
        tmax = t + model.Cij[i, j] + model.Ti[i]
        return sum(model.Yijdt[i, j, d, g] for g in range(t, tmax)) >= model.Sijdt[i, j, d, t]*(model.Cij[i, j] + model.Ti[i])
model.CompAct = Constraint(model.i, model.j, model.d, model.t, rule=CompAct, doc='Complete Activity')


def NoIntersect(model, d, t):
    return sum(model.Yijdt[i, j, d, t] for i in model.i for j in model.j) <= 1
model.NoIntersect = Constraint(model.d, model.t, rule=NoIntersect, doc='No Intersect')


def timeAvailable(model, d):
    return sum((model.Cij[i, j] + model.Ti[i])*model.Sijdt[i, j, d, t] for i in model.i for j in model.j for t in model.t) <= model.Rd[d]
model.timeAvailable = Constraint(model.d, rule=timeAvailable, doc='Time Available')


def limitActivities(model, d, t):
    return sum(model.Sijdt[i, j, d, t] for i in model.i for j in model.j) <= 1
model.limitActivities = Constraint(model.d, model.t, rule=limitActivities, doc='Schedule Activities')


def Continuity(model, i ,j, d, t):
    if j == 0:
        return Constraint.Skip
    else:
        return sum(model.Sijdt[j, h, d, g] for g in range(t + 1, 96) for h in model.j) >= model.Sijdt[i, j, d, t]
model.Continuity = Constraint(model.i, model.j, model.d, model.t, rule=Continuity, doc='Continuity')

## Define Objective and solve ##
def objectiveRule(model):
    return sum(model.Wi[i]*sum(model.Sijdt[i, j, d, t] for j in model.j for d in model.d for t in model.t) for i in model.i)
model.objectiveRule = Objective(rule=objectiveRule, sense=maximize, doc='Define Objective Function')


## Display of the output ##
# Display x.l, x.m ;
def pyomo_postprocess(options=None, instance=None, results=None):
    with open('results.txt', 'w') as f:
        for key, value in instance.Sijdt._data.items():
            if value._value > 0.5:
                f.write('% s: % s\n' % (key, int(round(value._value))))


if __name__ == '__main__':
    # This emulates what the pyomo command-line tools does
    from pyomo.opt import SolverFactory
    import pyomo.environ

    opt = SolverFactory("gurobi")
    results = opt.solve(model)
    # sends results to stdout
    results.write()
    print("\nWriting Solution\n" + '-' * 60)
    pyomo_postprocess(None, model, results)
    print("Complete")
