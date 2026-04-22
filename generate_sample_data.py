"""
generate_sample_data.py
-----------------------
Generates a realistic 90-day OPD dataset for testing.
Run: python generate_sample_data.py
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)

DEPARTMENTS = [
    "Emergency", "Cardiology", "Orthopedics",
    "Pediatrics", "Gynecology", "Neurology",
    "General OPD", "Dermatology"
]

OUTCOMES = ["admitted", "discharged", "referred", "left_ama"]
OUTCOME_WEIGHTS = [0.20, 0.55, 0.15, 0.10]

# Base wait times per department (in minutes)
BASE_WAIT = {
    "Emergency":   45,
    "Cardiology":  60,
    "Orthopedics": 50,
    "Pediatrics":  35,
    "Gynecology":  40,
    "Neurology":   70,
    "General OPD": 30,
    "Dermatology": 25,
}

# Multipliers by hour (busy morning + evening spike)
def hour_multiplier(h):
    if 8 <= h <= 11:
        return 1.8   # morning rush
    elif 12 <= h <= 13:
        return 0.7   # lunch dip
    elif 14 <= h <= 17:
        return 1.3   # afternoon
    elif 18 <= h <= 20:
        return 1.6   # evening rush
    else:
        return 0.5   # off hours

records = []
dates = pd.date_range("2024-01-01", periods=90)

for date in dates:
    is_weekend = date.dayofweek >= 5
    day_factor = 0.6 if is_weekend else 1.0

    # Number of patients per day
    n_patients = int(np.random.normal(120, 20) * day_factor)
    n_patients = max(40, n_patients)

    for _ in range(n_patients):
        dept  = np.random.choice(DEPARTMENTS)
        # Pick a realistic hour (mostly 8am–8pm)
        # 24 hours: weight morning/afternoon/evening more
        hour_probs = [0.005]*8 + [0.08, 0.09, 0.09, 0.08, 0.04, 0.07, 0.08, 0.08, 0.07, 0.07, 0.06, 0.06, 0.04] + [0.005, 0.005, 0.005]
        # normalise
        hour_probs = np.array(hour_probs) / sum(hour_probs)
        hour  = int(np.random.choice(range(24), p=hour_probs))
        minute = np.random.randint(0, 60)

        base   = BASE_WAIT[dept]
        h_mult = hour_multiplier(hour)
        noise  = np.random.normal(0, 10)

        # Occasional doctor-absence spike (5% chance)
        spike  = np.random.normal(40, 10) if np.random.random() < 0.05 else 0

        wait   = max(5, base * h_mult + noise + spike)
        wait   = round(wait, 1)

        outcome = np.random.choice(OUTCOMES, p=OUTCOME_WEIGHTS)

        records.append({
            "date":       date.strftime("%Y-%m-%d"),
            "time":       f"{hour:02d}:{minute:02d}",
            "department": dept,
            "wait_time":  wait,
            "outcome":    outcome,
        })

df = pd.DataFrame(records)
path = os.path.join(os.path.dirname(__file__), "static", "sample_data.csv")
df.to_csv(path, index=False)
print(f"✅ Generated {len(df)} records → {path}")
