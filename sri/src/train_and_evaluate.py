"""
Hierarchical AI Model Training, Geographic Holdout Evaluation & Ablation Suite
Trains the 2-Stage Probabilistic Classifier, evaluates on 530 unseen held-out test events,
computes Confusion Matrix, Precision/Recall, and runs Multi-Modal Ablation experiments.
"""

import numpy as np
import pandas as pd
import joblib
import json
import os
import sys

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    precision_score, recall_score, confusion_matrix, classification_report
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.feature_extractor import FEATURE_NAMES
from src.hierarchical_classifier import HierarchicalThermalClassifier, CLASS_MAP

# --- BASELINE 1: FIRMS-Only Heuristic ---
def predict_baseline_firms_only(df):
    preds = []
    for _, r in df.iterrows():
        if r['bright_mwir_k'] > 360.0:
            preds.append(0)  # Guess Flare
        elif r['frp_mw'] > 40.0:
            preds.append(2)  # Guess Wildfire
        else:
            preds.append(3)  # Guess Agro
    return np.array(preds)

# --- BASELINE 2: Distance Heuristic ---
def predict_baseline_rule_based(df):
    preds = []
    for _, r in df.iterrows():
        if r['dist_to_facility_km'] <= 2.0:
            if r['frp_z_score'] > 3.0:
                preds.append(1)  # Accident
            else:
                preds.append(0)  # Flare
        elif r['dist_to_mine_km'] <= 15.0 and r['recurrence_90d'] > 0.5:
            preds.append(4)  # Coal
        elif r['forest_fraction'] > 0.6:
            preds.append(2)  # Wildfire
        else:
            preds.append(3)  # Agro
    return np.array(preds)


def train_and_benchmark():
    print("🚀 Loading Labeled Benchmark Dataset...")
    df = pd.read_csv("data/processed/labeled_benchmark_dataset.csv")
    
    train_df = df[df['region_split'] == 'TRAIN'].copy()
    test_df = df[df['region_split'] == 'HELD_OUT_TEST'].copy()
    
    X_train = train_df[FEATURE_NAMES].values
    y_train = train_df['ground_truth_class'].values
    
    X_test = test_df[FEATURE_NAMES].values
    y_test = test_df['ground_truth_class'].values
    
    print(f"-> Train Set: {len(X_train)} samples across {len(train_df['site_name'].unique())} sites")
    print(f"-> Held-Out Test Set: {len(X_test)} samples across {len(test_df['site_name'].unique())} UNSEEN test sites")
    
    # 1. Train Proposed Hierarchical Model
    print("\n--- Training Proposed Multi-Modal Hierarchical Classifier ---")
    model = HierarchicalThermalClassifier()
    model.fit(X_train, y_train)
    
    # Predict on unseen test set
    test_dicts = test_df.to_dict(orient='records')
    y_pred_proposed = model.predict(X_test, feature_dicts=test_dicts)
    y_pred_b1 = predict_baseline_firms_only(test_df)
    y_pred_b2 = predict_baseline_rule_based(test_df)
    
    # Industrial Binary Mask (0: Flare, 1: Accident)
    y_test_is_ind = np.isin(y_test, [0, 1])
    
    def compute_metrics(y_true, y_pred, name):
        acc = accuracy_score(y_true, y_pred)
        bal_acc = balanced_accuracy_score(y_true, y_pred)
        macro_f1 = f1_score(y_true, y_pred, average='macro')
        
        # Industrial Precision & Recall
        pred_is_ind = np.isin(y_pred, [0, 1])
        ind_prec = precision_score(y_test_is_ind, pred_is_ind, zero_division=0)
        ind_rec = recall_score(y_test_is_ind, pred_is_ind, zero_division=0)
        
        return {
            "model_name": name,
            "accuracy": round(float(acc) * 100, 2),
            "balanced_accuracy": round(float(bal_acc) * 100, 2),
            "macro_f1": round(float(macro_f1) * 100, 2),
            "industrial_precision": round(float(ind_prec) * 100, 2),
            "industrial_recall": round(float(ind_rec) * 100, 2)
        }
        
    m_b1 = compute_metrics(y_test, y_pred_b1, "Baseline 1: FIRMS-Only Heuristic")
    m_b2 = compute_metrics(y_test, y_pred_b2, "Baseline 2: Spatial Proximity Rule Engine")
    m_prop = compute_metrics(y_test, y_pred_proposed, "Proposed Multi-Modal Hierarchical Model")
    
    comparison_table = pd.DataFrame([m_b1, m_b2, m_prop])
    print("\n🏆 MODEL PROGRESSION BENCHMARK RESULTS (On Unseen Held-Out Sites):")
    print(comparison_table.to_string(index=False))
    
    # Confusion Matrix for Proposed Model
    cm = confusion_matrix(y_test, y_pred_proposed, labels=[0, 1, 2, 3, 4, 5])
    print("\n📊 Confusion Matrix (Proposed Model):")
    print(pd.DataFrame(cm, index=[CLASS_MAP[i] for i in range(6)], columns=[CLASS_MAP[i] for i in range(6)]))
    
    # 2. Multi-Modal Ablation Study
    print("\n--- Running Multi-Modal Ablation Study ---")
    ablation_results = []
    
    modality_splits = [
        ("Thermal Only", FEATURE_NAMES[:6]),
        ("+ Industrial GIS", FEATURE_NAMES[:10]),
        ("+ 10m LULC Footprints", FEATURE_NAMES[:14]),
        ("+ Spatiotemporal Baselines", FEATURE_NAMES[:21]),
        ("+ Optical & Meteorology (Full 26-D)", FEATURE_NAMES)
    ]
    
    for mod_name, feats in modality_splits:
        idx = [FEATURE_NAMES.index(f) for f in feats]
        rf = RandomForestClassifier(n_estimators=80, max_depth=7, random_state=42)
        rf.fit(X_train[:, idx], y_train)
        pred = rf.predict(X_test[:, idx])
        
        ablation_results.append({
            "modality": mod_name,
            "feature_count": len(feats),
            "macro_f1": round(float(f1_score(y_test, pred, average='macro')) * 100, 2),
            "accuracy": round(float(accuracy_score(y_test, pred)) * 100, 2),
            "industrial_precision": round(float(precision_score(y_test_is_ind, np.isin(pred, [0, 1]), zero_division=0)) * 100, 2)
        })
        
    df_abl = pd.DataFrame(ablation_results)
    print(df_abl.to_string(index=False))
    
    # Save Artifacts
    joblib.dump(model, "data/processed/trained_hierarchical_model.joblib")
    
    report_data = {
        "benchmark_comparison": [m_b1, m_b2, m_prop],
        "ablation_study": ablation_results,
        "confusion_matrix": cm.tolist(),
        "classes": [CLASS_MAP[i] for i in range(6)],
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_count": len(FEATURE_NAMES)
    }
    
    with open("data/processed/evaluation_report.json", "w") as f:
        json.dump(report_data, f, indent=2)
        
    print("\n✅ Trained model saved to data/processed/trained_hierarchical_model.joblib")
    print("✅ Full benchmark report saved to data/processed/evaluation_report.json")

if __name__ == "__main__":
    train_and_benchmark()
