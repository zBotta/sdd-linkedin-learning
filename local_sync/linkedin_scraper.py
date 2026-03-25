from __future__ import annotations

import re
import os
from datetime import datetime, timezone
from typing import Any

from .config import LocalSyncConfig


class LinkedInSavedScraper:
    """Playwright scaffold that reuses a local browser profile for session auth."""

    def __init__(self, config: LocalSyncConfig) -> None:
        self._config = config

    def fetch_saved_posts(
        self,
        limit: int = 100,
        *,
        seen_source_keys: set[str] | None = None,
        stop_on_first_seen: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Open LinkedIn saved posts with a persistent context and return extracted rows.

        The extraction selectors are intentionally minimal for phase 1 and are expected
        to be hardened in later slices.
        """
        from playwright.sync_api import sync_playwright

        self._config.linkedin_profile_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            launch_kwargs: dict[str, Any] = {
                "user_data_dir": str(self._config.linkedin_profile_dir),
                "headless": self._config.linkedin_headless,
            }

            executable_override = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "").strip()
            if executable_override:
                launch_kwargs["executable_path"] = executable_override

            try:
                context = playwright.chromium.launch_persistent_context(**launch_kwargs)
            except Exception as exc:
                # Fallback for environments where Playwright-managed Chromium download is blocked.
                if "Executable doesn't exist" in str(exc):
                    fallback_kwargs = dict(launch_kwargs)
                    fallback_kwargs.pop("executable_path", None)
                    try:
                        fallback_kwargs["channel"] = "chrome"
                        context = playwright.chromium.launch_persistent_context(**fallback_kwargs)
                    except Exception:
                        fallback_kwargs["channel"] = "msedge"
                        context = playwright.chromium.launch_persistent_context(**fallback_kwargs)
                else:
                    raise
            page = context.new_page()
            self._open_saved_posts(page)

            if self._requires_manual_auth(page.url):
                print(
                    "LinkedIn login/challenge is required in the opened browser. Complete verification and press Enter here to continue."
                )
                input()
                self._open_saved_posts(page)

            extracted = self._extract_stub(
                page,
                limit=limit,
                seen_source_keys=seen_source_keys or set(),
                stop_on_first_seen=stop_on_first_seen,
            )
            context.close()
            return extracted

    @staticmethod
    def _requires_manual_auth(url: str) -> bool:
        lowered = (url or "").lower()
        return any(marker in lowered for marker in ("/login", "/checkpoint", "/challenge"))

    @staticmethod
    def _safe_goto(page: Any, url: str) -> None:
        try:
            page.goto(url, wait_until="domcontentloaded")
        except Exception as exc:
            # LinkedIn often redirects login/checkpoint flows while navigation is in progress.
            # In that case Playwright reports an interrupted navigation; keep current page state.
            if "interrupted by another navigation" not in str(exc):
                raise

    def _open_saved_posts(self, page: Any) -> None:
        saved_posts_url = "https://www.linkedin.com/my-items/saved-posts/"
        self._safe_goto(page, saved_posts_url)
        if self._requires_manual_auth(page.url):
            return
        self._safe_goto(page, saved_posts_url)

    def _extract_stub(
        self,
        page: Any,
        limit: int,
        seen_source_keys: set[str],
        stop_on_first_seen: bool,
    ) -> list[dict[str, Any]]:
        """Best-effort extraction of saved post cards for phase-1 validation."""
        page.wait_for_timeout(1200)
        self._expand_see_more(page)

        # Load a small viewport window so first saved cards are available for extraction.
        for _ in range(3):
            try:
                page.mouse.wheel(0, 1800)
            except Exception:
                break
            page.wait_for_timeout(700)
            self._expand_see_more(page)

        raw_candidates = page.evaluate(
            r"""
            (maxItems) => {
                            const norm = (s) => (s || '')
                                .replace(/…\s*see more/gi, ' ')
                                .replace(/\.\.\.\s*see more/gi, ' ')
                                .replace(/\s+/g, ' ')
                                .trim();
              const anchors = Array.from(document.querySelectorAll(
                'a[href*="/feed/update/"],a[href*="/posts/"],a[href*="/pulse/"]'
              ));
              const seen = new Set();
              const rows = [];

              for (const a of anchors) {
                const href = a.href || '';
                if (!href || seen.has(href)) continue;
                seen.add(href);

                const card =
                  a.closest('article, li, div[class*="feed"], div[class*="update"], div[data-urn]') ||
                  a.closest('div') ||
                  a;

                const text = norm(card.innerText);
                if (!text) continue;

                const heading = card.querySelector('h1,h2,h3,strong');
                let title = heading ? norm(heading.textContent) : '';
                if (!title) title = norm(a.textContent);

                rows.push({
                  url: href,
                  text,
                  title,
                  idHint: card.getAttribute('data-urn') || card.getAttribute('data-id') || '',
                });
                if (rows.length >= maxItems) break;
              }

              return rows;
            }
            """,
            max(limit * 8, 20),
        )

        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_streak = 0
        max_seen_streak = 3
        for idx, row in enumerate(raw_candidates or []):
            if len(items) >= limit:
                break

            content = self._clean_text(row.get("text", ""))
            if len(content) < 60:
                continue

            post_url = row.get("url")
            source_post_id = self._derive_source_post_id_from_hint(row.get("idHint"), post_url, idx)

            source_key = f"linkedin_saved:{source_post_id}"
            if source_key in seen_source_keys:
                seen_streak += 1
                # LinkedIn cards are not always strictly ordered; only stop after
                # encountering a short consecutive run of already-synced posts.
                if stop_on_first_seen and len(items) > 0 and seen_streak >= max_seen_streak:
                    break
                continue
            seen_streak = 0

            if source_post_id in seen_ids:
                continue
            seen_ids.add(source_post_id)

            title = self._clean_text(row.get("title") or "")
            if not title:
                title = content[:120]

            items.append(
                {
                    "source": "linkedin_saved",
                    "source_post_id": source_post_id,
                    "title": title[:220],
                    "content": content,
                    "url": post_url,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "selector": "link_anchored",
                        "raw_url": post_url,
                    },
                }
            )

        return items

    def _expand_see_more(self, page: Any) -> None:
        selectors = [
            "button:has-text('See more')",
            "button:has-text('see more')",
            "a:has-text('See more')",
            "a:has-text('see more')",
            "span:has-text('See more')",
            "span:has-text('see more')",
            "[aria-label*='See more']",
            "[aria-label*='see more']",
        ]

        for selector in selectors:
            locator = page.locator(selector)
            try:
                count = min(locator.count(), 60)
            except Exception:
                continue

            for idx in range(count):
                element = locator.nth(idx)
                try:
                    element.scroll_into_view_if_needed(timeout=800)
                    element.click(timeout=800)
                except Exception:
                    continue

    @staticmethod
    def _safe_inner_text(locator: Any) -> str:
        try:
            return locator.inner_text(timeout=1500)
        except Exception:
            return ""

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _extract_primary_url(self, card: Any) -> str | None:
        anchors = card.locator("a[href]")
        try:
            count = anchors.count()
        except Exception:
            count = 0

        for idx in range(min(count, 20)):
            href = anchors.nth(idx).get_attribute("href")
            if not href:
                continue
            if "linkedin.com" not in href:
                continue
            if any(marker in href for marker in ("/feed/update/", "/posts/", "/pulse/")):
                return href

        return None

    def _extract_title(self, card: Any, fallback: str) -> str:
        candidates = [
            "h1",
            "h2",
            "h3",
            "strong",
            "a span[aria-hidden='true']",
        ]
        for selector in candidates:
            node = card.locator(selector).first
            try:
                text = self._clean_text(node.inner_text(timeout=800))
            except Exception:
                text = ""
            if text and len(text) >= 3:
                return text[:220]

        return fallback[:120]

    def _derive_source_post_id(self, card: Any, post_url: str | None, idx: int) -> str:
        data_urn = card.get_attribute("data-urn")
        if data_urn:
            return self._clean_text(data_urn)

        if post_url:
            match = re.search(r"urn:li:[^/?#]+", post_url)
            if match:
                return match.group(0)
            match = re.search(r"/(posts|feed/update)/([^/?#]+)", post_url)
            if match:
                return match.group(2)

        return f"saved-{int(datetime.now(timezone.utc).timestamp())}-{idx}"

    def _derive_source_post_id_from_hint(self, id_hint: str | None, post_url: str | None, idx: int) -> str:
        if id_hint:
            cleaned = self._clean_text(id_hint)
            if cleaned:
                return cleaned

        if post_url:
            match = re.search(r"urn:li:[^/?#]+", post_url)
            if match:
                return match.group(0)
            match = re.search(r"/(posts|feed/update)/([^/?#]+)", post_url)
            if match:
                return match.group(2)

        return f"saved-{int(datetime.now(timezone.utc).timestamp())}-{idx}"
