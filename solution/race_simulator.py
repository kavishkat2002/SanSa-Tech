import sys
import json

def simulate_race(race_config, strategies):
    """
    Simulates the F1 race lap-by-lap based on the provided configuration.
    Accounts for tire degradation, compound offsets, track temperature, and pit stops.
    """
    base = race_config["base_lap_time"]
    pit_time = race_config["pit_lane_time"]
    track_temp = race_config["track_temp"]
    total_laps = race_config["total_laps"]

    # Discovered physics constants for the tire model
    offsets = {"SOFT": -2.8, "MEDIUM": 0.0, "HARD": 3.2}
    degs = {"SOFT": 0.035, "MEDIUM": 0.018, "HARD": 0.009}
    temp_factor = 0.012

    results = []
    
    for pos_key, strat in strategies.items():
        grid_pos = int(pos_key[3:])
        current_tire = strat["starting_tire"]
        stint_laps = 0
        total_time = 0.0
        
        # O(1) lookup for pit stops
        stops = {s["lap"]: s["to_tire"] for s in strat.get("pit_stops", [])}
        
        for lap in range(1, total_laps + 1):
            stint_laps += 1 # Age increases before calculation
            
            # Physics model: base + compound diff + degradation over time + temperature impact
            lap_time = base + offsets[current_tire] + (degs[current_tire] * (stint_laps ** 2)) + (temp_factor * track_temp)
            total_time += lap_time
            
            # Process pit stops at the end of the lap
            if lap in stops:
                total_time += pit_time
                current_tire = stops[lap]
                stint_laps = 0
                
        results.append((strat["driver_id"], total_time, grid_pos))
        
    # Sort ascending by total race time; ties broken by starting grid position
    return [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def main():
    try:
        data = json.load(sys.stdin)
    except Exception as exc:
        sys.stderr.write(f"Error reading input: {exc}\n")
        sys.exit(1)

    finishing = simulate_race(data["race_config"], data["strategies"])
    output = {
        "race_id": data.get("race_id", "UNKNOWN"),
        "finishing_positions": finishing,
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
