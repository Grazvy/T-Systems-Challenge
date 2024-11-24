import math
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
        customers_copy.pop(random_customer)
        payload["vehicles"].append({"id": cars[random_car]["id"], "customerId": customers_copy[random_customer]["id"]})
        customers_copy.remove(random_customer)

    return payload


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
