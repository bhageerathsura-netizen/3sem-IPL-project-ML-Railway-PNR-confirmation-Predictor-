# RailPredict AI: Machine Learning Classifier for Forecasting Indian Railway Berth Confirmation

> **Platform:** Enterprise Rail Analytics Platform  
> **Domain:** Indian Railways (IRCTC) PNR Berth Confirmation Intelligence  
> **Engine:** Calibrated Supervised Machine Learning Classifier

---

## 1. Project Background & Problem Statement
Every day, Indian Railways carries over 23 million passengers. Due to heavy demand-supply disparities, millions of passengers are forced to purchase waitlisted tickets (`GNWL`, `RLWL`, `PQWL`) with zero transparency on whether their berth will be confirmed before final chart preparation (4 hours prior to departure).

RailPredict AI deploys a supervised machine learning classification and probability calibration engine that forecasts final PNR chart status at the moment of booking, helping passengers avoid expensive emergency travel surge exploitation, Tatkal panic, and cancellation penalties.

---

## 2. Key Novel Enhancements & Architectural Features
1. **Multivariable Feature Engineering**: Combines waitlist density, lead time remaining, coach tier cancellation dynamics, and festive/weekend rush indicators.
2. **Quota-Specific Risk Profiling**: Models differential clearing velocity (`GNWL` clearing rate is ~3.5x higher than `RLWL` and `PQWL`).
3. **Calibrated Probability Scoring**: Platt scaling / Isotonic calibration transforms raw classification into statistically calibrated likelihoods ($0\text{--}100\%$).
4. **Three-Tier Actionable Strategy**:
   - **High Confirmation (>75%)**: Safe to book and retain.
   - **Medium Uncertainty / RAC (40% - 75%)**: High likelihood of half-berth RAC allocation; monitor chart preparation.
   - **High Risk / Likely Dropped (≤40%)**: Immediate tactical advice: Tatkal alerts, same-corridor alternative classes (e.g., 3E, SL), or split-station journeys.
5. **Interactive What-If Sensitivity Matrix**: Real-time multi-scenario simulation varying waitlist ranks and lead times.
6. **Zero Commercial Scraping Risk**: Trained on synthetic historical journey datasets without violating IRCTC terms of service.

---

## 3. Technology Stack & Specifications
- **Programming Language**: Python 3.10+ (Tested on Python 3.14)
- **Machine Learning**: `scikit-learn`, `NumPy`, `Pandas`, `joblib`
- **Classifiers**: Calibrated `RandomForestClassifier` (Primary) & `LogisticRegression` (Baseline)
- **Web Backend**: Python Flask REST API
- **Frontend / UI**: HTML5, Tailwind CSS, Chart.js, Glassmorphism Design System, SVG Radial Speedometer
- **Inference Latency**: Instantaneous (< 15 ms per query)

---

## 4. Directory Structure
```
IPL_project/
├── data/
│   ├── generate_dataset.py       # Historical trajectory dataset generator (18,000 PNRs)
│   └── pnr_clearing_dataset.csv  # Synthetic dataset across 8 major corridors
├── models/
│   ├── train_model.py            # Model training, calibration, and evaluation
│   ├── irctc_pnr_model.joblib    # Serialized calibrated model pipeline
│   └── model_metrics.json        # Accuracy, ROC-AUC, Confusion Matrix, Feature Importance
├── static/
│   ├── css/
│   │   └── style.css             # Premier luxury rail theme & glassmorphic styling
│   └── js/
│       └── app.js                # Frontend controllers, radial gauge, dynamic charts
├── templates/
│   └── index.html                # Premier single-page application
├── test_app.py                   # Automated unit & integration test suite
├── app.py                        # Flask server & REST API
├── requirements.txt              # Project dependencies
└── README.md                     # Documentation
```

---

## 5. How to Run the Application

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Automated Test Suite
```bash
python test_app.py
```

### Step 3: Start the Web Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 6. REST API Endpoints
- `GET /`: Serves the Premier UI.
- `GET /api/corridors`: Returns major Indian Railway corridors, trains, classes, and quotas.
- `GET /api/metrics`: Returns evaluation metrics (Accuracy, ROC-AUC, F1, Confusion Matrix, Feature Importance).
- `POST /api/predict`: Returns real-time confirmation probability, risk tier, clearance trajectory curve, quota comparisons, and class alternatives.
- `POST /api/simulate`: Generates a 6x6 scenario heatmap matrix across waitlists (5 to 100) and lead times (2 to 60 days).
