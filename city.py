import pygame
import random
from collections import deque
from constants import *

class City:

    def __init__(self):

        # Road intersections (graph nodes)

        self.nodes = [

            (250, 180),
            (700, 180),
            (1100, 180),

            (250, 450),
            (700, 450),
            (1100, 450),

            (250, 720),
            (700, 720),
            (1100, 720)

        ]
        # Which intersections are connected by roads
        self.graph = {
            0: [1, 3],
            1: [0, 2, 4],
            2: [1, 5],

            3: [0, 4, 6],
            4: [1, 3, 5, 7],
            5: [2, 4, 8],

            6: [3, 7],
            7: [4, 6, 8],
            8: [5, 7]
        }

    # =========================================

    def draw(self, screen):

        screen.fill(GRASS)

        # -------------------------
        # Districts
        # -------------------------

        pygame.draw.rect(screen, DOWNTOWN, (0, 0, 450, 300))
        pygame.draw.rect(screen, AIRPORT, (1000, 0, 400, 300))
        pygame.draw.rect(screen, RESIDENTIAL, (0, 600, 500, 300))
        pygame.draw.rect(screen, PARK, (1000, 600, 400, 300))

        # -------------------------
        # Roads
        # -------------------------

        self.draw_horizontal(screen, 180)
        self.draw_horizontal(screen, 450)
        self.draw_horizontal(screen, 720)

        self.draw_vertical(screen, 250)
        self.draw_vertical(screen, 700)
        self.draw_vertical(screen, 1100)

        # -------------------------
        # Buildings
        # -------------------------

        self.draw_buildings(screen)

        # -------------------------
        # Intersections
        # -------------------------

        self.draw_intersections(screen)

    # =========================================

    def draw_horizontal(self, screen, y):

        pygame.draw.line(
            screen,
            ROAD_EDGE,
            (0, y),
            (WIDTH, y),
            ROAD_WIDTH + 4
        )

        pygame.draw.line(
            screen,
            ROAD,
            (0, y),
            (WIDTH, y),
            ROAD_WIDTH
        )

        for x in range(0, WIDTH, 60):

            pygame.draw.line(
                screen,
                YELLOW,
                (x, y),
                (x + 30, y),
                4
            )

    # =========================================

    def draw_vertical(self, screen, x):

        pygame.draw.line(
            screen,
            ROAD_EDGE,
            (x, 0),
            (x, HEIGHT),
            ROAD_WIDTH + 4
        )

        pygame.draw.line(
            screen,
            ROAD,
            (x, 0),
            (x, HEIGHT),
            ROAD_WIDTH
        )

        for y in range(0, HEIGHT, 60):

            pygame.draw.line(
                screen,
                YELLOW,
                (x, y),
                (x, y + 30),
                4
            )

    # =========================================

    def draw_intersections(self, screen):

        for x, y in self.nodes:

            pygame.draw.circle(
                screen,
                ROAD,
                (x, y),
                ROAD_WIDTH // 2
            )

    # =========================================

    def draw_buildings(self, screen):

        # Downtown

        for x in range(30, 400, 80):

            for y in range(30, 250, 80):

                pygame.draw.rect(
                    screen,
                    BUILDING,
                    (x, y, 45, 45)
                )

        # Airport

        for x in range(1030, 1360, 80):

            for y in range(40, 250, 80):

                pygame.draw.rect(
                    screen,
                    BUILDING,
                    (x, y, 45, 45)
                )

        # Residential

        for x in range(40, 420, 80):

            for y in range(630, 850, 80):

                pygame.draw.rect(
                    screen,
                    BUILDING,
                    (x, y, 45, 45)
                )

    def random_road_position(self):
        from collections import deque

        # Choose a random intersection
        start = random.choice(list(self.graph.keys()))

        # Choose one connected road
        end = random.choice(self.graph[start])

        x1, y1 = self.nodes[start]
        x2, y2 = self.nodes[end]

        # Random point between them
        t = random.random()

        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t

        return x, y, start, end
    
    def find_path(self, start, goal):

        queue = deque()
        queue.append([start])

        visited = set()

        while queue:

            path = queue.popleft()
            node = path[-1]

            if node == goal:
                return path

            if node not in visited:

                visited.add(node)

                for neighbor in self.graph[node]:

                    new_path = list(path)
                    new_path.append(neighbor)

                    queue.append(new_path)

        return []