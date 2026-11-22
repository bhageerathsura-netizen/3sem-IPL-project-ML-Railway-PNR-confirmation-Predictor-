"""
Machine Learning Training Pipeline for Indian Railways PNR Confirmation Forecasting
Implements Feature Engineering, Random Forest and Logistic Regression training,
Probability Calibration (Platt Scaling), Cross-validation, and Model Serialization.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

def run_training():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, "data", "pnr_clearing_dataset.csv")
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Run generate_dataset.py first.")
        
    df = pd.read_csv(data_path)
    
    # Feature Engineering
    df["wl_per_day"] = df["current_wl"] / (df["lead_time_days"] + 1e-4)
    df["log_current_wl"] = np.log1p(df["current_wl"])
    df["lead_time_sqrt"] = np.sqrt(df["lead_time_days"])
    df["expected_clearance_ratio"] = (df["lead_time_days"] * df["base_cancellation_rate"] * 10) / (df["current_wl"] + 1)
    
    categorical_features = ["corridor", "train_category", "coach_class", "quota"]
    numerical_features = [
        "current_wl", "lead_time_days", "is_festive_season", 
        "is_weekend", "base_cancellation_rate", "wl_per_day", 
        "log_current_wl", "lead_time_sqrt", "expected_clearance_ratio"
    ]
    
    X = df[categorical_features + numerical_features]
    y = df["is_confirmed"]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    # Preprocessor pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )
    
    # Baseline Model: Logistic Regression
    lr_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_preds = lr_pipeline.predict(X_test)
    lr_probs = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_acc = accuracy_score(y_test, lr_preds)
    lr_auc = roc_auc_score(y_test, lr_probs)
    lr_f1 = f1_score(y_test, lr_preds)
    
    # Tuned Random Forest Classifier
    rf_base = RandomForestClassifier(
        n_estimators=200,
        max_depth=16,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1
    )
    
    calibrated_rf = CalibratedClassifierCV(estimator=rf_base, method="sigmoid", cv=3)
    
    rf_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", calibrated_rf)
    ])
    
    rf_pipeline.fit(X_train, y_train)
    rf_preds = rf_pipeline.predict(X_test)
    rf_probs = rf_pipeline.predict_proba(X_test)[:, 1]
    
    rf_acc = accuracy_score(y_test, rf_preds)
    rf_prec = precision_score(y_test, rf_preds)
    rf_rec = recall_score(y_test, rf_preds)
    rf_f1 = f1_score(y_test, rf_preds)
    rf_auc = roc_auc_score(y_test, rf_probs)
    conf_matrix = confusion_matrix(y_test, rf_preds)
    
    print("\n--- Model Performance (Tuned Random Forest) ---")
    print(f"Accuracy:  {rf_acc * 100:.2f}%")
    print(f"Precision: {rf_prec * 100:.2f}%")
    print(f"Recall:    {rf_rec * 100:.2f}%")
    print(f"F1-Score:  {rf_f1:.4f}")
    print(f"ROC-AUC:   {rf_auc:.4f}")
    
    # Extract Feature Importances
    preprocessor_fit = rf_pipeline.named_steps["preprocessor"]
    cat_encoder = preprocessor_fit.named_transformers_["cat"]
    cat_feature_names = list(cat_encoder.get_feature_names_out(categorical_features))
    all_feature_names = numerical_features + cat_feature_names
    
    temp_rf = RandomForestClassifier(n_estimators=100, max_depth=14, random_state=42, n_jobs=-1)
    X_train_trans = preprocessor_fit.transform(X_train)
    temp_rf.fit(X_train_trans, y_train)
    importances = temp_rf.feature_importances_
    
    feat_importance_df = pd.DataFrame({
        "feature": all_feature_names,
        "importance": importances
    }).sort_values(by="importance", ascending=False)
    
    top_features = feat_importance_df.head(10).to_dict(orient="records")
    
    # Save model pipeline
    models_dir = os.path.join(base_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    model_save_path = os.path.join(models_dir, "irctc_pnr_model.joblib")
    joblib.dump(rf_pipeline, model_save_path, compress=3)
    
    metrics = {
        "dataset_size": int(len(df)),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "random_forest": {
            "accuracy": round(float(rf_acc), 4),
            "precision": round(float(rf_prec), 4),
            "recall": round(float(rf_rec), 4),
            "f1_score": round(float(rf_f1), 4),
            "roc_auc": round(float(rf_auc), 4),
            "confusion_matrix": {
                "true_negative": int(conf_matrix[0][0]),
                "false_positive": int(conf_matrix[0][1]),
                "false_negative": int(conf_matrix[1][0]),
                "true_positive": int(conf_matrix[1][1])
            }
        },
        "logistic_regression": {
            "accuracy": round(float(lr_acc), 4),
            "roc_auc": round(float(lr_auc), 4),
            "f1_score": round(float(lr_f1), 4)
        },
        "top_features": top_features,
        "classes": ["DROPPED", "CONFIRMED"],
        "quotas_supported": ["GNWL", "RLWL", "PQWL"],
        "coach_classes_supported": ["1A", "2A", "3A", "3E", "SL", "CC"]
    }
    
    metrics_path = os.path.join(models_dir, "model_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Metrics saved at: {metrics_path}")
    return metrics

if __name__ == "__main__":
    run_training()
