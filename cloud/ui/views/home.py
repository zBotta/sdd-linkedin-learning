from __future__ import annotations

import streamlit as st

from cloud.ui.components.status_cards import render_status_cards
from cloud.ui.data_access import UILibraryRepository


def render_home(repo: UILibraryRepository) -> None:
    st.header("Home")
    metrics = repo.home_metrics()
    render_status_cards(metrics)

    st.subheader("Topic distribution")
    distribution = metrics.get("topic_distribution", [])
    if distribution:
        st.bar_chart({row["topic"]: row["count"] for row in distribution})
    else:
        st.info("No topic assignments yet.")


def render_inbox(repo: UILibraryRepository) -> None:
    st.header("Inbox")
    rows = repo.inbox_posts(limit=100)
    if not rows:
        st.info("No posts in inbox yet.")
        return

    for row in rows:
        with st.expander(f"{row.get('title') or '(untitled)'} | {row.get('topic_slug') or 'unassigned'}"):
            st.caption(f"Saved: {row.get('saved_at')} | Confidence: {row.get('confidence')}")
            if row.get("url"):
                st.markdown(f"[Open LinkedIn post]({row['url']})")
            st.write(row.get("content", ""))
