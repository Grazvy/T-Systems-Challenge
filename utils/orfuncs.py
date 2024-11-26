from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np


def create_array(cars, customers):
    size = 1 + len(cars) + 2 * len(customers)
    len_cars = len(cars)
    len_customers = len(customers)
    complete = [0] + cars + customers + customers
    arr = [[0 for _ in range(size)] for _ in range(size)]

    for i in range(1, size):
        for j in range(i, size):
            if i <= len_cars + len_customers and j <= len_cars + len_customers:
                arr[i][j] = int(10000 * np.sqrt(np.power(complete[i]["coordX"] - complete[j]["coordX"], 2) +
                                    np.power(complete[i]["coordY"] - complete[j]["coordY"], 2)))

            elif i <= len_cars + len_customers < j:
                arr[i][j] = int(10000 * np.sqrt(np.power(complete[i]["coordX"] - complete[j]["destinationX"], 2) +
                                    np.power(complete[i]["coordY"] - complete[j]["destinationY"], 2)))

            elif i > len_cars + len_customers >= j:
                arr[i][j] = int(10000 * np.sqrt(np.power(complete[i]["destinationX"] - complete[j]["coordX"], 2) +
                                    np.power(complete[i]["destinationY"] - complete[j]["coordY"], 2)))

            elif i > len_cars + len_customers and j > len_customers + len_cars:
                arr[i][j] = int(10000 * np.sqrt(np.power(complete[i]["destinationX"] - complete[j]["destinationX"], 2) +
                                    np.power(complete[i]["destinationY"] - complete[j]["destinationY"], 2)))

            if i != j:
                arr[j][i] = arr[i][j]
    return arr


def create_data_model(cars, customers):
    """Stores the data for the problem."""
    len_cars = len(cars)
    len_customers = len(customers)

    data = {}

    #data["distance_matrix"] = [
         #fmt: off
     #   [0, 0, 0, 0, 0, 0, 0],
      #  [0, 0, 100, 5, 10, 2, 2],
       # [0, 100, 0, 20, 5, 2, 2],
       # [0, 5, 20, 0, 2, 1, 2],
       # [0, 10, 5, 1, 0, 2, 1],
       # [0, 2, 2, 2, 1, 0, 100],
       # [0, 2, 2, 2, 1, 100, 0]
        # fmt: on
    #]

    data["distance_matrix"] = create_array(cars, customers)

    #data["pickups_deliveries"] = [
     #   [3, 5],
      #  [4, 6],
    #]

    data["pickups_deliveries"] = [
        [i, i + len_customers] for i in range(1 + len_cars, 1 + len_cars + len_customers)
    ]

    data["num_vehicles"] = len_cars
    #data["num_vehicles"] = 2

    data["starts"] = [i for i in range(1, len_cars + 1)]
    #data["starts"] = [1, 2]

    data["ends"] = [0 for _ in range(len_cars)]
    #data["ends"] = [0, 0]

    data["vehicle_capacities"] = [1 for _ in range(len_cars)]
    data["demands"] = [0] + [0 for _ in range(len_cars)] + [1 for _ in range(len_customers)] + [-1 for _ in range(len_customers)]

    return data


def print_solution(data, manager, routing, solution, cars, customers):
    """Prints solution on console."""
    print(f"Objective: {solution.ObjectiveValue()}")
    route_per_car = []
    len_car = len(cars)
    len_customer = len(customers)
    total_distance = 0
    for vehicle_id in range(data["num_vehicles"]):
        route_per_car.append([])
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        route_distance = 0
        while not routing.IsEnd(index):
            route_per_car[vehicle_id].append(index - len_car)
            plan_output += f" {manager.IndexToNode(index)} -> "
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )
        plan_output += f"{manager.IndexToNode(index)}\n"
        plan_output += f"Distance of the route: {route_distance}m\n"
        print(plan_output)
        total_distance += route_distance
    print(f"Total Distance of all routes: {total_distance}m")
    return route_per_car


def solve(cars, customers):
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model(cars, customers)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]), data["num_vehicles"], data["starts"], data["ends"]
    )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Define cost of each arc.
    def distance_callback(from_index, to_index):
        """Returns the manhattan distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distance_matrix"][from_node][to_node]

    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    demand_callback_index = routing.RegisterUnaryTransitCallback(
        demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    # Add Distance constraint.
    dimension_name = "Distance"
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        3000,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name,
    )
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Define Transportation Requests.
    for request in data["pickups_deliveries"]:
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
        )
        routing.solver().Add(
            distance_dimension.CumulVar(pickup_index)
            <= distance_dimension.CumulVar(delivery_index)
        )


    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        return print_solution(data, manager, routing, solution, cars, customers)
    return []



