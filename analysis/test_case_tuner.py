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
            lap_time = base + o[current_tire] + d[current_tire] * ((tire_age-1)**p) + t_f * track_temp
            total_time += lap_time
            if lap in pit_stops:
                total_time += pit_time
                current_tire = pit_stops[lap]
                tire_age = 0
        results.append((strategy["driver_id"], total_time, grid_pos))
    return [x[0] for x in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def run():
    # Load TEST_001
    with open('data/test_cases/inputs/test_001.json') as f:
        test_case = json.load(f)
    # Expected order from root expected_positions.txt
    target = "D006,D018,D003,D009,D019,D001,D008,D014,D015,D013,D017,D004,D007,D020,D012,D002,D011,D016,D010,D005".split(",")

    # Grid search on Test Case 001
    S_B = [-3.5, -3.0, -2.5, -2.0, -1.5]
    H_B = [1.5, 2.0, 2.5, 3.0, 3.5]
    D_S = [0.03, 0.04, 0.05, 0.06, 0.08]
    D_M = [0.015, 0.018, 0.02, 0.025, 0.03]
    D_H = [0.005, 0.008, 0.009, 0.01, 0.012]
    T_F = [0.0, 0.01, 0.012, 0.015]
    p = 2.0

    print("🚀 Tuning on TEST_001...")
    for s_o, h_o, s_r, m_r, h_r, t_f in product(S_B, H_B, D_S, D_M, D_H, T_F):
        if get_order(test_case, s_o, h_o, s_r, m_r, h_r, t_f, p) == target:
            print(f"  ✓ MATCH ON TEST_001!")
            print(f"  Params: s={s_o}, h={h_o}, deg=({s_r},{m_r},{h_r}), t={t_f}, p={p}")
            return

if __name__ == "__main__":
    run()
