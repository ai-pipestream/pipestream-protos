# Integration Alignment: Chunker, Embedder, and opensearch-manager

This document describes what **module-chunker**, **module-embedder** (embedder), and **opensearch-manager** need from each other so they can be developed concurrently. Use this as the handoff spec for parallel work.

---

## Kafka Topic Names (Aligned)

| Topic | Producer | Consumers | Purpose |
|-------|----------|-----------|---------|
| **semantic-metadata-events** | opensearch-manager | module-chunker, module-embedder (optional) | ChunkerConfig, EmbeddingModelConfig, IndexEmbeddingBinding CRUD events |

Single topic with `SemanticMetadataEvent` envelope; use `event_type` to discriminate.

---

## Event Schema

**Proto:** `ai.pipestream.opensearch.v1.SemanticMetadataEvent`

**Event types:**
- `SEMANTIC_METADATA_EVENT_TYPE_CHUNKER_CONFIG_CREATED`
- `SEMANTIC_METADATA_EVENT_TYPE_CHUNKER_CONFIG_UPDATED`
- `SEMANTIC_METADATA_EVENT_TYPE_CHUNKER_CONFIG_DELETED`
- `SEMANTIC_METADATA_EVENT_TYPE_EMBEDDING_MODEL_CONFIG_CREATED`
- `SEMANTIC_METADATA_EVENT_TYPE_EMBEDDING_MODEL_CONFIG_UPDATED`
- `SEMANTIC_METADATA_EVENT_TYPE_EMBEDDING_MODEL_CONFIG_DELETED`
- `SEMANTIC_METADATA_EVENT_TYPE_INDEX_EMBEDDING_BINDING_CREATED`
- `SEMANTIC_METADATA_EVENT_TYPE_INDEX_EMBEDDING_BINDING_UPDATED`
- `SEMANTIC_METADATA_EVENT_TYPE_INDEX_EMBEDDING_BINDING_DELETED`

**Fields:** `event_type`, `entity_id`, `occurred_at`, `payload` (oneof), `previous_payload` (oneof, for UPDATE)

---

## What module-chunker Needs

### 1. ChunkerConfig lookup (optional, future)

- **gRPC:** `ChunkerConfigService.GetChunkerConfig` (by id or by name)
- **Purpose:** Resolve a registered ChunkerConfig by `config_id` or name before chunking
- **Current state:** Chunker gets config inline from pipeline (ProcessConfiguration). Registry lookup is optional for validation/pre-registered configs.
- **Action for chunker thread:** No immediate changes. When ready, add optional call to opensearch-manager `ChunkerConfigService.GetChunkerConfig(config_id)` to validate or hydrate config. Chunker continues to accept inline JSON config.

### 2. Kafka consumer for semantic-metadata-events (optional)

- **Topic:** `semantic-metadata-events`
- **Filter:** `event_type` in `CHUNKER_CONFIG_*`
- **Purpose:** Invalidate local cache of ChunkerConfig when configs change (e.g. admin updates a config)
- **Action for chunker thread:** Add consumer for `semantic-metadata-events`, filter by ChunkerConfig events, clear any cached config for `entity_id` on UPDATE/DELETE

### 3. config_id format (already defined)

- **Format:** `{algorithm}-{sourceField}-{chunkSize}-{chunkOverlap}`
- **Examples:** `token-body-512-50`, `sentence-title-1000-100`
- **Source:** `ChunkerConfig.generateConfigId()` in module-chunker
- **Alignment:** opensearch-manager derives `config_id` from `config_json` using the same formula when `config_id` is omitted in CreateChunkerConfigRequest

---

## What module-embedder Needs

### 1. EmbeddingModelConfig lookup

- **gRPC:** `EmbeddingConfigService.GetEmbeddingModelConfig` (by id or by name)
- **Purpose:** Resolve embedding model (model_identifier, dimensions) for a given config id/name
- **Action for embedder thread:** Call opensearch-manager to get EmbeddingModelConfig before embedding; use dimensions for vector output, model_identifier for model selection

### 2. IndexEmbeddingBinding lookup (for index-aware embedding)

- **gRPC:** `EmbeddingConfigService.GetIndexEmbeddingBinding` or `ListIndexEmbeddingBindings(index_name)`
- **Purpose:** Determine which embedding config applies to a given index/field
- **Action for embedder thread:** When indexing to OpenSearch, resolve binding for `(index_name, field_name)` to get `embedding_model_config_id` → fetch EmbeddingModelConfig for dimensions/model

### 3. Kafka consumer for semantic-metadata-events (optional)

- **Topic:** `semantic-metadata-events`
- **Filter:** `event_type` in `EMBEDDING_MODEL_CONFIG_*`, `INDEX_EMBEDDING_BINDING_*`
- **Purpose:** Invalidate cache when embedding configs or bindings change
- **Action for embedder thread:** Add consumer, clear cached configs on UPDATE/DELETE

---

## What opensearch-manager Provides (Ready or In Progress)

| API | Status | Notes |
|-----|--------|-------|
| ChunkerConfigService CRUD | In progress | Proto committed; Java impl done; commit chunker_config.proto to pipestream-protos main |
| EmbeddingConfigService CRUD | Ready | Already implemented |
| IndexEmbeddingBinding CRUD | Ready | Already implemented |
| Kafka producer for semantic-metadata-events | To do | Publish on Create/Update/Delete |
| Topic: semantic-metadata-events | Defined | Proto defines event schema; create topic in Kafka |

---

## UUID in Protobufs

**Recommendation:** Use `string` for UUID fields. Protocol Buffers has no built-in UUID type.

- **id** (primary key): `string` in UUID format (e.g. `"550e8400-e29b-41d4-a716-446655440000"`)
- **config_id** (computed stable id): `string` (e.g. `"token-body-512-50"`)

**Optional:** `ai.pipestream.types.v1.Uuid` message exists in common for semantic typing when desired. Most fields continue to use `string` for simplicity.

---

## Proto Files to Commit to pipestream-protos main

1. **common/proto/ai/pipestream/types/v1/uuid.proto** – Optional UUID type
2. **opensearch/proto/ai/pipestream/opensearch/v1/chunker_config.proto** – ChunkerConfigService (documented, linted, formatted)
3. **opensearch/proto/ai/pipestream/opensearch/v1/semantic_metadata_events.proto** – Event schema and topic alignment

**Buf checks before commit:**
- `buf lint` (STANDARD)
- `buf format -w`
- All fields documented
- File-level plain English description where appropriate
