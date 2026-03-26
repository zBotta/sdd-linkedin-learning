from __future__ import annotations

from datetime import datetime

import streamlit as st

from cloud.ui.data_access import UILibraryRepository


def render(repo: UILibraryRepository) -> None:
    st.header("Search")

    col1, col2 = st.columns(2)
    query = col1.text_input("Full-text query")
    topic = col1.selectbox("Topic filter", ["", *repo.list_topics()])
    source = col2.selectbox("Source filter", ["", "linkedin_saved"])
    status = col2.selectbox("Status filter", ["", "new", "review", "approved", "archived"])
    min_conf = st.slider("Minimum confidence", 0.0, 1.0, 0.0, 0.05)
    date_col1, date_col2 = st.columns(2)
    date_from = date_col1.date_input("Saved from", value=None)
    date_to = date_col2.date_input("Saved to", value=None)

    parsed_date_from = None
    parsed_date_to = None
    if isinstance(date_from, datetime):
        parsed_date_from = date_from.date().isoformat()
    elif date_from:
        parsed_date_from = date_from.isoformat()
    if isinstance(date_to, datetime):
        parsed_date_to = date_to.date().isoformat()
    elif date_to:
        parsed_date_to = date_to.isoformat()

    if st.button("Run search"):
        rows = repo.search_posts(
            query=query,
            topic=topic or None,
            source=source or None,
            status=status or None,
            min_confidence=min_conf if min_conf > 0 else None,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            limit=100,
        )
        st.write(f"Results: {len(rows)}")
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No matches found.")
