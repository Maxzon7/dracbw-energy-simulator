class BaselineScenario:
    def __init__(self, monthly_consumption, days_per_week, hours_per_day, num_connections, amperage, enable_noise, noise_percentage):
        #user input
        self.monthly_consumption = monthly_consumption
        self.days_per_week = days_per_week
        self.hours_per_day = hours_per_day
        
        self.num_connections = num_connections
        self.amperage = amperage
        
        self.enable_noise = enable_noise
        self.noise_percentage = noise_percentage
        
        # profile is empty in the beginning, will get filled after the calcualtion
        self.load_profile = None