import pyomo.environ as pyo

model = pyo.ConcreteModel(name="Scheduler")
opt = pyo.SolverFactory('appsi_highs')      # glpk, cbc, appsi_highs
opt.options["threads"] = 1

model.customers = pyo.Set(initialize=["id1", "id2", "id3"], doc="customers")