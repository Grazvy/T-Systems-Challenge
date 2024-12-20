import pyomo.environ as pyo
import requests
import json
import math
import time
from utils.utils import calculate_distance, update_scenario, update_scenario_dist, randomized_payload
from itertools import chain, combinations
import logging

# Suppress Pyomo logging
logging.getLogger('pyomo').setLevel(logging.ERROR)

def _value(x):
    if x < 0:
        raise ValueError("x cannot be negative")

    return max(200 + 1/10 * x + 1/40 * (1/50 * x)**2, 2000)


def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

def count(set):
    result = 0
    for s1 in set:
        for s2 in set:
            if include_pair(s1, s2):
                result += 1
    return result

def calculate_score(wait_times, distances_dict):
    score = 0
    for id, t in wait_times.items():
            score += _value(distances_dict[id]) * t

    return score

collect_data = False
speed = 0.001
amount_v = 10
amount_c = 20
model = pyo.ConcreteModel(name="Scheduler")
opt = pyo.SolverFactory('appsi_highs')  # glpk, cbc, appsi_highs
opt.options["threads"] = 32
radius = 100
exceptions = []

"""
Simulation Initialization
"""
# create scenario
r = requests.post(f"http://localhost:8080/scenario/create?numberOfVehicles={amount_v}&numberOfCustomers={amount_c}")
r_json = json.loads(r.content.decode())
scenario_id = r_json["id"]

# initialize scenario (default values)
r = requests.post("http://localhost:8090/Scenarios/initialize_scenario", json=r_json)
r_json = json.loads(r.content.decode())

customers = r_json["scenario"]["customers"]  # [i]["id"] for i = {0,...,n} for n customers
vehicles = r_json["scenario"]["vehicles"]  # [j]["id"] for j = {0,...,m} for m vehicles

customers_coordX = [c["coordX"] for c in customers]
customers_coordY = [c["coordY"] for c in customers]
customers_destX = [c["destinationX"] for c in customers]
customers_destY = [c["destinationY"] for c in customers]

vehicles_coordX = [v["coordX"] for v in vehicles]
vehicles_coordY = [v["coordY"] for v in vehicles]

customer_ids = [c["id"] for c in customers]
vehicle_ids = [v["id"] for v in vehicles]

def check_radius_vc(cid, vid, radius):
    c_index = customer_ids.index(cid)
    v_index = vehicle_ids.index(vid)
    return calculate_distance(customers_coordX[c_index], customers_coordY[c_index], vehicle_coordX[v_index], vehicle_coordY[v_index]) < radius

def check_radius_cc(c1id, c2id, radius):
    c1_index = customer_ids.index(c1id)
    c2_index = customer_ids.index(c2id)
    return calculate_distance(customers_coordX[c2_index], customers_coordY[c2_index], customers_destX[c1_index], customers_destY[c1_index]) < radius

def include_pair(c1, c2):
    if c2 in exceptions:
        return True

    return c1 != c2 and check_radius_cc(c1, c2, radius)

def build_model(model):
    model.customers = pyo.Set(initialize=customer_ids, doc="customers")
    model.vehicles = pyo.Set(initialize=vehicle_ids, doc="vehicles")
    model.valid_pairs = pyo.Set(dimen=2, initialize=lambda m: [(i, j) for i in model.customers for j in model.customers
                                                               if include_pair(i, j)], doc="valid pairs")

    model.customer_destination_distance = pyo.Param(model.customers, initialize=customer_distances_dict,
                                                    doc="cd_d")  # dist pickup -> dest
    model.next_customer_distance = pyo.Param(model.valid_pairs, initialize=customer_pair_distances,
                                             doc="nc_d")  # dist between each customer
    model.vehicle_customer_distance = pyo.Param(model.vehicles, model.customers, initialize=vehicle_customer_distances,
                                                doc="vc_d")  # dist between each vehicle & customer
    model.value_function = pyo.Param(model.customers, initialize=customer_values_dict,
                                     doc="v")  # some value based on customer path length (n log n)

    model.customer_customer = pyo.Var(model.valid_pairs, within=pyo.Binary, doc="x_cc")
    model.vehicle_customer = pyo.Var(model.vehicles, model.customers, within=pyo.Binary, doc="x_vc")
    model.waiting_time = pyo.Var(model.customers, within=pyo.NonNegativeIntegers, doc="w")
    model.joker = pyo.Var(model.customers, within=pyo.Binary, doc="j")

    model.vehicle_max_connection = pyo.Constraint(model.vehicles, rule=vehicle_max_connection, doc="v_max")

    model.customer_max_connection = pyo.ConstraintList()

    for customer in model.customers:
        const = customer_max_connection(model, customer)

        try:
            model.customer_max_connection.add(const)
        except ValueError:
            continue

    model.gets_picked_up_once = pyo.Constraint(model.customers, rule=gets_picked_up_once, doc="pickup")

    model.waiting_time_chained = pyo.ConstraintList()

    for c1, c2 in model.valid_pairs:
        if include_pair(c2, c1):
            try:
                model.waiting_time_chained.add(waiting_time_chained(model, c1, c2))
            except ValueError:
                continue


    model.waiting_time_start = pyo.Constraint(model.customers, rule=waiting_time_start, doc="wt_s")

    model.subset_elimination_constraints = pyo.ConstraintList()

    sorted_sets = {}

    for set in customer_powerset:
        if len(set) in sorted_sets:
            sorted_sets[len(set)].append(set)

        else:
            sorted_sets[len(set)] = [set]

    for key, value in sorted_sets.items():
        setattr(model, f'set_dim_{key}', pyo.Set(dimen=key, initialize=value))

    for key in sorted_sets:
        set = getattr(model, f'set_dim_{key}')
        for subset in set:
            if count(subset) < len(subset):
                continue
            try:
                model.subset_elimination_constraints.add(subset_elimination(model, subset))
            except ValueError:
                continue

    model.loss = pyo.Objective(rule=loss, sense=pyo.minimize, doc="loss")

# calculate distances between dest and src for each customer
customer_distances = [calculate_distance(x1, y1, x2, y2) for x1, y1, x2, y2 in
                      zip(customers_coordX, customers_coordY, customers_destX, customers_destY)]
customer_distances_dict = {cid: dist for cid, dist in zip(customer_ids, customer_distances)}

# calculate distances between dest. of first customer and source of second customer for each pair of customers
customer_pair_distances = {}
for i, id1 in enumerate(customer_ids):
    for j, id2 in enumerate(customer_ids):
        if include_pair(id1, id2):
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
customer_values_dict = {cid: _value(val) for cid, val in zip(customer_ids, customer_distances)}

# customer powerset
customer_powerset = [x for x in list(powerset(customer_ids)) if len(x) > 1]

# launch scenario
r = requests.post(f"http://localhost:8090/Runner/launch_scenario/{scenario_id}?speed={speed}")

"""
Solver Logic
"""

model.customers = pyo.Set(initialize=customer_ids, doc="customers")
model.vehicles = pyo.Set(initialize=vehicle_ids, doc="vehicles")
model.valid_pairs = pyo.Set(dimen=2, initialize=lambda m: [(i, j) for i in model.customers for j in model.customers
                                                  if include_pair(i, j)], doc="valid pairs")

model.customer_destination_distance = pyo.Param(model.customers, initialize=customer_distances_dict,
                                                doc="cd_d")  # dist pickup -> dest
model.next_customer_distance = pyo.Param(model.valid_pairs, initialize=customer_pair_distances,
                                         doc="nc_d")  # dist between each customer
model.vehicle_customer_distance = pyo.Param(model.vehicles, model.customers, initialize=vehicle_customer_distances,
                                            doc="vc_d")  # dist between each vehicle & customer
model.value_function = pyo.Param(model.customers, initialize=customer_values_dict,
                                 doc="v")  # some value based on customer path length (n log n)

model.customer_customer = pyo.Var(model.valid_pairs, within=pyo.Binary, doc="x_cc")
model.vehicle_customer = pyo.Var(model.vehicles, model.customers, within=pyo.Binary, doc="x_vc")
model.waiting_time = pyo.Var(model.customers, within=pyo.NonNegativeIntegers, doc="w")
model.joker = pyo.Var(model.customers, within=pyo.Binary, doc="j")


def vehicle_max_connection(model, vehicle):
    return sum(model.vehicle_customer[vehicle, customer] for customer in model.customers) <= 1


model.vehicle_max_connection = pyo.Constraint(model.vehicles, rule=vehicle_max_connection, doc="v_max")


def customer_max_connection(model, customer1):
    return (sum(
        model.customer_customer[customer1, customer2] for customer2 in model.customers if include_pair(customer1, customer2))
            <= 1 - model.joker[customer1])


model.customer_max_connection = pyo.ConstraintList()

for customer in model.customers:
    const = customer_max_connection(model, customer)

    try:
        model.customer_max_connection.add(const)
    except ValueError:
        continue

def gets_picked_up_once(model, customer1):
    return (sum(
        model.customer_customer[customer2, customer1] for customer2 in model.customers if include_pair(customer2, customer1)) +
            sum(model.vehicle_customer[vehicle, customer1] for vehicle in model.vehicles) + model.joker[customer1]) == 1


model.gets_picked_up_once = pyo.Constraint(model.customers, rule=gets_picked_up_once, doc="pickup")

def waiting_time_chained(model, customer1, customer2):
    return (model.waiting_time[customer1] + model.customer_destination_distance[customer1] +
            model.next_customer_distance[customer1, customer2]) <= model.waiting_time[customer2] + (1 - model.customer_customer[customer1, customer2]) * 100000


model.waiting_time_chained = pyo.ConstraintList()

for c1, c2 in model.valid_pairs:
    if include_pair(c2, c1):
        model.waiting_time_chained.add(waiting_time_chained(model, c1, c2))

def waiting_time_start(model, customer):
    return (sum(model.vehicle_customer[vehicle, customer]
                * model.vehicle_customer_distance[vehicle, customer] for vehicle in model.vehicles)) <= \
        model.waiting_time[customer]


model.waiting_time_start = pyo.Constraint(model.customers, rule=waiting_time_start, doc="wt_s")


def subset_elimination(model, subset):
    return sum(sum(model.customer_customer[customer1, customer2] for customer2 in subset if include_pair(customer1, customer2))
               for customer1 in subset) <= len(subset) - 1


model.subset_elimination_constraints = pyo.ConstraintList()

sorted_sets = {}

for set in customer_powerset:
    if len(set) in sorted_sets:
        sorted_sets[len(set)].append(set)

    else:
        sorted_sets[len(set)] = [set]

for key, value in sorted_sets.items():
    setattr(model, f'set_dim_{key}', pyo.Set(dimen=key, initialize=value))


for key in sorted_sets:
    set = getattr(model, f'set_dim_{key}')
    for subset in set:
        if count(subset) < len(subset):
            continue

        try:
            model.subset_elimination_constraints.add(subset_elimination(model, subset))
        except ValueError:
            continue


def loss(model):
    return sum(model.value_function[customer] * model.waiting_time[customer] +
               model.value_function[customer] * model.joker[customer] * 10000 for customer in model.customers)


model.loss = pyo.Objective(rule=loss, sense=pyo.minimize, doc="loss")



if not collect_data:
    start_time = time.time()
    model.write('_model.lp')

result = opt.solve(model)


for joker in model.joker:
    if math.isclose(model.joker[joker].value, 1, rel_tol=1e-9):
        exceptions.append(joker)
        print(joker)

if exceptions:
    result = opt.solve(model)

connections = []
starts = []
for pair in model.valid_pairs:
    if math.isclose(model.customer_customer[pair].value, 1, rel_tol=1e-9):
        connections.append(pair)

for vehicle in model.vehicles:
    for customer in model.customers:
        if math.isclose(model.vehicle_customer[vehicle, customer].value, 1, rel_tol=1e-9):
            starts.append((vehicle, customer))


print("Starts (Vehicle -> Customer):")
for s in starts:
    print(s[0][:6] + " --> " + s[1][:6])
    
print()
    
print("Connections (Customer -> Customer):")
for c in connections:
    print(c[0][:6] + " --> " + c[1][:6])

print()

wait_times = update_scenario(starts, connections, scenario_id, speed)
print()
print(f"Final Score: {calculate_score(wait_times, customer_distances_dict)}")

test_scores = [3219157.550493392, 2732000, 3626000, 2128000, 2446000, 3536000, 2710000, 3930000, 4232000, 4292000, 3220380.605176285, 2970000, 3726000, 2533460.021475995, 3302262.1820069975, 2934000, 2924000, 3326000, 3132714.785188478, 4482000]
print(f"Average Scores (testing): {sum(test_scores) / len(test_scores)}")

random_scores = [6868000, 10567014.81795604, 7146000, 7572000, 7680000, 7176455.035555141, 8254000, 5641999.312590837, 6147638.373011272, 13873513.48782336, 6942000, 9413235.489025157, 8402000, 5336000, 9676000, 7796000, 11659198.093317661, 9220514.309734384, 8244962.554841987, 8592636.830676384]
print(f"Average Scores (random): {sum(random_scores) / len(random_scores)}")

if not collect_data:
    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)

    print(f"\n{minutes}:{seconds}")

if collect_data:
    speed = 0.0001
    amount_v = 5
    amount_c = 10
    opt_scores = []
    rnd_scores = []

    for i in range(20):
        """
        Update scenario
        """

        # create scenario
        r = requests.post(f"http://localhost:8080/scenario/create?numberOfVehicles={amount_v}&numberOfCustomers={amount_c}")
        r_json = json.loads(r.content.decode())
        scenario_json = r_json
        scenario_id = r_json["id"]

        customers = r_json["customers"]  # [i]["id"] for i = {0,...,n} for n customers
        vehicles = r_json["vehicles"]  # [j]["id"] for j = {0,...,m} for m vehicles

        customers_coordX = [c["coordX"] for c in customers]
        customers_coordY = [c["coordY"] for c in customers]
        customers_destX = [c["destinationX"] for c in customers]
        customers_destY = [c["destinationY"] for c in customers]

        vehicles_coordX = [v["coordX"] for v in vehicles]
        vehicles_coordY = [v["coordY"] for v in vehicles]

        customer_ids = [c["id"] for c in customers]
        vehicle_ids = [v["id"] for v in vehicles]

        # calculate distances between dest and src for each customer
        customer_distances = [calculate_distance(x1, y1, x2, y2) for x1, y1, x2, y2 in
                              zip(customers_coordX, customers_coordY, customers_destX, customers_destY)]
        customer_distances_dict = {cid: dist for cid, dist in zip(customer_ids, customer_distances)}

        # calculate distances between dest. of first customer and source of second customer for each pair of customers
        customer_pair_distances = {}
        for i, id1 in enumerate(customer_ids):
            for j, id2 in enumerate(customer_ids):
                if include_pair(id1, id2):
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
        customer_values_dict = {cid: _value(val) for cid, val in zip(customer_ids, customer_distances)}

        # customer powerset
        customer_powerset = [x for x in list(powerset(customer_ids)) if len(x) > 1]

        """
        Update solver
        """
        model = pyo.ConcreteModel(name="Scheduler")
        opt = pyo.SolverFactory('appsi_highs')  # glpk, cbc, appsi_highs
        exceptions = []

        build_model(model)

        start_time = time.time()
        # model.write('model.lp')
        result = opt.solve(model)

        for joker in model.joker:
            if math.isclose(model.joker[joker].value, 1, rel_tol=1e-6):
                exceptions.append(joker)
                print(joker)

        while True:
            if exceptions:
                build_model(model)
                result = opt.solve(model)
                exceptions = []

            for joker in model.joker:
                if math.isclose(model.joker[joker].value, 1, rel_tol=1e-6):
                    exceptions.append(joker)

            if exceptions:
                print("retry")
            else:
                break


        connections = []
        starts = []
        for pair in model.valid_pairs:
            if math.isclose(model.customer_customer[pair].value, 1, rel_tol=1e-6):
                connections.append(pair)

        for vehicle in model.vehicles:
            for customer in model.customers:
                if math.isclose(model.vehicle_customer[vehicle, customer].value, 1, rel_tol=1e-6):
                    starts.append((vehicle, customer))

        #print(connections)
        #print(starts)
        #print(pyo.value(model.loss))

        r = requests.post("http://localhost:8090/Scenarios/initialize_scenario", json=r_json)
        r = requests.post(f"http://localhost:8090/Runner/launch_scenario/{scenario_id}?speed={speed}")
        opt = update_scenario(starts, connections, scenario_id, speed)

        opt_scores.append(calculate_score(opt, customer_distances_dict))

        #print(wait_times)
        #print(f"solver: {calculate_score(opt, customer_distances_dict)}, random: {calculate_score(rnd, customer_distances_dict)}")

    for i in range(20):
        """
        Update scenario
        """

        # create scenario
        r = requests.post(f"http://localhost:8080/scenario/create?numberOfVehicles={amount_v}&numberOfCustomers={amount_c}")
        r_json = json.loads(r.content.decode())
        scenario_json = r_json
        scenario_id = r_json["id"]

        customers = r_json["customers"]  # [i]["id"] for i = {0,...,n} for n customers
        vehicles = r_json["vehicles"]  # [j]["id"] for j = {0,...,m} for m vehicles

        customers_coordX = [c["coordX"] for c in customers]
        customers_coordY = [c["coordY"] for c in customers]
        customers_destX = [c["destinationX"] for c in customers]
        customers_destY = [c["destinationY"] for c in customers]

        customer_ids = [c["id"] for c in customers]
        vehicle_ids = [v["id"] for v in vehicles]

        # calculate distances between dest and src for each customer
        customer_distances = [calculate_distance(x1, y1, x2, y2) for x1, y1, x2, y2 in
                              zip(customers_coordX, customers_coordY, customers_destX, customers_destY)]
        customer_distances_dict = {cid: dist for cid, dist in zip(customer_ids, customer_distances)}

        random_payload = randomized_payload(vehicles, customers)

        r = requests.post("http://localhost:8090/Scenarios/initialize_scenario", json=r_json)
        r = requests.post(f"http://localhost:8090/Runner/launch_scenario/{scenario_id}?speed={speed}")

        rnd = update_scenario_dist(random_payload, scenario_id, speed)

        rnd_scores.append(calculate_score(rnd, customer_distances_dict))

    print(opt_scores)
    print(rnd_scores)

