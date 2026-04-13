# Three-Step Semantic Pipeline — Design Contract

**Status:** Draft for review
**Scope:** Replace `SemanticIndexingOrchestrator` with three independent pipeline-step modules that share the existing `SearchMetadata.semantic_results[]` output contract.
**Affected repos:** `module-chunker`, `module-embedder`, `module-semantic-graph` (renamed from `module-semantic-manager`), `pipestream-wiremock-server`, `pipestream-protos`, `pipestream-engine`, `pipestream-opensearch`, `module-testing-sidecar`, `dev-assets`.
**Preserves:** every existing field on `PipeDoc`, `SearchMetadata`, `SemanticProcessingResult`, `SemanticChunk`, `ChunkEmbedding`, `NlpDocumentAnalysis`, `DocumentAnalytics`, `ChunkAnalytics`, `SourceFieldAnalytics`, `VectorSetDirectives`, `VectorDirective`.
**Changes zero protos.** Enforces stage invariants in code, not schema.

---

## 1. Goals

1. Replace the scatter-gather orchestrator with three stateless per-doc pipeline steps that each implement `PipeStepProcessorService.processData(ProcessDataRequest) → Uni<ProcessDataResponse>`.
2. Remove the "terrible mapping strategy" of three competing config modes (`directives` / convenience fields / `vector_set_ids`) in favor of a single directive-driven path with a legacy `ProcessConfiguration.json_config` fallback.
3. Preserve byte-for-byte the shape of `SearchMetadata.semantic_results[]` that reaches `opensearch-manager`.
4. Add Redis caching as an optional performance layer (not on the critical path; compute-through on outage).
5. Use the `quarkus-djl-embeddings` extension **in-process** inside `module-semantic-graph` for the small re-embed pass needed by semantic boundary detection. No gRPC to `module-embedder` from `module-semantic-graph`.
6. Enable parallel refactor work on the three module repos by locking the contract in this document plus wiremock mocks and stage fixtures.
7. Produce deterministic `semantic_results[]` output for diffability and snapshot testing.

## 2. Non-Goals

- Changing any `.proto` file.
- Touching `opensearch-manager`'s `schemamanager` package, `VectorSetEntity`, `VectorSetServiceEngine`, `OpenSearchIndexingService`, or the `SeparateIndicesIndexingStrategy` / `ChunkCombinedIndexingStrategy` lazy field-creation path.
- Changing the `opensearch-sink` module.
- Replacing Mutiny or moving off Quarkus.
- Building a new coordination layer (Redis-as-queue, Kafka-as-assembly-plane, etc.).
- Cross-document batching inside any module. Cross-doc concurrency comes from the engine's slot config, not from module-side aggregation.
- Implementing the full schemamanager ↔ directive wiring. This document defines stub interfaces for that; real implementation is a follow-up (tasks #78, #79).
- Implementing Apicurio schema versioning for OpenSearch mapping changes (task #80).

## 3. Architecture

```
PipeDoc enters at graph entry node
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│  chunker (module-chunker)                                    │
│    reads:  doc.search_metadata.vector_set_directives         │
│            OR legacy ProcessConfiguration.json_config        │
│    writes: search_metadata.semantic_results[] where every    │
│            entry has embedding_config_id == "" (placeholder) │
│    cache:  chunk:{sha256b64url(text)}:{chunker_config_id}    │
│            → serialized List<SemanticChunk>, TTL 30d         │
└──────────────────────────────────────────────────────────────┘
    │  Stage 1: placeholder SPRs with chunks, no vectors
    ▼
┌──────────────────────────────────────────────────────────────┐
│  embedder (module-embedder)                                  │
│    reads:  directives + placeholder SPRs                     │
│    writes: each placeholder replaced by N fanned-out SPRs    │
│            (N = configured embedder models for that          │
│            directive), each fully populated with vectors     │
│    calls:  local quarkus-djl-embeddings extension            │
│    cache:  embed:{sha256b64url(text)}:{model_id}             │
│            → serialized Vector, TTL 7d                       │
└──────────────────────────────────────────────────────────────┘
    │  Stage 2: fully-hydrated SPRs, zero placeholders
    ▼
┌──────────────────────────────────────────────────────────────┐
│  semantic-graph (module-semantic-graph)                      │
│    reads:  directives + hydrated SPRs                        │
│    writes: appends centroid SPRs (paragraph/section/doc)     │
│            + optional semantic-boundary SPRs                 │
│    calls:  local quarkus-djl-embeddings extension ONLY       │
│            (no gRPC to module-embedder), for ≤50 section     │
│            vectors per doc during boundary detection         │
│    cache:  delegated to DJL extension's own caching          │
└──────────────────────────────────────────────────────────────┘
    │  Stage 3: final output shape, identical to today's sink input
    ▼
opensearch-sink → opensearch-manager (unchanged)
```

**Engine transport transparency.** The engine routes between nodes via either direct gRPC or Kafka (sidecar-mediated). Modules don't know which. `PipeStepProcessorService.processData` is called exactly once per doc per node regardless of transport.

**Concurrency model.** Per-doc work only inside each module. Cross-doc concurrency comes from the engine's slot configuration for each node (`slots`, `partitions`, `leases`). Modules have no in-process cross-request state.

## 4. Stage Contracts

Every `PipeDoc` flowing through the semantic sub-pipeline has an implicit "stage" determined by the content of `search_metadata.semantic_results[]`. No proto field tracks it; the state is inferred from field values.

| Stage | Produced by | `semantic_results[]` content |
|---|---|---|
| **0 (raw)** | upstream (parser, mapper) | empty, or only SPRs from earlier steps that we pass through untouched |
| **1 (post-chunker)** | chunker step | one SPR per `(source_field, chunker_config)` with `embedding_config_id == ""`, chunks populated (text + offsets + chunk_id), vectors empty, `nlp_analysis` attached where available |
| **2 (post-embedder)** | embedder step | zero SPRs with `embedding_config_id == ""` remain; every placeholder replaced by N fanned-out SPRs where N = number of embedder configs in the matching directive; vectors populated |
| **3 (post-semantic-graph)** | semantic-graph step | all Stage 2 SPRs preserved; new SPRs appended for centroids (paragraph / section / document per config) and optional semantic-boundary SPRs; sorted deterministically |

### 4.1 Stage 1 shape (produced by chunker)

```
SemanticProcessingResult {
  result_id:              deterministic string, e.g. "{source_label}:{chunker_config_id}:stage1:{hash}"
  source_field_name:      from VectorDirective.source_label
  chunk_config_id:        from NamedChunkerConfig.config_id
  embedding_config_id:    ""                                  ← KEY: empty = placeholder
  result_set_name:        "" or optional template             ← embedder step will fill if empty
  chunks: [
    SemanticChunk {
      chunk_id:             deterministic, e.g. "{source_label}:{chunker_config_id}:{chunk_number}"
      chunk_number:         0-based sequential within this SPR
      embedding_info: ChunkEmbedding {
        text_content:             actual chunk text
        chunk_id:                 same as SemanticChunk.chunk_id
        original_char_start_offset, original_char_end_offset: character spans in source text
        chunk_config_id:          same as SPR.chunk_config_id
        vector:                   []                          ← KEY: empty list = unembedded
      }
      chunk_analytics:      ChunkAnalytics (positional + POS + text stats, always populated)
      metadata:             optional
    }
    ...
  ]
  nlp_analysis:           NlpDocumentAnalysis — full analysis of the source text, attached to every SPR that came from that source text
  metadata:               empty or diagnostic
  centroid_metadata:      unset
  semantic_config_id:     unset
  semantic_granularity:   unset
}
```

The chunker also populates `SearchMetadata.source_field_analytics[]` with one entry per unique `(source_field, chunker_config)` pair computed once per source text.

**Sentences are always computed.** Even if no `VectorDirective` requests sentence-level chunking, the chunker runs sentence detection (it does it anyway for NLP) and stamps a SPR with `chunk_config_id = "sentences_internal"`. This SPR exists so the semantic-graph step can do boundary detection on sentence vectors later without requiring an explicit directive. If no downstream step needs it, it passes through to `opensearch-sink` and the existing indexing strategies decide whether to index it (they currently do, which is fine; we can add an opt-out in a future iteration).

### 4.2 Stage 2 shape (produced by embedder)

Every Stage 1 SPR has been **replaced** (not appended to) by one or more populated SPRs:

```
// For each Stage 1 SPR with embedding_config_id=="", and for each
// NamedEmbedderConfig in its matching VectorDirective, produce:
SemanticProcessingResult {
  result_id:              "{source_label}:{chunker_config_id}:{embedder_config_id}:stage2"
  source_field_name:      preserved from Stage 1
  chunk_config_id:        preserved from Stage 1
  embedding_config_id:    NamedEmbedderConfig.config_id
  result_set_name:        resolved from directive template or "{source_label}_{chunker_id}_{embedder_id}"
  chunks: [                                      ← copied from Stage 1, vectors filled
    SemanticChunk {
      chunk_id:             preserved
      chunk_number:         preserved
      embedding_info: ChunkEmbedding {
        text_content:             preserved
        chunk_id:                 preserved
        original_char_start_offset, original_char_end_offset: preserved
        chunk_config_id:          preserved
        vector:                   [f0, f1, ... fD-1]   ← KEY: populated, length = model dimension
      }
      chunk_analytics:      preserved
      metadata:             preserved
    }
    ...
  ]
  nlp_analysis:           preserved from Stage 1
  metadata:               preserved; embedder may add {"embed_duration_ms", "cache_hit_ratio"}
  centroid_metadata:      unset
  semantic_config_id:     unset (semantic-graph sets it for boundary SPRs)
  semantic_granularity:   unset
}
```

Stage 1 placeholder SPRs are **not** carried forward. The embedder removes them from `semantic_results[]` and replaces them with the fan-out.

**Immutable preservation:** chunk_id, text_content, chunk_number, offsets, nlp_analysis, and chunk_analytics are copied from Stage 1 byte-for-byte. The embedder is only allowed to add vectors (and update result-level metadata).

### 4.3 Stage 3 shape (produced by semantic-graph)

Every Stage 2 SPR is preserved. New SPRs are appended:

**Centroid SPRs (one per enabled granularity, per `(source_field, chunker_config, model)` combo):**
```
SemanticProcessingResult {
  result_id:              "{source_label}:{chunker_config_id}:{embedder_config_id}:centroid:{granularity}"
  source_field_name:      preserved
  chunk_config_id:        "document_centroid" | "paragraph_centroid" | "section_centroid"
  embedding_config_id:    preserved from source SPR
  result_set_name:        "{source_label}_{embedder_id}_{granularity}"
  chunks: [                                      ← one centroid chunk per granularity unit
    SemanticChunk {
      chunk_id:             "{granularity}:{index}"
      embedding_info: ChunkEmbedding {
        text_content:             "" OR a representative excerpt
        vector:                   averaged vector of source chunks, length = model dimension
      }
    }
  ]
  centroid_metadata: CentroidMetadata {
    granularity:            "document_centroid" | "paragraph_centroid" | "section_centroid"
    source_vector_count:    number of source vectors averaged
    section_title, section_depth: set for section_centroid when DocOutline is present
  }
}
```

**Semantic-boundary SPRs (optional, one per `(source_field, model)` when `compute_semantic_boundaries=true`):**
```
SemanticProcessingResult {
  result_id:              "{source_label}:semantic:{embedder_config_id}:boundaries"
  source_field_name:      preserved
  chunk_config_id:        "semantic"
  embedding_config_id:    preserved
  result_set_name:        "{source_label}_semantic_{embedder_id}"
  chunks: [                                      ← one per boundary-detected group
    SemanticChunk {
      chunk_id:             "semantic:{index}"
      embedding_info: ChunkEmbedding {
        text_content:             concatenated text of the sentence group
        vector:                   re-embedded via local DJL extension (NOT a centroid)
      }
      metadata:             {"sentence_span": "start-end", "sentence_count": N}
    }
  ]
  semantic_config_id:     from directive
  semantic_granularity:   "SEMANTIC_CHUNK"
}
```

**`semantic_results[]` is sorted** at the end of every step by lex order on `(source_field_name, chunk_config_id, embedding_config_id, result_id)`.

## 5. Stage Invariants (checkable)

Every step asserts its input stage at entry and fails fast if the doc is in the wrong state. Assertions live in a shared helper `SemanticPipelineInvariants` committed to `pipestream-protos/testdata/semantic-pipeline/` and consumed by all three module repos + tests.

### 5.1 `assertPostChunker(PipeDoc)`

- `search_metadata` is set.
- `search_metadata.semantic_results` has ≥1 entry (unless the doc had no source text matching any directive, in which case 0 is valid).
- For every SPR in `semantic_results`:
  - `embedding_config_id == ""`
  - `source_field_name != ""`
  - `chunk_config_id != ""`
  - `chunks` is non-empty
  - For every chunk: `embedding_info.text_content != ""`, `embedding_info.vector` is empty, `chunk_id != ""`, offsets are non-negative and `start <= end`
  - `nlp_analysis` is set on at least one SPR per unique `source_field_name` (may be shared across SPRs of same source)
- `source_field_analytics[]` has one entry per unique `(source_field, chunk_config_id)` pair present in `semantic_results`.
- `semantic_results[]` is lex-sorted by the tuple described above.

### 5.2 `assertPostEmbedder(PipeDoc)`

- Everything from `assertPostChunker` **except** the `embedding_config_id == ""` rule.
- For every SPR in `semantic_results`:
  - `embedding_config_id != ""`
  - `embedding_config_id != ""` AND there exists at least one `VectorDirective` in `vector_set_directives` whose `embedder_configs[]` contains a `NamedEmbedderConfig` with this `config_id`
  - Every chunk's `embedding_info.vector` is non-empty and has length matching the expected model dimension
  - `chunk_id`, `text_content`, offsets, and `chunk_analytics` are byte-identical to what they were in Stage 1
- Zero SPRs with `embedding_config_id == ""`.
- `semantic_results[]` is lex-sorted.
- `nlp_analysis` and `source_field_analytics[]` are preserved from Stage 1.

### 5.3 `assertPostSemanticGraph(PipeDoc)`

- Everything from `assertPostEmbedder`.
- For every centroid SPR (`chunk_config_id` ends in `_centroid`):
  - `centroid_metadata` is set with valid `granularity` and `source_vector_count > 0`
  - Exactly one chunk with a populated vector
- For every semantic-boundary SPR (`chunk_config_id == "semantic"`):
  - `semantic_granularity == "SEMANTIC_CHUNK"`
  - `semantic_config_id != ""`
  - At least one chunk with `text_content != ""` and populated vector
  - Chunk count ≤ `max_semantic_chunks_per_doc` (default 50)
- All Stage 2 SPRs are preserved unchanged (deep-equal check on the pre-append portion of `semantic_results[]`).
- `semantic_results[]` is lex-sorted.

## 6. Config Schemas

Each step parses `ProcessConfiguration.json_config` (a `google.protobuf.Struct`) into a Java record using Jackson. If the JSON can't be parsed into the record, the step fails with a `StatusRuntimeException(INVALID_ARGUMENT)`. There is no default-on-parse-failure behavior.

### 6.1 `ChunkerStepOptions` (lives in `module-chunker`)

Per §21.1, there is no `legacy_fallback`. Directives come from `doc.search_metadata.vector_set_directives` or the step fails.

```java
@JsonIgnoreProperties(ignoreUnknown = true)
public record ChunkerStepOptions(
    @JsonProperty("cache_enabled") Boolean cacheEnabled,               // default true
    @JsonProperty("cache_ttl_seconds") Long cacheTtlSeconds,           // default 2592000 (30d)
    @JsonProperty("always_emit_sentences") Boolean alwaysEmitSentences // default true
) {
    public boolean effectiveCacheEnabled() { return cacheEnabled == null || cacheEnabled; }
    public long effectiveCacheTtlSeconds() { return cacheTtlSeconds != null && cacheTtlSeconds > 0 ? cacheTtlSeconds : 2_592_000L; }
    public boolean effectiveAlwaysEmitSentences() { return alwaysEmitSentences == null || alwaysEmitSentences; }
    public static String jsonV7Schema() { /* returns JSONForms schema */ }
}
```

### 6.2 `EmbedderStepOptions` (lives in `module-embedder`)

Per §21.1, there is no `legacy_fallback`. Embedder configs come from the `VectorDirective.embedder_configs[]` list on each directive.

```java
@JsonIgnoreProperties(ignoreUnknown = true)
public record EmbedderStepOptions(
    @JsonProperty("cache_enabled") Boolean cacheEnabled,           // default true
    @JsonProperty("cache_ttl_seconds") Long cacheTtlSeconds,       // default 604800 (7d)
    @JsonProperty("max_retry_attempts") Integer maxRetryAttempts,  // default 2
    @JsonProperty("retry_backoff_ms") Long retryBackoffMs          // default 100
) {
    public boolean effectiveCacheEnabled() { return cacheEnabled == null || cacheEnabled; }
    public long effectiveCacheTtlSeconds() { return cacheTtlSeconds != null && cacheTtlSeconds > 0 ? cacheTtlSeconds : 604_800L; }
    public int effectiveMaxRetryAttempts() { return maxRetryAttempts != null && maxRetryAttempts >= 0 ? maxRetryAttempts : 2; }
    public long effectiveRetryBackoffMs() { return retryBackoffMs != null && retryBackoffMs >= 0 ? retryBackoffMs : 100L; }
    public static String jsonV7Schema() { /* returns JSONForms schema */ }
}
```

### 6.3 `SemanticGraphStepOptions` (lives in `module-semantic-graph`)

```java
@JsonIgnoreProperties(ignoreUnknown = true)
public record SemanticGraphStepOptions(
    @JsonProperty("compute_paragraph_centroids") Boolean paragraphCentroids, // default true
    @JsonProperty("compute_section_centroids") Boolean sectionCentroids,     // default true
    @JsonProperty("compute_document_centroid") Boolean documentCentroid,     // default true
    @JsonProperty("compute_semantic_boundaries") Boolean semanticBoundaries, // default true
    @JsonProperty("boundary_embedding_model_id") String boundaryEmbeddingModelId, // REQUIRED when compute_semantic_boundaries=true; must resolve to a loaded DJL model (§21.3)
    @JsonProperty("max_semantic_chunks_per_doc") Integer maxSemanticChunksPerDoc, // default 50, hard cap
    @JsonProperty("boundary_similarity_threshold") Float boundarySimilarityThreshold, // default 0.5
    @JsonProperty("boundary_percentile_threshold") Integer boundaryPercentileThreshold, // default 20
    @JsonProperty("boundary_min_sentences_per_chunk") Integer boundaryMinSentencesPerChunk, // default 2
    @JsonProperty("boundary_max_sentences_per_chunk") Integer boundaryMaxSentencesPerChunk  // default 30
) {
    public boolean effectiveParagraphCentroids() { return paragraphCentroids == null || paragraphCentroids; }
    public boolean effectiveSectionCentroids() { return sectionCentroids == null || sectionCentroids; }
    public boolean effectiveDocumentCentroid() { return documentCentroid == null || documentCentroid; }
    public boolean effectiveSemanticBoundaries() { return semanticBoundaries == null || semanticBoundaries; }
    public int effectiveMaxSemanticChunksPerDoc() { return maxSemanticChunksPerDoc != null && maxSemanticChunksPerDoc > 0 ? maxSemanticChunksPerDoc : 50; }
    /* + other effective*() getters */
    public static String jsonV7Schema() { /* returns JSONForms schema */ }
}
```

All four `compute_*` flags default to `true`. If all four are `false`, the step is a pass-through (returns the input doc with only a deterministic sort applied).

## 7. Step Behavior Specs

### 7.1 Chunker step (`module-chunker`)

**Class:** `ChunkerGrpcImpl.processData(ProcessDataRequest)` (existing class, heavily modified)

**Behavior:**

1. Parse `ProcessConfiguration.json_config` into `ChunkerStepOptions`. Fail with `INVALID_ARGUMENT` on parse error.
2. Resolve directives from `request.document.search_metadata.vector_set_directives.directives`. If absent or empty, fail with `FAILED_PRECONDITION` (§21.1 — no fallback).
2a. Validate directive set: `source_label` must be unique across all directives. On duplicate, fail with `INVALID_ARGUMENT`. For each directive, compute `directive_key = sha256b64url(source_label + "|" + cel_selector + "|" + sorted(chunker_config_ids) + "|" + sorted(embedder_config_ids))` (§21.2).
3. For each `VectorDirective`:
   - Extract source text via `cel_selector` from the `PipeDoc`. If the result is empty or null, log a debug line and skip this directive (do not fail).
   - Cache lookup: compute `nlpCacheKey = sha256b64url(text)`. Check the Caffeine NLP cache. On miss, run the OpenNLP pipeline once (sentence detection, tokenization, POS, lemmatization, language detection) and cache.
   - For each `NamedChunkerConfig` in the directive:
     - Compute `chunkCacheKey = "chunk:" + sha256b64url(text) + ":" + config.config_id`.
     - If `options.effectiveCacheEnabled()`, query Redis `GET chunkCacheKey`. On hit, deserialize to `List<SemanticChunk>` and skip to step 4.
     - On miss, run the chunker with this config's parameters on the source text. Populate `SemanticChunk` with `chunk_id`, `chunk_number`, `embedding_info.text_content`, offsets, `chunk_config_id`. Set `embedding_info.vector` to empty. Compute `ChunkAnalytics` per chunk (positional, POS, etc.). On success, `SETEX chunkCacheKey options.effectiveCacheTtlSeconds() <serialized>`.
     - If Redis errors (connection, timeout), log WARN (rate-limited, one per minute per module instance), increment metric `chunker.cache.errors`, fall through to compute as if it were a cache miss, skip writeback.
   - Build one `SemanticProcessingResult` from the chunks plus the cached/computed `NlpDocumentAnalysis`. Set `embedding_config_id = ""`, `result_id` deterministic, `source_field_name = directive.source_label`, `chunk_config_id = config.config_id`.
   - Add to output list.
4. If `options.effectiveAlwaysEmitSentences()` is true AND no directive already requested sentence chunking (detected by scanning SPRs for `chunk_config_id`s that the chunker classifies as sentence-producing), also emit a sentence-level SPR with `chunk_config_id = "sentences_internal"`. Use the cached sentence spans from NLP.
5. Compute `SourceFieldAnalytics` for each unique `(source_field, chunk_config_id)` pair present in the output.
6. Build the enriched `PipeDoc`:
   - Preserve all existing fields (title, body, blob_bag, parsed_metadata, ownership, etc.).
   - Set `search_metadata.semantic_results[]` to the sorted list of output SPRs.
   - Append the new `source_field_analytics` entries (if `search_metadata.source_field_analytics[]` had entries from upstream, merge deduplicating by `(source_field, chunker_config)` — new entries win).
7. Return `ProcessDataResponse` with `outcome = PROCESSING_OUTCOME_SUCCESS` and the enriched doc.

**Error handling:**
- Parse error: `INVALID_ARGUMENT`, stream goes to quarantine via engine's DLQ path.
- CEL selector returns wrong type: `INVALID_ARGUMENT`.
- Chunker execution error (e.g., OpenNLP model missing): `INTERNAL`, retryable at engine level.
- Redis error: WARN + compute-through, never fail the doc.

**Preserved vs added:**
- Preserved: all existing NLP caching, OpenNLP sentence/tokenization, `DocumentAnalytics`, `ChunkAnalytics`, `SourceFieldAnalytics`.
- Added: directive-driven loop, Redis chunk cache, strict config parsing, mandatory sentence SPR, deterministic sort.
- Removed: legacy single-config single-source path. v1 requires directives on the doc per §21.1 — no fallback.

### 7.2 Embedder step (`module-embedder`)

**Class:** `EmbedderGrpcImpl.processData(ProcessDataRequest)` (existing class, heavily modified)

**Behavior:**

1. Parse `ProcessConfiguration.json_config` into `EmbedderStepOptions`. Fail with `INVALID_ARGUMENT` on parse error.
2. Resolve directives from `doc.search_metadata.vector_set_directives`. If absent, fail with `FAILED_PRECONDITION` (§21.1 — no fallback).
3. Validate input stage: call `SemanticPipelineInvariants.assertPostChunker(doc)`. If it fails, return `FAILED_PRECONDITION` with the assertion message.
4. Partition `semantic_results[]` into:
   - `placeholders`: SPRs with `embedding_config_id == ""`
   - `preExisting`: SPRs with `embedding_config_id != ""` (passthrough, should be empty in normal flow but handled defensively)
5. For each placeholder SPR:
   - Find its matching `VectorDirective` by `metadata["directive_key"]` first, falling back to `source_label == source_field_name` (§21.2). If no match, fail with `FAILED_PRECONDITION`.
   - For each `NamedEmbedderConfig` in the directive:
     - Build cache keys: for each chunk in the placeholder, `embedCacheKey = "embed:" + sha256b64url(chunk.text_content) + ":" + embedderConfig.config_id`.
     - `MGET` all keys from Redis. Partition chunks into:
       - `hits`: chunks whose cache key returned a vector
       - `misses`: chunks whose key returned null
     - If `misses` is non-empty, call the local `quarkus-djl-embeddings` provider with the list of miss texts and the model_id. Receive `List<Vector>` back, one per input text in order.
     - On DJL failure:
       - Transient (UNAVAILABLE, DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED): retry up to `options.effectiveMaxRetryAttempts()` with exponential backoff starting from `options.effectiveRetryBackoffMs()`. After retries exhausted, fail the doc (INTERNAL).
       - Permanent (NOT_FOUND, INVALID_ARGUMENT): fail the doc immediately (INVALID_ARGUMENT or FAILED_PRECONDITION).
     - `MSET` the new results back to Redis with `EX options.effectiveCacheTtlSeconds()`.
     - Merge `hits` + new results into a complete `Map<chunkId, Vector>` covering every chunk.
     - Clone the placeholder SPR:
       - `embedding_config_id = embedderConfig.config_id`
       - `result_set_name` resolved from directive template (or default `"{source_label}_{chunker_id}_{embedder_id}"`)
       - `result_id` deterministic, e.g. `"{source_label}:{chunker_id}:{embedder_id}:stage2"`
       - For each chunk, copy Stage 1 fields byte-for-byte and set `embedding_info.vector` from the result map
     - Add to output list.
6. Replace `semantic_results[]` with `preExisting + allClones`, sorted lex.
7. Optionally add result metadata: `embed_duration_ms`, `cache_hit_ratio`.
8. Return `ProcessDataResponse` with enriched doc.

**Redis outage behavior:**
- On `MGET` error: log WARN (rate-limited), increment `embedder.cache.mget.errors`, treat as all-miss, proceed with DJL call for every chunk.
- On `MSET` error: log WARN (rate-limited), increment `embedder.cache.mset.errors`, skip writeback, still return the populated doc. The cache simply didn't update — no correctness impact.

**DJL extension usage:**
- `@Inject DjlEmbeddingProvider djl;` (exact class name TBD in P5)
- `djl.embed(List<String> texts, String modelId)` returns `List<Vector>` in the same order
- Extension-side batching decisions (GPU batch size, concurrent calls) are the extension's concern, not the embedder module's
- Model loading happens at Quarkus startup per `application.properties` config; first call is already warm

### 7.3 Semantic-graph step (`module-semantic-graph`)

**Class:** `SemanticGraphGrpcImpl.processData(ProcessDataRequest)` (renamed from `SemanticManagerGrpcImpl`)

**Behavior:**

1. Parse `ProcessConfiguration.json_config` into `SemanticGraphStepOptions`. Fail on parse error.
2. Validate input stage: call `SemanticPipelineInvariants.assertPostEmbedder(doc)`.
3. Resolve directives.
4. Walk `semantic_results[]`. Group by `(source_field, chunker_config, embedder_config)` combo. For each group:
   - If `options.effectiveDocumentCentroid()`: compute document centroid by averaging all chunk vectors in the group, create a centroid SPR with `chunk_config_id = "document_centroid"`.
   - If `options.effectiveParagraphCentroids()` and the source text had paragraph structure (detectable from chunk offsets + NLP paragraph spans): compute paragraph centroids, emit one SPR per paragraph with `chunk_config_id = "paragraph_centroid"`.
   - If `options.effectiveSectionCentroids()` and the doc has `DocOutline`: compute section centroids, emit one SPR per section with `chunk_config_id = "section_centroid"` and `centroid_metadata.section_title` set.
   - Delegate actual averaging to the existing `CentroidComputer` helper (pure CPU math, already in the codebase).
5. If `options.effectiveSemanticBoundaries()`:
   - Find the sentence-level SPR in `semantic_results[]` (the one with `chunk_config_id == "sentences_internal"` or whatever config the directive specified for sentences).
   - Resolve `options.boundaryEmbeddingModelId` to a loaded DJL model. If unset or not loaded, fail with `FAILED_PRECONDITION` per §21.3. No "first available model" fallback.
   - Run `SemanticBoundaryDetector` on the sentence vectors with the configured thresholds. Get back grouped sentence indices.
   - For each group, concatenate the sentence texts → grouped text.
   - Enforce hard cap: if `groups.size() > options.effectiveMaxSemanticChunksPerDoc()`, fail with `INTERNAL` ("semantic boundary detection produced N groups exceeding cap M; this indicates misconfigured thresholds or pathological input"). Never silently truncate.
   - Call the local DJL extension (`@Inject DjlEmbeddingProvider`) with the grouped texts and `boundaryEmbeddingModelId`. Get back `List<Vector>`.
   - Build one semantic-boundary SPR with one chunk per group: `text_content = groupedText`, `vector = embeddedVector`, `metadata = {"sentence_span": "start-end", "sentence_count": N}`.
6. Append new centroid + boundary SPRs to `semantic_results[]`.
7. Sort `semantic_results[]` deterministically.
8. Return enriched doc.

**No external network calls.** No gRPC to `module-embedder`. No HTTP to opensearch-manager. The only non-local call is the in-process DJL extension.

**If `boundaryEmbeddingModelId` is unset and the config doesn't match any loaded model**, fail with `FAILED_PRECONDITION`. Do not silently pick a different model.

## 8. DJL Extension Integration

Both `module-embedder` and `module-semantic-graph` depend on `ai.pipestream:quarkus-djl-embeddings-runtime`.

**Version resolution during dev:**
- Running `./gradlew quarkusDev` (or `quarkus dev`) on `quarkus-djl-embeddings` publishes the current version to the local Maven repository.
- Both modules pick it up from their local Maven cache on their next build.

**Version resolution on main:**
- When `quarkus-djl-embeddings` merges to main, CI publishes a SNAPSHOT to the Sonatype snapshot repo.
- Both modules pick it up from Sonatype on their next CI build.

**Model configuration is per-app:**
- `module-embedder` loads whatever models its `application.properties` specifies (likely multiple models to serve the full range of embedder configs referenced by directives).
- `module-semantic-graph` loads only the small boundary-detection model (probably `all-MiniLM-L6-v2`, ~22MB).
- Duplication: both JVMs have `all-MiniLM-L6-v2` loaded. Combined RAM overhead: ~44MB. Acceptable.

**API surface expected:** to be confirmed in P5, but the refactor assumes at minimum:
```java
public interface DjlEmbeddingProvider {
    List<Vector> embed(List<String> texts, String modelId);
    Uni<List<Vector>> embedAsync(List<String> texts, String modelId);  // optional, preferred for Mutiny chains
    boolean isModelLoaded(String modelId);
    Set<String> getLoadedModels();
}
```

If the extension doesn't currently expose this interface, P5.5 adds it to the extension's `runtime/` module. The interface should be the public entry point; implementation details (model loader, DJL session management, batching) stay internal.

## 9. Redis Cache Layer

### 9.1 Keys

- Chunk cache: `chunk:{sha256b64url(text)}:{chunker_config_id}` → serialized `List<SemanticChunk>` (protobuf bytes)
- Embed cache: `embed:{sha256b64url(text)}:{embedding_config_id}` → serialized `Vector` (float array, bytes)

**Hash:** SHA-256 in URL-safe base64 without padding. 43 chars per hash. No collisions expected for this corpus size.

**Why `chunker_config_id` in the chunk key:** different configs produce different chunk spans for the same text. Safe; when a config version changes, bump `config_id` and the old cache entry becomes unreachable (and expires via TTL).

**Why `embedding_config_id` in the embed key:** different models produce different vectors for the same text. Model weight changes MUST come with a new `model_id` (or `config_id`) per the team convention.

### 9.2 Operations

- **Chunk lookup:** single `GET` per (text, config) combination — typically 1 per directive per source field.
- **Chunk writeback:** single `SETEX` per computed result.
- **Embed lookup:** **batch `MGET`** for all chunks in a placeholder SPR × model combination. Single Redis roundtrip to look up N chunks.
- **Embed writeback:** single pipelined `MSET` with per-key expiry (`SETEX` loop or a Lua script — implementation detail).

### 9.3 Outage behavior

- Redis unreachable at startup: module starts anyway, cache is disabled, log `ERROR` once.
- Redis errors during operation: WARN rate-limited to 1/min per module instance, increment error metric, compute-through (treat as cache miss, skip writeback).
- Configuration kill switch: `chunker.cache.enabled=false` or `embedder.cache.enabled=false` in `application.properties` bypasses cache entirely without needing Redis down.

### 9.4 Cache invariants

- A cache hit must produce **byte-identical** output to a cache miss for the same input.
- Chunk cache: stored `List<SemanticChunk>` must include the same `chunk_id`, `chunk_number`, offsets, `chunk_analytics`, `text_content`. Deterministic generation is required (`chunk_id` must be a function of text + config, not a fresh UUID).
- Embed cache: stored vector is a raw `float[]`; on read, it's dropped into a fresh `ChunkEmbedding.vector`. The surrounding `SemanticChunk` is preserved from Stage 1.

## 10. Error Semantics

### 10.1 Fail-fast categories

| Error | gRPC status | Action |
|---|---|---|
| Invalid JSON config | `INVALID_ARGUMENT` | Fail doc → quarantine |
| Directives absent on doc | `FAILED_PRECONDITION` | Fail doc → quarantine (§21.1) |
| Duplicate `source_label` in directive set | `INVALID_ARGUMENT` | Fail doc → quarantine (§21.2) |
| `boundary_embedding_model_id` unset or model not loaded | `FAILED_PRECONDITION` | Fail doc → quarantine (§21.3) |
| Stage invariant violation at entry | `FAILED_PRECONDITION` | Fail doc → quarantine |
| DJL `NOT_FOUND` (model doesn't exist) | `INVALID_ARGUMENT` | Fail doc → quarantine |
| DJL `INVALID_ARGUMENT` (bad input) | `INVALID_ARGUMENT` | Fail doc → quarantine |
| DJL transient (UNAVAILABLE, DEADLINE, RESOURCE_EXHAUSTED) | `INTERNAL` | Retry bounded, then fail → DLQ |
| Chunker internal error | `INTERNAL` | Retry bounded, then fail → DLQ |
| Redis error | `—` (never fails doc) | WARN + compute-through |
| Hard cap exceeded (e.g., semantic boundary groups > max) | `INTERNAL` | Fail doc → DLQ, with descriptive message |

**No partial results. No silent fallbacks. No "default on parse failure."** If the step can't produce a correct output, the doc fails and goes to DLQ or quarantine.

### 10.2 Retry policy

- Only the embedder step retries internally (for transient DJL errors). Chunker and semantic-graph retry at the engine level only.
- Bounded: `EmbedderStepOptions.effectiveMaxRetryAttempts()` (default 2).
- Backoff: exponential starting from `effectiveRetryBackoffMs()` (default 100ms), multiplier 2.
- Retries are on the DJL call only, not on the Redis cache layer.

## 11. Deterministic Ordering

Every step sorts `semantic_results[]` at the end of processing by lex order on the tuple:

```
(source_field_name, chunk_config_id, embedding_config_id, result_id)
```

All four fields are strings. Empty strings sort first. This ordering is stable, reproducible, and makes `git diff` on textpb fixtures useful.

**Why `result_id` as the final tiebreaker:** if two SPRs share the first three fields (possible for centroid SPRs at different granularities when the config_id happens to match), the `result_id` disambiguates.

**Other deterministic requirements:**
- `chunk_id` is a function of `(source_field, chunker_config_id, chunk_number)` or `(source_field, chunker_config_id, start_offset)` — implementation choice but must be deterministic.
- `result_id` is a function of the tuple above plus stage marker.
- Floating-point vector values are deterministic within a single DJL model version (the extension guarantees this, not us).

## 12. Follow-up Integration Points

Two stub interfaces exist in their home repos to unblock the refactor. They are no-ops today and will be implemented in follow-up work (tasks #78, #79).

### 12.1 `DirectivePopulator` (in `pipestream-engine`)

```java
public interface DirectivePopulator {
    /**
     * Populates VectorSetDirectives on a PipeDoc before it enters the semantic sub-pipeline.
     * Current implementation: no-op passthrough.
     * Future implementation: reads VectorSetEntity rows referenced in graph config,
     * converts them to VectorDirective, attaches to doc.search_metadata.vector_set_directives.
     */
    Uni<PipeDoc> populateDirectives(PipeDoc input, GraphNode targetNode);
}
```

Stub implementation:
```java
@ApplicationScoped
public class NoOpDirectivePopulator implements DirectivePopulator {
    @Override
    public Uni<PipeDoc> populateDirectives(PipeDoc input, GraphNode targetNode) {
        return Uni.createFrom().item(input);
    }
    // TODO task #78: replace with VectorSetEntity-driven implementation
}
```

Wired into `EngineV1Service.processNode` before dispatch. Until the real implementation lands, upstream (testing-sidecar, mapper step, or an ad-hoc setup step) is responsible for populating `doc.search_metadata.vector_set_directives` before the chunker node runs. Per §21.1 there is no fallback — absent directives mean the doc fails the chunker step.

### 12.2 `VectorSetProvisioner` (in `pipestream-opensearch/opensearch-manager`)

```java
public interface VectorSetProvisioner {
    /**
     * Ensures the OpenSearch index has knn_vector fields corresponding to the given directives.
     * Current implementation: no-op (relies on existing lazy ensureFlatKnnField at index time).
     * Future implementation: eagerly creates VectorSetEntity rows and calls the indexing
     * strategy to put mappings before any docs arrive.
     */
    Uni<Void> ensureFieldsForDirectives(VectorSetDirectives directives, String indexName);
}
```

Stub implementation:
```java
@ApplicationScoped
public class NoOpVectorSetProvisioner implements VectorSetProvisioner {
    @Override
    public Uni<Void> ensureFieldsForDirectives(VectorSetDirectives directives, String indexName) {
        return Uni.createFrom().voidItem();
    }
    // TODO task #79: replace with eager VectorSetEntity creation + putMapping
}
```

Why this is a no-op and why that's OK for now: `SeparateIndicesIndexingStrategy.ensureFlatKnnField` and `ChunkCombinedIndexingStrategy.ensureFlatKnnField` already create missing knn_vector fields lazily at indexing time with race-safe retry. The provisioner interface exists so a future eager path can hook in without another refactor.

## 13. Performance Gates

Baselines measured against the `pre-semantic-refactor` tag (pre-refactor commit on all repos):

| Metric | Baseline | Refactor target (merge gate) |
|---|---|---|
| 3-doc JDBC E2E (gRPC) wall clock | 10.5s | **≤ 5s** |
| 20-doc JDBC E2E (gRPC) wall clock | 25.6s | **≤ 15s** |
| 100-doc JDBC E2E (gRPC) wall clock | (not measured cleanly) | **≤ 60s** |
| 3-doc JDBC E2E (kafka) wall clock | working post-purge | **within 10% of gRPC** |
| Per-doc embedder step p95 latency | ~1.5s | **≤ 1s** |
| Per-doc semantic-graph step p95 latency | (not measured) | **≤ 500ms** |
| Embedder cache hit rate on identical re-crawl | 0 (no cache today) | **≥ 90%** |
| Chunker cache hit rate on identical re-crawl | 0 (no cache today) | **≥ 95%** |
| Full test suite per module | passing on pre-tag | **passing on refactor** |

Refactor merge is blocked until all gates are met on a clean run of the testing-sidecar E2E tab.

## 14. Testing Strategy

### 14.1 Unit tests per module

- **module-chunker:** `ChunkerGrpcImpl` tests that parse various configs (happy path, missing fields, invalid types), produce expected SPRs for fixtures, verify cache behavior (hit/miss/writeback/outage).
- **module-embedder:** `EmbedderGrpcImpl` tests with a mocked `DjlEmbeddingProvider` that returns deterministic fake vectors. Verify fan-out, cache MGET/MSET, retry behavior on transient errors, fail-fast on permanent errors.
- **module-semantic-graph:** tests with fixed Stage 2 input fixtures, assert exact Stage 3 output via `assertPostSemanticGraph`. `DjlEmbeddingProvider` mocked to return deterministic fake vectors for boundary re-embed.

### 14.2 Stage fixture tests (shared)

- `SemanticPipelineFixtures.java` helper generates canonical `PipeDoc`s for each stage.
- Committed `.textpb` files in `pipestream-protos/testdata/semantic-pipeline/`:
  - `stage0_raw.textpb`
  - `stage1_post_chunker.textpb`
  - `stage2_post_embedder.textpb`
  - `stage3_post_semantic_graph.textpb`
- `SemanticPipelineInvariants.java` asserter shared across modules.
- Each module's tests: "my step takes stage N input and produces stage N+1 output that passes `assertPostStageN+1`."

### 14.3 Wiremock-backed integration tests

Three new stage-transition helpers added to `pipestream-wiremock-server`:
- `ChunkerStepMock`: produces Stage 1-shaped output for `PipeStepProcessorService.ProcessData` calls with the `x-module-name: chunker` header
- `EmbedderStepMock`: produces Stage 2-shaped output for calls with `x-module-name: embedder`
- `SemanticGraphStepMock`: produces Stage 3-shaped output for calls with `x-module-name: semantic-graph`

These are **a separate PR from the module refactors** (P1). They ship first so each module's integration test can run against the mocks for upstream/downstream steps without requiring the real other modules.

**Constraints of the wiremock-server project — must be respected:**

- **Does NOT consume `pipestream-bom`.** The wiremock server is deliberately independent of the platform's BOM so changes to the main build don't cascade into mock breakage. All version pinning is local to its own `build.gradle` + `libs.versions.toml`.
- **Depends only on `pipestream-protos`** (fetched via the proto toolchain) plus WireMock, Jackson, SLF4J, and whatever it already uses. No `module-*` dependency, no shared-lib dependency from any service repo.
- **`generateMutiny = false`** in the proto toolchain block. The mocks use plain gRPC stubs, not Mutiny stubs. All new mock code uses `BlockingStub` equivalents and raw protobuf classes from `pipestream-protos`.
- **Mocks are not Quarkus `@GrpcService` classes.** They use `org.wiremock.grpc.dsl.WireMockGrpcService` to register stub mappings for method + request patterns. Dynamic per-request matching goes through `wireMock.register(...)` with header matchers.
- **Mocks implement `ai.pipestream.wiremock.client.ServiceMockInitializer`** — auto-discovered via ServiceLoader at server startup through `ServiceMockRegistry`.
- **`x-module-name` gRPC metadata header** is the standard discriminator when multiple modules share a gRPC service (which all three refactored steps do — they all implement `PipeStepProcessorService`). Each mock registers header-matched stubs so the same WireMock instance can serve different Stage N→N+1 transitions depending on which "module" the caller claims to be.

**Implementation note for the three mock classes:** since the three refactored steps all implement the same `PipeStepProcessorService`, each mock class's stubs must be scoped by `x-module-name` header to avoid collisions. The pattern is already established in `PipeStepProcessorMock.mockGetServiceRegistration`. New mocks extend that pattern.

**Forward-looking usage:** the wiremock server is also intended as a tool for front-end developers to build UI prototypes against a known-good mock of the platform. All new mocks should therefore expose deterministic, configurable scenarios (success / failure / partial / slow) rather than fixed-response stubs, so FE devs can flip between cases without rebuilding the server.

### 14.4 End-to-end tests

`module-testing-sidecar` already runs JDBC and transport E2E. After the refactor, the E2E graph wiring changes to `chunker → embedder → semantic-graph → opensearch-sink`. The existing E2E test infrastructure (which creates the graph via the engine's `PipelineGraphService`) gets updated to use the new node topology. No fundamental change to how E2E works.

## 15. Parallel Work Model

With P0–P6 done:
- Module-chunker, module-embedder, module-semantic-graph can be refactored **in parallel** on three separate worktrees/PRs.
- Each module validates against:
  1. `SemanticPipelineInvariants` (stage assertions)
  2. The wiremock mocks for upstream/downstream steps
  3. The committed `.textpb` fixtures as golden input/output
- Integration happens when all three modules pass their own contract tests. The `module-testing-sidecar` graph-wiring PR follows.

**Who owns the fixtures:** the fixtures live in `pipestream-protos` and are locked during parallel work. Any PR that needs to change the fixtures must stop, coordinate, and either update all three modules or get a design-doc amendment first. Treat fixture changes as contract breaks.

## 16. Rollback Plan

Every affected repo has a `pre-semantic-refactor` tag at its current main HEAD. To roll back any individual refactor PR:
```
git -C <repo> checkout pre-semantic-refactor
```
Or roll back via git revert of the refactor merge commit if the tag has moved.

Because protos are untouched and the output shape is preserved, a rollback of any one module returns that module to its pre-refactor state without breaking the others. The stub interfaces (DirectivePopulator, VectorSetProvisioner) are no-ops regardless of which module is rolled back.

## 17. Work Ordering

Preliminary work (blocking, must complete before refactor PRs):

| Phase | Deliverable | Repo |
|---|---|---|
| **P0** | This DESIGN.md | pipestream-protos |
| **P0.5** | `pipestream-dev.sh` for autonomous dev-mode management | dev-assets |
| **P1** | Three stage-transition mock helpers (`ChunkerStepMock`, `EmbedderStepMock`, `SemanticGraphStepMock`) with FE-friendly scenario toggles | pipestream-wiremock-server |
| **P2** | Stage fixtures (`.textpb` + Java helper + invariants) | pipestream-protos |
| **P3** | Java config records | each module |
| **P4** | Stub `DirectivePopulator` + `VectorSetProvisioner` | pipestream-engine + pipestream-opensearch |
| **P5** | Verify DJL extension API | quarkus-djl-embeddings |

Refactor work (parallelizable after P0–P5):

| Phase | Deliverable | Repo |
|---|---|---|
| **R1** | Chunker refactor | module-chunker |
| **R2** | Embedder refactor | module-embedder |
| **R3** | Semantic-graph refactor | module-semantic-graph |
| **R4** | Engine graph wiring update | module-testing-sidecar |
| **R5** | Full E2E verification against gates | module-testing-sidecar |

R1, R2, R3 can run concurrently. R4 depends on all three. R5 depends on R4.

## 18. Appendix A: Example `VectorDirective`

A typical directive set for a JDBC crawl test account:

```protobuf
vector_set_directives {
  directives {
    source_label: "body"
    cel_selector: "document.search_metadata.body"
    chunker_configs {
      config_id: "token_500_50"
      config {
        fields {
          key: "algorithm"
          value { string_value: "TOKEN" }
        }
        fields {
          key: "chunk_size"
          value { number_value: 500 }
        }
        fields {
          key: "chunk_overlap"
          value { number_value: 50 }
        }
      }
    }
    chunker_configs {
      config_id: "sentence_10_3"
      config {
        fields {
          key: "algorithm"
          value { string_value: "SENTENCE" }
        }
        fields {
          key: "chunk_size"
          value { number_value: 10 }
        }
        fields {
          key: "chunk_overlap"
          value { number_value: 3 }
        }
      }
    }
    embedder_configs {
      config_id: "minilm_v2"
      config {
        fields {
          key: "model_id"
          value { string_value: "all-MiniLM-L6-v2" }
        }
      }
    }
    embedder_configs {
      config_id: "paraphrase_l3"
      config {
        fields {
          key: "model_id"
          value { string_value: "paraphrase-MiniLM-L3-v2" }
        }
      }
    }
    field_name_template: "{source_label}_{chunker_id}_{embedder_id}"
  }
}
```

Expected Stage 1 output: 2 placeholder SPRs (one per chunker config) + the `sentences_internal` SPR if it's not already covered.

Expected Stage 2 output: 4 populated SPRs (2 chunker × 2 embedder) + embedded sentences_internal SPRs (2, one per embedder model on the sentence chunks).

Expected Stage 3 output: Stage 2 + centroid SPRs for each populated combo + optional semantic-boundary SPRs using the sentence vectors.

## 19. Appendix B: Proto Reference

All proto messages referenced in this document already exist. No changes required.

- `PipeDoc`: `pipestream-protos/common/proto/ai/pipestream/data/v1/pipeline_core_types.proto:68`
- `SearchMetadata`: same file, line 128
- `SemanticProcessingResult`: same file, line 829
- `SemanticChunk`: same file, line 812
- `ChunkEmbedding`: same file, line 776
- `CentroidMetadata`: same file, line 796
- `NlpDocumentAnalysis`: same file (search for `message NlpDocumentAnalysis`)
- `DocumentAnalytics`: same file, line 1144
- `ChunkAnalytics`: same file, line 1188
- `SourceFieldAnalytics`: same file, line 1244
- `VectorSetDirectives`: same file, line 1063
- `VectorDirective`: same file, line 1075
- `NamedChunkerConfig`: same file, line 1115
- `NamedEmbedderConfig`: same file, line 1126
- `DocOutline` / `Section`: same file, line 220+
- `PipeStepProcessorService`: `pipestream-protos/common/proto/ai/pipestream/data/module/v1/` (existing pipeline step interface)
- `ProcessDataRequest` / `ProcessDataResponse` / `ProcessConfiguration`: same package

No new messages, no new fields, no new services.

## 20. Open Questions

None. All six original decisions (rename scope, DESIGN.md location, wiremock PR ordering, stub interfaces, fixture format, DJL extension dependency) have been answered. §21 locks review amendments from the Codex review pass.

---

## 21. Design Amendments (Review Lock)

These amendments override any conflicting text above. Earlier sections will be inlined to match §21 in a cleanup pass before P0 is marked shippable; until then, treat §21 as authoritative wherever it covers the same topic.

### 21.1 No fallback behavior (hard rule)
- There is **zero fallback path** for directive/config resolution in v1.
- Remove `legacy_fallback` from all step option schemas and code paths.
- If directives are absent or invalid, step fails with `FAILED_PRECONDITION` or `INVALID_ARGUMENT`.
- If config parse fails, step fails. No default-on-parse-failure behavior.
- **Implication:** the testing-sidecar (and any other graph-creator) MUST populate `doc.search_metadata.vector_set_directives` on every PipeDoc entering the semantic sub-pipeline. The `DirectivePopulator` stub (§12.1) can stay a no-op passthrough for v1 as long as upstream ensures directives are present. If upstream does not set directives, v1 fails closed.

### 21.2 Source label uniqueness + directive identity
- `VectorDirective.source_label` MUST be unique within a single document's directive list.
- Validation fails fast if duplicate `source_label` is present.
- Matching by source label alone is not sufficient for long-term safety. Add a deterministic directive key:
  - `directive_key = sha256b64url(source_label + "|" + cel_selector + "|" + sorted_chunker_config_ids + "|" + sorted_embedder_config_ids)`
- Stamp `directive_key` into `SemanticProcessingResult.metadata["directive_key"]` at Stage 1.
- Step 2 and Step 3 correlate by `directive_key` first, `source_label` second.
- Invariants §5.1/5.2/5.3 implicitly include "every SPR carries `metadata["directive_key"]` matching its source directive"; assertion helpers will check this.

### 21.3 Explicit model requirements in semantic-graph
- Remove any "first available model" behavior.
- `boundary_embedding_model_id` must be explicit and resolvable.
- If model is missing/unloaded, fail with `FAILED_PRECONDITION`.

### 21.4 Empty CEL selector output policy
- Empty CEL output is allowed for optional fields and is treated as a skipped directive input (not a failure).
- Type mismatch or selector evaluation error is still `INVALID_ARGUMENT`.

### 21.5 Deterministic IDs (replace UUID usage)
- `result_id` and `chunk_id` must be deterministic; UUID generation is prohibited in pipeline outputs.
- Canonical forms:
  - `result_id = "{stage}:{docHash}:{source_label}:{chunk_config_id}:{embedding_config_id}"`
  - `chunk_id  = "{docHash}:{source_label}:{chunk_config_id}:{chunk_number}:{start}:{end}"`
- `docHash = sha256b64url(doc_id)` (or full deterministic doc key if `doc_id` is not stable).
- This replaces random UUID result IDs and prefix-truncated ID derivation throughout.
- `{stage}` values: `"stage1"`, `"stage2"`, `"stage3-centroid-{granularity}"`, `"stage3-boundary"`.

### 21.6 Redis via Quarkus APIs (with batch-aware caveat)
- Use Quarkus Redis primitives for production cache behavior.
- For embed cache, **use `ReactiveRedisDataSource`** (not `@CacheResult`) because embed hydration needs batch `MGET` + batch writeback to avoid N per-doc round-trips. `ReactiveRedisDataSource.value(String.class, byte[].class).mget(keys)` returns all hits in one call.
- Annotation-only caching (`@CacheResult`) is acceptable for small single-key paths (e.g. per-text-hash NLP analysis lookup in the chunker) but not sufficient for high-throughput per-batch embed hydration by itself.
- Chunker cache may use `@CacheResult` or `ReactiveRedisDataSource` — implementer's choice based on measured lookup count per doc.

### 21.7 RTBF constraints
- For streams/docs under Right-To-Be-Forgotten (RTBF) constraints, do not persist recoverable payload state that violates policy.
- The RTBF marker lives on the stream/doc metadata (exact field TBD — likely `PipeStream` or `OwnershipContext`); all three modules read it via a shared predicate `RtbfPolicy.isSuppressed(doc)`.
- **Cache writes must be suppressible for RTBF-marked traffic.** Both the chunker and embedder check the RTBF predicate before writing to Redis. Reads are still allowed (cached values from non-RTBF identical text can still serve RTBF requests — those values contain no identifying payload).
- **Failure handling (DLQ/quarantine) must follow RTBF policy gates** (`DO NOT SAVE` where configured). A failing RTBF doc goes through the same error semantics but with any recoverable payload omitted. The sidecar's `save_on_error` path already has a suppression hook — the modules must honor it.
- **Tests required** for RTBF + failure path interactions: a doc with RTBF set that hits a transient embedder error should retry without writing its text to the cache or to the save_on_error store.
- The concrete `RtbfPolicy` implementation is out of scope for this refactor but the interface + suppression checks are in scope.

### 21.8 Ordering and invariants remain mandatory
- Preserve deterministic sort contract at each stage (lex on `(source_field_name, chunk_config_id, embedding_config_id, result_id)`).
- Preserve strict stage assertions:
  - Post-chunker: placeholders only (`embedding_config_id == ""`)
  - Post-embedder: no placeholders
  - Post-semantic-graph: appended semantic layering only (Stage 2 preserved untouched)

### 21.9 Sentences_internal policy
- `sentences_internal` stays in-pipeline as first-class data for hydration and semantic boundary work.
- Indexing exposure/filtering is a **sink-side policy toggle**, not a chunker/embedder/semantic-graph concern. The three refactored modules always produce/preserve the sentence SPR; the sink decides whether to persist it.
- No opt-out knob in chunker/embedder/semantic-graph for sentence emission.

---

## 22. Appendix C: Measured Baselines (pre-refactor)

All numbers in this appendix are from runs captured before the `pre-semantic-refactor` tag was cut on each affected repo. They are the evidence behind the goals in §1, the gate targets in §13, and the decision in §21 to split `module-semantic-manager` into three stateless steps instead of tuning it. Sources are cited by session date so future work can recover the raw logs if needed.

### 22.1 E2E wall clock (JDBC crawl through opensearch-sink)

| Scale | Transport | Wall clock | Pass | Notes |
|---|---|---|---|---|
| 3 docs | gRPC | 10.5 s | 3/3 | §13 baseline, same JDBC test account |
| 20 docs | gRPC | 25.6 s | 20/20 | §13 baseline |
| 100 docs | gRPC + semantic | — | 100/100 | 38,388 chunks across 7 chunk types, zero embedding failures (2026-04-07, edge-case-fixes) |
| 1000 docs | gRPC + semantic | — | 1000/1000 | 274,695 chunks, 7 chunk indices (2026-04-07, connector-crud-perf) |
| 1000 docs | Kafka + semantic | ~20 min | 1000/1000 | 274,695 chunks, 714 MB; test wrapper timed out at 600 s but Kafka kept draining; sentence chunks = 172,664 / 274,695 = 63% of all chunks (2026-04-07, connector-crud-perf) |

The 100-doc and 1000-doc runs were instrumented only for correctness counts, not clean wall clock — which is why §13 lists 100-doc as "not measured cleanly." Establishing a clean 100-doc wall-clock baseline is itself a deliverable of R5.

### 22.2 Per-doc chunker-only fixtures (OpenNLP 3.0.0-M1, virtual-thread POS tagging)

Measured on `module-chunker` in isolation after the 2026-03-28 multi-config refactor. The chunker does a single NLP pass per document regardless of how many chunk configs are active.

| Fixture | Docs | Chunk configs | Wall clock | Per-doc | Breakdown |
|---|---|---|---|---|---|
| Bible KJV (4.5 MB, 948 K tokens, 30 K sentences) | 1 | 2 | 36 s | — | NLP pass 33 s (POS tagging parallelized across virtual threads), chunking < 1 s, per-chunk analytics < 1 s |
| Court opinions | 10 | 2 | 13.6 s | 1.36 s/doc | 2026-03-28, semantic-pipeline session |

The Bible figure is the worst-case single-doc NLP pass currently on record; everything smaller is bounded by it.

### 22.3 Throughput chain at 1000-doc semantic scale (2026-04-07)

Per-stage cost measured on the 1000-doc Kafka + semantic run:

| Stage | Per-doc cost | Bottleneck? |
|---|---|---|
| JDBC crawl + intake | ~10 ms | no |
| Standard chunking | ~100 ms | no |
| **DJL embedding (all models × all chunk types)** | **5–130 s** | **yes** |
| OpenSearch bulk indexing | ~1–5 s | no |

The 1000× spread on DJL embedding is the dominant cost. This is why §9 and §21.6 concentrate the cache investment on `embed:{sha256b64url(text)}:{model_id}` with `ReactiveRedisDataSource.mget` — single Redis round-trip to hydrate an entire placeholder SPR's worth of chunks, instead of N per-chunk round-trips.

### 22.4 `module-semantic-manager` per-doc cost at 1000-doc semantic scale

Measured on the current (pre-refactor) `module-semantic-manager` with all semantic strategies enabled (chunker fan-out + embedder fan-out + centroids + semantic boundaries):

- **Average per-doc: 419 s**
- **Max per-doc: 1005 s**
- GPU utilization: idle most of the time
- OpenSearch CPU: idle most of the time
- Sentence chunks alone = 63% of all chunks and dominated embedding time
- `opensearch-sink` OOMed at `-Xmx4g` receiving a PipeDoc with 172 K sentence chunks; had to be bumped to `-Xmx10g` for semantic docs
- Source: 2026-04-07 connector-crud-perf session

This is the concrete evidence behind goal #1 in §1. 419 s/doc averaged across a 1000-doc run with both the GPU and OpenSearch CPUs idle is not a tuning problem — no semaphore, executor, or thread-pool adjustment closes a gap that size when the bottleneck resources are sitting idle. The orchestrator was serializing its own cross-stage coordination inside one JVM. The three-step split fixes this structurally because:

1. Each step is stateless per doc and has no cross-stage coordination to serialize.
2. Cross-doc concurrency comes from the engine's slot config on each node, not from in-process scatter-gather.
3. Each step's output shape is an assertable invariant on `search_metadata.semantic_results[]`, so regressions in throughput, correctness, or ordering are caught by stage fixtures instead of by reading flamegraphs.

### 22.5 Known failure mode not to regress past (RTBF + sentence-loss)

The refactor is not allowed to re-introduce either of these. R5 verification runs must explicitly check both.

**MiniLM sentence-chunk loss on Kafka transport (2026-04-06, embedding-simplification):**
- JDBC Kafka 100-doc E2E indexed 100/100 docs.
- Sentence-chunk MiniLM vectors: **168 / 312 populated (46% miss)**.
- Same run: paraphrase vectors 312/312, token-chunk MiniLM vectors 96/96.
- Loss was specific to: Kafka transport × sentence chunker × MiniLM model. gRPC path was 100%. Token chunks under MiniLM were 100%. Paraphrase under sentence chunks was 100%.
- Hypothesis on record: StreamEmbeddings batches for MiniLM on sentence chunks hit DJL 400s that were not retried; failed batches got indexed without their MiniLM vectors.
- Root cause not yet isolated. Any regression of this pattern after R1–R5 is a merge blocker. The `module-embedder` refactor (§7.2) must either reproduce the loss against the mocks and fix it, or prove via test that the new retry path (R2) cannot leave a chunk with a null vector.

### 22.6 How the gates in §13 map onto these baselines

The merge gates in §13 are calibrated against the numbers in §22.1–§22.4. Hitting them means the three-step split has to deliver:

| Gate | Baseline | Required speedup | Where it comes from |
|---|---|---|---|
| 3-doc JDBC gRPC ≤ 5 s | 10.5 s | 2.1× | Embed cache hit on re-runs; in-process DJL vs. prior inter-process hop on cold runs |
| 20-doc JDBC gRPC ≤ 15 s | 25.6 s | 1.7× | Same as above + deterministic cross-doc parallelism from engine slot config |
| 100-doc JDBC gRPC ≤ 60 s | not measured cleanly | establishes a baseline | R5 deliverable — first clean 100-doc wall clock |
| Embedder p95 ≤ 1 s | ~1.5 s | 1.5× | Redis `MGET` hits + DJL extension warm-start |
| Semantic-graph p95 ≤ 500 ms | semantic-manager avg 419 s (**different workload**) | — | Not a direct comparison: semantic-graph in the new design does NOT run embedder fan-out. It only computes centroids (CPU math on existing vectors) and re-embeds ≤ 50 boundary vectors. 500 ms is realistic for that scope. |
| Chunker cache hit ≥ 95% on identical re-crawl | 0 (no cache today) | — | Redis chunk cache (§9.1) keyed on `(text_hash, chunker_config_id)` |
| Embedder cache hit ≥ 90% on identical re-crawl | 0 (no cache today) | — | Redis embed cache (§9.1) keyed on `(text_hash, embedding_config_id)` |
| Kafka transport within 10% of gRPC | 1000-doc Kafka took ~20 min wrapper timeout vs. gRPC all-passed | — | Correctness-first: 22.5 must not regress |

**Important caveat on the semantic-graph gate.** The 419 s/doc average for `module-semantic-manager` and the 500 ms p95 target for `module-semantic-graph` are not measuring the same work. The orchestrator owned chunking + embedding + centroids + boundary detection + fan-out + state assembly. The new `module-semantic-graph` owns only centroids + boundary detection + ≤ 50 in-process DJL calls. The 500 ms gate is set against that narrower scope; do not read the comparison as a raw 800× speedup claim.

### 22.7 Instrumentation owed by R5

R5 must capture, at minimum, on a clean run of the testing-sidecar E2E tab:

- Wall clock for 3-doc, 20-doc, and 100-doc JDBC gRPC + semantic runs.
- Wall clock for 3-doc and 20-doc JDBC Kafka + semantic runs (for the §13 "within 10% of gRPC" gate).
- Per-step p95 latency for chunker, embedder, semantic-graph — read from the existing pipeline-events audit trail, not from ad-hoc timers.
- Cache hit rate for `chunk:*` and `embed:*` keys on an identical re-crawl (a cold crawl followed immediately by the same crawl again; measure hit rate on the second pass).
- MiniLM sentence-chunk vector coverage across both transports for §22.5.
- opensearch-sink heap headroom on the 100-doc semantic run (the 2026-04-07 OOM at `-Xmx4g` is the baseline constraint here; the new design does not change the sink's input shape, so the same heap floor applies until sink batching lands).

These numbers, appended as `§22.1` / `§22.3` / `§22.5` updates after R5 passes, become the new `pre-refactor` baseline in the next cycle.

---

**End of design.**
