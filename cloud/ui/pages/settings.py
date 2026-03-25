from __future__ import annotations

import streamlit as st

from cloud.ui.data_access import UILibraryRepository


def render(repo: UILibraryRepository) -> None:
    st.header("Settings")
    summary = repo.settings_summary()

    st.subheader("Taxonomy versions")
    st.dataframe(summary.get("taxonomy_versions", []), use_container_width=True)

    st.subheader("Thresholds")
    st.json(summary.get("thresholds", {}))

    st.subheader("Latest sync diagnostics")
    latest_sync = summary.get("latest_sync")
    if latest_sync:
        st.json(latest_sync)
    else:
        st.info("No sync runs yet.")

    st.subheader("Recent topic runs")
    st.dataframe(summary.get("recent_topic_runs", []), use_container_width=True)
