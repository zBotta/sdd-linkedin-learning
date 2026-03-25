from __future__ import annotations

import streamlit as st

from cloud.ui.data_access import UILibraryRepository


def render_notes_panel(repo: UILibraryRepository, post_source: str, post_source_id: str, key_prefix: str) -> None:
    st.subheader("Notes")
    notes = repo.list_post_notes(post_source, post_source_id)
    for note in notes[:3]:
        st.caption(f"Updated: {note['updated_at']}")
        st.write(note["body"])

    body = st.text_area("Add or update note", key=f"{key_prefix}-note-body")
    if st.button("Save note", key=f"{key_prefix}-save-note"):
        if body.strip():
            repo.upsert_note(post_source, post_source_id, body.strip())
            st.success("Note saved")
            st.rerun()
        else:
            st.warning("Note body is empty")
