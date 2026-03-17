import json
from pathlib import Path
from itertools import product
import time

def simulate(race, params):
    cfg = race["race_config"]
    # params: s_off, h_off, s_r, m_r, h_r, t_f, p, formula_type
    base = cfg["base_lap_time"]
    pit_time = cfg["pit_lane_time"]
    track_temp = cfg["track_temp"]
    total_laps = cfg["total_laps"]
    
    results = []
    for pos_key, strategy in race["strategies"].items():
        grid_pos = int(pos_key[3:])
        driver_id = strategy["driver_id"]
        current_tire = strategy["starting_tire"]
        total_time = 0.0
        tire_age = 0
        pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}
        
        o = {"SOFT": params[0], "MEDIUM": 0.0, "HARD": params[1]}
        d = {"SOFT": params[2], "MEDIUM": params[3], "HARD": params[4]}
        t_f = params[5]
        p = params[6]
        f_type = params[7]

        for lap in range(1, total_laps + 1):
            tire_age += 1
            if f_type == 0: # Additive
                dt = d[current_tire] * ((tire_age-1)**p) + t_f * track_temp
            elif f_type == 1: # Multiplicative Deg
                dt = d[current_tire] * (1 + t_f * track_temp) * ((tire_age-1)**p)
            elif f_type == 2: # Multiplicative Temp (direct)
                dt = d[current_tire] * ((tire_age-1)**p) * (t_f * track_temp)
            elif f_type == 3: # Age starts at 1
                dt = d[current_tire] * (tire_age**p) + t_f * track_temp
            
            total_time += base + o[current_tire] + dt
            
            if lap in pit_stops:
                total_time += pit_time
                current_tire = pit_stops[lap]
                tire_age = 0
        
        results.append((driver_id, total_time, grid_pos))
    
    return [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def run():
    path = Path("data/historical_races/races_00000-00999.json")
    r0 = json.load(open(path))[0]
    target = r0["finishing_positions"]

    # Try restricted grid but multiple formulas
    S_B = [-3.0, -2.5, -2.0]
    H_B = [2.0, 2.5, 3.0]
    D_S = [0.04, 0.05, 0.06]
    D_M = [0.02, 0.025, 0.03]
    D_H = [0.01, 0.015, 0.02]
    T_F = [0.0, 0.01, 0.02]
    P = [2.0]
    F = [0, 1, 2, 3]

    print("Checking multiple formulas on Race 0...")
    for f in F:
        print(f"Formula {f}...")
        for s_o, h_o, s_r, m_r, h_r, t_f, p in product(S_B, H_B, D_S, D_M, D_H, T_F, P):
            params = (s_o, h_o, s_r, m_r, h_r, t_f, p, f)
            if simulate(r0, params) == target:
                print(f"  ✓ FOUND MATCH with Formula {f}!")
                print(f"  Params: {params}")
                return

if __name__ == "__main__":
    run()
