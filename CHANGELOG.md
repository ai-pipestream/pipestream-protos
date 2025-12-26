# Changelog

All notable changes to the pipestream-protos project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### CEL (Common Expression Language) Integration
- **GraphEdge.condition**: Enhanced documentation to specify CEL expression usage with `org.projectnessie.cel:cel-tools` for Java/Quarkus implementation. Available context variables: `document`, `metadata`, `context_params`.
- **NodeProcessingConfig.filter_condition** (field 6): New CEL expression field for document filtering before node processing. When evaluates to false, documents skip the node.
- **TransformConfig.cel_expression** (field 3): New CEL expression field for flexible field transformations. Available context: `value`, `document`, `metadata`.

#### GraphEdge Transport Configuration
- **GraphEdge.transport_type** (field 8): Transport mechanism override for the edge (MESSAGING or GRPC).
- **GraphEdge.kafka_topic** (field 9): Custom Kafka topic override for routing.
- **GraphEdge.max_hops** (field 10): Loop prevention with maximum hop count.

#### Dead Letter Queue (DLQ) Support
- **DlqConfig**: New message type for configuring DLQ behavior with:
  - `enabled`: Toggle DLQ handling
  - `topic_override`: Custom DLQ topic name
  - `max_retries`: Retry count before DLQ routing
  - `initial_backoff`, `max_backoff`, `backoff_multiplier`: Exponential backoff settings
  - `include_payload`: Option to preserve full message for debugging
- **GraphNode.dlq_config** (field 16): DLQ configuration attachment to graph nodes.

#### StreamMetadata Datasource Tracking
- **StreamMetadata.datasource_id** (field 9): DataSource identifier for document origin tracking.
- **StreamMetadata.account_id** (field 10): Account identifier for ownership and access control.
- **StreamMetadata.entry_node_id** (field 11): Entry node identifier for tracking pipeline entry points.

#### Engine Service Enhancements
- **EngineV1Service.IntakeHandoff**: New RPC for intake-to-engine stream handoff with datasource routing.
- **IntakeHandoffRequest**: Request message with stream, datasource_id, account_id, target override, and priority.
- **IntakeHandoffResponse**: Response with acceptance status, assigned stream ID, entry node, and queue depth.

#### Pipeline Graph Versioning
- **PipelineGraph.version** (field 10): Version number for optimistic locking to detect concurrent modifications.

### Deprecated

- **TransformConfig.rule_name** (field 1): Use `cel_expression` for new transformations.
- **TransformConfig.params** (field 2): Use `cel_expression` for new transformations.

### Migration Notes

#### TransformConfig Migration
Existing implementations using `rule_name` and `params` will continue to work but should migrate to `cel_expression`:

| Legacy rule_name | CEL Expression Equivalent |
|------------------|---------------------------|
| `uppercase` | `value.upperAscii()` |
| `lowercase` | `value.lowerAscii()` |
| `trim` | `value.trim()` |
| `substring` | `value.substring(start, end)` |

#### Field Number Safety
All new fields use previously unassigned field numbers:
- GraphEdge: 8, 9, 10
- GraphNode: 16
- NodeProcessingConfig: 6
- PipelineGraph: 10
- StreamMetadata: 9, 10, 11
- TransformConfig: 3

No breaking changes to wire format compatibility.
