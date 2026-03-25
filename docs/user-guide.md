# User Guide

## Accessing the hosted UI

1. Start the Streamlit app with `streamlit run cloud/ui/app.py`.
2. Open the URL in your desktop or mobile browser.
3. Enter the UI password from `UI_ACCESS_PASSWORD` in the sidebar.

## Home and Inbox

- Home shows totals for posts, new items, review backlog, candidate count, and last sync.
- Inbox lists recent posts and their current primary topic assignment.

## Topics

- Stable taxonomy table shows each topic and number of assigned posts.
- Candidate table shows discovery items pending review.

## Search

1. Enter a full-text query.
2. Optionally apply filters: topic, source, status, confidence, saved-from and saved-to dates.
3. Select **Run search** to view matching saved posts.

## Review

- Low-confidence assignments: approve, reassign primary topic, or adjust secondary topics.
- Discovery candidates: promote, merge into an existing topic, or reject.
- Manual backlog reprocess creates a queued topic run record for operator-driven reprocessing.

## Notes

- Open a post in Review and use the Notes panel.
- Enter note text and select **Save note**.
- Saved notes are persisted and included in search indexing.

## Settings

- View taxonomy versions in the database.
- Review configured confidence thresholds.
- Inspect latest sync status and recent topic run diagnostics.
