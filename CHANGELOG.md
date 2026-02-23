# Changelog

All notable changes to the pipestream-protos project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### CEL (Common Expression Language) Integration
- **GraphEdge.condition**: Enhanced documentation to specify CEL expression usage with `org.projectnessie.cel:cel-tools` for Java/Quarkus implementation. Available context variables: `document`, `metadata`, `context_params`.
- **NodeProcessingConfig.filter_condition** (field 6): New CEL expression field for document filtering before node processing. When evaluates to false, documents skip the node.
- **ProcessingMapping.MAPPING_TYPE_CEL**: New mapping type using `CelConfig` for flexible field transformations with full CEL expression support. Available context variables: `document`, `stream`, `value`.

#### Execution Record Terminology Alignment
- **StepExecutionRecord.node_id** (field 2): Renamed from `step_name` to align with graph-based node architecture
- **StepExecutionRecord.attempted_target_node_id** (field 9): Renamed from `attempted_target_step_name`
- **ErrorData.originating_node_id** (field 4): Renamed from `originating_step_name`
- **ErrorData.attempted_target_node_id** (field 5): Renamed from `attempted_target_step_name`

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

#### RTBF Ingestion Configuration
- **RightToBeForgottenConfig** (new): New datasource/stream policy type with:
  - `delete_search_index`: remove indexed content when enabled
  - `delete_source_blobs`: remove source/blob content when enabled
- **ConnectorGlobalConfig.right_to_be_forgotten**: Added to datasource-level config to provide default RTBF behavior.
- **IngestionConfig.right_to_be_forgotten**: Added stream metadata field carrying resolved RTBF policy through intake-to-engine handoff.
- **DatasourceInstance.NodeConfig.right_to_be_forgotten**: Added as stream-level override in engine graph config.

### Removed

#### Transport Configuration Cleanup
**BREAKING CHANGE**: Removed unused transport configuration fields from `GraphNode`:
- **`GraphNode.transport`** (field 7): Transport configuration moved to edges
- **`GraphNode.kafka_output_topic`** (field 11): Output routing moved to edges
- **`TransportConfig`**: Unused transport configuration message
- **`GrpcConfig`**: Unused gRPC configuration message
- **`MessagingConfig`**: Unused messaging configuration message

**Migration**: Transport is now configured per-edge using `GraphEdge.transport_type` and `GraphEdge.kafka_topic`.

### Migration Notes

#### CEL Expression Mapping
For advanced field transformations requiring full CEL expression power, use `MAPPING_TYPE_CEL` with `CelConfig`:

```protobuf
ProcessingMapping {
  mapping_type: MAPPING_TYPE_CEL
  cel_config: {
    expression: "value.upperAscii()"
  }
}
```

Traditional transforms continue to use `MAPPING_TYPE_TRANSFORM` with `TransformConfig.rule_name`:
- `uppercase`, `lowercase`, `trim`
- `proto_rules` for advanced ProtoFieldMapper syntax

#### Field Number Safety
**BREAKING CHANGE**: Removed fields from `GraphNode` causing field renumbering:
- GraphNode fields after transport (field 7) shifted down by 1
- GraphNode fields after kafka_output_topic (field 11) shifted down by 2

Wire format is incompatible due to field removal and renumbering.