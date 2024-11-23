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


def vehicle_max_connection(model, vehicle):
    return sum(model.vehicle_customer[vehicle, customer] for customer in model.customers) <= 1


model.vehicle_max_connection = pyo.Constraint(model.vehicles, rule=vehicle_max_connection, doc="v_max")


def customer_max_connection(model, customer1):
    return sum(model.customer_customer[customer1, customer2] for customer2 in model.customers) <= 1


model.customer_max_connection = pyo.Constraint(model.customers, rule=customer_max_connection, doc="c_max")