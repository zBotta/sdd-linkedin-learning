# V1 Scope Guardrails

## Included

- Single-user library workflows
- Local LinkedIn Saved-post ingestion and classification
- Stable-topic assignment and candidate discovery
- Authenticated cloud ingest API
- Authenticated Streamlit UI for browse/search/review/notes
- SQLite canonical persistence with safe backup and restore automation
- EC2 deployment with Docker Compose, healthchecks, and restart policies

## Excluded

- Multi-user roles, teams, or tenancy
- Native mobile application
- Browser extension delivery
- Cloud-side LinkedIn login/session handling
- Replacing SQLite with PostgreSQL
- Kubernetes or higher-ops orchestration platforms
- Mandatory paid API dependencies for core ingestion/classification

## Security and privacy boundaries

- LinkedIn credentials/session state stay local only.
- Cloud receives only authenticated JSON deltas.
- Secrets are sourced from Parameter Store and not hardcoded.

## Operational principles

- Prefer simple, inspectable runtime components.
- Keep automated tasks reviewable and failure-visible.
- Preserve recoverability through tested backup and restore drills.
