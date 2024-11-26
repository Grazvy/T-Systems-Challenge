### This is the backend for our project at hackaTUM 2024

## Usage
- `pip install -r requirements.txt`
- `python3 main.py`

## Inspiration
Nobody likes waiting - that's something both the consumer and the company have in common. At best, it wastes time. At worst, it wastes money. This is why flotteFlotte allows companies to easily and automatically manage and monitor a fleet of self-driving vehicles, maximizing productivity on both sides by keeping wait times low and prioritizing longer routes to keep the taxis always on the go. 

## What it does
At its core, the program optimizes for two metrics:
- Minimization of a customer's waiting time. The more a customer waits, the higher their dissatisfaction and the lower the company's potential throughput.
- Prioritization of longer routes. Longer routes mean constant fares and less time for a vehicle to remain idle or to travel without a passenger.

A simple implementation would, however, be too inefficient. This is why we take other constraints into account, such as:
- the proximity of a client's destination to another client's pick-up spot (can we make a fast chain of pick-ups and deliveries?)
- the effective radius around a client or a vehicle (should a taxi really have to drive across the whole city?)

Additionally, flotteFlotte shows you present statistics and potential profit opportunities by comparing current throughput with similar situations where progressively _less_ vehicles are deployed that could potentially be used for other purposes instead, such as replacements. This makes it easier to choose the right amount of resources.

## How we built it
The backend is primarily written in Python, making heavy use of libraries for solving linear and mixed-integer programming problems (such as HiGHS) or various operations research and optimization jobs (such as Google OR-Tools). This ensures fast enough execution and an easy enough workflow without sacrificing too much speed due to Python's inherently interpreted nature. 
The frontend is made in Flutter and is compatible with mobile, (preferably) tablet and (in some instances) desktop devices, allowing for seamless management anywhere you go, regardless of your technical know-how.

## Challenges we ran into
Perhaps dauntingly, the main challenge we ran into was... the challenge itself. We didn't really know what to expect, and a lot of our initial ideas revolved around tweaking the simulation, _not_ developing a solution for it. Soon enough, we realized what we had to do, and went back to the drawing board, this time with a clearer picture in mind.

That was not the end of the story, however, as we soon began to realize just how difficult such a problem could really be, even though it seemed so simplistic at first. Learning new technologies is a given at hackaTUM - only this time with a lot more theoretical research.

## Accomplishments that we're proud of
We're proud of the large amount of research and experimentation we've done in such a short amount of time about a topic none of us really had any idea about - ranging from incorporating personal anecdotes, reading and understanding scientifically-backed research and a whole lot of trial and error. 

## What we learned
Making flotteFlotte gave us a deep theoretical and analytical insight into the complex nature of balancing optimal solution-finding with speed and efficiency - a problem that's all too common in the world of logistics that only gets more complicated the more constraints and factors you consider.

## What's next for flotteFlotte
While we managed to incorporate the core functionality of our project, there are still some ideas and improvements left open; either due to time constraints or due to the purposefully simplistic simulation skeleton, such as:
- Finding better / more precise loss and value functions.
- Incorporating multiple relevant real-world influences (e.g. events, time of day).
- Heatmaps and other front-end QoL features.
- Using different, non-solver / heuristic algorithms for even faster execution, albeit less optimal.
- Multithreading and / or multiprocessing.
