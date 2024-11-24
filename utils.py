import math
import json
import time
import requests
import matplotlib.pyplot as plt
import pyomo.environ as pyo
import random


def calculate_remaining_travel_time(vehicle_coord_x, vehicle_coord_y, customer_coord_x, customer_coord_y, speed):
    """
    Calculate the remaining travel time based on the vehicle's and customer's coordinates.

    :param vehicle_coord_x: Latitude of the vehicle
    :param vehicle_coord_y: Longitude of the vehicle
    :param customer_coord_x: Latitude of the customer
    :param customer_coord_y: Longitude of the customer
    :param speed: Speed in meters per second
    :return: Remaining travel time in seconds
    """

    # Convert degrees to radians
    lat1 = math.radians(vehicle_coord_x)
    lon1 = math.radians(vehicle_coord_y)
    lat2 = math.radians(customer_coord_x)
    lon2 = math.radians(customer_coord_y)

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in meters
    r = 6371000  # radius of Earth in meters
    distance = r * c  # Distance in meters

    # Calculate time in seconds (distance/speed)
    if speed <= 0:
        raise ValueError("Speed must be greater than zero to calculate travel time.")

    remaining_travel_time = distance / speed  # in seconds
    return round(remaining_travel_time)


def calculate_distance(lat1, lon1, lat2, lon2):
    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance in meters
    distance = 6371000 * c
    return distance


def randomized_payload(cars, customers):
    cars_len = len(cars)
    customers_copy = list(customers)
    payload = {"vehicles": []}

    for i in range(len(customers_copy)):
        random_car = random.randint(0, cars_len - 1)
        random_customer = random.randint(0, len(customers_copy) - 1)
        payload["vehicles"].append({"id": cars[random_car]["id"], "customerId": customers_copy[random_customer]["id"]})
        customers_copy.pop(random_customer)

    return payload


def visualize_compare_cars(len_cars, results):
    #for now: one car less for every result
    #results go from full car setup to lowest car setup

    categories = []
    for i in range(len(results)):
        categories.append(len_cars - i)

    print(categories)

    plt.bar(categories, results)


    plt.xlabel('Number of Cars')
    plt.ylabel('Total Wait Time')
    plt.title('Customer Dissatisfaction')
    plt.show()

def plot_distance_distribution(model):
    distances = [pyo.value(model.customer_destination_distance[c]) for c in model.customers]

    # Plot the histogram
    plt.figure(figsize=(8, 5))
    plt.hist(distances, bins=5, edgecolor="black", color="skyblue", alpha=0.7)
    plt.title("Distribution of Customer Destination Distances")
    plt.xlabel("Distance")
    plt.ylabel("Frequency")
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.show()
    
def update_scenario(starts, connections, scenario_id, speed):
    # update scenario
    print("starting simulation")
    payload = {"vehicles":[{"id":x, "customerId":y} for (x,y) in starts]}
    payload_json = json.dumps(payload)
    r = requests.put(f"http://localhost:8090/Scenarios/update_scenario/{scenario_id}", json=json.loads(payload_json))
    r_json = json.loads(r.content.decode())        

    # first, for each customer, find them as the first element in a tuple in "connections"
    # this counts as a queue, and the driver responsible will go through the queue until finished
    # if no one follows in the queue, we're done
    updated_vehicles = r_json["updatedVehicles"]
    updated_vehicles_times = [{v["id"]: v["remainingTravelTime"]} for v in updated_vehicles]
    queues = {} # this will contain the remaining vehicle paths...
    time_elapsed = 0
    wait_times = [{v["customerId"]: v["remainingTravelTime"]} for v in updated_vehicles]
    for (vehicle, customer) in starts:
        queues[vehicle] = [customer]
        i = 0
        while i < len(connections):
            if connections[i][0] == customer:
                queues[vehicle].append(connections[i][1])
                customer = connections[i][1]
                i = 0
            else:
                i += 1
        if len(queues[vehicle]) == 1:
            del queues[vehicle]
        else:
            queues[vehicle] = queues[vehicle][1:]
                
    # decrement timers; as soon as one hits 0, see which and update status accordingly
    while True:
        # decrement all...
        for vehicle_time in updated_vehicles_times:
            for vehicle_id, remaining_time in vehicle_time.items():
                if remaining_time > 0:
                    vehicle_time[vehicle_id] -= 1
        
        # ... then check if one of them became 0
        # if so, see if the ID which is done has anything left in the queue
        # if not, remove it
        # if it does, dispatch next customer
        for vehicle_time in updated_vehicles_times:
            for vehicle_id, remaining_time in vehicle_time.items():
                if remaining_time == 0:
                    # get time to see if anything changed
                    r = requests.get(f"http://localhost:8090/Scenarios/get_scenario/{scenario_id}")
                    r_json = json.loads(r.content.decode())
                    r_vehicles = r_json["vehicles"]
                    for r_v in r_vehicles:
                        if r_v["id"] == vehicle_id:
                            if r_v["remainingTravelTime"] is not None:
                                vehicle_time[vehicle_id] += r_v["remainingTravelTime"]
                                break
                        
                    if vehicle_time[vehicle_id] != 0:
                        break
                    
                    if not vehicle_id in queues or not queues[vehicle_id]:
                        updated_vehicles_times.remove(vehicle_time)
                    else:
                        next_customer = queues[vehicle_id][0]
                        
                        payload = {"vehicles":[{"id":vehicle_id, "customerId":next_customer}]}
                        payload_json = json.dumps(payload)
                        
                        r = requests.put(f"http://localhost:8090/Scenarios/update_scenario/{scenario_id}", json=json.loads(payload_json))
                        r_json = json.loads(r.content.decode())     
                        
                        new_updated = r_json["updatedVehicles"]
                        new_wait_times = [{v["customerId"]: v["remainingTravelTime"]} for v in new_updated]
                        for item in new_wait_times:
                            for _, val in item.items():
                                val += time_elapsed
                        wait_times = wait_times + new_wait_times
                        
                        
                        queues[vehicle_id] = queues[vehicle_id][1:]
                    break

        if not updated_vehicles_times:
            break
        
        #print(updated_vehicles_times)
        time_elapsed += 1
        time.sleep(speed * 1.5) # safety net

        result = {}
        for dict in wait_times:
            for id, t in dict.items():
                result[id] = t
    print("done")
    return result

def update_scenario_dist(payload, scenario_id, speed):
    # build queues
    vehicles = payload["vehicles"]
    seen_ids = set()
    filtered_list = []
    queue = []

    for entry in vehicles:
        if entry['id'] not in seen_ids:
            filtered_list.append(entry)
            seen_ids.add(entry['id'])
        else:
            queue.append(entry)

    print("Filtered List:", filtered_list)
    print()
    print("Queue:", queue)
    print()
    
    actual_payload = {"vehicles": filtered_list}
    
    # update scenario
    payload_json = json.dumps(actual_payload)
    r = requests.put(f"http://localhost:8090/Scenarios/update_scenario/{scenario_id}", json=json.loads(payload_json))
    r_json = json.loads(r.content.decode())  
    
    updated_vehicles = r_json["updatedVehicles"]
    updated_vehicles_times = [{v["id"]: v["remainingTravelTime"]} for v in updated_vehicles]
    time_elapsed = 0
    wait_times = [{v["customerId"]: v["remainingTravelTime"]} for v in updated_vehicles]
    
    queues = {}

    for entry in queue:
        if entry['id'] not in queues:
            queues[entry['id']] = []
        queues[entry['id']].append(entry['customerId'])
    
    print(updated_vehicles_times)
    print()
    print(wait_times)
    
    while True:
        # decrement all...
        for vehicle_time in updated_vehicles_times:
            for vehicle_id, remaining_time in vehicle_time.items():
                if remaining_time > 0:
                    vehicle_time[vehicle_id] -= 1
        
        # ... then check if one of them became 0
        # if so, see if the ID which is done has anything left in the queue
        # if not, remove it
        # if it does, dispatch next customer
        for vehicle_time in updated_vehicles_times:
            for vehicle_id, remaining_time in vehicle_time.items():
                if remaining_time == 0:
                    # get time to see if anything changed
                    r = requests.get(f"http://localhost:8090/Scenarios/get_scenario/{scenario_id}")
                    r_json = json.loads(r.content.decode())
                    r_vehicles = r_json["vehicles"]
                    for r_v in r_vehicles:
                        if r_v["id"] == vehicle_id:
                            if r_v["remainingTravelTime"] is not None:
                                vehicle_time[vehicle_id] += r_v["remainingTravelTime"]
                                break
                        
                    if vehicle_time[vehicle_id] != 0:
                        break
                    
                    if not vehicle_id in queues or not queues[vehicle_id]:
                        updated_vehicles_times.remove(vehicle_time)
                    else:
                        next_customer = queues[vehicle_id][0]
                        
                        payload = {"vehicles":[{"id":vehicle_id, "customerId":next_customer}]}
                        payload_json = json.dumps(payload)
                        
                        r = requests.put(f"http://localhost:8090/Scenarios/update_scenario/{scenario_id}", json=json.loads(payload_json))
                        r_json = json.loads(r.content.decode())     
                        
                        new_updated = r_json["updatedVehicles"]
                        new_wait_times = [{v["customerId"]: v["remainingTravelTime"]} for v in new_updated]
                        for item in new_wait_times:
                            for _, val in item.items():
                                val += time_elapsed
                        wait_times = wait_times + new_wait_times
                        
                        
                        queues[vehicle_id] = queues[vehicle_id][1:]
                    break

        if not updated_vehicles_times:
            break
        
        print(updated_vehicles_times)
        time_elapsed += 1
        time.sleep(speed * 1.5) # safety net
    
    return wait_times
