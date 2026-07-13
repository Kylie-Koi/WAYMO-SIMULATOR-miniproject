class Stats:

    def __init__(self):

        self.total_passengers = 0
        self.completed_rides = 0

        self.total_wait_time = 0

        self.total_distance = 0

        self.total_empty_distance = 0
        self.total_occupied_distance = 0

        self.total_battery_used = 0

        #skibidi important statistics (financier)
        self.total_revenue = 0
        self.total_operating_cost = 0
        self.total_profit = 0

        #ride statistics stuff hehe
        self.total_trip_distance = 0
        self.total_empty_distance = 0

        self.max_wait_time = 0

        self.total_dispatch_distance = 0
        self.dispatches = 0

    def average_wait(self):

        if self.completed_rides == 0:
            return 0

        return self.total_wait_time / self.completed_rides
    
    def average_dispatch_distance(self):
        if self.dispatches == 0:
            return 0
        return self.total_dispatch_distance / self.dispatches