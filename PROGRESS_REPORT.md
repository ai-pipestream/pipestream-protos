# Proto Lint Cleanup Progress Report

## ✅ PHASE 1 COMPLETE: Directory Reorganization

### Accomplished:
1. **Reorganized all 48 proto files** into proper package-matching directory structure
   - Old: `core/pipeline_core_types.proto`
   - New: `ai/pipestream/data/v1/pipeline_core_types.proto`

2. **Added v1 versioning** to all packages without versions
   - `ai.pipestream.events` → `ai.pipestream.events.v1`
   - `ai.pipestream.mapping` → `ai.pipestream.mapping.v1`
   - etc.

3. **Fixed all import paths** to reference new locations
   - Updated 31 files with import fixes
   - Fixed tika metadata cross-references
   - Fixed core type references

4. **Cleaned up empty directories** after reorganization

### Errors Fixed: **94 errors** (346 → 252)

---

## 📋 PHASE 2: Naming Convention Fixes (252 errors remaining)

### Error Categories:

| Category | Count | Example |
|----------|-------|---------|
| **RPC Naming** | ~97 | `HealthRequest` → `GetHealthRequest` |
| **Enum Prefixes** | ~66 | `DELETE` → `INTENT_DELETE` |
| **Enum _UNSPECIFIED** | ~66 | `DELETE` (zero value) → `INTENT_DELETE_UNSPECIFIED` |
| **Shared Types** | ~64 | Same request/response used by multiple RPCs |
| **Service Suffix** | ~5 | `PipeStepProcessor` → `PipeStepProcessorService` |
| **Field Naming** | ~3 | `blobBag` → `blob_bag` |
| **Unused Imports** | ~3 | Remove unused import statements |

---

## 🎯 Next Steps

### Quick Wins (10 minutes):
1. **Fix field naming** (3 errors)
   - `blob Bag` → `blob_bag`
   - `blobData` → `blob_data`
   - `serviceRegistrationMetadata` → `service_registration_metadata`

2. **Add Service suffix** (5 errors)
   - `PipeStepProcessor` → `PipeStepProcessorService`
   - `TestHarness` → `TestHarnessService`
   - `LinearPipelineProcessor` → `LinearPipelineProcessorService`
   - `OpenSearchIngestion` → `OpenSearchIngestionService`
   - `PlatformRegistration` → `PlatformRegistrationService`

3. **Remove unused imports** (3 errors)
   - `google/protobuf/any.proto` in upload_service.proto
   - `google/protobuf/timestamp.proto` in repository_service.proto
   - `google/protobuf/struct.proto` in repository_service.proto

### Medium Effort (2-3 hours):
4. **Fix enum naming** (66 enums)
   - Add proper prefixes (e.g., `INTENT_`, `AGGREGATION_TYPE_`)
   - Add `_UNSPECIFIED` suffix to zero values
   - Can be largely automated with a script

### Larger Effort (4-6 hours):
5. **Fix RPC request/response naming** (97 errors)
   - Rename request/response types to match RPC names
   - Update all usages across files
   - Can be partially automated

### Configuration:
6. **Update buf.yaml** to disable rules we won't enforce:
   - `RPC_REQUEST_RESPONSE_UNIQUE` (shared types are sometimes intentional)

---

## 📊 Current Project Structure

```
src/main/proto/
└── ai/
    └── pipestream/
        ├── config/v1/           # Pipeline configuration
        ├── connector/intake/v1/  # Document intake
        ├── data/
        │   ├── module/v1/       # Module interfaces
        │   └── v1/              # Core data types
        ├── design/v1/           # Design mode
        ├── engine/
        │   ├── linear/v1/       # Linear pipeline
        │   └── v1/              # Engine service
        ├── events/v1/           # Event definitions
        ├── ingestion/v1/        # OpenSearch ingestion
        ├── linear/processor/v1/ # Linear processors
        ├── mapping/v1/          # Field mapping
        ├── opensearch/v1/       # OpenSearch management
        ├── parsed/data/         # Tika metadata (17 packages)
        │   ├── climate/v1/
        │   ├── creative_commons/v1/
        │   ├── database/v1/
        │   ├── dublin/v1/
        │   ├── email/v1/
        │   ├── epub/v1/
        │   ├── generic/v1/
        │   ├── html/v1/
        │   ├── image/v1/
        │   ├── media/v1/
        │   ├── office/v1/
        │   ├── pdf/v1/
        │   ├── rtf/v1/
        │   ├── tika/
        │   │   ├── base/v1/
        │   │   ├── font/v1/
        │   │   └── v1/
        │   └── warc/v1/
        ├── platform/registration/v1/ # Service registration
        ├── processing/tika/v1/       # Tika processing
        ├── repository/              # Repository services
        │   ├── account/v1/
        │   ├── crawler/v1/
        │   ├── filesystem/
        │   │   ├── upload/v1/
        │   │   └── v1/
        │   ├── pipedoc/v1/
        │   └── v1/
        ├── schemamanager/v1/    # Schema management
        ├── testing/harness/v1/  # Testing framework
        └── validation/v1/       # Validation service
```

---

## 🚀 Recommendation

Since you want to do this right and make the platform shine, I recommend we continue with all the naming fixes:

1. **Tonight/Now**: Fix the quick wins (11 errors in 10 minutes)
2. **Tomorrow**: Enum naming (66 errors, automated script)
3. **This Week**: RPC naming (97 errors, semi-automated)

**Total estimated effort**: 6-8 hours to achieve 0 lint errors

**Benefit**: Professional-grade API that follows all Google/Buf best practices

---

## Next Command

Ready to continue? I can start with the quick wins:
```bash
# Fix field naming, service suffix, and unused imports
# Then create enum fixing script
```

Sound good?
