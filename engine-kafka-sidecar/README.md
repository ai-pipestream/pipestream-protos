# engine-kafka-sidecar

> Part of the [AI Pipestream](https://github.com/ai-pipestream) platform - Open-source document processing for intelligent search

## Overview

The engine-kafka-sidecar module provides protocol buffer definitions for Kafka sidecar management and dead letter queue (DLQ) handling. This module supports operational control and monitoring of Kafka consumers in the pipeline, enabling pause/resume operations and comprehensive failure tracking for robust document processing workflows.

## Published Location

This module is published to the Buf Schema Registry:

**Repository**: `buf.build/pipestreamai/engine-kafka-sidecar`
**Latest Version**: [03816d02e29a48275182520c942a9dcdcb2374b4](https://buf.build/pipestreamai/engine-kafka-sidecar)

## Contents

- `ai/pipestream/engine/sidecar/v1/dlq_message.proto` - Dead letter queue message definitions for failed processing
- `ai/pipestream/engine/sidecar/v1/management_service.proto` - Kafka sidecar management service interface

## Dependencies

This module depends on:
- `buf.build/grpc/grpc` - gRPC core types
- `buf.build/googleapis/googleapis` - Google common types
- `buf.build/pipestreamai/common` - Platform core data types

## Usage

### With Buf CLI

```
# Add to your buf.yaml
deps:
  - buf.build/pipestreamai/engine-kafka-sidecar
```

### Code Generation

```
# Generate code for your language
buf generate buf.build/pipestreamai/engine-kafka-sidecar
```

### With Gradle (Java/Kotlin)

```
dependencies {
    implementation("build.buf.gen:pipestreamai_engine-kafka-sidecar_grpc_java:+")
    implementation("build.buf.gen:pipestreamai_engine-kafka-sidecar_protobuf_java:+")
}
```

## Key Messages/Services

### SidecarManagementService
- **GetLeases**: Retrieve active topic consumption leases
- **PauseConsumption**: Temporarily halt consumption for incident response
- **ResumeConsumption**: Restart consumption for paused topics

### DlqMessage
- **Failed processing tracking**: Captures error details, retry counts, and original message metadata
- **Operational visibility**: Enables monitoring and debugging of processing failures

## Related Modules

- `common` - Core data types including PipeStream referenced in DLQ messages
- `engine` - Main orchestration engine that may use sidecar management

## Documentation

- [Buf Schema Registry](https://buf.build/pipestreamai/engine-kafka-sidecar)
- [Platform Design Document](../../DESIGN_DOCUMENT.md)
- [AI Pipestream Documentation](https://github.com/ai-pipestream)

## License

MIT License - See [LICENSE](./LICENSE) file for details.