from __future__ import annotations

import streamlit as st

from cloud.ui.data_access import UILibraryRepository


def render(repo: UILibraryRepository) -> None:
    st.header("Topics")

    data = repo.topics_overview()
    stable_topics = data["stable_topics"]
    candidates = data["candidates"]

    st.subheader("Stable taxonomy")
    if stable_topics:
        st.dataframe(stable_topics, use_container_width=True)
    else:
        st.info("No stable topics yet.")

    st.subheader("Discovered candidates")
    if candidates:
        st.dataframe(candidates, use_container_width=True)
    else:
        st.info("No discovery candidates yet.")
