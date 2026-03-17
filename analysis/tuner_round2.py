import json
from pathlib import Path
import itertools
import time

def calculate_lap_time(base, tire, stint_laps, track_temp, compound_base, degr_rate, temp_factor, power):
    return base + compound_base[tire] + degr_rate[tire] * (stint_laps ** power) + temp_factor * track_temp

def simulate_race(race_config, strategies, compound_base, degr_rate, temp_factor, power):
    base = race_config["base_lap_time"]
    pit_time = race_config["pit_lane_time"]
    track_temp = race_config["track_temp"]
    total_laps = race_config["total_laps"]
    results = []
    for pos_key, strat in strategies.items():
        driver_id = strat["driver_id"]
        current_tire = strat["starting_tire"]
        total_time = 0.0
        stint_laps = 0
        pit_idx = 0
        stops = strat.get("pit_stops", [])
        grid_pos = int(pos_key[3:])
        for lap in range(1, total_laps + 1):
            lap_time = calculate_lap_time(base, current_tire, stint_laps, track_temp, compound_base, degr_rate, temp_factor, power)
            total_time += lap_time
            stint_laps += 1
            if pit_idx < len(stops) and stops[pit_idx]["lap"] == lap:
                total_time += pit_time
                current_tire = stops[pit_idx]["to_tire"]
                stint_laps = 0
                pit_idx += 1
        results.append((driver_id, total_time, grid_pos))
    sorted_drivers = [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]
    return sorted_drivers

def run_tuner():
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))[:3]
    print("🚀 Tuner Round 2: Exploring wider ranges and different powers...")
    
    # Try Power 1.0, 2.0, 3.0
    for power in [1.0, 2.0, 3.0]:
        print(f"--- Power {power} ---")
        soft_offsets = [-5.0, -4.0, -3.0, -2.0, -1.0, 0.0]
        hard_offsets = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        # Rates depend on power!
        if power == 1.0:
            soft_rates = [0.1, 0.2, 0.3]
            med_rates = [0.05, 0.1]
            hard_rates = [0.02, 0.05]
        elif power == 2.0:
            soft_rates = [0.02, 0.04, 0.06, 0.08]
            med_rates = [0.01, 0.02, 0.03]
            hard_rates = [0.005, 0.01, 0.02]
        else: # 3.0
            soft_rates = [0.001, 0.005, 0.01]
            med_rates = [0.0005, 0.001]
            hard_rates = [0.0001, 0.0005]
        
        temp_factors = [0.0, 0.01, 0.02, 0.03]
        
        for s_off, h_off, s_r, m_r, h_r, t_f in itertools.product(soft_offsets, hard_offsets, soft_rates, med_rates, hard_rates, temp_factors):
            cb = {"SOFT": s_off, "MEDIUM": 0.0, "HARD": h_off}
            dr = {"SOFT": s_r, "MEDIUM": m_r, "HARD": h_r}
            if all(simulate_race(r["race_config"], r["strategies"], cb, dr, t_f, power) == r["finishing_positions"] for r in races):
                print("\n🎉 PERFECT MATCH FOUND!")
                print(f'COMPOUND_BASE = {cb}')
                print(f'DEGRADATION_RATE = {dr}')
                print(f'TEMP_FACTOR = {t_f}')
                print(f'DEGRADATION_POWER = {power}')
                return
    print("\n❌ No match in Round 2.")

if __name__ == "__main__":
    run_tuner()
