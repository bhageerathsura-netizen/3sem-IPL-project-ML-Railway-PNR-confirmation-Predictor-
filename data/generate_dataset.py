"""
Data generation script for Indian Railways PNR Berth Confirmation Prediction
Creates realistic historical booking trajectory datasets adhering to authentic IRCTC
patterns, quota dynamics, and cancellation velocity across major rail corridors.
"""

import os
import random
import numpy as np
import pandas as pd

np.random.seed(42)
random.seed(42)

TOTAL_SAMPLES = 18000

CORRIDORS = {
    "Delhi-Mumbai": {"trains": ["12951/12952 Mumbai Rajdhani", "12953/12954 August Kranti", "12925/12926 Paschim SF"], "base_cancellation_rate": 0.22, "demand_factor": 1.25},
    "Delhi-Kolkata": {"trains": ["12301/12302 Howrah Rajdhani", "12313/12314 Sealdah Rajdhani", "12381/12382 Poorva SF"], "base_cancellation_rate": 0.20, "demand_factor": 1.30},
    "Bangalore-Chennai": {"trains": ["20607/20608 Vande Bharat", "12607/12608 Lalbagh SF", "12027/12028 Shatabdi"], "base_cancellation_rate": 0.26, "demand_factor": 1.10},
    "Delhi-Chennai": {"trains": ["12615/12616 Grand Trunk SF", "12621/12622 Tamil Nadu Express", "12433/12434 Chennai Rajdhani"], "base_cancellation_rate": 0.18, "demand_factor": 1.20},
    "Mumbai-Goa": {"trains": ["22229/22230 Vande Bharat", "10103/10104 Mandovi Express", "12051/12052 Jan Shatabdi"], "base_cancellation_rate": 0.24, "demand_factor": 1.15},
    "Delhi-Bangalore": {"trains": ["22691/22692 KSR Bengaluru Rajdhani", "12627/12628 Karnataka SF Express"], "base_cancellation_rate": 0.19, "demand_factor": 1.28},
    "Bangalore-Hyderabad": {"trains": ["12785/12786 Kacheguda SF", "20703/20704 Vande Bharat"], "base_cancellation_rate": 0.25, "demand_factor": 1.12},
    "Kolkata-Chennai": {"trains": ["12841/12842 Coromandel SF", "12839/12840 Howrah Chennai Mail"], "base_cancellation_rate": 0.21, "demand_factor": 1.18}
}

TRAIN_CATEGORIES = {
    "Rajdhani/VB": {"capacity_weight": 0.75, "premium": True},
    "Superfast": {"capacity_weight": 1.0, "premium": False},
    "Express": {"capacity_weight": 1.1, "premium": False},
    "Duronto": {"capacity_weight": 0.85, "premium": True}
}

CLASSES = {
    "1A": {"seats_per_coach": 22, "cancellation_propensity": 0.14, "wl_capacity": 15},
    "2A": {"seats_per_coach": 48, "cancellation_propensity": 0.21, "wl_capacity": 40},
    "3A": {"seats_per_coach": 72, "cancellation_propensity": 0.25, "wl_capacity": 85},
    "3E": {"seats_per_coach": 83, "cancellation_propensity": 0.22, "wl_capacity": 70},
    "SL": {"seats_per_coach": 80, "cancellation_propensity": 0.28, "wl_capacity": 150},
    "CC": {"seats_per_coach": 78, "cancellation_propensity": 0.24, "wl_capacity": 60}
}

# Quotas and clearing efficiency factors
QUOTAS = {
    "GNWL": {"efficiency": 1.00, "weight": 0.65},  # General Waitlist clears the fastest
    "RLWL": {"efficiency": 0.38, "weight": 0.22},  # Remote Location has strict quota limits
    "PQWL": {"efficiency": 0.28, "weight": 0.13}   # Pooled Quota clears slowest
}

def generate_records():
    records = []
    
    corridor_names = list(CORRIDORS.keys())
    quota_names = list(QUOTAS.keys())
    quota_weights = [QUOTAS[q]["weight"] for q in quota_names]
    class_names = list(CLASSES.keys())
    
    for i in range(TOTAL_SAMPLES):
        corridor = random.choice(corridor_names)
        corridor_info = CORRIDORS[corridor]
        train = random.choice(corridor_info["trains"])
        
        # Determine train category
        if "Rajdhani" in train or "Vande Bharat" in train or "Shatabdi" in train:
            category = "Rajdhani/VB"
        elif "Duronto" in train:
            category = "Duronto"
        elif "SF" in train or "Superfast" in train:
            category = "Superfast"
        else:
            category = "Express"
            
        coach_class = random.choices(
            class_names, 
            weights=[0.05, 0.15, 0.35, 0.10, 0.30, 0.05]
        )[0]
        
        # CC is only on Shatabdi/VB/Jan Shatabdi; SL is not on pure Rajdhani/VB
        if category == "Rajdhani/VB" and coach_class == "SL":
            coach_class = random.choice(["2A", "3A", "3E", "1A"])
        if category != "Rajdhani/VB" and coach_class == "CC" and "Jan Shatabdi" not in train:
            coach_class = "3A"
            
        quota = random.choices(quota_names, weights=quota_weights)[0]
        
        # Lead time: days left until chart preparation (0 to 120 days)
        # Bimodal distribution: many book within 1-15 days, many book 30-60 days out
        if random.random() < 0.45:
            lead_time_days = int(np.random.exponential(scale=7)) + 1
        else:
            lead_time_days = int(np.random.uniform(10, 90))
        lead_time_days = min(max(lead_time_days, 1), 120)
        
        # Current waitlist number at time of query
        max_wl_for_class = CLASSES[coach_class]["wl_capacity"]
        current_wl = int(np.random.triangular(1, max_wl_for_class * 0.35, max_wl_for_class))
        current_wl = max(1, current_wl)
        
        # Seasonality flags
        is_festive_season = 1 if random.random() < 0.22 else 0
        is_weekend = 1 if random.random() < 0.28 else 0
        
        # Real-world physics of IRCTC confirmation:
        # 1. Higher lead time = more opportunities for cancellations
        # 2. GNWL clears vastly better than RLWL/PQWL
        # 3. High festive demand = far lower cancellation rate
        # 4. Classes with more coaches (SL, 3A) have more raw turnover, but higher waitlists
        # 5. VIP / Emergency Quota (HO) releases at 4 hrs to chart preparation (usually 5-15 berths)
        
        base_clearing_rate = corridor_info["base_cancellation_rate"]
        quota_eff = QUOTAS[quota]["efficiency"]
        class_info = CLASSES[coach_class]
        
        # Expected cancellations per day for this train/class
        daily_cancellations = (class_info["seats_per_coach"] * 3.5) * (base_clearing_rate / 30.0)
        
        if is_festive_season:
            daily_cancellations *= 0.55  # People don't cancel festive tickets
        if is_weekend:
            daily_cancellations *= 0.85
            
        # Cumulative expected cleared seats over the remaining lead time
        expected_cleared = (daily_cancellations * (lead_time_days ** 0.85) * quota_eff)
        
        # Add chart-prep emergency quota release (usually 2-8 seats allocated to GNWL)
        chart_prep_release = random.uniform(2, 8) if quota == "GNWL" else random.uniform(0, 2)
        total_clearing_potential = expected_cleared + chart_prep_release
        
        # Probability calculation with sigmoid transition
        margin = total_clearing_potential - current_wl
        # Scale margin relative to current waitlist size
        logit = margin / (current_wl ** 0.5 + 4.0)
        # Apply slight random noise for real-world unpredictability (extra coach addition, VIP quota shifts)
        logit += np.random.normal(0, 0.45)
        
        true_prob = 1.0 / (1.0 + np.exp(-logit))
        
        # Final label: 1 if confirmed/RAC berth allotted, 0 if dropped/remained waitlisted
        confirmed = 1 if random.random() < true_prob else 0
        
        records.append({
            "pnr_id": f"PNR{4000000000 + i}",
            "train_number": train.split(" ")[0],
            "train_name": train,
            "corridor": corridor,
            "train_category": category,
            "coach_class": coach_class,
            "quota": quota,
            "current_wl": current_wl,
            "lead_time_days": lead_time_days,
            "is_festive_season": is_festive_season,
            "is_weekend": is_weekend,
            "base_cancellation_rate": round(base_clearing_rate, 3),
            "calculated_logit_prob": round(float(true_prob), 4),
            "status": "CONFIRMED" if confirmed == 1 else "DROPPED",
            "is_confirmed": confirmed
        })
        
    df = pd.DataFrame(records)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(out_dir, "pnr_clearing_dataset.csv")
    df.to_csv(csv_path, index=False)
    print(f"Dataset generated successfully at: {csv_path}")
    print(f"Total Records: {len(df)}")
    print(f"Confirmation Distribution: \n{df['is_confirmed'].value_counts(normalize=True)}")
    return csv_path

if __name__ == "__main__":
    generate_records()
