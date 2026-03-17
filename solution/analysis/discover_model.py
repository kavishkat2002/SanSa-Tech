import json
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution

def simulate(race, params):
    off_S, off_H, deg_S, deg_M, deg_H, ts = params
    base = race["race_config"]["base_lap_time"]
    pit_time = race["race_config"]["pit_lane_time"]
    temp = race["race_config"]["track_temp"]
    total_laps = race["race_config"]["total_laps"]
    
    offsets = {"SOFT": off_S, "MEDIUM": 0.0, "HARD": off_H}
    degs = {"SOFT": deg_S, "MEDIUM": deg_M, "HARD": deg_H}
    
    results = []
    for pos_key, strat in race["strategies"].items():
        grid_pos = int(pos_key[3:])
        current_tire, stint_laps, total_time = strat["starting_tire"], 0, 0.0
        stops = {s["lap"]: s["to_tire"] for s in strat.get("pit_stops", [])}
        for lap in range(1, total_laps + 1):
            deg = degs[current_tire] * (1 + (temp - BT) * ts)
            total_time += base + offsets[current_tire] + deg * stint_laps
            stint_laps += 1
            if lap in stops:
                total_time += pit_time
                current_tire = stops[lap]; stint_laps = 0
        results.append((strat["driver_id"], total_time, grid_pos))
    return [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

# GLOBAL CONSTANTS
BT = 25

def main():
    path = Path("data/historical_races/races_00000-00999.json")
    with open(path) as f:
        races = json.load(f)[:20]

    def objective(params):
        score = 0
        for race in races:
            if simulate(race, params) == race["finishing_positions"]:
                score += 1
        return -score

    print("Searching for linear model...")
    res = differential_evolution(objective, [(-3,0), (0,3), (0,0.5), (0,0.5), (0,0.5), (-0.1, 0.1)], popsize=20, maxiter=100)
    print(f"Linear Best: {res.x}, Score: {-res.fun}/20")

if __name__ == "__main__":
    main()
