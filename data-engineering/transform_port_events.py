import argparse
from pathlib import Path

import pandas as pd


# =========================================================
# LOAD RAW DATA
# =========================================================

def load_port_events(file_path):
    """
    Reads the raw port_events CSV.

    We intentionally do not modify the raw file.
    """

    print(f"Reading raw port-event data from: {file_path}")

    df = pd.read_csv(file_path)

    print(f"Rows loaded: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    return df


# =========================================================
# NORMALIZE TEXT FIELDS
# =========================================================

def normalize_event_ids(df):
    """
    Event IDs should use one consistent format.
    """

    df = df.copy()

    df["event_id"] = (
        df["event_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return df


def normalize_port_codes(df):
    """
    Port codes should use one consistent format.
    """

    df = df.copy()

    df["port_code"] = (
        df["port_code"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return df


def normalize_vessel_ids(df):
    """
    Vessel IDs are standardized to uppercase.
    """

    df = df.copy()

    df["vessel_id"] = (
        df["vessel_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return df


def normalize_event_type(df):
    """
    Standardize event types to uppercase and replace
    spaces/hyphens with underscores.

    Examples:
        arrival          -> ARRIVAL
        customs cleared  -> CUSTOMS_CLEARED
        loading-complete -> LOADING_COMPLETE

    Missing event type remains null and is handled
    later by quarantine logic.
    """

    df = df.copy()

    df["event_type"] = (
        df["event_type"]
        .astype("string")
        .str.strip()
        .str.upper()
        .str.replace(
            " ",
            "_",
            regex=False
        )
        .str.replace(
            "-",
            "_",
            regex=False
        )
    )

    return df


def normalize_notes(df):
    """
    Remove surrounding whitespace from notes.

    Missing notes are allowed because notes are optional
    descriptive information.
    """

    df = df.copy()

    df["notes"] = (
        df["notes"]
        .astype("string")
        .str.strip()
    )

    return df


# =========================================================
# DATE CONVERSION
# =========================================================

def convert_event_timestamp(df):
    """
    Convert event_timestamp to Pandas datetime.

    Invalid timestamps become NaT and will then be
    quarantined.
    """

    df = df.copy()

    df["event_timestamp"] = pd.to_datetime(
        df["event_timestamp"],
        errors="coerce"
    )

    return df


# =========================================================
# NUMERIC CONVERSION
# =========================================================

def convert_delay_minutes(df):
    """
    Convert delay_minutes to numeric.

    Invalid values become NaN and are subsequently
    quarantined.
    """

    df = df.copy()

    df["delay_minutes"] = pd.to_numeric(
        df["delay_minutes"],
        errors="coerce"
    )

    return df


# =========================================================
# REMOVE EXACT DUPLICATES
# =========================================================

def remove_exact_duplicates(df):
    """
    Exact duplicate rows are safe to remove.
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
    Move invalid records into quarantine rather
    than silently deleting them.
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
# MISSING EVENT ID
# =========================================================

def quarantine_missing_event_id(
        df,
        quarantine_frames
):
    """
    event_id is the natural identifier for an event.

    Events without an ID cannot safely be loaded into
    the serving layer.
    """

    mask = (
        df["event_id"].isna()
        |
        df["event_id"].eq("")
    )

    print(
        f"Missing event-ID rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="missing_event_id",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# CONFLICTING DUPLICATE EVENT IDs
# =========================================================

def quarantine_duplicate_event_ids(
        df,
        quarantine_frames
):
    """
    After exact duplicates have been removed,
    any remaining duplicated event_id represents
    conflicting event records.

    Example:

        EVT-000083 may appear twice with different
        timestamps, ports or vessels.

    Since there is no reliable way to know which
    record is correct, quarantine all records sharing
    that conflicting event_id.
    """

    mask = df[
        "event_id"
    ].duplicated(
        keep=False
    )

    count = int(mask.sum())

    print(
        f"Conflicting duplicate event rows quarantined: "
        f"{count}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="conflicting_duplicate_event_id",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# INVALID EVENT TIMESTAMP
# =========================================================

def quarantine_invalid_timestamp(
        df,
        quarantine_frames
):
    """
    An event without a valid event timestamp cannot be
    reliably ordered or used in event-stream analysis.
    """

    mask = df[
        "event_timestamp"
    ].isna()

    print(
        f"Invalid event-timestamp rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="invalid_event_timestamp",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# MISSING PORT CODE
# =========================================================

def quarantine_missing_port_code(
        df,
        quarantine_frames
):
    """
    Every port event must identify the port at which
    the event occurred.
    """

    mask = (
        df["port_code"].isna()
        |
        df["port_code"].eq("")
    )

    print(
        f"Missing port-code rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="missing_port_code",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# MISSING VESSEL ID
# =========================================================

def quarantine_missing_vessel_id(
        df,
        quarantine_frames
):
    """
    A port event should identify the vessel that
    generated the event.
    """

    mask = (
        df["vessel_id"].isna()
        |
        df["vessel_id"].eq("")
    )

    print(
        f"Missing vessel-ID rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="missing_vessel_id",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# MISSING EVENT TYPE
# =========================================================

def quarantine_missing_event_type(
        df,
        quarantine_frames
):
    """
    event_type is essential to understanding what
    happened at the port.

    Missing event types cannot safely be inferred,
    so these records are quarantined.
    """

    mask = (
        df["event_type"].isna()
        |
        df["event_type"].eq("")
    )

    print(
        f"Missing event-type rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="missing_event_type",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# INVALID DELAY
# =========================================================

def quarantine_invalid_delay_minutes(
        df,
        quarantine_frames
):
    """
    Delay duration cannot be negative.

    Non-numeric delay values are also invalid.
    """

    delay = df[
        "delay_minutes"
    ]

    mask = (
        delay.isna()
        |
        (delay < 0)
    )

    print(
        f"Invalid delay-minute rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="invalid_delay_minutes",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# OPTIONAL NOTES
# =========================================================

def report_missing_notes(df):
    """
    Missing notes are allowed.

    Notes are descriptive metadata and are not required
    for identifying or interpreting the core event.

    Therefore missing notes remain null and are not
    quarantined.
    """

    mask = (
        df["notes"].isna()
        |
        df["notes"].eq("")
    )

    print(
        f"Event rows with missing notes retained: "
        f"{int(mask.sum())}"
    )

    return df


# =========================================================
# BUILD CURATED DATASET
# =========================================================

def transform_port_events(df):

    print("\n")
    print("=" * 60)
    print("TRANSFORMING PORT EVENTS")
    print("=" * 60)

    quarantine_frames = []

    # -----------------------------------------------------
    # 1. Remove exact duplicates
    # -----------------------------------------------------

    df = remove_exact_duplicates(
        df
    )

    # -----------------------------------------------------
    # 2. Normalize text
    # -----------------------------------------------------

    df = normalize_event_ids(
        df
    )

    df = normalize_port_codes(
        df
    )

    df = normalize_vessel_ids(
        df
    )

    df = normalize_event_type(
        df
    )

    df = normalize_notes(
        df
    )

    # -----------------------------------------------------
    # 3. Convert timestamp
    # -----------------------------------------------------

    df = convert_event_timestamp(
        df
    )

    # -----------------------------------------------------
    # 4. Convert delay
    # -----------------------------------------------------

    df = convert_delay_minutes(
        df
    )

    # -----------------------------------------------------
    # 5. Quarantine missing event IDs
    # -----------------------------------------------------

    df = quarantine_missing_event_id(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 6. Quarantine conflicting duplicate event IDs
    # -----------------------------------------------------

    df = quarantine_duplicate_event_ids(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 7. Quarantine invalid timestamps
    # -----------------------------------------------------

    df = quarantine_invalid_timestamp(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 8. Quarantine missing port codes
    # -----------------------------------------------------

    df = quarantine_missing_port_code(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 9. Quarantine missing vessel IDs
    # -----------------------------------------------------

    df = quarantine_missing_vessel_id(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 10. Quarantine missing event types
    # -----------------------------------------------------

    df = quarantine_missing_event_type(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 11. Quarantine invalid delays
    # -----------------------------------------------------

    df = quarantine_invalid_delay_minutes(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 12. Report optional missing notes
    # -----------------------------------------------------

    df = report_missing_notes(
        df
    )

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
    #         transform_port_events.py

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
        / "port_events.csv"
    )

    default_curated = (
        project_root
        / "curated"
        / "port_events_curated.csv"
    )

    default_quarantine = (
        project_root
        / "quarantine"
        / "port_events_quarantine.csv"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Clean and transform raw port-event data "
            "into a curated dataset."
        )
    )

    parser.add_argument(
        "--input",
        default=str(default_input),
        help="Path to raw port_events.csv"
    )

    parser.add_argument(
        "--curated-output",
        default=str(default_curated),
        help="Path for curated port-events CSV"
    )

    parser.add_argument(
        "--quarantine-output",
        default=str(default_quarantine),
        help="Path for quarantined port-event rows"
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

    raw_df = load_port_events(
        input_path
    )

    # -----------------------------------------------------
    # Transform
    # -----------------------------------------------------

    curated_df, quarantine_df = (
        transform_port_events(
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