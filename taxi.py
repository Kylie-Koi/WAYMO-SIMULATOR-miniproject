import pygame
import math
import random

from constants import *


class Taxi:

    def __init__(self, city, stats, start_node=0):
        
        self.city = city

        self.stats = stats

        #taxi start place
        start = random.choice(list(city.graph.keys()))
        self.current_node = start
        self.x, self.y = city.nodes[start]

        self.route = []
        self.route_index = 0
        self.choose_new_destination()

        self.passenger = None

        self.goal_x = self.x
        self.goal_y = self.y

        self.destination_node = None

        self.trip_distance = 0

        # Load taxi image
        self.image = pygame.image.load("assets/taxi.png").convert_alpha()

        # Resize it
        self.image = pygame.transform.smoothscale(
            self.image,
            (60, 35)
        )

        self.rotated_image = self.image



        self.speed = TAXI_SPEED

        self.angle = 0

        self.state = "IDLE"

        self.color = (255, 220, 0)

        self.total_distance = 0

        self.empty_distance = 0

        self.occupied_distance = 0

        self.battery = 100.0

    # ------------------------------------------

    def choose_new_destination(self):

        destination = random.choice(
            list(self.city.graph.keys())
        )

        while destination == self.current_node:
            destination = random.choice(
                list(self.city.graph.keys())
            )

        self.set_route(destination)
    
    
    def set_route(self, destination):

        self.route = self.city.find_path(
            self.current_node,
            destination
        )

        # If we're already there, there is no "next" node
        if len(self.route) <= 1:
            self.route_index = len(self.route)
        else:
            self.route_index = 1

        print("--------------------------------")
        print("Current:", self.current_node)
        print("Destination:", destination)
        print("Route:", self.route)

    # ------------------------------------------

    def update(self):
        
        
        if self.battery <= 0:
            self.state = "OUT_OF_BATTERY"
            return

        # -----------------------
        # No passenger
        # -----------------------

        if self.state == "IDLE":

            if self.route_index < len(self.route):

                next_node = self.route[self.route_index]

                tx, ty = self.city.nodes[next_node]

                if self.move_towards(tx, ty):

                    self.current_node = next_node
                    self.route_index += 1


                    # Finished the patrol route?
                    if self.route_index >= len(self.route):
                        self.choose_new_destination()

            return

        # -----------------------
        # Going to pickup
        # -----------------------

        
        if self.state == "GOING_TO_PICKUP":
            
            # Already at pickup location
            if self.current_node == self.passenger.pickup_node:

                self.passenger.picked_up = True
                self.passenger.status = "RIDING"
                
                print("Picked up passenger")
                print("Current node:", self.current_node)
                print("Destination node:", self.passenger.destination_node)
                self.state = "WITH_PASSENGER"
                self.set_route(self.passenger.destination_node)
                return

            if self.route_index < len(self.route):

                next_node = self.route[self.route_index]

                tx, ty = self.city.nodes[next_node]

                if self.move_towards(tx, ty):

                    self.current_node = next_node
                    self.route_index += 1

                    # Have we reached the pickup location?
                    if self.route_index >= len(self.route):

                        self.passenger.picked_up = True
                        self.passenger.status = "RIDING"

                        self.state = "WITH_PASSENGER"

                        # Compute a new route to the destination
                        self.set_route(self.passenger.destination_node)

            return

        # -----------------------
        # Driving passenger
        # -----------------------

        if self.state == "WITH_PASSENGER":
            print("HAS")

            # Already at destination
            if self.current_node == self.passenger.destination_node:

                self.passenger.status = "ARRIVED"

                self.stats.completed_rides += 1
                
                self.stats.total_wait_time += self.passenger.wait_time
                self.stats.max_wait_time = max(
                    self.stats.max_wait_time,
                    self.passenger.wait_time
                )

                revenue = BASE_FARE + self.trip_distance * FARE_PER_PIXEL

                maintenance = self.trip_distance * MAINTENANCE_COST_PER_PIXEL

                battery_cost = self.trip_distance * BATTERY_COST_PER_PIXEL

                profit = revenue - maintenance - battery_cost

                self.stats.total_revenue += revenue
                self.stats.total_operating_cost += maintenance + battery_cost
                self.stats.total_profit += profit

                self.trip_distance = 0

                self.passenger = None

                self.state = "IDLE"
                self.choose_new_destination()
                return

            if self.route_index < len(self.route):
                print("HAS2")
                next_node = self.route[self.route_index]
                print("Route:", self.route)
                print("Route index:", self.route_index)

                tx, ty = self.city.nodes[next_node]

                print("----------------")
                print("Taxi:", round(self.x,1), round(self.y,1))
                print("Target node:", next_node)
                print("Target:", tx, ty)
                print("Distance:", math.hypot(tx-self.x, ty-self.y))

                if self.move_towards(tx, ty):
                    print("MOVE RETURNED TRUE")
                    print("HAS3")
                    self.current_node = next_node
                    self.route_index += 1

                    # Have we reached the destination?
                    if self.route_index >= len(self.route):

                        self.passenger.status = "ARRIVED"

                        self.stats.completed_rides += 1
                        
                        self.stats.total_wait_time += self.passenger.wait_time
                        self.stats.max_wait_time = max(
                            self.stats.max_wait_time,
                            self.passenger.wait_time
                        )

                        print("DONE")

                        revenue = BASE_FARE + self.trip_distance * FARE_PER_PIXEL

                        maintenance = self.trip_distance * MAINTENANCE_COST_PER_PIXEL

                        battery_cost = self.trip_distance * BATTERY_COST_PER_PIXEL

                        profit = revenue - maintenance - battery_cost

                        self.stats.total_revenue += revenue
                        self.stats.total_operating_cost += maintenance + battery_cost
                        self.stats.total_profit += profit

                        self.trip_distance = 0

                        self.passenger = None

                        self.state = "IDLE"

                        self.choose_new_destination()
                    print("New position:", round(self.x,1), round(self.y,1))

            return
        
    def move_towards(self, tx, ty):
        

        dx = tx - self.x
        dy = ty - self.y

        distance = math.hypot(dx, dy)

        # Already there (or extremely close)
        if distance <= 1:
            self.x = tx
            self.y = ty
            return True

        # How far to move this frame
        step = min(self.speed, distance)

        if self.state == "WITH_PASSENGER":
            self.trip_distance += step

        self.x += step * dx / distance
        self.y += step * dy / distance

        self.battery = max(0, self.battery - BATTERY_DRAIN)

        self.total_distance += step

        if self.state == "WITH_PASSENGER":
            self.occupied_distance += step
            
        else:
            self.empty_distance += step

        #if reached the target this frame, snap exactly to it
        if step == distance:
            self.x = tx
            self.y = ty
            print("REACHED NODE")
            return True

        print("step =", step, "distance =", distance)
        return False
    # ------------------------------------------

    def draw(self, screen):
        if self.battery <= 0:
            pygame.draw.line(
                screen,
                (255,0,0),
                (self.x-15,self.y-15),
                (self.x+15,self.y+15),
                3
            )

            pygame.draw.line(
                screen,
                (255,0,0),
                (self.x+15,self.y-15),
                (self.x-15,self.y+15),
                3
            )
        
        self.rotated_image = pygame.transform.rotate(
            self.image,
            self.angle
        )

        rect = self.rotated_image.get_rect(
            center=(self.x, self.y)
        )

        screen.blit(
            self.rotated_image,
            rect
        )

        # Battery bar

        pygame.draw.rect(
            screen,
            (70,70,70),
            (
                self.x-15,
                self.y-28,
                30,
                5
            )
        )

        pygame.draw.rect(
            screen,
            (0,220,0),
            (
                self.x-15,
                self.y-28,
                30*(self.battery/100),
                5
            )
        )
