"""
dashboard.py

All Streamlit UI rendering logic for the Content Operations Dashboard lives
here, kept separate from app.py (entry point) and utils.py (pure data
logic). This separation means:

- app.py stays a thin orchestrator.
- Future modules (Report Tracking, Approval Tracking, etc.) can add their
  own dashboard_<module>.py files following the same pattern, without
  touching this file.

Each function renders one section of the page and takes the processed
DataFrame (already enriched with Days Remaining / Status / Approval Upto
(Month)) as input.
"""

from __future__ import annotations

import calendar

import pandas as pd
import plotly.express as px
import streamlit as st

import config
import utils


# ----------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------

def render_sidebar_filters(df: pd.DataFrame) -> tuple[str, str, str]:
    """
    Render sidebar filter controls.

    Args:
        df: Enriched agreements DataFrame (used to populate the Approval
            Month dropdown with actual values present in the data; the
            actual filtering happens in app.py).

    Returns:
        Tuple of (search_text, status_filter, approval_month_filter).
    """
    st.sidebar.header("🔍 Filters")

    search_text = st.sidebar.text_input(
        "Search Label",
        placeholder="Type a label name...",
    )

    status_filter = st.sidebar.selectbox(
        "Status Filter",
        options=config.STATUS_FILTER_OPTIONS,
        index=0,
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
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Data as of **{pd.Timestamp.today().strftime('%d-%b-%Y')}**"
    )

    return search_text, status_filter, approval_month_filter


def apply_filters(
    df: pd.DataFrame,
    search_text: str,
    status_filter: str,
    approval_month_filter: str,
) -> pd.DataFrame:
    """
    Apply sidebar filter selections to the DataFrame.

    Args:
        df: Enriched agreements DataFrame.
        search_text: Free-text search on Label Name.
        status_filter: One of config.STATUS_FILTER_OPTIONS.
        approval_month_filter: "All" or a specific "Month YYYY" value.

    Returns:
        Filtered DataFrame.
    """
    filtered = df.copy()

    if search_text:
        filtered = filtered[
            filtered[config.COL_LABEL_NAME]
            .astype(str)
            .str.contains(search_text, case=False, na=False)
        ]

    if status_filter and status_filter != "All":
        filtered = filtered[filtered[config.COL_STATUS] == status_filter]

    if approval_month_filter and approval_month_filter != "All":
        filtered = filtered[
            filtered[config.COL_APPROVAL_MONTH_DISPLAY] == approval_month_filter
        ]

    return filtered


# ----------------------------------------------------------------------
# KPI CARDS (The cards which are showing the number.)
# ----------------------------------------------------------------------

def render_kpi_cards(df: pd.DataFrame) -> None:
    """
    Render the top-of-page KPI summary cards.

    Args:
        df: Enriched agreements DataFrame (unfiltered, so KPIs always
            reflect the full dataset regardless of table filters).
    """
    total_labels = len(df)
    active_count = (df[config.COL_STATUS] == config.STATUS_ACTIVE).sum()
    expired_count = (df[config.COL_STATUS] == config.STATUS_EXPIRED).sum()
    expiring_soon_count = (df[config.COL_STATUS] == config.STATUS_EXPIRING_SOON).sum()
    expiring_today_count = (df[config.COL_STATUS] == config.STATUS_EXPIRES_TODAY).sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Labels", total_labels)
    col2.metric("Active Agreements", int(active_count))
    col3.metric("Expired Agreements", int(expired_count))
    col4.metric("Expiring in 30 Days", int(expiring_soon_count))
    col5.metric("Expiring Today", int(expiring_today_count))


# ----------------------------------------------------------------------
# VISUALIZATIONS (Pie chart and graph)
# ----------------------------------------------------------------------

def render_status_pie_chart(df: pd.DataFrame) -> None:
    """
    Render a pie chart showing the distribution of Active / Expired /
    Expiring Soon / Expires Today agreements.
    """
    if df.empty:
        st.info("No data available to plot.")
        return

    status_counts = (
        df[config.COL_STATUS]
        .value_counts()
        .reindex(config.ALL_STATUSES, fill_value=0)
        .reset_index()
    )
    status_counts.columns = ["Status", "Count"]
    # Drop statuses with zero count for a cleaner chart
    status_counts = status_counts[status_counts["Count"] > 0]

    fig = px.pie(
        status_counts,
        names="Status",
        values="Count",
        color="Status",
        color_discrete_map=config.STATUS_COLORS,
        hole=0.45,
    )
    fig.update_traces(textinfo="label+percent")
    fig.update_layout(
        margin=dict(t=30, b=10, l=10, r=10),
        legend_title_text="",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_monthly_expiry_bar_chart(df: pd.DataFrame) -> None:
    """
    Render a bar chart showing the number of agreements expiring each
    calendar month (based on Expiry Date, across all years present).
    """
    valid_df = df.dropna(subset=[config.COL_EXPIRY_DATE])

    if valid_df.empty:
        st.info("No expiry dates available to plot.")
        return

    monthly = valid_df.copy()
    monthly["Month"] = monthly[config.COL_EXPIRY_DATE].dt.month
    monthly["Year"] = monthly[config.COL_EXPIRY_DATE].dt.year
    monthly["Year-Month"] = monthly[config.COL_EXPIRY_DATE].dt.to_period("M").astype(str)

    grouped = (
        monthly.groupby("Year-Month")
        .size()
        .reset_index(name="Count")
        .sort_values("Year-Month")
    )

    fig = px.bar(
        grouped,
        x="Year-Month",
        y="Count",
        text="Count",
        labels={"Year-Month": "Month", "Count": "Agreements Expiring"},
        color_discrete_sequence=["#4C78A8"],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        margin=dict(t=30, b=10, l=10, r=10),
        xaxis_title="",
        yaxis_title="Agreements Expiring",
    )
    st.plotly_chart(fig, use_container_width=True)

def render_export_button(df: pd.DataFrame) -> None:
    """
    Render a download button that exports the currently filtered
    agreements table as an .xlsx file. Uses plain text values (not the
    HTML badges used on screen) so the exported file opens cleanly in
    Excel.
    """
    if df.empty:
        return

    export_df = df.copy()
    export_df[config.COL_START_DATE] = export_df[config.COL_START_DATE].apply(utils.format_date)
    export_df[config.COL_EXPIRY_DATE] = export_df[config.COL_EXPIRY_DATE].apply(utils.format_date)
    export_df[config.COL_DAYS_REMAINING] = df[config.COL_DAYS_REMAINING].apply(
        utils.format_days_remaining
    )
    # Status and Approval Month are already plain text values -- no reformatting needed.

    columns_to_export = [
        config.COL_LABEL_NAME,
        config.COL_START_DATE,
        config.COL_EXPIRY_DATE,
        config.COL_DAYS_REMAINING,
        config.COL_STATUS,
        config.COL_APPROVAL_MONTH_DISPLAY,
    ]
    columns_to_export = [c for c in columns_to_export if c in export_df.columns]

    excel_bytes = utils.to_excel_bytes(export_df[columns_to_export], sheet_name="Agreements")

    st.download_button(
        label="⬇️ Export filtered data (Excel)",
        data=excel_bytes,
        file_name=f"agreement_monitor_{pd.Timestamp.today().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="agreement_monitor_export_button",
    )

def render_visualizations(df: pd.DataFrame) -> None:
    """Render the pie chart and bar chart side by side."""
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Status Distribution")
        render_status_pie_chart(df)

    with chart_col2:
        st.subheader("Agreements Expiring by Month")
        render_monthly_expiry_bar_chart(df)


# ----------------------------------------------------------------------
# DATA TABLE
# ----------------------------------------------------------------------

def render_agreements_table(df: pd.DataFrame) -> None:
    """
    Render a searchable, color-coded table of agreements.

    Uses an HTML table (via st.markdown) so the Status column can be
    rendered as colored badges, since Streamlit's native dataframe
    widget does not support per-cell colored badges out of the box.
    """
    st.subheader(f"Agreement Details ({len(df)} record{'s' if len(df) != 1 else ''})")

    if df.empty:
        st.warning("No agreements match the current filters.")
        return

    display_df = df.copy()
    display_df[config.COL_START_DATE] = display_df[config.COL_START_DATE].apply(utils.format_date)
    display_df[config.COL_EXPIRY_DATE] = display_df[config.COL_EXPIRY_DATE].apply(utils.format_date)
    display_df[config.COL_DAYS_REMAINING] = df[config.COL_DAYS_REMAINING].apply(
        utils.format_days_remaining
    )
    display_df[config.COL_STATUS] = df[config.COL_STATUS].apply(utils.status_badge_html)

    columns_to_show = [
        config.COL_LABEL_NAME,
        config.COL_START_DATE,
        config.COL_EXPIRY_DATE,
        config.COL_DAYS_REMAINING,
        config.COL_STATUS,
        config.COL_APPROVAL_MONTH_DISPLAY,
    ]
    columns_to_show = [c for c in columns_to_show if c in display_df.columns]

    table_html = display_df[columns_to_show].to_html(escape=False, index=False)

    # Light styling wrapper so the table matches the dashboard theme.
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
