import pyomo.environ as pyo

model = pyo.ConcreteModel(name="Scheduler")
opt = pyo.SolverFactory('appsi_highs')      # glpk, cbc, appsi_highs
opt.options["threads"] = 1

model.customers = pyo.Set(initialize=["id1", "id2"], doc="customers")
model.vehicles = pyo.Set(initialize=["id1", "id2", "id3"], doc="vehicles")


model.customer_destination_distance = pyo.Param(model.customers, initialize={"id1": 50, "id2": 50}, doc="cd_d")
model.next_customer_distance = pyo.Param(model.customers, model.customers, initialize={("id1", "id2"): 50}, doc="nc_d")
model.vehicle_customer_distance = pyo.Param(model.vehicles, model.customers, initialize={("id1", "id2"): 50}, doc="vc_d")
model.value_function = pyo.Param(model.customers, initialize={"id1": 5,"id2": 5}, doc="v")

model.customer_customer = pyo.Var(model.customers, model.customers, within=pyo.Binary, doc="x_cc")
model.vehicle_customer = pyo.Var(model.vehicles, model.customers, within=pyo.Binary, doc="x_vc")
model.waiting_time = pyo.Var(model.customers, within=pyo.NonNegativeIntegers, doc="w")