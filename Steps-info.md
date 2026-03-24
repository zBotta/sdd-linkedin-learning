# SDD overview

1. .constitution
   Define permanent project rules and constraints.

2. .specify
   Define what users need and what V1 or the feature must do.

3. .clarify
   Resolve ambiguity, hidden assumptions, and decision gaps.

4. .plan
   Design the technical solution that satisfies the clarified spec.

5. .tasks
   Break the plan into ordered, testable implementation work.

6. .implement
   Build one approved slice at a time.

# .constitution

This project is a single-user personal knowledge library for LinkedIn Saved posts. The system must optimize for simplicity, low maintenance, low recurring cost, privacy/security, mostly automated operation, and easy extension later.

Permanent engineering and product principles:

1. Single-user first
- Design only for one user in V1.
- Do not add multi-user abstractions, roles, or tenancy unless explicitly required later.

2. Local-first privacy boundary
- LinkedIn authentication must happen only on the local machine.
- Never store LinkedIn credentials, cookies, or browser session state in the cloud.
- Cloud infrastructure must never perform LinkedIn scraping.

3. Delta sync, not DB-file sync
- Do not sync by copying a SQLite file from local to cloud.
- The local agent must send JSON deltas.
- The cloud API must perform idempotent upserts.
- The UI must stay online and read the live database.

4. BERTopic-centered classification
- The classification system is built around BERTopic.
- Keep three concerns separate:
  - taxonomy_assignment
  - topic_discovery
  - topic_label_refinement
- Do not collapse these into one opaque pipeline.

5. Stable labels first, discovery second
- Stable taxonomy assignment is the default classification path.
- Emerging-topic discovery is secondary and supports promotion into the stable taxonomy.
- Known topics must remain consistent over time.

6. Local inference over paid APIs
- Prefer local models and local inference wherever practical.
- The system must not require paid LLM/API usage for V1.
- Local LLM usage should be optional for basic ingestion and primarily used for topic naming/refinement.

7. Low-ops cloud architecture
- Use the smallest practical hosted footprint.
- Prefer simple, inspectable infrastructure over distributed complexity.
- Avoid introducing services that materially increase maintenance burden.

8. Clear separation of responsibilities
- Local machine: scraping, normalization, deduplication, classification, delta push.
- Cloud: authenticated ingest API, canonical database, hosted UI, persistence, backups.

9. Safe persistence and backup
- Treat SQLite as a live database, not a file to replace casually.
- Backups must use SQLite-safe methods for a live database.
- The system must preserve data across EC2 restarts and failures.

10. Reviewable automation
- Automate scheduled sync, local classification, cloud deployment bootstrap, health checks, restarts, and backups.
- Do not automate LinkedIn MFA/captcha resolution, credential recovery, or unsafe login behavior.

11. Modularity and replaceability
- Keep scraper, preprocessing, taxonomy assignment, discovery, label refinement, ingest API, UI, and shared data models modular.
- Future migration paths should remain possible without major rewrites.

12. Quality expectations
- Favor simple, readable, testable code.
- Preserve observability with run metadata, sync diagnostics, and classification metadata.
- Record taxonomy versions and model versions for reproducibility.

# .specify

Build a single-user personal knowledge library that ingests my Saved posts from LinkedIn, classifies them into stable study topics, discovers emerging topics, stores everything in a searchable database, and exposes a web UI so I can browse it from my phone or work computer.

Primary use case:
- I save interesting posts on LinkedIn.
- A local sync agent collects them from my local authenticated browser session.
- The posts are classified into study topics such as Small Language Models, Rust, MCP, Agents, etc.
- I can browse, search, review, and annotate them in a hosted library.

V1 goals:
- Local LinkedIn Saved-post sync
- Local classification using BERTopic
- Stable taxonomy assignment for known topics
- Emerging-topic discovery for unknown themes
- Searchable hosted library with review workflow
- Authenticated remote access
- Low-maintenance deployment and backup

Core product behavior:

1. Local ingestion
- The system shall run a local sync agent that accesses LinkedIn Saved posts using the user’s local authenticated browser session.
- The agent shall scrape post text and metadata, normalize content, deduplicate records, classify locally, and push new/updated records to the cloud.

2. Stable labeling
- The system shall assign posts to predefined stable topics using BERTopic zero-shot topic modeling with a predefined taxonomy.
- Known topics should remain stable over time.
- Taxonomy matching thresholds must be configurable.
- Example predefined topics include:
  - Small Language Models
  - Rust
  - MCP
  - Agents
  - Vector Databases
  - RAG
  - Edge AI
  - AI Governance
  - Benchmarking
  - Career / Leadership

3. Emerging-topic discovery
- The system shall periodically discover new themes from unmatched or low-confidence posts.
- Discovered topics shall be presented as reviewable candidates before promotion into the stable taxonomy.
- Candidate topics should have readable names and keywords.

4. Review workflow
- The user shall be able to review low-confidence assignments and discovered topic candidates.
- The user shall be able to approve, merge, reject, or promote discovered topics.
- Promoted topics shall become part of the stable taxonomy for future ingestion.

5. Search and browse
- The user shall be able to browse posts by topic.
- The user shall be able to search full text across title, content, summaries, labels, and notes.
- The user shall be able to annotate posts with notes.

6. Remote access
- The library shall be hosted in the cloud and accessible from phone and work browser.
- The UI shall require authentication.
- The ingest API shall require authentication.

7. Canonical storage
- The cloud system shall maintain the canonical database.
- Local sync shall push JSON deltas and the cloud shall apply idempotent upserts.
- Syncing must not require replacing the database file or restarting the UI.

Core domain entities:
- posts
- topics
- post_topics
- topic_runs
- topic_candidates
- notes

Data expectations for posts:
- source and source_post_id
- URL
- author
- published_at and saved_at
- title and content
- content_hash
- language
- metadata/raw payload
- summary
- importance and novelty scores
- status
- timestamps

Required V1 pages:
- Home
- Inbox
- Topics
- Search
- Review
- Settings

Page expectations:
- Home: last sync time, total posts, new posts, discovered topic candidates, review backlog, topic distribution
- Inbox: newly ingested posts, assigned stable topics, confidence, approval/edit actions
- Topics: stable taxonomy topics, discovered topics, topic detail view, post list per topic
- Search: full-text search with topic/date/status/source/confidence filters
- Review: low-confidence assignments, unmatched posts, discovered topic candidates awaiting decisions
- Settings: taxonomy version, thresholds, sync diagnostics, BERTopic model settings summary

In scope for V1:
- LinkedIn Saved-post local sync
- BERTopic zero-shot taxonomy assignment
- BERTopic discovery job for unmatched/low-confidence posts
- local LLM-based topic naming/refinement
- cloud ingest API
- SQLite canonical DB
- Streamlit UI
- topic browsing
- full-text search
- review queue
- notes
- incremental sync
- authenticated remote access
- automated deployment/bootstrap
- automated local sync scheduling
- backups

Out of scope for V1:
- multi-user support
- native mobile app
- browser extension
- storing LinkedIn credentials in backend/cloud
- cloud-side LinkedIn scraping
- replacing SQLite with Postgres
- mandatory paid LLM/API usage

Acceptance criteria for V1:
- I can authenticate locally and sync LinkedIn Saved posts.
- New posts are classified into predefined stable topics using BERTopic zero-shot mode.
- Unmatched or uncertain posts can be processed by a discovery pipeline.
- Discovered topic candidates get readable labels with BERTopic representation models and local LLM refinement.
- I can approve or merge discovered topics into the stable taxonomy.
- The canonical library is hosted remotely and accessible through an authenticated UI.
- The ingest API is authenticated.
- SQLite persists across EC2 restarts.
- Syncing does not require DB-file replacement or UI restart.
- A safe backup path exists.
- The system remains single-user and low-maintenance.

# .clarify

Please clarify the following product and implementation decisions for V1. Prioritize simplicity, low maintenance, privacy, and low recurring cost. Where appropriate, propose a default recommendation and explain the tradeoff.

1. LinkedIn extraction reliability
- What exact Saved-page navigation and extraction strategy should be assumed?
- Can classification rely on content visible in the Saved list, or should the scraper open individual posts only when needed?

2. Weak-content enrichment
- For short or low-context posts, what enrichment sources should be attempted in priority order?
- Should article title, repost commentary, linked snippet, and visible metadata be part of normalized content?

3. Raw storage policy
- Should V1 persist normalized JSON only, or also raw HTML snapshots?
- What are the privacy, storage, and debugging tradeoffs?

4. Taxonomy assignment granularity
- Should zero-shot assignment run per post, or in small local batches?
- What batch size or strategy is best for BERTopic-based ingestion?

5. Confidence and multi-topic policy
- How should confidence be scored when a post matches multiple predefined topics?
- Should V1 allow one primary topic plus secondary topics, or only one stable label?

6. Discovery job scope
- Should discovery run on unmatched posts only, low-confidence posts too, a rolling recent window, or a combination?
- What is the simplest useful discovery cadence for V1?

7. Promotion workflow
- What exact user flow should exist for approving, merging, rejecting, and promoting discovered topics?
- After promotion, should old unmatched posts be reprocessed automatically, manually, or not at all in V1?

8. Local model defaults
- What embedding model should be the default local embedding model?
- What GGUF llama.cpp-compatible model should be the default for topic naming/refinement?

9. Summaries in V1
- Should post summaries and cluster summaries be included in V1, or deferred?
- If included, are they required or optional when the local LLM is disabled?

10. Review UX boundaries
- Which review actions are essential in V1 versus deferrable?
- What is the minimum workflow needed to keep the system useful without overbuilding?

Please surface any hidden assumptions or risks that would materially affect the plan.

# .plan
Create a technical plan for this system using the following implementation intent.

Architecture:
- Hybrid architecture with a local machine and a cloud instance.
- Local machine runs the LinkedIn sync + classification agent.
- Cloud instance runs the canonical library app.

Important architecture rule:
- Do not sync by copying a SQLite file from local to cloud and restarting the app.
- Local agent sends JSON deltas.
- Cloud API performs idempotent upserts.
- Streamlit UI remains online and reads the live database.

Local responsibilities:
- access LinkedIn using the local authenticated browser session
- scrape Saved posts
- normalize and deduplicate post data
- run classification locally
- push only new/updated records to the cloud

Cloud responsibilities:
- expose an authenticated ingest API
- store the canonical database
- serve the web UI
- provide authenticated remote access
- keep data persisted and backed up

Core classification design:
- BERTopic is part of the core design.
- Separate these modules:
  - taxonomy_assignment
  - topic_discovery
  - topic_label_refinement

Taxonomy assignment:
- Use BERTopic zero-shot topic modeling with:
  - zeroshot_topic_list
  - configurable zeroshot_min_similarity
  - versioned topics.yaml as source of truth

Topic discovery:
- Run periodically over unmatched posts, low-confidence posts, and/or a rolling recent window as clarified.
- Suggested BERTopic stack:
  - embedding model
  - UMAP
  - HDBSCAN
  - CountVectorizer
  - c-TF-IDF
  - representation models

Topic label refinement:
- Use BERTopic representation models for readable labels, including:
  - KeyBERTInspired
  - MaximalMarginalRelevance
  - LlamaCPP
- Local LLM is primarily for cluster naming, label refinement, and optional summaries.
- Basic ingestion should still work if LLM refinement is disabled.

Preprocessing guidance:
- LinkedIn saved posts are often short-to-medium text.
- Enrich weak-content posts where possible with repost commentary, article title, linked snippet, and visible metadata.
- Do not over-preprocess away context before embedding.

Security constraints:
- Never store LinkedIn credentials in the cloud.
- Use Playwright locally with manual local authentication and optional local session reuse.
- Cloud must only receive authenticated JSON payloads.

Tech stack:
- Local sync and cloud services in Python
- FastAPI for ingest service
- Streamlit for UI
- SQLite as canonical DB
- SQLite FTS5 for search
- SQLite WAL mode for live app behavior
- EC2 as deployment target
- Docker and Docker Compose for service packaging
- EBS-backed storage for DB persistence
- AWS Systems Manager Parameter Store for secrets/config
- Docker healthchecks and restart policies
- EC2 user data for bootstrap automation

Required API endpoints:
- POST /ingest/batch
- GET /health
- GET /sync-status
- POST /topic-runs
- GET /topic-candidates
- POST /topic-candidates/{id}/decision

Required DB entities:
- posts
- topics
- post_topics
- topic_runs
- topic_candidates
- notes
- FTS5 indexes over title, content, summary, and notes

Backup strategy:
- Do not naively copy a live SQLite DB file.
- Use a SQLite-safe backup approach.
- Optionally support EBS snapshots for recovery.

Suggested repo structure:
repo/
├─ local_sync/
│  ├─ sync_agent.py
│  ├─ linkedin_scraper.py
│  ├─ preprocessing.py
│  ├─ taxonomy_assignment.py
│  ├─ topic_discovery.py
│  ├─ topic_label_refinement.py
│  ├─ state_store.py
│  ├─ push_client.py
│  └─ config.py
├─ cloud/
│  ├─ api/
│  │  ├─ main.py
│  │  ├─ routes/
│  │  ├─ services/
│  │  └─ auth.py
│  ├─ ui/
│  │  ├─ app.py
│  │  ├─ pages/
│  │  └─ components/
│  ├─ docker-compose.yml
│  ├─ Dockerfile.api
│  ├─ Dockerfile.ui
│  └─ bootstrap/
│     └─ ec2_user_data.sh
├─ shared/
│  ├─ db.py
│  ├─ models.py
│  ├─ schemas.py
│  ├─ taxonomy.py
│  └─ utils.py
├─ scripts/
│  ├─ init_db.py
│  ├─ backup_db.py
│  └─ healthcheck.sh
├─ topics.yaml
├─ pyproject.toml
└─ README.md

Planning goals:
- turn the product spec into an implementation plan with phases, module boundaries, data flows, deployment design, and risk mitigation
- keep the system simple, single-user, and low-ops
- explicitly call out assumptions and unresolved risks
- prefer phased delivery over big-bang implementation

# .tasks
/speckit.tasks
Generate implementation tasks from the approved spec and plan.

Requirements for task generation:
- Organize tasks by the following phases:
  1. local sync prototype
  2. stable classification
  3. discovery pipeline
  4. cloud storage + ingest API
  5. Streamlit UI
  6. deployment automation
- Include setup, tests, schema work, observability, docs, and deployment tasks.
- Respect module boundaries between local_sync, cloud, and shared.
- Prefer vertical slices that produce demonstrable progress.
- Mark dependencies clearly.
- Keep V1 single-user and low-maintenance.
- Do not include out-of-scope features.

# Implement

## Phase 1
/speckit.implement
Implement Phase 1 only: local sync prototype.

Build:
- Playwright-based local scraper scaffold
- manual local auth/session reuse flow
- normalization pipeline
- deduplication/content hashing
- local checkpoint/state persistence
- normalized post JSON export
- basic config loading
- tests for normalization and deduplication

Do not start cloud, BERTopic discovery, or UI work yet.
Keep code modular so later phases can plug in taxonomy assignment and push-to-cloud.

## Phase 2
/speckit.implement
Implement Phase 2 only: stable classification.

Build:
- versioned topics.yaml support
- taxonomy loader/validator
- BERTopic zero-shot taxonomy assignment module
- configurable similarity threshold
- classification metadata persistence
- tests for topic assignment behavior and confidence thresholds

Do not implement discovery pipeline or cloud deployment yet.
Preserve separation between taxonomy_assignment and future topic_discovery/topic_label_refinement modules.

## Phase 3
/speckit.implement
Implement Phase 3 only: discovery pipeline.

Build:
- BERTopic clustering pipeline for unmatched or low-confidence items
- candidate-topic persistence model
- representation stack with KeyBERTInspired, MMR, and optional LlamaCPP refinement
- run metadata recording
- tests around candidate generation and pipeline boundaries

Do not merge discovery, taxonomy assignment, and label refinement into one module.

## Phase 4
/speckit.implement
Implement Phase 4 only: cloud storage and ingest API.

Build:
- FastAPI ingest service
- authenticated ingest token flow
- SQLite schema for posts, topics, post_topics, topic_runs, topic_candidates, notes
- idempotent upsert logic for JSON deltas
- GET /health
- GET /sync-status
- POST /ingest/batch
- POST /topic-runs
- GET /topic-candidates
- POST /topic-candidates/{id}/decision
- FTS5 search support
- tests for auth, validation, and idempotent upserts

Do not implement Streamlit pages or deployment automation yet.
Keep cloud/api and shared modules cleanly separated.

## Phase 5
/speckit.implement
Implement Phase 5 only: Streamlit UI.

Build:
- Streamlit app structure with pages:
  - Home
  - Inbox
  - Topics
  - Search
  - Review
  - Settings
- authenticated access for the UI
- topic browsing
- search UI over FTS-backed content
- review actions for low-confidence items and discovered topic candidates
- notes support
- sync diagnostics and settings summary
- tests for page-level data access and key flows where practical

Do not implement EC2 bootstrap or backup automation yet.
Keep the UI read-friendly for phone and work-browser use.

## Phase 6
/speckit.implement
Implement Phase 6 only: deployment automation.

Build:
- Dockerfile.api
- Dockerfile.ui
- docker-compose.yml
- healthchecks
- restart policies
- EC2 user-data bootstrap script
- Parameter Store integration for secrets/config
- persistent SQLite storage on EBS-backed volume
- backup script using a SQLite-safe live-backup approach
- deployment and recovery documentation

Do not add Postgres, Kubernetes, or other higher-ops infrastructure.
Preserve the single-user, low-maintenance architecture.
