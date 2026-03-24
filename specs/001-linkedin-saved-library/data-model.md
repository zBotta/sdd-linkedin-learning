# Data Model: LinkedIn Saved Posts Knowledge Library (V1)

## Entity: Post (`posts`)
- Purpose: Canonical saved LinkedIn content record.
- Key fields:
  - `id` (UUID)
  - `source` (text, expected: `linkedin_saved`)
  - `source_post_id` (text, unique with source)
  - `url` (text)
  - `author` (text)
  - `published_at` (datetime, nullable)
  - `saved_at` (datetime)
  - `title` (text, nullable)
  - `content` (text)
  - `content_hash` (text)
  - `language` (text, nullable)
  - `metadata_json` (text/json)
  - `summary` (text, nullable)
  - `importance_score` (real, nullable)
  - `novelty_score` (real, nullable)
  - `status` (text: `new|review|approved|archived`)
  - `created_at` / `updated_at` (datetime)
- Validation:
  - (`source`, `source_post_id`) unique.
  - `content_hash` required for dedup.
- State transitions:
  - `new -> review -> approved|archived`

## Entity: Topic (`topics`)
- Purpose: Stable taxonomy topics and promoted topics.
- Key fields:
  - `id` (UUID)
  - `name` (text, unique)
  - `slug` (text, unique)
  - `description` (text, nullable)
  - `taxonomy_version` (text)
  - `is_active` (boolean)
  - `source_type` (text: `predefined|promoted`)
  - `created_at` / `updated_at` (datetime)

## Entity: PostTopic (`post_topics`)
- Purpose: Topic assignments per post.
- Key fields:
  - `id` (UUID)
  - `post_id` (FK -> posts.id)
  - `topic_id` (FK -> topics.id)
  - `role` (text: `primary|secondary|discovery_candidate`)
  - `confidence` (real)
  - `assignment_source` (text: `taxonomy_assignment|discovery|manual_review`)
  - `review_state` (text: `pending|accepted|rejected|edited`)
  - `topic_run_id` (FK -> topic_runs.id, nullable)
  - `created_at` / `updated_at` (datetime)
- Validation:
  - One `primary` assignment max per post among accepted states.

## Entity: TopicRun (`topic_runs`)
- Purpose: Metadata for assignment/discovery/refinement runs.
- Key fields:
  - `id` (UUID)
  - `run_type` (text: `assignment|discovery|refinement`)
  - `taxonomy_version` (text)
  - `embedding_model` (text)
  - `representation_config` (text/json, nullable)
  - `input_count` / `output_count` / `error_count` (int)
  - `started_at` / `finished_at` (datetime)
  - `status` (text: `running|success|failed`)
  - `diagnostics_json` (text/json)

## Entity: TopicCandidate (`topic_candidates`)
- Purpose: Emerging-topic proposals awaiting review.
- Key fields:
  - `id` (UUID)
  - `label` (text)
  - `keywords_json` (text/json)
  - `evidence_count` (int)
  - `confidence` (real, nullable)
  - `state` (text: `pending|promoted|merged|rejected`)
  - `merged_into_topic_id` (FK -> topics.id, nullable)
  - `topic_run_id` (FK -> topic_runs.id)
  - `created_at` / `updated_at` (datetime)

## Entity: Note (`notes`)
- Purpose: User annotations over posts.
- Key fields:
  - `id` (UUID)
  - `post_id` (FK -> posts.id)
  - `body` (text)
  - `created_at` / `updated_at` (datetime)

## Search Design
- FTS5 virtual table indexes:
  - `posts.title`
  - `posts.content`
  - `posts.summary`
  - `notes.body`
- Filters supported in query layer:
  - topic/date/status/source/confidence

## Relationships
- `posts 1..* post_topics`
- `topics 1..* post_topics`
- `topic_runs 1..* post_topics`
- `topic_runs 1..* topic_candidates`
- `posts 1..* notes`

## Delta and Idempotency Considerations
- Upsert keys:
  - posts: (`source`, `source_post_id`)
  - topics: (`slug`, `taxonomy_version`) or stable topic id
  - post_topics: (`post_id`, `topic_id`, `role`, `assignment_source`)
- Batch operations must be idempotent for retries and partial-failure recovery.
