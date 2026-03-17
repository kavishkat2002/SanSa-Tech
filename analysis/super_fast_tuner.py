import json
from pathlib import Path
import itertools
import time

def precalculate_race_stats(race, power_list):
    config = race["race_config"]
    base = config["base_lap_time"]
    pit_time = config["pit_lane_time"]
    track_temp = config["track_temp"]
    total_laps = config["total_laps"]

    drivers_stats = []
    # strategy keys are "pos1", "pos2", ...
    for pos_key, strategy in race["strategies"].items():
        grid_pos = int(pos_key[3:])
        driver_id = strategy["driver_id"]
        current_tire = strategy["starting_tire"]
        
        # Coefficients for the linear formula:
        # TotalTime = Const + s_off * nS + h_off * nH + s_r * S_age_pow + m_r * M_age_pow + h_r * H_age_pow + t_f * TempFactorPart
        stats = {
            "driver_id": driver_id,
            "grid_pos": grid_pos,
            "const": base * total_laps + len(strategy.get("pit_stops", [])) * pit_time,
            "nS": 0,
            "nH": 0,
            "nM": 0,
            "S_age_pow": {p: 0.0 for p in power_list},
            "M_age_pow": {p: 0.0 for p in power_list},
            "H_age_pow": {p: 0.0 for p in power_list},
            "TempFactorPart": float(track_temp * total_laps)
        }

        age = 0
        pit_stops = {p["lap"]: p["to_tire"] for p in strategy.get("pit_stops", [])}
        for lap in range(1, total_laps + 1):
            age += 1
            if current_tire == "SOFT":
                stats["nS"] += 1
                for p in power_list: stats["S_age_pow"][p] += (age ** p)
            elif current_tire == "MEDIUM":
                stats["nM"] += 1
                for p in power_list: stats["M_age_pow"][p] += (age ** p)
            elif current_tire == "HARD":
                stats["nH"] += 1
                for p in power_list: stats["H_age_pow"][p] += (age ** p)
            
            if lap in pit_stops:
                current_tire = pit_stops[lap]
                age = 0
        
        drivers_stats.append(stats)
    
    return drivers_stats

def get_predicted_order(drivers_stats, s_off, h_off, s_r, m_r, h_r, t_f, p):
    results = []
    for s in drivers_stats:
        total_time = (
            s["const"] +
            s_off * s["nS"] +
            h_off * s["nH"] +
            s_r * s["S_age_pow"][p] +
            m_r * s["M_age_pow"][p] +
            h_r * s["H_age_pow"][p] +
            t_f * s["TempFactorPart"]
        )
        results.append((s["driver_id"], total_time, s["grid_pos"]))
    
    return [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def run_tuner():
    path = Path("data/historical_races/races_00000-00999.json")
    if not path.exists(): return
    races_data = json.load(open(path))[:100] # Use more races for reliability

    powers = [1.0, 1.5, 2.0, 2.5, 3.0]
    print("Precalculating stats...")
    all_races_stats = [precalculate_race_stats(r, powers) for r in races_data]
    targets = [r["finishing_positions"] for r in races_data]

    print("🚀 Starting super-fast grid search...")

    soft_offsets = [-3.5, -3.2, -3.0, -2.8, -2.5, -2.0, -1.8, -1.5, -1.2, -1.0, -0.8, -0.5]
    hard_offsets = [0.5, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 2.8, 3.0, 3.2, 3.5]
    soft_rates   = [0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06]
    med_rates    = [0.015, 0.018, 0.02, 0.022, 0.025, 0.03]
    hard_rates   = [0.005, 0.008, 0.009, 0.01, 0.012, 0.015]
    temp_factors = [0.0, 0.005, 0.01, 0.012, 0.015, 0.018, 0.02, 0.025]

    total = len(soft_offsets) * len(hard_offsets) * len(soft_rates) * len(med_rates) * len(hard_rates) * len(temp_factors) * len(powers)
    print(f"Testing {total:,} combinations...")

    start = time.time()
    best_score = 0
    for p in powers:
        print(f"Testing Power {p}...")
        for s_off, h_off, s_r, m_r, h_r, t_f in itertools.product(soft_offsets, hard_offsets, soft_rates, med_rates, hard_rates, temp_factors):
            # Check on first 5 races first for speed
            match_5 = True
            for i in range(5):
                if get_predicted_order(all_races_stats[i], s_off, h_off, s_r, m_r, h_r, t_f, p) != targets[i]:
                    match_5 = False
                    break
            
            if match_5:
                # Validate on 20 races
                score = 5
                for i in range(5, 50):
                    if get_predicted_order(all_races_stats[i], s_off, h_off, s_r, m_r, h_r, t_f, p) == targets[i]:
                        score += 1
                    else:
                        break
                
                if score > best_score:
                    best_score = score
                    print(f"  ✓ Found candidate: Score {score}/100, Params: s_off={s_off}, h_off={h_off}, s_r={s_r}, m_r={m_r}, h_r={h_r}, t_f={t_f}, p={p}")
                
                    if score == 50:
                        print("\n🎉 PERFECT MATCH FOUND!")
                        print(f'COMPOUND_BASE = {{"SOFT": {s_off}, "MEDIUM": 0.0, "HARD": {h_off}}}')
                        print(f'DEGRADATION = {{"SOFT": {s_r}, "MEDIUM": {m_r}, "HARD": {h_r}}}')
                        print(f'TEMP_FACTOR = {t_f}')
                        print(f'DEG_POWER = {p}')
                        print(f"\nTime taken: {time.time()-start:.1f} seconds")
                        return

    print(f"\n❌ Finished. Best score: {best_score}")

if __name__ == "__main__":
    run_tuner()
