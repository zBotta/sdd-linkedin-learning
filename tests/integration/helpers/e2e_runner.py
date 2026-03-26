from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class E2ERunResult:
    mode: str
    scraped_count: int
    new_count: int
    processed_count: int
    discovery_candidate_count: int
    push_applied: bool
    status: str


def run_e2e_with_fallback(
    run_once: callable,
) -> E2ERunResult:
    first = run_once(full_rescrape=False)
    if int(first.get("new_count", 0)) != 0:
        processed = int(first.get("processed_count", first.get("new_count", 0)))
        return E2ERunResult(
            mode="incremental_only",
            scraped_count=int(first.get("scraped_count", 0)),
            new_count=int(first.get("new_count", 0)),
            processed_count=processed,
            discovery_candidate_count=int(first.get("discovery_candidate_count", 0)),
            push_applied=bool(first.get("push_applied", False)),
            status="passed" if processed >= 1 and bool(first.get("push_applied", False)) else "failed",
        )

    fallback = run_once(full_rescrape=True)
    processed = int(fallback.get("processed_count", fallback.get("new_count", 0)))
    return E2ERunResult(
        mode="incremental_then_full_rescrape",
        scraped_count=int(fallback.get("scraped_count", 0)),
        new_count=int(fallback.get("new_count", 0)),
        processed_count=processed,
        discovery_candidate_count=int(fallback.get("discovery_candidate_count", 0)),
        push_applied=bool(fallback.get("push_applied", False)),
        status="passed" if processed >= 1 and bool(fallback.get("push_applied", False)) else "failed",
    )
