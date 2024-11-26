from solver import Solver
import requests
import json

# create scenario
r = requests.post("http://localhost:8080/scenario/create")
r_json = json.loads(r.content.decode())
scenario_id = r_json["id"]

# initialize scenario (default values)
r = requests.post("http://localhost:8090/Scenarios/initialize_scenario", json=r_json)
r_json = json.loads(r.content.decode())

customers = r_json["scenario"]["customers"]  # [i]["id"] for i = {0,...,n} for n customers
vehicles = r_json["scenario"]["vehicles"]  # [j]["id"] for j = {0,...,m} for m vehicles

Solver.setup(customers, vehicles)
Solver(customers, vehicles)