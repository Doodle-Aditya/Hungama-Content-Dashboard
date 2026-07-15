"""
config.py

Central configuration file for the Content Operations Dashboard.

Keeping all constants, thresholds, file paths, and static configuration
in a single module makes the application easy to extend. Future modules
(Report Tracking, Approval Tracking, Automated Email Notifications,
Client Summary Dashboard, Automatic Report Dispatch) can import from
this same file instead of hard-coding values elsewhere.
"""

import os


# ----------------------------------------------------------------------
# EXCEL SHEET NAMES
# ----------------------------------------------------------------------
# Both workbooks now contain several sheets, so sheets are targeted by
# NAME rather than position -- position was only safe when each workbook
# had exactly the two sheets we cared about, in a known order.

AGREEMENTS_SHEET_NAME = "Master"          # in Master_Label_Dashboard.xlsx
REPORTS_SHEET_NAME = "Reports Update"     # in Revenue_Summary_1.xlsx

# ----------------------------------------------------------------------
# EXPECTED EXCEL COLUMNS -- AGREEMENT MONITOR (Master sheet)
# ----------------------------------------------------------------------

COL_LABEL_NAME = "Label Name"
COL_START_DATE = "Start Date"
COL_EXPIRY_DATE = "Expiry Date"   # canonical name used everywhere downstream

# Optional column on the Master sheet holding a real date representing
# approval coverage upto a certain month (e.g. 31-03-2025).
COL_APPROVAL_UPTO = "Approval upto"

# Derived, display-only column: the same date reformatted as "Month YYYY"
# (e.g. "March 2025"). Named distinctly from the sheet's own separate
# "Approval Month" column (different meaning) to avoid any collision.
COL_APPROVAL_MONTH_DISPLAY = "Approval Upto (Month)"

# The Master sheet calls this column "End Date" instead of "Expiry Date".
# We read using this raw name, then rename it to COL_EXPIRY_DATE right
# after loading, so status computation / dashboard.py / report_tracker.py's
# label matching never need to know the source column was named differently.
SOURCE_COL_END_DATE = "End Date"

# Columns required on the RAW sheet, before the End Date -> Expiry Date rename.
RAW_AGREEMENTS_REQUIRED_COLUMNS = [COL_LABEL_NAME, COL_START_DATE, SOURCE_COL_END_DATE]

# Columns required AFTER the rename (used by enrich_dataframe etc.) --
# unchanged from before, so nothing downstream needs to change.
REQUIRED_COLUMNS = [COL_LABEL_NAME, COL_START_DATE, COL_EXPIRY_DATE]

# ----------------------------------------------------------------------
# DERIVED COLUMN NAMES (added by the app after processing)
# ----------------------------------------------------------------------

COL_DAYS_REMAINING = "Days Remaining"
COL_STATUS = "Status"

# ----------------------------------------------------------------------
# STATUS LABELS
# ----------------------------------------------------------------------

STATUS_ACTIVE = "Active"
STATUS_EXPIRING_SOON = "Expiring Soon"
STATUS_EXPIRES_TODAY = "Expires Today"
STATUS_EXPIRED = "Expired"
STATUS_UNKNOWN = "Unknown"  # used when S_FIldates are missing / invalid

ALL_STATUSES = [
    STATUS_ACTIVE,
    STATUS_EXPIRING_SOON,
    STATUS_EXPIRES_TODAY,
    STATUS_EXPIRED,
    STATUS_UNKNOWN
]

# ----------------------------------------------------------------------
# BUSINESS RULE THRESHOLDS
# ----------------------------------------------------------------------

# Number of days within which an agreement is considered "Expiring Soon"
EXPIRING_SOON_THRESHOLD_DAYS = 30

# ----------------------------------------------------------------------
# COLOR CODING (used for status badges / table styling / charts)
# ----------------------------------------------------------------------

STATUS_COLORS = {
    STATUS_ACTIVE: "#28a745",         # Green
    STATUS_EXPIRING_SOON: "#ffc107",  # Yellow
    STATUS_EXPIRES_TODAY: "#fd7e14",  # Orange
    STATUS_EXPIRED: "#dc3545",        # Red
    STATUS_UNKNOWN: "#6c757d",        # Grey (fallback)
}

# Text color to use on top of each status background (for contrast)
STATUS_TEXT_COLORS = {
    STATUS_ACTIVE: "#ffffff",
    STATUS_EXPIRING_SOON: "#000000",
    STATUS_EXPIRES_TODAY: "#ffffff",
    STATUS_EXPIRED: "#ffffff",
    STATUS_UNKNOWN: "#ffffff",
}

# ----------------------------------------------------------------------
# APP / UI CONFIGURATION
# ----------------------------------------------------------------------

APP_TITLE = "Content Operations Dashboard"
APP_ICON = "📋"
PAGE_LAYOUT = "wide"

# Sidebar filter options (dropdown for status filter)
STATUS_FILTER_OPTIONS = ["All"] + ALL_STATUSES


# ========================================================================
# REPORT TRACKER MODULE
# ------------------------------------------------------------------------
# Added for the "Report Tracker" page. Kept in a clearly separated block
# so the original Agreement Monitor configuration above is untouched.
# ========================================================================

# ----------------------------------------------------------------------
# REPORTS UPDATE SHEET — EXPECTED COLUMNS
# ----------------------------------------------------------------------

COL_TV_STUDIOS = "TV Studios"          # Label Name equivalent on this sheet
COL_PERIOD = "Period"
COL_REPORT_DATE = "Report Date"
COL_SHARED_WITH_CP = "Shared with CP"
COL_APPROVAL_TO_MIS = "Approval to MIS"
COL_APPROVAL_FROM_FINANCE = "Approval from Finance"

# Only these are required for report tracking (Version 1). Other
# operational columns present on the sheet (Approval to MIS, Approval
# from Finance, etc.) are read if present but are not mandatory.
REPORT_REQUIRED_COLUMNS = [
    COL_TV_STUDIOS,
    COL_PERIOD,
    COL_REPORT_DATE,
    COL_SHARED_WITH_CP,
]

# ----------------------------------------------------------------------
# DERIVED COLUMN NAMES (added after processing)
# ----------------------------------------------------------------------

COL_REPORT_STATUS = "Report Status"

# Agreement Status pulled in from the Agreements sheet, matched by label.
COL_AGREEMENT_STATUS = "Agreement Status"

# ----------------------------------------------------------------------
# REPORT STATUS LABELS
# ----------------------------------------------------------------------

REPORT_STATUS_SHARED = "Shared"
REPORT_STATUS_PENDING_TO_SHARE = "Pending to Share"
REPORT_STATUS_NO_INFO_FOUND = "No Info Found"

ALL_REPORT_STATUSES = [
    REPORT_STATUS_SHARED,
    REPORT_STATUS_PENDING_TO_SHARE,
    REPORT_STATUS_NO_INFO_FOUND,
]

REPORT_STATUS_FILTER_OPTIONS = ["All"] + ALL_REPORT_STATUSES

# ----------------------------------------------------------------------
# REPORT STATUS COLOR CODING
# ----------------------------------------------------------------------

REPORT_STATUS_COLORS = {
    REPORT_STATUS_SHARED: "#28a745",           # Green
    REPORT_STATUS_PENDING_TO_SHARE: "#ffc107",  # Yellow
    REPORT_STATUS_NO_INFO_FOUND: "#dc3545",     # Red
}

REPORT_STATUS_TEXT_COLORS = {
    REPORT_STATUS_SHARED: "#ffffff",
    REPORT_STATUS_PENDING_TO_SHARE: "#000000",
    REPORT_STATUS_NO_INFO_FOUND: "#ffffff",
}

# ----------------------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------------------

REPORT_TRACKER_TITLE = "Report Tracker"
REPORT_TRACKER_ICON = "🗂️"