import pygame

from constants import *

from city import City
from taxi import Taxi

from passenger import Passenger
from dispatcher import Dispatcher
import random

from stats import Stats

pygame.init()

screen = pygame.display.set_mode((WIDTH,HEIGHT))

pygame.display.set_caption("Waymo Simulator")

clock = pygame.time.Clock()

city = City()

taxis = []

dispatcher = Dispatcher()

stats = Stats()

passengers = []

for i in range(NUM_TAXIS):
    taxi = Taxi(city, stats, i % len(city.nodes))
    taxi.stats = stats
    taxis.append(taxi)

running = True

while running:

    if len(passengers) < MAX_PASSENGERS and random.random() < 0.02:

        pickup = random.randint(0, len(city.nodes)-1)

        destination = random.randint(0, len(city.nodes)-1)

        while destination == pickup:
            destination = random.randint(0, len(city.nodes)-1)

        passengers.append(
            Passenger(city, pickup, destination)
        )
        stats.total_passengers += 1
        print(f"Passenger spawned at node {pickup} -> {destination}")


    clock.tick(FPS)

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False
    
    dispatcher.assign(taxis, passengers)

    fleet_distance = sum(t.total_distance for t in taxis)
    
    occupied = sum(
        1 for t in taxis
        if t.state == "WITH_PASSENGER"
    )

    avg_battery = sum(t.battery for t in taxis) / len(taxis)
    

    if passengers:
        current_wait = (
            sum(p.wait_time for p in passengers)
            / len(passengers)
            / FPS
        )
    else:
        current_wait = 0

    empty = sum(t.empty_distance for t in taxis)
    occupied = sum(t.occupied_distance for t in taxis)

    city.draw(screen)

    for passenger in passengers:
        passenger.update()
        passenger.draw(screen)
    passengers = [
        p for p in passengers
        if p.status != "ARRIVED"
    ]

    for taxi in taxis:
        taxi.update()
        taxi.draw(screen)
    
    font = pygame.font.SysFont(None, 28)

    screen.blit(
        font.render(
            f"Passengers: {len(passengers)}",
            True,
            (255,255,255)
        ),
        (15,15)
    )

    screen.blit(
        font.render(
            f"Completed: {stats.completed_rides}",
            True,
            (255,255,255)
        ),
        (15,45)
    )

    screen.blit(
    font.render(
        f"Revenue: ${stats.total_revenue:.2f}",
        True,
        (255,255,255)
    ),
    (15,75)
)

    screen.blit(
        font.render(
            f"Cost: ${stats.total_operating_cost:.2f}",
            True,
            (255,255,255)
        ),
        (15,105)
    )


    screen.blit(
        font.render(
            f"Profit: ${stats.total_profit:.2f}",
            True,
            (255,255,255)
        ),
        (15,135)
    )

    screen.blit(
        font.render(
            f"AVG Wait: {stats.average_wait()/FPS:.1f}s",
            True,
            (255,255,255)
        ),
        (15,165)
    )
    screen.blit(
        font.render(
            f"Distance: {fleet_distance:.0f}pixels(px)",
            True,
            (255,255,255)
        ),
        (15,195)
    )

    screen.blit(
        font.render(
            f"Occupied: {occupied}/{len(taxis)}",
            True,
            (255,255,255)
        ),
        (15,225)
    )

    screen.blit(
        font.render(
            f"AVG Battery: {avg_battery:.1f}%",
            True,
            (255,255,255)
        ),
        (15,255)
    )

    screen.blit(
        font.render(
            f"Current Wait: {current_wait:.1f}s",
            True,
            (255,255,255)
        ),
        (15,285)
    )

    screen.blit(
        font.render(
            f"Empty: {empty:.0f}px",
            True,
            (255,255,255)
        ),
        (15,315)
    )

    screen.blit(
        font.render(
            f"Occupied Dist: {occupied:.0f}px",
            True,
            (255,255,255)
        ),
        (15,345)
    )

    screen.blit(
        font.render(
            #Dispatch efficiency, compute how far it is
            f"Avg Dispatch: {stats.average_dispatch_distance():.0f}px",
            True,
            (255,255,255)
        ),
        (15, 375)

    )

    screen.blit(
        font.render(
            f"Longest Wait: {stats.max_wait_time/FPS:.1f}s",
            True,
            (255,255,255)
        ),
        (15, 405)
    )

    
    
    
    

    pygame.display.flip()

pygame.quit()