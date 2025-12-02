# OpenSearch

> Part of the [AI Pipestream](https://github.com/ai-pipestream) platform - Open-source document processing for intelligent search

## Overview

The **opensearch** module provides OpenSearch indexing, collection management, and semantic search capabilities. It defines the document structure for OpenSearch indices, the manager service for schema and index lifecycle operations, and a high-throughput ingestion service for streaming document indexing.

This is the sink layer of the platform—where processed documents with embeddings are indexed for semantic and keyword search.

## Published Location

**Repository**: [`buf.build/pipestreamai/opensearch`](https://buf.build/pipestreamai/opensearch)

## Contents

| Proto File | Purpose |
|------------|---------|
| `ai/pipestream/opensearch/v1/opensearch_document.proto` | Canonical OpenSearch document structure |
| `ai/pipestream/opensearch/v1/opensearch_manager.proto` | Index management, schema, and document operations |
| `ai/pipestream/ingestion/v1/opensearch_ingestion.proto` | High-throughput streaming ingestion |

## Architecture

```mermaid
graph TD
    subgraph "Document Model"
        OSD[OpenSearchDocument]
        OSD --> CORE[Core Fields<br/>doc_id, title, body]
        OSD --> EMB[Embeddings<br/>Nested vectors]
        OSD --> CUSTOM[custom_fields<br/>Flexible JSON]
    end

    subgraph "Embedding Structure"
        EMB --> VEC[vector]
        EMB --> SRC[source_text]
        EMB --> CTX[context_text]
        EMB --> PRIM[is_primary<br/>title vs chunks]
    end

    subgraph "Manager Service"
        MGR[OpenSearchManagerService]
        MGR --> CREATE[CreateIndex]
        MGR --> DELETE[DeleteIndex]
        MGR --> SCHEMA[EnsureNestedEmbeddingsFieldExists]
        MGR --> INDEX[IndexDocument / IndexAnyDocument]
        MGR --> SEARCH[SearchFilesystemMeta]
    end

    subgraph "Ingestion Service"
        ING[OpenSearchIngestionService]
        ING --> STREAM[StreamDocuments<br/>Bidirectional]
        STREAM --> REQ[StreamDocumentsRequest]
        STREAM --> RESP[StreamDocumentsResponse<br/>Real-time ACKs]
    end
```

## Dependencies

- `buf.build/grpc/grpc` - gRPC core types
- `buf.build/googleapis/googleapis` - Google common types
- `buf.build/pipestreamai/common` - Core `PipeDoc` types

## Usage

### With Buf CLI

```yaml
# Add to your buf.yaml
deps:
  - buf.build/pipestreamai/opensearch
```

### Code Generation

```bash
buf generate buf.build/pipestreamai/opensearch
```

### With Gradle (Java/Kotlin)

```kotlin
dependencies {
    implementation("build.buf.gen:pipestreamai_opensearch_grpc_java:+")
    implementation("build.buf.gen:pipestreamai_opensearch_protobuf_java:+")
}
```

## Key Messages

| Message/Service | Description |
|-----------------|-------------|
| `OpenSearchManagerService` | Schema management, index lifecycle, document CRUD |
| `OpenSearchIngestionService` | Bidirectional streaming for high-throughput indexing |
| `OpenSearchDocument` | Canonical document with embeddings and custom fields |
| `Embedding` | Vector with source text, context, and metadata |
| `VectorFieldDefinition` | k-NN configuration (dimension, engine, space type) |
| `KnnMethodDefinition` | HNSW parameters (m, ef_construction, ef_search) |
| `SearchFilesystemMetaRequest/Response` | Filesystem metadata search |

## Embedding Model

```mermaid
graph TD
    subgraph "Document"
        DOC[OpenSearchDocument]
        DOC --> EMBS[embeddings: repeated Embedding]
    end

    subgraph "Embedding Fields"
        E[Embedding]
        E --> V[vector: float array]
        E --> ST[source_text: original text]
        E --> CT[context_text: derived text]
        E --> CCID[chunk_config_id]
        E --> EID[embedding_id]
        E --> IP[is_primary: title vs body chunk]
    end

    subgraph "k-NN Config"
        KNN[KnnMethodDefinition]
        KNN --> DIM[dimension: 768, 1536, etc.]
        KNN --> SPACE[space_type: cosine, innerproduct]
        KNN --> HNSW[HNSW params: m, ef_construction]
    end
```

## Streaming Ingestion

```mermaid
sequenceDiagram
    participant Client
    participant Ingestion
    participant OpenSearch

    Client->>Ingestion: StreamDocuments (bidirectional)

    loop Document Batch
        Client->>Ingestion: StreamDocumentsRequest (doc + request_id)
        Ingestion->>OpenSearch: Bulk index
        Ingestion-->>Client: StreamDocumentsResponse (ACK)
    end
```

## Related Modules

- [`common`](../common/) - Core `PipeDoc` with semantic chunks
- [`admin`](../admin/) - Schema manager integration
- [`engine`](../engine/) - Routes documents to OpenSearch sink

## Related Repositories

- [`pipestream-opensearch`](https://github.com/ai-pipestream/pipestream-opensearch) - OpenSearch service implementation

## Documentation

- [Buf Schema Registry](https://buf.build/pipestreamai/opensearch)
- [AI Pipestream Documentation](https://github.com/ai-pipestream)

## License

MIT License - See [LICENSE](./LICENSE) file for details.
