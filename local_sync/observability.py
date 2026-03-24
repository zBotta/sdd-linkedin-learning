from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DiscoveryTelemetry:
    candidate_count: int
    confidence_bands: dict[str, int]
    backlog_age_days: int
    scope_counts: dict[str, int] = field(default_factory=dict)


def build_confidence_bands(confidences: list[float]) -> dict[str, int]:
    bands = {"lt_0_4": 0, "0_4_to_0_7": 0, "gte_0_7": 0}
    for value in confidences:
        if value < 0.4:
            bands["lt_0_4"] += 1
        elif value < 0.7:
            bands["0_4_to_0_7"] += 1
        else:
            bands["gte_0_7"] += 1
    return bands