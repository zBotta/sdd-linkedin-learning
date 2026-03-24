from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS ingest_batches (
  batch_id TEXT PRIMARY KEY,
  sent_at TEXT NOT NULL,
  source TEXT NOT NULL,
  applied INTEGER NOT NULL DEFAULT 1,
  processed INTEGER NOT NULL DEFAULT 0,
  errors INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL,
  finished_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
  source TEXT NOT NULL,
  source_post_id TEXT NOT NULL,
  url TEXT,
  author TEXT,
  published_at TEXT,
  saved_at TEXT,
  title TEXT,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  language TEXT,
  metadata_json TEXT,
  summary TEXT,
  importance_score REAL,
  novelty_score REAL,
  status TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (source, source_post_id)
);

CREATE TABLE IF NOT EXISTS topics (
  slug TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  source_type TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (slug, taxonomy_version)
);

CREATE TABLE IF NOT EXISTS post_topics (
  post_source TEXT NOT NULL,
  post_source_id TEXT NOT NULL,
  topic_slug TEXT NOT NULL,
  role TEXT NOT NULL,
  confidence REAL NOT NULL,
  assignment_source TEXT,
  review_state TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (post_source, post_source_id, topic_slug, role, assignment_source)
);

CREATE TABLE IF NOT EXISTS topic_runs (
  id TEXT PRIMARY KEY,
  run_type TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  representation_config TEXT,
  input_count INTEGER,
  output_count INTEGER,
  error_count INTEGER,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  diagnostics_json TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS topic_candidates (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  keywords_json TEXT,
  evidence_count INTEGER NOT NULL,
  confidence REAL,
  state TEXT NOT NULL,
  merged_into_topic_slug TEXT,
  run_id TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  post_source TEXT NOT NULL,
  post_source_id TEXT NOT NULL,
  body TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
  source UNINDEXED,
  source_post_id UNINDEXED,
  title,
  content,
  summary,
  notes
);
"""


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @property
    def path(self) -> Path:
        return self._db_path

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
        finally:
            conn.close()
