"""
Flask Backend Application for Indian Railways PNR Berth Confirmation Forecasting
and Intelligent Trip Planner & Booking Simulator.
Provides REST API endpoints for model inference, train searching with predictive availability,
one-click digital ticket booking (IRCTC ERS), and alternative split-route optimization.
"""

import os
import json
import random
import time
import datetime
import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "irctc_pnr_model.joblib")
METRICS_PATH = os.path.join(BASE_DIR, "models", "model_metrics.json")

# Load model pipeline
print(f"Loading ML model from {MODEL_PATH}...")
model = joblib.load(MODEL_PATH)

# Load metrics
with open(METRICS_PATH, "r") as f:
    model_metrics = json.load(f)

# In-memory booking store for simulated tickets during user session
BOOKED_TICKETS = []

CORRIDOR_METADATA = {
    "Delhi-Mumbai": {
        "origin_code": "NDLS",
        "origin_name": "New Delhi",
        "dest_code": "MMCT",
        "dest_name": "Mumbai Central",
        "distance_km": 1386,
        "base_cancellation_rate": 0.22,
        "popular_trains": [
            {
                "number": "12952",
                "name": "Mumbai Tejas Rajdhani",
                "category": "Rajdhani/VB",
                "dep_time": "16:55",
                "arr_time": "08:35",
                "duration": "15h 40m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A"],
                "fares": {"1A": 4850, "2A": 2890, "3A": 2040},
                "availability": {"1A": "AVL 8", "2A": "RAC 6", "3A": "WL 14"}
            },
            {
                "number": "12954",
                "name": "August Kranti Rajdhani",
                "category": "Rajdhani/VB",
                "dep_time": "17:15",
                "arr_time": "10:05",
                "duration": "16h 50m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "3E"],
                "fares": {"1A": 4720, "2A": 2790, "3A": 1980, "3E": 1780},
                "availability": {"1A": "AVL 4", "2A": "WL 8", "3A": "WL 32", "3E": "WL 18"}
            },
            {
                "number": "12926",
                "name": "Paschim Superfast Express",
                "category": "Superfast",
                "dep_time": "16:35",
                "arr_time": "14:45",
                "duration": "22h 10m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "3E", "SL"],
                "fares": {"1A": 4120, "2A": 2420, "3A": 1690, "3E": 1540, "SL": 635},
                "availability": {"1A": "AVL 12", "2A": "AVL 24", "3A": "RAC 18", "3E": "AVL 40", "SL": "WL 58"}
            },
            {
                "number": "19020",
                "name": "Dehradun Express",
                "category": "Express",
                "dep_time": "21:50",
                "arr_time": "04:20",
                "duration": "30h 30m",
                "runs_on": "Daily",
                "classes": ["2A", "3A", "SL"],
                "fares": {"2A": 2180, "3A": 1510, "SL": 560},
                "availability": {"2A": "AVL 16", "3A": "AVL 38", "SL": "RAC 24"}
            }
        ],
        "split_journey": {
            "title": "Smart Break-Journey via Kota Junction",
            "hub": "Kota Jn (KOTA)",
            "leg1": {"train": "12060 Jan Shatabdi", "route": "New Delhi → Kota Jn", "dep": "12:45", "arr": "17:40", "status": "AVAILABLE 84"},
            "leg2": {"train": "12952 Tejas Rajdhani", "route": "Kota Jn → Mumbai Central", "dep": "21:05", "arr": "08:35", "status": "AVAILABLE 42"},
            "layover": "3h 25m layover at Kota (Executive Lounge available)",
            "total_duration": "19h 50m",
            "advantage": "100% Confirmed Berths on both trains vs. Waiting in long WL queue"
        }
    },
    "Delhi-Kolkata": {
        "origin_code": "NDLS",
        "origin_name": "New Delhi",
        "dest_code": "HWH",
        "dest_name": "Howrah Junction",
        "distance_km": 1447,
        "base_cancellation_rate": 0.20,
        "popular_trains": [
            {
                "number": "12302",
                "name": "Howrah Rajdhani Express",
                "category": "Rajdhani/VB",
                "dep_time": "16:50",
                "arr_time": "09:55",
                "duration": "17h 05m",
                "runs_on": "Daily except Fri",
                "classes": ["1A", "2A", "3A"],
                "fares": {"1A": 4910, "2A": 2940, "3A": 2080},
                "availability": {"1A": "AVL 6", "2A": "RAC 4", "3A": "WL 22"}
            },
            {
                "number": "12314",
                "name": "Sealdah Rajdhani Express",
                "category": "Rajdhani/VB",
                "dep_time": "16:30",
                "arr_time": "10:10",
                "duration": "17h 40m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A"],
                "fares": {"1A": 4870, "2A": 2910, "3A": 2060},
                "availability": {"1A": "AVL 2", "2A": "WL 12", "3A": "WL 38"}
            },
            {
                "number": "12382",
                "name": "Poorva Superfast Express",
                "category": "Superfast",
                "dep_time": "17:40",
                "arr_time": "17:00",
                "duration": "23h 20m",
                "runs_on": "Mon, Tue, Fri",
                "classes": ["1A", "2A", "3A", "3E", "SL"],
                "fares": {"1A": 4210, "2A": 2480, "3A": 1730, "3E": 1580, "SL": 655},
                "availability": {"1A": "AVL 14", "2A": "AVL 32", "3A": "RAC 12", "3E": "AVL 48", "SL": "WL 74"}
            },
            {
                "number": "12260",
                "name": "Sealdah AC Duronto",
                "category": "Duronto",
                "dep_time": "19:45",
                "arr_time": "12:25",
                "duration": "16h 40m",
                "runs_on": "Mon, Wed, Thu",
                "classes": ["1A", "2A", "3A", "3E"],
                "fares": {"1A": 4790, "2A": 2860, "3A": 2010, "3E": 1820},
                "availability": {"1A": "AVL 8", "2A": "AVL 18", "3A": "WL 16", "3E": "AVL 28"}
            }
        ],
        "split_journey": {
            "title": "Smart Break-Journey via Pt. Deen Dayal Upadhyaya (Mughalsarai)",
            "hub": "DDU Jn (Mughalsarai)",
            "leg1": {"train": "12424 Dibrugarh Rajdhani", "route": "New Delhi → DDU Jn", "dep": "16:20", "arr": "23:45", "status": "AVAILABLE 38"},
            "leg2": {"train": "12314 Sealdah Rajdhani", "route": "DDU Jn → Howrah/Sealdah", "dep": "01:25", "arr": "10:10", "status": "AVAILABLE 54"},
            "layover": "1h 40m seamless connection at DDU Jn",
            "total_duration": "17h 50m",
            "advantage": "Guaranteed confirmed berths on both legs at normal dynamic fare"
        }
    },
    "Bangalore-Chennai": {
        "origin_code": "SBC",
        "origin_name": "KSR Bengaluru",
        "dest_code": "MAS",
        "dest_name": "MGR Chennai Central",
        "distance_km": 360,
        "base_cancellation_rate": 0.26,
        "popular_trains": [
            {
                "number": "20608",
                "name": "Mysuru-Chennai Vande Bharat",
                "category": "Rajdhani/VB",
                "dep_time": "14:50",
                "arr_time": "19:20",
                "duration": "4h 30m",
                "runs_on": "Daily except Wed",
                "classes": ["CC", "1A"],
                "fares": {"CC": 995, "1A": 1885},
                "availability": {"CC": "AVL 112", "1A": "AVL 24"}
            },
            {
                "number": "12028",
                "name": "KSR Bengaluru Shatabdi",
                "category": "Rajdhani/VB",
                "dep_time": "06:00",
                "arr_time": "11:00",
                "duration": "5h 00m",
                "runs_on": "Daily except Tue",
                "classes": ["CC", "1A"],
                "fares": {"CC": 910, "1A": 1720},
                "availability": {"CC": "AVL 48", "1A": "RAC 4"}
            },
            {
                "number": "12608",
                "name": "Lalbagh Superfast Express",
                "category": "Superfast",
                "dep_time": "06:20",
                "arr_time": "12:15",
                "duration": "5h 55m",
                "runs_on": "Daily",
                "classes": ["CC", "2A", "3A", "SL"],
                "fares": {"CC": 560, "2A": 890, "3A": 630, "SL": 235},
                "availability": {"CC": "AVL 86", "2A": "AVL 28", "3A": "AVL 64", "SL": "RAC 16"}
            },
            {
                "number": "12658",
                "name": "Chennai Mail Express",
                "category": "Superfast",
                "dep_time": "22:40",
                "arr_time": "04:15",
                "duration": "5h 35m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "SL"],
                "fares": {"1A": 1680, "2A": 910, "3A": 650, "SL": 245},
                "availability": {"1A": "AVL 8", "2A": "WL 6", "3A": "WL 18", "SL": "WL 42"}
            }
        ],
        "split_journey": {
            "title": "Alternate Express Option via Katpadi Jn",
            "hub": "Katpadi Jn (KPD)",
            "leg1": {"train": "12610 Intercity SF", "route": "Bengaluru → Katpadi", "dep": "08:00", "arr": "11:45", "status": "AVAILABLE 140"},
            "leg2": {"train": "12676 Kovai Express", "route": "Katpadi → Chennai Central", "dep": "12:30", "arr": "14:05", "status": "AVAILABLE 82"},
            "layover": "45m cross-platform connection",
            "total_duration": "6h 05m",
            "advantage": "Instant confirmation when direct evening trains are full"
        }
    },
    "Delhi-Chennai": {
        "origin_code": "NDLS",
        "origin_name": "New Delhi",
        "dest_code": "MAS",
        "dest_name": "MGR Chennai Central",
        "distance_km": 2180,
        "base_cancellation_rate": 0.18,
        "popular_trains": [
            {
                "number": "12434",
                "name": "Chennai Central Rajdhani",
                "category": "Rajdhani/VB",
                "dep_time": "15:35",
                "arr_time": "20:45",
                "duration": "29h 10m",
                "runs_on": "Wed, Fri",
                "classes": ["1A", "2A", "3A"],
                "fares": {"1A": 5890, "2A": 3520, "3A": 2510},
                "availability": {"1A": "AVL 4", "2A": "RAC 8", "3A": "WL 18"}
            },
            {
                "number": "12616",
                "name": "Grand Trunk Superfast",
                "category": "Superfast",
                "dep_time": "16:10",
                "arr_time": "06:20",
                "duration": "38h 10m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "3E", "SL"],
                "fares": {"1A": 5120, "2A": 2980, "3A": 2080, "3E": 1890, "SL": 790},
                "availability": {"1A": "AVL 8", "2A": "AVL 22", "3A": "RAC 14", "3E": "AVL 36", "SL": "WL 62"}
            },
            {
                "number": "12622",
                "name": "Tamil Nadu Superfast",
                "category": "Superfast",
                "dep_time": "21:05",
                "arr_time": "06:35",
                "duration": "33h 30m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "SL"],
                "fares": {"1A": 5180, "2A": 3020, "3A": 2110, "SL": 810},
                "availability": {"1A": "AVL 6", "2A": "WL 10", "3A": "WL 36", "SL": "WL 88"}
            }
        ],
        "split_journey": {
            "title": "High-Speed Break Journey via Nagpur Junction",
            "hub": "Nagpur Jn (NGP)",
            "leg1": {"train": "22692 Bengaluru Rajdhani", "route": "New Delhi → Nagpur Jn", "dep": "20:45", "arr": "10:15", "status": "AVAILABLE 45"},
            "leg2": {"train": "12622 Tamil Nadu Express", "route": "Nagpur Jn → Chennai Central", "dep": "13:20", "arr": "06:35", "status": "AVAILABLE 62"},
            "layover": "3h 05m layover at Nagpur",
            "total_duration": "33h 50m",
            "advantage": "Breaks 33hr marathon with guaranteed berths in 3A/2A"
        }
    },
    "Mumbai-Goa": {
        "origin_code": "CSMT",
        "origin_name": "Mumbai CSMT",
        "dest_code": "MAO",
        "dest_name": "Madgaon Junction (Goa)",
        "distance_km": 580,
        "base_cancellation_rate": 0.24,
        "popular_trains": [
            {
                "number": "22230",
                "name": "Madgaon-Mumbai Vande Bharat",
                "category": "Rajdhani/VB",
                "dep_time": "05:25",
                "arr_time": "13:10",
                "duration": "7h 45m",
                "runs_on": "Mon, Wed, Fri, Sat",
                "classes": ["CC", "1A"],
                "fares": {"CC": 1435, "1A": 2780},
                "availability": {"CC": "AVL 64", "1A": "AVL 16"}
            },
            {
                "number": "12052",
                "name": "Jan Shatabdi Express",
                "category": "Rajdhani/VB",
                "dep_time": "05:10",
                "arr_time": "14:15",
                "duration": "9h 05m",
                "runs_on": "Daily",
                "classes": ["CC", "2S"],
                "fares": {"CC": 945, "2S": 290},
                "availability": {"CC": "AVL 42", "2S": "AVL 120"}
            },
            {
                "number": "10104",
                "name": "Mandovi Express",
                "category": "Express",
                "dep_time": "07:10",
                "arr_time": "19:00",
                "duration": "11h 50m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "SL"],
                "fares": {"1A": 2240, "2A": 1340, "3A": 960, "SL": 355},
                "availability": {"1A": "AVL 8", "2A": "AVL 14", "3A": "RAC 10", "SL": "WL 28"}
            }
        ],
        "split_journey": {
            "title": "Coastal Route Alternative via Ratnagiri",
            "hub": "Ratnagiri Jn (RN)",
            "leg1": {"train": "10111 Konkan Kanya Express", "route": "Mumbai CSMT → Ratnagiri", "dep": "23:05", "arr": "05:15", "status": "AVAILABLE 84"},
            "leg2": {"train": "12051 Jan Shatabdi", "route": "Ratnagiri → Madgaon Jn", "dep": "09:40", "arr": "14:15", "status": "AVAILABLE 110"},
            "layover": "Morning breakfast stop in scenic Konkan",
            "total_duration": "15h 10m",
            "advantage": "Overnight departure with scenic day arrival in South Goa"
        }
    },
    "Delhi-Bangalore": {
        "origin_code": "NDLS",
        "origin_name": "New Delhi",
        "dest_code": "SBC",
        "dest_name": "KSR Bengaluru",
        "distance_km": 2365,
        "base_cancellation_rate": 0.19,
        "popular_trains": [
            {
                "number": "22692",
                "name": "Bengaluru Rajdhani Express",
                "category": "Rajdhani/VB",
                "dep_time": "20:45",
                "arr_time": "05:20",
                "duration": "32h 35m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A"],
                "fares": {"1A": 6120, "2A": 3650, "3A": 2590},
                "availability": {"1A": "AVL 4", "2A": "RAC 6", "3A": "WL 19"}
            },
            {
                "number": "12628",
                "name": "Karnataka Superfast Express",
                "category": "Superfast",
                "dep_time": "20:20",
                "arr_time": "12:00",
                "duration": "39h 40m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "3E", "SL"],
                "fares": {"1A": 5340, "2A": 3120, "3A": 2180, "3E": 1980, "SL": 830},
                "availability": {"1A": "AVL 6", "2A": "AVL 16", "3A": "RAC 20", "3E": "AVL 32", "SL": "WL 64"}
            }
        ],
        "split_journey": {
            "title": "Smart Break-Journey via Secunderabad / Hyderabad",
            "hub": "Secunderabad Jn (SC)",
            "leg1": {"train": "12724 Telangana Express", "route": "New Delhi → Secunderabad Jn", "dep": "16:00", "arr": "17:10", "status": "AVAILABLE 48"},
            "leg2": {"train": "12785 Kacheguda SF", "route": "Kacheguda → KSR Bengaluru", "dep": "19:05", "arr": "06:25", "status": "AVAILABLE 64"},
            "layover": "1h 55m transit between twin cities",
            "total_duration": "38h 25m",
            "advantage": "High clearing probability and comfortable overnight sleep"
        }
    },
    "Bangalore-Hyderabad": {
        "origin_code": "SBC",
        "origin_name": "KSR Bengaluru",
        "dest_code": "SC",
        "dest_name": "Secunderabad / Hyderabad",
        "distance_km": 610,
        "base_cancellation_rate": 0.25,
        "popular_trains": [
            {
                "number": "20704",
                "name": "Kacheguda Vande Bharat",
                "category": "Rajdhani/VB",
                "dep_time": "14:45",
                "arr_time": "23:00",
                "duration": "8h 15m",
                "runs_on": "Daily except Wed",
                "classes": ["CC", "1A"],
                "fares": {"CC": 1540, "1A": 2890},
                "availability": {"CC": "AVL 74", "1A": "AVL 20"}
            },
            {
                "number": "12786",
                "name": "Kacheguda Superfast",
                "category": "Superfast",
                "dep_time": "18:20",
                "arr_time": "05:40",
                "duration": "11h 20m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "SL"],
                "fares": {"1A": 2240, "2A": 1340, "3A": 960, "SL": 365},
                "availability": {"1A": "AVL 6", "2A": "AVL 18", "3A": "RAC 12", "SL": "WL 34"}
            }
        ],
        "split_journey": {
            "title": "Daytime Intercity Option via Guntakal Jn",
            "hub": "Guntakal Jn (GTL)",
            "leg1": {"train": "12649 Karnataka Sampark Kranti", "route": "Bengaluru → Guntakal", "dep": "13:50", "arr": "18:25", "status": "AVAILABLE 90"},
            "leg2": {"train": "12708 AP Sampark Kranti", "route": "Guntakal → Kacheguda", "dep": "19:40", "arr": "02:15", "status": "AVAILABLE 78"},
            "layover": "1h 15m smooth connection",
            "total_duration": "12h 25m",
            "advantage": "Instant confirmed seats during peak festival and weekend rush"
        }
    },
    "Kolkata-Chennai": {
        "origin_code": "HWH",
        "origin_name": "Howrah Junction",
        "dest_code": "MAS",
        "dest_name": "MGR Chennai Central",
        "distance_km": 1660,
        "base_cancellation_rate": 0.21,
        "popular_trains": [
            {
                "number": "12841",
                "name": "Coromandel Express",
                "category": "Superfast",
                "dep_time": "15:20",
                "arr_time": "17:00",
                "duration": "25h 40m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "SL"],
                "fares": {"1A": 4480, "2A": 2620, "3A": 1820, "SL": 695},
                "availability": {"1A": "AVL 8", "2A": "AVL 24", "3A": "RAC 16", "SL": "WL 45"}
            },
            {
                "number": "12839",
                "name": "Howrah Chennai Mail",
                "category": "Superfast",
                "dep_time": "23:55",
                "arr_time": "03:45",
                "duration": "27h 50m",
                "runs_on": "Daily",
                "classes": ["1A", "2A", "3A", "SL"],
                "fares": {"1A": 4420, "2A": 2580, "3A": 1790, "SL": 685},
                "availability": {"1A": "AVL 6", "2A": "WL 8", "3A": "WL 24", "SL": "WL 60"}
            }
        ],
        "split_journey": {
            "title": "Smart Break-Journey via Visakhapatnam Jn",
            "hub": "Visakhapatnam Jn (VSKP)",
            "leg1": {"train": "20898 Vande Bharat", "route": "Howrah → Visakhapatnam", "dep": "06:10", "arr": "14:35", "status": "AVAILABLE 82"},
            "leg2": {"train": "12841 Coromandel Express", "route": "Visakhapatnam → Chennai", "dep": "17:15", "arr": "07:00", "status": "AVAILABLE 54"},
            "layover": "2h 40m port city transit",
            "total_duration": "24h 50m",
            "advantage": "Faster overall journey with confirmed Vande Bharat & Superfast sleeper"
        }
    }
}

def compute_engineered_features(df_input):
    df_feat = df_input.copy()
    df_feat["wl_per_day"] = df_feat["current_wl"] / (df_feat["lead_time_days"] + 1e-4)
    df_feat["log_current_wl"] = np.log1p(df_feat["current_wl"])
    df_feat["lead_time_sqrt"] = np.sqrt(df_feat["lead_time_days"])
    df_feat["expected_clearance_ratio"] = (
        df_feat["lead_time_days"] * df_feat["base_cancellation_rate"] * 10
    ) / (df_feat["current_wl"] + 1)
    return df_feat

def predict_single_pnr(data):
    corridor = data.get("corridor", "Delhi-Mumbai")
    train_category = data.get("train_category", "Superfast")
    coach_class = data.get("coach_class", "3A")
    quota = data.get("quota", "GNWL")
    current_wl = int(data.get("current_wl", 25))
    lead_time_days = max(int(data.get("lead_time_days", 14)), 1)
    is_festive_season = int(data.get("is_festive_season", 0))
    is_weekend = int(data.get("is_weekend", 0))
    
    corr_info = CORRIDOR_METADATA.get(corridor, CORRIDOR_METADATA["Delhi-Mumbai"])
    base_canc = float(data.get("base_cancellation_rate", corr_info["base_cancellation_rate"]))
    
    input_dict = {
        "corridor": [corridor],
        "train_category": [train_category],
        "coach_class": [coach_class],
        "quota": [quota],
        "current_wl": [current_wl],
        "lead_time_days": [lead_time_days],
        "is_festive_season": [is_festive_season],
        "is_weekend": [is_weekend],
        "base_cancellation_rate": [base_canc]
    }
    
    df_single = pd.DataFrame(input_dict)
    df_engineered = compute_engineered_features(df_single)
    
    raw_prob = float(model.predict_proba(df_engineered)[0, 1])
    prob_pct = round(raw_prob * 100, 1)
    
    if prob_pct >= 75.0:
        tier = "HIGH"
        tier_label = "High Confirmation Likelihood"
        tier_color = "emerald"
        recommendation = "Safe to Book & Retain"
        action_summary = "High probability of berth confirmation before final chart preparation. Proceed with standard booking."
        advice = [
            f"Your waitlist rank ({quota}-{current_wl}) has high clearance velocity on {corridor}.",
            f"Expected confirmation window: ~{max(1, int(lead_time_days * 0.4))} to {lead_time_days} days prior to departure.",
            "Minimal risk of ticket being auto-cancelled on chart preparation."
        ]
    elif prob_pct >= 40.0:
        tier = "MEDIUM"
        tier_label = "RAC / Moderate Uncertainty"
        tier_color = "amber"
        recommendation = "Monitor Closely or Secure RAC"
        action_summary = "Significant chance of partial confirmation (RAC berth) or tight chart preparation allotment."
        advice = [
            f"Current rank ({quota}-{current_wl}) is within the volatile RAC/Confirmation borderline.",
            "Higher likelihood of receiving RAC (Reservation Against Cancellation - half berth allotment).",
            "Set a calendar reminder 24 hours prior to departure to monitor chart prep movements.",
            "Keep a Tatkal booking window as an active standby fallback."
        ]
    else:
        tier = "LOW"
        tier_label = "High Risk / Likely Dropped"
        tier_color = "rose"
        recommendation = "Immediate Alternate Strategy Required"
        action_summary = "Critical waitlist density. The probability of final berth allotment is below 40%."
        advice = [
            f"Quota '{quota}' clears strictly; current waitlist ({current_wl}) exceeds expected corridor turnover.",
            "Tatkal Quota: Be ready at 10:00 AM (AC) or 11:00 AM (Non-AC) 1 day prior to origin station departure.",
            "Consider switching to higher-capacity classes (3E, SL) or parallel Superfast services.",
            "Consider our Smart Break-Journey via intermediate junction stations."
        ]
        
    return {
        "probability": raw_prob,
        "probability_pct": prob_pct,
        "risk_tier": tier,
        "tier_label": tier_label,
        "tier_color": tier_color,
        "recommendation": recommendation,
        "action_summary": action_summary,
        "advice_points": advice,
        "inputs": {
            "corridor": corridor,
            "train_category": train_category,
            "coach_class": coach_class,
            "quota": quota,
            "current_wl": current_wl,
            "lead_time_days": lead_time_days,
            "is_festive_season": is_festive_season,
            "is_weekend": is_weekend
        }
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/corridors", methods=["GET"])
def get_corridors():
    return jsonify({
        "status": "success",
        "corridors": CORRIDOR_METADATA,
        "quotas": [
            {"code": "GNWL", "name": "General Waitlist (Origin-Destination, Highest Clearance)"},
            {"code": "RLWL", "name": "Remote Location Waitlist (Intermediate Stations, Restricted Seats)"},
            {"code": "PQWL", "name": "Pooled Quota Waitlist (Small Stations & Short Legs, Lowest Clearance)"}
        ],
        "classes": [
            {"code": "1A", "name": "First AC (Executive Luxury)"},
            {"code": "2A", "name": "AC 2-Tier (Premium Sleeper)"},
            {"code": "3A", "name": "AC 3-Tier (Standard AC)"},
            {"code": "3E", "name": "AC 3 Economy (Modern High Capacity)"},
            {"code": "SL", "name": "Sleeper Class (Highest Coach Density)"},
            {"code": "CC", "name": "AC Chair Car (Shatabdi/Vande Bharat)"}
        ]
    })

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    return jsonify({
        "status": "success",
        "metrics": model_metrics
    })

@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True)
        result = predict_single_pnr(data)
        
        # Calculate trajectory over time
        lead_time = max(int(data.get("lead_time_days", 14)), 1)
        current_wl = int(data.get("current_wl", 25))
        
        trajectory_points = []
        step = max(1, lead_time // 10)
        days_range = sorted(list(set(list(range(1, lead_time + 1, step)) + [lead_time])))
        
        for d in days_range:
            sim_data = data.copy()
            sim_data["lead_time_days"] = d
            decay_factor = (d / lead_time) ** 0.85
            sim_data["current_wl"] = max(1, int(current_wl * decay_factor))
            sim_pred = predict_single_pnr(sim_data)
            trajectory_points.append({
                "days_remaining": d,
                "projected_wl": sim_data["current_wl"],
                "probability_pct": sim_pred["probability_pct"]
            })
            
        result["trajectory"] = trajectory_points
        
        # Quota clearance comparison for the same waitlist number
        quota_comparison = []
        for q in ["GNWL", "RLWL", "PQWL"]:
            q_data = data.copy()
            q_data["quota"] = q
            q_pred = predict_single_pnr(q_data)
            quota_comparison.append({
                "quota": q,
                "probability_pct": q_pred["probability_pct"],
                "tier": q_pred["risk_tier"]
            })
        result["quota_comparison"] = quota_comparison
        
        # Class alternatives on the same corridor
        available_classes = ["1A", "2A", "3A", "3E", "SL", "CC"]
        class_alternatives = []
        for c in available_classes:
            if c != data.get("coach_class", "3A"):
                c_data = data.copy()
                c_data["coach_class"] = c
                wl_multipliers = {"1A": 0.3, "2A": 0.6, "3A": 1.0, "3E": 0.9, "SL": 1.6, "CC": 0.8}
                ratio = wl_multipliers.get(c, 1.0) / wl_multipliers.get(data.get("coach_class", "3A"), 1.0)
                c_data["current_wl"] = max(1, int(current_wl * ratio))
                c_pred = predict_single_pnr(c_data)
                class_alternatives.append({
                    "coach_class": c,
                    "simulated_wl": c_data["current_wl"],
                    "probability_pct": c_pred["probability_pct"],
                    "tier": c_pred["risk_tier"],
                    "recommendation": c_pred["recommendation"]
                })
        result["class_alternatives"] = sorted(class_alternatives, key=lambda x: x["probability_pct"], reverse=True)
        
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/simulate", methods=["POST"])
def simulate():
    try:
        data = request.get_json(force=True)
        wl_values = [5, 15, 30, 50, 75, 100]
        days_values = [2, 7, 14, 21, 35, 60]
        
        matrix = []
        for wl in wl_values:
            row = {"waitlist": wl, "scores": []}
            for d in days_values:
                sim_data = data.copy()
                sim_data["current_wl"] = wl
                sim_data["lead_time_days"] = d
                res = predict_single_pnr(sim_data)
                row["scores"].append({
                    "days": d,
                    "probability_pct": res["probability_pct"],
                    "tier": res["risk_tier"]
                })
            matrix.append(row)
            
        return jsonify({
            "status": "success",
            "days_headers": days_values,
            "matrix": matrix
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ============================================================================
# NEW REVOLUTIONARY TRIP PLANNER & BOOKING SIMULATION APIS
# ============================================================================

@app.route("/api/search_trains", methods=["GET"])
def search_trains():
    """
    Trip Planner Search Engine:
    Given origin and destination (corridor), returns all running trains with real-time
    AI berth confirmation probability computed on-the-fly for any waitlisted classes!
    """
    corridor = request.args.get("corridor", "Delhi-Mumbai")
    travel_date = request.args.get("date", datetime.date.today().strftime("%Y-%m-%d"))
    quota = request.args.get("quota", "GNWL")
    preferred_class = request.args.get("class", "3A")
    
    corr_info = CORRIDOR_METADATA.get(corridor, CORRIDOR_METADATA["Delhi-Mumbai"])
    
    # Calculate days to travel from date
    try:
        dt = datetime.datetime.strptime(travel_date, "%Y-%m-%d").date()
        days_left = max(1, (dt - datetime.date.today()).days)
    except Exception:
        days_left = 15

    results = []
    for train in corr_info["popular_trains"]:
        train_entry = {
            "number": train["number"],
            "name": train["name"],
            "category": train["category"],
            "dep_time": train["dep_time"],
            "arr_time": train["arr_time"],
            "duration": train["duration"],
            "runs_on": train["runs_on"],
            "origin_code": corr_info["origin_code"],
            "dest_code": corr_info["dest_code"],
            "class_options": []
        }
        
        for c in train["classes"]:
            raw_avail = train.get("availability", {}).get(c, "AVL 15")
            fare = train.get("fares", {}).get(c, 1200)
            
            # If waitlisted, compute real-time AI confirmation likelihood
            ai_prob = None
            ai_tier = "AVAILABLE"
            if "WL" in raw_avail:
                try:
                    wl_num = int(raw_avail.replace("WL", "").strip())
                except Exception:
                    wl_num = 20
                
                pred_input = {
                    "corridor": corridor,
                    "train_category": train["category"],
                    "coach_class": c,
                    "quota": quota,
                    "current_wl": wl_num,
                    "lead_time_days": days_left
                }
                pred_res = predict_single_pnr(pred_input)
                ai_prob = pred_res["probability_pct"]
                ai_tier = pred_res["risk_tier"]
            elif "RAC" in raw_avail:
                ai_prob = 85.0
                ai_tier = "HIGH"
            else:
                ai_prob = 100.0
                ai_tier = "AVAILABLE"
                
            train_entry["class_options"].append({
                "coach_class": c,
                "fare": fare,
                "availability": raw_avail,
                "ai_probability": ai_prob,
                "ai_tier": ai_tier
            })
            
        results.append(train_entry)
        
    return jsonify({
        "status": "success",
        "corridor": corridor,
        "origin": f"{corr_info['origin_name']} ({corr_info['origin_code']})",
        "destination": f"{corr_info['dest_name']} ({corr_info['dest_code']})",
        "travel_date": travel_date,
        "days_left": days_left,
        "trains": results,
        "split_journey": corr_info.get("split_journey")
    })

@app.route("/api/book_ticket", methods=["POST"])
def book_ticket():
    """
    Simulates authentic IRCTC Ticket Reservation & Generates Official Digital E-Ticket (ERS)
    complete with 10-digit PNR, Coach/Berth Allocation, and Barcode/QR verification.
    """
    try:
        data = request.get_json(force=True)
        
        # Generate authentic 10-digit PNR (Indian Railways convention: 3 digits + '-' + 7 digits)
        prefix = random.choice([248, 482, 621, 834, 192])
        suffix = random.randint(1000000, 9999999)
        pnr_number = f"{prefix}-{suffix}"
        
        # Passengers
        passengers = data.get("passengers", [
            {"name": "Piyush Sharma", "age": 28, "gender": "Male", "berth_pref": "Lower Berth"}
        ])
        
        train_number = data.get("train_number", "12952")
        train_name = data.get("train_name", "Mumbai Tejas Rajdhani")
        coach_class = data.get("coach_class", "3A")
        quota = data.get("quota", "GNWL")
        travel_date = data.get("travel_date", datetime.date.today().strftime("%Y-%m-%d"))
        corridor = data.get("corridor", "Delhi-Mumbai")
        total_fare = float(data.get("total_fare", 2040.0))
        
        # Determine confirmed vs waitlist allotment
        availability_status = data.get("availability", "AVL 14")
        
        assigned_passengers = []
        coach_prefixes = {"1A": "H1", "2A": "A1", "3A": "B3", "3E": "M2", "SL": "S4", "CC": "C2"}
        coach = coach_prefixes.get(coach_class, "B1")
        
        for i, p in enumerate(passengers):
            berth_no = random.randint(1, 64)
            pref = p.get("berth_pref", "No Preference")
            if "Lower" in pref:
                berth_type = "LOWER"
            elif "Upper" in pref:
                berth_type = "UPPER"
            elif "Middle" in pref:
                berth_type = "MIDDLE"
            elif "Side Lower" in pref:
                berth_type = "SIDE LOWER"
            else:
                berth_type = random.choice(["LOWER", "MIDDLE", "UPPER", "SIDE LOWER", "SIDE UPPER"])
                
            if "AVL" in availability_status:
                booking_status = f"CONFIRMED (CNF)"
                current_status = f"{coach}-{berth_no} / {berth_type}"
            elif "RAC" in availability_status:
                booking_status = "RAC"
                current_status = f"RAC {i+1} (Coach {coach})"
            else:
                wl_num = random.randint(1, 15)
                booking_status = f"{quota} WL {wl_num}"
                current_status = f"WL {wl_num} (AI Protected)"
                
            assigned_passengers.append({
                "name": p.get("name", "Passenger"),
                "age": p.get("age", 30),
                "gender": p.get("gender", "M"),
                "booking_status": booking_status,
                "current_status": current_status,
                "berth_type": berth_type
            })
            
        corr_info = CORRIDOR_METADATA.get(corridor, CORRIDOR_METADATA["Delhi-Mumbai"])
        booking_record = {
            "pnr": pnr_number,
            "train_number": train_number,
            "train_name": train_name,
            "coach_class": coach_class,
            "quota": quota,
            "from_station": f"{corr_info['origin_name']} ({corr_info['origin_code']})",
            "to_station": f"{corr_info['dest_name']} ({corr_info['dest_code']})",
            "travel_date": travel_date,
            "booking_timestamp": datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S IST"),
            "total_fare": total_fare,
            "passengers": assigned_passengers,
            "trip_shield": True,
            "convenience_fee": 17.70,
            "gst": round(total_fare * 0.05, 2),
            "grand_total": round(total_fare + 17.70 + (total_fare * 0.05), 2),
            "qr_code_token": f"IRCTC-PNR-{pnr_number}-{train_number}-{travel_date}"
        }
        
        BOOKED_TICKETS.insert(0, booking_record)
        
        return jsonify({
            "status": "success",
            "message": "Ticket successfully reserved via RailPredict Intelligent Engine",
            "ticket": booking_record
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/my_tickets", methods=["GET"])
def get_my_tickets():
    return jsonify({
        "status": "success",
        "tickets": BOOKED_TICKETS
    })

@app.route("/api/tatkal_status", methods=["GET"])
def get_tatkal_status():
    """
    Returns live countdown and status for IRCTC Tatkal booking windows:
    AC Classes open at 10:00 AM IST; Non-AC Classes open at 11:00 AM IST.
    """
    now = datetime.datetime.now()
    today_ac = now.replace(hour=10, minute=0, second=0, microsecond=0)
    today_non_ac = now.replace(hour=11, minute=0, second=0, microsecond=0)
    
    if now < today_ac:
        next_ac = today_ac
        status_ac = "Opens at 10:00 AM"
    else:
        next_ac = today_ac + datetime.timedelta(days=1)
        status_ac = "Tomorrow at 10:00 AM"
        
    seconds_to_ac = int((next_ac - now).total_seconds())
    
    return jsonify({
        "status": "success",
        "server_time": now.strftime("%H:%M:%S IST"),
        "ac_tatkal": {
            "window": "10:00 AM IST (1A, 2A, 3A, 3E, CC)",
            "seconds_left": seconds_to_ac,
            "status": status_ac
        },
        "non_ac_tatkal": {
            "window": "11:00 AM IST (Sleeper, 2S)",
            "status": "11:00 AM IST Daily"
        }
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
