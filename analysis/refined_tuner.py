import json
from pathlib import Path
import itertools
import time

def calculate_lap_time(base, tire, age, track_temp, compound_offset, degr_rate, temp_factor, power):
    # Based on regulations.md: first lap on fresh tires is age 1
    return base + compound_offset[tire] + degr_rate[tire] * (age ** power) + temp_factor * track_temp

def simulate_race(race_data, compound_offset, degr_rate, temp_factor, power):
    config = race_data["race_config"]
    base = config["base_lap_time"]
    pit_time = config["pit_lane_time"]
    track_temp = config["track_temp"]
    total_laps = config["total_laps"]

    results = []
    # strategy keys are "pos1", "pos2", ...
    for pos_key, strategy in race_data["strategies"].items():
        grid_pos = int(pos_key[3:])
        driver_id = strategy["driver_id"]
        current_tire = strategy["starting_tire"]
        total_time = 0.0
        age = 0
        pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}

        for lap in range(1, total_laps + 1):
            age += 1 # Age increments before calculating lap time
            lap_time = calculate_lap_time(base, current_tire, age, track_temp, compound_offset, degr_rate, temp_factor, power)
            total_time += lap_time

            if lap in pit_stops:
                total_time += pit_time
                current_tire = pit_stops[lap]
                age = 0 # Reset age for next lap

        results.append({"driver_id": driver_id, "total_time": total_time, "grid_pos": grid_pos})

    # Sort by total_time (rounded) and then grid_pos
    sorted_drivers = sorted(results, key=lambda x: (round(x["total_time"], 10), x["grid_pos"]))
    return [d["driver_id"] for d in sorted_drivers]

def run_tuner():
    path = Path("data/historical_races/races_00000-00999.json")
    if not path.exists():
        print("❌ Historical data not found.")
        return

    races = json.load(open(path))[:5] # Use 5 races for better accuracy

    print("🚀 Refining the F1 simulation model tuning...")

    # Search grid
    # Based on previous attempts, let's try around the current values
    soft_offsets = [-3.5, -3.2, -3.0, -2.8, -2.5, -2.0]
    hard_offsets = [2.0, 2.5, 2.8, 3.0, 3.2, 3.5]
    soft_rates   = [0.03, 0.035, 0.04]
    med_rates    = [0.015, 0.018, 0.02, 0.025]
    hard_rates   = [0.005, 0.008, 0.009, 0.01, 0.012]
    temp_factors = [0.01, 0.012, 0.015, 0.02]
    powers       = [2.0] # Keeping it at 2.0 for now

    total = len(soft_offsets) * len(hard_offsets) * len(soft_rates) * len(med_rates) * len(hard_rates) * len(temp_factors)
    print(f"Testing {total:,} combinations on 5 races...")

    start = time.time()
    for s_off, h_off, s_r, m_r, h_r, t_f in itertools.product(soft_offsets, hard_offsets, soft_rates, med_rates, hard_rates, temp_factors):
        compound_offset = {"SOFT": s_off, "MEDIUM": 0.0, "HARD": h_off}
        degr_rate = {"SOFT": s_r, "MEDIUM": m_r, "HARD": h_r}
        power = 2.0

        match = True
        for r in races:
            if simulate_race(r, compound_offset, degr_rate, t_f, power) != r["finishing_positions"]:
                match = False
                break
        
        if match:
            print("\n🎉 PERFECT MATCH FOUND!")
            print(f'COMPOUND_OFFSET = {compound_offset}')
            print(f'DEGRADATION = {degr_rate}')
            print(f'TEMP_FACTOR = {t_f}')
            print(f'DEGRADATION_POWER = {power}')
            print(f"\nTime taken: {time.time()-start:.1f} seconds")
            return

    print("\n❌ No match found in this refined grid.")

if __name__ == "__main__":
    run_tuner()
