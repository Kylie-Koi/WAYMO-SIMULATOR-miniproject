import pygame

class Passenger:

    def __init__(self, city, pickup_node, destination_node):

        self.city = city

        self.pickup_node = pickup_node
        self.destination_node = destination_node

        self.x, self.y = city.nodes[pickup_node]

        self.wait_time = 0

        self.picked_up = False

        self.status = "WAITING"

    def update(self):
        if not self.picked_up:
            self.wait_time += 1

    def draw(self, screen):

        if self.picked_up:
            return

        pygame.draw.circle(
            screen,
            (0, 0, 255),
            (int(self.x), int(self.y)),
            12
        )

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (int(self.x), int(self.y)),
            12,
            3
        )