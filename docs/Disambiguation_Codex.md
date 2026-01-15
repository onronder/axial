## Universal Context Disambiguation Architecture (V1.1 Blueprint)

### 1) Diagnosis: Context Flattening Failure
- Current retrieval (`backend/api/v1/chat.py` Step 8/9) selects top-N vectors/keywords and sends mixed scopes directly to generation. No grouping or filtering by source identity → cross-project contamination.
- Metadata today: chunks carry `source_type` and sometimes `source_id`; ingestion utilities (`backend/core/ingestion_utils.py`) normalize providers but do not enforce hierarchical scope fields. Hybrid search results therefore lack scope-aware controls.
- Result: Similar wording across repos/manuals is merged, producing blended answers (e.g., Python config + 10-year-old product manual + new marketing brochure).

### 2) Universal Scope Taxonomy (per connector)
- Guiding rule: Scope = smallest unit that should remain semantically coherent for retrieval. Stored as `scope_id`, `scope_name`, `scope_type`, `scope_path`, `scope_version` (optional), and `scope_hints` (list).
- GitHub: `scope_type=repository`; `scope_id={owner}/{repo}@{branch}`; `scope_name=repo`; `scope_path=monorepo subdir (if ingestion limited)`; `scope_version=commit sha`; `scope_hints=[languages, top dirs]`.
- S3: `scope_type=bucket_prefix`; `scope_id={bucket}/{prefix}` (prefix can be empty/root); `scope_name=bucket or alias`; `scope_path=prefix`; `scope_version=ingestion timestamp`; `scope_hints=[mime clusters]`.
- Box: `scope_type=box_folder`; `scope_id={folder_id}`; `scope_name=folder title`; `scope_path=path from root`; `scope_hints=[child types counts]`.
- Dropbox: `scope_type=dropbox_folder`; `scope_id={namespace_id}/{folder_path}`; `scope_name=folder name`; `scope_hints=[doc types]`.
- Drive: `scope_type=drive_folder_or_shared_drive`; `scope_id={drive_id}/{folder_id}`; `scope_name=folder/drive name`; `scope_hints=[doc types, owners]`.
- Notion: `scope_type=notion_space_or_page`; `scope_id={workspace_id}/{root_page_id}`; `scope_name=root page/workspace`; `scope_hints=[database schemas, page count]`.

### 3) Identity Document (Scope Map) Generation
- Purpose: Provide a high-level, structured “Scope Identity Card” per scope to anchor retrieval and allow scope-level search/summarization.
- Trigger: Once ingestion for a scope completes (per connector job run).
- Composition (stored as a special doc with `is_scope_identity=true` and `scope_*` metadata):
  - Header: Name, Type, Scope ID, Version (commit/timestamp), Ingestion window.
  - Modality summary: counts by MIME/extension, top N file types, detected languages (code/text).
  - Structure: top-level tree (depth 2–3), key directories/sections, exemplar paths.
  - Key modules/sections: heuristics (top files by centrality/size) and optional LLM-tagged topics.
  - Guardrails: data sensitivity hints if detected.
- Generation strategy:
  - Code (GitHub): deterministic heuristics (git ls-tree), language detection, size caps; optional lightweight LLM to synthesize text summary from heuristics.
  - Object stores (S3/Box/Drive/Dropbox): inventory listing to create tree and MIME histogram; small LLM pass allowed only on metadata (no content) to phrase the narrative.
  - Notion: use page hierarchy and database schemas to build outline; optional LLM pass over titles only.
- Storage: Upsert into `documents` with `source_type`, `scope_*` fields and `content` = identity text; mark `embedding=false` if treated as structured text, or embed after truncation for scope-level search.

### 4) Ambiguity Guard (Chat-Time)
- Collision detection: after retrieval, compute `unique(scope_id)` across candidate docs. If >1 and query is not explicitly multi-scope, flag collision.
- Resolution policy:
  - If multi-scope: re-rank by (score, recency, same scope as conversation history if available), then either (a) select dominant scope (highest aggregate) when ratio > threshold (e.g., 0.6), or (b) ask for clarification listing scopes.
  - System prompt augmentation: prepend rule “If context spans multiple scopes and instructions conflict, list scopes with brief descriptors and ask which to use before answering.”
  - Identity doc boost: when a scope identity document is present, prefer it to answer scope-selection questions and to summarize before mixing.
- Optional re-ranking: group-by-scope aggregation of similarity; keep top K scopes, then top M docs per scope to avoid cross-scope mixing.

### 5) Data Model + Indexing
- Minimal change: keep `scope_*` in `metadata` JSONB for backward compatibility; ensure RPC filters accept `scope_id` and `scope_type`.
- Performance option: add indexed columns (`scope_id`, `scope_type`) in `documents` for faster WHERE clauses and group-by. Start with generated columns + b-tree index; migrate once proven.
- Identity docs: tag with `is_scope_identity=true`, `doc_kind=scope_card`.

### 6) Ingestion Pipeline Changes (high level)
- Normalize scope per connector in each loader; enrich chunk metadata with `scope_id`, `scope_name`, `scope_type`, `scope_path`, `scope_version`, `scope_hints`.
- Emit one identity document per scope after ingestion completion; store ingestion stats alongside for debugging.
- Maintain existing chunking/tokenization; do not alter chunk sizes to avoid regression. Metadata injection should be non-invasive.

### 7) Chat/Retrieval Changes (high level)
- Retrieval: add filter parameter to `hybrid_search` to restrict to a scope when user/session selects one; expose optional `scope_id` and `scope_type` in API.
- Post-retrieval: group docs by `scope_id`; apply dominance heuristic and collision detection. If collision persists, return a clarification response instead of blended answer.
- Prompting: extend system prompt with ambiguity rule and include per-scope headers (from identity docs) ahead of chunk text when available.
- Output: include `scope_id` and `scope_name` in `sources` so UI can show origin.

### 8) Implementation Roadmap (sequenced, low-risk)
- Phase 0: Schema toggle
  - Add metadata schema contract for `scope_*`; add generated columns/indexes if chosen; keep old fields untouched.
- Phase 1: Ingestion tagging
  - Implement scope builders per connector; inject `scope_*` into chunk metadata; add ingestion-time validation + logging.
  - Add unit tests for metadata presence and correctness per connector.
- Phase 2: Identity documents
  - Build inventory summarizers (non-LLM) and optional lightweight LLM narration step; store as `doc_kind=scope_card`.
  - Add tests that identity doc is emitted and linked to scope.
- Phase 3: Retrieval controls
  - Extend RPC filters to accept `scope_id`; add group-by-scope aggregation; re-rank within-scope.
  - Add collision detection logic in `backend/api/v1/chat.py`; update system prompt to request clarification when multi-scope.
- Phase 4: UI/UX hooks
  - Allow user to pin/select scope in chat; show source badges by scope; surface identity doc preview.
- Phase 5: Observability & guardrails
  - Log scope collisions, dominant-scope selections, and clarification prompts; add dashboards and alerting on high collision rates.
- Phase 6: Rollout
  - Shadow mode (log-only), then soft-enforce (clarify when high risk), then hard-enforce (reject blended answers).

### 9) Risks and Mitigations
- Risk: Mis-scoped ingestion (wrong prefix/branch) → Mitigate with deterministic scope builders and validation tests.
- Risk: Performance hit from scope grouping → Mitigate with generated columns/indexes and reduce per-scope doc count via top-M pruning.
- Risk: Over-clarification hurting UX → Use dominance ratio heuristic and conversation-level sticky scope.
- Risk: Identity docs drifting stale → regenerate on ingestion runs and store version/timestamp; allow TTL-based refresh.

### 10) Minimal Test Plan
- Unit: metadata injection per connector; identity doc creation; dominance heuristic decisions; collision detection branch coverage.
- Integration: ingestion run for GitHub/S3/Box fixture data produces identity doc and scoped chunks; chat query with mixed content triggers clarification; chat within pinned scope returns single-scope answers.
- Regression: ensure existing ingestion success path unchanged; hybrid search RPC still works without scope filters.
