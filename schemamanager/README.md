# Schema Manager

> Part of the [AI Pipestream](https://github.com/ai-pipestream) platform - Open-source document processing for intelligent search

## Overview

The **schema-manager** module provides the `SchemaManagerService` API for dynamically managing OpenSearch index schemas. It enables services to ensure that necessary mappings exist for vector embeddings and nested field configurations, with idempotent operations and distributed locking to prevent race conditions.

## Published Location

**Repository**: [`buf.build/pipestreamai/schema-manager`](https://buf.build/pipestreamai/schema-manager)

## Contents

| Proto File | Purpose |
|------------|---------|
| `ai/pipestream/schemamanager/v1/schema_manager.proto` | Schema management service and vector field definitions |

## Dependencies

- `buf.build/grpc/grpc` - gRPC core types
- `buf.build/googleapis/googleapis` - Google common types (wrappers)
- `buf.build/pipestreamai/common` - Core Pipestream types

## Usage

### With Buf CLI

```yaml
# Add to your buf.yaml
deps:
  - buf.build/pipestreamai/schema-manager
```

### Code Generation

```bash
buf generate buf.build/pipestreamai/schema-manager
```

## Key Messages

| Message | Description |
|---------|-------------|
| `SchemaManagerService` | Service for ensuring nested embeddings field exists in OpenSearch indices |
| `VectorFieldDefinition` | Configuration for knn_vector fields (dimensions, k-NN method) |
| `KnnMethodDefinition` | k-NN engine and space type configuration |
| `EnsureNestedEmbeddingsFieldExistsRequest/Response` | Idempotent schema management operations |

## Related Modules

- [`opensearch`](../opensearch/) - OpenSearch document and index management (depends on schema-manager)

## License

MIT License - See [LICENSE](./LICENSE) file for details.

