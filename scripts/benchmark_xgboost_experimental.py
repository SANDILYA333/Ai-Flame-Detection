"""NEXT-EXP-001: XGBoost Experimental Benchmark on Frozen Real Supervised Dataset.

Executes the authoritative scientific evaluation campaign for XGBoost on the exact
frozen benchmark dataset (feat_ds_real_supervised_v1.0.0):
1. Ingests all real observation chunks and authoritative ground-truth reference data.
2. Reconstructs identical 30-feature SupervisedDataset with PERSISTENT_SOURCE_HOLDOUT.
3. Preprocesses features with FeaturePreprocessor fitted strictly on TRAIN.
4. Performs internal validation (5-fold CV) strictly on TRAIN to select optimal conservative hyperparameters.
5. Evaluates XGBoost ONCE on the held-out test partition (271 events).
6. Computes all metrics: Accuracy, Balanced Accuracy, Precision, Recall, Macro F1,
   ROC-AUC, PR-AUC, Brier Score, ECE, Confusion Matrix, Abstention curve, and 95% Bootstrap CIs.
7. Persists experimental model artifact to artifacts/real/experimental/.
8. Saves experimental benchmark report and displays side-by-side comparison table.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from packages.context.ground_truth import GroundTruthIngestionService
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.data.firms.capture import compute_content_hash
from packages.data.firms.schemas import (
    RealDataAcquisitionManifest,
    RealDetectionDataset,
)
from packages.events.pipeline import (
    RealEventConstructionService,
    get_default_calibrated_scientific_config,
)
from packages.feasibility.candidates import get_candidate_study_area
from packages.schemas.common import BoundingBox
from packages.schemas.ml import (
    ModelArtifact,
    ModelMetadata,
    SplitStrategy,
)
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.evaluation.next_007_evaluator import Next007RealModelEvaluator
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.registry import ModelRegistry
from services.ml.models.xgboost_model import XGBoostClassifier
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor


def run_xgboost_benchmark() -> None:
    print("=" * 80)
    print("SIH26162 — PHASE 1: XGBOOST EXPERIMENTAL MODEL IMPLEMENTATION & BENCHMARK")
    print("=" * 80)
    print()

    config = get_default_calibrated_scientific_config()

    # 1. Discover and Load All Acquired Real FIRMS Observations
    raw_root = Path("data/real/raw/firms")
    csv_paths = sorted(raw_root.glob("*/*/*/raw.csv"))

    if not csv_paths:
        raise FileNotFoundError("No raw FIRMS data found in data/real/raw/firms/.")

    print(f"[1/8] Ingesting {len(csv_paths)} observation chunks across all corridors...")
    t_start = time.time()
    all_detections = []
    for p in csv_paths:
        parts = p.parts
        area_id = parts[-4]
        prod = parts[-3]
        sensor = "MODIS" if "MODIS" in prod.upper() else "VIIRS"
        dates = parts[-2].split("_")
        try:
            area = get_candidate_study_area(area_id)
            det_ds = FirmsDataActivationService.activate_from_csv(
                csv_input=p,
                study_area=area,
                requested_start_date=dates[0],
                requested_end_date=dates[1],
                source_product=prod,
                sensor=sensor,
            )
            all_detections.extend(det_ds.detections)
        except Exception as err:
            print(f"  [WARN] Failed activating {p}: {err}")

    seen_ids = set()
    dedup_detections = []
    for d in all_detections:
        if d.detection_id not in seen_ids:
            seen_ids.add(d.detection_id)
            dedup_detections.append(d)

    print(f"      -> Activated {len(dedup_detections)} unique satellite detections ({time.time()-t_start:.1f}s).")

    min_date = (
        min(d.acquired_at.strftime("%Y-%m-%d") for d in dedup_detections)
        if dedup_detections
        else "2026-03-01"
    )
    max_date = (
        max(d.acquired_at.strftime("%Y-%m-%d") for d in dedup_detections)
        if dedup_detections
        else "2026-08-30"
    )

    combined_manifest = RealDataAcquisitionManifest(
        dataset_id="ds_global_real_full",
        source_name="NASA_FIRMS",
        source_product="MULTI_GLOBAL",
        sensor="MULTI",
        study_area_id="global_corridors",
        study_area_name="Global Multi-Corridor Active Coverage",
        requested_start_date=min_date,
        requested_end_date=max_date,
        bounding_box=BoundingBox(
            min_latitude=-60.0,
            min_longitude=-180.0,
            max_latitude=75.0,
            max_longitude=180.0,
        ),
        raw_record_count=len(all_detections),
        valid_record_count=len(dedup_detections),
        canonical_record_count=len(dedup_detections),
        canonical_dataset_hash=compute_content_hash(b"global_real_full_dataset"),
        created_at=datetime.now(UTC),
    )
    combined_det_ds = RealDetectionDataset(
        manifest=combined_manifest,
        detections=dedup_detections,
    )

    print("[2/8] Spatiotemporal clustering into events and tracking persistent sources...")
    t_clust = time.time()
    event_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=combined_det_ds,
        config=config,
    )
    print(
        f"      -> Formed {len(event_ds.events)} physical events and "
        f"{len(event_ds.persistent_sources)} persistent sources ({time.time()-t_clust:.1f}s)."
    )

    print("[3/8] Ingesting ground-truth reference catalog and context features...")
    all_gt_records, gt_hashes = GroundTruthIngestionService.discover_and_load_catalog(
        ["data/real/reference", "fixtures/reference"]
    )
    matched_evidence = GroundTruthIngestionService.match_events_to_ground_truth(
        events=event_ds.events,
        ground_truth_records=all_gt_records,
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )
    sample_cf, sample_hashes = (
        RealContextLabelingService.load_context_features_from_fixture(
            "fixtures/context/context_sample_jamnagar.json"
        )
    )
    facility_features, fac_hashes = (
        GroundTruthIngestionService.load_facility_context_features(
            "data/real/reference/facilities"
        )
    )
    context_features = sample_cf + facility_features
    snapshot_hashes = {**sample_hashes, **fac_hashes, **gt_hashes}

    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=event_ds,
        candidate_features=context_features,
        snapshot_hashes=snapshot_hashes,
        config=config,
        data_status="LIVE_ACQUISITION",
        dataset_id="ds_real_enriched_v1.0.0",
        dataset_version="v1.0.0",
        external_reference_evidence=matched_evidence,
    )

    print("[4/8] Assembling canonical SupervisedDataset with PERSISTENT_SOURCE_HOLDOUT...")
    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=combined_det_ds,
        split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
        target_ids=["target_industrial_segregation"],
    )

    eligible_records = [
        r
        for r in supervised_ds.records
        if "target_industrial_segregation" in r.labels
        and r.labels["target_industrial_segregation"].assigned_class
        in ("industrial", "non_industrial")
    ]
    ind_count = sum(
        1
        for r in eligible_records
        if r.labels["target_industrial_segregation"].assigned_class == "industrial"
    )
    non_ind_count = sum(
        1
        for r in eligible_records
        if r.labels["target_industrial_segregation"].assigned_class == "non_industrial"
    )
    unknown_count = len(supervised_ds.records) - len(eligible_records)

    print(f"      -> Total Physical Events:    {len(supervised_ds.records)}")
    print(f"      -> Eligible Labeled Events:  {len(eligible_records)} (Industrial: {ind_count}, Non-Industrial: {non_ind_count})")
    print(f"      -> Unknown / Excluded:       {unknown_count}")
    print(f"      -> Feature Catalog Version:  {supervised_ds.manifest.feature_set_version}")
    print(f"      -> Dataset SHA-256 Hash:     {supervised_ds.manifest.sha256_hash}")

    # Extract matrices
    (
        x_train_raw,
        y_train,
        ids_train,
        x_val_raw,
        y_val,
        ids_val,
        x_test_raw,
        y_test,
        ids_test,
    ) = DatasetSplitExtractor.extract_split_matrices(
        dataset=supervised_ds,
        target_id="target_industrial_segregation",
    )

    print(f"      -> Partition Split: Train={len(x_train_raw)}, Val={len(x_val_raw)}, Test={len(x_test_raw)}")

    # 5. Fit FeaturePreprocessor STRICTLY on Train
    print("[5/8] Fitting FeaturePreprocessor strictly on TRAIN partition...")
    preprocessor = FeaturePreprocessor()
    preprocessor.fit(x_train_raw)
    x_train_vec = preprocessor.transform(x_train_raw)
    x_val_vec = preprocessor.transform(x_val_raw)
    x_test_vec = preprocessor.transform(x_test_raw)
    feature_names = preprocessor.output_column_names
    print(f"      -> Preprocessor produced {len(feature_names)} float features.")

    # 6. Internal Cross-Validation & Hyperparameter Selection on TRAIN ONLY
    print("[6/8] Executing internal hyperparameter selection strictly on TRAIN (K-Fold CV)...")
    candidate_configs = [
        {"max_depth": 2, "learning_rate": 0.05, "n_estimators": 40, "subsample": 0.8, "colsample_bytree": 0.8, "reg_alpha": 0.1, "reg_lambda": 1.0},
        {"max_depth": 3, "learning_rate": 0.05, "n_estimators": 50, "subsample": 0.8, "colsample_bytree": 0.8, "reg_alpha": 0.1, "reg_lambda": 1.0},
        {"max_depth": 3, "learning_rate": 0.03, "n_estimators": 60, "subsample": 0.8, "colsample_bytree": 0.8, "reg_alpha": 0.05, "reg_lambda": 1.0},
        {"max_depth": 4, "learning_rate": 0.03, "n_estimators": 40, "subsample": 0.8, "colsample_bytree": 0.8, "reg_alpha": 0.2, "reg_lambda": 1.5},
        {"max_depth": 2, "learning_rate": 0.10, "n_estimators": 30, "subsample": 0.8, "colsample_bytree": 0.8, "reg_alpha": 0.1, "reg_lambda": 1.0},
    ]

    # Deterministic 5-fold CV split on train
    n_train = len(x_train_vec)
    k_folds = 5
    rng = np.random.default_rng(seed=42)
    indices = np.arange(n_train)
    rng.shuffle(indices)
    folds = np.array_split(indices, k_folds)

    best_config: dict[str, Any] = candidate_configs[0]
    best_cv_macro_f1 = -1.0

    for cfg in candidate_configs:
        cv_f1s = []
        for k in range(k_folds):
            val_idx = folds[k]
            train_idx = np.concatenate([folds[j] for j in range(k_folds) if j != k])

            x_cv_tr = [x_train_vec[i] for i in train_idx]
            y_cv_tr = [y_train[i] for i in train_idx]
            x_cv_val = [x_train_vec[i] for i in val_idx]
            y_cv_val = [y_train[i] for i in val_idx]

            fold_model = XGBoostClassifier(**cfg, random_seed=42)
            fold_model.fit(x_cv_tr, y_cv_tr, feature_names=feature_names)
            fold_preds = fold_model.predict(x_cv_val)

            per_class = EvaluationHarness.compute_per_class_metrics(
                y_cv_val, fold_preds, fold_model.class_vocabulary
            )
            _, _, macro_f1 = EvaluationHarness.compute_macro_metrics(per_class)
            cv_f1s.append(macro_f1)

        mean_f1 = float(np.mean(cv_f1s))
        print(f"      Config {cfg['max_depth']}d / lr={cfg['learning_rate']} / {cfg['n_estimators']}trees -> CV Macro-F1: {mean_f1:.4f}")
        if mean_f1 > best_cv_macro_f1:
            best_cv_macro_f1 = mean_f1
            best_config = cfg

    print(f"      -> Selected Best Configuration: {best_config} (CV Macro-F1: {best_cv_macro_f1:.4f})")

    # 7. Fit Final XGBoost Model on Full Training Partition
    print("[7/8] Fitting final XGBoost model on full training partition (1,008 samples)...")
    final_model = XGBoostClassifier(**best_config, random_seed=42)
    final_model.fit(x_train_vec, y_train, feature_names=feature_names)

    # 8. Single Frozen Evaluation on Held-Out Test Set (271 samples)
    print("[8/8] Evaluating XGBoost on held-out test partition (271 events)...")
    y_pred = final_model.predict(x_test_vec)
    y_prob = final_model.predict_proba(x_test_vec)
    classes = final_model.class_vocabulary

    per_class = EvaluationHarness.compute_per_class_metrics(y_test, y_pred, classes)
    macro_p, macro_r, macro_f1 = EvaluationHarness.compute_macro_metrics(per_class)
    cm = EvaluationHarness.compute_confusion_matrix(y_test, y_pred, classes)

    pos_cls = "industrial"
    pos_idx = classes.index(pos_cls) if pos_cls in classes else 0
    tp = cm[pos_idx][pos_idx]
    fp = sum(cm[r][pos_idx] for r in range(len(classes)) if r != pos_idx)
    fn = sum(cm[pos_idx][c] for c in range(len(classes)) if c != pos_idx)
    tn = len(y_test) - (tp + fp + fn)

    accuracy = sum(cm[i][i] for i in range(len(classes))) / len(y_test)
    recalls = [float(per_class[c].recall or 0.0) for c in classes if c in per_class and per_class[c].recall is not None]
    balanced_accuracy = sum(recalls) / len(recalls) if recalls else 0.0

    pos_metrics = per_class.get(pos_cls)
    precision = float(pos_metrics.precision or 0.0) if pos_metrics else 0.0
    recall = float(pos_metrics.recall or 0.0) if pos_metrics else 0.0
    f1_score = float(pos_metrics.f1_score or 0.0) if pos_metrics else 0.0

    brier_score = EvaluationHarness.compute_brier_score(y_test, y_prob, class_labels=classes)
    log_loss = EvaluationHarness.compute_log_loss(y_test, y_prob)

    pos_probs = [p.get(pos_cls, 0.5) for p in y_prob]
    y_binary = [1 if y == pos_cls else 0 for y in y_test]

    roc_auc = Next007RealModelEvaluator._compute_roc_auc(y_binary, pos_probs)
    pr_auc = Next007RealModelEvaluator._compute_pr_auc(y_binary, pos_probs)
    ece, cal_bins = Next007RealModelEvaluator._compute_calibration(y_binary, pos_probs)

    abstention_curve = Next007RealModelEvaluator._compute_abstention_curve(
        y_test, y_pred, y_prob, pos_cls
    )

    bootstrap_ci = Next007RealModelEvaluator._compute_bootstrap_ci(
        y_test=y_test,
        y_pred=y_pred,
        y_prob=y_prob,
        classes=classes,
        pos_cls=pos_cls,
        n_rounds=1000,
        seed=42,
    )

    # Event coordinates for geographic stratification
    event_coords = {
        ev.event_id: (ev.centroid_geometry.latitude, ev.centroid_geometry.longitude)
        for ev in event_ds.events
    }
    geo_strat = Next007RealModelEvaluator._compute_geographic_stratification(
        x_test_raw, y_test, y_pred, ids_test, event_coords
    )
    sensor_strat = Next007RealModelEvaluator._compute_sensor_stratification(x_test_raw, y_test, y_pred)
    temp_strat = Next007RealModelEvaluator._compute_temporal_stratification(x_test_raw, y_test, y_pred)

    top_features = final_model.get_feature_importances(feature_names)
    sorted_features = sorted(top_features.items(), key=lambda x: x[1], reverse=True)[:10]

    # Persist experimental model artifact
    exp_dir = Path("artifacts/real/experimental")
    exp_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)

    model_id = f"real_xgboostclassifier_target_industrial_segregation_{supervised_ds.manifest.dataset_version}"
    meta = ModelMetadata(
        model_id=model_id,
        model_type="XGBoostClassifier",
        model_version="v1.0.0-experimental",
        model_family="GradientBoostedTrees",
        target_id="target_industrial_segregation",
        target_version="target_v1.0.0",
        dataset_id=supervised_ds.manifest.dataset_id,
        dataset_version=supervised_ds.manifest.dataset_version,
        dataset_hash=supervised_ds.manifest.sha256_hash,
        feature_set_version=supervised_ds.manifest.feature_set_version,
        label_set_version=supervised_ds.manifest.label_set_version,
        split_strategy=supervised_ds.split_manifest.split_strategy.value,
        split_version=supervised_ds.split_manifest.split_strategy.value,
        random_seed=42,
        hyperparameters=best_config,
        training_timestamp=now,
        train_record_count=len(x_train_raw),
        feature_names=feature_names,
        feature_dimensionality=len(feature_names),
        validation_metrics={
            "cv_macro_f1": best_cv_macro_f1,
            "cv_folds": 5,
        },
        test_metrics={
            "accuracy": accuracy,
            "balanced_accuracy": balanced_accuracy,
            "precision": precision,
            "recall": recall,
            "macro_f1": macro_f1,
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "brier_score": brier_score,
            "expected_calibration_error": ece,
            "test_samples": len(x_test_raw),
        },
    )

    raw_artifact = ModelArtifact(
        metadata=meta,
        preprocessor_state=preprocessor.to_dict(),
        model_parameters=final_model.get_parameters(),
        class_vocabulary=final_model.class_vocabulary,
    )
    content_hash = raw_artifact.compute_content_hash()
    artifact = raw_artifact.model_copy(
        update={
            "sha256_hash": content_hash,
            "metadata": meta.model_copy(update={"artifact_hash": content_hash}),
        }
    )

    artifact_path = exp_dir / f"{model_id}.json"
    ModelRegistry.save_to_file(artifact, artifact_path)
    print(f"\n[OK] Experimental artifact saved to: {artifact_path}")
    print(f"     SHA-256 Digest: {content_hash}")

    # Build evaluation report dict
    report_dict: dict[str, Any] = {
        "model_id": model_id,
        "model_type": "XGBoostClassifier",
        "model_role": "Phase 1 Experimental Candidate (Gradient Boosted Trees)",
        "model_version": "v1.0.0-experimental",
        "artifact_path": str(artifact_path),
        "artifact_hash": content_hash,
        "train_samples": len(x_train_raw),
        "val_samples": len(x_val_raw),
        "test_samples": len(x_test_raw),
        "positive_class": pos_cls,
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "macro_f1": macro_f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "brier_score": brier_score,
        "log_loss": log_loss,
        "expected_calibration_error": ece,
        "confidence_intervals": {k: list(v) for k, v in bootstrap_ci.items()},
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "positive_class": pos_cls,
        },
        "per_class_metrics": {
            k: {
                "class_name": v.class_name,
                "true_positives": v.true_positives,
                "false_positives": v.false_positives,
                "false_negatives": v.false_negatives,
                "true_negatives": v.true_negatives,
                "support": v.support,
                "precision": v.precision,
                "recall": v.recall,
                "f1_score": v.f1_score,
            }
            for k, v in per_class.items()
        },
        "top_features_by_gain": dict(sorted_features),
        "abstention_curve": [asdict(a) for a in abstention_curve],
        "calibration_bins": [asdict(b) for b in cal_bins],
        "geographic_stratification": [asdict(s) for s in geo_strat],
        "sensor_stratification": [asdict(s) for s in sensor_strat],
        "temporal_stratification": [asdict(s) for s in temp_strat],
    }

    # Evaluate all existing production baselines on this EXACT same held-out test partition
    print("\nEvaluating all production models on the identical test partition for exact head-to-head comparison...")
    prod_path = Path("artifacts/real/production")
    model_roles = {
        "MajorityClassClassifier": "B0 Baseline (Majority Class)",
        "DeterministicContextualClassifier": "B2 Reference (Deterministic)",
        "LogisticRegressionClassifier": "B3 Candidate (Softmax Linear)",
        "DecisionTreeClassifier": "B4-DT Candidate (CART Decision Tree)",
        "RandomForestClassifier": "B4-RF Candidate (Random Forest)",
    }

    paired_comparison: list[dict[str, Any]] = []
    for m_type, m_role in model_roles.items():
        p_file = prod_path / f"real_{m_type.lower()}_target_industrial_segregation_v1.0.0.json"
        if not p_file.exists():
            continue
        p_art = ModelRegistry.load_from_file(p_file)
        p_prep, p_inst = ModelRegistry.reconstruct_pipeline(p_art)
        if m_type == "DeterministicContextualClassifier":
            p_pred = p_inst.predict(x_test_raw)
            p_prob = p_inst.predict_proba(x_test_raw)
        else:
            p_test_vec = p_prep.transform(x_test_raw)
            p_pred = p_inst.predict(p_test_vec)
            p_prob = p_inst.predict_proba(p_test_vec)

        p_classes = sorted(set(y_test) | set(p_pred))
        p_per_class = EvaluationHarness.compute_per_class_metrics(y_test, p_pred, p_classes)
        _, _, p_macro_f1 = EvaluationHarness.compute_macro_metrics(p_per_class)
        p_cm = EvaluationHarness.compute_confusion_matrix(y_test, p_pred, p_classes)
        p_acc = sum(p_cm[i][i] for i in range(len(p_classes))) / len(y_test)
        p_recalls = [float(p_per_class[c].recall or 0.0) for c in p_classes if c in p_per_class and p_per_class[c].recall is not None]
        p_bal_acc = sum(p_recalls) / len(p_recalls) if p_recalls else 0.0
        p_pos = p_per_class.get(pos_cls)
        p_prec = float(p_pos.precision or 0.0) if p_pos else 0.0
        p_rec = float(p_pos.recall or 0.0) if p_pos else 0.0

        p_brier = None
        p_roc_auc = None
        p_pr_auc = None
        p_ece = None
        if p_prob and len(p_prob) == len(y_test):
            p_brier = EvaluationHarness.compute_brier_score(y_test, p_prob, class_labels=p_classes)
            p_pos_probs = [p.get(pos_cls, 0.5) for p in p_prob]
            p_roc_auc = Next007RealModelEvaluator._compute_roc_auc(y_binary, p_pos_probs)
            p_pr_auc = Next007RealModelEvaluator._compute_pr_auc(y_binary, p_pos_probs)
            p_ece, _ = Next007RealModelEvaluator._compute_calibration(y_binary, p_pos_probs)

        p_ci = Next007RealModelEvaluator._compute_bootstrap_ci(
            y_test=y_test, y_pred=p_pred, y_prob=p_prob, classes=p_classes, pos_cls=pos_cls, n_rounds=500, seed=42
        )
        p_ci_f1 = p_ci.get("macro_f1", (0.0, 0.0))

        paired_comparison.append(
            {
                "model_type": m_type,
                "role": m_role,
                "accuracy": round(p_acc, 4),
                "balanced_accuracy": round(p_bal_acc, 4),
                "precision": round(p_prec, 4),
                "recall": round(p_rec, 4),
                "macro_f1": round(p_macro_f1, 4),
                "roc_auc": round(p_roc_auc, 4) if p_roc_auc is not None else "N/A",
                "pr_auc": round(p_pr_auc, 4) if p_pr_auc is not None else "N/A",
                "brier_score": round(p_brier, 4) if p_brier is not None else "N/A",
                "ece": round(p_ece, 4) if p_ece is not None else "N/A",
                "ci_95_macro_f1": f"[{p_ci_f1[0]:.3f}, {p_ci_f1[1]:.3f}]",
            }
        )

    # Append XGBoost to paired comparison
    xgb_row = {
        "model_type": "XGBoostClassifier",
        "role": "Phase 1 Experimental Candidate (XGBoost)",
        "accuracy": round(accuracy, 4),
        "balanced_accuracy": round(balanced_accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "macro_f1": round(macro_f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else "N/A",
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else "N/A",
        "brier_score": round(brier_score, 4) if brier_score is not None else "N/A",
        "ece": round(ece, 4) if ece is not None else "N/A",
        "ci_95_macro_f1": f"[{bootstrap_ci['macro_f1'][0]:.3f}, {bootstrap_ci['macro_f1'][1]:.3f}]",
    }
    paired_comparison.append(xgb_row)

    report_dict["paired_comparison_table"] = paired_comparison

    # Load existing historical benchmark report
    prod_eval_file = Path("artifacts/real/evaluation/real_model_evaluation_report.json")
    historical_comparison = []
    if prod_eval_file.exists():
        prod_eval_data = json.loads(prod_eval_file.read_text(encoding="utf-8"))
        historical_comparison = prod_eval_data.get("model_comparison_table", [])
    report_dict["historical_next007_comparison"] = historical_comparison

    report_file = exp_dir / "xgboost_benchmark_report.json"
    report_file.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
    print(f"[OK] Benchmark report saved to: {report_file}")

    # Print Final Comparison Table
    print("\n" + "=" * 115)
    print(f"PAIRED BENCHMARK COMPARISON TABLE (N={len(x_test_raw)} Held-Out Test Events Under PERSISTENT_SOURCE_HOLDOUT)")
    print("=" * 115)
    header = (
        f"{'Model Architecture':<32} | {'Accuracy':<8} | {'Bal Acc':<8} | "
        f"{'Precision':<9} | {'Recall':<8} | {'Macro F1':<8} | {'ROC-AUC':<8} | {'PR-AUC':<8} | {'ECE':<8}"
    )
    print(header)
    print("-" * 115)

    for row in paired_comparison:
        m_name = row.get("model_type", "Unknown")
        acc = f"{row.get('accuracy', 0)*100:.2f}%"
        b_acc = f"{row.get('balanced_accuracy', 0)*100:.2f}%"
        prec = f"{row.get('precision', 0)*100:.2f}%"
        rec = f"{row.get('recall', 0)*100:.2f}%"
        mf1 = f"{row.get('macro_f1', 0)*100:.2f}%"
        rauc = f"{row.get('roc_auc', 'N/A')}"
        prauc = f"{row.get('pr_auc', 'N/A')}"
        ece_val = f"{row.get('ece', 'N/A')}"
        print(
            f"{m_name:<32} | {acc:<8} | {b_acc:<8} | {prec:<9} | {rec:<8} | {mf1:<8} | {rauc:<8} | {prauc:<8} | {ece_val:<8}"
        )

    print("=" * 115)
    print(f"\nConfusion Matrix for XGBoost (Test N={len(x_test_raw)}):")
    print(f"                      Predicted Industrial    Predicted Non-Industrial")
    print(f"True Industrial:             TP={tp:<17} FN={fn:<17}")
    print(f"True Non-Industrial:         FP={fp:<17} TN={tn:<17}")
    print()


if __name__ == "__main__":
    run_xgboost_benchmark()
