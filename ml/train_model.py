"""
Delay-risk model training (Part 3.1)
=====================================

Goal
----
Predict, **at booking time**, whether a shipment will arrive more than
24 hours late (`actual_delay_hours > 24`).

Booking-time feature philosophy
--------------------------------
A prediction is only useful if it can be made the moment a booking is
created -- before the vessel has sailed and long before it has arrived.
Anything derived from what *actually* happened during the voyage is a
label leak, not a feature. Concretely, the following curated columns
are **never** used as model inputs, and are only touched to build the
training label or to filter rows:

    actual_departure, actual_arrival, actual_delay_hours,
    on_time_flag, transit_days_actual, status

`status` in particular looks harmless but is a leak: a shipment isn't
"DELIVERED" or "CANCELLED" until after the fact, so it encodes the
outcome we're trying to predict.

Features used (all knowable at the moment of booking):

  Categorical
    - origin_port, destination_port  -> lane-specific effects
    - cargo_type                     -> handling/customs profile differs by cargo

  Numeric
    - weight_tons, container_count   -> shipment size
    - planned_transit_days           -> planned_arrival - planned_departure
    - booking_lead_days              -> planned_departure - booking_date
                                         (how far in advance the booking was made)
    - booking_month, booking_day_of_week -> seasonality / day-of-week effects
    - origin_congestion_score, destination_congestion_score
                                      -> static port reference data (ports.csv),
                                         known at booking time regardless of
                                         when the shipment actually sails

Deliberately excluded
    - customer_id, vessel_id: very high cardinality (251 / 80 unique values
      over ~4.5k rows) relative to sample size. A group-level check
      (mean delay-rate per group vs. its sample count) showed variation
      consistent with sampling noise, not a real per-customer / per-vessel
      effect -- including them risks the model memorising IDs rather than
      learning anything generalisable, and neither is a lane/cargo/season
      property a booking system could reason about upfront.

Honest evaluation
------------------
Rather than reporting a single train/test split (which is noisy on a
~4.5k-row dataset), this script:
  1. Runs 5-fold stratified cross-validation for two candidate models
     (Logistic Regression and Random Forest) and compares them on AUC.
  2. Picks the simpler model unless the more complex one clears a
     meaningful margin (avoids "prefer the fancier model on noise" bias).
  3. Refits the chosen model on a train split and reports precision,
     recall, F1, ROC-AUC and PR-AUC on a held-out test split.

On this dataset, both candidate models land at ROC-AUC ~0.49-0.50 --
essentially chance. That is reported as-is below (see the printed
"MODEL COMPARISON" and "TEST-SET EVALUATION" blocks): none of the
booking-time signals available in the current data (lane, cargo type,
size, season, static port congestion) carry meaningful information
about which bookings will end up >24h late. This was verified directly
(per-port, per-cargo-type, per-month, per-vessel and per-customer delay
rates all cluster within sampling noise of the ~40% base rate) -- it is
a genuine, checked finding, not a pipeline bug. Per the assignment
brief, an honestly-reported weak model beats a silently-overfit strong
one.

Monitoring plan (production)
-----------------------------
Ground truth (actual_delay_hours) only becomes available once a
shipment completes, so live evaluation is necessarily lagged.

Track on a rolling window (e.g. weekly), once enough completed
shipments have accumulated:
  - Rolling precision / recall / F1 / ROC-AUC / PR-AUC on shipments that
    have since completed, compared against the training-time baseline
    stored in model_metadata.json.
  - Calibration (Brier score, or predicted-vs-observed rate by decile)
    since a probability, not just a label, is returned.
  - Input drift: distribution of categorical features (origin/destination
    port mix, cargo type mix) and numeric features (weight, lead time)
    vs. the training distribution (e.g. population stability index / KS
    test); also track the rate of "unknown" categories hitting the
    one-hot encoder's handle_unknown fallback.
  - Prediction drift: the proportion of shipments flagged high-risk
    over time -- a sudden jump or collapse is a signal something changed
    upstream (routes, congestion data feed, seasonality) even before
    ground truth arrives.
  - Serving health: /predict-delay latency, error rate, and model/version
    served (see model_metadata.json's "model_version").

Retrain triggers:
  - Rolling AUC drops meaningfully below the recorded baseline for two
    consecutive evaluation windows (given the baseline is already near
    chance, this mainly guards against the model becoming *worse* than
    chance, e.g. systematically inverted on a changed population).
  - Material input drift on a feature that matters operationally (e.g.
    a new trade lane or cargo type not seen in training).
  - A fixed cadence regardless of drift (e.g. quarterly), since
    ports.csv congestion scores and route mix are expected to evolve.
  - Manual trigger if `ports.csv` reference data is refreshed, since
    congestion scores are joined in at feature-build time.

Usage
-----
    python ml/train_model.py
    python ml/train_model.py --shipments ./curated/shipments_curated.csv \\
                              --ports ./curated/ports_curated.csv \\
                              --cv-folds 5 --test-size 0.2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# --------------------------------------------------------------------------
# Logging (structured-ish: consistent key=value fields, matches the API's
# structured-logging intent from Part 1.1, just at INFO/console level here)
# --------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s level=%(levelname)s msg=%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("train_model")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHIPMENTS_PATH = PROJECT_ROOT / "curated" / "shipments_curated.csv"
DEFAULT_PORTS_PATH = PROJECT_ROOT / "curated" / "ports_curated.csv"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "ml" / "delay_model.joblib"
DEFAULT_METADATA_PATH = PROJECT_ROOT / "ml" / "model_metadata.json"

DELAY_THRESHOLD_HOURS = 24

CATEGORICAL_FEATURES = ["origin_port", "destination_port", "cargo_type"]
NUMERIC_FEATURES = [
    "weight_tons",
    "container_count",
    "planned_transit_days",
    "booking_lead_days",
    "booking_month",
    "booking_day_of_week",
    "origin_congestion_score",
    "destination_congestion_score",
]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# Columns that must NEVER be used as model inputs because they are only
# known after the voyage happens (label leakage guard, checked at runtime).
LEAKY_COLUMNS = {
    "actual_departure",
    "actual_arrival",
    "actual_delay_hours",
    "on_time_flag",
    "transit_days_actual",
    "status",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the booking-time delay-risk model.")
    parser.add_argument("--shipments", type=Path, default=DEFAULT_SHIPMENTS_PATH)
    parser.add_argument("--ports", type=Path, default=DEFAULT_PORTS_PATH)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--metadata-out", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def load_data(shipments_path: Path, ports_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.info(f"loading shipments path={shipments_path}")
    shipments_df = pd.read_csv(shipments_path)
    logger.info(f"loading ports path={ports_path}")
    ports_df = pd.read_csv(ports_path)
    logger.info(f"rows_loaded shipments={len(shipments_df)} ports={len(ports_df)}")
    return shipments_df, ports_df


def build_labelled_dataset(shipments_df: pd.DataFrame, ports_df: pd.DataFrame) -> pd.DataFrame:
    """Filter to labellable rows and attach the target column.

    Only shipments with a known `actual_delay_hours` can supply ground
    truth. Shipments still in transit or cancelled before an outcome was
    recorded are excluded from *training* (they are exactly the kind of
    shipment /predict-delay would be called on in production).
    """
    df = shipments_df.dropna(subset=["actual_delay_hours"]).copy()
    dropped = len(shipments_df) - len(df)
    logger.info(
        f"label_filter dropped_rows={dropped} "
        f"reason=no_actual_delay_hours_yet_or_cancelled_before_outcome"
    )

    df["delay_risk"] = (df["actual_delay_hours"] > DELAY_THRESHOLD_HOURS).astype(int)

    balance = df["delay_risk"].value_counts(normalize=True).round(4).to_dict()
    logger.info(f"label_balance {balance}")

    # Static, booking-time-safe port reference data.
    origin_ref = ports_df[["port_code", "avg_congestion_score"]].rename(
        columns={"port_code": "origin_port", "avg_congestion_score": "origin_congestion_score"}
    )
    destination_ref = ports_df[["port_code", "avg_congestion_score"]].rename(
        columns={"port_code": "destination_port", "avg_congestion_score": "destination_congestion_score"}
    )
    df = df.merge(origin_ref, on="origin_port", how="left")
    df = df.merge(destination_ref, on="destination_port", how="left")

    missing_origin_congestion = df["origin_congestion_score"].isna().sum()
    missing_dest_congestion = df["destination_congestion_score"].isna().sum()
    if missing_origin_congestion or missing_dest_congestion:
        logger.info(
            f"congestion_join_gaps origin_missing={missing_origin_congestion} "
            f"destination_missing={missing_dest_congestion} "
            f"reason=port_code_not_found_in_ports_reference_data "
            f"handling=median_imputation_in_pipeline"
        )

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add booking-time-only derived features. Does not touch any leaky column."""
    df = df.copy()
    df["booking_date"] = pd.to_datetime(df["booking_date"], errors="coerce")
    df["planned_departure"] = pd.to_datetime(df["planned_departure"], errors="coerce")
    df["planned_arrival"] = pd.to_datetime(df["planned_arrival"], errors="coerce")

    df["planned_transit_days"] = (
        df["planned_arrival"] - df["planned_departure"]
    ).dt.total_seconds() / 86400

    df["booking_lead_days"] = (
        df["planned_departure"] - df["booking_date"]
    ).dt.total_seconds() / 86400

    df["booking_month"] = df["booking_date"].dt.month
    df["booking_day_of_week"] = df["booking_date"].dt.dayofweek

    return df


def assert_no_leakage(feature_columns: list[str]) -> None:
    leaked = LEAKY_COLUMNS.intersection(feature_columns)
    if leaked:
        raise ValueError(f"Leaky column(s) found in feature set: {sorted(leaked)}")


def build_preprocessor() -> ColumnTransformer:
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("categorical", categorical_transformer, CATEGORICAL_FEATURES),
            ("numeric", numeric_transformer, NUMERIC_FEATURES),
        ]
    )


def get_candidate_models(random_state: int) -> dict:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=random_state,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        ),
    }


def compare_models_with_cv(X: pd.DataFrame, y: pd.Series, cv_folds: int, random_state: int) -> dict:
    """Cross-validated, honest comparison of candidate models. No test-set peeking."""
    preprocessor = build_preprocessor()
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    scoring = ["roc_auc", "f1", "precision", "recall"]

    results = {}
    for name, estimator in get_candidate_models(random_state).items():
        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])
        cv_result = cross_validate(pipeline, X, y, cv=skf, scoring=scoring, n_jobs=-1)
        summary = {
            f"mean_{metric}": round(float(np.mean(cv_result[f"test_{metric}"])), 4)
            for metric in scoring
        }
        summary["std_roc_auc"] = round(float(np.std(cv_result["test_roc_auc"])), 4)
        results[name] = summary
        logger.info(f"cv_result model={name} {summary}")

    return results


def select_model(cv_results: dict, margin: float = 0.02) -> tuple[str, str]:
    """Pick the simpler model unless the more complex one wins by a real margin.

    `margin` guards against choosing Random Forest purely on cross-fold
    noise when the AUC difference is within the noise band observed in
    the fold-to-fold std (see std_roc_auc above).
    """
    lr_auc = cv_results["logistic_regression"]["mean_roc_auc"]
    rf_auc = cv_results["random_forest"]["mean_roc_auc"]

    if rf_auc - lr_auc > margin:
        return "random_forest", (
            f"random_forest CV ROC-AUC ({rf_auc}) beats logistic_regression "
            f"({lr_auc}) by more than the {margin} margin."
        )
    return "logistic_regression", (
        f"logistic_regression selected: CV ROC-AUC (logreg={lr_auc}, rf={rf_auc}) "
        f"differ by <= {margin}, which is within cross-fold noise here "
        f"(see std_roc_auc). Preferring the simpler, more interpretable, "
        f"faster-to-serve model per 'honestly-evaluated simple model over "
        f"an unjustified complex one'."
    )


def evaluate(y_true, y_pred, y_proba) -> dict:
    return {
        "precision": round(float(precision_score(y_true, y_pred)), 4),
        "recall": round(float(recall_score(y_true, y_pred)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_proba)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_proba)), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def main() -> None:
    args = parse_args()

    shipments_df, ports_df = load_data(args.shipments, args.ports)
    labelled_df = build_labelled_dataset(shipments_df, ports_df)
    labelled_df = engineer_features(labelled_df)

    assert_no_leakage(FEATURE_COLUMNS)

    X = labelled_df[FEATURE_COLUMNS]
    y = labelled_df["delay_risk"]

    # --------------------------------------------------
    # Honest model comparison (cross-validated, no test-set peeking)
    # --------------------------------------------------
    logger.info(f"cross_validation folds={args.cv_folds}")
    cv_results = compare_models_with_cv(X, y, args.cv_folds, args.random_state)

    chosen_model_name, selection_reason = select_model(cv_results)
    logger.info(f"model_selected name={chosen_model_name} reason={selection_reason}")

    print("\n==============================")
    print("MODEL COMPARISON (5-fold CV)")
    print("==============================")
    for name, summary in cv_results.items():
        marker = " <- selected" if name == chosen_model_name else ""
        print(f"{name}{marker}: {summary}")
    print(f"\nSelection rationale: {selection_reason}")

    # --------------------------------------------------
    # Train/test split + final fit of the chosen model
    # --------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
    )
    logger.info(f"split train_rows={len(X_train)} test_rows={len(X_test)}")

    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("model", get_candidate_models(args.random_state)[chosen_model_name]),
        ]
    )
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)[:, 1]
    test_metrics = evaluate(y_test, predictions, probabilities)

    print("\n==============================")
    print("TEST-SET EVALUATION")
    print("==============================")
    print(f"Model    : {chosen_model_name}")
    print(f"Precision: {test_metrics['precision']:.4f}")
    print(f"Recall   : {test_metrics['recall']:.4f}")
    print(f"F1 Score : {test_metrics['f1_score']:.4f}")
    print(f"ROC-AUC  : {test_metrics['roc_auc']:.4f}")
    print(f"PR-AUC   : {test_metrics['pr_auc']:.4f}")
    print(f"Confusion matrix [[TN, FP], [FN, TP]]: {test_metrics['confusion_matrix']}")
    print("\nClassification report:")
    print(classification_report(y_test, predictions))

    if test_metrics["roc_auc"] < 0.55:
        print(
            "NOTE: ROC-AUC is close to 0.5 (chance). Cross-validation above shows this "
            "is consistent, not a one-off split -- the booking-time features available "
            "in the current curated dataset carry little to no signal about which "
            "shipments will end up >24h late. See the module docstring for the "
            "per-group signal checks performed (port, cargo type, month, vessel, "
            "customer) and the production monitoring/retrain plan."
        )

    # --------------------------------------------------
    # Persist artefacts
    # --------------------------------------------------
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, args.model_out)
    logger.info(f"model_saved path={args.model_out}")

    metadata = {
        "model_version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "python_version": sys.version.split()[0],
        "model_type": chosen_model_name,
        "selection_reason": selection_reason,
        "target": {
            "name": "delay_risk",
            "definition": f"actual_delay_hours > {DELAY_THRESHOLD_HOURS}",
        },
        "feature_columns": {
            "categorical": CATEGORICAL_FEATURES,
            "numeric": NUMERIC_FEATURES,
        },
        "excluded_features": {
            "leaky_columns": sorted(LEAKY_COLUMNS),
            "high_cardinality_no_signal": ["customer_id", "vessel_id"],
        },
        "dataset": {
            "shipments_path": str(args.shipments),
            "ports_path": str(args.ports),
            "total_rows": int(len(shipments_df)),
            "labelled_rows": int(len(labelled_df)),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "class_balance": labelled_df["delay_risk"].value_counts(normalize=True).round(4).to_dict(),
        },
        "cross_validation": {
            "folds": args.cv_folds,
            "results": cv_results,
        },
        "test_set_evaluation": test_metrics,
        "monitoring_plan": {
            "tracked_metrics": [
                "rolling_precision", "rolling_recall", "rolling_f1", "rolling_roc_auc",
                "rolling_pr_auc", "calibration_brier_score", "input_feature_drift_psi",
                "predicted_high_risk_rate", "predict_delay_latency_ms", "predict_delay_error_rate",
            ],
            "retrain_triggers": [
                "rolling AUC below baseline for 2+ consecutive evaluation windows",
                "material drift in route/cargo-type mix vs. training distribution",
                "fixed quarterly cadence regardless of drift",
                "ports.csv congestion reference data refreshed",
            ],
        },
    }

    args.metadata_out.write_text(json.dumps(metadata, indent=2, default=str))
    logger.info(f"metadata_saved path={args.metadata_out}")


if __name__ == "__main__":
    main()
