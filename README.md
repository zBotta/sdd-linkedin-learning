# sdd-linkedin-learning
A project to learn from LinkedIn saved posts using Spec-Driven Development.

## Project focus

Single-user personal knowledge library for LinkedIn Saved posts with an emphasis on:

- simplicity
- low maintenance
- low recurring cost
- privacy and security
- mostly automated operation
- easy extension over time

## Architecture boundaries (V1)

- Local machine handles LinkedIn authentication, scraping, normalization,
	deduplication, classification, and delta generation.
- Cloud handles authenticated ingest API, canonical database persistence,
	hosted UI, and backups.
- Sync occurs via JSON deltas with idempotent upserts; SQLite DB-file copy sync
	is not allowed.

## Classification strategy

Classification is BERTopic-centered with strict separation of concerns:

- taxonomy_assignment
- topic_discovery
- topic_label_refinement

Stable taxonomy labels are the default path; emerging-topic discovery is
secondary and supports promotion into the stable taxonomy.

## Governance

Engineering and product principles are defined in:

- `.specify/memory/constitution.md`

All specs, plans, tasks, and implementation changes must comply with the
constitution.

## Spec Kit with Codex
After installing Spec Kit, run the following to start a Codex-compatible spec-driven list of skills.
```
specify init . --ai codex --ai-skills
```

