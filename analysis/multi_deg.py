import json
from pathlib import Path
from itertools import product
import time

def get_order(race, s_off, h_off, s_r, m_r, h_r, t_f, p):
    cfg = race["race_config"]
    base = cfg["base_lap_time"]
    pit_time = cfg["pit_lane_time"]
    track_temp = cfg["track_temp"]
    total_laps = cfg["total_laps"]
    results = []
    o = {"SOFT": s_off, "MEDIUM": 0.0, "HARD": h_off}
    d = {"SOFT": s_r, "MEDIUM": m_r, "HARD": h_r}
    for pos_key, strategy in race["strategies"].items():
        grid_pos = int(pos_key[3:])
        total_time = 0.0
        tire_age = 0
        current_tire = strategy["starting_tire"]
        pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}
        for lap in range(1, total_laps + 1):
            tire_age += 1
            # NEW FORMULA: t_f scales BOTH offset and deg?
            # Or t_f scales just deg?
            lap_time = base + o[current_tire] + d[current_tire] * (tire_age**p) * (1 + t_f * track_temp)
            total_time += lap_time
            if lap in pit_stops:
                total_time += pit_time
                current_tire = pit_stops[lap]
                tire_age = 0
        results.append((strategy["driver_id"], total_time, grid_pos))
    return [x[0] for x in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def run():
    path = Path("data/historical_races/races_00000-00999.json")
    r0 = json.load(open(path))[0]
    target = r0["finishing_positions"]
    
    # Try wide grid on this new formula
    S_B = [-3.0, -2.0, -1.0]
    H_B = [1.0, 2.0, 3.0]
    D_S = [0.03, 0.05, 0.08]
    D_M = [0.015, 0.025, 0.035]
    D_H = [0.005, 0.01, 0.015]
    T_F = [0.0, 0.005, 0.01]
    
    print("Checking Multiplicative Deg Formula on Race 0...")
    for s_o, h_o, s_r, m_r, h_r, t_f in product(S_B, H_B, D_S, D_M, D_H, T_F):
        if get_order(r0, s_o, h_o, s_r, m_r, h_r, t_f, 2.0) == target:
            print(f"  ✓ MATCH! s={s_o}, h={h_o}, deg=({s_r},{m_r},{h_r}), t={t_f}")
            return

if __name__ == "__main__":
    run()
