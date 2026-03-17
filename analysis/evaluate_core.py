import json
from pathlib import Path

def get_order(race, s_off, h_off, s_r, m_r, h_r, t_f, p):
    config = race["race_config"]
    base = config["base_lap_time"]
    pit_time = config["pit_lane_time"]
    track_temp = config["track_temp"]
    total_laps = config["total_laps"]

    results = []
    # strategy keys are "pos1", "pos2", ...
    for pos_key, strategy in race["strategies"].items():
        grid_pos = int(pos_key[3:])
        driver_id = strategy["driver_id"]
        current_tire = strategy["starting_tire"]
        total_time = 0.0
        age = 0
        pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}
        
        comp_off = {"SOFT": s_off, "MEDIUM": 0.0, "HARD": h_off}
        comp_deg = {"SOFT": s_r, "MEDIUM": m_r, "HARD": h_r}

        for lap in range(1, total_laps + 1):
            age += 1
            # Current race_simulator logic (additive)
            lap_time = base + comp_off[current_tire] + comp_deg[current_tire] * (age ** p) + t_f * track_temp
            total_time += lap_time

            if lap in pit_stops:
                total_time += pit_time
                current_tire = pit_stops[lap]
                age = 0
        
        results.append((driver_id, total_time, grid_pos))
    
    return [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def evaluate():
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))[:100]
    
    # Values from core/tire_model.py
    s_off, h_off = -2.8, 3.2
    s_r, m_r, h_r = 0.035, 0.018, 0.009
    t_f = 0.012
    p = 2.0
    
    score = 0
    for r in races:
        if get_order(r, s_off, h_off, s_r, m_r, h_r, t_f, p) == r["finishing_positions"]:
            score += 1
    
    print(f"Current core values score: {score}/100")

    # Try shifting age by -1 (age starts at 0 for first lap)
    score_0 = 0
    for r in races:
        total_laps = r["race_config"]["total_laps"]
        base = r["race_config"]["base_lap_time"]
        pit_time = r["race_config"]["pit_lane_time"]
        track_temp = r["race_config"]["track_temp"]
        results = []
        for pos_key, strategy in r["strategies"].items():
            grid_pos = int(pos_key[3:])
            total_time = 0.0
            age = 0
            current_tire = strategy["starting_tire"]
            pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}
            comp_off = {"SOFT": s_off, "MEDIUM": 0.0, "HARD": h_off}
            comp_deg = {"SOFT": s_r, "MEDIUM": m_r, "HARD": h_r}
            for lap in range(1, total_laps + 1):
                # Using (age) where age starts at 0 for first lap
                lap_time = base + comp_off[current_tire] + comp_deg[current_tire] * (age ** p) + t_f * track_temp
                total_time += lap_time
                age += 1
                if lap in pit_stops:
                    total_time += pit_time
                    current_tire = pit_stops[lap]
                    age = 0
            results.append((strategy["driver_id"], total_time, grid_pos))
        pred = [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]
        if pred == r["finishing_positions"]:
            score_0 += 1
    print(f"Shifted age (0, 1, 2...) core values score: {score_0}/100")

if __name__ == "__main__":
    evaluate()
