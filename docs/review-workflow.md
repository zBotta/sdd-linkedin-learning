# Review And Reprocess Workflow

## Purpose

This guide documents the V1 review loop for discovery candidates and explicit backlog reprocessing.

## Candidate Review Actions

- Approve assignment when a low-confidence post is still correct.
- Reassign primary topic when a better stable topic is known.
- Adjust secondary topics when additional context is useful.
- Promote candidate to a new stable topic when evidence is strong.
- Merge candidate into an existing stable topic when overlap is high.
- Reject candidate when evidence is weak or noisy.

## Manual Backlog Reprocess

Reprocessing is manual by design in V1.

- Trigger `SyncAgent.manual_reprocess_backlog(...)` from an explicit operator action.
- The command reruns stable assignment and discovery over the backlog.
- Discovery run metadata and candidates are appended to state logs.
- This action is never run automatically during normal sync cycles.

## Operational Notes

- Keep taxonomy updates versioned in [topics.yaml](../topics.yaml).
- Review candidates before promotion to preserve label stability.
- Use discovery telemetry to monitor candidate volume and confidence drift.
