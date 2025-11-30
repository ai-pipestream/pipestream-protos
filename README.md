# pipestream-protos

Canonical Protocol Buffer definitions for the AI Pipestream platform.

[![Buf CI](https://github.com/ai-pipestream/pipestream-protos/actions/workflows/buf-ci.yml/badge.svg)](https://github.com/ai-pipestream/pipestream-protos/actions/workflows/buf-ci.yml)

## Overview

This repository is the **single source of truth** for all Protocol Buffer (`.proto`) files in the AI Pipestream platform. It follows a **schema-first architecture** where:

- Proto definitions are the canonical API contracts
- All services generate stubs from these definitions
- Breaking changes are automatically detected via CI/CD
- Schemas are published to [Buf Schema Registry](https://buf.build) for versioning and distribution
- Comprehensive documentation is embedded directly in the proto files

The proto files are packaged as a JAR artifact for Maven/Gradle consumption and published to BSR for cross-language usage.

## Maven Coordinates

### Releases
```xml
<dependency>
    <groupId>ai.pipestream</groupId>
    <artifactId>pipestream-protos</artifactId>
    <version>${version}</version>
</dependency>
```

### Snapshots
```xml
<repository>
    <id>maven-central-snapshots</id>
    <url>https://central.sonatype.com/repository/maven-snapshots/</url>
    <snapshots>
        <enabled>true</enabled>
    </snapshots>
</repository>

<dependency>
    <groupId>ai.pipestream</groupId>
    <artifactId>pipestream-protos</artifactId>
    <version>${version}-SNAPSHOT</version>
</dependency>
```

### Gradle
```groovy
dependencies {
    implementation 'ai.pipestream:pipestream-protos:${version}'
}
```

## Proto File Structure

All proto files are located in the `proto/` directory and follow a hierarchical package structure:

```
proto/
├── buf.yaml                          # Buf configuration (linting, formatting, breaking)
├── buf.lock                          # Buf dependencies lock file
└── ai/pipestream/
    ├── config/v1/                    # Pipeline configuration models
    ├── connector/intake/v1/          # Document upload and intake services
    ├── data/
    │   ├── module/v1/                # Module processing service contracts
    │   └── v1/                       # Core pipeline data types (PipeDoc, PipeStream)
    ├── design/v1/                    # Design mode service (frontend simulation)
    ├── engine/v1/                    # Pipeline engine orchestration
    ├── events/v1/                    # Event definitions (Kafka)
    ├── linear/
    │   ├── config/v1/                # Linear pipeline configuration
    │   └── processor/v1/             # Linear pipeline execution
    ├── mapping/v1/                   # Field mapping service
    ├── opensearch/v1/                # OpenSearch management and indexing
    ├── registration/v1/              # Platform service registration
    ├── repository/
    │   ├── account/v1/               # Account management
    │   ├── crawler/v1/               # Filesystem crawler
    │   ├── filesystem/v1/            # Filesystem repository
    │   ├── graph/v1/                 # Graph repository
    │   ├── pipedoc/v1/               # PipeDoc storage service
    │   └── v1/                       # Core repository services
    ├── schemamanager/v1/             # OpenSearch schema management
    ├── testing/harness/v1/           # Integration testing harness
    └── validation/v1/                # Validation service
```

### Documentation Standards

All proto files include **comprehensive documentation**:
- Service-level comments explaining purpose and integration patterns
- RPC-level comments describing operations and behavior
- Message-level comments explaining data structures
- Field-level comments with types, constraints, and usage notes
- Enum value comments describing each option

This documentation is automatically included in generated code for all languages.

## Development

### Prerequisites

- **Java 21 or later** - For building the JAR artifact
- **Gradle 9.x** - Wrapper included (`./gradlew`)
- **[Buf CLI](https://buf.build/docs/installation)** - For proto validation and formatting

### Installing Buf

```bash
# macOS
brew install bufbuild/buf/buf

# Linux
curl -sSL "https://github.com/bufbuild/buf/releases/latest/download/buf-$(uname -s)-$(uname -m)" -o /usr/local/bin/buf
chmod +x /usr/local/bin/buf

# Or use the Buf installer
curl -sSL https://github.com/bufbuild/buf/releases/latest/download/buf-$(uname -s)-$(uname -m).tar.gz | tar -xvzf - -C /usr/local/bin
```

### Local Development Workflow

```bash
# 1. Lint proto files (check for violations)
cd proto
buf lint

# 2. Format proto files (auto-fix formatting)
buf format -w

# 3. Check for breaking changes (against main branch)
buf breaking --against '.git#branch=main,subdir=proto'

# 4. Build the JAR artifact
./gradlew build

# 5. Publish to Maven Local for testing
./gradlew publishToMavenLocal

# 6. Check current version
./gradlew currentVersion
```

### Buf Configuration

All buf settings are in `proto/buf.yaml`:
- **Linting rules**: Google-style API design, field naming, RPC patterns
- **Breaking change detection**: Ensures API compatibility
- **Formatting**: Consistent style across all proto files
- **Dependencies**: Managed via `buf.lock`

## CI/CD Workflows

### Buf CI (`.github/workflows/buf-ci.yml`)

Automated proto validation runs on **every push and pull request**:

| Check | Description | When |
|-------|-------------|------|
| **Lint** | Validates proto files against buf rules | All PRs and pushes |
| **Format** | Ensures consistent formatting | All PRs and pushes |
| **Breaking** | Detects API breaking changes | PRs to main, commits on main |
| **BSR Publish** | Publishes to Buf Schema Registry | Pushes to main only |
| **PR Comments** | Posts detailed feedback on PRs | All pull requests |

**Features:**
- ✅ Prevents merging PRs with lint violations
- ✅ Auto-detects breaking changes before they reach production
- ✅ Enforces consistent formatting across all proto files
- ✅ Publishes validated schemas to BSR for versioning
- ✅ Full git history for accurate breaking change detection

### Maven Publishing

#### Snapshots (main branch)

Snapshots are automatically published to Maven Central Snapshots on:
- Every push to `main` branch
- Nightly at 3 AM UTC
- Manual workflow dispatch

#### Releases (version tags)

Releases are published to Maven Central when:
- A version tag (e.g., `v1.0.0`) is pushed
- Triggered via workflow dispatch with version bump

All Maven publishing workflows include proto validation via buf before building.

### Buf Schema Registry (BSR)

Validated schemas are automatically published to BSR on every merge to main. This enables:
- Cross-language stub generation
- Schema versioning and history
- Dependency management
- Public API documentation

**Setup**: Add `BUF_TOKEN` secret to GitHub repository settings (generate at [buf.build/settings/user](https://buf.build/settings/user))

## Contributing

### Making Changes

1. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your proto changes**
   - Add comprehensive documentation to all new messages/fields/RPCs
   - Follow existing naming conventions and package structure
   - Use semantic field numbering (don't reuse removed field numbers)

3. **Format and validate locally**
   ```bash
   cd proto
   buf format -w          # Auto-format
   buf lint              # Check for violations
   buf breaking --against '.git#branch=main,subdir=proto'  # Check breaking changes
   ```

4. **Commit and push**
   ```bash
   git add proto/
   git commit -m "feat: add new XYZ service"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**
   - CI will automatically run buf validation
   - Breaking changes will be flagged (consider semantic versioning)
   - Address any lint violations or format issues

### Best Practices

#### Documentation
- **Every** service, message, field, and enum MUST have a comment
- Use `//` for comments (buf will include them in generated code)
- Explain the "why" not just the "what"
- Include examples for complex fields

#### Versioning
- Use package versioning: `ai.pipestream.service.v1`, `v2`, etc.
- Never remove or rename fields without a major version bump
- Mark deprecated fields with `[deprecated = true]` and add a comment

#### Breaking Changes
Breaking changes include:
- Removing or renaming fields, messages, services, or RPCs
- Changing field types or numbers
- Removing enum values
- Changing field rules (optional ↔ required ↔ repeated)

**If you must introduce a breaking change:**
1. Discuss in a GitHub issue first
2. Plan a coordinated migration across services
3. Bump the package version (v1 → v2)

#### Field Numbering
- Fields 1-15: Single-byte encoding (use for frequently set fields)
- Fields 16-2047: Two-byte encoding
- Fields 19000-19999: Reserved by protobuf
- Never reuse deleted field numbers

## Versioning

This project uses [Axion Release Plugin](https://github.com/allegro/axion-release-plugin) for semantic versioning based on git tags.

- Version tags follow the format `v{major}.{minor}.{patch}` (e.g., `v0.1.0`)
- The plugin automatically determines the version from the latest git tag
- SNAPSHOT versions are automatically appended when not on a tag

## License

MIT License - see [LICENSE](LICENSE) for details.
