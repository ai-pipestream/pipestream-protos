# Guidelines for Module READMEs

Generate a README.md for each buf module following this structure:

## Template Structure

```markdown
# {Module Name}

> Part of the [AI Pipestream](https://github.com/ai-pipestream) platform - Open-source document processing for intelligent search

## Overview

{2-3 sentence description of what this module contains and its purpose in the platform}

## Published Location

This module is published to the Buf Schema Registry:

**Repository**: `buf.build/pipestreamai/{module-name}`
**Latest Version**: [{commit-hash}](https://buf.build/pipestreamai/{module-name})

## Contents

{List the main proto files and their purposes}

Example:
- `ai/pipestream/data/v1/pipeline_core_types.proto` - Core PipeDoc message and data types
- `ai/pipestream/events/v1/*.proto` - Platform event definitions

## Dependencies

This module depends on:
- `buf.build/grpc/grpc` - gRPC core types
- `buf.build/googleapis/googleapis` - Google common types
{List pipestream dependencies if any}

## Usage

### With Buf CLI

```bash
# Add to your buf.yaml
deps:
  - buf.build/pipestreamai/{module-name}
```

### Code Generation

```bash
# Generate code for your language
buf generate buf.build/pipestreamai/{module-name}
```

### With Gradle (Java/Kotlin)

```kotlin
dependencies {
    implementation("build.buf.gen:pipestreamai_{module-name}_grpc_java:+")
    implementation("build.buf.gen:pipestreamai_{module-name}_protobuf_java:+")
}
```

## Key Messages/Services

{List 3-5 most important messages or services with brief descriptions}

## Related Modules

{List related pipestream modules that consumers might also need}

## Documentation

- [Buf Schema Registry](https://buf.build/pipestreamai/{module-name})
- [Platform Design Document](../../DESIGN_DOCUMENT.md)
- [AI Pipestream Documentation](https://github.com/ai-pipestream)

## License

MIT License - See [LICENSE](./LICENSE) file for details.
```

## Module-Specific Descriptions

### common
- **Purpose**: Foundation types for the entire platform - PipeDoc, events, parsed data
- **Key**: Emphasize immutability of parsed_metadata vs mutability of search_metadata
- **Related**: pipeline-module, admin, repo (all depend on common)

### pipeline-module
- **Purpose**: Module service definitions for pipeline processing components
- **Key**: Defines the interface that all processing modules implement
- **Related**: Used by linear-processor, testing-harness, registration

### admin
- **Purpose**: Administrative services for repository management, validation, schema management
- **Key**: Account management, field mapping, schema validation
- **Related**: Works with repo module

### repo
- **Purpose**: Document repository services - storage, retrieval, filesystem, crawler integration
- **Key**: S3 storage backend, PipeDoc persistence
- **Related**: Depends on common, config, pipeline-module

### config
- **Purpose**: Platform configuration service - clusters, pipeline graphs, module registry
- **Key**: Replaces Consul-based configuration with gRPC streaming
- **Related**: Used by repo, design

### registration
- **Purpose**: Platform service discovery and registration
- **Key**: Module registration, health checks, service mesh coordination
- **Related**: All services register here

### intake
- **Purpose**: High-speed document ingestion entry point
- **Key**: First service in the pipeline, handles bulk document intake
- **Related**: Sends to repo or directly to engine

### engine
- **Purpose**: Pipeline orchestration and routing engine
- **Key**: Routes documents through processing modules, flow control
- **Related**: Core of the platform, coordinates all processing

### opensearch
- **Purpose**: OpenSearch indexing and collection management
- **Key**: Sink service for semantic search, collection lifecycle management
- **Related**: Final destination for processed documents

### design
- **Purpose**: Pipeline design and configuration UI backend
- **Key**: Design-time pipeline configuration, visual graph editing
- **Related**: Works with config module

### parser
- **Purpose**: Document parsing service definitions (Tika-based)
- **Key**: Text extraction, metadata parsing, multi-format support
- **Related**: Processing module, outputs to parsed_metadata in PipeDoc

### linear-processor
- **Purpose**: Linear pipeline processor (legacy)
- **Key**: Sequential document processing, may be deprecated
- **Related**: Older processing model

### testing-harness
- **Purpose**: Testing infrastructure for pipeline validation
- **Key**: Integration testing, pipeline validation, module testing
- **Related**: Used across all services for testing

### ui-ux
- **Purpose**: Frontend shell service for UI state management
- **Key**: Health monitoring, UI-backend communication
- **Related**: Platform frontend integration

## License Template

Each module should have a LICENSE file:

```
MIT License

Copyright (c) 2024-2025 AI Pipestream Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Instructions for LLM

For each module directory:

1. Read the proto files to understand the actual contents
2. Check buf.yaml for dependencies
3. Generate README.md following the template
4. Customize the Overview, Contents, and Key Messages sections based on actual proto files
5. Add LICENSE file with MIT license text
6. Ensure all links and module names are correct
7. Use the module-specific descriptions above for context
