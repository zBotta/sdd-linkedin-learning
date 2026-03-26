from __future__ import annotations

import streamlit as st

from cloud.ui.components.notes_panel import render_notes_panel
from cloud.ui.data_access import UILibraryRepository


def render(repo: UILibraryRepository) -> None:
    st.header("Review")

    low_conf = repo.review_low_confidence()
    unmatched = repo.review_unmatched()
    candidates = repo.review_candidates()

    st.subheader("Low-confidence assignments")
    if low_conf:
        for row in low_conf:
            with st.expander(f"{row.get('title') or '(untitled)'} | {row.get('confidence')}"):
                if row.get("url"):
                    st.markdown(f"[Open LinkedIn post]({row['url']})")
                st.write(row.get("content", ""))
                col_a, col_b = st.columns(2)
                if col_a.button("Approve", key=f"approve-{row['source']}-{row['source_post_id']}"):
                    repo.apply_assignment_action(row["source"], row["source_post_id"], action="approve")
                    st.success("Approved")
                    st.rerun()
                new_primary = col_b.text_input(
                    "Reassign primary topic slug",
                    key=f"reassign-input-{row['source']}-{row['source_post_id']}",
                )
                if col_b.button("Reassign", key=f"reassign-btn-{row['source']}-{row['source_post_id']}"):
                    if new_primary.strip():
                        repo.apply_assignment_action(
                            row["source"],
                            row["source_post_id"],
                            action="reassign",
                            primary_topic_slug=new_primary.strip(),
                        )
                        st.success("Primary topic updated")
                        st.rerun()
                sec_input = st.text_input(
                    "Secondary topics (comma-separated slugs)",
                    key=f"secondary-{row['source']}-{row['source_post_id']}",
                )
                if st.button("Adjust secondary", key=f"secondary-btn-{row['source']}-{row['source_post_id']}"):
                    slugs = [item.strip() for item in sec_input.split(",") if item.strip()]
                    repo.apply_assignment_action(
                        row["source"],
                        row["source_post_id"],
                        action="adjust_secondary",
                        secondary_topic_slugs=slugs,
                    )
                    st.success("Secondary topics updated")
                    st.rerun()
                render_notes_panel(repo, row["source"], row["source_post_id"], key_prefix=f"review-{row['source']}-{row['source_post_id']}")
    else:
        st.info("No low-confidence items.")

    st.subheader("Unmatched posts")
    if unmatched:
        st.dataframe(unmatched, use_container_width=True)
    else:
        st.info("No unmatched posts.")

    st.subheader("Discovery candidates")
    if candidates:
        for row in candidates:
            with st.expander(f"{row['label']} | confidence={row.get('confidence')}"):
                st.write(f"Keywords: {', '.join(row.get('keywords', []))}")
                action = st.selectbox(
                    "Decision",
                    ["promote", "merge", "reject"],
                    key=f"decision-{row['id']}",
                )
                target = st.text_input("Target topic slug (for merge)", key=f"target-{row['id']}")
                if st.button("Apply decision", key=f"decide-{row['id']}"):
                    repo.decide_candidate(row["id"], action, target_topic_slug=target or None)
                    st.success("Decision applied")
                    st.rerun()
    else:
        st.info("No pending topic candidates.")

    if st.button("Manual backlog reprocess"):
        run_id = repo.trigger_manual_reprocess()
        st.success(f"Manual reprocess queued: {run_id}")
