from __future__ import annotations

from scripts import validate_phase6


def test_e2e_stage_falls_back_to_full_rescrape_when_incremental_has_zero_new() -> None:
    calls: list[tuple[bool, int]] = []

    def fake_sync_runner(*, full_rescrape: bool, limit: int) -> dict:
        calls.append((full_rescrape, limit))
        if not full_rescrape:
            return {
                "scraped_count": 4,
                "new_count": 0,
                "processed_count": 0,
                "push_applied": False,
                "discovery_candidate_count": 0,
            }
        return {
            "scraped_count": 5,
            "new_count": 2,
            "processed_count": 2,
            "push_applied": True,
            "discovery_candidate_count": 1,
        }

    stage = validate_phase6.run_e2e_stage(sample_limit=10, sync_runner=fake_sync_runner)

    assert calls == [(False, 10), (True, 10)]
    assert stage["status"] == "passed"
    assert stage["metadata"]["mode"] == "incremental_then_full_rescrape"
    assert stage["metadata"]["processed_count"] == 2
    assert stage["metadata"]["push_applied"] is True


def test_e2e_stage_can_disable_full_rescrape_fallback() -> None:
    calls: list[tuple[bool, int]] = []

    def fake_sync_runner(*, full_rescrape: bool, limit: int) -> dict:
        calls.append((full_rescrape, limit))
        return {
            "scraped_count": 10,
            "new_count": 0,
            "processed_count": 0,
            "push_applied": False,
            "discovery_candidate_count": 0,
        }

    stage = validate_phase6.run_e2e_stage(
        sample_limit=10,
        sync_runner=fake_sync_runner,
        allow_full_rescrape_fallback=False,
    )

    assert calls == [(False, 10)]
    assert stage["status"] == "failed"
    assert stage["metadata"]["mode"] == "incremental_only_no_fallback"
