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

    # Sort consistent with engine: (total_time, grid_pos)
    sorted_drivers = [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]
    return sorted_drivers

def run_tuner():
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))[:3]

    soft_offsets = [-4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0]
    hard_offsets = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    soft_rates   = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    med_rates    = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035]
    hard_rates   = [0.002, 0.005, 0.008, 0.01, 0.012, 0.015, 0.02]
    temp_factors = [0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]
    power = 2.0

    print("🚀 Auto-tuning with EXACT Grok instructions...")

    for s_off, h_off, s_r, m_r, h_r, t_f in itertools.product(soft_offsets, hard_offsets, soft_rates, med_rates, hard_rates, temp_factors):
        compound_base = {"SOFT": s_off, "MEDIUM": 0.0, "HARD": h_off}
        degr_rate = {"SOFT": s_r, "MEDIUM": m_r, "HARD": h_r}

        if simulate_race(races[0]["race_config"], races[0]["strategies"], compound_base, degr_rate, t_f, power) == races[0]["finishing_positions"]:
            print(f"Candidate on Race 0: s_off={s_off}, h_off={h_off}, s_r={s_r}, m_r={m_r}, h_r={h_r}, t_f={t_f}")
            if all(simulate_race(r["race_config"], r["strategies"], compound_base, degr_rate, t_f, power) == r["finishing_positions"] for r in races):
                print("\n🎉 PERFECT MATCH FOUND!")
                print(f'COMPOUND_BASE = {compound_base}')
                print(f'DEGRADATION_RATE = {degr_rate}')
                print(f'TEMP_FACTOR = {t_f}')
                print(f'DEGRADATION_POWER = {power}')
                return

if __name__ == "__main__":
    run_tuner()
