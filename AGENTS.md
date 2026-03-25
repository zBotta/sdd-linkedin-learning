# sdd-linkedin-learning Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-25

## Active Technologies
- Python 3.11+ + Playwright (local scraping), FastAPI (cloud ingest), Streamlit (UI), Pydantic, sqlite3 (002-fix-scrape-diff)
- Local checkpoint JSON file for sync state; canonical cloud SQLite for ingested data (002-fix-scrape-diff)

- Python 3.11+ + FastAPI, Streamlit, Playwright, BERTopic, sentence-transformers, UMAP, HDBSCAN, scikit-learn, sqlite3, pydantic (001-linkedin-saved-library)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 002-fix-scrape-diff: Added Python 3.11+ + Playwright (local scraping), FastAPI (cloud ingest), Streamlit (UI), Pydantic, sqlite3

- 001-linkedin-saved-library: Added Python 3.11+ + FastAPI, Streamlit, Playwright, BERTopic, sentence-transformers, UMAP, HDBSCAN, scikit-learn, sqlite3, pydantic

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
