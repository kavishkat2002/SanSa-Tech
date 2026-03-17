import json
from .tire_model import Compound, TireModel

class Driver:
    def __init__(self, driver_id, starting_tire, pit_stops, grid_pos, config):
        self.driver_id = driver_id
        self.grid_pos = grid_pos
        self.config = config
        self.tire_model = TireModel(Compound(starting_tire), config['track_temp'])
        self.pit_stops = {p['lap']: p['to_tire'] for p in pit_stops}
        self.tire_age = 0
        self.total_time = 0.0

    def simulate_lap(self, lap_number):
        self.tire_age += 1
        lap_delta = self.tire_model.get_lap_delta(self.tire_age)
        self.total_time += self.config['base_lap_time'] + lap_delta
        
        if lap_number in self.pit_stops:
            self.tire_model = TireModel(Compound(self.pit_stops[lap_number]), self.config['track_temp'])
            self.tire_age = 0
            self.total_time += self.config['pit_lane_time']

class RaceEngine:
    def __init__(self, race_data):
        self.race_id = race_data['race_id']
        self.config = race_data['race_config']
        self.drivers = []
        
        for pos_key, data in race_data['strategies'].items():
            grid_pos = int(pos_key[3:])
            self.drivers.append(Driver(
                data['driver_id'], 
                data['starting_tire'], 
                data['pit_stops'], 
                grid_pos,
                self.config
            ))

    def run(self):
        for lap in range(1, self.config['total_laps'] + 1):
            for driver in self.drivers:
                driver.simulate_lap(lap)
        
        # Sort by deterministic criteria
        self.drivers.sort(key=lambda d: (round(d.total_time, 10), d.grid_pos))
        return [d.driver_id for d in self.drivers]
