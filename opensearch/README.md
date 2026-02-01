# OpenSearch Proto Module

This module defines the protocol buffer schemas for OpenSearch indexing, search, and semantic metadata management.

## Overview

The OpenSearch module provides gRPC services and message types for:

1. **Document Indexing** - Canonical document structure for OpenSearch with vector embeddings
2. **Embedding Configuration** - CRUD for embedding model configs and index-field bindings
3. **Chunker Configuration** - CRUD for text chunking strategies and parameters
4. **OpenSearch Management** - Index lifecycle, schema management, and search operations

## Services

### OpenSearchManagerService

Manages OpenSearch indices, documents, and search operations.

**Key RPCs:**
- `CreateIndex` - Create index with vector field mappings
- `IndexDocument` - Index a canonical OpenSearchDocument
- `IndexAnyDocument` - Index arbitrary protobuf messages with dynamic mapping
- `SearchFilesystemMeta` - Search documents with highlighting and pagination

### EmbeddingConfigService

Manages embedding model configurations and index-to-embedding bindings.

**Key RPCs:**
- `CreateEmbeddingModelConfig` - Register an embedding model (name, identifier, dimensions)
- `CreateIndexEmbeddingBinding` - Bind an embedding model to an index field
- CRUD operations for both configs and bindings

### ChunkerConfigService

Manages chunker configurations for text splitting strategies.

**Key RPCs:**
- `CreateChunkerConfig` - Register a chunking strategy (algorithm, size, overlap)
- CRUD operations with JSON blob storage for flexibility

## Data Model

### Semantic Metadata Architecture

```mermaid
graph TB
    subgraph "Document Processing Pipeline"
        DOC[Document] --> CHUNK[Chunker Service]
        CHUNK --> EMBED[Embedder Service]
        EMBED --> INDEX[OpenSearch Index]
    end
    
    subgraph "Semantic Metadata Service (opensearch-manager)"
        CC[ChunkerConfig]
        EMC[EmbeddingModelConfig]
        VS[VectorSet]
        IVB[IndexVectorBinding]
        
        CC -->|references| VS
        EMC -->|references| VS
        VS -->|maps to| IVB
        IVB -->|defines| INDEX
    end
    
    subgraph "Audit Trail"
        CHUNK -->|produces| SPR[SemanticProcessingResult]
        SPR -->|contains| CID[chunk_config_id]
        SPR -->|contains| EID[embedding_config_id]
        
        CID -.->|traces back to| CC
        EID -.->|traces back to| EMC
    end
    
    style CC fill:#e1f5ff
    style EMC fill:#e1f5ff
    style VS fill:#fff4e1
    style IVB fill:#f0f0f0
```

### Entity Relationships

```mermaid
erDiagram
    ChunkerConfig ||--o{ VectorSet : "used by"
    EmbeddingModelConfig ||--o{ VectorSet : "used by"
    VectorSet ||--o{ IndexVectorBinding : "maps to"
    IndexVectorBinding }o--|| OpenSearchIndex : "populates"
    
    ChunkerConfig {
        uuid id PK
        string name UK
        string config_id UK
        jsonb config_json
        string schema_ref
        timestamp created_at
        timestamp updated_at
        jsonb metadata
    }
    
    EmbeddingModelConfig {
        uuid id PK
        string name UK
        string model_identifier
        int dimensions
        timestamp created_at
        timestamp updated_at
        jsonb metadata
    }
    
    VectorSet {
        uuid id PK
        string name UK
        uuid chunker_config_id FK
        uuid embedding_model_config_id FK
        string source_field
        string result_set_name
        int vector_dimensions
        timestamp created_at
        timestamp updated_at
        jsonb metadata
    }
    
    IndexVectorBinding {
        uuid id PK
        uuid vector_set_id FK
        string engine
        string index_name
        string field_name
        timestamp created_at
        timestamp updated_at
    }
```

## Message Types

### OpenSearchDocument

Canonical structure for documents indexed in OpenSearch.

**Key Fields:**
- `original_doc_id` - Source document identifier
- `title`, `body`, `tags` - Core content fields
- `embeddings` - Nested array of `OpenSearchEmbedding` objects
- `custom_fields` - Flexible JSON container for user-defined data

### OpenSearchEmbedding

Represents a single vector embedding with metadata.

**Key Fields:**
- `vector` - Float array of embedding values
- `source_text` - Original text that was embedded
- `chunk_config_id` - Identifier of chunking strategy used
- `embedding_id` - Identifier of embedding model used
- `is_primary` - Flag for primary (title) vs secondary (chunk) embeddings

### ChunkerConfig

Stores text chunking strategy configurations.

**Key Fields:**
- `config_id` - Stable identifier (e.g., "token-body-512-50")
- `config_json` - Full chunker parameters as JSON blob
- `schema_ref` - Optional Apicurio Registry reference for validation

**Example config_json:**
```json
{
  "algorithm": "token",
  "sourceField": "body",
  "chunkSize": 512,
  "chunkOverlap": 50,
  "preserveUrls": true,
  "cleanText": true
}
```

### EmbeddingModelConfig

Stores embedding model configurations.

**Key Fields:**
- `model_identifier` - Model name/path (e.g., "sentence-transformers/all-MiniLM-L6-v2")
- `dimensions` - Vector dimensionality (e.g., 384)
- `metadata` - Additional model info (version, provider, etc.)

### IndexEmbeddingBinding

Links an embedding model to a specific OpenSearch index field.

**Key Fields:**
- `index_name` - Target OpenSearch index
- `embedding_model_config_id` - FK to EmbeddingModelConfig
- `field_name` - Field path (e.g., "embeddings_384.embedding")
- `result_set_name` - Optional result set identifier from pipeline

## Workflow Examples

### Creating a Vector-Enabled Index

```mermaid
sequenceDiagram
    participant Admin
    participant ChunkerService as ChunkerConfigService
    participant EmbedService as EmbeddingConfigService
    participant OSManager as OpenSearchManagerService
    
    Admin->>ChunkerService: CreateChunkerConfig
    Note over ChunkerService: Store chunker params as JSON
    ChunkerService-->>Admin: ChunkerConfig (id, config_id)
    
    Admin->>EmbedService: CreateEmbeddingModelConfig
    Note over EmbedService: Store model info + dimensions
    EmbedService-->>Admin: EmbeddingModelConfig (id, dimensions)
    
    Admin->>OSManager: CreateIndex(index_name, vector_field_definition)
    Note over OSManager: Create index with knn_vector field
    OSManager-->>Admin: CreateIndexResponse (success)
    
    Admin->>EmbedService: CreateIndexEmbeddingBinding
    Note over EmbedService: Link embedding model to index field
    EmbedService-->>Admin: IndexEmbeddingBinding (id)
```

### Document Indexing with Audit Trail

```mermaid
sequenceDiagram
    participant Pipeline
    participant Chunker
    participant Embedder
    participant OSManager as OpenSearchManagerService
    participant OpenSearch
    
    Pipeline->>Chunker: ProcessData(document, ChunkerConfig)
    Note over Chunker: Split text using config_id: token-body-512-50
    Chunker-->>Pipeline: SemanticProcessingResult (chunk_config_id)
    
    Pipeline->>Embedder: Embed(chunks, EmbeddingModelConfig)
    Note over Embedder: Generate vectors with model: all-MiniLM-L6-v2
    Embedder-->>Pipeline: Embeddings (embedding_id)
    
    Pipeline->>OSManager: IndexDocument(OpenSearchDocument)
    Note over OSManager: Document contains:<br/>chunk_config_id + embedding_id<br/>in each OpenSearchEmbedding
    OSManager->>OpenSearch: Bulk index via gRPC
    OpenSearch-->>OSManager: BulkResponse
    OSManager-->>Pipeline: IndexDocumentResponse (success)
    
    Note over Pipeline,OpenSearch: Audit trail preserved:<br/>chunk_config_id → ChunkerConfig<br/>embedding_id → EmbeddingModelConfig
```

## Configuration

### Index Naming Convention

Indices follow the pattern: `{domain}-{type}-{version}`

Examples:
- `repository-pipedocs` - Repository document index
- `filesystem-drives` - Filesystem drive metadata
- `filesystem-nodes` - Filesystem node metadata

### Field Naming Convention

Vector fields use dimension-based naming: `embeddings_{dimension}`

Examples:
- `embeddings_384` - For 384-dimensional vectors (MiniLM)
- `embeddings_768` - For 768-dimensional vectors (BERT-base)
- `embeddings_1536` - For 1536-dimensional vectors (OpenAI ada-002)

### Result Set Naming

Result sets from chunking follow: `{pipeStepName}_chunks_{config_id}`

Examples:
- `chunker-v1_chunks_token-body-512-50`
- `title-chunker_chunks_sentence-title-1000-100`

## Schema Validation

Chunker configurations can be validated against schemas stored in Apicurio Registry:

1. Register ChunkerConfig schema in Apicurio
2. Store artifact reference in `ChunkerConfig.schema_ref`
3. Validate `config_json` against schema before persistence

## Future Extensions

### VectorSet Entity (Planned)

A composite entity that ties together chunker + embedder + metadata:

```protobuf
message VectorSet {
  string id = 1;
  string name = 2;
  string chunker_config_id = 3;  // FK to ChunkerConfig
  string embedding_model_config_id = 4;  // FK to EmbeddingModelConfig
  string source_field = 5;  // e.g., "body", "title"
  string result_set_name = 6;
  int32 vector_dimensions = 7;  // Denormalized from embedding config
  google.protobuf.Timestamp created_at = 8;
  google.protobuf.Timestamp updated_at = 9;
  google.protobuf.Struct metadata = 10;
}
```

This will enable:
- Single entity representing "how to produce vectors"
- Simplified index binding (bind VectorSet → index field)
- Better audit trail and traceability

## References

- [OpenSearch k-NN Plugin](https://opensearch.org/docs/latest/search-plugins/knn/index/)
- [OpenSearch gRPC Transport](https://github.com/opensearch-project/opensearch-protobufs)
- [Apicurio Registry](https://www.apicur.io/registry/)
