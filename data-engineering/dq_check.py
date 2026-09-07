import argparse
import json
from pathlib import Path

import pandas as pd


# =========================================================
# COMMON HELPER
# =========================================================

def create_result(
        check_name,
        rows_affected,
        total_rows,
        severity,
        recommended_action
):
    """
    Creates one standardized Data Quality result.
    """

    percentage = 0.0

    if total_rows > 0:
        percentage = round(
            (rows_affected / total_rows) * 100,
            2
        )

    return {
        "check_name": check_name,
        "rows_affected": int(rows_affected),
        "percentage": percentage,
        "severity": severity,
        "recommended_action": recommended_action
    }


# =========================================================
# 1. DUPLICATE ROW CHECK
# =========================================================

def check_duplicate_rows(df):

    duplicate_mask = df.duplicated(
        keep=False
    )

    rows_affected = duplicate_mask.sum()

    return create_result(
        check_name="duplicate_rows",
        rows_affected=rows_affected,
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Remove exact duplicate rows after verifying "
            "that they are accidental duplicates."
        )
    )


# =========================================================
# 2. DUPLICATE SHIPMENT ID CHECK
# =========================================================

def check_duplicate_shipment_ids(df):

    duplicate_mask = df[
        "shipment_id"
    ].duplicated(
        keep=False
    )

    rows_affected = duplicate_mask.sum()

    return create_result(
        check_name="duplicate_shipment_ids",
        rows_affected=rows_affected,
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Shipment ID should uniquely identify a shipment. "
            "Investigate duplicates and keep only the correct record."
        )
    )


# =========================================================
# 3. MISSING SHIPMENT ID
# =========================================================

def check_missing_shipment_id(df):

    mask = (
        df["shipment_id"].isna()
        |
        (
            df["shipment_id"]
            .astype("string")
            .str.strip()
            == ""
        )
    )

    return create_result(
        check_name="missing_shipment_id",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Quarantine records without a shipment ID "
            "because shipment_id is the primary business identifier."
        )
    )


# =========================================================
# 4. MISSING CARGO TYPE
# =========================================================

def check_missing_cargo_type(df):

    rows_affected = df[
        "cargo_type"
    ].isna().sum()

    return create_result(
        check_name="missing_cargo_type",
        rows_affected=rows_affected,
        total_rows=len(df),
        severity="warning",
        recommended_action=(
            "Flag missing cargo type values. "
            "Do not infer cargo type unless a trustworthy source exists."
        )
    )


# =========================================================
# 5. MISSING WEIGHT
# =========================================================

def check_missing_weight(df):

    rows_affected = df[
        "weight_tons"
    ].isna().sum()

    return create_result(
        check_name="missing_weight_tons",
        rows_affected=rows_affected,
        total_rows=len(df),
        severity="warning",
        recommended_action=(
            "Flag shipments with missing weight. "
            "Keep as null unless the value can be reliably recovered."
        )
    )


# =========================================================
# 6. NEGATIVE WEIGHT
# =========================================================

def check_negative_weight(df):

    weight = pd.to_numeric(
        df["weight_tons"],
        errors="coerce"
    )

    mask = weight < 0

    return create_result(
        check_name="negative_weight_tons",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Negative shipment weight is physically invalid. "
            "Quarantine or correct affected records."
        )
    )


# =========================================================
# 7. ZERO / INVALID CONTAINER COUNT
# =========================================================

def check_zero_container_count(df):

    container_count = pd.to_numeric(
        df["container_count"],
        errors="coerce"
    )

    mask = container_count == 0

    return create_result(
        check_name="zero_container_count",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="warning",
        recommended_action=(
            "Review shipments with zero containers. "
            "They may represent invalid or incomplete booking data."
        )
    )


def check_negative_container_count(df):

    container_count = pd.to_numeric(
        df["container_count"],
        errors="coerce"
    )

    mask = container_count < 0

    return create_result(
        check_name="negative_container_count",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Container count cannot be negative. "
            "Correct or quarantine affected records."
        )
    )


# =========================================================
# 8. MISSING STATUS
# =========================================================

def check_missing_status(df):

    mask = (
        df["status"].isna()
        |
        (
            df["status"]
            .astype("string")
            .str.strip()
            == ""
        )
    )

    return create_result(
        check_name="missing_status",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="warning",
        recommended_action=(
            "Flag records with missing shipment status. "
            "Do not guess a status from unrelated fields."
        )
    )


# =========================================================
# 9. INCONSISTENT STATUS VALUES
# =========================================================

def check_inconsistent_status(df):

    """
    The dominant canonical values in the supplied dataset are:

    DELIVERED
    DELAYED
    CANCELLED

    Other observed values such as:
    delivered
    COMPLETED
    Complete

    are treated as inconsistent.
    """

    valid_statuses = {
        "DELIVERED",
        "DELAYED",
        "CANCELLED"
    }

    status = (
        df["status"]
        .astype("string")
        .str.strip()
    )

    mask = (
        status.notna()
        &
        ~status.isin(valid_statuses)
    )

    return create_result(
        check_name="inconsistent_status_values",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="warning",
        recommended_action=(
            "Standardize status values to a canonical vocabulary. "
            "For example normalize case and investigate whether "
            "'COMPLETED'/'Complete' should map to DELIVERED."
        )
    )


# =========================================================
# 10. CARGO TYPE FORMATTING
# =========================================================

def check_inconsistent_cargo_type_formatting(df):

    """
    Detects cargo values where case or surrounding spaces
    differ from their normalized form.

    Examples from the supplied dataset include:
        FURNITURE
        electronics
         Chemicals
        machinery
    """

    cargo = df[
        "cargo_type"
    ].astype("string")

    normalized = (
        cargo
        .str.strip()
        .str.lower()
    )

    canonical_map = (
        df.loc[
            df["cargo_type"].notna(),
            ["cargo_type"]
        ]
        .assign(
            normalized=lambda x:
            x["cargo_type"]
            .astype(str)
            .str.strip()
            .str.lower()
        )
    )

    counts = (
        canonical_map
        .groupby("normalized")["cargo_type"]
        .nunique()
    )

    inconsistent_normalized_values = set(
        counts[
            counts > 1
        ].index
    )

    mask = normalized.isin(
        inconsistent_normalized_values
    )

    return create_result(
        check_name="inconsistent_cargo_type_formatting",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="warning",
        recommended_action=(
            "Normalize cargo types by trimming whitespace "
            "and applying consistent capitalization."
        )
    )


# =========================================================
# DATE HELPERS
# =========================================================

DATE_COLUMNS = [
    "booking_date",
    "planned_departure",
    "actual_departure",
    "planned_arrival",
    "actual_arrival"
]


def parse_date_column(df, column):

    return pd.to_datetime(
        df[column],
        errors="coerce"
    )


# =========================================================
# 11. INVALID DATE FORMATS
# =========================================================

def check_invalid_date_format(df, column):

    original = df[column]

    converted = parse_date_column(
        df,
        column
    )

    mask = (
        original.notna()
        &
        converted.isna()
    )

    return create_result(
        check_name=f"invalid_date_format_{column}",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            f"Correct or quarantine values in '{column}' "
            "that cannot be parsed as timestamps."
        )
    )


# =========================================================
# 12. PLANNED DEPARTURE BEFORE BOOKING
# =========================================================

def check_planned_departure_before_booking(df):

    booking = parse_date_column(
        df,
        "booking_date"
    )

    planned_departure = parse_date_column(
        df,
        "planned_departure"
    )

    mask = (
        booking.notna()
        &
        planned_departure.notna()
        &
        (
            planned_departure
            < booking
        )
    )

    return create_result(
        check_name="planned_departure_before_booking",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Planned departure should not occur before "
            "the shipment booking date."
        )
    )


# =========================================================
# 13. ACTUAL DEPARTURE BEFORE BOOKING
# =========================================================

def check_actual_departure_before_booking(df):

    booking = parse_date_column(
        df,
        "booking_date"
    )

    actual_departure = parse_date_column(
        df,
        "actual_departure"
    )

    mask = (
        booking.notna()
        &
        actual_departure.notna()
        &
        (
            actual_departure
            < booking
        )
    )

    return create_result(
        check_name="actual_departure_before_booking",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Actual departure occurring before booking "
            "is chronologically inconsistent. Investigate "
            "and correct or quarantine the affected rows."
        )
    )


# =========================================================
# 14. PLANNED ARRIVAL BEFORE PLANNED DEPARTURE
# =========================================================

def check_planned_arrival_before_departure(df):

    departure = parse_date_column(
        df,
        "planned_departure"
    )

    arrival = parse_date_column(
        df,
        "planned_arrival"
    )

    mask = (
        departure.notna()
        &
        arrival.notna()
        &
        (
            arrival
            < departure
        )
    )

    return create_result(
        check_name="planned_arrival_before_planned_departure",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Planned arrival cannot occur before planned departure."
        )
    )


# =========================================================
# 15. ACTUAL ARRIVAL BEFORE ACTUAL DEPARTURE
# =========================================================

def check_actual_arrival_before_departure(df):

    departure = parse_date_column(
        df,
        "actual_departure"
    )

    arrival = parse_date_column(
        df,
        "actual_arrival"
    )

    mask = (
        departure.notna()
        &
        arrival.notna()
        &
        (
            arrival
            < departure
        )
    )

    return create_result(
        check_name="actual_arrival_before_actual_departure",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "Actual arrival cannot occur before actual departure."
        )
    )


# =========================================================
# 16. ACTUAL DATES MISSING
# =========================================================

def check_missing_actual_departure(df):

    rows_affected = df[
        "actual_departure"
    ].isna().sum()

    return create_result(
        check_name="missing_actual_departure",
        rows_affected=rows_affected,
        total_rows=len(df),
        severity="info",
        recommended_action=(
            "Keep null when appropriate for cancelled or "
            "not-yet-departed shipments. Validate against status."
        )
    )


def check_missing_actual_arrival(df):

    rows_affected = df[
        "actual_arrival"
    ].isna().sum()

    return create_result(
        check_name="missing_actual_arrival",
        rows_affected=rows_affected,
        total_rows=len(df),
        severity="info",
        recommended_action=(
            "Keep null when appropriate for cancelled or "
            "not-yet-arrived shipments. Validate against status."
        )
    )


# =========================================================
# OPTIONAL BUSINESS CONSISTENCY CHECK
# =========================================================

def check_delivered_without_actual_arrival(df):

    status = (
        df["status"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    mask = (
        status.eq("DELIVERED")
        &
        df["actual_arrival"].isna()
    )

    return create_result(
        check_name="delivered_without_actual_arrival",
        rows_affected=mask.sum(),
        total_rows=len(df),
        severity="critical",
        recommended_action=(
            "A delivered shipment should normally have an "
            "actual arrival timestamp. Investigate affected rows."
        )
    )


# =========================================================
# RUN ALL CHECKS
# =========================================================

def run_checks(df):

    results = []

    results.append(
        check_duplicate_rows(df)
    )

    results.append(
        check_duplicate_shipment_ids(df)
    )

    results.append(
        check_missing_shipment_id(df)
    )

    results.append(
        check_missing_cargo_type(df)
    )

    results.append(
        check_missing_weight(df)
    )

    results.append(
        check_negative_weight(df)
    )

    results.append(
        check_zero_container_count(df)
    )

    results.append(
        check_negative_container_count(df)
    )

    results.append(
        check_missing_status(df)
    )

    results.append(
        check_inconsistent_status(df)
    )

    results.append(
        check_inconsistent_cargo_type_formatting(df)
    )

    for column in DATE_COLUMNS:
        results.append(
            check_invalid_date_format(
                df,
                column
            )
        )

    results.append(
        check_planned_departure_before_booking(df)
    )

    results.append(
        check_actual_departure_before_booking(df)
    )

    results.append(
        check_planned_arrival_before_departure(df)
    )

    results.append(
        check_actual_arrival_before_departure(df)
    )

    results.append(
        check_missing_actual_departure(df)
    )

    results.append(
        check_missing_actual_arrival(df)
    )

    results.append(
        check_delivered_without_actual_arrival(df)
    )

    return results


# =========================================================
# CREATE REPORT
# =========================================================

def create_report(df, results):

    return {
        "dataset": "shipments.csv",

        "dataset_summary": {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": df.columns.tolist()
        },

        "quality_summary": {
            "total_checks": len(results),

            "checks_with_issues": sum(
                1
                for result in results
                if result["rows_affected"] > 0
            ),

            "critical_issues": sum(
                1
                for result in results
                if (
                    result["severity"] == "critical"
                    and result["rows_affected"] > 0
                )
            ),

            "warning_issues": sum(
                1
                for result in results
                if (
                    result["severity"] == "warning"
                    and result["rows_affected"] > 0
                )
            ),

            "info_issues": sum(
                1
                for result in results
                if (
                    result["severity"] == "info"
                    and result["rows_affected"] > 0
                )
            )
        },

        "checks": results
    }


# =========================================================
# SAVE JSON
# =========================================================

def save_report(report, output_file):

    output_path = Path(
        output_file
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4
        )

    print(
        f"\nDQ report generated successfully: {output_path}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run standalone Data Quality checks "
            "against raw shipments.csv"
        )
    )

    parser.add_argument(
        "--input",
        default="../data/shipments.csv",
        help="Path to shipments.csv"
    )

    parser.add_argument(
        "--output",
        default="../reports/dq_report.json",
        help="Path for generated DQ JSON report"
    )

    args = parser.parse_args()

    input_path = Path(
        args.input
    )

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    print("=" * 60)
    print("SHIPMENTS DATA QUALITY CHECK")
    print("=" * 60)

    print(
        f"\nReading: {input_path}"
    )

    df = pd.read_csv(
        input_path
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print(
        "\nRunning Data Quality checks..."
    )

    results = run_checks(
        df
    )

    report = create_report(
        df,
        results
    )

    save_report(
        report,
        args.output
    )

    print("\nDQ Summary")

    print(
        f"Total checks: "
        f"{report['quality_summary']['total_checks']}"
    )

    print(
        f"Checks with issues: "
        f"{report['quality_summary']['checks_with_issues']}"
    )

    print(
        f"Critical issues: "
        f"{report['quality_summary']['critical_issues']}"
    )

    print(
        f"Warning issues: "
        f"{report['quality_summary']['warning_issues']}"
    )

    print("\nCompleted successfully.")


if __name__ == "__main__":
    main()