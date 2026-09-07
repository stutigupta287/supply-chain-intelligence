import argparse
from pathlib import Path

import pandas as pd


# =========================================================
# LOAD RAW DATA
# =========================================================

def load_ports(file_path):
    """
    Reads the raw ports CSV.

    We intentionally do not modify the raw file.
    """

    print(f"Reading raw port data from: {file_path}")

    df = pd.read_csv(file_path)

    print(f"Rows loaded: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    return df


# =========================================================
# NORMALIZE TEXT FIELDS
# =========================================================

def normalize_port_codes(df):
    """
    Port codes should use one consistent format.

    We standardize them to uppercase and remove
    surrounding whitespace.
    """

    df = df.copy()

    df["port_code"] = (
        df["port_code"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return df


def normalize_port_names(df):
    """
    Remove unnecessary surrounding whitespace
    from port names.

    We do not apply title() because some legitimate
    names/acronyms may have intentional casing.
    """

    df = df.copy()

    df["port_name"] = (
        df["port_name"]
        .astype("string")
        .str.strip()
    )

    return df


def normalize_country(df):
    """
    Remove surrounding whitespace from country values.

    Missing country values remain null.

    We intentionally do not guess or hard-code a country
    when the source data does not provide one.
    """

    df = df.copy()

    df["country"] = (
        df["country"]
        .astype("string")
        .str.strip()
    )

    return df


def normalize_region(df):
    """
    Standardize regions to uppercase.

    Examples:
        APAC
        EUR
        AMER
        MEA
    """

    df = df.copy()

    df["region"] = (
        df["region"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return df


def normalize_timezone(df):
    """
    Remove surrounding whitespace from timezone values.

    Examples from supplied data:
        UTC+8
        UTC+1
        UTC+5:30
    """

    df = df.copy()

    df["timezone"] = (
        df["timezone"]
        .astype("string")
        .str.strip()
    )

    return df


# =========================================================
# NUMERIC CONVERSION
# =========================================================

def convert_congestion_score(df):
    """
    Convert avg_congestion_score into a numeric value.

    Invalid strings become NaN and will subsequently
    be quarantined.
    """

    df = df.copy()

    df["avg_congestion_score"] = pd.to_numeric(
        df["avg_congestion_score"],
        errors="coerce"
    )

    return df


# =========================================================
# REMOVE EXACT DUPLICATES
# =========================================================

def remove_exact_duplicates(df):
    """
    Exact duplicated rows are safe to remove.
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

    The raw records are not silently deleted.
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
# INVALID / MISSING PORT CODE
# =========================================================

def quarantine_missing_port_code(
        df,
        quarantine_frames
):
    """
    port_code is the natural identifier for a port.

    A port without a usable port code cannot safely be
    referenced by shipments or port events.
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
# CONFLICTING DUPLICATE PORT CODES
# =========================================================

def quarantine_duplicate_port_codes(
        df,
        quarantine_frames
):
    """
    After exact duplicates are removed, any remaining
    duplicated port_code means two different records
    claim to represent the same port.

    Instead of guessing which record is correct,
    quarantine all conflicting rows.
    """

    mask = df[
        "port_code"
    ].duplicated(
        keep=False
    )

    count = int(mask.sum())

    print(
        f"Conflicting duplicate port rows quarantined: "
        f"{count}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="conflicting_duplicate_port_code",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# INVALID PORT NAME
# =========================================================

def quarantine_missing_port_name(
        df,
        quarantine_frames
):
    """
    Port name is required reference information.
    """

    mask = (
        df["port_name"].isna()
        |
        df["port_name"].eq("")
    )

    print(
        f"Missing port-name rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="missing_port_name",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# INVALID CONGESTION SCORE
# =========================================================

def quarantine_invalid_congestion_score(
        df,
        quarantine_frames
):
    """
    avg_congestion_score is expected to be between
    0 and 1 inclusive.

    Invalid numeric values or values outside this range
    are quarantined.
    """

    score = df[
        "avg_congestion_score"
    ]

    mask = (
        score.isna()
        |
        (score < 0)
        |
        (score > 1)
    )

    print(
        f"Invalid congestion-score rows quarantined: "
        f"{int(mask.sum())}"
    )

    return quarantine_rows(
        df=df,
        mask=mask,
        reason="invalid_avg_congestion_score",
        quarantine_frames=quarantine_frames
    )


# =========================================================
# REPORT MISSING COUNTRY
# =========================================================

def report_missing_country(df):
    """
    Missing country is treated as a warning rather than
    a critical failure.

    The record remains useful because port_code is still
    valid and can be referenced by shipments/events.

    We intentionally do not invent or hard-code a value.
    """

    mask = (
        df["country"].isna()
        |
        df["country"].eq("")
    )

    print(
        f"Port rows with missing country retained: "
        f"{int(mask.sum())}"
    )

    return df


# =========================================================
# BUILD CURATED DATASET
# =========================================================

def transform_ports(df):

    print("\n")
    print("=" * 60)
    print("TRANSFORMING PORTS")
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

    df = normalize_port_codes(
        df
    )

    df = normalize_port_names(
        df
    )

    df = normalize_country(
        df
    )

    df = normalize_region(
        df
    )

    df = normalize_timezone(
        df
    )

    # -----------------------------------------------------
    # 3. Convert numeric fields
    # -----------------------------------------------------

    df = convert_congestion_score(
        df
    )

    # -----------------------------------------------------
    # 4. Quarantine missing port codes
    # -----------------------------------------------------

    df = quarantine_missing_port_code(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 5. Quarantine conflicting port codes
    # -----------------------------------------------------

    df = quarantine_duplicate_port_codes(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 6. Quarantine missing port names
    # -----------------------------------------------------

    df = quarantine_missing_port_name(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 7. Quarantine invalid congestion scores
    # -----------------------------------------------------

    df = quarantine_invalid_congestion_score(
        df,
        quarantine_frames
    )

    # -----------------------------------------------------
    # 8. Report non-critical missing country
    # -----------------------------------------------------

    df = report_missing_country(
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
    #         transform_ports.py

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
        / "ports.csv"
    )

    default_curated = (
        project_root
        / "curated"
        / "ports_curated.csv"
    )

    default_quarantine = (
        project_root
        / "quarantine"
        / "ports_quarantine.csv"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Clean and transform raw port data "
            "into a curated dataset."
        )
    )

    parser.add_argument(
        "--input",
        default=str(default_input),
        help="Path to raw ports.csv"
    )

    parser.add_argument(
        "--curated-output",
        default=str(default_curated),
        help="Path for curated ports CSV"
    )

    parser.add_argument(
        "--quarantine-output",
        default=str(default_quarantine),
        help="Path for quarantined port rows"
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

    raw_df = load_ports(
        input_path
    )

    # -----------------------------------------------------
    # Transform
    # -----------------------------------------------------

    curated_df, quarantine_df = (
        transform_ports(
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