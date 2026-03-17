from .tire_model import COMPOUND_OFFSET, DEGRADATION, TEMP_FACTOR

def calculate_lap_time(base: float, tire: str, stint_laps: int, track_temp: int) -> float:
    """
    stint_laps: 0 for the first lap of a stint.
    """
    return (base +
            COMPOUND_OFFSET[tire] +
            DEGRADATION[tire] * (stint_laps ** 2) +
            TEMP_FACTOR * track_temp)
