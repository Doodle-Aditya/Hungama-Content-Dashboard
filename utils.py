"""
utils.py

Helper functions for the Content Operations Dashboard.

Responsibilities:
- Loading and validating the two Excel data sources (Master_Label_Dashboard.xlsx
  and Revenue_Summary_1.xlsx).
- Parsing dates safely (handling invalid / missing values gracefully).
- Computing Days Remaining and Agreement Status for every record.
- Small formatting helpers reused by dashboard.py / report_tracker.py.

Keeping this logic separate from the UI (dashboard.py / report_tracker.py /
app.py) means future modules can reuse the same date/status utilities
without duplicating code.
"""

from datetime import datetime, date

import pandas as pd
import streamlit as st
import io
import config

# ----------------------------------------------------------------------
# FILE UPLOAD WIDGETS
# ----------------------------------------------------------------------

def render_agreements_uploader():
    """
    Render a sidebar uploader for the Master Label Dashboard workbook.

    The uploaded file is stashed in st.session_state under a fixed key,
    so it persists across reruns and across pages within the same
    session -- uploading it once (on either page) makes it available to
    both the Agreement Monitor and the Report Tracker's Agreement Status
    lookup. Re-uploading at any time replaces the active file immediately.

    Returns:
        The active UploadedFile, or None if nothing has been uploaded yet.
    """
    st.sidebar.markdown("### 📂 Master Label Dashboard")
    uploaded = st.sidebar.file_uploader(
        "Upload the latest Master_Label_Dashboard.xlsx",
        type=["xlsx"],
        key="agreements_file_uploader",
        help="Re-upload anytime to refresh the Agreement data.",
    )
    if uploaded is not None:
        st.session_state["agreements_file"] = uploaded
    return st.session_state.get("agreements_file")


def render_reports_uploader():
    """
    Render a sidebar uploader for the Revenue Summary workbook.

    Same session_state-backed pattern as render_agreements_uploader, kept
    as a separate key/file since it's a different workbook.

    Returns:
        The active UploadedFile, or None if nothing has been uploaded yet.
    """
    st.sidebar.markdown("### 📂 Revenue Summary")
    uploaded = st.sidebar.file_uploader(
        "Upload the latest Revenue_Summary.xlsx",
        type=["xlsx"],
        key="reports_file_uploader",
        help="Re-upload anytime to refresh the Reports data.",
    )
    if uploaded is not None:
        st.session_state["reports_file"] = uploaded
    return st.session_state.get("reports_file")


# ----------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------

def _read_excel_sheet(
    file_path: str,
    sheet_name,
    required_columns: list,
    sheet_label: str,
) -> pd.DataFrame:
    """
    Generic, defensive Excel-sheet reader shared by every module that
    reads from a workbook (Agreement Monitor, Report Tracker, and any
    future module).

    Handles gracefully, without crashing the app:
    - Missing workbook file.
    - Missing sheet within the workbook (by name OR by out-of-range index).
    - Missing required columns on that sheet.

    Args:
        file_path: Path to the Excel workbook.
        sheet_name: Sheet name (str) or position (int, 0 = first sheet,
            1 = second sheet, etc.).
        required_columns: Columns that must be present on this sheet.
        sheet_label: Human-readable label used in error messages.

    Returns:
        Raw DataFrame (dates NOT yet parsed) with blank rows dropped.
        Returns an empty DataFrame with the expected schema if the file
        or sheet is missing.
    """
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
    except FileNotFoundError:
        return pd.DataFrame(columns=required_columns)
    except ValueError as err:
        # Raised by pandas/openpyxl when the sheet doesn't exist -- either
        # a named sheet that's missing (e.g. "Worksheet named 'X' not
        # found") or an out-of-range index (e.g. "Worksheet index 5 is
        # invalid, 2 worksheets found").
        if "sheet" in str(err).lower() or "worksheet" in str(err).lower():
            return pd.DataFrame(columns=required_columns)
        raise

    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"'{sheet_label}' sheet is missing required column(s): "
            f"{', '.join(missing_cols)}. Expected columns: "
            f"{', '.join(required_columns)}"
        )

    # Drop fully blank rows (e.g. trailing empty Excel rows).
    df = df.dropna(how="all")

    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_agreements(
    file,
    sheet_name=config.AGREEMENTS_SHEET_NAME,
) -> pd.DataFrame:
    """
    Load the "Master" sheet from an uploaded Master_Label_Dashboard.xlsx.

    The source sheet has ~40 columns and calls the expiry column
    "End Date" rather than "Expiry Date" -- it is renamed immediately
    after loading so every downstream function (enrich_dataframe,
    compute_status, dashboard.py, report_tracker.py's label matching)
    keeps working against the same "Expiry Date" name as before.

    Args:
        file: An uploaded file object (e.g. from
            render_agreements_uploader) or a path string. Must not be None
            -- callers should check for an active upload before calling.
        sheet_name: Sheet name. Defaults to config.AGREEMENTS_SHEET_NAME
            ("Master").

    Returns:
        A DataFrame with parsed Start Date / Expiry Date columns, plus
        all other original Master-sheet columns passed through untouched.
    """
    df = _read_excel_sheet(
        file, sheet_name, config.RAW_AGREEMENTS_REQUIRED_COLUMNS, "Master"
    )

    if df.empty:
        return df

    df = df.rename(columns={config.SOURCE_COL_END_DATE: config.COL_EXPIRY_DATE})

    df[config.COL_START_DATE] = pd.to_datetime(
        df[config.COL_START_DATE], errors="coerce"
    )
    df[config.COL_EXPIRY_DATE] = pd.to_datetime(
        df[config.COL_EXPIRY_DATE], errors="coerce"
    )

    # "Approval upto" is optional -- only parse it if the sheet has it.
    if config.COL_APPROVAL_UPTO in df.columns:
        df[config.COL_APPROVAL_UPTO] = pd.to_datetime(
            df[config.COL_APPROVAL_UPTO], errors="coerce"
        )

    return df


# ----------------------------------------------------------------------
# STATUS / DAYS REMAINING COMPUTATION
# ----------------------------------------------------------------------

def compute_days_remaining(expiry_date, today: date = None) -> "int | None":
    """
    Compute the number of days remaining until expiry.

    Args:
        expiry_date: A pandas Timestamp, datetime, or NaT.
        today: Reference date (defaults to today's date).

    Returns:
        Integer days remaining (can be negative if already expired),
        or None if the expiry date is missing/invalid.
    """
    if pd.isna(expiry_date):
        return None

    if today is None:
        today = datetime.today().date()

    # Normalize expiry_date to a plain date for subtraction.
    if hasattr(expiry_date, "date"):
        expiry_date = expiry_date.date()

    return (expiry_date - today).days


def compute_status(days_remaining) -> str:
    """
    Determine the Agreement Status based on Days Remaining.

    Status Rules (as per business requirements):
        Expired         -> Expiry Date < Today      (days_remaining < 0)
        Expires Today   -> Expiry Date == Today      (days_remaining == 0)
        Expiring Soon   -> 0 < Days Remaining <= 30
        Active          -> Days Remaining > 30

    Args:
        days_remaining: Integer day count, or None if unknown.

    Returns:
        One of the STATUS_* constants from config.py.
    """
    if days_remaining is None:
        return config.STATUS_UNKNOWN

    if days_remaining < 0:
        return config.STATUS_EXPIRED
    elif days_remaining == 0:
        return config.STATUS_EXPIRES_TODAY
    elif days_remaining <= config.EXPIRING_SOON_THRESHOLD_DAYS:
        return config.STATUS_EXPIRING_SOON
    else:
        return config.STATUS_ACTIVE


def enrich_dataframe(df: pd.DataFrame, today: date = None) -> pd.DataFrame:
    """
    Add 'Days Remaining' and 'Status' columns to the agreements DataFrame.

    This is the single source of truth for status computation, used by
    both the KPI cards and the data table so numbers always stay in sync.

    Args:
        df: Raw agreements DataFrame (with parsed date columns).
        today: Optional override for "today" (useful for testing).

    Returns:
        A new DataFrame with the additional computed columns.
    """
    if today is None:
        today = datetime.today().date()

    df = df.copy()

    df[config.COL_DAYS_REMAINING] = df[config.COL_EXPIRY_DATE].apply(
        lambda d: compute_days_remaining(d, today)
    )
    df[config.COL_STATUS] = df[config.COL_DAYS_REMAINING].apply(compute_status)

    # Reformat "Approval upto" as "Month YYYY" for display. Falls back to
    # "—" for every row if the source column wasn't present at all, so
    # downstream code can always rely on this column existing.
    if config.COL_APPROVAL_UPTO in df.columns:
        df[config.COL_APPROVAL_MONTH_DISPLAY] = df[config.COL_APPROVAL_UPTO].apply(
            format_approval_month
        )
    else:
        df[config.COL_APPROVAL_MONTH_DISPLAY] = "—"

    return df


# ----------------------------------------------------------------------
# FORMATTING HELPERS
# ----------------------------------------------------------------------

def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    """
    Convert a DataFrame to raw .xlsx bytes, suitable for st.download_button.

    Args:
        df: DataFrame to export. Should contain plain, already-formatted
            values (not HTML badges) so the exported file is clean.
        sheet_name: Name of the sheet inside the exported workbook.

    Returns:
        Bytes of a valid .xlsx file.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()

    
def format_date(value) -> str:
    """Format a date value for display, handling missing/invalid dates."""
    if pd.isna(value):
        return "—"
    return value.strftime("%d-%b-%Y")

def format_approval_month(value) -> str:
    """
    Format an 'Approval upto' date as 'Month YYYY' (e.g. 'March 2025').
    Returns '—' for missing/invalid dates.
    """
    if pd.isna(value):
        return "—"
    return value.strftime("%B %Y")

def format_days_remaining(value) -> str:
    """Format days-remaining for display (handles None gracefully)."""
    if value is None or pd.isna(value):
        return "—"
    value = int(value)
    if value < 0:
        return f"{abs(value)} days overdue"
    if value == 0:
        return "Today"
    return f"{value} days"


def status_badge_html(status: str) -> str:
    """
    Return an HTML span styled as a colored badge for the given status.
    Used to color-code the Status column in the data table.
    """
    bg_color = config.STATUS_COLORS.get(status, config.STATUS_COLORS[config.STATUS_UNKNOWN])
    text_color = config.STATUS_TEXT_COLORS.get(status, "#ffffff")
    return (
        f'<span style="background-color:{bg_color}; color:{text_color}; '
        f'padding:4px 10px; border-radius:12px; font-weight:600; '
        f'font-size:0.85rem;">{status}</span>'
    )


def colored_badge_html(text: str, bg_color: str, text_color: str = "#ffffff") -> str:
    """
    Generic colored-badge renderer. Both `status_badge_html` (Agreement
    Status) and the Report Tracker's Report Status / Label Name badges
    build on this, so the visual style stays identical across pages.
    """
    return (
        f'<span style="background-color:{bg_color}; color:{text_color}; '
        f'padding:4px 10px; border-radius:12px; font-weight:600; '
        f'font-size:0.85rem;">{text}</span>'
    )


# ========================================================================
# REPORT TRACKER MODULE
# ------------------------------------------------------------------------
# Reuses the Agreement Monitor's date/status logic above
# (compute_days_remaining, compute_status, format_date,
# colored_badge_html) instead of duplicating it.
# ========================================================================

@st.cache_data(show_spinner=False)
def load_reports(
    file,
    sheet_name=config.REPORTS_SHEET_NAME,
) -> pd.DataFrame:
    """
    Load the "Reports Update" sheet from an uploaded Revenue_Summary.xlsx.

    Args:
        file: An uploaded file object (e.g. from render_reports_uploader)
            or a path string. Must not be None -- callers should check
            for an active upload before calling.
        sheet_name: Sheet name. Defaults to config.REPORTS_SHEET_NAME
            ("Reports Update").

    Returns:
        A DataFrame with parsed Report Date / Shared with CP columns.
    """
    df = _read_excel_sheet(
        file, sheet_name, config.REPORT_REQUIRED_COLUMNS, "Reports Update"
    )

    if df.empty:
        return df

    df[config.COL_REPORT_DATE] = pd.to_datetime(
        df[config.COL_REPORT_DATE], errors="coerce"
    )
    df[config.COL_SHARED_WITH_CP] = pd.to_datetime(
        df[config.COL_SHARED_WITH_CP], errors="coerce"
    )

    for optional_date_col in (config.COL_APPROVAL_TO_MIS, config.COL_APPROVAL_FROM_FINANCE):
        if optional_date_col in df.columns:
            df[optional_date_col] = pd.to_datetime(df[optional_date_col], errors="coerce")

    return df


def compute_report_status(report_date, shared_with_cp) -> str:
    """
    Determine Report Status for one row of the Reports Update sheet.

    Rules:
        Shared           -> "Shared with CP" contains a valid date
        Pending to Share -> "Report Date" has a date, "Shared with CP" is blank
        No Info Found    -> both fields are blank

    Args:
        report_date: Value from the "Report Date" column (Timestamp or NaT).
        shared_with_cp: Value from the "Shared with CP" column (Timestamp or NaT).

    Returns:
        One of the REPORT_STATUS_* constants from config.py.
    """
    if pd.notna(shared_with_cp):
        return config.REPORT_STATUS_SHARED
    elif pd.notna(report_date):
        return config.REPORT_STATUS_PENDING_TO_SHARE
    else:
        return config.REPORT_STATUS_NO_INFO_FOUND


def enrich_reports_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add the 'Report Status' column to the reports DataFrame.

    Args:
        df: Raw reports DataFrame (with parsed date columns).

    Returns:
        A new DataFrame with the additional 'Report Status' column.
    """
    df = df.copy()
    df[config.COL_REPORT_STATUS] = df.apply(
        lambda row: compute_report_status(
            row[config.COL_REPORT_DATE], row[config.COL_SHARED_WITH_CP]
        ),
        axis=1,
    )
    return df


def _normalize_label(value) -> str:
    """Normalize a label for matching (trims whitespace, case-insensitive)."""
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()


def dedupe_latest_per_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse the reports DataFrame down to one row per label, keeping
    only the LAST occurrence of each label as it appears in the Excel
    sheet (i.e. bottom-most row = most recent entry).

    Matching is case-insensitive / whitespace-trimmed, same as
    attach_agreement_status, so "Sony Music " and "Sony Music" collapse
    to a single label instead of being treated as different labels.

    Args:
        df: Raw or enriched reports DataFrame (must contain COL_TV_STUDIOS).
            Must still be in original sheet order for "last row wins" to
            mean what it says -- call this before any sorting/filtering.

    Returns:
        A new DataFrame with exactly one row per distinct label.
    """
    df = df.copy()
    df["_match_key"] = df[config.COL_TV_STUDIOS].apply(_normalize_label)
    df = df.drop_duplicates(subset="_match_key", keep="last")
    df = df.drop(columns=["_match_key"]).reset_index(drop=True)
    return df


def attach_agreement_status(
    reports_df: pd.DataFrame, agreements_enriched_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Match each row's "TV Studios" label against the Agreement Monitor's
    "Label Name" and pull in the already-computed Agreement Status
    (reusing compute_status / enrich_dataframe -- status is never
    recalculated here, just looked up).

    Matching is case-insensitive and whitespace-trimmed to tolerate minor
    inconsistencies between the two sheets (e.g. "Sony Music " vs
    "Sony Music"). Labels with no match in the Agreements sheet get
    Agreement Status = "Unknown" rather than crashing or being dropped.

    Args:
        reports_df: Enriched reports DataFrame (must contain COL_TV_STUDIOS).
        agreements_enriched_df: Agreements DataFrame already run through
            utils.enrich_dataframe (must contain COL_LABEL_NAME, COL_STATUS).

    Returns:
        A new DataFrame with an added 'Agreement Status' column.
    """
    reports_df = reports_df.copy()

    if agreements_enriched_df.empty or config.COL_STATUS not in agreements_enriched_df.columns:
        reports_df[config.COL_AGREEMENT_STATUS] = config.STATUS_UNKNOWN
        return reports_df

    lookup = (
        agreements_enriched_df[[config.COL_LABEL_NAME, config.COL_STATUS]]
        .drop_duplicates(subset=[config.COL_LABEL_NAME], keep="last")
        .copy()
    )
    lookup["_match_key"] = lookup[config.COL_LABEL_NAME].apply(_normalize_label)
    lookup = lookup.set_index("_match_key")[config.COL_STATUS]

    reports_df["_match_key"] = reports_df[config.COL_TV_STUDIOS].apply(_normalize_label)
    reports_df[config.COL_AGREEMENT_STATUS] = (
        reports_df["_match_key"].map(lookup).fillna(config.STATUS_UNKNOWN)
    )
    reports_df = reports_df.drop(columns=["_match_key"])

    return reports_df

def attach_approval_month(
    reports_df: pd.DataFrame, agreements_enriched_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Match each row's "TV Studios" label against the Agreements sheet's
    "Label Name" and pull in the already-computed Approval Upto (Month)
    display value -- same normalized-label matching as
    attach_agreement_status, reusing the value rather than recomputing it.
    """
    reports_df = reports_df.copy()

    if (
        agreements_enriched_df.empty
        or config.COL_APPROVAL_MONTH_DISPLAY not in agreements_enriched_df.columns
    ):
        reports_df[config.COL_APPROVAL_MONTH_DISPLAY] = "—"
        return reports_df

    lookup = (
        agreements_enriched_df[[config.COL_LABEL_NAME, config.COL_APPROVAL_MONTH_DISPLAY]]
        .drop_duplicates(subset=[config.COL_LABEL_NAME], keep="last")
        .copy()
    )
    lookup["_match_key"] = lookup[config.COL_LABEL_NAME].apply(_normalize_label)
    lookup = lookup.set_index("_match_key")[config.COL_APPROVAL_MONTH_DISPLAY]

    reports_df["_match_key"] = reports_df[config.COL_TV_STUDIOS].apply(_normalize_label)
    reports_df[config.COL_APPROVAL_MONTH_DISPLAY] = (
        reports_df["_match_key"].map(lookup).fillna("—")
    )
    reports_df = reports_df.drop(columns=["_match_key"])

    return reports_df

def label_badge_html(label: str, agreement_status: str) -> str:
    """
    Render the TV Studios / Label Name with its background colored
    according to Agreement Status (Green/Yellow/Orange/Red), reusing the
    same color map as the Agreement Monitor's Status badges.
    """
    bg_color = config.STATUS_COLORS.get(agreement_status, config.STATUS_COLORS[config.STATUS_UNKNOWN])
    text_color = config.STATUS_TEXT_COLORS.get(agreement_status, "#ffffff")
    return colored_badge_html(label, bg_color, text_color)


def report_status_badge_html(status: str) -> str:
    """
    Render a colored badge for Report Status (Green/Yellow/Red), separate
    from the Agreement Status color coding.
    """
    bg_color = config.REPORT_STATUS_COLORS.get(status, "#6c757d")
    text_color = config.REPORT_STATUS_TEXT_COLORS.get(status, "#ffffff")
    return colored_badge_html(status, bg_color, text_color)