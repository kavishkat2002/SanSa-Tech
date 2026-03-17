import json
from pathlib import Path
from itertools import product
import time

def precalculate(races, p_list):
    all_data = []
    for r in races:
        cfg = r["race_config"]
        target = r["finishing_positions"]
        base = cfg["base_lap_time"]
        pit_time = cfg["pit_lane_time"]
        track_temp = cfg["track_temp"]
        total_laps = cfg["total_laps"]
        
        drivers = []
        for pos_key, strategy in r["strategies"].items():
            grid_pos = int(pos_key[3:])
            driver_id = strategy["driver_id"]
            current_tire = strategy["starting_tire"]
            stats = {
                "id": driver_id, "grid": grid_pos,
                "const": base * total_laps + len(strategy.get("pit_stops", [])) * pit_time,
                "n": {"SOFT": 0, "MEDIUM": 0, "HARD": 0},
                "age_pow": {p: {"SOFT": 0.0, "MEDIUM": 0.0, "HARD": 0.0} for p in p_list},
                "temp_part": float(track_temp * total_laps)
            }
            age = 0
            pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}
            for lap in range(1, total_laps + 1):
                age += 1
                stats["n"][current_tire] += 1
                for p in p_list: stats["age_pow"][p][current_tire] += (age ** p)
                if lap in pit_stops:
                    current_tire = pit_stops[lap]
                    age = 0
            drivers.append(stats)
        all_data.append({"drivers": drivers, "target": target})
    return all_data

def check(race_data, s_off, h_off, s_r, m_r, h_r, t_f, p):
    results = []
    for d in race_data["drivers"]:
        t = (d["const"] + 
             s_off * d["n"]["SOFT"] + 
             h_off * d["n"]["HARD"] + 
             s_r * d["age_pow"][p]["SOFT"] + 
             m_r * d["age_pow"][p]["MEDIUM"] + 
             h_r * d["age_pow"][p]["HARD"] + 
             t_f * d["temp_part"])
        results.append((d["id"], t, d["grid"]))
    # Order following discovery scripts
    pred = [x[0] for x in sorted(results, key=lambda x: x[1])]
    return pred == race_data["target"]

def run():
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))[:100]
    p_list = [1.0, 1.5, 2.0, 2.5, 3.0]
    print("Precalc...")
    all_data = precalculate(races, p_list)

    # Wide but reasonable grid
    S_B = [-3.5, -3.0, -2.8, -2.5, -2.2, -2.0, -1.8, -1.5]
    H_B = [1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2, 3.5]
    D_S = [0.03, 0.035, 0.04, 0.045, 0.05, 0.06]
    D_M = [0.015, 0.018, 0.02, 0.022, 0.025, 0.03]
    D_H = [0.005, 0.008, 0.009, 0.01, 0.012, 0.015]
    T_F = [0.0, 0.01, 0.012, 0.015, 0.018, 0.02]

    print("Search...")
    start = time.time()
    for p in p_list:
        print(f"P={p}")
        for s_off, h_off, s_r, m_r, h_r, t_f in product(S_B, H_B, D_S, D_M, D_H, T_F):
            if check(all_data[0], s_off, h_off, s_r, m_r, h_r, t_f, p):
                # Match on Race 0, verify on Race 1-2
                if check(all_data[1], s_off, h_off, s_r, m_r, h_r, t_f, p) and \
                   check(all_data[2], s_off, h_off, s_r, m_r, h_r, t_f, p):
                    print(f"Candidate: p={p}, s={s_off}, h={h_off}, s_r={s_r}, m_r={m_r}, h_r={h_r}, t={t_f}")
                    # Final check
                    score = 0
                    for i in range(100):
                        if check(all_data[i], s_off, h_off, s_r, m_r, h_r, t_f, p): score += 1
                    print(f"SCORE: {score}/100")
                    if score >= 90:
                        print("MATCH FOUND")
                        return

if __name__ == "__main__":
    run()
