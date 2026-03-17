# core/tire_model.py

# These constants were reverse-engineered from historical race data
COMPOUND_OFFSET = {
    "SOFT": -2.8,
    "MEDIUM": 0.0,
    "HARD": 3.2
}

DEGRADATION = {
    "SOFT": 0.035,
    "MEDIUM": 0.018,
    "HARD": 0.009
}

TEMP_FACTOR = 0.012
