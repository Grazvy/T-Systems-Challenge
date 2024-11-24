import requests
import stolenCode
import json

# create scenario
#
#r = requests.post("http://localhost:8080/scenario/create")
#r_json = json.loads(r.content.decode())
#
#scenario_id = r_json["id"]
#
# initialize scenario (default values)
#r = requests.post("http://localhost:8090/Scenarios/initialize_scenario", json=r_json)
#r = requests.post(f"http://localhost:8090/Runner/launch_scenario/{scenario_id}")
#r = requests.get(f"http://localhost:8090/Scenarios/get_scenario/{scenario_id}")
#r_json = json.loads(r.content.decode())

#customers = r_json["customers"]
#vehicles = r_json["vehicles"]

#print(str(len(vehicles)) + " vehicles")
#print(str(len(customers)) + " customers")
#print(vehicles[4]["customerId"])
#print(customers[0])


def distance_optimize(vehicles, customers):
    # THIS IS THE OPTIMIZER
    # RESULT = dimensions(cars, assigned customers in the order of pick_up to this car)
    result = stolenCode.solve(vehicles, customers)

    for rez in result:
        rez.pop(0)
        for i in range(len(rez) - 1, -1, -1):
            if i % 2 != 0:
                rez.pop(i)

    print(result)  # indexes of clients cars should be assigned to

    payload = {"vehicles": []}

    # initialize
    for i in range(len(result)):
        for j in range(len(result[i])):
            payload["vehicles"].append({"id": vehicles[i]["id"], "customerId": customers[result[i][0]]["id"]})

    return payload


# send first payload
#payload_json = json.dumps(payload)
#r = requests.put(f"http://localhost:8090/Scenarios/update_scenario/{scenario_id}", json=json.loads(payload_json))
