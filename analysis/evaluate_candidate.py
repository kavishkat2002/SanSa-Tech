import json
from pathlib import Path

def simulate(race, soft_b, hard_b, deg_s, deg_m, deg_h, t_f, p):
    config = race["race_config"]
    base = config["base_lap_time"]
    pit_time = config["pit_lane_time"]
    track_temp = config["track_temp"]
    total_laps = config["total_laps"]
    results = []
    o = {"SOFT": soft_b, "MEDIUM": 0.0, "HARD": hard_b}
    d = {"SOFT": deg_s, "MEDIUM": deg_m, "HARD": deg_h}
    for pos_key, strategy in race["strategies"].items():
        grid_pos = int(pos_key[3:])
        total_time = 0.0
        tire_age = 0
        current_tire = strategy["starting_tire"]
        pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}
        for lap in range(1, total_laps + 1):
            tire_age += 1 # age 1, 2, ...
            # Formula from discover_and_fix.py
            lap_time = base + o[current_tire] + d[current_tire] * (tire_age**p) + t_f * track_temp
            total_time += lap_time
            if lap in pit_stops:
                total_time += pit_time
                current_tire = pit_stops[lap]
                tire_age = 0
        results.append((strategy["driver_id"], total_time, grid_pos))
    return [x[0] for x in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def evaluate():
    path = Path("data/historical_races/races_00000-00999.json")
    r0 = json.load(open(path))[0]
    target = r0["finishing_positions"]
    
    params = (-4.0, 1.0, 0.02, 0.005, 0.001, 0.0, 1.5)
    pred = simulate(r0, *params)
    print(f"Match Race 0? {pred == target}")
    if not pred == target:
        for i in range(20):
            print(f"Rank {i+1}: Expected {target[i]}, Pred {pred[i]}")

if __name__ == "__main__":
    evaluate()
