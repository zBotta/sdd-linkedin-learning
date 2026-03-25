from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from cloud.ui.components.auth_gate import require_auth
from cloud.ui.data_access import UILibraryRepository
from cloud.ui.pages.home import render_home, render_inbox
from cloud.ui.pages.review import render as render_review
from cloud.ui.pages.search import render as render_search
from cloud.ui.pages.settings import render as render_settings
from cloud.ui.pages.topics import render as render_topics
from shared.db import Database


@st.cache_resource
def get_repository(db_path: str) -> UILibraryRepository:
    db = Database(Path(db_path))
    db.initialize()
    return UILibraryRepository(db)


def main() -> None:
    st.set_page_config(page_title="LinkedIn Saved Library", layout="wide")
    require_auth()

    db_path = os.getenv("CLOUD_DB_PATH", ".state/library.db")
    repo = get_repository(db_path)

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Page",
        ["Home", "Inbox", "Topics", "Search", "Review", "Settings"],
    )

    if page == "Home":
        render_home(repo)
    elif page == "Inbox":
        render_inbox(repo)
    elif page == "Topics":
        render_topics(repo)
    elif page == "Search":
        render_search(repo)
    elif page == "Review":
        render_review(repo)
    elif page == "Settings":
        render_settings(repo)


if __name__ == "__main__":
    main()
