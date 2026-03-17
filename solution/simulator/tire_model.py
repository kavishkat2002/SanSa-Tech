from enum import Enum

class Compound(Enum):
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

class TireModel:
    def __init__(self, compound: Compound, track_temp: float):
        self.compound = compound
        self.track_temp = track_temp
        
        self.SPEED_OFFSETS = {
            Compound.SOFT: -1.0,
            Compound.MEDIUM: 0.0,
            Compound.HARD: 1.0
        }
        
        self.BASE_DEGRADATION = {
            Compound.SOFT: 0.15,
            Compound.MEDIUM: 0.10,
            Compound.HARD: 0.05
        }
        
    def get_lap_delta(self, age: int) -> float:
        # lap_time = base + tire_speed + (tire_age * degradation)
        # Testing a small plateau or age adjustment
        # age 1 on fresh tires
        offset = self.SPEED_OFFSETS[self.compound]
        deg = self.BASE_DEGRADATION[self.compound]
        
        # If age starts at 1, but degradation starts after Lap 1?
        return offset + (age * deg)
