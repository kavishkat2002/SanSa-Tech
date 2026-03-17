import json
from pathlib import Path
import itertools
import time

def calculate_lap_time(base, tire, age, track_temp, compound_offset, degr_rate, temp_factor, power):
    # Trying the formula from the tuner: stint_laps starts at 0, which is age 1
    stint_laps = age - 1
    return base + compound_offset[tire] + degr_rate[tire] * (stint_laps ** power) + temp_factor * track_temp

def simulate_race(race_data, compound_offset, degr_rate, temp_factor, power):
    config = race_data["race_config"]
    base = config["base_lap_time"]
    pit_time = config["pit_lane_time"]
    track_temp = config["track_temp"]
    total_laps = config["total_laps"]

    results = []
    for pos_key, strategy in race_data["strategies"].items():
        grid_pos = int(pos_key[3:])
        driver_id = strategy["driver_id"]
        current_tire = strategy["starting_tire"]
        total_time = 0.0
        age = 0
        pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}

        for lap in range(1, total_laps + 1):
            age += 1
            lap_time = calculate_lap_time(base, current_tire, age, track_temp, compound_offset, degr_rate, temp_factor, power)
            total_time += lap_time

            if lap in pit_stops:
                total_time += pit_time
                current_tire = pit_stops[lap]
                age = 0

        results.append({"driver_id": driver_id, "total_time": total_time, "grid_pos": grid_pos})

    # Sort by total_time and then grid_pos
    sorted_drivers = sorted(results, key=lambda x: (round(x["total_time"], 10), x["grid_pos"]))
    return [d["driver_id"] for d in sorted_drivers]

def run_tuner():
    path = Path("data/historical_races/races_00000-00999.json")
    if not path.exists(): return
    races = json.load(open(path))[:1] # ONE RACE ONLY for discovery

    print("🚀 Brute-force searching for parameters on ONE race...")

    # Expanded Grid
    soft_offsets = [-4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0]
    hard_offsets = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    soft_rates   = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    med_rates    = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035]
    hard_rates   = [0.001, 0.002, 0.005, 0.008, 0.01, 0.012, 0.015, 0.02]
    temp_factors = [0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]
    power = 2.0

    target = races[0]["finishing_positions"]

    start = time.time()
    count = 0
    for s_off, h_off, s_r, m_r, h_r, t_f in itertools.product(soft_offsets, hard_offsets, soft_rates, med_rates, hard_rates, temp_factors):
        compound_offset = {"SOFT": s_off, "MEDIUM": 0.0, "HARD": h_off}
        degr_rate = {"SOFT": s_r, "MEDIUM": m_r, "HARD": h_r}

        if simulate_race(races[0], compound_offset, degr_rate, t_f, power) == target:
            print(f"\n🎉 CANDIDATE FOUND on Race 0!")
            print(f'COMPOUND_OFFSET = {compound_offset}')
            print(f'DEGRADATION = {degr_rate}')
            print(f'TEMP_FACTOR = {t_f}')
            
            # Check on 2 more races
            races_3 = json.load(open(path))[:3]
            if all(simulate_race(r, compound_offset, degr_rate, t_f, power) == r["finishing_positions"] for r in races_3):
                print("✅ PASSED ON ALL 3 RACES!")
                return
            else:
                print("❌ FAILED on other races. Continuing...")
        
        count += 1
        if count % 100000 == 0:
            print(f"Tested {count} combos...")

    print("\n❌ No global match found.")

if __name__ == "__main__":
    run_tuner()
