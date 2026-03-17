from typing import List, Dict, Any
from .lap_calculator import calculate_lap_time

def simulate_race(race_config: Dict[str, Any], strategies: Dict[str, Any]) -> List[str]:
    total_laps = race_config["total_laps"]
    base = race_config["base_lap_time"]
    pit_time = race_config["pit_lane_time"]
    temp = race_config["track_temp"]
    
    results = []
    for pos_key, strat in strategies.items():
        driver_id = strat["driver_id"]
        grid_pos = int(pos_key[3:])
        current_tire = strat["starting_tire"]
        total_time = 0.0
        stint_laps = 0
        pit_index = 0
        
        # Sort pit stops just in case they are not in order
        stops = sorted(strat.get("pit_stops", []), key=lambda x: x["lap"])
        
        for lap in range(1, total_laps + 1):
            total_time += calculate_lap_time(base, current_tire, stint_laps, temp)
            stint_laps += 1
            
            # Check if pit this lap
            if pit_index < len(stops) and stops[pit_index]["lap"] == lap:
                total_time += pit_time
                current_tire = stops[pit_index]["to_tire"]
                stint_laps = 0
                pit_index += 1
        
        results.append((driver_id, total_time, grid_pos))
    
    # Sort by total time, tie-break by grid position
    # The user's Step 3 didn't mention grid position, but Step 2 did implicitly
    # and it's standard for these challenges.
    results.sort(key=lambda x: (round(x[1], 10), x[2]))
    return [d[0] for d in results]
