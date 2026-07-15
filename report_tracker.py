"""
report_tracker.py

UI rendering logic for the "Report Tracker" page, following the exact
same pattern as dashboard.py (Agreement Monitor):

- config.py holds constants.
- utils.py holds pure data logic (loading, status computation, matching).
- This file only renders Streamlit UI from already-processed DataFrames.
- pages/1_Report_Tracker.py is the thin entry point that wires it together.

No Agreement Monitor code (app.py / dashboard.py) is modified or
duplicated here -- Agreement Status and Approval Upto (Month) are reused
via utils.attach_agreement_status / utils.attach_approval_month, which
look up values already computed by utils.enrich_dataframe.

NOTE: This page shows one row per label (most recent Excel entry only --
see utils.dedupe_latest_per_label), and exposes Agreement Status, Period,
and Approval Month as filters. Report Date / Shared with CP / Report
Status are not shown here.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

import config
import utils


def render_export_button(df: pd.DataFrame) -> None:
    """
    Render a download button that exports the currently filtered reports
    table as an .xlsx file. Values are already plain text (no HTML badges
    at this stage), so no reformatting is needed before export.
    """
    if df.empty:
        return

    columns_to_export = [
        config.COL_TV_STUDIOS,
        config.COL_PERIOD,
        config.COL_AGREEMENT_STATUS,
        config.COL_APPROVAL_MONTH_DISPLAY,
    ]
    columns_to_export = [c for c in columns_to_export if c in df.columns]

    excel_bytes = utils.to_excel_bytes(df[columns_to_export], sheet_name="Report Tracker")

    st.download_button(
        label="⬇️ Export filtered data (Excel)",
        data=excel_bytes,
        file_name=f"report_tracker_{pd.Timestamp.today().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="report_tracker_export_button",
    )

    

# SIDEBAR FILTERS


def render_sidebar_filters(df: pd.DataFrame) -> tuple[str, str, str]:
    """
    Render sidebar filter controls for the Report Tracker page.

    Args:
        df: Enriched (deduped) reports DataFrame, used to populate the
            Period and Approval Month dropdowns with actual values
            present in the data.

    Returns:
        Tuple of (agreement_status_filter, period_filter, approval_month_filter).
    """
    st.sidebar.header("🔍 Filters")

    agreement_status_filter = st.sidebar.selectbox(
        "Agreement Status",
        options=config.STATUS_FILTER_OPTIONS,
        index=0,
        key="report_tracker_agreement_status",
    )

    period_options = ["All"]
    if not df.empty and config.COL_PERIOD in df.columns:
        period_options += sorted(
            df[config.COL_PERIOD].dropna().astype(str).unique().tolist()
        )
    period_filter = st.sidebar.selectbox(
        "Period",
        options=period_options,
        index=0,
        key="report_tracker_period",
    )

    approval_month_options = ["All"]
    if not df.empty and config.COL_APPROVAL_MONTH_DISPLAY in df.columns:
        approval_month_options += sorted(
            df[config.COL_APPROVAL_MONTH_DISPLAY]
            .dropna()
            .astype(str)
            .loc[lambda s: s != "—"]
            .unique()
            .tolist()
        )
    approval_month_filter = st.sidebar.selectbox(
        "Approval Month",
        options=approval_month_options,
        index=0,
        key="report_tracker_approval_month",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Data as of **{pd.Timestamp.today().strftime('%d-%b-%Y')}**"
    )

    return agreement_status_filter, period_filter, approval_month_filter


def apply_filters(
    df: pd.DataFrame,
    agreement_status_filter: str,
    period_filter: str,
    approval_month_filter: str,
) -> pd.DataFrame:
    """Apply sidebar filter selections to the (deduped) reports DataFrame."""
    filtered = df.copy()

    if agreement_status_filter and agreement_status_filter != "All":
        filtered = filtered[filtered[config.COL_AGREEMENT_STATUS] == agreement_status_filter]

    if period_filter and period_filter != "All":
        filtered = filtered[filtered[config.COL_PERIOD].astype(str) == period_filter]

    if approval_month_filter and approval_month_filter != "All":
        filtered = filtered[
            filtered[config.COL_APPROVAL_MONTH_DISPLAY] == approval_month_filter
        ]

    return filtered



# KPI CARDS


def render_kpi_cards(df: pd.DataFrame) -> None:
    """
    Render the top-of-page KPI summary cards for the Report Tracker.

    Broken down by Agreement Status. df is expected to already be
    deduped to one row per label.

    Args:
        df: Enriched, deduped reports DataFrame (unfiltered, so KPIs
            always reflect the full label set regardless of table filters).
    """
    total_labels = len(df)
    active_count = (df[config.COL_AGREEMENT_STATUS] == config.STATUS_ACTIVE).sum()
    expiring_soon_count = (df[config.COL_AGREEMENT_STATUS] == config.STATUS_EXPIRING_SOON).sum()
    expiring_today_count = (df[config.COL_AGREEMENT_STATUS] == config.STATUS_EXPIRES_TODAY).sum()
    expired_count = (df[config.COL_AGREEMENT_STATUS] == config.STATUS_EXPIRED).sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Labels", total_labels)
    col2.metric("Active Agreements", int(active_count))
    col3.metric("Expiring in 30 Days", int(expiring_soon_count))
    col4.metric("Expiring Today", int(expiring_today_count))
    col5.metric("Expired Agreements", int(expired_count))



# VISUALIZATION


def render_agreement_status_pie_chart(df: pd.DataFrame) -> None:
    """
    Render a pie chart showing the distribution of Agreement Status
    across labels on this page.
    """
    if df.empty:
        st.info("No data available to plot.")
        return

    status_counts = (
        df[config.COL_AGREEMENT_STATUS]
        .value_counts()
        .reindex(config.ALL_STATUSES + [config.STATUS_UNKNOWN], fill_value=0)
        .reset_index()
    )
    status_counts.columns = ["Agreement Status", "Count"]
    status_counts = status_counts[status_counts["Count"] > 0]

    fig = px.pie(
        status_counts,
        names="Agreement Status",
        values="Count",
        color="Agreement Status",
        color_discrete_map=config.STATUS_COLORS,
        hole=0.45,
    )
    fig.update_traces(textinfo="label+percent")
    fig.update_layout(margin=dict(t=30, b=10, l=10, r=10), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)



# DATA TABLE


def render_reports_table(df: pd.DataFrame) -> None:
    """
    Render a searchable, color-coded table of report tracking records --
    one row per label (most recent Excel entry).

    Report Date, Shared with CP, and Report Status are intentionally
    omitted. Agreement Status is shown both as the label's background
    color and as its own text badge column. Approval Upto (Month) is
    shown last.
    """
    st.subheader(f"Report Details ({len(df)} record{'s' if len(df) != 1 else ''})")

    if df.empty:
        st.warning("No reports match the current filters.")
        return

    display_df = df.copy()

    display_df[config.COL_TV_STUDIOS] = df.apply(
        lambda row: utils.label_badge_html(
            row[config.COL_TV_STUDIOS], row[config.COL_AGREEMENT_STATUS]
        ),
        axis=1,
    )
    display_df[config.COL_AGREEMENT_STATUS] = df[config.COL_AGREEMENT_STATUS].apply(
        utils.status_badge_html
    )

    columns_to_show = [
        config.COL_TV_STUDIOS,
        config.COL_PERIOD,
        config.COL_AGREEMENT_STATUS,
        config.COL_APPROVAL_MONTH_DISPLAY,
    ]
    columns_to_show = [c for c in columns_to_show if c in display_df.columns]

    table_html = display_df[columns_to_show].to_html(escape=False, index=False)

    styled_html = f"""
    <div style="overflow-x:auto;">
    <style>
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        th {{
            background-color: #f0f2f6;
            text-align: left;
            padding: 8px 12px;
            border-bottom: 2px solid #ddd;
        }}
        td {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background-color: #fafafa;
        }}
    </style>
    {table_html}
    </div>
    """
    st.markdown(styled_html, unsafe_allow_html=True)