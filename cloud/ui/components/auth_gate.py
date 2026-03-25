from __future__ import annotations

import os

import streamlit as st


def expected_password() -> str:
    return os.getenv("UI_ACCESS_PASSWORD", "dev-ui-password")


def is_valid_password(candidate: str) -> bool:
    return bool(candidate) and candidate == expected_password()


def require_auth() -> None:
    if st.session_state.get("ui_authenticated"):
        return

    st.sidebar.subheader("Authentication")
    password = st.sidebar.text_input("Access password", type="password")
    if st.sidebar.button("Sign in"):
        if is_valid_password(password):
            st.session_state["ui_authenticated"] = True
            st.sidebar.success("Authenticated")
            st.rerun()
        else:
            st.sidebar.error("Invalid password")

    st.title("LinkedIn Saved Library")
    st.info("Sign in from the sidebar to access the hosted library.")
    st.stop()
