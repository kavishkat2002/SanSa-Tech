import json
import sys

# ── Tire model parameters ─────────────────────────────────────────────────────
# SOFT is fastest (negative offset = faster) but degrades quickly
# HARD is slowest but most durable
# MEDIUM is the baseline (0.0 offset)
#
# ⚠️  THESE VALUES ARE TUNED ESTIMATES — run analysis/discover_and_fix.py
#    to auto-discover exact values from historical data.
# ─────────────────────────────────────────────────────────────────────────────
COMPOUND_BASE = {"SOFT": -2.8, "MEDIUM": 0.0, "HARD": 3.2}
DEGRADATION   = {"SOFT": 0.035, "MEDIUM": 0.018, "HARD": 0.009}
TEMP_FACTOR   = 0.012
DEG_POWER     = 2.0


def simulate_race(race_config, strategies):
    """
    Lap-by-lap F1 race simulation.

    Key rule from docs/regulations.md §Tire Age Tracking:
      'At the start of each lap, tire age increments by 1 BEFORE calculating
       lap time — the first lap on fresh tyres is driven at age 1.'

    This means:
      - tire_age starts at 0 when tyres are fitted
      - tire_age += 1 BEFORE computing the lap time each lap
      - After a pit stop tire_age resets to 0 → next lap = age 1 again
    """
    base       = race_config["base_lap_time"]
    pit_time   = race_config["pit_lane_time"]
    track_temp = race_config["track_temp"]
    total_laps = race_config["total_laps"]

    results = []
    for pos_key, strat in strategies.items():
        grid_pos     = int(pos_key[3:]) # "pos1" -> 1
        driver_id    = strat["driver_id"]
        current_tire = strat["starting_tire"]
        total_time   = 0.0
        tire_age     = 0        # resets to 0 on fresh tyres; first lap → +1 = 1
        pit_idx      = 0
        stops        = strat.get("pit_stops", [])

        for lap in range(1, total_laps + 1):
            # ── PRE-INCREMENT before calculation (spec requirement) ──
            tire_age += 1

            lap_time = (
                base
                + COMPOUND_BASE[current_tire]
                + DEGRADATION[current_tire] * (tire_age ** DEG_POWER)
                + TEMP_FACTOR * track_temp
            )
            total_time += lap_time

            # Pit stop occurs at the END of this lap
            if pit_idx < len(stops) and stops[pit_idx]["lap"] == lap:
                total_time  += pit_time
                current_tire = stops[pit_idx]["to_tire"]
                tire_age     = 0    # fresh set → next lap = age 1
                pit_idx     += 1

        results.append((driver_id, total_time, grid_pos))

    # Sort ascending by total time, then by grid position (standard tie-breaker)
    return [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        sys.stderr.write(f"Error reading input: {e}\n")
        sys.exit(1)

    finishing = simulate_race(data["race_config"], data["strategies"])
    print(json.dumps({"race_id": data["race_id"], "finishing_positions": finishing}))


if __name__ == "__main__":
    main()
