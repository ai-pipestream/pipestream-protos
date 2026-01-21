# s3-connector

> Part of the [AI Pipestream](https://github.com/ai-pipestream) platform - Open-source document processing for intelligent search

## Overview

The s3-connector module provides protocol buffer definitions for Amazon S3 data source integration. This module enables crawling S3 buckets, managing S3 connections, and emitting crawl events for document processing pipelines. It supports both public and private S3 buckets with flexible authentication options including AWS credentials and KMS integration.

## Published Location

This module is published to the Buf Schema Registry:

**Repository**: `buf.build/pipestreamai/s3-connector`
**Latest Version**: [a3cfc36918bdcb9ed56daaf8df600c7e27203c67](https://buf.build/pipestreamai/s3-connector)

## Contents

- `ai/pipestream/connector/s3/v1/s3_connector_control.proto` - Control service for triggering crawls and testing connections
- `ai/pipestream/connector/s3/v1/s3_crawl_events.proto` - Event definitions for S3 object discovery and processing

## Dependencies

This module depends on:
- `buf.build/grpc/grpc` - gRPC core types
- `buf.build/googleapis/googleapis` - Google common types

## Usage

### With Buf CLI

```
# Add to your buf.yaml
deps:
  - buf.build/pipestreamai/s3-connector
```

### Code Generation

```
# Generate code for your language
buf generate buf.build/pipestreamai/s3-connector
```

### With Gradle (Java/Kotlin)

```
dependencies {
    implementation("build.buf.gen:pipestreamai_s3-connector_grpc_java:+")
    implementation("build.buf.gen:pipestreamai_s3-connector_protobuf_java:+")
}
```

## Key Messages/Services

### S3ConnectorControlService
- **StartCrawl**: Trigger S3 bucket crawling with configurable parameters
- **TestBucketCrawl**: Validate S3 connectivity and optionally count/preview objects

### S3CrawlEvent
- **S3 object metadata**: Captures bucket, key, size, ETag, and modification timestamps
- **Deterministic event IDs**: Hash-based identification for reliable processing
- **Versioning support**: Handles S3 object versions for comprehensive data capture

### S3ConnectionConfig
- **Flexible authentication**: Support for anonymous access, static credentials, and KMS references
- **Regional configuration**: Customizable S3 endpoints and path-style access
- **Security integration**: KMS-backed credential management for enhanced security

## Related Modules

- `intake` - May consume S3 crawl events for document ingestion
- `repo` - Repository service that can store S3-crawled documents

## Documentation

- [Buf Schema Registry](https://buf.build/pipestreamai/s3-connector)
- [Platform Design Document](../../DESIGN_DOCUMENT.md)
- [AI Pipestream Documentation](https://github.com/ai-pipestream)

## License

MIT License - See [LICENSE](./LICENSE) file for details.