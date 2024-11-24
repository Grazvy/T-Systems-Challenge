import requests
import orfuncs
import json

def distance_optimize(vehicles, customers):
    # THIS IS THE OPTIMIZER
    # RESULT = dimensions(cars, assigned customers in the order of pick_up to this car)
    result = orfuncs.solve(vehicles, customers)

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
            payload["vehicles"].append({"id": vehicles[i]["id"], "customerId": customers[result[i][j]]["id"]})

    return payload
