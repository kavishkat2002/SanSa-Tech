import json
from pathlib import Path
import random

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
    path = Path("data/historical_races/races_00000-00999.json")
    r0 = json.load(open(path))[0]
    target = r0["finishing_positions"]

    best_p = None
    best_m = -1

    print("🚀 Hill climbing to find a match for Race 0...")
    
    # Start with core values
    p = [-2.8, 3.2, 0.035, 0.018, 0.009, 0.012, 2.0]
    
    for _ in range(100000):
        # Tweak one param
        p_new = list(p)
        idx = random.randint(0, 6)
        if idx < 2: p_new[idx] += random.uniform(-0.1, 0.1) # offsets
        elif idx < 5: p_new[idx] *= random.uniform(0.9, 1.1) # rates
        elif idx == 5: p_new[idx] += random.uniform(-0.001, 0.001) # temp
        else: p_new[idx] = random.choice([1.0, 1.5, 2.0, 2.2, 2.5]) # power
        
        pred = get_order(r0, *p_new)
        # count matching positions from front
        match_count = 0
        for i in range(20):
            if pred[i] == target[i]: match_count += 1
            else: break
        
        if match_count > best_m:
            best_m = match_count
            p = p_new
            print(f"  ✓ New best match: {best_m}/20. Params: {p}")
            if best_m == 20:
                print("🎉 PERFECT MATCH FOR RACE 0!")
                return

if __name__ == "__main__":
    run()
