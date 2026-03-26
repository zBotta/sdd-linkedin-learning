from __future__ import annotations

from pathlib import Path

from scripts import validate_phase6


def test_embedding_passes_when_online_or_fallback_available() -> None:
    online_stage = validate_phase6.run_embedding_stage(
        online_available=True,
        fallback_path=None,
    )
    assert online_stage["status"] == "passed"
    assert online_stage["metadata"]["online_path_status"] == "passed"

    fallback_path = Path("tests/integration/embedding_fallback_test.bin")
    fallback_path.write_text("ok", encoding="utf-8")
    try:
        fallback_stage = validate_phase6.run_embedding_stage(
            online_available=False,
            fallback_path=str(fallback_path),
        )
    finally:
        if fallback_path.exists():
            try:
                fallback_path.unlink()
            except PermissionError:
                pass

    assert fallback_stage["status"] == "passed"
    assert fallback_stage["metadata"]["local_fallback_status"] == "passed"
    assert fallback_stage["metadata"]["fallback_path_valid"] is True


def test_invalid_fallback_returns_explicit_error_detail() -> None:
    bad_path = "tests/integration/does_not_exist.gguf"
    stage = validate_phase6.run_embedding_stage(
        online_available=False,
        fallback_path=bad_path,
    )

    assert stage["status"] == "failed"
    assert bad_path in stage["metadata"]["error_detail"]
    assert "invalid" in stage["metadata"]["error_detail"].lower()
