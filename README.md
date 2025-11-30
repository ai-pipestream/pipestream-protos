# pipestream-protos

Proto definitions for the gRPC services that make up the AI Pipestream platform.

## Overview

This repository contains the source-of-truth Protocol Buffer (`.proto`) files for all gRPC services in the AI Pipestream platform. The proto files are packaged as a JAR artifact that can be consumed by other projects for code generation.

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

```
src/main/proto/
├── buf.yaml           # buf linting configuration
├── buf.lock           # buf dependencies lock file
├── tika_parser.proto
├── validation_service.proto
├── core/              # Core pipeline types and services
├── engine/            # Pipeline engine services
├── events/            # Event definitions
├── mapping-service/   # Mapping service protos
├── module/            # Module service protos
│   ├── connectors/    # Connector intake services
│   └── parser/        # Parser metadata protos (tika)
├── opensearch-manager/ # OpenSearch management services
├── registration/      # Platform registration services
└── repository/        # Repository services
    ├── account/       # Account management
    ├── crawler/       # Filesystem crawler
    ├── filesystem/    # Filesystem services
    ├── graph/         # Graph repository services
    └── pipedoc/       # Pipedoc services
```

## Building

### Prerequisites

- Java 21 or later
- Gradle 9.x (wrapper included)

### Build Commands

```bash
# Build the project
./gradlew build

# Publish to Maven Local
./gradlew publishToMavenLocal

# Check current version
./gradlew currentVersion
```

### Proto Linting

This project uses [buf](https://buf.build/) for proto linting. The linting configuration is defined in `src/main/proto/buf.yaml`.

To lint locally, install buf and run:
```bash
buf lint src/main/proto
```

## CI/CD Workflows

### Snapshots (main branch)

Snapshots are automatically published to Maven Central Snapshots repository on:
- Every push to the `main` branch
- Nightly at 3 AM UTC
- Manual workflow dispatch

Proto linting is performed before building and publishing snapshots.

### Releases (version tags)

Releases are published to Maven Central when:
- A version tag (e.g., `v1.0.0`) is pushed
- Triggered via workflow dispatch with version bump selection

Proto linting is performed before building and publishing releases.

## Versioning

This project uses [Axion Release Plugin](https://github.com/allegro/axion-release-plugin) for semantic versioning based on git tags.

- Version tags follow the format `v{major}.{minor}.{patch}` (e.g., `v0.1.0`)
- The plugin automatically determines the version from the latest git tag
- SNAPSHOT versions are automatically appended when not on a tag

## License

MIT License - see [LICENSE](LICENSE) for details.
