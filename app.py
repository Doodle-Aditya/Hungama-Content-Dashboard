"""
app.py

Entry point for the Content Operations Dashboard.

Data is no longer read from a fixed path on disk -- the user uploads the
latest Master_Label_Dashboard.xlsx via a sidebar uploader each session,
and can re-upload at any time to refresh the data.
"""

import streamlit as st
import config
import dashboard
import utils


def main() -> None:
    # PAGE CONFIGURATION
     
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.APP_ICON,
        layout=config.PAGE_LAYOUT,
    )
    st.title(f"{config.APP_ICON} {config.APP_TITLE}")

    # FILE UPLOAD (sidebar uploader, persists via session_state so it
    # stays available on reruns and on the Report Tracker page too)
     
    agreements_file = utils.render_agreements_uploader()

    if agreements_file is None:
        st.info(
            "📥 Please upload the latest **Master Label Dashboard** "
            "(.xlsx) using the uploader in the sidebar to get started."
        )
        st.stop()     
    # DATA LOADING
     
    try:
        raw_df = utils.load_agreements(agreements_file)
    except ValueError as err:
        st.error(f"⚠️ {err}")
        st.stop()

    if raw_df.empty:
        st.warning(
            f"No data found in the uploaded file. Please make sure it has "
            f"a sheet named '{config.AGREEMENTS_SHEET_NAME}' with columns: "
            f"{', '.join(config.RAW_AGREEMENTS_REQUIRED_COLUMNS)}."
        )
        st.stop()

    # Compute Days Remaining + Status for every record (single source of truth).
    enriched_df = utils.enrich_dataframe(raw_df)

    # SIDEBAR FILTERS     
    search_text, status_filter, approval_month_filter = dashboard.render_sidebar_filters(
        enriched_df
    )
    filtered_df = dashboard.apply_filters(
        enriched_df, search_text, status_filter, approval_month_filter
    )

    # KPI CARDS (always reflect full dataset, not the filtered view)
     
    dashboard.render_kpi_cards(enriched_df)
    st.markdown("---")
 
    # VISUALIZATIONS (reflect full dataset for a stable overview)
     
    dashboard.render_visualizations(enriched_df)
    st.markdown("---")

    # DATA TABLE (reflects sidebar filters)     
    dashboard.render_agreements_table(filtered_df)
    st.markdown("---")

if __name__ == "__main__":
    main()