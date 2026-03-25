from __future__ import annotations

import streamlit as st


def render_status_cards(metrics: dict[str, object]) -> None:
    cols = st.columns(4)
    cols[0].metric("Total posts", int(metrics.get("total_posts", 0)))
    cols[1].metric("New posts", int(metrics.get("new_posts", 0)))
    cols[2].metric("Review backlog", int(metrics.get("review_backlog", 0)))
    cols[3].metric("Candidates", int(metrics.get("candidate_count", 0)))

    last_sync = metrics.get("last_sync")
    if last_sync:
        st.caption(f"Last sync: {last_sync}")
