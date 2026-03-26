from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(slots=True)
class SQLTableVerification:
    table_name: str
    expected_min_updates: int
    observed_updates: int
    required_for_pass: bool
    status: str


def verify_sql_tables(
    db_path: str,
    expected_minimums: dict[str, int],
    *,
    require_topic_candidates: bool,
) -> dict[str, SQLTableVerification]:
    required_tables = {"posts", "post_topics", "topic_runs"}
    if require_topic_candidates:
        required_tables.add("topic_candidates")

    results: dict[str, SQLTableVerification] = {}
    with sqlite3.connect(db_path) as conn:
        for table_name, expected_min in expected_minimums.items():
            row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            observed = int(row[0] if row else 0)
            is_required = table_name in required_tables
            passed = observed >= expected_min if is_required else True
            results[table_name] = SQLTableVerification(
                table_name=table_name,
                expected_min_updates=expected_min,
                observed_updates=observed,
                required_for_pass=is_required,
                status="passed" if passed else "failed",
            )

    return results
