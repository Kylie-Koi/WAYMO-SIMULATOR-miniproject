import math


class Dispatcher:

    def __init__(self):
        pass

    def assign(self, taxis, passengers):

        for passenger in passengers:

            if passenger.status != "WAITING":
                continue

            already_assigned = False

            for taxi in taxis:
                if taxi.passenger == passenger:
                    already_assigned = True

            if already_assigned:
                continue

            best = None
            best_distance = float("inf")

            for taxi in taxis:

                if taxi.state != "IDLE":
                    continue

                dx = taxi.x - passenger.x
                dy = taxi.y - passenger.y

                d = math.hypot(dx, dy)

                if d < best_distance:

                    best_distance = d
                    best = taxi

            if best:

                best.passenger = passenger

                best.stats.total_dispatch_distance += best_distance
                best.stats.dispatches += 1
                
                best.state = "GOING_TO_PICKUP"
                best.set_route(passenger.pickup_node)