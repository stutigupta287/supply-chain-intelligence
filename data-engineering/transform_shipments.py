import argparse
from pathlib import Path

import pandas as pd


# =========================================================
# CONSTANTS
# =========================================================

DATE_COLUMNS = [
    "booking_date",
    "planned_departure",
    "actual_departure",
    "planned_arrival",
    "actual_arrival"
]


# =========================================================
# LOAD RAW DATA
# =========================================================

def load_shipments(file_path):
    """
    Reads the raw shipments CSV.

    We intentionally do not modify the raw file.
    """

    print(f"Reading raw shipment data from: {file_path}")

    df = pd.read_csv(file_path)

    print(f"Rows loaded: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    return df

# =========================================================
# NORMALIZE TEXT FIELDS
# =========================================================

def normalize_status(df):
    """
    Standardize shipment statuses.

    Observed in the supplied CSV:
        DELIVERED
        delivered
        DELAYED
        CANCELLED
        COMPLETED
        Complete
        null

    Decision:
        delivered  -> DELIVERED
        COMPLETED  -> DELIVERED
        Complete   -> DELIVERED

    Missing status remains null.
    """

    df = df.copy()

    df["status"] = (
        df["status"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    status_mapping = {
        "COMPLETED": "DELIVERED",
        "COMPLETE": "DELIVERED"
    }

    df["status"] = (
        df["status"]
        .replace(status_mapping)
    )

    return df


def normalize_cargo_type(df):
    """
    Standardize cargo type formatting.

    Examples from supplied data:

        FURNITURE        -> Furniture
        electronics     -> Electronics
         Chemicals      -> Chemicals
        machinery       -> Machinery

    Missing values remain null.
    """

    df = df.copy()

    df["cargo_type"] = (
        df["cargo_type"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    return df


def normalize_port_codes(df):
    """
    Port codes should use one consistent format.
    We standardize them to uppercase and remove spaces.
    """

    df = df.copy()

    for column in [
        "origin_port",
        "destination_port"
    ]:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    return df


# =========================================================
# DATE CONVERSION
# =========================================================

def convert_dates(df):
    """
    Convert all date columns into Pandas datetime values.

    errors='coerce' means invalid values become NaT
    rather than crashing the pipeline.
    """

    df = df.copy()

    for column in DATE_COLUMNS:

        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

    return df


# =========================================================
# REMOVE EXACT DUPLICATES
# =========================================================

def remove_exact_duplicates(df):
    """
    Exact duplicated rows are safe to remove.

    In the supplied dataset there are exact duplicate rows.
    """

    before = len(df)

    df = df.drop_duplicates().copy()

    after = len(df)

    print(
        f"Exact duplicate rows removed: "
        f"{before - after}"
    )

    return df


# =========================================================
# QUARANTINE HELPER
# =========================================================

def quarantine_rows(
        df,
        mask,
        reason,
        quarantine_frames
):
    """
    Move invalid rows into the quarantine collection.

    The raw rows are not silently deleted.
    We preserve them along with a reason explaining
    why they were excluded from curated data.
    """

    bad_rows = df.loc[mask].copy()

    if len(bad_rows) > 0:

        bad_rows["quarantine_reason"] = reason

        quarantine_frames.append(
            bad_rows
        )

    clean_rows = df.loc[~mask].copy()

    return clean_rows


# =========================================================
# CONFLICTING DUPLICATE SHIPMENT IDs
# =========================================================

def quarantine_duplicate_shipment_ids(
        df,
        quarantine_frames
):
    """
    After exact duplicates have already been removed,
    any remaining duplicated shipment_id means that
    two different records claim to represent the same
    shipment.

    Instead of guessing which one is correct,
    quarantine all conflicting records.
    """

    mask = df[
        "shipment_id"
    ].duplicated(
        keep=False
    )

    count = int(mask.sum())

    print(
        f"Conflicting duplicate shipment rows quarantined: "
        f"{count}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="conflicting_duplicate_shipment_id",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# INVALID WEIGHT
# =========================================================

def quarantine_negative_weight(
        df,
        quarantine_frames
):
    """
    Negative physical shipment weight is invalid.
    """

    df = df.copy()

    df["weight_tons"] = pd.to_numeric(
        df["weight_tons"],
        errors="coerce"
    )

    mask = (
        df["weight_tons"].notna()
        &
        (df["weight_tons"] < 0)
    )

    print(
        f"Negative weight rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="negative_weight_tons",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# INVALID CONTAINER COUNT
# =========================================================

def quarantine_invalid_container_count(
        df,
        quarantine_frames
):
    """
    For this dataset we treat zero or negative
    container_count as invalid.

    The supplied data contains zero values.
    """

    df = df.copy()

    df["container_count"] = pd.to_numeric(
        df["container_count"],
        errors="coerce"
    )

    mask = (
        df["container_count"].notna()
        &
        (df["container_count"] <= 0)
    )

    print(
        f"Invalid container-count rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="invalid_container_count",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# INVALID DATE RELATIONSHIPS
# =========================================================

def quarantine_invalid_date_relationships(
        df,
        quarantine_frames
):
    """
    Quarantine records with impossible chronological
    relationships.

    Rules:

    planned_departure >= booking_date

    actual_departure >= booking_date

    planned_arrival >= planned_departure

    actual_arrival >= actual_departure
    """

    booking = df["booking_date"]

    planned_departure = df[
        "planned_departure"
    ]

    actual_departure = df[
        "actual_departure"
    ]

    planned_arrival = df[
        "planned_arrival"
    ]

    actual_arrival = df[
        "actual_arrival"
    ]

    # ---------------------------------------------
    # Planned departure before booking
    # ---------------------------------------------

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

    print(
        "Planned departure before booking "
        f"quarantined: {int(mask.sum())}"
    )

    df = quarantine_rows(
        df,
        mask,
        "planned_departure_before_booking",
        quarantine_frames
    )

    # Re-read columns because df may now have
    # fewer rows.

    booking = df["booking_date"]
    actual_departure = df[
        "actual_departure"
    ]

    # ---------------------------------------------
    # Actual departure before booking
    # ---------------------------------------------

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

    print(
        "Actual departure before booking "
        f"quarantined: {int(mask.sum())}"
    )

    df = quarantine_rows(
        df,
        mask,
        "actual_departure_before_booking",
        quarantine_frames
    )

    # ---------------------------------------------
    # Planned arrival before planned departure
    # ---------------------------------------------

    planned_departure = df[
        "planned_departure"
    ]

    planned_arrival = df[
        "planned_arrival"
    ]

    mask = (
        planned_departure.notna()
        &
        planned_arrival.notna()
        &
        (
            planned_arrival
            < planned_departure
        )
    )

    print(
        "Planned arrival before planned departure "
        f"quarantined: {int(mask.sum())}"
    )

    df = quarantine_rows(
        df,
        mask,
        "planned_arrival_before_planned_departure",
        quarantine_frames
    )

    # ---------------------------------------------
    # Actual arrival before actual departure
    # ---------------------------------------------

    actual_departure = df[
        "actual_departure"
    ]

    actual_arrival = df[
        "actual_arrival"
    ]

    mask = (
        actual_departure.notna()
        &
        actual_arrival.notna()
        &
        (
            actual_arrival
            < actual_departure
        )
    )

    print(
        "Actual arrival before actual departure "
        f"quarantined: {int(mask.sum())}"
    )

    df = quarantine_rows(
        df,
        mask,
        "actual_arrival_before_actual_departure",
        quarantine_frames
    )

    return df


# =========================================================
# REQUIRED DERIVED FIELD #1
# actual_delay_hours
# =========================================================

def add_actual_delay_hours(df):
    """
    actual_delay_hours =
        actual_arrival - planned_arrival

    Example:

    planned = Jan 10 10:00
    actual  = Jan 11 16:00

    delay = 30 hours

    If actual_arrival is missing, result remains null.
    """

    df = df.copy()

    difference = (
        df["actual_arrival"]
        -
        df["planned_arrival"]
    )

    df["actual_delay_hours"] = (
        difference.dt.total_seconds()
        / 3600
    )

    return df


# =========================================================
# REQUIRED DERIVED FIELD #2
# on_time_flag
# =========================================================

def add_on_time_flag(df):
    """
    Assignment rule:

    on_time_flag = true when delay <= 24 hours.

    Missing actual arrival means we do not yet know
    whether the shipment was on time.

    Therefore its flag should be null rather than False.
    """

    df = df.copy()

    df["on_time_flag"] = pd.Series(
        pd.NA,
        index=df.index,
        dtype="boolean"
    )

    has_delay = df[
        "actual_delay_hours"
    ].notna()

    df.loc[
        has_delay,
        "on_time_flag"
    ] = (
        df.loc[
            has_delay,
            "actual_delay_hours"
        ]
        <= 24
    )

    return df


# =========================================================
# REQUIRED DERIVED FIELD #3
# route_key
# =========================================================

def add_route_key(df):
    """
    Example:

        CNSHA → NLRTM
    """

    df = df.copy()

    df["route_key"] = (
        df["origin_port"]
        +
        " → "
        +
        df["destination_port"]
    )

    return df


# =========================================================
# REQUIRED DERIVED FIELD #4
# transit_days_planned
# =========================================================

def add_transit_days_planned(df):

    df = df.copy()

    difference = (
        df["planned_arrival"]
        -
        df["planned_departure"]
    )

    df["transit_days_planned"] = (
        difference.dt.total_seconds()
        / 86400
    )

    return df


# =========================================================
# REQUIRED DERIVED FIELD #5
# transit_days_actual
# =========================================================

def add_transit_days_actual(df):

    df = df.copy()

    difference = (
        df["actual_arrival"]
        -
        df["actual_departure"]
    )

    df["transit_days_actual"] = (
        difference.dt.total_seconds()
        / 86400
    )

    return df

def quarantine_delivered_without_actual_arrival(
        df,
        quarantine_frames
):
    """
    A shipment marked DELIVERED should have
    an actual arrival timestamp.

    If it does not, the record is internally
    inconsistent and should be quarantined.
    """

    mask = (
        df["status"].eq("DELIVERED").fillna(False)
        &
        df["actual_arrival"].isna()
    )

    print(
        "Delivered shipments without actual arrival "
        f"quarantined: {int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="delivered_without_actual_arrival",
        quarantine_frames=quarantine_frames
    )
# =========================================================
# BUILD CURATED DATASET
# =========================================================

def transform_shipments(df):

    print("\n")
    print("=" * 60)
    print("TRANSFORMING SHIPMENTS")
    print("=" * 60)

    quarantine_frames = []

    # -----------------------------------------------------
    # 1. Remove exact duplicate rows
    # -----------------------------------------------------

    df = remove_exact_duplicates(
        df
    )

    # -----------------------------------------------------
    # 2. Normalize text
    # -----------------------------------------------------

    df = normalize_status(
        df
    )

    df = normalize_cargo_type(
        df
    )

    df = normalize_port_codes(
        df
    )

    # -----------------------------------------------------
    # 3. Convert date columns
    # -----------------------------------------------------

    df = convert_dates(
        df
    )

    # -----------------------------------------------------
    # 4. Quarantine conflicting duplicates
    # -----------------------------------------------------

    df = quarantine_duplicate_shipment_ids(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 5. Quarantine invalid weight
    # -----------------------------------------------------

    df = quarantine_negative_weight(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 6. Quarantine invalid containers
    # -----------------------------------------------------

    df = quarantine_invalid_container_count(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 7. Quarantine impossible dates
    # -----------------------------------------------------

    df = quarantine_invalid_date_relationships(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 8. Quarantine delivered shipments without arrival
    # -----------------------------------------------------

    df = quarantine_delivered_without_actual_arrival(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 9. Required derived fields
    # -----------------------------------------------------

    df = add_actual_delay_hours(df)
    df = add_on_time_flag(df)
    df = add_route_key(df)
    df = add_transit_days_planned(df)
    df = add_transit_days_actual(df)

    # -----------------------------------------------------
    # Combine quarantine records
    # -----------------------------------------------------

    if quarantine_frames:

        quarantine_df = pd.concat(
            quarantine_frames,
            ignore_index=True
        )

    else:

        quarantine_df = pd.DataFrame()

    return df, quarantine_df


# =========================================================
# SAVE OUTPUT
# =========================================================

def save_output(
        curated_df,
        quarantine_df,
        curated_path,
        quarantine_path
):

    curated_path = Path(
        curated_path
    )

    quarantine_path = Path(
        quarantine_path
    )

    curated_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    quarantine_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # CSV does not preserve Pandas nullable booleans very
    # elegantly, but this is perfectly fine for our
    # intermediate curated output.

    curated_df.to_csv(
        curated_path,
        index=False
    )

    quarantine_df.to_csv(
        quarantine_path,
        index=False
    )

    print("\n")
    print("=" * 60)
    print("TRANSFORMATION COMPLETE")
    print("=" * 60)

    print(
        f"Curated rows: {len(curated_df)}"
    )

    print(
        f"Quarantined rows: {len(quarantine_df)}"
    )

    print(
        f"\nCurated file:\n{curated_path}"
    )

    print(
        f"\nQuarantine file:\n{quarantine_path}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # Location of this Python file:
    #
    # supply-chain-intelligence/
    #     data-engineering/
    #         transform_shipments.py

    script_directory = (
        Path(__file__)
        .resolve()
        .parent
    )

    project_root = (
        script_directory.parent
    )

    default_input = (
        project_root
        / "data"
        / "shipments.csv"
    )

    default_curated = (
        project_root
        / "curated"
        / "shipments_curated.csv"
    )

    default_quarantine = (
        project_root
        / "quarantine"
        / "shipments_quarantine.csv"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Clean and transform raw shipment data "
            "into a curated dataset."
        )
    )

    parser.add_argument(
        "--input",
        default=str(default_input),
        help="Path to raw shipments.csv"
    )

    parser.add_argument(
        "--curated-output",
        default=str(default_curated),
        help="Path for curated shipments CSV"
    )

    parser.add_argument(
        "--quarantine-output",
        default=str(default_quarantine),
        help="Path for quarantined shipment rows"
    )

    args = parser.parse_args()

    input_path = Path(
        args.input
    )

    if not input_path.exists():

        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    # -----------------------------------------------------
    # Load
    # -----------------------------------------------------

    raw_df = load_shipments(
        input_path
    )

    # -----------------------------------------------------
    # Transform
    # -----------------------------------------------------

    curated_df, quarantine_df = (
        transform_shipments(
            raw_df
        )
    )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    save_output(
        curated_df=curated_df,
        quarantine_df=quarantine_df,
        curated_path=args.curated_output,
        quarantine_path=args.quarantine_output
    )


if __name__ == "__main__":
    main()