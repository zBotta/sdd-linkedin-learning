from __future__ import annotations

from typing import Any

from .config import LocalSyncConfig


class LinkedInSavedScraper:
    """Playwright scaffold that reuses a local browser profile for session auth."""

    def __init__(self, config: LocalSyncConfig) -> None:
        self._config = config

    def fetch_saved_posts(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Open LinkedIn saved posts with a persistent context and return extracted rows.

        The extraction selectors are intentionally minimal for phase 1 and are expected
        to be hardened in later slices.
        """
        from playwright.sync_api import sync_playwright

        self._config.linkedin_profile_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self._config.linkedin_profile_dir),
                headless=self._config.linkedin_headless,
            )
            page = context.new_page()
            page.goto("https://www.linkedin.com/my-items/saved-posts/", wait_until="domcontentloaded")

            if "login" in page.url:
                print(
                    "LinkedIn login is required in the opened browser. Complete login and press Enter here to continue."
                )
                input()
                page.goto("https://www.linkedin.com/my-items/saved-posts/", wait_until="domcontentloaded")

            extracted = self._extract_stub(page, limit=limit)
            context.close()
            return extracted

    def _extract_stub(self, page: Any, limit: int) -> list[dict[str, Any]]:
        """
        Placeholder extraction routine for phase 1.

        This method intentionally returns an empty list by default to keep scope
        focused on local sync plumbing and testability.
        """
        _ = page
        _ = limit
        return []
