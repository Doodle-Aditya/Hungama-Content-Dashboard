"""
pages/1_Report_Tracker.py

Entry point for the "Report Tracker" page.

Both source workbooks are now uploaded via sidebar uploaders instead of
read from a fixed path:
- Revenue Summary (Reports Update sheet) -- uploaded here.
- Master Label Dashboard (for Agreement Status) -- shares the SAME
  session_state-backed uploader as the Agreement Monitor page, so
  uploading it on either page makes it available on both.

Shows one row per label (most recent Excel entry only -- see
utils.dedupe_latest_per_label), filterable by Agreement Status and Period.
"""

import pandas as pd
import streamlit as st

import config
import report_tracker
import utils


def main() -> None:
    st.set_page_config(
        page_title=config.REPORT_TRACKER_TITLE,
        page_icon=config.REPORT_TRACKER_ICON,
        layout=config.PAGE_LAYOUT,
    )

    st.title(f"{config.REPORT_TRACKER_ICON} {config.REPORT_TRACKER_TITLE}")
    st.caption(
        "One entry per label (most recent record) — filter by Agreement "
        "Status and Period — Legal · Finance · MIS"
    )

    # ------------------------------------------------------------------
    # FILE UPLOADS (sidebar). Reports file is specific to this page;
    # Agreements file is shared with the Agreement Monitor page.
    # ------------------------------------------------------------------
    reports_file = utils.render_reports_uploader()
    agreements_file = utils.render_agreements_uploader()

    if reports_file is None:
        st.info(
            "📥 Please upload the latest **Revenue Summary** (.xlsx) "
            "using the uploader in the sidebar to get started."
        )
        st.stop()

    # ------------------------------------------------------------------
    # DATA LOADING — Reports
    # ------------------------------------------------------------------
    try:
        raw_reports_df = utils.load_reports(reports_file)
    except ValueError as err:
        st.error(f"⚠️ {err}")
        st.stop()

    if raw_reports_df.empty:
        st.warning(
            f"No report tracking data found in the uploaded file. Please "
            f"make sure it has a sheet named '{config.REPORTS_SHEET_NAME}' "
            f"with columns: {', '.join(config.REPORT_REQUIRED_COLUMNS)}."
        )
        st.stop()

    # Collapse to one row per label -- last matching row in the sheet wins.
    # Must happen BEFORE any sorting/filtering so "last row" still means
    # "most recent" in the original Excel order.
    deduped_reports_df = utils.dedupe_latest_per_label(raw_reports_df)

    # ------------------------------------------------------------------
    # DATA LOADING — Agreements (for Agreement Status lookup)
    # ------------------------------------------------------------------
    if agreements_file is None:
        st.warning(
            "⚠️ Master Label Dashboard hasn't been uploaded yet. "
            "Agreement Status will show as 'Unknown' for all labels until "
            "you upload it in the sidebar."
        )
        agreements_enriched_df = pd.DataFrame()
    else:
        try:
            agreements_df = utils.load_agreements(agreements_file)
            agreements_enriched_df = utils.enrich_dataframe(agreements_df)
        except ValueError as err:
            st.warning(
                f"⚠️ Could not load Agreement data ({err}). Agreement "
                f"Status will show as 'Unknown' for all labels."
            )
            agreements_enriched_df = pd.DataFrame()

    # Attach Agreement Status by matching TV Studios <-> Label Name.
    reports_enriched_df = utils.attach_agreement_status(
        deduped_reports_df, agreements_enriched_df
    )
    # Attach Agreement Status by matching TV Studios <-> Label Name.
    reports_enriched_df = utils.attach_agreement_status(
        deduped_reports_df, agreements_enriched_df
    )

    # Attach Approval Upto (Month) the same way.
    reports_enriched_df = utils.attach_approval_month(
        reports_enriched_df, agreements_enriched_df
    )

    # ------------------------------------------------------------------
    # SIDEBAR FILTERS
    # ------------------------------------------------------------------
    agreement_status_filter, period_filter, approval_month_filter = (
        report_tracker.render_sidebar_filters(reports_enriched_df)
    )
    filtered_df = report_tracker.apply_filters(
        reports_enriched_df,
        agreement_status_filter,
        period_filter,
        approval_month_filter,
    )

    # ------------------------------------------------------------------
    # KPI CARDS (always reflect full deduped dataset, not the filtered view)
    # ------------------------------------------------------------------
    report_tracker.render_kpi_cards(reports_enriched_df)

    st.markdown("---")

    # ------------------------------------------------------------------
    # VISUALIZATION
    # ------------------------------------------------------------------
    st.subheader("Agreement Status Distribution")
    report_tracker.render_agreement_status_pie_chart(reports_enriched_df)

    st.markdown("---")

    # ------------------------------------------------------------------
    # EXPORT (reflects sidebar filters -- same rows as the table below)
    # ------------------------------------------------------------------
    report_tracker.render_export_button(filtered_df)

    # ------------------------------------------------------------------
    # DATA TABLE (reflects sidebar filters)
    # ------------------------------------------------------------------
    report_tracker.render_reports_table(filtered_df)


if __name__ == "__main__":
    main()