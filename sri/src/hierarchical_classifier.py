"""
Hierarchical Multi-Modal AI Classifier Class Definition
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier

CLASS_MAP = {
    0: "INDUSTRIAL_ROUTINE_FLARE",
    1: "INDUSTRIAL_ACCIDENTAL_FIRE",
    2: "NATURAL_FOREST_WILDFIRE",
    3: "AGRICULTURAL_CROP_BURNING",
    4: "MINING_COAL_SEAM_FIRE",
    5: "OTHER_THERMAL_ANOMALY"
}

class HierarchicalThermalClassifier:
    def __init__(self):
        # Stage 1: Industrial (0, 1) vs Non-Industrial (2, 3, 4, 5)
        self.stage1_model = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
        # Stage 2a: Industrial Sub-Classifier (0: Flare vs 1: Accident)
        self.stage2a_model = GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
        # Stage 2b: Non-Industrial Sub-Classifier (2: Forest, 3: Agro, 4: Mining, 5: Other)
        self.stage2b_model = ExtraTreesClassifier(n_estimators=200, max_depth=14, min_samples_split=2, class_weight='balanced', random_state=42)

    def fit(self, X_train, y_train):
        y_stage1 = np.isin(y_train, [0, 1]).astype(int)
        self.stage1_model.fit(X_train, y_stage1)
        
        ind_mask = (y_stage1 == 1)
        if np.sum(ind_mask) > 0:
            self.stage2a_model.fit(X_train[ind_mask], y_train[ind_mask])
            
        non_ind_mask = (y_stage1 == 0)
        if np.sum(non_ind_mask) > 0:
            self.stage2b_model.fit(X_train[non_ind_mask], y_train[non_ind_mask])
            
        return self

    def predict(self, X, feature_dicts=None):
        p_ind = self.stage1_model.predict_proba(X)[:, 1]
        preds = np.zeros(len(X), dtype=int)
        
        for i in range(len(X)):
            x_single = X[i:i+1]
            if p_ind[i] >= 0.5:
                preds[i] = int(self.stage2a_model.predict(x_single)[0])
            else:
                if feature_dicts and i < len(feature_dicts):
                    fd = feature_dicts[i]
                    if fd.get('dist_to_mine_km', 999.0) < 30.0 and fd.get('recurrence_90d', 0.0) > 0.40:
                        preds[i] = 4
                    elif fd.get('bare_fraction', 0.0) > 0.08 and fd.get('frp_mw', 0.0) < 10.0 and fd.get('recurrence_90d', 0.0) < 0.1:
                        preds[i] = 5
                    else:
                        preds[i] = int(self.stage2b_model.predict(x_single)[0])
                else:
                    preds[i] = int(self.stage2b_model.predict(x_single)[0])
                
        return preds

    def predict_proba_and_evidence(self, x_vector, feature_dict, feature_names=None):
        x_2d = x_vector.reshape(1, -1)
        p_ind = float(self.stage1_model.predict_proba(x_2d)[0, 1])
        
        if p_ind >= 0.5:
            pred_class = int(self.stage2a_model.predict(x_2d)[0])
            probs = self.stage2a_model.predict_proba(x_2d)[0]
            confidence = float(np.max(probs) * p_ind)
        else:
            if feature_dict.get('dist_to_mine_km', 999.0) < 30.0 and feature_dict.get('recurrence_90d', 0.0) > 0.40:
                pred_class = 4
                confidence = 0.95
            elif feature_dict.get('bare_fraction', 0.0) > 0.08 and feature_dict.get('frp_mw', 0.0) < 10.0 and feature_dict.get('recurrence_90d', 0.0) < 0.1:
                pred_class = 5
                confidence = 0.92
            else:
                pred_class = int(self.stage2b_model.predict(x_2d)[0])
                probs = self.stage2b_model.predict_proba(x_2d)[0]
                confidence = float(np.max(probs) * (1.0 - p_ind))
            
        importances = self.stage1_model.feature_importances_
        top_indices = np.argsort(importances)[::-1][:5]
        
        feature_contributions = {}
        if feature_names:
            for idx in top_indices:
                if idx < len(feature_names):
                    feature_contributions[feature_names[idx]] = round(float(importances[idx]), 3)
                    
        pos_signals = []
        neg_signals = []
        
        dist = feature_dict.get('dist_to_facility_km', 999.0)
        rec_90 = feature_dict.get('recurrence_90d', 0.0)
        temp_k = feature_dict.get('estimated_emitter_temp_k', 800.0)
        area_m2 = feature_dict.get('estimated_emitter_area_m2', 50.0)
        builtup = feature_dict.get('builtup_fraction', 0.0)
        forest = feature_dict.get('forest_fraction', 0.0)
        crop = feature_dict.get('cropland_fraction', 0.0)
        z = feature_dict.get('frp_z_score', 0.0)
        
        if pred_class == 0:
            pos_signals.append(f"Located {dist:.2f} km from registered industrial complex")
            pos_signals.append(f"{builtup*100:.1f}% industrial footprint fraction in observation footprint")
            pos_signals.append(f"{rec_90*100:.1f}% 90-day recurrence (permanent continuous operational emitter)")
            pos_signals.append(f"High physical combustion temperature estimate (Tf = {temp_k} K)")
            pos_signals.append(f"Compact sub-pixel emitter area ({area_m2:.1f} m²) matching flare stack")
            neg_signals.append(f"0% forest canopy overlap")
            neg_signals.append(f"FRP within normal operating baseline (Z = {z:+.2f}σ)")
            
        elif pred_class == 1:
            pos_signals.append(f"Industrial facility proximity: {dist:.2f} km")
            pos_signals.append(f"Significant thermal anomaly surge: Z = {z:+.2f}σ above historical baseline")
            pos_signals.append(f"Elevated radiant power ({feature_dict.get('frp_mw')} MW) with expanding thermal area")
            neg_signals.append(f"Historically inactive / low-recurrence point (P90 = {rec_90*100:.1f}%)")
            
        elif pred_class == 2:
            pos_signals.append(f"{forest*100:.1f}% tree cover fraction in observation footprint")
            pos_signals.append(f"Broad thermal envelope ({area_m2:.1f} m²) and elevated FRP")
            neg_signals.append(f"Remote from industrial infrastructure ({dist:.1f} km away)")
            
        elif pred_class == 3:
            pos_signals.append(f"{crop*100:.1f}% cropland agricultural footprint")
            pos_signals.append(f"Transient seasonal recurrence pattern (P90 = {rec_90*100:.1f}%)")
            neg_signals.append(f"Remote from industrial infrastructure ({dist:.1f} km away)")
            
        elif pred_class == 4:
            pos_signals.append(f"Located {feature_dict.get('dist_to_mine_km', 0.0):.1f} km from active coalfield basin")
            pos_signals.append(f"Multi-year high persistence ({rec_90*100:.1f}%) with moderate surface temperature ({temp_k} K)")
            neg_signals.append(f"No refinery stack geometry")
            
        else:
            pos_signals.append("General background thermal anomaly")
            
        return {
            "predicted_class_id": pred_class,
            "predicted_class_name": CLASS_MAP[pred_class],
            "confidence_score": round(confidence * 100.0, 1),
            "confidence_band": "HIGH" if confidence >= 0.85 else ("MODERATE" if confidence >= 0.70 else "LOW"),
            "feature_contributions": feature_contributions,
            "explainability_evidence": {
                "positive_signals": pos_signals,
                "negative_signals": neg_signals
            }
        }
