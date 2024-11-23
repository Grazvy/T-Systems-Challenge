import pyomo.environ as pyo
import requests
import json
import math
from utils import calculate_distance

def value(x):
    if x <= 0:
        raise ValueError("x cannot be negative")
    return x * math.log2(x)

model = pyo.ConcreteModel(name="Scheduler")
opt = pyo.SolverFactory('appsi_highs')      # glpk, cbc, appsi_highs
opt.options["threads"] = 1

"""
Simulation Initialization
"""
# create scenario
r = requests.post("http://localhost:8080/scenario/create")
r_json = json.loads(r.content.decode())
scenario_id = r_json["id"]

# initialize scenario (default values)
r = requests.post("http://localhost:8090/Scenarios/initialize_scenario", json=r_json)
r_json = json.loads(r.content.decode())

customers = r_json["scenario"]["customers"] # [i]["id"] for i = {0,...,n} for n customers
vehicles = r_json["scenario"]["vehicles"] # [j]["id"] for j = {0,...,m} for m vehicles

customers_coordX = [c["coordX"] for c in customers]
customers_coordY = [c["coordY"] for c in customers]
customers_destX = [c["destinationX"] for c in customers]
customers_destY = [c["destinationY"] for c in customers]

vehicles_coordX = [v["coordX"] for v in vehicles]
vehicles_coordY = [v["coordY"] for v in vehicles]

customer_ids = [c["id"] for c in customers]
vehicle_ids = [v["id"] for v in vehicles]

# calculate distances between dest and src for each customer
customer_distances = [calculate_distance(x1, y1, x2, y2) for x1, y1, x2, y2 in zip(customers_coordX, customers_coordY, customers_destX, customers_destY)]
customer_distances_dict = {cid: dist for cid, dist in zip(customer_ids, customer_distances)}

# calculate distances between dest. of first customer and source of second customer for each pair of customers
customer_pair_distances = {}
for i, id1 in enumerate(customer_ids):
    for j, id2 in enumerate(customer_ids):
        if i != j:
            destX1, destY1 = customers_destX[i], customers_destY[i]
            coordX2, coordY2 = customers_coordX[j], customers_coordY[j]
            distance = calculate_distance(destX1, destY1, coordX2, coordY2)
            customer_pair_distances[(id1, id2)] = distance

# calculate distances between vehicle positions and customer source positions
vehicle_customer_distances = {}
for j, vehicle_id in enumerate(vehicle_ids):
    vehicle_coordX, vehicle_coordY = vehicles_coordX[j], vehicles_coordY[j]
    for i, customer_id in enumerate(customer_ids):
        coordX, coordY = customers_coordX[i], customers_coordY[i]
        distance = calculate_distance(vehicle_coordX, vehicle_coordY, coordX, coordY)
        vehicle_customer_distances[(vehicle_id, customer_id)] = distance

# get value of customer path lengths
customer_values_dict = {cid: value(val) for cid, val in zip(customer_ids, customer_distances)}

# launch scenario
r = requests.post(f"http://localhost:8090/Runner/launch_scenario/{scenario_id}")

"""
Solver Logic
"""

model.customers = pyo.Set(initialize=customer_ids, doc="customers")
model.vehicles = pyo.Set(initialize=vehicle_ids, doc="vehicles")


model.customer_destination_distance = pyo.Param(model.customers, initialize=customer_distances_dict, doc="cd_d") # dist pickup -> dest
model.next_customer_distance = pyo.Param(model.customers, model.customers, initialize=customer_pair_distances, doc="nc_d") # dist between each customer
model.vehicle_customer_distance = pyo.Param(model.vehicles, model.customers, initialize=vehicle_customer_distances, doc="vc_d") # dist between each vehicle & customer
model.value_function = pyo.Param(model.customers, initialize=customer_values_dict, doc="v") # some value based on customer path length (n log n)

model.customer_customer = pyo.Var(model.customers, model.customers, within=pyo.Binary, doc="x_cc")
model.vehicle_customer = pyo.Var(model.vehicles, model.customers, within=pyo.Binary, doc="x_vc")
model.waiting_time = pyo.Var(model.customers, within=pyo.NonNegativeIntegers, doc="w")


def vehicle_max_connection(model, vehicle):
    return sum(model.vehicle_customer[vehicle, customer] for customer in model.customers) <= 1


model.vehicle_max_connection = pyo.Constraint(model.vehicles, rule=vehicle_max_connection, doc="v_max")


def customer_max_connection(model, customer1):
    return sum(model.customer_customer[customer1, customer2] for customer2 in model.customers) <= 1


model.customer_max_connection = pyo.Constraint(model.customers, rule=customer_max_connection, doc="c_max")