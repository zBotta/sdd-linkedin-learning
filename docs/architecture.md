# Architecture

## V1 topology

The system uses a hybrid topology with strict local/cloud boundaries.

- Local machine:
  - LinkedIn authenticated session access
  - Saved-post extraction and normalization
  - Deduplication and local classification
  - JSON delta push to cloud ingest API
- Cloud EC2 host:
  - FastAPI ingest service
  - Streamlit UI
  - Canonical SQLite database
  - Backup and restore automation

## Module boundaries

- `local_sync/`:
  - scraping and preprocessing
  - taxonomy assignment
  - topic discovery
  - topic label refinement
  - delta push orchestration
- `cloud/api/`:
  - ingest and review endpoints
  - auth enforcement
  - idempotent upsert services
- `cloud/ui/`:
  - authenticated browse/search/review UI
  - notes and diagnostics views
- `shared/`:
  - database schema/connection
  - common models and schemas
  - taxonomy utilities

## Data flow

1. Local sync agent reads Saved posts from local browser context.
2. Agent normalizes content, deduplicates, and classifies locally.
3. Agent sends authenticated JSON deltas to cloud ingest API.
4. Cloud ingest service applies idempotent upserts into SQLite.
5. Streamlit UI reads live SQLite state through repository layer.

## Deployment runtime

- Single EC2 instance
- Docker Compose with two services (API and UI)
- Shared persistent data directory mounted into both containers
- SQLite in WAL mode for concurrent read/write behavior
- Healthchecks and restart policies for low-ops recovery

## Non-goals in V1

- Multi-user tenancy
- Cloud-side LinkedIn authentication/scraping
- PostgreSQL or distributed infrastructure
- Kubernetes-based orchestration
